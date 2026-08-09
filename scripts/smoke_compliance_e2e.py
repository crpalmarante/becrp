#!/usr/bin/env python3
"""Smoke E2E do Compliance Engine (RFC-0060, Sprint CP-01).

Valida o contrato de fechamento: apuração (Tax) × provisionado (Accounting)
× caixa (Finance). Faz backup/restauração dos dados para não sujar o repo.
"""

from __future__ import annotations

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import accounting_integration as integ
import accounting_periods as periods
import compliance_engine as ce
import journal_entries as je

FILES = (
    "dados/lancamentos.json",
    "dados/posting_history.json",
    "dados/accounting_integration_log.json",
    "dados/vendas.json",
    "dados/nfe_entrada.json",
    "dados/compliance_fechamentos.json",
    "dados/diarios.json",
)

BACKUP = "/tmp/opencode/cp01_backup"
EMPTY = {
    "dados/lancamentos.json": {"atualizado_em": None, "lancamentos": [], "total": 0},
    "dados/posting_history.json": {"atualizado_em": None, "eventos": []},
    "dados/accounting_integration_log.json": {"atualizado_em": None, "eventos": []},
    "dados/vendas.json": {"vendas": [], "total_vendas": 0},
    "dados/compliance_fechamentos.json": {"atualizado_em": None, "fechamentos": []},
}


def _backup():
    os.makedirs(BACKUP, exist_ok=True)
    for path in FILES:
        src = os.path.join(ROOT, path)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(BACKUP, os.path.basename(path)))


def _restore():
    for path in FILES:
        dst = os.path.join(ROOT, path)
        bkp = os.path.join(BACKUP, os.path.basename(path))
        if os.path.exists(bkp):
            shutil.copy2(bkp, dst)


