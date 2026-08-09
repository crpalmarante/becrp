"""
Delivery — Scheduling (RFC-18005 MVP).

Slots de entrega (data + janela + capacidade por origem).
Reserva capacidade; atualiza promise na Delivery Order.
Não move estoque. Não cria venda.
Fonte: dados/delivery_scheduling.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import delivery_orders

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "delivery_scheduling.json")

PERIODS = {
    "manha": {"label": "Manhã", "inicio": "08:00", "fim": "12:00"},
    "tarde": {"label": "Tarde", "inicio": "13:00", "fim": "18:00"},
    "noite": {"label": "Noite", "inicio": "18:00", "fim": "21:00"},
    "dia": {"label": "Dia inteiro", "inicio": "08:00", "fim": "18:00"},
}

SLOT_STATUSES = {
    "open": "Aberto",
    "full": "Lotado",
    "closed": "Fechado",
    "cancelled": "Cancelado",
}

BOOKING_STATUSES = {
    "requested": "Solicitado",
    "scheduled": "Agendado",
    "confirmed": "Confirmado",
    "rescheduled": "Reagendado",
    "cancelled": "Cancelado",
}

DEFAULT_CAPACITY = 10


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("slots"), list):
        return ensure_seed()
    if not data["slots"]:
        return ensure_seed()
    data.setdefault("seq", len(data["slots"]))
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("slots") or [])
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
    return f"SL-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def _period_meta(periodo):
    key = str(periodo or "tarde").strip().lower()
    if key not in PERIODS:
        raise ValueError(f"período inválido: {periodo}")
    return key, PERIODS[key]


def _count_active(reservas):
    return sum(
        1
        for r in (reservas or [])
        if r.get("status") in ("requested", "scheduled", "confirmed", "rescheduled")
    )


def _sync_capacity(row):
    booked = _count_active(row.get("reservas"))
    cap = int(row.get("capacidade") or 0)
    row["booked"] = booked
    row["disponivel"] = max(0, cap - booked)
    if row.get("status") not in ("closed", "cancelled"):
        row["status"] = "full" if booked >= cap else "open"
    return row


def ensure_seed():
    delivery_orders.ensure_seed()
    now = _now()
    today = _today()
    row = {
        "id": "SL-SEED-0001",
        "data": today,
        "periodo": "tarde",
        "inicio": "13:00",
        "fim": "18:00",
        "fonte": "DC-01",
        "tipo": "scheduled",
        "capacidade": DEFAULT_CAPACITY,
        "booked": 1,
        "disponivel": DEFAULT_CAPACITY - 1,
        "status": "open",
        "observacao": "Seed — tarde de hoje",
        "reservas": [{
            "entrega_id": "DO-SEED-0001",
            "parceiro": "Cliente Demo",
            "status": "confirmed",
            "motivo": "seed",
            "historico": [_hist("confirmed", "seed", "seed")],
            "criado_em": now,
            "atualizado_em": now,
        }],
        "historico": [_hist("open", "seed", "criação")],
        "criado_em": now,
        "atualizado_em": now,
    }
    data = {"seq": 1, "atualizado_em": now, "slots": [row], "total": 1}
    _save(data)
    # alinha promise no seed DO se existir
    try:
        _patch_order("DO-SEED-0001", {
            "data_agendada": today,
            "janela": "tarde",
            "slot_id": "SL-SEED-0001",
            "scheduling_status": "confirmed",
        }, usuario="seed")
    except Exception:
        pass
    return data


def _enrich(row):
    out = dict(row)
    _sync_capacity(out)
    per = PERIODS.get(out.get("periodo") or "", {})
    out["periodo_label"] = per.get("label") or out.get("periodo") or ""
    out["status_label"] = SLOT_STATUSES.get(out.get("status"), out.get("status") or "")
    out["promise"] = (
        f"{out.get('data') or ''} · {out.get('inicio') or ''}-{out.get('fim') or ''}"
    ).strip(" ·")
    reservas = []
    for r in out.get("reservas") or []:
        rr = dict(r)
        rr["status_label"] = BOOKING_STATUSES.get(rr.get("status"), rr.get("status") or "")
        reservas.append(rr)
    out["reservas"] = reservas
    out["reservas_ativas"] = _count_active(reservas)
    out["acoes"] = _actions(out)
    return out


def _actions(row):
    st = row.get("status")
    acts = []
    if st == "open":
        acts.extend(["reserve", "close"])
    elif st == "full":
        acts.append("close")
    if st in ("open", "full"):
        acts.append("cancel")
    return acts


def meta():
    return {
        "periodos": [
            {"id": k, "label": v["label"], "inicio": v["inicio"], "fim": v["fim"]}
            for k, v in PERIODS.items()
        ],
        "slot_statuses": [{"id": k, "label": v} for k, v in SLOT_STATUSES.items()],
        "booking_statuses": [{"id": k, "label": v} for k, v in BOOKING_STATUSES.items()],
        "default_capacity": DEFAULT_CAPACITY,
    }


def list_slots(q=None, status=None, fonte=None, data=None, data_de=None, data_ate=None):
    data_raw = _load_raw()
    rows = [_enrich(r) for r in data_raw.get("slots") or []]
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in (r.get("id") or "").lower()
            or qq in (r.get("fonte") or "").lower()
            or qq in (r.get("periodo") or "").lower()
            or any(qq in (x.get("entrega_id") or "").lower() for x in r.get("reservas") or [])
        ]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if fonte:
        rows = [r for r in rows if (r.get("fonte") or "").upper() == str(fonte).strip().upper()]
    if data:
        rows = [r for r in rows if r.get("data") == data]
    if data_de:
        rows = [r for r in rows if (r.get("data") or "") >= data_de]
    if data_ate:
        rows = [r for r in rows if (r.get("data") or "") <= data_ate]
    rows.sort(key=lambda r: (r.get("data") or "", r.get("inicio") or "", r.get("id") or ""))
    return {
        "slots": rows,
        "total": len(data_raw.get("slots") or []),
        "filtrado": len(rows),
        "atualizado_em": data_raw.get("atualizado_em"),
    }


def get_slot(sid):
    key = str(sid or "").strip().upper()
    for r in _load_raw().get("slots") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def availability(fonte=None, data_de=None, data_ate=None):
    """Slots com capacidade livre no intervalo."""
    out = list_slots(
        status=None,
        fonte=fonte,
        data_de=data_de or _today(),
        data_ate=data_ate,
    )
    open_slots = [
        r for r in out["slots"]
        if r.get("status") == "open" and int(r.get("disponivel") or 0) > 0
    ]
    return {
        "slots": open_slots,
        "total": len(open_slots),
        "fonte": fonte or "",
        "data_de": data_de or _today(),
        "data_ate": data_ate or "",
        "atualizado_em": out.get("atualizado_em"),
    }


def _find(data, sid):
    key = str(sid or "").strip().upper()
    for i, r in enumerate(data.get("slots") or []):
        if str(r.get("id") or "").upper() == key:
            return i, r
    return None, None


def create_slot(body, usuario=""):
    body = body or {}
    data_str = str(body.get("data") or "").strip() or _today()
    periodo, meta_p = _period_meta(body.get("periodo") or "tarde")
    fonte = str(body.get("fonte") or "DC-01").strip().upper() or "DC-01"
    try:
        cap = int(body.get("capacidade") if body.get("capacidade") is not None else DEFAULT_CAPACITY)
    except (TypeError, ValueError):
        raise ValueError("capacidade inválida")
    if cap < 1:
        raise ValueError("capacidade deve ser >= 1")

    tipo = str(body.get("tipo") or "scheduled").strip().lower()
    if tipo not in ("same_day", "scheduled", "window"):
        tipo = "scheduled"

    raw = _load_raw()
    # evita duplicata data+periodo+fonte
    for r in raw.get("slots") or []:
        if (
            r.get("data") == data_str
            and r.get("periodo") == periodo
            and (r.get("fonte") or "").upper() == fonte
            and r.get("status") not in ("cancelled",)
        ):
            raise ValueError(f"já existe slot {r.get('id')} para {data_str}/{periodo}/{fonte}")

    now = _now()
    row = {
        "id": _next_id(raw),
        "data": data_str,
        "periodo": periodo,
        "inicio": str(body.get("inicio") or meta_p["inicio"]),
        "fim": str(body.get("fim") or meta_p["fim"]),
        "fonte": fonte,
        "tipo": tipo,
        "capacidade": cap,
        "booked": 0,
        "disponivel": cap,
        "status": "open",
        "observacao": str(body.get("observacao") or "").strip(),
        "reservas": [],
        "historico": [_hist("open", usuario, "criação")],
        "criado_em": now,
        "atualizado_em": now,
    }
    raw.setdefault("slots", []).append(row)
    _save(raw)
    return _enrich(row)


def generate_week(body=None, usuario=""):
    """Gera slots manhã+tarde para N dias a partir de data (default hoje, 7 dias)."""
    body = body or {}
    fonte = str(body.get("fonte") or "DC-01").strip().upper() or "DC-01"
    try:
        days = int(body.get("dias") if body.get("dias") is not None else 7)
    except (TypeError, ValueError):
        days = 7
    days = max(1, min(days, 31))
    try:
        cap = int(body.get("capacidade") if body.get("capacidade") is not None else DEFAULT_CAPACITY)
    except (TypeError, ValueError):
        cap = DEFAULT_CAPACITY
    start = str(body.get("data") or "").strip() or _today()
    try:
        base = datetime.strptime(start, "%Y-%m-%d")
    except ValueError:
        raise ValueError("data inválida (YYYY-MM-DD)")

    periodos = body.get("periodos") or ["manha", "tarde"]
    if not isinstance(periodos, list):
        periodos = ["manha", "tarde"]

    created = []
    skipped = []
    for i in range(days):
        d = (base + timedelta(days=i)).strftime("%Y-%m-%d")
        for p in periodos:
            try:
                created.append(create_slot({
                    "data": d,
                    "periodo": p,
                    "fonte": fonte,
                    "capacidade": cap,
                    "tipo": "scheduled",
                }, usuario=usuario))
            except ValueError as e:
                skipped.append({"data": d, "periodo": p, "motivo": str(e)})
    return {
        "criados": len(created),
        "pulados": len(skipped),
        "slots": created,
        "skipped": skipped,
        "fonte": fonte,
    }


def _patch_order(entrega_id, fields, usuario=""):
    """Atualiza campos de agenda na DO sem mudar status operacional."""
    data = delivery_orders._load_raw()
    idx, row = delivery_orders._find(data, entrega_id)
    if row is None:
        return None
    for k, v in (fields or {}).items():
        row[k] = v
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    nota = f"agenda {fields.get('data_agendada') or ''} {fields.get('janela') or ''} ({fields.get('scheduling_status') or ''})"
    hist.append(delivery_orders._hist(row.get("status") or "draft", usuario, nota.strip()))
    row["historico"] = hist
    data["orders"][idx] = row
    delivery_orders._save(data)
    return delivery_orders._enrich(row)


def _active_booking_for_order(entrega_id):
    key = str(entrega_id or "").strip().upper()
    for slot in _load_raw().get("slots") or []:
        for r in slot.get("reservas") or []:
            if (
                str(r.get("entrega_id") or "").upper() == key
                and r.get("status") in ("requested", "scheduled", "confirmed", "rescheduled")
            ):
                return slot, r
    return None, None


def reserve(slot_id, entrega_id, usuario="", status="scheduled", motivo=""):
    """Reserva capacidade no slot e grava promise na DO."""
    eid = str(entrega_id or "").strip().upper()
    if not eid:
        raise ValueError("entrega_id obrigatório")
    order = delivery_orders.get_order(eid)
    if not order:
        raise ValueError("entrega não encontrada")
    if order.get("status") in ("completed", "cancelled"):
        raise ValueError("entrega fechada")

    existing_slot, existing_book = _active_booking_for_order(eid)
    if existing_slot and str(existing_slot.get("id")).upper() != str(slot_id).strip().upper():
        raise ValueError(
            f"entrega já agendada em {existing_slot.get('id')} — use reagendar"
        )

    raw = _load_raw()
    idx, row = _find(raw, slot_id)
    if row is None:
        raise ValueError("slot não encontrado")
    if row.get("status") in ("closed", "cancelled"):
        raise ValueError("slot fechado")

    _sync_capacity(row)
    # se já reservado neste slot, só atualiza status
    for r in row.get("reservas") or []:
        if str(r.get("entrega_id") or "").upper() == eid and r.get("status") != "cancelled":
            r["status"] = status if status in BOOKING_STATUSES else "scheduled"
            r["atualizado_em"] = _now()
            r.setdefault("historico", []).append(_hist(r["status"], usuario, motivo or "atualização"))
            _sync_capacity(row)
            row["atualizado_em"] = _now()
            raw["slots"][idx] = row
            _save(raw)
            _patch_order(eid, {
                "data_agendada": row["data"],
                "janela": row["periodo"],
                "slot_id": row["id"],
                "scheduling_status": r["status"],
            }, usuario=usuario)
            return _enrich(row)

    if int(row.get("disponivel") or 0) < 1:
        raise ValueError("slot sem capacidade disponível")

    book_st = status if status in BOOKING_STATUSES else "scheduled"
    now = _now()
    booking = {
        "entrega_id": eid,
        "parceiro": order.get("parceiro") or "",
        "status": book_st,
        "motivo": str(motivo or "").strip(),
        "historico": [_hist(book_st, usuario, motivo or "reserva")],
        "criado_em": now,
        "atualizado_em": now,
    }
    reservas = list(row.get("reservas") or [])
    reservas.append(booking)
    row["reservas"] = reservas
    _sync_capacity(row)
    row["atualizado_em"] = now
    hist = list(row.get("historico") or [])
    hist.append(_hist(row["status"], usuario, f"reserva {eid}"))
    row["historico"] = hist
    raw["slots"][idx] = row
    _save(raw)

    _patch_order(eid, {
        "data_agendada": row["data"],
        "janela": row["periodo"],
        "slot_id": row["id"],
        "scheduling_status": book_st,
    }, usuario=usuario)
    try:
        import delivery_tracking
        delivery_tracking.sync_scheduled(
            eid, usuario=usuario,
            mensagem=f"Promise {row['data']} {row['periodo']} ({row['id']})",
        )
    except Exception:
        pass
    return _enrich(row)


def confirm_booking(slot_id, entrega_id, usuario=""):
    return reserve(slot_id, entrega_id, usuario=usuario, status="confirmed", motivo="confirmado")


def cancel_booking(slot_id, entrega_id, usuario="", motivo=""):
    reason = str(motivo or "").strip()
    if not reason:
        raise ValueError("motivo obrigatório para cancelar reserva")
    eid = str(entrega_id or "").strip().upper()
    raw = _load_raw()
    idx, row = _find(raw, slot_id)
    if row is None:
        raise ValueError("slot não encontrado")
    found = None
    for r in row.get("reservas") or []:
        if str(r.get("entrega_id") or "").upper() == eid and r.get("status") != "cancelled":
            found = r
            break
    if not found:
        raise ValueError("reserva não encontrada")
    found["status"] = "cancelled"
    found["motivo"] = reason
    found["atualizado_em"] = _now()
    found.setdefault("historico", []).append(_hist("cancelled", usuario, reason))
    _sync_capacity(row)
    row["atualizado_em"] = _now()
    row.setdefault("historico", []).append(_hist(row["status"], usuario, f"libera {eid}: {reason}"))
    raw["slots"][idx] = row
    _save(raw)
    _patch_order(eid, {
        "slot_id": "",
        "scheduling_status": "cancelled",
    }, usuario=usuario)
    return _enrich(row)


def reschedule(entrega_id, novo_slot_id, usuario="", motivo=""):
    """Move reserva ativa para outro slot (libera capacidade no anterior)."""
    reason = str(motivo or "reagendamento").strip()
    eid = str(entrega_id or "").strip().upper()
    old_slot, old_book = _active_booking_for_order(eid)
    if not old_slot:
        # sem reserva prévia: só reserva no novo
        return reserve(novo_slot_id, eid, usuario=usuario, status="rescheduled", motivo=reason)

    if str(old_slot.get("id")).upper() == str(novo_slot_id).strip().upper():
        return confirm_booking(novo_slot_id, eid, usuario=usuario)

    cancel_booking(old_slot["id"], eid, usuario=usuario, motivo=reason)
    return reserve(novo_slot_id, eid, usuario=usuario, status="rescheduled", motivo=reason)


def close_slot(slot_id, usuario="", motivo=""):
    raw = _load_raw()
    idx, row = _find(raw, slot_id)
    if row is None:
        raise ValueError("slot não encontrado")
    if row.get("status") in ("closed", "cancelled"):
        raise ValueError("slot já fechado")
    row["status"] = "closed"
    row["atualizado_em"] = _now()
    row.setdefault("historico", []).append(
        _hist("closed", usuario, str(motivo or "fechado").strip())
    )
    raw["slots"][idx] = row
    _save(raw)
    return _enrich(row)


def cancel_slot(slot_id, usuario="", motivo=""):
    reason = str(motivo or "").strip()
    if not reason:
        raise ValueError("motivo obrigatório")
    raw = _load_raw()
    idx, row = _find(raw, slot_id)
    if row is None:
        raise ValueError("slot não encontrado")
    # cancela reservas ativas
    for r in row.get("reservas") or []:
        if r.get("status") in ("requested", "scheduled", "confirmed", "rescheduled"):
            r["status"] = "cancelled"
            r["motivo"] = reason
            r["atualizado_em"] = _now()
            r.setdefault("historico", []).append(_hist("cancelled", usuario, reason))
            _patch_order(r.get("entrega_id"), {
                "slot_id": "",
                "scheduling_status": "cancelled",
            }, usuario=usuario)
    row["status"] = "cancelled"
    _sync_capacity(row)
    row["atualizado_em"] = _now()
    row.setdefault("historico", []).append(_hist("cancelled", usuario, reason))
    raw["slots"][idx] = row
    _save(raw)
    return _enrich(row)
