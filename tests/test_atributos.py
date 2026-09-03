"""Testes do CRUD de atributos de produtos (COBOL — gerir_atributos.cbl).

Usa cobol_bridge direto (mesmo padrão de test_variantes.py).
Cria dados de teste e limpa em finally para não sujar dados reais.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cobol_bridge

CRIADOS = []


def _limpar():
    for aid in list(CRIADOS):
        try:
            cobol_bridge.atributos_excluir(aid)
        except Exception:
            pass
    CRIADOS.clear()


def _criar(dados):
    aid = cobol_bridge.atributos_incluir(dados)
    CRIADOS.append(aid)
    return aid


def test_atributo_incluir_listar():
    try:
        aid = _criar({"produto_id": 1, "nome": "Cor", "valor": "Azul"})
        lista = cobol_bridge.atributos_listar()
        a = next((x for x in lista if x["id"] == aid), None)
        assert a is not None, "atributo não encontrado na listagem"
        assert a["produto_id"] == 1
        assert a["nome"] == "Cor"
        assert a["valor"] == "Azul"
    finally:
        _limpar()


def test_atributo_listar_por_produto():
    try:
        aid1 = _criar({"produto_id": 1, "nome": "Tamanho", "valor": "GG"})
        aid2 = _criar({"produto_id": 1, "nome": "Cor", "valor": "Roxo"})
        result = cobol_bridge.atributos_listar_por_produto(1)
        ids = [x["id"] for x in result]
        assert aid1 in ids
        assert aid2 in ids
        # Excluir um e verificar que some
        cobol_bridge.atributos_excluir(aid2)
        CRIADOS.remove(aid2)
        result2 = cobol_bridge.atributos_listar_por_produto(1)
        ids2 = [x["id"] for x in result2]
        assert aid1 in ids2
        assert aid2 not in ids2
    finally:
        _limpar()


def test_atributo_alterar():
    try:
        aid = _criar({"produto_id": 1, "nome": "Cor", "valor": "Verde"})
        ok = cobol_bridge.atributos_alterar(aid, {"nome": "Cor", "valor": "Amarelo"})
        assert ok
        result = cobol_bridge.atributos_listar_por_produto(1)
        a = next((x for x in result if x["id"] == aid), None)
        assert a is not None
        assert a["valor"] == "Amarelo"
    finally:
        _limpar()


def test_atributo_excluir():
    try:
        aid = _criar({"produto_id": 1, "nome": "Material", "valor": "Algodao"})
        ok = cobol_bridge.atributos_excluir(aid)
        assert ok
        CRIADOS.remove(aid)
        result = cobol_bridge.atributos_listar()
        assert all(x["id"] != aid for x in result), "atributo não foi excluído"
    finally:
        _limpar()


def test_atributo_nome_obrigatorio():
    try:
        cobol_bridge.atributos_incluir({"produto_id": 1, "nome": "", "valor": "X"})
        raise AssertionError("nome vazio deveria falhar")
    except Exception as e:
        assert "nome" in str(e).lower() or "obrigatorio" in str(e).lower()


def test_atributo_valor_obrigatorio():
    try:
        cobol_bridge.atributos_incluir({"produto_id": 1, "nome": "Cor", "valor": ""})
        raise AssertionError("valor vazio deveria falhar")
    except Exception as e:
        assert "valor" in str(e).lower() or "obrigatorio" in str(e).lower()


def test_atributo_produto_id_obrigatorio():
    try:
        cobol_bridge.atributos_incluir({"produto_id": 0, "nome": "Cor", "valor": "Azul"})
        raise AssertionError("produto_id=0 deveria falhar")
    except Exception as e:
        assert "produto" in str(e).lower() or "obrigatorio" in str(e).lower()


def test_atributo_produto_inexistente():
    try:
        cobol_bridge.atributos_incluir({"produto_id": 999999, "nome": "Cor", "valor": "Azul"})
        raise AssertionError("produto inexistente deveria falhar")
    except Exception as e:
        assert "nao encontrado" in str(e).lower() or "não encontrado" in str(e).lower()


def test_atributo_alterar_inexistente():
    ok = cobol_bridge.atributos_alterar(999999, {"nome": "X", "valor": "Y"})
    assert ok is False


def test_atributo_excluir_inexistente():
    ok = cobol_bridge.atributos_excluir(999999)
    assert ok is False
