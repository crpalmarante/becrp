#!/usr/bin/env python3
"""Teste de integração — máquina de estados do RFC-006 (migration 010).

Valida a máquina de estados das competências (payroll_periods) de ponta a
ponta via psycopg2, num cluster PostgreSQL 16 TEMPORÁRIO e descartável
(infra compartilhada em tests/pg_bootstrap.py):

  * aplica as migrations NA ORDEM do projeto: 002 → 009 → 011 → 010;
  * valida o seed das transições (7) alinhado à matriz de permissões (011);
  * valida a AUTORIZAÇÃO POR PAPEL via f_has_permission_guc em cada
    transição — abrir=OPERADOR/ADMINISTRADOR (✅ duplo), calcular=OPERADOR,
    validar=CONFERENTE, fechar=APROVADOR, registrar_pagamento=TESOURARIA;
  * valida as regras do RFC-006: estados sequenciais (regra 4 — pulo de
    estado rejeitado e INSERT forçado a nascer 'aberta'), imutabilidade de
    fechada/paga (regra 1 — inclusive UPDATE de coluna não-status e a
    blindagem fechada→paga), marcos temporais, competência única (decisão 2)
    e transições regressivas † (RFC-015 §3.1).

Executar:
  python3 -m unittest tests.test_state_machine_integration -v
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
]

OPEN = ("INSERT INTO payroll_periods (reference, year, month, kind) "
        "VALUES ('{ref}', {year}, {month}, 'mensal')")
TO = ("UPDATE payroll_periods SET status = '{to_status}' "
      "WHERE reference = '{ref}'")


class TestStateMachineIntegration(unittest.TestCase):
    """Máquina de estados do RFC-006 (010) — transições e autorização por papel."""

    @classmethod
    def setUpClass(cls):
        if not HAS_PSYCOPG:
            raise unittest.SkipTest("psycopg2 não instalado")
        if not test_backend_available():
            raise unittest.SkipTest(
                "sem PostgreSQL: defina ERP_TEST_DATABASE_URL (CI) ou instale initdb/pg_ctl")
        cls.cluster = TempCluster(db_name="erp_sm_test", migrations=MIGRATIONS)
        # Limpeza garantida MESMO se o start() falhar daqui em diante:
        # addClassCleanup roda também quando o setUpClass levanta (stop() é
        # idempotente — seguro em cluster não iniciado).
        cls.addClassCleanup(cls.cluster.stop)
        cls.cluster.start()

    # ------------------------------------------------------------------
    # Helpers — cada chamada abre sessão própria (GUC sempre limpo)
    # ------------------------------------------------------------------
    def _run(self, sql, guc=None):
        """Executa esperando sucesso (GUC opcional na mesma sessão)."""
        conn = self.cluster.connect()
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

    def _scalar(self, sql):
        conn = self.cluster.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchone()[0]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # 1. Seed das transições alinhado à matriz de permissões (011)
    # ------------------------------------------------------------------
    def test_seed_transicoes_alinhado_a_matriz(self):
        """010 seeda 7 transições e toda required_action existe na matriz (011)."""
        n = self._scalar("SELECT count(*) FROM payroll_period_status_transitions")
        self.assertEqual(n, 7)
        ok = self._scalar(
            "SELECT bool_and(required_action IN (SELECT action FROM permissions)) "
            "FROM payroll_period_status_transitions")
        self.assertIs(ok, True)

    def test_transicao_acao_fora_da_matriz_rejeitada(self):
        """required_action fora das 8 ações da matriz viola o CHECK da 010."""
        self._fails(
            "INSERT INTO payroll_period_status_transitions "
            "(from_status, to_status, required_action, description) "
            "VALUES ('aberta', 'paga', 'apagar_tudo', 'x')",
            err=psycopg2.errors.CheckViolation)

    # ------------------------------------------------------------------
    # 2. Abrir competência — ação 'abrir_competencia' (OPERADOR/ADMINISTRADOR)
    # ------------------------------------------------------------------
    def test_abrir_competencia_permissao(self):
        """Abrir exige abrir_competencia: OPERADOR e ADMINISTRADOR ✅, outros ❌."""
        self._run(OPEN.format(ref="2026-08", year=2026, month=8), guc="OPERADOR")
        self._run(OPEN.format(ref="2026-07", year=2026, month=7), guc="ADMINISTRADOR")
        self._fails(OPEN.format(ref="2026-09", year=2026, month=9),
                    guc="CONFERENTE", msg="abrir_competencia")
        self._fails(OPEN.format(ref="2026-10", year=2026, month=10),
                    msg="abrir_competencia")

    def test_insert_forcado_a_aberta(self):
        """RFC-006 regra 4: estado não pode ser injetado no INSERT."""
        self._run(
            "INSERT INTO payroll_periods (reference, year, month, kind, status) "
            "VALUES ('2026-06', 2026, 6, 'mensal', 'fechada')", guc="OPERADOR")
        st = self._scalar("SELECT status FROM payroll_periods WHERE reference = '2026-06'")
        self.assertEqual(st, "aberta")

    # ------------------------------------------------------------------
    # 3. Sequência (regra 4) e fail-closed do GUC
    # ------------------------------------------------------------------
    def test_transicao_invalida_rejeitada(self):
        """Pulo de estado (aberta → calculada) não está na tabela de transições."""
        self._run(OPEN.format(ref="2027-01", year=2027, month=1), guc="OPERADOR")
        self._fails(TO.format(ref="2027-01", to_status="calculada"),
                    guc="OPERADOR", msg="Transição inválida")

    def test_transicao_sem_guc_fail_closed(self):
        """Transição válida SEM GUC → rejeitada (f_has_permission_guc fail-closed)."""
        self._run(OPEN.format(ref="2027-02", year=2027, month=2), guc="OPERADOR")
        self._fails(TO.format(ref="2027-02", to_status="em_calculo"),
                    msg="exige a ação")

    # ------------------------------------------------------------------
    # 4. Fluxo completo aberta → paga com marcos temporais
    # ------------------------------------------------------------------
    def test_fluxo_completo_com_marcos(self):
        """aberta→em_calculo→calculada→validada→fechada→paga com o papel certo."""
        ref = "2026-05"
        self._run(OPEN.format(ref=ref, year=2026, month=5), guc="OPERADOR")

        self._run(TO.format(ref=ref, to_status="em_calculo"), guc="OPERADOR")
        self._run(TO.format(ref=ref, to_status="calculada"), guc="OPERADOR")
        self.assertTrue(self._scalar(
            f"SELECT calculated_at IS NOT NULL FROM payroll_periods WHERE reference = '{ref}'"))

        self._run(TO.format(ref=ref, to_status="validada"), guc="CONFERENTE")
        self.assertTrue(self._scalar(
            f"SELECT validated_at IS NOT NULL FROM payroll_periods WHERE reference = '{ref}'"))

        self._run(TO.format(ref=ref, to_status="fechada"), guc="APROVADOR")
        self.assertTrue(self._scalar(
            f"SELECT closed_at IS NOT NULL FROM payroll_periods WHERE reference = '{ref}'"))

        self._run(TO.format(ref=ref, to_status="paga"), guc="TESOURARIA")
        self.assertTrue(self._scalar(
            f"SELECT paid_at IS NOT NULL FROM payroll_periods WHERE reference = '{ref}'"))
        self.assertEqual(self._scalar(
            f"SELECT status FROM payroll_periods WHERE reference = '{ref}'"), "paga")

    # ------------------------------------------------------------------
    # 5. Autorização por papel em CADA transição (via f_has_permission_guc)
    # ------------------------------------------------------------------
    def test_autorizacao_por_papel_em_cada_transicao(self):
        """Papel errado falha em cada passo; papel da matriz §3.1 passa."""
        ref = "2026-04"
        self._run(OPEN.format(ref=ref, year=2026, month=4), guc="OPERADOR")

        self._fails(TO.format(ref=ref, to_status="em_calculo"), guc="CONFERENTE", msg="exige a ação")
        self._run(TO.format(ref=ref, to_status="em_calculo"), guc="OPERADOR")

        self._fails(TO.format(ref=ref, to_status="calculada"), guc="TESOURARIA", msg="exige a ação")
        self._run(TO.format(ref=ref, to_status="calculada"), guc="OPERADOR")

        self._fails(TO.format(ref=ref, to_status="validada"), guc="OPERADOR", msg="exige a ação")
        self._run(TO.format(ref=ref, to_status="validada"), guc="CONFERENTE")

        self._fails(TO.format(ref=ref, to_status="fechada"), guc="CONFERENTE", msg="exige a ação")
        self._run(TO.format(ref=ref, to_status="fechada"), guc="APROVADOR")

        self._fails(TO.format(ref=ref, to_status="paga"), guc="APROVADOR", msg="exige a ação")
        self._run(TO.format(ref=ref, to_status="paga"), guc="TESOURARIA")

        self.assertEqual(self._scalar(
            f"SELECT status FROM payroll_periods WHERE reference = '{ref}'"), "paga")

    # ------------------------------------------------------------------
    # 6. Transições regressivas † (RFC-015 §3.1)
    # ------------------------------------------------------------------
    def test_transicoes_regressivas(self):
        """Recalcular (calculada→em_calculo) e devolver (validada→calculada)."""
        ref = "2026-03"
        self._run(OPEN.format(ref=ref, year=2026, month=3), guc="OPERADOR")
        self._run(TO.format(ref=ref, to_status="em_calculo"), guc="OPERADOR")
        self._run(TO.format(ref=ref, to_status="calculada"), guc="OPERADOR")
        self._run(TO.format(ref=ref, to_status="em_calculo"), guc="OPERADOR")   # recalcular †
        self._run(TO.format(ref=ref, to_status="calculada"), guc="OPERADOR")
        self._run(TO.format(ref=ref, to_status="validada"), guc="CONFERENTE")
        self._run(TO.format(ref=ref, to_status="calculada"), guc="CONFERENTE")  # devolver †
        self.assertEqual(self._scalar(
            f"SELECT status FROM payroll_periods WHERE reference = '{ref}'"), "calculada")

    # ------------------------------------------------------------------
    # 7. Cross-check da matriz: ADMINISTRADOR abre mas não fecha nem paga
    # ------------------------------------------------------------------
    def test_admin_abre_mas_nao_fecha_nem_paga(self):
        """abrir_competencia é ✅ duplo; fechar/registrar_pagamento não são do Admin."""
        ref = "2026-02"
        self._run(OPEN.format(ref=ref, year=2026, month=2), guc="ADMINISTRADOR")
        self._run(TO.format(ref=ref, to_status="em_calculo"), guc="OPERADOR")
        self._run(TO.format(ref=ref, to_status="calculada"), guc="OPERADOR")
        self._run(TO.format(ref=ref, to_status="validada"), guc="CONFERENTE")

        self._fails(TO.format(ref=ref, to_status="fechada"), guc="ADMINISTRADOR", msg="exige a ação")
        self._run(TO.format(ref=ref, to_status="fechada"), guc="APROVADOR")

        self._fails(TO.format(ref=ref, to_status="paga"), guc="ADMINISTRADOR", msg="exige a ação")
        self._run(TO.format(ref=ref, to_status="paga"), guc="TESOURARIA")

    # ------------------------------------------------------------------
    # 8. Imutabilidade de fechada/paga (regra 1) — inclusive coluna não-status
    # ------------------------------------------------------------------
    def test_imutabilidade_fechada_paga(self):
        """Fechada/paga imutáveis; única exceção fechada→paga (blindagem inclusa)."""
        ref = "2026-01"
        self._run(OPEN.format(ref=ref, year=2026, month=1), guc="OPERADOR")
        self._run(TO.format(ref=ref, to_status="em_calculo"), guc="OPERADOR")
        self._run(TO.format(ref=ref, to_status="calculada"), guc="OPERADOR")
        self._run(TO.format(ref=ref, to_status="validada"), guc="CONFERENTE")
        self._run(TO.format(ref=ref, to_status="fechada"), guc="APROVADOR")

        # UPDATE de coluna que NÃO é status: dispara o trigger de todas as colunas
        self._fails(f"UPDATE payroll_periods SET year = 2025 WHERE reference = '{ref}'",
                    guc="ADMINISTRADOR", msg="imutável")
        self._fails(f"UPDATE payroll_periods SET year = 2025 WHERE reference = '{ref}'",
                    msg="imutável")   # sem GUC também (imutabilidade não depende do GUC)

        # blindagem fechada → paga: colunas de negócio não mudam no mesmo UPDATE
        self._fails(f"UPDATE payroll_periods SET status = 'paga', year = 2025 WHERE reference = '{ref}'",
                    guc="TESOURARIA", msg="imutável")
        self._run(TO.format(ref=ref, to_status="paga"), guc="TESOURARIA")

        # paga: imutável e sem transição de volta
        self._fails(f"UPDATE payroll_periods SET year = 2025 WHERE reference = '{ref}'",
                    guc="ADMINISTRADOR", msg="imutável")
        self._fails(TO.format(ref=ref, to_status="fechada"), guc="TESOURARIA", msg="imutável")

    # ------------------------------------------------------------------
    # 9. Competência única (year, month, kind) — RFC-006 decisão 2
    # ------------------------------------------------------------------
    def test_competencia_unica_por_mes_tipo(self):
        """Duplicar (year, month, kind) viola a UNIQUE da 010."""
        self._run(OPEN.format(ref="2028-01", year=2028, month=1), guc="OPERADOR")
        self._fails(
            "INSERT INTO payroll_periods (reference, year, month, kind) "
            "VALUES ('2028-01-x', 2028, 1, 'mensal')",
            guc="OPERADOR", err=psycopg2.errors.UniqueViolation)


if __name__ == "__main__":
    unittest.main(verbosity=2)
