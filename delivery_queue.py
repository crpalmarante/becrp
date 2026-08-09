"""
Delivery — Queue (RFC-18102 MVP).

Fila operacional: projeção dinâmica de Delivery Orders.
Não possui dados próprios. Não move estoque.
Ações delegam a Orders / Dispatch / Scheduling.
"""

from __future__ import annotations

from datetime import datetime

import delivery_dispatch
import delivery_orders
import delivery_pod
import delivery_scheduling
import delivery_tracking

CATEGORIES = {
    "waiting_stock": "Aguardando estoque",
    "ready": "Pronta p/ despacho",
    "waiting_assignment": "Aguardando atribuição",
    "scheduled_today": "Agendada hoje",
    "in_transit": "Em trânsito",
    "exceptions": "Exceções",
    "completed_today": "Concluídas hoje",
    "all_open": "Todas abertas",
}

PRIO_RANK = {
    "emergency": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
}


def _now():
    return datetime.now()


def _today():
    return _now().strftime("%Y-%m-%d")


def _date_only(val):
    s = str(val or "").strip()
    return s[:10] if s else ""


def meta():
    return {
        "categorias": [{"id": k, "label": v} for k, v in CATEGORIES.items()],
        "prioridades": [
            {"id": k, "label": v} for k, v in delivery_orders.PRIORITIES.items()
        ],
        "refresh_seconds": 30,
        "nota": "Projeção — não armazena fila própria.",
    }


def _is_delayed(o, today):
    if o.get("status") in ("delivered", "completed", "cancelled"):
        return False
    d = _date_only(o.get("data_agendada"))
    return bool(d and d < today)


def _completed_today(o, today):
    if o.get("status") not in ("delivered", "completed"):
        return False
    for h in reversed(o.get("historico") or []):
        if h.get("status") in ("delivered", "completed") and _date_only(h.get("em")) == today:
            return True
    return _date_only(o.get("atualizado_em")) == today


def _destination(o):
    stops = o.get("paradas") or []
    if not stops:
        return ""
    st = stops[0]
    parts = [st.get("cidade") or "", st.get("uf") or ""]
    end = st.get("endereco") or ""
    city = " ".join(p for p in parts if p).strip()
    return end or city


def _region(o):
    for st in o.get("paradas") or []:
        if st.get("cidade"):
            return str(st.get("cidade")).strip()
    return o.get("fonte") or ""


def _progress(o):
    stops = o.get("paradas") or []
    if not stops:
        return "—"
    done = sum(1 for s in stops if s.get("status") in ("delivered", "skipped"))
    return f"{done}/{len(stops)}"


def _quick(o, delayed=False):
    st = o.get("status")
    if delayed and st in ("ready", "assigned", "confirmed"):
        return {"action": "reschedule", "label": "Reagendar"}
    if st == "draft":
        return {"action": "confirm", "label": "Confirmar"}
    if st == "confirmed":
        return {"action": "ready", "label": "Pronta"}
    if st == "waiting_stock":
        return {"action": "ready", "label": "Liberar"}
    if st == "ready" and not (o.get("motorista") or o.get("recurso_id")):
        return {"action": "assign", "label": "Atribuir"}
    if st == "ready":
        return {"action": "dispatch", "label": "Despachar"}
    if st == "assigned":
        return {"action": "depart", "label": "Sair"}
    if st == "in_transit":
        return {"action": "deliver", "label": "Entregar"}
    if st == "delivered":
        return {"action": "complete", "label": "Concluir"}
    return None


def _category_of(o, today, delayed, failed_track, rejected_pod):
    if delayed or failed_track or rejected_pod:
        return "exceptions"
    st = o.get("status")
    if st == "waiting_stock":
        return "waiting_stock"
    if st == "ready" and not (o.get("motorista") or o.get("recurso_id")):
        return "waiting_assignment"
    if st == "ready":
        return "ready"
    if st == "in_transit":
        return "in_transit"
    if _completed_today(o, today):
        return "completed_today"
    if _date_only(o.get("data_agendada")) == today and st not in ("cancelled",):
        return "scheduled_today"
    if st == "assigned":
        return "waiting_assignment"
    return "all_open"


