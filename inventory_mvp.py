"""
Inventário MVP — ledger JSON (RFC-INVENTORY-MVP).

Fonte da verdade = movimentos. Saldo = cache. Promise só lê.
Warehouse = estabelecimento_id.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

MOVEMENTS_FILE = os.path.join(DATA_DIR, "inventory_movements.json")
BALANCES_FILE = os.path.join(DATA_DIR, "inventory_balances.json")
TRANSIT_FILE = os.path.join(DATA_DIR, "inventory_transit.json")
COUNTS_FILE = os.path.join(DATA_DIR, "inventory_counts.json")
LEGACY_ESTOQUE_FILE = os.path.join(DATA_DIR, "estoque.json")

# qty sempre positiva; sinal pelo tipo (adjust usa sign)
MOVEMENT_SIGN = {
    "sale": -1,
    "receive": 1,
    "transfer_out": -1,
    "transfer_in": 1,
    "transit": 0,
    "adjust": None,  # usa parâmetro sign (+1/-1)
    "concerto": -1,      # remessa para concerto (saída)
    "demonstracao": -1,  # produtos para demonstração (saída)
    "devolucao": 1,      # devolução (entrada)
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


def load_counts():
    data = _load(COUNTS_FILE, lambda: {"next_id": 1, "counts": []})
    if not isinstance(data.get("counts"), list):
        data["counts"] = []
    if not isinstance(data.get("next_id"), int):
        data["next_id"] = 1
    return data


def save_counts(data):
    _save(COUNTS_FILE, data)


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


def inventory_start_count(estabelecimento_id, *, nota=None, user_id=None):
    """Abre uma contagem física: snapshot do saldo atual por produto na loja."""
    eid = str(estabelecimento_id or "").strip()
    if not eid:
        raise ValueError("estabelecimento obrigatório")
    balances = load_balances()
    loja = (balances.get("por_estabelecimento") or {}).get(eid) or {}
    itens = [
        {"produto_id": str(pid), "qtd_sistema": _as_qty(qty), "qtd_contada": None, "divergencia": None}
        for pid, qty in loja.items()
    ]
    itens.sort(key=lambda i: i["produto_id"])
    counts = load_counts()
    cid = int(counts.get("next_id") or 1)
    count = {
        "id": cid,
        "estabelecimento_id": eid,
        "status": "aberto",
        "nota": nota,
        "itens": itens,
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "fechado_em": None,
        "resumo": None,
    }
    counts.setdefault("counts", []).append(count)
    counts["next_id"] = cid + 1
    save_counts(counts)
    return count


def inventory_get_count(count_id):
    counts = load_counts()
    return next(
        (c for c in counts.get("counts") or [] if int(c.get("id") or 0) == int(count_id)),
        None,
    )


def inventory_count_set_items(count_id, itens, *, user_id=None):
    """Registra quantidades contadas. itens: [{produto_id, qtd_contada}]."""
    counts = load_counts()
    count = next(
        (c for c in counts.get("counts") or [] if int(c.get("id") or 0) == int(count_id)),
        None,
    )
    if not count:
        raise ValueError("contagem não encontrada")
    if count.get("status") != "aberto":
        raise ValueError("contagem já fechada")
    mapa = {str(i.get("produto_id")): i for i in (count.get("itens") or [])}
    for item in itens or []:
        pid = str(item.get("produto_id") or "")
        if not pid:
            continue
        try:
            qc = float(item.get("qtd_contada"))
        except (TypeError, ValueError):
            raise ValueError(f"quantidade contada inválida para o produto {pid}")
        if pid not in mapa:
            mapa[pid] = {"produto_id": pid, "qtd_sistema": 0.0, "qtd_contada": None, "divergencia": None}
            count.setdefault("itens", []).append(mapa[pid])
        mapa[pid]["qtd_contada"] = _as_qty(qc)
        mapa[pid]["divergencia"] = None
    save_counts(counts)
    return count


def inventory_close_count(count_id, *, user_id=None):
    """Fecha a contagem: aplica ajustes (in/out) para cada divergência."""
    counts = load_counts()
    count = next(
        (c for c in counts.get("counts") or [] if int(c.get("id") or 0) == int(count_id)),
        None,
    )
    if not count:
        raise ValueError("contagem não encontrada")
    if count.get("status") != "aberto":
        raise ValueError("contagem já fechada")

    movements = load_movements()
    balances = load_balances()
    transit = load_transit()
    ajustes = []
    contados = 0
    for item in count.get("itens") or []:
        if item.get("qtd_contada") is None:
            continue
        contados += 1
        qc = _as_qty(item.get("qtd_contada"))
        qs = _as_qty(item.get("qtd_sistema") or 0)
        diff = round(qc - qs, QTY_DECIMALS)
        item["divergencia"] = diff
        if abs(diff) < 1e-9:
            continue
        sign = 1 if diff > 0 else -1
        r = inventory_apply_movement(
            "adjust",
            count["estabelecimento_id"],
            item["produto_id"],
            abs(diff),
            sign=sign,
            ref_tipo="inventory_count",
            ref_id=count_id,
            nota=f"contagem #{count_id}: sistema {qs} → contado {qc}",
            user_id=user_id,
            movements=movements,
            balances=balances,
            transit=transit,
            persist=False,
        )
        ajustes.append({
            "produto_id": item["produto_id"],
            "qtd_sistema": qs,
            "qtd_contada": qc,
            "divergencia": diff,
            "movement_id": r["movement_id"],
        })

    save_movements(movements)
    save_balances(balances)
    save_transit(transit)
    count["status"] = "fechado"
    count["fechado_em"] = datetime.now().isoformat(timespec="seconds")
    count["resumo"] = {
        "itens_contados": contados,
        "ajustes": ajustes,
        "total_ajustes": len(ajustes),
        "acuracia": round((contados - len(ajustes)) / contados * 100, 1) if contados else 100.0,
        "itens_sem_divergencia": contados - len(ajustes),
    }
    save_counts(counts)
    return count


# ── Análise de divergências e auditoria ───────────────────────────────

# Causas padrão de divergência (etapa 4 da rotina rotativa)
CAUSAS_DIVERGENCIA = {
    "erro_contagem": "Erro de contagem (recontar)",
    "quebra_perda": "Quebra / perda física",
    "extravio": "Extravio / sumiço",
    "erro_recebimento": "Erro no recebimento",
    "erro_baixa": "Erro de baixa / venda",
    "nao_localizado": "Item não localizado",
    "obsolescencia": "Obsolescência / vencido",
    "outros": "Outros",
}


def inventory_count_set_causas(count_id, causas, *, user_id=None):
    """
    Registra a causa de cada divergência antes do fechamento.
    causas: [{produto_id, causa, observacao}]
    Só aceita itens com divergência (qtd_contada registrada e ≠ sistema).
    """
    counts = load_counts()
    count = next(
        (c for c in counts.get("counts") or [] if int(c.get("id") or 0) == int(count_id)),
        None,
    )
    if not count:
        raise ValueError("contagem não encontrada")
    if count.get("status") != "aberto":
        raise ValueError("contagem já fechada")
    mapa = {str(i.get("produto_id")): i for i in (count.get("itens") or [])}
    registradas = 0
    for c in causas or []:
        pid = str(c.get("produto_id") or "")
        if not pid or pid not in mapa:
            continue
        item = mapa[pid]
        # só itens já contados com divergência
        if item.get("qtd_contada") is None:
            continue
        diff = round(
            _as_qty(item.get("qtd_contada")) - _as_qty(item.get("qtd_sistema") or 0),
            QTY_DECIMALS,
        )
        if abs(diff) < 1e-9:
            continue
        causa = str(c.get("causa") or "").strip()
        if causa and causa not in CAUSAS_DIVERGENCIA:
            causa = "outros"
        item["causa"] = causa or "outros"
        item["causa_label"] = CAUSAS_DIVERGENCIA.get(item["causa"], item["causa"])
        item["observacao"] = str(c.get("observacao") or "").strip()
        registradas += 1
    save_counts(counts)
    return {"registradas": registradas, "count": count}


def inventory_divergence_analysis(estabelecimento_id=None, produtos=None, *, min_ocorrencias=2):
    """
    Analisa divergências recorrentes: produtos que divergiram em 2+ ciclos
    fechados (sinal de problema crônico de processo) + causas mais frequentes.
    """
    counts = load_counts().get("counts") or []
    eid = str(estabelecimento_id or "").strip()
    prod_map = {str(p.get("id")): p for p in (produtos or []) if isinstance(p, dict)}

    por_produto = {}  # pid -> {ocorrencias, total_divergencia, causas, ciclos}
    por_causa = {}
    total_ajustes = 0
    total_valor_ajustado = 0.0
    for c in counts:
        if c.get("status") != "fechado":
            continue
        if eid and str(c.get("estabelecimento_id") or "") != eid:
            continue
        for item in c.get("itens") or []:
            diff = item.get("divergencia")
            if diff is None or abs(_as_qty(diff)) < 1e-9:
                continue
            pid = str(item.get("produto_id") or "")
            total_ajustes += 1
            custo = _as_qty((prod_map.get(pid) or {}).get("preco_custo") or 0)
            total_valor_ajustado += abs(_as_qty(diff)) * custo
            causa = str(item.get("causa") or "nao_informada")
            por_causa[causa] = por_causa.get(causa, 0) + 1
            rec = por_produto.setdefault(pid, {
                "produto_id": pid,
                "produto": (prod_map.get(pid) or {}).get("nome") or pid,
                "categoria": (prod_map.get(pid) or {}).get("categoria") or "",
                "ocorrencias": 0,
                "total_divergencia": 0.0,
                "causas": {},
                "ultimo_ciclo": None,
            })
            rec["ocorrencias"] += 1
            rec["total_divergencia"] = round(rec["total_divergencia"] + _as_qty(diff), QTY_DECIMALS)
            rec["causas"][causa] = rec["causas"].get(causa, 0) + 1
            cid = c.get("id")
            if rec["ultimo_ciclo"] is None or cid > rec["ultimo_ciclo"]:
                rec["ultimo_ciclo"] = cid

    recorrentes = [
        {**r, "causas": dict(sorted(r["causas"].items(), key=lambda kv: -kv[1]))}
        for r in por_produto.values()
        if r["ocorrencias"] >= max(1, int(min_ocorrencias or 2))
    ]
    recorrentes.sort(key=lambda r: (-r["ocorrencias"], -abs(r["total_divergencia"])))

    causas = [
        {"causa": k, "label": CAUSAS_DIVERGENCIA.get(k, k), "total": v}
        for k, v in sorted(por_causa.items(), key=lambda kv: -kv[1])
    ]
    return {
        "estabelecimento_id": eid or None,
        "total_ajustes": total_ajustes,
        "total_valor_ajustado": round(total_valor_ajustado, 2),
        "causas": causas,
        "recorrentes": recorrentes,
    }


def inventory_count_audit(count_id, produtos=None):
    """
    Relatório de auditoria de uma contagem (documentação p/ controles internos):
    dados gerais + itens com divergência e causa + resumo por causa.
    """
    counts = load_counts().get("counts") or []
    count = next((c for c in counts if int(c.get("id") or 0) == int(count_id)), None)
    if not count:
        raise ValueError("contagem não encontrada")
    prod_map = {str(p.get("id")): p for p in (produtos or []) if isinstance(p, dict)}
    r = count.get("resumo") or {}

    itens = []
    for item in count.get("itens") or []:
        pid = str(item.get("produto_id") or "")
        qc = item.get("qtd_contada")
        row = {
            "produto_id": pid,
            "produto": (prod_map.get(pid) or {}).get("nome") or pid,
            "categoria": item.get("categoria") or (prod_map.get(pid) or {}).get("categoria") or "",
            "localizacao": item.get("localizacao") or (prod_map.get(pid) or {}).get("localizacao") or "",
            "qtd_sistema": item.get("qtd_sistema"),
            "qtd_contada": qc,
            "divergencia": item.get("divergencia"),
            "causa": item.get("causa"),
            "causa_label": item.get("causa_label") or CAUSAS_DIVERGENCIA.get(item.get("causa"), ""),
            "observacao": item.get("observacao") or "",
        }
        itens.append(row)

    por_causa = {}
    for it in itens:
        d = it["divergencia"]
        if d is None or abs(_as_qty(d)) < 1e-9:
            continue
        k = it["causa"] or "nao_informada"
        por_causa.setdefault(k, {"label": CAUSAS_DIVERGENCIA.get(k, k), "itens": 0, "valor": 0.0})
        por_causa[k]["itens"] += 1
        custo = _as_qty((prod_map.get(it["produto_id"]) or {}).get("preco_custo") or 0)
        por_causa[k]["valor"] = round(por_causa[k]["valor"] + abs(_as_qty(d)) * custo, 2)

    return {
        "id": count.get("id"),
        "estabelecimento_id": count.get("estabelecimento_id"),
        "modo": count.get("modo") or "anual",
        "escopo": count.get("escopo") or {"tipo": "completo"},
        "nota": count.get("nota") or "",
        "status": count.get("status"),
        "criado_em": count.get("criado_em"),
        "fechado_em": count.get("fechado_em"),
        "resumo": r,
        "itens": itens,
        "por_causa": [
            {"causa": k, **v}
            for k, v in sorted(por_causa.items(), key=lambda kv: -kv[1]["itens"])
        ],
    }


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


# ── KPIs, alertas e relatório ─────────────────────────────────────────


def _load_vendas_json():
    """Projeção de vendas (dados/vendas.json, gerada pelo COBOL)."""
    path = os.path.join(BASE_DIR, "dados", "vendas.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("vendas") if isinstance(data, dict) else (data or [])
    except (json.JSONDecodeError, OSError):
        return []


def inventory_vendas_por_produto(estabelecimento_id=None, produto_id=None, dias=None, vendas=None):
    """Soma unidades vendidas por produto no período (fonte: vendas.json)."""
    vendas = vendas if vendas is not None else _load_vendas_json()
    eid = str(estabelecimento_id or "").strip()
    pid_f = str(produto_id or "").strip()
    limite = None
    if dias:
        try:
            limite = (datetime.now() - timedelta(days=max(1, int(dias)))).date()
        except (TypeError, ValueError):
            limite = None
    por_prod = {}
    for v in vendas or []:
        if not isinstance(v, dict):
            continue
        data_v = str(v.get("data") or "")[:10]
        if limite:
            try:
                if datetime.strptime(data_v, "%Y-%m-%d").date() < limite:
                    continue
            except ValueError:
                continue
        for it in v.get("itens") or []:
            if not isinstance(it, dict):
                continue
            if eid and str(it.get("filial_id") or "").strip() and str(it.get("filial_id")) != eid:
                continue
            pid = str(it.get("prod_id") or it.get("produto_id") or "")
            if not pid:
                continue
            if pid_f and pid != pid_f:
                continue
            try:
                qtd = float(it.get("qtd") or 0)
            except (TypeError, ValueError):
                qtd = 0
            por_prod[pid] = por_prod.get(pid, 0.0) + qtd
    return por_prod


def inventory_kpis(estabelecimento_id=None, dias=30, produtos=None, vendas=None):
    """
    KPIs de inventário: valor de estoque, giro, cobertura (dias) e ruptura.
    produtos: lista com id, nome, preco_custo (opcional — usado p/ valor).
    """
    dias = max(1, int(dias or 30))
    produtos = produtos or []
    prod_map = {str(p.get("id")): p for p in produtos if isinstance(p, dict)}
    balances = load_balances()
    eid = str(estabelecimento_id or "").strip()

    # estoque atual: unidades e valor (saldo × preco_custo)
    loja_total = 0.0
    loja_valor = 0.0
    saldo_por_prod = {}
    if eid:
        loja = (balances.get("por_estabelecimento") or {}).get(eid) or {}
        for pid, qty in loja.items():
            q = _as_qty(qty)
            loja_total += q
            saldo_por_prod[str(pid)] = q
            custo = _as_qty((prod_map.get(str(pid)) or {}).get("preco_custo") or 0)
            loja_valor += q * custo
    else:
        for _eid, loja in (balances.get("por_estabelecimento") or {}).items():
            for pid, qty in loja.items():
                q = _as_qty(qty)
                loja_total += q
                saldo_por_prod[str(pid)] = saldo_por_prod.get(str(pid), 0.0) + q
                custo = _as_qty((prod_map.get(str(pid)) or {}).get("preco_custo") or 0)
                loja_valor += q * custo

    vendas = inventory_vendas_por_produto(
        estabelecimento_id=eid or None,
        dias=dias,
        vendas=vendas,
    )
    unidades_vendidas = sum(vendas.values())
    media_diaria = unidades_vendidas / dias

    estoque_medio = loja_total + unidades_vendidas / 2.0
    giro = round(unidades_vendidas / estoque_medio, 2) if estoque_medio > 0 else 0.0
    cobertura_dias = round(loja_total / media_diaria, 1) if media_diaria > 0 else None

    # ruptura: vendeu no período mas está sem saldo
    ruptura = []
    for pid, vendido in sorted(vendas.items(), key=lambda kv: -kv[1]):
        saldo = saldo_por_prod.get(pid, 0.0)
        if saldo <= 0:
            ruptura.append({
                "produto_id": pid,
                "produto": (prod_map.get(pid) or {}).get("nome") or pid,
                "vendido": round(vendido, QTY_DECIMALS),
                "saldo": saldo,
            })

    return {
        "dias": dias,
        "estabelecimento_id": eid or None,
        "unidades_estoque": round(loja_total, QTY_DECIMALS),
        "valor_estoque": round(loja_valor, 2),
        "unidades_vendidas": round(unidades_vendidas, QTY_DECIMALS),
        "media_diaria_vendas": round(media_diaria, QTY_DECIMALS),
        "giro": giro,
        "cobertura_dias": cobertura_dias,
        "ruptura": ruptura,
    }


def inventory_alerts(estabelecimento_id=None, produtos=None):
    """Produtos abaixo do estoque mínimo (estoque_min do cadastro) ou zerados."""
    produtos = produtos or []
    prod_map = {str(p.get("id")): p for p in produtos if isinstance(p, dict)}
    balances = load_balances()
    eid = str(estabelecimento_id or "").strip()

    lojas = {}
    if eid:
        lojas[eid] = (balances.get("por_estabelecimento") or {}).get(eid) or {}
    else:
        lojas = balances.get("por_estabelecimento") or {}

    alertas = []
    for pid, p in prod_map.items():
        try:
            minimo = _as_qty(p.get("estoque_min") or 0)
        except (TypeError, ValueError):
            minimo = 0.0
        if minimo <= 0:
            continue
        saldo = sum(_as_qty((loja or {}).get(pid) or 0) for loja in lojas.values())
        if saldo < minimo:
            alertas.append({
                "produto_id": pid,
                "produto": p.get("nome") or pid,
                "saldo": round(saldo, QTY_DECIMALS),
                "minimo": round(minimo, QTY_DECIMALS),
                "faltam": round(minimo - saldo, QTY_DECIMALS),
                "localizacao": p.get("localizacao") or "",
            })
    alertas.sort(key=lambda a: a["faltam"], reverse=True)
    return alertas


def inventory_movements_report(
    *,
    estabelecimento_id=None,
    produto_id=None,
    tipo=None,
    de=None,
    ate=None,
    limit=500,
):
    """
    Relatório de movimentação: filtros + totais de entrada/saída.
    de/ate no formato YYYY-MM-DD.
    """
    rows = list(load_movements().get("movements") or [])
    eid = str(estabelecimento_id or "").strip()
    pid = str(produto_id or "").strip()
    tipo_f = str(tipo or "").strip()

    if eid:
        rows = [m for m in rows if str(m.get("estabelecimento_id") or "") == eid]
    if pid:
        rows = [m for m in rows if str(m.get("produto_id") or "") == pid]
    if tipo_f:
        if tipo_f == "transfer":
            rows = [m for m in rows if m.get("tipo") in ("transfer_out", "transfer_in")]
        else:
            rows = [m for m in rows if m.get("tipo") == tipo_f]
    if de or ate:
        def _key(m):
            return str(m.get("at") or "")[:10]

        if de:
            rows = [m for m in rows if _key(m) >= str(de)[:10]]
        if ate:
            rows = [m for m in rows if _key(m) <= str(ate)[:10]]

    rows.sort(key=lambda m: m.get("id") or 0, reverse=True)
    rows = rows[: max(1, min(int(limit or 500), 2000))]

    total_entrada = 0.0
    total_saida = 0.0
    por_tipo = {}
    for m in rows:
        sign = MOVEMENT_SIGN.get(m.get("tipo"))
        if sign is None:
            try:
                sign = int(m.get("sign") or 1)
            except (TypeError, ValueError):
                sign = 1
        q = _as_qty(m.get("qty") or 0)
        if sign > 0:
            total_entrada += q
        elif sign < 0:
            total_saida += q
        t = m.get("tipo") or "?"
        por_tipo[t] = por_tipo.get(t, 0.0) + q

    return {
        "movements": rows,
        "total": len(rows),
        "totais": {
            "entrada": round(total_entrada, QTY_DECIMALS),
            "saida": round(total_saida, QTY_DECIMALS),
            "saldo_periodo": round(total_entrada - total_saida, QTY_DECIMALS),
        },
        "por_tipo": por_tipo,
    }


# ── Inventário rotativo (cycle counting) ──────────────────────────────

# Curva ABC — limites de valor acumulado (padrão 70/95) e periodicidade
ABC_LIMITS = {"A": 0.70, "B": 0.95}  # A até 70% do valor, B até 95%, resto C
ABC_PERIODICITY_DAYS = {"A": 7, "B": 30, "C": 60}
ABC_PERIODICITY_LABEL = {"A": "semanal", "B": "mensal", "C": "bimestral"}

# ── Agendamento de ciclos ─────────────────────────────────────────────
SCHEDULE_FILE = os.path.join(DATA_DIR, "inventory_schedule.json")

DIAS_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def inventory_schedule_default():
    """Agenda padrão: A semanal, B mensal, C bimestral."""
    return {
        "classes": {
            "A": {"periodicidade": "semanal", "dia_semana": 0, "dia_mes": 1, "ativo": True},
            "B": {"periodicidade": "mensal", "dia_semana": 0, "dia_mes": 1, "ativo": True},
            "C": {"periodicidade": "bimestral", "dia_semana": 0, "dia_mes": 1, "ativo": True},
        }
    }


def load_schedule():
    data = _load(SCHEDULE_FILE, inventory_schedule_default)
    if not isinstance(data, dict) or not isinstance(data.get("classes"), dict):
        data = inventory_schedule_default()
    for cls in ("A", "B", "C"):
        cfg = data.setdefault("classes", {}).setdefault(cls, {})
        cfg.setdefault("periodicidade", ABC_PERIODICITY_LABEL[cls])
        cfg.setdefault("dia_semana", 0)
        cfg.setdefault("dia_mes", 1)
        cfg.setdefault("ativo", True)
    return data


def save_schedule(schedule):
    _save(SCHEDULE_FILE, schedule)


def _proxima_data(classe, cfg=None, base=None):
    """Próxima data de contagem agendada para a classe (base = hoje por padrão)."""
    cfg = cfg or {}
    base = base or datetime.now()
    if not cfg.get("ativo", True):
        return None
    periodicidade = str(cfg.get("periodicidade") or ABC_PERIODICITY_LABEL.get(classe, "mensal"))
    if periodicidade == "semanal":
        dia = int(cfg.get("dia_semana") or 0)
        dias_ate = (dia - base.weekday()) % 7
        if dias_ate == 0:
            dias_ate = 7  # próximo ciclo é daqui a uma semana, não hoje
        return (base + timedelta(days=dias_ate)).date().isoformat()
    # mensal / bimestral
    dia_mes = max(1, min(int(cfg.get("dia_mes") or 1), 28))
    meses = 2 if periodicidade == "bimestral" else 1
    prox = base.replace(day=1) + timedelta(days=31 * meses)
    prox = prox.replace(day=dia_mes)
    return prox.date().isoformat()


def inventory_schedule_due(estabelecimento_id=None, produtos=None):
    """
    Agenda do inventário rotativo + itens vencidos por classe.
    Um item está vencido quando passou a periodicidade da classe sem contagem.
    """
    eid = str(estabelecimento_id or "").strip()
    schedule = load_schedule()
    abc = inventory_abc_classify(eid or None, produtos=produtos)
    last = _ultima_contagem_map(eid or None)
    hoje = datetime.now().date()

    classes = {}
    total_vencidos = 0
    proximos = []
    for cls in ("A", "B", "C"):
        cfg = schedule.get("classes", {}).get(cls, {})
        itens = [r for r in abc.get("itens") or [] if r["classe"] == cls]
        vencidos = [r for r in itens if r.get("vencido")]
        total_vencidos += len(vencidos)
        prox = _proxima_data(cls, cfg)
        if prox:
            proximos.append({"classe": cls, "data": prox, "periodicidade": cfg.get("periodicidade")})
        classes[cls] = {
            "periodicidade": cfg.get("periodicidade"),
            "dia_semana": cfg.get("dia_semana"),
            "dia_mes": cfg.get("dia_mes"),
            "ativo": bool(cfg.get("ativo", True)),
            "itens": len(itens),
            "vencidos": len(vencidos),
            "ultima_contagem": max(
                (r.get("ultima_contagem") or "" for r in itens),
                default="",
            ),
        }

    # primeiro vencido ordenado por classe (A primeiro)
    primeiro = None
    for cls in ("A", "B", "C"):
        if classes[cls]["vencidos"]:
            primeiro = cls
            break

    return {
        "estabelecimento_id": eid or None,
        "classes": classes,
        "proximos": sorted(proximos, key=lambda p: (p["data"], "ABC".index(p["classe"]))),
        "total_vencidos": total_vencidos,
        "primeiro_vencido": primeiro,
    }


def _ultima_contagem_map(estabelecimento_id=None):
    """Mapa produto_id → {contado_em, divergencia} do último ciclo fechado."""
    counts = load_counts().get("counts") or []
    eid = str(estabelecimento_id or "").strip()
    last = {}
    for c in counts:
        if c.get("status") != "fechado":
            continue
        if eid and str(c.get("estabelecimento_id") or "") != eid:
            continue
        for item in c.get("itens") or []:
            pid = str(item.get("produto_id") or "")
            if not pid:
                continue
            last[pid] = {
                "contado_em": c.get("fechado_em") or c.get("criado_em") or "",
                "divergencia": item.get("divergencia"),
            }
    return last


def _dias_desde(data_iso):
    if not data_iso:
        return None
    try:
        dt = datetime.fromisoformat(str(data_iso))
    except (TypeError, ValueError):
        return None
    return max(0, (datetime.now() - dt).days)


def inventory_abc_classify(
    estabelecimento_id=None,
    produtos=None,
    vendas=None,
    *,
    criterio="valor",
    dias=90,
):
    """
    Classifica os itens pela curva ABC (por valor de estoque ou giro).

    - criterio "valor": valor = saldo × preço de custo
    - criterio "giro": valor = unidades vendidas no período (vendas.json)
    - A: até 70% do valor acumulado (contagem semanal)
    - B: até 95% (mensal)
    - C: restante (bimestral)
    Retorna lista ordenada por valor desc com classe e periodicidade.
    """
    produtos = produtos or []
    eid = str(estabelecimento_id or "").strip()
    balances = load_balances()
    last = _ultima_contagem_map(eid or None)

    if criterio == "giro":
        vendas_map = inventory_vendas_por_produto(
            estabelecimento_id=eid or None,
            dias=dias,
            vendas=vendas,
        )

    rows = []
    for p in produtos:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "")
        if not pid:
            continue
        # saldo na loja (ou somado entre lojas se sem filtro)
        if eid:
            saldo = inventory_balance(eid, pid, balances=balances)
        else:
            saldo = sum(
                _as_qty((loja or {}).get(pid) or 0)
                for loja in (balances.get("por_estabelecimento") or {}).values()
            )
        if criterio == "giro":
            valor = _as_qty(vendas_map.get(pid) or 0)
        else:
            custo = _as_qty(p.get("preco_custo") or 0)
            valor = round(saldo * custo, 2)
        rows.append({
            "produto_id": pid,
            "produto": p.get("nome") or pid,
            "categoria": p.get("categoria") or "",
            "localizacao": p.get("localizacao") or "",
            "saldo": round(saldo, QTY_DECIMALS),
            "valor": valor,
            "classe": None,
            "pct_acumulado": None,
            "ultima_contagem": (last.get(pid) or {}).get("contado_em") or "",
            "dias_desde_contagem": _dias_desde((last.get(pid) or {}).get("contado_em")),
            "divergencia": (last.get(pid) or {}).get("divergencia"),
        })

    # ignora itens sem valor (zerados/sem custo) na classificação
    rows = [r for r in rows if r["valor"] > 0]
    rows.sort(key=lambda r: r["valor"], reverse=True)
    total = sum(r["valor"] for r in rows) or 1.0
    acum = 0.0
    for r in rows:
        pct_antes = acum / total
        acum += r["valor"]
        pct = acum / total
        r["pct_acumulado"] = round(pct * 100, 1)
        # o item que cruza o limite entra na faixa (ex.: um único item > 70% é A)
        if pct <= ABC_LIMITS["A"] or pct_antes < ABC_LIMITS["A"]:
            r["classe"] = "A"
        elif pct <= ABC_LIMITS["B"] or pct_antes < ABC_LIMITS["B"]:
            r["classe"] = "B"
        else:
            r["classe"] = "C"
        r["periodicidade"] = ABC_PERIODICITY_LABEL[r["classe"]]
        r["periodicidade_dias"] = ABC_PERIODICITY_DAYS[r["classe"]]
        # nunca contado (None) também é vencido — precisa de contagem
        r["vencido"] = (
            r["dias_desde_contagem"] is None
            or r["dias_desde_contagem"] > r["periodicidade_dias"]
        )

    # resumo por classe
    resumo = {}
    for cls in ("A", "B", "C"):
        itens = [r for r in rows if r["classe"] == cls]
        resumo[cls] = {
            "itens": len(itens),
            "valor": round(sum(r["valor"] for r in itens), 2),
            "pct_valor": round(sum(r["valor"] for r in itens) / total * 100, 1) if itens else 0.0,
            "periodicidade": ABC_PERIODICITY_LABEL[cls],
            "periodicidade_dias": ABC_PERIODICITY_DAYS[cls],
            "vencidos": sum(1 for r in itens if r["vencido"]),
        }

    return {
        "criterio": criterio,
        "dias": dias,
        "estabelecimento_id": eid or None,
        "total_valor": round(total, 2),
        "itens": rows,
        "resumo": resumo,
    }


def inventory_start_cycle_count(
    estabelecimento_id,
    *,
    escopo=None,
    produtos=None,
    nota=None,
    user_id=None,
    max_itens=50,
):
    """
    Abre uma contagem rotativa: subconjunto do estoque (sem parar operação).

    escopo: {"tipo": "categoria" | "localizacao" | "classe" | "produtos" | "amostra", "valor": ...}
    - categoria: valor = nome da categoria (ex.: "Alimentacao")
    - localizacao: valor = endereço (ex.: "A1-01")
    - classe: valor = "A" | "B" | "C" (curva ABC por valor de estoque)
    - produtos: valor = lista de ids
    - amostra: valor = N itens (primeiros N ordenados por id)
    produtos: lista de dicts {id, nome, categoria, localizacao} para resolver o escopo.
    """
    eid = str(estabelecimento_id or "").strip()
    if not eid:
        raise ValueError("estabelecimento obrigatório")
    balances = load_balances()
    loja = (balances.get("por_estabelecimento") or {}).get(eid) or {}
    if not loja:
        raise ValueError(f"sem saldo registrado para {eid}")

    scope = dict(escopo or {})
    tipo = str(scope.get("tipo") or "amostra").strip().lower()
    valor = scope.get("valor")
    prods = produtos or []
    prod_map = {str(p.get("id")): p for p in prods if isinstance(p, dict)}

    if tipo == "produtos":
        ids = [str(x) for x in (valor if isinstance(valor, list) else [valor])]
    elif tipo == "categoria":
        cat = str(valor or "")
        ids = [str(p.get("id")) for p in prods if str(p.get("categoria") or "") == cat]
    elif tipo == "localizacao":
        loc = str(valor or "")
        ids = [str(p.get("id")) for p in prods if str(p.get("localizacao") or "") == loc]
    elif tipo == "classe":
        cls = str(valor or "").strip().upper()
        if cls not in ABC_PERIODICITY_DAYS:
            raise ValueError(f"classe ABC inválida: {valor}")
        abc = inventory_abc_classify(eid, produtos=prods)
        ids = [r["produto_id"] for r in abc["itens"] if r["classe"] == cls]
    else:  # amostra
        ids = sorted(loja.keys())
        try:
            n = max(1, min(int(valor or 10), len(ids)))
        except (TypeError, ValueError):
            n = min(10, len(ids))
        ids = ids[:n]

    itens = []
    for pid in ids:
        pid = str(pid)
        if pid not in loja:
            continue
        itens.append({
            "produto_id": pid,
            "qtd_sistema": _as_qty(loja.get(pid) or 0),
            "qtd_contada": None,
            "divergencia": None,
            "categoria": (prod_map.get(pid) or {}).get("categoria") or "",
            "localizacao": (prod_map.get(pid) or {}).get("localizacao") or "",
        })
    itens.sort(key=lambda i: i["produto_id"])
    if not itens:
        raise ValueError("nenhum item no escopo do ciclo")

    counts = load_counts()
    cid = int(counts.get("next_id") or 1)
    count = {
        "id": cid,
        "estabelecimento_id": eid,
        "status": "aberto",
        "modo": "rotativo",
        "escopo": {"tipo": tipo, "valor": valor},
        "nota": nota,
        "itens": itens,
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "fechado_em": None,
        "resumo": None,
    }
    counts.setdefault("counts", []).append(count)
    counts["next_id"] = cid + 1
    save_counts(counts)
    return count


def inventory_cycle_suggest(estabelecimento_id=None, produtos=None, *, max_itens=15):
    """
    Sugere o próximo ciclo rotativo com base na curva ABC:
    - prioriza classe A (semanal), depois B (mensal), depois C (bimestral)
    - dentro da classe: itens vencidos (sem contagem além da periodicidade),
      nunca contados ou com divergência no último ciclo vêm primeiro
    Retorna a sugestão agrupada pela classe mais crítica.
    """
    eid = str(estabelecimento_id or "").strip()
    last = _ultima_contagem_map(eid or None)
    abc = inventory_abc_classify(eid or None, produtos=produtos)
    classe_ord = {"A": 0, "B": 1, "C": 2}

    scored = []
    for r in abc.get("itens") or []:
        pid = r["produto_id"]
        info = last.get(pid)
        score = 0
        # vencido pela periodicidade da classe → prioridade máxima
        if r.get("vencido"):
            score += 300
        if not info:
            score += 100  # nunca contado
        if info and info.get("divergencia"):
            score += 80  # divergência no último ciclo
        days = r.get("dias_desde_contagem") or 0
        score += min(days, 60)
        # penalidade leve: mais dias desde a última contagem soma
        scored.append({
            **r,
            "score": score,
            "ultima_contagem": r.get("ultima_contagem") or "",
        })
    scored.sort(key=lambda s: (-classe_ord.get(s["classe"] or "C", 2), -s["score"], s["produto_id"]))

    # agrupa pela classe com maior prioridade que tenha itens
    sugestao = scored[:max_itens]
    classe = None
    for cls in ("A", "B", "C"):
        itens = [s for s in scored if s["classe"] == cls]
        if itens:
            classe = cls
            sugestao = itens[:max_itens]
            break

    return {
        "sugestao": sugestao,
        "classe": classe,
        "categoria": sugestao[0]["categoria"] if sugestao else None,
        "periodicidade": ABC_PERIODICITY_LABEL[classe] if classe else None,
        "periodicidade_dias": ABC_PERIODICITY_DAYS[classe] if classe else None,
        "total_candidatos": len(scored),
    }


def inventory_cycle_accuracy(estabelecimento_id=None):
    """Acuracidade por ciclo fechado (rotativo ou anual)."""
    counts = load_counts().get("counts") or []
    eid = str(estabelecimento_id or "").strip()
    rows = []
    for c in counts:
        if c.get("status") != "fechado":
            continue
        if eid and str(c.get("estabelecimento_id") or "") != eid:
            continue
        r = c.get("resumo") or {}
        itens = r.get("itens_contados") or 0
        ajustes = r.get("total_ajustes") or 0
        acuracia = round((itens - ajustes) / itens * 100, 1) if itens else 100.0
        rows.append({
            "id": c.get("id"),
            "estabelecimento_id": c.get("estabelecimento_id"),
            "modo": c.get("modo") or "anual",
            "escopo": c.get("escopo") or {"tipo": "completo"},
            "itens_contados": itens,
            "total_ajustes": ajustes,
            "acuracia": acuracia,
            "fechado_em": c.get("fechado_em") or "",
        })
    rows.sort(key=lambda r: r.get("fechado_em") or "", reverse=True)
    return rows


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