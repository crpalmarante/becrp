"""
WMS — Warehouse Tasks (RFC-9005 MVP).

Unidades executáveis geradas a partir de operações.
Fonte: dados/wms_tasks.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import wms_operations
import wms_warehouses

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_tasks.json")

TASK_TYPES = {
    "picking": "Picking",
    "putaway": "Put Away",
    "move": "Movimentação Interna",
    "counting": "Contagem",
    "packing": "Packing",
    "loading": "Carregamento",
}

STATUSES = {
    "created": "Criada",
    "assigned": "Atribuída",
    "started": "Iniciada",
    "executing": "Em execução",
    "completed": "Concluída",
    "validated": "Validada",
    "closed": "Fechada",
    "cancelled": "Cancelada",
}

PRIORITIES = {
    "urgent": "Urgente",
    "high": "Alta",
    "normal": "Normal",
    "low": "Baixa",
}

TRANSITIONS = {
    ("created", "assign"): "assigned",
    ("created", "cancel"): "cancelled",
    ("assigned", "start"): "started",
    ("assigned", "cancel"): "cancelled",
    ("started", "execute"): "executing",
    ("started", "complete"): "completed",  # atalho
    ("started", "cancel"): "cancelled",
    ("executing", "complete"): "completed",
    ("executing", "cancel"): "cancelled",
    ("completed", "validate"): "validated",
    ("validated", "close"): "closed",
}

# workflow step (RFC-9003) → task type
WORKFLOW_MAP = {
    "pick": "picking",
    "picking": "picking",
    "receive": "putaway",
    "putaway": "putaway",
    "inspect": "counting",
    "count": "counting",
    "adjust": "counting",
    "pack": "packing",
    "packing": "packing",
    "ship": "loading",
    "loading": "loading",
    "transit": "move",
    "move": "move",
    "return": "move",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return ensure_seed()
    if not isinstance(data.get("tarefas"), list):
        data["tarefas"] = []
    if data.get("seq") is None:
        data["seq"] = len(data["tarefas"])
    if not data["tarefas"]:
        return ensure_seed()
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("tarefas") or [])
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
    day = datetime.now().strftime("%Y%m%d")
    return f"TK-{day}-{seq:04d}"


def _norm_tipo(val):
    s = str(val or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "pick": "picking",
        "separacao": "picking",
        "separação": "picking",
        "put_away": "putaway",
        "armazenagem": "putaway",
        "movimentacao": "move",
        "movimentação": "move",
        "contagem": "counting",
        "inventario": "counting",
        "inventário": "counting",
        "embalagem": "packing",
        "carregamento": "loading",
        "expedicao": "loading",
        "expedição": "loading",
    }
    s = aliases.get(s, s)
    if s not in TASK_TYPES:
        raise ValueError(
            "tipo deve ser: picking, putaway, move, counting, packing ou loading"
        )
    return s


def _norm_priority(val):
    s = str(val or "").strip().lower()
    aliases = {"urgente": "urgent", "alta": "high", "baixa": "low", "media": "normal", "média": "normal"}
    s = aliases.get(s, s) or "normal"
    if s not in PRIORITIES:
        raise ValueError("prioridade deve ser: urgent, high, normal ou low")
    return s


def _norm_status(val):
    s = str(val or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "criada": "created",
        "atribuida": "assigned",
        "atribuída": "assigned",
        "iniciada": "started",
        "em_execucao": "executing",
        "em_execução": "executing",
        "concluida": "completed",
        "concluída": "completed",
        "validada": "validated",
        "fechada": "closed",
        "cancelada": "cancelled",
    }
    s = aliases.get(s, s)
    if s not in STATUSES:
        raise ValueError("status inválido")
    return s


def ensure_seed():
    wms_operations.ensure_seed()
    now = _now()
    rows = [
        {
            "id": "TK-SEED-0001",
            "operacao_id": "OP-SEED-0002",
            "tipo": "picking",
            "armazem": "DC-01",
            "produto_id": "1",
            "produto": "Produto demo",
            "qtd": 2,
            "qtd_feita": 0,
            "loc_origem": "PCK-01",
            "loc_destino": "SHP-STAGE",
            "prioridade": "high",
            "status": "assigned",
            "operador": "bruno",
            "workflow_step": "pick",
            "observacao": "Seed — picking da expedição demo",
            "historico": [
                _hist("created", "seed", "gerada"),
                _hist("assigned", "seed", "bruno"),
            ],
            "cancelamento_motivo": "",
            "origem": "seed",
            "criado_em": now,
            "atualizado_em": now,
        },
        {
            "id": "TK-SEED-0002",
            "operacao_id": "OP-SEED-0002",
            "tipo": "packing",
            "armazem": "DC-01",
            "produto_id": "1",
            "produto": "Produto demo",
            "qtd": 2,
            "qtd_feita": 0,
            "loc_origem": "SHP-STAGE",
            "loc_destino": "SHP-STAGE",
            "prioridade": "high",
            "status": "created",
            "operador": "",
            "workflow_step": "pack",
            "observacao": "Seed — packing aguardando atribuição",
            "historico": [_hist("created", "seed", "gerada")],
            "cancelamento_motivo": "",
            "origem": "seed",
            "criado_em": now,
            "atualizado_em": now,
        },
    ]
    data = {"seq": 2, "atualizado_em": now, "tarefas": rows, "total": len(rows)}
    _save(data)
    return data


def _enrich(row):
    out = dict(row)
    out["tipo_label"] = TASK_TYPES.get(out.get("tipo"), out.get("tipo") or "")
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    out["prioridade_label"] = PRIORITIES.get(out.get("prioridade"), out.get("prioridade") or "")
    op = wms_operations.get_operacao(out.get("operacao_id")) if out.get("operacao_id") else None
    out["operacao_tipo"] = (op or {}).get("tipo") or ""
    out["operacao_doc"] = (op or {}).get("documento_ref") or ""
    wh = wms_warehouses.get_armazem(out.get("armazem"))
    out["armazem_nome"] = (wh or {}).get("nome") or ""
    st = out.get("status")
    out["acoes"] = [a for (from_st, a), _to in TRANSITIONS.items() if from_st == st]
    out["pode_editar"] = st in ("created", "assigned")
    return out


def _build_row(payload, existing=None, task_id=None, usuario=""):
    body = payload if isinstance(payload, dict) else {}
    tid = str(task_id or (existing or {}).get("id") or "").strip().upper()
    if not tid:
        raise ValueError("id obrigatório")

    tipo = _norm_tipo(
        body.get("tipo") if body.get("tipo") is not None else (existing or {}).get("tipo") or "move"
    )
    prioridade = _norm_priority(
        body.get("prioridade")
        if body.get("prioridade") is not None
        else (existing or {}).get("prioridade")
        or "normal"
    )

    operacao_id = str(
        body.get("operacao_id")
        if body.get("operacao_id") is not None
        else (existing or {}).get("operacao_id")
        or ""
    ).strip().upper()

    armazem = str(
        body.get("armazem")
        if body.get("armazem") is not None
        else (existing or {}).get("armazem")
        or ""
    ).strip().upper()

    if operacao_id:
        op = wms_operations.get_operacao(operacao_id)
        if not op:
            raise ValueError(f"operação não encontrada: {operacao_id}")
        if not armazem:
            armazem = str(op.get("armazem") or "").upper()
        if "prioridade" not in body and not existing:
            prioridade = _norm_priority(op.get("prioridade") or "normal")

    if not armazem:
        raise ValueError("armazém obrigatório")
    if not wms_warehouses.get_armazem(armazem):
        raise ValueError(f"armazém não encontrado: {armazem}")

    def _field(key, default=""):
        if key in body:
            return str(body.get(key) or "").strip()
        return str((existing or {}).get(key) or default).strip()

    try:
        qtd = float(
            body.get("qtd")
            if body.get("qtd") is not None
            else (existing or {}).get("qtd")
            or 0
        )
    except (TypeError, ValueError):
        raise ValueError("qtd deve ser número") from None
    if qtd < 0:
        raise ValueError("qtd não pode ser negativa")

    if "qtd_feita" in body:
        try:
            qtd_feita = float(body.get("qtd_feita") or 0)
        except (TypeError, ValueError):
            raise ValueError("qtd_feita deve ser número") from None
    else:
        qtd_feita = float((existing or {}).get("qtd_feita") or 0)
    if qtd_feita < 0:
        raise ValueError("qtd_feita não pode ser negativa")

    status = (existing or {}).get("status") or "created"
    historico = list((existing or {}).get("historico") or [])
    if not existing:
        historico = [_hist("created", usuario, "criação")]

    return {
        "id": tid,
        "operacao_id": operacao_id,
        "tipo": tipo,
        "armazem": armazem,
        "produto_id": _field("produto_id"),
        "produto": _field("produto") or _field("produto_id") or "item",
        "qtd": qtd,
        "qtd_feita": qtd_feita,
        "loc_origem": _field("loc_origem").upper(),
        "loc_destino": _field("loc_destino").upper(),
        "prioridade": prioridade,
        "status": status,
        "operador": _field("operador"),
        "workflow_step": _field("workflow_step"),
        "observacao": _field("observacao"),
        "historico": historico,
        "cancelamento_motivo": (existing or {}).get("cancelamento_motivo") or "",
        "origem": (existing or {}).get("origem") or "manual",
        "criado_em": (existing or {}).get("criado_em") or _now(),
        "atualizado_em": _now(),
    }


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("tarefas") or []),
        "tipos": TASK_TYPES,
        "status": STATUSES,
        "prioridades": PRIORITIES,
        "acoes": sorted({a for (_s, a) in TRANSITIONS}),
        "atualizado_em": data.get("atualizado_em"),
    }


def list_tarefas(
    q=None,
    status=None,
    tipo=None,
    armazem=None,
    operacao_id=None,
    operador=None,
):
    rows = list(_load_raw().get("tarefas") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("produto") or "").lower()
            or qq in str(r.get("operacao_id") or "").lower()
            or qq in str(r.get("operador") or "").lower()
            or qq in str(r.get("loc_origem") or "").lower()
            or qq in str(r.get("loc_destino") or "").lower()
        ]
    if status:
        st = _norm_status(status)
        rows = [r for r in rows if r.get("status") == st]
    if tipo:
        t = _norm_tipo(tipo)
        rows = [r for r in rows if r.get("tipo") == t]
    if armazem:
        ak = str(armazem).strip().upper()
        rows = [r for r in rows if str(r.get("armazem") or "").upper() == ak]
    if operacao_id:
        ok = str(operacao_id).strip().upper()
        rows = [r for r in rows if str(r.get("operacao_id") or "").upper() == ok]
    if operador:
        op = str(operador).strip().lower()
        rows = [r for r in rows if op in str(r.get("operador") or "").lower()]

    order = {s: i for i, s in enumerate(STATUSES)}
    rows.sort(
        key=lambda r: (
            order.get(r.get("status"), 99),
            str(r.get("prioridade") or ""),
            str(r.get("id") or ""),
        )
    )
    return {
        "total": len(_load_raw().get("tarefas") or []),
        "filtrado": len(rows),
        "tipos": TASK_TYPES,
        "status_opcoes": STATUSES,
        "prioridades": PRIORITIES,
        "tarefas": [_enrich(r) for r in rows],
    }


def get_tarefa(task_id):
    key = str(task_id or "").strip().upper()
    if not key:
        return None
    for r in _load_raw().get("tarefas") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def create_tarefa(payload, usuario=""):
    data = _load_raw()
    body = dict(payload or {})
    tid = str(body.get("id") or "").strip().upper() or _next_id(data)
    if any(str(r.get("id") or "").upper() == tid for r in data["tarefas"]):
        raise ValueError(f"já existe tarefa {tid}")
    row = _build_row(body, existing=None, task_id=tid, usuario=usuario)
    row["origem"] = "manual"
    data["tarefas"].append(row)
    _save(data)
    return _enrich(row)


def update_tarefa(task_id, payload, usuario=""):
    data = _load_raw()
    key = str(task_id or "").strip().upper()
    idx = None
    existing = None
    for i, r in enumerate(data.get("tarefas") or []):
        if str(r.get("id") or "").upper() == key:
            idx = i
            existing = r
            break
    if existing is None:
        raise ValueError("tarefa não encontrada")
    if existing.get("status") not in ("created", "assigned"):
        raise ValueError("só é possível editar tarefas criadas ou atribuídas")
    body = dict(payload or {})
    body.pop("id", None)
    body.pop("status", None)
    row = _build_row(body, existing=existing, task_id=existing.get("id"), usuario=usuario)
    data["tarefas"][idx] = row
    _save(data)
    return _enrich(row)


def transition(task_id, action, usuario="", motivo="", operador=None, qtd_feita=None):
    data = _load_raw()
    key = str(task_id or "").strip().upper()
    idx = None
    existing = None
    for i, r in enumerate(data.get("tarefas") or []):
        if str(r.get("id") or "").upper() == key:
            idx = i
            existing = r
            break
    if existing is None:
        raise ValueError("tarefa não encontrada")

    act = str(action or "").strip().lower()
    cur = existing.get("status") or "created"
    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    if act == "assign":
        op = str(operador if operador is not None else motivo or "").strip()
        if not op:
            raise ValueError("operador obrigatório para atribuir")
        existing["operador"] = op
        nota = op
    elif act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório para cancelar")
        existing["cancelamento_motivo"] = reason
        nota = reason
    else:
        nota = str(motivo or act).strip()

    if qtd_feita is not None:
        try:
            qf = float(qtd_feita)
        except (TypeError, ValueError):
            raise ValueError("qtd_feita deve ser número") from None
        if qf < 0:
            raise ValueError("qtd_feita não pode ser negativa")
        existing["qtd_feita"] = qf
    elif act == "complete" and float(existing.get("qtd_feita") or 0) <= 0:
        existing["qtd_feita"] = float(existing.get("qtd") or 0)

    if operador and act != "assign":
        existing["operador"] = str(operador).strip()

    existing["status"] = nxt
    existing["atualizado_em"] = _now()
    hist = list(existing.get("historico") or [])
    hist.append(_hist(nxt, usuario, nota))
    existing["historico"] = hist
    data["tarefas"][idx] = existing
    _save(data)
    return _enrich(existing)


def delete_tarefa(task_id):
    data = _load_raw()
    key = str(task_id or "").strip().upper()
    idx = None
    target = None
    for i, r in enumerate(data.get("tarefas") or []):
        if str(r.get("id") or "").upper() == key:
            idx = i
            target = r
            break
    if target is None:
        raise ValueError("tarefa não encontrada")
    if target.get("status") != "created":
        raise ValueError("só é possível excluir tarefas no status criada — cancele as demais")
    data["tarefas"].pop(idx)
    _save(data)
    return True


def generate_from_operation(operacao_id, usuario=""):
    """Gera tarefas a partir do workflow do tipo + linhas da operação."""
    op = wms_operations.get_operacao(operacao_id)
    if not op:
        raise ValueError("operação não encontrada")
    if op.get("status") in ("draft", "cancelled", "closed"):
        raise ValueError("operação em status inadequado para gerar tarefas")

    steps = list(op.get("tipo_workflow") or [])
    if not steps:
        steps = ["move"]
    linhas = list(op.get("linhas") or [])
    if not linhas:
        linhas = [{"produto": "item", "qtd": 1, "loc_origem": "", "loc_destino": ""}]

    data = _load_raw()
    created = []
    for step in steps:
        ttype = WORKFLOW_MAP.get(str(step).lower(), "move")
        for line in linhas:
            tid = _next_id(data)
            body = {
                "operacao_id": op["id"],
                "tipo": ttype,
                "armazem": op.get("armazem"),
                "produto_id": line.get("produto_id") or "",
                "produto": line.get("produto") or "item",
                "qtd": line.get("qtd") or 0,
                "loc_origem": line.get("loc_origem") or "",
                "loc_destino": line.get("loc_destino") or "",
                "prioridade": op.get("prioridade") or "normal",
                "workflow_step": step,
                "observacao": f"Gerada de {op['id']} / {step}",
            }
            row = _build_row(body, existing=None, task_id=tid, usuario=usuario)
            row["origem"] = "generated"
            data["tarefas"].append(row)
            created.append(_enrich(row))
    _save(data)
    return {
        "operacao_id": op["id"],
        "geradas": len(created),
        "tarefas": created,
    }
