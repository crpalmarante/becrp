"""Testes de persistência dos campos extras de produtos.

Verifica que todos os campos extra (preço, logística, estoque, etc.)
são salvos e carregados corretamente pelo cobol_bridge.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cobol_bridge

CRIADOS = []


def _limpar():
    for pid in list(CRIADOS):
        try:
            cobol_bridge.produtos_excluir(pid)
        except Exception:
            pass
    CRIADOS.clear()


def _criar(dados):
    pid = cobol_bridge.produtos_incluir(dados)
    CRIADOS.append(pid)
    return pid


EXTRA_COMPLETO = {
    "nome": "Produto Teste Extra",
    "preco": 99.90,
    "preco_custo": 50.00,
    "stock": 25,
    "margem": 99.80,
    "codigo_barras": "7899999999999",
    "categoria": "TesteExtra",
    "unidade": "UN",
    "ncm": "85166000",
    "fornecedor": "Fornecedor Teste",
    "localizacao": "X1-01",
    "filial_id": 0,
    "cst": "000",
    "cfop": "5102",
    "icms_alq": 18.0,
    "servico": "N",
    "iss_alq": 0.0,
    "cod_serv_mun": "",
    "extra": {
        # ── Identidade ──
        "nome_reduzido": "Prod Teste",
        "marca": "MarcaX",
        "fabricante": "FabY",
        "unidade_compra": "CX",
        "tipo": "kit",
        "modelo": "ModeloZ",
        "tags": "tag1, tag2",
        "descricao": "Descrição completa do produto",
        # ── Preços ──
        "preco_promo": 89.90,
        "preco_min": 79.90,
        "preco_max": 149.90,
        "comissao": 5.0,
        "modo_preco": "despesas",
        "despesa_fixa": 2.50,
        "despesa_pct": 3.0,
        # ── Variações ──
        "variacoes": [
            {
                "atributo": "Cor",
                "valor": "Azul",
                "tipo_preco": "delta",
                "valor_preco": "5",
                "ean": "7890000000001",
                "estoque": "10",
            },
            {
                "atributo": "Tamanho",
                "valor": "GG",
                "tipo_preco": "absoluto",
                "valor_preco": "119.90",
                "ean": "",
                "estoque": "",
            },
        ],
        # ── Estoque ──
        "estoque_min": 5,
        "estoque_max": 100,
        "validade_dias": 365,
        "controla_estoque": True,
        "estoque_negativo": False,
        "controla_lote": True,
        "controla_serie": False,
        # ── Fiscal ──
        "cest": "02.001.00",
        "origem": "0",
        # ── Flags ──
        "ativo": True,
        "vendavel": True,
        "compravel": True,
        "pdv": True,
        "usa_balanca": False,
        "compra_ok": True,
        "venda_ok": True,
        "fracionado": False,
        "por_peso": False,
        # ── Compras ──
        "qtd_min_compra": 10,
        "qtd_padrao": 50,
        "lead_time": 7,
        "garantia": 12,
        # ── Logística ──
        "peso_liq": 1.5,
        "peso_bruto": 2.0,
        "tipo_embalagem": "cx_papelao",
        "embalagem_outro": "",
        "qtd_por_embalagem": 12,
        "altura": 30.0,
        "largura": 20.0,
        "comprimento": 15.0,
        "volume": 0.009,
        "altura_emb": 35.0,
        "largura_emb": 25.0,
        "comprimento_emb": 20.0,
        "volume_emb": 0.0175,
    },
}


def _get_produto(pid):
    """Busca produto por ID na listagem."""
    for p in cobol_bridge.produtos_listar():
        if p["id"] == pid:
            return p
    return None


def test_extra_persistencia_campos_identidade():
    """Campos de identidade (nome_reduzido, marca, fabricante, etc.)."""
    try:
        pid = _criar(EXTRA_COMPLETO)
        p = _get_produto(pid)
        assert p is not None, "produto não encontrado"
        assert p.get("nome_reduzido") == "Prod Teste"
        assert p.get("marca") == "MarcaX"
        assert p.get("fabricante") == "FabY"
        assert p.get("unidade_compra") == "CX"
        assert p.get("tipo") == "kit"
        assert p.get("modelo") == "ModeloZ"
        assert p.get("tags") == "tag1, tag2"
        assert p.get("descricao") == "Descrição completa do produto"
    finally:
        _limpar()


def test_extra_persistencia_campos_preco():
    """Campos de preço (promo, min, max, comissão, modo_preco, despesas)."""
    try:
        pid = _criar(EXTRA_COMPLETO)
        p = _get_produto(pid)
        assert p is not None
        assert abs(float(p.get("preco_promo", 0)) - 89.90) < 0.01
        assert abs(float(p.get("preco_min", 0)) - 79.90) < 0.01
        assert abs(float(p.get("preco_max", 0)) - 149.90) < 0.01
        assert abs(float(p.get("comissao", 0)) - 5.0) < 0.01
        assert p.get("modo_preco") == "despesas"
        assert abs(float(p.get("despesa_fixa", 0)) - 2.50) < 0.01
        assert abs(float(p.get("despesa_pct", 0)) - 3.0) < 0.01
    finally:
        _limpar()


def test_extra_persistencia_variacoes():
    """Variações do produto."""
    try:
        pid = _criar(EXTRA_COMPLETO)
        p = _get_produto(pid)
        assert p is not None
        vars_ = p.get("variacoes", [])
        assert len(vars_) == 2
        v1 = vars_[0]
        assert v1["atributo"] == "Cor"
        assert v1["valor"] == "Azul"
        assert v1["tipo_preco"] == "delta"
        assert v1["ean"] == "7890000000001"
        v2 = vars_[1]
        assert v2["atributo"] == "Tamanho"
        assert v2["valor"] == "GG"
        assert v2["tipo_preco"] == "absoluto"
    finally:
        _limpar()


def test_extra_persistencia_estoque():
    """Campos de estoque (mínimo, máximo, validade, flags)."""
    try:
        pid = _criar(EXTRA_COMPLETO)
        p = _get_produto(pid)
        assert p is not None
        assert p.get("estoque_min") == 5 or str(p.get("estoque_min")) == "5"
        assert p.get("estoque_max") == 100 or str(p.get("estoque_max")) == "100"
        assert p.get("validade_dias") == 365 or str(p.get("validade_dias")) == "365"
        assert p.get("controla_estoque") is True
        assert p.get("estoque_negativo") is False
        assert p.get("controla_lote") is True
        assert p.get("controla_serie") is False
    finally:
        _limpar()


def test_extra_persistencia_fiscal():
    """Campos fiscais (CEST, origem)."""
    try:
        pid = _criar(EXTRA_COMPLETO)
        p = _get_produto(pid)
        assert p is not None
        assert p.get("cest") == "02.001.00"
        assert p.get("origem") == "0"
    finally:
        _limpar()


def test_extra_persistencia_flags():
    """Flags booleanas (ativo, vendavel, compravel, pdv, etc.)."""
    try:
        pid = _criar(EXTRA_COMPLETO)
        p = _get_produto(pid)
        assert p is not None
        assert p.get("vendavel") is True
        assert p.get("compravel") is True
        assert p.get("pdv") is True
        assert p.get("usa_balanca") is False
        assert p.get("compra_ok") is True
        assert p.get("venda_ok") is True
        assert p.get("fracionado") is False
        assert p.get("por_peso") is False
    finally:
        _limpar()


def test_extra_persistencia_compras():
    """Campos de compras (qtd_min, qtd_padrao, lead_time, garantia)."""
    try:
        pid = _criar(EXTRA_COMPLETO)
        p = _get_produto(pid)
        assert p is not None
        assert p.get("qtd_min_compra") == 10 or str(p.get("qtd_min_compra")) == "10"
        assert p.get("qtd_padrao") == 50 or str(p.get("qtd_padrao")) == "50"
        assert p.get("lead_time") == 7 or str(p.get("lead_time")) == "7"
        assert p.get("garantia") == 12 or str(p.get("garantia")) == "12"
    finally:
        _limpar()


def test_extra_persistencia_logistica():
    """Campos de logística (pesos, embalagem, dimensões)."""
    try:
        pid = _criar(EXTRA_COMPLETO)
        p = _get_produto(pid)
        assert p is not None
        assert abs(float(p.get("peso_liq", 0)) - 1.5) < 0.01
        assert abs(float(p.get("peso_bruto", 0)) - 2.0) < 0.01
        assert p.get("tipo_embalagem") == "cx_papelao"
        assert p.get("qtd_por_embalagem") == 12 or str(p.get("qtd_por_embalagem")) == "12"
        assert abs(float(p.get("altura", 0)) - 30.0) < 0.1
        assert abs(float(p.get("largura", 0)) - 20.0) < 0.1
        assert abs(float(p.get("comprimento", 0)) - 15.0) < 0.1
        assert abs(float(p.get("altura_emb", 0)) - 35.0) < 0.1
        assert abs(float(p.get("largura_emb", 0)) - 25.0) < 0.1
        assert abs(float(p.get("comprimento_emb", 0)) - 20.0) < 0.1
    finally:
        _limpar()


def test_extra_alterar_persiste():
    """Alterar extras e verificar persistência."""
    try:
        pid = _criar(EXTRA_COMPLETO)
        cobol_bridge.produtos_alterar(pid, {
            "nome": "Produto Alterado",
            "extra": {
                "marca": "MarcaAlterada",
                "variacao": [{"atributo": "Cor", "valor": "Vermelho"}],
                "estoque_min": 10,
                "controla_estoque": False,
            },
        })
        p = _get_produto(pid)
        assert p is not None
        assert p.get("marca") == "MarcaAlterada"
        assert p.get("estoque_min") == 10 or str(p.get("estoque_min")) == "10"
        assert p.get("controla_estoque") is False
    finally:
        _limpar()


def test_extra_excluir_limpa_extras():
    """Excluir produto remove extras do arquivo."""
    try:
        pid = _criar(EXTRA_COMPLETO)
        # Verificar que extra existe
        ext = cobol_bridge.produtos_extra_get(pid)
        assert ext.get("marca") == "MarcaX"
        # Excluir
        cobol_bridge.produtos_excluir(pid)
        CRIADOS.remove(pid)
        # Verificar que extra foi removido
        ext2 = cobol_bridge.produtos_extra_get(pid)
        assert not ext2 or ext2.get("marca") is None
    finally:
        _limpar()
