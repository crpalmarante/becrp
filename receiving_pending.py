"""
Receiving Pending Items (RFC-4007).

Gerencia ciclo de vida de pendências — não executa negócio
(não cria produto, não move estoque, não importa XML).
"""

from __future__ import annotations

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PENDING_FILE = os.path.join(DATA_DIR, "receiving_pending.json")

STATUSES = ("open", "in_progress", "resolved", "ignored", "cancelled")
PRIORITIES = ("low", "medium", "high", "critical")

TYPES = {
    "product_not_found": ("product", "high"),
    "supplier_not_found": ("supplier", "medium"),
    "supplier_multiple": ("supplier", "medium"),
    "quantity_difference": ("verification", "high"),
    "damaged": ("verification", "medium"),
    "missing": ("verification", "high"),
    "xml_error": ("xml", "high"),
    "xml_duplicate": ("xml", "low"),
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load():
    if not os.path.exists(PENDING_FILE):
        return {"next_id": 1, "items": []}
    with open(PENDING_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"next_id": 1, "items": []}
    if not isinstance(data.get("items"), list):
        data["items"] = []
    if not isinstance(data.get("next_id"), int):
        data["next_id"] = 1
    return data


def _save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _get(data, pid):
    for it in data.get("items") or []:
        if str(it.get("id")) == str(pid):
            return it
    return None


def list_pending(
    *,
    status=None,
    receiving_id=None,
    category=None,
    open_only=False,
    limit=200,
):
    rows = list(_load().get("items") or [])
    if open_only:
        rows = [r for r in rows if r.get("status") in ("open", "in_progress")]
    st = str(status or "").strip().lower()
    if st:
        rows = [r for r in rows if str(r.get("status")) == st]
    rid = str(receiving_id or "").strip()
    if rid:
        rows = [r for r in rows if str(r.get("receiving_id") or "") == rid]
    cat = str(category or "").strip().lower()
    if cat:
        rows = [r for r in rows if str(r.get("category")) == cat]
    rows.sort(key=lambda r: (
        {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.get("priority"), 9),
        -(r.get("id") or 0),
    ))
    return rows[: max(1, int(limit or 200))]


def get_pending(pid):
    return _get(_load(), pid)


def _default_dedupe(type_key, receiving_id, monitor_id, metadata):
    meta = metadata if isinstance(metadata, dict) else {}
    parts = [type_key, str(receiving_id or ""), str(monitor_id or "")]
    if "item_index" in meta:
        parts.append(f"item:{meta['item_index']}")
    if meta.get("chave"):
        parts.append(f"chave:{meta['chave']}")
    return "|".join(parts)


def create_pending(
    *,
    type_key,
    description,
    receiving_id=None,
    monitor_id=None,
    priority=None,
    metadata=None,
    assigned_to=None,
    user_id=None,
    dedupe_key=None,
):
    """Cria pendência; se dedupe_key já existe open/in_progress, retorna a existente."""
    cat_prio = TYPES.get(type_key)
    if not cat_prio:
        category, prio = "system", "medium"
    else:
        category, prio = cat_prio
    if priority and str(priority).lower() in PRIORITIES:
        prio = str(priority).lower()

    key = dedupe_key or _default_dedupe(type_key, receiving_id, monitor_id, metadata)
    data = _load()
    if key:
        for it in data.get("items") or []:
            if it.get("dedupe_key") == key and it.get("status") in ("open", "in_progress"):
                return it

    pid = int(data.get("next_id") or 1)
    item = {
        "id": pid,
        "receiving_id": receiving_id,
        "monitor_id": monitor_id,
        "category": category,
        "type": type_key,
        "priority": prio,
        "status": "open",
        "description": (description or "").strip(),
        "assigned_to": assigned_to,
        "metadata": metadata if isinstance(metadata, dict) else {},
        "dedupe_key": key,
        "created_at": _now(),
        "created_by": user_id,
        "resolved_at": None,
        "resolved_by": None,
        "resolution": None,
        "events": [
            {"at": _now(), "tipo": "created", "by": user_id},
        ],
    }
    data["items"].append(item)
    data["next_id"] = pid + 1
    _save(data)
    return item


def set_status(pid, status, user_id=None, note=None, resolution=None):
    status = str(status or "").strip().lower()
    if status not in STATUSES:
        raise ValueError(f"status inválido: {status}")
    data = _load()
    item = _get(data, pid)
    if not item:
        raise ValueError("pendência não encontrada")
    item["status"] = status
    if status in ("resolved", "ignored", "cancelled"):
        item["resolved_at"] = _now()
        item["resolved_by"] = user_id
        item["resolution"] = (resolution or note or status).strip()
    item.setdefault("events", []).append({
        "at": _now(), "tipo": status, "by": user_id, "note": note,
    })
    _save(data)
    return item


def resolve(pid, user_id=None, note=None, resolution=None):
    return set_status(pid, "resolved", user_id=user_id, note=note, resolution=resolution or "resolved")


def ignore(pid, user_id=None, note=None):
    return set_status(pid, "ignored", user_id=user_id, note=note, resolution=note or "ignored")


def cancel(pid, user_id=None, note=None):
    return set_status(pid, "cancelled", user_id=user_id, note=note, resolution=note or "cancelled")


def assign(pid, assigned_to, user_id=None):
    data = _load()
    item = _get(data, pid)
    if not item:
        raise ValueError("pendência não encontrada")
    if item.get("status") not in ("open", "in_progress"):
        raise ValueError("só atribui pendência aberta")
    item["assigned_to"] = assigned_to
    if item.get("status") == "open":
        item["status"] = "in_progress"
    item.setdefault("events", []).append({
        "at": _now(), "tipo": "assigned", "by": user_id, "assigned_to": assigned_to,
    })
    _save(data)
    return item


def resolve_by_dedupe_prefix(prefix, user_id=None, resolution=None):
    data = _load()
    out = []
    for it in data.get("items") or []:
        if it.get("status") not in ("open", "in_progress"):
            continue
        if str(it.get("dedupe_key") or "").startswith(prefix):
            it["status"] = "resolved"
            it["resolved_at"] = _now()
            it["resolved_by"] = user_id
            it["resolution"] = resolution or "auto"
            it.setdefault("events", []).append({
                "at": _now(), "tipo": "resolved", "by": user_id, "note": "auto",
            })
            out.append(it)
    if out:
        _save(data)
    return out


def sync_from_receiving(rec, user_id=None):
    """Gera/atualiza pendências a partir do estado do receiving."""
    if not isinstance(rec, dict):
        return []
    rid = rec.get("id")
    created = []

    for idx, it in enumerate(rec.get("items") or []):
        if str(it.get("produto_id") or "").strip():
            resolve_by_dedupe_prefix(
                f"product_not_found|{rid}||item:{idx}",
                user_id=user_id,
                resolution="product_linked",
            )
            continue
        desc = (
            (it.get("nfe_item") or {}).get("descricao")
            or it.get("produto_nome")
            or f"item {idx + 1}"
        )
        ean = (it.get("nfe_item") or {}).get("ean") or ""
        created.append(create_pending(
            type_key="product_not_found",
            description=f"Produto não localizado: {desc}" + (f" (EAN {ean})" if ean else ""),
            receiving_id=rid,
            metadata={
                "item_index": idx,
                "ean": ean,
                "codigo_fornecedor": (it.get("nfe_item") or {}).get("codigo_fornecedor"),
                "descricao": desc,
            },
            user_id=user_id,
        ))

    pl = rec.get("partner_lookup") if isinstance(rec.get("partner_lookup"), dict) else {}
    if rec.get("fornecedor_id"):
        resolve_by_dedupe_prefix(f"supplier_not_found|{rid}|", user_id=user_id, resolution="partner_linked")
        resolve_by_dedupe_prefix(f"supplier_multiple|{rid}|", user_id=user_id, resolution="partner_linked")
    elif pl.get("status") == "multiple":
        created.append(create_pending(
            type_key="supplier_multiple",
            description=f"Vários fornecedores para CNPJ {rec.get('fornecedor_cnpj') or '—'}",
            receiving_id=rid,
            metadata={"cnpj": rec.get("fornecedor_cnpj"), "partners": pl.get("partners") or []},
            user_id=user_id,
        ))
    elif not rec.get("fornecedor_id") and (
        pl.get("status") == "not_found"
        or (rec.get("origem") == "nfe" and rec.get("fornecedor_cnpj") and pl.get("status") != "found")
    ):
        created.append(create_pending(
            type_key="supplier_not_found",
            description=(
                f"Fornecedor não identificado: {rec.get('fornecedor_nome') or ''} "
                f"CNPJ {rec.get('fornecedor_cnpj') or '—'}"
            ),
            receiving_id=rid,
            metadata={"cnpj": rec.get("fornecedor_cnpj"), "nome": rec.get("fornecedor_nome")},
            user_id=user_id,
        ))

    ver = rec.get("verification") if isinstance(rec.get("verification"), dict) else {}
    if ver.get("status") == "completed" and isinstance(ver.get("items"), list):
        for idx, vit in enumerate(ver["items"]):
            result = vit.get("result") or "verified"
            if result == "verified":
                for tk in ("quantity_difference", "damaged", "missing"):
                    resolve_by_dedupe_prefix(
                        f"{tk}|{rid}||item:{idx}",
                        user_id=user_id,
                        resolution="cleared",
                    )
                continue
            type_key = result if result in TYPES else "quantity_difference"
            created.append(create_pending(
                type_key=type_key,
                description=(
                    f"Conferência {result}: {vit.get('produto_nome') or vit.get('produto_id')} "
                    f"esp={vit.get('expected_quantity')} bom={vit.get('received_quantity')} "
                    f"avaria={vit.get('damaged_quantity')}"
                ),
                receiving_id=rid,
                metadata={
                    "item_index": idx,
                    "produto_id": vit.get("produto_id"),
                    "result": result,
                    "expected": vit.get("expected_quantity"),
                    "received": vit.get("received_quantity"),
                    "damaged": vit.get("damaged_quantity"),
                    "notes": vit.get("notes"),
                },
                user_id=user_id,
            ))

    return created


def sync_from_monitor_doc(doc, user_id=None):
    if not isinstance(doc, dict):
        return None
    mid = doc.get("id")
    st = doc.get("status")
    if st == "error":
        return create_pending(
            type_key="xml_error",
            description=f"XML monitor #{mid}: {doc.get('error') or 'erro'}",
            monitor_id=mid,
            metadata={"chave": doc.get("chave"), "error": doc.get("error")},
            user_id=user_id,
        )
    if st == "duplicate":
        return create_pending(
            type_key="xml_duplicate",
            description=f"XML duplicado monitor #{mid} chave {doc.get('chave') or '—'}",
            monitor_id=mid,
            receiving_id=doc.get("receiving_id"),
            metadata={"chave": doc.get("chave"), "receiving_id": doc.get("receiving_id")},
            user_id=user_id,
        )
    if st == "done":
        resolve_by_dedupe_prefix(f"xml_error||{mid}", user_id=user_id, resolution="processed")
        resolve_by_dedupe_prefix(f"xml_duplicate||{mid}", user_id=user_id, resolution="processed")
    return None


def open_count(receiving_id=None):
    return len(list_pending(receiving_id=receiving_id, open_only=True, limit=5000))
