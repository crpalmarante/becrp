#!/usr/bin/env python3
"""Smoke E2E dos bloqueios da RFC-003 na camada HTTP (server.py).

Cobre:
  - §3.4.1: data de demissão bloqueia novos processamentos na folha —
    /api/folha/competencia/calcular rejeita funcionário desligado (400).
  - §2.3.3: exame admissional vencido bloqueia a admissão —
    /api/funcionario/incluir rejeita exame_adm_venc anterior à data de
    admissão (400); exame válido é aceito.

Sobe o servidor em porta dedicada, seeda um funcionário completo, executa os
fluxos e restaura os arquivos de seed no final (mesmo padrão dos reviews).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge  # noqa: E402

FILES = (
    "dados/funcionarios.dat",
    "dados/departamentos.dat",
    "dados/cargos.dat",
    "dados/folhas.dat",
    "dados/folhas.tmp",
    "data/users.json",
)
BACKUP = "/tmp/becrp_rfc003_bloqueios_backup"

PORT = 8141

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
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        status = e.code
    except Exception as e:
        return None, {"_erro": str(e)}
    try:
        return status, (json.loads(raw) if raw.strip() else {})
    except ValueError:
        return status, {}


def _post_form(path, token, campos):
    body = urllib.parse.urlencode(campos).encode("utf-8")
    return _req("POST", path, token=token, data=body)


def _token_dev():
    try:
        with open(os.path.join(ROOT, "data", "users.json"), encoding="utf-8") as f:
            users = json.load(f)
        items = users.items() if isinstance(users, dict) else [
            (u.get("usuario"), u) for u in users]
        for _k, v in items:
            if v.get("role") in ("admin", "instrutor") and v.get("token"):
                return v["token"]
    except Exception:
        pass
    return None


def _seed_funcionario_completo():
    """Reusa departamento/cargo existentes ou cria; cria um funcionário
    completo (evita o bloqueio RFC-002 §3.2 no calcular)."""
    deps = cobol_bridge.departamentos_listar()
    did = next((d.get("id") for d in deps if d.get("codigo") == "CI"), None)
    if not did:
        did = cobol_bridge.departamento_incluir({
            "codigo": "CI", "descricao": "CI Bloqueios",
            "centro_custo": "CC-BLOQ", "responsavel": "CI"})
    cars = cobol_bridge.cargos_listar()
    cid = next((c.get("id") for c in cars if c.get("codigo") == "CI"), None)
    if not cid:
        cid = cobol_bridge.cargo_incluir({
            "codigo": "CI", "descricao": "CI Bloqueios",
            "cbo": "0000-00", "salario_referencia": "3000.00"})
    fid = cobol_bridge.funcionario_incluir({
        "nome": "BLOQUEIO RFC003", "usuario": "bloq.rfc003",
        "senha": "x123", "cpf": "888.777.666-55",
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
    return fid


def _login(usuario, senha):
    body = json.dumps({"usuario": usuario, "senha": senha}).encode("utf-8")
    code, data = _req("POST", "/api/auth/login", data=body)
    token = data.get("token")
    if code == 200 and token:
        return token
    return _token_dev()


def main():
    _backup()
    proc = None
    log = None
    try:
        log = open(os.path.join(BACKUP, "server.log"), "w")
        proc = subprocess.Popen([sys.executable, "server.py", str(PORT)],
                                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        up = False
        for _ in range(40):
            if proc.poll() is not None:
                break
            code, _data = _req("GET", "/api/auth/check-setup")
            if code == 200:
                up = True
                break
            time.sleep(1)
        check("servidor sobe (check-setup 200)", up and proc.poll() is None)
        if not up or proc.poll() is not None:
            log.flush()
            print("\nERRO: servidor não subiu. Log:")
            print(open(os.path.join(BACKUP, "server.log")).read()[-2000:])
            print(f"\nResultado: {PASS} ✅  {FAIL} ❌")
            return 1 if FAIL else 0

        token = _login("bruno", "123456")
        check("login admin → token", bool(token))
        if not token:
            return 1 if FAIL else 0

        print("\n1. RFC-003 §3.4.1 — desligado bloqueia processamento")
        fid = _seed_funcionario_completo()
        check("seed funcionário completo", fid > 0)
        # a tela lista via GET /api/funcionarios (token)
        _code, data = _req("GET", "/api/funcionarios", token=token)
        funcs = data.get("funcionarios", []) if isinstance(data, dict) else []
        fobj = next((f for f in funcs if str(f.get("id")) == str(fid)), None)
        check("funcionário listado", fobj is not None)

        code, r = _post_form("/api/folha/competencia/abrir", token,
                             {"competencia": "2026/08"})
        check("abrir 2026/08 → ok", code in (200, 400) and r.get("status") == "ok",
              f"{code} {r}")
        code, r = _post_form("/api/folha/competencia/calcular", token, {
            "competencia": "2026/08", "funcionario_id": fid,
            "salario_base": 3000.00})
        check("calcular ativo → ok", code == 200 and r.get("status") == "ok",
              f"{code} {r}")

        code, r = _post_form("/api/funcionarios/desligar", token, {
            "id": fid, "data_dem": "2026-08-08", "motivo": "sem-justa-causa"})
        check("desligar → ok", code == 200 and r.get("status") == "ok", f"{code} {r}")

        code, r = _post_form("/api/folha/competencia/calcular", token, {
            "competencia": "2026/08", "funcionario_id": fid,
            "salario_base": 3000.00})
        check("calcular desligado → 400 bloqueado (§3.4.1)",
              code == 400 and "desligado" in str(r.get("message", "")).lower(),
              f"{code} {r}")

        code, r = _post_form("/api/funcionarios/reativar", token, {"id": fid})
        check("reativar → ok", code == 200 and r.get("status") == "ok", f"{code} {r}")

        print("\n2. RFC-003 §2.3.3 — exame admissional vencido bloqueia admissão")
        base = {
            "nome": "EXAME VENCIDO", "usuario": "exame.vencido",
            "senha": "x123", "cpf": "444.333.222-11",
            "data_adm": "2026-08-09",
        }
        code, r = _post_form("/api/funcionario/incluir", token,
                             {**base, "exame_adm_venc": "2026-01-01"})
        check("exame vencido (antes da admissão) → 400 (§2.3.3)",
              code == 400 and "exame" in str(r.get("message", "")).lower(),
              f"{code} {r}")

        code, r = _post_form("/api/funcionario/incluir", token,
                             {**base, "cpf": "444.333.222-12",
                              "exame_adm_venc": "2026-12-01"})
        check("exame válido (depois da admissão) → ok",
              code == 200 and r.get("status") == "ok", f"{code} {r}")

        code, r = _post_form("/api/funcionario/incluir", token,
                             {**base, "cpf": "444.333.222-13"})
        check("sem exame informado → aceito (política não bloqueia)",
              code == 200 and r.get("status") == "ok", f"{code} {r}")

        print(f"\n{'=' * 50}\nResultado: {PASS} ok / {FAIL} falhas\n{'=' * 50}")
        return 1 if FAIL else 0
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
        if log:
            log.close()
        _restore()


if __name__ == "__main__":
    sys.exit(main())
