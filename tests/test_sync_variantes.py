"""Tests for sync_variantes_for_produto: inline product form ↔ COBOL variantes.dat"""
import cobol_bridge


# ── Helpers ─────────────────────────────────────────────────

def _cleanup_variantes(produto_id):
    """Remove all COBOL variantes for a product."""
    for v in cobol_bridge.variantes_listar():
        if v.get("produto_id") == produto_id:
            cobol_bridge.variantes_excluir(v["id"])


# ── Tests ───────────────────────────────────────────────────

class TestSyncVariantesForProduto:
    """sync_variantes_for_produto creates/updates/deactivates COBOL records."""

    def setup_method(self):
        self.produto_id = 1  # exists in test data
        _cleanup_variantes(self.produto_id)  # clean before each test

    def teardown_method(self):
        _cleanup_variantes(self.produto_id)

    def test_sync_cria_variantes(self):
        """Inline variants → COBOL variantes.dat created."""
        variacoes = [
            {"atributo": "Cor", "valor": "Vermelho", "tipo_preco": "delta",
             "valor_preco": 5.00, "ean": "7891234567890", "estoque": "", "ativo": True},
            {"atributo": "Cor", "valor": "Azul", "tipo_preco": "delta",
             "valor_preco": 0, "ean": "", "estoque": "", "ativo": True},
        ]
        cobol_bridge.sync_variantes_for_produto(self.produto_id, variacoes, 100.00)

        listed = cobol_bridge.variantes_listar_por_produto(self.produto_id)
        assert len(listed) == 2
        nomes = {v["nome"] for v in listed}
        assert "Cor: Vermelho" in nomes
        assert "Cor: Azul" in nomes

    def test_sync_preco_absoluto(self):
        """Absolute pricing: preco_final = valor_preco."""
        variacoes = [
            {"atributo": "Tamanho", "valor": "GG", "tipo_preco": "absoluto",
             "valor_preco": 250.00, "ean": "", "estoque": "", "ativo": True},
        ]
        cobol_bridge.sync_variantes_for_produto(self.produto_id, variacoes, 100.00)

        listed = cobol_bridge.variantes_listar_por_produto(self.produto_id)
        assert len(listed) == 1
        assert listed[0]["preco"] == 250.00

    def test_sync_preco_delta(self):
        """Delta pricing: preco_final = preco_base + valor_preco."""
        variacoes = [
            {"atributo": "Tamanho", "valor": "GG", "tipo_preco": "delta",
             "valor_preco": 50.00, "ean": "", "estoque": "", "ativo": True},
        ]
        cobol_bridge.sync_variantes_for_produto(self.produto_id, variacoes, 100.00)

        listed = cobol_bridge.variantes_listar_por_produto(self.produto_id)
        assert len(listed) == 1
        assert listed[0]["preco"] == 150.00

    def test_sync_update_existente(self):
        """Second sync updates existing records (by nome match)."""
        v1 = [{"atributo": "Cor", "valor": "Vermelho", "tipo_preco": "delta",
               "valor_preco": 5.00, "ean": "111", "estoque": "", "ativo": True}]
        cobol_bridge.sync_variantes_for_produto(self.produto_id, v1, 100.00)

        v2 = [{"atributo": "Cor", "valor": "Vermelho", "tipo_preco": "absoluto",
               "valor_preco": 200.00, "ean": "222", "estoque": "", "ativo": True}]
        cobol_bridge.sync_variantes_for_produto(self.produto_id, v2, 100.00)

        listed = cobol_bridge.variantes_listar_por_produto(self.produto_id)
        assert len(listed) == 1  # no duplicate
        assert listed[0]["preco"] == 200.00
        assert listed[0]["codigo"] == "222"

    def test_sync_desativa_removidas(self):
        """Variants removed from form are deactivated in COBOL."""
        v1 = [
            {"atributo": "Cor", "valor": "Vermelho", "tipo_preco": "delta",
             "valor_preco": 0, "ean": "", "estoque": "", "ativo": True},
            {"atributo": "Cor", "valor": "Azul", "tipo_preco": "delta",
             "valor_preco": 0, "ean": "", "estoque": "", "ativo": True},
        ]
        cobol_bridge.sync_variantes_for_produto(self.produto_id, v1, 100.00)

        # Remove Azul, keep only Vermelho
        v2 = [
            {"atributo": "Cor", "valor": "Vermelho", "tipo_preco": "delta",
             "valor_preco": 0, "ean": "", "estoque": "", "ativo": True},
        ]
        cobol_bridge.sync_variantes_for_produto(self.produto_id, v2, 100.00)

        listed = cobol_bridge.variantes_listar_por_produto(self.produto_id)
        active = [v for v in listed if v["ativo"]]
        assert len(active) == 1
        assert active[0]["nome"] == "Cor: Vermelho"

    def test_sync_vazio_desativa_tudo(self):
        """Empty variacoes list deactivates all COBOL variants."""
        v1 = [{"atributo": "Cor", "valor": "Verde", "tipo_preco": "delta",
               "valor_preco": 0, "ean": "", "estoque": "", "ativo": True}]
        cobol_bridge.sync_variantes_for_produto(self.produto_id, v1, 100.00)

        cobol_bridge.sync_variantes_for_produto(self.produto_id, [], 100.00)

        listed = cobol_bridge.variantes_listar_por_produto(self.produto_id)
        active = [v for v in listed if v["ativo"]]
        assert len(active) == 0

    def test_sync_apenas_atributo(self):
        """Variant with only atributo (no valor) uses atributo as nome."""
        variacoes = [
            {"atributo": "Opcional", "valor": "", "tipo_preco": "delta",
             "valor_preco": 0, "ean": "", "estoque": "", "ativo": True},
        ]
        cobol_bridge.sync_variantes_for_produto(self.produto_id, variacoes, 100.00)

        listed = cobol_bridge.variantes_listar_por_produto(self.produto_id)
        assert len(listed) == 1
        assert listed[0]["nome"] == "Opcional"

    def test_sync_apenas_valor(self):
        """Variant with only valor (no atributo) uses valor as nome."""
        variacoes = [
            {"atributo": "", "valor": "Promoção", "tipo_preco": "absoluto",
             "valor_preco": 50.00, "ean": "", "estoque": "", "ativo": True},
        ]
        cobol_bridge.sync_variantes_for_produto(self.produto_id, variacoes, 100.00)

        listed = cobol_bridge.variantes_listar_por_produto(self.produto_id)
        assert len(listed) == 1
        assert listed[0]["nome"] == "Promoção"
        assert listed[0]["preco"] == 50.00

    def test_variantes_listar_por_produto(self):
        """variantes_listar_por_produto filters correctly."""
        cobol_bridge.variantes_incluir(
            {"produto_id": self.produto_id, "nome": "Teste A", "preco": 10})
        cobol_bridge.variantes_incluir(
            {"produto_id": 999, "nome": "Teste B", "preco": 20})

        result = cobol_bridge.variantes_listar_por_produto(self.produto_id)
        assert all(v["produto_id"] == self.produto_id for v in result)
        assert len(result) >= 1

        # Cleanup the extra product 999 variant
        for v in cobol_bridge.variantes_listar():
            if v.get("produto_id") == 999:
                cobol_bridge.variantes_excluir(v["id"])
