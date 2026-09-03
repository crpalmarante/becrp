from datetime import datetime

import pytest

import inventory_mvp


@pytest.fixture(autouse=True)
def _isolated_files(tmp_path, monkeypatch):
    """Isola os arquivos JSON do inventário para não tocar dados reais."""
    for name in ("MOVEMENTS_FILE", "BALANCES_FILE", "TRANSIT_FILE", "COUNTS_FILE"):
        monkeypatch.setattr(inventory_mvp, name, str(tmp_path / f"{name}.json"))


def test_balance_apos_recebimento():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    assert inventory_mvp.inventory_balance("matriz", "1") == 10.0
    assert inventory_mvp.inventory_balance("filial_sp", "1") == 0.0


def test_transferencia_move_saldo():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    inventory_mvp.inventory_transfer("matriz", "filial_sp", [{"produto_id": "1", "qty": 4}])
    assert inventory_mvp.inventory_balance("matriz", "1") == 6.0
    assert inventory_mvp.inventory_balance("filial_sp", "1") == 4.0


def test_transferencia_saldo_insuficiente_bloqueia():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 3)
    with pytest.raises(ValueError, match="estoque insuficiente"):
        inventory_mvp.inventory_transfer("matriz", "filial_sp", [{"produto_id": "1", "qty": 5}])


def test_ajuste_in_e_out():
    inventory_mvp.inventory_adjust("matriz", "1", 7, direcao="in", nota="teste")
    assert inventory_mvp.inventory_balance("matriz", "1") == 7.0
    inventory_mvp.inventory_adjust("matriz", "1", 2, direcao="out", nota="teste")
    assert inventory_mvp.inventory_balance("matriz", "1") == 5.0


def test_ajuste_saida_maior_que_saldo_bloqueia():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 2)
    with pytest.raises(ValueError, match="maior que saldo"):
        inventory_mvp.inventory_adjust("matriz", "1", 5, direcao="out", nota="teste")


def test_contagem_fisica_aplica_divergencias():
    # saldo inicial: produto 1 = 50, produto 10 = 90
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 50)
    inventory_mvp.inventory_apply_movement("receive", "matriz", "10", 90)

    count = inventory_mvp.inventory_start_count("matriz", nota="contagem teste")
    assert count["status"] == "aberto"
    assert len(count["itens"]) == 2

    inventory_mvp.inventory_count_set_items(count["id"], [
        {"produto_id": "1", "qtd_contada": 48},
        {"produto_id": "10", "qtd_contada": 95},
    ])
    closed = inventory_mvp.inventory_close_count(count["id"])
    assert closed["status"] == "fechado"
    assert closed["resumo"]["total_ajustes"] == 2
    assert inventory_mvp.inventory_balance("matriz", "1") == 48.0
    assert inventory_mvp.inventory_balance("matriz", "10") == 95.0


def test_novos_tipos_operacao_concerto_demonstracao_devolucao():
    # remessa para concerto e demonstração saem; devolução entra
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    inventory_mvp.inventory_apply_movement("concerto", "matriz", "1", 3)
    inventory_mvp.inventory_apply_movement("demonstracao", "matriz", "1", 2)
    inventory_mvp.inventory_apply_movement("devolucao", "matriz", "1", 5)
    assert inventory_mvp.inventory_balance("matriz", "1") == 10.0


def test_contagem_fechada_nao_aceita_itens():
    count = inventory_mvp.inventory_start_count("matriz")
    inventory_mvp.inventory_close_count(count["id"])
    with pytest.raises(ValueError, match="já fechada"):
        inventory_mvp.inventory_count_set_items(count["id"], [{"produto_id": "1", "qtd_contada": 1}])


def test_kpis_valor_giro_cobertura_e_ruptura():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    produtos = [{"id": "1", "nome": "Arroz", "preco_custo": 5.0}]
    vendas = [{
        "id": 1, "data": "2026-07-12", "itens": [{"prod_id": "1", "qtd": 4}]
    }]
    kpis = inventory_mvp.inventory_kpis(estabelecimento_id="matriz", dias=90, produtos=produtos, vendas=vendas)
    assert kpis["unidades_estoque"] == 10.0
    assert kpis["valor_estoque"] == 50.0
    assert kpis["unidades_vendidas"] == 4.0
    assert kpis["giro"] > 0
    assert kpis["cobertura_dias"] is not None
    assert kpis["ruptura"] == []


