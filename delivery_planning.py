"""
Delivery — Planning Board (RFC-18103 MVP).

Quadro de planejamento: DO × recurso × janela / zona / despacho.
Muda atribuição operacional — não altera venda, não move estoque.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

import delivery_dispatch
import delivery_orders
import delivery_resources
import delivery_scheduling

MODES = {
    "driver": "Motoristas",
    "vehicle": "Veículos",
    "dispatch": "Despachos",
    "window": "Janelas",
    "zone": "Zonas",
}

PLAN_STATUSES = frozenset({
    "draft", "confirmed", "waiting_stock", "ready", "assigned",
})

CAPACITY_DEFAULT = 8  # entregas/dia por motorista (MVP)


def _now():
    return datetime.now()


def _today():
    return _now().strftime("%Y-%m-%d")


def _date_only(val):
    s = str(val or "").strip()
    return s[:10] if s else ""


def meta():
    return {
        "modes": [{"id": k, "label": v} for k, v in MODES.items()],
        "capacidade_padrao": CAPACITY_DEFAULT,
        "refresh_seconds": 45,
        "nota": "Planning precede execução — não muda pedido comercial.",
    }


def _slim(o):
    stops = o.get("paradas") or []
    dest = ""
    zona = ""
    if stops:
        dest = stops[0].get("endereco") or ""
        zona = stops[0].get("cidade") or o.get("fonte") or ""
    return {
        "id": o.get("id"),
        "parceiro": o.get("parceiro"),
        "fonte": o.get("fonte"),
        "status": o.get("status"),
        "status_label": o.get("status_label"),
        "prioridade": o.get("prioridade") or "normal",
        "prioridade_label": o.get("prioridade_label") or "Normal",
        "data_agendada": o.get("data_agendada"),
        "janela": o.get("janela") or "",
        "slot_id": o.get("slot_id") or "",
        "motorista": o.get("motorista") or "",
        "veiculo": o.get("veiculo") or "",
        "recurso_id": o.get("recurso_id") or "",
        "destino": dest,
        "zona": zona,
        "paradas_count": o.get("paradas_count") or len(stops),
    }


def _is_unassigned(o):
    return not (o.get("motorista") or o.get("recurso_id"))


def _for_day(orders, data):
    day = _date_only(data) or _today()
    out = []
    for o in orders:
        if o.get("status") in ("completed", "cancelled", "delivered"):
            continue
        if o.get("status") not in PLAN_STATUSES and o.get("status") != "in_transit":
            # só planeja pipeline + assigned
            if o.get("status") != "in_transit":
                continue
        d = _date_only(o.get("data_agendada"))
        if d and d != day:
            # inclui sem data (planejar hoje) ou atrasadas
            if d > day:
                continue
        out.append(o)
    return out


def board(mode="driver", fonte=None, data=None):
    """Retorna colunas do planning board."""
    mode_n = str(mode or "driver").strip().lower()
    if mode_n not in MODES:
        mode_n = "driver"
    day = _date_only(data) or _today()
    fk = str(fonte or "").strip().upper() or None

    orders = delivery_orders.list_orders(fonte=fk).get("orders") or []
    pool = [_slim(o) for o in _for_day(orders, day)]
    # full rows for actions need ids from pool
    by_id = {o.get("id"): o for o in orders}

    unassigned = [p for p in pool if _is_unassigned(p) and p.get("status") in PLAN_STATUSES]
    assigned_pool = [p for p in pool if not _is_unassigned(p) or p.get("status") == "in_transit"]

    columns = []

    if mode_n == "driver":
        drivers = [
            r for r in (delivery_resources.list_recursos().get("recursos") or [])
            if r.get("tipo") == "driver" and r.get("ativo", True)
        ]
        for r in drivers:
            nome = r.get("nome") or r.get("id")
            rid = r.get("id")
            items = [
                p for p in assigned_pool
                if str(p.get("recurso_id") or "") == str(rid)
                or str(p.get("motorista") or "").lower() == str(nome or "").lower()
            ]
            cap = int(r.get("capacidade") or 0) or CAPACITY_DEFAULT
            # capacidade 0 no seed driver means use default
            if r.get("tipo") == "driver" and not r.get("capacidade"):
                cap = CAPACITY_DEFAULT
            n = len(items)
            columns.append({
                "id": rid,
                "tipo": "driver",
                "titulo": nome,
                "subtitulo": r.get("status_label") or r.get("status"),
                "capacidade": cap,
                "carga": n,
                "utilizacao_pct": round(100.0 * n / cap, 1) if cap else None,
                "sobrecarga": n > cap,
                "items": items,
            })
        # motoristas soltos (nome sem recurso)
        known = {c["id"] for c in columns}
        known_names = {str(c["titulo"] or "").lower() for c in columns}
        orphans = defaultdict(list)
        for p in assigned_pool:
            if p.get("recurso_id") and p.get("recurso_id") in known:
                continue
            nome = (p.get("motorista") or "").strip()
            if nome and nome.lower() not in known_names:
                orphans[nome].append(p)
        for nome, items in sorted(orphans.items()):
            columns.append({
                "id": f"name:{nome}",
                "tipo": "driver",
                "titulo": nome,
                "subtitulo": "sem cadastro",
                "capacidade": CAPACITY_DEFAULT,
                "carga": len(items),
                "utilizacao_pct": round(100.0 * len(items) / CAPACITY_DEFAULT, 1),
                "sobrecarga": len(items) > CAPACITY_DEFAULT,
                "items": items,
            })

    elif mode_n == "vehicle":
        vehicles = [
            r for r in (delivery_resources.list_recursos().get("recursos") or [])
            if r.get("tipo") == "vehicle" and r.get("ativo", True)
        ]
        for r in vehicles:
            placa = r.get("placa") or r.get("nome") or r.get("id")
            items = [
                p for p in assigned_pool
                if str(p.get("veiculo") or "").upper() == str(placa or "").upper()
                or str(p.get("veiculo") or "").lower() == str(r.get("nome") or "").lower()
            ]
            cap = int(r.get("capacidade") or 0) or CAPACITY_DEFAULT
            # capacidade em kg no seed — use count default for board
            if cap > 50:
                cap = CAPACITY_DEFAULT
            n = len(items)
            columns.append({
                "id": r.get("id"),
                "tipo": "vehicle",
                "titulo": r.get("nome") or placa,
                "subtitulo": placa,
                "capacidade": cap,
                "carga": n,
                "utilizacao_pct": round(100.0 * n / cap, 1) if cap else None,
                "sobrecarga": n > cap,
                "items": items,
            })

    elif mode_n == "dispatch":
        dispatches = delivery_dispatch.list_dispatches(fonte=fk, data=day).get("dispatches") or []
        if not dispatches:
            dispatches = [
                d for d in (delivery_dispatch.list_dispatches(fonte=fk).get("dispatches") or [])
                if d.get("status") in ("open", "planning", "assigned", "released", "in_progress")
                or _date_only(d.get("data")) == day
            ]
        used = set()
        for d in dispatches:
            items = []
            for eid in d.get("entrega_ids") or []:
                o = by_id.get(eid)
                if o:
                    items.append(_slim(o))
                    used.add(eid)
            columns.append({
                "id": d.get("id"),
                "tipo": "dispatch",
                "titulo": d.get("id"),
                "subtitulo": f"{d.get('status_label') or d.get('status')} · {d.get('motorista') or '—'}",
                "capacidade": CAPACITY_DEFAULT,
                "carga": len(items),
                "utilizacao_pct": round(100.0 * len(items) / CAPACITY_DEFAULT, 1),
                "sobrecarga": len(items) > CAPACITY_DEFAULT,
                "items": items,
                "status": d.get("status"),
            })
        # unassigned already excludes those with driver; also show not in any dispatch
        unassigned = [
            p for p in pool
            if p.get("id") not in used and p.get("status") in PLAN_STATUSES
        ]

    elif mode_n == "window":
        slots = delivery_scheduling.list_slots(fonte=fk, data=day).get("slots") or []
        by_janela = defaultdict(list)
        for p in pool:
            key = (p.get("janela") or "sem_janela").strip().lower() or "sem_janela"
            by_janela[key].append(p)
        # prefer known periods
        order_keys = ["manha", "tarde", "noite", "dia", "sem_janela"]
        keys = [k for k in order_keys if k in by_janela] + sorted(
            k for k in by_janela if k not in order_keys
        )
        slot_by_periodo = {s.get("periodo"): s for s in slots}
        for key in keys:
            items = by_janela[key]
            sl = slot_by_periodo.get(key)
            cap = int((sl or {}).get("capacidade") or 0) or CAPACITY_DEFAULT
            n = len(items)
            columns.append({
                "id": key,
                "tipo": "window",
                "titulo": (sl or {}).get("periodo_label") or key,
                "subtitulo": (
                    f"{(sl or {}).get('inicio') or ''}–{(sl or {}).get('fim') or ''}".strip("–")
                    or "sem slot"
                ),
                "capacidade": cap,
                "carga": n,
                "utilizacao_pct": round(100.0 * n / cap, 1) if cap else None,
                "sobrecarga": n > cap,
                "items": items,
                "slot_id": (sl or {}).get("id") or "",
            })
        unassigned = [p for p in pool if not (p.get("janela") or p.get("slot_id"))]

    else:  # zone
        by_zone = defaultdict(list)
        for p in pool:
            z = (p.get("zona") or p.get("fonte") or "Sem zona").strip() or "Sem zona"
            by_zone[z].append(p)
        for z, items in sorted(by_zone.items(), key=lambda x: (-len(x[1]), x[0])):
            n = len(items)
            columns.append({
                "id": z,
                "tipo": "zone",
                "titulo": z,
                "subtitulo": f"{n} entrega(s)",
                "capacidade": CAPACITY_DEFAULT,
                "carga": n,
                "utilizacao_pct": round(100.0 * n / CAPACITY_DEFAULT, 1),
                "sobrecarga": n > CAPACITY_DEFAULT,
                "items": items,
            })
        unassigned = [p for p in pool if not (p.get("zona") or "").strip()]

    balanced = not any(c.get("sobrecarga") for c in columns)
    overload = [c["titulo"] for c in columns if c.get("sobrecarga")]

    fontes = sorted({
        str(o.get("fonte") or "").upper()
        for o in delivery_orders.list_orders().get("orders") or []
        if o.get("fonte")
    })
    if "DC-01" not in fontes:
        fontes.insert(0, "DC-01")

    return {
        "gerado_em": _now().isoformat(timespec="seconds"),
        "mode": mode_n,
        "mode_label": MODES[mode_n],
        "data": day,
        "fonte": fk or "TODAS",
        "unassigned": unassigned,
        "unassigned_count": len(unassigned),
        "columns": columns,
        "resumo": {
            "nao_atribuidas": len(unassigned),
            "colunas": len(columns),
            "total_no_board": len(pool),
            "balanceado": balanced,
            "sobrecargas": overload,
        },
        "fontes": fontes,
        "meta": meta(),
    }


def move(entrega_id, mode, target_id, usuario="", **extra):
    """Move / atribui DO no board (simula drag-and-drop)."""
    mode_n = str(mode or "driver").strip().lower()
    eid = str(entrega_id or "").strip()
    tid = str(target_id or "").strip()
    if not eid:
        raise ValueError("entrega_id obrigatório")
    order = delivery_orders.get_order(eid)
    if not order:
        raise ValueError("entrega não encontrada")
    if order.get("status") in ("completed", "cancelled"):
        raise ValueError("entrega fechada")

    # unassign
    if tid in ("", "unassigned", "__unassigned__"):
        data = delivery_orders._load_raw()
        idx, row = delivery_orders._find(data, eid)
        if row is None:
            raise ValueError("entrega não encontrada")
        row["motorista"] = ""
        row["veiculo"] = ""
        row["recurso_id"] = ""
        row["atualizado_em"] = _now().isoformat(timespec="seconds")
        hist = list(row.get("historico") or [])
        hist.append(delivery_orders._hist(row.get("status"), usuario, "planning: desatribuído"))
        row["historico"] = hist
        # se estava assigned, volta para ready
        if row.get("status") == "assigned":
            row["status"] = "ready"
            hist.append(delivery_orders._hist("ready", usuario, "volta à fila"))
        data["orders"][idx] = row
        delivery_orders._save(data)
        return {"action": "unassign", "order": delivery_orders._enrich(row)}

    if mode_n == "driver":
        motorista = extra.get("motorista") or ""
        veiculo = extra.get("veiculo") or order.get("veiculo") or ""
        recurso_id = tid
        if tid.startswith("name:"):
            motorista = tid.split(":", 1)[1]
            recurso_id = ""
        else:
            rec = delivery_resources.get_recurso(tid)
            if not rec:
                raise ValueError("motorista/recurso não encontrado")
            motorista = motorista or rec.get("nome") or tid
            if not veiculo:
                # tenta veículo disponível
                vehs = [
                    r for r in (delivery_resources.list_recursos().get("recursos") or [])
                    if r.get("tipo") == "vehicle" and r.get("status") == "available"
                ]
                if vehs:
                    veiculo = vehs[0].get("placa") or vehs[0].get("nome") or ""
        st = order.get("status")
        if st == "ready":
            row = delivery_orders.transition(
                eid, "assign", usuario=usuario,
                motorista=motorista, veiculo=veiculo, recurso_id=recurso_id,
            )
        else:
            # patch assignment fields
            data = delivery_orders._load_raw()
            idx, row = delivery_orders._find(data, eid)
            row["motorista"] = motorista
            row["veiculo"] = veiculo
            row["recurso_id"] = recurso_id
            row["atualizado_em"] = _now().isoformat(timespec="seconds")
            hist = list(row.get("historico") or [])
            hist.append(delivery_orders._hist(
                row.get("status"), usuario, f"planning → {motorista}",
            ))
            row["historico"] = hist
            data["orders"][idx] = row
            delivery_orders._save(data)
            row = delivery_orders._enrich(row)
        return {"action": "assign_driver", "order": row}

    if mode_n == "vehicle":
        rec = delivery_resources.get_recurso(tid)
        if not rec:
            raise ValueError("veículo não encontrado")
        placa = rec.get("placa") or rec.get("nome") or tid
        data = delivery_orders._load_raw()
        idx, row = delivery_orders._find(data, eid)
        row["veiculo"] = placa
        row["atualizado_em"] = _now().isoformat(timespec="seconds")
        hist = list(row.get("historico") or [])
        hist.append(delivery_orders._hist(row.get("status"), usuario, f"planning veículo {placa}"))
        row["historico"] = hist
        data["orders"][idx] = row
        delivery_orders._save(data)
        return {"action": "assign_vehicle", "order": delivery_orders._enrich(row)}

    if mode_n == "dispatch":
        if tid.startswith("DS") or tid.startswith("ds"):
            row = delivery_dispatch.add_entregas(tid, [eid], usuario=usuario)
            return {"action": "add_dispatch", "dispatch": row, "order": delivery_orders.get_order(eid)}
        # create new
        row = delivery_dispatch.create_dispatch({
            "fonte": order.get("fonte") or "DC-01",
            "data": order.get("data_agendada") or _today(),
            "entrega_ids": [eid],
            "motorista": order.get("motorista") or "",
            "veiculo": order.get("veiculo") or "",
            "recurso_id": order.get("recurso_id") or "",
        }, usuario=usuario)
        return {"action": "create_dispatch", "dispatch": row, "order": order}

    if mode_n == "window":
        # set janela + optional reserve slot
        periodo = tid if tid != "sem_janela" else ""
        data = delivery_orders._load_raw()
        idx, row = delivery_orders._find(data, eid)
        row["janela"] = periodo
        if not row.get("data_agendada"):
            row["data_agendada"] = _today()
        row["atualizado_em"] = _now().isoformat(timespec="seconds")
        hist = list(row.get("historico") or [])
        hist.append(delivery_orders._hist(row.get("status"), usuario, f"planning janela {periodo or '—'}"))
        row["historico"] = hist
        data["orders"][idx] = row
        delivery_orders._save(data)
        # try reserve matching slot
        slots = delivery_scheduling.list_slots(
            fonte=order.get("fonte"), data=row.get("data_agendada") or _today(),
        ).get("slots") or []
        match = next((s for s in slots if s.get("periodo") == periodo and s.get("status") == "open"), None)
        if match and periodo:
            try:
                delivery_scheduling.reserve(
                    match["id"], eid, usuario=usuario, status="scheduled",
                    motivo="planning board",
                )
            except Exception:
                pass
        return {"action": "set_window", "order": delivery_orders.get_order(eid)}

    if mode_n == "zone":
        # only audit note — zona vem do endereço; não inventa geo
        data = delivery_orders._load_raw()
        idx, row = delivery_orders._find(data, eid)
        hist = list(row.get("historico") or [])
        hist.append(delivery_orders._hist(
            row.get("status"), usuario, f"planning zona ref {tid}",
        ))
        row["historico"] = hist
        row["atualizado_em"] = _now().isoformat(timespec="seconds")
        # opcional: atualiza cidade da 1ª parada se vazia
        if row.get("paradas") and tid and tid != "Sem zona":
            if not (row["paradas"][0].get("cidade") or "").strip():
                row["paradas"][0]["cidade"] = tid
        data["orders"][idx] = row
        delivery_orders._save(data)
        return {"action": "set_zone", "order": delivery_orders._enrich(row)}

    raise ValueError(f"mode inválido: {mode_n}")
