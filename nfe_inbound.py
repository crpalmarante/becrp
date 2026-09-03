"""
NF-e inbound (RFC-4002) — parse fiscal leve + criação de receiving draft.

Não move estoque.
Fluxo: XML → validar → draft Receiving (itens com match).
Auto-cria fornecedor (parceiro SUPPLIER) e produto quando sem match.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from xml.etree import ElementTree as ET

import org_store
import receiving_mvp
import product_localization

QTY_DECIMALS = 3


def _as_qty(val, default=0.0):
    try:
        q = float(val)
    except (TypeError, ValueError):
        return float(default)
    if q < 0:
        return 0.0
    return round(q, QTY_DECIMALS)

try:
    from lxml import etree as LET
    HAS_LXML = True
except ImportError:
    HAS_LXML = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XML_STORE = os.path.join(BASE_DIR, "data", "nfe_inbound")


def _local(tag):
    if not tag:
        return ""
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _find(el, name):
    if el is None:
        return None
    for child in el.iter():
        if _local(child.tag) == name:
            return child
    return None


def _find_direct(el, name):
    if el is None:
        return None
    for child in list(el):
        if _local(child.tag) == name:
            return child
    return None


def _text(el, default=""):
    if el is None or el.text is None:
        return default
    return str(el.text).strip()


def _digits(val):
    return "".join(ch for ch in str(val or "") if ch.isdigit())


def _parse_root(xml_bytes: bytes):
    if HAS_LXML:
        parser = LET.XMLParser(recover=True, resolve_entities=False, no_network=True)
        return LET.fromstring(xml_bytes, parser=parser)
    return ET.fromstring(xml_bytes)


def parse_nfe_xml(xml_text_or_bytes):
    """
    Extrai cabeçalho + itens de NF-e modelo 55.
    Retorna dict ou levanta ValueError.
    """
    if isinstance(xml_text_or_bytes, str):
        raw = xml_text_or_bytes.encode("utf-8", errors="replace")
    else:
        raw = bytes(xml_text_or_bytes or b"")
    if not raw.strip():
        raise ValueError("XML vazio")

    try:
        root = _parse_root(raw)
    except Exception as e:
        raise ValueError(f"XML ilegível: {e}") from e

    # aceita nfeProc > NFe > infNFe ou NFe > infNFe
    inf = _find(root, "infNFe")
    if inf is None:
        raise ValueError("estrutura inválida: infNFe não encontrado")

    # lxml: Element com só texto é falsy (len==0) — nunca usar `a or b` em Element
    ide = _find_direct(inf, "ide")
    if ide is None:
        ide = _find(inf, "ide")
    emit = _find_direct(inf, "emit")
    if emit is None:
        emit = _find(inf, "emit")
    dest = _find_direct(inf, "dest")
    if dest is None:
        dest = _find(inf, "dest")
    total = _find_direct(inf, "total")
    if total is None:
        total = _find(inf, "total")

    mod = _text(_find(ide, "mod")) if ide is not None else ""
    if mod and mod not in ("55", "65"):
        raise ValueError(f"modelo não suportado no MVP: {mod} (esperado 55)")
    if not mod:
        mod = "55"

    # chave: Id="NFe3524..." ou protNFe/infProt/chNFe
    chave = ""
    id_attr = inf.get("Id") or inf.get("id") or ""
    if id_attr.upper().startswith("NFE"):
        chave = _digits(id_attr)
    if not chave:
        chave = _digits(_text(_find(root, "chNFe")))
    if len(chave) != 44:
        # tenta montar a partir de cUF+AAMM+CNPJ+mod+serie+nNF+tpEmis+cNF+cDV — skip no MVP
        raise ValueError("chave de acesso inválida ou ausente (44 dígitos)")

    nNF = _text(_find(ide, "nNF")) if ide is not None else ""
    serie = _text(_find(ide, "serie")) if ide is not None else ""
    dhEmi = ""
    if ide is not None:
        dhEmi = _text(_find(ide, "dhEmi")) or _text(_find(ide, "dEmi"))

    def _doc_id(party):
        if party is None:
            return ""
        el = _find(party, "CNPJ")
        if el is None:
            el = _find(party, "CPF")
        return _digits(_text(el))

    emit_cnpj = _doc_id(emit)
    emit_nome = ""
    if emit is not None:
        emit_nome = _text(_find(emit, "xNome")) or _text(_find(emit, "xFant"))
    dest_cnpj = _doc_id(dest)
    dest_nome = _text(_find(dest, "xNome")) if dest is not None else ""

    vNF = 0.0
    total_dict = {}
    if total is not None:
        icms_tot = _find(total, "ICMSTot")
        if icms_tot is not None:
            for tag in ("vBC", "vICMS", "vICMSDeson", "vFCP", "vBCST", "vST",
                        "vFCPST", "vFCPSTRet", "vProd", "vFrete", "vSeg",
                        "vDesc", "vII", "vIPI", "vIPIDevol", "vPIS", "vCOFINS",
                        "vOutro", "vNF"):
                val = _text(_find(icms_tot, tag))
                if val:
                    total_dict[tag] = val
        try:
            vNF = float(total_dict.get("vNF") or 0)
        except ValueError:
            vNF = 0.0

    # cobrança / duplicatas
    duplicatas = []
    cobr = _find_direct(inf, "cobr")
    if cobr is None:
        cobr = _find(inf, "cobr")
    if cobr is not None:
        for dup in cobr:
            if _local(dup.tag) != "dup":
                continue
            n_dup = _text(_find(dup, "nDup"))
            d_venc = _text(_find(dup, "dVenc"))
            try:
                v_dup = float(_text(_find(dup, "vDup")) or 0)
            except ValueError:
                v_dup = 0.0
            duplicatas.append({
                "n_dup": n_dup,
                "vencimento": d_venc[:10] if d_venc else "",
                "valor": v_dup,
            })

    itens = []
    for det in inf.iter():
        if _local(det.tag) != "det":
            continue
        prod = _find_direct(det, "prod")
        if prod is None:
            prod = _find(det, "prod")
        if prod is None:
            continue
        nitem = det.get("nItem") or str(len(itens) + 1)
        try:
            qcom = float(_text(_find(prod, "qCom")) or 0)
        except ValueError:
            qcom = 0.0
        try:
            vun = float(_text(_find(prod, "vUnCom")) or 0)
        except ValueError:
            vun = 0.0
        try:
            vprod = float(_text(_find(prod, "vProd")) or 0)
        except ValueError:
            vprod = 0.0
        ean = _digits(_text(_find(prod, "cEAN")))
        if not ean:
            ean = _digits(_text(_find(prod, "cEANTrib")))
        itens.append({
            "n_item": nitem,
            "codigo_fornecedor": _text(_find(prod, "cProd")),
            "ean": ean,
            "descricao": _text(_find(prod, "xProd")),
            "ncm": _digits(_text(_find(prod, "NCM"))),
            "cfop": _text(_find(prod, "CFOP")),
            "unidade": _text(_find(prod, "uCom")) or "UN",
            "qty": _as_qty(qcom),
            "preco_unit": vun,
            "valor": vprod,
        })

    if not itens:
        raise ValueError("NF-e sem itens")

    return {
        "chave": chave,
        "modelo": mod,
        "numero": nNF,
        "serie": serie,
        "emissao": dhEmi,
        "fornecedor_cnpj": emit_cnpj,
        "fornecedor_nome": emit_nome,
        "destinatario_cnpj": dest_cnpj,
        "destinatario_nome": dest_nome,
        "valor_total": vNF,
        "total": total_dict,
        "duplicatas": duplicatas,
        "itens": itens,
        "xml_sha256": hashlib.sha256(raw).hexdigest(),
    }


def resolve_estabelecimento_by_cnpj(dest_cnpj, hint_id=None):
    """Casa destinatário com estabelecimento; hint_id tem prioridade se CNPJ bater ou estiver vazio."""
    hint = str(hint_id or "").strip()
    empresas = org_store.load_empresas()
    dig = _digits(dest_cnpj)

    if hint and hint in empresas:
        est = empresas[hint]
        ec = _digits(est.get("cnpj"))
        # se hint tem CNPJ e XML tem outro, ainda assim permite override manual (usuário escolheu loja)
        if not dig or not ec or dig == ec or hint:
            return hint, "ok" if (not dig or not ec or dig == ec) else "cnpj_divergente"

    matches = []
    for eid, e in empresas.items():
        if dig and _digits(e.get("cnpj")) == dig:
            matches.append(eid)
    if len(matches) == 1:
        return matches[0], "ok"
    if len(matches) > 1:
        return (hint if hint in matches else matches[0]), "multiplo"
    if hint and hint in empresas:
        return hint, "sem_match_cnpj_usando_hint"
    # fallback padrão
    padrao = org_store.estabelecimento_padrao_id()
    if padrao:
        return padrao, "fallback_padrao"
    raise ValueError("empresa destinatária não identificada (CNPJ não casa com nenhum estabelecimento)")


def match_produto(item, catalog, supplier_cnpj=None):
    """Delega à RFC-4004 (product_localization)."""
    return product_localization.match_item(
        item, catalog=catalog, supplier_cnpj=supplier_cnpj
    )


def _ensure_supplier(parsed, user_id=None):
    """
    Localiza fornecedor; se not_found e CNPJ válido, cria parceiro SUPPLIER.
    Retorna (partner_id|None, partner_lookup dict, created bool).
    """
    import partner_lookup

    cnpj = _digits(parsed.get("fornecedor_cnpj"))
    nome = (parsed.get("fornecedor_nome") or "").strip() or f"Fornecedor {cnpj}"
    pl = partner_lookup.lookup(cnpj=cnpj, role="SUPPLIER", module="receiving.nfe")
    info = {
        "status": pl.get("status"),
        "match": pl.get("match"),
        "criteria": pl.get("criteria"),
        "partners": pl.get("partners") or [],
        "partner": pl.get("partner"),
        "auto_created": False,
    }
    if pl.get("status") == "found" and pl.get("partner"):
        return pl["partner"]["id"], info, False
    if pl.get("status") == "multiple":
        info["partner"] = None
        return None, info, False
    if len(cnpj) != 14:
        info["partner"] = None
        return None, info, False

    import partners_store
    created = partners_store.save(
        {
            "display_name": nome[:40],
            "legal_name": nome[:60],
            "trade_name": nome[:40],
            "person_type": "COMPANY",
            "roles": ["SUPPLIER"],
            "status": "ACTIVE",
            "documents": [{"document_type": "CNPJ", "document_number": cnpj}],
            "observacao": f"auto NF-e {_digits(parsed.get('chave'))[:14]}",
            "ativo": True,
        },
        is_new=True,
    )
    pid = created.get("id") if created else None
    info["status"] = "found"
    info["match"] = "auto_created"
    info["auto_created"] = True
    info["partner"] = {
        "id": pid,
        "display_name": nome,
        "legal_name": nome,
        "documents": [{"document_type": "CNPJ", "document_number": cnpj}],
    }
    return pid, info, True


def _ensure_product(it, supplier_cnpj, catalog, user_id=None):
    """Cria produto COBOL + referência fornecedor quando sem match."""
    import cobol_bridge

    nome = (it.get("descricao") or "Produto NF-e")[:60]
    ean = _digits(it.get("ean"))
    ncm = _digits(it.get("ncm"))
    custo = float(it.get("preco_unit") or 0)
    pid = cobol_bridge.produtos_incluir({
        "nome": nome,
        "categoria": "Importacao NF-e",  # COBOL exige categoria; NF-e nao traz no XML
        "preco": custo,
        "preco_custo": custo,
        "stock": 0,
        "ativo": True,
        "codigo_barras": ean[:14] if ean else "",
        "unidade": (it.get("unidade") or "UN")[:6],
        "ncm": ncm[:8] if ncm else "",
        "cfop": (it.get("cfop") or "")[:4],  # CFOP da propria nota (default do produto)
        "fornecedor": _digits(supplier_cnpj)[:18],
        "fracionado": True,
    }, importacao=True)
    pid_s = str(pid)
    try:
        product_localization.upsert_ref(
            supplier_cnpj=supplier_cnpj,
            product_id=pid_s,
            supplier_code=it.get("codigo_fornecedor"),
            supplier_description=it.get("descricao"),
            gtin=ean,
            product_nome=nome,
            source="nfe_auto",
            user_id=user_id,
        )
    except Exception:
        pass
    catalog.append({
        "id": pid,
        "nome": nome,
        "codigo_barras": ean,
        "ncm": ncm,
    })
    return {
        "produto_id": pid_s,
        "produto_nome": nome,
        "match": "auto_created",
    }


def _store_xml(chave, raw: bytes):
    os.makedirs(XML_STORE, exist_ok=True)
    path = os.path.join(XML_STORE, f"{chave}.xml")
    with open(path, "wb") as f:
        f.write(raw)
    return path


def find_by_chave(chave):
    chave = _digits(chave)
    for r in receiving_mvp.list_receivings():
        if _digits((r.get("nfe") or {}).get("chave")) == chave:
            return r
        if _digits(r.get("documento_ref")) == chave:
            return r
    return None


def create_receiving_from_nfe(
    xml_text_or_bytes,
    *,
    estabelecimento_id=None,
    user_id=None,
    catalog=None,
    auto_create=True,
):
    """
    Valida XML, resolve loja, faz match de produtos, cria draft origem=nfe.
    auto_create=True: cria fornecedor e produtos sem match.
    """
    if isinstance(xml_text_or_bytes, str):
        raw = xml_text_or_bytes.encode("utf-8", errors="replace")
    else:
        raw = bytes(xml_text_or_bytes or b"")

    parsed = parse_nfe_xml(raw)
    if parsed.get("modelo") == "65":
        raise ValueError("NFC-e (65) não é entrada de fornecedor no MVP — use NF-e 55")

    dup = find_by_chave(parsed["chave"])
    if dup and dup.get("status") != "cancelled":
        raise ValueError(f"NF-e já importada no recebimento #{dup.get('id')} (status={dup.get('status')})")

    eid, resolve_status = resolve_estabelecimento_by_cnpj(
        parsed.get("destinatario_cnpj"), hint_id=estabelecimento_id
    )

    if catalog is None:
        try:
            import cobol_bridge
            catalog = cobol_bridge.produtos_listar() or []
        except Exception:
            catalog = []
    else:
        catalog = list(catalog)

    supplier_cnpj = parsed.get("fornecedor_cnpj") or ""
    fornecedor_id = None
    partner_info = {}
    auto_supplier = False
    try:
        if auto_create:
            fornecedor_id, partner_info, auto_supplier = _ensure_supplier(parsed, user_id=user_id)
        else:
            import partner_lookup
            pl = partner_lookup.lookup(
                cnpj=supplier_cnpj, role="SUPPLIER", module="receiving.nfe"
            )
            partner_info = {
                "status": pl.get("status"),
                "match": pl.get("match"),
                "criteria": pl.get("criteria"),
                "partners": pl.get("partners") or [],
                "partner": pl.get("partner"),
                "auto_created": False,
            }
            if pl.get("status") == "found" and pl.get("partner"):
                fornecedor_id = pl["partner"]["id"]
    except Exception as e:
        partner_info = {"status": "error", "error": str(e), "auto_created": False}

    items = []
    pending = 0
    auto_products = 0
    for it in parsed["itens"]:
        qty = _as_qty(it.get("qty"))
        if qty <= 0:
            continue
        m = match_produto(it, catalog, supplier_cnpj=supplier_cnpj)
        if m["match"] == "none" and auto_create:
            try:
                m = _ensure_product(it, supplier_cnpj, catalog, user_id=user_id)
                auto_products += 1
            except Exception:
                pending += 1
        elif m["match"] == "none":
            pending += 1
        row = {
            "produto_id": m.get("produto_id") or "",
            "produto_nome": m.get("produto_nome") or it.get("descricao") or "",
            "qty_expected": qty,
            "qty_verified": None,
            "unidade": it.get("unidade") or "UN",
            "match": m.get("match") or "none",
            "nfe_item": {
                "n_item": it.get("n_item"),
                "codigo_fornecedor": it.get("codigo_fornecedor"),
                "ean": it.get("ean"),
                "descricao": it.get("descricao"),
                "ncm": it.get("ncm"),
                "cfop": it.get("cfop"),
                "qty_xml": qty,
                "preco_unit": it.get("preco_unit"),
            },
        }
        if m.get("suggestions"):
            row["suggestions"] = m["suggestions"]
        items.append(row)

    if not items:
        raise ValueError("nenhum item com quantidade válida")

    xml_path = _store_xml(parsed["chave"], raw)
    fornecedor_nome = parsed.get("fornecedor_nome") or ""
    if partner_info.get("partner"):
        fornecedor_nome = (
            partner_info["partner"].get("display_name")
            or partner_info["partner"].get("legal_name")
            or fornecedor_nome
        )

    payload = {
        "estabelecimento_id": eid,
        "origem": "nfe",
        "fornecedor_nome": fornecedor_nome,
        "fornecedor_cnpj": supplier_cnpj,
        "fornecedor_id": fornecedor_id,
        "documento_ref": parsed["chave"],
        "nota": f"NF-e {parsed.get('numero')}/{parsed.get('serie')} · {parsed.get('emissao')}",
        "items": items,
        "allow_unmatched": True,
        "partner_lookup": partner_info,
        "nfe": {
            "chave": parsed["chave"],
            "modelo": parsed["modelo"],
            "numero": parsed.get("numero"),
            "serie": parsed.get("serie"),
            "emissao": parsed.get("emissao"),
            "valor_total": parsed.get("valor_total"),
            "total": parsed.get("total") or {},
            "duplicatas": parsed.get("duplicatas") or [],
            "destinatario_cnpj": parsed.get("destinatario_cnpj"),
            "fornecedor_cnpj": supplier_cnpj,
            "xml_path": xml_path,
            "xml_sha256": parsed.get("xml_sha256"),
            "resolve_estabelecimento": resolve_status,
            "itens_sem_match": pending,
            "auto_created_supplier": auto_supplier,
            "auto_created_products": auto_products,
        },
    }

    rec = receiving_mvp.create_receiving(payload, user_id=user_id)
    return rec
