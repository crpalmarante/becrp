"""
WMS — Ciclo de Contagem / Inventário Físico (RFC-5009).

Sessão de contagem por localização. Não baixa estoque sozinha:
divergência → aprovação → ajuste no ledger (inventory_mvp).
Fonte: dados/wms_counting.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import inventory_mvp
import settings_store
import wms_locations
import wms_warehouses

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_counting.json")

TIPOS = {
    "full": "Inventário completo",
    "cycle": "Contagem cíclica",
    "location": "Por localização",
    "spot": "Pontual",
}

STATUSES = {
    "created": "Criada",
    "counting": "Em contagem",
    "review": "Revisão",
    "pending_approval": "Aguardando aprovação",
    "approved": "Aprovada",
    "applied": "Ajustes aplicados",
    "closed": "Encerrada",
    "cancelled": "Cancelada",
}

LINE_STATUS = {
    "pending": "Pendente",
    "counted": "Contada",
    "match": "Confere",
    "gain": "Sobra",
    "loss": "Falta",
}

CAUSAS = {
    "erro_contagem": "Erro de contagem (recontar)",
    "quebra_perda": "Quebra / perda física",
    "extravio": "Extravio / sumiço",
    "erro_recebimento": "Erro no recebimento",
    "erro_baixa": "Erro de baixa / venda",
    "nao_localizado": "Item não localizado",
    "encontrado": "Item encontrado fora do sistema",
    "obsolescencia": "Obsolescência / vencido",
    "outros": "Outros",
}

TRANSITIONS = {
    ("created", "start"): "counting",
    ("created", "cancel"): "cancelled",
    ("counting", "submit_review"): "review",
    ("counting", "cancel"): "cancelled",
    ("review", "recount"): "counting",
    ("review", "request_adjust"): "pending_approval",
    ("review", "close"): "closed",
    ("review", "cancel"): "cancelled",
    ("pending_approval", "approve"): "approved",
    ("pending_approval", "reject"): "counting",
    ("approved", "apply"): "applied",
    ("approved", "cancel"): "cancelled",
    ("applied", "close"): "closed",
}

QTY_DECIMALS = 3


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _as_qty(val, default=0.0):
    try:
        return round(float(val), QTY_DECIMALS)
    except (TypeError, ValueError):
        return float(default)


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return {"seq": 0, "sessoes": [], "atualizado_em": None}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"seq": 0, "sessoes": [], "atualizado_em": None}
    if not isinstance(data.get("sessoes"), list):
        data["sessoes"] = []
    if data.get("seq") is None:
        data["seq"] = len(data["sessoes"])
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("sessoes") or [])
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
    return f"CT-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def _norm_tipo(val):
    s = str(val or "").strip().lower()
    aliases = {
        "completo": "full",
        "inventario": "full",
        "inventário": "full",
        "ciclica": "cycle",
        "cíclica": "cycle",
        "rotativa": "cycle",
        "localizacao": "location",
        "localização": "location",
        "endereco": "location",
        "pontual": "spot",
        "avulsa": "spot",
    }
    s = aliases.get(s, s) or "location"
    if s not in TIPOS:
        raise ValueError("tipo deve ser: full, cycle, location ou spot")
    return s


def _produto_nome(pid):
    path = os.path.join(BASE_DIR, "dados", "produtos.json")
    if not os.path.exists(path):
        return str(pid)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("produtos") if isinstance(data, dict) else data
        for p in rows or []:
            if str(p.get("id") or p.get("codigo") or "") == str(pid):
                return p.get("nome") or p.get("descricao") or str(pid)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return str(pid)


def _loc_stock_map(armazem):
    """Saldo por localização do armazém (chave estabelecimento ou código do CD)."""
    eid = wms_warehouses.map_armazem_to_estabelecimento(armazem) or armazem
    bal = inventory_mvp.load_balances()
    por_loc = bal.get("por_localizacao") or {}
    locs = por_loc.get(str(eid))
    if not locs:
        locs = por_loc.get(str(armazem).upper()) or {}
    return str(eid), locs or {}


def _select_locations(armazem, tipo, localizacoes=None, tipos_local=None):
    listed = (wms_locations.list_localizacoes(armazem=armazem).get("localizacoes") or [])
    if tipo in ("location", "spot"):
        wanted = {str(x or "").strip().upper() for x in (localizacoes or []) if str(x or "").strip()}
        if not wanted:
            raise ValueError("informe ao menos uma localização")
        rows = [l for l in listed if str(l.get("codigo") or "").upper() in wanted]
        missing = wanted - {str(l.get("codigo") or "").upper() for l in rows}
        if missing:
            raise ValueError("localização inválida: " + ", ".join(sorted(missing)))
        return rows
    if tipo == "cycle":
        tipos = [str(t).strip().lower() for t in (tipos_local or ["storage", "picking"])]
        return [l for l in listed if str(l.get("tipo") or "").lower() in tipos and l.get("status") != "inactive"]
    return [l for l in listed if l.get("status") != "inactive"]


def _line_diff(ln):
    if ln.get("qtd_contada") is None:
        return None
    return round(_as_qty(ln.get("qtd_contada")) - _as_qty(ln.get("qtd_sistema") or 0), QTY_DECIMALS)


def _classify_line(ln):
    diff = _line_diff(ln)
    if ln.get("qtd_contada") is None:
        ln["status"] = "pending"
        ln["divergencia"] = None
        return ln
    ln["divergencia"] = diff
    if abs(diff or 0) < 1e-9:
        ln["status"] = "match"
    elif (diff or 0) > 0:
        ln["status"] = "gain"
    else:
        ln["status"] = "loss"
    return ln


def _resumo(row):
    linhas = list(row.get("linhas") or [])
    contadas = [l for l in linhas if l.get("qtd_contada") is not None]
    divs = [l for l in contadas if abs(_as_qty(l.get("divergencia") or 0)) >= 1e-9]
    n = len(contadas)
    return {
        "linhas": len(linhas),
        "contadas": n,
        "pendentes": sum(1 for l in linhas if l.get("status") == "pending"),
        "divergencias": len(divs),
        "sobras": sum(1 for l in divs if (l.get("divergencia") or 0) > 0),
        "faltas": sum(1 for l in divs if (l.get("divergencia") or 0) < 0),
        "acuracia": round((n - len(divs)) / n * 100, 1) if n else None,
        "ajustes": len(row.get("ajustes") or []),
    }


def _enrich(row):
    out = dict(row)
    out["tipo_label"] = TIPOS.get(out.get("tipo"), out.get("tipo") or "")
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    linhas = []
    for ln in out.get("linhas") or []:
        ll = dict(ln)
        ll["status_label"] = LINE_STATUS.get(ll.get("status"), ll.get("status") or "")
        if ll.get("causa"):
            ll["causa_label"] = CAUSAS.get(ll.get("causa"), ll.get("causa"))
        linhas.append(ll)
    out["linhas"] = linhas
    out["resumo"] = _resumo(out)
    st = out.get("status")
    out["acoes"] = [a for (fr, a), _to in TRANSITIONS.items() if fr == st]
    wh = wms_warehouses.get_armazem(out.get("armazem"))
    out["armazem_nome"] = (wh or {}).get("nome") or ""
    return out


def _find(data, sid):
    key = str(sid or "").strip().upper()
    for i, r in enumerate(data.get("sessoes") or []):
        if str(r.get("id") or "").upper() == key:
            return i, r
    return None, None


def _requer_aprovacao():
    return bool(settings_store.get("wms", "contagem_requer_aprovacao", True))


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("sessoes") or []),
        "tipos": TIPOS,
        "status": STATUSES,
        "linha_status": LINE_STATUS,
        "causas": CAUSAS,
        "requer_aprovacao": _requer_aprovacao(),
        "atualizado_em": data.get("atualizado_em"),
    }


def list_sessoes(q=None, status=None, tipo=None, armazem=None):
    rows = list(_load_raw().get("sessoes") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("armazem") or "").lower()
            or qq in str(r.get("responsavel") or "").lower()
            or qq in str(r.get("observacao") or "").lower()
        ]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [r for r in rows if r.get("status") == st]
    if tipo:
        tp = _norm_tipo(tipo)
        rows = [r for r in rows if r.get("tipo") == tp]
    if armazem:
        ak = str(armazem).strip().upper()
        rows = [r for r in rows if str(r.get("armazem") or "").upper() == ak]
    order = {s: i for i, s in enumerate(STATUSES)}
    rows.sort(key=lambda r: (order.get(r.get("status"), 99), str(r.get("id") or "")))
    return {
        "total": len(_load_raw().get("sessoes") or []),
        "filtrado": len(rows),
        "tipos": TIPOS,
        "status_opcoes": STATUSES,
        "causas": CAUSAS,
        "sessoes": [_enrich(r) for r in rows],
    }


def get_sessao(sid):
    key = str(sid or "").strip().upper()
    for r in _load_raw().get("sessoes") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def create_sessao(payload, usuario=""):
    body = dict(payload or {})
    armazem = str(body.get("armazem") or "").strip().upper()
    if not armazem or not wms_warehouses.get_armazem(armazem):
        raise ValueError("armazém obrigatório/válido")
    tipo = _norm_tipo(body.get("tipo") or "location")
    locs = _select_locations(
        armazem,
        tipo,
        localizacoes=body.get("localizacoes"),
        tipos_local=body.get("tipos_local"),
    )
    if not locs:
        raise ValueError("nenhuma localização no escopo da contagem")

    pids_filter = {str(p).strip() for p in (body.get("produtos") or []) if str(p).strip()}
    incluir_zerados = bool(body.get("incluir_zerados"))
    eid, stock = _loc_stock_map(armazem)

    linhas = []
    n = 0
    for loc in locs:
        codigo = str(loc.get("codigo") or "").upper()
        prods = dict(stock.get(codigo) or {})
        if pids_filter:
            keys = pids_filter if incluir_zerados else (set(prods) & pids_filter)
        else:
            keys = set(prods)
        for pid in sorted(keys, key=str):
            n += 1
            qs = _as_qty(prods.get(pid) or 0)
            linhas.append({
                "linha": n,
                "produto_id": str(pid),
                "produto": _produto_nome(pid),
                "loc_origem": codigo,
                "loc_nome": loc.get("nome") or codigo,
                "qtd_sistema": qs,
                "qtd_contada": None,
                "divergencia": None,
                "status": "pending",
                "causa": "",
                "observacao": "",
                "contado_por": "",
                "contado_em": "",
            })

    data = _load_raw()
    sid = str(body.get("id") or "").strip().upper() or _next_id(data)
    if any(str(r.get("id") or "").upper() == sid for r in data["sessoes"]):
        raise ValueError(f"já existe sessão {sid}")

    row = {
        "id": sid,
        "tipo": tipo,
        "armazem": armazem,
        "estabelecimento_id": eid,
        "localizacoes": [str(l.get("codigo") or "").upper() for l in locs],
        "produtos_filtro": sorted(pids_filter),
        "status": "created",
        "responsavel": str(body.get("responsavel") or usuario or "").strip(),
        "linhas": linhas,
        "ajustes": [],
        "historico": [_hist("created", usuario, "snapshot de saldos")],
        "observacao": str(body.get("observacao") or "").strip(),
        "cancelamento_motivo": "",
        "aprovado_por": "",
        "aprovado_em": "",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["sessoes"].append(row)
    _save(data)
    return _enrich(row)


def count_line(sid, linha, qtd_contada, usuario="", causa="", observacao=""):
    data = _load_raw()
    idx, row = _find(data, sid)
    if row is None:
        raise ValueError("sessão não encontrada")
    if row.get("status") not in ("created", "counting"):
        raise ValueError("contagem só em created/counting")
    try:
        qc = _as_qty(qtd_contada)
    except (TypeError, ValueError):
        raise ValueError("qtd_contada inválida") from None
    if qc < 0:
        raise ValueError("qtd_contada não pode ser negativa")

    found = None
    for ln in row.get("linhas") or []:
        if int(ln.get("linha") or 0) == int(linha):
            found = ln
            break
    if found is None:
        raise ValueError("linha não encontrada")

    found["qtd_contada"] = qc
    found["contado_por"] = str(usuario or "").strip()
    found["contado_em"] = _now()
    if causa:
        c = str(causa).strip()
        if c not in CAUSAS:
            c = "outros"
        found["causa"] = c
    if observacao is not None and str(observacao).strip():
        found["observacao"] = str(observacao).strip()
    _classify_line(found)

    if row.get("status") == "created":
        row["status"] = "counting"
        hist = list(row.get("historico") or [])
        hist.append(_hist("counting", usuario, "início via linha"))
        row["historico"] = hist

    row["atualizado_em"] = _now()
    data["sessoes"][idx] = row
    _save(data)
    return _enrich(row)


def add_line(sid, payload, usuario=""):
    """Inclui item encontrado que não estava no snapshot."""
    body = dict(payload or {})
    data = _load_raw()
    idx, row = _find(data, sid)
    if row is None:
        raise ValueError("sessão não encontrada")
    if row.get("status") not in ("created", "counting"):
        raise ValueError("inclusão só em created/counting")
    pid = str(body.get("produto_id") or "").strip()
    loc = str(body.get("loc_origem") or body.get("localizacao") or "").strip().upper()
    if not pid or not loc:
        raise ValueError("produto_id e localização obrigatórios")
    if loc not in (row.get("localizacoes") or []):
        raise ValueError("localização fora do escopo da sessão")
    _eid, stock = _loc_stock_map(row.get("armazem"))
    qs = _as_qty((stock.get(loc) or {}).get(pid) or 0)
    n = max((int(l.get("linha") or 0) for l in (row.get("linhas") or [])), default=0) + 1
    qc = body.get("qtd_contada")
    ln = {
        "linha": n,
        "produto_id": pid,
        "produto": body.get("produto") or _produto_nome(pid),
        "loc_origem": loc,
        "loc_nome": loc,
        "qtd_sistema": qs,
        "qtd_contada": _as_qty(qc) if qc is not None and str(qc) != "" else None,
        "divergencia": None,
        "status": "pending",
        "causa": "encontrado" if qs == 0 else "",
        "observacao": str(body.get("observacao") or "").strip(),
        "contado_por": str(usuario or "").strip() if qc is not None else "",
        "contado_em": _now() if qc is not None else "",
        "origem": "encontrado",
    }
    if ln["qtd_contada"] is not None:
        _classify_line(ln)
    row.setdefault("linhas", []).append(ln)
    if row.get("status") == "created":
        row["status"] = "counting"
        hist = list(row.get("historico") or [])
        hist.append(_hist("counting", usuario, f"item encontrado {pid}@{loc}"))
        row["historico"] = hist
    row["atualizado_em"] = _now()
    data["sessoes"][idx] = row
    _save(data)
    return _enrich(row)


def set_causa(sid, linha, causa, observacao="", usuario=""):
    data = _load_raw()
    idx, row = _find(data, sid)
    if row is None:
        raise ValueError("sessão não encontrada")
    if row.get("status") not in ("counting", "review", "pending_approval"):
        raise ValueError("causa só em counting/review/pending_approval")
    found = None
    for ln in row.get("linhas") or []:
        if int(ln.get("linha") or 0) == int(linha):
            found = ln
            break
    if found is None:
        raise ValueError("linha não encontrada")
    c = str(causa or "").strip()
    if c and c not in CAUSAS:
        c = "outros"
    found["causa"] = c
    found["observacao"] = str(observacao or "").strip()
    row["atualizado_em"] = _now()
    data["sessoes"][idx] = row
    _save(data)
    return _enrich(row)


def _apply_ajustes(row, usuario=""):
    eid = row.get("estabelecimento_id") or wms_warehouses.map_armazem_to_estabelecimento(row.get("armazem"))
    if not eid:
        raise ValueError("sessão sem estabelecimento para ajustar estoque")
    movements = inventory_mvp.load_movements()
    balances = inventory_mvp.load_balances()
    transit = inventory_mvp.load_transit()
    ajustes = []
    for ln in row.get("linhas") or []:
        _classify_line(ln)
        diff = _as_qty(ln.get("divergencia") or 0)
        if ln.get("qtd_contada") is None or abs(diff) < 1e-9:
            continue
        sign = 1 if diff > 0 else -1
        loc = ln.get("loc_origem") or ""
        if sign < 0:
            atual = inventory_mvp.inventory_balance(eid, ln.get("produto_id"), balances=balances, location_id=loc)
            if abs(diff) > atual + 1e-9:
                raise ValueError(
                    f"ajuste de saída maior que saldo em {loc} "
                    f"(produto {ln.get('produto_id')}: {atual})"
                )
        r = inventory_mvp.inventory_apply_movement(
            "adjust",
            eid,
            ln.get("produto_id"),
            abs(diff),
            sign=sign,
            ref_tipo="wms_count",
            ref_id=row.get("id"),
            nota=(
                f"contagem {row.get('id')} {loc}: "
                f"sistema {ln.get('qtd_sistema')} → contado {ln.get('qtd_contada')}"
            ),
            user_id=usuario,
            location_id=loc or None,
            movements=movements,
            balances=balances,
            transit=transit,
            persist=False,
        )
        ajustes.append({
            "linha": ln.get("linha"),
            "produto_id": ln.get("produto_id"),
            "loc_origem": loc,
            "qtd_sistema": ln.get("qtd_sistema"),
            "qtd_contada": ln.get("qtd_contada"),
            "divergencia": diff,
            "causa": ln.get("causa") or "",
            "movement_id": r.get("movement_id"),
        })
    inventory_mvp.save_movements(movements)
    inventory_mvp.save_balances(balances)
    inventory_mvp.save_transit(transit)
    row["ajustes"] = ajustes
    return ajustes


def transition(sid, action, usuario="", motivo=""):
    data = _load_raw()
    idx, row = _find(data, sid)
    if row is None:
        raise ValueError("sessão não encontrada")

    act = str(action or "").strip().lower()
    cur = row.get("status") or "created"
    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    for ln in row.get("linhas") or []:
        _classify_line(ln)
    resumo = _resumo(row)

    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório para cancelar")
        row["cancelamento_motivo"] = reason
        nota = reason
    elif act == "submit_review":
        pending = [l for l in (row.get("linhas") or []) if l.get("status") == "pending"]
        if pending:
            raise ValueError("ainda há linhas pendentes — conte ou remova do escopo")
        nota = f"{resumo['contadas']} linhas, {resumo['divergencias']} divergências"
    elif act == "request_adjust":
        if resumo["divergencias"] <= 0:
            raise ValueError("sem divergências — use close")
        if not _requer_aprovacao():
            nxt = "approved"
            nota = "divergências sem aprovação (config)"
        else:
            nota = f"{resumo['divergencias']} ajuste(s) para aprovação"
    elif act == "close":
        if cur == "review" and resumo["divergencias"] > 0:
            raise ValueError("há divergências — solicite ajuste ou reconte")
        nota = "encerrada sem ajuste" if not row.get("ajustes") else "encerrada"
    elif act == "approve":
        row["aprovado_por"] = str(usuario or "").strip()
        row["aprovado_em"] = _now()
        nota = "aprovado"
    elif act == "reject":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório para rejeitar")
        nota = reason
    elif act == "apply":
        _apply_ajustes(row, usuario=usuario)
        nota = f"{len(row.get('ajustes') or [])} movimento(s)"
    else:
        nota = str(motivo or act).strip()

    row["status"] = nxt
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(nxt, usuario, nota))
    row["historico"] = hist
    data["sessoes"][idx] = row
    _save(data)
    return _enrich(row)
