"""
Delivery — Workspace (RFC-18100 MVP).

Cockpit operacional: KPIs do dia, fila de despacho, motoristas,
entregas ativas, alertas e ações rápidas.
Não possui dados próprios — consome Orders/Dispatch/Scheduling/
Tracking/POD/Analytics/Resources. Não move estoque.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import delivery_analytics
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


def _shift_label(dt=None):
    h = (dt or _now()).hour
    if 5 <= h < 13:
        return "Manhã"
    if 13 <= h < 21:
        return "Tarde"
    return "Noite"


OPEN_STATUSES = frozenset({
    "draft", "confirmed", "waiting_stock", "ready", "assigned", "in_transit",
})
ACTIVE_STATUSES = frozenset({"assigned", "in_transit"})
DONE_STATUSES = frozenset({"delivered", "completed"})
QUEUE_STATUSES = frozenset({"ready", "assigned", "confirmed"})


def _slim_order(o):
    return {
        "id": o.get("id"),
        "parceiro": o.get("parceiro"),
        "fonte": o.get("fonte"),
        "status": o.get("status"),
        "status_label": o.get("status_label"),
        "data_agendada": o.get("data_agendada"),
        "janela": o.get("janela"),
        "slot_id": o.get("slot_id"),
        "motorista": o.get("motorista"),
        "veiculo": o.get("veiculo"),
        "origem_ref": o.get("origem_ref"),
        "paradas_count": o.get("paradas_count"),
        "acoes": o.get("acoes") or [],
    }


def _quick_order(o):
    st = o.get("status")
    if st == "draft":
        return {"action": "confirm", "label": "Confirmar"}
    if st == "confirmed":
        return {"action": "ready", "label": "Pronta"}
    if st == "ready":
        return {"action": "assign", "label": "Atribuir"}
    if st == "assigned":
        return {"action": "depart", "label": "Sair"}
    if st == "in_transit":
        return {"action": "deliver", "label": "Entregar"}
    if st == "delivered":
        return {"action": "complete", "label": "Concluir"}
    return None


def _is_delayed(o, today):
    if o.get("status") in DONE_STATUSES or o.get("status") == "cancelled":
        return False
    d = _date_only(o.get("data_agendada"))
    return bool(d and d < today)


def _in_period(o, periodo, today):
    p = str(periodo or "today").strip().lower()
    d = _date_only(o.get("data_agendada") or o.get("criado_em"))
    if p == "all" or not d:
        return True if p == "all" else bool(d == today or not d)
    if p == "today":
        return d == today or (not _date_only(o.get("data_agendada")) and o.get("status") in OPEN_STATUSES)
    if p == "tomorrow":
        tom = (datetime.strptime(today, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        return d == tom
    if p in ("week", "this_week"):
        base = datetime.strptime(today, "%Y-%m-%d")
        end = (base + timedelta(days=6)).strftime("%Y-%m-%d")
        return today <= d <= end
    return True


def meta():
    return {
        "periodos": [
            {"id": "today", "label": "Hoje"},
            {"id": "tomorrow", "label": "Amanhã"},
            {"id": "week", "label": "Esta semana"},
            {"id": "all", "label": "Todos"},
        ],
        "perfis": [
            {"id": "despachante", "label": "Despachante"},
            {"id": "motorista", "label": "Motorista"},
            {"id": "supervisor", "label": "Supervisor"},
            {"id": "gerente", "label": "Gerente"},
        ],
        "refresh_seconds": 45,
    }


def workspace(fonte=None, perfil=None, periodo="today", motorista=None):
    today = _today()
    now = _now()
    periodo_n = str(periodo or "today").strip().lower() or "today"
    perfil_n = str(perfil or "despachante").strip().lower()
    if perfil_n not in ("despachante", "motorista", "supervisor", "gerente"):
        perfil_n = "despachante"

    orders = delivery_orders.list_orders(fonte=fonte).get("orders") or []
    recursos = delivery_resources.list_recursos().get("recursos") or []
    dispatches = delivery_dispatch.list_dispatches(fonte=fonte).get("dispatches") or []
    slots = delivery_scheduling.list_slots(
        fonte=fonte, data_de=today,
        data_ate=(now + timedelta(days=6)).strftime("%Y-%m-%d"),
    ).get("slots") or []
    tracks = delivery_tracking.list_tracks(fonte=fonte).get("tracks") or []
    pods = delivery_pod.list_pods().get("pods") or []
    if fonte:
        fk = str(fonte).strip().upper()
        pods = [p for p in pods if str(p.get("fonte") or "").upper() == fk]

    drv_filter = str(motorista or "").strip().lower()
    if perfil_n == "motorista" and drv_filter:
        orders = [
            o for o in orders
            if drv_filter in str(o.get("motorista") or "").lower()
            or drv_filter in str(o.get("recurso_id") or "").lower()
        ]

    period_orders = [o for o in orders if _in_period(o, periodo_n, today)]

    # KPIs
    today_orders = [
        o for o in orders
        if _date_only(o.get("data_agendada")) == today
        or (not _date_only(o.get("data_agendada")) and o.get("status") in OPEN_STATUSES)
    ]
    scheduled_today = len([
        o for o in today_orders
        if o.get("status") not in ("cancelled",)
    ])
    in_transit = [o for o in orders if o.get("status") == "in_transit"]
    delayed = [o for o in orders if _is_delayed(o, today)]
    completed_today = []
    for o in orders:
        if o.get("status") not in DONE_STATUSES:
            continue
        for h in reversed(o.get("historico") or []):
            if h.get("status") in ("delivered", "completed") and _date_only(h.get("em")) == today:
                completed_today.append(o)
                break
        else:
            if _date_only(o.get("atualizado_em")) == today:
                completed_today.append(o)
    failed_pods = [p for p in pods if p.get("status") == "rejected"]
    failed_tracks = [t for t in tracks if t.get("status") == "failed"]
    failed_n = len(failed_pods) + len([
        o for o in orders if o.get("status") == "cancelled"
        and _date_only(o.get("atualizado_em")) == today
    ])

    cards = [
        {
            "id": "hoje",
            "titulo": "Hoje",
            "valor": scheduled_today,
            "sub": "agendadas / abertas",
            "href": "entregas.html",
            "prioridade": "normal",
            "urgentes": 0,
        },
        {
            "id": "atrasadas",
            "titulo": "Atrasadas",
            "valor": len(delayed),
            "sub": "passou a data",
            "href": "entregas.html",
            "prioridade": "high" if delayed else "normal",
            "urgentes": len(delayed),
        },
        {
            "id": "transito",
            "titulo": "Em trânsito",
            "valor": len(in_transit),
            "sub": "em execução",
            "href": "entregas.html",
            "prioridade": "high" if in_transit else "normal",
            "urgentes": len(in_transit),
        },
        {
            "id": "concluidas",
            "titulo": "Concluídas hoje",
            "valor": len(completed_today),
            "sub": "delivered / completed",
            "href": "entregas.html",
            "prioridade": "normal",
            "urgentes": 0,
        },
        {
            "id": "falhas",
            "titulo": "Falhas",
            "valor": failed_n + len(failed_tracks),
            "sub": "POD rejeitado / canceladas",
            "href": "entregas.html",
            "prioridade": "high" if (failed_n or failed_tracks) else "normal",
            "urgentes": failed_n + len(failed_tracks),
        },
        {
            "id": "fila",
            "titulo": "Fila despacho",
            "valor": len([o for o in orders if o.get("status") in QUEUE_STATUSES]),
            "sub": "ready / assigned",
            "href": "entregas.html",
            "prioridade": "normal",
            "urgentes": 0,
        },
    ]

    # Dispatch queue
    queue_src = [
        o for o in period_orders
        if o.get("status") in QUEUE_STATUSES or _is_delayed(o, today)
    ]
    queue_src = sorted(
        queue_src,
        key=lambda o: (
            0 if _is_delayed(o, today) else 1,
            0 if o.get("status") == "ready" else 1,
            o.get("data_agendada") or "",
            o.get("id") or "",
        ),
    )[:12]
    fila = []
    for o in queue_src:
        item = _slim_order(o)
        item["kind"] = "order"
        item["urgente"] = _is_delayed(o, today) or o.get("status") == "ready"
        q = _quick_order(o)
        if q:
            item["acao_rapida"] = q
        item["atrasada"] = _is_delayed(o, today)
        fila.append(item)

    # Active deliveries
    ativos = []
    for o in orders:
        if o.get("status") not in ACTIVE_STATUSES:
            continue
        item = _slim_order(o)
        item["kind"] = "order"
        tr = next((t for t in tracks if t.get("entrega_id") == o.get("id")), None)
        item["tracking_status"] = (tr or {}).get("status")
        item["tracking_status_label"] = (tr or {}).get("status_label")
        stops = o.get("paradas") or []
        done = sum(1 for s in stops if s.get("status") in ("delivered", "skipped"))
        item["progresso"] = f"{done}/{len(stops)}" if stops else "—"
        q = _quick_order(o)
        if q:
            item["acao_rapida"] = q
        item["urgente"] = o.get("status") == "in_transit"
        ativos.append(item)
    ativos = ativos[:10]

    # Drivers
    drivers = [r for r in recursos if r.get("tipo") in ("driver", "carrier") and r.get("ativo", True)]
    motoristas = []
    for r in drivers:
        nome = r.get("nome") or r.get("id")
        assigned = [
            o for o in orders
            if o.get("status") in ACTIVE_STATUSES
            and (
                str(o.get("recurso_id") or "") == str(r.get("id") or "")
                or str(o.get("motorista") or "").lower() == str(nome or "").lower()
            )
        ]
        motoristas.append({
            "id": r.get("id"),
            "nome": nome,
            "tipo": r.get("tipo"),
            "tipo_label": r.get("tipo_label"),
            "status": r.get("status"),
            "status_label": r.get("status_label"),
            "placa": r.get("placa") or "",
            "entregas_ativas": len(assigned),
            "tarefa_atual": assigned[0]["id"] if assigned else "",
        })
    motoristas.sort(key=lambda x: (0 if x.get("status") == "available" else 1, x.get("nome") or ""))

    # Calendar strip (7 days) — preview; full calendar = 18104
    calendar = []
    for i in range(7):
        d = (now + timedelta(days=i)).strftime("%Y-%m-%d")
        day_slots = [s for s in slots if s.get("data") == d]
        day_orders = [o for o in orders if _date_only(o.get("data_agendada")) == d]
        cap = sum(int(s.get("capacidade") or 0) for s in day_slots)
        booked = sum(int(s.get("booked") or 0) for s in day_slots)
        calendar.append({
            "data": d,
            "label": "Hoje" if i == 0 else ("Amanhã" if i == 1 else d[5:]),
            "entregas": len(day_orders),
            "slots": len(day_slots),
            "capacidade": cap,
            "reservados": booked,
            "lotado": any(s.get("status") == "full" for s in day_slots),
        })

    # Alerts
    alerts = []
    for o in delayed[:8]:
        alerts.append({
            "tipo": "atraso",
            "nivel": "warn",
            "id": o.get("id"),
            "texto": f"Atrasada · {o.get('parceiro') or ''} · {o.get('data_agendada')}",
            "status": o.get("status"),
        })
    for p in failed_pods[:5]:
        alerts.append({
            "tipo": "pod",
            "nivel": "warn",
            "id": p.get("id"),
            "texto": f"POD rejeitado · {p.get('entrega_id')} · {p.get('motivo_rejeicao') or ''}",
            "status": p.get("status"),
        })
    for t in failed_tracks[:5]:
        alerts.append({
            "tipo": "tracking",
            "nivel": "warn",
            "id": t.get("entrega_id") or t.get("id"),
            "texto": "Falha em rota",
            "status": t.get("status"),
        })
    for s in slots:
        if s.get("status") == "full" and s.get("data") == today:
            alerts.append({
                "tipo": "capacidade",
                "nivel": "info",
                "id": s.get("id"),
                "texto": f"Slot lotado · {s.get('periodo')} {s.get('data')}",
                "status": "full",
            })

    # Notifications chips
    notifications = []
    if delayed:
        notifications.append({
            "tipo": "atraso", "nivel": "warn",
            "texto": f"{len(delayed)} entrega(s) atrasada(s)",
        })
    if in_transit:
        notifications.append({
            "tipo": "transito", "nivel": "info",
            "texto": f"{len(in_transit)} em trânsito",
        })
    pod_waiting = sum(1 for p in pods if p.get("status") in ("created", "waiting"))
    if pod_waiting:
        notifications.append({
            "tipo": "pod", "nivel": "info",
            "texto": f"{pod_waiting} POD(s) aguardando",
        })
    open_disp = [d for d in dispatches if d.get("status") in ("open", "planning", "assigned", "released")]
    if open_disp:
        notifications.append({
            "tipo": "despacho", "nivel": "info",
            "texto": f"{len(open_disp)} lote(s) de despacho abertos",
        })

    # Current focus = first delayed or first in transit or first queue
    current = None
    if delayed:
        current = _slim_order(delayed[0])
        current["kind"] = "order"
        current["motivo"] = "atrasada"
        q = _quick_order(delayed[0])
        if q:
            current["acao_rapida"] = q
    elif in_transit:
        current = ativos[0] if ativos else _slim_order(in_transit[0])
        current["motivo"] = "em trânsito"
    elif fila:
        current = dict(fila[0])
        current["motivo"] = "fila"

    layout = {
        "mostrar_cards": True,
        "mostrar_fila": perfil_n != "motorista",
        "mostrar_motoristas": perfil_n != "motorista",
        "mostrar_ativos": True,
        "mostrar_calendario": perfil_n in ("despachante", "supervisor", "gerente"),
        "mostrar_alertas": perfil_n != "motorista",
        "mostrar_analytics": perfil_n in ("supervisor", "gerente"),
        "enfatizar_meus": perfil_n == "motorista",
    }

    atalhos = [
        {"label": "Nova entrega", "href": "entregas.html"},
        {"label": "Despacho", "href": "entregas.html"},
        {"label": "Agenda", "href": "entregas.html"},
        {"label": "Tracking", "href": "entregas.html"},
        {"label": "POD", "href": "entregas.html"},
        {"label": "Recursos", "href": "entregas.html"},
    ]
    if layout["mostrar_analytics"]:
        atalhos.append({"label": "Analytics", "href": "entregas.html"})
    atalhos.append({"label": "WMS Expedição", "href": "wms-expedicao.html"})

    # Fontes disponíveis (para filtro)
    fontes = sorted({
        str(o.get("fonte") or "").upper()
        for o in delivery_orders.list_orders().get("orders") or []
        if o.get("fonte")
    })
    if "DC-01" not in fontes:
        fontes.insert(0, "DC-01")

    dash = None
    if layout["mostrar_analytics"]:
        try:
            dash = delivery_analytics.dashboard(fonte=fonte, data_de=today, data_ate=today)
        except Exception:
            dash = None

    return {
        "gerado_em": now.isoformat(timespec="seconds"),
        "perfil": perfil_n,
        "periodo": periodo_n,
        "contexto": {
            "fonte": (fonte or "").upper() or "TODAS",
            "data": today,
            "hora": now.strftime("%H:%M"),
            "turno": _shift_label(now),
            "pergunta": "O que precisa de atenção agora?",
        },
        "layout": layout,
        "cards": cards,
        "kpis": {
            "hoje": scheduled_today,
            "atrasadas": len(delayed),
            "em_transito": len(in_transit),
            "concluidas_hoje": len(completed_today),
            "falhas": failed_n + len(failed_tracks),
        },
        "notificacoes": notifications,
        "alertas": alerts[:20],
        "fila_despacho": fila,
        "entregas_ativas": ativos,
        "motoristas": motoristas,
        "calendario": calendar,
        "foco": current,
        "atalhos": atalhos,
        "fontes": fontes,
        "lotes_abertos": len(open_disp),
        "analytics_hoje": {
            "on_time_pct": (dash or {}).get("kpis", {}).get("on_time_pct"),
            "pod_sucesso_pct": (dash or {}).get("kpis", {}).get("pod_sucesso_pct"),
        } if dash else None,
        "meta": meta(),
    }


def quick_action(kind, oid, action, usuario="", motorista="", veiculo="", recurso_id="", motivo=""):
    """Ação rápida do cockpit — delega aos módulos Core."""
    kind = str(kind or "").strip().lower()
    act = str(action or "").strip().lower()
    key = str(oid or "").strip()
    if not key or not act:
        raise ValueError("kind, id e action obrigatórios")

    if kind in ("order", "entrega", "do"):
        extra = {}
        if act == "assign":
            extra["motorista"] = motorista or "Carlos Motorista"
            extra["veiculo"] = veiculo or "ABC1D23"
            extra["recurso_id"] = recurso_id or "DRV-01"
        if act == "cancel":
            if not str(motivo or "").strip():
                raise ValueError("motivo obrigatório para cancelar")
        if act == "complete":
            # force opcional não — workspace respeita POD
            pass
        row = delivery_orders.transition(
            key, act, usuario=usuario, motivo=motivo or "", **extra,
        )
        return {"kind": "order", "item": row}

    if kind in ("dispatch", "lote", "ds"):
        row = delivery_dispatch.transition(
            key, act, usuario=usuario, motivo=motivo or "",
            motorista=motorista or None,
            veiculo=veiculo or None,
            recurso_id=recurso_id or None,
        )
        return {"kind": "dispatch", "item": row}

    if kind == "pod":
        if act == "confirm":
            row = delivery_pod.confirm(key, {
                "receptor_nome": motorista or "Cliente",
                "entregador": usuario or "Motorista",
            }, usuario=usuario)
        elif act == "reject":
            row = delivery_pod.reject(key, {"motivo": motivo or "recusa"}, usuario=usuario)
        else:
            raise ValueError(f"ação POD inválida: {act}")
        return {"kind": "pod", "item": row}

    raise ValueError(f"kind inválido: {kind}")
