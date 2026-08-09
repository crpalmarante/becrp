"""
Escrituração de NF-e de entrada (dados/nfe_entrada.json).

Usado pelo SPED fiscal e livro de entradas.
Receiving complete → upsert aqui.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import fiscal_reforma_store
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "nfe_entrada.json")


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _digits(val):
    return "".join(c for c in str(val or "") if c.isdigit())


def _calc_ibs_cbs_item(vl_total, ncm):
    try:
        return fiscal_reforma_store.calcular(float(vl_total), ncm=ncm, contexto="nfe_entrada")
    except Exception:
        return {
            "valor_operacao": float(vl_total),
            "cbs": 0.0,
            "ibs": 0.0,
            "aliquota_cbs": 0.6,
            "aliquota_ibs": 17.0,
            "reducao_base": 0.0,
        }


def _load():
    if not os.path.exists(DATA_FILE):
        return {"nfe_entradas": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"nfe_entradas": []}
    data.setdefault("nfe_entradas", [])
    if not isinstance(data["nfe_entradas"], list):
        data["nfe_entradas"] = []
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    jsonio.save(DATA_FILE, data)


def listar():
    return list(_load().get("nfe_entradas") or [])


def find_by_chave(chave):
    dig = _digits(chave)
    for row in listar():
        if _digits(row.get("chave")) == dig:
            return row
    return None


def upsert_from_receiving(rec, parsed=None):
    """
    Grava/atualiza entrada fiscal a partir do receiving concluído.
    parsed: opcional (saída de nfe_inbound.parse_nfe_xml).
    """
    rec = rec or {}
    nfe = dict(rec.get("nfe") or {})
    chave = _digits(nfe.get("chave") or rec.get("documento_ref"))
    if len(chave) != 44:
        raise ValueError("receiving sem chave NF-e válida para escrituração")

    # totais / itens do XML se disponível
    tot = {}
    itens_xml = []
    if parsed:
        tot = {
            "vNF": f"{float(parsed.get('valor_total') or 0):.2f}",
            "vProd": f"{float(parsed.get('valor_total') or 0):.2f}",
        }
        if parsed.get("total"):
            tot.update(parsed["total"])
        for it in parsed.get("itens") or []:
            vl_total = float(it.get('valor') or 0)
            ncm = it.get("ncm") or ""
            ibs_cbs = _calc_ibs_cbs_item(vl_total, ncm)
            itens_xml.append({
                "n_item": str(it.get("n_item") or ""),
                "codigo": it.get("codigo_fornecedor") or "",
                "nome": it.get("descricao") or "",
                "ncm": ncm,
                "cfop": it.get("cfop") or "",
                "cest": "",
                "ean": it.get("ean") or "",
                "unidade": it.get("unidade") or "UN",
                "quantidade": f"{float(it.get('qty') or 0):.4f}",
                "vl_unitario": f"{float(it.get('preco_unit') or 0):.10f}",
                "vl_total": f"{vl_total:.2f}",
                "icms_cst": "",
                "icms_csosn": "",
                "icms_aliquota": "",
                "icms_valor": "",
                "ibs_cbs": {
                    "vBC": ibs_cbs.get("valor_operacao"),
                    "pCBS": ibs_cbs.get("aliquota_cbs"),
                    "vCBS": ibs_cbs.get("cbs"),
                    "pIBS": ibs_cbs.get("aliquota_ibs"),
                    "vIBS": ibs_cbs.get("ibs"),
                },
            })

    if not itens_xml:
        for i, it in enumerate(rec.get("items") or [], start=1):
            nx = it.get("nfe_item") or {}
            q = it.get("qty_verified")
            if q is None:
                q = it.get("qty_expected") or nx.get("qty_xml") or 0
            vl_total = float(q or 0) * float(nx.get('preco_unit') or 0)
            ncm = nx.get("ncm") or ""
            ibs_cbs = _calc_ibs_cbs_item(vl_total, ncm)
            itens_xml.append({
                "n_item": str(nx.get("n_item") or i),
                "codigo": nx.get("codigo_fornecedor") or "",
                "nome": nx.get("descricao") or it.get("produto_nome") or "",
                "ncm": ncm,
                "cfop": "",
                "cest": "",
                "ean": nx.get("ean") or "",
                "unidade": it.get("unidade") or "UN",
                "quantidade": f"{float(q or 0):.4f}",
                "vl_unitario": f"{float(nx.get('preco_unit') or 0):.10f}",
                "vl_total": f"{vl_total:.2f}",
                "produto_id": it.get("produto_id") or "",
                "icms_cst": "",
                "icms_csosn": "",
                "icms_aliquota": "",
                "icms_valor": "",
                "ibs_cbs": {
                    "vBC": ibs_cbs.get("valor_operacao"),
                    "pCBS": ibs_cbs.get("aliquota_cbs"),
                    "vCBS": ibs_cbs.get("cbs"),
                    "pIBS": ibs_cbs.get("aliquota_ibs"),
                    "vIBS": ibs_cbs.get("ibs"),
                },
            })

    if not tot:
        try:
            tot = {"vNF": f"{float(nfe.get('valor_total') or 0):.2f}"}
        except (TypeError, ValueError):
            tot = {"vNF": "0.00"}

    # Totais IBS/CBS (Reforma Tributária) calculados sobre vNF
    vnf_total = float(tot.get("vNF", 0))
    total_ibs_cbs = _calc_ibs_cbs_item(vnf_total, "")
    tot["vCBS"] = f"{total_ibs_cbs.get('cbs') or 0:.2f}"
    tot["vIBS"] = f"{total_ibs_cbs.get('ibs') or 0:.2f}"
    tot["pCBS"] = f"{total_ibs_cbs.get('aliquota_cbs') or 0:.2f}"
    tot["pIBS"] = f"{total_ibs_cbs.get('aliquota_ibs') or 0:.2f}"

    emissao = (nfe.get("emissao") or "")[:10]
    if "T" in emissao:
        emissao = emissao.split("T")[0]

    row = {
        "chave": chave,
        "numero": str(nfe.get("numero") or ""),
        "serie": str(nfe.get("serie") or ""),
        "data_emissao": emissao,
        "data_importacao": _now(),
        "receiving_id": rec.get("id"),
        "estabelecimento_id": rec.get("estabelecimento_id"),
        "fornecedor": {
            "cnpj": _digits(nfe.get("fornecedor_cnpj") or rec.get("fornecedor_cnpj")),
            "nome": rec.get("fornecedor_nome") or "",
            "ie": "",
            "partner_id": rec.get("fornecedor_id") or "",
        },
        "total": tot,
        "itens": itens_xml,
        "duplicatas": list(nfe.get("duplicatas") or (parsed or {}).get("duplicatas") or []),
        "status": "ESCRITURADA",
        "xml_path": nfe.get("xml_path") or "",
    }

    data = _load()
    rows = data["nfe_entradas"]
    for i, existing in enumerate(rows):
        if _digits(existing.get("chave")) == chave:
            row["data_importacao"] = existing.get("data_importacao") or row["data_importacao"]
            rows[i] = row
            _save(data)
            return row
    rows.insert(0, row)
    _save(data)
    return row
