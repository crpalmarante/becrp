#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cenário visual da aba Complementar (RFC-013) — sobe o servidor em porta
dedicada com 4 complementares (C/V/F/P) seedadas via API e mantém vivo para
inspeção com browser-use/navegador. Restaura os dados ao encerrar.

Uso:
    python3 scripts/cenario_complementar_browser.py [--port 8191] [--no-seed]
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

PORT = 8191
BACKUP = "/tmp/becrp_visual_comp"

FILES = (
    "dados/complementar.dat",
    "dados/complementar.tmp",
    "dados/funcionarios.dat",
    "dados/folha_config.dat",
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
    users.setdefault("rh2", {
        "usuario": "rh2", "nome": "RH Aprovador", "senha": senha,
        "role": "instrutor", "ativo": True, "empresas": {},
    })
    for uid, u in users.items():
        u.setdefault("senha", senha)
        u.setdefault("role", "admin" if uid == "bruno" else "instrutor")
        u.setdefault("ativo", True)
        u.setdefault("empresas", {})
    # token fixo do seed visual — o folha.html injeta via localStorage
    users["bruno"]["token"] = "tok-visual-comp"
    users["rh2"]["token"] = "tok-visual-comp-rh2"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    return "tok-visual-comp", "tok-visual-comp-rh2"


def _garantir_funcionario():
    import cobol_bridge
    for f in cobol_bridge.funcionarios_listar():
        if str(f.get("usuario") or "").strip() == "review.comp":
            return f.get("id"), float(f.get("salario") or 0)
    fid = cobol_bridge.funcionario_incluir({
        "nome": "Maria Complementar",
        "usuario": "review.comp",
        "senha": "x123",
        "cpf": "333.444.555-66",
        "data_nasc": "1991-03-03",
        "sexo": "F",
        "nacionalidade": "brasileira",
        "endereco": "Rua Visual, 3",
        "cep": "99000000",
        "cidade": "Passo Fundo",
        "uf": "RS",
        "ctps": "2222222",
        "data_adm": "2025-03-10",
        "salario": "3000.00",
        "departamento_id": "1",
        "cargo_id": "1",
        "forma_pagamento": "mensal",
        "situacao_vinculo": "ativo",
    })
    return fid, 3000.00


def _seed(token, token2, fid):
    """Cria 4 complementares — uma em cada estado do fluxo (C/V/F/P)."""
    def incluir(motivo, valor):
        st, r = _post("/api/folha/complementar/incluir", token, {
            "funcionario_id": fid, "competencia": "2026/07",
            "competencia_ref": "2026/06", "motivo": motivo, "valor": valor,
        })
        return r.get("id")

    c1 = incluir("hora extra nao lancada", "500.00")          # C
    c2 = incluir("erro de calculo", "350.00")                 # -> V
    c3 = incluir("diferenca de tabela", "280.00")             # -> F
    c4 = incluir("erro comprovado", "-120.00")                # -> P (negativa)
    ids = [x for x in (c1, c2, c3, c4) if x]

    if len(ids) >= 2:
        _post("/api/folha/complementar/validar", token, {"id": c2})
    if len(ids) >= 3:
        _post("/api/folha/complementar/validar", token, {"id": c3})
        _post("/api/folha/complementar/fechar", token2, {"id": c3})
    if len(ids) >= 4:
        _post("/api/folha/complementar/validar", token, {"id": c4})
        _post("/api/folha/complementar/fechar", token2, {"id": c4})
        _post("/api/folha/complementar/pagar", token, {"id": c4,
                                                       "data_pagamento": "2026-08-06"})
    return ids


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
        for rel in ("dados/complementar.dat", "dados/complementar.tmp"):
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                os.remove(p)
        if not no_seed:
            token, token2 = _garantir_usuarios()
            fid, _sal = _garantir_funcionario()
        else:
            token = "tok-visual-comp"

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
            _seed(token, token2, fid)
            print("  ✅ seed: 4 complementares (C/V/F/P) + funcionario review.comp")
        print()
        print("=" * 60)
        print(f"SERVIDOR VIVO em http://localhost:{PORT}/  (Ctrl+C encerra)")
        print("Login: bruno / 123456")
        print(f"Página: http://localhost:{PORT}/pages/folha.html")
        print()
        print("Checagens visuais esperadas (browser-use / manual):")
        print("  1) Aba Complementar → tabela com 4 linhas:")
        print("     - #1 CALCULADA (+500) com botões Validar/Holerite/Excluir")
        print("     - #2 VALIDADA  (+350) com botões Fechar/Holerite/Excluir")
        print("     - #3 FECHADA   (+280) com botões Pagar/Holerite/Excluir")
        print("     - #4 PAGA      (-120, vermelho) com botão Holerite apenas")
        print("  2) Clicar em 'Holerite' da linha #4 → modal 'Holerite")
        print("     Complementar #4' exibindo apenas as diferenças")
        print("     (competencia_ref 2026/06, motivo, valor/INSS/IRRF/liquido)")
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
