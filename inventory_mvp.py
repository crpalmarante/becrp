"""
Inventário MVP — ledger JSON (RFC-INVENTORY-MVP).

Fonte da verdade = movimentos. Saldo = cache. Promise só lê.
Warehouse = estabelecimento_id.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

MOVEMENTS_FILE = os.path.join(DATA_DIR, "inventory_movements.json")
BALANCES_FILE = os.path.join(DATA_DIR, "inventory_balances.json")
TRANSIT_FILE = os.path.join(DATA_DIR, "inventory_transit.json")
LEGACY_ESTOQUE_FILE = os.path.join(DATA_DIR, "estoque.json")

# qty sempre positiva; sinal pelo tipo (adjust usa sign)
MOVEMENT_SIGN = {
    "sale": -1,
    "receive": 1,
    "transfer_out": -1,
    "transfer_in": 1,
    "transit": 0,
    "adjust": None,  # usa parâmetro sign (+1/-1)
}

SLA_TRANSFERENCIA_HORAS = 2


def _load(path, default):
    if not os.path.exists(path):
        return default() if callable(default) else default
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else (default() if callable(default) else default)


def _save(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_movements():
    data = _load(MOVEMENTS_FILE, lambda: {"next_id": 1, "movements": []})
    if not isinstance(data.get("movements"), list):
        data["movements"] = []
    if not isinstance(data.get("next_id"), int):
        data["next_id"] = 1
    return data


def save_movements(data):
    _save(MOVEMENTS_FILE, data)


def load_balances():
    data = _load(
        BALANCES_FILE,
        lambda: {"por_estabelecimento": {}, "atualizado_em": None, "sla_transferencia_horas": SLA_TRANSFERENCIA_HORAS},
    )
    if not isinstance(data.get("por_estabelecimento"), dict):
        data["por_estabelecimento"] = {}
    if "sla_transferencia_horas" not in data:
        data["sla_transferencia_horas"] = SLA_TRANSFERENCIA_HORAS
    return data


def save_balances(data):
    data["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    _save(BALANCES_FILE, data)


def load_transit():
    data = _load(TRANSIT_FILE, lambda: {"itens": []})
    if not isinstance(data.get("itens"), list):
        data["itens"] = []
    return data


def save_transit(data):
    _save(TRANSIT_FILE, data)


QTY_DECIMALS = 3


def _as_qty(val, default=0.0):
    try:
        q = float(val)
    except (TypeError, ValueError):
        return float(default)
    return round(q, QTY_DECIMALS)


def inventory_balance(estabelecimento_id, produto_id, balances=None, *, location_id=None):
    balances = balances if balances is not None else load_balances()
    eid = str(estabelecimento_id or "").strip()
    pid = str(produto_id)
    if location_id:
        loc = str(location_id)
        locs = (balances.get("por_localizacao") or {}).get(eid) or {}
        prod_locs = locs.get(loc) or {}
        try:
            return _as_qty(prod_locs.get(pid, 0) or 0)
        except (TypeError, ValueError):
            return 0.0
    loja = (balances.get("por_estabelecimento") or {}).get(eid) or {}
    try:
        return _as_qty(loja.get(pid, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _set_balance(balances, estabelecimento_id, produto_id, qty, *, location_id=None):
    eid = str(estabelecimento_id or "").strip()
    pid = str(produto_id)
    q = max(0.0, _as_qty(qty))
    # total por estabelecimento
    lojas = balances.setdefault("por_estabelecimento", {})
    loja = dict(lojas.get(eid) or {})
    loja[pid] = q
    lojas[eid] = loja
    if location_id:
        loc = str(location_id)
        locs = balances.setdefault("por_localizacao", {})
        loc_map = dict(locs.get(eid) or {})
        prod_map = dict(loc_map.get(loc) or {})
        prod_map[pid] = q
        loc_map[loc] = prod_map
        locs[eid] = loc_map


def _apply_delta(balances, estabelecimento_id, produto_id, delta, *, location_id=None):
    atual = inventory_balance(estabelecimento_id, produto_id, balances=balances, location_id=location_id)
    _set_balance(balances, estabelecimento_id, produto_id, atual + _as_qty(delta), location_id=location_id)


def rebuild_balances_from_ledger():
    """Reconstrói cache a partir do ledger (fonte da verdade)."""
    mov = load_movements()
    balances = {
        "por_estabelecimento": {},
        "por_localizacao": {},
        "sla_transferencia_horas": SLA_TRANSFERENCIA_HORAS,
        "atualizado_em": None,
    }
    for m in mov.get("movements") or []:
        tipo = m.get("tipo")
        sign = MOVEMENT_SIGN.get(tipo)
        if sign is None:
            sign = int(m.get("sign") or 1)
        if sign == 0:
            continue
        eid = m.get("estabelecimento_id")
        pid = m.get("produto_id")
        qty = _as_qty(m.get("qty") or 0)
        loc = m.get("location_id")
        if not eid or not pid or qty <= 0:
            continue
        _apply_delta(balances, eid, pid, sign * qty, location_id=loc)
    save_balances(balances)
    return balances


def inventory_apply_movement(
    tipo,
    estabelecimento_id,
    produto_id,
    qty,
    *,
    ref_tipo=None,
    ref_id=None,
    group_id=None,
    nota=None,
    user_id=None,
    sign=None,
    transit_meta=None,
    location_id=None,
    movements=None,
    balances=None,
    transit=None,
    persist=True,
):
    """
    Registra um movimento e atualiza cache.
    qty > 0. Para adjust, passe sign=+1 ou -1.
    transit_meta: dict opcional {origem, destino_estabelecimento_id, eta_horas}
    """
    tipo = str(tipo or "").strip()
    if tipo not in MOVEMENT_SIGN:
        raise ValueError(f"tipo de movimento inválido: {tipo}")
    eid = str(estabelecimento_id or "").strip()
    pid = str(produto_id)
    q = _as_qty(qty)
    if q <= 0:
        raise ValueError("qty deve ser positiva")
    if tipo != "transit" and not eid:
        raise ValueError("estabelecimento_id obrigatório")

    dir_sign = MOVEMENT_SIGN[tipo]
    if dir_sign is None:
        dir_sign = int(sign if sign is not None else 1)
        if dir_sign not in (-1, 1):
            raise ValueError("adjust exige sign +1 ou -1")

    movements = movements if movements is not None else load_movements()
    balances = balances if balances is not None else load_balances()
    transit = transit if transit is not None else load_transit()

    mid = int(movements.get("next_id") or 1)
    entry = {
        "id": mid,
        "tipo": tipo,
        "estabelecimento_id": eid or None,
        "produto_id": pid,
        "qty": q,
        "at": datetime.now().isoformat(timespec="seconds"),
        "ref_tipo": ref_tipo,
        "ref_id": str(ref_id) if ref_id is not None else None,
        "group_id": group_id,
        "nota": nota,
        "user_id": user_id,
        "location_id": location_id,
    }
    if tipo == "adjust":
        entry["sign"] = dir_sign

    movements["movements"].append(entry)
    movements["next_id"] = mid + 1

    if dir_sign != 0 and eid:
        _apply_delta(balances, eid, pid, dir_sign * q, location_id=location_id)

    transit_id = None
    if tipo == "transit":
        meta = transit_meta or {}
        destino = str(meta.get("destino_estabelecimento_id") or eid or "").strip()
        transit_id = str(uuid.uuid4())[:8]
        transit.setdefault("itens", []).append({
            "id": transit_id,
            "produto_id": pid,
            "qty": q,
            "origem": meta.get("origem") or "",
            "destino_estabelecimento_id": destino,
            "eta_horas": int(meta.get("eta_horas") or 24),
            "status": "open",
            "movement_id": mid,
        })

    if persist:
        save_movements(movements)
        save_balances(balances)
        save_transit(transit)

    return {
        "movement_id": mid,
        "transit_id": transit_id,
        "balance": inventory_balance(eid, pid, balances=balances, location_id=location_id) if eid else None,
    }


def inventory_apply_sale(estabelecimento_id, linhas, venda_id=None, user_id=None):
    """
    Aplica linhas do pedido ao ledger:
    - qtd > 0 → movimento sale (baixa)
    - troca / qtd < 0 → receive (devolução ao estoque)
    """
    eid = str(estabelecimento_id or "").strip()
    if not eid or not linhas:
        return []
    movements = load_movements()
    balances = load_balances()
    transit = load_transit()
    ids = []
    for line in linhas:
        if not isinstance(line, dict):
            continue
        if line.get("servico"):
            continue
        pid = str(line.get("id") or line.get("produto_id") or "")
        if not pid:
            continue
        try:
            qtd = float(line.get("qtd") or line.get("quantidade") or 0)
        except (TypeError, ValueError):
            qtd = 0
        is_return = bool(line.get("troca")) or qtd < 0
        q_abs = abs(qtd)
        if q_abs <= 0:
            continue
        dec = 1 if line.get("peso") and q_abs < 1 else int(round(q_abs))
        if dec <= 0:
            continue
        if is_return:
            r = inventory_apply_movement(
                "receive",
                eid,
                pid,
                dec,
                ref_tipo="troca",
                ref_id=venda_id,
                nota=line.get("obs") or "devolução POS",
                user_id=user_id,
                movements=movements,
                balances=balances,
                transit=transit,
                persist=False,
            )
            ids.append(r["movement_id"])
            continue
        # não deixa saldo negativo na venda
        atual = inventory_balance(eid, pid, balances=balances)
        dec = min(dec, atual) if atual >= 0 else 0
        if dec <= 0:
            continue
        r = inventory_apply_movement(
            "sale",
            eid,
            pid,
            dec,
            ref_tipo="venda",
            ref_id=venda_id,
            user_id=user_id,
            movements=movements,
            balances=balances,
            transit=transit,
            persist=False,
        )
        ids.append(r["movement_id"])
    save_movements(movements)
    save_balances(balances)
    save_transit(transit)
    return ids


def inventory_apply_receive(request):
    """
    RFC-4009 — InventoryRequest mínimo.
    request: {id, receiving_id, warehouse_id, items:[{produto_id|id, qty|quantidade}], requested_by?}
    """
    req = request if isinstance(request, dict) else {}
    warehouse = str(req.get("warehouse_id") or req.get("estabelecimento_id") or "").strip()
    items = req.get("items") or req.get("produtos") or []
    receiving_id = req.get("receiving_id") or req.get("id")
    user_id = req.get("requested_by")
    if not warehouse:
        return {"status": "Failed", "errors": ["warehouse_id obrigatório"], "movement_ids": []}

    movements = load_movements()
    balances = load_balances()
    transit = load_transit()
    movement_ids = []
    errors = []
    for it in items:
        if not isinstance(it, dict):
            continue
        pid = str(it.get("produto_id") or it.get("id") or "")
        q = _as_qty(it.get("qty") or it.get("quantidade") or 0)
        if not pid or q <= 0:
            errors.append(f"item inválido: {it}")
            continue
        r = inventory_apply_movement(
            "receive",
            warehouse,
            pid,
            q,
            ref_tipo="receiving",
            ref_id=receiving_id,
            user_id=user_id,
            location_id=it.get("location_id"),
            movements=movements,
            balances=balances,
            transit=transit,
            persist=False,
        )
        movement_ids.append(r["movement_id"])
        # fecha trânsito aberto do mesmo produto/destino, se houver
        for t in transit.get("itens") or []:
            if (
                t.get("status") == "open"
                and str(t.get("produto_id")) == pid
                and str(t.get("destino_estabelecimento_id") or "") in ("", warehouse)
            ):
                t["status"] = "closed"
                t["closed_by_movement_id"] = r["movement_id"]

    save_movements(movements)
    save_balances(balances)
    save_transit(transit)
    status = "Completed" if movement_ids and not errors else ("Failed" if not movement_ids else "Completed")
    return {
        "request_id": req.get("id"),
        "status": status,
        "movement_ids": movement_ids,
        "processed_items": len(movement_ids),
        "errors": errors,
        "warnings": [],
        "completed_at": datetime.now().isoformat(timespec="seconds"),
    }


def inventory_transfer(origem, destino, linhas, *, user_id=None, nota=None):
    """Par transfer_out + transfer_in com mesmo group_id."""
    o = str(origem or "").strip()
    d = str(destino or "").strip()
    if not o or not d or o == d:
        raise ValueError("origem e destino distintos obrigatórios")
    group_id = str(uuid.uuid4())[:8]
    movements = load_movements()
    balances = load_balances()
    transit = load_transit()
    ids = []
    for line in linhas or []:
        pid = str(line.get("produto_id") or line.get("id") or "")
        q = int(round(float(line.get("qty") or line.get("quantidade") or 0)))
        if not pid or q <= 0:
            continue
        atual = inventory_balance(o, pid, balances=balances)
        if q > atual:
            raise ValueError(f"estoque insuficiente em {o} para produto {pid} (tem {atual}, pediu {q})")
        r_out = inventory_apply_movement(
            "transfer_out", o, pid, q,
            ref_tipo="transfer", ref_id=group_id, group_id=group_id,
            nota=nota, user_id=user_id,
            movements=movements, balances=balances, transit=transit, persist=False,
        )
        r_in = inventory_apply_movement(
            "transfer_in", d, pid, q,
            ref_tipo="transfer", ref_id=group_id, group_id=group_id,
            nota=nota, user_id=user_id,
            movements=movements, balances=balances, transit=transit, persist=False,
        )
        ids.extend([r_out["movement_id"], r_in["movement_id"]])
    if not ids:
        raise ValueError("nenhum item válido para transferir")
    save_movements(movements)
    save_balances(balances)
    save_transit(transit)
    return {"group_id": group_id, "movement_ids": ids}


def inventory_adjust(estabelecimento_id, produto_id, qty, *, direcao="in", nota=None, user_id=None):
    """Ajuste auditável. direcao: in (+ ) ou out (−)."""
    eid = str(estabelecimento_id or "").strip()
    pid = str(produto_id)
    try:
        q = int(round(float(qty)))
    except (TypeError, ValueError):
        q = 0
    if not eid or not pid or q <= 0:
        raise ValueError("estabelecimento, produto e qty > 0 obrigatórios")
    d = str(direcao or "in").strip().lower()
    if d in ("out", "-", "saida", "saída", "down"):
        sign = -1
        atual = inventory_balance(eid, pid)
        if q > atual:
            raise ValueError(f"ajuste de saída maior que saldo ({atual})")
    else:
        sign = 1
    return inventory_apply_movement(
        "adjust",
        eid,
        pid,
        q,
        sign=sign,
        ref_tipo="adjust",
        ref_id=None,
        nota=nota or "ajuste manual",
        user_id=user_id,
    )


def list_recent_movements(limit=50, estabelecimento_id=None, produto_id=None):
    mov = load_movements().get("movements") or []
    eid = str(estabelecimento_id or "").strip()
    pid = str(produto_id or "").strip()
    rows = list(mov)
    if eid:
        rows = [m for m in rows if str(m.get("estabelecimento_id") or "") == eid]
    if pid:
        rows = [m for m in rows if str(m.get("produto_id") or "") == pid]
    rows.sort(key=lambda m: m.get("id") or 0, reverse=True)
    return rows[: max(1, min(int(limit or 50), 200))]


def inventory_promise(estabelecimento_id, produto_id, *, empresas=None, balances=None, transit=None):
    """
    Promise Engine — mesma UX do POS:
    local → branch → transit → none
    """
    empresas = empresas if empresas is not None else {}
    balances = balances if balances is not None else load_balances()
    transit = transit if transit is not None else load_transit()
    eid = str(estabelecimento_id or "").strip()
    pid = str(produto_id)
    sla = int(balances.get("sla_transferencia_horas") or SLA_TRANSFERENCIA_HORAS)

    local_qty = inventory_balance(eid, pid, balances=balances) if eid else 0
    if local_qty > 0:
        return {
            "stock": local_qty,
            "stockStatus": "local",
            "promise": {
                "tipo": "local",
                "label": "Disponível nesta loja",
                "horas": 0,
                "estabelecimento_id": eid,
                "estabelecimento_nome": (empresas.get(eid) or {}).get("nome") or eid,
            },
            "branches": [],
        }

    branches = []
    for other_id, loja in (balances.get("por_estabelecimento") or {}).items():
        if str(other_id) == eid:
            continue
        info = empresas.get(other_id) or {}
        if info.get("ativo") is False:
            continue
        try:
            qty = int((loja or {}).get(pid, 0) or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty > 0:
            nome = info.get("nome") or other_id
            branches.append({
                "estabelecimento_id": other_id,
                "estabelecimento_nome": nome,
                "stock": qty,
                "horas": sla,
                "label": f"Disponível em {nome} em ~{sla}h",
            })

    if branches:
        branches.sort(key=lambda b: (-b["stock"], b["horas"]))
        best = branches[0]
        return {
            "stock": 0,
            "stockStatus": "branch",
            "promise": {
                "tipo": "branch",
                "label": best["label"],
                "horas": best["horas"],
                "estabelecimento_id": best["estabelecimento_id"],
                "estabelecimento_nome": best["estabelecimento_nome"],
            },
            "branches": branches,
        }

    for t in transit.get("itens") or []:
        if t.get("status") != "open":
            continue
        if str(t.get("produto_id")) != pid:
            continue
        if int(t.get("qty") or 0) <= 0:
            continue
        destino = str(t.get("destino_estabelecimento_id") or "")
        if destino and eid and destino != eid:
            continue
        horas = int(t.get("eta_horas") or 24)
        return {
            "stock": 0,
            "stockStatus": "transit",
            "promise": {
                "tipo": "transit",
                "label": f"Em trânsito — chega em ~{horas}h",
                "horas": horas,
                "origem": t.get("origem") or "",
                "estabelecimento_id": eid,
            },
            "branches": [],
        }

    return {
        "stock": 0,
        "stockStatus": "none",
        "promise": {
            "tipo": "none",
            "label": "Sem previsão — ver similares",
            "horas": None,
        },
        "branches": [],
    }


def enriquecer_produtos_com_promise(produtos, estabelecimento_id, empresas=None):
    balances = load_balances()
    transit = load_transit()
    empresas = empresas if empresas is not None else {}
    out = []
    for p in produtos or []:
        item = dict(p)
        prom = inventory_promise(
            estabelecimento_id,
            item.get("id"),
            empresas=empresas,
            balances=balances,
            transit=transit,
        )
        item["stock"] = prom["stock"]
        item["stockStatus"] = prom["stockStatus"]
        item["promise"] = prom["promise"]
        item["promiseBranches"] = prom["branches"]
        out.append(item)
    return out


def migrate_from_estoque_if_needed(force=False):
    """
    Se o ledger estiver vazio e existir estoque.json legado, gera movimentos receive + transit.
    """
    mov = load_movements()
    if mov.get("movements") and not force:
        # garante balances alinhados
        if not load_balances().get("por_estabelecimento"):
            rebuild_balances_from_ledger()
        return {"migrated": False, "reason": "ledger já populado"}

    if not os.path.exists(LEGACY_ESTOQUE_FILE):
        if not mov.get("movements"):
            save_movements({"next_id": 1, "movements": []})
            save_balances({
                "por_estabelecimento": {},
                "sla_transferencia_horas": SLA_TRANSFERENCIA_HORAS,
                "atualizado_em": None,
            })
            save_transit({"itens": []})
        return {"migrated": False, "reason": "sem estoque.json"}

    with open(LEGACY_ESTOQUE_FILE, "r", encoding="utf-8") as f:
        legacy = json.load(f)

    sla = int((legacy.get("_meta") or {}).get("sla_transferencia_horas") or SLA_TRANSFERENCIA_HORAS)
    movements = {"next_id": 1, "movements": []}
    balances = {
        "por_estabelecimento": {},
        "sla_transferencia_horas": sla,
        "atualizado_em": None,
    }
    transit = {"itens": []}

    for eid, loja in (legacy.get("por_estabelecimento") or {}).items():
        for pid, qty in (loja or {}).items():
            try:
                q = int(qty or 0)
            except (TypeError, ValueError):
                q = 0
            if q <= 0:
                # zera explícito no cache para demos none
                _set_balance(balances, eid, pid, 0)
                continue
            inventory_apply_movement(
                "receive",
                eid,
                pid,
                q,
                ref_tipo="seed",
                ref_id="bootstrap-estoque.json",
                nota="migração estoque.json → ledger",
                movements=movements,
                balances=balances,
                transit=transit,
                persist=False,
            )

    for pid, tr in (legacy.get("transito") or {}).items():
        if not isinstance(tr, dict):
            continue
        try:
            q = int(tr.get("qty") or 0)
        except (TypeError, ValueError):
            q = 0
        if q <= 0:
            continue
        destino = str(tr.get("destino") or "").strip()
        inventory_apply_movement(
            "transit",
            destino,
            pid,
            q,
            ref_tipo="seed",
            ref_id="bootstrap-estoque.json",
            nota="migração trânsito legado",
            transit_meta={
                "origem": tr.get("origem") or "",
                "destino_estabelecimento_id": destino,
                "eta_horas": int(tr.get("eta_horas") or 24),
            },
            movements=movements,
            balances=balances,
            transit=transit,
            persist=False,
        )

    save_movements(movements)
    save_balances(balances)
    save_transit(transit)

    # marca legado
    legacy["_meta"] = dict(legacy.get("_meta") or {})
    legacy["_meta"]["deprecated"] = True
    legacy["_meta"]["nota"] = (
        "LEGADO — migrado para inventory_movements/balances/transit. "
        "Não gravar aqui; ver RFC-INVENTORY-MVP."
    )
    _save(LEGACY_ESTOQUE_FILE, legacy)

    return {
        "migrated": True,
        "movements": len(movements["movements"]),
        "transit_open": sum(1 for t in transit["itens"] if t.get("status") == "open"),
    }


# Bootstrap automático ao importar (idempotente)
_BOOT = migrate_from_estoque_if_needed()
