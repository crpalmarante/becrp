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

# RFC-4008 item results
VERIFY_RESULTS = (
    "verified",
    "quantity_difference",
    "damaged",
    "missing",
    "rejected",
)
VERIFY_METHODS = ("manual", "barcode", "mixed")


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


def _as_int(val, default=0):
    try:
        return int(round(float(val)))
    except (TypeError, ValueError):
        return default


def _digits(val):
    return "".join(ch for ch in str(val or "") if ch.isdigit())


def classify_item_result(it):
    """RFC-4008: classifica resultado físico do item (não move estoque)."""
    expected = _as_int(it.get("qty_expected"))
    good = _as_int(it.get("qty_verified"))
    damaged = max(0, _as_int(it.get("qty_damaged")))
    rejected = bool(it.get("rejected"))
    if rejected:
        return "rejected"
    if good <= 0 and damaged <= 0 and expected > 0:
        return "missing"
    if damaged > 0 and good == 0 and expected > 0:
        return "damaged"
    if good != expected or damaged > 0:
        if damaged > 0 and good == expected:
            return "damaged"
        return "quantity_difference" if good != expected else "damaged"
    return "verified"


def _build_verification_summary(rec, user_id=None, method="manual"):
    items_out = []
    diffs = 0
    for it in rec.get("items") or []:
        expected = _as_int(it.get("qty_expected"))
        good = _as_int(it.get("qty_verified"))
        damaged = max(0, _as_int(it.get("qty_damaged")))
        result = classify_item_result(it)
        if result != "verified":
            diffs += 1
        items_out.append({
            "produto_id": str(it.get("produto_id") or ""),
            "produto_nome": it.get("produto_nome") or "",
            "expected_quantity": expected,
            "received_quantity": good,
            "damaged_quantity": damaged,
            "difference": good - expected,
            "result": result,
            "notes": (it.get("notes") or "").strip(),
        })
    started = (rec.get("verification") or {}).get("started_at") or _now()
    return {
        "receiving_id": rec.get("id"),
        "warehouse_id": rec.get("estabelecimento_id"),
        "operator_id": user_id,
        "method": method if method in VERIFY_METHODS else "manual",
        "started_at": started,
        "completed_at": _now(),
        "status": "completed",
        "differences_count": diffs,
        "items": items_out,
    }


def start_verification(rid, user_id=None, method="manual"):
    """Marca início da conferência física (status permanece draft até finish)."""
    data = _load()
    rec = None
    for r in data.get("receivings") or []:
        if str(r.get("id")) == str(rid):
            rec = r
            break
    if not rec:
        raise ValueError("recebimento não encontrado")
    if rec.get("status") not in ("draft", "verified"):
        raise ValueError(f"não inicia conferência em status={rec.get('status')}")
    if unmatched_count(rec):
        raise ValueError(
            f"{unmatched_count(rec)} item(ns) sem produto vinculado — localize antes de conferir"
        )
    if rec.get("status") == "verified":
        # reabre para nova conferência
        rec["status"] = "draft"
    ver = rec.get("verification") if isinstance(rec.get("verification"), dict) else {}
    if ver.get("status") != "in_progress":
        ver = {
            "receiving_id": rec.get("id"),
            "warehouse_id": rec.get("estabelecimento_id"),
            "operator_id": user_id,
            "method": method if method in VERIFY_METHODS else "manual",
            "started_at": _now(),
            "completed_at": None,
            "status": "in_progress",
            "differences_count": 0,
            "items": [],
        }
        rec["verification"] = ver
        rec.setdefault("events", []).append({
            "at": _now(), "tipo": "verification_started", "by": user_id, "method": ver["method"],
        })
    _save(data)
    return rec


