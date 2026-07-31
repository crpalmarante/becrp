"""
Receiving MVP — coordenação de entrada de mercadorias (RFC-RECEIVING-MVP).

Não move estoque: na conclusão chama inventory_mvp.inventory_apply_receive.
Warehouse = estabelecimento_id.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import inventory_mvp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECEIVINGS_FILE = os.path.join(DATA_DIR, "receivings.json")

# draft → verified → completed | cancelled
STATUSES = ("draft", "verified", "completed", "cancelled")
ORIGENS = ("manual", "nfe", "transfer", "return", "adjustment")


def _load():
    if not os.path.exists(RECEIVINGS_FILE):
        return {"next_id": 1, "receivings": []}
    with open(RECEIVINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"next_id": 1, "receivings": []}
    if not isinstance(data.get("receivings"), list):
        data["receivings"] = []
    if not isinstance(data.get("next_id"), int):
        data["next_id"] = 1
    return data


def _save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RECEIVINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _normalize_items(items, allow_unmatched=False):
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        pid = str(it.get("produto_id") or it.get("id") or "").strip()
        try:
            expected = int(round(float(it.get("qty_expected") or it.get("qty") or it.get("quantidade") or 0)))
        except (TypeError, ValueError):
            expected = 0
        if expected <= 0:
            continue
        if not pid and not allow_unmatched:
            continue
        verified_raw = it.get("qty_verified")
        try:
            verified = int(round(float(verified_raw))) if verified_raw is not None else None
        except (TypeError, ValueError):
            verified = None
        row = {
            "produto_id": pid,
            "produto_nome": (it.get("produto_nome") or it.get("nome") or "").strip(),
            "qty_expected": expected,
            "qty_verified": verified,
            "unidade": (it.get("unidade") or "UN").strip() or "UN",
            "match": it.get("match") or ("ok" if pid else "none"),
        }
        if isinstance(it.get("nfe_item"), dict):
            row["nfe_item"] = it["nfe_item"]
        if isinstance(it.get("suggestions"), list):
            row["suggestions"] = it["suggestions"]
        out.append(row)
    return out


def unmatched_count(rec):
    n = 0
    for it in (rec or {}).get("items") or []:
        if not str(it.get("produto_id") or "").strip():
            n += 1
    return n


def list_receivings(estabelecimento_id=None, status=None):
    data = _load()
    rows = list(data.get("receivings") or [])
    eid = str(estabelecimento_id or "").strip()
    st = str(status or "").strip()
    if eid:
        rows = [r for r in rows if str(r.get("estabelecimento_id")) == eid]
    if st:
        rows = [r for r in rows if str(r.get("status")) == st]
    rows.sort(key=lambda r: r.get("id") or 0, reverse=True)
    return rows


def get_receiving(rid):
    rid = str(rid)
    for r in _load().get("receivings") or []:
        if str(r.get("id")) == rid:
            return r
    return None


def create_receiving(payload, user_id=None):
    body = payload if isinstance(payload, dict) else {}
    eid = str(body.get("estabelecimento_id") or body.get("warehouse_id") or "").strip()
    if not eid:
        raise ValueError("estabelecimento_id obrigatório")
    allow_unmatched = bool(body.get("allow_unmatched"))
    items = _normalize_items(body.get("items") or body.get("itens") or [], allow_unmatched=allow_unmatched)
    if not items:
        raise ValueError("informe ao menos um item com qty > 0")
    origem = str(body.get("origem") or "manual").strip().lower()
    if origem not in ORIGENS:
        origem = "manual"

    data = _load()
    rid = int(data.get("next_id") or 1)
    rec = {
        "id": rid,
        "status": "draft",
        "origem": origem,
        "estabelecimento_id": eid,
        "fornecedor_nome": (body.get("fornecedor_nome") or body.get("supplier") or "").strip(),
        "fornecedor_id": body.get("fornecedor_id") or body.get("partner_id"),
        "fornecedor_cnpj": (body.get("fornecedor_cnpj") or "").strip(),
        "documento_ref": (body.get("documento_ref") or body.get("document_ref") or "").strip(),
        "nota": (body.get("nota") or body.get("notes") or "").strip(),
        "items": items,
        "nfe": body.get("nfe") if isinstance(body.get("nfe"), dict) else None,
        "created_at": _now(),
        "created_by": user_id,
        "verified_at": None,
        "verified_by": None,
        "completed_at": None,
        "completed_by": None,
        "inventory": None,
        "events": [
            {"at": _now(), "tipo": "created", "by": user_id, "origem": origem},
        ],
    }
    data["receivings"].append(rec)
    data["next_id"] = rid + 1
    _save(data)
    return rec


def link_item_product(rid, item_index, produto_id, produto_nome=None, user_id=None, remember=True):
    """Vincula item sem match a um produto interno (RFC-4004) e grava vínculo fornecedor."""
    data = _load()
    rec = None
    for r in data.get("receivings") or []:
        if str(r.get("id")) == str(rid):
            rec = r
            break
    if not rec:
        raise ValueError("recebimento não encontrado")
    if rec.get("status") in ("completed", "cancelled"):
        raise ValueError("não altera itens neste status")
    items = rec.get("items") or []
    try:
        idx = int(item_index)
    except (TypeError, ValueError):
        raise ValueError("item_index inválido")
    if idx < 0 or idx >= len(items):
        raise ValueError("item_index fora do intervalo")
    pid = str(produto_id or "").strip()
    if not pid:
        raise ValueError("produto_id obrigatório")

    nome = (produto_nome or "").strip()
    if not nome:
        try:
            import cobol_bridge
            for p in cobol_bridge.produtos_listar() or []:
                if str(p.get("id")) == pid:
                    nome = p.get("nome") or ""
                    break
        except Exception:
            pass

    items[idx]["produto_id"] = pid
    if nome:
        items[idx]["produto_nome"] = nome
    items[idx]["match"] = "manual"
    items[idx].pop("suggestions", None)
    rec["items"] = items
    if isinstance(rec.get("nfe"), dict):
        rec["nfe"]["itens_sem_match"] = unmatched_count(rec)

    ref = None
    if remember:
        try:
            import product_localization
            ref = product_localization.remember_from_receiving_item(
                rec, items[idx], pid, produto_nome=nome or None, user_id=user_id
            )
        except Exception:
            ref = None

    event = {
        "at": _now(), "tipo": "product_linked", "by": user_id,
        "item_index": idx, "produto_id": pid,
    }
    if ref:
        event["ref_id"] = ref.get("id")
    rec.setdefault("events", []).append(event)
    _save(data)
    return rec


def verify_receiving(rid, payload=None, user_id=None):
    """Conferência física: grava qty_verified e status=verified."""
    data = _load()
    rec = None
    for r in data.get("receivings") or []:
        if str(r.get("id")) == str(rid):
            rec = r
            break
    if not rec:
        raise ValueError("recebimento não encontrado")
    if rec.get("status") in ("completed", "cancelled"):
        raise ValueError(f"não é possível conferir status={rec.get('status')}")
    if unmatched_count(rec):
        raise ValueError(
            f"{unmatched_count(rec)} item(ns) sem produto vinculado — localize antes de conferir"
        )

    body = payload if isinstance(payload, dict) else {}
    overrides = {}
    for it in body.get("items") or []:
        if not isinstance(it, dict):
            continue
        # index-based or produto_id
        if "item_index" in it:
            try:
                overrides[("idx", int(it["item_index"]))] = int(round(float(
                    it.get("qty_verified") if it.get("qty_verified") is not None else it.get("qty") or 0
                )))
            except (TypeError, ValueError):
                continue
            continue
        pid = str(it.get("produto_id") or it.get("id") or "")
        if not pid:
            continue
        try:
            overrides[("pid", pid)] = int(round(float(it.get("qty_verified") if it.get("qty_verified") is not None else it.get("qty") or 0)))
        except (TypeError, ValueError):
            continue

    for i, it in enumerate(rec.get("items") or []):
        pid = str(it.get("produto_id") or "")
        if ("idx", i) in overrides:
            it["qty_verified"] = max(0, overrides[("idx", i)])
        elif ("pid", pid) in overrides:
            it["qty_verified"] = max(0, overrides[("pid", pid)])
        elif it.get("qty_verified") is None:
            it["qty_verified"] = int(it.get("qty_expected") or 0)

    if not any(int(it.get("qty_verified") or 0) > 0 for it in rec.get("items") or []):
        raise ValueError("nenhum item com qty conferida > 0")

    rec["status"] = "verified"
    rec["verified_at"] = _now()
    rec["verified_by"] = user_id
    rec.setdefault("events", []).append({"at": _now(), "tipo": "verified", "by": user_id})
    _save(data)
    return rec


def complete_receiving(rid, user_id=None, auto_verify=False):
    """
    Confirma recebimento e pede entrada ao Inventário.
    Se auto_verify=True e ainda draft, confere qty_expected automaticamente.
    """
    data = _load()
    rec = None
    for r in data.get("receivings") or []:
        if str(r.get("id")) == str(rid):
            rec = r
            break
    if not rec:
        raise ValueError("recebimento não encontrado")
    if rec.get("status") == "completed":
        return rec
    if rec.get("status") == "cancelled":
        raise ValueError("recebimento cancelado")

    if rec.get("status") == "draft":
        if not auto_verify:
            raise ValueError("conferência física obrigatória antes de concluir")
        verify_receiving(rid, user_id=user_id)
        data = _load()
        rec = next(r for r in data["receivings"] if str(r.get("id")) == str(rid))

    if rec.get("status") != "verified":
        raise ValueError(f"status inválido para conclusão: {rec.get('status')}")
    if unmatched_count(rec):
        raise ValueError("há itens sem produto — não conclui inventário")

    items = []
    for it in rec.get("items") or []:
        q = int(it.get("qty_verified") or 0)
        pid = str(it.get("produto_id") or "").strip()
        if q <= 0 or not pid:
            continue
        items.append({"produto_id": pid, "qty": q})

    if not items:
        raise ValueError("sem itens conferidos para inventário")

    inv = inventory_mvp.inventory_apply_receive({
        "id": f"rcv-{rec['id']}",
        "receiving_id": str(rec["id"]),
        "warehouse_id": rec["estabelecimento_id"],
        "items": items,
        "requested_by": user_id,
    })

    if inv.get("status") == "Failed":
        rec.setdefault("events", []).append({
            "at": _now(),
            "tipo": "inventory_failed",
            "by": user_id,
            "detail": inv,
        })
        _save(data)
        raise ValueError("inventário falhou: " + "; ".join(inv.get("errors") or ["erro desconhecido"]))

    rec["status"] = "completed"
    rec["completed_at"] = _now()
    rec["completed_by"] = user_id
    rec["inventory"] = {
        "status": inv.get("status"),
        "movement_ids": inv.get("movement_ids") or [],
        "completed_at": inv.get("completed_at"),
    }
    rec.setdefault("events", []).append({
        "at": _now(),
        "tipo": "completed",
        "by": user_id,
        "movement_ids": inv.get("movement_ids") or [],
    })
    _save(data)
    return rec


def cancel_receiving(rid, user_id=None, motivo=None):
    data = _load()
    rec = None
    for r in data.get("receivings") or []:
        if str(r.get("id")) == str(rid):
            rec = r
            break
    if not rec:
        raise ValueError("recebimento não encontrado")
    if rec.get("status") == "completed":
        raise ValueError("não cancela recebimento já concluído (estoque já entrou)")
    if rec.get("status") == "cancelled":
        return rec
    rec["status"] = "cancelled"
    rec["cancelled_at"] = _now()
    rec["cancelled_by"] = user_id
    rec["cancel_motivo"] = (motivo or "").strip()
    rec.setdefault("events", []).append({"at": _now(), "tipo": "cancelled", "by": user_id})
    _save(data)
    return rec


def ensure_seed():
    """Demo: rascunho matriz — Açúcar 40 un (fecha trânsito ao concluir)."""
    data = _load()
    if data.get("receivings"):
        return {"seeded": False}
    rid = int(data.get("next_id") or 1)
    rec = {
        "id": rid,
        "status": "draft",
        "origem": "manual",
        "estabelecimento_id": "matriz",
        "fornecedor_nome": "CD Central",
        "fornecedor_id": None,
        "documento_ref": "ROMANEIO-DEMO-4",
        "nota": "Seed: conferir e concluir para entrar Açúcar e fechar trânsito no Promise",
        "items": [
            {
                "produto_id": "4",
                "produto_nome": "Acucar 2kg",
                "qty_expected": 40,
                "qty_verified": None,
                "unidade": "UN",
            }
        ],
        "created_at": _now(),
        "created_by": "seed",
        "verified_at": None,
        "verified_by": None,
        "completed_at": None,
        "completed_by": None,
        "inventory": None,
        "events": [{"at": _now(), "tipo": "created", "by": "seed"}],
    }
    data["receivings"] = [rec]
    data["next_id"] = rid + 1
    _save(data)
    return {"seeded": True, "id": rid}


ensure_seed()