def _reset():
    for path, payload in EMPTY.items():
        with open(os.path.join(ROOT, path), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(os.path.join(ROOT, "dados/diarios.json"), "r", encoding="utf-8") as f:
        d = json.load(f)
    for x in d.get("diarios") or []:
        x["usos"] = 0
        x["proximo"] = 1
    with open(os.path.join(ROOT, "dados/diarios.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def _salvar_venda(venda):
    with open(os.path.join(ROOT, "dados/vendas.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    lista = data.get("vendas") or []
    venda["id"] = (max([int(v.get("id") or 0) for v in lista] or [0]) + 1)
    lista.append(venda)
    data["vendas"] = lista
    data["total_vendas"] = len(lista)
    with open(os.path.join(ROOT, "dados/vendas.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return venda


def main():
    _backup()
    try:
        _reset()
        periods.ensure_year(2026)
        periods.set_status("2026-07", "open")

        # 1) vendas reais (salvas em vendas.json) → on_pos_sale posta contabilmente
        for v, fp in (
            (
                {"total": 100.0, "data": "2026-07-10", "estabelecimento_id": "1",
                 "itens": [{"qtd": 1, "subtotal": 100.0, "custo": 60.0}]},
                "Dinheiro",
            ),
            (
                {"total": 200.0, "data": "2026-07-11", "estabelecimento_id": "1",
                 "itens": [{"qtd": 2, "subtotal": 200.0, "custo": 50.0}]},
                "PIX",
            ),
        ):
            venda = _salvar_venda(dict(v, forma_pg=fp))
            r = integ.on_pos_sale(venda, forma_pg=fp, actor="cp01")
            assert r["ok"] and not r["skipped"], r
            assert r.get("cmv") and r["cmv"]["ok"], r

        # 1b) recebimento com NF-e de entrada (ICMS/PIS/COFINS destacados)
        #     → compra posta + créditos de entrada (débito a recuperar)
        nfe_entrada = {
            "chave": "42260162832155000141550010000000021000000099",
            "numero": "99",
            "serie": "1",
            "data_emissao": "2026-07-12",
            "data_importacao": "2026-07-12 12:00:00",
            "receiving_id": "cp01-r1",
            "estabelecimento_id": "1",
            "fornecedor": {"cnpj": "11222333000181", "nome": "F", "ie": ""},
            "total": {"vNF": 200.0, "vICMS": 34.0, "vPIS": 3.0, "vCOFINS": 10.0},
            "itens": [{"n_item": "1", "codigo": "X", "nome": "Y", "ncm": "22021000", "cfop": "5102", "quantidade": "2", "vl_unitario": "100", "vl_total": "200"}],
        }
        import json as _json
        nfe_path = "dados/nfe_entrada.json"
        nfe_data = _json.load(open(nfe_path, encoding="utf-8"))
        nfe_data["nfe_entradas"].append(nfe_entrada)
        with open(nfe_path, "w", encoding="utf-8") as f:
            _json.dump(nfe_data, f, ensure_ascii=False, indent=2)
        r_rcv = integ.on_receiving_complete(
            {
                "id": "cp01-r1",
                "completed_at": "2026-07-12T12:00:00",
                "items": [{"qty_verified": 2, "preco_unit": 100.0}],
                "nfe": {
                    "total": {"vNF": 200.0, "vICMS": 34.0, "vPIS": 3.0, "vCOFINS": 10.0},
                },
            },
            actor="cp01",
        )
        assert r_rcv["ok"] and not r_rcv["skipped"], r_rcv
        # compra é rascunho por padrão → postar para o fechamento contábil ver
        import posting_engine as pe
        lanc = je.get_lancamento(r_rcv["lancamento_id"])
        assert lanc["status"] == "draft", lanc["status"]
        if lanc["status"] == "draft":
            pe.post(r_rcv["lancamento_id"], actor="cp01")
        # compra com créditos: débito em tributos a recuperar registrado
        lanc = je.get_lancamento(r_rcv["lancamento_id"])
        contas_rec = {ln["conta"] for ln in lanc["linhas"]}
        assert "1.01.02.03.02" in contas_rec, contas_rec  # ICMS a recuperar

        # 2) fechamento do período → deve ser VALIDO (EFD == ECD == Caixa)
        rel = ce.fechamento(2026, 7)
        assert rel["status"] == "valido", [c for c in rel["checagens"] if not c["ok"]]
        assert rel["evento"] == "fechamento_valido", rel["evento"]
        assert rel["total_divergencias"] == 0, rel["divergencias"]
        print("fechamento valido:", rel["periodo"]["label"],
              "| saldo icms", rel["apurado_fiscal"]["saldo_a_recolher"]["icms"])

        # apuração casa com provisionamento (incluindo créditos de entrada)
        ap = rel["apurado_fiscal"]
        pr = rel["provisionado_contabil"]
        assert ap["creditos"]["icms"] > 0, ap["creditos"]  # crédito da compra entrou
        for nome in ("icms", "pis", "cofins"):
            assert abs(ap["saldo_a_recolher"][nome] - pr["saldo_a_recolher"][nome]) < 0.02, (
                nome, ap["saldo_a_recolher"], pr["saldo_a_recolher"],
            )
        assert abs(rel["caixa_finance"] - ap["base"]) < 0.02, rel["caixa_finance"]

        # 3) quebra proposital: apaga o lançamento de uma venda → DIVERGENTE
        lancamentos = je._load_raw()
        alvo = lancamentos["lancamentos"][0]["id"]
        lancamentos["lancamentos"] = [l for l in lancamentos["lancamentos"] if l["id"] != alvo]
        with open(os.path.join(ROOT, "dados/lancamentos.json"), "w", encoding="utf-8") as f:
            json.dump(lancamentos, f, indent=2, ensure_ascii=False)

        rel2 = ce.fechamento(2026, 7)
        assert rel2["status"] == "divergente", rel2["status"]
        assert rel2["evento"] == "fechamento_divergente", rel2["evento"]
        assert rel2["total_divergencias"] > 0, rel2["divergencias"]
        print("fechamento divergente detectado:", rel2["total_divergencias"], "divergencia(s)")

        # 4) histórico de fechamentos registra ambos eventos
        hist = ce.list_fechamentos().get("fechamentos") or []
        eventos = [h["evento"] for h in hist]
        assert "fechamento_valido" in eventos and "fechamento_divergente" in eventos, eventos

        print("SMOKE COMPLIANCE CP-01 OK")
        print("  eventos:", eventos)
        print("reset ok")
    finally:
        _restore()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