def verify_receiving(rid, payload=None, user_id=None):
    """
    Conferência física (RFC-4008): grava qty/notas/avaria, classifica divergências.
    Não move estoque — só status=verified + registro verification.
    """
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
    method = str(body.get("method") or "manual").strip().lower()
    if method not in VERIFY_METHODS:
        method = "manual"

    # inicia se ainda não
    if not isinstance(rec.get("verification"), dict) or rec["verification"].get("status") != "in_progress":
        if not isinstance(rec.get("verification"), dict) or not rec["verification"].get("started_at"):
            rec["verification"] = {
                "receiving_id": rec.get("id"),
                "warehouse_id": rec.get("estabelecimento_id"),
                "operator_id": user_id,
                "method": method,
                "started_at": _now(),
                "completed_at": None,
                "status": "in_progress",
                "differences_count": 0,
                "items": [],
            }
            rec.setdefault("events", []).append({
                "at": _now(), "tipo": "verification_started", "by": user_id, "method": method,
            })

    overrides = {}
    for it in body.get("items") or []:
        if not isinstance(it, dict):
            continue
        key = None
        if "item_index" in it:
            try:
                key = ("idx", int(it["item_index"]))
            except (TypeError, ValueError):
                continue
        else:
            pid = str(it.get("produto_id") or it.get("id") or "")
            if not pid:
                continue
            key = ("pid", pid)
        entry = {}
        if it.get("qty_verified") is not None or it.get("qty") is not None:
            entry["qty_verified"] = max(0, _as_int(
                it.get("qty_verified") if it.get("qty_verified") is not None else it.get("qty")
            ))
        if it.get("qty_damaged") is not None:
            entry["qty_damaged"] = max(0, _as_int(it.get("qty_damaged")))
        if "notes" in it:
            entry["notes"] = str(it.get("notes") or "").strip()
        if "rejected" in it:
            entry["rejected"] = bool(it.get("rejected"))
        overrides[key] = entry

    for i, it in enumerate(rec.get("items") or []):
        pid = str(it.get("produto_id") or "")
        ov = overrides.get(("idx", i)) or overrides.get(("pid", pid)) or {}
        if "qty_verified" in ov:
            it["qty_verified"] = ov["qty_verified"]
        elif it.get("qty_verified") is None:
            it["qty_verified"] = _as_int(it.get("qty_expected"))
        if "qty_damaged" in ov:
            it["qty_damaged"] = ov["qty_damaged"]
        elif it.get("qty_damaged") is None:
            it["qty_damaged"] = 0
        if "notes" in ov:
            it["notes"] = ov["notes"]
        if "rejected" in ov:
            it["rejected"] = ov["rejected"]
        it["verify_result"] = classify_item_result(it)
        it["qty_difference"] = _as_int(it.get("qty_verified")) - _as_int(it.get("qty_expected"))

    # permite concluir só com divergências (faltando tudo) se allow_empty
    has_any = any(
        _as_int(it.get("qty_verified")) > 0 or bool(it.get("rejected"))
        or _as_int(it.get("qty_damaged")) > 0
        or classify_item_result(it) == "missing"
        for it in rec.get("items") or []
    )
    if not has_any:
        raise ValueError("nenhum item conferido")
    if not any(_as_int(it.get("qty_verified")) > 0 for it in rec.get("items") or []):
        if not body.get("allow_zero_receive"):
            raise ValueError(
                "nenhum item com qty boa > 0 — use allow_zero_receive=true para registrar só faltas/avarias"
            )

    prev_method = (rec.get("verification") or {}).get("method") or "manual"
    if prev_method != method and prev_method in VERIFY_METHODS:
        method = "mixed"

    summary = _build_verification_summary(rec, user_id=user_id, method=method)
    rec["verification"] = summary
    rec["status"] = "verified"
    rec["verified_at"] = summary["completed_at"]
    rec["verified_by"] = user_id
    rec.setdefault("events", []).append({
        "at": _now(),
        "tipo": "verified",
        "by": user_id,
        "method": method,
        "differences_count": summary["differences_count"],
    })
    if summary["differences_count"]:
        rec.setdefault("events", []).append({
            "at": _now(),
            "tipo": "verification_difference_detected",
            "by": user_id,
            "count": summary["differences_count"],
        })
    _save(data)
    return rec


