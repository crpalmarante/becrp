"""
WMS — Shipping Process (RFC-9008 MVP).

Ciclo físico de expedição no armazém (não substitui emissão fiscal).
Fonte: dados/wms_shipping.json

Importante: WMS NÃO baixa estoque de venda.
A baixa comercial fica no POS/Sales. No despacho, apenas gera Delivery Order.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import wms_operations
import wms_picking
import wms_warehouses

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_shipping.json")

DESTINOS = {
    "customer": "Cliente",
    "transfer": "Transferência",
    "repair": "Reparo / assistência",
    "other": "Outro",
}

STATUSES = {
    "created": "Criada",
    "planned": "Planejada",
    "picking": "Em picking",
    "checking": "Conferência",
    "packing": "Em packing",
    "loading": "Carregamento",
    "dispatched": "Despachada",
    "completed": "Concluída",
    "cancelled": "Cancelada",
}

LINE_STATUS = {
    "pending": "Pendente",
    "checked": "Conferida",
    "short": "Falta",
}

TRANSITIONS = {
    ("created", "plan"): "planned",
    ("created", "cancel"): "cancelled",
    ("planned", "start_pick"): "picking",
    ("planned", "cancel"): "cancelled",
    ("picking", "start_check"): "checking",
    ("picking", "cancel"): "cancelled",
    ("checking", "start_pack"): "packing",
    ("checking", "cancel"): "cancelled",
    ("packing", "start_load"): "loading",
    ("packing", "cancel"): "cancelled",
    ("loading", "dispatch"): "dispatched",
    ("loading", "cancel"): "cancelled",
    ("dispatched", "complete"): "completed",
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
    if not isinstance(data.get("expedicoes"), list):
        data["expedicoes"] = []
    if data.get("seq") is None:
        data["seq"] = len(data["expedicoes"])
    if not data["expedicoes"]:
        return ensure_seed()
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("expedicoes") or [])
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
    return f"SH-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def _norm_destino(val):
    s = str(val or "").strip().lower()
    aliases = {
        "cliente": "customer",
        "venda": "customer",
        "transferencia": "transfer",
        "transferência": "transfer",
        "reparo": "repair",
        "assistencia": "repair",
        "assistência": "repair",
        "outro": "other",
    }
    s = aliases.get(s, s) or "customer"
    if s not in DESTINOS:
        raise ValueError("destino deve ser: customer, transfer, repair ou other")
    return s


def ensure_seed():
    wms_operations.ensure_seed()
    now = _now()
    row = {
        "id": "SH-SEED-0001",
        "destino": "customer",
        "operacao_id": "OP-SEED-0002",
        "pick_list_id": "PK-SEED-0001",
        "package_ids": [],
        "armazem": "DC-01",
        "documento_tipo": "pedido_venda",
        "documento_ref": "PV-100",
        "parceiro": "Cliente Demo",
        "transportadora": "",
        "veiculo": "",
        "motorista": "",
        "rota": "",
        "status": "created",
        "operador": "bruno",
        "loc_expedicao": "SHP-STAGE",
        "linhas": [
            {
                "linha": 1,
                "produto_id": "1",
                "produto": "Produto demo",
                "qtd_esperada": 2,
                "qtd_conferida": 0,
                "loc_origem": "PCK-01",
                "status": "pending",
            }
        ],
        "historico": [_hist("created", "seed", "criação")],
        "observacao": "Seed — expedição cliente demo",
        "cancelamento_motivo": "",
        "origem_dado": "seed",
        "criado_em": now,
        "atualizado_em": now,
    }
    data = {"seq": 1, "atualizado_em": now, "expedicoes": [row], "total": 1}
    _save(data)
    return data


def _enrich(row):
    out = dict(row)
    out["destino_label"] = DESTINOS.get(out.get("destino"), out.get("destino") or "")
    out["status_label"] = STATUSES.get(out.get("status"), out.get("status") or "")
    linhas = []
    for ln in out.get("linhas") or []:
        ll = dict(ln)
        ll["status_label"] = LINE_STATUS.get(ll.get("status"), ll.get("status") or "")
        linhas.append(ll)
    out["linhas"] = linhas
    out["linhas_count"] = len(linhas)
    out["pendentes"] = sum(1 for l in linhas if l.get("status") == "pending")
    out["faltas"] = sum(1 for l in linhas if l.get("status") == "short")
    st = out.get("status")
    out["acoes"] = [a for (fr, a), _to in TRANSITIONS.items() if fr == st]
    wh = wms_warehouses.get_armazem(out.get("armazem"))
    out["armazem_nome"] = (wh or {}).get("nome") or ""
    return out


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("expedicoes") or []),
        "destinos": DESTINOS,
        "status": STATUSES,
        "linha_status": LINE_STATUS,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_expedicoes(q=None, status=None, destino=None, armazem=None):
    rows = list(_load_raw().get("expedicoes") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("documento_ref") or "").lower()
            or qq in str(r.get("parceiro") or "").lower()
            or qq in str(r.get("operacao_id") or "").lower()
            or qq in str(r.get("pick_list_id") or "").lower()
            or qq in str(r.get("transportadora") or "").lower()
        ]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [r for r in rows if r.get("status") == st]
    if destino:
        dg = _norm_destino(destino)
        rows = [r for r in rows if r.get("destino") == dg]
    if armazem:
        ak = str(armazem).strip().upper()
        rows = [r for r in rows if str(r.get("armazem") or "").upper() == ak]
    order = {s: i for i, s in enumerate(STATUSES)}
    rows.sort(key=lambda r: (order.get(r.get("status"), 99), str(r.get("id") or "")))
    return {
        "total": len(_load_raw().get("expedicoes") or []),
        "filtrado": len(rows),
        "destinos": DESTINOS,
        "status_opcoes": STATUSES,
        "expedicoes": [_enrich(r) for r in rows],
    }


def get_expedicao(sid):
    key = str(sid or "").strip().upper()
    for r in _load_raw().get("expedicoes") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich(r)
    return None


def create_from_operation(operacao_id, usuario="", destino="customer"):
    op = wms_operations.get_operacao(operacao_id)
    if not op:
        raise ValueError("operação não encontrada")
    if op.get("status") in ("cancelled", "closed"):
        raise ValueError("operação cancelada/fechada")
    data = _load_raw()
    sid = _next_id(data)
    linhas = []
    for i, ln in enumerate(op.get("linhas") or [], start=1):
        linhas.append({
            "linha": i,
            "produto_id": str(ln.get("produto_id") or ""),
            "produto": str(ln.get("produto") or "item"),
            "qtd_esperada": float(ln.get("qtd") or 0),
            "qtd_conferida": 0,
            "loc_origem": str(ln.get("loc_origem") or "").upper(),
            "status": "pending",
        })
    if not linhas:
        linhas = [{
            "linha": 1,
            "produto_id": "",
            "produto": "item",
            "qtd_esperada": 1,
            "qtd_conferida": 0,
            "loc_origem": "",
            "status": "pending",
        }]
    row = {
        "id": sid,
        "destino": _norm_destino(destino),
        "operacao_id": op["id"],
        "pick_list_id": "",
        "package_ids": [],
        "armazem": str(op.get("armazem") or "").upper(),
        "documento_tipo": str(op.get("documento_tipo") or ""),
        "documento_ref": str(op.get("documento_ref") or ""),
        "parceiro": str(op.get("parceiro") or ""),
        "transportadora": "",
        "veiculo": "",
        "motorista": "",
        "rota": "",
        "status": "created",
        "operador": str(op.get("responsavel") or "").strip(),
        "loc_expedicao": "SHP-STAGE",
        "linhas": linhas,
        "historico": [_hist("created", usuario, f"gerado de {op['id']}")],
        "observacao": "",
        "cancelamento_motivo": "",
        "origem_dado": "generated",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    if not wms_warehouses.get_armazem(row["armazem"]):
        raise ValueError("armazém inválido")
    data["expedicoes"].append(row)
    _save(data)
    return _enrich(row)


def create_from_pick_list(pick_list_id, usuario="", destino="customer"):
    pk = wms_picking.get_pick_list(pick_list_id)
    if not pk:
        raise ValueError("lista de picking não encontrada")
    if pk.get("status") in ("cancelled", "closed"):
        raise ValueError("picking cancelado/fechado")
    data = _load_raw()
    sid = _next_id(data)
    linhas = []
    for i, ln in enumerate(pk.get("linhas") or [], start=1):
        qtd = float(ln.get("qtd_feita") if ln.get("qtd_feita") is not None else ln.get("qtd") or 0)
        linhas.append({
            "linha": i,
            "produto_id": str(ln.get("produto_id") or ""),
            "produto": str(ln.get("produto") or "item"),
            "qtd_esperada": qtd or float(ln.get("qtd") or 0),
            "qtd_conferida": 0,
            "loc_origem": str(ln.get("loc_origem") or "").upper(),
            "status": "pending",
        })
    if not linhas:
        raise ValueError("picking sem linhas")
    ops = pk.get("operacao_ids") or []
    row = {
        "id": sid,
        "destino": _norm_destino(destino),
        "operacao_id": ops[0] if ops else "",
        "pick_list_id": pk["id"],
        "package_ids": [],
        "armazem": str(pk.get("armazem") or "").upper(),
        "documento_tipo": "",
        "documento_ref": str(pk.get("documento_ref") or ""),
        "parceiro": str(pk.get("parceiro") or ""),
        "transportadora": "",
        "veiculo": "",
        "motorista": "",
        "rota": "",
        "status": "created",
        "operador": str(pk.get("operador") or "").strip(),
        "loc_expedicao": "SHP-STAGE",
        "linhas": linhas,
        "historico": [_hist("created", usuario, f"gerado de {pk['id']}")],
        "observacao": "",
        "cancelamento_motivo": "",
        "origem_dado": "from_pick",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["expedicoes"].append(row)
    _save(data)
    return _enrich(row)


def create_expedicao(payload, usuario=""):
    body = dict(payload or {})
    if body.get("pick_list_id") and not body.get("linhas"):
        return create_from_pick_list(
            body.get("pick_list_id"),
            usuario=usuario,
            destino=body.get("destino") or "customer",
        )
    if body.get("operacao_id") and not body.get("linhas") and not body.get("pick_list_id"):
        return create_from_operation(
            body.get("operacao_id"),
            usuario=usuario,
            destino=body.get("destino") or "customer",
        )

    data = _load_raw()
    sid = str(body.get("id") or "").strip().upper() or _next_id(data)
    if any(str(r.get("id") or "").upper() == sid for r in data["expedicoes"]):
        raise ValueError(f"já existe expedição {sid}")

    armazem = str(body.get("armazem") or "").strip().upper()
    if not armazem or not wms_warehouses.get_armazem(armazem):
        raise ValueError("armazém obrigatório/válido")

    linhas_in = body.get("linhas") or []
    if isinstance(linhas_in, str):
        parsed = []
        for i, line in enumerate(linhas_in.split("\n"), start=1):
            parts = [p.strip() for p in line.split("|")]
            if not parts[0]:
                continue
            parsed.append({
                "linha": i,
                "produto": parts[0],
                "qtd_esperada": float(parts[1]) if len(parts) > 1 and parts[1] else 1,
                "qtd_conferida": 0,
                "loc_origem": (parts[2] if len(parts) > 2 else "").upper(),
                "produto_id": "",
                "status": "pending",
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
            "qtd_esperada": float(
                ln.get("qtd_esperada") if ln.get("qtd_esperada") is not None else ln.get("qtd") or 0
            ),
            "qtd_conferida": float(ln.get("qtd_conferida") or 0),
            "loc_origem": str(ln.get("loc_origem") or "").upper(),
            "status": str(ln.get("status") or "pending"),
        })
    if not linhas:
        raise ValueError("informe linhas, operacao_id ou pick_list_id")

    op_id = str(body.get("operacao_id") or "").strip().upper()
    if op_id and not wms_operations.get_operacao(op_id):
        raise ValueError(f"operação não encontrada: {op_id}")
    pick_id = str(body.get("pick_list_id") or "").strip().upper()
    if pick_id and not wms_picking.get_pick_list(pick_id):
        raise ValueError(f"picking não encontrado: {pick_id}")

    pkgs = body.get("package_ids") or []
    if isinstance(pkgs, str):
        pkgs = [p.strip() for p in pkgs.split(",") if p.strip()]

    row = {
        "id": sid,
        "destino": _norm_destino(body.get("destino")),
        "operacao_id": op_id,
        "pick_list_id": pick_id,
        "package_ids": [str(p).strip().upper() for p in pkgs],
        "armazem": armazem,
        "documento_tipo": str(body.get("documento_tipo") or "").strip(),
        "documento_ref": str(body.get("documento_ref") or "").strip(),
        "parceiro": str(body.get("parceiro") or "").strip(),
        "transportadora": str(body.get("transportadora") or "").strip(),
        "veiculo": str(body.get("veiculo") or "").strip(),
        "motorista": str(body.get("motorista") or "").strip(),
        "rota": str(body.get("rota") or "").strip(),
        "status": "created",
        "operador": str(body.get("operador") or "").strip(),
        "loc_expedicao": str(body.get("loc_expedicao") or "SHP-STAGE").strip().upper(),
        "linhas": linhas,
        "historico": [_hist("created", usuario, "criação")],
        "observacao": str(body.get("observacao") or "").strip(),
        "cancelamento_motivo": "",
        "origem_dado": "manual",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["expedicoes"].append(row)
    _save(data)
    return _enrich(row)


def _find(data, sid):
    key = str(sid or "").strip().upper()
    for i, r in enumerate(data.get("expedicoes") or []):
        if str(r.get("id") or "").upper() == key:
            return i, r
    return None, None


def confirm_line(sid, linha, qtd_conferida, usuario=""):
    data = _load_raw()
    idx, row = _find(data, sid)
    if row is None:
        raise ValueError("expedição não encontrada")
    if row.get("status") not in ("picking", "checking"):
        raise ValueError("conferência só em picking/checking")

    try:
        qc = float(qtd_conferida)
    except (TypeError, ValueError):
        raise ValueError("qtd_conferida deve ser número") from None
    if qc < 0:
        raise ValueError("qtd_conferida não pode ser negativa")

    found = None
    for ln in row.get("linhas") or []:
        if int(ln.get("linha") or 0) == int(linha):
            found = ln
            break
    if found is None:
        raise ValueError("linha não encontrada")

    expected = float(found.get("qtd_esperada") or 0)
    found["qtd_conferida"] = qc
    if qc < expected:
        found["status"] = "short"
    else:
        found["status"] = "checked"

    if row.get("status") == "picking":
        row["status"] = "checking"
        hist = list(row.get("historico") or [])
        hist.append(_hist("checking", usuario, "conferência via linha"))
        row["historico"] = hist

    row["atualizado_em"] = _now()
    data["expedicoes"][idx] = row
    _save(data)
    return _enrich(row)


def set_loading(sid, usuario="", **extra):
    data = _load_raw()
    idx, row = _find(data, sid)
    if row is None:
        raise ValueError("expedição não encontrada")
    if row.get("status") not in ("packing", "loading"):
        raise ValueError("dados de carga só em packing/loading")

    for field in ("transportadora", "veiculo", "motorista", "rota"):
        if extra.get(field) is not None:
            row[field] = str(extra.get(field) or "").strip()
    if extra.get("package_ids") is not None:
        pkgs = extra.get("package_ids") or []
        if isinstance(pkgs, str):
            pkgs = [p.strip() for p in pkgs.split(",") if p.strip()]
        row["package_ids"] = [str(p).strip().upper() for p in pkgs]

    if row.get("status") == "packing" and any(
        row.get(k) for k in ("transportadora", "veiculo", "motorista")
    ):
        row["status"] = "loading"
        hist = list(row.get("historico") or [])
        hist.append(_hist("loading", usuario, "dados de carga"))
        row["historico"] = hist

    row["atualizado_em"] = _now()
    data["expedicoes"][idx] = row
    _save(data)
    return _enrich(row)


def transition(sid, action, usuario="", motivo="", **extra):
    data = _load_raw()
    idx, row = _find(data, sid)
    if row is None:
        raise ValueError("expedição não encontrada")

    act = str(action or "").strip().lower()
    cur = row.get("status") or "created"
    nxt = TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório para cancelar")
        row["cancelamento_motivo"] = reason
        nota = reason
    elif act == "start_pack":
        pending = [l for l in (row.get("linhas") or []) if l.get("status") == "pending"]
        if pending:
            raise ValueError("confira todas as linhas antes do packing")
        nota = act
    elif act == "start_load":
        for field in ("transportadora", "veiculo", "motorista", "rota"):
            if extra.get(field) is not None:
                row[field] = str(extra.get(field) or "").strip()
        nota = act
    elif act == "dispatch":
        if not (row.get("transportadora") or row.get("veiculo")):
            raise ValueError("informe transportadora ou veículo antes do despacho")
        for field in ("transportadora", "veiculo", "motorista", "rota"):
            if extra.get(field) is not None:
                row[field] = str(extra.get(field) or "").strip()
        nota = "despacho"
    elif act == "complete":
        nota = act
    else:
        nota = str(motivo or act).strip()

    row["status"] = nxt
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(nxt, usuario, nota))
    row["historico"] = hist
    data["expedicoes"][idx] = row
    _save(data)
    out = _enrich(row)

    # Handoff → Delivery (sem tocar inventory)
    if nxt == "dispatched":
        try:
            import delivery_orders
            do, created = delivery_orders.ensure_from_shipping(row["id"], usuario=usuario)
            out["delivery_order_id"] = do.get("id")
            out["delivery_created"] = created
        except Exception as exc:  # noqa: BLE001 — despacho WMS não deve falhar por Delivery
            out["delivery_error"] = str(exc)
    return out
