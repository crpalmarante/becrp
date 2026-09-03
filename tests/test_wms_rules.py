"""Testes das regras push/pull do WMS (wms_rules.py)."""

import pytest

import inventory_mvp
import wms_locations
import wms_operation_types
import wms_operations
import wms_rules
import wms_warehouses


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    """Isola arquivos JSON de inventário e WMS para não tocar dados reais."""
    for name in ("MOVEMENTS_FILE", "BALANCES_FILE", "TRANSIT_FILE", "COUNTS_FILE"):
        monkeypatch.setattr(inventory_mvp, name, str(tmp_path / f"{name}.json"))
    monkeypatch.setattr(wms_rules, "DATA_FILE", str(tmp_path / "wms_rules.json"))
    monkeypatch.setattr(wms_operations, "DATA_FILE", str(tmp_path / "wms_operations.json"))
    monkeypatch.setattr(wms_operation_types, "DATA_FILE", str(tmp_path / "wms_op_types.json"))
    monkeypatch.setattr(wms_warehouses, "DATA_FILE", str(tmp_path / "wms_warehouses.json"))
    monkeypatch.setattr(wms_locations, "DATA_FILE", str(tmp_path / "wms_locations.json"))
    monkeypatch.setenv("LOCALIZACOES_DAT", str(tmp_path / "localizacoes.dat"))
    monkeypatch.setenv("LOCALIZACOES_TMP", str(tmp_path / "localizacoes.tmp"))
    wms_warehouses.ensure_seed()
    wms_locations.ensure_seed()


def _seed_saldos():
    inventory_mvp.inventory_apply_movement("receive", "DC-01", "1", 30, location_id="A01-01-01")
    inventory_mvp.inventory_apply_movement("receive", "DC-01", "1", 2, location_id="PCK-01")
    inventory_mvp.inventory_apply_movement("receive", "DC-01", "2", 50, location_id="REC-DOCK-01")


def _regra_pull(**over):
    payload = {
        "nome": "Reposição picking",
        "tipo": "pull",
        "armazem": "DC-01",
        "origem": "A01-01-01",
        "destino": "PCK-01",
        "produto_id": "1",
        "nivel_min": 5,
        "qtd_reposicao": 10,
    }
    payload.update(over)
    return wms_rules.create_regra(payload)


def _regra_push(**over):
    payload = {
        "nome": "Escoamento doca",
        "tipo": "push",
        "armazem": "DC-01",
        "origem": "REC-DOCK-01",
        "destino": "A01-01-02",
        "produto_id": "2",
        "nivel_max": 20,
    }
    payload.update(over)
    return wms_rules.create_regra(payload)


def test_regra_pull_gera_sugestao():
    _seed_saldos()
    r = _regra_pull()
    ev = wms_rules.wms_rules_evaluate()
    sug = [s for s in ev["sugestoes"] if s["regra_id"] == r["id"]]
    assert len(sug) == 1
    s = sug[0]
    assert s["tipo"] == "pull"
    assert s["origem"] == "A01-01-01" and s["destino"] == "PCK-01"
    assert s["qtd"] == 10
    assert s["status"] == "ok"


def test_regra_pull_destino_acima_do_minimo_nao_dispara():
    _seed_saldos()
    inventory_mvp.inventory_apply_movement("receive", "DC-01", "1", 10, location_id="PCK-01")
    r = _regra_pull(nivel_min=5)
    ev = wms_rules.wms_rules_evaluate()
    assert not [s for s in ev["sugestoes"] if s["regra_id"] == r["id"]]


def test_regra_pull_sem_estoque_origem():
    # origem vazia para o produto 1
    r = _regra_pull()
    ev = wms_rules.wms_rules_evaluate()
    sug = [s for s in ev["sugestoes"] if s["regra_id"] == r["id"]]
    assert len(sug) == 1
    assert sug[0]["status"] == "sem_estoque_origem"


def test_regra_push_gera_sugestao_do_excedente():
    _seed_saldos()
    r = _regra_push()
    ev = wms_rules.wms_rules_evaluate()
    sug = [s for s in ev["sugestoes"] if s["regra_id"] == r["id"]]
    assert len(sug) == 1
    s = sug[0]
    assert s["tipo"] == "push"
    assert s["qtd"] == 30  # 50 - 20
    assert s["status"] == "ok"


def test_regra_push_respeita_capacidade_do_destino():
    # A01-01-02 tem capacidade 40; destino já tem 35 → só cabem 5
    inventory_mvp.inventory_apply_movement("receive", "DC-01", "2", 50, location_id="REC-DOCK-01")
    inventory_mvp.inventory_apply_movement("receive", "DC-01", "2", 35, location_id="A01-01-02")
    r = _regra_push()
    ev = wms_rules.wms_rules_evaluate()
    sug = [s for s in ev["sugestoes"] if s["regra_id"] == r["id"]]
    assert len(sug) == 1
    assert sug[0]["qtd"] == 5
    assert sug[0]["status"] == "parcial"


