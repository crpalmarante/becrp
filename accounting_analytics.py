"""
Accounting Analytics Engine (RFC-8009 MVP).

Consome ledger/postados + integração. Não altera contabilidade.
"""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

import accounting_integration
import accounting_reports
import journal_entries
import ledger

MONEY = Decimal("0.01")


def _money(val):
    return Decimal(str(val if val is not None else "0")).quantize(
        MONEY, rounding=ROUND_HALF_UP
    )


def _parse_date(raw, default=None):
    s = str(raw or "").strip()[:10]
    if not s:
        return default
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise ValueError(f"data inválida: {raw}") from None


def _month_bounds(year, month):
    last = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def _posted_rows(data_de=None, data_ate=None):
    de = data_de.isoformat() if isinstance(data_de, date) else (str(data_de or "")[:10] or None)
    ate = data_ate.isoformat() if isinstance(data_ate, date) else (str(data_ate or "")[:10] or None)
    rows = []
    for r in journal_entries._load_raw().get("lancamentos") or []:
        if str(r.get("status") or "") != "posted":
            continue
        data = str(r.get("data") or "")[:10]
        if de and data < de:
            continue
        if ate and data > ate:
            continue
        rows.append(r)
    return rows


def _kpis(data_de=None, data_ate=None):
    de_s = data_de.isoformat() if isinstance(data_de, date) else data_de
    ate_s = data_ate.isoformat() if isinstance(data_ate, date) else data_ate
    dre = accounting_reports.income_statement(data_de=de_s, data_ate=ate_s)
    bp = accounting_reports.balance_sheet(data_ate=ate_s)
    rows = _posted_rows(data_de, data_ate)
    tot_d = sum((_money(r.get("total_debito")) for r in rows), Decimal("0"))
    return {
        "receitas": dre["totais"]["receitas"],
        "despesas": dre["totais"]["despesas"],
        "resultado": dre["totais"]["resultado"],
        "natureza_resultado": dre["totais"]["natureza"],
        "ativo": bp["totais"]["ativo"],
        "passivo_pl_resultado": bp["totais"]["passivo_pl_resultado"],
        "bp_balanceado": bp["totais"]["balanceado"],
        "lancamentos": len(rows),
        "volume_debito": float(tot_d),
        "ticket_medio": float(tot_d / len(rows)) if rows else 0.0,
    }


def _by_journal(rows):
    buckets = defaultdict(lambda: {"diario": "", "lancamentos": 0, "debito": Decimal("0"), "credito": Decimal("0")})
    for r in rows:
        d = str(r.get("diario") or "—")
        b = buckets[d]
        b["diario"] = d
        b["lancamentos"] += 1
        b["debito"] += _money(r.get("total_debito"))
        b["credito"] += _money(r.get("total_credito"))
    out = []
    for d, b in sorted(buckets.items(), key=lambda x: -float(x[1]["debito"])):
        out.append(
            {
                "diario": d,
                "lancamentos": b["lancamentos"],
                "debito": float(b["debito"]),
                "credito": float(b["credito"]),
            }
        )
    return out


def _top_accounts(rows, limit=10):
    acc = defaultdict(lambda: {"conta": "", "nome": "", "debito": Decimal("0"), "credito": Decimal("0")})
    for r in rows:
        for ln in r.get("linhas") or []:
            c = str(ln.get("conta") or "")
            if not c:
                continue
            b = acc[c]
            b["conta"] = c
            b["nome"] = ln.get("conta_nome") or b["nome"]
            b["debito"] += _money(ln.get("debito"))
            b["credito"] += _money(ln.get("credito"))
    ranked = []
    for c, b in acc.items():
        mov = b["debito"] + b["credito"]
        ranked.append(
            {
                "conta": c,
                "conta_nome": b["nome"],
                "debito": float(b["debito"]),
                "credito": float(b["credito"]),
                "movimento": float(mov),
            }
        )
    ranked.sort(key=lambda x: -x["movimento"])
    try:
        lim = max(1, min(int(limit or 10), 50))
    except (TypeError, ValueError):
        lim = 10
    return ranked[:lim]


