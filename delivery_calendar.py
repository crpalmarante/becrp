"""
Delivery — Calendar / Field (RFC-18104 MVP).

Visualização temporal de entregas + capacidade de slots.
Visão field = sequência do dia por motorista.
Não possui dados próprios. Não move estoque.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

import delivery_orders
import delivery_scheduling

VIEWS = {
    "day": "Dia",
    "week": "Semana",
    "month": "Mês",
    "field": "Campo",
}

# cores semânticas (UI pode mapear)
STATUS_COLOR = {
    "draft": "gray",
    "confirmed": "green",
    "waiting_stock": "orange",
    "ready": "green",
    "assigned": "blue",
    "in_transit": "orange",
    "delivered": "gray",
    "completed": "gray",
    "cancelled": "darkred",
    "delayed": "red",
    "failed": "darkred",
}

PERIOD_ORDER = ["manha", "tarde", "noite", "dia", ""]


def _now():
    return datetime.now()


def _today():
    return _now().strftime("%Y-%m-%d")


def _date_only(val):
    s = str(val or "").strip()
    return s[:10] if s else ""


def _parse_day(data):
    d = _date_only(data) or _today()
    try:
        return datetime.strptime(d, "%Y-%m-%d"), d
    except ValueError:
        t = _today()
        return datetime.strptime(t, "%Y-%m-%d"), t


def meta():
    return {
        "views": [{"id": k, "label": v} for k, v in VIEWS.items()],
        "cores": STATUS_COLOR,
        "refresh_seconds": 45,
        "nota": "Projeção de Scheduling + Orders — calendário não armazena eventos.",
    }


def _is_delayed(o, today):
    if o.get("status") in ("delivered", "completed", "cancelled"):
        return False
    d = _date_only(o.get("data_agendada"))
    return bool(d and d < today)


def _region(o):
    for st in o.get("paradas") or []:
        if st.get("cidade"):
            return str(st.get("cidade")).strip()
    return o.get("fonte") or ""


def _event(o, today):
    delayed = _is_delayed(o, today)
    st = "delayed" if delayed else (o.get("status") or "draft")
    periodo = (o.get("janela") or "").strip().lower()
    meta_p = delivery_scheduling.PERIODS.get(periodo) or {}
    return {
        "id": o.get("id"),
        "entrega_id": o.get("id"),
        "parceiro": o.get("parceiro"),
        "data": _date_only(o.get("data_agendada")) or today,
        "janela": periodo,
        "janela_label": meta_p.get("label") or periodo or "—",
        "inicio": meta_p.get("inicio") or "",
        "fim": meta_p.get("fim") or "",
        "motorista": o.get("motorista") or "",
        "veiculo": o.get("veiculo") or "",
        "regiao": _region(o),
        "status": o.get("status"),
        "status_label": o.get("status_label"),
        "prioridade": o.get("prioridade") or "normal",
        "prioridade_label": o.get("prioridade_label") or "Normal",
        "slot_id": o.get("slot_id") or "",
        "cor": STATUS_COLOR.get(st, "green"),
        "atrasada": delayed,
        "fonte": o.get("fonte") or "",
    }


def _slots_for_range(fonte, data_de, data_ate):
    return delivery_scheduling.list_slots(
        fonte=fonte, data_de=data_de, data_ate=data_ate,
    ).get("slots") or []


def _window_blocks(day, events, slots):
    """Blocos de capacidade do dia."""
    by_periodo = defaultdict(list)
    for e in events:
        if e.get("data") != day:
            continue
        by_periodo[(e.get("janela") or "").strip().lower()].append(e)

    slot_by_p = {}
    for s in slots:
        if s.get("data") == day:
            slot_by_p[s.get("periodo")] = s

    keys = []
    for k in PERIOD_ORDER:
        if k in by_periodo or k in slot_by_p:
            keys.append(k)
    for k in sorted(set(list(by_periodo) + list(slot_by_p))):
        if k not in keys:
            keys.append(k)

    blocks = []
    for k in keys:
        sl = slot_by_p.get(k)
        evs = by_periodo.get(k, [])
        cap = int((sl or {}).get("capacidade") or 0)
        booked = int((sl or {}).get("booked") or len(evs))
        if not cap and evs:
            cap = max(len(evs), 10)
        disponivel = max(0, cap - booked) if cap else None
        util = round(100.0 * booked / cap, 1) if cap else None
        meta_p = delivery_scheduling.PERIODS.get(k) or {}
        blocks.append({
            "periodo": k or "sem_janela",
            "periodo_label": meta_p.get("label") or (k or "Sem janela"),
            "inicio": (sl or {}).get("inicio") or meta_p.get("inicio") or "",
            "fim": (sl or {}).get("fim") or meta_p.get("fim") or "",
            "slot_id": (sl or {}).get("id") or "",
            "capacidade": cap,
            "agendadas": len(evs),
            "reservados": booked,
            "disponivel": disponivel,
            "utilizacao_pct": util,
            "lotado": (sl or {}).get("status") == "full" or (cap and booked >= cap),
            "status": (sl or {}).get("status") or "",
            "eventos": sorted(evs, key=lambda x: (x.get("inicio") or "", x.get("id") or "")),
        })
    return blocks


def _conflicts(events, blocks):
    warns = []
    for b in blocks:
        if b.get("lotado"):
            warns.append({
                "tipo": "capacidade",
                "nivel": "warn",
                "texto": f"Janela lotada · {b.get('periodo_label')} ({b.get('reservados')}/{b.get('capacidade')})",
                "periodo": b.get("periodo"),
            })
    # driver double-book same window
    by_drv = defaultdict(list)
    for e in events:
        if e.get("motorista") and e.get("status") not in ("completed", "cancelled", "delivered"):
            key = (e.get("data"), e.get("janela"), e.get("motorista"))
            by_drv[key].append(e)
    for key, rows in by_drv.items():
        if len(rows) > 3:  # soft warn
            warns.append({
                "tipo": "motorista",
                "nivel": "info",
                "texto": f"{key[2]} com {len(rows)} entregas em {key[0]} / {key[1] or '—'}",
                "motorista": key[2],
            })
    for e in events:
        if e.get("atrasada"):
            warns.append({
                "tipo": "atraso",
                "nivel": "warn",
                "texto": f"Atrasada · {e.get('id')} · {e.get('parceiro')}",
                "entrega_id": e.get("id"),
            })
    return warns[:30]


def calendar(view="day", data=None, fonte=None, motorista=None):
    view_n = str(view or "day").strip().lower()
    if view_n not in VIEWS:
        view_n = "day"
    base, day = _parse_day(data)
    today = _today()
    fk = str(fonte or "").strip().upper() or None
    mk = str(motorista or "").strip().lower()

    orders = delivery_orders.list_orders(fonte=fk).get("orders") or []
    events_all = [
        _event(o, today) for o in orders
        if o.get("status") != "cancelled"
    ]
    if mk:
        events_all = [
            e for e in events_all
            if mk in str(e.get("motorista") or "").lower()
        ]

    if view_n == "day":
        data_de = data_ate = day
        events = [e for e in events_all if e.get("data") == day]
    elif view_n == "week":
        # semana a partir do dia (7 dias)
        data_de = day
        data_ate = (base + timedelta(days=6)).strftime("%Y-%m-%d")
        events = [
            e for e in events_all
            if e.get("data") and data_de <= e.get("data") <= data_ate
        ]
    elif view_n == "month":
        start = base.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
        data_de = start.strftime("%Y-%m-%d")
        data_ate = end.strftime("%Y-%m-%d")
        day = data_de  # âncora do mês
        events = [
            e for e in events_all
            if e.get("data") and data_de <= e.get("data") <= data_ate
        ]
    else:  # field
        data_de = data_ate = day
        events = [
            e for e in events_all
            if e.get("data") == day
            or (e.get("atrasada") and e.get("status") in ("assigned", "in_transit", "ready"))
        ]
        if mk:
            events = [e for e in events if mk in str(e.get("motorista") or "").lower()]

    slots = _slots_for_range(fk, data_de, data_ate)

    # day cells for week/month
    days = []
    if view_n in ("week", "month"):
        cur = datetime.strptime(data_de, "%Y-%m-%d")
        end = datetime.strptime(data_ate, "%Y-%m-%d")
        while cur <= end:
            ds = cur.strftime("%Y-%m-%d")
            day_ev = [e for e in events if e.get("data") == ds]
            day_slots = [s for s in slots if s.get("data") == ds]
            cap = sum(int(s.get("capacidade") or 0) for s in day_slots)
            booked = sum(int(s.get("booked") or 0) for s in day_slots)
            days.append({
                "data": ds,
                "label": ds[5:],
                "weekday": cur.strftime("%a"),
                "hoje": ds == today,
                "entregas": len(day_ev),
                "capacidade": cap,
                "reservados": booked,
                "utilizacao_pct": round(100.0 * booked / cap, 1) if cap else None,
                "lotado": any(s.get("status") == "full" for s in day_slots),
                "atrasadas": sum(1 for e in day_ev if e.get("atrasada")),
                "eventos": day_ev,
            })
            cur += timedelta(days=1)

    focus_day = day if view_n in ("day", "field") else (_date_only(data) or today)
    if view_n == "month" and not _date_only(data):
        focus_day = today if data_de <= today <= data_ate else data_de
    windows = _window_blocks(focus_day, events, slots)
    conflicts = _conflicts(
        [e for e in events if e.get("data") == focus_day] if view_n != "day" else events,
        windows,
    )

    # field: group by driver sequence
    field_routes = []
    if view_n == "field":
        by_drv = defaultdict(list)
        for e in events:
            key = (e.get("motorista") or "(sem motorista)").strip()
            by_drv[key].append(e)
        for nome, rows in sorted(by_drv.items(), key=lambda x: (x[0] == "(sem motorista)", x[0])):
            rows = sorted(rows, key=lambda x: (
                PERIOD_ORDER.index(x.get("janela")) if x.get("janela") in PERIOD_ORDER else 9,
                x.get("id") or "",
            ))
            field_routes.append({
                "motorista": nome,
                "entregas": len(rows),
                "em_transito": sum(1 for r in rows if r.get("status") == "in_transit"),
                "eventos": rows,
            })

    fontes = sorted({
        str(o.get("fonte") or "").upper()
        for o in delivery_orders.list_orders().get("orders") or []
        if o.get("fonte")
    })
    if "DC-01" not in fontes:
        fontes.insert(0, "DC-01")

    return {
        "gerado_em": _now().isoformat(timespec="seconds"),
        "view": view_n,
        "view_label": VIEWS[view_n],
        "data": day if view_n != "month" else data_de,
        "data_de": data_de,
        "data_ate": data_ate,
        "fonte": fk or "TODAS",
        "eventos": sorted(events, key=lambda e: (e.get("data") or "", e.get("inicio") or "", e.get("id") or "")),
        "eventos_count": len(events),
        "janelas": windows,
        "dias": days,
        "rotas_campo": field_routes,
        "conflitos": conflicts,
        "resumo": {
            "entregas": len(events),
            "atrasadas": sum(1 for e in events if e.get("atrasada")),
            "em_transito": sum(1 for e in events if e.get("status") == "in_transit"),
            "lotadas": sum(1 for w in windows if w.get("lotado")),
            "conflitos": len(conflicts),
        },
        "fontes": fontes,
        "meta": meta(),
    }


def reschedule(entrega_id, data=None, periodo=None, slot_id=None, usuario="", motivo=""):
    """Reagenda DO (data/janela ou slot) — usado pelo drag do calendário."""
    eid = str(entrega_id or "").strip()
    order = delivery_orders.get_order(eid)
    if not order:
        raise ValueError("entrega não encontrada")
    if order.get("status") in ("completed", "cancelled"):
        raise ValueError("entrega fechada")

    sid = str(slot_id or "").strip()
    if not sid and data and periodo:
        per = str(periodo).strip().lower()
        slots = delivery_scheduling.list_slots(
            fonte=order.get("fonte"),
            data=_date_only(data),
        ).get("slots") or []
        match = next(
            (s for s in slots
             if s.get("periodo") == per and s.get("status") not in ("cancelled",)),
            None,
        )
        if match:
            sid = match["id"]
        else:
            try:
                created = delivery_scheduling.create_slot({
                    "data": _date_only(data),
                    "periodo": per,
                    "fonte": order.get("fonte") or "DC-01",
                }, usuario=usuario)
                sid = created["id"]
            except ValueError:
                pass

    if sid:
        slot = delivery_scheduling.reschedule(
            eid, sid, usuario=usuario,
            motivo=motivo or "reagendamento pelo calendário",
        )
        return {
            "action": "reschedule",
            "slot": slot,
            "order": delivery_orders.get_order(eid),
        }

    # fallback: só grava data/janela na DO
    data_raw = delivery_orders._load_raw()
    idx, row = delivery_orders._find(data_raw, eid)
    if row is None:
        raise ValueError("entrega não encontrada")
    if data is not None:
        row["data_agendada"] = _date_only(data)
    if periodo is not None:
        row["janela"] = str(periodo or "").strip().lower()
    row["atualizado_em"] = _now().isoformat(timespec="seconds")
    hist = list(row.get("historico") or [])
    hist.append(delivery_orders._hist(
        row.get("status"), usuario,
        f"calendário → {row.get('data_agendada')} {row.get('janela')}",
    ))
    row["historico"] = hist
    data_raw["orders"][idx] = row
    delivery_orders._save(data_raw)
    return {"action": "set_schedule", "order": delivery_orders._enrich(row)}
