"""
Devolução de Compra.

Registra devoluções de mercadoria a fornecedores e estorna estoque.
Fonte: data/devolucoes_compra.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import inventory_mvp
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "devolucoes_compra.json")

STATUSES = ("rascunho", "concluido", "cancelado")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _load():
    if not os.path.exists(DATA_FILE):
        return {"next_id": 1, "devolucoes": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"next_id": 1, "devolucoes": []}
    data.setdefault("devolucoes", [])
    data.setdefault("next_id", 1)
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    jsonio.save(DATA_FILE, data)


def listar(*, status=None, pedido_id=None, recebimento_id=None):
    data = _load()
    rows = list(data.get("devolucoes") or [])
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if pedido_id is not None:
        rows = [r for r in rows if str(r.get("pedido_id")) == str(pedido_id)]
    if recebimento_id is not None:
        rows = [r for r in rows if str(r.get("recebimento_id")) == str(recebimento_id)]
    rows.sort(key=lambda r: r.get("id") or 0, reverse=True)
    return rows


def get(dev_id):
    for r in _load().get("devolucoes") or []:
        if str(r.get("id")) == str(dev_id):
            return r
    return None


def criar(payload, *, usuario=""):
    body = payload if isinstance(payload, dict) else {}
    eid = str(body.get("estabelecimento_id") or body.get("warehouse_id") or "").strip()
    if not eid:
        raise ValueError("estabelecimento_id obrigatório")

    itens = []
    for it in body.get("itens") or body.get("items") or []:
        pid = str(it.get("produto_id") or it.get("id") or "").strip()
        qtd = float(it.get("qtd") or it.get("quantidade") or 0)
        if not pid or qtd <= 0:
            continue
        itens.append({
            "produto_id": pid,
            "produto_nome": str(it.get("produto_nome") or it.get("nome") or "").strip(),
            "qtd": qtd,
            "uom": str(it.get("uom") or it.get("unidade") or "UN").strip() or "UN",
            "motivo_item": str(it.get("motivo_item") or "").strip(),
        })
    if not itens:
        raise ValueError("informe ao menos um item com qtd > 0")

    data = _load()
    did = int(data.get("next_id") or 1)
    row = {
        "id": did,
        "status": "rascunho",
        "estabelecimento_id": eid,
        "pedido_id": body.get("pedido_id") or body.get("pedido_compra_id"),
        "pedido_num": str(body.get("pedido_num") or "").strip(),
        "recebimento_id": body.get("recebimento_id"),
        "fornecedor_id": str(body.get("fornecedor_id") or "").strip(),
        "fornecedor": str(body.get("fornecedor") or body.get("fornecedor_nome") or "").strip(),
        "cnpj": "".join(c for c in str(body.get("cnpj") or "") if c.isdigit()),
        "data": str(body.get("data") or _today()),
        "motivo": str(body.get("motivo") or "").strip(),
        "autorizado_por": str(body.get("autorizado_por") or usuario or "").strip(),
        "itens": itens,
        "total_qtd": sum(i["qtd"] for i in itens),
        "created_at": _now(),
        "created_by": usuario,
        "completed_at": None,
        "completed_by": None,
        "events": [{"at": _now(), "tipo": "created", "by": usuario}],
    }
    data["devolucoes"].insert(0, row)
    data["next_id"] = did + 1
    _save(data)
    return row


def concluir(dev_id, *, usuario=""):
    data = _load()
    row = None
    for r in data.get("devolucoes") or []:
        if str(r.get("id")) == str(dev_id):
            row = r
            break
    if not row:
        raise ValueError("devolução não encontrada")
    if row.get("status") == "concluido":
        return row
    if row.get("status") == "cancelado":
        raise ValueError("devolução cancelada")

    eid = row.get("estabelecimento_id")
    if not eid:
        raise ValueError("estabelecimento_id obrigatório")

    movements = inventory_mvp.load_movements()
    balances = inventory_mvp.load_balances()
    transit = inventory_mvp.load_transit()
    movement_ids = []
    errors = []

    for it in row.get("itens") or []:
        pid = it.get("produto_id")
        qtd = float(it.get("qtd") or 0)
        if not pid or qtd <= 0:
            continue
        # estorno: sign=-1, tipo adjust
        res = inventory_mvp.inventory_apply_movement(
            "adjust",
            eid,
            pid,
            qtd,
            sign=-1,
            ref_tipo="devolucao_compra",
            ref_id=str(dev_id),
            nota=f"Devolução de compra #{dev_id}: {row.get('motivo')}",
            user_id=usuario,
            movements=movements,
            balances=balances,
            transit=transit,
            persist=False,
        )
        if isinstance(res, dict):
            movement_ids.append(res.get("movement_id"))
        else:
            errors.append(f"falha no item {pid}")

    if errors:
        raise ValueError("; ".join(errors))

    inventory_mvp.save_movements(movements)
    inventory_mvp.save_balances(balances)
    inventory_mvp.save_transit(transit)

    row["status"] = "concluido"
    row["completed_at"] = _now()
    row["completed_by"] = usuario
    row["movement_ids"] = movement_ids
    row.setdefault("events", []).append({"at": _now(), "tipo": "concluido", "by": usuario})
    _save(data)
    return row


def cancelar(dev_id, *, usuario=""):
    data = _load()
    for r in data.get("devolucoes") or []:
        if str(r.get("id")) == str(dev_id):
            if r.get("status") == "concluido":
                raise ValueError("não cancela devolução concluída")
            r["status"] = "cancelado"
            r["cancelled_at"] = _now()
            r["cancelled_by"] = usuario
            r.setdefault("events", []).append({"at": _now(), "tipo": "cancelado", "by": usuario})
            _save(data)
            return r
    raise ValueError("devolução não encontrada")