def test_regra_inativa_nao_e_avaliada():
    _seed_saldos()
    r = _regra_pull()
    wms_rules.set_ativo(r["id"], False)
    ev = wms_rules.wms_rules_evaluate()
    assert not [s for s in ev["sugestoes"] if s["regra_id"] == r["id"]]


def test_apply_modo_operacao_cria_operacao_wms():
    _seed_saldos()
    r = _regra_pull()
    out = wms_rules.wms_rules_apply(regra_ids=[r["id"]], usuario="teste")
    assert out["resumo"]["aplicadas"] == 1
    ops = wms_operations.list_operacoes()
    criadas = [o for o in ops["operacoes"] if str(o.get("id") or "").startswith("OP-REGRA-")]
    assert len(criadas) == 1
    op = criadas[0]
    assert op["tipo"] == "TRF-INT"
    assert op["linhas"][0]["loc_origem"] == "A01-01-01"
    assert op["linhas"][0]["loc_destino"] == "PCK-01"
    assert op["linhas"][0]["qtd"] == 10
    assert op["origem"] == "regra:pull"


def test_apply_modo_direto_move_estoque():
    _seed_saldos()
    r = _regra_pull(modo_aplicar="direto")
    antes_origem = inventory_mvp.inventory_balance("DC-01", "1", location_id="A01-01-01")
    antes_destino = inventory_mvp.inventory_balance("DC-01", "1", location_id="PCK-01")
    out = wms_rules.wms_rules_apply(regra_ids=[r["id"]], usuario="teste")
    assert out["resumo"]["aplicadas"] == 1
    assert inventory_mvp.inventory_balance("DC-01", "1", location_id="A01-01-01") == antes_origem - 10
    assert inventory_mvp.inventory_balance("DC-01", "1", location_id="PCK-01") == antes_destino + 10
    # nenhuma operação WMS criada no modo direto
    ops = wms_operations.list_operacoes()
    assert not [o for o in ops["operacoes"] if str(o.get("id") or "").startswith("OP-REGRA-")]


def test_apply_filtra_regra_ids():
    _seed_saldos()
    r1 = _regra_pull()
    r2 = _regra_push()
    out = wms_rules.wms_rules_apply(regra_ids=[r1["id"]], usuario="teste")
    ids = {a["regra_id"] for a in out["aplicadas"]}
    assert ids == {r1["id"]}


def test_validacao_rejeita_origem_destino_iguais():
    with pytest.raises(ValueError, match="diferentes"):
        _regra_pull(destino="A01-01-01")


def test_validacao_rejeita_localizacao_inexistente():
    with pytest.raises(ValueError, match="não encontrada"):
        _regra_pull(origem="XYZ-99")


def test_validacao_pull_exige_niveis():
    with pytest.raises(ValueError, match="nivel_min"):
        _regra_pull(nivel_min=0)
    with pytest.raises(ValueError, match="qtd_reposicao"):
        _regra_pull(nivel_min=5, qtd_reposicao=0)


def test_validacao_push_exige_nivel_max():
    with pytest.raises(ValueError, match="nivel_max"):
        _regra_push(nivel_max=0)


def test_duplicidade_id_rejeitada():
    wms_rules.create_regra({
        "nome": "Regra id fixo", "tipo": "pull",
        "armazem": "DC-01", "origem": "A01-01-01", "destino": "PCK-01",
        "produto_id": "1", "nivel_min": 2, "qtd_reposicao": 3, "id": "R99",
    })
    with pytest.raises(ValueError, match="já existe"):
        wms_rules.create_regra({
            "nome": "Duplicada", "tipo": "pull",
            "armazem": "DC-01", "origem": "A01-01-01", "destino": "PCK-01",
            "produto_id": "1", "nivel_min": 2, "qtd_reposicao": 3, "id": "R99",
        })


# ──────────────────────── pull por demanda (cascata) ────────────────────────

def _seed_cadeia():
    """Cria a rota em duas etapas: A01-01-01 (estoque) → SHP-STAGE (envio) → CLIENTE."""
    wms_locations.create_localizacao({
        "codigo": "CLIENTE", "nome": "Local do cliente", "tipo": "virtual",
        "armazem": "DC-01", "area": "SHP", "status": "available",
    })
    inventory_mvp.inventory_apply_movement("receive", "DC-01", "1", 30, location_id="A01-01-01")
    inventory_mvp.inventory_apply_movement("receive", "DC-01", "1", 4, location_id="SHP-STAGE")
    r_envio = wms_rules.create_regra({
        "nome": "Envio ao cliente", "tipo": "pull", "armazem": "DC-01",
        "origem": "SHP-STAGE", "destino": "CLIENTE",
        "produto_id": "1", "nivel_min": 1, "qtd_reposicao": 1,
    })
    r_repo = wms_rules.create_regra({
        "nome": "Reposição do envio", "tipo": "pull", "armazem": "DC-01",
        "origem": "A01-01-01", "destino": "SHP-STAGE",
        "produto_id": "1", "nivel_min": 1, "qtd_reposicao": 1,
    })
    return r_envio, r_repo


