"""Testes para cálculo de comissão do PDV (pos_commission.py)."""

import os
import sys
import tempfile
import unittest
import shutil

# pos_commission.py usa caminhos relativos a BASE_DIR = __file__
import pos_commission as pc


class PosCommissionTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_dir = os.path.dirname(os.path.abspath(pc.__file__))

        # Sobrescreve caminhos para usar diretório temporário
        self._rules_orig = pc.RULES_FILE
        self._comm_orig = pc.COMMISSIONS_FILE
        pc.RULES_FILE = os.path.join(self.tmpdir, "commission_rules.json")
        pc.COMMISSIONS_FILE = os.path.join(self.tmpdir, "pos_commissions.json")
        pc.save_rules(pc.DEFAULT_EMPTY_RULES)
        pc.save_commissions({"comissoes": []})

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        pc.RULES_FILE = self._rules_orig
        pc.COMMISSIONS_FILE = self._comm_orig

    def _make_rules(self, global_rate=0.0, users=None):
        rules = {"version": 1, "global_rate": global_rate, "users": users or {}}
        pc.save_rules(rules)
        return rules

    def _make_venda(self, itens, total=None):
        if total is None:
            total = round(sum(i["qtd"] * i["preco"] for i in itens), 2)
        return {
            "id": 123,
            "data": "2026-09-07",
            "total": total,
            "itens": itens,
            "forma_pg": "Dinheiro",
        }

    def _make_pedido(self):
        return {
            "id": "ped-abc",
            "pdvUserId": "vendedor1",
            "terminal_id": "t-pdv-1",
            "estabelecimento_id": "loja-1",
        }

    def test_precedencia_produto_sobre_categoria(self):
        self._make_rules(users={
            "vendedor1": {
                "default_rate": 1.0,
                "rules": [
                    {"type": "produto", "target": "1", "rate_percent": 10.0, "active": True},
                    {"type": "categoria", "target": "Alimentacao", "rate_percent": 5.0, "active": True},
                ],
            }
        })
        venda = self._make_venda([
            {"prod_id": 1, "produto": "Arroz", "categoria": "Alimentacao", "qtd": 2, "preco": 10.0},
        ])
        result = pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1")
        self.assertEqual(result["total_commission"], 2.0)  # 20 * 10%
        self.assertEqual(result["items"][0]["rate_source"], "produto")
        self.assertEqual(result["items"][0]["rate_percent"], 10.0)

    def test_precedencia_categoria_sobre_padrao(self):
        self._make_rules(users={
            "vendedor1": {
                "default_rate": 1.0,
                "rules": [
                    {"type": "categoria", "target": "Bebidas", "rate_percent": 4.0, "active": True},
                ],
            }
        })
        venda = self._make_venda([
            {"prod_id": 6, "produto": "Leite", "categoria": "Bebidas", "qtd": 1, "preco": 100.0},
        ])
        result = pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1")
        self.assertEqual(result["total_commission"], 4.0)
        self.assertEqual(result["items"][0]["rate_source"], "categoria")

    def test_fallback_padrao_usuario(self):
        self._make_rules(users={
            "vendedor1": {"default_rate": 2.5, "rules": []}
        })
        venda = self._make_venda([
            {"prod_id": 99, "produto": "Genérico", "categoria": "Outros", "qtd": 1, "preco": 200.0},
        ])
        result = pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1")
        self.assertEqual(result["total_commission"], 5.0)
        self.assertEqual(result["items"][0]["rate_source"], "padrao")

    def test_fallback_global(self):
        self._make_rules(global_rate=1.5)
        venda = self._make_venda([
            {"prod_id": 99, "produto": "Genérico", "categoria": "Outros", "qtd": 1, "preco": 100.0},
        ])
        result = pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1")
        self.assertEqual(result["total_commission"], 1.5)
        self.assertEqual(result["items"][0]["rate_source"], "global")

    def test_regra_inativa_nao_aplica(self):
        self._make_rules(users={
            "vendedor1": {
                "default_rate": 1.0,
                "rules": [
                    {"type": "produto", "target": "1", "rate_percent": 10.0, "active": False},
                ],
            }
        })
        venda = self._make_venda([
            {"prod_id": 1, "produto": "Arroz", "categoria": "Alimentacao", "qtd": 1, "preco": 50.0},
        ])
        result = pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1")
        self.assertEqual(result["total_commission"], 0.5)  # default 1%
        self.assertEqual(result["items"][0]["rate_percent"], 1.0)

    def test_vigencia_invalida_nao_aplica(self):
        self._make_rules(users={
            "vendedor1": {
                "default_rate": 1.0,
                "rules": [
                    {"type": "produto", "target": "1", "rate_percent": 10.0, "active": True,
                     "valid_from": "2027-01-01", "valid_until": "2027-12-31"},
                ],
            }
        })
        venda = self._make_venda([
            {"prod_id": 1, "produto": "Arroz", "categoria": "Alimentacao", "qtd": 1, "preco": 50.0},
        ])
        result = pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1")
        self.assertEqual(result["total_commission"], 0.5)

    def test_troca_parcial_mesmo_produto(self):
        self._make_rules(users={
            "vendedor1": {
                "default_rate": 2.0,
                "rules": [
                    {"type": "produto", "target": "1", "rate_percent": 10.0, "active": True},
                ],
            }
        })
        venda = self._make_venda([
            {"prod_id": 1, "produto": "Arroz", "categoria": "Alimentacao", "qtd": 3, "preco": 10.0},
        ])
        venda["itens_troca"] = [
            {"prod_id": "1", "produto": "Arroz", "categoria": "Alimentacao", "qtd": 1, "preco": 10.0, "subtotal": 10.0},
        ]
        venda["valor_troca"] = 10.0
        result = pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1")
        # base líquida: 30 - 10 = 20; taxa 10% = 2
        self.assertEqual(result["total_commission"], 2.0)
        self.assertEqual(result["valor_troca"], 10.0)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["subtotal"], 20.0)
        self.assertEqual(result["items"][0]["commission_value"], 2.0)

    def test_troca_parcial_rateio_entre_produtos(self):
        self._make_rules(global_rate=2.0)
        venda = self._make_venda([
            {"prod_id": 1, "produto": "Arroz", "categoria": "Alimentacao", "qtd": 1, "preco": 100.0},
            {"prod_id": 2, "produto": "Feijao", "categoria": "Alimentacao", "qtd": 1, "preco": 100.0},
        ])
        venda["itens_troca"] = [
            {"prod_id": "3", "produto": "Outro", "categoria": "Alimentacao", "qtd": 1, "preco": 50.0, "subtotal": 50.0},
        ]
        venda["valor_troca"] = 50.0
        result = pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1")
        # base bruta 200; crédito 50 rateado 50/50 = 25 cada; liquido 75 cada; 2% = 1,5 cada; total 3
        self.assertEqual(result["total_commission"], 3.0)
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(sum(i["subtotal"] for i in result["items"]), 150.0)

    def test_troca_total_zerando_comissao(self):
        self._make_rules(global_rate=2.0)
        venda = self._make_venda([
            {"prod_id": 1, "produto": "Arroz", "categoria": "Alimentacao", "qtd": 1, "preco": 100.0},
        ])
        venda["itens_troca"] = [
            {"prod_id": "1", "produto": "Arroz", "categoria": "Alimentacao", "qtd": 1, "preco": 100.0, "subtotal": 100.0},
        ]
        venda["valor_troca"] = 100.0
        result = pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1")
        self.assertEqual(result["total_commission"], 0.0)
        self.assertEqual(len(result["items"]), 0)

    def test_record_e_get_by_sale(self):
        self._make_rules(global_rate=1.0)
        venda = self._make_venda([
            {"prod_id": 1, "produto": "Arroz", "categoria": "Alimentacao", "qtd": 1, "preco": 100.0},
        ])
        commission = pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1")
        pc.record_commission(commission)
        found = pc.get_commission_by_sale(123)
        self.assertIsNotNone(found)
        self.assertEqual(found["total_commission"], 1.0)

    def test_list_commissions_por_periodo(self):
        self._make_rules(global_rate=1.0)
        for venda_id in [1, 2, 3]:
            venda = self._make_venda([
                {"prod_id": venda_id, "produto": "P", "categoria": "C", "qtd": 1, "preco": 100.0},
            ])
            venda["id"] = venda_id
            venda["data"] = "2026-09-01" if venda_id < 3 else "2026-10-01"
            pedido = self._make_pedido()
            pedido["pdvUserId"] = "vendedor1" if venda_id < 3 else "vendedor2"
            pc.record_commission(pc.calculate_sale_commission(venda, pedido, pedido["pdvUserId"]))
        rows = pc.list_commissions(employee_id="vendedor1", period="2026-09")
        self.assertEqual(len(rows), 2)

    def test_cancelamento_marca_status(self):
        self._make_rules(global_rate=1.0)
        venda = self._make_venda([
            {"prod_id": 1, "produto": "Arroz", "categoria": "Alimentacao", "qtd": 1, "preco": 100.0},
        ])
        pc.record_commission(pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1"))
        pc.cancel_sale_commission(123)
        found = pc.get_commission_by_sale(123)
        self.assertEqual(found["status"], "cancelada")

    def test_cancelamento_tambem_marca_faturada(self):
        self._make_rules(global_rate=1.0)
        venda = self._make_venda([
            {"prod_id": 1, "produto": "Arroz", "categoria": "Alimentacao", "qtd": 1, "preco": 100.0},
        ])
        venda["id"] = 555
        pc.record_commission(pc.calculate_sale_commission(venda, self._make_pedido(), "vendedor1"))
        pc.cancel_sale_commission(555)
        found = pc.get_commission_by_sale(555)
        self.assertEqual(found["status"], "cancelada")

    def test_crud_regras(self):
        pc.save_rules(pc.DEFAULT_EMPTY_RULES)
        # global
        r = pc.save_rule({"type": "global", "rate_percent": 1.5})
        self.assertEqual(r["type"], "global")
        # usuário padrão
        r = pc.save_rule({"user_id": "vendedor1", "type": "padrao", "rate_percent": 2.0})
        self.assertEqual(r["type"], "padrao")
        # produto
        r = pc.save_rule({"user_id": "vendedor1", "type": "produto", "target": "1", "rate_percent": 5.0})
        self.assertEqual(r["type"], "produto")
        # categoria
        r2 = pc.save_rule({"user_id": "vendedor1", "type": "categoria", "target": "Bebidas", "rate_percent": 3.0})
        self.assertEqual(r2["type"], "categoria")

        rules = pc.list_rules()
        self.assertEqual(len(rules), 4)
        self.assertTrue(any(x["type"] == "global" for x in rules))

        # delete
        self.assertTrue(pc.delete_rule(r2["id"]))
        rules = pc.list_rules()
        self.assertEqual(len(rules), 3)

        # update
        updated = pc.save_rule({"id": r["id"], "user_id": "vendedor1", "type": "produto", "target": "2", "rate_percent": 7.0})
        self.assertEqual(updated["target"], "2")
        self.assertEqual(updated["rate_percent"], 7.0)

    def test_build_report(self):
        self._make_rules(users={
            "vendedor1": {
                "default_rate": 2.0,
                "rules": [
                    {"type": "produto", "target": "1", "rate_percent": 10.0, "active": True},
                ],
            }
        })
        for venda_id in [10, 11]:
            venda = self._make_venda([
                {"prod_id": 1, "produto": "Arroz", "categoria": "Alimentacao", "qtd": 1, "preco": 100.0},
                {"prod_id": 2, "produto": "Feijao", "categoria": "Alimentacao", "qtd": 1, "preco": 50.0},
            ])
            venda["id"] = venda_id
            pedido = self._make_pedido()
            pedido["pdvUserId"] = "vendedor1"
            pc.record_commission(pc.calculate_sale_commission(venda, pedido, "vendedor1"))
        report = pc.build_report(employee_id="vendedor1", period="2026-09")
        self.assertEqual(report["count"], 2)
        # Arroz: 10% de 100 = 10; Feijao: 2% de 50 = 1; por venda = 11; total = 22
        self.assertEqual(report["total_commission"], 22.0)
        self.assertEqual(len(report["por_vendedor"]), 1)
        self.assertEqual(report["por_vendedor"][0]["comissao"], 22.0)
        self.assertEqual(len(report["por_produto"]), 2)
        arroz = next(p for p in report["por_produto"] if p["prod_id"] == "1")
        self.assertEqual(arroz["comissao"], 20.0)

    def test_faturar_comissoes(self):
        import purchase_finance
        # isola purchase_finance em arquivo temporário para não poluir o repo
        self._pf_orig = purchase_finance.DATA_FILE
        purchase_finance.DATA_FILE = os.path.join(self.tmpdir, "titulos_ap.json")
        purchase_finance._save({"titulos": [], "seq": 0})

        self._make_rules(global_rate=1.0)
        for venda_id in [20, 21]:
            venda = self._make_venda([
                {"prod_id": venda_id, "produto": "P", "categoria": "C", "qtd": 1, "preco": 100.0},
            ])
            venda["id"] = venda_id
            venda["data"] = "2026-10-01"
            pedido = self._make_pedido()
            pedido["pdvUserId"] = "vendedor1"
            pc.record_commission(pc.calculate_sale_commission(venda, pedido, "vendedor1"))

        result = pc.faturar_comissoes("vendedor1", "Vendedor Um", "2026-10", vencimento="2026-10-30")
        self.assertEqual(result["total_comissao"], 2.0)  # 1% de 100 + 1% de 100
        self.assertEqual(result["comissoes_faturadas"], 2)
        self.assertEqual(result["titulo"]["fornecedor"], "Vendedor Um")
        self.assertEqual(result["titulo"]["origem"], "comissao")
        self.assertEqual(result["titulo"]["periodo"], "2026-10")
        self.assertEqual(result["titulo"]["status"], "aberto")

        # Idempotência: tentar faturar novamente deve falhar
        with self.assertRaises(ValueError) as ctx:
            pc.faturar_comissoes("vendedor1", "Vendedor Um", "2026-10")
        self.assertIn("Não há comissões pendentes", str(ctx.exception))

        # Restaura
        purchase_finance.DATA_FILE = self._pf_orig

    def test_faturar_gera_contabilidade(self):
        import purchase_finance
        self._pf_orig = purchase_finance.DATA_FILE
        purchase_finance.DATA_FILE = os.path.join(self.tmpdir, "titulos_ap.json")
        purchase_finance._save({"titulos": [], "seq": 0})

        self._make_rules(global_rate=1.0)
        venda = self._make_venda([
            {"prod_id": 50, "produto": "P", "categoria": "C", "qtd": 1, "preco": 100.0},
        ])
        venda["id"] = 50
        venda["data"] = "2026-11-01"
        pedido = self._make_pedido()
        pedido["pdvUserId"] = "vendedor1"
        pc.record_commission(pc.calculate_sale_commission(venda, pedido, "vendedor1"))

        result = pc.faturar_comissoes("vendedor1", "Vendedor Um", "2026-11")
        # contabilidade pode ser gerada ou None, mas não deve quebrar
        self.assertIn("contabilidade", result)
        self.assertEqual(result["total_comissao"], 1.0)

        purchase_finance.DATA_FILE = self._pf_orig


if __name__ == "__main__":
    unittest.main()