def _enrich_row(o, *, today, disp_by_do, tracks_by_do, pods_by_do):
    delayed = _is_delayed(o, today)
    tr = tracks_by_do.get(o.get("id"))
    pods = pods_by_do.get(o.get("id") or "", [])
    rejected_pod = any(p.get("status") == "rejected" for p in pods)
    failed_track = bool(tr and tr.get("status") == "failed")
    cat = _category_of(o, today, delayed, failed_track, rejected_pod)
    prio = o.get("prioridade") or "normal"
    item = {
        "id": o.get("id"),
        "prioridade": prio,
        "prioridade_label": o.get("prioridade_label") or prio,
        "parceiro": o.get("parceiro"),
        "fonte": o.get("fonte"),
        "destino": _destination(o),
        "regiao": _region(o),
        "data_agendada": o.get("data_agendada"),
        "janela": o.get("janela"),
        "status": o.get("status"),
        "status_label": o.get("status_label"),
        "motorista": o.get("motorista") or "",
        "veiculo": o.get("veiculo") or "",
        "recurso_id": o.get("recurso_id") or "",
        "dispatch_id": disp_by_do.get(o.get("id")) or "",
        "progresso": _progress(o),
        "tracking_status": (tr or {}).get("status") or "",
        "tracking_status_label": (tr or {}).get("status_label") or "",
        "pod_pendente": any(p.get("status") in ("created", "waiting") for p in pods),
        "atrasada": delayed,
        "excecao": delayed or failed_track or rejected_pod,
        "categoria": cat,
        "categoria_label": CATEGORIES.get(cat, cat),
        "origem_ref": o.get("origem_ref") or "",
        "criado_em": o.get("criado_em") or "",
        "acoes": o.get("acoes") or [],
        "urgente": delayed or prio in ("emergency", "high"),
    }
    q = _quick(o, delayed=delayed)
    if q:
        item["acao_rapida"] = q
    return item


def _sort_key(row):
    return (
        0 if row.get("excecao") else 1,
        PRIO_RANK.get(row.get("prioridade") or "normal", 9),
        0 if row.get("atrasada") else 1,
        row.get("data_agendada") or "9999",
        row.get("janela") or "",
        row.get("criado_em") or "",
        row.get("id") or "",
    )


def queue(
    categoria=None,
    fonte=None,
    status=None,
    prioridade=None,
    motorista=None,
    q=None,
    regiao=None,
):
    today = _today()
    orders = delivery_orders.list_orders(fonte=fonte).get("orders") or []
    dispatches = delivery_dispatch.list_dispatches(fonte=fonte).get("dispatches") or []
    tracks = delivery_tracking.list_tracks(fonte=fonte).get("tracks") or []
    pods = delivery_pod.list_pods().get("pods") or []

    disp_by_do = {}
    for d in dispatches:
        if d.get("status") in ("cancelled", "closed"):
            continue
        for eid in d.get("entrega_ids") or []:
            disp_by_do[eid] = d.get("id")

    tracks_by_do = {t.get("entrega_id"): t for t in tracks if t.get("entrega_id")}
    pods_by_do = {}
    for p in pods:
        pods_by_do.setdefault(p.get("entrega_id"), []).append(p)

    rows = [
        _enrich_row(
            o, today=today, disp_by_do=disp_by_do,
            tracks_by_do=tracks_by_do, pods_by_do=pods_by_do,
        )
        for o in orders
    ]

    # contadores por categoria (antes do filtro de categoria)
    counts = {k: 0 for k in CATEGORIES}
    for r in rows:
        c = r.get("categoria")
        if c in counts and c != "all_open":
            counts[c] += 1
        if r.get("status") not in ("completed", "cancelled"):
            counts["all_open"] += 1

    cat = str(categoria or "").strip().lower() or None
    if cat and cat in CATEGORIES:
        if cat == "all_open":
            rows = [r for r in rows if r.get("status") not in ("completed", "cancelled")]
        elif cat == "scheduled_today":
            rows = [
                r for r in rows
                if _date_only(r.get("data_agendada")) == today
                and r.get("status") not in ("cancelled",)
            ]
        elif cat == "completed_today":
            # recompute from orders for accuracy
            rows = [r for r in rows if r.get("categoria") == "completed_today"]
        else:
            rows = [r for r in rows if r.get("categoria") == cat]

    if status:
        rows = [r for r in rows if r.get("status") == status]
    if prioridade:
        rows = [r for r in rows if r.get("prioridade") == prioridade]
    if motorista:
        mk = str(motorista).strip().lower()
        rows = [
            r for r in rows
            if mk in str(r.get("motorista") or "").lower()
            or mk in str(r.get("recurso_id") or "").lower()
        ]
    if regiao:
        rk = str(regiao).strip().lower()
        rows = [r for r in rows if rk in str(r.get("regiao") or "").lower()]
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("parceiro") or "").lower()
            or qq in str(r.get("motorista") or "").lower()
            or qq in str(r.get("destino") or "").lower()
            or qq in str(r.get("origem_ref") or "").lower()
        ]

    rows.sort(key=_sort_key)

    fontes = sorted({
        str(o.get("fonte") or "").upper()
        for o in delivery_orders.list_orders().get("orders") or []
        if o.get("fonte")
    })
    if "DC-01" not in fontes:
        fontes.insert(0, "DC-01")

    return {
        "gerado_em": _now().isoformat(timespec="seconds"),
        "categoria": cat or "all_open",
        "categorias": [
            {"id": k, "label": v, "count": counts.get(k, 0)}
            for k, v in CATEGORIES.items()
        ],
        "items": rows,
        "filtrado": len(rows),
        "total_aberto": counts.get("all_open", 0),
        "fontes": fontes,
        "meta": meta(),
    }


