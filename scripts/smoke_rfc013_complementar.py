#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke E2E do RFC-013 — Folha Complementar (ajuste de competência fechada).

Sobe o servidor local em porta dedicada e cobre (RFC-013 Decisões 1–4):
  CRUD + motivo obrigatório (Decisão 1)
    - incluir sem motivo → 400
    - incluir com motivo → id + valores calculados (INSS/IRRF sobre a diferença)
    - listar via GET /api/folha/complementares
  Valores positivos e negativos (Decisão 2)
    - valor negativo com motivo não validado → 400
    - valor negativo com motivo validado (devolucao) → ok, líquido negativo
    - desconto acima de 70% do salário → 400 (limite legal)
  Múltiplas complementares por competência (Decisão 3)
    - duas complementares da mesma competência com motivos distintos
  Fluxo de estados + separação de funções (Regra 3 + RFC-009)
    - C → V (validar) → F (fechar) → P (pagar)
    - fechar exige Aprovador ≠ Operador (quem incluiu não fecha)
    - pagar exige Tesouraria ≠ Aprovador (quem fechou não paga)
  Auditoria (Regra 6)
    - eventos incluir_complementar/fechar_complementar na trilha

Isolamento: backup/restauração de dados/complementar.dat, complementar.tmp,
funcionarios.dat, folha_config.dat, folha_auditoria.jsonl e data/users.json.
Servidor encerrado ao fim.

Uso:
    python3 scripts/smoke_rfc013_complementar.py [--port 8184]
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
    "dados/complementar.dat",
    "dados/complementar.tmp",
    "dados/funcionarios.dat",
    "dados/folha_config.dat",
    "dados/folha_auditoria.jsonl",
    "data/users.json",
)
BACKUP = "/tmp/becrp_rfc013_backup"

PORT = 8184

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
    """Admin + segundo usuário (instrutor) para a separação de funções."""
    import hashlib
    path = os.path.join(ROOT, "data/users.json")
    users = _users() if os.path.exists(path) else {}
    senha = hashlib.sha256("123456".encode()).hexdigest()
    users.setdefault("bruno", {
        "usuario": "bruno", "nome": "Bruno", "senha": senha,
        "role": "admin", "ativo": True,
    })
    users.setdefault("rh2", {
        "usuario": "rh2", "nome": "RH Aprovador", "senha": senha,
        "role": "instrutor", "ativo": True,
    })
    for uid, u in users.items():
        if not u.get("token"):
            u["token"] = f"tok-{uid}-{abs(hash(uid)) % 10**8}"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _funcionario_teste():
    """Garante um funcionário ativo para os cenários. Retorna (id, salario)."""
    funcs = cobol_bridge.funcionarios_listar()
    for f in funcs:
        if str(f.get("nome") or "").strip().lower().startswith("ana comp"):
            return f.get("id"), float(f.get("salario") or 0)
    dados = {
        "nome": "Ana Complementar RFC013",
        "usuario": "ana_comp_rfc013",
        "senha": "x123",
        "cpf": "222.333.444-55",
        "data_nasc": "1992-02-02",
        "sexo": "F",
        "nacionalidade": "brasileira",
        "endereco": "Rua Teste, 2",
        "cep": "99000000",
        "cidade": "Passo Fundo",
        "uf": "RS",
        "ctps": "1111111",
        "data_adm": "2025-02-10",
        "salario": "3000.00",
        "departamento_id": "1",
        "cargo_id": "1",
        "forma_pagamento": "mensal",
        "situacao_vinculo": "ativo",
    }
    fid = cobol_bridge.funcionario_incluir(dados)
    return fid, 3000.00


def _servidor(port):
    env = os.environ.copy()
    env["BECRP_DEV_SEED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-u", "-B", os.path.join(ROOT, "server.py"), str(port)],
        cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            st, body = _req("GET", "/api/folha/empresa", token=None)
            if st in (200, 401, 403):
                return proc
        except Exception:
            pass
        time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("Servidor não subiu a tempo")


