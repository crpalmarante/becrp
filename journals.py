"""
Diários contábeis (RFC-8002 MVP).

CRUD de diários com conta padrão do plano de contas.
Fonte: dados/diarios.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import planocontas

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "diarios.json")

JOURNAL_TYPES = {
    "sales": "Vendas",
    "purchase": "Compras",
    "cash": "Caixa",
    "bank": "Banco",
    "inventory": "Estoque",
    "general": "Geral",
}

# Seed: conta_padrao = classificação analítica do plano referencial (quando existir).
SEED = (
    {
        "codigo": "VEN",
        "nome": "Diário de Vendas",
        "tipo": "sales",
        "prefixo": "VEN",
        "conta_padrao": "3.01.01.01.01.05",
    },
    {
        "codigo": "COM",
        "nome": "Diário de Compras",
        "tipo": "purchase",
        "prefixo": "COM",
        "conta_padrao": "2.01.01.03.01",
    },
    {
        "codigo": "CXA",
        "nome": "Diário de Caixa",
        "tipo": "cash",
        "prefixo": "CXA",
        "conta_padrao": "1.01.01.01.01",
    },
    {
        "codigo": "BCO",
        "nome": "Diário de Banco",
        "tipo": "bank",
        "prefixo": "BCO",
        "conta_padrao": "1.01.01.02.01",
    },
    {
        "codigo": "EST",
        "nome": "Diário de Estoque",
        "tipo": "inventory",
        "prefixo": "EST",
        "conta_padrao": "1.01.03.01.01",
    },
    {
        "codigo": "GER",
        "nome": "Diário Geral",
        "tipo": "general",
        "prefixo": "GER",
        "conta_padrao": "",
    },
)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _empty():
    return {"atualizado_em": None, "diarios": []}


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return ensure_seed()
    if not isinstance(data.get("diarios"), list):
        data["diarios"] = []
    if not data["diarios"]:
        return ensure_seed()
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("diarios") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_seed():
    """Cria seed padrão se arquivo ausente ou vazio."""
    rows = []
    for s in SEED:
        rows.append(_build_row(s, existing=None, codigo=s["codigo"]))
    data = {"atualizado_em": _now(), "diarios": rows, "total": len(rows)}
    _save(data)
    return data


def _norm_tipo(val):
    s = str(val or "").strip().lower()
    aliases = {
        "venda": "sales",
        "vendas": "sales",
        "compra": "purchase",
        "compras": "purchase",
        "caixa": "cash",
        "banco": "bank",
        "estoque": "inventory",
        "inventario": "inventory",
        "inventário": "inventory",
        "geral": "general",
    }
    s = aliases.get(s, s)
    if s not in JOURNAL_TYPES:
        raise ValueError(
            "tipo deve ser: sales, purchase, cash, bank, inventory ou general"
        )
    return s


def _resolve_conta(ref):
    """Valida conta no plano; retorna (classificacao|codigo, conta|None)."""
    key = str(ref or "").strip()
    if not key:
        return "", None
    conta = planocontas.get_conta(key)
    if not conta:
        raise ValueError(f"conta padrão não encontrada no plano: {key}")
    # Preferir classificação (mais legível); aceitar código também.
    return str(conta.get("classificacao") or conta.get("codigo") or key), conta


def _enrich(row):
    out = dict(row)
    out["tipo_label"] = JOURNAL_TYPES.get(out.get("tipo"), out.get("tipo") or "")
    ref = out.get("conta_padrao") or ""
    conta = planocontas.get_conta(ref) if ref else None
    if conta:
        out["conta_padrao_nome"] = conta.get("nome") or conta.get("descricao") or ""
        out["conta_padrao_codigo"] = conta.get("codigo") or ""
        out["conta_padrao_classificacao"] = conta.get("classificacao") or ""
    else:
        out["conta_padrao_nome"] = ""
        out["conta_padrao_codigo"] = ""
        out["conta_padrao_classificacao"] = ref
    return out


def _build_row(payload, existing=None, codigo=None):
    body = payload if isinstance(payload, dict) else {}
    cod = str(
        codigo
        or body.get("codigo")
        or (existing or {}).get("codigo")
        or ""
    ).strip().upper()
    if not cod:
        raise ValueError("codigo obrigatório")
    if len(cod) > 12:
        raise ValueError("codigo deve ter até 12 caracteres")
    nome = str(
        body.get("nome") if body.get("nome") is not None else (existing or {}).get("nome") or ""
    ).strip()
    if not nome:
        raise ValueError("nome obrigatório")
    tipo = _norm_tipo(
        body.get("tipo") if body.get("tipo") is not None else (existing or {}).get("tipo") or "general"
    )
    prefixo = str(
        body.get("prefixo")
        if body.get("prefixo") is not None
        else (existing or {}).get("prefixo")
        or cod
    ).strip().upper() or cod
    if "conta_padrao" in body:
        conta_ref = body.get("conta_padrao")
    else:
        conta_ref = (existing or {}).get("conta_padrao") or ""
    conta_key, _ = _resolve_conta(conta_ref)
    ativo = body.get("ativo") if "ativo" in body else (existing or {}).get("ativo", True)
    try:
        prox = int(
            body.get("proximo")
            if body.get("proximo") is not None
            else (existing or {}).get("proximo")
            or 1
        )
    except (TypeError, ValueError):
        raise ValueError("proximo deve ser número inteiro") from None
    if prox < 1:
        raise ValueError("proximo deve ser >= 1")
    usos = int((existing or {}).get("usos") or 0)
    return {
        "codigo": cod,
        "nome": nome,
        "tipo": tipo,
        "prefixo": prefixo,
        "proximo": prox,
        "conta_padrao": conta_key,
        "ativo": bool(ativo),
        "usos": usos,
        "origem": (existing or {}).get("origem") or "manual",
        "atualizado_em": _now(),
    }


def list_diarios(q=None, tipo=None, ativos=None):
    rows = list(_load_raw().get("diarios") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            d
            for d in rows
            if qq in str(d.get("codigo") or "").lower()
            or qq in str(d.get("nome") or "").lower()
            or qq in str(d.get("tipo") or "").lower()
            or qq in str(d.get("conta_padrao") or "").lower()
        ]
    if tipo:
        t = _norm_tipo(tipo)
        rows = [d for d in rows if d.get("tipo") == t]
    if ativos is True:
        rows = [d for d in rows if d.get("ativo", True)]
    elif ativos is False:
        rows = [d for d in rows if not d.get("ativo", True)]
    rows.sort(key=lambda d: (str(d.get("tipo") or ""), str(d.get("codigo") or "")))
    return {
        "total": len(_load_raw().get("diarios") or []),
        "filtrado": len(rows),
        "tipos": JOURNAL_TYPES,
        "diarios": [_enrich(d) for d in rows],
    }


def get_diario(codigo):
    key = str(codigo or "").strip().upper()
    if not key:
        return None
    for d in _load_raw().get("diarios") or []:
        if str(d.get("codigo") or "").upper() == key:
            return _enrich(d)
    return None


def create_diario(payload):
    data = _load_raw()
    body = payload if isinstance(payload, dict) else {}
    codigo = str(body.get("codigo") or "").strip().upper()
    if not codigo:
        raise ValueError("codigo obrigatório")
    if any(str(d.get("codigo") or "").upper() == codigo for d in data["diarios"]):
        raise ValueError(f"já existe diário com código {codigo}")
    row = _build_row(body, codigo=codigo)
    row["origem"] = "manual"
    row["usos"] = 0
    data["diarios"].append(row)
    _save(data)
    return _enrich(row)


def update_diario(codigo, payload):
    data = _load_raw()
    key = str(codigo or "").strip().upper()
    idx = None
    existing = None
    for i, d in enumerate(data.get("diarios") or []):
        if str(d.get("codigo") or "").upper() == key:
            idx = i
            existing = d
            break
    if existing is None:
        raise ValueError("diário não encontrado")
    body = dict(payload or {})
    # código imutável
    body.pop("codigo", None)
    row = _build_row(body, existing=existing, codigo=existing.get("codigo"))
    row["usos"] = int(existing.get("usos") or 0)
    row["origem"] = existing.get("origem") or "manual"
    data["diarios"][idx] = row
    _save(data)
    return _enrich(row)


def delete_diario(codigo):
    """Remove diário sem uso. Com lançamentos (usos>0), só inativar."""
    data = _load_raw()
    key = str(codigo or "").strip().upper()
    idx = None
    target = None
    for i, d in enumerate(data.get("diarios") or []):
        if str(d.get("codigo") or "").upper() == key:
            idx = i
            target = d
            break
    if target is None:
        raise ValueError("diário não encontrado")
    if int(target.get("usos") or 0) > 0:
        raise ValueError(
            "não é possível excluir: diário já possui lançamentos — inative-o"
        )
    data["diarios"].pop(idx)
    _save(data)
    return True


def mark_uso(codigo, n=1):
    """Incrementa contador de uso (chamado pelos lançamentos no futuro)."""
    data = _load_raw()
    key = str(codigo or "").strip().upper()
    for i, d in enumerate(data.get("diarios") or []):
        if str(d.get("codigo") or "").upper() == key:
            d["usos"] = int(d.get("usos") or 0) + max(1, int(n or 1))
            d["atualizado_em"] = _now()
            data["diarios"][i] = d
            _save(data)
            return _enrich(d)
    raise ValueError("diário não encontrado")
