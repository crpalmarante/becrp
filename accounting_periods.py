"""
Períodos contábeis (RFC-8006 MVP).

Exercício + meses; controla se a data do lançamento pode ser postada.
Fonte: dados/periodos.json
"""

from __future__ import annotations

import json
import os
from calendar import monthrange
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "periodos.json")

STATUSES = ("open", "closing", "closed", "locked")
STATUS_LABELS = {
    "open": "Aberto",
    "closing": "Em fechamento",
    "closed": "Fechado",
    "locked": "Bloqueado",
}
MONTH_NAMES = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _empty():
    return {"atualizado_em": None, "exercicios": [], "periodos": []}


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return _empty()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return _empty()
    if not isinstance(data.get("periodos"), list):
        data["periodos"] = []
    if not isinstance(data.get("exercicios"), list):
        data["exercicios"] = []
    return data


def _ensure_data():
    data = _load_raw()
    if data.get("periodos"):
        return data
    return ensure_year(date.today().year, status="open")


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("periodos") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_seed():
    """Garante exercício do ano corrente com 12 meses abertos."""
    return ensure_year(date.today().year, status="open")


def _period_row(year, month, status="open"):
    last = monthrange(year, month)[1]
    codigo = f"{year}-{month:02d}"
    return {
        "codigo": codigo,
        "exercicio": year,
        "mes": month,
        "nome": f"{MONTH_NAMES[month - 1]}/{year}",
        "inicio": f"{year}-{month:02d}-01",
        "fim": f"{year}-{month:02d}-{last:02d}",
        "status": status if status in STATUSES else "open",
        "atualizado_em": _now(),
    }


def ensure_year(ano, status="open"):
    """Cria exercício e 12 períodos mensais se ainda não existirem."""
    try:
        year = int(ano)
    except (TypeError, ValueError) as e:
        raise ValueError("exercício inválido") from e
    if year < 2000 or year > 2100:
        raise ValueError("exercício fora da faixa permitida")
    st = str(status or "open").strip().lower()
    if st not in STATUSES:
        raise ValueError("status inválido")

    data = _load_raw()
    exercicios = list(data.get("exercicios") or [])
    if year not in exercicios:
        exercicios.append(year)
        exercicios.sort()
    data["exercicios"] = exercicios

    existing = {str(p.get("codigo")) for p in data.get("periodos") or []}
    created = []
    for m in range(1, 13):
        codigo = f"{year}-{m:02d}"
        if codigo in existing:
            continue
        row = _period_row(year, m, status=st)
        data.setdefault("periodos", []).append(row)
        created.append(codigo)
    data["periodos"].sort(key=lambda p: str(p.get("codigo") or ""))
    _save(data)
    return {
        "exercicio": year,
        "criados": created,
        "periodos": [_enrich(p) for p in data["periodos"] if int(p.get("exercicio") or 0) == year],
    }


def list_periodos(exercicio=None, status=None):
    data = _ensure_data()
    rows = list(data.get("periodos") or [])
    if exercicio is not None and str(exercicio).strip() != "":
        try:
            y = int(exercicio)
        except (TypeError, ValueError) as e:
            raise ValueError("exercício inválido") from e
        rows = [p for p in rows if int(p.get("exercicio") or 0) == y]
    if status:
        st = str(status).strip().lower()
        if st not in STATUSES:
            raise ValueError("status inválido")
        rows = [p for p in rows if p.get("status") == st]
    rows.sort(key=lambda p: str(p.get("codigo") or ""))
    return {
        "exercicios": list(_load_raw().get("exercicios") or []),
        "total": len(rows),
        "statuses": STATUS_LABELS,
        "periodos": [_enrich(p) for p in rows],
    }


def _enrich(p):
    out = dict(p)
    out["status_label"] = STATUS_LABELS.get(out.get("status"), out.get("status") or "")
    out["permite_postagem"] = out.get("status") in ("open", "closing")
    return out


def get_periodo(codigo_or_date):
    """Busca por código YYYY-MM ou por data YYYY-MM-DD."""
    key = str(codigo_or_date or "").strip()
    if not key:
        return None
    if len(key) >= 10 and key[4] == "-":
        # date
        try:
            d = date.fromisoformat(key[:10])
            key = f"{d.year}-{d.month:02d}"
        except ValueError:
            pass
    for p in _ensure_data().get("periodos") or []:
        if str(p.get("codigo")) == key:
            return _enrich(p)
    return None


def set_status(codigo, status, actor=None):
    data = _ensure_data()
    key = str(codigo or "").strip()
    st = str(status or "").strip().lower()
    if st not in STATUSES:
        raise ValueError("status deve ser open|closing|closed|locked")
    for i, p in enumerate(data.get("periodos") or []):
        if str(p.get("codigo")) != key:
            continue
        current = p.get("status")
        # locked is terminal unless reopening via open (admin break-glass)
        if current == "locked" and st != "open":
            raise ValueError("período bloqueado: só pode reabrir (open)")
        if current == "closed" and st == "closing":
            raise ValueError("não é possível voltar de closed para closing")
        p = dict(p)
        p["status"] = st
        p["atualizado_em"] = _now()
        p["alterado_por"] = str(actor or "").strip() or None
        data["periodos"][i] = p
        _save(data)
        return _enrich(p)
    raise ValueError(f"período não encontrado: {key}")


def allows_posting(data_lanc):
    """
    Retorna (ok, mensagem_erro|None, periodo|None).
    open/closing → ok; closed/locked → bloqueia; sem cadastro → bloqueia.
    """
    raw = str(data_lanc or "").strip()
    if not raw:
        return False, "data contábil obrigatória", None
    try:
        d = date.fromisoformat(raw[:10])
    except ValueError:
        return False, "data contábil inválida", None

    # auto-ensure year exists (meses novos abertos)
    data = _ensure_data()
    if d.year not in (data.get("exercicios") or []):
        ensure_year(d.year, status="open")

    periodo = get_periodo(d.isoformat())
    if not periodo:
        return False, f"período {d.year}-{d.month:02d} não cadastrado", None
    st = periodo.get("status")
    if st in ("open", "closing"):
        return True, None, periodo
    label = STATUS_LABELS.get(st, st)
    return False, f"período {periodo.get('codigo')} está {label} — postagem bloqueada", periodo


def meta():
    data = _ensure_data()
    open_n = sum(1 for p in data.get("periodos") or [] if p.get("status") == "open")
    return {
        "exercicios": data.get("exercicios") or [],
        "total_periodos": len(data.get("periodos") or []),
        "abertos": open_n,
        "fonte": "dados/periodos.json",
    }
