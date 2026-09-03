"""Testes do CRUD de localizações WMS via COBOL (gerir_localizacoes.cbl).

O piloto da migração WMS → COBOL: wms_locations.py grava em
dados/localizacoes.dat via cobol_bridge. Os testes isolam o .dat com as env
vars LOCALIZACOES_DAT / LOCALIZACOES_TMP (ASSIGN dinâmico do GnuCOBOL).
"""

import pytest

import wms_locations
import wms_warehouses


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALIZACOES_DAT", str(tmp_path / "localizacoes.dat"))
    monkeypatch.setenv("LOCALIZACOES_TMP", str(tmp_path / "localizacoes.tmp"))
    monkeypatch.setattr(wms_warehouses, "DATA_FILE", str(tmp_path / "wms_warehouses.json"))
    wms_warehouses.ensure_seed()
    wms_locations.ensure_seed()


def test_seed_cria_7_localizacoes():
    data = wms_locations.list_localizacoes()
    assert data["total"] == 7
    codigos = {r["codigo"] for r in data["localizacoes"]}
    assert {"REC-DOCK-01", "A01-01-01", "PCK-01", "SHP-STAGE", "LJ-RETIRA"} <= codigos


def test_criar_buscar_alterar_excluir():
    row = wms_locations.create_localizacao({
        "codigo": "TEST-Z1",
        "nome": "Zona Teste",
        "tipo": "storage",
        "armazem": "DC-01",
        "area": "STO",
        "zona": "Z1",
        "capacidade_qtd": 33,
    })
    assert row["codigo"] == "TEST-Z1"

    got = wms_locations.get_localizacao("test-z1")  # case-insensitive
    assert got["nome"] == "Zona Teste"
    assert got["capacidade_qtd"] == 33.0
    assert got["tipo_label"] == "Armazenagem"  # enriquecimento mantido

    upd = wms_locations.update_localizacao(
        "TEST-Z1",
        {"nome": "Renomeada", "status": "blocked", "bloqueio_motivo": "obra"},
    )
    assert upd["status"] == "blocked"
    assert upd["bloqueio_motivo"] == "obra"

    assert wms_locations.delete_localizacao("TEST-Z1") is True
    assert wms_locations.get_localizacao("TEST-Z1") is None


def test_codigo_duplicado_rejeitado():
    with pytest.raises(ValueError, match="já existe"):
        wms_locations.create_localizacao({
            "codigo": "PCK-01",
            "nome": "Duplicada",
            "tipo": "picking",
            "armazem": "DC-01",
            "area": "PCK",
        })


def test_capacidade_opcional_fica_nula():
    row = wms_locations.create_localizacao({
        "codigo": "TEST-NULL",
        "nome": "Sem capacidade",
        "tipo": "shipping",
        "armazem": "DC-01",
        "area": "SHP",
    })
    assert row["capacidade_qtd"] is None
    got = wms_locations.get_localizacao("TEST-NULL")
    assert got["capacidade_qtd"] is None
    wms_locations.delete_localizacao("TEST-NULL")


def test_filtros_da_listagem():
    wms_locations.create_localizacao({
        "codigo": "TEST-F1", "nome": "Filtro 1", "tipo": "storage",
        "armazem": "DC-01", "area": "STO", "corredor": "B02",
    })
    rows = wms_locations.list_localizacoes(armazem="dc-01")["localizacoes"]
    assert any(r["codigo"] == "TEST-F1" for r in rows)
    assert wms_locations.list_localizacoes(tipo="storage")["filtrado"] >= 4
    wms_locations.delete_localizacao("TEST-F1")
