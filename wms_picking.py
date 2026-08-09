"""
WMS — Picking & Packing (RFC-9006 MVP).

Listas de separação e volumes de embalagem.
Fonte: dados/wms_picking.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import wms_operations
import wms_warehouses

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_picking.json")

STRATEGIES = {
    "single": "Pedido único",
    "batch": "Batch",
    "wave": "Wave",
    "zone": "Zona",
}

PICK_STATUS = {
    "open": "Aberta",
    "picking": "Em picking",
    "picked": "Separada",
    "packing": "Em packing",
    "packed": "Embalada",
    "ready_ship": "Pronta p/ expedição",
    "closed": "Fechada",
    "cancelled": "Cancelada",
}

PKG_STATUS = {
    "open": "Aberta",
    "sealed": "Lacrada",
    "ready": "Pronta",
    "shipped": "Expedida",
    "cancelled": "Cancelada",
}

LINE_STATUS = {
    "pending": "Pendente",
    "picked": "Separada",
    "short": "Falta",
}

PICK_TRANSITIONS = {
    ("open", "start_pick"): "picking",
    ("open", "cancel"): "cancelled",
    ("picking", "complete_pick"): "picked",
    ("picking", "cancel"): "cancelled",
    ("picked", "start_pack"): "packing",
    ("packing", "complete_pack"): "packed",
    ("packed", "ready_ship"): "ready_ship",
    ("ready_ship", "close"): "closed",
}

PKG_TRANSITIONS = {
    ("open", "seal"): "sealed",
    ("open", "cancel"): "cancelled",
    ("sealed", "ready"): "ready",
    ("sealed", "cancel"): "cancelled",
    ("ready", "ship"): "shipped",
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
    data.setdefault("pick_lists", [])
    data.setdefault("packages", [])
    data.setdefault("seq_pick", len(data["pick_lists"]))
    data.setdefault("seq_pkg", len(data["packages"]))
    if not data["pick_lists"] and not data["packages"]:
        return ensure_seed()
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total_pick"] = len(data.get("pick_lists") or [])
    data["total_pkg"] = len(data.get("packages") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _hist(status, usuario="", nota=""):
    return {
        "status": status,
        "em": _now(),
        "usuario": str(usuario or "").strip(),
        "nota": str(nota or "").strip(),
    }


def _next_pick_id(data):
    seq = int(data.get("seq_pick") or 0) + 1
    data["seq_pick"] = seq
    return f"PK-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def _next_pkg_id(data):
    seq = int(data.get("seq_pkg") or 0) + 1
    data["seq_pkg"] = seq
    return f"PKG-{datetime.now().strftime('%Y%m%d')}-{seq:04d}"


def _norm_strategy(val):
    s = str(val or "").strip().lower()
    aliases = {
        "unico": "single",
        "único": "single",
        "pedido": "single",
        "lote": "batch",
        "onda": "wave",
        "zona": "zone",
    }
    s = aliases.get(s, s) or "single"
    if s not in STRATEGIES:
        raise ValueError("estrategia deve ser: single, batch, wave ou zone")
    return s


def ensure_seed():
    wms_operations.ensure_seed()
    now = _now()
    pick = {
        "id": "PK-SEED-0001",
        "estrategia": "single",
        "operacao_ids": ["OP-SEED-0002"],
        "armazem": "DC-01",
        "status": "picking",
        "operador": "bruno",
        "documento_ref": "PV-100",
        "parceiro": "Cliente Demo",
        "linhas": [
            {
                "linha": 1,
                "produto_id": "1",
                "produto": "Produto demo",
                "qtd": 2,
                "qtd_feita": 0,
                "loc_origem": "PCK-01",
                "status": "pending",
            }
        ],
        "rota": ["PCK-01"],
        "historico": [
            _hist("open", "seed", "criação"),
            _hist("picking", "seed", "iniciada"),
        ],
        "observacao": "Seed — picking da expedição demo",
        "origem": "seed",
        "criado_em": now,
        "atualizado_em": now,
    }
    data = {
        "seq_pick": 1,
        "seq_pkg": 0,
        "atualizado_em": now,
        "pick_lists": [pick],
        "packages": [],
        "total_pick": 1,
        "total_pkg": 0,
    }
    _save(data)
    return data


def _enrich_pick(row):
    out = dict(row)
    out["estrategia_label"] = STRATEGIES.get(out.get("estrategia"), out.get("estrategia") or "")
    out["status_label"] = PICK_STATUS.get(out.get("status"), out.get("status") or "")
    linhas = []
    for ln in out.get("linhas") or []:
        ll = dict(ln)
        ll["status_label"] = LINE_STATUS.get(ll.get("status"), ll.get("status") or "")
        linhas.append(ll)
    out["linhas"] = linhas
    out["linhas_count"] = len(linhas)
    out["pendentes"] = sum(1 for l in linhas if l.get("status") == "pending")
    st = out.get("status")
    out["acoes"] = [a for (fr, a), _to in PICK_TRANSITIONS.items() if fr == st]
    pkgs = [
        p
        for p in (_load_raw().get("packages") or [])
        if str(p.get("pick_list_id") or "").upper() == str(out.get("id") or "").upper()
    ]
    out["packages_count"] = len(pkgs)
    return out


def _enrich_pkg(row):
    out = dict(row)
    out["status_label"] = PKG_STATUS.get(out.get("status"), out.get("status") or "")
    out["itens_count"] = len(out.get("itens") or [])
    st = out.get("status")
    out["acoes"] = [a for (fr, a), _to in PKG_TRANSITIONS.items() if fr == st]
    return out


def meta():
    data = _load_raw()
    return {
        "total_pick": len(data.get("pick_lists") or []),
        "total_pkg": len(data.get("packages") or []),
        "estrategias": STRATEGIES,
        "status_pick": PICK_STATUS,
        "status_pkg": PKG_STATUS,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_pick_lists(q=None, status=None, armazem=None, estrategia=None):
    rows = list(_load_raw().get("pick_lists") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("documento_ref") or "").lower()
            or qq in str(r.get("parceiro") or "").lower()
            or qq in str(r.get("operador") or "").lower()
            or any(qq in str(oid).lower() for oid in (r.get("operacao_ids") or []))
        ]
    if status:
        st = str(status).strip().lower()
        if st not in PICK_STATUS:
            raise ValueError("status de picking inválido")
        rows = [r for r in rows if r.get("status") == st]
    if armazem:
        ak = str(armazem).strip().upper()
        rows = [r for r in rows if str(r.get("armazem") or "").upper() == ak]
    if estrategia:
        es = _norm_strategy(estrategia)
        rows = [r for r in rows if r.get("estrategia") == es]
    order = {s: i for i, s in enumerate(PICK_STATUS)}
    rows.sort(key=lambda r: (order.get(r.get("status"), 99), str(r.get("id") or "")))
    return {
        "total": len(_load_raw().get("pick_lists") or []),
        "filtrado": len(rows),
        "estrategias": STRATEGIES,
        "status_opcoes": PICK_STATUS,
        "pick_lists": [_enrich_pick(r) for r in rows],
    }


def get_pick_list(pick_id):
    key = str(pick_id or "").strip().upper()
    for r in _load_raw().get("pick_lists") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich_pick(r)
    return None


def create_from_operation(operacao_id, estrategia="single", usuario="", operador=""):
    op = wms_operations.get_operacao(operacao_id)
    if not op:
        raise ValueError("operação não encontrada")
    if op.get("status") in ("draft", "cancelled", "closed"):
        raise ValueError("operação em status inadequado para picking")
    if not wms_warehouses.get_armazem(op.get("armazem")):
        raise ValueError("armazém da operação inválido")

    data = _load_raw()
    pid = _next_pick_id(data)
    linhas = []
    for i, ln in enumerate(op.get("linhas") or [], start=1):
        linhas.append({
            "linha": i,
            "produto_id": str(ln.get("produto_id") or ""),
            "produto": str(ln.get("produto") or "item"),
            "qtd": float(ln.get("qtd") or 0),
            "qtd_feita": 0,
            "loc_origem": str(ln.get("loc_origem") or "").upper(),
            "status": "pending",
        })
    if not linhas:
        linhas = [{
            "linha": 1,
            "produto_id": "",
            "produto": "item",
            "qtd": 1,
            "qtd_feita": 0,
            "loc_origem": "",
            "status": "pending",
        }]

    rota = sorted({l["loc_origem"] for l in linhas if l.get("loc_origem")})
    row = {
        "id": pid,
        "estrategia": _norm_strategy(estrategia),
        "operacao_ids": [op["id"]],
        "armazem": str(op.get("armazem") or "").upper(),
        "status": "open",
        "operador": str(operador or op.get("responsavel") or "").strip(),
        "documento_ref": str(op.get("documento_ref") or ""),
        "parceiro": str(op.get("parceiro") or ""),
        "linhas": linhas,
        "rota": rota,
        "historico": [_hist("open", usuario, f"gerada de {op['id']}")],
        "observacao": "",
        "origem": "generated",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["pick_lists"].append(row)
    _save(data)
    return _enrich_pick(row)


def create_pick_list(payload, usuario=""):
    body = dict(payload or {})
    op_ids = body.get("operacao_ids") or []
    if isinstance(op_ids, str):
        op_ids = [p.strip() for p in op_ids.replace(";", ",").split(",") if p.strip()]
    if body.get("operacao_id") and not op_ids:
        op_ids = [body.get("operacao_id")]
    if len(op_ids) == 1:
        return create_from_operation(
            op_ids[0],
            estrategia=body.get("estrategia") or "single",
            usuario=usuario,
            operador=body.get("operador") or "",
        )
    if not op_ids:
        raise ValueError("informe operacao_id ou operacao_ids")

    # batch/wave: merge lines from multiple ops
    data = _load_raw()
    pid = _next_pick_id(data)
    estrategia = _norm_strategy(body.get("estrategia") or "batch")
    linhas = []
    armazem = ""
    docs = []
    parceiros = []
    for oid in op_ids:
        op = wms_operations.get_operacao(oid)
        if not op:
            raise ValueError(f"operação não encontrada: {oid}")
        if not armazem:
            armazem = str(op.get("armazem") or "").upper()
        elif str(op.get("armazem") or "").upper() != armazem:
            raise ValueError("todas as operações devem ser do mesmo armazém")
        docs.append(str(op.get("documento_ref") or oid))
        if op.get("parceiro"):
            parceiros.append(op["parceiro"])
        for ln in op.get("linhas") or []:
            linhas.append({
                "linha": len(linhas) + 1,
                "produto_id": str(ln.get("produto_id") or ""),
                "produto": str(ln.get("produto") or "item"),
                "qtd": float(ln.get("qtd") or 0),
                "qtd_feita": 0,
                "loc_origem": str(ln.get("loc_origem") or "").upper(),
                "status": "pending",
                "operacao_id": op["id"],
            })
    rota = sorted({l["loc_origem"] for l in linhas if l.get("loc_origem")})
    row = {
        "id": pid,
        "estrategia": estrategia,
        "operacao_ids": [str(x).upper() for x in op_ids],
        "armazem": armazem,
        "status": "open",
        "operador": str(body.get("operador") or "").strip(),
        "documento_ref": ", ".join(docs),
        "parceiro": ", ".join(parceiros),
        "linhas": linhas,
        "rota": rota,
        "historico": [_hist("open", usuario, "batch/wave")],
        "observacao": str(body.get("observacao") or "").strip(),
        "origem": "manual",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["pick_lists"].append(row)
    _save(data)
    return _enrich_pick(row)


def confirm_line(pick_id, linha, qtd_feita, usuario=""):
    data = _load_raw()
    key = str(pick_id or "").strip().upper()
    idx = None
    row = None
    for i, r in enumerate(data.get("pick_lists") or []):
        if str(r.get("id") or "").upper() == key:
            idx = i
            row = r
            break
    if row is None:
        raise ValueError("lista de picking não encontrada")
    if row.get("status") not in ("open", "picking"):
        raise ValueError("só é possível confirmar linhas em open/picking")

    try:
        qf = float(qtd_feita)
    except (TypeError, ValueError):
        raise ValueError("qtd_feita deve ser número") from None
    if qf < 0:
        raise ValueError("qtd_feita não pode ser negativa")

    found = None
    for ln in row.get("linhas") or []:
        if int(ln.get("linha") or 0) == int(linha):
            found = ln
            break
    if found is None:
        raise ValueError("linha não encontrada")

    expected = float(found.get("qtd") or 0)
    found["qtd_feita"] = qf
    if qf >= expected and expected > 0:
        found["status"] = "picked"
    elif qf > 0:
        found["status"] = "short"
    else:
        found["status"] = "pending"

    if row.get("status") == "open":
        row["status"] = "picking"
        hist = list(row.get("historico") or [])
        hist.append(_hist("picking", usuario, "início via confirmação"))
        row["historico"] = hist

    row["atualizado_em"] = _now()
    data["pick_lists"][idx] = row
    _save(data)
    return _enrich_pick(row)


def transition_pick(pick_id, action, usuario="", motivo=""):
    data = _load_raw()
    key = str(pick_id or "").strip().upper()
    idx = None
    row = None
    for i, r in enumerate(data.get("pick_lists") or []):
        if str(r.get("id") or "").upper() == key:
            idx = i
            row = r
            break
    if row is None:
        raise ValueError("lista de picking não encontrada")

    act = str(action or "").strip().lower()
    cur = row.get("status") or "open"
    nxt = PICK_TRANSITIONS.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")

    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório para cancelar")
        row["cancelamento_motivo"] = reason
        nota = reason
    elif act == "complete_pick":
        pending = [l for l in (row.get("linhas") or []) if l.get("status") == "pending"]
        if pending:
            raise ValueError("ainda há linhas pendentes — confirme ou marque falta")
        # Baixa estoque por localização (picking → saída)
        try:
            import inventory_mvp
            import wms_warehouses
            eid = wms_warehouses.map_armazem_to_estabelecimento(row.get("armazem"))
            inv_items = []
            for l in (row.get("linhas") or []):
                if l.get("status") not in ("picked", "short"):
                    continue
                q = float(l.get("qtd_feita") or 0)
                if q <= 0:
                    continue
                inv_items.append({
                    "produto_id": str(l.get("produto_id") or ""),
                    "qty": q,
                    "location_id": l.get("loc_origem") or "PCK-01",
                })
            if inv_items:
                inventory_mvp.inventory_apply_sale(
                    eid or row.get("armazem"),
                    inv_items,
                    venda_id=row.get("documento_ref") or row.get("id"),
                    user_id=usuario,
                )
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
    data["pick_lists"][idx] = row
    _save(data)
    return _enrich_pick(row)


def list_packages(q=None, status=None, pick_list_id=None):
    rows = list(_load_raw().get("packages") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("id") or "").lower()
            or qq in str(r.get("pick_list_id") or "").lower()
            or qq in str(r.get("etiqueta") or "").lower()
        ]
    if status:
        st = str(status).strip().lower()
        if st not in PKG_STATUS:
            raise ValueError("status de package inválido")
        rows = [r for r in rows if r.get("status") == st]
    if pick_list_id:
        pk = str(pick_list_id).strip().upper()
        rows = [r for r in rows if str(r.get("pick_list_id") or "").upper() == pk]
    rows.sort(key=lambda r: str(r.get("id") or ""))
    return {
        "total": len(_load_raw().get("packages") or []),
        "filtrado": len(rows),
        "status_opcoes": PKG_STATUS,
        "packages": [_enrich_pkg(r) for r in rows],
    }


def get_package(pkg_id):
    key = str(pkg_id or "").strip().upper()
    for r in _load_raw().get("packages") or []:
        if str(r.get("id") or "").upper() == key:
            return _enrich_pkg(r)
    return None


def create_package(payload, usuario=""):
    body = dict(payload or {})
    pick_id = str(body.get("pick_list_id") or "").strip().upper()
    pick = get_pick_list(pick_id)
    if not pick:
        raise ValueError("lista de picking não encontrada")
    if pick.get("status") not in ("picked", "packing", "packed"):
        raise ValueError("packing só após picking completo (ou em packing)")

    data = _load_raw()
    # ensure pick is in packing when first package created
    for i, r in enumerate(data.get("pick_lists") or []):
        if str(r.get("id") or "").upper() == pick_id and r.get("status") == "picked":
            r["status"] = "packing"
            hist = list(r.get("historico") or [])
            hist.append(_hist("packing", usuario, "início packing"))
            r["historico"] = hist
            r["atualizado_em"] = _now()
            data["pick_lists"][i] = r
            break

    itens = body.get("itens")
    if not itens:
        # default: all picked lines
        itens = [
            {
                "produto_id": l.get("produto_id"),
                "produto": l.get("produto"),
                "qtd": l.get("qtd_feita") or l.get("qtd") or 0,
            }
            for l in (pick.get("linhas") or [])
            if l.get("status") in ("picked", "short")
        ]
    if not isinstance(itens, list) or not itens:
        raise ValueError("itens do volume obrigatórios")

    try:
        peso = float(body.get("peso_kg") if body.get("peso_kg") is not None else 0)
        vol = float(body.get("volume_m3") if body.get("volume_m3") is not None else 0)
    except (TypeError, ValueError):
        raise ValueError("peso_kg/volume_m3 devem ser números") from None

    pkg_id = _next_pkg_id(data)
    row = {
        "id": pkg_id,
        "pick_list_id": pick_id,
        "operacao_id": (pick.get("operacao_ids") or [""])[0],
        "etiqueta": str(body.get("etiqueta") or pkg_id).strip(),
        "peso_kg": peso,
        "volume_m3": vol,
        "itens": [
            {
                "produto_id": str(it.get("produto_id") or ""),
                "produto": str(it.get("produto") or "item"),
                "qtd": float(it.get("qtd") or 0),
            }
            for it in itens
            if isinstance(it, dict)
        ],
        "status": "open",
        "historico": [_hist("open", usuario, "criação")],
        "observacao": str(body.get("observacao") or "").strip(),
        "origem": "manual",
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["packages"].append(row)
    _save(data)
    return _enrich_pkg(row)


def transition_package(pkg_id, action, usuario="", motivo=""):
    data = _load_raw()
    key = str(pkg_id or "").strip().upper()
    idx = None
    row = None
    for i, r in enumerate(data.get("packages") or []):
        if str(r.get("id") or "").upper() == key:
            idx = i
            row = r
            break
    if row is None:
        raise ValueError("volume não encontrado")

    act = str(action or "").strip().lower()
    cur = row.get("status") or "open"
    mapping = {
        ("open", "seal"): "sealed",
        ("open", "cancel"): "cancelled",
        ("sealed", "ready"): "ready",
        ("sealed", "cancel"): "cancelled",
        ("ready", "ship"): "shipped",
    }
    nxt = mapping.get((cur, act))
    if not nxt:
        raise ValueError(f"ação '{act}' não permitida no status '{cur}'")
    if act == "cancel":
        reason = str(motivo or "").strip()
        if not reason:
            raise ValueError("motivo obrigatório")
        row["cancelamento_motivo"] = reason
        nota = reason
    else:
        nota = act

    row["status"] = nxt
    row["atualizado_em"] = _now()
    hist = list(row.get("historico") or [])
    hist.append(_hist(nxt, usuario, nota))
    row["historico"] = hist
    data["packages"][idx] = row
    _save(data)
    return _enrich_pkg(row)