def test_kpis_ruptura_quando_vendeu_e_zerou():
    # produto 2 vendeu 3 e nunca teve saldo -> ruptura
    produtos = [{"id": "1", "nome": "A", "preco_custo": 1.0}, {"id": "2", "nome": "B", "preco_custo": 2.0}]
    vendas = [{
        "id": 1, "data": "2026-07-12", "itens": [{"prod_id": "2", "qtd": 3}]
    }]
    kpis = inventory_mvp.inventory_kpis(estabelecimento_id="matriz", dias=90, produtos=produtos, vendas=vendas)
    assert len(kpis["ruptura"]) == 1
    assert kpis["ruptura"][0]["produto_id"] == "2"
    assert kpis["ruptura"][0]["vendido"] == 3.0


def test_kpis_ignora_vendas_fora_do_periodo():
    produtos = [{"id": "1", "nome": "A"}]
    vendas = [{"id": 1, "data": "2020-01-01", "itens": [{"prod_id": "1", "qtd": 9}]}]
    kpis = inventory_mvp.inventory_kpis(estabelecimento_id="matriz", dias=30, produtos=produtos, vendas=vendas)
    assert kpis["unidades_vendidas"] == 0.0


def test_alerts_abaixo_do_minimo():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 3)
    produtos = [
        {"id": "1", "nome": "Arroz", "estoque_min": 5},
        {"id": "2", "nome": "Feijao", "estoque_min": 1},
    ]
    alerts = inventory_mvp.inventory_alerts(estabelecimento_id="matriz", produtos=produtos)
    # produto 1: saldo 3 < mín 5 (faltam 2); produto 2: saldo 0 < mín 1
    assert len(alerts) == 2
    by_id = {a["produto_id"]: a for a in alerts}
    assert by_id["1"]["faltam"] == 2.0
    assert by_id["2"]["faltam"] == 1.0
    assert alerts[0]["faltam"] >= alerts[1]["faltam"]  # ordenado por falta desc


def test_report_filtros_e_totais():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    inventory_mvp.inventory_apply_movement("sale", "matriz", "1", 4)
    inventory_mvp.inventory_apply_movement("receive", "filial_sp", "2", 7)
    rep = inventory_mvp.inventory_movements_report(estabelecimento_id="matriz")
    assert rep["total"] == 2
    assert rep["totais"]["entrada"] == 10.0
    assert rep["totais"]["saida"] == 4.0
    assert rep["totais"]["saldo_periodo"] == 6.0
    rep_tipo = inventory_mvp.inventory_movements_report(estabelecimento_id="matriz", tipo="sale")
    assert rep_tipo["total"] == 1
    assert rep_tipo["totais"]["saida"] == 4.0


def test_report_filtra_por_produto_e_periodo():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    inventory_mvp.inventory_apply_movement("receive", "matriz", "2", 5)
    rep = inventory_mvp.inventory_movements_report(produto_id="2")
    assert rep["total"] == 1
    # período vazio (data futura) -> nada
    rep_fut = inventory_mvp.inventory_movements_report(de="2099-01-01")
    assert rep_fut["total"] == 0


# ── Inventário rotativo ──────────────────────────────────────────────

def _seed_produtos():
    return [
        {"id": "1", "nome": "Arroz", "categoria": "Alimentacao", "localizacao": "A1-01", "preco_custo": 5.0},
        {"id": "2", "nome": "Feijao", "categoria": "Alimentacao", "localizacao": "A1-02", "preco_custo": 4.0},
        {"id": "3", "nome": "Oleo", "categoria": "Alimentacao", "localizacao": "A1-03", "preco_custo": 3.0},
        {"id": "10", "nome": "Detergente", "categoria": "Limpeza", "localizacao": "B1-01", "preco_custo": 2.0},
        {"id": "11", "nome": "Geladeira", "categoria": "EletroDomestico", "localizacao": "C1-01", "preco_custo": 100.0},
    ]


