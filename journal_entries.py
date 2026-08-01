"""
Lançamentos contábeis (RFC-8003 MVP).

Partida dobrada: rascunho → postado; estorno gera lançamento inverso.
Fonte: dados/lancamentos.json
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import journals
import planocontas

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "lancamentos.json")

STATUSES = ("draft", "posted", "cancelled")
MONEY = Decimal("0.01")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _money(val):
    try:
        d = Decimal(str(val if val is not None else "0"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("valor monetário inválido") from None
    return d.quantize(MONEY, rounding=ROUND_HALF_UP)


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return {"atualizado_em": None, "lancamentos": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"atualizado_em": None, "lancamentos": []}
    if not isinstance(data.get("lancamentos"), list):
        data["lancamentos"] = []
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("lancamentos") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _find(data, key):
    k = str(key or "").strip()
    if not k:
        return None, None
    for i, row in enumerate(data.get("lancamentos") or []):
        if str(row.get("id")) == k or str(row.get("numero")) == k:
            return i, row
    return None, None


def _parse_linhas(raw_lines):
    if not isinstance(raw_lines, list) or len(raw_lines) < 2:
        raise ValueError("informe ao menos 2 linhas (débito e crédito)")
    linhas = []
    total_d = Decimal("0")
    total_c = Decimal("0")
    for i, ln in enumerate(raw_lines, start=1):
        if not isinstance(ln, dict):
            raise ValueError(f"linha {i} inválida")
        conta_ref = str(ln.get("conta") or "").strip()
        if not conta_ref:
            raise ValueError(f"linha {i}: conta obrigatória")
        conta = planocontas.get_conta(conta_ref)
        if not conta:
            raise ValueError(f"linha {i}: conta não encontrada ({conta_ref})")
        if str(conta.get("tipo") or "").upper() != "A":
            raise ValueError(
                f"linha {i}: use conta analítica ({conta.get('classificacao') or conta_ref})"
            )
        deb = _money(ln.get("debito") or 0)
        cred = _money(ln.get("credito") or 0)
        if deb < 0 or cred < 0:
            raise ValueError(f"linha {i}: valores não podem ser negativos")
        if (deb > 0 and cred > 0) or (deb == 0 and cred == 0):
            raise ValueError(f"linha {i}: informe débito ou crédito (não ambos)")
        hist = str(ln.get("historico") or "").strip()
        linhas.append(
            {
                "conta": str(conta.get("classificacao") or conta.get("codigo")),
                "conta_codigo": str(conta.get("codigo") or ""),
                "conta_nome": str(conta.get("nome") or conta.get("descricao") or ""),
                "debito": float(deb),
                "credito": float(cred),
                "historico": hist,
            }
        )
        total_d += deb
        total_c += cred
    return linhas, total_d, total_c


def _balanced(total_d, total_c):
    return total_d == total_c and total_d > 0


def _enrich(row):
    out = dict(row)
    diario = journals.get_diario(out.get("diario"))
    out["diario_nome"] = (diario or {}).get("nome") or ""
    out["diario_tipo"] = (diario or {}).get("tipo") or ""
    out["balanceado"] = _balanced(
        _money(out.get("total_debito") or 0), _money(out.get("total_credito") or 0)
    )
    return out


def list_lancamentos(q=None, diario=None, status=None, limit=200):
    rows = list(_load_raw().get("lancamentos") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("numero") or "").lower()
            or qq in str(r.get("historico") or "").lower()
            or qq in str(r.get("referencia") or "").lower()
            or qq in str(r.get("diario") or "").lower()
        ]
    if diario:
        d = str(diario).strip().upper()
        rows = [r for r in rows if str(r.get("diario") or "").upper() == d]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido (draft|posted|cancelled)")
        rows = [r for r in rows if str(r.get("status") or "") == st]
    rows.sort(key=lambda r: (str(r.get("data") or ""), str(r.get("numero") or "")), reverse=True)
    try:
        lim = max(1, min(int(limit or 200), 2000))
    except (TypeError, ValueError):
        lim = 200
    return {
        "total": len(_load_raw().get("lancamentos") or []),
        "filtrado": len(rows),
        "lancamentos": [_enrich(r) for r in rows[:lim]],
    }


def get_lancamento(key):
    _, row = _find(_load_raw(), key)
    return _enrich(row) if row else None


def create_lancamento(payload):
    body = payload if isinstance(payload, dict) else {}
    diario_cod = str(body.get("diario") or "").strip().upper()
    if not diario_cod:
        raise ValueError("diario obrigatório")
    diario = journals.get_diario(diario_cod)
    if not diario:
        raise ValueError(f"diário não encontrado: {diario_cod}")
    if not diario.get("ativo", True):
        raise ValueError(f"diário {diario_cod} está inativo")

    data_lanc = str(body.get("data") or date.today().isoformat()).strip()
    try:
        date.fromisoformat(data_lanc[:10])
        data_lanc = data_lanc[:10]
    except ValueError as e:
        raise ValueError("data inválida (YYYY-MM-DD)") from e

    linhas, total_d, total_c = _parse_linhas(body.get("linhas"))
    numero = journals.allocate_numero(diario_cod)
    row = {
        "id": str(uuid.uuid4()),
        "numero": numero,
        "diario": diario_cod,
        "data": data_lanc,
        "referencia": str(body.get("referencia") or "").strip(),
        "historico": str(body.get("historico") or "").strip() or f"Lançamento {numero}",
        "status": "draft",
        "linhas": linhas,
        "total_debito": float(total_d),
        "total_credito": float(total_c),
        "origem": str(body.get("origem") or "manual").strip() or "manual",
        "origem_ref": str(body.get("origem_ref") or "").strip(),
        "estorna_id": None,
        "estornado_por": None,
        "criado_em": _now(),
        "atualizado_em": _now(),
        "posted_em": None,
    }
    data = _load_raw()
    data["lancamentos"].append(row)
    _save(data)
    return _enrich(row)


def update_lancamento(key, payload):
    data = _load_raw()
    idx, existing = _find(data, key)
    if existing is None:
        raise ValueError("lançamento não encontrado")
    if existing.get("status") != "draft":
        raise ValueError("somente rascunho pode ser editado")
    body = payload if isinstance(payload, dict) else {}

    diario_cod = str(
        body.get("diario") if body.get("diario") is not None else existing.get("diario") or ""
    ).strip().upper()
    if diario_cod != str(existing.get("diario") or "").upper():
        raise ValueError("não é possível trocar o diário após criar o número")

    data_lanc = str(
        body.get("data") if body.get("data") is not None else existing.get("data") or ""
    ).strip()
    try:
        date.fromisoformat(data_lanc[:10])
        data_lanc = data_lanc[:10]
    except ValueError as e:
        raise ValueError("data inválida (YYYY-MM-DD)") from e

    if "linhas" in body:
        linhas, total_d, total_c = _parse_linhas(body.get("linhas"))
    else:
        linhas = existing.get("linhas") or []
        total_d = _money(existing.get("total_debito") or 0)
        total_c = _money(existing.get("total_credito") or 0)

    row = dict(existing)
    row.update(
        {
            "data": data_lanc,
            "referencia": str(
                body.get("referencia")
                if body.get("referencia") is not None
                else existing.get("referencia")
                or ""
            ).strip(),
            "historico": str(
                body.get("historico")
                if body.get("historico") is not None
                else existing.get("historico")
                or ""
            ).strip(),
            "linhas": linhas,
            "total_debito": float(total_d),
            "total_credito": float(total_c),
            "atualizado_em": _now(),
        }
    )
    data["lancamentos"][idx] = row
    _save(data)
    return _enrich(row)


def delete_lancamento(key):
    data = _load_raw()
    idx, existing = _find(data, key)
    if existing is None:
        raise ValueError("lançamento não encontrado")
    if existing.get("status") != "draft":
        raise ValueError("somente rascunho pode ser excluído — estorne o postado")
    data["lancamentos"].pop(idx)
    _save(data)
    return True


def post_lancamento(key):
    data = _load_raw()
    idx, existing = _find(data, key)
    if existing is None:
        raise ValueError("lançamento não encontrado")
    if existing.get("status") != "draft":
        raise ValueError("somente rascunho pode ser postado")
    total_d = _money(existing.get("total_debito") or 0)
    total_c = _money(existing.get("total_credito") or 0)
    if not _balanced(total_d, total_c):
        raise ValueError(
            f"lançamento desbalanceado: débito {total_d} ≠ crédito {total_c}"
        )
    # revalida contas
    _parse_linhas(existing.get("linhas") or [])
    row = dict(existing)
    row["status"] = "posted"
    row["posted_em"] = _now()
    row["atualizado_em"] = _now()
    data["lancamentos"][idx] = row
    _save(data)
    journals.mark_uso(row.get("diario"), 1)
    return _enrich(row)


def reverse_lancamento(key, payload=None):
    """Estorna lançamento postado criando lançamento inverso já postado."""
    body = payload if isinstance(payload, dict) else {}
    data = _load_raw()
    idx, existing = _find(data, key)
    if existing is None:
        raise ValueError("lançamento não encontrado")
    if existing.get("status") != "posted":
        raise ValueError("somente lançamento postado pode ser estornado")
    if existing.get("estornado_por"):
        raise ValueError("lançamento já estornado")

    rev_lines = []
    for ln in existing.get("linhas") or []:
        rev_lines.append(
            {
                "conta": ln.get("conta"),
                "debito": ln.get("credito") or 0,
                "credito": ln.get("debito") or 0,
                "historico": f"Estorno {existing.get('numero')}",
            }
        )
    linhas, total_d, total_c = _parse_linhas(rev_lines)
    numero = journals.allocate_numero(existing.get("diario"))
    rev = {
        "id": str(uuid.uuid4()),
        "numero": numero,
        "diario": existing.get("diario"),
        "data": str(body.get("data") or date.today().isoformat())[:10],
        "referencia": str(body.get("referencia") or existing.get("referencia") or "").strip(),
        "historico": str(body.get("historico") or f"Estorno de {existing.get('numero')}").strip(),
        "status": "posted",
        "linhas": linhas,
        "total_debito": float(total_d),
        "total_credito": float(total_c),
        "origem": "estorno",
        "origem_ref": str(existing.get("numero") or ""),
        "estorna_id": existing.get("id"),
        "estornado_por": None,
        "criado_em": _now(),
        "atualizado_em": _now(),
        "posted_em": _now(),
    }
    # Original permanece posted (imutável no razão); correção = novo lançamento.
    existing = dict(existing)
    existing["estornado_por"] = rev["id"]
    existing["atualizado_em"] = _now()
    data["lancamentos"][idx] = existing
    data["lancamentos"].append(rev)
    _save(data)
    journals.mark_uso(rev.get("diario"), 1)
    return _enrich(rev)
