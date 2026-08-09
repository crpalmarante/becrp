#!/usr/bin/env python3
"""Teste de integração — execução e resultado da folha (migration 012).

Valida payroll_runs (execução do processamento) e payroll_lines (resultado
consolidado por funcionário) de ponta a ponta via psycopg2, num cluster
PostgreSQL 16 TEMPORÁRIO e descartável (infra compartilhada em
tests/pg_bootstrap.py):

  * aplica as migrations NA ORDEM do projeto: 002 → 009 → 011 → 010 → 012;
  * valida a PERMISSÃO DE ESCRITA POR AÇÃO (RFC-009 §3.1 via 011):
    escrever execução/resultado exige f_has_permission_guc('calcular')
    (OPERADOR) — fail-closed sem GUC;
  * valida o run_number SEQUENCIAL por competência (recálculo = nova execução,
    RFC-015 §3.1) e o status forçado 'em_calculo' no INSERT;
  * valida a EQUAÇÃO DO LÍQUIDO (RFC-007 regra 3: líquido = proventos −
    descontos — CHECK no banco) e a UNIQUE (run_id, employee_id);
  * valida o funcionário 'desligado' fora de processamento novo (RFC-002 §3
    regra 5) e o resultado só em execução em_calculo (invariante 5);
  * valida o CONGELAMENTO pós-'calculada' (RFC-006 regra 1: nada se escreve)
    e a proteção contra exclusão física (DELETE/TRUNCATE).

Executar:
  python3 -m unittest tests.test_runs_lines_integration -v
"""
import unittest
from decimal import Decimal

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
]

# Linha mínima de resultado — valores do EXEMPLO-competencia.md:
# proventos 4.806,82 · descontos 787,26 (INSS 464,32 + IRRF 322,94)
# · líquido 4.019,56 — satisfaz a equação do RFC-007 regra 3.
LINE = (
    "INSERT INTO payroll_lines (run_id, employee_id, base_salary, "
    "total_proventos, total_descontos, base_inss, inss, base_irrf, irrf, "
    "base_fgts, liquid_value) VALUES "
    "({run_id}, {employee_id}, {base_salary}, {proventos}, {descontos}, "
    "{base_inss}, {inss}, {base_irrf}, {irrf}, {base_fgts}, {liquid})"
)


