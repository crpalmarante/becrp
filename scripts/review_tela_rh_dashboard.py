#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Revisão automatizada do RH Dashboard (pages/rh_dashboard.html).

Sobe o servidor local em porta dedicada e replica o fluxo da tela via HTTP:

  Tela e assets
    - /pages/rh_dashboard.html servida, CSS resolvido, assets sem 404
    - wrapper de fetch injetando X-Auth-Token (AuthService/localStorage)
  Autenticação
    - /api/rh/dashboard, licencas/despesas/timesheets e workflow exigem token
  Dashboard
    - KPIs numéricos (funcionários, folha/INSS/IRRF/FGTS, holerites a pagar)
    - ALERTA de férias vencidas (RFC-010 Decisão 4): funcionário com período
      concessivo expirado sem gozo → 1 alerta por período; cobrir com registro
      de férias reduz o alerta
  Aprovações
    - licenças pendentes (COBOL) e despesas pendentes (dados/despesas.json)
    - aprovar licença/despesa → sai da lista de pendentes
  Workflow
    - definitions (licenca/despesa), history, transition com validação de role
      (role não autorizada → 403) e gravação do histórico

Isolamento: backup/restauração de users.json, funcionarios.dat, licencas.dat,
licencas.tmp, timesheets.dat, timesheets.tmp, despesas.json,
workflow_history.json, ferias.dat e ferias.tmp; servidor encerrado ao final.
Não rode com outro servidor usando os mesmos dados/ simultaneamente.

Uso:
    python3 scripts/review_tela_rh_dashboard.py [--port 8140]
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge  # noqa: E402
import despesas_store  # noqa: E402

FILES = (
    "data/users.json",
    "dados/funcionarios.dat",
    "dados/licencas.dat",
    "dados/licencas.tmp",
    "dados/timesheets.dat",
    "dados/timesheets.tmp",
    "dados/despesas.json",
    "dados/workflow_history.json",
    "dados/ferias.dat",
    "dados/ferias.tmp",
)
BACKUP = "/tmp/becrp_review_rh_backup"

PORT = 8140
TOKEN = "ci-token-rh-dashboard-2026"

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


def quase(a, b, tol=0.01):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def _add_months(d, months):
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    import calendar
    dia = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, dia)


def _concessivos_expirados(data_adm, hoje):
    """Quantos períodos aquisitivos já tiveram o concessivo vencido em `hoje`.

    Espelha a regra do servidor (_ferias_vencidas_alertas) para a asserção
    não depender da data em que o CI roda."""
    y, m, d = int(data_adm[0:4]), int(data_adm[5:7]), int(data_adm[8:10])
    ini = date(y, m, d)
    n = 0
    for _ in range(15):
        fim = _add_months(ini, 12) - timedelta(days=1)
        if _add_months(fim, 12) >= hoje:
            break
        n += 1
        ini = _add_months(ini, 12)
    return n


# --------------------------------------------------------------------------
# Backup/restauração (mesmo padrão dos demais reviews)
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _req(method, path, token=None, data=None, ctype="application/x-www-form-urlencoded"):
    url = f"http://127.0.0.1:{PORT}{path}"
    req = urllib.request.Request(url, method=method, data=data)
    if token:
        req.add_header("X-Auth-Token", token)
    if data is not None:
        req.add_header("Content-Type", ctype)
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


def _get(path, token=None):
    return _req("GET", path, token=token)


def _post_form(path, token, campos):
    body = urllib.parse.urlencode(campos).encode("utf-8")
    return _req("POST", path, token=token, data=body)


def _text(path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=10) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return ""


def _assets_ok(html, base):
    """Assets locais (sem http) resolvem sem 404 (urljoin normaliza ../)."""
    faltando = []
    for m in re.findall(r'(?:src|href)="([^"#]+)"', html):
        u = urllib.parse.urljoin(base, m)
        if u.startswith(("http", "data:", "javascript:", "mailto:")):
            continue
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{u}", timeout=10):
                pass
        except Exception:
            faltando.append(u)
    return faltando


