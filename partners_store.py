"""
Business Partners — store COBOL (fonte da verdade).

.dat SEQUENTIAL:
  dados/parceiros.dat
  dados/parceiros_end.dat
  dados/parceiros_ctt.dat

Projeção: data/partners.json (consulta/UI).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

import cobol_bridge
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "data", "partners.json")
DAT_CORE = os.path.join(BASE_DIR, "dados", "parceiros.dat")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _clip(val, n):
    s = str(val if val is not None else "")
    s = s.replace('"', "'").replace("\n", " ").replace("\r", " ")
    return s[:n]


def _parse_blob(out, key):
    text = (out or "").strip()
    marker = '{"' + key + '":'
    start = text.find(marker)
    if start < 0:
        return []
    try:
        return json.loads(text[start:]).get(key) or []
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip().rstrip(",")
            if line.startswith("{") and '"id"' in line or '"partner_id"' in line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return rows


def _yn(val):
    if val is True or str(val).lower() in ("1", "s", "y", "true", "sim"):
        return "S"
    if val is False or str(val).lower() in ("0", "n", "false", "nao", "não"):
        return "N"
    return "S" if val else "N"


def _roles_str(roles):
    if isinstance(roles, str):
        return _clip(roles.replace(" ", ""), 40)
    if isinstance(roles, list):
        return _clip(",".join(str(r) for r in roles), 40)
    return "CUSTOMER"


def _roles_list(s):
    return [x.strip() for x in str(s or "").split(",") if x.strip()]


def _docs_from_core(cnpj, ie):
    docs = []
    if cnpj:
        docs.append({"id": "d1", "document_type": "CNPJ", "document_number": cnpj})
    if ie:
        docs.append({"id": "d2", "document_type": "IE", "document_number": ie})
    return docs


def _cnpj_ie_from_docs(documents):
    cnpj, ie = "", ""
    for d in documents or []:
        if not isinstance(d, dict):
            continue
        dtype = str(d.get("document_type") or "").upper()
        num = str(d.get("document_number") or "").strip()
        if dtype == "CNPJ" and num:
            cnpj = num
        elif dtype in ("IE", "STATE_REGISTRATION") and num:
            ie = num
    return cnpj, ie


def _normalize_core(row):
    pid = str(row.get("id") or "").strip()
    blocked = str(row.get("credit_blocked") or "N").upper() == "S"
    ativo = str(row.get("ativo") or "S").upper() != "N"
    cnpj = row.get("cnpj") or ""
    ie = row.get("ie") or ""
    return {
        "id": pid,
        "partner_code": row.get("partner_code") or "",
        "person_type": row.get("person_type") or "COMPANY",
        "display_name": row.get("display_name") or "",
        "legal_name": row.get("legal_name") or "",
        "trade_name": row.get("trade_name") or "",
        "status": row.get("status") or ("ACTIVE" if ativo else "INACTIVE"),
        "roles": _roles_list(row.get("roles")),
        "documents": _docs_from_core(cnpj, ie),
        "default_price_list_id": row.get("default_price_list_id") or "",
        "credit_limit": float(row.get("credit_limit") or 0),
        "payment_terms": row.get("payment_terms") or "30",
        "credit_blocked": blocked,
        "regime": row.get("regime") or "SN",
        "contribuinte_icms": row.get("contribuinte_icms") or "1",
        "observacao": row.get("observacao") or "",
        "ativo": ativo,
        "cnpj": cnpj,
        "ie": ie,
    }


def _normalize_addr(a, seq=None):
    pref = str(a.get("preferred") or a.get("pref") or "N").upper() == "S" or a.get("preferred") is True
    return {
        "id": a.get("id") or f"a{seq or a.get('seq') or 1}",
        "address_type": a.get("address_type") or a.get("type") or "HEADQUARTERS",
        "zip_code": a.get("zip_code") or a.get("zip") or "",
        "street": a.get("street") or "",
        "number": a.get("number") or "",
        "district": a.get("district") or "",
        "city": a.get("city") or "",
        "state": a.get("state") or a.get("uf") or "",
        "country": a.get("country") or "BR",
        "preferred": pref,
    }


def _normalize_ctt(c, seq=None):
    pref = str(c.get("preferred") or "N").upper() == "S" or c.get("preferred") is True
    return {
        "id": c.get("id") or f"c{seq or c.get('seq') or 1}",
        "name": c.get("name") or "",
        "department": c.get("department") or "",
        "job_title": c.get("job_title") or "",
        "email": c.get("email") or "",
        "phone": c.get("phone") or "",
        "mobile": c.get("mobile") or "",
        "preferred": pref,
    }


def listar_cores():
    out, _ = cobol_bridge._run("gerir_parceiros", {"ACAO": "listar"})
    return [_normalize_core(r) for r in _parse_blob(out, "parceiros")]


def listar_enderecos(partner_id=None):
    if partner_id:
        out, _ = cobol_bridge._run(
            "gerir_end_parceiro",
            {"ACAO": "listar-bp", "PARTNER_ID": str(partner_id)},
        )
    else:
        out, _ = cobol_bridge._run("gerir_end_parceiro", {"ACAO": "listar"})
    return _parse_blob(out, "enderecos")


def listar_contatos(partner_id=None):
    if partner_id:
        out, _ = cobol_bridge._run(
            "gerir_ctt_parceiro",
            {"ACAO": "listar-bp", "PARTNER_ID": str(partner_id)},
        )
    else:
        out, _ = cobol_bridge._run("gerir_ctt_parceiro", {"ACAO": "listar"})
    return _parse_blob(out, "contatos")


def as_dict():
    """Shape legado {id: partner} para partner_lookup / UI."""
    cores = listar_cores()
    ends = listar_enderecos()
    ctts = listar_contatos()
    by_end, by_ctt = {}, {}
    for a in ends:
        pid = str(a.get("partner_id") or "")
        by_end.setdefault(pid, []).append(
            _normalize_addr(a, a.get("seq"))
        )
    for c in ctts:
        pid = str(c.get("partner_id") or "")
        by_ctt.setdefault(pid, []).append(
            _normalize_ctt(c, c.get("seq"))
        )
    out = {}
    for core in cores:
        pid = core["id"]
        row = dict(core)
        row.pop("cnpj", None)
        row.pop("ie", None)
        row["addresses"] = by_end.get(pid, [])
        row["contacts"] = by_ctt.get(pid, [])
        row["bank_accounts"] = []
        out[pid] = row
    return out


def get(partner_id):
    d = as_dict()
    return d.get(str(partner_id or "").strip())


def _core_env(p, pid=None):
    cnpj, ie = _cnpj_ie_from_docs(p.get("documents"))
    if not cnpj:
        cnpj = p.get("cnpj") or ""
    if not ie:
        ie = p.get("ie") or ""
    env = {
        "PARTNER_CODE": _clip(p.get("partner_code"), 16),
        "PERSON_TYPE": _clip(p.get("person_type") or "COMPANY", 10),
        "DISPLAY_NAME": _clip(p.get("display_name") or p.get("trade_name") or p.get("legal_name"), 40),
        "LEGAL_NAME": _clip(p.get("legal_name"), 60),
        "TRADE_NAME": _clip(p.get("trade_name"), 40),
        "STATUS": _clip(p.get("status") or ("ACTIVE" if p.get("ativo", True) else "INACTIVE"), 10),
        "ROLES": _roles_str(p.get("roles")),
        "CNPJ": _clip(cnpj, 18),
        "IE": _clip(ie, 20),
        "PRICE_LIST": _clip(p.get("default_price_list_id"), 20),
        "CREDIT_LIMIT": str(p.get("credit_limit") or 0),
        "PAYMENT_TERMS": _clip(p.get("payment_terms") or "30", 20),
        "CREDIT_BLOCKED": _yn(p.get("credit_blocked")),
        "REGIME": _clip(p.get("regime") or "SN", 4),
        "CONTRIBUINTE": _clip(p.get("contribuinte_icms") or "1", 2),
        "OBSERVACAO": _clip(p.get("observacao"), 60),
        "ATIVO": _yn(p.get("ativo", True) if p.get("status") != "INACTIVE" else False),
    }
    if pid:
        env["ID"] = _clip(pid, 12)
    return env


def _replace_enderecos(pid, addresses):
    cobol_bridge._run("gerir_end_parceiro", {"ACAO": "limpar", "PARTNER_ID": pid})
    for i, a in enumerate(addresses or [], start=1):
        cobol_bridge._run(
            "gerir_end_parceiro",
            {
                "ACAO": "incluir",
                "PARTNER_ID": pid,
                "SEQ": str(i),
                "ADDRESS_TYPE": _clip(a.get("address_type") or "HEADQUARTERS", 16),
                "ZIP": _clip(a.get("zip_code"), 10),
                "STREET": _clip(a.get("street"), 40),
                "NUMBER": _clip(a.get("number"), 10),
                "DISTRICT": _clip(a.get("district"), 30),
                "CITY": _clip(a.get("city"), 30),
                "STATE": _clip(a.get("state") or a.get("uf"), 2),
                "COUNTRY": _clip(a.get("country") or "BR", 2),
                "PREFERRED": _yn(a.get("preferred")),
            },
        )


def _replace_contatos(pid, contacts):
    cobol_bridge._run("gerir_ctt_parceiro", {"ACAO": "limpar", "PARTNER_ID": pid})
    for i, c in enumerate(contacts or [], start=1):
        cobol_bridge._run(
            "gerir_ctt_parceiro",
            {
                "ACAO": "incluir",
                "PARTNER_ID": pid,
                "SEQ": str(i),
                "NAME": _clip(c.get("name"), 40),
                "DEPARTMENT": _clip(c.get("department"), 20),
                "JOB_TITLE": _clip(c.get("job_title"), 20),
                "EMAIL": _clip(c.get("email"), 40),
                "PHONE": _clip(c.get("phone"), 20),
                "MOBILE": _clip(c.get("mobile"), 20),
                "PREFERRED": _yn(c.get("preferred")),
            },
        )


def save(partner, *, partner_id=None, is_new=False):
    p = dict(partner or {})
    pid = partner_id or p.get("id")
    env = _core_env(p, pid if not is_new else pid)
    if is_new or not pid:
        env["ACAO"] = "incluir"
        if pid:
            env["ID"] = _clip(pid, 12)
        out, err = cobol_bridge._run("gerir_parceiros", env)
        new_id = None
        for line in (out or "").splitlines():
            line = line.strip()
            if line.startswith("ERRO:"):
                raise ValueError(line)
            if line and not line.startswith("{") and "ERRO" not in line:
                new_id = line
                break
        if not new_id:
            raise ValueError("falha ao incluir parceiro: " + (out or err or ""))
        pid = new_id
    else:
        env["ACAO"] = "alterar"
        env["ID"] = _clip(pid, 12)
        out, err = cobol_bridge._run("gerir_parceiros", env)
        if "ERRO:" in (out or ""):
            raise ValueError((out or err or "").strip())
    _replace_enderecos(pid, p.get("addresses") or [])
    _replace_contatos(pid, p.get("contacts") or [])
    sync_json()
    return get(pid)


def delete(partner_id):
    pid = str(partner_id or "").strip()
    out, _ = cobol_bridge._run("gerir_parceiros", {"ACAO": "excluir", "ID": pid})
    if "ERRO:" in (out or ""):
        raise ValueError((out or "").strip())
    cobol_bridge._run("gerir_end_parceiro", {"ACAO": "limpar", "PARTNER_ID": pid})
    cobol_bridge._run("gerir_ctt_parceiro", {"ACAO": "limpar", "PARTNER_ID": pid})
    sync_json()
    return True


def sync_json(data=None):
    payload = data if data is not None else as_dict()
    os.makedirs(os.path.dirname(JSON_FILE) or ".", exist_ok=True)
    # marca meta sem quebrar shape dict-by-id
    jsonio.save(JSON_FILE, payload)
    return payload


def migrate_json_to_cobol(force=False):
    if os.path.exists(DAT_CORE) and os.path.getsize(DAT_CORE) > 0 and not force:
        return {"migrated": 0, "message": "dat ja existe"}
    if not os.path.exists(JSON_FILE):
        return {"migrated": 0, "message": "sem json"}
    if force:
        for name in ("parceiros.dat", "parceiros.tmp", "parceiros_end.dat",
                     "parceiros_end.tmp", "parceiros_ctt.dat", "parceiros_ctt.tmp"):
            p = os.path.join(BASE_DIR, "dados", name)
            if os.path.exists(p):
                os.remove(p)
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"migrated": 0, "message": "json invalido"}
    n = 0
    for pid, p in data.items():
        if not isinstance(p, dict):
            continue
        # ignora chaves meta
        if pid.startswith("_"):
            continue
        try:
            row = dict(p)
            row["id"] = pid
            save(row, partner_id=pid, is_new=True)
            n += 1
        except Exception:
            continue
    sync_json()
    return {"migrated": n, "message": "ok"}
