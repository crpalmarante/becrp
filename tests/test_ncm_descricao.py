import uuid

from cobol_bridge import produtos_excluir, produtos_incluir, produtos_listar
from modules.lookup.ncm_cest_service import get_ncm


def test_ncm_85166000_usa_descricao_exata_do_item():
    item = get_ncm("85166000")
    assert item is not None
    assert item["codigo"] == "85166000"
    assert item["descricao"] == (
        "Outros fornos; fogões de cozinha, fogareiros (incluindo as chapas de cocção), "
        "grelhas e assadeiras"
    )


def test_produto_salvo_aparece_na_lista():
    nome = f"Produto Save Test {uuid.uuid4().hex[:6]}"
    pid = produtos_incluir({
        "nome": nome,
        "preco": 55.5,
        "preco_custo": 40,
        "stock": 12,
        "ncm": "85166000",
        "categoria": "Teste",
        "sub_categoria": "Teste",
        "unidade": "UN",
        "fornecedor": "",
        "localizacao": "B2",
        "ativo": True,
        "vendavel": True,
        "compravel": True,
        "pdv": True,
        "filial_id": 0,
    })
    try:
        rows = produtos_listar()
        found = next((row for row in rows if str(row.get("id")) == str(pid)), None)
        assert found is not None
        assert found.get("nome") == nome
        assert found.get("ncm") == "85166000"
    finally:
        assert produtos_excluir(pid) is True
