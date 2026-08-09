#!/usr/bin/env python3
"""run_ci.py — Suíte de CI: smokes COBOL/RFC + review da tela Processar Folha.

Etapas:
  1. Build: recompila os programas COBOL (cobol/programs/*.cbl → cobol/bin/*)
     para garantir que os binários estão em dia com as fontes
  2. Smokes: smoke_jsonio, smoke_rfc002_cobol, smoke_rfc003_rescisao,
     smoke_rfc004_eventos, smoke_rfc006_folha, smoke_rfc007_holerite,
     smoke_rfc008_empresa (cada um com backup/restauração própria)
  3. Seed: usuário admin (bruno/123456 com token fixo) + departamento/cargo/
     funcionário ativo (a tela lista os ativos)
  4. review_tela_folha.py — sobe o servidor em porta dedicada e replica o
     fluxo completo da tela Processar Folha + Holerites
  5. Restaura os arquivos de seed e reporta o resumo

Os arquivos de seed (data/users.json, dados/departamentos.dat,
dados/cargos.dat, dados/funcionarios.dat) são restaurados ao final, então é
seguro rodar localmente. Não rode com outro servidor usando os mesmos dados/
simultaneamente.

Uso:
    python3 scripts/run_ci.py             # suíte completa
    python3 scripts/run_ci.py --no-build  # pula a recompilação do COBOL
"""

from __future__ import annotations

import glob
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import cobol_bridge  # noqa: E402
import jsonio  # noqa: E402

SMOKES = [
    "smoke_jsonio",
    "smoke_rfc002_cobol",
    "smoke_rfc003_rescisao",
    "smoke_rfc004_eventos",
    "smoke_rfc006_folha",
    "smoke_rfc007_holerite",
    "smoke_rfc008_empresa",
]

SEED_FILES = [
    "data/users.json",
    "dados/departamentos.dat",
    "dados/cargos.dat",
    "dados/funcionarios.dat",
]
SEED_BACKUP = "/tmp/becrp_ci_seed_backup"

PASS = 0
FAIL = 0


def step(title):
    print(f"\n{'─' * 60}\n▶ {title}\n{'─' * 60}")


def run(cmd, **kw):
    """Roda um comando herdando a saída; devolve o exit code."""
    return subprocess.run(cmd, cwd=ROOT, **kw).returncode


def build_cobol(force=False):
    """Recompila os programas COBOL. Com force=True ignora mtime (git não
    preserva timestamps no checkout — em CI limpo o mtime comparado mentiria)."""
    built, erro = [], []
    for src in sorted(glob.glob("cobol/programs/*.cbl")):
        prog = os.path.basename(src)[:-4]
        exe = os.path.join("cobol", "bin", prog)
        if (not force and os.path.exists(exe)
                and os.path.getmtime(exe) >= os.path.getmtime(src)):
            continue
        r = subprocess.run(["cobc", "-x", src, "-o", exe], cwd=ROOT,
                           capture_output=True, text=True)
        if r.returncode == 0:
            built.append(prog)
        else:
            erro.append(f"{prog}: {r.stderr.strip().splitlines()[-1][:120] if r.stderr else '?'}")
    if erro:
        print("  ❌ falhas de compilação:", *erro, sep="\n     ")
        return False
    print(f"  ✅ {len(built)} programa(s) compilado(s)" if built
          else "  ✅ binários COBOL já em dia")
    return True


def backup_seed():
    os.makedirs(SEED_BACKUP, exist_ok=True)
    for rel in SEED_FILES:
        src = os.path.join(ROOT, rel)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(SEED_BACKUP, os.path.basename(rel)))
        else:
            open(os.path.join(SEED_BACKUP, os.path.basename(rel) + ".nao-existia"), "w").close()


def restore_seed():
    for rel in SEED_FILES:
        dst = os.path.join(ROOT, rel)
        bak = os.path.join(SEED_BACKUP, os.path.basename(rel))
        marker = bak + ".nao-existia"
        if os.path.exists(bak):
            shutil.copy2(bak, dst)
        elif os.path.exists(marker) and os.path.exists(dst):
            os.remove(dst)
    shutil.rmtree(SEED_BACKUP, ignore_errors=True)


