#!/usr/bin/env python3
"""run_ci.py — Suíte de CI: smokes COBOL/RFC + review da tela Processar Folha.

Etapas:
  1. Build: recompila os programas COBOL (cobol/programs/*.cbl → cobol/bin/*)
     para garantir que os binários estão em dia com as fontes
  2. Seed: usuário admin (bruno/123456 com token fixo) + departamento/cargo/
     funcionário ativo (a tela lista os ativos)
  3. Smokes: smoke_jsonio, smoke_rfc002_cobol, smoke_rfc003_rescisao,
     smoke_rfc004_eventos, smoke_rfc005_tabelas, smoke_rfc006_folha,
     smoke_rfc007_holerite, smoke_rfc008_empresa,
     smoke_rfc010_011_ferias_decimo, smoke_rfc013_complementar (cada um com
     backup/restauração própria)
  4. review_tela_folha.py — sobe o servidor em porta dedicada e replica o
     fluxo completo da tela Processar Folha + Holerites
  5. review_tela_funcionarios.py — revisão da tela de funcionários (máscaras)
  6. review_tela_ferias_decimo.py — revisão das abas Férias e 13º Salario
     (RFC-010/011) com a guarda do portal (role funcionario); o modo --browser
     sobe o servidor com cenário visual (férias VENCIDA + normal) para
     conferência em navegador real
  7. checks de render (Node) — check_render_ferias_node.js,
     check_render_rescisao_node.js, check_render_rh_dashboard_node.js,
     check_render_rh_workflow_node.js e check_render_complementar_node.js
     executam o código real das páginas (folha.html / rh_dashboard.html) com
     DOM stub e validam os badges VENCIDA (férias) e EM DOBRO (rescisão), os
     toasts de alerta, o wrapper de autenticação, o badge-alerta de férias
     vencidas, o workflow (badges de role/histórico, gating de botões por role
     e envio do user_role) no RH Dashboard e a aba Complementar (badges de
     situação C/V/F/P e gating dos botões Validar/Fechar/Pagar/Holerite/
     Excluir por estado — RFC-013). Requerem node no ambiente; quando ausente
     (CI Python puro) o passo é pulado com aviso e não conta no resumo. Dica:
     rodar com node instalado (node está pré-instalado nos runners do GitHub
     Actions)
  8. review_tela_rh_dashboard.py — revisão do RH Dashboard (KPIs, alerta de
     férias vencidas, aprovações de licenças/despesas e workflow)
  9. [opcional --browser] Cenários visuais das abas Complementar e Rescisão
     — o cenario_complementar_browser.py sobe o servidor na porta 8141 com
     seed de 4 complementares (estados C/V/F/P) e o cenario_rescisao_browser.py
     na porta 8142 com seed de 2 rescisões (uma EM DOBRO e uma normal). Cada um
     é validado via HTTP (GET /api/folha/complementares e /api/folha/rescisoes
     com token fixo do cenário) e encerrado com SIGTERM, que restaura os dados.
     São os mesmos cenários usados com browser-use para conferência visual em
     navegador real (badges de situação, botões por estado, badge EM DOBRO);
     no CI rodam como check determinístico da consistência do seed — o render
     visual em si continua coberto pelos checks Node do passo 7 e, para
     conferência manual, o cenário pode ser deixado vivo (Ctrl+C encerra e
     restaura)
  10. Restaura os arquivos de seed e reporta o resumo

Os arquivos de seed (data/users.json, dados/departamentos.dat,
dados/cargos.dat, dados/funcionarios.dat) são restaurados ao final, então é
seguro rodar localmente. Não rode com outro servidor usando os mesmos dados/
simultaneamente.

Uso:
    python3 scripts/run_ci.py             # suíte completa (passos 1–8 + 10)
    python3 scripts/run_ci.py --no-build  # pula a recompilação do COBOL
    python3 scripts/run_ci.py --browser   # adiciona o passo 9: valida os
                                          # cenários visuais das abas
                                          # Complementar (4 complementares
                                          # C/V/F/P na porta 8141) e Rescisão
                                          # (2 rescisões — 1 EM DOBRO + 1
                                          # normal — na porta 8142), subindo
                                          # cada cenário, conferindo o seed via
                                          # HTTP e encerrando com restauração
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import cobol_bridge  # noqa: E402
import jsonio  # noqa: E402

SMOKES = [
    "smoke_jsonio",
    "smoke_rfc002_cobol",
    "smoke_rfc003_rescisao",
    "smoke_rfc003_bloqueios",
    "smoke_rfc004_eventos",
    "smoke_rfc005_tabelas",
    "smoke_rfc006_folha",
    "smoke_rfc007_holerite",
    "smoke_rfc008_empresa",
    "smoke_rfc010_011_ferias_decimo",
    "smoke_rfc012_afastamentos",
    "smoke_rfc013_complementar",
    "smoke_rfc014_encargos",
    "smoke_rfc009_auditoria",
]

SEED_FILES = [
    "data/users.json",
    "dados/departamentos.dat",
    "dados/cargos.dat",
    "dados/funcionarios.dat",
    "dados/folha_auditoria.jsonl",
]
SEED_BACKUP = "/tmp/becrp_ci_seed_backup"

PASS = 0
FAIL = 0


def step(title):
    print(f"\n{'─' * 60}\n▶ {title}\n{'─' * 60}")


def run(cmd, **kw):
    """Roda um comando herdando a saída; devolve o exit code."""
    return subprocess.run(cmd, cwd=ROOT, **kw).returncode


def _http_get(url, token=None):
    """GET com timeout curto; devolve (status, dict) sem estourar o CI."""
    req = urllib.request.Request(url)
    if token:
        req.add_header("X-Auth-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw)
            except ValueError:
                return r.status, {}
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception:
        return None, {}


def _cenario_visual(script, port, token, path, valida):
    """Sobe um cenario_*_browser.py em background, valida o seed via HTTP e
    encerra com SIGTERM (o script restaura os dados). `valida` recebe o dict
    do GET <path> e devolve bool. Modo opcional --browser. Em falha, imprime
    o tail do log do cenário (arquivo em /tmp, fora do backup que é varrido)."""
    proc = None
    logf = None
    try:
        logf = open(os.path.join("/tmp", f"ci_cenario_{script}.log"), "w")
        proc = subprocess.Popen(
            [sys.executable, "-B", os.path.join("scripts", script),
             "--port", str(port)],
            cwd=ROOT, stdout=logf, stderr=subprocess.STDOUT)
        # aguarda o servidor subir (o script seeda depois de servir)
        up = False
        for _ in range(45):
            if proc.poll() is not None:
                break
            code, _d = _http_get(f"http://127.0.0.1:{port}/api/auth/check-setup")
            if code == 200:
                up = True
                break
            time.sleep(1)
        if not up:
            print(f"  ❌ {script}: servidor não subiu em {port} "
                  f"(exit {proc.poll()})")
            _print_cenario_log(logf, script)
            return False
        # o seed roda DEPOIS do check-setup (servidor no ar) — faz poll do GET
        # até o valida() passar ou estourar o tempo (seed leva ~1-3s)
        ok = False
        for _ in range(30):
            if proc.poll() is not None:
                break
            code, data = _http_get(f"http://127.0.0.1:{port}{path}", token=token)
            if code == 200 and valida(data):
                ok = True
                break
            time.sleep(1)
        if not ok:
            exit_c = proc.poll()
            code, data = _http_get(f"http://127.0.0.1:{port}{path}", token=token)
            chave = path.rstrip("/").split("/")[-1]
            print(f"  ❌ {script}: seed não validado (HTTP {code}, exit "
                  f"{exit_c}, {chave}={len(data.get(chave, []))})")
            _print_cenario_log(logf, script)
            return False
        print(f"  ✅ {script}: seed validado via HTTP")
        return True
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
        if logf is not None:
            logf.close()


def _print_cenario_log(logf, script):
    """Imprime as últimas linhas do log do cenário em falha (ajuda a ver a
    causa: usuário não criado, COBOL errando no seed, porta ocupada etc.)."""
    try:
        logf.flush()
        with open(os.path.join("/tmp", f"ci_cenario_{script}.log"),
                  encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        if lines:
            print("  ↪ log do cenário (tail):")
            for line in lines[-10:]:
                print(f"      {line}")
    except OSError:
        pass


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
    # RFC-009 §4.2/Decisão 4 (separação de funções): o CI precisa de DOIS
    # usuários — quem opera (abre/calcula) não pode fechar. O review da tela
    # usa 'bruno' para operar e 'aprovador' para validar/fechar.
    users = {
        "bruno": {
            "usuario": "bruno",
            "nome": "Bruno CI",
            "email": "bruno@ci.local",
            "senha": hashlib.sha256(b"123456").hexdigest(),
            "role": "admin",
            "empresas": {},
            "ativo": True,
            "token": "ci-token-becrp-2026",
        },
        "aprovador": {
            "usuario": "aprovador",
            "nome": "Aprovador CI",
            "email": "aprovador@ci.local",
            "senha": hashlib.sha256(b"654321").hexdigest(),
            "role": "admin",
            "empresas": {},
            "ativo": True,
            "token": "ci-token-aprovador-2026",
        },
        # RFC-009 §4.2 (Tesouraria): quem registra o pagamento não pode ser o
        # Aprovador da competência. O CI usa 'tesouraria' para pagar.
        "tesouraria": {
            "usuario": "tesouraria",
            "nome": "Tesouraria CI",
            "email": "tesouraria@ci.local",
            "senha": hashlib.sha256(b"123123").hexdigest(),
            "role": "admin",
            "empresas": {},
            "ativo": True,
            "token": "ci-token-tesouraria-2026",
        },
    }
    jsonio.save("data/users.json", users)
    # remove a trilha de auditoria de execuções anteriores (gerada em runtime)
    try:
        os.remove(os.path.join(ROOT, "dados/folha_auditoria.jsonl"))
    except OSError:
        pass
    # Idempotente: se o registro CI já existe (ex.: .dat restaurado de um
    # snapshot com o seed antigo), reusa em vez de falhar com
    # "codigo ja cadastrado".
    deps = cobol_bridge.departamentos_listar()
    dep_ci = next((d for d in deps if d.get("codigo") == "CI"), None)
    did = dep_ci["id"] if dep_ci else cobol_bridge.departamento_incluir({
        "codigo": "CI", "descricao": "CI Pipeline",
        "centro_custo": "CC-CI", "responsavel": "CI"})
    cargos = cobol_bridge.cargos_listar()
    cargo_ci = next((c for c in cargos if c.get("codigo") == "CI"), None)
    cid = cargo_ci["id"] if cargo_ci else cobol_bridge.cargo_incluir({
        "codigo": "CI", "descricao": "CI Cargo",
        "cbo": "0000-00", "salario_referencia": "3000.00"})
    funcs_existentes = cobol_bridge.funcionarios_listar()
    func_ci = next((f for f in funcs_existentes if f.get("usuario") == "ci.func"), None)
    if func_ci:
        fid = func_ci["id"]
    else:
        fid = cobol_bridge.funcionario_incluir({
            "nome": "CI FUNCIONARIO", "usuario": "ci.func",
            "senha": "x123", "cpf": "000.111.222-33",  # exclusivo: smokes usam 999.888.777-66
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
    print(f"  ✅ seed: admin bruno/123456 + aprovador/654321 + tesouraria/123123 (RFC-009) · departamento #{did} · cargo #{cid} · funcionário #{fid}")


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

    step("2. Seed (admin + funcionário ativo)")
    backup_seed()
    try:
        try:
            seed()
        except Exception as e:
            FAIL += 1
            print(f"  ❌ seed: {e}")
            return finalize()  # o finally restaura

        # Seed antes dos smokes: vários smokes (ex.: rescisão) exigem
        # funcionário ativo, que não existe em um checkout limpo de CI.
        step("3. Smokes (RFC + jsonio)")
        for name in SMOKES:
            code = run([sys.executable, "-B", os.path.join("scripts", name + ".py")])
            if code == 0:
                PASS += 1
                print(f"  └─ ✅ {name}")
            else:
                FAIL += 1
                print(f"  └─ ❌ {name} (exit {code})")

        step("4. Review da tela Processar Folha + Holerites")
        code = run([sys.executable, "scripts/review_tela_folha.py", "--port", "8137"])
        if code == 0:
            PASS += 1
            print("  └─ ✅ review_tela_folha")
        else:
            FAIL += 1
            print(f"  └─ ❌ review_tela_folha (exit {code})")

        step("5. Review da tela Funcionários (máscaras CPF/moeda)")
        code = run([sys.executable, "scripts/review_tela_funcionarios.py", "--port", "8138"])
        if code == 0:
            PASS += 1
            print("  └─ ✅ review_tela_funcionarios")
        else:
            FAIL += 1
            print(f"  └─ ❌ review_tela_funcionarios (exit {code})")

        step("6. Review da tela Férias e 13º (RFC-010/011)")
        code = run([sys.executable, "scripts/review_tela_ferias_decimo.py", "--port", "8139"])
        if code == 0:
            PASS += 1
            print("  └─ ✅ review_tela_ferias_decimo")
        else:
            FAIL += 1
            print(f"  └─ ❌ review_tela_ferias_decimo (exit {code})")

        step("7. Check do render — badges VENCIDA/EM DOBRO, alertas e wrapper (Node)")
        node_bin = shutil.which("node")
        if not node_bin:
            # CI Python puro: sem node os checks são pulados (e não contam no
            # resumo); node está pré-instalado nos runners do GitHub Actions
            print("  ↪ node não encontrado — checks de render pulados "
                  "(instale node para ativá-los)")
        else:
            for check_js in ("check_render_ferias_node.js",
                             "check_render_rescisao_node.js",
                             "check_render_rh_dashboard_node.js",
                             "check_render_rh_workflow_node.js",
                             "check_render_complementar_node.js"):
                try:
                    r = subprocess.run(
                        [node_bin, os.path.join("scripts", check_js)],
                        cwd=ROOT, capture_output=True, text=True, timeout=60)
                except subprocess.TimeoutExpired:
                    FAIL += 1
                    print(f"  └─ ❌ {check_js} (timeout 60s)")
                    continue
                out = (r.stdout + r.stderr).strip()
                if r.returncode == 0:
                    PASS += 1
                    ultima = out.splitlines()[-1] if out else "RENDER OK"
                    print(f"  └─ ✅ {check_js} — {ultima}")
                else:
                    FAIL += 1
                    print(f"  └─ ❌ {check_js} (exit {r.returncode})")
                    print(out[-600:])

        step("8. Review do RH Dashboard (férias vencidas + aprovações + workflow)")
        code = run([sys.executable, "scripts/review_tela_rh_dashboard.py", "--port", "8140"])
        if code == 0:
            PASS += 1
            print("  └─ ✅ review_tela_rh_dashboard")
        else:
            FAIL += 1
            print(f"  └─ ❌ review_tela_rh_dashboard (exit {code})")

        # Modo opcional --browser: valida os cenários visuais das abas
        # Complementar e Rescisão (os mesmos usados com browser-use para
        # conferência em navegador real).
        if "--browser" in sys.argv:
            step("9. Cenários visuais das abas Complementar e Rescisão "
                 "(--browser, opcional)")

            def _valida_complementares(data):
                comps = data.get("complementares", []) if isinstance(data, dict) else []
                situacoes = {str(c.get("situacao")) for c in comps}
                ok = len(comps) >= 4 and {"C", "V", "F", "P"} <= situacoes
                if not ok:
                    print(f"  ↪ esperado 4 complementares C/V/F/P; veio "
                          f"{len(comps)} ({sorted(situacoes)})")
                return ok

            def _valida_rescisoes(data):
                resc = data.get("rescisoes", []) if isinstance(data, dict) else []
                tem_dobro = any(r.get("ferias_venc_dobro") is True for r in resc)
                tem_normal = any(r.get("ferias_venc_dobro") is False for r in resc)
                ok = len(resc) >= 2 and tem_dobro and tem_normal
                if not ok:
                    print(f"  ↪ esperado 2 rescisões (1 EM DOBRO + 1 normal); "
                          f"veio {len(resc)} (dobro={tem_dobro}, normal={tem_normal})")
                return ok

            cenarios = (
                ("cenario_complementar_browser.py", 8141,
                 "tok-visual-comp", "/api/folha/complementares",
                 _valida_complementares),
                ("cenario_rescisao_browser.py", 8142,
                 "tok-visual-resc", "/api/folha/rescisoes",
                 _valida_rescisoes),
            )
            for script, porta, token, path, valida in cenarios:
                if _cenario_visual(script, porta, token, path, valida):
                    PASS += 1
                    print(f"  └─ ✅ {script}")
                else:
                    FAIL += 1
                    print(f"  └─ ❌ {script}")
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
