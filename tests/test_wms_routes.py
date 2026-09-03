"""Testes das rotas WMS (wms_routes.py) — coleção de regras push/pull."""

import pytest

import inventory_mvp
import settings_store
import wms_locations
import wms_operation_types
import wms_operations
import wms_routes
import wms_rules
import wms_warehouses


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    for name in ("MOVEMENTS_FILE", "BALANCES_FILE", "TRANSIT_FILE", "COUNTS_FILE"):
        monkeypatch.setattr(inventory_mvp, name, str(tmp_path / f"{name}.json"))
    monkeypatch.setattr(wms_rules, "DATA_FILE", str(tmp_path / "wms_rules.json"))
    monkeypatch.setattr(wms_operations, "DATA_FILE", str(tmp_path / "wms_operations.json"))
    monkeypatch.setattr(wms_operation_types, "DATA_FILE", str(tmp_path / "wms_op_types.json"))
    monkeypatch.setattr(wms_warehouses, "DATA_FILE", str(tmp_path / "wms_warehouses.json"))
    monkeypatch.setattr(wms_locations, "DATA_FILE", str(tmp_path / "wms_locations.json"))
    monkeypatch.setattr(wms_routes, "DATA_FILE", str(tmp_path / "wms_routes.json"))
    monkeypatch.setattr(settings_store, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    monkeypatch.setenv("LOCALIZACOES_DAT", str(tmp_path / "localizacoes.dat"))
    monkeypatch.setenv("LOCALIZACOES_TMP", str(tmp_path / "localizacoes.tmp"))
    wms_warehouses.ensure_seed()
    wms_locations.ensure_seed()
    wms_locations.create_localizacao({
        "codigo": "CLIENTE", "nome": "Cliente", "tipo": "virtual",
        "armazem": "DC-01", "area": "SHP", "status": "available",
    })


def _rota(**over):
    payload = {
        "nome": "Rota de teste",
        "tipo": "armazenagem",
        "armazem": "DC-01",
        "etapas": [{"localizacao": "REC-DOCK-01", "papel": "recebimento"},
                   {"localizacao": "A01-01-01", "papel": "armazenagem"}],
    }
    payload.update(over)
    return wms_routes.create_rota(payload)


def test_rota_duas_etapas_criada():
    r = _rota()
    assert r["id"].startswith("RT-")
    assert [e["localizacao"] for e in r["etapas"]] == ["REC-DOCK-01", "A01-01-01"]
    assert r["etapas"][0]["papel"] == "recebimento"


def test_rota_tres_etapas_bloqueada_sem_multi():
    with pytest.raises(ValueError, match="várias etapas"):
        _rota(etapas=["REC-DOCK-01", "A01-01-02", "A01-01-01"])


def test_rota_multietapas_apos_ativar_config():
    settings_store.set_key("estoque", "rotas_multiplas_etapas", True)
    assert wms_routes.config_rotas()["rotas_multiplas_etapas"] is True
    r = _rota(tipo="qualidade", etapas=["REC-DOCK-01", "A01-01-02", "A01-01-01"])
    assert len(r["etapas"]) == 3


def test_rota_valida_localizacoes():
    with pytest.raises(ValueError, match="não encontrada"):
        _rota(etapas=["XYZ-99", "A01-01-01"])


def test_rota_rejeita_etapa_repetida():
    settings_store.set_key("estoque", "rotas_multiplas_etapas", True)
    with pytest.raises(ValueError, match="repetida"):
        _rota(etapas=["REC-DOCK-01", "A01-01-01", "REC-DOCK-01"])


def test_rota_duplicidade_id():
    _rota(id="RT-99")
    with pytest.raises(ValueError, match="já existe"):
        _rota(id="RT-99")


def test_gerar_regras_da_rota():
    settings_store.set_key("estoque", "rotas_multiplas_etapas", True)
    r = _rota(tipo="qualidade", etapas=["REC-DOCK-01", "A01-01-02", "A01-01-01"])
    out = wms_routes.wms_routes_gerar_regras(r["id"])
    assert out["total"] == 2
    rotas_regras = [(x["origem"], x["destino"]) for x in out["criadas"]]
    assert rotas_regras == [("REC-DOCK-01", "A01-01-02"), ("A01-01-02", "A01-01-01")]
    # as regras geradas são pull
    for x in out["criadas"]:
        assert x["regra"]["tipo"] == "pull"


def test_gerar_regras_rota_sem_2_etapas():
    r = _rota(etapas=["REC-DOCK-01"])
    with pytest.raises(ValueError, match="ao menos 2 etapas"):
        wms_routes.wms_routes_gerar_regras(r["id"])


def test_local_padrao_produto_crud():
    out = wms_routes.set_local_padrao("1", "DC-01", "PCK-01")
    assert out["padrao"] == {"armazem": "DC-01", "localizacao": "PCK-01"}
    assert wms_routes.list_locais_padrao("1")["padrao"]["localizacao"] == "PCK-01"
    assert wms_routes.list_locais_padrao()["total"] == 1
    wms_routes.delete_local_padrao("1")
    assert wms_routes.list_locais_padrao("1")["padrao"] == {}


def test_local_padrao_valida_localizacao():
    with pytest.raises(ValueError, match="não encontrada"):
        wms_routes.set_local_padrao("1", "DC-01", "XYZ-99")


def _rota_aluguel():
    settings_store.set_key("estoque", "rotas_multiplas_etapas", True)
    return wms_routes.create_rota({
        "nome": "Devolução de aluguel", "tipo": "aluguel", "armazem": "DC-01",
        "etapas": ["CLIENTE", "A01-01-02", "A01-01-01"],
    })


def test_devolucao_aluguel_gera_operacoes():
    r = _rota_aluguel()
    out = wms_routes.wms_routes_devolucao_aluguel("DC-01", "5", 2, usuario="teste")
    assert out["rota_id"] == r["id"]
    assert out["total"] == 2
    assert [(p["origem"], p["destino"]) for p in out["passos"]] == [
        ("CLIENTE", "A01-01-02"), ("A01-01-02", "A01-01-01")]
    ops = wms_operations.list_operacoes()["operacoes"]
    criadas = [o for o in ops if str(o.get("id") or "").startswith("OP-RET-")]
    assert len(criadas) == 2
    assert all(o["tipo"] == "TRF-INT" for o in criadas)
    assert all(o["origem"] == "rota:aluguel" for o in criadas)


def test_devolucao_aluguel_sem_rota():
    with pytest.raises(ValueError, match="aluguel"):
        wms_routes.wms_routes_devolucao_aluguel("DC-01", "5", 2)


def test_devolucao_aluguel_local_atual_antecipa():
    _rota_aluguel()
    out = wms_routes.wms_routes_devolucao_aluguel(
        "DC-01", "5", 2, local_atual="SHP-STAGE", usuario="teste")
    assert [(p["origem"], p["destino"]) for p in out["passos"]] == [
        ("SHP-STAGE", "CLIENTE"), ("CLIENTE", "A01-01-02"), ("A01-01-02", "A01-01-01")]
