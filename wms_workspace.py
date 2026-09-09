"""
WMS — Warehouse Workspace (RFC-9010).

Cockpit conceitual: disposição de contexto, cards, filas, tarefas e exceções.
A execução detalhada permanece nas RFCs 9004–9008; aqui só visão + ação rápida.
"""

from __future__ import annotations

from datetime import datetime

import wms_analytics
import wms_operations
import wms_picking
import wms_receiving
import wms_shipping
import wms_tasks
import wms_warehouses
import wms_counting


def _now():
    return datetime.now().isoformat(timespec="seconds")


OP_PENDING = frozenset({"draft", "planned", "ready", "in_progress"})
TASK_PENDING = frozenset({"created", "assigned", "started", "executing"})
REC_PENDING = frozenset({
    "expected", "arrived", "unloading", "checking", "inspection", "putaway",
})
SHIP_PENDING = frozenset({
    "created", "planned", "picking", "checking", "packing", "loading", "dispatched",
})
PICK_PENDING = frozenset({
    "open", "picking", "picked", "packing", "packed", "ready_ship",
})
COUNT_PENDING = frozenset({
    "created", "counting", "review", "pending_approval", "approved",
})

# Tipos de operação usados nos cards de processo (RFC §7)
TIPO_TRANSFER = frozenset({"TRF-INT", "TRANSFER", "XDOCK"})
TIPO_REPAIR = frozenset({"REP-ENVIO", "REP-RETORNO", "REPAIR"})
URGENT_PRIO = frozenset({"urgent", "high"})


def _filter_arm(rows, armazem):
    if not armazem:
        return list(rows)
    ak = str(armazem).strip().upper()
    return [r for r in rows if str(r.get("armazem") or "").upper() == ak]


def _slim(row, *fields):
    out = {f: row.get(f) for f in fields}
    for extra in (
        "status_label", "origem_label", "destino_label", "tipo_label",
        "tipo_nome", "prioridade", "acoes", "loc_origem", "loc_destino", "qtd",
    ):
        if row.get(extra) is not None:
            out[extra] = row.get(extra)
    return out


def _shift_label(dt=None):
    h = (dt or datetime.now()).hour
    if 5 <= h < 13:
        return "Manhã"
    if 13 <= h < 21:
        return "Tarde"
    return "Noite"


def _quick_rec(r):
    st = r.get("status")
    if st == "expected":
        return {"action": "arrive", "label": "Chegada"}
    if st == "arrived":
        return {"action": "unload", "label": "Descarga"}
    if st == "unloading":
        return {"action": "start_check", "label": "Conferir"}
    return None


def _quick_ship(s):
    st = s.get("status")
    if st == "created":
        return {"action": "plan", "label": "Planejar"}
    if st == "planned":
        return {"action": "start_pick", "label": "Picking"}
    if st == "picking":
        return {"action": "start_check", "label": "Conferir"}
    return None


def _quick_task(t):
    st = t.get("status")
    if st == "created":
        return {"action": "assign", "label": "Atribuir"}
    if st == "assigned":
        return {"action": "start", "label": "Iniciar"}
    if st in ("started", "executing"):
        return {"action": "complete", "label": "Concluir"}
    return None


def _quick_op(o):
    st = o.get("status")
    if st == "draft":
        return {"action": "plan", "label": "Planejar"}
    if st == "planned":
        return {"action": "ready", "label": "Liberar"}
    if st == "ready":
        return {"action": "start", "label": "Iniciar"}
    return None


def _enrich_queue(items, kind):
    out = []
    for row in items:
        q = None
        if kind == "recebimento":
            base = _slim(row, "id", "documento_ref", "parceiro", "status", "armazem", "origem")
            q = _quick_rec(row)
        elif kind == "expedicao":
            base = _slim(row, "id", "documento_ref", "parceiro", "status", "armazem", "destino")
            q = _quick_ship(row)
        elif kind == "tarefa":
            base = _slim(
                row, "id", "tipo", "produto", "status", "operador",
                "operacao_id", "prioridade", "loc_origem", "loc_destino", "qtd",
            )
            q = _quick_task(row)
        else:
            base = _slim(row, "id", "tipo", "documento_ref", "status", "parceiro", "prioridade")
            q = _quick_op(row)
        base["kind"] = kind
        base["urgente"] = (
            row.get("prioridade") in URGENT_PRIO
            or row.get("status") in ("arrived", "loading", "assigned", "ready")
        )
        if q:
            base["acao_rapida"] = q
        out.append(base)
    return out