class TestRunsLinesIntegration(unittest.TestCase):
    """payroll_runs/payroll_lines — permissão, run_number, congelamento, líquido."""

    @classmethod
    def setUpClass(cls):
        if not HAS_PSYCOPG:
            raise unittest.SkipTest("psycopg2 não instalado")
        if not test_backend_available():
            raise unittest.SkipTest(
                "sem PostgreSQL: defina ERP_TEST_DATABASE_URL (CI) ou instale initdb/pg_ctl")
        cls.cluster = TempCluster(db_name="erp_runs_test", migrations=MIGRATIONS)
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
    # Helpers de negócio (competência → execução → linha)
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

    def _line_sql(self, run_id, employee_id=1, base=4500.00, proventos=4806.82,
                  descontos=787.26, liquid=4019.56):
        return LINE.format(run_id=run_id, employee_id=employee_id, base_salary=base,
                           proventos=proventos, descontos=descontos,
                           base_inss=proventos, inss=464.32,
                           base_irrf=4019.56, irrf=322.94,
                           base_fgts=proventos, liquid=liquid)

    # ------------------------------------------------------------------
    # 1. Estrutura e restrições
    # ------------------------------------------------------------------
    def test_tabelas_e_restricoes(self):
        """payroll_runs/payroll_lines existem com CHECK do líquido e UNIQUE."""
        n = self._scalar(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_name IN ('payroll_runs', 'payroll_lines')")
        self.assertEqual(n, 2)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_constraint WHERE conname = 'ck_liquid_equation'"), 1)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_constraint WHERE conname = 'uq_line_per_employee'"), 1)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_constraint WHERE conname = 'uq_run_per_period'"), 1)

    # ------------------------------------------------------------------
    # 2. Permissão de escrita por ação (RFC-009 §3.1 via db/011)
    # ------------------------------------------------------------------
    def test_permissao_criar_execucao(self):
        """Criar execução exige ação calcular: OPERADOR ok, outros/sem-GUC não."""
        self._open("2026-08", 2026, 8)
        pid = self._period_id("2026-08")
        # OPERADOR cria a 1ª execução; valida o run_number (sequencial por
        # competência) e não o id global do BIGSERIAL (outros testes já
        # consumiram ids — ordem alfabética do unittest).
        first_run = self._new_run(pid)
        self.assertEqual(self._scalar(
            f"SELECT run_number FROM payroll_runs WHERE id = {first_run}"), 1)
        self._fails(f"INSERT INTO payroll_runs (period_id) VALUES ({pid})",
                    guc="CONFERENTE", msg="exige a ação calcular")
        self._fails(f"INSERT INTO payroll_runs (period_id) VALUES ({pid})",
                    msg="exige a ação calcular")
        self._fails("INSERT INTO payroll_runs (period_id) VALUES (999)",
                    guc="OPERADOR", msg="Competência inexistente")

    def test_permissao_gravar_resultado(self):
        """Gravar resultado exige ação calcular: OPERADOR ok, outros/sem-GUC não."""
        self._open("2026-06", 2026, 6)
        run_id = self._new_run(self._period_id("2026-06"))
        self._run(self._line_sql(run_id), guc="OPERADOR")
        # roundtrip: o valor gravado bate com o inserido (líquido da equação)
        self.assertEqual(self._scalar(
            f"SELECT liquid_value FROM payroll_lines WHERE run_id = {run_id}"),
            Decimal("4019.56"))
        self._fails(self._line_sql(run_id), guc="CONFERENTE", msg="exige a ação calcular")
        self._fails(self._line_sql(run_id), msg="exige a ação calcular")

    # ------------------------------------------------------------------
    # 3. run_number sequencial + status forçado
    # ------------------------------------------------------------------
    def test_run_number_sequencial_e_status(self):
        """Cada execução nasce 'em_calculo' com run_number sequencial (1, 2)."""
        self._open("2026-07", 2026, 7)
        pid = self._period_id("2026-07")
        r1 = self._new_run(pid)
        r2 = self._new_run(pid)
        self.assertNotEqual(r1, r2)
        self.assertEqual(self._scalar(
            f"SELECT run_number FROM payroll_runs WHERE id = {r1}"), 1)
        self.assertEqual(self._scalar(
            f"SELECT run_number FROM payroll_runs WHERE id = {r2}"), 2)
        for run_id in (r1, r2):
            self.assertEqual(self._scalar(
                f"SELECT status FROM payroll_runs WHERE id = {run_id}"), "em_calculo")

    # ------------------------------------------------------------------
    # 4. Equação do líquido (RFC-007 regra 3) e unicidade por funcionário
    # ------------------------------------------------------------------
    def test_equacao_do_liquido(self):
        """líquido ≠ proventos − descontos viola o CHECK ck_liquid_equation."""
        self._open("2026-05", 2026, 5)
        run_id = self._new_run(self._period_id("2026-05"))
        self._fails(self._line_sql(run_id, proventos=4806.82, descontos=787.26,
                                   liquid=9999.00),
                    guc="OPERADOR", err=psycopg2.errors.CheckViolation)

    def test_unicidade_linha_por_funcionario(self):
        """Duplicar funcionário na mesma execução viola UNIQUE(run_id, employee_id)."""
        self._open("2026-04", 2026, 4)
        run_id = self._new_run(self._period_id("2026-04"))
        self._run(self._line_sql(run_id), guc="OPERADOR")
        self._fails(self._line_sql(run_id), guc="OPERADOR",
                    err=psycopg2.errors.UniqueViolation)

    # ------------------------------------------------------------------
    # 5. Funcionário inexistente / desligado (RFC-002 §3 regra 5)
    # ------------------------------------------------------------------
    def test_funcionario_inexistente(self):
        """Linha de funcionário inexistente é rejeitada."""
        self._open("2026-03", 2026, 3)
        run_id = self._new_run(self._period_id("2026-03"))
        self._fails(self._line_sql(run_id, employee_id=999), guc="OPERADOR",
                    msg="inexistente")

    def test_funcionario_desligado(self):
        """Desligado não entra em processamento novo; restaurado volta a entrar."""
        self._open("2026-02", 2026, 2)
        run_id = self._new_run(self._period_id("2026-02"))
        self._run("UPDATE employees SET employment_status = 'desligado' WHERE id = 1")
        self._fails(self._line_sql(run_id), guc="OPERADOR", msg="desligado")
        self._run("UPDATE employees SET employment_status = 'ativo' WHERE id = 1")
        self._run(self._line_sql(run_id), guc="OPERADOR")

    # ------------------------------------------------------------------
    # 6. Transições da execução e invariante 5 (linha só em em_calculo)
    # ------------------------------------------------------------------
    def test_transicoes_da_execucao(self):
        """em_calculo→calculada (marco) | cancelada; sem regressão; linha fora de em_calculo não."""
        self._open("2026-01", 2026, 1)
        pid = self._period_id("2026-01")
        r1 = self._new_run(pid)
        r2 = self._new_run(pid)

        self._fails(f"UPDATE payroll_runs SET status = 'calculada' WHERE id = {r1}",
                    guc="CONFERENTE", msg="exige a ação calcular")
        self._run(f"UPDATE payroll_runs SET status = 'calculada' WHERE id = {r1}",
                  guc="OPERADOR")
        self.assertTrue(self._scalar(
            f"SELECT calculated_at IS NOT NULL FROM payroll_runs WHERE id = {r1}"))
        self._fails(f"UPDATE payroll_runs SET status = 'em_calculo' WHERE id = {r1}",
                    guc="OPERADOR", msg="Transição de execução inválida")

        self._run(f"UPDATE payroll_runs SET status = 'cancelada' WHERE id = {r2}",
                  guc="OPERADOR")
        self._fails(self._line_sql(r2), guc="OPERADOR",
                    msg="em_calculo")     # invariante 5: linha só em execução em_calculo

    # ------------------------------------------------------------------
    # 7. Congelamento pós-'calculada' (RFC-006 regra 1)
    # ------------------------------------------------------------------
    def test_congelamento_pos_calculada(self):
        """Competência calculada: nada se escreve em runs/lines (nem UPDATE)."""
        self._open("2027-01", 2027, 1)
        pid = self._period_id("2027-01")
        run_id = self._new_run(pid)
        self._run(self._line_sql(run_id), guc="OPERADOR")

        self._run(f"UPDATE payroll_periods SET status = 'em_calculo' WHERE id = {pid}",
                  guc="OPERADOR")
        self._run(f"UPDATE payroll_periods SET status = 'calculada' WHERE id = {pid}",
                  guc="OPERADOR")

        self._fails(f"INSERT INTO payroll_runs (period_id) VALUES ({pid})",
                    guc="OPERADOR", msg="não aceita execução")
        self._fails(self._line_sql(run_id), guc="OPERADOR", msg="não aceita resultado")
        self._fails(f"UPDATE payroll_lines SET base_salary = 5000.00 "
                    f"WHERE run_id = {run_id}", guc="OPERADOR", msg="não aceita resultado")
        self._fails(f"UPDATE payroll_runs SET started_at = now() WHERE id = {run_id}",
                    guc="OPERADOR", msg="não aceita execução")

    # ------------------------------------------------------------------
    # 8. Sem exclusão física (rastreabilidade — padrão RFC-008 decisão 4)
    # ------------------------------------------------------------------
    def test_protecao_delete_truncate(self):
        """DELETE/TRUNCATE de runs/lines bloqueados (mesmo p/ ADMINISTRADOR)."""
        self._open("2027-02", 2027, 2)
        pid = self._period_id("2027-02")
        run_id = self._new_run(pid)
        self._run(self._line_sql(run_id), guc="OPERADOR")

        self._fails(f"DELETE FROM payroll_lines WHERE run_id = {run_id}",
                    guc="ADMINISTRADOR", msg="Exclusão física")
        self._fails(f"DELETE FROM payroll_runs WHERE id = {run_id}",
                    guc="ADMINISTRADOR", msg="Exclusão física")
        self._fails("TRUNCATE payroll_lines", msg="Exclusão física")


if __name__ == "__main__":
    unittest.main(verbosity=2)
