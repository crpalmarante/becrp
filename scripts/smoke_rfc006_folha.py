#!/usr/bin/env python3
"""Smoke E2E do RFC-006 — Processamento da Folha (INSS/IRRF reais).

Cobre (motor COBOL via cobol_bridge):
  - folha_config_seed: regrava dados/folha_config.dat no layout novo com a
    tabela 2026 (deduções IRRF + 5ª faixa) — idempotente
  - folha_abrir: competência única (RFC-006 §2, decisão 2); duplicada bloqueada
  - folha_calcular: INSS progressivo por faixa (RFC-005 §2) e IRRF com
    dedução de faixa e dependentes (RFC-005 §3) — conferidos com referência
    Python; base IRRF = base INSS - INSS - dep×ded_dep; líquido = prov − desc
  - transições de estado (RFC-006 §2/§4): abrir → concluir (calculada) →
    validar → fechar → pagar; guards: pagar sem fechar, fechar sem validar,
    recalcular depois de paga, abrir duplicada
  - folha_listar/folha_mostrar: totais por competência e detalhe por
    funcionário (bases INSS/IRRF, situação, data de pagamento)

Faz backup/restauração de dados/folhas.dat, folhas.tmp e folha_config.dat.
"""

from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge

FILES = ("dados/folhas.dat", "dados/folhas.tmp", "dados/folha_config.dat")
BACKUP = "/tmp/becrp_rfc006_backup"

PASS = 0
FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} {extra}")


def quase(a, b, tol=0.01):
    return abs(float(a) - float(b)) <= tol


def _backup():
    os.makedirs(BACKUP, exist_ok=True)
    for path in FILES:
        src = os.path.join(ROOT, path)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(BACKUP, os.path.basename(path)))
        else:
            marker = os.path.join(BACKUP, os.path.basename(path) + ".nao-existia")
            open(marker, "w").close()


def _restore():
    for path in FILES:
        dst = os.path.join(ROOT, path)
        bak = os.path.join(BACKUP, os.path.basename(path))
        marker = bak + ".nao-existia"
        if os.path.exists(bak):
            shutil.copy2(bak, dst)
        elif os.path.exists(marker):
            if os.path.exists(dst):
                os.remove(dst)
    shutil.rmtree(BACKUP, ignore_errors=True)


def inss_progressivo(base, cfg):
    """Referência Python do INSS progressivo por faixa (RFC-005 §2)."""
    tetos = [cfg["inss_f1_teto"], cfg["inss_f2_teto"],
             cfg["inss_f3_teto"], cfg["inss_f4_teto"]]
    aliqs = [cfg["inss_f1_aliq"], cfg["inss_f2_aliq"],
             cfg["inss_f3_aliq"], cfg["inss_f4_aliq"]]
    total = 0.0
    anterior = 0.0
    for teto, aliq in zip(tetos, aliqs):
        limite = min(base, teto) - anterior
        if limite > 0:
            total += limite * aliq / 100
        if base <= teto:
            break
        anterior = teto
    return round(total, 2)


def irrf_calcular(base_irrf, cfg):
    """Referência Python do IRRF (RFC-005 §3): alíquota da faixa − dedução."""
    if base_irrf <= cfg["irrf_f1_teto"]:
        return 0.0
    faixas = [
        (cfg["irrf_f2_teto"], cfg["irrf_f2_aliq"], cfg["irrf_f2_ded"]),
        (cfg["irrf_f3_teto"], cfg["irrf_f3_aliq"], cfg["irrf_f3_ded"]),
        (cfg["irrf_f4_teto"], cfg["irrf_f4_aliq"], cfg["irrf_f4_ded"]),
        (float("inf"), cfg["irrf_f5_aliq"], cfg["irrf_f5_ded"]),
    ]
    for teto, aliq, ded in faixas:
        if base_irrf <= teto:
            v = round(base_irrf * aliq / 100 - ded, 2)
            return max(v, 0.0)
    return 0.0


