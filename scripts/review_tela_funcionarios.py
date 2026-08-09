#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Revisão automatizada da tela 'Funcionários' (máscaras CPF/moeda).

Sobe o servidor local em uma porta dedicada e replica o fluxo da tela via HTTP:

  Tela e assets
    - /pages/funcionarios.html servida, CSS resolvido, masks.js incluído
    - campos monetários com data-mask="moeda" (type="text") e o f-pensao-valor
      preservado como type="number" (aceita percentual — não pode ser moeda)
    - envio do salário usa Mascaras.limparMoeda (payload numérico com ponto)
  Máscaras (unit, node)
    - funções puras do js/masks.js: fmtMoeda/limparMoeda (round-trip e
      idempotência), validarCPF/validarCNPJ (dígitos verificadores),
      fmtCPF/fmtCNPJ/fmtTel/fmtCEP
  CRUD via API (round-trip real das máscaras)
    - incluir funcionário com CPF MASCARADO (529.982.247-25) e salário
      "3000.00" (como a tela envia após limparMoeda) → COBOL aceita
    - incluir o mesmo CPF mascarado de novo → bloqueado (duplicidade normaliza)
    - listar devolve os valores; alterar (salário + celular mascarado) reflete;
      excluir remove

Isolamento: backup/restauração de dados/departamentos.dat, cargos.dat,
funcionarios.dat e dependentes.dat; o servidor é encerrado ao final.

Uso:
    python3 scripts/review_tela_funcionarios.py [--port 8138]
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FILES = (
    "dados/departamentos.dat",
    "dados/cargos.dat",
    "dados/funcionarios.dat",
    "dados/dependentes.dat",
)
BACKUP = "/tmp/becrp_review_func_backup"

PORT = 8138

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


# --------------------------------------------------------------------------
# Backup/restauração (mesmo padrão dos smokes/reviews)
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
# HTTP (idêntico ao review_tela_folha)
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


def _token_dev():
    try:
        with open(os.path.join(ROOT, "data", "users.json"), encoding="utf-8") as f:
            users = json.load(f)
        items = users.items() if isinstance(users, dict) else [
            (u.get("usuario"), u) for u in users]
        for _k, v in items:
            if v.get("role") in ("admin", "instrutor") and v.get("token"):
                return v["token"]
        for _k, v in items:
            if v.get("token"):
                return v["token"]
    except Exception:
        pass
    return None


# --------------------------------------------------------------------------
# Máscaras — testes unit nas funções puras do masks.js via node
# --------------------------------------------------------------------------
NODE_PROG = r"""
const M = require(process.argv[1]);
const r = [];
function c(n, ok) { r.push((ok ? 'PASS|' : 'FAIL|') + n); }
c('fmtMoeda 1500', M.fmtMoeda('1500') === 'R$ 15,00');
c('fmtMoeda 150000', M.fmtMoeda('150000') === 'R$ 1.500,00');
c('limparMoeda mascara', M.limparMoeda('R$ 1.500,00') === '1500.00');
c('limparMoeda idempotente', M.limparMoeda('1500.00') === '1500.00');
c('limparMoeda vazio', M.limparMoeda('') === '');
c('validarCPF ok', M.validarCPF('529.982.247-25') === true);
c('validarCPF repetido', M.validarCPF('111.111.111-11') === false);
c('validarCPF dv errado', M.validarCPF('529.982.247-24') === false);
c('validarCNPJ ok', M.validarCNPJ('11.444.777/0001-61') === true);
c('validarCNPJ dv errado', M.validarCNPJ('11.444.777/0001-62') === false);
c('fmtCPF', M.fmtCPF('12345678901') === '123.456.789-01');
c('fmtCNPJ', M.fmtCNPJ('12345678000190') === '12.345.678/0001-90');
c('fmtTel celular', M.fmtTel('11999999999') === '(11) 99999-9999');
c('fmtCEP', M.fmtCEP('13560220') === '13560-220');
console.log(r.join('\n'));
process.exit(r.some(x => x.startsWith('FAIL')) ? 1 : 0);
"""


