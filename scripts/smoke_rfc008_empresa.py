#!/usr/bin/env python3
"""Smoke E2E do RFC-008 §2 — Dados da Empresa para a Folha.

Cobre:
  - org_store.folha_prontida(): validação da regra 3 (razão social, CNPJ,
    CNAE principal e regime tributário obrigatórios — decisão 1 / §5.3)
  - org_store.salvar_empresa_folha(): grava no estabelecimento padrão e
    devolve o status de prontidão pós-gravação
  - Espelho legado (dados/empresa.json) continua sendo sincronizado

Faz backup/restauração dos JSONs de origem (data/*) para não sujar o repo.
"""

from __future__ import annotations

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import org_store

FILES = (
    "data/empresas.json",
    "data/estabelecimentos_fiscal.json",
    "data/organizacao.json",
    "dados/empresa.json",
)

BACKUP = "/tmp/becrp_rfc008_backup"

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
        if os.path.exists(marker):
            if os.path.exists(dst):
                os.remove(dst)
            os.remove(marker)
        elif os.path.exists(bak):
            shutil.copy2(bak, dst)


def main():
    print("=" * 60)
    print("Smoke RFC-008 §2 — Dados da Empresa (Folha)")
    print("=" * 60)

    _backup()
    try:
        # ── Garante o estado da empresa (CNAE + regime) mesmo em ambiente
        #    limpo de CI, onde a configuração local não está versionada ──
        org_store.salvar_empresa_folha({
            "nome_razao": "COMERCIAL FABIELI LTDA",
            "cnpj": "62832155000141",
            "cnae_prim_codigo": "4754701",
            "tipo_fiscal": "Simples Nacional",
            "crt": 1,
            "uf": "SC",
        })

        # ── Estado atual (empresa Fabieli já tem CNAE + regime) ──
        print("\n1. Prontidão da folha (regra 3)")
        emp = org_store.resolve_empresa_fiscal()
        check("empresa resolvida com nome_razao", bool(emp.get("nome_razao") or emp.get("nome")))
        pronta, faltantes = org_store.folha_prontida()
        check("Fabieli pronta (CNAE + regime preenchidos)", pronta, f"faltantes={faltantes}")
        check("faltantes vazio quando pronta", faltantes == [])

        # ── Zerar regime → fica pendente ──
        print("\n2. Validação da regra 3 (obrigatórios)")
        emp2, pronta2, falt2 = org_store.salvar_empresa_folha({"tipo_fiscal": ""})
        check("sem regime → não pronta", not pronta2, f"faltantes={falt2}")
        check("regime listado como faltante", "tipo_fiscal" in falt2, f"faltantes={falt2}")
        check("crt não substitui tipo_fiscal", "crt" not in falt2, f"faltantes={falt2}")
        check("CNPJ continua obrigatório", "cnpj" not in falt2)  # Fabieli tem CNPJ

        # ── Limpar campo não-fiscal (CEP) → some do overlay/resolvido ──
        emp_cep, _, _ = org_store.salvar_empresa_folha({"cep": ""})
        check("limpar cep remove do resolvido", emp_cep.get("cep") in (None, ""), f"cep={emp_cep.get('cep')!r}")
        emp_cep2, _, _ = org_store.salvar_empresa_folha({"cep": "89335000"})
        check("cep restaurado", emp_cep2.get("cep") == "89335000", f"cep={emp_cep2.get('cep')!r}")

        # ── Voltar regime → pronta de novo ──
        emp3, pronta3, falt3 = org_store.salvar_empresa_folha({"tipo_fiscal": "Lucro Presumido", "crt": 3})
        check("regime restaurado → pronta", pronta3, f"faltantes={falt3}")
        check("crt salvo no overlay", str(emp3.get("crt")) == "3", f"({emp3.get('crt')})")

        # ── Espelho legado continua sendo sincronizado ──
        print("\n3. Espelho legado")
        mirror = org_store.load_empresa_fiscal()
        check("dados/empresa.json espelha a fonte", mirror.get("nome_razao") == emp3.get("nome_razao"))

        # ── Campos RFC-008 §2 presentes ──
        print("\n4. Campos do RFC-008 §2")
        for campo in ("nome_razao", "nome_fantasia", "cnpj", "cnae_prim_codigo",
                      "tipo_fiscal", "uf", "cep", "telefone", "email"):
            check(f"campo {campo} exposto", campo in emp3)

        print("\n" + "=" * 60)
        print(f"RESULTADO: {PASS} OK · {FAIL} FALHOU")
        print("=" * 60)
        sys.exit(1 if FAIL else 0)
    finally:
        _restore()


if __name__ == "__main__":
    main()
