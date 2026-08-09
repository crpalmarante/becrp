#!/usr/bin/env python3
"""Teste de integração — contabilização automática da comissão (RFC-Payroll/003).

Valida, em SQL puro no cluster PostgreSQL temporário, a **regra do evento 7
mapeada com par de contas** no lançamento contábil — a especificação do
RFC-Payroll/003 (✅ Aprovado):

  * REGRA MAPEADA (§4) — a regra de comissão do **evento 7** carrega
    `debit_account_id` (ex.: 3.1.03 — despesas com comissões) e
    `credit_account_id` (ex.: 2.1.04 — comissões a pagar), **sem campos
    novos** (reusa o RFC-Payroll/001 §4.1) e respeitando o invariante de PAR
    (§4.4: ambos ou nenhum);
  * EXEMPLO §6 — folha com salário base + comissão (evento 7) + encargos →
    lançamento EQUILIBRADO (16.400 = 16.400), com a comissão contribuindo com
    seu **par próprio** (débito 3.1.03 / crédito 2.1.04 — 2.000), agrupado por
    categoria (Despesa);
  * CONSOLIDAÇÃO POR REGRA (§8 decisão 5) — o lançamento é consolidado por
    regra: a comissão contribui com **um par de linhas** (sem detalhamento por
    venda de origem, que permanece analítico no RFC-COMISSION/005 §7);
  * FALLBACK E BLOQUEIO (§8 decisão 3) — regra de comissão **sem par** usa o
    par padrão do contracheque (RFC-Payroll/001 §4.2); sem nenhum dos dois, a
    geração é BLOQUEADA (invariante §4.4);
  * IDEMPOTÊNCIA E ESTORNO (mecânica herdada do RFC-Payroll/002 §3/§4) — um
    `move_id` por contracheque; o cancelamento estorna **também o par da
    comissão** (sinais invertidos + `reversed_entry_id` + `move_reversal_id`,
    com `move_id` preservado).

Decisão 4 (§8) fora do escopo SQL: o **tratamento de comissão negativa**
(abater no mês seguinte — política RFC-COMISSION/001) acontece ANTES do
lançamento — o valor que entra no evento 7 já é o líquido apurado conforme a
política — e o schema simulado exige `amount > 0`; os testes validam o
lançamento do valor do contracheque, não a apuração do PDV (RFC-COMISSION/005).

A série RFC-Payroll NÃO define migration SQL própria (decisão 1 do RFC-001); o
schema simulado (`acct_*` — mesmos modelos da plataforma simulados para o
RFC-001/002) é REUTILIZADO de tests/test_payroll_accounting_integration.py
(SCHEMA_SIMULADO), e este arquivo adiciona apenas a regra de comissão do evento
7 e os cenários do RFC-003.

Nota sobre isolamento: cada teste que gera/estorna usa um CONTROCHEQUE próprio
e dedicado (1–7) — nenhum teste depende de estado deixado por outro (rodagens
parciais com -k também funcionam).

Executar:
  python3 -m unittest tests.test_commission_accounting_integration -v
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

# A contabilização da comissão reutiliza a MESMA mecânica do RFC-001/002
# (RFC-003 §4/§5 — "sem código novo de contabilização"): o schema simulado da
# série é compartilhado com o teste irmão (import direto, sem duplicação).
try:
    from tests.test_payroll_accounting_integration import SCHEMA_SIMULADO
except ImportError:
    from test_payroll_accounting_integration import SCHEMA_SIMULADO

HAS_PSYCOPG = HAS_PSYCOPG and _HAS_PG

MIGRATIONS = []   # a série não adiciona migration ao db/ (RFC-Payroll/001 decisão 1)

# --------------------------------------------------------------------------
# Folha do RFC-Payroll/003 §6 (exemplo numérico) — com a comissão (evento 7).
# Regras (código, categoria, conta débito, conta crédito):
#   1. Salário base         (Despesa, 3101, 2101) — 10.000,00
#   2. INSS empregador      (Encargos, 3102, 2102) — 2.400,00
#   3. INSS empregado       (Dedução, 2101, 2102) — 900,00
#   4. IRRF                 (Dedução, 2101, 2103) — 1.100,00
#   6. Comissão (evento 7)  (Despesa, 3103, 2104) — 2.000,00   ← par 3.1.03/2.1.04
#   7. Comissão (evento 7)  sem par (NULL/NULL) — p/ fallback e bloqueio
# Total débito = Total crédito = 16.400,00
# --------------------------------------------------------------------------
TOTAL_EXEMPLO = Decimal("16400.00")
COMISSAO_VALOR = Decimal("2000.00")
PAR_COMISSAO = (3103, 2104)      # despesas com comissões / comissões a pagar


class TestCommissionAccountingIntegration(unittest.TestCase):
    """Contabilização da comissão como regra do evento 7 mapeada (RFC-Payroll/003)."""

    @classmethod
    def setUpClass(cls):
        if not HAS_PSYCOPG:
            raise unittest.SkipTest("psycopg2 não instalado")
        if not test_backend_available():
            raise unittest.SkipTest(
                "sem PostgreSQL: defina ERP_TEST_DATABASE_URL (CI) ou instale initdb/pg_ctl")
        cls.cluster = TempCluster(db_name="erp_commission_acct_test", migrations=MIGRATIONS)
        cls.addClassCleanup(cls.cluster.stop)
        cls.cluster.start()
        # O schema simulado (RFC-Payroll/001 §4) é criado pelo próprio teste —
        # a série NÃO define migration SQL (decisão 1).
        cls._run(SCHEMA_SIMULADO)
        cls._seed()

    # ------------------------------------------------------------------
    # Helpers — cada chamada abre sessão própria
    # ------------------------------------------------------------------
    @classmethod
    def _run(cls, sql):
        conn = cls.cluster.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
        finally:
            conn.close()

    def _fails(self, sql, err=psycopg2.errors.RaiseException, msg=None):
        """Executa esperando erro; valida a classe e (opcional) fragmento."""
        conn = self.cluster.connect()
        try:
            with conn.cursor() as cur:
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

    def _rows(self, sql):
        conn = self.cluster.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Seed — folha do RFC-Payroll/003 §6 + contracheques dedicados por cenário
    # ------------------------------------------------------------------
    @classmethod
    def _seed(cls):
        # regras: folha base + comissão do evento 7 (mapeada e sem par)
        cls._run(
            "INSERT INTO acct_hr_salary_rule (id, code, name, category, debit_account_id, "
            "credit_account_id) VALUES "
            "(1, 'BASE',    'Salário base',       'Despesa',  3101, 2101),"
            "(2, 'INSS-EMP','INSS empregador',    'Encargos', 3102, 2102),"
            "(3, 'INSS-DEP','INSS empregado',     'Dedução',  2101, 2102),"
            "(4, 'IRRF',    'IRRF',               'Dedução',  2101, 2103),"
            "(6, 'COMM7',   'Comissão (evento 7)','Despesa',  3103, 2104),"
            "(7, 'COMM7-NA','Comissão sem contas','Despesa',  NULL, NULL)")
        # contracheques dedicados por cenário (isolamento entre testes):
        #   1 exemplo completo · 2 fallback da comissão · 3 bloqueio ·
        #   4 estorno postado · 5 idempotência · 6 consolidação (só comissão) ·
        #   7 exemplo completo (par da comissão no lançamento)
        cls._run(
            "INSERT INTO acct_hr_payslip (id, employee_id, journal_id, "
            "default_debit_account_id, default_credit_account_id) VALUES "
            "(1, 100, 101, 3101, 2101),"
            "(2, 200, 101, 3101, 2101),"
            "(3, 300, 101, NULL, NULL),"
            "(4, 400, 101, 3101, 2101),"
            "(5, 500, 101, 3101, 2101),"
            "(6, 600, 101, 3101, 2101),"
            "(7, 700, 101, 3101, 2101)")
        cls._run(
            "INSERT INTO acct_hr_payslip_line (payslip_id, rule_id, amount) VALUES "
            # 1 — exemplo completo (RFC-003 §6): 10.000 + 2.000 + 2.400 + 900 + 1.100
            "(1, 1, 10000.00), (1, 2, 2400.00), (1, 3, 900.00), (1, 4, 1100.00), (1, 6, 2000.00),"
            # 2 — só comissão SEM par, contracheque com par padrão (fallback — 500)
            "(2, 7, 500.00),"
            # 3 — só comissão SEM par e SEM fallback (bloqueio)
            "(3, 7, 500.00),"
            # 4 — exemplo completo (estorno postado)
            "(4, 1, 10000.00), (4, 2, 2400.00), (4, 3, 900.00), (4, 4, 1100.00), (4, 6, 2000.00),"
            # 5 — exemplo completo (idempotência)
            "(5, 1, 10000.00), (5, 2, 2400.00), (5, 3, 900.00), (5, 4, 1100.00), (5, 6, 2000.00),"
            # 6 — SÓ comissão mapeada (consolidação por regra)
            "(6, 6, 2000.00),"
            # 7 — exemplo completo (par da comissão no lançamento)
            "(7, 1, 10000.00), (7, 2, 2400.00), (7, 3, 900.00), (7, 4, 1100.00), (7, 6, 2000.00)")

    # ------------------------------------------------------------------
    # 1. Regra do evento 7 mapeada (§4)
    # ------------------------------------------------------------------
    def test_regra_evento7_mapeada_com_par(self):
        """A regra de comissão do evento 7 tem o par 3.1.03/2.1.04 e categoria Despesa."""
        self.assertEqual(self._rows(
            "SELECT code, category, debit_account_id, credit_account_id "
            "FROM acct_hr_salary_rule WHERE id = 6"),
            [("COMM7", "Despesa", PAR_COMISSAO[0], PAR_COMISSAO[1])])
        # invariante de PAR (RFC-001 §4.4): comissão com só uma conta é REJEITADA
        self._fails(
            "INSERT INTO acct_hr_salary_rule (id, code, name, category, "
            "debit_account_id, credit_account_id) "
            "VALUES (99, 'C7-D', 'Comissão só débito', 'Despesa', 3103, NULL)",
            err=psycopg2.errors.CheckViolation)
        self._fails(
            "INSERT INTO acct_hr_salary_rule (id, code, name, category, "
            "debit_account_id, credit_account_id) "
            "VALUES (98, 'C7-C', 'Comissão só crédito', 'Despesa', NULL, 2104)",
            err=psycopg2.errors.CheckViolation)

    # ------------------------------------------------------------------
    # 2. GERAÇÃO — exemplo do RFC-Payroll/003 §6 (contracheque 1 dedicado)
    # ------------------------------------------------------------------
    def test_geracao_exemplo_rfc003_equilibrado(self):
        """Folha com comissão (evento 7) → 10 linhas (par por regra), 16.400 = 16.400."""
        move_id = self._scalar("SELECT acct_generate_move(1)")
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_account_move_line WHERE move_id = %s" % move_id), 10)
        self.assertEqual(self._scalar(
            "SELECT count(DISTINCT rule_id) FROM acct_account_move_line WHERE move_id = %s"
            % move_id), 5)
        # categorias envolvidas (Despesa — inclui a comissão, Encargos, Dedução)
        self.assertEqual(self._scalar(
            "SELECT count(DISTINCT category) FROM acct_account_move_line WHERE move_id = %s"
            % move_id), 3)
        # equilíbrio (RFC-001 §4.4.3) — 16.400 = 16.400
        self.assertEqual(self._scalar(
            "SELECT sum(debit) FROM acct_account_move_line WHERE move_id = %s" % move_id),
            TOTAL_EXEMPLO)
        self.assertEqual(self._scalar(
            "SELECT sum(credit) FROM acct_account_move_line WHERE move_id = %s" % move_id),
            TOTAL_EXEMPLO)
        # postado e vinculado ao contracheque (§4.2)
        self.assertEqual(self._scalar(
            "SELECT state FROM acct_account_move WHERE id = %s" % move_id), "posted")
        self.assertEqual(self._scalar(
            "SELECT move_id FROM acct_hr_payslip WHERE id = 1"), move_id)

    # ------------------------------------------------------------------
    # 3. Par da comissão no lançamento (contracheque 7 dedicado)
    # ------------------------------------------------------------------
    def test_par_da_comissao_no_lancamento(self):
        """A comissão contribui com o par 3.1.03/2.1.04 (2.000) no lançamento."""
        move_id = self._scalar("SELECT acct_generate_move(7)")
        self.assertEqual(self._rows(
            "SELECT l.category, l.account_id, l.debit, l.credit "
            "FROM acct_account_move_line l "
            "WHERE l.move_id = %s AND l.rule_id = 6 ORDER BY l.id" % move_id),
            [("Despesa", PAR_COMISSAO[0], COMISSAO_VALOR, Decimal("0.00")),
             ("Despesa", PAR_COMISSAO[1], Decimal("0.00"), COMISSAO_VALOR)])

    # ------------------------------------------------------------------
    # 4. CONSOLIDAÇÃO POR REGRA (§8 decisão 5) — contracheque 6 dedicado
    # ------------------------------------------------------------------
    def test_consolidacao_por_regra(self):
        """Comissão entra consolidada (um par de linhas), sem detalhe por venda."""
        move_id = self._scalar("SELECT acct_generate_move(6)")
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_account_move_line WHERE move_id = %s" % move_id), 2)
        self.assertEqual(self._scalar(
            "SELECT count(DISTINCT rule_id) FROM acct_account_move_line WHERE move_id = %s"
            % move_id), 1)

    # ------------------------------------------------------------------
    # 5. FALLBACK da comissão (§8 decisão 3) — contracheque 2 dedicado
    # ------------------------------------------------------------------
    def test_fallback_da_comissao(self):
        """Comissão sem par usa o par padrão do contracheque na geração."""
        move_id = self._scalar("SELECT acct_generate_move(2)")
        self.assertEqual(self._rows(
            "SELECT l.account_id, l.debit, l.credit FROM acct_account_move_line l "
            "WHERE l.move_id = %s ORDER BY l.id" % move_id),
            [(3101, Decimal("500.00"), Decimal("0.00")),
             (2101, Decimal("0.00"), Decimal("500.00"))])
        self.assertEqual(self._scalar(
            "SELECT sum(debit) FROM acct_account_move_line WHERE move_id = %s" % move_id),
            Decimal("500.00"))
        self.assertEqual(self._scalar(
            "SELECT sum(credit) FROM acct_account_move_line WHERE move_id = %s" % move_id),
            Decimal("500.00"))

    # ------------------------------------------------------------------
    # 6. BLOQUEIO (§8 decisão 3) — contracheque 3 dedicado
    # ------------------------------------------------------------------
    def test_bloqueio_comissao_sem_contas(self):
        """Comissão sem par + contracheque sem par padrão → geração BLOQUEADA."""
        self._fails(
            "SELECT acct_generate_move(3)",
            msg="sem contas e sem fallback")

    # ------------------------------------------------------------------
    # 7. IDEMPOTÊNCIA — contracheque 5 dedicado
    # ------------------------------------------------------------------
    def test_idempotencia_um_move_por_contracheque(self):
        """Segunda geração do mesmo contracheque (com comissão) é BLOQUEADA."""
        self._scalar("SELECT acct_generate_move(5)")
        self._fails(
            "SELECT acct_generate_move(5)",
            msg="já lançado")

    # ------------------------------------------------------------------
    # 8. ESTORNO do par da comissão (RFC-002 §4) — contracheque 4 dedicado
    # ------------------------------------------------------------------
    def test_estorno_estorna_o_par_da_comissao(self):
        """Cancelamento estorna também o par da comissão (sinais invertidos)."""
        move_id = self._scalar("SELECT acct_generate_move(4)")
        rev_id = self._scalar("SELECT acct_reverse_move(4)")
        # estorno postado, associado ao original, vinculado ao contracheque;
        # move_id preservado (rastreabilidade — RFC-002 §8 decisão 6)
        self.assertEqual(self._scalar(
            "SELECT state FROM acct_account_move WHERE id = %s" % rev_id), "posted")
        self.assertEqual(self._scalar(
            "SELECT reversed_entry_id FROM acct_account_move WHERE id = %s" % rev_id),
            move_id)
        self.assertEqual(self._scalar(
            "SELECT move_reversal_id FROM acct_hr_payslip WHERE id = 4"), rev_id)
        self.assertEqual(self._scalar(
            "SELECT move_id FROM acct_hr_payslip WHERE id = 4"), move_id)
        # estorno equilibrado (16.400 = 16.400) e com o mesmo nº de linhas do
        # original (10 = 5 regras × par)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_account_move_line WHERE move_id = %s" % rev_id), 10)
        self.assertEqual(self._scalar(
            "SELECT sum(debit) FROM acct_account_move_line WHERE move_id = %s" % rev_id),
            TOTAL_EXEMPLO)
        self.assertEqual(self._scalar(
            "SELECT sum(credit) FROM acct_account_move_line WHERE move_id = %s" % rev_id),
            TOTAL_EXEMPLO)
        # par da comissão INVERTIDO no estorno: débito em 2.1.04 (comissões a
        # pagar), crédito em 3.1.03 (despesa com comissões)
        self.assertEqual(self._rows(
            "SELECT l.category, l.account_id, l.debit, l.credit "
            "FROM acct_account_move_line l "
            "WHERE l.move_id = %s AND l.rule_id = 6 ORDER BY l.account_id" % rev_id),
            [("Despesa", PAR_COMISSAO[1], COMISSAO_VALOR, Decimal("0.00")),
             ("Despesa", PAR_COMISSAO[0], Decimal("0.00"), COMISSAO_VALOR)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
