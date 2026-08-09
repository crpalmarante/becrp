"""
Delivery — Dispatch Management (RFC-18003 MVP).

Agrupa Delivery Orders em lote operacional e atribui recursos.
Não move estoque. Não cria vendas.
Fonte: dados/delivery_dispatch.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import delivery_orders
import delivery_resources
import delivery_tasks

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "delivery_dispatch.json")

STATUSES = {
    "open": "Aberto",
    "planning": "Planejando",
    "assigned": "Atribuído",
    "released": "Liberado",
    "in_progress": "Em execução",
    "completed": "Concluído",
    "closed": "Fechado",
    "cancelled": "Cancelado",
}

PRIORITIES = {
    "emergency": "Emergência",
    "high": "Alta",
    "normal": "Normal",
    "low": "Baixa",
}

TRANSITIONS = {
    ("open", "plan"): "planning",
    ("open", "cancel"): "cancelled",
    ("planning", "assign"): "assigned",
    ("planning", "cancel"): "cancelled",
    ("assigned", "release"): "released",
    ("assigned", "cancel"): "cancelled",
    ("released", "start"): "in_progress",
    ("in_progress", "complete"): "completed",
    ("completed", "close"): "closed",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("dispatches"), list):
        return ensure_seed()
    if not data["dispatches"]:
        return ensure_seed()
    data.setdefault("seq", len(data["dispatches"]))
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("dispatches") or [])
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
    return f"DS-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def ensure_seed():
    delivery_orders.ensure_seed()
    now = _now()
    row = {
        "id": "DS-SEED-0001",
        "data": datetime.now().strftime("%Y-%m-%d"),
        "fonte": "DC-01",
        "status": "open",
        "prioridade": "normal",
        "recurso_id": "DRV-01",
        "motorista": "Carlos Motorista",
        "veiculo": "ABC1D23",
        "entrega_ids": ["DO-SEED-0001"],
        "observacao": "Seed — lote do dia",
        "historico": [_hist("open", "seed", "criação")],
        "cancelamento_motivo": "",
        "criado_em": now,
        "atualizado_em": now,
    }
    data = {"seq": 1, "atualizado_em": now, "dispatches": [row], "total": 1}
    _save(data)
    return data


def _enrich(row):
    out = dict(row)
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    out["prioridade_label"] = PRIORITIES.get(out.get("prioridade"), out.get("prioridade") or "")
    ids = list(out.get("entrega_ids") or [])
    out["entregas_count"] = len(ids)
    entregas = []
    for eid in ids:
        do = delivery_orders.get_order(eid)
        if do:
            entregas.append({
                "id": do["id"],
                "parceiro": do.get("parceiro"),
                "status": do.get("status"),
                "status_label": do.get("status_label"),
                "paradas_count": do.get("paradas_count"),
            })
    out["entregas"] = entregas
    st = out.get("status")
    out["acoes"] = [a for (fr, a), _to in TRANSITIONS.items() if fr == st]
    return out


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("dispatches") or []),
        "status": STATUSES,
        "prioridades": PRIORITIES,
        "atualizado_em": data.get("atualizado_em"),
    }


def queue(fonte=None, status=None):
    """Fila de DOs prontos para despacho (ready/assigned)."""
    allowed = {"draft", "confirmed", "ready", "assigned"}
    out = delivery_orders.list_orders(status=None, fonte=fonte)
    rows = [
        r for r in (out.get("orders") or [])
        if r.get("status") in allowed
    ]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return {
        "filtrado": len(rows),
        "orders": rows,
    }


def list_dispatches(q=None, status=None, fonte=None, data=None):
    rows = list(_load_raw().get("dispatches") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("motorista") or "").lower()
            or any(qq in str(e).lower() for e in (r.get("entrega_ids") or []))
        ]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [r for r in rows if r.get("status") == st]
    if fonte:
        fk = str(fonte).strip().upper()
        rows = [r for r in rows if str(r.get("fonte") or "").upper() == fk]
    if data:
        rows = [r for r in rows if r.get("data") == str(data).strip()]
    order = {s: i for i, s in enumerate(STATUSES)}
    rows.sort(key=lambda r: (order.get(r.get("status"), 99), str(r.get("id") or "")))
    return {
        "total": len(_load_raw().get("dispatches") or []),
        "filtrado": len(rows),
        "status_opcoes": STATUSES,
        "prioridades": PRIORITIES,
        "dispatches": [_enrich(r) for r in rows],
    }


def get_dispatch(did):
    key = str(did or "").strip().upper()
    for r in _load_raw().get("dispatches") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def create_dispatch(payload, usuario=""):
    body = dict(payload or {})
    data = _load_raw()
    did = str(body.get("id") or "").strip().upper() or _next_id(data)
    if any(str(r.get("id") or "").upper() == did for r in data["dispatches"]):
        raise ValueError(f"já existe despacho {did}")

    ids = body.get("entrega_ids") or []
    if isinstance(ids, str):
        ids = [x.strip() for x in ids.split(",") if x.strip()]
    ids = [str(x).strip().upper() for x in ids]
    if not ids:
        raise ValueError("informe entrega_ids")

    for eid in ids:
        if not delivery_orders.get_order(eid):
            raise ValueError(f"entrega não encontrada: {eid}")

    prio = str(body.get("prioridade") or "normal").strip().lower()
    if prio not in PRIORITIES:
        raise ValueError("prioridade inválida")

    recurso_id = str(body.get("recurso_id") or "").strip().upper()
    motorista = str(body.get("motorista") or "").strip()
    veiculo = str(body.get("veiculo") or "").strip()
    if recurso_id:
        rec = delivery_resources.get_recurso(recurso_id)
        if not rec:
            raise ValueError(f"recurso não encontrado: {recurso_id}")
        if not motorista and rec.get("tipo") == "driver":
            motorista = rec.get("nome") or ""

    row = {
        "id": did,
        "data": str(body.get("data") or datetime.now().strftime("%Y-%m-%d")),
        "fonte": str(body.get("fonte") or "DC-01").strip().upper(),
        "status": "open",
        "prioridade": prio,
        "recurso_id": recurso_id,
        "motorista": motorista,
        "veiculo": veiculo,
        "entrega_ids": ids,
        "observacao": str(body.get("observacao") or "").strip(),
        "historico": [_hist("open", usuario, "criação")],
        "cancelamento_motivo": "",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["dispatches"].append(row)
    _save(data)
    return _enrich(row)


def _find(data, did):
    key = str(did or "").strip().upper()
    for i, r in enumerate(data.get("dispatches") or []):
        if str(r.get("id") or "").upper() == key:
            return i, r
    return None, None


def add_entregas(did, entrega_ids, usuario=""):
    data = _load_raw()
    idx, row = _find(data, did)
    if row is None:
        raise ValueError("despacho não encontrado")
    if row.get("status") not in ("open", "planning"):
        raise ValueError("só é possível incluir entregas em open/planning")

    ids = entrega_ids or []
    if isinstance(ids, str):
        ids = [x.strip() for x in ids.split(",") if x.strip()]
    cur = list(row.get("entrega_ids") or [])
    for eid in ids:
        eid = str(eid).strip().upper()
        if not delivery_orders.get_order(eid):
            raise ValueError(f"entrega não encontrada: {eid}")
        if eid not in cur:
            cur.append(eid)
    row["entrega_ids"] = cur
    row["atualizado_em"] = _now()
    data["dispatches"][idx] = row
    _save(data)
    return _enrich(row)


def transition(did, action, usuario="", motivo="", **extra):
    data = _load_raw()
    idx, row = _find(data, did)
    if row is None:
        raise ValueError("despacho não encontrado")

    act = str(action or "").strip().lower()
    cur = row.get("status") or "open"
    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório")
        row["cancelamento_motivo"] = reason
        nota = reason
    elif act == "assign":
        if extra.get("recurso_id") is not None:
            row["recurso_id"] = str(extra.get("recurso_id") or "").strip().upper()
        if extra.get("motorista") is not None:
            row["motorista"] = str(extra.get("motorista") or "").strip()
        if extra.get("veiculo") is not None:
            row["veiculo"] = str(extra.get("veiculo") or "").strip()
        if not (row.get("motorista") or row.get("recurso_id")):
            raise ValueError("informe motorista ou recurso")
        # propaga para DOs ready → assigned
        for eid in row.get("entrega_ids") or []:
            do = delivery_orders.get_order(eid)
            if not do:
                continue
            if do.get("status") == "ready":
                try:
                    delivery_orders.transition(
                        eid,
                        "assign",
                        usuario=usuario,
                        motorista=row.get("motorista"),
                        veiculo=row.get("veiculo"),
                        recurso_id=row.get("recurso_id"),
                    )
                except ValueError:
                    pass
            elif do.get("status") in ("draft", "confirmed"):
                try:
                    if do.get("status") == "draft":
                        delivery_orders.transition(eid, "confirm", usuario=usuario)
                        do = delivery_orders.get_order(eid)
                    if do and do.get("status") == "confirmed":
                        delivery_orders.transition(eid, "ready", usuario=usuario)
                    do = delivery_orders.get_order(eid)
                    if do and do.get("status") == "ready":
                        delivery_orders.transition(
                            eid,
                            "assign",
                            usuario=usuario,
                            motorista=row.get("motorista"),
                            veiculo=row.get("veiculo"),
                            recurso_id=row.get("recurso_id"),
                        )
                except ValueError:
                    pass
        if row.get("recurso_id"):
            try:
                delivery_resources.set_status(row["recurso_id"], "busy", usuario=usuario)
            except ValueError:
                pass
        nota = f"atribuído {row.get('motorista') or row.get('recurso_id')}"
    elif act == "release":
        # gera tarefas das entregas
        for eid in row.get("entrega_ids") or []:
            try:
                delivery_tasks.generate_from_order(eid, usuario=usuario)
            except ValueError:
                pass
        nota = "liberado"
    elif act == "start":
        for eid in row.get("entrega_ids") or []:
            do = delivery_orders.get_order(eid)
            if do and do.get("status") == "assigned":
                try:
                    delivery_orders.transition(eid, "depart", usuario=usuario)
                except ValueError:
                    pass
        nota = "em rota"
    elif act == "complete":
        for eid in row.get("entrega_ids") or []:
            do = delivery_orders.get_order(eid)
            if not do:
                continue
            try:
                if do.get("status") == "in_transit":
                    delivery_orders.transition(eid, "deliver", usuario=usuario)
                    do = delivery_orders.get_order(eid)
                if do and do.get("status") == "delivered":
                    delivery_orders.transition(eid, "complete", usuario=usuario)
            except ValueError:
                pass
        if row.get("recurso_id"):
            try:
                delivery_resources.set_status(row["recurso_id"], "available", usuario=usuario)
            except ValueError:
                pass
        nota = "concluído"
    else:
        nota = str(motivo or act).strip()

    row["status"] = nxt
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(nxt, usuario, nota))
    row["historico"] = hist
    data["dispatches"][idx] = row
    _save(data)
    return _enrich(row)