def test_ciclo_rotativo_por_categoria():
    # saldos: 1, 2, 3 na matriz; 10 e 11 também
    for pid in ("1", "2", "3", "10", "11"):
        inventory_mvp.inventory_apply_movement("receive", "matriz", pid, 10)
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz",
        escopo={"tipo": "categoria", "valor": "Alimentacao"},
        produtos=_seed_produtos(),
    )
    assert count["modo"] == "rotativo"
    assert count["escopo"]["tipo"] == "categoria"
    # só os 3 de Alimentacao
    pids = sorted(i["produto_id"] for i in count["itens"])
    assert pids == ["1", "2", "3"]
    # cada item carrega categoria/localização
    assert count["itens"][0]["categoria"] == "Alimentacao"
    assert count["itens"][0]["localizacao"] == "A1-01"


def test_ciclo_rotativo_por_localizacao():
    for pid in ("1", "2", "3", "10", "11"):
        inventory_mvp.inventory_apply_movement("receive", "matriz", pid, 10)
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz",
        escopo={"tipo": "localizacao", "valor": "B1-01"},
        produtos=_seed_produtos(),
    )
    pids = sorted(i["produto_id"] for i in count["itens"])
    assert pids == ["10"]


def test_ciclo_rotativo_por_produtos_e_amostra():
    for pid in ("1", "2", "3"):
        inventory_mvp.inventory_apply_movement("receive", "matriz", pid, 10)
    # lista explícita
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz",
        escopo={"tipo": "produtos", "valor": ["1", "3"]},
        produtos=_seed_produtos(),
    )
    assert sorted(i["produto_id"] for i in count["itens"]) == ["1", "3"]
    # amostra de 2
    count2 = inventory_mvp.inventory_start_cycle_count(
        "matriz",
        escopo={"tipo": "amostra", "valor": 2},
        produtos=_seed_produtos(),
    )
    assert len(count2["itens"]) == 2


def test_ciclo_rotativo_fecha_com_acuracia():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    inventory_mvp.inventory_apply_movement("receive", "matriz", "2", 10)
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz",
        escopo={"tipo": "categoria", "valor": "Alimentacao"},
        produtos=_seed_produtos(),
    )
    inventory_mvp.inventory_count_set_items(count["id"], [
        {"produto_id": "1", "qtd_contada": 8},   # divergência -2
        {"produto_id": "2", "qtd_contada": 10},  # ok
    ])
    closed = inventory_mvp.inventory_close_count(count["id"])
    assert closed["status"] == "fechado"
    assert closed["resumo"]["total_ajustes"] == 1
    assert closed["resumo"]["itens_contados"] == 2
    assert closed["resumo"]["acuracia"] == 50.0
    assert inventory_mvp.inventory_balance("matriz", "1") == 8.0


def test_sugestao_prioriza_sem_contagem_e_divergentes():
    # dá saldo para todos os produtos do seed (ABC considera só valor > 0)
    for pid in ("1", "2", "3", "10", "11"):
        inventory_mvp.inventory_apply_movement("receive", "matriz", pid, 10)
    # fecha um ciclo contando só o produto 2 (ok) — produto 1 fica sem contagem
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz",
        escopo={"tipo": "produtos", "valor": ["2"]},
        produtos=_seed_produtos(),
    )
    inventory_mvp.inventory_count_set_items(count["id"], [{"produto_id": "2", "qtd_contada": 10}])
    inventory_mvp.inventory_close_count(count["id"])

    sugg = inventory_mvp.inventory_cycle_suggest("matriz", produtos=_seed_produtos())
    assert sugg["total_candidatos"] == 5
    # sugestão prioriza classe A (item 11 = Geladeira, maior valor) e é semanal
    assert sugg["classe"] == "A"
    assert sugg["periodicidade"] == "semanal"
    by_id = {s["produto_id"]: s for s in sugg["sugestao"]}
    assert "11" in by_id  # geladeira (classe A, nunca contada) na sugestão
    assert by_id["11"]["score"] == 400  # vencida (300) + nunca contada (100)
    # sugestão agrupa só pela classe A (prioridade ABC), não inclui C
    assert "2" not in by_id


def test_ciclo_por_classe_abc():
    # geladeira (custo 100) domina o valor → classe A
    for pid in ("1", "2", "11"):
        inventory_mvp.inventory_apply_movement("receive", "matriz", pid, 10)
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz",
        escopo={"tipo": "classe", "valor": "A"},
        produtos=_seed_produtos(),
    )
    pids = sorted(i["produto_id"] for i in count["itens"])
    assert pids == ["11"]  # só a geladeira é classe A
    assert count["escopo"]["tipo"] == "classe"
    assert count["escopo"]["valor"] == "A"


