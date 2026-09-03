#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cenário visual da aba Rescisão (RFC-003) — sobe o servidor em porta
dedicada com 2 rescisões seedadas via API e mantém vivo para inspeção com
browser-use/navegador. Restaura os dados ao encerrar.

Uso:
    python3 scripts/cenario_rescisao_browser.py [--port 8192] [--no-seed]
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PORT = 8192
BACKUP = "/tmp/becrp_visual_resc"

FILES = (
    "dados/rescisoes.dat",
    "dados/rescisoes.tmp",
    "dados/funcionarios.dat",
    "dados/folha_auditoria.jsonl",
    "data/users.json",
)


def _backup():
    os.makedirs(BACKUP, exist_ok=True)
    for rel in FILES:
        src = os.path.join(ROOT, rel)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(BACKUP, os.path.basename(rel)))
        else:
            open(os.path.join(BACKUP, os.path.basename(rel) + ".nao-existia"), "w").close()


def _restore():
    for rel in FILES:
        dst = os.path.join(ROOT, rel)
        bak = os.path.join(BACKUP, os.path.basename(rel))
        marker = bak + ".nao-existia"
        if os.path.exists(bak):
            shutil.copy2(bak, dst)
        elif os.path.exists(marker) and os.path.exists(dst):
            os.remove(dst)
    shutil.rmtree(BACKUP, ignore_errors=True)


def _req(method, path, token=None, data=None):
    url = f"http://127.0.0.1:{PORT}{path}"
    req = urllib.request.Request(url, method=method, data=data)
    if token:
        req.add_header("X-Auth-Token", token)
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {}
    except Exception as e:
        return None, {"_erro": str(e)}


def _post(path, token, campos):
    body = urllib.parse.urlencode(campos).encode("utf-8")
    return _req("POST", path, token=token, data=body)


def _get(path, token=None):
    return _req("GET", path, token=token)


def _garantir_usuarios():
    path = os.path.join(ROOT, "data", "users.json")
    users = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            users = json.load(f)
    senha = hashlib.sha256(b"123456").hexdigest()
    users.setdefault("bruno", {
        "usuario": "bruno", "nome": "Bruno Visual", "senha": senha,
        "role": "admin", "ativo": True, "empresas": {},
    })
    for uid, u in users.items():
        u.setdefault("senha", senha)
        u.setdefault("role", "admin")
        u.setdefault("ativo", True)
        u.setdefault("empresas", {})
    # token fixo do seed visual — o folha.html injeta via localStorage
    users["bruno"]["token"] = "tok-visual-resc"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    return "tok-visual-resc"


def _garantir_funcionarios():
    """Cria 2 funcionários ativos dedicados ao cenário (a rescisão desliga o
    funcionário, então cada rescisão precisa do seu próprio)."""
    import cobol_bridge

    def _existe(marca):
        for f in cobol_bridge.funcionarios_listar():
            if str(f.get("usuario") or "").strip() == marca:
                return f.get("id")
        return None

    out = {}
    for marca, nome, cpf, sal in (
        ("review.resc1", "Joao Rescisao Dobro", "111.222.333-44", 3000.00),
        ("review.resc2", "Ana Rescisao Normal", "555.666.777-88", 2500.00),
    ):
        fid = _existe(marca)
        if fid is None:
            fid = cobol_bridge.funcionario_incluir({
                "nome": nome, "usuario": marca, "senha": "x123",
                "cpf": cpf, "data_nasc": "1988-05-05", "sexo": "M",
                "nacionalidade": "brasileira", "endereco": "Rua Visual, 5",
                "cep": "99000000", "cidade": "Passo Fundo", "uf": "RS",
                "ctps": "3333333", "data_adm": "2026-01-05",
                "salario": str(sal), "departamento_id": "1", "cargo_id": "1",
                "forma_pagamento": "mensal", "situacao_vinculo": "ativo",
            })
        out[marca] = (fid, nome, sal)
    return out


