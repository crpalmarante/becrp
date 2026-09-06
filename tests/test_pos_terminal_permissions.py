"""Testes para restrição de acesso a PDVs por usuário."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# server.py lê sys.argv[1] como porta; isolamos antes de importar
_orig_argv = sys.argv[:]
sys.argv = [sys.argv[0]]
try:
    import server
finally:
    sys.argv = _orig_argv


class PosTerminalPermissionsTest(unittest.TestCase):
    def _terminais(self):
        return [
            {"id": "t-pdv-1", "tipo": "pdv", "ativo": True, "estabelecimento_id": "e1", "usuario_id": "u-vendedor-1"},
            {"id": "t-pdv-2", "tipo": "pdv", "ativo": True, "estabelecimento_id": "e1", "usuario_id": "u-vendedor-2"},
            {"id": "t-pdv-3", "tipo": "pdv", "ativo": True, "estabelecimento_id": "e2", "usuario_id": ""},
            {"id": "t-caixa-1", "tipo": "caixa", "ativo": True, "estabelecimento_id": "e1", "usuario_id": "u-caixa-1"},
            {"id": "t-inativo", "tipo": "pdv", "ativo": False, "estabelecimento_id": "e1", "usuario_id": "u-vendedor-1"},
        ]

    def test_admin_ve_todos_ativos(self):
        users = {"u-admin": {"role": "admin"}}
        terminais = self._terminais()
        permitidos = server._terminais_permitidos("u-admin", users=users, terminais=terminais)
        self.assertEqual({t["id"] for t in permitidos}, {"t-pdv-1", "t-pdv-2", "t-pdv-3", "t-caixa-1"})

    def test_gerente_ve_estabelecimentos_vinculados(self):
        users = {
            "u-gerente": {"role": "gerente", "empresas": {"e1": "gerente"}}
        }
        terminais = self._terminais()
        permitidos = server._terminais_permitidos("u-gerente", users=users, terminais=terminais)
        self.assertEqual({t["id"] for t in permitidos}, {"t-pdv-1", "t-pdv-2", "t-caixa-1"})

    def test_gerente_herda_estabelecimento_do_terminal_legado(self):
        users = {
            "u-gerente": {"role": "gerente", "empresas": {}}
        }
        terminais = self._terminais()
        permitidos = server._terminais_permitidos("u-gerente", users=users, terminais=terminais)
        # sem vínculo legado nem empresa, não vê nada
        self.assertEqual(permitidos, [])

    def test_vendedor_somente_pdvs_permitidos(self):
        users = {
            "u-vendedor": {"role": "vendedor", "pos_terminal_ids": ["t-pdv-1", "t-pdv-3"]}
        }
        terminais = self._terminais()
        permitidos = server._terminais_permitidos("u-vendedor", users=users, terminais=terminais)
        self.assertEqual({t["id"] for t in permitidos}, {"t-pdv-1", "t-pdv-3"})

    def test_vendedor_herda_vinculo_legado(self):
        users = {
            "u-vendedor-1": {"role": "vendedor", "pos_terminal_ids": []}
        }
        terminais = self._terminais()
        permitidos = server._terminais_permitidos("u-vendedor-1", users=users, terminais=terminais)
        self.assertEqual({t["id"] for t in permitidos}, {"t-pdv-1"})

    def test_caixa_somente_caixa_permitido(self):
        users = {
            "u-caixa": {"role": "caixa", "pos_terminal_ids": ["t-caixa-1"]}
        }
        terminais = self._terminais()
        permitidos = server._terminais_permitidos("u-caixa", users=users, terminais=terminais)
        self.assertEqual({t["id"] for t in permitidos}, {"t-caixa-1"})

    def test_fiscal_sem_acesso(self):
        users = {"u-fiscal": {"role": "fiscal"}}
        terminais = self._terminais()
        permitidos = server._terminais_permitidos("u-fiscal", users=users, terminais=terminais)
        self.assertEqual(permitidos, [])

    def test_filtrar_por_terminais_permitidos(self):
        users = {"u-vendedor": {"role": "vendedor", "pos_terminal_ids": ["t-pdv-1"]}}
        terminais = self._terminais()
        rows = [
            {"id": "v1", "terminal_id": "t-pdv-1"},
            {"id": "v2", "terminal_id": "t-pdv-2"},
            {"id": "v3", "terminal_caixa_id": "t-pdv-1"},
        ]
        filtrado = server._filtrar_por_terminais_permitidos("u-vendedor", rows, users=users, terminais=terminais)
        self.assertEqual([r["id"] for r in filtrado], ["v1", "v3"])

    def test_terminal_do_usuario_retorna_primeiro(self):
        users = {"u-vendedor": {"role": "vendedor", "pos_terminal_ids": ["t-pdv-2", "t-pdv-1"]}}
        terminais = self._terminais()
        term = server._terminal_do_usuario("u-vendedor", users=users, terminais=terminais)
        # a ordem segue a lista de terminais; t-pdv-1 aparece primeiro
        self.assertEqual(term["id"], "t-pdv-1")


if __name__ == "__main__":
    unittest.main()
