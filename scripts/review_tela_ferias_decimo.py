#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Revisão automatizada das abas 'Férias' e '13o Salario' (RFC-010/011).

Sobe o servidor local em uma porta dedicada, replica EXATAMENTE o fluxo dos
botões das abas via HTTP e confere o resultado em cada etapa:

  Tela e assets
    - páginas servidas (/ e /pages/folha.html) e CSS resolvido (../css/style.css)
    - abas 'Ferias' e '13o Salario' e o JS do fluxo presentes na página
    - /api/folha/ferias e /api/folha/decimos exigem autenticação (403 sem token)
  Aba Férias
    - calcular: base = salário/30 × dias; +1/3 constitucional; abono com 1/3
      próprio; INSS/IRRF progressivos das tabelas da config sobre o total
      (conferidos contra a referência Python, mesma usada no smoke RFC-010)
    - incluir (o botão da tela) → listagem com situação C → pagar → situação P
      → excluir → lista volta a ficar vazia
    - férias vencidas (RFC-010 Decisão 4): gozo após aquis_fim + 12 meses →
      vencida=true, alerta e salário em dobro (1/3/abono na base normal), na
      listagem e no cálculo; gozo no último dia do concessivo não é vencida
  Aba 13o Salario
    - calcular 1ª parcela (sem descontos), 2ª parcela e única (com INSS/IRRF)
      conferidos contra a referência Python (RFC-011 §3.1/§3.2)
    - incluir → listar → pagar → excluir (mesmo ciclo da tela)
  Validações e segurança
    - funcionário/dias/parcela/meses/abono (guardas do COBOL, RFC-010 §5)
    - role 'funcionario' (portal): incluir só o próprio vínculo (salário sempre
      do cadastro), 403 para outro vínculo e para os demais endpoints

Isolamento: backup/restauração de dados/ferias.dat, ferias.tmp, decimo.dat,
decimo.tmp, funcionarios.dat e data/users.json (o portal cria usuário de teste);
o servidor é encerrado ao final. Não rode com outro servidor usando os mesmos
dados/ simultaneamente.

Autenticação: tenta o login real (--usuario/--senha, padrão bruno/123456) e,
se falhar, usa o token do primeiro admin/instrutor em data/users.json.

Uso:
    python3 scripts/review_tela_ferias_decimo.py [--port 8139]
    python3 scripts/review_tela_ferias_decimo.py --port 8139 --usuario bruno --senha 123456
    python3 scripts/review_tela_ferias_decimo.py --port 8139 --browser
        (sobe o servidor com férias VENCIDA + normal gravadas e fica servindo
        para conferir o badge VENCIDA e o toast em navegador real — use com o
        agente browser-use ou manualmente; Ctrl+C restaura os dados)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
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

import cobol_bridge  # noqa: E402  (para ler a config da folha e achar/ criar funcionários)

FILES = (
    "dados/ferias.dat",
    "dados/ferias.tmp",
    "dados/decimo.dat",
    "dados/decimo.tmp",
    "dados/funcionarios.dat",
    "data/users.json",
)
BACKUP = "/tmp/becrp_review_ferias_decimo_backup"

PORT = 8139

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
# Backup/restauração (mesmo padrão dos smokes RFC-003/004/006/007/010/011)
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
# Referências Python do INSS/IRRF (cópias do smoke RFC-006) e do RFC-010/011
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


