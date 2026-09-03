#!/usr/bin/env python3
"""Smoke E2E do RFC-010 (Férias) e RFC-011 (13º Salário).

Cobre (motor COBOL via cobol_bridge — mesmo padrão da rescisão RFC-003):
  - ferias_calcular: base = salario/30 x dias; +1/3 constitucional; abono
    pecuniário com 1/3 próprio; INSS/IRRF progressivos das tabelas da
    config (folha_config.dat) sobre o total (RFC-010 §3/§5)
  - decimo_calcular: base = salario/12 x meses; 1ª parcela sem descontos
    (RFC-011 §3.1), 2ª parcela e única com INSS/IRRF (RFC-011 §3.2)
  - férias vencidas (RFC-010 Decisão 4): gozo após o fim do período
    concessivo (aquis_fim + 12 meses) → vencida=true, alerta e salário em
    dobro (1/3 e abono permanecem na base normal)
  - validations: funcionário obrigatório, dias de férias obrigatórios,
    parcela inválida
  - ferias_incluir/decimo_incluir + listar + pagar + excluir

Faz backup/restauração de dados/ferias.dat, dados/decimo.dat e
dados/funcionarios.dat.
"""

from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge

FILES = ("dados/ferias.dat", "dados/ferias.tmp", "dados/decimo.dat",
         "dados/decimo.tmp", "dados/funcionarios.dat")
BACKUP = "/tmp/becrp_rfc010_011_backup"

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


def quase(a, b, tol=0.01):
    return abs(float(a) - float(b)) <= tol


