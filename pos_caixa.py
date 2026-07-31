"""
Movimentos de caixa POS (sangria / suprimento) — persistência simples.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CAIXA_FILE = os.path.join(DATA_DIR, "pos_caixa_movimentos.json")


def _load():
    if not os.path.exists(CAIXA_FILE):
        return {"movimentos": []}
    with open(CAIXA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"movimentos": []}
    if not isinstance(data.get("movimentos"), list):
        data["movimentos"] = []
    return data


def _save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CAIXA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_movimentos(terminal_id=None, estabelecimento_id=None, limit=50):
    rows = list(_load().get("movimentos") or [])
    tid = str(terminal_id or "").strip()
    eid = str(estabelecimento_id or "").strip()
    if tid:
        rows = [m for m in rows if str(m.get("terminal_id") or "") == tid]
    if eid:
        rows = [m for m in rows if str(m.get("estabelecimento_id") or "") == eid]
    rows.sort(key=lambda m: m.get("at") or "", reverse=True)
    return rows[: max(1, min(int(limit or 50), 200))]


def add_movimento(payload, user_id=None):
    body = payload if isinstance(payload, dict) else {}
    kind = str(body.get("kind") or body.get("tipo") or "").strip().lower()
    if kind in ("sangria", "out", "saida", "saída"):
        kind = "out"
    elif kind in ("suprimento", "in", "entrada"):
        kind = "in"
    else:
        raise ValueError("kind deve ser in (suprimento) ou out (sangria)")
    try:
        value = float(body.get("value") or body.get("valor") or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        raise ValueError("valor deve ser > 0")
    reason = (body.get("reason") or body.get("motivo") or "").strip()
    if not reason:
        raise ValueError("motivo obrigatório")

    data = _load()
    mid = int(datetime.now().timestamp() * 1000)
    entry = {
        "id": mid,
        "kind": kind,
        "value": round(value, 2),
        "reason": reason,
        "docType": body.get("docType") or body.get("doc_type") or "",
        "docRef": body.get("docRef") or body.get("doc_ref") or "",
        "terminal_id": body.get("terminal_id") or "",
        "estabelecimento_id": body.get("estabelecimento_id") or "",
        "user_id": user_id,
        "user_nome": body.get("user_nome") or "",
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    data["movimentos"].append(entry)
    # mantém últimos 500
    if len(data["movimentos"]) > 500:
        data["movimentos"] = data["movimentos"][-500:]
    _save(data)
    return entry
