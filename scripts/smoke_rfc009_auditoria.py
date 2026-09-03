#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke E2E do RFC-009 — Usuários, papéis e trilha de auditoria.

Sobe o servidor em porta dedicada e confere via HTTP:

  Trilha de auditoria (RFC-009 §5 / Decisão 3)
    - abrir_competencia, calcular, concluir, validar, fechar e pagar ficam
      registrados com quem/quando/contexto/antes/depois
    - o cálculo registra a versão das tabelas usadas (RFC-005 §5.1.2)
    - alterar_tabela (config/salvar) e alterar_cadastro (funcionário) entram
      na trilha — a auditoria cobre cadastros e tabelas, não só o processamento
    - imutabilidade (RFC-009 §5.1.1): a trilha é append-only — eventos antigos
      não são editados/apagados quando novos eventos são gravados

  Regras de separação de funções (RFC-009 §4.2 / Decisão 4)
    - quem abre/calcula a competência é o Operador
    - validar pelo próprio Operador → bloqueado (Conferente ≠ Operador)
    - fechar pelo próprio Operador → bloqueado (Aprovador ≠ Operador)
    - validar/fechar por um segundo usuário (Aprovador) → ok
    - pagar pelo Aprovador → bloqueado (Tesouraria ≠ Aprovador)
    - pagar por um terceiro usuário (Tesouraria) → ok (competência e holerite)

Isolamento: backup/restauração de dados/folhas.dat, folhas.tmp,
folha_config.dat, folha_auditoria.jsonl e data/users.json. O servidor é
encerrado ao final. Não rode com outro servidor usando os mesmos dados/
simultaneamente.

Uso:
    python3 scripts/smoke_rfc009_auditoria.py [--port 8168]