def testar_mascaras_node():
    """Roda as funções puras do masks.js em node; retorna (ok, detalhe)."""
    masks = os.path.join(ROOT, "js", "masks.js")
    if not os.path.exists(masks):
        return False, "js/masks.js não encontrado"
    try:
        proc = subprocess.run(
            ["node", "-e", NODE_PROG, masks],
            capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return False, "node não disponível"
    linhas = (proc.stdout or "").strip().splitlines()
    n_pass = sum(1 for l in linhas if l.startswith("PASS|"))
    n_fail = sum(1 for l in linhas if l.startswith("FAIL|"))
    detalhe = f"{n_pass} ok · {n_fail} falhou" + (f"\n{proc.stderr[-500:]}" if proc.returncode and proc.stderr else "")
    return proc.returncode == 0 and n_fail == 0, detalhe


def main():
    global PORT
    args = sys.argv[1:]
    PORT = 8138
    usuario = "bruno"
    senha = "123456"
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            PORT = int(args[i + 1])
            i += 2
        elif args[i] == "--usuario" and i + 1 < len(args):
            usuario = args[i + 1]
            i += 2
        elif args[i] == "--senha" and i + 1 < len(args):
            senha = args[i + 1]
            i += 2
        else:
            i += 1

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
            code, _data = _get("/api/auth/check-setup")
            if code == 200:
                up = True
                break
            time.sleep(1)
        check("servidor sobe (check-setup 200)", up and proc.poll() is None)
        if not up or proc.poll() is not None:
            log.flush()
            print("\nERRO: servidor não subiu (ou morreu). Log:")
            print(open(os.path.join(BACKUP, "server.log")).read()[-2000:])
            print(f"\nResultado: {PASS} ✅  {FAIL} ❌")
            return 1

        print("\n1. Tela e assets")
        code, _ = _get("/")
        check("GET / → 200 (tela de login)", code == 200, code)
        code, _ = _get("/pages/funcionarios.html")
        check("GET /pages/funcionarios.html → 200", code == 200, code)
        code, _ = _get("/css/style.css")
        check("GET /css/style.css → 200 (CSS resolvido)", code == 200, code)
        code, _ = _get("/js/masks.js")
        check("GET /js/masks.js → 200 (máscaras servidas)", code == 200, code)
        html = _text("/pages/funcionarios.html")
        check("funcionarios.html inclui ../js/masks.js", "../js/masks.js" in html)
        check("funcionarios.html usa ../css/style.css", 'href="../css/style.css"' in html)
        fsal = re.search(r'<input[^>]*id="f-salario"[^>]*>', html)
        check("f-salario com data-mask=moeda e type=text",
              fsal is not None and 'data-mask="moeda"' in fsal.group(0)
              and 'type="text"' in fsal.group(0),
              fsal.group(0) if fsal else "input não encontrado")
        check("f-vt-desconto/f-vr/f-plano-saude-valor com data-mask=moeda",
              'id="f-vt-desconto" data-mask="moeda"' in html
              and 'id="f-vr" data-mask="moeda"' in html
              and 'id="f-plano-saude-valor" data-mask="moeda"' in html)
        pensao = re.search(r'<input[^>]*id="f-pensao-valor"[^>]*>', html)
        check("f-pensao-valor segue type=number (aceita %)",
              pensao is not None and 'type="number"' in pensao.group(0))
        check("envio do salário usa Mascaras.limparMoeda",
              "Mascaras.limparMoeda(document.getElementById('f-salario')" in html)
        refs = re.findall(r'(?:src|href)="([^"]+)"', html)
        # ignora strings JS concatenadas e placeholders conhecidos não versionados
        locais = [r for r in refs
                  if r.strip() and "'" not in r and "$" not in r
                  and not r.startswith(("http", "#", "mailto:", "data:", "javascript:"))
                  and r not in ("/img/sem-foto.png",)]
        faltando = []
        for ref in locais:
            url = urllib.parse.urljoin("/pages/funcionarios.html", ref)
            c, _ = _get(url)
            if c is None or c >= 400:
                faltando.append(f"{ref} → {c}")
        check("assets locais de funcionarios.html sem 404", not faltando, "; ".join(faltando[:5]))

        print("\n2. Autenticação")
        # /api/funcionarios é rota pública (o front lista sem token);
        # o check de 403 usa uma rota protegida (mesma do review_tela_folha).
        code, _ = _get("/api/folha/competencias")
        check("GET /api/folha/competencias sem token → 403", code == 403, code)
        dev_token = _token_dev()
        check("token de dev disponível em data/users.json", bool(dev_token))
        body = json.dumps({"usuario": usuario, "senha": senha}).encode("utf-8")
        code, data = _req("POST", "/api/auth/login", data=body, ctype="application/json")
        login_token = data.get("token")
        check(f"login UI ({usuario}/{senha}) → token",
              code == 200 and bool(login_token), f"{code} {data}")
        token = login_token or _token_dev() or dev_token
        if not token:
            print("\nERRO: sem token de autenticação")
            print(f"\nResultado: {PASS} ✅  {FAIL} ❌")
            return 1

        print("\n3. Máscaras — unit (node, funções puras do js/masks.js)")
        node_ok, node_detalhe = testar_mascaras_node()
        check("máscaras (node): fmtMoeda/limparMoeda/validarCPF/CNPJ/fmt*",
              node_ok, node_detalhe)

        print("\n4. CRUD via API — round-trip das máscaras")
        base = {
            "nome": "REVIEW MASCARA", "usuario": "review.mascara",
            "senha": "x123", "permissoes": "operador",
            "cpf": "529.982.247-25",  # mascarado, como digitado na tela
            "data_nasc": "1990-01-01", "data_adm": "2026-01-05",
            "salario": "3000.00",  # como a tela envia após limparMoeda
        }
        code, data = _post_form("/api/funcionario/incluir", token, base)
        fid = data.get("id")
        check("incluir com CPF mascarado + salário numérico → ok",
              code == 200 and data.get("status") == "ok" and fid, f"{code} {data}")
        if not fid:
            print(f"\nResultado: {PASS} ✅  {FAIL} ❌")
            return 1
        code, data = _post_form("/api/funcionario/incluir", token, base)
        dup = data.get("status") == "error" and "cadastrado" in str(data.get("message", ""))
        check("mesmo CPF mascarado de novo → bloqueado (duplicidade normaliza)",
              code in (200, 400) and dup, f"{code} {data}")
        code, data = _get("/api/funcionarios", token=token)
        funcs = data.get("funcionarios", [])
        novo = next((f for f in funcs if str(f.get("id")) == str(fid)), None)
        check("lista contém o funcionário criado", novo is not None)
        if novo:
            check("cpf retornado = 529.982.247-25 (mascarado, PIC X(14))",
                  str(novo.get("cpf", "")).strip() == "529.982.247-25",
                  repr(novo.get("cpf")))
            check("salario retornado = 3000.00",
                  float(str(novo.get("salario", "0")).replace(",", ".")) == 3000.0,
                  novo.get("salario"))
        code, data = _post_form("/api/funcionario/alterar", token, {
            "id": fid, "salario": "3200.00", "celular": "(11) 99999-9999"})
        check("alterar (salário 3200 + celular mascarado) → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, data = _get("/api/funcionarios", token=token)
        novo = next((f for f in data.get("funcionarios", [])
                     if str(f.get("id")) == str(fid)), None)
        if novo:
            check("alteração reflete: salario 3200.00 e celular (11) 99999-9999",
                  float(str(novo.get("salario", "0")).replace(",", ".")) == 3200.0
                  and str(novo.get("celular", "")).strip() == "(11) 99999-9999",
                  f"salario={novo.get('salario')} celular={novo.get('celular')!r}")
        code, data = _post_form("/api/funcionario/excluir", token, {"id": fid})
        check("excluir → ok", code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, data = _get("/api/funcionarios", token=token)
        restantes = [f for f in data.get("funcionarios", [])
                     if str(f.get("id")) == str(fid)]
        check("funcionário de teste some da lista", not restantes)

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
