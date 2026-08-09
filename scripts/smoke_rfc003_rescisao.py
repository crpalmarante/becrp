#!/usr/bin/env python3
"""Smoke E2E do RFC-003 — Admissão e Demissão (Rescisão).

Cobre (motor COBOL via cobol_bridge):
  - rescisao_calcular: verbas do acerto (decisão 1 — calcula e exibe)
    * saldo de salário, aviso prévio (indenizado vs trabalhado),
      férias + 1/3, 13º proporcional, FGTS 8%, multa FGTS (40% sem justa
      causa / 20% acordo / 0 demais) e prazo de pagamento (data + 10 dias)
  - validations: motivo obrigatório/válido (RFC-003 §3.1), dupla rescisão
    pendente bloqueada, rescisão paga não pode pagar/excluir de novo
  - gerir_funcionarios desligar/reativar: status do vínculo "desligado"
    com data_dem + motivo (RFC-003 §3.3.7 e §3.4.1)

Faz backup/restauração de dados/rescisoes.dat e dados/funcionarios.dat.
"""

from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cobol_bridge

FILES = ("dados/rescisoes.dat", "dados/rescisoes.tmp", "dados/funcionarios.dat")
BACKUP = "/tmp/becrp_rfc003_backup"

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
        elif os.path.exists(marker):
            if os.path.exists(dst):
                os.remove(dst)
    shutil.rmtree(BACKUP, ignore_errors=True)


def quase(a, b, tol=0.01):
    return abs(float(a) - float(b)) <= tol


