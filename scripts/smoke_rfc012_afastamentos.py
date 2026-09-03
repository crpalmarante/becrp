#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke E2E do RFC-012 — Afastamentos, licenças e suspensões do vínculo.

Sobe o servidor local em porta dedicada e cobre (RFC-012 Decisões 1–4):
  CRUD dedicado (Decisão 1)
    - GET /api/licencas (lista todas, com nome do vínculo)
    - POST /api/licenca/incluir → id
    - POST /api/licenca/alterar (datas/motivo antes da aprovação)
    - POST /api/licenca/excluir (só não aprovada)
  Situação do vínculo (Decisão 2)
    - aprovar licença → funcionário vira "afastado"
    - rejeitar → volta para "ativo"
  Pró-rata por dias trabalhados (Decisão 3)
    - licença não remunerada aprovada na competência → dias de afastamento
      somados às faltas no processamento (salário proporcional)
    - maternidade/paternidade → zero dias (pagamento integral)
    - auxílio-doença → só o excedente dos 15 primeiros dias entra
  Suspensão do período aquisitivo (Decisão 4)
    - afastamento aprovado >30 dias no período aquisitivo → aviso nas férias

Isolamento: backup/restauração de dados/licencas.dat, licencas.tmp,
funcionarios.dat, folhas.dat, folhas.tmp, folha_config.dat, ferias.dat,
ferias.tmp, folha_auditoria.jsonl e data/users.json. Servidor encerrado ao fim.

Uso:
    python3 scripts/smoke_rfc012_afastamentos.py [--port 8183]
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
    "dados/licencas.dat",
    "dados/licencas.tmp",
    "dados/funcionarios.dat",
    "dados/folhas.dat",
    "dados/folhas.tmp",
    "dados/folha_config.dat",
    "dados/ferias.dat",
    "dados/ferias.tmp",
    "dados/folha_auditoria.jsonl",
    "data/users.json",
)
BACKUP = "/tmp/becrp_rfc012_backup"

PORT = 8183

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


def quase(a, b, tol=0.02):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


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


def _users():
    with open(os.path.join(ROOT, "data/users.json"), encoding="utf-8") as f:
        return json.load(f)


def _token(login):
    for _uid, u in _users().items():
        if str(u.get("usuario") or "") == login and u.get("token"):
            return u["token"]
    return None


