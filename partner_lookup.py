"""
Business Partner Lookup (RFC-4005).

Responsabilidade única: localizar um parceiro existente.
Não cria, não atualiza, não sincroniza.

Resultados: found | not_found | multiple
"""

from __future__ import annotations

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PARTNERS_FILE = os.path.join(DATA_DIR, "partners.json")
AUDIT_FILE = os.path.join(DATA_DIR, "partner_lookup_audit.json")
AUDIT_MAX = 200


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _digits(val):
    return "".join(ch for ch in str(val or "") if ch.isdigit())


def _load_partners():
    if not os.path.exists(PARTNERS_FILE):
        return {}
    with open(PARTNERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _audit(entry):
    try:
        rows = []
        if os.path.exists(AUDIT_FILE):
            with open(AUDIT_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                rows = raw
            elif isinstance(raw, dict) and isinstance(raw.get("entries"), list):
                rows = raw["entries"]
        rows.append(entry)
        rows = rows[-AUDIT_MAX:]
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(AUDIT_FILE, "w", encoding="utf-8") as f:
            json.dump({"entries": rows}, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _partner_docs(p):
    docs = p.get("documents") if isinstance(p.get("documents"), list) else []
    out = {"cnpj": "", "cpf": "", "ie": "", "external_ref": ""}
    for d in docs:
        if not isinstance(d, dict):
            continue
        dtype = str(d.get("document_type") or d.get("type") or "").upper()
        num = _digits(d.get("document_number") or d.get("number") or d.get("value"))
        if dtype == "CNPJ" and num:
            out["cnpj"] = num
        elif dtype == "CPF" and num:
            out["cpf"] = num
        elif dtype in ("IE", "STATE_REGISTRATION") and (d.get("document_number") or ""):
            out["ie"] = str(d.get("document_number") or "").strip()
        elif dtype in ("EXTERNAL", "EXTERNAL_REF", "REF") and (d.get("document_number") or ""):
            out["external_ref"] = str(d.get("document_number") or "").strip()
    # fallbacks flat
    if not out["cnpj"]:
        out["cnpj"] = _digits(p.get("cnpj"))
    if not out["cpf"]:
        out["cpf"] = _digits(p.get("cpf"))
    if not out["external_ref"]:
        out["external_ref"] = str(p.get("external_ref") or p.get("external_reference") or "").strip()
    return out


def _active(p):
    if p.get("ativo") is False:
        return False
    st = str(p.get("status") or "").upper()
    if st in ("INACTIVE", "BLOCKED", "CANCELLED"):
        return False
    return True


def _has_role(p, role):
    if not role:
        return True
    want = str(role).upper().strip()
    roles = p.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    roles_u = {str(r).upper() for r in roles}
    # aliases
    aliases = {
        "SUPPLIER": {"SUPPLIER", "FORNECEDOR", "VENDOR"},
        "CUSTOMER": {"CUSTOMER", "CLIENTE"},
        "CARRIER": {"CARRIER", "TRANSPORTADORA"},
    }
    accept = aliases.get(want, {want})
    return bool(roles_u & accept)


def _summary(pid, p):
    docs = _partner_docs(p)
    return {
        "id": pid,
        "partner_code": p.get("partner_code") or "",
        "display_name": p.get("display_name") or p.get("trade_name") or p.get("legal_name") or "",
        "legal_name": p.get("legal_name") or "",
        "trade_name": p.get("trade_name") or "",
        "roles": list(p.get("roles") or []),
        "cnpj": docs["cnpj"],
        "cpf": docs["cpf"],
        "status": p.get("status") or ("ACTIVE" if p.get("ativo") is not False else "INACTIVE"),
    }


def lookup(
    *,
    cnpj=None,
    cpf=None,
    partner_code=None,
    external_ref=None,
    partner_id=None,
    role=None,
    module="generic",
    audit=True,
):
    """
    Ordem RFC-4005: external_ref → CNPJ → CPF → internal code (partner_code / id).
    """
    criteria = {
        "external_ref": str(external_ref or "").strip(),
        "cnpj": _digits(cnpj),
        "cpf": _digits(cpf),
        "partner_code": str(partner_code or "").strip().upper(),
        "partner_id": str(partner_id or "").strip(),
        "role": str(role or "").strip().upper() or None,
    }
    data = _load_partners()
    candidates = []

    def consider(pid, p, via):
        if not isinstance(p, dict):
            return
        if not _active(p):
            return
        if not _has_role(p, criteria["role"]):
            return
        candidates.append((via, pid, p))

    # 1) external ref
    if criteria["external_ref"]:
        for pid, p in data.items():
            docs = _partner_docs(p)
            if docs["external_ref"] and docs["external_ref"] == criteria["external_ref"]:
                consider(pid, p, "external_ref")

    # 2) CNPJ
    if not candidates and criteria["cnpj"]:
        for pid, p in data.items():
            docs = _partner_docs(p)
            if docs["cnpj"] and docs["cnpj"] == criteria["cnpj"]:
                consider(pid, p, "cnpj")

    # 3) CPF
    if not candidates and criteria["cpf"]:
        for pid, p in data.items():
            docs = _partner_docs(p)
            if docs["cpf"] and docs["cpf"] == criteria["cpf"]:
                consider(pid, p, "cpf")

    # 4) internal code / id
    if not candidates and (criteria["partner_code"] or criteria["partner_id"]):
        for pid, p in data.items():
            code = str(p.get("partner_code") or "").strip().upper()
            if criteria["partner_id"] and pid == criteria["partner_id"]:
                consider(pid, p, "partner_id")
            elif criteria["partner_code"] and code == criteria["partner_code"]:
                consider(pid, p, "partner_code")

    # dedupe by pid keeping first via
    seen = {}
    ordered = []
    for via, pid, p in candidates:
        if pid in seen:
            continue
        seen[pid] = via
        ordered.append((via, pid, p))

    if len(ordered) == 1:
        via, pid, p = ordered[0]
        result = {
            "status": "found",
            "match": via,
            "partner": _summary(pid, p),
            "partners": [],
            "criteria": {k: v for k, v in criteria.items() if v},
        }
    elif len(ordered) > 1:
        result = {
            "status": "multiple",
            "match": None,
            "partner": None,
            "partners": [_summary(pid, p) for _, pid, p in ordered],
            "criteria": {k: v for k, v in criteria.items() if v},
        }
    else:
        result = {
            "status": "not_found",
            "match": None,
            "partner": None,
            "partners": [],
            "criteria": {k: v for k, v in criteria.items() if v},
        }

    if audit:
        _audit({
            "at": _now(),
            "module": module,
            "criteria": result["criteria"],
            "result": result["status"],
            "partner_id": (result.get("partner") or {}).get("id"),
            "count": 1 if result["status"] == "found" else len(result.get("partners") or []),
        })
    return result


def search(query, *, role=None, limit=20):
    """Busca auxiliar para UI (não é chave principal da RFC)."""
    q = str(query or "").strip()
    if not q:
        return []
    q_low = q.lower()
    q_dig = _digits(q)
    data = _load_partners()
    scored = []
    for pid, p in data.items():
        if not isinstance(p, dict) or not _active(p):
            continue
        if not _has_role(p, role):
            continue
        docs = _partner_docs(p)
        nome = (p.get("display_name") or p.get("trade_name") or p.get("legal_name") or "")
        score = 0
        if q_dig and docs["cnpj"] and (q_dig == docs["cnpj"] or docs["cnpj"].endswith(q_dig)):
            score += 100
        if q_dig and docs["cpf"] and q_dig == docs["cpf"]:
            score += 100
        if str(p.get("partner_code") or "").upper() == q.upper():
            score += 90
        if pid == q:
            score += 90
        if q_low and q_low in nome.lower():
            score += 40
        if q_low and q_low in (p.get("legal_name") or "").lower():
            score += 30
        if score <= 0:
            continue
        row = _summary(pid, p)
        row["score"] = score
        scored.append(row)
    scored.sort(key=lambda x: (-x["score"], x.get("display_name") or ""))
    return scored[: max(1, int(limit or 20))]
