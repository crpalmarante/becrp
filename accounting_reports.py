"""
Relatórios contábeis (RFC-8007 MVP).

Somente dados postados (ledger). Não altera lançamentos.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

import journal_entries
import ledger
import planocontas

MONEY = Decimal("0.01")


def _money(val):
    return Decimal(str(val if val is not None else "0")).quantize(
        MONEY, rounding=ROUND_HALF_UP
    )


def _saldo_tuple(debito, credito):
    d = _money(debito)
    c = _money(credito)
    saldo = d - c
    if saldo >= 0:
        return {
            "debito": float(d),
            "credito": float(c),
            "saldo": float(saldo),
            "saldo_abs": float(saldo),
            "natureza": "D",
        }
    return {
        "debito": float(d),
        "credito": float(c),
        "saldo": float(saldo),
        "saldo_abs": float(-saldo),
        "natureza": "C",
    }


def _posted_in_range(data_de=None, data_ate=None, diario=None):
    de = str(data_de or "").strip()[:10] or None
    ate = str(data_ate or "").strip()[:10] or None
    dj = str(diario or "").strip().upper() or None
    rows = []
    for r in journal_entries._load_raw().get("lancamentos") or []:
        if str(r.get("status") or "") != "posted":
            continue
        data = str(r.get("data") or "")[:10]
        if de and data < de:
            continue
        if ate and data > ate:
            continue
        if dj and str(r.get("diario") or "").upper() != dj:
            continue
        rows.append(r)
    rows.sort(key=lambda r: (str(r.get("data") or ""), str(r.get("numero") or "")))
    return rows


def _accumulate(rows, prefix=None):
    """Soma D/C por conta analítica a partir de lançamentos."""
    acc = {}
    for r in rows:
        for ln in r.get("linhas") or []:
            c = str(ln.get("conta") or "")
            if not c:
                continue
            if prefix and not (c == prefix or c.startswith(prefix + ".")):
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
            if not bucket["conta_nome"]:
                conta = planocontas.get_conta(c)
                if conta:
                    bucket["conta_nome"] = conta.get("nome") or ""
                    bucket["conta_codigo"] = conta.get("codigo") or bucket["conta_codigo"]
    return acc


def trial_balance(data_ate=None, q=None, limit=500):
    """Balancete de verificação (saldos acumulados até data_ate)."""
    out = ledger.saldos(data_ate=data_ate, q=q, so_movimentadas=True, limit=limit)
    return {
        "tipo": "balancete",
        "titulo": "Balancete de verificação",
        **out,
        "meta": ledger.meta(),
    }


def general_ledger(conta, data_de=None, data_ate=None, diario=None, limit=2000):
    """Razão analítico (reutiliza ledger)."""
    out = ledger.razao(
        conta=conta,
        data_de=data_de,
        data_ate=data_ate,
        diario=diario,
        limit=limit,
    )
    return {"tipo": "razao", "titulo": "Razão analítico", **out, "meta": ledger.meta()}


def journal_book(diario=None, data_de=None, data_ate=None, limit=300):
    """Livro diário: lançamentos postados no período."""
    rows = _posted_in_range(data_de=data_de, data_ate=data_ate, diario=diario)
    try:
        lim = max(1, min(int(limit or 300), 2000))
    except (TypeError, ValueError):
        lim = 300
    lancamentos = []
    tot_d = Decimal("0")
    tot_c = Decimal("0")
    for r in rows[:lim]:
        tot_d += _money(r.get("total_debito"))
        tot_c += _money(r.get("total_credito"))
        lancamentos.append(
            {
                "numero": r.get("numero"),
                "id": r.get("id"),
                "data": r.get("data"),
                "diario": r.get("diario"),
                "historico": r.get("historico"),
                "referencia": r.get("referencia") or "",
                "total_debito": float(_money(r.get("total_debito"))),
                "total_credito": float(_money(r.get("total_credito"))),
                "linhas": r.get("linhas") or [],
            }
        )
    return {
        "tipo": "diario",
        "titulo": "Livro diário",
        "filtros": {
            "diario": str(diario or "").strip().upper() or None,
            "data_de": str(data_de or "").strip()[:10] or None,
            "data_ate": str(data_ate or "").strip()[:10] or None,
        },
        "total_lancamentos": len(rows),
        "totais": _saldo_tuple(tot_d, tot_c),
        "lancamentos": lancamentos,
        "meta": ledger.meta(),
    }


def _group_section(acc, matcher, label):
    items = []
    tot_d = Decimal("0")
    tot_c = Decimal("0")
    for c, b in sorted(acc.items(), key=lambda x: x[0]):
        if not matcher(c):
            continue
        sal = _saldo_tuple(b["debito"], b["credito"])
        if sal["debito"] == 0 and sal["credito"] == 0:
            continue
        tot_d += _money(b["debito"])
        tot_c += _money(b["credito"])
        items.append(
            {
                "conta": c,
                "conta_codigo": b.get("conta_codigo") or "",
                "conta_nome": b.get("conta_nome") or "",
                **sal,
            }
        )
    return {
        "codigo": label,
        "itens": items,
        "totais": _saldo_tuple(tot_d, tot_c),
    }


def balance_sheet(data_ate=None):
    """
    Balanço patrimonial simplificado (ECD/referencial):
    1.* ativo · 2.01/2.02 passivo · 2.03 PL · resultado 3.* no PL.
    """
    # acumulado até data_ate
    rows = _posted_in_range(data_ate=data_ate)
    acc = _accumulate(rows)

    ativo = _group_section(acc, lambda c: c.startswith("1."), "ativo")
    passivo = _group_section(
        acc, lambda c: c.startswith("2.01.") or c.startswith("2.02."), "passivo"
    )
    pl = _group_section(acc, lambda c: c.startswith("2.03."), "patrimonio_liquido")

    # resultado do exercício (contas 3.*) — natureza crédito = lucro
    res_acc = {k: v for k, v in acc.items() if k.startswith("3.")}
    res_d = sum((_money(v["debito"]) for v in res_acc.values()), Decimal("0"))
    res_c = sum((_money(v["credito"]) for v in res_acc.values()), Decimal("0"))
    # lucro = C - D (saldo credor do resultado)
    resultado_liquido = float(res_c - res_d)

    ativo_saldo = _money(ativo["totais"]["saldo"])  # D-C, esperado D
    passivo_saldo_c = _money(passivo["totais"]["credito"]) - _money(passivo["totais"]["debito"])
    pl_saldo_c = _money(pl["totais"]["credito"]) - _money(pl["totais"]["debito"])
    # lado direito do BP = passivo + PL + resultado (em natureza credora)
    passivo_pl = float(passivo_saldo_c + pl_saldo_c + Decimal(str(resultado_liquido)))
    ativo_total = float(ativo_saldo)

    return {
        "tipo": "balanco",
        "titulo": "Balanço patrimonial",
        "data_ate": str(data_ate or "").strip()[:10] or None,
        "ativo": ativo,
        "passivo": passivo,
        "patrimonio_liquido": pl,
        "resultado_exercicio": {
            "valor": resultado_liquido,
            "natureza": "C" if resultado_liquido >= 0 else "D",
            "label": "Resultado do exercício (lucro)" if resultado_liquido >= 0 else "Resultado do exercício (prejuízo)",
        },
        "totais": {
            "ativo": ativo_total,
            "passivo_pl_resultado": passivo_pl,
            "diferenca": round(ativo_total - passivo_pl, 2),
            "balanceado": abs(ativo_total - passivo_pl) < 0.02,
        },
        "meta": ledger.meta(),
    }


def income_statement(data_de=None, data_ate=None):
    """DRE simplificada: movimentos da classe 3 no período."""
    rows = _posted_in_range(data_de=data_de, data_ate=data_ate)
    acc = _accumulate(rows, prefix="3")

    receitas = []
    despesas = []
    tot_rec = Decimal("0")
    tot_desp = Decimal("0")

    for c, b in sorted(acc.items(), key=lambda x: x[0]):
        sal = _saldo_tuple(b["debito"], b["credito"])
        if sal["debito"] == 0 and sal["credito"] == 0:
            continue
        # crédito líquido → receita; débito líquido → despesa/custo
        liquido = _money(b["credito"]) - _money(b["debito"])
        item = {
            "conta": c,
            "conta_codigo": b.get("conta_codigo") or "",
            "conta_nome": b.get("conta_nome") or "",
            **sal,
            "liquido": float(liquido),
        }
        if liquido >= 0:
            receitas.append(item)
            tot_rec += liquido
        else:
            despesas.append(item)
            tot_desp += -liquido

    resultado = tot_rec - tot_desp
    return {
        "tipo": "dre",
        "titulo": "Demonstração do resultado (simplificada)",
        "filtros": {
            "data_de": str(data_de or "").strip()[:10] or None,
            "data_ate": str(data_ate or "").strip()[:10] or None,
        },
        "receitas": receitas,
        "despesas": despesas,
        "totais": {
            "receitas": float(tot_rec),
            "despesas": float(tot_desp),
            "resultado": float(resultado),
            "natureza": "lucro" if resultado >= 0 else "prejuizo",
        },
        "meta": ledger.meta(),
    }