def main():
    _backup()
    try:
        # estado limpo: remove o .dat do processamento antes do 1º abrir
        for path in FILES:
            if path.endswith("folhas.dat") and os.path.exists(os.path.join(ROOT, path)):
                os.remove(os.path.join(ROOT, path))
        print("1. Config (RFC-005) — seed idempotente no layout novo")
        cobol_bridge.folha_config_seed()
        cfg = cobol_bridge.folha_config_ler()
        check("config tem deduções IRRF", cfg.get("irrf_f2_ded") == 169.44, cfg.get("irrf_f2_ded"))
        check("config tem 5ª faixa (27,5%)", cfg.get("irrf_f5_aliq") == 27.5, cfg.get("irrf_f5_aliq"))
        check("config f1 IRRF 2026 = 2259,20", cfg.get("irrf_f1_teto") == 2259.20, cfg.get("irrf_f1_teto"))
        check("seed idempotente (2ª chamada não regrava)", cobol_bridge.folha_config_seed() is False)

        print("\n2. Abrir competência (RFC-006 §3.1)")
        comp = "2026/08"
        check("abrir → OK", cobol_bridge.folha_abrir(comp))
        try:
            cobol_bridge.folha_abrir(comp)
            check("abrir duplicada → bloqueado", False)
        except Exception as ex:
            check("abrir duplicada → bloqueado", "ja existe" in str(ex), str(ex))

        print("\n3. Calcular funcionários (INSS/IRRF de verdade)")
        r1 = cobol_bridge.folha_calcular({
            "competencia": comp, "funcionario_id": 1, "nome": "Joao Silva",
            "salario_base": 3000.00, "horas_extras": 0, "dsr": 0,
            "faltas": 0, "dependentes": 0, "outros_proventos": 0,
            "outros_descontos": 0,
        })
        check("func 1: proventos = salário", quase(r1["proventos"], 3000.00), r1)
        inss1 = inss_progressivo(3000.00, cfg)
        check("func 1: INSS progressivo", quase(r1["inss"], inss1), f"{r1['inss']} vs {inss1}")
        base_irrf1 = round(3000.00 - r1["inss"], 2)
        check("func 1: base IRRF = base INSS − INSS", quase(r1["base_irrf"], base_irrf1), r1)
        irrf1 = irrf_calcular(base_irrf1, cfg)
        check("func 1: IRRF (faixa − dedução)", quase(r1["irrf"], irrf1), f"{r1['irrf']} vs {irrf1}")
        check("func 1: líquido = prov − desc", quase(r1["liquido"],
              3000.00 - r1["total_descontos"]), r1)

        r2 = cobol_bridge.folha_calcular({
            "competencia": comp, "funcionario_id": 2, "nome": "Maria Souza",
            "salario_base": 5000.00, "horas_extras": 0, "dsr": 0,
            "faltas": 0, "dependentes": 2, "outros_proventos": 0,
            "outros_descontos": 0,
        })
        inss2 = inss_progressivo(5000.00, cfg)
        check("func 2: INSS progressivo (faixa 3/4)", quase(r2["inss"], inss2), f"{r2['inss']} vs {inss2}")
        base_irrf2 = round(5000.00 - r2["inss"] - 2 * cfg["irrf_ded_dep"], 2)
        check("func 2: base IRRF desconta dependentes",
              quase(r2["base_irrf"], base_irrf2), f"{r2['base_irrf']} vs {base_irrf2}")
        irrf2 = irrf_calcular(base_irrf2, cfg)
        check("func 2: IRRF com dependentes", quase(r2["irrf"], irrf2), f"{r2['irrf']} vs {irrf2}")

        # função na faixa 5 (acima de 4664,68)
        r3 = cobol_bridge.folha_calcular({
            "competencia": comp, "funcionario_id": 3, "nome": "Carlos Lima",
            "salario_base": 12000.00, "horas_extras": 0, "dsr": 0,
            "faltas": 0, "dependentes": 0, "outros_proventos": 0,
            "outros_descontos": 0,
        })
        inss3 = inss_progressivo(12000.00, cfg)
        check("func 3: INSS no teto", quase(r3["inss"], inss3), f"{r3['inss']} vs {inss3}")
        base_irrf3 = round(12000.00 - r3["inss"], 2)
        irrf3 = irrf_calcular(base_irrf3, cfg)
        check("func 3: IRRF 5ª faixa (27,5%)", quase(r3["irrf"], irrf3), f"{r3['irrf']} vs {irrf3}")

        print("\n4. Transições de estado (RFC-006 §2/§4.4)")
        check("concluir A→C", cobol_bridge.folha_concluir(comp))
        try:
            cobol_bridge.folha_validar(comp)  # já C→V
            check("validar C→V", True)
        except Exception as ex:
            check("validar C→V", False, str(ex))
        try:
            cobol_bridge.folha_pagar(comp, "2026-08-10")  # V ≠ F → deve falhar
            check("pagar sem fechar → bloqueado", False)
        except Exception as ex:
            check("pagar sem fechar → bloqueado", "fechada" in str(ex), str(ex))
        check("fechar V→F", cobol_bridge.folha_fechar(comp))
        check("pagar F→P", cobol_bridge.folha_pagar(comp, "2026-08-10"))
        try:
            cobol_bridge.folha_calcular({
                "competencia": comp, "funcionario_id": 1, "nome": "Joao",
                "salario_base": 9999.00, "horas_extras": 0, "dsr": 0,
                "faltas": 0, "dependentes": 0, "outros_proventos": 0,
                "outros_descontos": 0,
            })
            check("recalcular competência paga → bloqueado", False)
        except Exception as ex:
            check("recalcular competência paga → bloqueado", "recalculo" in str(ex), str(ex))

        print("\n5. Listar / Mostrar")
        comps = cobol_bridge.folha_listar()
        check("listar tem 2026/08", any(c["competencia"] == comp for c in comps), comps)
        c08 = next(c for c in comps if c["competencia"] == comp)
        check("situacao P (paga)", c08["situacao"] == "P", c08)
        check("3 funcionários na competência", c08["qtde_funcionarios"] == 3, c08)
        det = cobol_bridge.folha_mostrar(comp)
        funcs = det.get("funcionarios", [])
        check("mostrar: 3 funcionários", len(funcs) == 3, len(funcs))
        maria = next(f for f in funcs if f["funcionario_id"] == 2)
        check("mostrar: Maria com bases INSS/IRRF", maria["base_inss"] > 0 and maria["base_irrf"] > 0)
        check("mostrar: data de pagamento gravada",
              all(f["data_pagamento"] == "2026-08-10" for f in funcs),
              [f["data_pagamento"] for f in funcs])

        # conferência: total líquido = soma dos funcionários
        soma_liq = round(sum(f["liquido"] for f in funcs), 2)
        check("listar: total líquido = soma", quase(c08["liquido"], soma_liq),
              f"{c08['liquido']} vs {soma_liq}")

        print(f"\n{'='*50}\nResultado: {PASS} ok / {FAIL} falhas\n{'='*50}")
        sys.exit(0 if FAIL == 0 else 1)
    finally:
        _restore()


if __name__ == "__main__":
    main()