def main():
    _backup()
    try:
        # cria um funcionário só para os testes (some no restore)
        novo_id = cobol_bridge.funcionario_incluir({
            "nome": "Smoke RFC010/011",
            "usuario": "smoke_rfc010_011",
            "senha": "smoke123",
            "permissoes": "operador",
            "cpf": "99988877755",
            "data_nasc": "1990-01-01",
            "data_adm": "2026-01-05",
            "salario": 3000.00,
        })
        y = next(f for f in cobol_bridge.funcionarios_listar() if f["id"] == novo_id)
        print(f"Usando funcionário #{y['id']} {y['nome']} (salário 3000,00)")

        base_ferias = {
            "funcionario_id": y["id"],
            "nome": y["nome"],
            "aquis_inicio": "2025-07-01",
            "aquis_fim": "2026-06-30",
            "inicio": "2026-08-03",
            "fim": "2026-09-01",
            "dias": 30,
            "dias_abono": 0,
            "salario_base": 3000.00,
        }

        print("\n1. Cálculo de férias (RFC-010 — valores para conferência)")
        r = cobol_bridge.ferias_calcular(base_ferias)
        check("valor base = 30 dias * 100,00", quase(r["valor_base"], 3000.00))
        check("1/3 constitucional", quase(r["um_terco"], 1000.00))
        check("abono zerado sem venda de dias", quase(r["abono"], 0.00))
        check("bruto = base + 1/3", quase(r["bruto"], 4000.00))
        check("INSS progressivo sobre 4000,00", quase(r["inss"], 373.41))
        check("IRRF sobre 4000,00 - INSS", quase(r["irrf"], 162.55))
        check("líquido = bruto - INSS - IRRF", quase(r["liquido"], 3464.04))

        print("\n1b. Férias com abono pecuniário (venda de 10 dias)")
        r2 = cobol_bridge.ferias_calcular({**base_ferias, "dias_abono": 10})
        check("abono = 10 dias * 100,00", quase(r2["abono"], 1000.00))
        check("1/3 do abono", quase(r2["abono_terco"], 333.33))
        check("bruto com abono", quase(r2["bruto"], 5333.33))
        check("INSS com abono", quase(r2["inss"], 556.26))
        check("IRRF com abono", quase(r2["irrf"], 417.69))
        check("líquido com abono", quase(r2["liquido"], 4359.38))

        print("\n1c. Férias vencidas (RFC-010 Decisão 4 — alerta + salário em dobro)")
        # concessivo = aquis_fim + 12m = 2026-06-30 + 12m = 2027-06-30
        base_vencida = {**base_ferias, "inicio": "2027-07-05", "fim": "2027-08-03"}
        rv = cobol_bridge.ferias_calcular(base_vencida)
        check("alerta: vencida=true no cálculo", rv.get("vencida") is True)
        check("salário em dobro (30d x 100,00 x 2)", quase(rv["valor_base"], 6000.00))
        check("1/3 na base normal (1000,00)", quase(rv["um_terco"], 1000.00))
        check("bruto = 6000 + 1000", quase(rv["bruto"], 7000.00))
        check("INSS progressivo sobre 7000,00", quase(rv["inss"], 789.60))
        check("IRRF sobre 7000,00 - INSS", quase(rv["irrf"], 811.86))
        check("líquido vencida", quase(rv["liquido"], 5398.54))

        rv2 = cobol_bridge.ferias_calcular({**base_vencida, "dias_abono": 10})
        check("vencida c/ abono: abono normal (10d x 100,00)", quase(rv2["abono"], 1000.00))
        check("vencida c/ abono: 1/3 do abono normal", quase(rv2["abono_terco"], 333.33))
        check("vencida c/ abono: bruto", quase(rv2["bruto"], 8333.33))
        check("vencida c/ abono: INSS (teto respeitado)", quase(rv2["inss"], 951.63))

        rlim = cobol_bridge.ferias_calcular({**base_ferias, "inicio": "2027-06-30"})
        check("gozo no último dia do concessivo não é vencida",
              rlim.get("vencida") is False)
        check("sem dobro no limite do concessivo", quase(rlim["valor_base"], 3000.00))

        print("\n1d. Registro de férias vencidas + listagem com alerta")
        rinc_v = cobol_bridge.ferias_incluir(base_vencida)
        check("incluir vencida → ok com vencida=true",
              bool(rinc_v.get("id")) and rinc_v.get("vencida") is True)
        ferias_v = cobol_bridge.ferias_listar()
        rec_v = next((ff for ff in ferias_v
                      if str(ff.get("id")) == str(rinc_v.get("id"))), None)
        check("listagem marca vencida (recomputado do registro)",
              rec_v is not None and rec_v.get("vencida") is True)
        check("listagem vencida gravou salário em dobro",
              rec_v is not None and quase(rec_v.get("valor_base"), 6000.00))

        print("\n2. Cálculo de 13º (RFC-011)")
        base_decimo = {"funcionario_id": y["id"], "nome": y["nome"],
                       "ano": "2026", "parcela": "1", "meses": 12,
                       "salario_base": 3000.00}
        rd = cobol_bridge.decimo_calcular(base_decimo)
        check("1ª parcela: base = 3000,00", quase(rd["valor_base"], 3000.00))
        check("1ª parcela sem INSS (RFC-011 §3.1)", quase(rd["inss"], 0.00))
        check("1ª parcela sem IRRF", quase(rd["irrf"], 0.00))
        check("1ª parcela: líquido = bruto", quase(rd["liquido"], 3000.00))

        rd2 = cobol_bridge.decimo_calcular({**base_decimo, "parcela": "2"})
        check("2ª parcela: INSS", quase(rd2["inss"], 253.41))
        check("2ª parcela: IRRF", quase(rd2["irrf"], 36.55))
        check("2ª parcela: líquido", quase(rd2["liquido"], 2710.04))

        rd3 = cobol_bridge.decimo_calcular({**base_decimo, "parcela": "U", "meses": 7})
        check("parcela única 7 meses: base = 1750,00", quase(rd3["valor_base"], 1750.00))
        check("parcela única: INSS", quase(rd3["inss"], 134.73))
        check("parcela única: IRRF zero (faixa 1)", quase(rd3["irrf"], 0.00))

        print("\n3. Validações")
        try:
            cobol_bridge.ferias_calcular({**base_ferias, "funcionario_id": 0})
            check("férias sem funcionário → erro", False)
        except Exception as e:
            check("férias sem funcionário → erro", "obrigatorio" in str(e).lower(), str(e))
        try:
            cobol_bridge.ferias_calcular({**base_ferias, "dias": 0})
            check("férias sem dias → erro", False)
        except Exception as e:
            check("férias sem dias → erro", "dias" in str(e).lower(), str(e))
        try:
            cobol_bridge.decimo_calcular({**base_decimo, "parcela": "X"})
            check("parcela inválida → erro", False)
        except Exception as e:
            check("parcela inválida → erro", "parcela" in str(e).lower(), str(e))
        try:
            cobol_bridge.decimo_calcular({**base_decimo, "meses": 13})
            check("meses > 12 → erro", False)
        except Exception as e:
            check("meses > 12 → erro", "meses" in str(e).lower(), str(e))
        try:
            cobol_bridge.ferias_calcular({**base_ferias, "dias": 30, "dias_abono": 11})
            check("abono acima de 1/3 dos dias → erro", False)
        except Exception as e:
            check("abono acima de 1/3 dos dias → erro", "abono" in str(e).lower(), str(e))

        print("\n4. Registro + listagem + pagamento (folha_pagamento)")
        rinc = cobol_bridge.ferias_incluir({**base_ferias, "dias_abono": 10})
        fid = rinc.get("id")
        check("incluir férias → id retornado", fid and int(fid) > 0)
        ferias = cobol_bridge.ferias_listar()
        achou = next((ff for ff in ferias if str(ff.get("id")) == str(fid)), None)
        check("listar contém as férias", achou is not None)
        check("férias: valores gravados (líquido)", achou and quase(achou.get("liquido"), 4359.38))
        check("férias: situação inicial = C", achou and achou.get("situacao") == "C")
        check("pagar férias → OK", cobol_bridge.ferias_pagar(fid))

        rdec = cobol_bridge.decimo_incluir(base_decimo)
        did = rdec.get("id")
        check("incluir 13º → id retornado", did and int(did) > 0)
        decimos = cobol_bridge.decimos_listar()
        achou2 = next((dd for dd in decimos if str(dd.get("id")) == str(did)), None)
        check("listar contém o 13º", achou2 is not None)
        check("13º: valores gravados (líquido)", achou2 and quase(achou2.get("liquido"), 3000.00))
        check("13º: situação inicial = C", achou2 and achou2.get("situacao") == "C")
        check("pagar 13º → OK", cobol_bridge.decimo_pagar(did))

        print("\n5. Exclusão (registro não pago)")
        rinc2 = cobol_bridge.ferias_incluir({**base_ferias, "inicio": "2026-10-01", "fim": "2026-10-30"})
        fid2 = rinc2.get("id")
        check("excluir férias 'C' → OK", cobol_bridge.ferias_excluir(fid2))
        rdec2 = cobol_bridge.decimo_incluir({**base_decimo, "ano": "2025"})
        did2 = rdec2.get("id")
        check("excluir 13º 'C' → OK", cobol_bridge.decimo_excluir(did2))

        print(f"\n{'=' * 50}\nResultado: {PASS} ok / {FAIL} falhas\n{'=' * 50}")
        sys.exit(0 if FAIL == 0 else 1)
    finally:
        _restore()


if __name__ == "__main__":
    main()
