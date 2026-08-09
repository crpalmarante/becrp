"""
Delivery — Tasks (RFC-18002 MVP).

Unidades operacionais geradas a partir do Delivery Order.
Fonte: dados/delivery_tasks.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import delivery_orders

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "delivery_tasks.json")

TIPOS = {
    "load": "Carregar",
    "travel": "Deslocar",
    "deliver_stop": "Entregar parada",
    "collect_pod": "Coletar comprovante",
    "return": "Retorno",
}

STATUSES = {
    "pending": "Pendente",
    "assigned": "Atribuída",
    "in_progress": "Em execução",
    "done": "Concluída",
    "failed": "Falhou",
    "cancelled": "Cancelada",
}

TRANSITIONS = {
    ("pending", "assign"): "assigned",
    ("pending", "cancel"): "cancelled",
    ("assigned", "start"): "in_progress",
    ("assigned", "cancel"): "cancelled",
    ("in_progress", "complete"): "done",
    ("in_progress", "fail"): "failed",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("tarefas"), list):
        return ensure_seed()
    if not data["tarefas"]:
        return ensure_seed()
    data.setdefault("seq", len(data["tarefas"]))
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("tarefas") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _hist(status, usuario="", nota=""):
    return {
        "status": status,
        "em": _now(),
        "usuario": str(usuario or "").strip(),
        "nota": str(nota or "").strip(),
    }


def _next_id(data):
    seq = int(data.get("seq") or 0) + 1
    data["seq"] = seq
    return f"DT-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def ensure_seed():
    delivery_orders.ensure_seed()
    now = _now()
    row = {
        "id": "DT-SEED-0001",
        "tipo": "deliver_stop",
        "entrega_id": "DO-SEED-0001",
        "parada": 1,
        "titulo": "Entregar parada 1 — Casa do cliente",
        "status": "pending",
        "operador": "",
        "recurso_id": "",
        "historico": [_hist("pending", "seed", "criação")],
        "observacao": "Seed",
        "criado_em": now,
        "atualizado_em": now,
    }
    data = {"seq": 1, "atualizado_em": now, "tarefas": [row], "total": 1}
    _save(data)
    return data


def _enrich(row):
    out = dict(row)
    out["tipo_label"] = TIPOS.get(out.get("tipo"), out.get("tipo") or "")
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    st = out.get("status")
    out["acoes"] = [a for (fr, a), _to in TRANSITIONS.items() if fr == st]
    return out


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("tarefas") or []),
        "tipos": TIPOS,
        "status": STATUSES,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_tarefas(q=None, status=None, entrega_id=None, operador=None):
    rows = list(_load_raw().get("tarefas") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("titulo") or "").lower()
            or qq in str(r.get("entrega_id") or "").lower()
        ]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [r for r in rows if r.get("status") == st]
    if entrega_id:
        ek = str(entrega_id).strip().upper()
        rows = [r for r in rows if str(r.get("entrega_id") or "").upper() == ek]
    if operador:
        op = str(operador).strip().lower()
        rows = [r for r in rows if op in str(r.get("operador") or "").lower()]
    order = {s: i for i, s in enumerate(STATUSES)}
    rows.sort(key=lambda r: (order.get(r.get("status"), 99), str(r.get("id") or "")))
    return {
        "total": len(_load_raw().get("tarefas") or []),
        "filtrado": len(rows),
        "tipos": TIPOS,
        "status_opcoes": STATUSES,
        "tarefas": [_enrich(r) for r in rows],
    }


def get_tarefa(tid):
    key = str(tid or "").strip().upper()
    for r in _load_raw().get("tarefas") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def generate_from_order(entrega_id, usuario=""):
    do = delivery_orders.get_order(entrega_id)
    if not do:
        raise ValueError("entrega não encontrada")
    if do.get("status") in ("cancelled", "completed"):
        raise ValueError("entrega fechada")

    data = _load_raw()
    # evita duplicar se já existem tarefas abertas
    existing = [
        t for t in data["tarefas"]
        if str(t.get("entrega_id") or "").upper() == do["id"]
        and t.get("status") not in ("cancelled",)
    ]
    if existing:
        return {
            "geradas": 0,
            "entrega_id": do["id"],
            "tarefas": [_enrich(t) for t in existing],
            "message": "já existem tarefas para esta entrega",
        }

    created = []
    # load
    tid = _next_id(data)
    load = {
        "id": tid,
        "tipo": "load",
        "entrega_id": do["id"],
        "parada": 0,
        "titulo": f"Carregar {do['id']} em {do.get('fonte') or 'origem'}",
        "status": "pending",
        "operador": do.get("motorista") or "",
        "recurso_id": do.get("recurso_id") or "",
        "historico": [_hist("pending", usuario, "gerada")],
        "observacao": "",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["tarefas"].append(load)
    created.append(load)

    for st in do.get("paradas") or []:
        tid = _next_id(data)
        t = {
            "id": tid,
            "tipo": "deliver_stop",
            "entrega_id": do["id"],
            "parada": int(st.get("parada") or 0),
            "titulo": f"Entregar parada {st.get('parada')} — {st.get('rotulo') or ''}",
            "status": "pending",
            "operador": do.get("motorista") or "",
            "recurso_id": do.get("recurso_id") or "",
            "historico": [_hist("pending", usuario, "gerada")],
            "observacao": st.get("endereco") or "",
            "criado_em": _now(),
            "atualizado_em": _now(),
        }
        data["tarefas"].append(t)
        created.append(t)

        tid = _next_id(data)
        pod = {
            "id": tid,
            "tipo": "collect_pod",
            "entrega_id": do["id"],
            "parada": int(st.get("parada") or 0),
            "titulo": f"Comprovante parada {st.get('parada')}",
            "status": "pending",
            "operador": do.get("motorista") or "",
            "recurso_id": do.get("recurso_id") or "",
            "historico": [_hist("pending", usuario, "gerada")],
            "observacao": "",
            "criado_em": _now(),
            "atualizado_em": _now(),
        }
        data["tarefas"].append(pod)
        created.append(pod)

    _save(data)
    return {
        "geradas": len(created),
        "entrega_id": do["id"],
        "tarefas": [_enrich(t) for t in created],
    }


def transition(tid, action, usuario="", motivo="", operador=""):
    data = _load_raw()
    key = str(tid or "").strip().upper()
    idx = None
    row = None
    for i, r in enumerate(data.get("tarefas") or []):
        if str(r.get("id") or "").upper() == key:
            idx, row = i, r
            break
    if row is None:
        raise ValueError("tarefa não encontrada")

    act = str(action or "").strip().lower()
    cur = row.get("status") or "pending"
    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório")
        nota = reason
    elif act == "assign":
        op = str(operador or motivo or "").strip()
        if not op:
            raise ValueError("operador obrigatório")
        row["operador"] = op
        nota = op
    elif act == "fail":
        nota = str(motivo or "falha").strip()
    else:
        nota = act

    row["status"] = nxt
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(nxt, usuario, nota))
    row["historico"] = hist
    data["tarefas"][idx] = row
    _save(data)
    return _enrich(row)
