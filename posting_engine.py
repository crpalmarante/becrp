"""
Posting Engine (RFC-8004 MVP).

Gate de validação antes do lançamento virar verdade contábil (ledger).
Também mantém regras evento→diário/contas para gerar lançamentos.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import accounting_periods
import journal_entries
import journals
import planocontas

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(BASE_DIR, "dados", "posting_rules.json")
HISTORY_FILE = os.path.join(BASE_DIR, "dados", "posting_history.json")

MONEY = Decimal("0.01")

# Seed: regras simples (2 linhas: D/C). Contas = plano referencial.
SEED_RULES = (
    {
        "codigo": "SALE_CASH",
        "nome": "Venda à vista (caixa)",
        "evento": "sale_cash",
        "diario": "VEN",
        "conta_debito": "1.01.01.01.01",
        "conta_credito": "3.01.01.01.01.05",
        "auto_post": True,
    },
    {
        "codigo": "SALE_BANK",
        "nome": "Venda (banco/PIX)",
        "evento": "sale_bank",
        "diario": "VEN",
        "conta_debito": "1.01.01.02.01",
        "conta_credito": "3.01.01.01.01.05",
        "auto_post": True,
    },
    {
        "codigo": "PURCHASE",
        "nome": "Compra a prazo (fornecedor)",
        "evento": "purchase",
        "diario": "COM",
        "conta_debito": "1.01.03.01.01",
        "conta_credito": "2.01.01.03.01",
        "auto_post": False,
    },
    {
        "codigo": "INV_ADJ_UP",
        "nome": "Ajuste estoque (+)",
        "evento": "inventory_adjust_up",
        "diario": "EST",
        "conta_debito": "1.01.03.01.01",
        "conta_credito": "3.01.01.05.01.99",
        "auto_post": False,
    },
    {
        "codigo": "CASH_IN",
        "nome": "Suprimento de caixa",
        "evento": "cash_in",
        "diario": "CXA",
        "conta_debito": "1.01.01.01.01",
        "conta_credito": "1.01.01.02.01",
        "auto_post": True,
    },
)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _money(val):
    try:
        d = Decimal(str(val if val is not None else "0"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("valor monetário inválido") from None
    return d.quantize(MONEY, rounding=ROUND_HALF_UP)


def _load_json(path, empty):
    if not os.path.exists(path):
        return empty
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else empty


def _save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_rules():
    data = _load_json(RULES_FILE, None)
    if data is None or not isinstance(data.get("regras"), list) or not data["regras"]:
        return ensure_seed_rules()
    return data


def _save_rules(data):
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("regras") or [])
    _save_json(RULES_FILE, data)


def ensure_seed_rules():
    rows = []
    for s in SEED_RULES:
        rows.append(_build_rule(s, existing=None, codigo=s["codigo"]))
    data = {"atualizado_em": _now(), "regras": rows, "total": len(rows)}
    _save_rules(data)
    return data


def _load_history():
    data = _load_json(HISTORY_FILE, {"atualizado_em": None, "eventos": []})
    if not isinstance(data.get("eventos"), list):
        data["eventos"] = []
    return data


def _append_history(event):
    data = _load_history()
    data["eventos"].append(event)
    # keep last 500
    if len(data["eventos"]) > 500:
        data["eventos"] = data["eventos"][-500:]
    data["atualizado_em"] = _now()
    _save_json(HISTORY_FILE, data)
    return event


def _resolve_conta(ref, label="conta"):
    key = str(ref or "").strip()
    if not key:
        raise ValueError(f"{label} obrigatória")
    conta = planocontas.get_conta(key)
    if not conta:
        raise ValueError(f"{label} não encontrada: {key}")
    if str(conta.get("tipo") or "").upper() != "A":
        raise ValueError(f"{label} deve ser analítica: {key}")
    return str(conta.get("classificacao") or conta.get("codigo")), conta


def _period_allows(data_lanc):
    """RFC-8006: só open/closing permitem postagem."""
    ok, err, _periodo = accounting_periods.allows_posting(data_lanc)
    return ok, err


def validate_entry(entry):
    """Valida lançamento antes do post. Retorna {ok, errors, warnings}."""
    errors = []
    warnings = []
    if not entry:
        return {"ok": False, "errors": ["lançamento não encontrado"], "warnings": []}

    status = str(entry.get("status") or "")
    if status != "draft":
        errors.append(f"status deve ser draft (atual: {status or '—'})")

    diario = journals.get_diario(entry.get("diario"))
    if not diario:
        errors.append(f"diário inválido: {entry.get('diario')}")
    elif not diario.get("ativo", True):
        errors.append(f"diário inativo: {entry.get('diario')}")

    ok_period, period_err = _period_allows(entry.get("data"))
    if not ok_period:
        errors.append(period_err or "período contábil fechado")

    try:
        total_d = _money(entry.get("total_debito") or 0)
        total_c = _money(entry.get("total_credito") or 0)
    except ValueError as e:
        errors.append(str(e))
        total_d = total_c = Decimal("0")

    if total_d != total_c:
        errors.append(f"desbalanceado: débito {total_d} ≠ crédito {total_c}")
    if total_d <= 0:
        errors.append("total deve ser maior que zero")

    linhas = entry.get("linhas") or []
    if len(linhas) < 2:
        errors.append("mínimo de 2 linhas")
    for i, ln in enumerate(linhas, start=1):
        ref = ln.get("conta")
        conta = planocontas.get_conta(ref)
        if not conta:
            errors.append(f"linha {i}: conta inválida ({ref})")
            continue
        if str(conta.get("tipo") or "").upper() != "A":
            errors.append(f"linha {i}: conta não analítica ({ref})")
        try:
            deb = _money(ln.get("debito") or 0)
            cred = _money(ln.get("credito") or 0)
        except ValueError:
            errors.append(f"linha {i}: valor inválido")
            continue
        if (deb > 0 and cred > 0) or (deb == 0 and cred == 0):
            errors.append(f"linha {i}: informe débito ou crédito")

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}


def post(key, actor=None, source="api"):
    """Valida e posta. Em falha, registra histórico e não altera o lançamento."""
    entry = journal_entries.get_lancamento(key)
    result = validate_entry(entry)
    hist = {
        "id": str(uuid.uuid4()),
        "acao": "post",
        "lancamento_id": (entry or {}).get("id"),
        "numero": (entry or {}).get("numero"),
        "ok": result["ok"],
        "errors": result["errors"],
        "warnings": result.get("warnings") or [],
        "actor": str(actor or "").strip() or None,
        "source": source,
        "em": _now(),
    }
    if not result["ok"]:
        _append_history(hist)
        raise ValueError("; ".join(result["errors"]))

    posted = journal_entries.post_lancamento(key)
    hist["ok"] = True
    hist["posted_em"] = posted.get("posted_em")
    hist["numero"] = posted.get("numero")
    _append_history(hist)
    return posted


def reverse(key, payload=None, actor=None, source="api"):
    rev = journal_entries.reverse_lancamento(key, payload)
    _append_history(
        {
            "id": str(uuid.uuid4()),
            "acao": "reverse",
            "lancamento_id": rev.get("id"),
            "numero": rev.get("numero"),
            "estorna": rev.get("origem_ref") or key,
            "ok": True,
            "errors": [],
            "actor": str(actor or "").strip() or None,
            "source": source,
            "em": _now(),
        }
    )
    return rev


def list_history(limit=100):
    rows = list(_load_history().get("eventos") or [])
    rows.reverse()
    try:
        lim = max(1, min(int(limit or 100), 500))
    except (TypeError, ValueError):
        lim = 100
    return {"total": len(_load_history().get("eventos") or []), "eventos": rows[:lim]}


# ── Regras de posting (evento → lançamento) ──


def _build_rule(payload, existing=None, codigo=None):
    body = payload if isinstance(payload, dict) else {}
    cod = str(
        codigo or body.get("codigo") or (existing or {}).get("codigo") or ""
    ).strip().upper()
    if not cod:
        raise ValueError("codigo obrigatório")
    nome = str(
        body.get("nome") if body.get("nome") is not None else (existing or {}).get("nome") or ""
    ).strip()
    if not nome:
        raise ValueError("nome obrigatório")
    evento = str(
        body.get("evento")
        if body.get("evento") is not None
        else (existing or {}).get("evento")
        or ""
    ).strip().lower()
    if not evento:
        raise ValueError("evento obrigatório")
    diario_cod = str(
        body.get("diario")
        if body.get("diario") is not None
        else (existing or {}).get("diario")
        or ""
    ).strip().upper()
    diario = journals.get_diario(diario_cod)
    if not diario:
        raise ValueError(f"diário inválido: {diario_cod}")

    if "conta_debito" in body or existing is None:
        deb_ref = body.get("conta_debito") if "conta_debito" in body else None
    else:
        deb_ref = existing.get("conta_debito")
    if "conta_credito" in body or existing is None:
        cred_ref = body.get("conta_credito") if "conta_credito" in body else None
    else:
        cred_ref = existing.get("conta_credito")

    # fallback: conta padrão do diário no crédito ou débito conforme tipo
    if not deb_ref and not cred_ref and diario.get("conta_padrao"):
        raise ValueError("informe conta_debito e conta_credito")
    deb_key, _ = _resolve_conta(deb_ref, "conta_debito")
    cred_key, _ = _resolve_conta(cred_ref, "conta_credito")
    if deb_key == cred_key:
        raise ValueError("conta_debito e conta_credito devem ser diferentes")

    ativo = body.get("ativo") if "ativo" in body else (existing or {}).get("ativo", True)
    auto_post = (
        body.get("auto_post")
        if "auto_post" in body
        else (existing or {}).get("auto_post", False)
    )
    return {
        "codigo": cod,
        "nome": nome,
        "evento": evento,
        "diario": diario_cod,
        "conta_debito": deb_key,
        "conta_credito": cred_key,
        "auto_post": bool(auto_post),
        "ativo": bool(ativo),
        "origem": (existing or {}).get("origem") or "manual",
        "atualizado_em": _now(),
    }


def list_rules(q=None, evento=None, ativos=None):
    rows = list(_load_rules().get("regras") or [])
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            r
            for r in rows
            if qq in str(r.get("codigo") or "").lower()
            or qq in str(r.get("nome") or "").lower()
            or qq in str(r.get("evento") or "").lower()
        ]
    if evento:
        ev = str(evento).strip().lower()
        rows = [r for r in rows if r.get("evento") == ev]
    if ativos is True:
        rows = [r for r in rows if r.get("ativo", True)]
    elif ativos is False:
        rows = [r for r in rows if not r.get("ativo", True)]
    return {"total": len(_load_rules().get("regras") or []), "regras": rows}


def get_rule(codigo_or_evento):
    key = str(codigo_or_evento or "").strip()
    if not key:
        return None
    ku = key.upper()
    kl = key.lower()
    for r in _load_rules().get("regras") or []:
        if str(r.get("codigo") or "").upper() == ku or str(r.get("evento") or "") == kl:
            return r
    return None


def create_rule(payload):
    data = _load_rules()
    body = payload if isinstance(payload, dict) else {}
    codigo = str(body.get("codigo") or "").strip().upper()
    if any(str(r.get("codigo") or "").upper() == codigo for r in data["regras"]):
        raise ValueError(f"já existe regra {codigo}")
    row = _build_rule(body, codigo=codigo)
    row["origem"] = "manual"
    data["regras"].append(row)
    _save_rules(data)
    return row


def update_rule(codigo, payload):
    data = _load_rules()
    key = str(codigo or "").strip().upper()
    idx = None
    existing = None
    for i, r in enumerate(data.get("regras") or []):
        if str(r.get("codigo") or "").upper() == key:
            idx = i
            existing = r
            break
    if existing is None:
        raise ValueError("regra não encontrada")
    body = dict(payload or {})
    body.pop("codigo", None)
    row = _build_rule(body, existing=existing, codigo=existing.get("codigo"))
    data["regras"][idx] = row
    _save_rules(data)
    return row


def delete_rule(codigo):
    data = _load_rules()
    key = str(codigo or "").strip().upper()
    for i, r in enumerate(data.get("regras") or []):
        if str(r.get("codigo") or "").upper() == key:
            data["regras"].pop(i)
            _save_rules(data)
            return True
    raise ValueError("regra não encontrada")


def apply_event(payload, actor=None):
    """
    Gera lançamento a partir de regra de evento.

    payload: {evento|regra, valor, data?, referencia?, historico?, auto_post?}
    """
    body = payload if isinstance(payload, dict) else {}
    regra = get_rule(body.get("regra") or body.get("evento") or "")
    if not regra or not regra.get("ativo", True):
        raise ValueError("regra de posting não encontrada ou inativa")
    valor = _money(body.get("valor"))
    if valor <= 0:
        raise ValueError("valor deve ser > 0")

    data_lanc = str(body.get("data") or date.today().isoformat())[:10]
    ok_period, period_err = _period_allows(data_lanc)
    if not ok_period:
        raise ValueError(period_err or "período fechado")

    historico = str(body.get("historico") or regra.get("nome") or "").strip()
    referencia = str(body.get("referencia") or "").strip()
    linhas = [
        {
            "conta": regra["conta_debito"],
            "debito": float(valor),
            "credito": 0,
            "historico": historico,
        },
        {
            "conta": regra["conta_credito"],
            "debito": 0,
            "credito": float(valor),
            "historico": historico,
        },
    ]
    entry = journal_entries.create_lancamento(
        {
            "diario": regra["diario"],
            "data": data_lanc,
            "historico": historico,
            "referencia": referencia,
            "origem": f"posting:{regra.get('evento')}",
            "origem_ref": referencia or regra.get("codigo"),
            "linhas": linhas,
        }
    )
    do_auto = body.get("auto_post")
    if do_auto is None:
        do_auto = regra.get("auto_post", False)
    if do_auto:
        entry = post(entry["id"], actor=actor, source=f"rule:{regra.get('codigo')}")
    _append_history(
        {
            "id": str(uuid.uuid4()),
            "acao": "apply_event",
            "regra": regra.get("codigo"),
            "evento": regra.get("evento"),
            "lancamento_id": entry.get("id"),
            "numero": entry.get("numero"),
            "valor": float(valor),
            "ok": True,
            "errors": [],
            "actor": str(actor or "").strip() or None,
            "source": "apply_event",
            "em": _now(),
        }
    )
    return {"regra": regra, "lancamento": entry}