def workspace(armazem=None, operador=None, perfil=None):
    arms = wms_warehouses.list_armazens(ativos=True).get("armazens") or []
    if armazem:
        ak = str(armazem).strip().upper()
        if not any(str(a.get("codigo") or "").upper() == ak for a in arms):
            raise ValueError(f"armazém inválido: {ak}")
        wh = next(
            (a for a in arms if str(a.get("codigo") or "").upper() == ak),
            None,
        )
    else:
        ak = None
        wh = None

    ops = _filter_arm(wms_operations.list_operacoes().get("operacoes") or [], ak)
    tasks = _filter_arm(wms_tasks.list_tarefas().get("tarefas") or [], ak)
    picks = _filter_arm(wms_picking.list_pick_lists().get("pick_lists") or [], ak)
    counts = _filter_arm(wms_counting.list_sessoes().get("sessoes") or [], ak)
    recs = _filter_arm(wms_receiving.list_recebimentos().get("recebimentos") or [], ak)
    ships = _filter_arm(wms_shipping.list_expedicoes().get("expedicoes") or [], ak)

    op_name = str(operador or "").strip().lower()
    my_tasks = tasks
    if op_name:
        my_tasks = [
            t for t in tasks
            if op_name in str(t.get("operador") or "").lower()
            or op_name in str(t.get("responsavel") or "").lower()
            or not t.get("operador")  # disponíveis
        ]

    def _tipo_ops(tipos):
        return [
            o for o in ops
            if o.get("status") in OP_PENDING
            and str(o.get("tipo") or "").upper() in tipos
        ]

    rec_open = [r for r in recs if r.get("status") in REC_PENDING]
    ship_open = [s for s in ships if s.get("status") in SHIP_PENDING]
    pick_open = [p for p in picks if p.get("status") in PICK_PENDING]
    count_open = [c for c in counts if c.get("status") in COUNT_PENDING]
    op_open = [o for o in ops if o.get("status") in OP_PENDING]
    task_open = [t for t in tasks if t.get("status") in TASK_PENDING]
    trf_open = _tipo_ops(TIPO_TRANSFER)
    rep_open = _tipo_ops(TIPO_REPAIR)

    rec_urgent = sum(1 for r in rec_open if r.get("status") in ("arrived", "unloading"))
    ship_urgent = sum(1 for s in ship_open if s.get("status") in ("loading", "dispatched"))
    task_urgent = sum(
        1 for t in task_open
        if t.get("prioridade") in URGENT_PRIO or t.get("status") == "assigned"
    )
    op_urgent = sum(1 for o in op_open if o.get("prioridade") in URGENT_PRIO)

    cards = [
        {
            "id": "recebimento",
            "titulo": "Recebimento",
            "pendentes": len(rec_open),
            "urgentes": rec_urgent,
            "href": "wms-recebimento.html",
            "prioridade": "high" if rec_urgent else "normal",
        },
        {
            "id": "expedicao",
            "titulo": "Expedição",
            "pendentes": len(ship_open),
            "urgentes": ship_urgent,
            "href": "wms-expedicao.html",
            "prioridade": "high" if ship_urgent else "normal",
        },
        {
            "id": "picking",
            "titulo": "Picking",
            "pendentes": len(pick_open),
            "urgentes": sum(1 for p in pick_open if p.get("status") in ("open", "picking")),
            "href": "wms-picking.html",
            "prioridade": "normal",
        },
        {
            "id": "contagem",
            "titulo": "Contagem",
            "pendentes": len(count_open),
            "urgentes": sum(1 for c in count_open if c.get("status") in ("pending_approval", "review")),
            "href": "wms-contagem.html",
            "prioridade": "high" if any(c.get("status") == "pending_approval" for c in count_open) else "normal",
        },
        {
            "id": "transferencia",
            "titulo": "Transferência",
            "pendentes": len(trf_open),
            "urgentes": sum(1 for o in trf_open if o.get("prioridade") in URGENT_PRIO),
            "href": "wms-operacoes.html",
            "prioridade": "normal",
        },
        {
            "id": "reparo",
            "titulo": "Reparo",
            "pendentes": len(rep_open),
            "urgentes": 0,
            "href": "wms-operacoes.html",
            "prioridade": "low",
        },
        {
            "id": "tarefas",
            "titulo": "Minhas tarefas",
            "pendentes": len([t for t in my_tasks if t.get("status") in TASK_PENDING]),
            "urgentes": task_urgent,
            "href": "wms-tarefas.html",
            "prioridade": "high" if task_urgent else "normal",
        },
    ]

    fila_rec = sorted(
        rec_open,
        key=lambda r: (0 if r.get("status") == "arrived" else 1, r.get("id") or ""),
    )[:8]
    fila_ship = sorted(
        ship_open,
        key=lambda s: (0 if s.get("status") in ("loading", "dispatched") else 1, s.get("id") or ""),
    )[:8]
    fila_tasks = sorted(
        [t for t in my_tasks if t.get("status") in TASK_PENDING],
        key=lambda t: (
            0 if t.get("prioridade") in URGENT_PRIO else 1,
            0 if t.get("status") in ("assigned", "started", "executing") else 1,
            t.get("id") or "",
        ),
    )[:10]
    fila_ops = sorted(
        op_open,
        key=lambda o: (
            0 if o.get("prioridade") in URGENT_PRIO else 1,
            o.get("id") or "",
        ),
    )[:8]

    # Tarefa atual = primeira em execução / atribuída
    current = None
    for t in fila_tasks:
        if t.get("status") in ("started", "executing", "assigned"):
            current = t
            break
    if current is None and fila_tasks:
        current = fila_tasks[0]

    dash = wms_analytics.dashboard(armazem=ak)
    exceptions = dash.get("excecoes") or []
    overview = dash.get("overview") or {}

    notifications = []
    if exceptions:
        notifications.append({
            "tipo": "excecao",
            "texto": f"{len(exceptions)} exceção(ões)",
            "nivel": "warn",
        })
    if rec_urgent:
        notifications.append({
            "tipo": "recebimento",
            "texto": f"{rec_urgent} recebimento(s) na doca",
            "nivel": "info",
        })
    if ship_urgent:
        notifications.append({
            "tipo": "expedicao",
            "texto": f"{ship_urgent} expedição(ões) em carga",
            "nivel": "info",
        })
    if op_urgent:
        notifications.append({
            "tipo": "operacao",
            "texto": f"{op_urgent} operação(ões) prioritárias",
            "nivel": "warn",
        })

    perfil_n = str(perfil or "").strip().lower()
    if perfil_n not in ("operador", "supervisor", "gerente"):
        # heurística leve
        if op_name and not exceptions:
            perfil_n = "operador"
        else:
            perfil_n = "supervisor"

    layout = {
        "mostrar_cards": True,
        "mostrar_filas": perfil_n != "operador",
        "mostrar_tarefa_atual": True,
        "mostrar_excecoes": perfil_n != "operador",
        "mostrar_analytics_chip": perfil_n in ("supervisor", "gerente"),
        "enfatizar_tarefas": perfil_n == "operador",
    }

    atalhos = [
        {"label": "Recebimento", "href": "wms-recebimento.html"},
        {"label": "Expedição", "href": "wms-expedicao.html"},
        {"label": "Picking", "href": "wms-picking.html"},
        {"label": "Contagem", "href": "wms-contagem.html"},
        {"label": "Tarefas", "href": "wms-tarefas.html"},
        {"label": "Operações", "href": "wms-operacoes.html"},
    ]
    if layout["mostrar_analytics_chip"]:
        atalhos.append({"label": "Analytics", "href": "wms-analytics.html"})

    current_task = None
    if current:
        current_task = _enrich_queue([current], "tarefa")[0]
        current_task["href"] = "wms-tarefas.html"

    return {
        "gerado_em": _now(),
        "armazem": ak,
        "contexto": {
            "armazem_codigo": ak or (arms[0].get("codigo") if arms else None),
            "armazem_nome": (wh or {}).get("nome") or (
                "Todos os armazéns" if not ak else ak
            ),
            "turno": _shift_label(),
            "data": datetime.now().strftime("%d/%m/%Y"),
            "hora": datetime.now().strftime("%H:%M"),
        },
        "armazens": [
            {
                "codigo": a.get("codigo"),
                "nome": a.get("nome"),
                "tipo": a.get("tipo"),
                "tipo_label": a.get("tipo_label"),
            }
            for a in arms
        ],
        "perfil": perfil_n,
        "layout": layout,
        "notificacoes": notifications,
        "overview": overview,
        "cards": cards,
        "filas": {
            "recebimentos": _enrich_queue(fila_rec, "recebimento"),
            "expedicoes": _enrich_queue(fila_ship, "expedicao"),
            "operacoes": _enrich_queue(fila_ops, "operacao"),
            "minhas_tarefas": _enrich_queue(fila_tasks, "tarefa"),
        },
        "tarefa_atual": current_task,
        "excecoes": exceptions[:20],
        "atalhos": atalhos,
        "operador": op_name or None,
    }


