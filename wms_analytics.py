"""
WMS — Warehouse Analytics (RFC-9009 MVP).

Camada read-only: agrega dados dos módulos WMS existentes.
Não altera estoque, operações, tarefas ou documentos.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

import wms_locations
import wms_operations
import wms_picking
import wms_receiving
import wms_shipping
import wms_tasks
import wms_warehouses


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _count_by(rows, field="status"):
    return dict(Counter(str(r.get(field) or "") for r in rows))


def _pct(num, den):
    if not den:
        return None
    return round(100.0 * float(num) / float(den), 1)


def _filter_armazem(rows, armazem):
    if not armazem:
        return list(rows)
    ak = str(armazem).strip().upper()
    return [r for r in rows if str(r.get("armazem") or "").upper() == ak]


def dashboard(armazem=None):
    """Visão executiva + blocos por processo."""
    wh_out = wms_warehouses.list_armazens(ativos=True)
    loc_out = wms_locations.list_localizacoes(armazem=armazem)
    ops = _filter_armazem(wms_operations.list_operacoes().get("operacoes") or [], armazem)
    tasks = _filter_armazem(wms_tasks.list_tarefas().get("tarefas") or [], armazem)
    picks = _filter_armazem(wms_picking.list_pick_lists().get("pick_lists") or [], armazem)
    pkgs = wms_picking.list_packages().get("packages") or []
    recs = _filter_armazem(wms_receiving.list_recebimentos().get("recebimentos") or [], armazem)
    ships = _filter_armazem(wms_shipping.list_expedicoes().get("expedicoes") or [], armazem)

    if armazem:
        # packages don't always carry armazem — keep those linked to filtered picks
        pick_ids = {p.get("id") for p in picks}
        pkgs = [p for p in pkgs if p.get("pick_list_id") in pick_ids]

    locs = loc_out.get("localizacoes") or []
    loc_status = _count_by(locs, "status")
    available = loc_status.get("available", 0) + loc_status.get("disponivel", 0)
    occupiedish = sum(
        v for k, v in loc_status.items()
        if k and k not in ("available", "disponivel", "empty", "vazio")
    )
    util_den = len(locs) or 0
    utilization = _pct(occupiedish or (util_den - available), util_den) if util_den else None

    # Receiving accuracy
    rec_exp = rec_recv = 0.0
    for r in recs:
        for ln in r.get("linhas") or []:
            rec_exp += float(ln.get("qtd_esperada") or 0)
            rec_recv += float(ln.get("qtd_recebida") or 0)
    rec_open = [r for r in recs if r.get("status") not in ("completed", "cancelled")]
    rec_done = [r for r in recs if r.get("status") == "completed"]

    # Picking
    pick_open = [p for p in picks if p.get("status") not in ("closed", "cancelled")]
    pick_lines = sum(int(p.get("linhas_count") or len(p.get("linhas") or [])) for p in picks)
    pick_pending = sum(int(p.get("pendentes") or 0) for p in picks)
    pick_accuracy = _pct(pick_lines - pick_pending, pick_lines) if pick_lines else None

    # Shipping fulfillment
    ship_total = len(ships)
    ship_out = len([s for s in ships if s.get("status") in ("dispatched", "completed")])
    ship_pending = [s for s in ships if s.get("status") not in ("completed", "cancelled", "dispatched")]

    # Ops / tasks pending
    op_terminal = {"closed", "cancelled", "completed"}
    task_terminal = {"closed", "cancelled", "completed", "validated"}  # pending = others
    ops_pending = [o for o in ops if o.get("status") not in op_terminal]
    tasks_pending = [t for t in tasks if t.get("status") not in task_terminal]
    tasks_by_op = _count_by(tasks, "operador") if tasks else {}

    # Exceptions heuristic
    exceptions = []
    for r in recs:
        if (r.get("divergencias") or 0) > 0 or (r.get("rejeitadas") or 0) > 0:
            exceptions.append({
                "tipo": "recebimento",
                "id": r.get("id"),
                "nota": f"{r.get('divergencias') or 0} diverg. / {r.get('rejeitadas') or 0} rej.",
                "status": r.get("status"),
            })
    for s in ships:
        if (s.get("faltas") or 0) > 0:
            exceptions.append({
                "tipo": "expedicao",
                "id": s.get("id"),
                "nota": f"{s.get('faltas')} falta(s)",
                "status": s.get("status"),
            })
    for loc in locs:
        if loc.get("status") in ("blocked", "bloqueado", "damaged"):
            exceptions.append({
                "tipo": "localizacao",
                "id": loc.get("codigo"),
                "nota": loc.get("status_label") or loc.get("status"),
                "status": loc.get("status"),
            })

    overview = {
        "armazens": len(wh_out.get("armazens") or []) if not armazem else 1,
        "localizacoes": len(locs),
        "operacoes_pendentes": len(ops_pending),
        "tarefas_pendentes": len(tasks_pending),
        "recebimentos_abertos": len(rec_open),
        "expedicoes_abertas": len(ship_pending),
        "picking_abertos": len(pick_open),
        "volumes": len(pkgs),
        "excecoes": len(exceptions),
        "utilizacao_pct": utilization,
        "inbound_itens": round(rec_recv, 2),
        "outbound_despachados": ship_out,
    }

    return {
        "gerado_em": _now(),
        "armazem": (str(armazem).strip().upper() if armazem else None),
        "overview": overview,
        "recebimento": {
            "total": len(recs),
            "abertos": len(rec_open),
            "concluidos": len(rec_done),
            "por_status": _count_by(recs),
            "qtd_esperada": round(rec_exp, 2),
            "qtd_recebida": round(rec_recv, 2),
            "acuracia_pct": _pct(rec_recv, rec_exp) if rec_exp else None,
        },
        "picking": {
            "total": len(picks),
            "abertos": len(pick_open),
            "por_status": _count_by(picks),
            "linhas": pick_lines,
            "pendentes": pick_pending,
            "acuracia_pct": pick_accuracy,
            "volumes": {
                "total": len(pkgs),
                "por_status": _count_by(pkgs),
            },
        },
        "expedicao": {
            "total": ship_total,
            "abertas": len(ship_pending),
            "despachadas": ship_out,
            "por_status": _count_by(ships),
            "fulfillment_pct": _pct(ship_out, ship_total) if ship_total else None,
        },
        "operacoes": {
            "total": len(ops),
            "pendentes": len(ops_pending),
            "por_status": _count_by(ops),
            "por_tipo": _count_by(ops, "tipo"),
        },
        "tarefas": {
            "total": len(tasks),
            "pendentes": len(tasks_pending),
            "por_status": _count_by(tasks),
            "por_operador": tasks_by_op,
        },
        "utilizacao": {
            "localizacoes": len(locs),
            "por_status": loc_status,
            "por_tipo": _count_by(locs, "tipo"),
            "utilizacao_pct": utilization,
        },
        "excecoes": exceptions[:50],
    }


def meta():
    return {
        "read_only": True,
        "fontes": [
            "armazens", "localizacoes", "operacoes", "tarefas",
            "picking", "packages", "recebimentos", "expedicoes",
        ],
        "gerado_em": _now(),
    }
