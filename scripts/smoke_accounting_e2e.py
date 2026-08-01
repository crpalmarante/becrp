#!/usr/bin/env python3
"""Smoke E2E da trilha contábil (endurecimento) — sem SEFAZ."""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import accounting_analytics as analytics
import accounting_integration as integ
import accounting_periods as periods
import accounting_reports as reports
import journal_entries as je
import ledger
import posting_engine as pe


def _reset():
    for path, payload in (
        ("dados/lancamentos.json", {"atualizado_em": None, "lancamentos": [], "total": 0}),
        ("dados/posting_history.json", {"atualizado_em": None, "eventos": []}),
        ("dados/accounting_integration_log.json", {"atualizado_em": None, "eventos": []}),
    ):
        with open(os.path.join(ROOT, path), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(os.path.join(ROOT, "dados/diarios.json"), "r", encoding="utf-8") as f:
        d = json.load(f)
    for x in d.get("diarios") or []:
        x["usos"] = 0
        x["proximo"] = 1
    with open(os.path.join(ROOT, "dados/diarios.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    integ.update_config(
        {
            "enabled": True,
            "domains": {"pos_sale": True, "receiving": True, "inventory_adjust": False},
        }
    )


def main():
    _reset()
    periods.ensure_year(2026)
    periods.set_status("2026-07", "open")

    # 1) Venda dinheiro
    r_cash = integ.on_pos_sale(
        {"id": 1, "total": 100.0, "forma_pg": "Dinheiro", "data": "2026-07-20"},
        forma_pg="Dinheiro",
        actor="smoke",
    )
    assert r_cash["ok"] and not r_cash["skipped"], r_cash
    assert r_cash.get("numero", "").startswith("VEN-"), r_cash
    assert "message" in r_cash

    # 2) Venda PIX
    r_pix = integ.on_pos_sale(
        {"id": 2, "total": 45.5, "forma_pg": "PIX", "data": "2026-07-20"},
        forma_pg="PIX",
        actor="smoke",
    )
    assert r_pix["ok"] and not r_pix["skipped"], r_pix
    # banco/PIX → SALE_BANK
    lanc_pix = je.get_lancamento(r_pix["lancamento_id"])
    assert any(ln.get("conta", "").startswith("1.01.01.02") for ln in lanc_pix["linhas"]), lanc_pix

    # 3) Razão / DRE / analytics
    rz = ledger.razao("1.01.01.01.01", data_de="2026-07-01", data_ate="2026-07-31")
    assert rz["final"]["saldo"] >= 100, rz["final"]
    dre = reports.income_statement("2026-07-01", "2026-07-31")
    assert dre["totais"]["receitas"] >= 145.5, dre["totais"]
    dash = analytics.dashboard(data_de="2026-07-01", data_ate="2026-07-31", meses=3)
    assert dash["kpis"]["lancamentos"] >= 2

    # 4) Receiving com preco_unit → rascunho compra
    r_rcv = integ.on_receiving_complete(
        {
            "id": "e2e-1",
            "completed_at": "2026-07-20T12:00:00",
            "items": [{"qty_verified": 3, "preco_unit": 10.0}],
        },
        actor="smoke",
    )
    assert r_rcv["ok"] and not r_rcv["skipped"], r_rcv
    assert abs(r_rcv["valor"] - 30.0) < 0.01, r_rcv
    draft = je.get_lancamento(r_rcv["lancamento_id"])
    assert draft["status"] == "draft"
    posted = pe.post(draft["id"], actor="smoke")
    assert posted["status"] == "posted"

    # 5) Período fechado bloqueia post
    periods.set_status("2026-07", "closed")
    r_block = integ.on_pos_sale(
        {"id": 3, "total": 10.0, "data": "2026-07-21"},
        forma_pg="Dinheiro",
        actor="smoke",
    )
    assert not r_block["ok"], r_block
    assert "período" in (r_block.get("error") or "").lower() or "fechado" in (
        r_block.get("error") or ""
    ).lower(), r_block
    periods.set_status("2026-07", "open")

    # 6) Idempotência
    again = integ.on_pos_sale(
        {"id": 1, "total": 100.0, "data": "2026-07-20"},
        forma_pg="Dinheiro",
        actor="smoke",
    )
    assert again.get("skipped") and again.get("reason") == "já integrado"

    print("SMOKE E2E OK")
    print("  cash", r_cash["numero"], "| pix", r_pix["numero"], "| rcv", r_rcv["numero"])
    print("  dre receitas", dre["totais"]["receitas"], "| kpis", dash["kpis"]["resultado"])

    _reset()
    periods.set_status("2026-07", "open")
    print("reset ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
