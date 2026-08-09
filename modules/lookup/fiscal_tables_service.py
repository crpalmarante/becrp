"""
Serviço de lookup para tabelas fiscais: CFOP e CST.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFOP_FILE = os.path.join(BASE_DIR, "dados", "cfop.json")
CST_FILE = os.path.join(BASE_DIR, "dados", "cst.json")


def _load(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


@lru_cache(maxsize=1)
def _cfop_cache():
    data = _load(CFOP_FILE)
    return {c["codigo"]: c for c in data.get("cfop", []) if isinstance(c, dict)}


@lru_cache(maxsize=1)
def _cst_cache():
    data = _load(CST_FILE)
    return {c["codigo"]: c for c in data.get("cst", []) if isinstance(c, dict)}


def reload_cache():
    _cfop_cache.cache_clear()
    _cst_cache.cache_clear()


def list_cfop():
    return list(_cfop_cache().values())


def search_cfop(q=None, tipo=None, limit=50):
    rows = list_cfop()
    if tipo:
        rows = [r for r in rows if r.get("tipo") == tipo]
    if q:
        q = str(q).lower()
        rows = [r for r in rows if q in str(r.get("codigo") or "").lower() or q in str(r.get("descricao") or "").lower()]
    return rows[:limit]


def get_cfop(codigo):
    return _cfop_cache().get(str(codigo or ""))


def save_cfop(codigo, dados):
    data = _load(CFOP_FILE)
    rows = {r["codigo"]: r for r in data.get("cfop", []) if isinstance(r, dict)}
    cod = str(codigo).strip()
    rows[cod] = {
        "codigo": cod,
        "descricao": dados.get("descricao", ""),
        "tipo": dados.get("tipo", "saida"),
        "aplicacao": dados.get("aplicacao", ""),
        "ativo": bool(dados.get("ativo", True)),
    }
    data["cfop"] = list(rows.values())
    os.makedirs(os.path.dirname(CFOP_FILE), exist_ok=True)
    with open(CFOP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    reload_cache()
    return rows[cod]


def delete_cfop(codigo):
    data = _load(CFOP_FILE)
    rows = [r for r in data.get("cfop", []) if isinstance(r, dict) and str(r.get("codigo")) != str(codigo)]
    data["cfop"] = rows
    with open(CFOP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    reload_cache()
    return True


def list_cst():
    return list(_cst_cache().values())


def search_cst(q=None, tipo=None, regime=None, limit=50):
    rows = list_cst()
    if tipo:
        rows = [r for r in rows if r.get("tipo") == tipo]
    if regime:
        rows = [r for r in rows if r.get("regime") in (regime, "todos")]
    if q:
        q = str(q).lower()
        rows = [r for r in rows if q in str(r.get("codigo") or "").lower() or q in str(r.get("descricao") or "").lower()]
    return rows[:limit]


def get_cst(codigo):
    return _cst_cache().get(str(codigo or ""))


def save_cst(codigo, dados):
    data = _load(CST_FILE)
    rows = {r["codigo"]: r for r in data.get("cst", []) if isinstance(r, dict)}
    cod = str(codigo).strip()
    rows[cod] = {
        "codigo": cod,
        "descricao": dados.get("descricao", ""),
        "tipo": dados.get("tipo", "icms"),
        "regime": dados.get("regime", "todos"),
        "ativo": bool(dados.get("ativo", True)),
    }
    data["cst"] = list(rows.values())
    os.makedirs(os.path.dirname(CST_FILE), exist_ok=True)
    with open(CST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    reload_cache()
    return rows[cod]


def delete_cst(codigo):
    data = _load(CST_FILE)
    rows = [r for r in data.get("cst", []) if isinstance(r, dict) and str(r.get("codigo")) != str(codigo)]
    data["cst"] = rows
    with open(CST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    reload_cache()
    return True