def ref_ferias(cfg, sal, dias, dias_abono=0, vencida=False):
    """Espelho Python do calcular-ferias (RFC-010): base = sal/30 × dias;
    +1/3; abono com 1/3 próprio; INSS/IRRF sobre o total.

    vencida (RFC-010 Decisão 4): só o salário dobra; 1/3 e abono seguem
    na base normal (decisão de produto).

    O COBOL guarda ws-salario-dia em PIC 9(7)V99 (trunca para 2 casas)
    antes de multiplicar — espelhamos a truncagem para valores não exatos."""
    sal_dia = int(sal / 30 * 100) / 100
    base_normal = round(sal_dia * dias, 2)
    valor_base = round(base_normal * 2, 2) if vencida else base_normal
    um_terco = round(base_normal / 3, 2)
    abono = round(sal_dia * dias_abono, 2)
    abono_terco = round(abono / 3, 2)
    bruto = round(valor_base + um_terco + abono + abono_terco, 2)
    inss = inss_progressivo(bruto, cfg)
    base_irrf = max(bruto - inss, 0.0)
    irrf = irrf_calcular(base_irrf, cfg)
    liquido = round(bruto - inss - irrf, 2)
    return dict(valor_base=valor_base, um_terco=um_terco, abono=abono,
                abono_terco=abono_terco, bruto=bruto, inss=inss, irrf=irrf,
                liquido=liquido)


def ref_decimo(cfg, sal, meses, parcela):
    """Espelho Python do calcular-decimo (RFC-011): base = sal/12 × meses;
    1ª parcela sem descontos; 2ª/única com INSS/IRRF."""
    valor_base = round(sal / 12 * meses, 2)
    if str(parcela) == "1":
        inss = irrf = 0.0
    else:
        inss = inss_progressivo(valor_base, cfg)
        irrf = irrf_calcular(max(valor_base - inss, 0.0), cfg)
    liquido = round(valor_base - inss - irrf, 2)
    return dict(valor_base=valor_base, inss=inss, irrf=irrf, liquido=liquido)


def _funcionario_por_usuario(usuario):
    for f in cobol_bridge.funcionarios_listar():
        if str(f.get("usuario") or "").strip() == usuario:
            return f
    return None


def _garantir_funcionario_ativo():
    """Garante ≥1 funcionário ativo no funcionarios.dat (cria se não houver)."""
    ativos = [f for f in cobol_bridge.funcionarios_listar()
              if str(f.get("situacao_vinculo", "") or "").lower()
              in ("ativo", "a", "")]
    if not ativos:
        cobol_bridge.funcionario_incluir({
            "nome": "CI Review Ferias", "usuario": "review.ferias",
            "senha": "x123", "permissoes": "operador",
            "cpf": "000.111.222-66",  # exclusivo do review
            "data_nasc": "1990-01-01", "data_adm": "2026-01-05",
            "salario": 3000.00})
        ativos = [f for f in cobol_bridge.funcionarios_listar()
                  if str(f.get("situacao_vinculo", "") or "").lower()
                  in ("ativo", "a", "")]
    return ativos


