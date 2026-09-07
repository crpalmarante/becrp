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


if __name__ == "__main__":
    unittest.main()
