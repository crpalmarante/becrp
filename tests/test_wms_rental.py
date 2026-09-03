"""Testes do aluguel / locação WMS (wms_rental.py) + destino final por local padrão."""

import pytest

import cobol_bridge
import inventory_mvp
import settings_store
import wms_locations
import wms_operation_types
import wms_operations
import wms_rental
import wms_routes
import wms_rules
import wms_warehouses

CATALOGO = [
    {"id": "1", "nome": "Arroz 5kg", "categoria": "Alimentacao"},
    {"id": "5", "nome": "Produto 5", "categoria": "Teste"},
]


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    for name in ("MOVEMENTS_FILE", "BALANCES_FILE", "TRANSIT_FILE", "COUNTS_FILE"):
        monkeypatch.setattr(inventory_mvp, name, str(tmp_path / f"{name}.json"))
    monkeypatch.setattr(wms_rules, "DATA_FILE", str(tmp_path / "wms_rules.json"))
    monkeypatch.setattr(wms_operations, "DATA_FILE", str(tmp_path / "wms_operations.json"))
    monkeypatch.setattr(wms_operation_types, "DATA_FILE", str(tmp_path / "wms_op_types.json"))
    monkeypatch.setattr(wms_warehouses, "DATA_FILE", str(tmp_path / "wms_warehouses.json"))
    monkeypatch.setattr(wms_locations, "DATA_FILE", str(tmp_path / "wms_locations.json"))
    monkeypatch.setenv("LOCALIZACOES_DAT", str(tmp_path / "localizacoes.dat"))
    monkeypatch.setenv("LOCALIZACOES_TMP", str(tmp_path / "localizacoes.tmp"))
    monkeypatch.setattr(wms_routes, "DATA_FILE", str(tmp_path / "wms_routes.json"))
    monkeypatch.setattr(wms_rental, "DATA_FILE", str(tmp_path / "wms_rental.json"))
    monkeypatch.setattr(settings_store, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    monkeypatch.setattr(cobol_bridge, "PRODUTOS_EXTRA_FILE", str(tmp_path / "produtos_extra.json"))

    def _fake_produtos_listar():
        # replica a mesclagem real: extras sobrescrevem o catálogo
        extras = cobol_bridge._load_produtos_extra()
        return [dict(p, **extras.get(str(p["id"]), {})) for p in CATALOGO]

    monkeypatch.setattr(cobol_bridge, "produtos_listar", _fake_produtos_listar)
    wms_warehouses.ensure_seed()
    wms_locations.ensure_seed()
    wms_locations.create_localizacao({
        "codigo": "CLIENTE", "nome": "Cliente", "tipo": "virtual",
        "armazem": "DC-01", "area": "SHP", "status": "available",
    })


def _rota_aluguel():
    settings_store.set_key("estoque", "rotas_multiplas_etapas", True)
    return wms_routes.create_rota({
        "nome": "Devolução de aluguel", "tipo": "aluguel", "armazem": "DC-01",
        "etapas": ["CLIENTE", "A01-01-02", "A01-01-01"],
    })


def _locacao(**over):
    payload = {
        "produto_id": "5", "qtd": 2, "cliente": "Cliente Demo",
        "data_inicio": "2026-06-01", "prazo_dias": 30,
    }
    payload.update(over)
    return wms_rental.create_locacao(payload)


def test_criar_locacao_calcula_prevista():
    loc = _locacao()
    assert loc["id"].startswith("AL-")
    assert loc["data_prevista"] == "2026-07-01"
    assert loc["status"] == "ativo"
    assert loc["produto_nome"] == "Produto 5"


def test_criar_locacao_valida_produto():
    with pytest.raises(ValueError, match="não encontrado"):
        _locacao(produto_id="999")


def test_criar_locacao_valida_qtd_e_prazo():
    with pytest.raises(ValueError, match="qtd"):
        _locacao(qtd=0)
    with pytest.raises(ValueError, match="prazo_dias"):
        _locacao(prazo_dias=0)


def test_check_vencidos_marca_por_prazo():
    _locacao()  # prevista 2026-07-01 < hoje
    out = wms_rental.check_vencidos()
    assert len(out["marcadas"]) == 1
    loc = wms_rental.list_locacoes()["locacoes"][0]
    assert loc["status"] == "vencido"


def test_check_vencidos_nao_marca_futuras():
    _locacao(data_inicio="2026-08-10", prazo_dias=30)  # prevista 2026-09-09
    out = wms_rental.check_vencidos()
    assert out["marcadas"] == []


def test_set_alugavel_flag():
    wms_rental.set_alugavel("5", True)
    alugaveis = wms_rental.produtos_alugaveis()
    assert "5" in [p["produto_id"] for p in alugaveis]
    wms_rental.set_alugavel("5", False)
    assert "5" not in [p["produto_id"] for p in wms_rental.produtos_alugaveis()]


def test_set_status_devolvido():
    loc = _locacao()
    wms_rental.set_status(loc["id"], "devolvido")
    assert wms_rental.get_locacao(loc["id"])["status"] == "devolvido"


def test_gerar_devolucoes_vencidas_com_local_padrao():
    _rota_aluguel()
    wms_routes.set_local_padrao("5", "DC-01", "PCK-01")
    loc = _locacao()
    wms_rental.check_vencidos()
    out = wms_rental.gerar_devolucoes_vencidas(usuario="teste")
    assert out["resumo"]["geradas"] == 1
    assert out["resumo"]["puladas"] == 0
    atual = wms_rental.get_locacao(loc["id"])
    assert atual["status"] == "devolucao_gerada"
    passos = atual["devolucao"]["passos"]
    # local padrão (PCK-01) entra como destino final automático
    assert passos[-1]["destino"] == "PCK-01"
    assert [p["origem"] for p in passos] == ["CLIENTE", "A01-01-02", "A01-01-01"]
    ops = wms_operations.list_operacoes()["operacoes"]
    assert len([o for o in ops if str(o.get("id") or "").startswith("OP-RET-")]) == 3


def test_gerar_devolucoes_sem_rota_aluguel_pula():
    loc = _locacao()
    wms_rental.check_vencidos()
    out = wms_rental.gerar_devolucoes_vencidas(usuario="teste")
    assert out["resumo"]["geradas"] == 0
    assert out["resumo"]["puladas"] == 1
    assert "aluguel" in out["puladas"][0]["motivo"]
    # continua vencida (não foi marcada como gerada)
    assert wms_rental.get_locacao(loc["id"])["status"] == "vencido"


def test_devolucao_aluguel_destino_final_explicito():
    _rota_aluguel()
    out = wms_routes.wms_routes_devolucao_aluguel(
        "DC-01", "5", 2, local_atual="SHP-STAGE", destino_final="LJ-STO-01", usuario="teste")
    rota = [p["origem"] for p in out["passos"]] + [out["passos"][-1]["destino"]]
    assert rota == ["SHP-STAGE", "CLIENTE", "A01-01-02", "A01-01-01", "LJ-STO-01"]
