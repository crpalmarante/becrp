#!/usr/bin/env python3
"""Smoke E2E do RFC-014 — Encargos patronais: FGTS, INSS patronal, RAT/SAT.

Cobre (motor COBOL via cobol_bridge):
  - config versionado com alíquotas de encargos (INSS patronal 20%, RAT 2%,
    terceiros 0%) no layout novo (230 bytes por linha)
  - salvar/ler das alíquotas de encargos por competência
  - cálculo no fechamento (RFC-014 §4.4/Decisão 4): base = soma dos proventos
    que incidem FGTS; INSS patronal/RAT/terceiros sobre a tabela vigente;
    encargos NUNCA aparecem no holerite (RFC-007 decisão 1)
  - regime Simples Nacional (RFC-014 §3/Decisão 2): zera INSS patronal,
    RAT e terceiros (recolhimento unificado DAS); FGTS permanece
  - persistência: encargos-mostrar lê o registro gravado no fechamento

Faz backup/restauração de dados/folha_config.dat, dados/folhas.dat,
dados/folhas.tmp e dados/encargos.dat (arquivos tocados pelo fluxo).
"""

from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge

FILES = ("dados/folha_config.dat", "dados/folhas.dat", "dados/folhas.tmp",
         "dados/holerites.dat", "dados/encargos.dat", "dados/encargos.tmp")
BACKUP = "/tmp/becrp_rfc014_backup"

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


def _processar(comp, salario):
    cobol_bridge.folha_abrir(comp)
    cobol_bridge.folha_calcular({
        "competencia": comp, "funcionario_id": 1, "nome": "Joao",
        "salario_base": salario, "horas_extras": 0, "dsr": 0, "faltas": 0,
        "dependentes": 0, "outros_proventos": 0, "outros_descontos": 0,
        "cotas_sf": 0,
    })
    cobol_bridge.folha_concluir(comp)
    cobol_bridge.folha_validar(comp)
    cobol_bridge.folha_fechar(comp)


def main():
    _backup()
    try:
        for path in FILES:
            dst = os.path.join(ROOT, path)
            if os.path.exists(dst):
                os.remove(dst)

        print("1. Config — encargos patronais versionados (RFC-014 §4.2)")
        cobol_bridge.folha_config_seed()
        cfg = cobol_bridge.folha_config_ler()
        check("config tem INSS patronal 20%", quase(cfg.get("inss_patronal_aliq"), 20.00),
              cfg.get("inss_patronal_aliq"))
        check("config tem RAT/SAT 2%", quase(cfg.get("rat_aliq"), 2.00),
              cfg.get("rat_aliq"))
        check("config tem terceiros 0% (configurável)", quase(cfg.get("terceiros_aliq"), 0.00),
              cfg.get("terceiros_aliq"))
        with open(os.path.join(ROOT, "dados/folha_config.dat"), encoding="utf-8",
                  errors="replace") as f:
            linhas = [l for l in f.read().splitlines() if l.strip()]
        check("layout físico 230 bytes (RFC-014 estendeu o config)",
              len(linhas) == 1 and len(linhas[0].strip()) == 230,
              f"{len(linhas[0].strip()) if linhas else 0} bytes")

        print("\n2. Fechamento — encargos calculados e consolidados (§4.4)")
        comp = "2026/05"
        _processar(comp, "3000.00")
        enc = cobol_bridge.folha_encargos(comp, regime="lucro")
        check("base de encargos = salário base (3000,00)", quase(enc.get("base"), 3000.00),
              enc.get("base"))
        check("FGTS 8% = 240,00", quase(enc.get("fgts"), 240.00), enc.get("fgts"))
        check("INSS patronal 20% = 600,00", quase(enc.get("inss_patronal"), 600.00),
              enc.get("inss_patronal"))
        check("RAT/SAT 2% = 60,00", quase(enc.get("rat"), 60.00), enc.get("rat"))
        check("terceiros 0% = 0,00", quase(enc.get("terceiros"), 0.00), enc.get("terceiros"))
        check("total = 900,00", quase(enc.get("total"), 900.00), enc.get("total"))

        print("\n3. Persistência — registro gravado no fechamento")
        enc2 = cobol_bridge.folha_encargos_mostrar(comp)
        check("encargos-mostrar retorna a competência", enc2.get("competencia") == comp,
              enc2.get("competencia"))
        check("total persistido (900,00)", quase(enc2.get("total"), 900.00),
              enc2.get("total"))
        check("regime gravado (lucro)", (enc2.get("regime") or "").strip() == "lucro",
              enc2.get("regime"))

        print("\n4. Simples Nacional — sem INSS patronal separado (§3/Decisão 2)")
        comp2 = "2026/04"
        _processar(comp2, "3000.00")
        enc3 = cobol_bridge.folha_encargos(comp2, regime="simples")
        check("regime aplicado (simples)", (enc3.get("regime") or "").strip() == "simples",
              enc3.get("regime"))
        check("FGTS permanece 240,00", quase(enc3.get("fgts"), 240.00), enc3.get("fgts"))
        check("INSS patronal zerado (DAS)", quase(enc3.get("inss_patronal"), 0.00),
              enc3.get("inss_patronal"))
        check("RAT zerado (DAS)", quase(enc3.get("rat"), 0.00), enc3.get("rat"))
        check("terceiros zerado (DAS)", quase(enc3.get("terceiros"), 0.00),
              enc3.get("terceiros"))

        print("\n5. Encargos NUNCA aparecem no holerite (RFC-007 decisão 1)")
        det = cobol_bridge.folha_mostrar(comp)
        funcs = det.get("funcionarios", [])
        campos_encargo = ("inss_patronal", "rat", "terceiros")
        check("holerite não expõe encargos patronais",
              all(k not in f for f in funcs for k in campos_encargo),
              [list(f.keys()) for f in funcs])

        print(f"\n{'='*50}\nResultado: {PASS} ok / {FAIL} falhas\n{'='*50}")
        sys.exit(0 if FAIL == 0 else 1)
    finally:
        _restore()


if __name__ == "__main__":
    main()
