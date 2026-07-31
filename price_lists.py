"""
Listas de preço (estilo Odoo, MVP).

- produto.preco = preço base
- lista com itens fixos (produto_id → preço)
- estabelecimento.default_price_list_id → lista padrão da loja
- resolução: item da lista → senão preco base
"""

from __future__ import annotations

import json
import os
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LISTS_FILE = os.path.join(DATA_DIR, "price_lists.json")


def _load():
    if not os.path.exists(LISTS_FILE):
        return {"lists": []}
    with open(LISTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"lists": []}
    if not isinstance(data.get("lists"), list):
        data["lists"] = []
    return data


def _save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LISTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _norm_items(raw):
    """Aceita dict {id: preço} ou lista [{produto_id, preco}]."""
    out = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                price = float(v)
            except (TypeError, ValueError):
                continue
            if price < 0:
                continue
            out[str(k)] = round(price, 2)
        return out
    if isinstance(raw, list):
        for row in raw:
            if not isinstance(row, dict):
                continue
            pid = row.get("produto_id")
            if pid is None:
                pid = row.get("id")
            if pid is None:
                continue
            try:
                price = float(row.get("preco") if row.get("preco") is not None else row.get("price"))
            except (TypeError, ValueError):
                continue
            if price < 0:
                continue
            out[str(pid)] = round(price, 2)
    return out


def list_all(active_only=False):
    rows = list(_load().get("lists") or [])
    if active_only:
        rows = [x for x in rows if x.get("active", True)]
    rows.sort(key=lambda x: (x.get("name") or x.get("code") or x.get("id") or "").lower())
    return rows


def get_list(list_id):
    lid = str(list_id or "").strip()
    if not lid:
        return None
    for row in _load().get("lists") or []:
        if str(row.get("id")) == lid:
            return row
    return None


def upsert_list(payload, list_id=None):
    body = payload if isinstance(payload, dict) else {}
    data = _load()
    lid = str(list_id or body.get("id") or "").strip()
    existing = None
    idx = None
    if lid:
        for i, row in enumerate(data["lists"]):
            if str(row.get("id")) == lid:
                existing = row
                idx = i
                break
    if not lid:
        lid = "pl_" + str(uuid.uuid4())[:8]

    name = (body.get("name") or body.get("nome") or (existing or {}).get("name") or "").strip()
    if not name:
        raise ValueError("name obrigatório")
    code = (body.get("code") or body.get("codigo") or (existing or {}).get("code") or name).strip()
    active = body.get("active")
    if active is None:
        active = (existing or {}).get("active", True)
    active = bool(active)

    if "items" in body:
        items = _norm_items(body.get("items"))
    else:
        items = dict((existing or {}).get("items") or {})

    row = {
        "id": lid,
        "name": name,
        "code": code,
        "active": active,
        "items": items,
    }
    if idx is None:
        data["lists"].append(row)
    else:
        data["lists"][idx] = row
    _save(data)
    return row


def delete_list(list_id):
    lid = str(list_id or "").strip()
    data = _load()
    before = len(data["lists"])
    data["lists"] = [x for x in data["lists"] if str(x.get("id")) != lid]
    if len(data["lists"]) == before:
        raise ValueError("lista não encontrada")
    _save(data)
    return True


def set_item(list_id, produto_id, preco):
    pl = get_list(list_id)
    if not pl:
        raise ValueError("lista não encontrada")
    try:
        price = float(preco)
    except (TypeError, ValueError):
        raise ValueError("preço inválido")
    if price < 0:
        raise ValueError("preço inválido")
    items = dict(pl.get("items") or {})
    items[str(produto_id)] = round(price, 2)
    return upsert_list({"name": pl["name"], "code": pl.get("code"), "active": pl.get("active", True), "items": items}, list_id=pl["id"])


def remove_item(list_id, produto_id):
    pl = get_list(list_id)
    if not pl:
        raise ValueError("lista não encontrada")
    items = dict(pl.get("items") or {})
    items.pop(str(produto_id), None)
    return upsert_list({"name": pl["name"], "code": pl.get("code"), "active": pl.get("active", True), "items": items}, list_id=pl["id"])


def resolve_price(produto, list_id=None):
    """
    Retorna dict com preco resolvido.
    produto: dict com id e preco (base).
    """
    base = 0.0
    try:
        base = float((produto or {}).get("preco") or 0)
    except (TypeError, ValueError):
        base = 0.0
    pid = str((produto or {}).get("id") or "")
    lid = str(list_id or "").strip()
    source = "base"
    price = round(base, 2)
    if lid and pid:
        pl = get_list(lid)
        if pl and pl.get("active", True):
            items = pl.get("items") or {}
            if pid in items:
                try:
                    price = round(float(items[pid]), 2)
                    source = "list"
                except (TypeError, ValueError):
                    pass
    return {
        "preco": price,
        "preco_base": round(base, 2),
        "price_list_id": lid or None,
        "price_source": source,
    }


def apply_to_produtos(produtos, estabelecimento_id=None, list_id=None):
    """Aplica resolução de preço em lista de produtos (mutável)."""
    lid = str(list_id or "").strip()
    if not lid and estabelecimento_id:
        try:
            import org_store

            empresas = org_store.load_empresas()
            estab = empresas.get(str(estabelecimento_id)) or {}
            lid = str(estab.get("default_price_list_id") or "").strip()
        except Exception:
            lid = ""
    out = []
    for p in produtos or []:
        if not isinstance(p, dict):
            continue
        row = dict(p)
        resolved = resolve_price(row, lid)
        row["preco_base"] = resolved["preco_base"]
        row["preco"] = resolved["preco"]
        row["price_list_id"] = resolved["price_list_id"]
        row["price_source"] = resolved["price_source"]
        out.append(row)
    return out
