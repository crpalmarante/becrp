"""
Delivery — Resources (RFC-18004 MVP).

Motoristas / veículos / equipes de entrega.
Fonte: dados/delivery_resources.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "delivery_resources.json")

TIPOS = {
    "driver": "Motorista",
    "vehicle": "Veículo",
    "team": "Equipe",
    "carrier": "Transportadora",
}

STATUSES = {
    "available": "Disponível",
    "busy": "Em rota",
    "offline": "Offline",
    "inactive": "Inativo",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("recursos"), list):
        return ensure_seed()
    if not data["recursos"]:
        return ensure_seed()
    data.setdefault("seq", len(data["recursos"]))
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("recursos") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_seed():
    now = _now()
    rows = [
        {
            "id": "DRV-01",
            "tipo": "driver",
            "nome": "Carlos Motorista",
            "placa": "",
            "telefone": "(54) 98888-1001",
            "capacidade": 0,
            "status": "available",
            "ativo": True,
            "observacao": "Seed",
            "criado_em": now,
            "atualizado_em": now,
        },
        {
            "id": "VEH-01",
            "tipo": "vehicle",
            "nome": "Fiat Fiorino",
            "placa": "ABC1D23",
            "telefone": "",
            "capacidade": 500,
            "status": "available",
            "ativo": True,
            "observacao": "Seed",
            "criado_em": now,
            "atualizado_em": now,
        },
        {
            "id": "CAR-01",
            "tipo": "carrier",
            "nome": "Transportadora X",
            "placa": "",
            "telefone": "(54) 3333-0000",
            "capacidade": 0,
            "status": "available",
            "ativo": True,
            "observacao": "Seed parceiro CARRIER",
            "criado_em": now,
            "atualizado_em": now,
        },
    ]
    data = {"seq": 3, "atualizado_em": now, "recursos": rows, "total": 3}
    _save(data)
    return data


def _enrich(row):
    out = dict(row)
    out["tipo_label"] = TIPOS.get(out.get("tipo"), out.get("tipo") or "")
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    return out


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("recursos") or []),
        "tipos": TIPOS,
        "status": STATUSES,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_recursos(q=None, tipo=None, status=None, ativos=None):
    rows = list(_load_raw().get("recursos") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("nome") or "").lower()
            or qq in str(r.get("placa") or "").lower()
        ]
    if tipo:
        t = str(tipo).strip().lower()
        if t not in TIPOS:
            raise ValueError("tipo inválido")
        rows = [r for r in rows if r.get("tipo") == t]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [r for r in rows if r.get("status") == st]
    if ativos is True:
        rows = [r for r in rows if r.get("ativo") is not False]
    return {
        "total": len(_load_raw().get("recursos") or []),
        "filtrado": len(rows),
        "tipos": TIPOS,
        "status_opcoes": STATUSES,
        "recursos": [_enrich(r) for r in rows],
    }


def get_recurso(rid):
    key = str(rid or "").strip().upper()
    for r in _load_raw().get("recursos") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def create_recurso(payload, usuario=""):
    body = dict(payload or {})
    data = _load_raw()
    rid = str(body.get("id") or "").strip().upper()
    if not rid:
        seq = int(data.get("seq") or 0) + 1
        data["seq"] = seq
        prefix = {"driver": "DRV", "vehicle": "VEH", "team": "TEM", "carrier": "CAR"}.get(
            str(body.get("tipo") or "driver").lower(), "RES"
        )
        rid = f"{prefix}-{seq:02d}"
    if any(str(r.get("id") or "").upper() == rid for r in data["recursos"]):
        raise ValueError(f"já existe recurso {rid}")
    tipo = str(body.get("tipo") or "driver").strip().lower()
    if tipo not in TIPOS:
        raise ValueError("tipo deve ser: driver, vehicle, team ou carrier")
    nome = str(body.get("nome") or "").strip()
    if not nome:
        raise ValueError("nome obrigatório")
    row = {
        "id": rid,
        "tipo": tipo,
        "nome": nome,
        "placa": str(body.get("placa") or "").strip().upper(),
        "telefone": str(body.get("telefone") or "").strip(),
        "capacidade": float(body.get("capacidade") or 0),
        "status": str(body.get("status") or "available").strip().lower(),
        "ativo": body.get("ativo") is not False,
        "observacao": str(body.get("observacao") or "").strip(),
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    if row["status"] not in STATUSES:
        raise ValueError("status inválido")
    data["recursos"].append(row)
    _save(data)
    return _enrich(row)


def set_status(rid, status, usuario=""):
    data = _load_raw()
    key = str(rid or "").strip().upper()
    st = str(status or "").strip().lower()
    if st not in STATUSES:
        raise ValueError("status inválido")
    for i, r in enumerate(data.get("recursos") or []):
        if str(r.get("id") or "").upper() == key:
            r["status"] = st
            r["atualizado_em"] = _now()
            data["recursos"][i] = r
            _save(data)
            return _enrich(r)
    raise ValueError("recurso não encontrado")