def quick_action(kind, item_id, action, usuario="", operador=""):
    """Executa a próxima ação operacional a partir do cockpit."""
    kind = str(kind or "").strip().lower()
    action = str(action or "").strip().lower()
    item_id = str(item_id or "").strip()
    if not kind or not action or not item_id:
        raise ValueError("kind, id e action obrigatórios")

    if kind in ("recebimento", "receiving"):
        row = wms_receiving.transition(item_id, action, usuario=usuario)
        return {"kind": "recebimento", "item": row}

    if kind in ("expedicao", "shipping"):
        row = wms_shipping.transition(item_id, action, usuario=usuario)
        return {"kind": "expedicao", "item": row}

    if kind in ("tarefa", "task"):
        row = wms_tasks.transition(
            item_id,
            action,
            usuario=usuario,
            operador=operador or usuario,
        )
        return {"kind": "tarefa", "item": row}

    if kind in ("operacao", "operation"):
        row = wms_operations.transition(item_id, action, usuario=usuario)
        return {"kind": "operacao", "item": row}

    raise ValueError("kind inválido: use recebimento, expedicao, tarefa ou operacao")


def meta():
    return {
        "entry_point": True,
        "conceitual": True,
        "secoes": [
            "contexto", "notificacoes", "cards", "filas",
            "tarefa_atual", "excecoes", "atalhos",
        ],
        "paginas": [
            "wms-workspace.html",
            "wms-analytics.html",
            "wms-recebimento.html",
            "wms-expedicao.html",
            "wms-picking.html",
            "wms-contagem.html",
            "wms-operacoes.html",
            "wms-tarefas.html",
        ],
        "gerado_em": _now(),
    }
