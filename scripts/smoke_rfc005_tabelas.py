#!/usr/bin/env python3
"""Smoke E2E do RFC-005 — Tabelas fiscais: INSS/IRRF/Salário-Família.

Cobre (motor COBOL via cobol_bridge):
  - seed idempotente no layout novo (215 bytes, competência + 28 campos)
  - faixas de salário-família no config (2 faixas: teto + valor por cota)
  - versionamento por competência (Regra 1/Decisão 1): config-ler sem
    competência devolve a última versão; com competência devolve a vigente;
    'versões' preserva o histórico
  - guard (Regra 2): salvar tabela de competência já fechada/paga é
    bloqueado (imutabilidade)
  - cálculo no processamento (RFC-005 §4): cotas_sf × valor da faixa;
    o valor entra nos proventos e no líquido, mas NÃO incide INSS/IRRF
    (a base INSS é calculada antes do salário-família)

Faz backup/restauração de dados/folha_config.dat, dados/folhas.dat,
dados/folhas.tmp e dados/holerites.dat (arquivos tocados pelo fluxo).
"""

from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge

FILES = ("dados/folha_config.dat", "dados/folhas.dat", "dados/folhas.tmp",
         "dados/holerites.dat")
BACKUP = "/tmp/becrp_rfc005_backup"

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


def quase(a, b, tol=0.02):
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
        elif os.path.exists(marker) and os.path.exists(dst):
            os.remove(dst)
    shutil.rmtree(BACKUP, ignore_errors=True)


