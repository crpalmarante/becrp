#!/usr/bin/env python3
"""Smoke E2E do CRUD COBOL do RFC-002 (Cadastro de Funcionário).

Cobre:
  - gerir_departamentos (RFC-008 §3) — incluir, listar, inativar
  - gerir_cargos (RFC-008 §4)       — incluir, listar, inativar
  - gerir_funcionarios (RFC-002)    — incluir com cargo/departamento,
    CPF duplicado BLOQUEADO (regra 1), alterar, listar com nomes
  - dependentes (RFC-002 §2.6)      — grau de parentesco + tipos
    múltiplos IRRF e/ou salário-família (decisão 3)

Faz backup/restauração dos .dat para não sujar o repo.
"""

from __future__ import annotations

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge

FILES = (
    "dados/departamentos.dat",
    "dados/cargos.dat",
    "dados/funcionarios.dat",
    "dados/dependentes.dat",
)

BACKUP = "/tmp/becrp_rfc002_backup"

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
            # garante que a restauração apaga arquivo criado pelo teste
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
    print("Smoke RFC-002 — CRUD COBOL de Funcionário/Depto/Cargo/Dependentes")
    print("=" * 60)

    _backup()
    try:
        # ── Departamentos ──────────────────────────────────────
        print("\n1. Departamentos (RFC-008 §3)")
        deps = cobol_bridge.departamentos_listar()
        base = len(deps)
        did = cobol_bridge.departamento_incluir({
            "codigo": "TI", "descricao": "Tecnologia",
            "centro_custo": "CC-01", "responsavel": "Ana",
        })
        check("incluir departamento retorna id", isinstance(did, int) and did > 0, f"(id={did})")
        try:
            cobol_bridge.departamento_incluir({
                "codigo": "TI", "descricao": "Duplicado"})
            check("codigo duplicado bloqueado", False)
        except Exception:
            check("codigo duplicado bloqueado", True)
        deps = cobol_bridge.departamentos_listar()
        check("listar inclui novo departamento", len(deps) == base + 1)
        ativos = cobol_bridge.departamentos_listar(ativos_only=True)
        check("listar-ativos só traz ativos", all(d["status"] == "ativo" for d in ativos))

        # Inativação lógica (RFC-008 decisão 4 — nunca exclusão física)
        ok_inat = cobol_bridge.departamento_excluir(did)
        check("inativar departamento retorna OK", ok_inat)
        deps = cobol_bridge.departamentos_listar()
        dep_inat = next((d for d in deps if d["id"] == did), None)
        check("departamento inativado (status=inativo)", dep_inat is not None
              and dep_inat["status"] == "inativo", f"({dep_inat and dep_inat.get('status')})")
        ativos = cobol_bridge.departamentos_listar(ativos_only=True)
        check("inativo some de listar-ativos", all(d["id"] != did for d in ativos))
        # reativa para o teste do funcionário usar
        cobol_bridge.departamento_alterar(did, {"status": "ativo"})

        # ── Cargos ─────────────────────────────────────────────
        print("\n2. Cargos (RFC-008 §4)")
        cargos = cobol_bridge.cargos_listar()
        base_c = len(cargos)
        cid = cobol_bridge.cargo_incluir({
            "codigo": "DEV", "descricao": "Analista de Sistemas",
            "cbo": "2124-05", "salario_referencia": "5000.00"})
        check("incluir cargo retorna id", isinstance(cid, int) and cid > 0, f"(id={cid})")
        cargos = cobol_bridge.cargos_listar()
        novo = next((c for c in cargos if c["id"] == cid), None)
        check("cargo listado com salario_referencia", novo is not None
              and float(novo.get("salario_referencia", 0)) == 5000.00, f"({novo})")

        # Inativação lógica de cargo
        ok_c_inat = cobol_bridge.cargo_excluir(cid)
        check("inativar cargo retorna OK", ok_c_inat)
        cargos = cobol_bridge.cargos_listar()
        car_inat = next((c for c in cargos if c["id"] == cid), None)
        check("cargo inativado (status=inativo)", car_inat is not None
              and car_inat["status"] == "inativo")
        ativos_c = cobol_bridge.cargos_listar(ativos_only=True)
        check("inativo some de listar-ativos", all(c["id"] != cid for c in ativos_c))
        cobol_bridge.cargo_alterar(cid, {"status": "ativo"})

        # ── Funcionário (RFC-002) ──────────────────────────────
        print("\n3. Funcionario (RFC-002)")
        fid = cobol_bridge.funcionario_incluir({
            "nome": "MARIA DA SILVA", "usuario": "maria",
            "senha": "x123", "cpf": "111.222.333-44",
            "data_nasc": "1990-05-10", "sexo": "F",
            "nacionalidade": "Brasileira", "endereco": "Rua A, 10",
            "cep": "01001-000", "cidade": "Sao Paulo", "uf": "SP",
            "ctps": "12345", "ctps_serie": "1", "ctps_uf": "SP",
            "data_adm": "2024-01-15", "salario": "3200.00",
            "forma_pagamento": "Mensalista", "banco": "BB",
            "agencia": "1234", "conta": "56789",
            "vt_optante": "S", "departamento_id": str(did),
            "cargo_id": str(cid),
        })
        check("incluir funcionario retorna id", isinstance(fid, int) and fid > 0, f"(id={fid})")

        # CPF duplicado — regra 1
        try:
            cobol_bridge.funcionario_incluir({
                "nome": "OUTRA PESSOA", "usuario": "outra",
                "senha": "y123", "cpf": "111.222.333-44",
                "data_nasc": "1985-01-01", "sexo": "M",
                "nacionalidade": "Brasileira", "endereco": "Rua B, 5",
                "cep": "02002-000", "cidade": "Campinas", "uf": "SP",
                "ctps": "54321", "ctps_serie": "2", "ctps_uf": "SP",
                "data_adm": "2024-02-01", "salario": "2500.00",
                "forma_pagamento": "Mensalista", "banco": "ITAU",
                "agencia": "4321", "conta": "98765",
                "vt_optante": "N", "departamento_id": str(did),
                "cargo_id": str(cid),
            })
            check("CPF duplicado bloqueado", False)
        except Exception as e:
            check("CPF duplicado bloqueado", "CPF" in str(e), f"({e})")

        funcs = cobol_bridge.funcionarios_listar()
        maria = next((f for f in funcs if f["id"] == fid), None)
        check("funcionario listado com departamento_id/cargo_id",
              maria is not None
              and maria.get("departamento_id") == did
              and maria.get("cargo_id") == cid, f"({maria and maria.get('departamento_id')}/{maria and maria.get('cargo_id')})")

        # RFC-008 regra 2: cargo/departamento inativo não pode ser atribuído
        cobol_bridge.departamento_excluir(did)
        try:
            cobol_bridge.funcionario_incluir({
                "nome": "INATIVO DEPT", "usuario": "inad", "senha": "z123",
                "cpf": "333.444.555-66", "data_nasc": "1992-02-02", "sexo": "M",
                "nacionalidade": "Brasileira", "endereco": "Rua C, 1",
                "cep": "03003-000", "cidade": "SP", "uf": "SP",
                "ctps": "11111", "ctps_serie": "1", "ctps_uf": "SP",
                "data_adm": "2024-03-01", "salario": "2200.00",
                "forma_pagamento": "Mensalista", "banco": "BB",
                "agencia": "1", "conta": "2", "vt_optante": "N",
                "departamento_id": str(did), "cargo_id": str(cid)})
            check("departamento inativo bloqueado", False)
        except Exception as e:
            check("departamento inativo bloqueado", "departamento" in str(e).lower(), f"({e})")
        cobol_bridge.departamento_alterar(did, {"status": "ativo"})

        cobol_bridge.cargo_excluir(cid)
        try:
            cobol_bridge.funcionario_incluir({
                "nome": "INATIVO CARGO", "usuario": "inac", "senha": "w123",
                "cpf": "444.555.666-77", "data_nasc": "1993-03-03", "sexo": "F",
                "nacionalidade": "Brasileira", "endereco": "Rua D, 2",
                "cep": "04004-000", "cidade": "SP", "uf": "SP",
                "ctps": "22222", "ctps_serie": "2", "ctps_uf": "SP",
                "data_adm": "2024-04-01", "salario": "2100.00",
                "forma_pagamento": "Mensalista", "banco": "BB",
                "agencia": "3", "conta": "4", "vt_optante": "N",
                "departamento_id": str(did), "cargo_id": str(cid)})
            check("cargo inativo bloqueado", False)
        except Exception as e:
            check("cargo inativo bloqueado", "cargo" in str(e).lower(), f"({e})")
        cobol_bridge.cargo_alterar(cid, {"status": "ativo"})

        # ── Dependentes (RFC-002 §2.6) ─────────────────────────
        print("\n4. Dependentes (decisão 3: múltiplos tipos)")
        did_dep = cobol_bridge.dependente_incluir({
            "funcionario_id": str(fid), "nome": "PEDRO SILVA",
            "cpf": "999.888.777-66", "data_nasc": "2015-03-20",
            "grau_parentesco": "filho", "irrf": "S", "sal_familia": "S"})
        check("incluir dependente retorna id", isinstance(did_dep, int) and did_dep > 0)
        deps_f = cobol_bridge.dependentes_listar(fid)
        dep = next((d for d in deps_f if d["id"] == did_dep), None)
        check("dependente com IRRF + Sal. Familia simultaneos",
              dep is not None and dep.get("irrf") == "S"
              and dep.get("sal_familia") == "S", f"({dep})")
        check("grau_parentesco exposto", dep is not None
              and dep.get("grau_parentesco") == "filho")

        # só IRRF (sem salário-família) — múltiplos tipos independentes
        cobol_bridge.dependente_incluir({
            "funcionario_id": str(fid), "nome": "ANA SILVA",
            "cpf": "777.666.555-44", "data_nasc": "2018-07-10",
            "grau_parentesco": "conjuge", "irrf": "S", "sal_familia": "N"})
        deps_f = cobol_bridge.dependentes_listar(fid)
        check("dois dependentes listados", len(deps_f) == 2, f"({len(deps_f)})")

        print("\n" + "=" * 60)
        print(f"RESULTADO: {PASS} OK · {FAIL} FALHOU")
        print("=" * 60)
        sys.exit(1 if FAIL else 0)
    finally:
        _restore()


if __name__ == "__main__":
    main()