def _garantir_usuarios():
    """Admin para o cenário — usa o token gravado em data/users.json."""
    import hashlib
    path = os.path.join(ROOT, "data/users.json")
    users = _users() if os.path.exists(path) else {}
    senha = hashlib.sha256("123456".encode()).hexdigest()
    users.setdefault("bruno", {
        "usuario": "bruno", "nome": "Bruno", "senha": senha,
        "role": "admin", "ativo": True,
    })
    for uid, u in users.items():
        if not u.get("token"):
            u["token"] = f"tok-{uid}-{abs(hash(uid)) % 10**8}"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _funcionario_teste():
    """Garante um funcionário ativo para os cenários. Retorna o id."""
    funcs = cobol_bridge.funcionarios_listar()
    for f in funcs:
        if str(f.get("nome") or "").strip().lower().startswith("joao"):
            return f.get("id"), f
    dados = {
        "nome": "Joao Afastamento RFC012",
        "usuario": "joao_afast_rfc012",
        "senha": "x123",
        "cpf": "111.222.333-44",
        "data_nasc": "1990-01-01",
        "sexo": "M",
        "nacionalidade": "brasileiro",
        "endereco": "Rua Teste, 1",
        "cep": "99000000",
        "cidade": "Passo Fundo",
        "uf": "RS",
        "ctps": "0000000",
        "data_adm": "2025-01-10",
        "salario": "3000.00",
        "departamento_id": "1",
        "cargo_id": "1",
        "forma_pagamento": "mensal",
        "situacao_vinculo": "ativo",
    }
    fid = cobol_bridge.funcionario_incluir(dados)
    return fid, {"id": fid, "nome": dados["nome"]}


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
                    "dados/folha_auditoria.jsonl", "dados/licencas.dat",
                    "dados/licencas.tmp"):
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                os.remove(p)
        log = open(os.path.join(BACKUP, "server.log"), "w", encoding="utf-8")
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

        token = _token("bruno")
        check("token de admin disponivel", bool(token))

        # ── cenário: funcionário + limpeza de licenças antigas ──
        fid, fobj = _funcionario_teste()
        check("funcionario de teste existe", fid is not None)
        # garante vínculo ativo no início
        cobol_bridge.funcionario_alterar(fid, {"situacao_vinculo": "ativo"})

        print("\n1. CRUD dedicado (RFC-012 Decisão 1)")
        code, r = _post("/api/licenca/incluir", token, {
            "funcionario_id": fid, "tipo": "licenca-nao-remunerada",
            "data_inicio": "2026-05-01", "data_fim": "2026-05-10",
            "dias": "10", "motivo": "tratamento pessoal"})
        check("incluir cria licenca (id)", code == 200 and r.get("id"), r)
        lid = r.get("id")
        check("listar todas traz a licenca com nome", any(
            str(l.get("id")) == str(lid) and l.get("nome")
            for l in (_get("/api/licencas", token)[1].get("licencas") or [])),
            [l for l in (_get("/api/licencas", token)[1].get("licencas") or [])])
        code, r = _post("/api/licenca/alterar", token, {
            "id": lid, "motivo": "tratamento pessoal - extensao"})
        check("alterar licenca (motivo)", code == 200 and r.get("status") == "ok", r)

        print("\n2. Situação do vínculo (RFC-012 Decisão 2)")
        code, r = _post("/api/licenca/aprovar", token, {"id": lid})
        check("aprovar licenca", code == 200 and r.get("status") == "ok", r)
        f = next((x for x in cobol_bridge.funcionarios_listar()
                  if str(x.get("id")) == str(fid)), {})
        check("funcionario passou para 'afastado'",
              (f.get("situacao_vinculo") or "").strip().lower() == "afastado",
              f.get("situacao_vinculo"))
        code, r = _post("/api/licenca/rejeitar", token, {"id": lid})
        check("rejeitar licenca", code == 200 and r.get("status") == "ok", r)
        f = next((x for x in cobol_bridge.funcionarios_listar()
                  if str(x.get("id")) == str(fid)), {})
        check("rejeicao volta o funcionario para 'ativo'",
              (f.get("situacao_vinculo") or "").strip().lower() in ("ativo", "a", ""),
              f.get("situacao_vinculo"))

        print("\n3. Pró-rata por dias trabalhados (RFC-012 Decisão 3)")
        # licença não remunerada aprovada cobre 10 dias de 2026/05
        lid2 = cobol_bridge.licenca_incluir({
            "funcionario_id": fid, "tipo": "licenca-nao-remunerada",
            "data_inicio": "2026-05-01", "data_fim": "2026-05-10",
            "dias": "10", "motivo": "nao remunerada - smoke"})
        cobol_bridge.licenca_aprovar(lid2, "bruno", "2026-05-03")
        dias = cobol_bridge.dias_afastamento_na_competencia(fid, "2026/05")
        check("dias de afastamento na competencia = 10", dias == 10, dias)
        cobol_bridge.folha_config_seed()
        cobol_bridge.folha_abrir("2026/05")
        code, r = _post("/api/folha/competencia/calcular", token, {
            "competencia": "2026/05", "funcionario_id": fid,
            "nome": fobj.get("nome"), "salario_base": "3000.00"})
        check("calcular com afastamento devolve dias_afastamento",
              code == 200 and int(r.get("dias_afastamento") or 0) == 10, r)
        # salário proporcional: as faltas de afastamento (10 dias × 3000/30 =
        # 1000,00) entram nos descontos — desc_faltas = total_descontos − INSS
        # − IRRF (sem outros descontos neste cenário)
        desc_faltas = float(r.get("total_descontos") or 0) - float(r.get("inss") or 0) - float(r.get("irrf") or 0)
        check("desconto de faltas reflete o pró-rata (1000,00)",
              quase(desc_faltas, 1000.00), desc_faltas)
        det = cobol_bridge.folha_mostrar("2026/05")
        funcs = det.get("funcionarios") or []
        # folha-mostrar não expõe o campo faltas; o desconto gravado confirma
        # que os dias de afastamento entraram no processamento (1000,00)
        ok_persistido = False
        for f in funcs:
            if str(f.get("funcionario_id")) == str(fid):
                desc_f = float(f.get("total_descontos") or 0) - float(f.get("inss") or 0) - float(f.get("irrf") or 0)
                ok_persistido = quase(desc_f, 1000.00)
                break
        check("pró-rata persistido no processamento (desc faltas 1000,00)",
              ok_persistido, funcs)

        # maternidade → zero dias de afastamento na competência
        lid3 = cobol_bridge.licenca_incluir({
            "funcionario_id": fid, "tipo": "licenca-maternidade",
            "data_inicio": "2026-06-01", "data_fim": "2026-09-28",
            "dias": "120", "motivo": "maternidade - smoke"})
        cobol_bridge.licenca_aprovar(lid3, "bruno", "2026-06-01")
        dias_mat = cobol_bridge.dias_afastamento_na_competencia(fid, "2026/06")
        check("maternidade nao gera dias nao pagos", dias_mat == 0, dias_mat)

        # auxílio-doença 30 dias → só os 15 excedentes entram
        lid4 = cobol_bridge.licenca_incluir({
            "funcionario_id": fid, "tipo": "auxilio-doenca",
            "data_inicio": "2026-07-01", "data_fim": "2026-07-30",
            "dias": "30", "motivo": "doenca - smoke"})
        cobol_bridge.licenca_aprovar(lid4, "bruno", "2026-07-01")
        dias_doenca = cobol_bridge.dias_afastamento_na_competencia(fid, "2026/07")
        check("auxilio-doenca 30d -> 15 dias nao pagos", dias_doenca == 15, dias_doenca)

        # auxílio-doença atravessando mês (20/06 → 19/07, 30 dias): os 15
        # primeiros pagos pela empresa em junho; julho inteiro entra (INSS)
        lid5 = cobol_bridge.licenca_incluir({
            "funcionario_id": fid, "tipo": "auxilio-doenca",
            "data_inicio": "2026-08-20", "data_fim": "2026-09-18",
            "dias": "30", "motivo": "doenca atravessando mes - smoke"})
        cobol_bridge.licenca_aprovar(lid5, "bruno", "2026-08-20")
        dias_set = cobol_bridge.dias_afastamento_na_competencia(fid, "2026/09")
        # 20/08..18/09 (30d): primeiros 15 pagos (20/08..03/09); em setembro
        # ficam não pagos os dias 04..18 = 15
        check("auxilio-doenca atravessando mes: saldo apos cota de 15 (15 dias)",
              dias_set == 15, dias_set)

        print("\n2.1 Aprovação via workflow (dashboard) também marca o vínculo")
        lid_wf = cobol_bridge.licenca_incluir({
            "funcionario_id": fid, "tipo": "licenca-nao-remunerada",
            "data_inicio": "2026-10-01", "data_fim": "2026-10-05",
            "dias": "5", "motivo": "workflow - smoke"})
        cobol_bridge.licenca_transitar(lid_wf, "S", "bruno", "2026-10-01")
        code, r = _post("/api/workflow/transition", token, {
            "module": "licenca", "record_id": lid_wf,
            "target_status": "A", "user_name": "bruno", "user_role": "admin"})
        check("workflow aprova licenca", code == 200 and r.get("status") == "ok", r)
        f = next((x for x in cobol_bridge.funcionarios_listar()
                  if str(x.get("id")) == str(fid)), {})
        check("aprovação via workflow marca 'afastado'",
              (f.get("situacao_vinculo") or "").strip().lower() == "afastado",
              f.get("situacao_vinculo"))
        # concluir (C = retorno) volta a ativo quando não há outra aprovada;
        # aqui há lid5 (doença) aprovada — o vínculo permanece afastado
        cobol_bridge.funcionario_alterar(fid, {"situacao_vinculo": "ativo"})

        print("\n4. Suspensão do período aquisitivo (RFC-012 Decisão 4)")
        # sem afastamento no período aquisitivo → sem aviso
        code, r = _post("/api/folha/ferias/calcular", token, {
            "funcionario_id": fid, "nome": fobj.get("nome"),
            "periodo_inicio": "2025-01-10", "periodo_fim": "2026-01-09",
            "inicio_ferias": "2026-08-01", "fim_ferias": "2026-08-30",
            "dias": "30", "dias_abono": "0", "salario_base": "3000.00"})
        check("sem afastamento no periodo aquisitivo nao gera aviso",
              code == 200 and int(r.get("aviso_suspensao_aquisitivo") or 0) == 0,
              r)
        # um único afastamento aprovado >30d dentro do período → aviso
        lid_susp = cobol_bridge.licenca_incluir({
            "funcionario_id": fid, "tipo": "licenca-nao-remunerada",
            "data_inicio": "2025-02-01", "data_fim": "2025-03-17",
            "dias": "45", "motivo": "suspensao aquisitivo - smoke"})
        cobol_bridge.licenca_aprovar(lid_susp, "bruno", "2025-02-01")
        code2, r2 = _post("/api/folha/ferias/calcular", token, {
            "funcionario_id": fid, "nome": fobj.get("nome"),
            "periodo_inicio": "2025-01-10", "periodo_fim": "2026-01-09",
            "inicio_ferias": "2026-08-01", "fim_ferias": "2026-08-30",
            "dias": "30", "dias_abono": "0", "salario_base": "3000.00"})
        aviso = int(r2.get("aviso_suspensao_aquisitivo") or 0)
        check("afastamento 45d no periodo aquisitivo gera aviso (>30)",
              code2 == 200 and aviso >= 45, r2)

        print("\n5. Exclusão e trilha de auditoria")
        lid_ex = cobol_bridge.licenca_incluir({
            "funcionario_id": fid, "tipo": "suspensao",
            "data_inicio": "2026-08-01", "data_fim": "2026-08-03",
            "dias": "3", "motivo": "excluir - smoke"})
        code, r = _post("/api/licenca/excluir", token, {"id": lid_ex})
        check("excluir licenca nao aprovada", code == 200 and r.get("status") == "ok", r)
        restantes = [l for l in cobol_bridge.licencas_listar()
                     if str(l.get("id")) == str(lid_ex)]
        check("licenca excluida nao lista mais", not restantes)
        try:
            with open(os.path.join(ROOT, "dados/folha_auditoria.jsonl"),
                      encoding="utf-8") as f:
                linhas = [l for l in f.read().strip().splitlines() if l.strip()]
            auditoria = json.loads(linhas[-1])
            check("trilha de auditoria registrou a licenca",
                  (auditoria.get("contexto") or {}).get("tipo") == "licenca",
                  auditoria)
        except (OSError, IndexError, ValueError):
            check("trilha de auditoria registrou a licenca", False, "sem eventos")

        print(f"\n{'='*50}\nResultado: {PASS} ok / {FAIL} falhas\n{'='*50}")
        return 0 if FAIL == 0 else 1
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
        _restore()


if __name__ == "__main__":
    main()
