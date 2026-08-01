"""
Razão / saldos contábeis (RFC-8005 MVP).

Fonte oficial: lançamentos com status=posted (imutáveis).
Estornos entram como novos lançamentos postados; originais cancelled ficam fora do razão.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

import journal_entries
import planocontas

MONEY = Decimal("0.01")


def _money(val):
    return Decimal(str(val if val is not None else "0")).quantize(
        MONEY, rounding=ROUND_HALF_UP
    )


def _posted_rows():
    rows = []
    for r in journal_entries._load_raw().get("lancamentos") or []:
        if str(r.get("status") or "") != "posted":
            continue
        rows.append(r)
    rows.sort(
        key=lambda r: (
            str(r.get("data") or ""),
            str(r.get("posted_em") or ""),
            str(r.get("numero") or ""),
        )
    )
    return rows


def _iter_lines(data_de=None, data_ate=None, conta=None, diario=None):
    """Yield ledger lines from posted entries (filtered)."""
    de = str(data_de or "").strip()[:10] or None
    ate = str(data_ate or "").strip()[:10] or None
    conta_key = str(conta or "").strip()
    conta_obj = planocontas.get_conta(conta_key) if conta_key else None
    conta_classif = (
        str(conta_obj.get("classificacao") or conta_obj.get("codigo") or "")
        if conta_obj
        else conta_key
    )
    diario_key = str(diario or "").strip().upper() or None

    for r in _posted_rows():
        data = str(r.get("data") or "")[:10]
        if de and data < de:
            continue
        if ate and data > ate:
            continue
        if diario_key and str(r.get("diario") or "").upper() != diario_key:
            continue
        for ln in r.get("linhas") or []:
            c = str(ln.get("conta") or "")
            if conta_classif and c != conta_classif and c != conta_key:
                # also match by codigo stored
                if str(ln.get("conta_codigo") or "") != conta_key:
                    continue
            yield {
                "data": data,
                "posted_em": r.get("posted_em"),
                "numero": r.get("numero"),
                "lancamento_id": r.get("id"),
                "diario": r.get("diario"),
                "referencia": r.get("referencia") or "",
                "historico": ln.get("historico") or r.get("historico") or "",
                "conta": c,
                "conta_codigo": ln.get("conta_codigo") or "",
                "conta_nome": ln.get("conta_nome") or "",
                "debito": float(_money(ln.get("debito"))),
                "credito": float(_money(ln.get("credito"))),
                "origem": r.get("origem") or "",
                "origem_ref": r.get("origem_ref") or "",
            }


def _saldo_tuple(debito, credito):
    d = _money(debito)
    c = _money(credito)
    saldo = d - c
    if saldo >= 0:
        natureza = "D"
        saldo_abs = saldo
    else:
        natureza = "C"
        saldo_abs = -saldo
    return {
        "debito": float(d),
        "credito": float(c),
        "saldo": float(saldo),
        "saldo_abs": float(saldo_abs),
        "natureza": natureza,
    }


def razao(conta, data_de=None, data_ate=None, diario=None, limit=2000):
    """Razão analítico de uma conta com saldo acumulado."""
    conta_key = str(conta or "").strip()
    if not conta_key:
        raise ValueError("conta obrigatória")
    conta_obj = planocontas.get_conta(conta_key)
    if not conta_obj:
        raise ValueError(f"conta não encontrada: {conta_key}")
    classif = str(conta_obj.get("classificacao") or conta_obj.get("codigo"))

    de = str(data_de or "").strip()[:10] or None
    # saldo inicial = movimentos postados antes de data_de
    abertura_d = Decimal("0")
    abertura_c = Decimal("0")
    if de:
        for r in _posted_rows():
            data = str(r.get("data") or "")[:10]
            if data >= de:
                continue
            if diario and str(r.get("diario") or "").upper() != str(diario).strip().upper():
                continue
            for ln in r.get("linhas") or []:
                c = str(ln.get("conta") or "")
                if c != classif and str(ln.get("conta_codigo") or "") != conta_key:
                    continue
                abertura_d += _money(ln.get("debito"))
                abertura_c += _money(ln.get("credito"))

    abertura = _saldo_tuple(abertura_d, abertura_c)
    running = abertura_d - abertura_c
    movimentos = []
    for ln in _iter_lines(data_de=de, data_ate=data_ate, conta=classif, diario=diario):
        running += _money(ln["debito"]) - _money(ln["credito"])
        nat = "D" if running >= 0 else "C"
        movimentos.append(
            {
                **ln,
                "saldo": float(running),
                "saldo_abs": float(abs(running)),
                "natureza": nat,
            }
        )

    try:
        lim = max(1, min(int(limit or 2000), 10000))
    except (TypeError, ValueError):
        lim = 2000

    periodo_d = sum((_money(m["debito"]) for m in movimentos), Decimal("0"))
    periodo_c = sum((_money(m["credito"]) for m in movimentos), Decimal("0"))
    final = _saldo_tuple(abertura_d + periodo_d, abertura_c + periodo_c)

    return {
        "conta": {
            "codigo": conta_obj.get("codigo"),
            "classificacao": classif,
            "nome": conta_obj.get("nome") or conta_obj.get("descricao") or "",
            "tipo": conta_obj.get("tipo"),
        },
        "filtros": {
            "data_de": de,
            "data_ate": str(data_ate or "").strip()[:10] or None,
            "diario": str(diario or "").strip().upper() or None,
        },
        "abertura": abertura,
        "periodo": _saldo_tuple(periodo_d, periodo_c),
        "final": final,
        "total_movimentos": len(movimentos),
        "movimentos": movimentos[:lim],
    }


def saldos(data_ate=None, q=None, so_movimentadas=True, limit=500):
    """Balancete simples: saldos por conta até data_ate (só postados)."""
    ate = str(data_ate or "").strip()[:10] or None
    qq = str(q or "").strip().lower()

    acc = {}  # classif -> totals
    for r in _posted_rows():
        data = str(r.get("data") or "")[:10]
        if ate and data > ate:
            continue
        for ln in r.get("linhas") or []:
            c = str(ln.get("conta") or "")
            if not c:
                continue
            bucket = acc.setdefault(
                c,
                {
                    "conta": c,
                    "conta_codigo": ln.get("conta_codigo") or "",
                    "conta_nome": ln.get("conta_nome") or "",
                    "debito": Decimal("0"),
                    "credito": Decimal("0"),
                },
            )
            bucket["debito"] += _money(ln.get("debito"))
            bucket["credito"] += _money(ln.get("credito"))
            if not bucket["conta_nome"] and ln.get("conta_nome"):
                bucket["conta_nome"] = ln.get("conta_nome")

    rows = []
    for c, b in acc.items():
        conta = planocontas.get_conta(c)
        nome = (conta or {}).get("nome") or b.get("conta_nome") or ""
        codigo = (conta or {}).get("codigo") or b.get("conta_codigo") or ""
        classif = (conta or {}).get("classificacao") or c
        if qq:
            blob = f"{classif} {codigo} {nome}".lower()
            if qq not in blob:
                continue
        sal = _saldo_tuple(b["debito"], b["credito"])
        if so_movimentadas and sal["debito"] == 0 and sal["credito"] == 0:
            continue
        rows.append(
            {
                "conta": classif,
                "conta_codigo": str(codigo),
                "conta_nome": nome,
                **sal,
            }
        )

    rows.sort(key=lambda r: str(r.get("conta") or ""))
    try:
        lim = max(1, min(int(limit or 500), 5000))
    except (TypeError, ValueError):
        lim = 500

    tot_d = sum((_money(r["debito"]) for r in rows), Decimal("0"))
    tot_c = sum((_money(r["credito"]) for r in rows), Decimal("0"))
    return {
        "data_ate": ate,
        "total_contas": len(rows),
        "totais": _saldo_tuple(tot_d, tot_c),
        "saldos": rows[:lim],
    }


def meta():
    posted = _posted_rows()
    return {
        "lancamentos_postados": len(posted),
        "fonte": "dados/lancamentos.json (status=posted)",
    }