"""

from __future__ import annotations

import hashlib
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

import jsonio  # noqa: E402

FILES = (
    "dados/folhas.dat",
    "dados/folhas.tmp",
    "dados/folha_config.dat",
    "dados/folha_auditoria.jsonl",
    # cadastros mestres de RH auditados na seção 4 (cargos, departamentos,
    # eventos) — restaurados para manter o smoke isolado
    "dados/cargos.dat",
    "dados/departamentos.dat",
    "dados/eventos.dat",
    "data/users.json",
)
BACKUP = "/tmp/becrp_rfc009_backup"

PORT = 8168

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


def _post(path, token, campos):
    body = urllib.parse.urlencode(campos).encode("utf-8")
    return _req("POST", path, token=token, data=body)


def _get(path, token=None):
    return _req("GET", path, token=token)


def _get_raw(path, token=None):
    """GET que devolve o corpo bruto (para relatórios HTML, sem parse JSON)."""
    url = f"http://127.0.0.1:{PORT}{path}"
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("X-Auth-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


def _users():
    with open(os.path.join(ROOT, "data/users.json"), encoding="utf-8") as f:
        return json.load(f)


def _garantir_usuarios():
    """Usuários do cenário: bruno (Operador), aprovador (Aprovador) e
    tesouraria (Tesouraria — quem registra o pagamento, RFC-009 §4.2)."""
    path = os.path.join(ROOT, "data/users.json")
    users = _users() if os.path.exists(path) else {}
    users.setdefault("bruno", {
        "usuario": "bruno", "nome": "Bruno RFC009", "email": "b@ci.local",
        "senha": hashlib.sha256(b"123456").hexdigest(), "role": "admin",
        "empresas": {}, "ativo": True, "token": "ci-token-becrp-2026",
    })
    users.setdefault("aprovador", {
        "usuario": "aprovador", "nome": "Aprovador RFC009",
        "email": "a@ci.local", "senha": hashlib.sha256(b"654321").hexdigest(),
        "role": "admin", "empresas": {}, "ativo": True,
        "token": "ci-token-aprovador-2026",
    })
    users.setdefault("tesouraria", {
        "usuario": "tesouraria", "nome": "Tesouraria RFC009",
        "email": "t@ci.local", "senha": hashlib.sha256(b"123123").hexdigest(),
        "role": "admin", "empresas": {}, "ativo": True,
        "token": "ci-token-tesouraria-2026",
    })
    jsonio.save(path, users)


def _token(login):
    for _uid, u in _users().items():
        if str(u.get("usuario") or "") == login and u.get("token"):
            return u["token"]
    return None


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
        _garantir_usuarios()
        for rel in ("dados/folhas.dat", "dados/folhas.tmp",
                    "dados/folha_auditoria.jsonl"):
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                os.remove(p)

        log = open(os.path.join(BACKUP, "server.log"), "w")
        proc = subprocess.Popen([sys.executable, "server.py", str(PORT)],
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
        check("servidor sobe (check-setup 200)", up and proc.poll() is None)
        if not up or proc.poll() is not None:
            log.flush()
            tail = open(os.path.join(BACKUP, "server.log"), encoding="utf-8").read()[-800:]
            print(tail)
            return 1

        tok_oper = _token("bruno")
        tok_aprov = _token("aprovador")
        tok_tes = _token("tesouraria")
        check("token Operador (bruno)", bool(tok_oper))
        check("token Aprovador (aprovador)", bool(tok_aprov))
        check("token Tesouraria (tesouraria)", bool(tok_tes))

        print("\n1. Autenticação e guarda da trilha")
        code, _ = _get("/api/folha/auditoria")
        check("GET /api/folha/auditoria sem token → 403", code == 403, code)
        code, data = _get("/api/folha/auditoria", token=tok_oper)
        check("GET auditoria autenticado → ok", code == 200 and data.get("status") == "ok",
              f"{code} {data}")

        print("\n2. Trilha — abrir/calcular/concluir (Operador = bruno)")
        comp = "2026/09"
        code, data = _post("/api/folha/competencia/abrir", tok_oper, {"competencia": comp})
        check("abrir competência → ok", code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?competencia=" + urllib.parse.quote(comp),
                         token=tok_oper)
        acoes = [e.get("acao") for e in evs.get("eventos", [])]
        check("trilha registrou abrir_competencia", "abrir_competencia" in acoes, acoes)
        ev_abr = next((e for e in evs.get("eventos", [])
                       if e.get("acao") == "abrir_competencia"), None)
        check("abrir: quem = bruno", ev_abr is not None and ev_abr.get("quem") == "bruno", ev_abr)
        check("abrir: contexto tem competência",
              ev_abr is not None and ev_abr.get("contexto", {}).get("competencia") == comp, ev_abr)

        code, data = _post("/api/folha/competencia/calcular", tok_oper, {
            "competencia": comp, "funcionario_id": "1", "nome": "Joao",
            "salario_base": "3000.00", "horas_extras": "0", "dsr": "0",
            "faltas": "0", "dependentes": "0", "outros_proventos": "0",
            "outros_descontos": "0",
        })
        check("calcular → ok", code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?competencia=" + urllib.parse.quote(comp),
                         token=tok_oper)
        ev_calc = next((e for e in evs.get("eventos", [])
                        if e.get("acao") == "calcular"), None)
        check("trilha registrou calcular", ev_calc is not None, evs.get("eventos"))
        check("calcular: quem = bruno", ev_calc is not None and ev_calc.get("quem") == "bruno",
              ev_calc)
        check("calcular: depois tem líquido",
              ev_calc is not None and "liquido" in (ev_calc.get("depois") or {}), ev_calc)
        check("calcular: registrou versão das tabelas (RFC-005 §5.1.2)",
              ev_calc is not None and ev_calc.get("tax_table_versions"), ev_calc)
        check("calcular: contexto tem funcionario_id",
              ev_calc is not None and ev_calc.get("contexto", {}).get("funcionario_id") == "1",
              ev_calc)

        code, data = _post("/api/folha/competencia/concluir", tok_oper, {"competencia": comp})
        check("concluir → ok", code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?competencia=" + urllib.parse.quote(comp),
                         token=tok_oper)
        acoes = [e.get("acao") for e in evs.get("eventos", [])]
        check("trilha registrou concluir", "concluir" in acoes, acoes)

        print("\n3. Regra Aprovador ≠ Operador (RFC-009 §4.2/Decisão 4)")
        code, data = _post("/api/folha/competencia/validar", tok_oper, {"competencia": comp})
        check("validar pelo Operador → bloqueado",
              data.get("status") == "error"
              and "Operador" in str(data.get("message", "")),
              f"{code} {data}")
        code, data = _post("/api/folha/competencia/fechar", tok_oper, {"competencia": comp})
        check("fechar pelo Operador → bloqueado",
              data.get("status") == "error"
              and "Aprovador" in str(data.get("message", "")),
              f"{code} {data}")

        code, data = _post("/api/folha/competencia/validar", tok_aprov, {"competencia": comp})
        check("validar pelo Aprovador → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, data = _post("/api/folha/competencia/fechar", tok_aprov, {"competencia": comp})
        check("fechar pelo Aprovador → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?competencia=" + urllib.parse.quote(comp),
                         token=tok_oper)
        ev_val = next((e for e in evs.get("eventos", []) if e.get("acao") == "validar"), None)
        ev_fec = next((e for e in evs.get("eventos", []) if e.get("acao") == "fechar"), None)
        check("validar: quem = aprovador",
              ev_val is not None and ev_val.get("quem") == "aprovador", ev_val)
        check("fechar: quem = aprovador",
              ev_fec is not None and ev_fec.get("quem") == "aprovador", ev_fec)

        print("\n3b. Regra Tesouraria ≠ Aprovador no pagamento (RFC-009 §4.2)")
        code, data = _post("/api/folha/competencia/pagar", tok_aprov,
                           {"competencia": comp, "data_pagamento": "2026-09-10"})
        check("pagar pelo Aprovador → bloqueado",
              data.get("status") == "error"
              and "Tesouraria" in str(data.get("message", "")),
              f"{code} {data}")
        code, data = _post("/api/folha/competencia/pagar", tok_tes,
                           {"competencia": comp, "data_pagamento": "2026-09-10"})
        check("pagar pela Tesouraria → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?competencia=" + urllib.parse.quote(comp),
                         token=tok_oper)
        ev_pag = next((e for e in evs.get("eventos", [])
                       if e.get("acao") == "pagar"), None)
        check("pagar: quem = tesouraria",
              ev_pag is not None and ev_pag.get("quem") == "tesouraria", ev_pag)
        check("pagar: antes/depois de situação",
              ev_pag is not None and (ev_pag.get("antes") or {}).get("situacao") == "F"
              and (ev_pag.get("depois") or {}).get("situacao") == "P", ev_pag)

        print("\n3c. Regra Tesouraria ≠ Aprovador no holerite (RFC-009 §4.2)")
        code, data = _post("/api/folha/holerite/gerar", tok_oper,
                           {"competencia": comp})
        check("gerar holerites → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?competencia=" + urllib.parse.quote(comp),
                         token=tok_oper)
        ev_gh = next((e for e in evs.get("eventos", [])
                      if e.get("acao") == "gerar_holerites"), None)
        check("trilha registrou gerar_holerites", ev_gh is not None, evs.get("eventos"))
        check("gerar_holerites: depois tem gerados > 0",
              ev_gh is not None and (ev_gh.get("depois") or {}).get("gerados") > 0, ev_gh)
        hid = None
        code, hd = _get("/api/folha/holerites", token=tok_oper)
        for h in hd.get("holerites", []):
            if h.get("competencia") == comp:
                hid = h.get("id")
                break
        check("holerite da competência encontrado", hid is not None, hd)
        code, data = _post("/api/folha/holerite/pagar", tok_aprov,
                           {"id": hid, "data_pagamento": "2026-09-15"})
        check("pagar holerite pelo Aprovador → bloqueado",
              data.get("status") == "error"
              and "Tesouraria" in str(data.get("message", "")),
              f"{code} {data}")
        code, data = _post("/api/folha/holerite/pagar", tok_tes,
                           {"id": hid, "data_pagamento": "2026-09-15"})
        check("pagar holerite pela Tesouraria → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?acao=pagar_holerite", token=tok_oper)
        ev_hp = next((e for e in evs.get("eventos", [])
                      if e.get("contexto", {}).get("holerite_id") == str(hid)), None)
        check("trilha registrou pagar_holerite (com competência)",
              ev_hp is not None and ev_hp.get("quem") == "tesouraria"
              and ev_hp.get("contexto", {}).get("competencia") == comp, ev_hp)

        print("\n3d. Anexo de auditoria no relatório de fechamento (RFC-015)")
        status, body = _get_raw("/api/folha/encargos/relatorio?competencia="
                                + urllib.parse.quote(comp), token=tok_oper)
        check("relatório de encargos → HTML 200",
              status == 200 and "<!DOCTYPE html>" in body, status)
        check("relatório inclui o anexo de auditoria",
              "Trilha de auditoria" in body, "anexo ausente")
        check("anexo lista os eventos da competência (abrir/fechar/pagar)",
              "Abrir competência" in body and "Fechar" in body
              and "Registrar pagamento" in body, "eventos ausentes")
        check("anexo mostra quem operou (bruno/aprovador/tesouraria)",
              "bruno" in body and "aprovador" in body and "tesouraria" in body,
              "quem ausente")

        print("\n4. Auditoria cobre cadastros e tabelas (RFC-009 §5.1.3)")
        # tabela alterada numa competência ABERTA (a 2026/09 já foi fechada e é
        # imutável — RFC-005 Regra 2; usar 2026/10 que está aberta)
        code, data = _post("/api/folha/config/salvar", tok_oper, {
            "competencia": "2026/10", "sf_f1_teto": "1905.52", "sf_f1_valor": "62.04",
        })
        check("config/salvar → ok", code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?acao=alterar_tabela", token=tok_oper)
        ev_tab = next((e for e in evs.get("eventos", []) if e.get("acao") == "alterar_tabela"), None)
        check("alterar_tabela registrado",
              ev_tab is not None and ev_tab.get("contexto", {}).get("tabela") == "folha_config",
              ev_tab)
        check("alterar_tabela: depois tem sf_f1_teto",
              ev_tab is not None and "sf_f1_teto" in (ev_tab.get("depois") or {}), ev_tab)

        cpf_uniq = f"{int(time.time()) % 1000:03d}.444.555-66"
        code, data = _post("/api/funcionario/incluir", tok_oper, {
            "nome": "Auditado RFC009", "usuario": "audit.rfc009", "senha": "x123",
            "cpf": cpf_uniq, "data_nasc": "1992-03-03", "sexo": "F",
            "nacionalidade": "Brasileira", "endereco": "Rua X", "cep": "01000-000",
            "cidade": "Sao Paulo", "uf": "SP", "data_adm": "2026-01-01",
            "salario": "2000.00",
        })
        check("funcionario/incluir → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?acao=alterar_cadastro", token=tok_oper)
        ev_cad = next((e for e in evs.get("eventos", []) if e.get("acao") == "alterar_cadastro"), None)
        check("alterar_cadastro registrado (funcionário)",
              ev_cad is not None and ev_cad.get("contexto", {}).get("tipo") == "funcionario",
              ev_cad)

        # RFC-009 §5.1.3 — cadastros mestres de RH também são auditados.
        uniq = str(int(time.time() * 1000) % 10**9)
        code, data = _post("/api/departamento/incluir", tok_oper, {
            "codigo": "AUD-" + uniq[-5:], "descricao": "Depto Auditado RFC009",
            "centro_custo": "CC-AUD", "responsavel": "Auditor"})
        check("departamento/incluir → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?acao=alterar_cadastro", token=tok_oper)
        ev_dep = next((e for e in evs.get("eventos", [])
                       if e.get("contexto", {}).get("tipo") == "departamento"
                       and e.get("contexto", {}).get("acao") == "incluir"), None)
        check("alterar_cadastro registrado (departamento)",
              ev_dep is not None and ev_dep.get("depois", {}).get("descricao"), ev_dep)
        did_aud = data.get("id")
        code, data = _post("/api/departamento/alterar", tok_oper, {
            "id": did_aud, "descricao": "Depto Auditado RFC009 ALTERADO"})
        check("departamento/alterar → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?acao=alterar_cadastro", token=tok_oper)
        ev_dep_alt = next((e for e in evs.get("eventos", [])
                           if e.get("contexto", {}).get("tipo") == "departamento"
                           and e.get("contexto", {}).get("acao") == "alterar"), None)
        check("alterar_cadastro registrado (departamento alterar)",
              ev_dep_alt is not None
              and ev_dep_alt.get("depois", {}).get("descricao") == "Depto Auditado RFC009 ALTERADO",
              ev_dep_alt)

        code, data = _post("/api/cargo/incluir", tok_oper, {
            "codigo": "AUD-" + uniq[-5:], "descricao": "Cargo Auditado RFC009",
            "cbo": "0000-00", "salario_referencia": "1000.00"})
        check("cargo/incluir → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?acao=alterar_cadastro", token=tok_oper)
        ev_car = next((e for e in evs.get("eventos", [])
                       if e.get("contexto", {}).get("tipo") == "cargo"
                       and e.get("contexto", {}).get("acao") == "incluir"), None)
        check("alterar_cadastro registrado (cargo)",
              ev_car is not None and ev_car.get("depois", {}).get("descricao"), ev_car)

        code, data = _post("/api/evento/incluir", tok_oper, {
            # código numérico único (o COBOL valida NUMVAL > 0)
            "codigo": str(100 + int(uniq) % 10**5), "descricao": "Evento Auditado RFC009",
            "tipo": "provento", "categoria": "salario", "referencia": "MENSAL",
            "formula": "base", "incide_inss": "S", "incide_irrf": "S",
            "incide_fgts": "S", "ordem": "90", "uso": "S", "status": "A"})
        check("evento/incluir → ok",
              code == 200 and data.get("status") == "ok", f"{code} {data}")
        code, evs = _get("/api/folha/auditoria?acao=alterar_cadastro", token=tok_oper)
        ev_evt = next((e for e in evs.get("eventos", [])
                       if e.get("contexto", {}).get("tipo") == "evento"
                       and e.get("contexto", {}).get("acao") == "incluir"), None)
        check("alterar_cadastro registrado (evento)",
              ev_evt is not None and ev_evt.get("depois", {}).get("descricao"), ev_evt)

        print("\n5. Imutabilidade (RFC-009 §5.1.1)")
        code, evs_a = _get("/api/folha/auditoria", token=tok_oper)
        por_id_a = {e.get("id"): e for e in evs_a.get("eventos", [])}
        ids_a = sorted(por_id_a.keys())
        _post("/api/folha/competencia/abrir", tok_oper, {"competencia": "2026/10"})
        _post("/api/folha/competencia/calcular", tok_oper, {
            "competencia": "2026/10", "funcionario_id": "1", "nome": "Joao",
            "salario_base": "2000.00", "horas_extras": "0", "dsr": "0",
            "faltas": "0", "dependentes": "0", "outros_proventos": "0",
            "outros_descontos": "0",
        })
        code, evs_b = _get("/api/folha/auditoria", token=tok_oper)
        por_id_b = {e.get("id"): e for e in evs_b.get("eventos", [])}
        ids_b = sorted(por_id_b.keys())
        check("novos eventos só acrescentam (ids anteriores preservados)",
              all(i in ids_b for i in ids_a) and len(ids_b) > len(ids_a),
              f"{len(ids_a)} → {len(ids_b)}")
        check("eventos antigos idênticos após o append (imutável)",
              all(por_id_b.get(i) == por_id_a.get(i) for i in ids_a),
              "algum evento antigo foi alterado")

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
