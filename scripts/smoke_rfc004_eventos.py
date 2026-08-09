#!/usr/bin/env python3
"""Smoke E2E do RFC-004 — Eventos: Proventos e Descontos.

Cobre (motor COBOL via cobol_bridge):
  - seed do catálogo inicial (RFC-004 §3): 19 eventos (10 proventos + 9
    descontos) e idempotência do seed
  - estrutura do evento: código, tipo, categoria, referência, incidências
    INSS/IRRF/FGTS, ordem, uso e teto (decisão 3)
  - validações: código obrigatório/único (entre ativos), tipo válido
  - CRUD: incluir, alterar, inativação lógica (nunca exclusão física)

Faz backup/restauração de dados/eventos.dat e dados/eventos.tmp.
"""

from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge

FILES = ("dados/eventos.dat", "dados/eventos.tmp")
BACKUP = "/tmp/becrp_rfc004_backup"

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


def main():
    _backup()
    try:
        # garante estado limpo: remove o .dat antes do 1º seed (restaurado no fim)
        for path in FILES:
            if path.endswith(".dat") and os.path.exists(os.path.join(ROOT, path)):
                os.remove(os.path.join(ROOT, path))
        print("1. Catálogo inicial (RFC-004 §3)")
        criados = cobol_bridge.eventos_seed_catalogo()
        check("seed cria 19 eventos", len(criados) == 19, f"{len(criados)}")
        check("seed idempotente (2ª chamada = 0)", len(cobol_bridge.eventos_seed_catalogo()) == 0)
        evs = cobol_bridge.eventos_listar()
        check("listar → 19", len(evs) == 19, f"{len(evs)}")
        check("listar-ativos → 19", len(cobol_bridge.eventos_listar(ativos_only=True)) == 19)
        por_codigo = {e["codigo"]: e for e in evs}
        sb = por_codigo[1]
        check("código 1 = Salário Base (provento)", sb["descricao"] == "Salário Base" and sb["tipo"] == "provento")
        check("Salário Base incide INSS/IRRF/FGTS", sb["incide_inss"] == "S" and sb["incide_irrf"] == "S" and sb["incide_fgts"] == "S")
        sf = por_codigo[9]
        check("Salário-Família NÃO incide (RFC §5)", sf["incide_inss"] == "N" and sf["incide_irrf"] == "N" and sf["incide_fgts"] == "N")
        vt = por_codigo[22]
        check("Vale-Transporte é desconto", vt["tipo"] == "desconto")
        check("ordem de cálculo coerente", por_codigo[1]["ordem"] == 1 and por_codigo[21]["ordem"] == 21)

        print("\n2. Incluir evento custom")
        eid = cobol_bridge.evento_incluir({
            "codigo": 30, "descricao": "Bonus Producao", "tipo": "provento",
            "categoria": "remuneracao", "referencia": "valor",
            "formula": "Valor fixo conforme producao", "incide_inss": "S",
            "incide_irrf": "S", "incide_fgts": "S", "ordem": 30, "uso": "mensal",
            "teto": 500.00,
        })
        check("incluir → id retornado", eid and int(eid) > 0)
        evs = cobol_bridge.eventos_listar()
        e30 = next(e for e in evs if e["codigo"] == 30)
        check("evento 30 gravado com teto", e30["teto"] == 500.00, f"{e30.get('teto')}")
        try:
            cobol_bridge.evento_incluir({"codigo": 30, "descricao": "Dup", "tipo": "provento"})
            check("código duplicado ativo → bloqueado", False)
        except Exception as ex:
            check("código duplicado ativo → bloqueado", "ja cadastrado" in str(ex).lower(), str(ex))
        try:
            cobol_bridge.evento_incluir({"codigo": 31, "descricao": "X", "tipo": "bonus"})
            check("tipo inválido → bloqueado", False)
        except Exception as ex:
            check("tipo inválido → bloqueado", "tipo de evento invalido" in str(ex).lower(), str(ex))

        print("\n3. Alterar")
        ok = cobol_bridge.evento_alterar(eid, {"descricao": "Bonus Producao Q2", "teto": 600.00})
        check("alterar → OK", ok)
        e30b = next(e for e in cobol_bridge.eventos_listar() if e["codigo"] == 30)
        check("descricao atualizada", e30b["descricao"] == "Bonus Producao Q2", e30b["descricao"])
        check("teto atualizado", e30b["teto"] == 600.00)
        # alterar trocando o código para um já ativo (Salário Base = 1) → bloqueado
        try:
            cobol_bridge.evento_alterar(eid, {"codigo": 1})
            check("alterar p/ código duplicado ativo → bloqueado", False)
        except Exception as ex:
            check("alterar p/ código duplicado ativo → bloqueado", "ja cadastrado" in str(ex).lower(), str(ex))
        # alterar trocando o código para um livre → OK
        ok = cobol_bridge.evento_alterar(eid, {"codigo": 31})
        check("alterar trocando código p/ livre → OK", ok)
        e31 = next(e for e in cobol_bridge.eventos_listar() if e["codigo"] == 31)
        check("código 31 gravado", e31["id"] == int(eid))

        print("\n4. Inativação lógica")
        check("inativar → OK", cobol_bridge.evento_excluir(eid))
        ativos = cobol_bridge.eventos_listar(ativos_only=True)
        check("código 31 some de listar-ativos", all(e["codigo"] != 31 for e in ativos))
        todos = cobol_bridge.eventos_listar()
        e30c = next(e for e in todos if e["codigo"] == 31)
        check("código 31 segue no listar como inativo", e30c["status"] == "inativo")

        print("\n5. Re-seed recria inativado (validação permite duplicar só inativo)")
        novo = cobol_bridge.eventos_seed_catalogo()
        check("re-seed não recria código 31 (fora do catálogo)", 31 not in novo)
        # inativa o Salário Base (código 1, do catálogo) e re-seeda
        e1 = next(e for e in cobol_bridge.eventos_listar() if e["codigo"] == 1)
        cobol_bridge.evento_excluir(e1["id"])
        novo2 = cobol_bridge.eventos_seed_catalogo()
        check("re-seed recria Salário Base inativado", 1 in novo2, f"{novo2}")
        ativos = cobol_bridge.eventos_listar(ativos_only=True)
        check("total ativos = 19 (30 inativo + 1 recriado)", len(ativos) == 19, f"{len(ativos)}")

        print(f"\n{'='*50}\nResultado: {PASS} ok / {FAIL} falhas\n{'='*50}")
        sys.exit(0 if FAIL == 0 else 1)
    finally:
        _restore()


if __name__ == "__main__":
    main()