def main():
    global PORT
    if "--port" in sys.argv:
        PORT = int(sys.argv[sys.argv.index("--port") + 1])

    _backup()
    try:
        _garantir_usuarios()
        fid, salario = _funcionario_teste()
        proc = _servidor(PORT)
        try:
            token = _token("bruno")
            token2 = _token("rh2")
            check("token admin disponivel", bool(token))
            check("token instrutor disponivel", bool(token2))

            # ---- CRUD + Decisão 1 (motivo obrigatório) ----
            st, r = _post("/api/folha/complementar/incluir", token, {
                "funcionario_id": fid, "competencia": "2026/07",
                "competencia_ref": "2026/06", "motivo": "", "valor": "500.00",
            })
            check("incluir sem motivo -> 400", st == 400, f"st={st}")

            st, r = _post("/api/folha/complementar/incluir", token, {
                "funcionario_id": fid, "competencia": "2026/07",
                "competencia_ref": "2026/06", "motivo": "hora extra nao lancada",
                "valor": "500.00",
            })
            check("incluir com motivo -> ok", st == 200 and r.get("id"), f"st={st} r={r.get('message')}")
            c1 = r.get("id")
            if r.get("id"):
                check("diferenca positiva tributa INSS", float(r.get("inss") or 0) > 0)
                check("resposta traz inss/irrf/liquido",
                      all(k in r for k in ("inss", "irrf", "liquido")))
                liq_esperado = float(r.get("valor") or 0) - float(r.get("inss") or 0) - float(r.get("irrf") or 0)
                check("liquido = valor - inss - irrf", quase(r.get("liquido"), liq_esperado))
                check("situacao inicial C (calculada)", (r.get("situacao") or "C") == "C")

            # ---- Decisão 2: negativo exige motivo específico ----
            st, r = _post("/api/folha/complementar/incluir", token, {
                "funcionario_id": fid, "competencia": "2026/07",
                "competencia_ref": "2026/06", "motivo": "hora extra nao lancada",
                "valor": "-200.00",
            })
            check("negativo com motivo nao validado -> 400", st == 400, f"st={st}")

            st, r = _post("/api/folha/complementar/incluir", token, {
                "funcionario_id": fid, "competencia": "2026/07",
                "competencia_ref": "2026/06", "motivo": "devolucao",
                "valor": "-200.00",
            })
            check("negativo com motivo validado (devolucao) -> ok", st == 200 and r.get("id"), f"st={st} r={r.get('message')}")
            c2 = r.get("id")
            if r.get("id"):
                check("liquido negativo (devolucao)", float(r.get("liquido") or 0) < 0)
                check("devolucao nao tributa", quase(r.get("inss"), 0) and quase(r.get("irrf"), 0))

            # ---- Limite legal de desconto (70% do salário) ----
            st, r = _post("/api/folha/complementar/incluir", token, {
                "funcionario_id": fid, "competencia": "2026/07",
                "competencia_ref": "2026/06", "motivo": "devolucao",
                "valor": f"-{salario * 0.71:.2f}",
            })
            check("desconto acima de 70% do salario -> 400", st == 400, f"st={st}")

            # ---- Decisão 3: múltiplas complementares por competência ----
            st, r = _get("/api/folha/complementares", token)
            check("GET listar complementares", st == 200)
            comps = r.get("complementares") or []
            check("duas complementares na mesma competencia (Decisao 3)", len(comps) >= 2,
                  f"n={len(comps)}")
            check("motivos distintos preservados", len({x.get("motivo") for x in comps[:2]}) >= 2)

            # ---- Regra 3 + RFC-009: separação de funções ----
            st, r = _post("/api/folha/complementar/fechar", token, {"id": c1})
            check("fechar pelo operador -> 403 (aprovador = operador)", st == 403, f"st={st}")

            st, r = _post("/api/folha/complementar/validar", token, {"id": c1})
            check("validar (C -> V) pelo operador", st == 200, f"st={st}")

            st, r = _post("/api/folha/complementar/fechar", token2, {"id": c1})
            check("fechar por aprovador distinto -> ok", st == 200, f"st={st} r={r.get('message')}")
            enc_dif = (r or {}).get("encargos_diferenca") or {}
            check("fechar retorna encargos sobre a diferenca (Decisao 4)",
                  float(enc_dif.get("fgts") or 0) > 0, f"enc={enc_dif}")
            if enc_dif:
                check("base de encargos = soma das diferencas positivas",
                      quase(enc_dif.get("base"), 500.00), f"base={enc_dif.get('base')}")
            lanc = (r or {}).get("lancamentos_contabeis") or []
            check("fechamento gera lancamentos contabeis dos encargos", len(lanc) > 0,
                  f"n={len(lanc)}")

            st, r = _get("/api/folha/complementar/encargos?competencia=2026/07", token)
            check("GET encargos da diferenca", st == 200, f"st={st}")
            if st == 200:
                enc2 = (r.get("encargos") or {})
                check("encargos GET consistentes (fgts>0)", float(enc2.get("fgts") or 0) > 0)

            st, r = _get("/api/folha/complementar/holerite?id=" + str(c1), token)
            check("GET holerite complementar distinto (Regra 5)", st == 200, f"st={st}")
            if st == 200:
                hol = r.get("holerite") or {}
                check("holerite marca tipo COMPLEMENTAR", hol.get("tipo") == "COMPLEMENTAR")
                check("holerite exibe competencia_ref + motivo",
                      bool(hol.get("competencia_ref")) and bool(hol.get("motivo")))
                check("holerite exibe apenas as diferencas (valor/liquido)",
                      hol.get("valor") is not None and hol.get("liquido") is not None)

            st, r = _post("/api/folha/complementar/pagar", token2, {"id": c1, "data_pagamento": "2026-08-05"})
            check("pagar pelo aprovador -> 403 (tesouraria = aprovador)", st == 403, f"st={st}")

            st, r = _post("/api/folha/complementar/pagar", token, {"id": c1, "data_pagamento": "2026-08-05"})
            check("pagar pela tesouraria (operador) -> ok", st == 200, f"st={st} r={r.get('message')}")

            # ---- Estado final + trilha de auditoria (Regra 6) ----
            st, r = _get("/api/folha/complementares", token)
            comp1 = next((x for x in (r.get("complementares") or []) if x.get("id") == c1), {})
            check("complementar 1 ficou PAGA", comp1.get("situacao") == "P",
                  f"sit={comp1.get('situacao')}")
            st, r = _get("/api/folha/auditoria", token)
            eventos = r.get("eventos") or []
            acoes = {e.get("acao") for e in eventos}
            check("trilha tem incluir_complementar", "incluir_complementar" in acoes)
            check("trilha tem fechar_complementar", "fechar_complementar" in acoes)

            # ---- Excluir: bloqueado para paga, ok para não paga ----
            st, r = _post("/api/folha/complementar/excluir", token, {"id": c1})
            check("excluir complementar PAGA -> 400 (imutavel)", st == 400, f"st={st}")
            st, r = _post("/api/folha/complementar/excluir", token, {"id": c2})
            check("excluir complementar nao paga -> ok", st == 200, f"st={st}")

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
    finally:
        _restore()

    print(f"\nRFC-013: {PASS} checks OK, {FAIL} falhas")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