def main():
    _backup()
    try:
        # estado limpo: remove os .dat do processamento e o config antes do
        # seed (o seed é idempotente e não regrava um config já no layout novo)
        for path in FILES:
            if path.endswith(("folhas.dat", "folha_config.dat")) \
                    and os.path.exists(os.path.join(ROOT, path)):
                os.remove(os.path.join(ROOT, path))

        print("1. Config — seed idempotente no layout novo (competência + SF + encargos)")
        cobol_bridge.folha_config_seed()
        cfg = cobol_bridge.folha_config_ler()
        check("config tem competência", bool(cfg.get("competencia")), cfg.get("competencia"))
        check("config tem faixa 1 SF (teto 1905,52)", quase(cfg.get("sf_f1_teto"), 1905.52), cfg.get("sf_f1_teto"))
        check("config tem faixa 1 SF (valor 62,04)", quase(cfg.get("sf_f1_valor"), 62.04), cfg.get("sf_f1_valor"))
        check("config tem faixa 2 SF (teto 3047,00)", quase(cfg.get("sf_f2_teto"), 3047.00), cfg.get("sf_f2_teto"))
        check("config tem faixa 2 SF (valor 43,17)", quase(cfg.get("sf_f2_valor"), 43.17), cfg.get("sf_f2_valor"))
        # RFC-014 — encargos patronais versionados
        check("config tem INSS patronal 20%", quase(cfg.get("inss_patronal_aliq"), 20.00), cfg.get("inss_patronal_aliq"))
        check("config tem RAT/SAT 2%", quase(cfg.get("rat_aliq"), 2.00), cfg.get("rat_aliq"))
        check("config tem terceiros 0% (configurável)", quase(cfg.get("terceiros_aliq"), 0.00), cfg.get("terceiros_aliq"))
        check("seed idempotente (2ª chamada não regrava)", cobol_bridge.folha_config_seed() is False)
        # layout físico: 230 bytes por linha (RFC-014 estendeu de 215)
        with open(os.path.join(ROOT, "dados/folha_config.dat"), encoding="utf-8", errors="replace") as f:
            linhas = [l for l in f.read().splitlines() if l.strip()]
        check("arquivo multi-linha (uma versão por linha)",
              len(linhas) == 1 and len(linhas[0].strip()) == 230,
              f"{len(linhas)} linhas, {len(linhas[0].strip()) if linhas else 0} bytes")

        print("\n2. Versionamento por competência (Regra 1/Decisão 1)")
        base = dict(cfg)
        base.update({"competencia": "2026/07", "sf_f1_teto": 1900.00, "sf_f1_valor": 60.00})
        cobol_bridge.folha_config_salvar(base)
        v07 = cobol_bridge.folha_config_ler("2026/07")
        check("versão 2026/07 salva e lida", v07.get("competencia") == "2026/07"
              and quase(v07.get("sf_f1_valor"), 60.00), v07.get("competencia"))
        v_ult = cobol_bridge.folha_config_ler()
        check("ler sem competência devolve a última versão",
              v_ult.get("competencia") == "2026/07", v_ult.get("competencia"))
        check("histórico 'versões' preserva as competências",
              # invariante: o histórico mantém a versão semeada (mês corrente)
              # E a versão salva neste teste — sem depender do mês da execução
              set(v_ult.get("versoes") or []) >= {"2026/07", cfg.get("competencia")},
              v_ult.get("versoes"))

        print("\n3. Guard (Regra 2) — tabela de competência fechada é imutável")
        comp = "2026/06"
        cobol_bridge.folha_config_salvar(dict(base, competencia=comp))
        cobol_bridge.folha_abrir(comp)
        cobol_bridge.folha_calcular({
            "competencia": comp, "funcionario_id": 1, "nome": "Joao",
            "salario_base": 2000.00, "horas_extras": 0, "dsr": 0,
            "faltas": 0, "dependentes": 0, "outros_proventos": 0,
            "outros_descontos": 0, "cotas_sf": 2,
        })
        cobol_bridge.folha_concluir(comp)
        cobol_bridge.folha_validar(comp)
        cobol_bridge.folha_fechar(comp)
        try:
            cobol_bridge.folha_config_salvar(dict(base, competencia=comp,
                                                  sf_f1_valor=99.00))
            check("salvar tabela de competência fechada → bloqueado", False)
        except Exception as ex:
            check("salvar tabela de competência fechada → bloqueado",
                  "imutavel" in str(ex) or "fechada" in str(ex), str(ex))
        v06 = cobol_bridge.folha_config_ler(comp)
        check("valor da tabela fechada preservado", quase(v06.get("sf_f1_valor"), 60.00),
              v06.get("sf_f1_valor"))

        print("\n4. Cálculo do salário-família no processamento (RFC-005 §4)")
        # competência aberta (limpa) para recalcular
        comp2 = "2026/05"
        cobol_bridge.folha_abrir(comp2)
        # faixa 1: salário 1500 ≤ 1900 → 2 cotas × 60,00 = 120,00
        r_f1 = cobol_bridge.folha_calcular({
            "competencia": comp2, "funcionario_id": 1, "nome": "Faixa1",
            "salario_base": 1500.00, "horas_extras": 0, "dsr": 0,
            "faltas": 0, "dependentes": 0, "outros_proventos": 0,
            "outros_descontos": 0, "cotas_sf": 2,
        })
        check("faixa 1: 2 cotas × 60,00 = 120,00", quase(r_f1.get("salario_familia"), 120.00),
              r_f1.get("salario_familia"))
        check("faixa 1: proventos = salário + SF", quase(r_f1.get("proventos"), 1620.00),
              r_f1.get("proventos"))
        check("faixa 1: SF não incide INSS (base = salário)",
              quase(r_f1.get("base_inss"), 1500.00), r_f1.get("base_inss"))
        # faixa 2: salário 2500 (1900 < 2500 ≤ 3047) → 2 cotas × 45,00... mas o
        # valor da faixa 2 no config atual é 43,17 (padrão) — usamos a faixa 2
        # da competência 2026/05 (padrão): teto 3047/valor 43,17
        r_f2 = cobol_bridge.folha_calcular({
            "competencia": comp2, "funcionario_id": 2, "nome": "Faixa2",
            "salario_base": 2500.00, "horas_extras": 0, "dsr": 0,
            "faltas": 0, "dependentes": 0, "outros_proventos": 0,
            "outros_descontos": 0, "cotas_sf": 2,
        })
        check("faixa 2: 2 cotas × 43,17 = 86,34", quase(r_f2.get("salario_familia"), 86.34),
              r_f2.get("salario_familia"))
        check("faixa 2: SF fora da base INSS", quase(r_f2.get("base_inss"), 2500.00),
              r_f2.get("base_inss"))
        # sem direito: salário acima do 2º teto (3047) → 0
        r_sem = cobol_bridge.folha_calcular({
            "competencia": comp2, "funcionario_id": 3, "nome": "SemDireito",
            "salario_base": 4000.00, "horas_extras": 0, "dsr": 0,
            "faltas": 0, "dependentes": 0, "outros_proventos": 0,
            "outros_descontos": 0, "cotas_sf": 2,
        })
        check("acima do 2º teto → sem salário-família",
              quase(r_sem.get("salario_familia"), 0.00), r_sem.get("salario_familia"))
        # sem cotas (dependente sem elegibilidade) → 0 mesmo na faixa 1
        r_semcota = cobol_bridge.folha_calcular({
            "competencia": comp2, "funcionario_id": 4, "nome": "SemCota",
            "salario_base": 1500.00, "horas_extras": 0, "dsr": 0,
            "faltas": 0, "dependentes": 0, "outros_proventos": 0,
            "outros_descontos": 0, "cotas_sf": 0,
        })
        check("sem cotas → 0 mesmo na faixa 1",
              quase(r_semcota.get("salario_familia"), 0.00), r_semcota.get("salario_familia"))

        print("\n5. Persistência — salário-família no detalhe da folha")
        det = cobol_bridge.folha_mostrar(comp2)
        funcs = det.get("funcionarios", [])
        check("mostrar expõe salario_familia", all("salario_familia" in f for f in funcs),
              [f.get("salario_familia") for f in funcs])
        f1 = next((f for f in funcs if f.get("funcionario_id") == 1), {})
        check("SF persistido no registro (120,00)", quase(f1.get("salario_familia"), 120.00),
              f1.get("salario_familia"))

        print(f"\n{'='*50}\nResultado: {PASS} ok / {FAIL} falhas\n{'='*50}")
        sys.exit(0 if FAIL == 0 else 1)
    finally:
        _restore()


if __name__ == "__main__":
    main()
