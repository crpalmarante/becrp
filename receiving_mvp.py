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
import quality_checks_store

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


QTY_DECIMALS = 3


def _as_qty(val, default=0.0):
    try:
        q = float(val)
    except (TypeError, ValueError):
        return float(default)
    if q < 0:
        return 0.0
    return round(q, QTY_DECIMALS)


def _qty_eq(a, b, eps=0.0005):
    return abs(float(a) - float(b)) <= eps


def _normalize_items(items, allow_unmatched=False):
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        pid = str(it.get("produto_id") or it.get("id") or "").strip()
        expected = _as_qty(it.get("qty_expected") or it.get("qty") or it.get("quantidade") or 0)
        if expected <= 0:
            continue
        if not pid and not allow_unmatched:
            continue
        verified_raw = it.get("qty_verified")
        verified = _as_qty(verified_raw) if verified_raw is not None else None
        row = {
            "produto_id": pid,
            "produto_nome": (it.get("produto_nome") or it.get("nome") or "").strip(),
            "qty_expected": expected,
            "qty_verified": verified,
            "unidade": (it.get("unidade") or "UN").strip() or "UN",
            "match": it.get("match") or ("ok" if pid else "none"),
            "preco": float(it.get("preco") or it.get("custo") or 0),
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
        "pedido_compra_id": body.get("pedido_compra_id") or body.get("pedido_id") or None,
        "items": items,
        "nfe": body.get("nfe") if isinstance(body.get("nfe"), dict) else None,
        "partner_lookup": body.get("partner_lookup") if isinstance(body.get("partner_lookup"), dict) else None,
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
    try:
        import receiving_pending
        receiving_pending.sync_from_receiving(rec, user_id=user_id)
    except Exception:
        pass
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
    try:
        import receiving_pending
        receiving_pending.sync_from_receiving(rec, user_id=user_id)
    except Exception:
        pass
    return rec


def link_partner(rid, partner_id, user_id=None):
    """
    Vincula manualmente um Business Partner ao recebimento (RFC-4005).
    Não cria parceiro — só associa id existente.
    """
    import partner_lookup

    data = _load()
    rec = None
    for r in data.get("receivings") or []:
        if str(r.get("id")) == str(rid):
            rec = r
            break
    if not rec:
        raise ValueError("recebimento não encontrado")
    if rec.get("status") in ("completed", "cancelled"):
        raise ValueError("não altera fornecedor neste status")

    pid = str(partner_id or "").strip()
    if not pid:
        raise ValueError("partner_id obrigatório")

    pl = partner_lookup.lookup(partner_id=pid, role="SUPPLIER", module="receiving.link", audit=True)
    if pl.get("status") != "found":
        pl = partner_lookup.lookup(partner_id=pid, module="receiving.link", audit=True)
    if pl.get("status") != "found" or not pl.get("partner"):
        raise ValueError(f"parceiro não encontrado: {pid}")

    partner = pl["partner"]
    rec["fornecedor_id"] = partner["id"]
    rec["fornecedor_nome"] = (
        partner.get("display_name") or partner.get("legal_name") or rec.get("fornecedor_nome") or ""
    )
    if partner.get("cnpj"):
        rec["fornecedor_cnpj"] = partner["cnpj"]
    rec["partner_lookup"] = {
        "status": "found",
        "match": "manual",
        "partner": partner,
        "criteria": {"partner_id": pid},
    }
    rec.setdefault("events", []).append({
        "at": _now(),
        "tipo": "partner_linked",
        "by": user_id,
        "partner_id": partner["id"],
    })
    _save(data)
    try:
        import receiving_pending
        receiving_pending.sync_from_receiving(rec, user_id=user_id)
    except Exception:
        pass
    return rec


def resolve_partner_on_receiving(rid, user_id=None):
    """Reexecuta lookup pelo CNPJ já gravado no receiving."""
    import partner_lookup

    data = _load()
    rec = None
    for r in data.get("receivings") or []:
        if str(r.get("id")) == str(rid):
            rec = r
            break
    if not rec:
        raise ValueError("recebimento não encontrado")
    cnpj = rec.get("fornecedor_cnpj") or ((rec.get("nfe") or {}).get("fornecedor_cnpj"))
    pl = partner_lookup.lookup(cnpj=cnpj, role="SUPPLIER", module="receiving.resolve", audit=True)
    rec["partner_lookup"] = {
        "status": pl.get("status"),
        "match": pl.get("match"),
        "partner": pl.get("partner"),
        "partners": pl.get("partners") or [],
        "criteria": pl.get("criteria"),
    }
    if pl.get("status") == "found" and pl.get("partner"):
        rec["fornecedor_id"] = pl["partner"]["id"]
        rec["fornecedor_nome"] = (
            pl["partner"].get("display_name")
            or pl["partner"].get("legal_name")
            or rec.get("fornecedor_nome")
            or ""
        )
        rec.setdefault("events", []).append({
            "at": _now(), "tipo": "partner_resolved", "by": user_id,
            "partner_id": pl["partner"]["id"],
        })
    _save(data)
    try:
        import receiving_pending
        receiving_pending.sync_from_receiving(rec, user_id=user_id)
    except Exception:
        pass
    return rec


def _as_int(val, default=0):
    """Compat: inteiro arredondado (IDs, contagens). Preferir _as_qty para quantidades."""
    try:
        return int(round(float(val)))
    except (TypeError, ValueError):
        return default


def _digits(val):
    return "".join(ch for ch in str(val or "") if ch.isdigit())


def classify_item_result(it):
    """RFC-4008: classifica resultado físico do item (não move estoque)."""
    expected = _as_qty(it.get("qty_expected"))
    good = _as_qty(it.get("qty_verified"))
    damaged = max(0.0, _as_qty(it.get("qty_damaged")))
    rejected = bool(it.get("rejected"))
    if rejected:
        return "rejected"
    if good <= 0 and damaged <= 0 and expected > 0:
        return "missing"
    if damaged > 0 and good == 0 and expected > 0:
        return "damaged"
    if not _qty_eq(good, expected) or damaged > 0:
        if damaged > 0 and _qty_eq(good, expected):
            return "damaged"
        return "quantity_difference" if not _qty_eq(good, expected) else "damaged"
    return "verified"


def _build_verification_summary(rec, user_id=None, method="manual"):
    items_out = []
    diffs = 0
    for it in rec.get("items") or []:
        expected = _as_qty(it.get("qty_expected"))
        good = _as_qty(it.get("qty_verified"))
        damaged = max(0.0, _as_qty(it.get("qty_damaged")))
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
            entry["qty_verified"] = max(0.0, _as_qty(
                it.get("qty_verified") if it.get("qty_verified") is not None else it.get("qty")
            ))
        if it.get("qty_damaged") is not None:
            entry["qty_damaged"] = max(0.0, _as_qty(it.get("qty_damaged")))
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
            it["qty_verified"] = _as_qty(it.get("qty_expected"))
        if "qty_damaged" in ov:
            it["qty_damaged"] = ov["qty_damaged"]
        elif it.get("qty_damaged") is None:
            it["qty_damaged"] = 0.0
        if "notes" in ov:
            it["notes"] = ov["notes"]
        if "rejected" in ov:
            it["rejected"] = ov["rejected"]
        it["verify_result"] = classify_item_result(it)
        it["qty_difference"] = round(
            _as_qty(it.get("qty_verified")) - _as_qty(it.get("qty_expected")),
            QTY_DECIMALS,
        )

    # permite concluir só com divergências (faltando tudo) se allow_empty
    has_any = any(
        _as_qty(it.get("qty_verified")) > 0 or bool(it.get("rejected"))
        or _as_qty(it.get("qty_damaged")) > 0
        or classify_item_result(it) == "missing"
        for it in rec.get("items") or []
    )
    if not has_any:
        raise ValueError("nenhum item conferido")
    if not any(_as_qty(it.get("qty_verified")) > 0 for it in rec.get("items") or []):
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
    try:
        import receiving_pending
        receiving_pending.sync_from_receiving(rec, user_id=user_id)
    except Exception:
        pass
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
    add = _as_qty(qty, 1.0)
    if add <= 0:
        add = 1.0

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
    cur = _as_qty(it.get("qty_verified")) if it.get("qty_verified") is not None else 0.0
    it["qty_verified"] = round(cur + add, QTY_DECIMALS)
    if it.get("qty_damaged") is None:
        it["qty_damaged"] = 0.0
    it["verify_result"] = classify_item_result(it)
    it["qty_difference"] = round(
        _as_qty(it.get("qty_verified")) - _as_qty(it.get("qty_expected")),
        QTY_DECIMALS,
    )
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


def complete_receiving(rid, user_id=None, auto_verify=False, quality_respostas=None, force_quality=None):
    """
    Confirma recebimento e pede entrada ao Inventário.
    Se auto_verify=True e ainda draft, confere qty_expected automaticamente.
    quality_respostas: respostas do quality check; se omitido, usa aprovado se nenhum crítico exigir.
    force_quality: ignora resultado rejected e conclui mesmo assim (supervisor).
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

    if rec.get("status") not in ("verified", "quality_rejected"):
        raise ValueError(f"status inválido para conclusão: {rec.get('status')}")
    if rec.get("status") == "quality_rejected" and not force_quality:
        raise ValueError("recebimento rejeitado por qualidade — use force_quality para concluir")
    if unmatched_count(rec):
        raise ValueError("há itens sem produto — não conclui inventário")

    # Quality check
    qc = quality_checks_store.avaliar(rec["id"], quality_respostas or {}, usuario=user_id or "")
    rec["quality_check"] = qc
    if qc["resultado"] == "rejected" and not force_quality:
        rec["status"] = "quality_rejected"
        rec.setdefault("events", []).append({"at": _now(), "tipo": "quality_rejected", "by": user_id, "qc": qc})
        _save(data)
        raise ValueError(f"quality check REJEITADO: {qc['ok_count']}/{qc['total']} aprovado(s)")

    items = []
    for it in rec.get("items") or []:
        q = _as_qty(it.get("qty_verified"))
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

    # RFC-4011 / escrituração + RFC-4010 AP
    if (rec.get("origem") == "nfe" or (rec.get("nfe") or {}).get("chave")):
        try:
            import nfe_entrada_store
            parsed = None
            xml_path = (rec.get("nfe") or {}).get("xml_path")
            if xml_path and os.path.exists(xml_path):
                try:
                    import nfe_inbound
                    with open(xml_path, "rb") as xf:
                        parsed = nfe_inbound.parse_nfe_xml(xf.read())
                except Exception:
                    parsed = None
            entrada = nfe_entrada_store.upsert_from_receiving(rec, parsed=parsed)
            rec["nfe_entrada"] = {"chave": entrada.get("chave"), "status": entrada.get("status")}
        except Exception as e:
            rec["nfe_entrada"] = {"ok": False, "error": str(e)}
        try:
            import purchase_finance
            ap = purchase_finance.create_from_receiving(rec, usuario=user_id or "")
            rec["accounts_payable"] = {
                "already": ap.get("already"),
                "titulos": [t.get("id") for t in (ap.get("titulos") or [])],
                "count": len(ap.get("titulos") or []),
            }
        except Exception as e:
            rec["accounts_payable"] = {"ok": False, "error": str(e)}

    # Gera recebimento WMS a partir do recebimento fiscal
    try:
        import wms_receiving
        import wms_warehouses
        armazem = wms_warehouses.map_estabelecimento_to_armazem(rec.get("estabelecimento_id"))
        if armazem:
            wms_lines = []
            for i, it in enumerate(rec.get("items") or [], start=1):
                if not str(it.get("produto_id") or "").strip():
                    continue
                wms_lines.append({
                    "linha": i,
                    "produto_id": str(it.get("produto_id")),
                    "produto": it.get("produto_nome") or "",
                    "qtd_esperada": float(it.get("qty_verified") or it.get("qty_expected") or 0),
                    "qtd_recebida": float(it.get("qty_verified") or 0),
                    "qtd_aprovada": float(it.get("qty_verified") or 0),
                    "loc_destino": "",
                    "inspecao": "approved",
                })
            if wms_lines:
                loc_receb = wms_warehouses.get_default_receiving_location(armazem)
                wms_rec = wms_receiving.create_recebimento({
                    "armazem": armazem,
                    "origem": "compra" if rec.get("origem") in ("manual", "nfe") else (rec.get("origem") or "supplier"),
                    "documento_tipo": "receiving",
                    "documento_ref": f"RCV-{rec['id']}",
                    "parceiro": rec.get("fornecedor_nome") or "",
                    "loc_recebimento": loc_receb,
                    "linhas": wms_lines,
                }, usuario=user_id or "")
                rec["wms_recebimento_id"] = wms_rec.get("id")
    except Exception:
        pass

    # Atualiza pedido de compra vinculado, se houver
    if rec.get("pedido_compra_id"):
        try:
            import compras_store
            pid = rec["pedido_compra_id"]
            pedido = compras_store.get(pid)
            if pedido:
                pedido["recebimento_id"] = str(rec["id"])
                pedido["recebimento_num"] = f"RCV-{rec['id']}"
                pedido["status"] = "recebido"
                compras_store.save(pedido)
        except Exception:
            pass

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