def test_pull_demand_cascata_duas_etapas():
    _seed_cadeia()
    plano = wms_rules.wms_rules_pull_demand("DC-01", "CLIENTE", [{"produto_id": "1", "qtd": 10}])
    assert plano["resumo"]["passos"] == 2
    assert plano["resumo"]["nao_resolvido"] == 0
    # ordem de execução: separação (upstream) primeiro, envio por último
    p1, p2 = plano["passos"]
    assert p1["etapa"] == "separacao" and p1["origem"] == "A01-01-01" and p1["destino"] == "SHP-STAGE"
    assert p1["qtd"] == 6  # 10 - 4 já em SHP
    assert p2["etapa"] == "envio" and p2["origem"] == "SHP-STAGE" and p2["destino"] == "CLIENTE"
    assert p2["qtd"] == 4


def test_pull_demand_destino_final_ja_coberto():
    _seed_cadeia()
    inventory_mvp.inventory_apply_movement("receive", "DC-01", "1", 10, location_id="CLIENTE")
    plano = wms_rules.wms_rules_pull_demand("DC-01", "CLIENTE", [{"produto_id": "1", "qtd": 5}])
    assert plano["resumo"]["passos"] == 0
    assert plano["resumo"]["nao_resolvido"] == 0


def test_pull_demand_falta_nao_resolvida():
    _seed_cadeia()
    plano = wms_rules.wms_rules_pull_demand("DC-01", "CLIENTE", [{"produto_id": "1", "qtd": 100}])
    # 4 em SHP + 30 em A01 = 34 resolvidos; sobram 66
    assert plano["resumo"]["passos"] == 2
    assert len(plano["nao_resolvido"]) == 1
    assert plano["nao_resolvido"][0]["falta"] == 66
    assert plano["nao_resolvido"][0]["destino"] == "A01-01-01"


def test_pull_demand_sem_regra_para_destino():
    _seed_cadeia()
    # nenhuma regra tem REC-DOCK-01 como destino
    plano = wms_rules.wms_rules_pull_demand("DC-01", "REC-DOCK-01", [{"produto_id": "1", "qtd": 5}])
    assert plano["resumo"]["passos"] == 0
    assert len(plano["nao_resolvido"]) == 1


def test_pull_demand_apply_ordem_execucao():
    _seed_cadeia()
    out = wms_rules.wms_rules_pull_demand_apply("DC-01", "CLIENTE", [{"produto_id": "1", "qtd": 10}], usuario="teste")
    assert out["resumo"]["aplicados"] == 2
    ops = wms_operations.list_operacoes()["operacoes"]
    criadas = [o for o in ops if str(o.get("id") or "").startswith("OP-PULL-")]
    assert len(criadas) == 2
    # o sufixo do id codifica a ordem de execução: -01 separação, -02 envio
    por_id = {str(o.get("id") or "")[-2:]: o for o in criadas}
    sep = por_id["01"]
    env = por_id["02"]
    assert sep["linhas"][0]["loc_origem"] == "A01-01-01"
    assert sep["linhas"][0]["loc_destino"] == "SHP-STAGE"
    assert sep["origem"] == "demanda:separacao"
    assert env["linhas"][0]["loc_origem"] == "SHP-STAGE"
    assert env["linhas"][0]["loc_destino"] == "CLIENTE"
    assert env["origem"] == "demanda:envio"


def test_pull_demand_escopo_produto():
    _seed_cadeia()
    # regra de outro produto não atende a demanda do produto 1
    wms_rules.create_regra({
        "nome": "Envio produto 2", "tipo": "pull", "armazem": "DC-01",
        "origem": "SHP-STAGE", "destino": "CLIENTE",
        "produto_id": "2", "nivel_min": 1, "qtd_reposicao": 1,
    })
    plano = wms_rules.wms_rules_pull_demand("DC-01", "CLIENTE", [{"produto_id": "1", "qtd": 10}])
    # usa a regra do produto 1 (R envio p/ produto 1), não a do produto 2
    assert all(p["regra_id"] != "" for p in plano["passos"])
    ids = {p["regra_id"] for p in plano["passos"]}
    regra_prod2 = [r for r in wms_rules.list_regras()["regras"] if r.get("produto_id") == "2"]
    assert regra_prod2[0]["id"] not in ids


def test_regra_por_categoria_avalia_todos_os_produtos():
    # produtos da categoria Alimentacao sem saldo no destino disparam
    inventory_mvp.inventory_apply_movement("receive", "DC-01", "1", 20, location_id="A01-01-01")
    r = wms_rules.create_regra({
        "nome": "Reposição categoria",
        "tipo": "pull",
        "armazem": "DC-01",
        "origem": "A01-01-01",
        "destino": "PCK-01",
        "categoria": "Alimentacao",
        "nivel_min": 3,
        "qtd_reposicao": 5,
    })
    ev = wms_rules.wms_rules_evaluate()
    sug = [s for s in ev["sugestoes"] if s["regra_id"] == r["id"]]
    # produto 1 tem saldo na origem → ok; demais da categoria → sem estoque na origem
    assert any(s["produto_id"] == "1" and s["status"] == "ok" for s in sug)
    assert any(s["status"] == "sem_estoque_origem" for s in sug)
