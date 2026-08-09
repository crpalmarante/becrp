#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Revisão automatizada da tela 'Processar Folha' e 'Holerites' (RFC-006/007).

Sobe o servidor local em uma porta dedicada, replica EXATAMENTE o fluxo dos
botões da tela via HTTP e confere o resultado em cada etapa:

  Tela e assets
    - páginas servidas (/ e /pages/folha.html) e CSS resolvido (../css/style.css)
    - abas 'Processar' e 'Holerites' e o JS do fluxo presentes na página
    - /api/folha/* exige autenticação (403 sem token)
  Aba Processar
    - abrir competência (duplicada bloqueada)
    - calcular funcionário com INSS/IRRF conferidos contra a referência Python
      (a mesma usada no smoke do RFC-006): base INSS = salário + extras + DSR;
      base IRRF = base INSS − INSS − dep×ded; líquido = prov − desc
    - concluir → competência listada como calculada; detalhe com as bases
  Aba Holerites
    - gerar a partir do processamento → lista (FGTS = 8% do salário base)
    - detalhes (bases de cálculo + componentes) e salvar observações
    - guards de estado: pagar holerite exige folha fechada; excluir holerite
      já pago é bloqueado

Isolamento: backup/restauração de dados/folhas.dat, folhas.tmp,
folha_config.dat, holerites.dat e holerites.tmp; o servidor é encerrado ao
final. Não rode com outro servidor usando os mesmos dados/ simultaneamente.

Autenticação: tenta o login real (--usuario/--senha, padrão bruno/123456) e,
se falhar, usa o token do primeiro admin/instrutor em data/users.json.

Uso:
    python3 scripts/review_tela_folha.py [--port 8137]
    python3 scripts/review_tela_folha.py --port 8137 --usuario bruno --senha 123456
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge  # noqa: E402  (para ler a config da folha após o seed do servidor)

FILES = (
    "dados/folhas.dat",
    "dados/folhas.tmp",
    "dados/folha_config.dat",
    "dados/holerites.dat",
    "dados/holerites.tmp",
)
BACKUP = "/tmp/becrp_review_folha_backup"

PORT = 8137

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


# --------------------------------------------------------------------------
# Backup/restauração (mesmo padrão dos smokes RFC-003/004/006/007)
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
    """Retorna (http_status, dict_json). data é bytes; ctype define o Content-Type.

    Corpo não-JSON (ex.: HTML) preserva o status HTTP e devolve {}.
    """
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
    except Exception as e:  # conexão recusada/timeout de verdade
        return None, {"_erro": str(e)}
    try:
        return status, (json.loads(raw) if raw.strip() else {})
    except ValueError:  # corpo não-JSON (HTML) — mantém o status
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
    """Token do primeiro admin/instrutor (ou qualquer usuário) em data/users.json."""
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
# Referências Python do INSS/IRRF (cópias do smoke RFC-006)
# --------------------------------------------------------------------------
def inss_progressivo(base, cfg):
    """Referência Python do INSS progressivo por faixa (RFC-005 §2)."""
    tetos = [cfg["inss_f1_teto"], cfg["inss_f2_teto"],
             cfg["inss_f3_teto"], cfg["inss_f4_teto"]]
    aliqs = [cfg["inss_f1_aliq"], cfg["inss_f2_aliq"],
             cfg["inss_f3_aliq"], cfg["inss_f4_aliq"]]
    total = 0.0
    anterior = 0.0
    for teto, aliq in zip(tetos, aliqs):
        limite = min(base, teto) - anterior
        if limite > 0:
            total += limite * aliq / 100
        if base <= teto:
            break
        anterior = teto
    return round(total, 2)


def irrf_calcular(base_irrf, cfg):
    """Referência Python do IRRF (RFC-005 §3): alíquota da faixa − dedução."""
    if base_irrf <= cfg["irrf_f1_teto"]:
        return 0.0
    faixas = [
        (cfg["irrf_f2_teto"], cfg["irrf_f2_aliq"], cfg["irrf_f2_ded"]),
        (cfg["irrf_f3_teto"], cfg["irrf_f3_aliq"], cfg["irrf_f3_ded"]),
        (cfg["irrf_f4_teto"], cfg["irrf_f4_aliq"], cfg["irrf_f4_ded"]),
        (float("inf"), cfg["irrf_f5_aliq"], cfg["irrf_f5_ded"]),
    ]
    for teto, aliq, ded in faixas:
        if base_irrf <= teto:
            v = round(base_irrf * aliq / 100 - ded, 2)
            return max(v, 0.0)
    return 0.0


def main():
    global PORT
    args = sys.argv[1:]
    PORT = 8137
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
        # estado limpo do processamento (o backup guarda o original)
        for rel in ("dados/folhas.dat", "dados/folhas.tmp",
                    "dados/holerites.dat", "dados/holerites.tmp"):
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                os.remove(p)

        log = open(os.path.join(BACKUP, "server.log"), "w")
        proc = subprocess.Popen([sys.executable, "server.py", str(PORT)],
                                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        up = False
        for _ in range(40):
            if proc.poll() is not None:
                break  # o processo morreu — reporta o log abaixo
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
        code, _ = _get("/pages/folha.html")
        check("GET /pages/folha.html → 200", code == 200, code)
        code, _ = _get("/css/style.css")
        check("GET /css/style.css → 200 (CSS resolvido)", code == 200, code)
        html = _text("/pages/folha.html")
        check("folha.html tem aba 'Processar'", "Processar" in html)
        check("folha.html tem aba 'Holerites'", "Holerites" in html)
        check("folha.html usa ../css/style.css", 'href="../css/style.css"' in html)
        check("JS do fluxo presente (apiFolha + renderFuncsFolha)",
              "apiFolha" in html and "renderFuncsFolha" in html)
        check("filtro de ativos case-insensitive (situacao_vinculo)",
              "toLowerCase" in html and "situacao_vinculo" in html)
        refs = re.findall(r'(?:src|href)="([^"]+)"', html)
        locais = [r for r in refs
                  if r.strip() and not r.startswith(("http", "#", "mailto:", "data:", "javascript:"))]
        faltando = []
        for ref in locais:
            url = urllib.parse.urljoin("/pages/folha.html", ref)
            c, _ = _get(url)
            if c is None or c >= 400:
                faltando.append(f"{ref} → {c}")
        check("assets locais de folha.html sem 404", not faltando, "; ".join(faltando[:5]))

        print("\n2. Autenticação")
        code, _ = _get("/api/folha/competencias")
        check("GET /api/folha/competencias sem token → 403", code == 403, code)
        dev_token = _token_dev()
        check("token de dev disponível em data/users.json", bool(dev_token))
        login_token = None
        body = json.dumps({"usuario": usuario, "senha": senha}).encode("utf-8")
        code, data = _req("POST", "/api/auth/login", data=body, ctype="application/json")
        login_token = data.get("token")
        check(f"login UI ({usuario}/{senha}) → token",
              code == 200 and bool(login_token), f"{code} {data}")
        # O login rotaciona o token (save_users). Se a resposta se perder por
        # qualquer motivo, o token de dev lido antes fica stale — relê agora.
        token = login_token or _token_dev() or dev_token
        if not token:
            print("\nERRO: sem token de autenticação")
            print(f"\nResultado: {PASS} ✅  {FAIL} ❌")
            return 1

        print("\n3. Aba Processar — abrir competência")
        comp = "2026/08"
        code, data = _post_form("/api/folha/competencia/abrir", token, {"competencia": comp})
        check("abrir 2026/08 → ok", code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, data = _post_form("/api/folha/competencia/abrir", token, {"competencia": comp})
        dup = (data.get("status") == "error"
               and "existe" in str(data.get("message", "")).lower())
        check("abrir duplicada → bloqueado ('já existe')",
              code in (200, 400) and dup, f"{code} {data}")

        print("\n4. Aba Processar — calcular (INSS/IRRF de verdade)")
        code, data = _get("/api/funcionarios", token=token)
        funcs = data if isinstance(data, list) else (
            data.get("funcionarios", data.get("data", [])))
        ativos = [f for f in funcs
                  if str(f.get("situacao_vinculo", "") or "").lower() in ("ativo", "a", "")]
        check("existe ≥1 funcionário ativo para a tela listar",
              len(ativos) > 0, f"{len(ativos)} ativo(s) em {len(funcs)}")
        if not ativos:
            print(f"\nResultado: {PASS} ✅  {FAIL} ❌")
            return 1
        fid = ativos[0].get("id")
        nome = ativos[0].get("nome") or f"Func {fid}"
        cfg = cobol_bridge.folha_config_ler()  # já seedada pelo servidor
        sal, he, dsr, dep = 3000.00, 200.00, 33.33, 0
        base_inss = round(sal + he + dsr, 2)
        exp_inss = inss_progressivo(base_inss, cfg)
        exp_base_irrf = round(base_inss - exp_inss - dep * cfg["irrf_ded_dep"], 2)
        exp_irrf = irrf_calcular(exp_base_irrf, cfg)
        code, r = _post_form("/api/folha/competencia/calcular", token, {
            "competencia": comp, "funcionario_id": fid, "nome": nome,
            "salario_base": sal, "horas_extras": he, "dsr": dsr,
            "faltas": 0, "dependentes": dep, "outros_proventos": 0,
            "outros_descontos": 0,
        })
        check("calcular → ok", code == 200 and r.get("status") == "ok", f"{code} {r}")
        check("proventos = salário + extras + DSR",
              quase(r.get("proventos"), base_inss), r.get("proventos"))
        check("INSS progressivo confere com a referência",
              quase(r.get("inss"), exp_inss), f"{r.get('inss')} vs {exp_inss}")
        check("base IRRF = base INSS − INSS − dep×ded",
              quase(r.get("base_irrf"), exp_base_irrf),
              f"{r.get('base_irrf')} vs {exp_base_irrf}")
        check("IRRF (faixa − dedução) confere com a referência",
              quase(r.get("irrf"), exp_irrf), f"{r.get('irrf')} vs {exp_irrf}")
        check("total descontos = INSS + IRRF",
              quase(r.get("total_descontos"), r.get("inss", 0) + r.get("irrf", 0)), r)
        check("líquido = proventos − descontos",
              quase(r.get("liquido"), r.get("proventos", 0) - r.get("total_descontos", 0)), r)

        print("\n5. Aba Processar — concluir e estado")
        code, data = _post_form("/api/folha/competencia/concluir", token, {"competencia": comp})
        check("concluir → ok", code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, data = _get("/api/folha/competencias", token=token)
        comps = data.get("competencias", [])
        linha = next((c for c in comps if str(c.get("competencia", "")) == comp), None)
        check("competência 2026/08 listada", linha is not None,
              [c.get("competencia") for c in comps])
        check("situação = C (calculada)",
              linha is not None and str(linha.get("situacao", "")) == "C", linha)
        code, data = _get("/api/folha/competencia?competencia=" + urllib.parse.quote(comp),
                          token=token)
        ffuncs = data.get("funcionarios", [])
        det = next((f for f in ffuncs if str(f.get("funcionario_id")) == str(fid)), None)
        check("detalhe mostra funcionário com bases", det is not None, ffuncs)
        if det:
            check("detalhe: base INSS confere", quase(det.get("base_inss"), base_inss), det)
            check("detalhe: líquido confere com o calcular",
                  quase(det.get("liquido"), r.get("liquido")), det)

        print("\n6. Aba Holerites — gerar, detalhes, observações")
        code, data = _post_form("/api/folha/holerite/gerar", token, {"competencia": comp})
        check("gerar holerites → ok", code == 200 and data.get("status") == "ok",
              f"{code} {data}")
        check("gerados = 1 (funcionário calculado)", data.get("gerados") == 1, data)
        code, data = _get("/api/folha/holerites", token=token)
        hs = [h for h in data.get("holerites", []) if h.get("competencia") == comp]
        check("lista tem 1 holerite de 2026/08", len(hs) == 1, f"{len(hs)}")
        if hs:
            h = hs[0]
            check("holerite: FGTS = 8% do salário base",
                  quase(h.get("fgts"), round(0.08 * sal, 2)), h.get("fgts"))
            check("holerite: líquido = líquido da folha",
                  quase(h.get("liquido"), r.get("liquido")), h.get("liquido"))
            check("holerite: situação C (calculado)",
                  str(h.get("situacao", "")) == "C", h.get("situacao"))
            hid = h.get("id")
            code, det = _get(f"/api/folha/holerite/detalhes?id={hid}", token=token)
            bases = det.get("bases", {})
            check("detalhes: bases de cálculo presentes",
                  quase(bases.get("salario"), sal)
                  and quase(bases.get("base_inss"), base_inss)
                  and quase(bases.get("fgts"), round(0.08 * sal, 2)),
                  bases)
            check("detalhes: componentes detalhados",
                  len(det.get("componentes", [])) > 0,
                  f"{len(det.get('componentes', []))}")
            code, d = _post_form("/api/folha/holerite/detalhes/salvar", token,
                                 {"id": hid, "observacoes": "Revisão automatizada da tela"})
            check("salvar observações → ok", code == 200 and d.get("status") == "ok",
                  f"{code} {d}")
            code, det2 = _get(f"/api/folha/holerite/detalhes?id={hid}", token=token)
            check("observações salvas aparecem no detalhe",
                  str(det2.get("observacoes", "")).strip() == "Revisão automatizada da tela",
                  det2)

            print("\n7. Guards de holerite (estado)")
            code, d = _post_form("/api/folha/holerite/pagar", token,
                                 {"id": hid, "data_pagamento": "2026-08-10"})
            check("pagar holerite com folha em C → bloqueado",
                  d.get("status") == "error", f"{code} {d}")
            code, d = _post_form("/api/folha/competencia/validar", token,
                                 {"competencia": comp})
            check("validar folha → ok", code == 200 and d.get("status") == "ok",
                  f"{code} {d}")
            code, d = _post_form("/api/folha/competencia/fechar", token,
                                 {"competencia": comp})
            check("fechar folha → ok", code == 200 and d.get("status") == "ok",
                  f"{code} {d}")
            code, d = _post_form("/api/folha/holerite/pagar", token,
                                 {"id": hid, "data_pagamento": "2026-08-10"})
            check("pagar holerite com folha fechada → ok",
                  code == 200 and d.get("status") == "ok", f"{code} {d}")
            code, d = _post_form("/api/folha/holerite/excluir", token, {"id": hid})
            check("excluir holerite PAGO → bloqueado",
                  d.get("status") == "error", f"{code} {d}")

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