def action(entrega_id, action, usuario="", **extra):
    """Ações da fila — delega aos módulos Core."""
    act = str(action or "").strip().lower()
    eid = str(entrega_id or "").strip()
    if not eid or not act:
        raise ValueError("entrega_id e action obrigatórios")

    if act == "priority" or act == "set_priority":
        return {
            "action": "priority",
            "order": delivery_orders.set_priority(
                eid, extra.get("prioridade") or extra.get("priority"), usuario=usuario,
            ),
        }

    if act in ("confirm", "ready", "wait_stock", "assign", "depart", "deliver", "complete", "cancel"):
        kwargs = {}
        if act == "assign":
            kwargs["motorista"] = extra.get("motorista") or "Carlos Motorista"
            kwargs["veiculo"] = extra.get("veiculo") or "ABC1D23"
            kwargs["recurso_id"] = extra.get("recurso_id") or "DRV-01"
        if act == "cancel":
            if not str(extra.get("motivo") or "").strip():
                raise ValueError("motivo obrigatório")
        row = delivery_orders.transition(
            eid, act, usuario=usuario, motivo=extra.get("motivo") or "", **kwargs,
        )
        return {"action": act, "order": row}

    if act == "dispatch":
        # cria lote aberto com esta DO (ou adiciona a lote existente)
        ds_id = str(extra.get("dispatch_id") or "").strip()
        order = delivery_orders.get_order(eid)
        if not order:
            raise ValueError("entrega não encontrada")
        if ds_id:
            row = delivery_dispatch.add_entregas(ds_id, [eid], usuario=usuario)
            return {"action": "dispatch", "dispatch": row, "order": order}
        row = delivery_dispatch.create_dispatch({
            "fonte": order.get("fonte") or "DC-01",
            "data": order.get("data_agendada") or _today(),
            "entrega_ids": [eid],
            "recurso_id": order.get("recurso_id") or extra.get("recurso_id") or "",
            "motorista": order.get("motorista") or extra.get("motorista") or "",
            "veiculo": order.get("veiculo") or extra.get("veiculo") or "",
            "prioridade": order.get("prioridade") or "normal",
        }, usuario=usuario)
        return {"action": "dispatch", "dispatch": row, "order": order}

    if act == "reschedule":
        slot_id = str(extra.get("slot_id") or extra.get("novo_slot_id") or "").strip()
        if not slot_id:
            # pega primeiro slot aberto da fonte
            order = delivery_orders.get_order(eid)
            avail = delivery_scheduling.availability(
                fonte=(order or {}).get("fonte"),
                data_de=_today(),
            ).get("slots") or []
            if not avail:
                raise ValueError("nenhum slot disponível — crie na Agenda")
            slot_id = avail[0]["id"]
        row = delivery_scheduling.reschedule(
            eid, slot_id, usuario=usuario,
            motivo=extra.get("motivo") or "reagendamento pela fila",
        )
        return {"action": "reschedule", "slot": row, "order": delivery_orders.get_order(eid)}

    raise ValueError(f"ação inválida: {act}")