def _seed(token, funcs):
    """Cria 2 rescisões: uma com férias vencidas EM DOBRO (Calculado) e uma
    sem vencidas (Paga) — o contraste mostra o badge só na linha certa."""
    def incluir(func, motivo, venc_dias, sal):
        fid, nome, _s = funcs[func]
        return _post("/api/folha/rescisao/incluir", token, {
            "funcionario_id": fid, "nome": nome, "motivo": motivo,
            "data_desligamento": "2026-08-08", "tipo_aviso": "indenizado",
            "dias_aviso": 33, "saldo_dias": 8,
            "ferias_vencidas_dias": venc_dias, "ferias_proporcionais_meses": 6,
            "13_meses": 7, "salario_base": sal,
        })

    st1, r1 = incluir("review.resc1", "sem-justa-causa", 30, 3000.00)   # EM DOBRO
    st2, r2 = incluir("review.resc2", "pedido-demissao", 0, 2500.00)    # normal
    ids = [x.get("id") for x in (r1, r2) if x.get("id")]
    if len(ids) >= 2:
        _post("/api/folha/rescisao/pagar", token, {
            "id": ids[1], "data_pagamento": "2026-08-08"})
    return ids, r1, r2


def _main():
    global PORT
    no_seed = False
    args = sys.argv[1:]
    if "--port" in args:
        PORT = int(args[args.index("--port") + 1])
    if "--no-seed" in args:
        no_seed = True

    _backup()
    proc = None
    log = None

    def _sair_limpo(_sig, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _sair_limpo)
    try:
        for rel in ("dados/rescisoes.dat", "dados/rescisoes.tmp"):
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                os.remove(p)
        if not no_seed:
            token = _garantir_usuarios()
            funcs = _garantir_funcionarios()
        else:
            token = "tok-visual-resc"

        log = open(os.path.join(BACKUP, "server.log"), "w")
        proc = subprocess.Popen([sys.executable, "-B", "server.py", str(PORT)],
                                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        up = False
        for _ in range(40):
            if proc.poll() is not None:
                break
            code, _d = _get("/api/auth/check-setup")
            if code == 200:
                up = True
                break
            time.sleep(1)
        if not up or proc.poll() is not None:
            log.flush()
            print("ERRO: servidor não subiu. Log:")
            print(open(os.path.join(BACKUP, "server.log")).read()[-2000:])
            return 1

        if not no_seed:
            ids, r1, r2 = _seed(token, funcs)
            print(f"  ✅ seed: 2 rescisoes — #{ids[0]} EM DOBRO (Calculado) "
                  f"+ #{ids[1]} normal (Paga)")
            print(f"      r1 dobro={r1.get('ferias_venc_dobro')} "
                  f"liquido={r1.get('liquido')}")
            print(f"      r2 dobro={r2.get('ferias_venc_dobro')} "
                  f"liquido={r2.get('liquido')}")
        print()
        print("=" * 60)
        print(f"SERVIDOR VIVO em http://localhost:{PORT}/  (Ctrl+C encerra)")
        print("Login: bruno / 123456")
        print(f"Página: http://localhost:{PORT}/pages/folha.html")
        print()
        print("Checagens visuais esperadas (browser-use / manual):")
        print("  1) Aba Rescisao → tabela com 2 linhas:")
        print("     - #1 motivo 'Sem justa causa', coluna Ferias com o badge")
        print("       vermelho 'EM DOBRO' (title: 'Ferias vencidas pagas em")
        print("       dobro'), situacao 'Calculado', botoes Pagar/Excluir")
        print("     - #2 motivo 'Pedido demissao', SEM badge EM DOBRO,")
        print("       situacao 'Pago', apenas botao Excluir")
        print("  2) Selecionar o funcionario #1 no form (Férias Vencidas")
        print("     default 30) e clicar 'Calcular e Registrar' → toast")
        print("     laranja 'ALERTA: ferias vencidas em DOBRO na rescisao!'")
        print("     e o resumo (summary-grid) mostra o badge EM DOBRO ao")
        print("     lado de 'Ferias' com valores em dobro")
        print("=" * 60)
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nEncerrando e restaurando dados...")
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        if log is not None:
            log.close()
        _restore()
    return 0


if __name__ == "__main__":
    sys.exit(_main())
