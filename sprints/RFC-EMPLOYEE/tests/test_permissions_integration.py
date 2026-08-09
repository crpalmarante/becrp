#!/usr/bin/env python3
"""Teste de integração — f_has_permission() contra a matriz RFC-009 §3.1.

Valida a checagem de permissões NO NÍVEL DO BANCO (migration 011) de ponta a
ponta via psycopg2, contra um cluster PostgreSQL 16 TEMPORÁRIO e descartável
(infra compartilhada em tests/pg_bootstrap.py):

  * bootstrap: initdb + pg_ctl em diretório efêmero (/tmp), porta livre;
  * aplica as migrations NA ORDEM do projeto: 002 → 009 → 011;
  * valida o seed da tabela permissions contra a matriz ação × papel do
    RFC-009 §3.1 (células ✅) e a função f_has_permission() em TODO o
    produto cartesiano ação × papel (40 casos), além de CSV multi-papel
    com espaços, fail-closed (NULL/vazio/papel desconhecido), o leitor de
    GUC (f_has_permission_guc + app.actor_roles) e a integridade do seed
    (PK, CHECK das 8 ações, FK para roles.code).

Executar:
  python3 -m unittest tests.test_permissions_integration -v

Requisitos (sem eles o teste é PULADO — nunca falha por falta de ambiente):
  * psycopg2 (única dependência de runtime obrigatória — PLAN_ERP §2);
  * E pelo menos um dos backends de banco: binários do PostgreSQL (initdb/pg_ctl
    — env PG_BINDIR, /usr/lib/postgresql/<versão>/bin ou `pg_config --bindir`)
    para o bootstrap de cluster, OU ERP_TEST_DATABASE_URL (CI) apontando para
    um banco dedicado/descartável (ver tests/pg_bootstrap.py).
"""
import unittest

try:
    import psycopg2
    import psycopg2.errors
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False

try:
    from tests.pg_bootstrap import HAS_PSYCOPG as _HAS_PG, TempCluster, test_backend_available
except ImportError:                                   # execução direta (sem pacote)
    from pg_bootstrap import HAS_PSYCOPG as _HAS_PG, TempCluster, test_backend_available

HAS_PSYCOPG = HAS_PSYCOPG and _HAS_PG

# --------------------------------------------------------------------------
# Referência independente — matriz RFC-009 §3.1 (ação × papel, células ✅).
# A autoridade do TESTE: o seed da 011 deve bater exatamente com isto.
# --------------------------------------------------------------------------
ACTIONS = [
    "abrir_competencia",
    "lancar_eventos",
    "calcular",
    "validar",
    "fechar",
    "registrar_pagamento",
    "manter_cadastros",
    "manter_usuarios",
]
ROLES = ["OPERADOR", "CONFERENTE", "APROVADOR", "TESOURARIA", "ADMINISTRADOR"]

MATRIX = {
    "abrir_competencia":  {"OPERADOR", "ADMINISTRADOR"},  # ✅ duplo
    "lancar_eventos":     {"OPERADOR"},
    "calcular":           {"OPERADOR"},
    "validar":            {"CONFERENTE"},
    "fechar":             {"APROVADOR"},
    "registrar_pagamento": {"TESOURARIA"},
    "manter_cadastros":   {"ADMINISTRADOR"},
    "manter_usuarios":    {"ADMINISTRADOR"},
}

MIGRATIONS = [
    "002_employees_departments_positions.sql",
    "009_users_roles_audit.sql",
    "011_permissions.sql",
]


