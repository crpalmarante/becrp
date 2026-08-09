#!/usr/bin/env python3
"""Smoke E2E do RFC-007 — Holerite como visão do processamento.

Cobre (motor COBOL via cobol_bridge):
  - holerite_gerar: só a partir do processamento (folhas.dat); nada digitado
    (RFC-007 §1/§3.1); competência inexistente ou aberta bloqueada; regeneração
    substitui os holerites da competência (RFC-007 §3.4 — valores idênticos)
  - FGTS gravado no processamento (RFC-005 §4) e exibido no holerite
  - holerite_listar: campos do processamento (bases INSS/IRRF, proventos,
    descontos, líquido, situação, data de pagamento)
  - holerite_mostrar: bases de cálculo + componentes (proventos/descontos)
    rastreáveis ao processamento (RFC-007 §2.2–2.4); observações livres (§5.2)
  - holerite-obs: observações por holerite
  - guards: pagar exige competência fechada; excluir holerite pago bloqueado;
    holerite espelha a folha paga (P + data)
  - segunda competência (cobre o fix do folha-abrir: header sobrescrito pelo
    READ ao abrir competência com registros existentes)

Faz backup/restauração de dados/folhas.dat, holerites.dat e .tmp.
"""

from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge

FILES = ("dados/folhas.dat", "dados/folhas.tmp",
         "dados/holerites.dat", "dados/holerites.tmp",
         "dados/folha_config.dat")
BACKUP = "/tmp/becrp_rfc007_backup"

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


def espera_erro(fn, fragmento, label):
    try:
        fn()
        check(label, False, "(não levantou erro)")
    except Exception as ex:
        check(label, fragmento in str(ex), str(ex))


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