def seed():
    """Cria usuário admin e um funcionário ativo para a tela listar."""
    # atenção: o login responde "nome" do usuário — sem esse campo o handler
    # quebra DEPOIS de rotacionar o token e a resposta se perde (403s em cascata)
    users = {"bruno": {
        "usuario": "bruno",
        "nome": "Bruno CI",
        "email": "bruno@ci.local",
        "senha": hashlib.sha256(b"123456").hexdigest(),
        "role": "admin",
        "empresas": {},
        "ativo": True,
        "token": "ci-token-becrp-2026",
    }}
    jsonio.save("data/users.json", users)
    did = cobol_bridge.departamento_incluir({
        "codigo": "CI", "descricao": "CI Pipeline",
        "centro_custo": "CC-CI", "responsavel": "CI"})
    cid = cobol_bridge.cargo_incluir({
        "codigo": "CI", "descricao": "CI Cargo",
        "cbo": "0000-00", "salario_referencia": "3000.00"})
    fid = cobol_bridge.funcionario_incluir({
        "nome": "CI FUNCIONARIO", "usuario": "ci.func",
        "senha": "x123", "cpf": "999.888.777-66",
        "data_nasc": "1990-01-01", "sexo": "M",
        "nacionalidade": "Brasileira", "endereco": "Rua CI, 1",
        "cep": "01000-000", "cidade": "Sao Paulo", "uf": "SP",
        "ctps": "90001", "ctps_serie": "1", "ctps_uf": "SP",
        "data_adm": "2026-01-05", "salario": "3000.00",
        "forma_pagamento": "Mensalista", "banco": "BB",
        "agencia": "0001", "conta": "12345",
        "vt_optante": "S", "departamento_id": str(did),
        "cargo_id": str(cid),
    })
    if not (isinstance(did, int) and did > 0 and isinstance(cid, int) and cid > 0
            and isinstance(fid, int) and fid > 0):
        raise RuntimeError(f"seed falhou: dep={did} cargo={cid} func={fid}")
    # auto-verificação: a tela depende de ≥1 funcionário com situação ativa
    funcs = cobol_bridge.funcionarios_listar()
    ativos = [f for f in funcs
              if str(f.get("situacao_vinculo", "") or "").lower() in ("ativo", "a", "")]
    if not ativos:
        raise RuntimeError(
            "seed: nenhum funcionário ativo em funcionarios_listar: "
            f"{[f.get('situacao_vinculo') for f in funcs]}")
    print(f"  ✅ seed: admin bruno/123456 · departamento #{did} · cargo #{cid} · funcionário #{fid}")


def main():
    global PASS, FAIL
    do_build = "--no-build" not in sys.argv
    force_build = "--force-build" in sys.argv

    if do_build:
        step("1. Build COBOL")
        if not build_cobol(force=force_build):
            FAIL += 1
        else:
            PASS += 1

    step("2. Smokes (RFC + jsonio)")
    for name in SMOKES:
        code = run([sys.executable, "-B", os.path.join("scripts", name + ".py")])
        if code == 0:
            PASS += 1
            print(f"  └─ ✅ {name}")
        else:
            FAIL += 1
            print(f"  └─ ❌ {name} (exit {code})")

    step("3. Seed (admin + funcionário ativo)")
    backup_seed()
    try:
        try:
            seed()
        except Exception as e:
            FAIL += 1
            print(f"  ❌ seed: {e}")
            return finalize()  # o finally restaura

        step("4. Review da tela Processar Folha + Holerites")
        code = run([sys.executable, "scripts/review_tela_folha.py", "--port", "8137"])
        if code == 0:
            PASS += 1
            print("  └─ ✅ review_tela_folha")
        else:
            FAIL += 1
            print(f"  └─ ❌ review_tela_folha (exit {code})")
    finally:
        restore_seed()

    return finalize()


def finalize():
    print(f"\n{'=' * 60}")
    print(f"CI: {PASS} ✅  {FAIL} ❌")
    print(f"{'=' * 60}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
