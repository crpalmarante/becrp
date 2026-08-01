"""
Campanhas de desconto (camada sobre lista de preços).

MVP: % sobre itens de uma categoria, com vigência e opcional forma de pagamento.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CAMPAIGNS_FILE = os.path.join(DATA_DIR, "campaigns.json")


def _today():
    return date.today()


def _parse_day(val):
    s = str(val or "").strip()[:10]
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _norm_forma(fp):
    s = str(fp or "").strip().lower()
    if not s:
        return ""
    if s in ("dinheiro", "cash", "especie", "espécie"):
        return "dinheiro"
    if s in ("pix",):
        return "pix"
    if s in ("debito", "débito", "debit"):
        return "debito"
    if s in ("credito", "crédito", "credit"):
        return "credito"
    if s in ("voucher", "vale", "vr", "va"):
        return "voucher"
    return s


def _load():
    if not os.path.exists(CAMPAIGNS_FILE):
        return {"campaigns": []}
    with open(CAMPAIGNS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"campaigns": []}
    if not isinstance(data.get("campaigns"), list):
        data["campaigns"] = []
    return data


def _save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CAMPAIGNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_all(active_only=False):
    rows = list(_load().get("campaigns") or [])
    if active_only:
        rows = [c for c in rows if c.get("active", True)]
    rows.sort(key=lambda c: (c.get("name") or c.get("id") or "").lower())
    return rows


def get_campaign(cid):
    key = str(cid or "").strip()
    if not key:
        return None
    for row in _load().get("campaigns") or []:
        if str(row.get("id")) == key:
            return row
    return None


def upsert_campaign(payload, campaign_id=None):
    body = payload if isinstance(payload, dict) else {}
    data = _load()
    cid = str(campaign_id or body.get("id") or "").strip()
    existing = None
    idx = None
    if cid:
        for i, row in enumerate(data["campaigns"]):
            if str(row.get("id")) == cid:
                existing = row
                idx = i
                break
    if not cid:
        cid = "camp_" + str(uuid.uuid4())[:8]

    name = (body.get("name") or body.get("nome") or (existing or {}).get("name") or "").strip()
    if not name:
        raise ValueError("name obrigatório")
    categoria = (
        body.get("categoria")
        if "categoria" in body
        else (existing or {}).get("categoria")
    ) or ""
    categoria = str(categoria).strip()
    if not categoria:
        raise ValueError("categoria obrigatória")

    try:
        pct = float(
            body.get("discount_pct")
            if body.get("discount_pct") is not None
            else body.get("pct")
            if body.get("pct") is not None
            else (existing or {}).get("discount_pct")
            or 0
        )
    except (TypeError, ValueError):
        pct = 0.0
    if pct <= 0 or pct > 100:
        raise ValueError("discount_pct deve ser entre 0 e 100")

    start = body.get("start") if "start" in body else (existing or {}).get("start")
    end = body.get("end") if "end" in body else (existing or {}).get("end")
    if start and not _parse_day(start):
        raise ValueError("start inválido (YYYY-MM-DD)")
    if end and not _parse_day(end):
        raise ValueError("end inválido (YYYY-MM-DD)")

    active = body.get("active")
    if active is None:
        active = (existing or {}).get("active", True)

    forma = body.get("forma_pg") if "forma_pg" in body else (existing or {}).get("forma_pg")
    forma = str(forma or "").strip()

    row = {
        "id": cid,
        "name": name,
        "active": bool(active),
        "start": str(start or "")[:10],
        "end": str(end or "")[:10],
        "categoria": categoria,
        "discount_pct": round(pct, 2),
        "forma_pg": forma,
    }
    if idx is None:
        data["campaigns"].append(row)
    else:
        data["campaigns"][idx] = row
    _save(data)
    return row


def delete_campaign(campaign_id):
    cid = str(campaign_id or "").strip()
    data = _load()
    before = len(data["campaigns"])
    data["campaigns"] = [c for c in data["campaigns"] if str(c.get("id")) != cid]
    if len(data["campaigns"]) == before:
        raise ValueError("campanha não encontrada")
    _save(data)
    return True


def is_active_on(camp, on_day=None):
    if not camp or not camp.get("active", True):
        return False
    day = on_day or _today()
    start = _parse_day(camp.get("start"))
    end = _parse_day(camp.get("end"))
    if start and day < start:
        return False
    if end and day > end:
        return False
    return True


def active_campaigns(on_day=None):
    return [c for c in list_all() if is_active_on(c, on_day)]


def _line_subtotal(line):
    try:
        qtd = float(line.get("qtd") or 0)
    except (TypeError, ValueError):
        qtd = 0.0
    try:
        preco = float(line.get("preco") or 0)
    except (TypeError, ValueError):
        preco = 0.0
    if line.get("troca") or qtd < 0:
        return 0.0
    desc = float(line.get("descPct") or 0)
    sub = qtd * preco
    if desc:
        sub *= 1 - desc / 100.0
    return round(sub, 2)


def apply_campaigns(lines, catalog_by_id=None, forma_pg=None, on_day=None, provisional=False):
    """
    Aplica campanhas ativas.

    - forma_pg None + provisional=True → campanhas com forma entram só como hint
    - forma_pg None + provisional=False → só campanhas sem restrição de pagamento
    - forma_pg set → inclui campanhas daquela forma + sem restrição
    """
    catalog = catalog_by_id or {}
    day = on_day or _today()
    want = _norm_forma(forma_pg) if forma_pg is not None else None
    discount = 0.0
    applied = []
    hints = []

    for camp in active_campaigns(day):
        camp_fp = _norm_forma(camp.get("forma_pg"))
        if camp_fp:
            if want is None:
                if provisional:
                    # calcula potencial só para hint
                    pass
                else:
                    continue
            elif want != camp_fp:
                continue

        cat = str(camp.get("categoria") or "").strip().lower()
        pct = float(camp.get("discount_pct") or 0)
        if not cat or pct <= 0:
            continue

        matching_sub = 0.0
        matched = 0
        for line in lines or []:
            if not isinstance(line, dict):
                continue
            if line.get("troca") or float(line.get("qtd") or 0) < 0:
                continue
            pid = str(line.get("id") or line.get("prod_id") or "")
            prod = catalog.get(pid) or {}
            line_cat = str(
                line.get("categoria")
                or line.get("cat")
                or prod.get("categoria")
                or prod.get("cat")
                or ""
            ).strip().lower()
            if line_cat != cat:
                continue
            matching_sub += _line_subtotal(line)
            matched += 1

        if matched <= 0 or matching_sub <= 0:
            continue

        d = round(matching_sub * pct / 100.0, 2)
        label = f"{camp.get('name')} −{pct:g}%"
        if camp_fp and want is None and provisional:
            hints.append({
                "campaign_id": camp.get("id"),
                "label": label + f" (no {camp.get('forma_pg')})",
                "discount": d,
                "forma_pg": camp.get("forma_pg"),
            })
            continue

        discount += d
        applied.append({
            "campaign_id": camp.get("id"),
            "label": label,
            "discount": d,
            "forma_pg": camp.get("forma_pg") or "",
            "categoria": camp.get("categoria"),
        })

    return {
        "discount": round(discount, 2),
        "label": " · ".join(a["label"] for a in applied),
        "applied": applied,
        "hints": hints,
    }