def main():
    _backup()
    try:
        for path in ("dados/folhas.dat", "dados/holerites.dat"):
            if os.path.exists(os.path.join(ROOT, path)):
                os.remove(os.path.join(ROOT, path))

        cobol_bridge.folha_config_seed()
        comp = "2026/08"

        print("1. Processamento base (RFC-006) para gerar o holerite")
        check("abrir competência", cobol_bridge.folha_abrir(comp))
        r1 = cobol_bridge.folha_calcular({
            "competencia": comp, "funcionario_id": 1, "nome": "Joao Silva",
            "salario_base": 3000.00, "horas_extras": 200.00, "dsr": 33.33,
            "faltas": 0, "dependentes": 0, "outros_proventos": 0,
            "outros_descontos": 0,
        })
        r2 = cobol_bridge.folha_calcular({
            "competencia": comp, "funcionario_id": 2, "nome": "Maria Souza",
            "salario_base": 5000.00, "horas_extras": 0, "dsr": 0,
            "faltas": 1, "dependentes": 2, "outros_proventos": 0,
            "outros_descontos": 0,
        })
        check("folha calculada (2 funcionários)", r1["proventos"] > 0 and r2["proventos"] > 0)
        check("concluir → calculada", cobol_bridge.folha_concluir(comp))

        print("\n2. Guards de geração (RFC-007 §3.1)")
        espera_erro(lambda: cobol_bridge.holerite_gerar(""),
                    "competencia obrigatoria", "gerar sem competência → bloqueado")
        espera_erro(lambda: cobol_bridge.holerite_gerar("2027/01"),
                    "nao processada", "gerar competência inexistente → bloqueado")
        check("abrir 2ª competência (aberta)", cobol_bridge.folha_abrir("2026/09"))
        espera_erro(lambda: cobol_bridge.holerite_gerar("2026/09"),
                    "processe a folha", "gerar competência aberta → bloqueado")

        print("\n3. Gerar holerites da competência")
        ger = cobol_bridge.holerite_gerar(comp)
        check("gerar → status ok", ger.get("status") == "ok", ger)
        check("gerar → 2 holerites", ger.get("gerados") == 2, ger)
        hs = cobol_bridge.holerite_listar()
        check("listar → 2", len(hs) == 2, len(hs))

        h1 = next(h for h in hs if h["funcionario_id"] == 1)
        h2 = next(h for h in hs if h["funcionario_id"] == 2)
        check("valores = processamento (proventos)", quase(h1["proventos"], r1["proventos"]), h1)
        check("valores = processamento (INSS)", quase(h1["inss"], r1["inss"]), h1)
        check("valores = processamento (IRRF)", quase(h1["irrf"], r1["irrf"]), h1)
        check("base INSS no holerite", quase(h1["base_inss"], r1["base_inss"]), h1)
        check("base IRRF no holerite", quase(h1["base_irrf"], r1["base_irrf"]), h1)
        check("FGTS = salário × 8%", quase(h1["fgts"], 3000.00 * 0.08), h1["fgts"])
        check("líquido = proventos − descontos (regra 3)",
              quase(h1["liquido"], h1["proventos"] - h1["total_descontos"]), h1)
        check("situação inicial C", h1["situacao"] == "C", h1["situacao"])
        check("data pagamento vazia", h1["data_pagamento"] == "", h1["data_pagamento"])
        check("horas extras no holerite", quase(h1["horas_extras"], 200.00), h1["horas_extras"])
        check("dependentes no holerite (Maria)", h2["dependentes"] == 2,
              h2.get("dependentes"))

        print("\n4. Detalhes (bases + componentes) e observações")
        det = cobol_bridge.holerite_mostrar(h1["id"])
        check("bases presentes", set(det["bases"]) >= {"salario", "base_inss", "base_irrf", "fgts"},
              det.get("bases"))
        check("base salário correta", quase(det["bases"]["salario"], 3000.00), det["bases"])
        nomes = [c["nome"] for c in det["componentes"]]
        check("componente Salário Base", "Salario Base" in nomes, nomes)
        check("componente Horas Extras", "Horas Extras" in nomes, nomes)
        check("componente DSR", "DSR" in nomes, nomes)
        check("componente INSS", "INSS" in nomes, nomes)
        check("componente IRRF", "IRRF" in nomes, nomes)
        provs = [c for c in det["componentes"] if c["tipo"] == "provento"]
        descs = [c for c in det["componentes"] if c["tipo"] == "desconto"]
        check("soma proventos = total", quase(sum(c["valor_auto"] for c in provs), h1["proventos"]), det)
        check("observações vazias", det["observacoes"] == "", det["observacoes"])
        check("salvar observações", cobol_bridge.holerite_obs(h1["id"], "Pagar até dia 10"))
        det2 = cobol_bridge.holerite_mostrar(h1["id"])
        check("observações persistidas", det2["observacoes"] == "Pagar até dia 10", det2["observacoes"])

        print("\n5. Pagamento (RFC-007 §3.4/§5.1) e exclusão")
        espera_erro(lambda: cobol_bridge.holerite_pagar(h1["id"], "2026-08-10"),
                    "deve estar fechada", "pagar com folha calculada → bloqueado")
        check("validar", cobol_bridge.folha_validar(comp))
        check("fechar", cobol_bridge.folha_fechar(comp))
        check("pagar holerite (folha fechada)", cobol_bridge.holerite_pagar(h1["id"], "2026-08-10"))
        hs = cobol_bridge.holerite_listar()
        hp = next(h for h in hs if h["id"] == h1["id"])
        check("holerite marcado P", hp["situacao"] == "P", hp["situacao"])
        check("data de pagamento gravada", hp["data_pagamento"] == "2026-08-10", hp["data_pagamento"])
        espera_erro(lambda: cobol_bridge.holerite_excluir(h1["id"]),
                    "pago nao pode ser excluido", "excluir holerite pago → bloqueado")

        print("\n6. Regeneração — valores idênticos (imutável, regra 4)")
        antes = {h["funcionario_id"]: h for h in cobol_bridge.holerite_listar()}
        ger2 = cobol_bridge.holerite_gerar(comp)
        check("regenerar → 2 novamente", ger2.get("gerados") == 2, ger2)
        depois = {h["funcionario_id"]: h for h in cobol_bridge.holerite_listar()}
        for fid in antes:
            check(f"regenerado func {fid}: líquido idêntico",
                  quase(antes[fid]["liquido"], depois[fid]["liquido"]),
                  f"{antes[fid]['liquido']} vs {depois[fid]['liquido']}")
            check(f"regenerado func {fid}: FGTS idêntico",
                  quase(antes[fid]["fgts"], depois[fid]["fgts"]),
                  f"{antes[fid]['fgts']} vs {depois[fid]['fgts']}")
            check(f"regenerado func {fid}: base IRRF idêntica",
                  quase(antes[fid]["base_irrf"], depois[fid]["base_irrf"]),
                  f"{antes[fid]['base_irrf']} vs {depois[fid]['base_irrf']}")
        check("excluir holerite não-pago", cobol_bridge.holerite_excluir(depois[1]["id"]))
        check("listar após exclusão → 1", len(cobol_bridge.holerite_listar()) == 1)

        print("\n7. Holerite espelha folha paga + segunda competência")
        check("pagar folha (competência F)", cobol_bridge.folha_pagar(comp, "2026-08-12"))
        ger3 = cobol_bridge.holerite_gerar(comp)
        check("regenerar após pagar folha → todos os funcionários",
              ger3.get("gerados") == 2, ger3)
        hs = cobol_bridge.holerite_listar()
        hrest = [h for h in hs if h["competencia"] == comp]
        check("holerites espelham P com data",
              all(h["situacao"] == "P" and h["data_pagamento"] == "2026-08-12"
                  for h in hrest), hrest)
        cobol_bridge.folha_calcular({
            "competencia": "2026/09", "funcionario_id": 1, "nome": "Joao Silva",
            "salario_base": 3000.00, "horas_extras": 0, "dsr": 0,
            "faltas": 0, "dependentes": 0, "outros_proventos": 0,
            "outros_descontos": 0,
        })
        check("concluir 2026/09", cobol_bridge.folha_concluir("2026/09"))
        ger4 = cobol_bridge.holerite_gerar("2026/09")
        check("gerar 2026/09 → 1 holerite", ger4.get("gerados") == 1, ger4)
        hs = cobol_bridge.holerite_listar()
        check("listar preserva competências (2+1)", len(hs) == 3, len(hs))

        print(f"\n==> RFC-007: {PASS} checks OK, {FAIL} falhas")
        if FAIL:
            sys.exit(1)
    finally:
        _restore()


if __name__ == "__main__":
    main()
