"""Testes do CRUD de variantes de produtos (COBOL — gerir_variantes.cbl).

Usa cobol_bridge direto (mesmo padrão de test_fornecedores_categorias.py).
Cria dados de teste e limpa em finally para não sujar dados reais.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cobol_bridge

CRIADOS = []


def _limpar():
    for vid in list(CRIADOS):
        try:
            cobol_bridge.variantes_excluir(vid)
        except Exception:
            pass
    CRIADOS.clear()


def _criar(dados):
    vid = cobol_bridge.variantes_incluir(dados)
    CRIADOS.append(vid)
    return vid


def test_variante_incluir_listar_excluir():
    try:
        vid = _criar({
            "produto_id": 1,
            "nome": "Arroz Integral Teste",
            "atributos": "Cor: Marrom; Tipo: Integral",
            "codigo": "TST-INT-1",
            "preco": 34.9,
        })
        lista = cobol_bridge.variantes_listar()
        v = next((x for x in lista if x["id"] == vid), None)
        assert v is not None, "variante não encontrada na listagem"
        assert v["produto_id"] == 1
        assert v["nome"] == "Arroz Integral Teste"
        assert v["atributos"] == "Cor: Marrom; Tipo: Integral"
        assert v["codigo"] == "TST-INT-1"
        assert abs(float(v["preco"]) - 34.9) < 0.01
        assert v["ativo"] is True
        assert cobol_bridge.variantes_excluir(vid)
        CRIADOS.remove(vid)
    finally:
        _limpar()


def test_variante_duplicada_bloqueada():
    try:
        vid = _criar({"produto_id": 2, "nome": "Feijao Carioca 1kg"})
        try:
            cobol_bridge.variantes_incluir({"produto_id": 2, "nome": "feijao carioca 1kg"})
            raise AssertionError("duplicata deveria ser bloqueada")
        except Exception as e:
            assert "duplicada" in str(e).lower()
    finally:
        _limpar()


def test_variante_mesmo_nome_produtos_diferentes():
    """Mesmo nome em produtos diferentes NÃO é duplicata."""
    try:
        vid1 = _criar({"produto_id": 3, "nome": "Embalagem 1kg"})
        vid2 = _criar({"produto_id": 4, "nome": "Embalagem 1kg"})
        lista = cobol_bridge.variantes_listar()
        nomes = [(x["produto_id"], x["nome"]) for x in lista if x["id"] in (vid1, vid2)]
        assert len(nomes) == 2
    finally:
        _limpar()


def test_variante_alterar():
    try:
        vid = _criar({"produto_id": 5, "nome": "Oleo 900ml", "preco": 12.4})
        ok = cobol_bridge.variantes_alterar(vid, {
            "produto_id": 5,
            "nome": "Oleo de Soja 900ml",
            "preco": 13.9,
            "codigo": "OLEO-900",
        })
        assert ok
        v = next(x for x in cobol_bridge.variantes_listar() if x["id"] == vid)
        assert v["nome"] == "Oleo de Soja 900ml"
        assert abs(float(v["preco"]) - 13.9) < 0.01
        assert v["codigo"] == "OLEO-900"
    finally:
        _limpar()


def test_variante_alterar_limpar_codigo():
    """CODIGO_CLEAR: enviar codigo vazio no alterar remove o código."""
    try:
        vid = _criar({"produto_id": 6, "nome": "Leite Integral", "codigo": "LEITE-1L"})
        ok = cobol_bridge.variantes_alterar(vid, {
            "produto_id": 6,
            "codigo": "",
        })
        assert ok
        v = next(x for x in cobol_bridge.variantes_listar() if x["id"] == vid)
        assert v["codigo"] == ""
    finally:
        _limpar()


def test_variante_toggle_ativo():
    try:
        vid = _criar({"produto_id": 7, "nome": "Paozinho Integral"})
        lista = cobol_bridge.variantes_listar()
        alvo = next(x for x in lista if x["id"] == vid)
        cobol_bridge.variantes_alterar(vid, {"ativo": False})
        v = next(x for x in cobol_bridge.variantes_listar() if x["id"] == vid)
        assert v["ativo"] is False
        cobol_bridge.variantes_alterar(vid, {"ativo": True})
        v = next(x for x in cobol_bridge.variantes_listar() if x["id"] == vid)
        assert v["ativo"] is True
    finally:
        _limpar()


def test_variante_nome_obrigatorio():
    try:
        cobol_bridge.variantes_incluir({"produto_id": 1, "nome": ""})
        raise AssertionError("nome vazio deveria falhar")
    except Exception as e:
        assert "nome" in str(e).lower()
    finally:
        _limpar()
