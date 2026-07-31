"""
Product localization MVP (RFC-4004).

Localiza item externo → produto interno.
Não cria produto, não move estoque, não altera preço.

Prioridade:
1. vínculo fornecedor × código já conhecido
2. GTIN/EAN
3. código fornecedor == id/sku interno
4. sugestões por texto (não auto-associa)
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REFS_FILE = os.path.join(DATA_DIR, "supplier_product_refs.json")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _digits(val):
    return "".join(ch for ch in str(val or "") if ch.isdigit())


def _norm_code(val):
    return str(val or "").strip().upper()


def _load_refs():
    if not os.path.exists(REFS_FILE):
        return {"refs": []}
    with open(REFS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"refs": []}
    if not isinstance(data.get("refs"), list):
        data["refs"] = []
    return data


def _save_refs(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REFS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_refs(supplier_cnpj=None):
    dig = _digits(supplier_cnpj)
    rows = list(_load_refs().get("refs") or [])
    if dig:
        rows = [r for r in rows if _digits(r.get("supplier_cnpj")) == dig]
    return rows


def find_ref(supplier_cnpj, supplier_code=None, ean=None):
    dig = _digits(supplier_cnpj)
    code = _norm_code(supplier_code)
    ean_d = _digits(ean)
    for r in _load_refs().get("refs") or []:
        if dig and _digits(r.get("supplier_cnpj")) != dig:
            continue
        if code and _norm_code(r.get("supplier_code")) == code:
            return r
        if ean_d and _digits(r.get("gtin")) == ean_d:
            return r
    return None


def upsert_ref(
    *,
    supplier_cnpj,
    product_id,
    supplier_code=None,
    supplier_description=None,
    gtin=None,
    manufacturer_reference=None,
    product_nome=None,
    source="manual",
    user_id=None,
):
    """Cria/atualiza SupplierProductReference."""
    dig = _digits(supplier_cnpj)
    pid = str(product_id or "").strip()
    if not pid:
        raise ValueError("product_id obrigatório")
    code = _norm_code(supplier_code)
    ean_d = _digits(gtin)
    if not dig and not code and not ean_d:
        raise ValueError("informe supplier_cnpj, supplier_code ou gtin")

    data = _load_refs()
    refs = data.get("refs") or []
    existing = None
    for r in refs:
        same_sup = (not dig) or (_digits(r.get("supplier_cnpj")) == dig)
        if not same_sup:
            continue
        if code and _norm_code(r.get("supplier_code")) == code:
            existing = r
            break
        if ean_d and _digits(r.get("gtin")) == ean_d and not code:
            existing = r
            break

    if existing is None:
        existing = {
            "id": len(refs) + 1,
            "supplier_cnpj": dig,
            "product_id": pid,
            "supplier_code": code,
            "supplier_description": (supplier_description or "").strip(),
            "gtin": ean_d,
            "manufacturer_reference": (manufacturer_reference or "").strip(),
            "product_nome": (product_nome or "").strip(),
            "source": source,
            "created_at": _now(),
            "created_by": user_id,
            "last_seen_date": _now(),
            "times_seen": 1,
        }
        refs.append(existing)
    else:
        existing["product_id"] = pid
        if code:
            existing["supplier_code"] = code
        if supplier_description:
            existing["supplier_description"] = str(supplier_description).strip()
        if ean_d:
            existing["gtin"] = ean_d
        if manufacturer_reference:
            existing["manufacturer_reference"] = str(manufacturer_reference).strip()
        if product_nome:
            existing["product_nome"] = str(product_nome).strip()
        existing["last_seen_date"] = _now()
        existing["times_seen"] = int(existing.get("times_seen") or 0) + 1
        existing["updated_by"] = user_id
        existing["source"] = source or existing.get("source") or "manual"

    data["refs"] = refs
    _save_refs(data)
    return existing


def _catalog():
    try:
        import cobol_bridge
        return cobol_bridge.produtos_listar() or []
    except Exception:
        return []


def match_item(item, catalog=None, supplier_cnpj=None):
    """
    Retorna {produto_id, produto_nome, match, suggestions?}.
    match: supplier_ref | ean | codigo | none
    """
    catalog = catalog if catalog is not None else _catalog()
    ean = _digits(item.get("ean") or item.get("gtin"))
    cprod = str(item.get("codigo_fornecedor") or item.get("supplier_code") or "").strip()
    desc = (item.get("descricao") or item.get("supplier_description") or "").strip()

    # 1) vínculo conhecido
    ref = find_ref(supplier_cnpj, supplier_code=cprod, ean=ean)
    if ref and ref.get("product_id"):
        pid = str(ref["product_id"])
        nome = ref.get("product_nome") or ""
        for p in catalog:
            if str(p.get("id")) == pid:
                nome = p.get("nome") or nome
                break
        return {
            "produto_id": pid,
            "produto_nome": nome,
            "match": "supplier_ref",
            "ref_id": ref.get("id"),
        }

    # 2) EAN / 3) código == id/sku
    for p in catalog:
        pid = str(p.get("id") or "")
        bars = _digits(p.get("codigo_barras") or p.get("ean") or "")
        sku = str(p.get("sku") or p.get("codigo") or "").strip()
        if ean and bars and ean == bars:
            return {"produto_id": pid, "produto_nome": p.get("nome") or "", "match": "ean"}
        if cprod and (cprod == pid or _norm_code(cprod) == _norm_code(sku)):
            return {"produto_id": pid, "produto_nome": p.get("nome") or "", "match": "codigo"}

    suggestions = suggest_products(
        query=desc or cprod or ean,
        catalog=catalog,
        limit=5,
    )
    return {
        "produto_id": "",
        "produto_nome": desc,
        "match": "none",
        "suggestions": suggestions,
    }


def search_products(query, catalog=None, limit=20):
    """Busca catálogo por id, EAN, sku, nome (para UI de vínculo)."""
    return suggest_products(query=query, catalog=catalog, limit=limit)


def suggest_products(query, catalog=None, limit=8):
    q = str(query or "").strip()
    if not q:
        return []
    catalog = catalog if catalog is not None else _catalog()
    q_low = q.lower()
    q_dig = _digits(q)
    tokens = [t for t in re.split(r"\s+", q_low) if len(t) >= 2]
    scored = []
    for p in catalog:
        if p.get("ativo") is False:
            continue
        pid = str(p.get("id") or "")
        nome = str(p.get("nome") or "")
        nome_l = nome.lower()
        bars = _digits(p.get("codigo_barras") or p.get("ean") or "")
        sku = str(p.get("sku") or p.get("codigo") or "").strip()
        score = 0
        if q_dig and bars and (q_dig == bars or bars.endswith(q_dig) or q_dig.endswith(bars)):
            score += 100
        if q == pid or q_dig == pid:
            score += 90
        if sku and _norm_code(q) == _norm_code(sku):
            score += 80
        if q_low and q_low in nome_l:
            score += 40
        for t in tokens:
            if t in nome_l:
                score += 10
        if score <= 0:
            continue
        scored.append((score, {
            "id": pid,
            "nome": nome,
            "codigo_barras": bars,
            "sku": sku,
            "score": score,
        }))
    scored.sort(key=lambda x: (-x[0], x[1]["nome"]))
    return [row for _, row in scored[: max(1, int(limit or 8))]]


def remember_from_receiving_item(rec, item, produto_id, produto_nome=None, user_id=None):
    """Persiste vínculo a partir de item de receiving (após link manual ou match EAN)."""
    nfe_item = item.get("nfe_item") if isinstance(item.get("nfe_item"), dict) else {}
    supplier_cnpj = (
        (rec or {}).get("fornecedor_cnpj")
        or ((rec or {}).get("nfe") or {}).get("fornecedor_cnpj")
        or ""
    )
    code = nfe_item.get("codigo_fornecedor") or ""
    ean = nfe_item.get("ean") or ""
    desc = nfe_item.get("descricao") or item.get("produto_nome") or ""
    if not _digits(supplier_cnpj) and not _norm_code(code) and not _digits(ean):
        return None
    return upsert_ref(
        supplier_cnpj=supplier_cnpj,
        product_id=produto_id,
        supplier_code=code,
        supplier_description=desc,
        gtin=ean,
        product_nome=produto_nome or item.get("produto_nome"),
        source="manual",
        user_id=user_id,
    )
