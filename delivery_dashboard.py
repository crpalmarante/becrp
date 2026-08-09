"""
Delivery — Dashboard (RFC-18101 MVP).

Visão operacional em tempo real: KPIs, widgets, agenda do dia, alertas e eventos.
Read-only — não altera operação, não move estoque.
Complementa Workspace (18100) e Analytics (18008).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

import delivery_dispatch
import delivery_orders
import delivery_pod
import delivery_resources
import delivery_scheduling
import delivery_tracking


def _now():
    return datetime.now()


def _today():
    return _now().strftime("%Y-%m-%d")


def _date_only(val):
    s = str(val or "").strip()
    return s[:10] if s else ""


def _pct(num, den):
    if not den:
        return None
    return round(100.0 * float(num) / float(den), 1)


def _count_by(rows, field="status"):
    return dict(Counter(str(r.get(field) or "") or "(vazio)" for r in rows))


def _is_delayed(o, today):
    if o.get("status") in ("delivered", "completed", "cancelled"):
        return False
    d = _date_only(o.get("data_agendada"))
    return bool(d and d < today)


def meta():
    return {
        "read_only": True,
        "refresh_seconds": 45,
        "widgets": [
            "kpis", "status", "drivers", "dispatch", "schedule",
            "regions", "alerts", "events",
        ],
        "nota": "Dashboard operacional do dia — Analytics (18008) cobre histórico/BI.",
    }


def dashboard(fonte=None):
    """Overview operacional de hoje."""
    today = _today()
    now = _now()
    fk = str(fonte or "").strip().upper() or None

    orders = delivery_orders.list_orders(fonte=fk).get("orders") or []
    dispatches = delivery_dispatch.list_dispatches(fonte=fk, data=today).get("dispatches") or []
    # se filtro data zerar, pega abertos do dia sem data strict
    if not dispatches and fk:
        dispatches = [
            d for d in (delivery_dispatch.list_dispatches(fonte=fk).get("dispatches") or [])
            if _date_only(d.get("data")) == today or d.get("status") not in ("closed", "cancelled", "completed")
        ]
    elif not dispatches:
        dispatches = [
            d for d in (delivery_dispatch.list_dispatches().get("dispatches") or [])
            if _date_only(d.get("data")) == today
            or d.get("status") in ("open", "planning", "assigned", "released", "in_progress")
        ]

    recursos = delivery_resources.list_recursos().get("recursos") or []
    slots = delivery_scheduling.list_slots(fonte=fk, data=today).get("slots") or []
    tracks = delivery_tracking.list_tracks(fonte=fk).get("tracks") or []
    pods = delivery_pod.list_pods().get("pods") or []
    if fk:
        pods = [p for p in pods if str(p.get("fonte") or "").upper() == fk]

    # today-focused order set
    today_orders = [
        o for o in orders
        if _date_only(o.get("data_agendada")) == today
        or (
            not _date_only(o.get("data_agendada"))
            and o.get("status") not in ("completed", "cancelled")
        )
        or (o.get("status") in ("in_transit", "assigned") and _date_only(o.get("atualizado_em")) == today)
    ]
    # also include delayed still open
    delayed = [o for o in orders if _is_delayed(o, today)]
    for o in delayed:
        if o not in today_orders:
            today_orders.append(o)

    scheduled = len([
        o for o in today_orders
        if o.get("status") not in ("cancelled",)
    ])
    ready = [o for o in orders if o.get("status") == "ready"]
    in_transit = [o for o in orders if o.get("status") == "in_transit"]
    assigned = [o for o in orders if o.get("status") == "assigned"]

    delivered_today = []
    for o in orders:
        if o.get("status") not in ("delivered", "completed"):
            continue
        hit = False
        for h in reversed(o.get("historico") or []):
            if h.get("status") in ("delivered", "completed") and _date_only(h.get("em")) == today:
                hit = True
                break
        if hit or _date_only(o.get("atualizado_em")) == today:
            delivered_today.append(o)

    failed_pods = [p for p in pods if p.get("status") == "rejected"]
    failed_tracks = [t for t in tracks if t.get("status") == "failed"]
    cancelled_today = [
        o for o in orders
        if o.get("status") == "cancelled" and _date_only(o.get("atualizado_em")) == today
    ]
    pending_pod = [p for p in pods if p.get("status") in ("created", "waiting")]

    kpis = [
        {
            "id": "scheduled",
            "titulo": "Agendadas hoje",
            "valor": scheduled,
            "href": "entregas.html",
            "filtro": "today",
        },
        {
            "id": "ready",
            "titulo": "Prontas p/ despacho",
            "valor": len(ready),
            "href": "entregas.html",
            "filtro": "ready",
            "prioridade": "high" if ready else "normal",
        },
        {
            "id": "in_transit",
            "titulo": "Em trânsito",
            "valor": len(in_transit),
            "href": "entregas-workspace.html",
            "filtro": "in_transit",
            "prioridade": "high" if in_transit else "normal",
        },
        {
            "id": "delivered",
            "titulo": "Entregues hoje",
            "valor": len(delivered_today),
            "href": "entregas.html",
            "filtro": "delivered",
        },
        {
            "id": "delayed",
            "titulo": "Atrasadas",
            "valor": len(delayed),
            "href": "entregas-workspace.html",
            "filtro": "delayed",
            "prioridade": "high" if delayed else "normal",
        },
        {
            "id": "failed",
            "titulo": "Falhas",
            "valor": len(failed_pods) + len(failed_tracks) + len(cancelled_today),
            "href": "entregas.html",
            "filtro": "failed",
            "prioridade": "high" if (failed_pods or failed_tracks) else "normal",
        },
        {
            "id": "pending_pod",
            "titulo": "POD pendente",
            "valor": len(pending_pod),
            "href": "entregas.html",
            "filtro": "pod_waiting",
        },
    ]

    # Status widget — today's relevant + open pipeline
    status_pool = list({
        o.get("id"): o
        for o in (today_orders + ready + assigned + in_transit)
        if o.get("id")
    }.values())
    by_status = _count_by(status_pool, "status")
    # inject delayed count as pseudo bucket for visibility
    status_bars = [
        {"id": k, "label": delivery_orders.STATUSES.get(k, k), "valor": v}
        for k, v in sorted(by_status.items(), key=lambda x: -x[1])
    ]
    if delayed:
        status_bars.append({
            "id": "delayed",
            "label": "Atrasadas",
            "valor": len(delayed),
        })

    # Driver activity
    drivers = [
        r for r in recursos
        if r.get("tipo") in ("driver", "carrier") and r.get("ativo", True)
    ]
    driver_rows = []
    for r in drivers:
        nome = r.get("nome") or r.get("id")
        cur = [
            o for o in orders
            if o.get("status") in ("assigned", "in_transit")
            and (
                str(o.get("recurso_id") or "") == str(r.get("id") or "")
                or str(o.get("motorista") or "").lower() == str(nome or "").lower()
            )
        ]
        first = cur[0] if cur else None
        stop = None
        if first:
            for st in first.get("paradas") or []:
                if st.get("status") in ("en_route", "arrived", "pending"):
                    stop = st
                    break
            if stop is None and first.get("paradas"):
                stop = first["paradas"][0]
        tr = None
        if first:
            tr = next((t for t in tracks if t.get("entrega_id") == first.get("id")), None)
        driver_rows.append({
            "id": r.get("id"),
            "nome": nome,
            "status": r.get("status"),
            "status_label": r.get("status_label"),
            "placa": r.get("placa") or "",
            "entrega_atual": (first or {}).get("id") or "",
            "parceiro": (first or {}).get("parceiro") or "",
            "parada_atual": (stop or {}).get("rotulo") or (stop or {}).get("parada") or "",
            "tracking": (tr or {}).get("status_label") or (tr or {}).get("status") or "",
            "ativas": len(cur),
        })
    driver_rows.sort(key=lambda x: (-x["ativas"], x.get("nome") or ""))

    # Dispatch overview
    disp_by = _count_by(dispatches, "status")
    dispatch_widget = {
        "total": len(dispatches),
        "por_status": disp_by,
        "barras": [
            {"id": k, "label": delivery_dispatch.STATUSES.get(k, k), "valor": v}
            for k, v in sorted(disp_by.items(), key=lambda x: -x[1])
        ],
    }

    # Today's schedule (slots)
    schedule = []
    for s in sorted(slots, key=lambda x: (x.get("inicio") or "", x.get("id") or "")):
        cap = int(s.get("capacidade") or 0)
        booked = int(s.get("booked") or 0)
        schedule.append({
            "id": s.get("id"),
            "periodo": s.get("periodo"),
            "periodo_label": s.get("periodo_label"),
            "inicio": s.get("inicio"),
            "fim": s.get("fim"),
            "janela": f"{s.get('inicio') or ''}–{s.get('fim') or ''}",
            "entregas": booked,
            "capacidade": cap,
            "utilizacao_pct": _pct(booked, cap),
            "status": s.get("status"),
            "status_label": s.get("status_label"),
            "lotado": s.get("status") == "full",
        })

    # Regional — cidade das paradas (fallback fonte)
    region_counter = Counter()
    for o in today_orders or orders:
        if o.get("status") == "cancelled":
            continue
        cities = []
        for st in o.get("paradas") or []:
            c = str(st.get("cidade") or "").strip()
            if c:
                cities.append(c)
        if not cities:
            cities = [str(o.get("fonte") or "Sem região")]
        for c in set(cities):
            region_counter[c] += 1
    regions = [
        {"regiao": k, "entregas": v}
        for k, v in region_counter.most_common(12)
    ]

    # Alerts
    alerts = []
    for o in delayed[:10]:
        alerts.append({
            "severidade": "high",
            "tipo": "atraso",
            "id": o.get("id"),
            "texto": f"Atrasada · {o.get('parceiro') or ''} · {o.get('data_agendada')}",
            "status": o.get("status"),
        })
    for p in failed_pods[:6]:
        alerts.append({
            "severidade": "high",
            "tipo": "pod",
            "id": p.get("id"),
            "texto": f"POD rejeitado · {p.get('entrega_id')} · {p.get('motivo_rejeicao') or ''}",
            "status": p.get("status"),
        })
    for t in failed_tracks[:6]:
        alerts.append({
            "severidade": "high",
            "tipo": "tracking",
            "id": t.get("entrega_id") or t.get("id"),
            "texto": "Falha em rota",
            "status": t.get("status"),
        })
    for s in schedule:
        if s.get("lotado"):
            alerts.append({
                "severidade": "medium",
                "tipo": "capacidade",
                "id": s.get("id"),
                "texto": f"Capacidade esgotada · {s.get('janela')}",
                "status": "full",
            })
    sev_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: sev_order.get(a.get("severidade"), 9))

    # Recent events — tracking events + order historico
    events = []
    for t in tracks:
        for ev in (t.get("events") or [])[-5:]:
            events.append({
                "em": ev.get("em") or "",
                "tipo": ev.get("tipo_label") or ev.get("tipo"),
                "entrega_id": t.get("entrega_id"),
                "mensagem": ev.get("mensagem") or "",
                "usuario": ev.get("usuario") or "",
                "fonte": "tracking",
            })
    for o in orders:
        for h in (o.get("historico") or [])[-3:]:
            events.append({
                "em": h.get("em") or "",
                "tipo": h.get("status") or "",
                "entrega_id": o.get("id"),
                "mensagem": h.get("nota") or "",
                "usuario": h.get("usuario") or "",
                "fonte": "order",
            })
    events.sort(key=lambda e: e.get("em") or "", reverse=True)
    events = events[:25]

    on_schedule = None
    den = len(delivered_today) + len(delayed)
    if den:
        # rough: delivered today vs delayed open
        on_schedule = _pct(len(delivered_today), den)

    fontes = sorted({
        str(o.get("fonte") or "").upper()
        for o in delivery_orders.list_orders().get("orders") or []
        if o.get("fonte")
    })
    if "DC-01" not in fontes:
        fontes.insert(0, "DC-01")

    return {
        "gerado_em": now.isoformat(timespec="seconds"),
        "contexto": {
            "fonte": fk or "TODAS",
            "data": today,
            "hora": now.strftime("%H:%M"),
            "pergunta": "As operações estão no prazo?",
        },
        "kpis": kpis,
        "resumo": {
            "agendadas": scheduled,
            "prontas": len(ready),
            "atribuidas": len(assigned),
            "em_transito": len(in_transit),
            "entregues_hoje": len(delivered_today),
            "atrasadas": len(delayed),
            "falhas": len(failed_pods) + len(failed_tracks) + len(cancelled_today),
            "pod_pendente": len(pending_pod),
            "no_prazo_pct": on_schedule,
            "capacidade_slots_pct": _pct(
                sum(int(s.get("booked") or 0) for s in slots),
                sum(int(s.get("capacidade") or 0) for s in slots),
            ),
        },
        "status": status_bars,
        "motoristas": driver_rows,
        "dispatch": dispatch_widget,
        "agenda": schedule,
        "regioes": regions,
        "alertas": alerts[:30],
        "eventos": events,
        "fontes": fontes,
        "meta": meta(),
    }
