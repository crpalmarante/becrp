"""
Delivery — Analytics (RFC-18008 MVP).

Camada read-only: agrega Orders, Tasks, Dispatch, Resources,
Scheduling, Tracking e POD.
Não executa entregas, não altera registros operacionais, não move estoque.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

import delivery_dispatch
import delivery_orders
import delivery_pod
import delivery_resources
import delivery_scheduling
import delivery_tasks
import delivery_tracking


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _pct(num, den):
    if not den:
        return None
    return round(100.0 * float(num) / float(den), 1)


def _count_by(rows, field="status"):
    return dict(Counter(str(r.get(field) or "") or "(vazio)" for r in rows))


def _date_only(val):
    s = str(val or "").strip()
    if not s:
        return ""
    return s[:10]


def _filter_fonte(rows, fonte, field="fonte"):
    if not fonte:
        return list(rows)
    fk = str(fonte).strip().upper()
    return [r for r in rows if str(r.get(field) or "").upper() == fk]


def meta():
    return {
        "read_only": True,
        "dimensoes": ["fonte", "motorista", "status", "periodo", "parceiro"],
        "kpis": [
            "volume", "on_time", "pod", "scheduling", "resources",
            "dispatch", "tasks", "tracking",
        ],
        "nota": "Custos/receita de frete ficam para integração futura — MVP sem inventar valores.",
    }


def dashboard(fonte=None, data_de=None, data_ate=None):
    """Visão executiva Delivery — somente leitura."""
    orders = delivery_orders.list_orders().get("orders") or []
    tasks = delivery_tasks.list_tarefas().get("tarefas") or []
    dispatches = delivery_dispatch.list_dispatches().get("dispatches") or []
    recursos = delivery_resources.list_recursos().get("recursos") or []
    slots = delivery_scheduling.list_slots().get("slots") or []
    tracks = delivery_tracking.list_tracks().get("tracks") or []
    pods = delivery_pod.list_pods().get("pods") or []

    orders = _filter_fonte(orders, fonte)
    # filter period by data_agendada (fallback criado_em)
    de = _date_only(data_de)
    ate = _date_only(data_ate)

    def in_period(row, field_pref="data_agendada"):
        d = _date_only(row.get(field_pref) or row.get("criado_em") or row.get("data"))
        if not d:
            return not (de or ate)
        if de and d < de:
            return False
        if ate and d > ate:
            return False
        return True

    if de or ate:
        orders = [r for r in orders if in_period(r)]
        order_ids = {r.get("id") for r in orders}
        tasks = [t for t in tasks if t.get("entrega_id") in order_ids]
        pods = [p for p in pods if p.get("entrega_id") in order_ids]
        tracks = [t for t in tracks if t.get("entrega_id") in order_ids]
        dispatches = [d for d in dispatches if in_period(d, "data")]
        slots = [s for s in slots if in_period(s, "data")]
        if fonte:
            slots = _filter_fonte(slots, fonte)
            dispatches = _filter_fonte(dispatches, fonte)
    else:
        if fonte:
            slots = _filter_fonte(slots, fonte)
            dispatches = _filter_fonte(dispatches, fonte)
            tracks = [t for t in tracks if str(t.get("fonte") or "").upper() == str(fonte).strip().upper()]
            pods = [p for p in pods if str(p.get("fonte") or "").upper() == str(fonte).strip().upper()]

    # ── Volume ──
    by_status = _count_by(orders, "status")
    total = len(orders)
    completed = by_status.get("completed", 0)
    delivered = by_status.get("delivered", 0) + completed
    cancelled = by_status.get("cancelled", 0)
    in_transit = by_status.get("in_transit", 0)
    openish = total - completed - cancelled

    # ── On-time (promise date vs POD confirm date / order update) ──
    pod_by_do = defaultdict(list)
    for p in pods:
        pod_by_do[p.get("entrega_id")].append(p)

    on_time = late = no_promise = 0
    for o in orders:
        if o.get("status") not in ("delivered", "completed"):
            continue
        promise = _date_only(o.get("data_agendada"))
        if not promise:
            no_promise += 1
            continue
        actual = ""
        for p in pod_by_do.get(o.get("id"), []):
            if p.get("status") in ("confirmed", "reviewed", "closed") and p.get("confirmado_em"):
                actual = _date_only(p.get("confirmado_em"))
                break
        if not actual:
            # histórico delivered
            for h in reversed(o.get("historico") or []):
                if h.get("status") in ("delivered", "completed"):
                    actual = _date_only(h.get("em"))
                    break
        if not actual:
            actual = _date_only(o.get("atualizado_em"))
        if actual and actual <= promise:
            on_time += 1
        elif actual:
            late += 1
        else:
            no_promise += 1

    delivered_n = on_time + late
    on_time_rate = _pct(on_time, delivered_n)
    late_rate = _pct(late, delivered_n)

    # ── Scheduling ──
    slot_cap = sum(int(s.get("capacidade") or 0) for s in slots)
    slot_booked = sum(int(s.get("booked") or 0) for s in slots)
    slot_open = len([s for s in slots if s.get("status") == "open"])
    slot_full = len([s for s in slots if s.get("status") == "full"])
    rescheduled = sum(
        1 for o in orders
        if (o.get("scheduling_status") or "") == "rescheduled"
    )
    scheduled = sum(1 for o in orders if o.get("slot_id") or o.get("data_agendada"))

    # ── POD ──
    pod_by_st = _count_by(pods, "status")
    pod_confirmed = sum(
        pod_by_st.get(k, 0) for k in ("confirmed", "reviewed", "closed")
    )
    pod_rejected = pod_by_st.get("rejected", 0)
    pod_pending = sum(pod_by_st.get(k, 0) for k in ("created", "waiting"))
    pod_success = _pct(pod_confirmed, pod_confirmed + pod_rejected) if (pod_confirmed + pod_rejected) else None

    # ── Resources / drivers ──
    by_driver = defaultdict(lambda: {"entregas": 0, "concluidas": 0, "falhas": 0})
    for o in orders:
        drv = (o.get("motorista") or o.get("recurso_id") or "").strip() or "(sem motorista)"
        by_driver[drv]["entregas"] += 1
        if o.get("status") in ("delivered", "completed"):
            by_driver[drv]["concluidas"] += 1
        if o.get("status") == "cancelled":
            by_driver[drv]["falhas"] += 1
    for p in pods:
        if p.get("status") == "rejected":
            drv = (p.get("entregador") or "").strip() or "(sem motorista)"
            by_driver[drv]["falhas"] += 1

    drivers = []
    for name, st in sorted(by_driver.items(), key=lambda x: -x[1]["entregas"]):
        ent = st["entregas"]
        drivers.append({
            "motorista": name,
            "entregas": ent,
            "concluidas": st["concluidas"],
            "falhas": st["falhas"],
            "sucesso_pct": _pct(st["concluidas"], ent),
        })

    rec_by_tipo = _count_by(recursos, "tipo")
    rec_by_status = _count_by(recursos, "status")
    rec_available = sum(
        1 for r in recursos
        if r.get("status") == "available" and r.get("ativo", True)
    )

    # ── Dispatch / tasks / tracking ──
    disp_by_st = _count_by(dispatches, "status")
    task_by_st = _count_by(tasks, "status")
    track_by_st = _count_by(tracks, "status")
    by_fonte = _count_by(orders, "fonte")

    # Top clientes
    by_parc = _count_by(orders, "parceiro")
    top_clientes = sorted(
        [{"parceiro": k, "entregas": v} for k, v in by_parc.items()],
        key=lambda x: -x["entregas"],
    )[:8]

    # Exceptions
    exceptions = []
    for o in orders:
        if o.get("status") == "cancelled":
            exceptions.append({
                "tipo": "entrega",
                "id": o.get("id"),
                "nota": o.get("cancelamento_motivo") or "cancelada",
                "status": o.get("status"),
            })
        elif o.get("status") == "waiting_stock":
            exceptions.append({
                "tipo": "estoque",
                "id": o.get("id"),
                "nota": "aguardando estoque",
                "status": o.get("status"),
            })
    for p in pods:
        if p.get("status") == "rejected":
            exceptions.append({
                "tipo": "pod",
                "id": p.get("id"),
                "nota": p.get("motivo_rejeicao") or "rejeitado",
                "status": p.get("status"),
            })
    for t in tracks:
        if t.get("status") == "failed":
            exceptions.append({
                "tipo": "tracking",
                "id": t.get("entrega_id") or t.get("id"),
                "nota": "falha em rota",
                "status": t.get("status"),
            })
    for s in slots:
        if s.get("status") == "full":
            exceptions.append({
                "tipo": "agenda",
                "id": s.get("id"),
                "nota": f"lotado {s.get('data')} {s.get('periodo')}",
                "status": s.get("status"),
            })

    return {
        "gerado_em": _now(),
        "filtros": {
            "fonte": fonte or "",
            "data_de": de,
            "data_ate": ate,
        },
        "kpis": {
            "entregas_total": total,
            "entregas_abertas": openish,
            "entregas_entregues": delivered,
            "entregas_concluidas": completed,
            "entregas_canceladas": cancelled,
            "em_transito": in_transit,
            "on_time_pct": on_time_rate,
            "late_pct": late_rate,
            "pod_sucesso_pct": pod_success,
            "slots_utilizacao_pct": _pct(slot_booked, slot_cap),
            "recursos_disponiveis": rec_available,
        },
        "volume": {
            "por_status": by_status,
            "por_fonte": by_fonte,
            "on_time": on_time,
            "late": late,
            "sem_promise": no_promise,
        },
        "scheduling": {
            "slots": len(slots),
            "abertos": slot_open,
            "lotados": slot_full,
            "capacidade": slot_cap,
            "reservados": slot_booked,
            "utilizacao_pct": _pct(slot_booked, slot_cap),
            "entregas_agendadas": scheduled,
            "reagendadas": rescheduled,
        },
        "pod": {
            "total": len(pods),
            "confirmados": pod_confirmed,
            "rejeitados": pod_rejected,
            "pendentes": pod_pending,
            "sucesso_pct": pod_success,
            "por_status": pod_by_st,
        },
        "recursos": {
            "total": len(recursos),
            "disponiveis": rec_available,
            "por_tipo": rec_by_tipo,
            "por_status": rec_by_status,
            "motoristas": drivers[:10],
        },
        "dispatch": {
            "total": len(dispatches),
            "por_status": disp_by_st,
        },
        "tarefas": {
            "total": len(tasks),
            "por_status": task_by_st,
        },
        "tracking": {
            "total": len(tracks),
            "por_status": track_by_st,
        },
        "clientes": top_clientes,
        "exceptions": exceptions[:40],
        "exceptions_count": len(exceptions),
        "custos": {
            "disponivel": False,
            "nota": "Sem motor de custo de frete no MVP — não inventar valores.",
        },
    }