def main():
    _backup()
    try:
        funcs = cobol_bridge.funcionarios_listar()
        ativos = [f for f in funcs if (f.get("situacao_vinculo") or "").strip() != "desligado"]
        if not ativos:
            print("⚠️  precisa de pelo menos 1 funcionário ativo no funcionarios.dat")
            sys.exit(2)
        x = ativos[0]
        # cria um segundo funcionário só para os testes (some no restore)
        novo_id = cobol_bridge.funcionario_incluir({
            "nome": "Smoke RFC003",
            "usuario": "smoke_rfc003",
            "senha": "smoke123",
            "permissoes": "operador",
            "cpf": "99988877766",
            "data_nasc": "1990-01-01",
            "data_adm": "2026-01-05",
            "salario": 3000.00,
        })
        y = next(f for f in cobol_bridge.funcionarios_listar() if f["id"] == novo_id)
        print(f"Usando funcionários ativos: #{x['id']} {x['nome']} e #{y['id']} {y['nome']}")

        base = {
            "funcionario_id": x["id"],
            "nome": x["nome"],
            "motivo": "sem-justa-causa",
            "data_deslig": "2026-08-08",
            "tipo_aviso": "indenizado",
            "dias_aviso": 33,
            "saldo_dias": 8,
            "ferias_venc_dias": 30,
            "ferias_prop_meses": 6,
            "13_prop_meses": 7,
            "salario_base": 3000.00,
        }

        print("\n1. Cálculo do acerto (decisão 1 — valores para conferência)")
        r = cobol_bridge.rescisao_calcular(base)
        check("saldo de salário = 8 dias * 100,00", quase(r["saldo_salario"], 800.00))
        check("aviso prévio indenizado = 33 dias", quase(r["aviso_previo"], 3300.00))
        check("férias (venc + prop + 1/3)", quase(r["ferias"], 4500.00))
        check("13º proporcional (7 meses)", quase(r["decimo_proporcional"], 1750.00))
        check("FGTS 8% das verbas", quase(r["fgts"], 948.00))
        check("multa FGTS 40% (sem justa causa)", quase(r["multa_fgts"], 379.20))
        check("líquido = verbas + FGTS + multa", quase(r["liquido"], 13177.20))
        check("prazo de pagamento = deslig + 10 dias", r["prazo_pagamento"] == "2026-08-18")

        print("\n2. Aviso trabalhado → sem aviso indenizado (decisão 2)")
        r2 = cobol_bridge.rescisao_calcular({**base, "motivo": "pedido-demissao", "tipo_aviso": "trabalhado", "saldo_dias": 5})
        check("aviso prévio = 0 (trabalhado)", quase(r2["aviso_previo"], 0.00))
        check("multa FGTS = 0 (pedido de demissão)", quase(r2["multa_fgts"], 0.00))

        print("\n2b. Precisão — salário não múltiplo de 30 (truncamento v1)")
        r3 = cobol_bridge.rescisao_calcular({
            **base, "salario_base": 2800.00, "motivo": "pedido-demissao",
            "tipo_aviso": "trabalhado", "dias_aviso": 0, "saldo_dias": 8,
            "ferias_venc_dias": 0, "ferias_prop_meses": 0, "13_prop_meses": 0,
        })
        # 2800/30 = 93,33… (truncado p/ 2 casas no COBOL) → 8 dias = 746,64
        check("2800/30 → saldo 8 dias = 746,64", quase(r3["saldo_salario"], 746.64))
        check("aviso e multa zerados", quase(r3["aviso_previo"], 0.00) and quase(r3["multa_fgts"], 0.00))

        print("\n3. Validação de motivo (RFC-003 §3.1)")
        try:
            cobol_bridge.rescisao_calcular({**base, "motivo": ""})
            check("motivo vazio → erro", False)
        except Exception as e:
            check("motivo vazio → erro", "obrigatorio" in str(e).lower(), str(e))
        try:
            cobol_bridge.rescisao_calcular({**base, "motivo": "motivo-invalido"})
            check("motivo inválido → erro", False)
        except Exception as e:
            check("motivo inválido → erro", "invalido" in str(e).lower(), str(e))

        print("\n4. Registro da rescisão (folha_pagamento)")
        rinc = cobol_bridge.rescisao_incluir(base)
        rid = rinc.get("id")
        check("incluir → id retornado", rid and int(rid) > 0)
        rescisoes = cobol_bridge.rescisao_listar()
        achou = next((rr for rr in rescisoes if str(rr.get("id")) == str(rid)), None)
        check("listar contém a rescisão", achou is not None)
        check("motivo gravado", achou and achou.get("motivo") == "sem-justa-causa")
        check("prazo gravado", achou and achou.get("prazo_pagamento") == "2026-08-18")
        check("situação inicial = C", achou and achou.get("situacao") == "C")
        try:
            cobol_bridge.rescisao_incluir(base)
            check("dupla rescisão pendente → bloqueada", False)
        except Exception as e:
            check("dupla rescisão pendente → bloqueada", "pendente" in str(e).lower(), str(e))

        print("\n5. Pagamento (RFC-003 §3.4.2 — acerto imutável após pagamento)")
        check("pagar → OK", cobol_bridge.rescisao_pagar(rid))
        try:
            cobol_bridge.rescisao_pagar(rid)
            check("pagar 2ª vez → bloqueado", False)
        except Exception as e:
            check("pagar 2ª vez → bloqueado", "ja paga" in str(e).lower(), str(e))
        try:
            cobol_bridge.rescisao_excluir(rid)
            check("excluir rescisão paga → bloqueado", False)
        except Exception as e:
            check("excluir rescisão paga → bloqueado", "paga" in str(e).lower(), str(e))

        print("\n6. Status do vínculo — desligar/reativar (RFC-003 §3.3.7)")
        check("desligar → OK", cobol_bridge.funcionario_desligar(x["id"], "2026-08-08", "sem-justa-causa"))
        fx = next(f for f in cobol_bridge.funcionarios_listar() if f["id"] == x["id"])
        check("situação = desligado", fx.get("situacao_vinculo") == "desligado", fx.get("situacao_vinculo"))
        check("data_dem gravada", fx.get("data_dem") == "2026-08-08", fx.get("data_dem"))
        check("motivo gravado", fx.get("motivo_deslig") == "sem-justa-causa", fx.get("motivo_deslig"))
        try:
            cobol_bridge.funcionario_desligar(x["id"], "2026-08-09", "acordo")
            check("desligar de novo → bloqueado", False)
        except Exception as e:
            check("desligar de novo → bloqueado", "ja desligado" in str(e).lower(), str(e))

        print("\n7. Exclusão de rescisão (não paga) + reativação")
        rinc2 = cobol_bridge.rescisao_incluir({**base, "funcionario_id": y["id"], "nome": y["nome"]})
        rid2 = rinc2.get("id")
        check("incluir rescisão p/ 2º funcionário", int(rid2) > 0)
        rescisoes2 = cobol_bridge.rescisao_listar()
        check("listar com 2 registros (JSON íntegro)", len(rescisoes2) == 2, f"{len(rescisoes2)}")
        check("excluir rescisão 'C' → OK", cobol_bridge.rescisao_excluir(rid2))
        check("reativar → OK", cobol_bridge.funcionario_reativar(x["id"]))
        fx2 = next(f for f in cobol_bridge.funcionarios_listar() if f["id"] == x["id"])
        check("situação volta a ativo", fx2.get("situacao_vinculo") == "ativo", fx2.get("situacao_vinculo"))
        check("data_dem limpa", not fx2.get("data_dem"))
        check("motivo limpo", not fx2.get("motivo_deslig"))

        print(f"\n{'='*50}\nResultado: {PASS} ok / {FAIL} falhas\n{'='*50}")
        sys.exit(0 if FAIL == 0 else 1)
    finally:
        _restore()


if __name__ == "__main__":
    main()
