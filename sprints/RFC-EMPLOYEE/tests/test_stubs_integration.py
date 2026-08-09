#!/usr/bin/env python3
"""Teste de integração — documento do holerite (migration 014).

Valida payroll_stubs (RFC-007 — demonstrativo de pagamento) de ponta a ponta
via psycopg2, num cluster PostgreSQL 16 TEMPORÁRIO e descartável (infra
compartilhada em tests/pg_bootstrap.py):

  * aplica as migrations NA ORDEM do projeto: 002 → 009 → 011 → 010 → 012 → 014;
  * valida a PERMISSÃO DE EMISSÃO POR AÇÃO (RFC-009 §3.1 via 011):
    emitir holerite exige f_has_permission_guc('calcular') (OPERADOR) —
    fail-closed sem GUC;
  * valida a emissão SÓ DE EXECUÇÃO CALCULADA (RFC-006 regra 1: valores
    prontos) — em_calculo/cancelada rejeitadas;
  * valida o SNAPSHOT do cabeçalho (RFC-007 §2.1: nome, CPF, admissão, cargo,
    departamento, competência) tirado do cadastro no momento da emissão;
  * valida a RFC-007 regra 1 ("nada é digitado no holerite"): snapshot
    fornecido no INSERT é SOBRESCRITO pelo trigger (notes preservada);
  * valida UNIQUE(line_id) — um holerite por resultado — e que a linha
    pertence à execução informada;
  * valida a IMUTABILIDADE (RFC-007 regra 4): UPDATE/DELETE/TRUNCATE
    bloqueados (mesmo p/ ADMINISTRADOR).

Executar:
  python3 -m unittest tests.test_stubs_integration -v
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

MIGRATIONS = [
    "002_employees_departments_positions.sql",
    "009_users_roles_audit.sql",
    "011_permissions.sql",
    "010_payroll_periods_events.sql",
    "012_payroll_runs_lines.sql",
    "014_payroll_stubs.sql",
]

# Linha mínima de resultado — valores do EXEMPLO-competencia.md:
# proventos 4.806,82 · descontos 787,26 (INSS 464,32 + IRRF 322,94)
# · líquido 4.019,56 — satisfaz a equação do RFC-007 regra 3.
LINE = (
    "INSERT INTO payroll_lines (run_id, employee_id, base_salary, "
    "total_proventos, total_descontos, base_inss, inss, base_irrf, irrf, "
    "base_fgts, liquid_value) VALUES "
    "({run_id}, {employee_id}, {base_salary}, {proventos}, {descontos}, "
    "{base_inss}, {inss}, {base_irrf}, {irrf}, {base_fgts}, {liquid}) "
    "RETURNING id"
)

# O INSERT do holerite só precisa de run_id + line_id (+ notes opcional):
# o trigger tira TODO o resto do processamento (RFC-007 regra 1).
STUB = "INSERT INTO payroll_stubs (run_id, line_id) VALUES ({run_id}, {line_id})"


class TestStubsIntegration(unittest.TestCase):
    """payroll_stubs — permissão, emissão só em calculada, snapshot, UNIQUE, imutabilidade."""

    @classmethod
    def setUpClass(cls):
        if not HAS_PSYCOPG:
            raise unittest.SkipTest("psycopg2 não instalado")
        if not test_backend_available():
            raise unittest.SkipTest(
                "sem PostgreSQL: defina ERP_TEST_DATABASE_URL (CI) ou instale initdb/pg_ctl")
        cls.cluster = TempCluster(db_name="erp_stubs_test", migrations=MIGRATIONS)
        # Limpeza garantida MESMO se o start() falhar: addClassCleanup roda
        # também quando o setUpClass levanta (stop() idempotente).
        cls.addClassCleanup(cls.cluster.stop)
        cls.cluster.start()

        # cadastros base (uma vez, sem GUC — 002 não tem trigger de permissão)
        cls._run("INSERT INTO departments (code, description) VALUES ('TI', 'Tecnologia')")
        cls._run("INSERT INTO positions (code, description) VALUES ('DEV', 'Desenvolvedor')")
        cls._run(
            "INSERT INTO employees (full_name, birth_date, gender, nationality, cpf, "
            "address_cep, address_street, address_number, address_neighborhood, "
            "address_city, address_uf, ctps_number, ctps_series, ctps_uf, "
            "admission_date, position_id, department_id, contract_type, base_salary, "
            "payment_form, bank_code, bank_agency, bank_account, transit_benefit) VALUES "
            "('Maria da Silva', '1990-05-10', 'F', 'Brasileira', '12345678901', "
            "'01001-000', 'Rua A', '10', 'Centro', 'Sao Paulo', 'SP', '1234567', "
            "'001', 'SP', '2020-01-05', 1, 1, 'CLT', 4500.00, 'mensalista', "
            "'001', '0001', '12345-6', true)")

    # ------------------------------------------------------------------
    # Helpers — cada chamada abre sessão própria (GUC de sessão sempre limpo)
    # ------------------------------------------------------------------
    @classmethod
    def _run(cls, sql, guc=None):
        """Executa esperando sucesso (GUC opcional na mesma sessão)."""
        conn = cls.cluster.connect()
        try:
            with conn.cursor() as cur:
                if guc:
                    cur.execute(f"SET app.actor_roles = '{guc}'")
                cur.execute(sql)
        finally:
            conn.close()

    def _fails(self, sql, guc=None, err=psycopg2.errors.RaiseException, msg=None):
        """Executa esperando erro; valida a classe e (opcional) fragmento."""
        conn = self.cluster.connect()
        try:
            with conn.cursor() as cur:
                if guc:
                    cur.execute(f"SET app.actor_roles = '{guc}'")
                with self.assertRaises(err) as cm:
                    cur.execute(sql)
                if msg:
                    self.assertIn(msg, str(cm.exception))
        finally:
            conn.close()

    def _scalar(self, sql, guc=None):
        conn = self.cluster.connect()
        try:
            with conn.cursor() as cur:
                if guc:
                    cur.execute(f"SET app.actor_roles = '{guc}'")
                cur.execute(sql)
                return cur.fetchone()[0]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Helpers de negócio (competência → execução → linha → calculada)
    # ------------------------------------------------------------------
    def _open(self, ref, year, month):
        self._run(
            f"INSERT INTO payroll_periods (reference, year, month, kind) "
            f"VALUES ('{ref}', {year}, {month}, 'mensal')", guc="OPERADOR")

    def _period_id(self, ref):
        return self._scalar(f"SELECT id FROM payroll_periods WHERE reference = '{ref}'")

    def _new_run(self, period_id, guc="OPERADOR"):
        return self._scalar(
            f"INSERT INTO payroll_runs (period_id) VALUES ({period_id}) RETURNING id",
            guc=guc)

    def _new_line(self, run_id, employee_id=1):
        """Insere a linha de resultado e devolve o id real (RETURNING id)."""
        return self._scalar(
            LINE.format(run_id=run_id, employee_id=employee_id, base_salary=4500.00,
                        proventos=4806.82, descontos=787.26,
                        base_inss=4806.82, inss=464.32,
                        base_irrf=4019.56, irrf=322.94,
                        base_fgts=4806.82, liquid=4019.56),
            guc="OPERADOR")

    def _calculada(self, run_id):
        """Transiciona a execução em_calculo → calculada (RFC-006 §3.2)."""
        self._run(f"UPDATE payroll_runs SET status = 'calculada' WHERE id = {run_id}",
                  guc="OPERADOR")

    # ------------------------------------------------------------------
    # 1. Estrutura e restrições
    # ------------------------------------------------------------------
    def test_estrutura_e_restricoes(self):
        """payroll_stubs existe com UNIQUE(line_id) e FKs p/ run e line."""
        n = self._scalar(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_name = 'payroll_stubs'")
        self.assertEqual(n, 1)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_constraint WHERE conname = 'uq_stub_per_line'"), 1)
        # FKs auto-geradas (padrão <tabela>_<coluna>_fkey)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_constraint "
            "WHERE conname IN ('payroll_stubs_run_id_fkey', 'payroll_stubs_line_id_fkey')"), 2)

    # ------------------------------------------------------------------
    # 2. Permissão de emissão (RFC-009 §3.1 via db/011 — ação 'calcular')
    # ------------------------------------------------------------------
    def test_permissao_emissao(self):
        """Emitir holerite exige ação calcular: OPERADOR ok, outros/sem-GUC não."""
        self._open("2026-08", 2026, 8)
        run_id = self._new_run(self._period_id("2026-08"))
        line_id = self._new_line(run_id)
        self._calculada(run_id)

        self._fails(STUB.format(run_id=run_id, line_id=line_id), msg="exige a ação calcular")
        self._fails(STUB.format(run_id=run_id, line_id=line_id), guc="CONFERENTE",
                    msg="exige a ação calcular")
        self._run(STUB.format(run_id=run_id, line_id=line_id), guc="OPERADOR")

    # ------------------------------------------------------------------
    # 3. Emissão só de execução CALCULADA (RFC-006 regra 1)
    # ------------------------------------------------------------------
    def test_emissao_somente_calculada(self):
        """em_calculo e cancelada rejeitadas; calculada aceita."""
        self._open("2026-07", 2026, 7)
        pid = self._period_id("2026-07")
        r1 = self._new_run(pid)
        line1 = self._new_line(r1)
        # execução ainda em_calculo → rejeitado (valores não estão prontos)
        self._fails(STUB.format(run_id=r1, line_id=line1), guc="OPERADOR", msg="CALCULADA")

        self._calculada(r1)
        self._run(STUB.format(run_id=r1, line_id=line1), guc="OPERADOR")

        # execução cancelada → rejeitado (nunca é calculada)
        r2 = self._new_run(pid)
        line2 = self._new_line(r2)
        self._run(f"UPDATE payroll_runs SET status = 'cancelada' WHERE id = {r2}",
                  guc="OPERADOR")
        self._fails(STUB.format(run_id=r2, line_id=line2), guc="OPERADOR", msg="CALCULADA")

    # ------------------------------------------------------------------
    # 4. Snapshot do cabeçalho (RFC-007 §2.1) tirado do cadastro
    # ------------------------------------------------------------------
    def test_snapshot_do_cabecalho(self):
        """Cabeçalho congelado no momento da emissão: nome, CPF, admissão, cargo, departamento."""
        self._open("2026-06", 2026, 6)
        run_id = self._new_run(self._period_id("2026-06"))
        line_id = self._new_line(run_id)
        self._calculada(run_id)
        self._run(STUB.format(run_id=run_id, line_id=line_id), guc="OPERADOR")

        self.assertEqual(self._scalar(
            f"SELECT employee_full_name FROM payroll_stubs WHERE line_id = {line_id}"),
            "Maria da Silva")
        self.assertEqual(self._scalar(
            f"SELECT employee_cpf FROM payroll_stubs WHERE line_id = {line_id}"),
            "12345678901")
        self.assertEqual(self._scalar(
            f"SELECT admission_date::text FROM payroll_stubs WHERE line_id = {line_id}"),
            "2020-01-05")
        self.assertEqual(self._scalar(
            f"SELECT position_description FROM payroll_stubs WHERE line_id = {line_id}"),
            "Desenvolvedor")
        self.assertEqual(self._scalar(
            f"SELECT department_description FROM payroll_stubs WHERE line_id = {line_id}"),
            "Tecnologia")
        self.assertEqual(self._scalar(
            f"SELECT period_reference FROM payroll_stubs WHERE line_id = {line_id}"),
            "2026-06")
        self.assertTrue(self._scalar(
            f"SELECT issued_at IS NOT NULL FROM payroll_stubs WHERE line_id = {line_id}"))

    # ------------------------------------------------------------------
    # 5. RFC-007 regra 1 — nada é digitado no holerite
    # ------------------------------------------------------------------
    def test_regra1_nada_digitado(self):
        """Snapshot fornecido no INSERT é SOBRESCRITO pelo trigger (notes preservada)."""
        self._open("2026-05", 2026, 5)
        run_id = self._new_run(self._period_id("2026-05"))
        line_id = self._new_line(run_id)
        self._calculada(run_id)

        # tenta injetar snapshot falso — o trigger tira do cadastro (RFC-007 regra 1)
        self._run(
            "INSERT INTO payroll_stubs (run_id, line_id, employee_full_name, "
            "period_reference, notes) VALUES "
            f"({run_id}, {line_id}, 'FRAUDE', '1999-01', 'obs')", guc="OPERADOR")

        self.assertEqual(self._scalar(
            f"SELECT employee_full_name FROM payroll_stubs WHERE line_id = {line_id}"),
            "Maria da Silva")
        self.assertEqual(self._scalar(
            f"SELECT period_reference FROM payroll_stubs WHERE line_id = {line_id}"),
            "2026-05")
        # notes é do usuário (RFC-007 decisão 2) e é preservada
        self.assertEqual(self._scalar(
            f"SELECT notes FROM payroll_stubs WHERE line_id = {line_id}"), "obs")

    # ------------------------------------------------------------------
    # 6. UNIQUE(line_id) — um holerite por resultado
    # ------------------------------------------------------------------
    def test_unicidade_line_id(self):
        """Duplicar o holerite do mesmo resultado viola UNIQUE(line_id)."""
        self._open("2026-04", 2026, 4)
        run_id = self._new_run(self._period_id("2026-04"))
        line_id = self._new_line(run_id)
        self._calculada(run_id)

        self._run(STUB.format(run_id=run_id, line_id=line_id), guc="OPERADOR")
        self._fails(STUB.format(run_id=run_id, line_id=line_id), guc="OPERADOR",
                    err=psycopg2.errors.UniqueViolation)

    # ------------------------------------------------------------------
    # 7. Linha pertence à execução informada
    # ------------------------------------------------------------------
    def test_linha_pertence_a_execucao(self):
        """Holerite só é emitido da linha da própria execução (run_id = line.run_id)."""
        self._open("2026-03", 2026, 3)
        pid = self._period_id("2026-03")
        r1 = self._new_run(pid)
        line1 = self._new_line(r1)
        self._calculada(r1)

        r2 = self._new_run(pid)
        self._fails(STUB.format(run_id=r2, line_id=line1), guc="OPERADOR",
                    msg="não pertence")
        # linha inexistente também rejeitada
        self._fails(STUB.format(run_id=r1, line_id=999), guc="OPERADOR",
                    msg="inexistente")

    # ------------------------------------------------------------------
    # 8. Imutabilidade (RFC-007 regra 4)
    # ------------------------------------------------------------------
    def test_imutabilidade(self):
        """UPDATE/DELETE/TRUNCATE de payroll_stubs bloqueados (mesmo p/ ADMINISTRADOR)."""
        self._open("2026-02", 2026, 2)
        run_id = self._new_run(self._period_id("2026-02"))
        line_id = self._new_line(run_id)
        self._calculada(run_id)
        self._run(STUB.format(run_id=run_id, line_id=line_id), guc="OPERADOR")

        self._fails(f"UPDATE payroll_stubs SET notes = 'x' WHERE line_id = {line_id}",
                    guc="OPERADOR", msg="imutável")
        self._fails(f"DELETE FROM payroll_stubs WHERE line_id = {line_id}",
                    guc="ADMINISTRADOR", msg="imutável")
        self._fails("TRUNCATE payroll_stubs", msg="imutável")


if __name__ == "__main__":
    unittest.main(verbosity=2)
