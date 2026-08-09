"""
Livro de Entradas e Saídas — consulta e relatório.

Fontes:
  - Saídas: dados/nfe.json (NF-e emitidas) + dados/vendas.json (POS/NFC-e)
  - Entradas: dados/nfe_entrada.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NFE_FILE = os.path.join(BASE_DIR, "dados", "nfe.json")
NFE_ENTRADA_FILE = os.path.join(BASE_DIR, "dados", "nfe_entrada.json")
VENDAS_FILE = os.path.join(BASE_DIR, "dados", "vendas.json")


def _load(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def _parse_date(s):
    if not s:
        return ""
    if "T" in s:
        return s.split("T")[0]
    return str(s)[:10]


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _item_from_nfe_entrada(it):
    ncm = it.get("ncm") or ""
    vl_total = _safe_float(it.get("vl_total"))
    ibs_cbs = it.get("ibs_cbs") or {}
    return {
        "n_item": it.get("n_item") or "",
        "codigo": it.get("codigo") or "",
        "produto": it.get("nome") or "",
        "ncm": ncm,
        "cfop": it.get("cfop") or "",
        "unidade": it.get("unidade") or "UN",
        "quantidade": _safe_float(it.get("quantidade")),
        "vl_unitario": _safe_float(it.get("vl_unitario")),
        "vl_total": vl_total,
        "vl_icms": _safe_float(it.get("icms_valor")),
        "vl_cbs": _safe_float(ibs_cbs.get("vCBS")),
        "vl_ibs": _safe_float(ibs_cbs.get("vIBS")),
    }


def entradas(dt_ini=None, dt_fim=None, fornecedor=None):
    data = _load(NFE_ENTRADA_FILE)
    rows = []
    for e in data.get("nfe_entradas") or []:
        data_nota = _parse_date(e.get("data_emissao"))
        if dt_ini and data_nota < dt_ini:
            continue
        if dt_fim and data_nota > dt_fim:
            continue
        fn = e.get("fornecedor") or {}
        nome = fn.get("nome") or ""
        if fornecedor and fornecedor.lower() not in nome.lower():
            continue
        total = e.get("total") or {}
        itens = [_item_from_nfe_entrada(it) for it in e.get("itens") or []]
        rows.append({
            "tipo": "entrada",
            "data": data_nota,
            "chave": e.get("chave") or "",
            "numero": e.get("numero") or "",
            "serie": e.get("serie") or "",
            "fornecedor": nome,
            "cnpj": fn.get("cnpj") or "",
            "valor_total": _safe_float(total.get("vNF")),
            "valor_icms": _safe_float(total.get("vICMS")),
            "valor_cbs": _safe_float(total.get("vCBS")),
            "valor_ibs": _safe_float(total.get("vIBS")),
            "itens": itens,
        })
    rows.sort(key=lambda r: r.get("data") or "", reverse=True)
    return rows


def _item_from_nfe_saida(it):
    ncm = str(it.get("ncm") or "").replace(".", "")
    vl_total = _safe_float(it.get("subtotal") or (it.get("preco", 0) * it.get("qtd", 1)))
    return {
        "n_item": str(it.get("prod_id") or ""),
        "codigo": str(it.get("prod_id") or ""),
        "produto": it.get("produto") or "",
        "ncm": ncm,
        "cfop": it.get("cfop") or "",
        "unidade": it.get("unidade") or "UN",
        "quantidade": _safe_float(it.get("qtd")),
        "vl_unitario": _safe_float(it.get("preco")),
        "vl_total": vl_total,
        "vl_icms": _safe_float(it.get("icms_valor") or (vl_total * _safe_float(it.get("icms_alq")) / 100)),
        "vl_cbs": 0.0,
        "vl_ibs": 0.0,
    }


def saidas(dt_ini=None, dt_fim=None, cliente=None):
    data = _load(NFE_FILE)
    rows = []
    for n in data.get("nfe") or []:
        data_nota = _parse_date(n.get("data"))
        if dt_ini and data_nota < dt_ini:
            continue
        if dt_fim and data_nota > dt_fim:
            continue
        nome = n.get("cliente") or ""
        if cliente and cliente.lower() not in nome.lower():
            continue
        itens = n.get("itens") or []
        if not itens and n.get("xml"):
            # tenta extrair itens do XML se não tiver em JSON
            try:
                from lxml import etree
                from modules.sefaz.sped_fiscal import _parse_nota
                parsed = _parse_nota(n)
                itens = parsed.get("itens", [])
            except Exception:
                pass
        rows.append({
            "tipo": "saida",
            "data": data_nota,
            "chave": n.get("chave") or "",
            "numero": n.get("numero") or "",
            "serie": n.get("serie") or "",
            "cliente": nome,
            "cnpj": n.get("cnpj") or "",
            "valor_total": _safe_float(n.get("total")),
            "valor_icms": 0.0,
            "valor_cbs": 0.0,
            "valor_ibs": 0.0,
            "itens": [_item_from_nfe_saida(it) for it in itens],
        })
    rows.sort(key=lambda r: r.get("data") or "", reverse=True)
    return rows


def livro(dt_ini=None, dt_fim=None, tipo=None, parceiro=None):
    """Retorna entradas + saídas unificadas."""
    ent = entradas(dt_ini, dt_fim, parceiro) if tipo in (None, "entrada") else []
    sai = saidas(dt_ini, dt_fim, parceiro) if tipo in (None, "saida") else []
    rows = ent + sai
    rows.sort(key=lambda r: r.get("data") or "", reverse=True)
    total_entradas = sum(r["valor_total"] for r in ent)
    total_saidas = sum(r["valor_total"] for r in sai)
    return {
        "rows": rows,
        "resumo": {
            "entradas": {"qtd": len(ent), "total": round(total_entradas, 2)},
            "saidas": {"qtd": len(sai), "total": round(total_saidas, 2)},
        },
    }