class TestPermissionsIntegration(unittest.TestCase):
    """f_has_permission / f_has_permission_guc vs. matriz §3.1 (Postgres real)."""

    @classmethod
    def setUpClass(cls):
        if not HAS_PSYCOPG:
            raise unittest.SkipTest("psycopg2 não instalado")
        if not test_backend_available():
            raise unittest.SkipTest(
                "sem PostgreSQL: defina ERP_TEST_DATABASE_URL (CI) ou instale initdb/pg_ctl")
        cls.cluster = TempCluster(db_name="erp_perm_test", migrations=MIGRATIONS)
        # Limpeza garantida MESMO se o start() falhar daqui em diante:
        # addClassCleanup roda também quando o setUpClass levanta (stop() é
        # idempotente — seguro em cluster não iniciado).
        cls.addClassCleanup(cls.cluster.stop)
        cls.cluster.start()

    def _scalar(self, sql, params=None):
        conn = self.cluster.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()[0]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 1. Seed == matriz RFC-009 §3.1
    # ------------------------------------------------------------------
    def test_seed_bate_com_a_matriz(self):
        """As 9 células ✅ seedadas em permissions == matriz §3.1 do teste."""
        conn = self.cluster.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT action, role_code FROM permissions")
                got = {tuple(row) for row in cur.fetchall()}
        finally:
            conn.close()
        expected = {(a, r) for a, roles in MATRIX.items() for r in roles}
        self.assertEqual(got, expected)

    def test_8_acoes_e_5_papeis_seedados(self):
        """Seed: 8 ações distintas, 5 papéis e 9 células (linhas/colunas da matriz)."""
        n_actions = self._scalar("SELECT count(DISTINCT action) FROM permissions")
        n_roles = self._scalar("SELECT count(DISTINCT role_code) FROM permissions")
        n_cells = self._scalar("SELECT count(*) FROM permissions")
        n_catalog = self._scalar("SELECT count(*) FROM roles")   # catálogo da 009
        self.assertEqual(n_actions, len(ACTIONS))
        self.assertEqual(n_roles, len(ROLES))
        self.assertEqual(n_cells, 9)
        self.assertEqual(n_catalog, len(ROLES))   # papéis fixos da 009 == matriz

    # ------------------------------------------------------------------
    # 2. f_has_permission — produto cartesiano ação × papel (40 casos)
    # ------------------------------------------------------------------
    def test_produto_cartesiano_acao_papel(self):
        """f_has_permission(ação, papel) == célula da matriz para TODO o produto."""
        conn = self.cluster.connect()
        try:
            with conn.cursor() as cur:
                for action in ACTIONS:
                    for role in ROLES:
                        with self.subTest(action=action, role=role):
                            cur.execute("SELECT f_has_permission(%s, %s)", (action, role))
                            got = cur.fetchone()[0]
                            expected = role in MATRIX[action]
                            self.assertIs(got, expected,
                                          f"{action} × {role}: esperado {expected}")
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 3. Lista CSV multi-papel (espaços tolerados — padrão app.actor_roles)
    # ------------------------------------------------------------------
    def test_csv_multipapel_com_espacos(self):
        """CSV com espaços: qualquer papel da lista com a ação basta (OR)."""
        self.assertTrue(self._scalar(
            "SELECT f_has_permission('fechar', 'OPERADOR, APROVADOR')"))
        self.assertTrue(self._scalar(
            "SELECT f_has_permission('fechar', 'APROVADOR , CONFERENTE')"))
        self.assertFalse(self._scalar(
            "SELECT f_has_permission('fechar', 'OPERADOR, CONFERENTE')"))

    # ------------------------------------------------------------------
    # 4. Fail-closed
    # ------------------------------------------------------------------
    def test_fail_closed_nulo_vazio_e_desconhecido(self):
        """NULL/vazio/papel desconhecido/ação fora da matriz → FALSE."""
        self.assertFalse(self._scalar("SELECT f_has_permission('fechar', NULL)"))
        self.assertFalse(self._scalar("SELECT f_has_permission('fechar', '')"))
        self.assertFalse(self._scalar("SELECT f_has_permission('fechar', 'NAO_EXISTE')"))
        self.assertFalse(self._scalar("SELECT f_has_permission('acao_inexistente', 'OPERADOR')"))

    # ------------------------------------------------------------------
    # 5. f_has_permission_guc — lê os papéis do ator do GUC de sessão
    # ------------------------------------------------------------------
    def test_guc_le_papeis_do_ator(self):
        """SET app.actor_roles = ... → f_has_permission_guc segue a matriz."""
        conn = self.cluster.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SET app.actor_roles = 'APROVADOR'")
                cur.execute("SELECT f_has_permission_guc('fechar')")
                self.assertIs(cur.fetchone()[0], True)
                cur.execute("SELECT f_has_permission_guc('calcular')")
                self.assertIs(cur.fetchone()[0], False)

                cur.execute("SET app.actor_roles = 'OPERADOR,CONFERENTE'")
                cur.execute("SELECT f_has_permission_guc('calcular')")
                self.assertIs(cur.fetchone()[0], True)
                cur.execute("SELECT f_has_permission_guc('validar')")
                self.assertIs(cur.fetchone()[0], True)
                cur.execute("SELECT f_has_permission_guc('fechar')")
                self.assertIs(cur.fetchone()[0], False)
        finally:
            conn.close()

    def test_guc_ausente_fail_closed(self):
        """Sessão SEM app.actor_roles → f_has_permission_guc retorna FALSE."""
        self.assertFalse(self._scalar("SELECT f_has_permission_guc('fechar')"))

    # ------------------------------------------------------------------
    # 6. Integridade do seed (protege a matriz no nível do banco)
    # ------------------------------------------------------------------
    def test_duplicata_de_celula_rejeitada(self):
        """Repetir célula ✅ existente viola a PK (action, role_code)."""
        conn = self.cluster.connect()
        try:
            with self.assertRaises(psycopg2.errors.UniqueViolation):
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO permissions (action, role_code) "
                        "VALUES ('fechar', 'APROVADOR')")
        finally:
            conn.close()

    def test_acao_fora_da_matriz_rejeitada(self):
        """Ação fora das 8 da matriz viola o CHECK (linha nova da §3.1)."""
        conn = self.cluster.connect()
        try:
            with self.assertRaises(psycopg2.errors.CheckViolation):
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO permissions (action, role_code) "
                        "VALUES ('hackear', 'OPERADOR')")
        finally:
            conn.close()

    def test_papel_fora_do_catalogo_rejeitado(self):
        """Papel inexistente em roles viola a FK role_code → roles.code."""
        conn = self.cluster.connect()
        try:
            with self.assertRaises(psycopg2.errors.ForeignKeyViolation):
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO permissions (action, role_code) "
                        "VALUES ('fechar', 'CEO_ESPERTO')")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
