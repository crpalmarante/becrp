"""
Delivery — Tracking (RFC-18006 MVP).

Visibilidade da execução: status + eventos + timeline (+ localização opcional).
Não cria entregas, não despacha, não calcula rota, não move estoque.
Fonte: dados/delivery_tracking.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import delivery_orders

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "delivery_tracking.json")

# lifecycle de tracking (visão operacional / cliente)
TRACK_STATUSES = {
    "created": "Criada",
    "scheduled": "Agendada",
    "prepared": "Preparada",
    "assigned": "Atribuída",
    "departed": "Saiu para entrega",
    "in_transit": "Em trânsito",
    "arrived": "No destino",
    "delivered": "Entregue",
    "confirmed": "Confirmada",
    "failed": "Falhou",
    "cancelled": "Cancelada",
}

EVENT_TYPES = {
    "created": "Entrega criada",
    "scheduled": "Agendada",
    "prepared": "Preparada",
    "assigned": "Recurso atribuído",
    "departed": "Motorista saiu",
    "in_transit": "Em trânsito",
    "arrived": "Chegou no destino",
    "delivered": "Entregue",
    "confirmed": "Confirmada / concluída",
    "failed": "Falha na entrega",
    "cancelled": "Cancelada",
    "location": "Atualização de localização",
    "note": "Observação",
    "stop_update": "Atualização de parada",
}

# DO status → tracking status
_ORDER_TO_TRACK = {
    "draft": "created",
    "confirmed": "created",
    "waiting_stock": "prepared",
    "ready": "prepared",
    "assigned": "assigned",
    "in_transit": "in_transit",
    "delivered": "delivered",
    "completed": "confirmed",
    "cancelled": "cancelled",
}

# ação da DO → tipo de evento
_ACTION_TO_EVENT = {
    "confirm": "created",
    "wait_stock": "prepared",
    "ready": "prepared",
    "assign": "assigned",
    "depart": "departed",
    "deliver": "delivered",
    "complete": "confirmed",
    "cancel": "cancelled",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("tracks"), list):
        return ensure_seed()
    if not data["tracks"]:
        return ensure_seed()
    data.setdefault("seq", len(data["tracks"]))
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("tracks") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_event_id(track):
    seq = int(track.get("event_seq") or 0) + 1
    track["event_seq"] = seq
    return f"EV-{seq:04d}"


def ensure_seed():
    delivery_orders.ensure_seed()
    now = _now()
    order = delivery_orders.get_order("DO-SEED-0001") or {}
    track = {
        "id": "TR-SEED-0001",
        "entrega_id": "DO-SEED-0001",
        "status": _ORDER_TO_TRACK.get(order.get("status") or "ready", "prepared"),
        "motorista": order.get("motorista") or "",
        "veiculo": order.get("veiculo") or "",
        "last_lat": None,
        "last_lng": None,
        "last_location_at": "",
        "event_seq": 3,
        "events": [
            {
                "id": "EV-0001",
                "tipo": "created",
                "em": now,
                "usuario": "seed",
                "mensagem": "Entrega seed criada",
                "parada": None,
                "lat": None,
                "lng": None,
                "visivel_cliente": True,
            },
            {
                "id": "EV-0002",
                "tipo": "prepared",
                "em": now,
                "usuario": "seed",
                "mensagem": "Pronta para despacho",
                "parada": None,
                "lat": None,
                "lng": None,
                "visivel_cliente": True,
            },
            {
                "id": "EV-0003",
                "tipo": "scheduled",
                "em": now,
                "usuario": "seed",
                "mensagem": f"Agenda {order.get('data_agendada') or ''} {order.get('janela') or ''}".strip(),
                "parada": None,
                "lat": None,
                "lng": None,
                "visivel_cliente": True,
            },
        ],
        "criado_em": now,
        "atualizado_em": now,
    }
    data = {"seq": 1, "atualizado_em": now, "tracks": [track], "total": 1}
    _save(data)
    return data


def meta():
    return {
        "statuses": [{"id": k, "label": v} for k, v in TRACK_STATUSES.items()],
        "event_types": [{"id": k, "label": v} for k, v in EVENT_TYPES.items()],
    }


def _enrich(track, order=None):
    out = dict(track)
    oid = out.get("entrega_id")
    if order is None and oid:
        order = delivery_orders.get_order(oid)
    out["status_label"] = TRACK_STATUSES.get(out.get("status"), out.get("status") or "")
    if order:
        out["parceiro"] = order.get("parceiro") or ""
        out["fonte"] = order.get("fonte") or ""
        out["order_status"] = order.get("status")
        out["order_status_label"] = order.get("status_label") or order.get("status")
        out["data_agendada"] = order.get("data_agendada") or ""
        out["janela"] = order.get("janela") or ""
        out["slot_id"] = order.get("slot_id") or ""
        out["origem_ref"] = order.get("origem_ref") or ""
        out["paradas"] = order.get("paradas") or []
        out["paradas_count"] = order.get("paradas_count") or len(out["paradas"])
        out["motorista"] = out.get("motorista") or order.get("motorista") or ""
        out["veiculo"] = out.get("veiculo") or order.get("veiculo") or ""
    events = []
    for ev in out.get("events") or []:
        e = dict(ev)
        e["tipo_label"] = EVENT_TYPES.get(e.get("tipo"), e.get("tipo") or "")
        events.append(e)
    events.sort(key=lambda x: x.get("em") or "")
    out["events"] = events
    out["events_count"] = len(events)
    out["last_event"] = events[-1] if events else None
    out["acoes"] = _actions(out)
    out["customer"] = _customer_view(out)
    return out


def _actions(track):
    st = track.get("status")
    acts = ["note", "location"]
    if st in ("assigned", "departed", "in_transit"):
        acts.append("arrived")
    if st in ("departed", "in_transit", "arrived", "assigned"):
        acts.append("failed")
    if st in ("created", "scheduled", "prepared") and track.get("order_status") == "ready":
        pass
    return acts


def _customer_view(track):
    """Resumo visível ao cliente (sem detalhes internos)."""
    public = [
        e for e in (track.get("events") or [])
        if e.get("visivel_cliente") and e.get("tipo") not in ("note",)
    ]
    return {
        "entrega_id": track.get("entrega_id"),
        "status": track.get("status"),
        "status_label": TRACK_STATUSES.get(track.get("status"), track.get("status") or ""),
        "parceiro": track.get("parceiro") or "",
        "agendada": f"{track.get('data_agendada') or ''} {track.get('janela') or ''}".strip(),
        "motorista": track.get("motorista") or "",
        "ultima_atualizacao": (track.get("atualizado_em") or ""),
        "timeline": [
            {
                "em": e.get("em"),
                "tipo": e.get("tipo"),
                "label": EVENT_TYPES.get(e.get("tipo"), e.get("tipo")),
                "mensagem": e.get("mensagem") or "",
            }
            for e in public
        ],
    }


def _find(data, entrega_id=None, track_id=None):
    if track_id:
        key = str(track_id or "").strip().upper()
        for i, r in enumerate(data.get("tracks") or []):
            if str(r.get("id") or "").upper() == key:
                return i, r
    if entrega_id:
        key = str(entrega_id or "").strip().upper()
        for i, r in enumerate(data.get("tracks") or []):
            if str(r.get("entrega_id") or "").upper() == key:
                return i, r
    return None, None


def _next_track_id(data):
    seq = int(data.get("seq") or 0) + 1
    data["seq"] = seq
    return f"TR-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def ensure_track(entrega_id, usuario=""):
    """Garante track para a DO; cria se não existir."""
    order = delivery_orders.get_order(entrega_id)
    if not order:
        raise ValueError("entrega não encontrada")
    raw = _load_raw()
    idx, row = _find(raw, entrega_id=order["id"])
    if row is not None:
        return _enrich(row, order)

    now = _now()
    st = _ORDER_TO_TRACK.get(order.get("status") or "draft", "created")
    row = {
        "id": _next_track_id(raw),
        "entrega_id": order["id"],
        "status": st,
        "motorista": order.get("motorista") or "",
        "veiculo": order.get("veiculo") or "",
        "last_lat": None,
        "last_lng": None,
        "last_location_at": "",
        "event_seq": 1,
        "events": [{
            "id": "EV-0001",
            "tipo": "created",
            "em": now,
            "usuario": str(usuario or "").strip(),
            "mensagem": f"Tracking iniciado ({order.get('status')})",
            "parada": None,
            "lat": None,
            "lng": None,
            "visivel_cliente": True,
        }],
        "criado_em": now,
        "atualizado_em": now,
    }
    raw.setdefault("tracks", []).append(row)
    _save(raw)
    return _enrich(row, order)


def list_tracks(q=None, status=None, fonte=None):
    raw = _load_raw()
    # enriquece / sincroniza leve com DO
    rows = []
    for r in raw.get("tracks") or []:
        order = delivery_orders.get_order(r.get("entrega_id"))
        rows.append(_enrich(r, order))
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in (r.get("id") or "").lower()
            or qq in (r.get("entrega_id") or "").lower()
            or qq in (r.get("parceiro") or "").lower()
            or qq in (r.get("motorista") or "").lower()
        ]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if fonte:
        rows = [r for r in rows if (r.get("fonte") or "").upper() == str(fonte).strip().upper()]
    rows.sort(key=lambda r: r.get("atualizado_em") or "", reverse=True)
    return {
        "tracks": rows,
        "total": len(raw.get("tracks") or []),
        "filtrado": len(rows),
        "atualizado_em": raw.get("atualizado_em"),
    }


def get_track(key):
    """key = TR-… ou DO-…"""
    raw = _load_raw()
    k = str(key or "").strip().upper()
    idx, row = _find(raw, track_id=k)
    if row is None:
        idx, row = _find(raw, entrega_id=k)
    if row is None:
        # auto-cria se for DO válida
        if k.startswith("DO-") and delivery_orders.get_order(k):
            return ensure_track(k)
        return None
    return _enrich(row, delivery_orders.get_order(row.get("entrega_id")))


def timeline(entrega_id):
    track = get_track(entrega_id)
    if not track:
        raise ValueError("tracking não encontrado")
    return {
        "entrega_id": track["entrega_id"],
        "status": track["status"],
        "status_label": track["status_label"],
        "events": track["events"],
        "paradas": track.get("paradas") or [],
        "customer": track.get("customer"),
    }


def customer_view(entrega_id):
    track = get_track(entrega_id)
    if not track:
        raise ValueError("tracking não encontrado")
    return track["customer"]


def _append_event(row, tipo, usuario="", mensagem="", parada=None, lat=None, lng=None,
                  visivel_cliente=True, status=None):
    tipo = str(tipo or "").strip().lower()
    if tipo not in EVENT_TYPES:
        raise ValueError(f"tipo de evento inválido: {tipo}")
    ev = {
        "id": _next_event_id(row),
        "tipo": tipo,
        "em": _now(),
        "usuario": str(usuario or "").strip(),
        "mensagem": str(mensagem or EVENT_TYPES.get(tipo) or tipo).strip(),
        "parada": parada,
        "lat": lat,
        "lng": lng,
        "visivel_cliente": bool(visivel_cliente),
    }
    events = list(row.get("events") or [])
    events.append(ev)
    row["events"] = events
    if status and status in TRACK_STATUSES:
        row["status"] = status
    elif tipo in TRACK_STATUSES and tipo not in ("location", "note", "stop_update"):
        # avança status se fizer sentido (não regride confirmed/delivered)
        cur = row.get("status") or "created"
        order = list(TRACK_STATUSES.keys())
        if tipo in order and cur in order:
            if order.index(tipo) >= order.index(cur) or cur in ("failed",):
                if cur not in ("confirmed", "cancelled") or tipo == cur:
                    if cur != "confirmed" or tipo == "confirmed":
                        if not (cur in ("delivered", "confirmed") and tipo in ("arrived", "in_transit", "departed")):
                            row["status"] = tipo
        elif tipo in TRACK_STATUSES:
            row["status"] = tipo
    if lat is not None and lng is not None:
        try:
            row["last_lat"] = float(lat)
            row["last_lng"] = float(lng)
            row["last_location_at"] = ev["em"]
        except (TypeError, ValueError):
            pass
    row["atualizado_em"] = _now()
    return ev


def add_event(entrega_id, tipo, usuario="", mensagem="", parada=None, lat=None, lng=None,
              visivel_cliente=True, status=None):
    order = delivery_orders.get_order(entrega_id)
    if not order:
        raise ValueError("entrega não encontrada")
    ensure_track(order["id"], usuario=usuario)
    raw = _load_raw()
    idx, row = _find(raw, entrega_id=order["id"])
    if row is None:
        raise ValueError("tracking não encontrado")

    # efeitos colaterais leves na DO (só paradas / não inventário)
    tipo_l = str(tipo or "").strip().lower()
    if tipo_l == "arrived" and parada is not None:
        try:
            delivery_orders.update_stop(
                order["id"], int(parada), {"status": "arrived"}, usuario=usuario,
            )
        except Exception:
            pass
    elif tipo_l == "arrived" and parada is None:
        # marca primeira parada pendente
        for st in order.get("paradas") or []:
            if st.get("status") in ("pending", "en_route"):
                try:
                    delivery_orders.update_stop(
                        order["id"], st.get("parada"), {"status": "arrived"}, usuario=usuario,
                    )
                    parada = st.get("parada")
                except Exception:
                    pass
                break

    if tipo_l == "failed":
        status = status or "failed"

    ev = _append_event(
        row, tipo_l, usuario=usuario, mensagem=mensagem, parada=parada,
        lat=lat, lng=lng, visivel_cliente=visivel_cliente, status=status,
    )
    if order.get("motorista"):
        row["motorista"] = order.get("motorista") or row.get("motorista")
    if order.get("veiculo"):
        row["veiculo"] = order.get("veiculo") or row.get("veiculo")
    raw["tracks"][idx] = row
    _save(raw)
    return _enrich(row, delivery_orders.get_order(order["id"]))


def sync_from_order(order, action="", usuario="", nota=""):
    """Chamado pelas transições da DO (best-effort)."""
    if not order or not order.get("id"):
        return None
    try:
        ensure_track(order["id"], usuario=usuario)
        raw = _load_raw()
        idx, row = _find(raw, entrega_id=order["id"])
        if row is None:
            return None
        act = str(action or "").strip().lower()
        tipo = _ACTION_TO_EVENT.get(act)
        track_st = _ORDER_TO_TRACK.get(order.get("status") or "", row.get("status"))
        if act == "depart":
            track_st = "departed"
        if tipo:
            # evita duplicar o mesmo tipo consecutivamente com mesma ação
            last = (row.get("events") or [])[-1] if row.get("events") else None
            msg = str(nota or EVENT_TYPES.get(tipo) or tipo)
            if not (last and last.get("tipo") == tipo and last.get("mensagem") == msg):
                _append_event(
                    row, tipo, usuario=usuario, mensagem=msg,
                    status=track_st if track_st in TRACK_STATUSES else None,
                )
        else:
            if track_st and track_st in TRACK_STATUSES:
                row["status"] = track_st
                row["atualizado_em"] = _now()
        row["motorista"] = order.get("motorista") or row.get("motorista") or ""
        row["veiculo"] = order.get("veiculo") or row.get("veiculo") or ""
        raw["tracks"][idx] = row
        _save(raw)
        return _enrich(row, order)
    except Exception:
        return None


def sync_scheduled(entrega_id, usuario="", mensagem=""):
    """Hook opcional do Scheduling (promise confirmada)."""
    try:
        return add_event(
            entrega_id, "scheduled", usuario=usuario,
            mensagem=mensagem or "Horário confirmado",
            status="scheduled",
        )
    except Exception:
        return None