def test_abc_classifica_por_valor():
    for pid in ("1", "2", "3", "10", "11"):
        inventory_mvp.inventory_apply_movement("receive", "matriz", pid, 10)
    abc = inventory_mvp.inventory_abc_classify("matriz", produtos=_seed_produtos())
    by_id = {r["produto_id"]: r for r in abc["itens"]}
    # geladeira = 10×100 = 1000 (87,7% do valor) → A; arroz (50) → B
    assert by_id["11"]["classe"] == "A"
    assert by_id["11"]["periodicidade"] == "semanal"
    assert by_id["11"]["periodicidade_dias"] == 7
    assert by_id["1"]["classe"] == "B"
    assert by_id["1"]["periodicidade"] == "mensal"
    assert by_id["1"]["periodicidade_dias"] == 30
    assert abc["resumo"]["A"]["itens"] == 1
    assert abc["resumo"]["A"]["periodicidade_dias"] == 7
    assert abc["resumo"]["B"]["periodicidade_dias"] == 30
    assert abc["resumo"]["C"]["periodicidade_dias"] == 60


# ── Agendamento de ciclos ────────────────────────────────────────────

def test_schedule_padrao_e_proxima_data():
    sched = inventory_mvp.inventory_schedule_default()
    assert sched["classes"]["A"]["periodicidade"] == "semanal"
    assert sched["classes"]["B"]["periodicidade"] == "mensal"
    assert sched["classes"]["C"]["periodicidade"] == "bimestral"
    # classe A semanal: próxima data > hoje
    prox = inventory_mvp._proxima_data("A", sched["classes"]["A"])
    assert prox is not None
    assert prox > datetime.now().date().isoformat()
    # classe desativada → sem próxima data
    cfg = dict(sched["classes"]["A"], ativo=False)
    assert inventory_mvp._proxima_data("A", cfg) is None


def test_schedule_due_identifica_vencidos():
    # classe A (semanal): nunca contada → vencida
    for pid in ("1", "2", "11"):
        inventory_mvp.inventory_apply_movement("receive", "matriz", pid, 10)
    due = inventory_mvp.inventory_schedule_due("matriz", produtos=_seed_produtos())
    assert due["total_vencidos"] > 0
    assert due["primeiro_vencido"] == "A"  # A vem primeiro
    assert due["classes"]["A"]["vencidos"] > 0
    assert due["classes"]["A"]["periodicidade"] == "semanal"
    # próximos contém as 3 classes
    assert {p["classe"] for p in due["proximos"]} == {"A", "B", "C"}


def test_schedule_due_apos_contagem_atualizada():
    # após contar a classe A, ela deixa de ter vencidos (contagem de hoje)
    for pid in ("1", "2", "11"):
        inventory_mvp.inventory_apply_movement("receive", "matriz", pid, 10)
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz",
        escopo={"tipo": "classe", "valor": "A"},
        produtos=_seed_produtos(),
    )
    inventory_mvp.inventory_count_set_items(count["id"], [
        {"produto_id": "1", "qtd_contada": 10},
        {"produto_id": "2", "qtd_contada": 10},
        {"produto_id": "11", "qtd_contada": 10},
    ])
    inventory_mvp.inventory_close_count(count["id"])
    due = inventory_mvp.inventory_schedule_due("matriz", produtos=_seed_produtos())
    assert due["classes"]["A"]["vencidos"] == 0
    assert due["primeiro_vencido"] in (None, "B", "C")  # A em dia


# ── Análise de divergências e auditoria ───────────────────────────────

def test_set_causas_so_em_divergencias():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    inventory_mvp.inventory_apply_movement("receive", "matriz", "2", 10)
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz", escopo={"tipo": "produtos", "valor": ["1", "2"]}, produtos=_seed_produtos()
    )
    inventory_mvp.inventory_count_set_items(count["id"], [
        {"produto_id": "1", "qtd_contada": 8},   # diverge
        {"produto_id": "2", "qtd_contada": 10},  # ok
    ])
    out = inventory_mvp.inventory_count_set_causas(count["id"], [
        {"produto_id": "1", "causa": "quebra_perda", "observacao": "vidro quebrado"},
        {"produto_id": "2", "causa": "extravio"},  # sem divergência → ignorada
    ])
    assert out["registradas"] == 1
    item1 = next(i for i in out["count"]["itens"] if i["produto_id"] == "1")
    assert item1["causa"] == "quebra_perda"
    assert item1["causa_label"] == "Quebra / perda física"
    assert item1["observacao"] == "vidro quebrado"


