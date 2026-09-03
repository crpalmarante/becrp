import uuid

import pytest

from cobol_bridge import (
    categorias_alterar,
    categorias_excluir,
    categorias_incluir,
    categorias_listar,
    fornecedores_alterar,
    fornecedores_excluir,
    fornecedores_incluir,
    fornecedores_listar,
)


def _cnpj():
    """CNPJ fictício de 14 dígitos baseado em uuid (sem colisão com dados reais)."""
    return uuid.uuid4().hex[:14]


# ── Fornecedores (gerir_fornecedores.cbl) ───────────────────


def test_fornecedor_incluir_listar_excluir():
    nome = f"Forn Test {uuid.uuid4().hex[:6]}"
    cnpj = _cnpj()
    fid = fornecedores_incluir({
        "nome": nome,
        "cnpj": cnpj,
        "endereco": "Rua Teste, 123",
        "cep": "01310-100",
        "telefone": "(11) 99999-0000",
        "email": "teste@exemplo.com",
        "ie": "123456",
        "cnae": "4711-3/00",
        "cnae_desc": "Comercio varejista",
    })
    try:
        rows = fornecedores_listar()
        found = next((r for r in rows if str(r.get("id")) == str(fid)), None)
        assert found is not None
        assert found.get("nome") == nome
        assert found.get("cnpj") == cnpj
        assert found.get("cep") == "01310-100"
        assert found.get("cnae") == "4711-3/00"
    finally:
        assert fornecedores_excluir(fid) is True


def test_fornecedor_cnpj_duplicado_bloqueado():
    nome = f"Forn Dup {uuid.uuid4().hex[:6]}"
    cnpj = _cnpj()
    fid = fornecedores_incluir({"nome": nome, "cnpj": cnpj})
    try:
        with pytest.raises(Exception, match="CNPJ ja cadastrado"):
            # mesma formatação diferente (pontos/barras) deve ser bloqueada
            fmt = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
            fornecedores_incluir({"nome": "Outro", "cnpj": fmt})
    finally:
        assert fornecedores_excluir(fid) is True


def test_fornecedor_alterar_campos_e_limpar_logo():
    nome = f"Forn Alt {uuid.uuid4().hex[:6]}"
    fid = fornecedores_incluir({"nome": nome, "cnpj": _cnpj(), "logo": "https://exemplo.com/logo.png"})
    try:
        assert fornecedores_alterar(fid, {
            "cnae": "4751-2/00",
            "cnae_desc": "Comercio varejista especializado",
            "cep": "80000-000",
            "logo": "",
        }) is True
        rows = fornecedores_listar()
        found = next(r for r in rows if str(r.get("id")) == str(fid))
        assert found.get("cnae") == "4751-2/00"
        assert found.get("cep") == "80000-000"
        assert found.get("logo") == ""
    finally:
        assert fornecedores_excluir(fid) is True


def test_fornecedor_nome_obrigatorio():
    with pytest.raises(Exception, match="nome obrigatorio"):
        fornecedores_incluir({"nome": "", "cnpj": _cnpj()})


# ── Categorias (gerir_categorias.cbl) ───────────────────────


def test_categoria_pai_filho_e_exclusao_protegida():
    pai = f"Cat Pai {uuid.uuid4().hex[:6]}"
    filho = f"Cat Filho {uuid.uuid4().hex[:6]}"
    pid = categorias_incluir({"nome": pai})
    try:
        cid = categorias_incluir({"nome": filho, "pai_id": pid})
        try:
            rows = categorias_listar()
            child = next(r for r in rows if str(r.get("id")) == str(cid))
            assert child.get("pai_id") == pid
            # excluir pai com filho deve ser bloqueado
            with pytest.raises(Exception, match="subcategorias"):
                categorias_excluir(pid)
        finally:
            assert categorias_excluir(cid) is True
    finally:
        assert categorias_excluir(pid) is True


def test_categoria_duplicada_bloqueada():
    nome = f"Cat Dup {uuid.uuid4().hex[:6]}"
    cid = categorias_incluir({"nome": nome})
    try:
        with pytest.raises(Exception, match="duplicado"):
            categorias_incluir({"nome": nome.lower() + " "})
        # alterar para nome duplicado também bloqueado
        outro = categorias_incluir({"nome": f"Outra {uuid.uuid4().hex[:6]}"})
        try:
            with pytest.raises(Exception, match="duplicado"):
                categorias_alterar(outro, {"nome": nome})
        finally:
            assert categorias_excluir(outro) is True
    finally:
        assert categorias_excluir(cid) is True


def test_categoria_alterar_pai():
    pai = f"Cat Alt Pai {uuid.uuid4().hex[:6]}"
    a = categorias_incluir({"nome": pai})
    b = categorias_incluir({"nome": f"Filho {uuid.uuid4().hex[:6]}", "pai_id": a})
    try:
        assert categorias_alterar(b, {"pai_id": 0}) is True
        rows = categorias_listar()
        found = next(r for r in rows if str(r.get("id")) == str(b))
        assert found.get("pai_id") == 0
    finally:
        assert categorias_excluir(b) is True
        assert categorias_excluir(a) is True