def scan_receiving_item(rid, barcode, qty=1, user_id=None):
    """
    Conferência assistida por código de barras (RFC-4008).
    Incrementa qty_verified do item cujo EAN/produto casa com o bip.
    Mantém status draft (in_progress).
    """
    code = _digits(barcode) or str(barcode or "").strip()
    if not code:
        raise ValueError("código de barras vazio")
    add = max(1, _as_int(qty, 1))

    data = _load()
    rec = None
    for r in data.get("receivings") or []:
        if str(r.get("id")) == str(rid):
            rec = r
            break
    if not rec:
        raise ValueError("recebimento não encontrado")
    if rec.get("status") in ("completed", "cancelled"):
        raise ValueError(f"não confere bip em status={rec.get('status')}")
    if unmatched_count(rec):
        raise ValueError("localize produtos antes de bipar")

    if rec.get("status") == "verified":
        rec["status"] = "draft"

    ver = rec.get("verification") if isinstance(rec.get("verification"), dict) else {}
    if ver.get("status") != "in_progress":
        rec["verification"] = {
            "receiving_id": rec.get("id"),
            "warehouse_id": rec.get("estabelecimento_id"),
            "operator_id": user_id,
            "method": "barcode",
            "started_at": _now(),
            "completed_at": None,
            "status": "in_progress",
            "differences_count": 0,
            "items": [],
        }
        rec.setdefault("events", []).append({
            "at": _now(), "tipo": "verification_started", "by": user_id, "method": "barcode",
        })
    else:
        m = ver.get("method") or "barcode"
        ver["method"] = "mixed" if m == "manual" else m
        rec["verification"] = ver

    # resolve produto pelo EAN no catálogo se bip for EAN
    hit_idx = None
    for i, it in enumerate(rec.get("items") or []):
        nfe = it.get("nfe_item") if isinstance(it.get("nfe_item"), dict) else {}
        ean = _digits(nfe.get("ean"))
        pid = str(it.get("produto_id") or "")
        if ean and ean == code:
            hit_idx = i
            break
        if pid and pid == code:
            hit_idx = i
            break

    if hit_idx is None:
        # tenta catálogo → produto_id
        try:
            import cobol_bridge
            for p in cobol_bridge.produtos_listar() or []:
                bars = _digits(p.get("codigo_barras") or p.get("ean"))
                if bars and bars == code:
                    pid = str(p.get("id"))
                    for i, it in enumerate(rec.get("items") or []):
                        if str(it.get("produto_id")) == pid:
                            hit_idx = i
                            break
                    break
        except Exception:
            pass

    if hit_idx is None:
        raise ValueError(f"código não encontrado neste recebimento: {code}")

    it = rec["items"][hit_idx]
    cur = _as_int(it.get("qty_verified")) if it.get("qty_verified") is not None else 0
    it["qty_verified"] = cur + add
    if it.get("qty_damaged") is None:
        it["qty_damaged"] = 0
    it["verify_result"] = classify_item_result(it)
    it["qty_difference"] = _as_int(it.get("qty_verified")) - _as_int(it.get("qty_expected"))
    rec.setdefault("events", []).append({
        "at": _now(),
        "tipo": "verification_item_scanned",
        "by": user_id,
        "item_index": hit_idx,
        "barcode": code,
        "qty_add": add,
        "qty_verified": it["qty_verified"],
    })
    _save(data)
    return {
        "receiving": rec,
        "item_index": hit_idx,
        "item": it,
        "barcode": code,
    }


def reopen_verification(rid, user_id=None):
    """Supervisor: volta verified → draft para reconferir (não toca inventário)."""
    data = _load()
    rec = None
    for r in data.get("receivings") or []:
        if str(r.get("id")) == str(rid):
            rec = r
            break
    if not rec:
        raise ValueError("recebimento não encontrado")
    if rec.get("status") != "verified":
        raise ValueError("só reabre conferência em status=verified")
    rec["status"] = "draft"
    ver = rec.get("verification") if isinstance(rec.get("verification"), dict) else {}
    ver["status"] = "reopened"
    ver["reopened_at"] = _now()
    ver["reopened_by"] = user_id
    rec["verification"] = ver
    rec["verified_at"] = None
    rec["verified_by"] = None
    rec.setdefault("events", []).append({
        "at": _now(), "tipo": "verification_reopened", "by": user_id,
    })
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