def _seed_admin():
    """Garante um admin com token fixo (users.json é restaurado ao final)."""
    import hashlib
    path = os.path.join(ROOT, "data", "users.json")
    users = {}
    try:
        with open(path, encoding="utf-8") as f:
            users = json.load(f)
    except (ValueError, OSError):
        users = {}
    if not isinstance(users, dict):
        users = {}
    users["ci.rh"] = {
        "usuario": "ci.rh",
        "nome": "CI RH",
        "senha": hashlib.sha256(b"x").hexdigest(),
        "role": "admin",
        "empresas": {},
        "ativo": True,
        "token": TOKEN,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def main():
    global PORT
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            PORT = int(args[i + 1])
            i += 2
        else:
            i += 1

    _backup()
    proc = None
    log = None
    try:
        # usuário admin de teste (users.json volta no restore)
        _seed_admin()
        # funcionário dedicado: admissão antiga gera férias vencidas no alerta
        fid = cobol_bridge.funcionario_incluir({
            "nome": "RH Dashboard CI", "usuario": "rh.dash.ci",
            "senha": "x", "cpf": "333.444.555-66",
            "data_nasc": "1990-01-01", "sexo": "M",
            "nacionalidade": "Brasileira", "endereco": "Rua CI, 1",
            "cep": "01000-000", "cidade": "Sao Paulo", "uf": "SP",
            "ctps": "90002", "ctps_serie": "1", "ctps_uf": "SP",
            "data_adm": "2023-01-05", "salario": "3000.00",
            "forma_pagamento": "Mensalista", "banco": "BB",
            "agencia": "0001", "conta": "12346",
            "vt_optante": "S",
        })
        # licenças enviadas para aprovação (status S): 1ª testa o endpoint
        # direto; 2ª fica disponível para a transição do workflow (seção 8)
        lid = cobol_bridge.licenca_incluir({
            "funcionario_id": fid, "tipo": "Medica",
            "data_inicio": "2026-08-01", "data_fim": "2026-08-05",
            "dias": 5, "motivo": "Atestado", "status": "S"})
        lid2 = cobol_bridge.licenca_incluir({
            "funcionario_id": fid, "tipo": "Paternidade",
            "data_inicio": "2026-08-10", "data_fim": "2026-08-15",
            "dias": 5, "motivo": "Nascimento", "status": "S"})
        # despesas enviadas para aprovação (status S): idem
        desp = despesas_store.incluir({
            "funcionario_id": fid, "data": "2026-08-01",
            "categoria": "Transporte", "descricao": "Uber", "valor": 120.50})
        did = desp["id"]
        desp2 = despesas_store.incluir({
            "funcionario_id": fid, "data": "2026-08-02",
            "categoria": "Alimentacao", "descricao": "Almoco", "valor": 45.90})
        did2 = desp2["id"]
        # timesheet
        cobol_bridge.timesheet_incluir({
            "funcionario_id": fid, "data": "2026-08-05", "projeto": "RH CI",
            "tarefa": "Dashboard", "horas": "2.5", "descricao": "Revisao"})

        log = open(os.path.join(BACKUP, "server.log"), "w")
        proc = subprocess.Popen([sys.executable, "server.py", str(PORT)],
                                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        up = False
        for _ in range(40):
            if proc.poll() is not None:
                break
            code, _data = _get("/api/auth/check-setup")
            if code == 200:
                up = True
                break
            time.sleep(1)
        check("servidor sobe (check-setup 200)", up and proc.poll() is None)
        if not up or proc.poll() is not None:
            log.flush()
            print(open(os.path.join(BACKUP, "server.log")).read()[-2000:])
            return 1

        print("\n1. Tela e assets")
        code, _ = _get("/pages/rh_dashboard.html")
        check("GET /pages/rh_dashboard.html → 200", code == 200, code)
        html = _text("/pages/rh_dashboard.html")
        check("página tem o título do RH Dashboard", "RH Dashboard" in html)
        check("wrapper de fetch injeta X-Auth-Token",
              "X-Auth-Token" in html and "auth_token" in html)
        check("JS do fluxo presente (carregarDashboard/carregarAprovacoes)",
              "carregarDashboard" in html and "carregarAprovacoes" in html)
        code, _ = _get("/css/style.css")
        check("GET /css/style.css → 200 (CSS resolvido)", code == 200, code)
        faltando = _assets_ok(html, "/pages/")
        check("assets locais de rh_dashboard.html sem 404",
              not faltando, "; ".join(faltando[:5]))

        print("\n2. Autenticação")
        for p in ("/api/rh/dashboard", "/api/licencas/pendentes",
                  "/api/despesas/pendentes", "/api/timesheets",
                  "/api/workflow/definitions"):
            code, _ = _get(p)
            check(f"GET {p} sem token → 403", code == 403, code)

        print("\n3. Dashboard — KPIs e alerta de férias vencidas (RFC-010)")
        code, r = _get("/api/rh/dashboard", token=TOKEN)
        check("GET /api/rh/dashboard → ok", code == 200 and r.get("status") == "ok",
              f"{code} {r}")
        d = r.get("dashboard") or {}
        check("total_funcionarios ≥ 1", (d.get("total_funcionarios") or 0) >= 1,
              d.get("total_funcionarios"))
        for k in ("folha_total", "inss_total", "irrf_total", "fgts_total"):
            check(f"KPI {k} é numérico", isinstance(d.get(k), (int, float)), d.get(k))
        alertas = [a for a in (d.get("alertas_contrato") or [])
                   if str(a.get("funcionario_id")) == str(fid)]
        esperados = _concessivos_expirados("2023-01-05", date.today())
        check(f"funcionário antigo tem {esperados} alerta(s) de férias vencidas",
              len(alertas) == esperados, f"{len(alertas)} alertas: {alertas}")
        if alertas:
            check("alerta: tipo = 'Ferias vencidas' (badge da tela)",
                  all(a.get("tipo") == "Ferias vencidas" for a in alertas))
            check("alerta: data do fim do concessivo preenchida",
                  all(a.get("data") for a in alertas))
            check("alerta: dias de atraso > 0", all((a.get("dias") or 0) > 0 for a in alertas))
            check("alerta: 1º período aquisitivo = admissão (2023-01-05)",
                  any(a.get("aquis_inicio") == "2023-01-05" for a in alertas))

        print("\n4. Cobertura por registro de férias (alerta some)")
        code, r = _post_form("/api/folha/ferias/incluir", TOKEN, {
            "funcionario_id": fid, "nome": "RH Dashboard CI",
            "periodo_inicio": "2023-01-05", "periodo_fim": "2024-01-04",
            "inicio_ferias": "2024-01-15", "fim_ferias": "2024-02-13",
            "dias": 30, "dias_abono": 0, "salario_base": 3000})
        check("incluir férias do 1º período → ok",
              code == 200 and r.get("status") == "ok", f"{code} {r}")
        code, r = _get("/api/rh/dashboard", token=TOKEN)
        alertas = [a for a in (r.get("dashboard") or {}).get("alertas_contrato") or []
                   if str(a.get("funcionario_id")) == str(fid)]
        check("coberto o 1º período → sobra N−1 alerta",
              len(alertas) == max(esperados - 1, 0), f"{len(alertas)} alertas")

        print("\n5. Licenças pendentes + aprovação")
        code, r = _get("/api/licencas/pendentes", token=TOKEN)
        pend = r.get("licencas") or []
        check("licença pendente listada (status S)",
              any(str(x.get("id")) == str(lid) and x.get("status") == "S" for x in pend),
              pend)
        code, r = _post_form("/api/licenca/aprovar", TOKEN, {"id": lid})
        check("aprovar licença → ok", code == 200 and r.get("status") == "ok",
              f"{code} {r}")
        code, r = _get("/api/licencas/pendentes", token=TOKEN)
        check("licença aprovada sai da lista de pendentes",
              all(str(x.get("id")) != str(lid) for x in (r.get("licencas") or [])))

        print("\n6. Despesas pendentes + aprovação")
        code, r = _get("/api/despesas/pendentes", token=TOKEN)
        pend = r.get("despesas") or []
        check("despesa pendente listada (status S)",
              any(str(x.get("id")) == str(did) and x.get("status") == "S" for x in pend),
              pend)
        code, r = _post_form("/api/despesa/aprovar", TOKEN, {"id": did})
        check("aprovar despesa → ok", code == 200 and r.get("status") == "ok",
              f"{code} {r}")
        code, r = _get("/api/despesas/pendentes", token=TOKEN)
        check("despesa aprovada sai da lista de pendentes",
              all(str(x.get("id")) != str(did) for x in (r.get("despesas") or [])))

        print("\n7. Timesheets")
        code, r = _get("/api/timesheets", token=TOKEN)
        ts = r.get("timesheets") or []
        check("timesheet do funcionário listado",
              any(str(x.get("funcionario_id")) == str(fid) for x in ts), ts)
        check("horas do timesheet > 0",
              any(str(x.get("funcionario_id")) == str(fid) and
                  (x.get("horas") or 0) > 0 for x in ts))

        print("\n8. Workflow — definitions, history e transições")
        code, r = _get("/api/workflow/definitions", token=TOKEN)
        wf = r.get("workflows") or {}
        check("definitions contém licenca e despesa",
              "licenca" in wf and "despesa" in wf, list(wf.keys()))
        code, r = _get(f"/api/workflow/history?module=licenca&record_id={lid2}",
                       token=TOKEN)
        check("history da licença começa vazio", len(r.get("entries") or []) == 0,
              r)
        code, r = _post_form("/api/workflow/transition", TOKEN, {
            "module": "licenca", "record_id": lid2, "target_status": "A",
            "user_name": "CI RH", "user_role": "rh"})
        check("transição licença S→A (role rh) → ok",
              code == 200 and r.get("status") == "ok", f"{code} {r}")
        code, r = _get(f"/api/workflow/history?module=licenca&record_id={lid2}",
                       token=TOKEN)
        entries = r.get("entries") or []
        check("history gravou a transição (S→A)",
              len(entries) == 1 and entries[0].get("to_status") == "A", entries)
        code, r = _post_form("/api/workflow/transition", TOKEN, {
            "module": "licenca", "record_id": lid2, "target_status": "C",
            "user_name": "Emp", "user_role": "employee"})
        check("transição com role não autorizada → 403",
              code == 403, f"{code} {r}")
        # segurança: usuário role 'funcionario' NÃO pode escalar enviando
        # user_role=admin — o servidor usa o papel real do usuário logado
        import hashlib
        users = json.load(open(os.path.join(ROOT, "data", "users.json"),
                               encoding="utf-8"))
        users["ci.func.user"] = {
            "usuario": "ci.func.user", "nome": "CI Func",
            "senha": hashlib.sha256(b"x").hexdigest(),
            "role": "funcionario", "empresas": {}, "ativo": True,
            "token": "ci-token-func-user"}
        json.dump(users, open(os.path.join(ROOT, "data", "users.json"), "w"),
                  ensure_ascii=False, indent=2)
        code, r = _post_form("/api/workflow/transition", "ci-token-func-user", {
            "module": "licenca", "record_id": lid2, "target_status": "C",
            "user_name": "Func", "user_role": "admin"})
        check("funcionario não escala via user_role=admin → 403",
              code == 403, f"{code} {r}")
        # despesa via workflow (transição S→A)
        code, r = _post_form("/api/workflow/transition", TOKEN, {
            "module": "despesa", "record_id": did2, "target_status": "A",
            "user_name": "CI RH", "user_role": "rh"})
        check("transição despesa S→A (role rh) → ok",
              code == 200 and r.get("status") == "ok", f"{code} {r}")
        code, r = _get("/api/despesas/pendentes", token=TOKEN)
        check("despesa transitada não está mais pendente",
              all(str(x.get("id")) != str(did2) for x in (r.get("despesas") or [])))

        print(f"\n{'=' * 52}")
        print(f"Resultado: {PASS} ✅  {FAIL} ❌")
        print(f"{'=' * 52}")
        return 0 if FAIL == 0 else 1
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


if __name__ == "__main__":
    sys.exit(main())