def test_set_causas_causa_invalida_vira_outros():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz", escopo={"tipo": "produtos", "valor": ["1"]}, produtos=_seed_produtos()
    )
    inventory_mvp.inventory_count_set_items(count["id"], [{"produto_id": "1", "qtd_contada": 9}])
    out = inventory_mvp.inventory_count_set_causas(count["id"], [
        {"produto_id": "1", "causa": "causa_inventada"}
    ])
    item = next(i for i in out["count"]["itens"] if i["produto_id"] == "1")
    assert item["causa"] == "outros"


def test_divergence_analysis_recorrentes_e_causas():
    # dois ciclos com o mesmo produto divergindo → recorrente
    for pid in ("1", "2"):
        inventory_mvp.inventory_apply_movement("receive", "matriz", pid, 10)
    for n in range(2):
        count = inventory_mvp.inventory_start_cycle_count(
            "matriz", escopo={"tipo": "produtos", "valor": ["1", "2"]}, produtos=_seed_produtos()
        )
        # conta -2 do saldo atual (sempre diverge)
        q1 = inventory_mvp.inventory_balance("matriz", "1") - 2
        inventory_mvp.inventory_count_set_items(count["id"], [
            {"produto_id": "1", "qtd_contada": q1},
            {"produto_id": "2", "qtd_contada": inventory_mvp.inventory_balance("matriz", "2")},
        ])
        inventory_mvp.inventory_count_set_causas(count["id"], [
            {"produto_id": "1", "causa": "erro_baixa"},
        ])
        inventory_mvp.inventory_close_count(count["id"])
    ana = inventory_mvp.inventory_divergence_analysis("matriz", produtos=_seed_produtos())
    assert ana["total_ajustes"] == 2
    assert len(ana["recorrentes"]) == 1
    assert ana["recorrentes"][0]["produto_id"] == "1"
    assert ana["recorrentes"][0]["ocorrencias"] == 2
    assert ana["causas"][0]["causa"] == "erro_baixa"
    assert ana["causas"][0]["total"] == 2
    assert ana["total_valor_ajustado"] > 0  # 2 un × preco_custo 5


def test_count_audit_relatorio_completo():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz", escopo={"tipo": "produtos", "valor": ["1"]}, produtos=_seed_produtos()
    )
    inventory_mvp.inventory_count_set_items(count["id"], [{"produto_id": "1", "qtd_contada": 7}])
    inventory_mvp.inventory_count_set_causas(count["id"], [
        {"produto_id": "1", "causa": "extravio", "observacao": "sumiu da prateleira"}
    ])
    inventory_mvp.inventory_close_count(count["id"])
    audit = inventory_mvp.inventory_count_audit(count["id"], produtos=_seed_produtos())
    assert audit["id"] == count["id"]
    assert audit["modo"] == "rotativo"
    assert audit["resumo"]["total_ajustes"] == 1
    assert audit["resumo"]["acuracia"] == 0.0  # 1 item, 1 divergente
    assert len(audit["itens"]) == 1
    assert audit["itens"][0]["causa"] == "extravio"
    assert audit["itens"][0]["causa_label"] == "Extravio / sumiço"
    assert audit["itens"][0]["observacao"] == "sumiu da prateleira"
    assert audit["por_causa"][0]["causa"] == "extravio"
    assert audit["por_causa"][0]["itens"] == 1


def test_cycle_accuracy_lista_ciclos_fechados():
    inventory_mvp.inventory_apply_movement("receive", "matriz", "1", 10)
    count = inventory_mvp.inventory_start_cycle_count(
        "matriz",
        escopo={"tipo": "amostra", "valor": 1},
        produtos=_seed_produtos(),
    )
    inventory_mvp.inventory_count_set_items(count["id"], [{"produto_id": "1", "qtd_contada": 10}])
    inventory_mvp.inventory_close_count(count["id"])
    rows = inventory_mvp.inventory_cycle_accuracy("matriz")
    assert len(rows) == 1
    assert rows[0]["modo"] == "rotativo"
    assert rows[0]["acuracia"] == 100.0
    assert rows[0]["total_ajustes"] == 0
