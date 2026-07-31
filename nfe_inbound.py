"""
NF-e inbound (RFC-4002) — parse fiscal leve + criação de receiving draft.

Não move estoque. Não cria produto/fornecedor.
Fluxo: XML → validar → draft Receiving (itens com match opcional).
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from xml.etree import ElementTree as ET

import org_store
import receiving_mvp

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
    if total is not None:
        icms_tot = _find(total, "ICMSTot")
        try:
            vNF = float(_text(_find(icms_tot, "vNF") if icms_tot is not None else None) or 0)
        except ValueError:
            vNF = 0.0

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
            "qty": qcom,
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


def match_produto(item, catalog):
    """
    Match mínimo RFC-4004: EAN → código barras; depois código fornecedor == id/sku.
    """
    ean = _digits(item.get("ean"))
    cprod = str(item.get("codigo_fornecedor") or "").strip()
    for p in catalog or []:
        pid = str(p.get("id") or "")
        bars = _digits(p.get("codigo_barras") or p.get("ean") or "")
        sku = str(p.get("sku") or "").strip()
        if ean and bars and ean == bars:
            return {"produto_id": pid, "produto_nome": p.get("nome") or "", "match": "ean"}
        if cprod and (cprod == pid or cprod == sku):
            return {"produto_id": pid, "produto_nome": p.get("nome") or "", "match": "codigo"}
    return {"produto_id": "", "produto_nome": item.get("descricao") or "", "match": "none"}


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


def create_receiving_from_nfe(xml_text_or_bytes, *, estabelecimento_id=None, user_id=None, catalog=None):
    """
    Valida XML, resolve loja, faz match de produtos, cria draft origem=nfe.
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

    items = []
    pending = 0
    for it in parsed["itens"]:
        m = match_produto(it, catalog)
        qty = it.get("qty") or 0
        try:
            qty_i = int(round(float(qty)))
        except (TypeError, ValueError):
            qty_i = 0
        if qty_i <= 0 and float(qty or 0) > 0:
            # fracionado: arredonda para cima mínimo 1 se <1? keep round
            qty_i = max(1, int(round(float(qty)))) if float(qty) >= 0.5 else 0
        if qty_i <= 0:
            continue
        if m["match"] == "none":
            pending += 1
        items.append({
            "produto_id": m["produto_id"] or "",
            "produto_nome": m["produto_nome"] or it.get("descricao") or "",
            "qty_expected": qty_i,
            "qty_verified": None,
            "unidade": it.get("unidade") or "UN",
            "match": m["match"],
            "nfe_item": {
                "n_item": it.get("n_item"),
                "codigo_fornecedor": it.get("codigo_fornecedor"),
                "ean": it.get("ean"),
                "descricao": it.get("descricao"),
                "ncm": it.get("ncm"),
                "qty_xml": it.get("qty"),
                "preco_unit": it.get("preco_unit"),
            },
        })

    if not items:
        raise ValueError("nenhum item com quantidade válida")

    xml_path = _store_xml(parsed["chave"], raw)

    # create via receiving_mvp with relaxed items (allow empty produto_id)
    payload = {
        "estabelecimento_id": eid,
        "origem": "nfe",
        "fornecedor_nome": parsed.get("fornecedor_nome") or "",
        "fornecedor_cnpj": parsed.get("fornecedor_cnpj") or "",
        "documento_ref": parsed["chave"],
        "nota": f"NF-e {parsed.get('numero')}/{parsed.get('serie')} · {parsed.get('emissao')}",
        "items": items,
        "allow_unmatched": True,
        "nfe": {
            "chave": parsed["chave"],
            "modelo": parsed["modelo"],
            "numero": parsed.get("numero"),
            "serie": parsed.get("serie"),
            "emissao": parsed.get("emissao"),
            "valor_total": parsed.get("valor_total"),
            "destinatario_cnpj": parsed.get("destinatario_cnpj"),
            "fornecedor_cnpj": parsed.get("fornecedor_cnpj"),
            "xml_path": xml_path,
            "xml_sha256": parsed.get("xml_sha256"),
            "resolve_estabelecimento": resolve_status,
            "itens_sem_match": pending,
        },
    }
    rec = receiving_mvp.create_receiving(payload, user_id=user_id)
    return rec