# --------------------------------------------------------------------------
# Modo --browser: sobe o servidor com um cenário visual (férias VENCIDA +
# normal) e mantém vivo para inspeção em navegador real (browser-use/manual).
# --------------------------------------------------------------------------
def _modo_browser():
    """Sobe o servidor com férias VENCIDA + normal já gravadas e fica servindo
    até Ctrl+C — para conferir o badge VENCIDA e o toast em navegador real.

    Prints URL, credenciais e as checagens visuais esperadas. Restaura os
    dados ao encerrar (mesmo backup do modo HTTP).
    """
    _backup()
    proc = None
    log = None

    def _sair_limpo(_sig, _frame):
        # SIGTERM (kill) deve encerrar o server.py filho e restaurar os dados
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _sair_limpo)
    try:
        for rel in ("dados/ferias.dat", "dados/ferias.tmp",
                    "dados/decimo.dat", "dados/decimo.tmp"):
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                os.remove(p)
        _garantir_funcionario_ativo()
        # admin bruno/123456 para o login da tela (se não existir no users.json)
        users_path = os.path.join(ROOT, "data", "users.json")
        users = {}
        if os.path.exists(users_path):
            with open(users_path, encoding="utf-8") as f:
                users = json.load(f)
        bruno = next((u for u in users.values()
                      if u.get("usuario") == "bruno"), None)
        if bruno is None:
            users["bruno"] = {
                "usuario": "bruno", "nome": "Bruno Visual",
                "senha": hashlib.sha256(b"123456").hexdigest(),
                "role": "admin", "empresas": {}, "ativo": True,
                "token": "tok-visual-becrp",
            }
        else:
            # login visual confiável: garante a senha do banner (e role admin)
            bruno["senha"] = hashlib.sha256(b"123456").hexdigest()
            bruno.setdefault("role", "admin")
            bruno.setdefault("ativo", True)
            bruno.setdefault("empresas", {})
        # token fixo do seed visual — sem ele as chamadas de seed dão 403 e
        # nenhuma férias é criada (o login real rotaciona o token depois)
        bruno["token"] = "tok-visual-becrp"
        with open(users_path, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

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
        if not up or proc.poll() is not None:
            log.flush()
            print("\nERRO: servidor não subiu (ou morreu). Log:")
            print(open(os.path.join(BACKUP, "server.log")).read()[-2000:])
            return 1

        # seed visual via API (mesmo fluxo da tela): uma férias VENCIDA e uma
        # normal, para o badge aparecer já na primeira carga da lista
        token = "tok-visual-becrp"
        code, data = _get("/api/funcionarios", token=token)
        funcs = data.get("funcionarios", []) if isinstance(data, dict) else []
        fid = next((f.get("id") for f in funcs
                    if str(f.get("usuario") or "").strip() == "review.ferias"),
                   None)
        fid = fid or (funcs[0].get("id") if funcs else None)
        if fid:
            # admissão 2026-01-05 → aquisitivo 1 = 2026-01-05..2027-01-04,
            # concessivo até 2028-01-04 → gozo 2028-02-01 é VENCIDA
            _post_form("/api/folha/ferias/incluir", token, {
                "funcionario_id": fid,
                "periodo_inicio": "2026-01-05", "periodo_fim": "2027-01-04",
                "inicio_ferias": "2028-02-01", "fim_ferias": "2028-03-01",
                "dias": 30, "dias_abono": 0, "salario_base": 3000})
            _post_form("/api/folha/ferias/incluir", token, {
                "funcionario_id": fid,
                "periodo_inicio": "2025-01-05", "periodo_fim": "2026-01-04",
                "inicio_ferias": "2026-08-01", "fim_ferias": "2026-08-30",
                "dias": 30, "dias_abono": 0, "salario_base": 3000})

        print("\n" + "=" * 60)
        print(f"SERVIDOR VIVO em http://localhost:{PORT}/  (Ctrl+C encerra)")
        print("Login: bruno / 123456")
        print(f"Página: http://localhost:{PORT}/pages/folha.html")
        print("\nChecagens visuais esperadas (browser-use / manual):")
        print("  1) Aba Férias → linha do gozo 2028-02-01 a 2028-03-01")
        print("     com o badge vermelho VENCIDA (tooltip: 'Gozo apos o fim")
        print("     do periodo concessivo - salario em dobro')")
        print("  2) Preencher o formulário (período aquisitivo 2026-01-05 a")
        print("     2027-01-04, gozo 2028-02-01 a 2028-03-01, 30 dias) e")
        print("     clicar em 'Registrar Ferias' → toast laranja 'ALERTA:")
        print("     ferias VENCIDAS registradas - salario em dobro!'")
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


def main():
    global PORT
    args = sys.argv[1:]
    PORT = 8139
    usuario = "bruno"
    senha = "123456"
    browser_mode = False
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
        elif args[i] == "--browser":
            browser_mode = True
            i += 1
        else:
            i += 1

    if browser_mode:
        return _modo_browser()

    _backup()
    proc = None
    log = None
    try:
        # estado limpo dos registros (o backup guarda o original)
        for rel in ("dados/ferias.dat", "dados/ferias.tmp",
                    "dados/decimo.dat", "dados/decimo.tmp"):
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                os.remove(p)
        # fora do CI não há funcionário seedado — cria um ativo (some no restore)
        _garantir_funcionario_ativo()

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
        check("folha.html tem aba 'Ferias'", "aba-ferias" in html and "Ferias" in html)
        check("folha.html tem aba '13o Salario'", "aba-decimo" in html and "13o Salario" in html)
        check("folha.html usa ../css/style.css", 'href="../css/style.css"' in html)
        check("JS do fluxo de férias presente (calcularFerias/carregarFerias)",
              "calcularFerias" in html and "carregarFerias" in html)
        check("JS do fluxo de 13º presente (calcularDecimo/carregarDecimos)",
              "calcularDecimo" in html and "carregarDecimos" in html)
        check("tabelas de listagem presentes (tabela-ferias/tabela-decimos)",
              'id="tabela-ferias"' in html and 'id="tabela-decimos"' in html)
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
        # o render do badge VENCIDA/toast/wrapper é validado pelo passo próprio
        # check_render_ferias_node.js no run_ci.py (passo 7) — não duplicar aqui

        print("\n2. Autenticação")
        code, _ = _get("/api/folha/ferias")
        check("GET /api/folha/ferias sem token → 403", code == 403, code)
        code, _ = _get("/api/folha/decimos")
        check("GET /api/folha/decimos sem token → 403", code == 403, code)
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

        print("\n3. Aba Férias — calcular (referência RFC-010)")
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
        # salário da fonte da verdade (cadastro COBOL), não do payload da tela
        try:
            sal = float(next(f for f in cobol_bridge.funcionarios_listar()
                             if str(f.get("id")) == str(fid)).get("salario") or 0)
            sal = sal or 3000.00
        except (StopIteration, TypeError, ValueError):
            sal = 3000.00
        cfg = cobol_bridge.folha_config_ler()  # já seedada pelo servidor
        ref = ref_ferias(cfg, sal, 30, 0)
        campos = {"funcionario_id": fid, "nome": nome,
                  "periodo_inicio": "2025-07-01", "periodo_fim": "2026-06-30",
                  "inicio_ferias": "2026-08-03", "fim_ferias": "2026-09-01",
                  "dias": 30, "dias_abono": 0, "salario_base": sal}
        code, r = _post_form("/api/folha/ferias/calcular", token, campos)
        check("calcular → ok", code == 200 and r.get("status") == "ok", f"{code} {r}")
        check("valor base = salário/30 × 30 dias",
              quase(r.get("valor_base"), ref["valor_base"]), r.get("valor_base"))
        check("1/3 constitucional",
              quase(r.get("um_terco"), ref["um_terco"]), r.get("um_terco"))
        check("INSS progressivo confere com a referência",
              quase(r.get("inss"), ref["inss"]), f"{r.get('inss')} vs {ref['inss']}")
        check("IRRF (bruto − INSS) confere com a referência",
              quase(r.get("irrf"), ref["irrf"]), f"{r.get('irrf')} vs {ref['irrf']}")
        check("líquido = bruto − INSS − IRRF",
              quase(r.get("liquido"), ref["liquido"]), f"{r.get('liquido')} vs {ref['liquido']}")

        print("\n3b. Férias com abono pecuniário (venda de 10 dias)")
        ref2 = ref_ferias(cfg, sal, 30, 10)
        code, r2 = _post_form("/api/folha/ferias/calcular", token,
                              {**campos, "dias_abono": 10})
        check("calcular com abono → ok",
              code == 200 and r2.get("status") == "ok", f"{code} {r2}")
        check("abono = 10 dias × salário/30",
              quase(r2.get("abono"), ref2["abono"]), r2.get("abono"))
        check("1/3 do abono",
              quase(r2.get("abono_terco"), ref2["abono_terco"]), r2.get("abono_terco"))
        check("bruto com abono",
              quase(r2.get("bruto"), ref2["bruto"]), f"{r2.get('bruto')} vs {ref2['bruto']}")
        check("INSS com abono",
              quase(r2.get("inss"), ref2["inss"]), f"{r2.get('inss')} vs {ref2['inss']}")
        check("líquido com abono",
              quase(r2.get("liquido"), ref2["liquido"]), f"{r2.get('liquido')} vs {ref2['liquido']}")

        print("\n3c. Férias vencidas — alerta + salário em dobro (RFC-010 Decisão 4)")
        # concessivo = aquis_fim + 12m = 2026-06-30 + 12m = 2027-06-30
        refv = ref_ferias(cfg, sal, 30, 0, vencida=True)
        code, rv = _post_form("/api/folha/ferias/calcular", token,
                              {**campos, "inicio_ferias": "2027-07-05",
                               "fim_ferias": "2027-08-03"})
        check("calcular vencida → ok",
              code == 200 and rv.get("status") == "ok", f"{code} {rv}")
        check("vencida=true no cálculo (alerta automático)",
              rv.get("vencida") is True, rv.get("vencida"))
        check("salário em dobro confere com a referência",
              quase(rv.get("valor_base"), refv["valor_base"]),
              f"{rv.get('valor_base')} vs {refv['valor_base']}")
        check("1/3 permanece na base normal",
              quase(rv.get("um_terco"), refv["um_terco"]),
              f"{rv.get('um_terco')} vs {refv['um_terco']}")
        check("INSS da referência (vencida)",
              quase(rv.get("inss"), refv["inss"]), f"{rv.get('inss')} vs {refv['inss']}")
        check("líquido da referência (vencida)",
              quase(rv.get("liquido"), refv["liquido"]),
              f"{rv.get('liquido')} vs {refv['liquido']}")
        code, rlim = _post_form("/api/folha/ferias/calcular", token,
                                {**campos, "inicio_ferias": "2027-06-30"})
        check("gozo no último dia do concessivo não é vencida",
              code == 200 and rlim.get("vencida") is False, f"{code} {rlim}")

        print("\n4. Aba Férias — incluir (botão da tela), listar, pagar, excluir")
        code, r = _post_form("/api/folha/ferias/incluir", token,
                             {**campos, "dias_abono": 10})
        fid_ferias = r.get("id")
        check("incluir → ok com id", code == 200 and r.get("status") == "ok" and bool(fid_ferias),
              f"{code} {r}")
        check("incluir grava os valores calculados",
              quase(r.get("liquido"), ref2["liquido"]), f"{r.get('liquido')} vs {ref2['liquido']}")
        code, data = _get("/api/folha/ferias", token=token)
        lista = data.get("ferias", [])
        linha = next((f for f in lista if str(f.get("id")) == str(fid_ferias)), None)
        check("listagem contém as férias recém-incluídas", linha is not None, lista)
        if linha:
            check("listagem: período aquisitivo e gozo (chaves da tela)",
                  linha.get("aquis_inicio") == "2025-07-01"
                  and linha.get("aquis_fim") == "2026-06-30"
                  and linha.get("inicio") == "2026-08-03"
                  and linha.get("fim") == "2026-09-01", linha)
            check("listagem: líquido gravado confere",
                  quase(linha.get("liquido"), ref2["liquido"]), linha.get("liquido"))
            check("listagem: situação inicial = C (calculado)",
                  str(linha.get("situacao", "")) == "C", linha.get("situacao"))
        code, d = _post_form("/api/folha/ferias/pagar", token, {"id": fid_ferias})
        check("pagar férias → ok", code == 200 and d.get("status") == "ok", f"{code} {d}")
        code, data = _get("/api/folha/ferias", token=token)
        linha = next((f for f in data.get("ferias", [])
                      if str(f.get("id")) == str(fid_ferias)), None)
        check("listagem: situação P após pagar",
              linha is not None and str(linha.get("situacao", "")) == "P", linha)
        code, d = _post_form("/api/folha/ferias/excluir", token, {"id": fid_ferias})
        check("excluir férias → ok", code == 200 and d.get("status") == "ok", f"{code} {d}")
        code, data = _get("/api/folha/ferias", token=token)
        check("listagem vazia após excluir", len(data.get("ferias", [])) == 0,
              data.get("ferias"))

        print("\n4b. Férias vencidas — incluir, listagem com alerta, excluir")
        code, rv = _post_form("/api/folha/ferias/incluir", token,
                              {**campos, "inicio_ferias": "2027-07-05",
                               "fim_ferias": "2027-08-03"})
        fid_venc = rv.get("id")
        check("incluir vencida → ok com id",
              code == 200 and rv.get("status") == "ok" and bool(fid_venc),
              f"{code} {rv}")
        check("incluir vencida → vencida=true no retorno", rv.get("vencida") is True,
              rv.get("vencida"))
        code, data = _get("/api/folha/ferias", token=token)
        linha = next((f for f in data.get("ferias", [])
                      if str(f.get("id")) == str(fid_venc)), None)
        check("listagem marca vencida (recomputado do registro)",
              linha is not None and linha.get("vencida") is True, linha)
        check("listagem vencida gravou salário em dobro",
              linha is not None and quase(linha.get("valor_base"), refv["valor_base"]),
              linha and linha.get("valor_base"))
        code, d = _post_form("/api/folha/ferias/excluir", token, {"id": fid_venc})
        check("excluir férias vencidas → ok",
              code == 200 and d.get("status") == "ok", f"{code} {d}")

        print("\n5. Aba 13o Salario — calcular (referência RFC-011)")
        base13 = {"funcionario_id": fid, "nome": nome, "ano": "2026",
                  "parcela": "1", "meses_trabalhados": 12, "salario_base": sal}
        ref1 = ref_decimo(cfg, sal, 12, "1")
        code, rd = _post_form("/api/folha/decimo/calcular", token, base13)
        check("calcular → ok", code == 200 and rd.get("status") == "ok", f"{code} {rd}")
        check("1ª parcela: base = salário/12 × 12",
              quase(rd.get("valor_base"), ref1["valor_base"]), rd.get("valor_base"))
        check("1ª parcela sem INSS (RFC-011 §3.1)",
              quase(rd.get("inss"), 0.00), rd.get("inss"))
        check("1ª parcela sem IRRF",
              quase(rd.get("irrf"), 0.00), rd.get("irrf"))
        check("1ª parcela: líquido = base",
              quase(rd.get("liquido"), ref1["liquido"]), rd.get("liquido"))

        ref2d = ref_decimo(cfg, sal, 12, "2")
        code, rd2 = _post_form("/api/folha/decimo/calcular", token,
                               {**base13, "parcela": "2"})
        check("2ª parcela: INSS confere com a referência",
              quase(rd2.get("inss"), ref2d["inss"]), f"{rd2.get('inss')} vs {ref2d['inss']}")
        check("2ª parcela: IRRF confere com a referência",
              quase(rd2.get("irrf"), ref2d["irrf"]), f"{rd2.get('irrf')} vs {ref2d['irrf']}")
        check("2ª parcela: líquido confere",
              quase(rd2.get("liquido"), ref2d["liquido"]), f"{rd2.get('liquido')} vs {ref2d['liquido']}")

        ref3 = ref_decimo(cfg, sal, 7, "U")
        code, rd3 = _post_form("/api/folha/decimo/calcular", token,
                               {**base13, "parcela": "U", "meses_trabalhados": 7})
        check("parcela única 7 meses: base confere",
              quase(rd3.get("valor_base"), ref3["valor_base"]), rd3.get("valor_base"))
        check("parcela única: INSS confere",
              quase(rd3.get("inss"), ref3["inss"]), f"{rd3.get('inss')} vs {ref3['inss']}")
        check("parcela única: IRRF confere",
              quase(rd3.get("irrf"), ref3["irrf"]), f"{rd3.get('irrf')} vs {ref3['irrf']}")

        print("\n6. Aba 13o Salario — incluir (botão da tela), listar, pagar, excluir")
        code, rd = _post_form("/api/folha/decimo/incluir", token,
                              {**base13, "parcela": "2"})
        did = rd.get("id")
        check("incluir → ok com id", code == 200 and rd.get("status") == "ok" and bool(did),
              f"{code} {rd}")
        check("incluir grava os valores calculados",
              quase(rd.get("liquido"), ref2d["liquido"]), f"{rd.get('liquido')} vs {ref2d['liquido']}")
        code, data = _get("/api/folha/decimos", token=token)
        linha = next((d for d in data.get("decimos", []) if str(d.get("id")) == str(did)), None)
        check("listagem contém o 13º recém-incluído", linha is not None, data.get("decimos"))
        if linha:
            check("listagem: ano/parcela e valores (chaves da tela)",
                  str(linha.get("ano")) == "2026" and str(linha.get("parcela")) == "2"
                  and quase(linha.get("valor_base"), ref2d["valor_base"]), linha)
            check("listagem: situação inicial = C (calculado)",
                  str(linha.get("situacao", "")) == "C", linha.get("situacao"))
        code, d = _post_form("/api/folha/decimo/pagar", token, {"id": did})
        check("pagar 13º → ok", code == 200 and d.get("status") == "ok", f"{code} {d}")
        code, data = _get("/api/folha/decimos", token=token)
        linha = next((d for d in data.get("decimos", []) if str(d.get("id")) == str(did)), None)
        check("listagem: situação P após pagar",
              linha is not None and str(linha.get("situacao", "")) == "P", linha)
        code, d = _post_form("/api/folha/decimo/excluir", token, {"id": did})
        check("excluir 13º → ok", code == 200 and d.get("status") == "ok", f"{code} {d}")
        code, data = _get("/api/folha/decimos", token=token)
        check("listagem vazia após excluir", len(data.get("decimos", [])) == 0,
              data.get("decimos"))

        print("\n7. Validações (guardas do COBOL)")
        code, d = _post_form("/api/folha/ferias/incluir", token, {**campos, "funcionario_id": 0})
        check("incluir sem funcionário → erro 'obrigatorio'",
              d.get("status") == "error" and "obrigatorio" in str(d.get("message", "")).lower(),
              f"{code} {d}")
        code, d = _post_form("/api/folha/ferias/calcular", token, {**campos, "dias": 0})
        check("férias sem dias → erro 'dias'",
              d.get("status") == "error" and "dias" in str(d.get("message", "")).lower(),
              f"{code} {d}")
        code, d = _post_form("/api/folha/ferias/calcular", token,
                             {**campos, "dias": 30, "dias_abono": 11})
        check("abono acima de 1/3 dos dias → erro 'abono' (RFC-010 §5)",
              d.get("status") == "error" and "abono" in str(d.get("message", "")).lower(),
              f"{code} {d}")
        code, d = _post_form("/api/folha/decimo/calcular", token, {**base13, "parcela": "X"})
        check("parcela inválida → erro 'parcela'",
              d.get("status") == "error" and "parcela" in str(d.get("message", "")).lower(),
              f"{code} {d}")
        code, d = _post_form("/api/folha/decimo/calcular", token,
                             {**base13, "meses_trabalhados": 13})
        check("meses > 12 → erro 'meses'",
              d.get("status") == "error" and "meses" in str(d.get("message", "")).lower(),
              f"{code} {d}")

        print("\n8. Portal do funcionário (role 'funcionario' — segurança)")
        code, d = _post_form("/api/folha/ferias/incluir", None, {**campos, "dias_abono": 0})
        check("incluir sem token → 403", code == 403, code)
        portal_func = _funcionario_por_usuario("ci.func")
        if portal_func is None:
            novo_id = cobol_bridge.funcionario_incluir({
                "nome": "CI Portal Ferias", "usuario": "ci.func",
                "senha": "x123", "permissoes": "operador",
                "cpf": "000.111.222-44",  # exclusivo do review
                "data_nasc": "1990-01-01", "data_adm": "2026-01-05",
                "salario": 3000.00})
            portal_func = next((f for f in cobol_bridge.funcionarios_listar()
                                if f["id"] == novo_id), None)
        own_fid = (portal_func or {}).get("id")
        check("funcionário do portal (usuario 'ci.func') disponível", bool(own_fid))
        if not own_fid:
            print(f"\nResultado: {PASS} ✅  {FAIL} ❌")
            return 1
        with open(os.path.join(ROOT, "data", "users.json"), encoding="utf-8") as f:
            users = json.load(f)
        users["portal_review"] = {
            "usuario": "ci.func", "nome": "CI Portal",
            "senha": hashlib.sha256(b"123456").hexdigest(),
            "role": "funcionario", "empresas": {}, "ativo": True, "token": "",
        }
        with open(os.path.join(ROOT, "data", "users.json"), "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        body = json.dumps({"usuario": "ci.func", "senha": "123456"}).encode("utf-8")
        code, data = _req("POST", "/api/auth/login", data=body, ctype="application/json")
        portal_token = data.get("token")
        resp_fid = data.get("funcionario_id")
        check("login do portal devolve token e funcionario_id do vínculo",
              code == 200 and bool(portal_token)
              and str(resp_fid) == str(own_fid), f"{code} {data}")
        campos_portal = {"funcionario_id": own_fid,
                         "periodo_inicio": "2025-07-01", "periodo_fim": "2026-06-30",
                         "inicio_ferias": "2027-01-04", "fim_ferias": "2027-02-02",
                         "dias": 30, "dias_abono": 0,
                         "salario_base": 99999}  # cliente tenta inflar — deve ser ignorado
        code, d = _post_form("/api/folha/ferias/incluir", portal_token, campos_portal)
        check("portal inclui férias do próprio vínculo → ok",
              code == 200 and d.get("status") == "ok" and d.get("id"), f"{code} {d}")
        if d.get("id"):
            ref_own = ref_ferias(cfg, float(portal_func.get("salario") or 0) or 3000.00, 30, 0)
            check("portal: salário SEMPRE do cadastro (cliente enviou 99999)",
                  quase(d.get("valor_base"), ref_own["valor_base"]),
                  f"{d.get('valor_base')} vs {ref_own['valor_base']}")
            _post_form("/api/folha/ferias/excluir", token, {"id": d.get("id")})
        outro = _funcionario_por_usuario("review.outro")
        if outro is None:
            outro_id = cobol_bridge.funcionario_incluir({
                "nome": "Outro Vinculo", "usuario": "review.outro",
                "senha": "x123", "permissoes": "operador",
                "cpf": "000.111.222-55",  # exclusivo do review
                "data_nasc": "1990-01-01", "data_adm": "2026-01-05",
                "salario": 3000.00})
            outro = next(f for f in cobol_bridge.funcionarios_listar()
                         if f["id"] == outro_id)
        code, d = _post_form("/api/folha/ferias/incluir", portal_token,
                             {**campos_portal, "funcionario_id": outro.get("id"),
                              "inicio_ferias": "2027-03-01", "fim_ferias": "2027-03-30"})
        check("portal: incluir para OUTRO vínculo → 403",
              code == 403 and "proprio" in str(d.get("message", "")).lower(), f"{code} {d}")
        code, _ = _get("/api/folha/ferias", token=portal_token)
        check("portal: GET /api/folha/ferias → 403 (acesso restrito)",
              code == 403, code)
        code, d = _post_form("/api/folha/ferias/calcular", portal_token, campos_portal)
        check("portal: ferias/calcular → 403", code == 403, code)
        code, d = _post_form("/api/folha/decimo/incluir", portal_token, {
            "funcionario_id": own_fid, "ano": "2026", "parcela": "1",
            "meses_trabalhados": 12, "salario_base": 99999})
        check("portal: decimo/incluir → 403 (só férias liberadas)",
              code == 403, f"{code} {d}")

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
