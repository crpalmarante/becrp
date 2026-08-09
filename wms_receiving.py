"""
WMS — Receiving Process (RFC-9007 MVP).

Ciclo físico de recebimento no armazém (não substitui o recebimento fiscal).
Fonte: dados/wms_receiving.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import wms_operations
import wms_warehouses

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_receiving.json")

SOURCES = {
    "supplier": "Fornecedor",
    "transfer": "Transferência",
    "return": "Devolução cliente",
    "repair": "Retorno reparo",
}

STATUSES = {
    "expected": "Esperado",
    "arrived": "Chegou",
    "unloading": "Descarregando",
    "checking": "Conferência",
    "inspection": "Inspeção",
    "putaway": "Put Away",
    "completed": "Concluído",
    "cancelled": "Cancelado",
}

LINE_INSPECTION = {
    "pending": "Pendente",
    "approved": "Aprovado",
    "rejected": "Rejeitado",
}

TRANSITIONS = {
    ("expected", "arrive"): "arrived",
    ("expected", "cancel"): "cancelled",
    ("arrived", "unload"): "unloading",
    ("arrived", "cancel"): "cancelled",
    ("unloading", "start_check"): "checking",
    ("unloading", "cancel"): "cancelled",
    ("checking", "start_inspect"): "inspection",
    ("checking", "cancel"): "cancelled",
    ("inspection", "start_putaway"): "putaway",
    ("inspection", "cancel"): "cancelled",
    ("putaway", "complete"): "completed",
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
    if not isinstance(data.get("recebimentos"), list):
        data["recebimentos"] = []
    if data.get("seq") is None:
        data["seq"] = len(data["recebimentos"])
    if not data["recebimentos"]:
        return ensure_seed()
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("recebimentos") or [])
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
    return f"RV-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def _norm_source(val):
    s = str(val or "").strip().lower()
    aliases = {
        "fornecedor": "supplier",
        "compra": "supplier",
        "transferencia": "transfer",
        "transferência": "transfer",
        "devolucao": "return",
        "devolução": "return",
        "reparo": "repair",
    }
    s = aliases.get(s, s) or "supplier"
    if s not in SOURCES:
        raise ValueError("origem deve ser: supplier, transfer, return ou repair")
    return s


def ensure_seed():
    wms_operations.ensure_seed()
    now = _now()
    row = {
        "id": "RV-SEED-0001",
        "origem": "supplier",
        "operacao_id": "OP-SEED-0001",
        "armazem": "DC-01",
        "documento_tipo": "pedido_compra",
        "documento_ref": "PC-5001",
        "parceiro": "Fornecedor Demo",
        "transportadora": "Transportadora X",
        "veiculo": "",
        "status": "expected",
        "operador": "",
        "loc_recebimento": "REC-DOCK-01",
        "linhas": [
            {
                "linha": 1,
                "produto_id": "1",
                "produto": "Produto demo",
                "qtd_esperada": 10,
                "qtd_recebida": 0,
                "qtd_aprovada": 0,
                "loc_destino": "",
                "inspecao": "pending",
                "lote": "",
                "serie": "",
            }
        ],
        "historico": [_hist("expected", "seed", "criação")],
        "observacao": "Seed — recebimento esperado",
        "cancelamento_motivo": "",
        "origem_dado": "seed",
        "criado_em": now,
        "atualizado_em": now,
    }
    data = {"seq": 1, "atualizado_em": now, "recebimentos": [row], "total": 1}
    _save(data)
    return data


def _enrich(row):
    out = dict(row)
    out["origem_label"] = SOURCES.get(out.get("origem"), out.get("origem") or "")
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    linhas = []
    for ln in out.get("linhas") or []:
        ll = dict(ln)
        ll["inspecao_label"] = LINE_INSPECTION.get(ll.get("inspecao"), ll.get("inspecao") or "")
        linhas.append(ll)
    out["linhas"] = linhas
    out["linhas_count"] = len(linhas)
    out["divergencias"] = sum(
        1
        for l in linhas
        if float(l.get("qtd_recebida") or 0) != float(l.get("qtd_esperada") or 0)
        and float(l.get("qtd_recebida") or 0) > 0
    )
    out["rejeitadas"] = sum(1 for l in linhas if l.get("inspecao") == "rejected")
    st = out.get("status")
    out["acoes"] = [a for (fr, a), _to in TRANSITIONS.items() if fr == st]
    wh = wms_warehouses.get_armazem(out.get("armazem"))
    out["armazem_nome"] = (wh or {}).get("nome") or ""
    return out


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("recebimentos") or []),
        "origens": SOURCES,
        "status": STATUSES,
        "inspecao": LINE_INSPECTION,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_recebimentos(q=None, status=None, origem=None, armazem=None):
    rows = list(_load_raw().get("recebimentos") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("documento_ref") or "").lower()
            or qq in str(r.get("parceiro") or "").lower()
            or qq in str(r.get("operacao_id") or "").lower()
            or qq in str(r.get("transportadora") or "").lower()
        ]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [r for r in rows if r.get("status") == st]
    if origem:
        og = _norm_source(origem)
        rows = [r for r in rows if r.get("origem") == og]
    if armazem:
        ak = str(armazem).strip().upper()
        rows = [r for r in rows if str(r.get("armazem") or "").upper() == ak]
    order = {s: i for i, s in enumerate(STATUSES)}
    rows.sort(key=lambda r: (order.get(r.get("status"), 99), str(r.get("id") or "")))
    return {
        "total": len(_load_raw().get("recebimentos") or []),
        "filtrado": len(rows),
        "origens": SOURCES,
        "status_opcoes": STATUSES,
        "recebimentos": [_enrich(r) for r in rows],
    }


def get_recebimento(rid):
    key = str(rid or "").strip().upper()
    for r in _load_raw().get("recebimentos") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def create_from_operation(operacao_id, usuario="", origem="supplier"):
    op = wms_operations.get_operacao(operacao_id)
    if not op:
        raise ValueError("operação não encontrada")
    if op.get("status") in ("cancelled", "closed"):
        raise ValueError("operação cancelada/fechada")
    data = _load_raw()
    rid = _next_id(data)
    linhas = []
    for i, ln in enumerate(op.get("linhas") or [], start=1):
        linhas.append({
            "linha": i,
            "produto_id": str(ln.get("produto_id") or ""),
            "produto": str(ln.get("produto") or "item"),
            "qtd_esperada": float(ln.get("qtd") or 0),
            "qtd_recebida": 0,
            "qtd_aprovada": 0,
            "loc_destino": str(ln.get("loc_destino") or "").upper(),
            "inspecao": "pending",
            "lote": "",
            "serie": "",
        })
    if not linhas:
        linhas = [{
            "linha": 1,
            "produto_id": "",
            "produto": "item",
            "qtd_esperada": 1,
            "qtd_recebida": 0,
            "qtd_aprovada": 0,
            "loc_destino": "",
            "inspecao": "pending",
            "lote": "",
            "serie": "",
        }]
    row = {
        "id": rid,
        "origem": _norm_source(origem),
        "operacao_id": op["id"],
        "armazem": str(op.get("armazem") or "").upper(),
        "documento_tipo": str(op.get("documento_tipo") or ""),
        "documento_ref": str(op.get("documento_ref") or ""),
        "parceiro": str(op.get("parceiro") or ""),
        "transportadora": "",
        "veiculo": "",
        "status": "expected",
        "operador": str(op.get("responsavel") or "").strip(),
        "loc_recebimento": "REC-DOCK-01",
        "linhas": linhas,
        "historico": [_hist("expected", usuario, f"gerado de {op['id']}")],
        "observacao": "",
        "cancelamento_motivo": "",
        "origem_dado": "generated",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    if not wms_warehouses.get_armazem(row["armazem"]):
        raise ValueError("armazém inválido")
    data["recebimentos"].append(row)
    _save(data)
    return _enrich(row)


def create_recebimento(payload, usuario=""):
    body = dict(payload or {})
    if body.get("operacao_id") and not body.get("linhas"):
        return create_from_operation(
            body.get("operacao_id"),
            usuario=usuario,
            origem=body.get("origem") or "supplier",
        )

    data = _load_raw()
    rid = str(body.get("id") or "").strip().upper() or _next_id(data)
    if any(str(r.get("id") or "").upper() == rid for r in data["recebimentos"]):
        raise ValueError(f"já existe recebimento {rid}")

    armazem = str(body.get("armazem") or "").strip().upper()
    if not armazem or not wms_warehouses.get_armazem(armazem):
        raise ValueError("armazém obrigatório/válido")

    linhas_in = body.get("linhas") or []
    if isinstance(linhas_in, str):
        # produto|qtd por linha
        parsed = []
        for i, line in enumerate(linhas_in.split("\n"), start=1):
            parts = [p.strip() for p in line.split("|")]
            if not parts[0]:
                continue
            parsed.append({
                "linha": i,
                "produto": parts[0],
                "qtd_esperada": float(parts[1]) if len(parts) > 1 and parts[1] else 1,
                "qtd_recebida": 0,
                "qtd_aprovada": 0,
                "loc_destino": (parts[2] if len(parts) > 2 else "").upper(),
                "produto_id": "",
                "inspecao": "pending",
                "lote": "",
                "serie": "",
            })
        linhas_in = parsed

    linhas = []
    for i, ln in enumerate(linhas_in, start=1):
        if not isinstance(ln, dict):
            continue
        linhas.append({
            "linha": int(ln.get("linha") or i),
            "produto_id": str(ln.get("produto_id") or ""),
            "produto": str(ln.get("produto") or "item"),
            "qtd_esperada": float(ln.get("qtd_esperada") if ln.get("qtd_esperada") is not None else ln.get("qtd") or 0),
            "qtd_recebida": float(ln.get("qtd_recebida") or 0),
            "qtd_aprovada": float(ln.get("qtd_aprovada") or 0),
            "loc_destino": str(ln.get("loc_destino") or "").upper(),
            "inspecao": str(ln.get("inspecao") or "pending"),
            "lote": str(ln.get("lote") or ""),
            "serie": str(ln.get("serie") or ""),
        })
    if not linhas:
        raise ValueError("informe linhas ou operacao_id")

    op_id = str(body.get("operacao_id") or "").strip().upper()
    if op_id and not wms_operations.get_operacao(op_id):
        raise ValueError(f"operação não encontrada: {op_id}")

    row = {
        "id": rid,
        "origem": _norm_source(body.get("origem")),
        "operacao_id": op_id,
        "armazem": armazem,
        "documento_tipo": str(body.get("documento_tipo") or "").strip(),
        "documento_ref": str(body.get("documento_ref") or "").strip(),
        "parceiro": str(body.get("parceiro") or "").strip(),
        "transportadora": str(body.get("transportadora") or "").strip(),
        "veiculo": str(body.get("veiculo") or "").strip(),
        "status": "expected",
        "operador": str(body.get("operador") or "").strip(),
        "loc_recebimento": str(body.get("loc_recebimento") or "REC-DOCK-01").strip().upper(),
        "linhas": linhas,
        "historico": [_hist("expected", usuario, "criação")],
        "observacao": str(body.get("observacao") or "").strip(),
        "cancelamento_motivo": "",
        "origem_dado": "manual",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["recebimentos"].append(row)
    _save(data)
    return _enrich(row)


def _find(data, rid):
    key = str(rid or "").strip().upper()
    for i, r in enumerate(data.get("recebimentos") or []):
        if str(r.get("id") or "").upper() == key:
            return i, r
    return None, None


def confirm_line(rid, linha, qtd_recebida, usuario="", lote="", serie=""):
    data = _load_raw()
    idx, row = _find(data, rid)
    if row is None:
        raise ValueError("recebimento não encontrado")
    if row.get("status") not in ("unloading", "checking", "arrived"):
        raise ValueError("conferência só em arrived/unloading/checking")

    try:
        qr = float(qtd_recebida)
    except (TypeError, ValueError):
        raise ValueError("qtd_recebida deve ser número") from None
    if qr < 0:
        raise ValueError("qtd_recebida não pode ser negativa")

    found = None
    for ln in row.get("linhas") or []:
        if int(ln.get("linha") or 0) == int(linha):
            found = ln
            break
    if found is None:
        raise ValueError("linha não encontrada")

    found["qtd_recebida"] = qr
    if lote:
        found["lote"] = str(lote).strip()
    if serie:
        found["serie"] = str(serie).strip()

    if row.get("status") in ("arrived", "unloading"):
        row["status"] = "checking"
        hist = list(row.get("historico") or [])
        hist.append(_hist("checking", usuario, "conferência via linha"))
        row["historico"] = hist

    row["atualizado_em"] = _now()
    data["recebimentos"][idx] = row
    _save(data)
    return _enrich(row)


def inspect_line(rid, linha, resultado, usuario="", qtd_aprovada=None):
    data = _load_raw()
    idx, row = _find(data, rid)
    if row is None:
        raise ValueError("recebimento não encontrado")
    if row.get("status") not in ("checking", "inspection"):
        raise ValueError("inspeção só em checking/inspection")

    res = str(resultado or "").strip().lower()
    aliases = {"aprovado": "approved", "rejeitado": "rejected", "ok": "approved", "nok": "rejected"}
    res = aliases.get(res, res)
    if res not in ("approved", "rejected"):
        raise ValueError("resultado deve ser approved ou rejected")

    found = None
    for ln in row.get("linhas") or []:
        if int(ln.get("linha") or 0) == int(linha):
            found = ln
            break
    if found is None:
        raise ValueError("linha não encontrada")

    found["inspecao"] = res
    if qtd_aprovada is not None:
        try:
            found["qtd_aprovada"] = float(qtd_aprovada)
        except (TypeError, ValueError):
            raise ValueError("qtd_aprovada deve ser número") from None
    elif res == "approved":
        found["qtd_aprovada"] = float(found.get("qtd_recebida") or found.get("qtd_esperada") or 0)
    else:
        found["qtd_aprovada"] = 0

    if row.get("status") == "checking":
        row["status"] = "inspection"
        hist = list(row.get("historico") or [])
        hist.append(_hist("inspection", usuario, "inspeção via linha"))
        row["historico"] = hist

    row["atualizado_em"] = _now()
    data["recebimentos"][idx] = row
    _save(data)
    return _enrich(row)


def putaway_line(rid, linha, loc_destino, usuario=""):
    data = _load_raw()
    idx, row = _find(data, rid)
    if row is None:
        raise ValueError("recebimento não encontrado")
    if row.get("status") not in ("inspection", "putaway"):
        raise ValueError("put away só em inspection/putaway")

    loc = str(loc_destino or "").strip().upper()
    if not loc:
        raise ValueError("loc_destino obrigatório")

    found = None
    for ln in row.get("linhas") or []:
        if int(ln.get("linha") or 0) == int(linha):
            found = ln
            break
    if found is None:
        raise ValueError("linha não encontrada")
    if found.get("inspecao") == "rejected":
        raise ValueError("linha rejeitada não vai para put away")

    found["loc_destino"] = loc

    if row.get("status") == "inspection":
        row["status"] = "putaway"
        hist = list(row.get("historico") or [])
        hist.append(_hist("putaway", usuario, "início put away"))
        row["historico"] = hist

    row["atualizado_em"] = _now()
    data["recebimentos"][idx] = row
    _save(data)
    return _enrich(row)


def transition(rid, action, usuario="", motivo="", **extra):
    data = _load_raw()
    idx, row = _find(data, rid)
    if row is None:
        raise ValueError("recebimento não encontrado")

    act = str(action or "").strip().lower()
    cur = row.get("status") or "expected"
    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório para cancelar")
        row["cancelamento_motivo"] = reason
        nota = reason
    elif act == "arrive":
        if extra.get("transportadora") is not None:
            row["transportadora"] = str(extra.get("transportadora") or "").strip()
        if extra.get("veiculo") is not None:
            row["veiculo"] = str(extra.get("veiculo") or "").strip()
        if extra.get("operador"):
            row["operador"] = str(extra.get("operador") or "").strip()
        nota = "chegada"
    elif act == "start_inspect":
        pending_check = [
            l for l in (row.get("linhas") or [])
            if float(l.get("qtd_recebida") or 0) <= 0
        ]
        if pending_check:
            raise ValueError("confira todas as linhas (qtd_recebida) antes da inspeção")
        nota = act
    elif act == "start_putaway":
        pending_insp = [
            l for l in (row.get("linhas") or [])
            if l.get("inspecao") == "pending"
        ]
        if pending_insp:
            raise ValueError("finalize a inspeção de todas as linhas")
        nota = act
    elif act == "complete":
        need_loc = [
            l for l in (row.get("linhas") or [])
            if l.get("inspecao") == "approved" and not l.get("loc_destino")
        ]
        if need_loc:
            raise ValueError("defina loc_destino nas linhas aprovadas")
        # registra entrada no estoque por localização
        try:
            import inventory_mvp
            wms_items = []
            for l in (row.get("linhas") or []):
                if l.get("inspecao") != "approved":
                    continue
                q = float(l.get("qtd_aprovada") or l.get("qtd_recebida") or 0)
                if q <= 0:
                    continue
                wms_items.append({
                    "produto_id": str(l.get("produto_id") or ""),
                    "qty": q,
                    "location_id": l.get("loc_destino"),
                })
            if wms_items:
                eid = wms_warehouses.map_armazem_to_estabelecimento(row.get("armazem"))
                inventory_mvp.inventory_apply_receive({
                    "id": f"wms-{row['id']}",
                    "receiving_id": row["id"],
                    "warehouse_id": eid or row.get("armazem"),
                    "items": wms_items,
                    "requested_by": usuario,
                })
        except Exception:
            pass
        nota = act
    else:
        nota = str(motivo or act).strip()

    row["status"] = nxt
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(nxt, usuario, nota))
    row["historico"] = hist
    data["recebimentos"][idx] = row
    _save(data)
    return _enrich(row)
