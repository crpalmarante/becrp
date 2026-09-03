"""
WMS — Warehouse Operations (RFC-9004 MVP).

Instâncias operacionais com ciclo de vida controlado.
Fonte: dados/wms_operations.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import wms_operation_types
import wms_warehouses

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_operations.json")

STATUSES = {
    "draft": "Rascunho",
    "planned": "Planejada",
    "ready": "Pronta",
    "in_progress": "Em execução",
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

# Transições permitidas: status_atual → action → status_novo
TRANSITIONS = {
    ("draft", "plan"): "planned",
    ("draft", "cancel"): "cancelled",
    ("planned", "ready"): "ready",
    ("planned", "cancel"): "cancelled",
    ("ready", "start"): "in_progress",
    ("ready", "cancel"): "cancelled",
    ("in_progress", "complete"): "completed",
    ("in_progress", "cancel"): "cancelled",
    ("completed", "validate"): "validated",
    ("validated", "close"): "closed",
}

EDITABLE = frozenset({"draft", "planned"})
TERMINAL = frozenset({"closed", "cancelled"})


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return ensure_seed()
    if not isinstance(data.get("operacoes"), list):
        data["operacoes"] = []
    if data.get("seq") is None:
        data["seq"] = len(data["operacoes"])
    if not data["operacoes"]:
        return ensure_seed()
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("operacoes") or [])
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
    return f"OP-{day}-{seq:04d}"


def _norm_priority(val):
    s = str(val or "").strip().lower()
    aliases = {
        "urgente": "urgent",
        "alta": "high",
        "media": "normal",
        "média": "normal",
        "baixa": "low",
    }
    s = aliases.get(s, s) or "normal"
    if s not in PRIORITIES:
        raise ValueError("prioridade deve ser: urgent, high, normal ou low")
    return s


def _norm_status(val):
    s = str(val or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "rascunho": "draft",
        "planejada": "planned",
        "planejado": "planned",
        "pronta": "ready",
        "pronto": "ready",
        "em_execucao": "in_progress",
        "em_execução": "in_progress",
        "execucao": "in_progress",
        "concluida": "completed",
        "concluída": "completed",
        "validada": "validated",
        "validado": "validated",
        "fechada": "closed",
        "fechado": "closed",
        "cancelada": "cancelled",
        "cancelado": "cancelled",
    }
    s = aliases.get(s, s)
    if s not in STATUSES:
        raise ValueError("status inválido")
    return s


def _normalize_lines(raw):
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("linhas deve ser lista")
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        produto = str(item.get("produto") or item.get("nome") or "").strip()
        pid = str(item.get("produto_id") or item.get("id") or "").strip()
        try:
            qtd = float(item.get("qtd") if item.get("qtd") is not None else item.get("quantidade") or 0)
        except (TypeError, ValueError):
            raise ValueError("qtd da linha deve ser número") from None
        if qtd < 0:
            raise ValueError("qtd da linha não pode ser negativa")
        if not produto and not pid and qtd == 0:
            continue
        out.append({
            "produto_id": pid,
            "produto": produto or pid or "item",
            "qtd": qtd,
            "loc_origem": str(item.get("loc_origem") or "").strip().upper(),
            "loc_destino": str(item.get("loc_destino") or "").strip().upper(),
        })
    return out


def ensure_seed():
    wms_operation_types.ensure_seed()
    wms_warehouses.ensure_seed()
    now = _now()
    rows = [
        {
            "id": "OP-SEED-0001",
            "tipo": "REC-COMPRA",
            "armazem": "DC-01",
            "documento_tipo": "pedido_compra",
            "documento_ref": "PC-5001",
            "parceiro": "Fornecedor Demo",
            "prioridade": "normal",
            "status": "draft",
            "responsavel": "",
            "data_planejada": "",
            "observacao": "Recebimento demo — rascunho",
            "linhas": [
                {"produto_id": "1", "produto": "Produto demo", "qtd": 10, "loc_origem": "", "loc_destino": "REC-DOCK-01"},
            ],
            "historico": [_hist("draft", "seed", "criação seed")],
            "cancelamento_motivo": "",
            "origem": "seed",
            "criado_em": now,
            "atualizado_em": now,
        },
        {
            "id": "OP-SEED-0002",
            "tipo": "EXP-CLIENTE",
            "armazem": "DC-01",
            "documento_tipo": "pedido_venda",
            "documento_ref": "PV-100",
            "parceiro": "Cliente Demo",
            "prioridade": "high",
            "status": "ready",
            "responsavel": "bruno",
            "data_planejada": datetime.now().strftime("%Y-%m-%d"),
            "observacao": "Expedição demo — pronta para executar",
            "linhas": [
                {"produto_id": "1", "produto": "Produto demo", "qtd": 2, "loc_origem": "PCK-01", "loc_destino": "SHP-STAGE"},
            ],
            "historico": [
                _hist("draft", "seed", "criação"),
                _hist("planned", "seed", "planejada"),
                _hist("ready", "seed", "tarefas preparadas"),
            ],
            "cancelamento_motivo": "",
            "origem": "seed",
            "criado_em": now,
            "atualizado_em": now,
        },
    ]
    data = {"seq": 2, "atualizado_em": now, "operacoes": rows, "total": len(rows)}
    _save(data)
    return data


def _enrich(row):
    out = dict(row)
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    out["prioridade_label"] = PRIORITIES.get(out.get("prioridade"), out.get("prioridade") or "")
    tipo = wms_operation_types.get_tipo(out.get("tipo"))
    out["tipo_nome"] = (tipo or {}).get("nome") or out.get("tipo") or ""
    out["tipo_direcao"] = (tipo or {}).get("direcao") or ""
    out["tipo_workflow"] = list((tipo or {}).get("workflow") or [])
    wh = wms_warehouses.get_armazem(out.get("armazem"))
    out["armazem_nome"] = (wh or {}).get("nome") or ""
    out["linhas_count"] = len(out.get("linhas") or [])
    out["pode_editar"] = out.get("status") in EDITABLE
    st = out.get("status")
    actions = []
    for (from_st, action), _to in TRANSITIONS.items():
        if from_st == st:
            actions.append(action)
    out["acoes"] = actions
    return out


def _validate_refs(tipo, armazem):
    t = wms_operation_types.get_tipo(tipo)
    if not t:
        raise ValueError(f"tipo de operação não encontrado: {tipo}")
    if t.get("ativo") is False:
        raise ValueError(f"tipo de operação inativo: {tipo}")
    wh = wms_warehouses.get_armazem(armazem)
    if not wh:
        raise ValueError(f"armazém não encontrado: {armazem}")
    if wh.get("ativo") is False:
        raise ValueError(f"armazém inativo: {armazem}")
    return t, wh


def _build_row(payload, existing=None, op_id=None, usuario=""):
    body = payload if isinstance(payload, dict) else {}
    oid = str(op_id or (existing or {}).get("id") or "").strip().upper()
    if not oid:
        raise ValueError("id obrigatório")

    tipo = str(
        body.get("tipo") if body.get("tipo") is not None else (existing or {}).get("tipo") or ""
    ).strip().upper()
    if not tipo:
        raise ValueError("tipo obrigatório")

    armazem = str(
        body.get("armazem")
        if body.get("armazem") is not None
        else (existing or {}).get("armazem")
        or ""
    ).strip().upper()
    if not armazem:
        raise ValueError("armazém obrigatório")

    _validate_refs(tipo, armazem)

    prioridade = _norm_priority(
        body.get("prioridade")
        if body.get("prioridade") is not None
        else (existing or {}).get("prioridade")
        or "normal"
    )

    if existing:
        status = existing.get("status") or "draft"
    else:
        status = "draft"

    if "linhas" in body:
        linhas = _normalize_lines(body.get("linhas"))
    else:
        linhas = list((existing or {}).get("linhas") or [])

    def _field(key, default=""):
        if key in body:
            return str(body.get(key) or "").strip()
        return str((existing or {}).get(key) or default).strip()

    historico = list((existing or {}).get("historico") or [])
    if not existing:
        historico = [_hist("draft", usuario, "criação")]

    return {
        "id": oid,
        "tipo": tipo,
        "armazem": armazem,
        "documento_tipo": _field("documento_tipo"),
        "documento_ref": _field("documento_ref"),
        "parceiro": _field("parceiro"),
        "prioridade": prioridade,
        "status": status,
        "responsavel": _field("responsavel"),
        "data_planejada": _field("data_planejada"),
        "observacao": _field("observacao"),
        "linhas": linhas,
        "historico": historico,
        "cancelamento_motivo": (existing or {}).get("cancelamento_motivo") or "",
        "origem": _field("origem") or (existing or {}).get("origem") or "manual",
        "criado_em": (existing or {}).get("criado_em") or _now(),
        "atualizado_em": _now(),
    }


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("operacoes") or []),
        "status": STATUSES,
        "prioridades": PRIORITIES,
        "acoes": sorted({a for (_s, a) in TRANSITIONS}),
        "atualizado_em": data.get("atualizado_em"),
    }


def list_operacoes(q=None, status=None, tipo=None, armazem=None, prioridade=None):
    rows = list(_load_raw().get("operacoes") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("tipo") or "").lower()
            or qq in str(r.get("documento_ref") or "").lower()
            or qq in str(r.get("parceiro") or "").lower()
            or qq in str(r.get("responsavel") or "").lower()
            or qq in str(r.get("observacao") or "").lower()
        ]
    if status:
        st = _norm_status(status)
        rows = [r for r in rows if r.get("status") == st]
    if tipo:
        tk = str(tipo).strip().upper()
        rows = [r for r in rows if str(r.get("tipo") or "").upper() == tk]
    if armazem:
        ak = str(armazem).strip().upper()
        rows = [r for r in rows if str(r.get("armazem") or "").upper() == ak]
    if prioridade:
        pr = _norm_priority(prioridade)
        rows = [r for r in rows if r.get("prioridade") == pr]

    order = {s: i for i, s in enumerate(STATUSES)}
    rows.sort(
        key=lambda r: (
            order.get(r.get("status"), 99),
            str(r.get("prioridade") or ""),
            str(r.get("id") or ""),
        )
    )
    return {
        "total": len(_load_raw().get("operacoes") or []),
        "filtrado": len(rows),
        "status_opcoes": STATUSES,
        "prioridades": PRIORITIES,
        "operacoes": [_enrich(r) for r in rows],
    }


def get_operacao(op_id):
    key = str(op_id or "").strip().upper()
    if not key:
        return None
    for r in _load_raw().get("operacoes") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def create_operacao(payload, usuario=""):
    data = _load_raw()
    body = dict(payload or {})
    oid = str(body.get("id") or "").strip().upper() or _next_id(data)
    if any(str(r.get("id") or "").upper() == oid for r in data["operacoes"]):
        raise ValueError(f"já existe operação {oid}")
    row = _build_row(body, existing=None, op_id=oid, usuario=usuario)
    row["origem"] = str(body.get("origem") or "manual").strip()
    data["operacoes"].append(row)
    _save(data)
    return _enrich(row)


def update_operacao(op_id, payload, usuario=""):
    data = _load_raw()
    key = str(op_id or "").strip().upper()
    idx = None
    existing = None
    for i, r in enumerate(data.get("operacoes") or []):
        if str(r.get("id") or "").upper() == key:
            idx = i
            existing = r
            break
    if existing is None:
        raise ValueError("operação não encontrada")
    if existing.get("status") not in EDITABLE:
        raise ValueError("só é possível editar operações em rascunho ou planejada")
    body = dict(payload or {})
    body.pop("id", None)
    body.pop("status", None)
    row = _build_row(body, existing=existing, op_id=existing.get("id"), usuario=usuario)
    data["operacoes"][idx] = row
    _save(data)
    return _enrich(row)


def transition(op_id, action, usuario="", motivo=""):
    data = _load_raw()
    key = str(op_id or "").strip().upper()
    idx = None
    existing = None
    for i, r in enumerate(data.get("operacoes") or []):
        if str(r.get("id") or "").upper() == key:
            idx = i
            existing = r
            break
    if existing is None:
        raise ValueError("operação não encontrada")

    act = str(action or "").strip().lower()
    cur = existing.get("status") or "draft"
    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório para cancelar")
        existing["cancelamento_motivo"] = reason

    existing["status"] = nxt
    existing["atualizado_em"] = _now()
    hist = list(existing.get("historico") or [])
    hist.append(_hist(nxt, usuario, motivo if act == "cancel" else act))
    existing["historico"] = hist
    data["operacoes"][idx] = existing
    _save(data)
    return _enrich(existing)


def delete_operacao(op_id):
    """Só rascunho sem histórico avançado (ou apenas draft)."""
    data = _load_raw()
    key = str(op_id or "").strip().upper()
    idx = None
    target = None
    for i, r in enumerate(data.get("operacoes") or []):
        if str(r.get("id") or "").upper() == key:
            idx = i
            target = r
            break
    if target is None:
        raise ValueError("operação não encontrada")
    if target.get("status") != "draft":
        raise ValueError("só é possível excluir operações em rascunho — cancele as demais")
    data["operacoes"].pop(idx)
    _save(data)
    return True