def _trends(meses=6, ate=None):
    """Série mensal: receitas, despesas, resultado, volume."""
    try:
        n = max(1, min(int(meses or 6), 24))
    except (TypeError, ValueError):
        n = 6
    end = ate if isinstance(ate, date) else (ate and _parse_date(ate)) or date.today()
    # go back n-1 months
    y, m = end.year, end.month
    series = []
    for _ in range(n):
        ini, fim = _month_bounds(y, m)
        dre = accounting_reports.income_statement(
            data_de=ini.isoformat(), data_ate=fim.isoformat()
        )
        rows = _posted_rows(ini, fim)
        series.append(
            {
                "periodo": f"{y}-{m:02d}",
                "label": f"{m:02d}/{y}",
                "receitas": dre["totais"]["receitas"],
                "despesas": dre["totais"]["despesas"],
                "resultado": dre["totais"]["resultado"],
                "lancamentos": len(rows),
                "volume": float(sum((_money(r.get("total_debito")) for r in rows), Decimal("0"))),
            }
        )
        # previous month
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    series.reverse()
    return series


def _integration_pulse():
    log = accounting_integration.list_log(limit=50)
    eventos = log.get("eventos") or []
    ok = sum(1 for e in eventos if e.get("ok") and not e.get("skipped"))
    fail = sum(1 for e in eventos if not e.get("ok"))
    skip = sum(1 for e in eventos if e.get("skipped"))
    cfg = accounting_integration.get_config()
    return {
        "enabled": bool(cfg.get("enabled")),
        "domains": cfg.get("domains") or {},
        "amostra": len(eventos),
        "ok": ok,
        "falhas": fail,
        "skipped": skip,
        "taxa_sucesso": round(ok / max(1, ok + fail), 4) if (ok + fail) else None,
    }


def dashboard(data_de=None, data_ate=None, meses=6, top=10):
    """Painel analítico consolidado."""
    today = date.today()
    ate = _parse_date(data_ate, today)
    # default: mês corrente
    if data_de:
        de = _parse_date(data_de)
    else:
        de = date(ate.year, ate.month, 1)

    if de > ate:
        raise ValueError("data_de não pode ser maior que data_ate")

    rows = _posted_rows(de, ate)
    by_j = _by_journal(rows)
    tops = _top_accounts(rows, limit=top)
    trends = _trends(meses=meses, ate=ate)
    kpis = _kpis(de, ate)

    # margem simples
    rec = _money(kpis["receitas"])
    margem = float(( _money(kpis["resultado"]) / rec ).quantize(MONEY)) if rec > 0 else None

    return {
        "titulo": "Accounting Analytics",
        "filtros": {
            "data_de": de.isoformat(),
            "data_ate": ate.isoformat(),
            "meses_tendencia": int(meses or 6),
        },
        "kpis": {**kpis, "margem": margem},
        "por_diario": by_j,
        "top_contas": tops,
        "tendencia": trends,
        "integracao": _integration_pulse(),
        "meta": {
            **ledger.meta(),
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
        },
    }


def compare_periods(periodo_a=None, periodo_b=None):
    """
    Compara dois meses YYYY-MM (default: mês atual vs anterior).
    """
    today = date.today()
    a = str(periodo_a or f"{today.year}-{today.month:02d}").strip()
    try:
        ay, am = int(a[:4]), int(a[5:7])
    except (TypeError, ValueError) as e:
        raise ValueError("periodo_a inválido (YYYY-MM)") from e

    if periodo_b:
        b = str(periodo_b).strip()
        try:
            by, bm = int(b[:4]), int(b[5:7])
        except (TypeError, ValueError) as e:
            raise ValueError("periodo_b inválido (YYYY-MM)") from e
    else:
        bm = am - 1
        by = ay
        if bm == 0:
            bm = 12
            by -= 1

    def pack(y, m):
        ini, fim = _month_bounds(y, m)
        k = _kpis(ini, fim)
        return {
            "periodo": f"{y}-{m:02d}",
            "inicio": ini.isoformat(),
            "fim": fim.isoformat(),
            **k,
        }

    pa = pack(ay, am)
    pb = pack(by, bm)

    def delta(key):
        va = _money(pa.get(key))
        vb = _money(pb.get(key))
        diff = va - vb
        pct = float((diff / vb).quantize(Decimal("0.0001"))) if vb != 0 else None
        return {"a": float(va), "b": float(vb), "delta": float(diff), "pct": pct}

    return {
        "titulo": "Comparativo de períodos",
        "periodo_a": pa,
        "periodo_b": pb,
        "deltas": {
            "receitas": delta("receitas"),
            "despesas": delta("despesas"),
            "resultado": delta("resultado"),
            "volume_debito": delta("volume_debito"),
            "lancamentos": delta("lancamentos"),
        },
    }
