#!/usr/bin/env python3
"""Teste de integração — modelo de dados da contabilização da folha (RFC-Payroll).

Simula, em SQL puro no cluster PostgreSQL temporário, os modelos da plataforma
que o módulo de contabilização estende (RFC-Payroll/001 §4) — `hr.salary.rule`
(par de contas débito/crédito), `hr.payslip` (diário, contas padrão, vínculos
do lançamento) e `account.move`/`account.move.line` (lançamento tipo *entry*,
estorno) — e valida os ALGORITMOS do RFC-Payroll/002:

  * invariante de PAR da regra (§4.1): débito/crédito ambos ou nenhum;
  * FALLBACK (§4.2/§4.4): regra sem par usa o par padrão do contracheque;
    sem nenhum dos dois, a geração é BLOQUEADA (decisão 7);
  * GERAÇÃO (RFC-002 §3): movimento por regra por categoria — par de linhas
    débito/crédito por regra, agrupado por categoria, lançamento EQUILIBRADO
    (total débito = total crédito), postado e vinculado ao contracheque;
  * IDEMPOTÊNCIA (§4.4): um `move_id` por contracheque — nova geração falha;
  * ESTORNO (RFC-002 §4): rascunho é cancelado; postado gera estorno com
    sinais invertidos, `reversed_entry_id` → original e `move_reversal_id`
    vinculado ao contracheque; um estorno por contracheque (decisão 5).

A série RFC-Payroll NÃO define migration SQL própria (decisão 1 — os campos
estendem modelos da plataforma Odoo); por isso o schema simulado é criado pelo
próprio teste (MIGRATIONS = []), espelhando fielmente o RFC-001 §4.

Nota sobre isolamento: cada teste que gera/estorna usa um CONTROCHEQUE próprio
e dedicado (1–8) e resolve os ids dentro do próprio teste — nenhum teste depende
de estado deixado por outro (rodagens parciais com -k também funcionam).

Executar:
  python3 -m unittest tests.test_payroll_accounting_integration -v
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

# A contabilização NÃO adiciona migration ao db/ (RFC-Payroll/001 decisão 1):
# o schema simulado é criado pelo próprio teste (SCHEMA_SIMULADO abaixo).
MIGRATIONS = []

SCHEMA_SIMULADO = """
-- =====================================================================
-- Simulação dos modelos da plataforma estendidos (RFC-Payroll/001 §4)
-- (nomes com prefixo acct_ para não colidir com o núcleo do ERP)
-- =====================================================================

-- hr.salary.rule + campos novos (§4.1)
CREATE TABLE acct_hr_salary_rule (
    id               serial PRIMARY KEY,
    code             text NOT NULL,
    name             text NOT NULL,
    category         text NOT NULL,           -- Despesa / Encargos / Dedução
    debit_account_id bigint,                  -- Many2one account.account
    credit_account_id bigint,                 -- Many2one account.account
    CHECK ((debit_account_id IS NULL) = (credit_account_id IS NULL))  -- par (§4.4)
);

-- hr.payslip + campos novos (§4.2)
CREATE TABLE acct_hr_payslip (
    id                      serial PRIMARY KEY,
    employee_id             bigint NOT NULL,
    journal_id              bigint NOT NULL,  -- Many2one account.journal
    default_debit_account_id  bigint,         -- despesas com salários (fallback)
    default_credit_account_id bigint,         -- salários a pagar (fallback)
    move_id                 bigint,           -- lançamento efetuado (somente leitura)
    move_reversal_id        bigint            -- estorno vinculado (somente leitura)
);

-- linhas do contracheque (regra × valor) — origem do movimento
CREATE TABLE acct_hr_payslip_line (
    id         serial PRIMARY KEY,
    payslip_id bigint NOT NULL REFERENCES acct_hr_payslip(id),
    rule_id    bigint NOT NULL REFERENCES acct_hr_salary_rule(id),
    amount     numeric(14,2) NOT NULL CHECK (amount > 0)
);

-- account.move (tipo entry) + account.move.line (§4.3)
CREATE TABLE acct_account_move (
    id                serial PRIMARY KEY,
    move_type         text NOT NULL DEFAULT 'entry',
    state             text NOT NULL DEFAULT 'draft',   -- draft/posted/cancel
    journal_id        bigint NOT NULL,
    payslip_id        bigint NOT NULL REFERENCES acct_hr_payslip(id),
    reversed_entry_id bigint REFERENCES acct_account_move(id)  -- estorno → original
);

CREATE TABLE acct_account_move_line (
    id         serial PRIMARY KEY,
    move_id    bigint NOT NULL REFERENCES acct_account_move(id),
    rule_id    bigint NOT NULL REFERENCES acct_hr_salary_rule(id),
    category   text NOT NULL,
    account_id bigint NOT NULL,
    debit      numeric(14,2) NOT NULL DEFAULT 0,
    credit     numeric(14,2) NOT NULL DEFAULT 0,
    CHECK ((debit = 0) <> (credit = 0))       -- linha é débito OU crédito
);

-- =====================================================================
-- Resolução de contas (RFC-001 §4.4 e RFC-002 §3.2)
--   regra mapeada → par da regra; senão par padrão do contracheque;
--   senão BLOQUEIA (decisão 7).
-- =====================================================================
CREATE OR REPLACE FUNCTION acct_resolve_accounts(p_rule_id bigint, p_payslip_id bigint)
RETURNS TABLE(debit_account bigint, credit_account bigint) AS $$
DECLARE
    v_rule_debit  bigint;
    v_rule_credit bigint;
    v_slip_debit  bigint;
    v_slip_credit bigint;
BEGIN
    SELECT debit_account_id, credit_account_id INTO v_rule_debit, v_rule_credit
      FROM acct_hr_salary_rule WHERE id = p_rule_id;
    IF v_rule_debit IS NOT NULL THEN
        RETURN QUERY SELECT v_rule_debit, v_rule_credit;
        RETURN;
    END IF;
    SELECT default_debit_account_id, default_credit_account_id
      INTO v_slip_debit, v_slip_credit
      FROM acct_hr_payslip WHERE id = p_payslip_id;
    IF v_slip_debit IS NOT NULL THEN
        RETURN QUERY SELECT v_slip_debit, v_slip_credit;
        RETURN;
    END IF;
    RAISE EXCEPTION 'regra % sem contas e sem fallback no contracheque % (bloqueio)',
        p_rule_id, p_payslip_id;
END $$ LANGUAGE plpgsql;

-- =====================================================================
-- GERAÇÃO do lançamento (RFC-002 §3)
-- Movimento por regra por categoria: cada regra contribui com par
-- débito/crédito, agrupado por categoria, num account.move tipo 'entry'.
-- Valida equilíbrio (débito = crédito) e posta; grava move_id (idempotência).
-- =====================================================================
CREATE OR REPLACE FUNCTION acct_generate_move(p_payslip_id bigint)
RETURNS bigint AS $$
DECLARE
    v_move_id    bigint;
    v_existing   bigint;
    v_rule       record;
    v_acct       record;
BEGIN
    -- idempotência (RFC-001 §4.4.4 / decisão 5)
    SELECT move_id INTO v_existing FROM acct_hr_payslip WHERE id = p_payslip_id;
    IF v_existing IS NOT NULL THEN
        RAISE EXCEPTION 'contracheque % já lançado (move %)', p_payslip_id, v_existing;
    END IF;

    INSERT INTO acct_account_move (move_type, state, journal_id, payslip_id)
    SELECT 'entry', 'draft', journal_id, id FROM acct_hr_payslip WHERE id = p_payslip_id
    RETURNING id INTO v_move_id;

    FOR v_rule IN
        SELECT l.rule_id, r.category, l.amount
          FROM acct_hr_payslip_line l
          JOIN acct_hr_salary_rule r ON r.id = l.rule_id
         WHERE l.payslip_id = p_payslip_id
         ORDER BY r.category, l.rule_id
    LOOP
        SELECT * INTO v_acct FROM acct_resolve_accounts(v_rule.rule_id, p_payslip_id);
        INSERT INTO acct_account_move_line (move_id, rule_id, category, account_id, debit)
        VALUES (v_move_id, v_rule.rule_id, v_rule.category, v_acct.debit_account, v_rule.amount);
        INSERT INTO acct_account_move_line (move_id, rule_id, category, account_id, credit)
        VALUES (v_move_id, v_rule.rule_id, v_rule.category, v_acct.credit_account, v_rule.amount);
    END LOOP;

    -- equilíbrio (RFC-001 §4.4.3)
    IF (SELECT COALESCE(sum(debit), 0) FROM acct_account_move_line WHERE move_id = v_move_id) <>
       (SELECT COALESCE(sum(credit), 0) FROM acct_account_move_line WHERE move_id = v_move_id) THEN
        RAISE EXCEPTION 'lançamento % desequilibrado', v_move_id;
    END IF;

    UPDATE acct_account_move SET state = 'posted' WHERE id = v_move_id;
    UPDATE acct_hr_payslip SET move_id = v_move_id WHERE id = p_payslip_id;
    RETURN v_move_id;
END $$ LANGUAGE plpgsql;

-- =====================================================================
-- ESTORNO no cancelamento (RFC-002 §4)
--   rascunho → cancela o registro (nada no razão);
--   postado  → estorno com sinais invertidos, reversed_entry_id → original,
--              move_reversal_id no contracheque; move_id preservado
--              (rastreabilidade — decisão 6).
-- Um estorno por contracheque (decisão 5).
-- =====================================================================
CREATE OR REPLACE FUNCTION acct_reverse_move(p_payslip_id bigint)
RETURNS bigint AS $$
DECLARE
    v_move_id bigint;
    v_rev_id   bigint;
    v_line     record;
    v_rev_existing bigint;
BEGIN
    SELECT move_id INTO v_move_id FROM acct_hr_payslip WHERE id = p_payslip_id;
    IF v_move_id IS NULL THEN
        RETURN NULL;   -- nada a estornar
    END IF;

    -- caso A — lançamento em rascunho (RFC-002 §4.2)
    IF (SELECT state FROM acct_account_move WHERE id = v_move_id) = 'draft' THEN
        UPDATE acct_account_move SET state = 'cancel' WHERE id = v_move_id;
        RETURN NULL;
    END IF;

    -- um estorno por contracheque (RFC-002 decisão 5)
    SELECT move_reversal_id INTO v_rev_existing FROM acct_hr_payslip WHERE id = p_payslip_id;
    IF v_rev_existing IS NOT NULL THEN
        RAISE EXCEPTION 'contracheque % já estornado (estorno %)', p_payslip_id, v_rev_existing;
    END IF;

    -- caso B — estorno com sinais invertidos (RFC-002 §4.3)
    INSERT INTO acct_account_move (move_type, state, journal_id, payslip_id, reversed_entry_id)
    SELECT 'entry', 'draft', journal_id, id, v_move_id
      FROM acct_hr_payslip WHERE id = p_payslip_id
    RETURNING id INTO v_rev_id;

    FOR v_line IN
        SELECT rule_id, category, account_id, debit, credit
          FROM acct_account_move_line WHERE move_id = v_move_id
    LOOP
        INSERT INTO acct_account_move_line
            (move_id, rule_id, category, account_id, debit, credit)
        VALUES (v_rev_id, v_line.rule_id, v_line.category, v_line.account_id,
                v_line.credit, v_line.debit);          -- sinais invertidos
    END LOOP;

    UPDATE acct_account_move SET state = 'posted' WHERE id = v_rev_id;
    UPDATE acct_hr_payslip SET move_reversal_id = v_rev_id WHERE id = p_payslip_id;
    RETURN v_rev_id;
END $$ LANGUAGE plpgsql;
"""

# --------------------------------------------------------------------------
# Folha de referência — mesma do RFC-Payroll/002 §5.1 (exemplo numérico).
# Regras (código, categoria, conta débito, conta crédito):
#   1. Salário base     (Despesa, 3101, 2101) — 10.000,00
#   2. INSS empregador  (Encargos, 3102, 2102) — 2.000,00
#   3. INSS empregado   (Dedução, 2101, 2102) — 900,00
#   4. IRRF             (Dedução, 2101, 2103) — 1.100,00
# Total débito = Total crédito = 14.000,00
# --------------------------------------------------------------------------
TOTAL_EXEMPLO = Decimal("14000.00")


class TestPayrollAccountingIntegration(unittest.TestCase):
    """Contabilização da folha (RFC-Payroll/001 §4 + RFC-Payroll/002) — SQL puro."""

    @classmethod
    def setUpClass(cls):
        if not HAS_PSYCOPG:
            raise unittest.SkipTest("psycopg2 não instalado")
        if not test_backend_available():
            raise unittest.SkipTest(
                "sem PostgreSQL: defina ERP_TEST_DATABASE_URL (CI) ou instale initdb/pg_ctl")
        cls.cluster = TempCluster(db_name="erp_payroll_acct_test", migrations=MIGRATIONS)
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
    # Seed — folha do RFC-002 §5.1 + contracheques dedicados por cenário
    # ------------------------------------------------------------------
    @classmethod
    def _seed(cls):
        cls._run(
            "INSERT INTO acct_hr_salary_rule (id, code, name, category, debit_account_id, "
            "credit_account_id) VALUES "
            "(1, 'BASE',     'Salário base',    'Despesa',  3101, 2101),"
            "(2, 'INSS-EMP', 'INSS empregador', 'Encargos', 3102, 2102),"
            "(3, 'INSS-DEP', 'INSS empregado',  'Dedução',  2101, 2102),"
            "(4, 'IRRF',     'IRRF',            'Dedução',  2101, 2103),"
            "(5, 'ADIC',     'Adicional sem contas', 'Despesa', NULL, NULL)")
        # contracheques dedicados por cenário (isolamento entre testes):
        #   1 geracao · 2 fallback · 3 bloqueio · 4 estorno postado ·
        #   5 estorno rascunho · 6 linhas exemplo · 7 idempotência · 8 estorno único
        cls._run(
            "INSERT INTO acct_hr_payslip (id, employee_id, journal_id, "
            "default_debit_account_id, default_credit_account_id) VALUES "
            "(1, 100, 101, 3101, 2101),"
            "(2, 200, 101, 3101, 2101),"
            "(3, 300, 101, NULL, NULL),"
            "(4, 400, 101, 3101, 2101),"
            "(5, 500, 101, 3101, 2101),"
            "(6, 600, 101, 3101, 2101),"
            "(7, 700, 101, 3101, 2101),"
            "(8, 800, 101, 3101, 2101)")
        cls._run(
            "INSERT INTO acct_hr_payslip_line (payslip_id, rule_id, amount) VALUES "
            "(1, 1, 10000.00), (1, 2, 2000.00), (1, 3, 900.00), (1, 4, 1100.00),"
            "(2, 5, 500.00),"
            "(3, 5, 500.00),"
            "(4, 1, 10000.00), (4, 2, 2000.00), (4, 3, 900.00), (4, 4, 1100.00),"
            "(6, 1, 10000.00), (6, 2, 2000.00), (6, 3, 900.00), (6, 4, 1100.00),"
            "(7, 1, 10000.00),"
            "(8, 1, 10000.00), (8, 2, 2000.00), (8, 3, 900.00), (8, 4, 1100.00)")

    # ------------------------------------------------------------------
    # 1. Estrutura — campos do RFC-Payroll/001 §4
    # ------------------------------------------------------------------
    def test_campos_dos_modelos(self):
        """hr.salary.rule e hr.payslip simulados têm os campos do §4.1/§4.2."""
        for table, col in [
                ("acct_hr_salary_rule", "debit_account_id"),
                ("acct_hr_salary_rule", "credit_account_id"),
                ("acct_hr_payslip", "journal_id"),
                ("acct_hr_payslip", "default_debit_account_id"),
                ("acct_hr_payslip", "default_credit_account_id"),
                ("acct_hr_payslip", "move_id"),
                ("acct_hr_payslip", "move_reversal_id")]:
            self.assertEqual(self._scalar(
                "SELECT count(*) FROM information_schema.columns "
                f"WHERE table_name = '{table}' AND column_name = '{col}'"), 1)
        # account.move tipo entry + reversed_entry_id (§4.3)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = 'acct_account_move' AND column_name = 'reversed_entry_id'"), 1)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = 'acct_account_move' AND column_name = 'move_type'"), 1)

    # ------------------------------------------------------------------
    # 2. Invariante de PAR da regra (§4.1/§4.4)
    # ------------------------------------------------------------------
    def test_par_de_contas_da_regra(self):
        """Regra com apenas uma conta é REJEITADA (par: ambos ou nenhum)."""
        self._fails(
            "INSERT INTO acct_hr_salary_rule (id, code, name, category, "
            "debit_account_id, credit_account_id) "
            "VALUES (99, 'X', 'Só débito', 'Despesa', 3101, NULL)",
            err=psycopg2.errors.CheckViolation)
        self._fails(
            "INSERT INTO acct_hr_salary_rule (id, code, name, category, "
            "debit_account_id, credit_account_id) "
            "VALUES (98, 'X', 'Só crédito', 'Despesa', NULL, 2101)",
            err=psycopg2.errors.CheckViolation)
        # ambos → aceito
        self._run(
            "INSERT INTO acct_hr_salary_rule (id, code, name, category, "
            "debit_account_id, credit_account_id) "
            "VALUES (97, 'OK', 'Par completo', 'Despesa', 3101, 2101)")
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_hr_salary_rule WHERE id = 97"), 1)

    # ------------------------------------------------------------------
    # 3. Fallback (§4.2/§4.4) e bloqueio (decisão 7)
    # ------------------------------------------------------------------
    def test_fallback_par_padrao_do_contracheque(self):
        """Regra sem par usa o par padrão do contracheque na geração."""
        self.assertEqual(self._rows(
            "SELECT debit_account, credit_account FROM acct_resolve_accounts(5, 2)"),
            [(3101, 2101)])

    def test_bloqueio_sem_contas_nem_fallback(self):
        """Regra sem par + contracheque sem par padrão → geração BLOQUEADA."""
        self._fails(
            "SELECT acct_generate_move(3)",
            msg="sem contas e sem fallback")

    # ------------------------------------------------------------------
    # 4. GERAÇÃO — movimento por regra por categoria (RFC-002 §3)
    # ------------------------------------------------------------------
    def test_geracao_movimento_por_regra_por_categoria(self):
        """Folha do RFC-002 §5.1 → 8 linhas (par por regra), 3 categorias, 14.000."""
        move_id = self._scalar("SELECT acct_generate_move(1)")
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_account_move_line WHERE move_id = %s" % move_id), 8)
        # par débito/crédito por regra (2 linhas por regra)
        self.assertEqual(self._scalar(
            "SELECT count(DISTINCT rule_id) FROM acct_account_move_line WHERE move_id = %s"
            % move_id), 4)
        # categorias envolvidas (Despesa, Encargos, Dedução)
        self.assertEqual(self._scalar(
            "SELECT count(DISTINCT category) FROM acct_account_move_line WHERE move_id = %s"
            % move_id), 3)
        # equilíbrio (RFC-001 §4.4.3)
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

    def test_linhas_do_exemplo_rfc002(self):
        """As 4 linhas de débito espelham o exemplo do RFC-002 §5.1 (contracheque 6)."""
        move_id = self._scalar("SELECT acct_generate_move(6)")
        self.assertEqual(self._rows(
            "SELECT l.rule_id, l.category, l.account_id, l.debit "
            "FROM acct_account_move_line l WHERE l.move_id = %s AND l.debit > 0 "
            "ORDER BY l.rule_id" % move_id),
            [(1, "Despesa", 3101, Decimal("10000.00")),
             (2, "Encargos", 3102, Decimal("2000.00")),
             (3, "Dedução", 2101, Decimal("900.00")),
             (4, "Dedução", 2101, Decimal("1100.00"))])

    def test_fallback_na_geracao(self):
        """Contracheque com regra sem par + fallback gera lançamento equilibrado."""
        move_id = self._scalar("SELECT acct_generate_move(2)")
        self.assertEqual(self._scalar(
            "SELECT sum(debit) FROM acct_account_move_line WHERE move_id = %s" % move_id),
            Decimal("500.00"))
        self.assertEqual(self._scalar(
            "SELECT sum(credit) FROM acct_account_move_line WHERE move_id = %s" % move_id),
            Decimal("500.00"))
        # usou o par padrão do contracheque (3101/2101)
        self.assertEqual(self._rows(
            "SELECT account_id, debit, credit FROM acct_account_move_line "
            "WHERE move_id = %s ORDER BY id" % move_id),
            [(3101, Decimal("500.00"), Decimal("0.00")),
             (2101, Decimal("0.00"), Decimal("500.00"))])

    # ------------------------------------------------------------------
    # 5. IDEMPOTÊNCIA (§4.4 / decisão 5)
    # ------------------------------------------------------------------
    def test_idempotencia_um_move_por_contracheque(self):
        """Segunda geração para o mesmo contracheque é BLOQUEADA (contracheque 7)."""
        self._scalar("SELECT acct_generate_move(7)")
        self._fails(
            "SELECT acct_generate_move(7)",
            msg="já lançado")

    # ------------------------------------------------------------------
    # 6. ESTORNO — caso postado (RFC-002 §4.3) — contracheque 4 dedicado
    # ------------------------------------------------------------------
    def test_estorno_caso_postado(self):
        """Estorno com sinais invertidos, associado ao original, vincula o contracheque."""
        move_id = self._scalar("SELECT acct_generate_move(4)")
        rev_id = self._scalar("SELECT acct_reverse_move(4)")
        # estorno postado, com reversed_entry_id → original
        self.assertEqual(self._scalar(
            "SELECT state FROM acct_account_move WHERE id = %s" % rev_id), "posted")
        self.assertEqual(self._scalar(
            "SELECT reversed_entry_id FROM acct_account_move WHERE id = %s" % rev_id),
            move_id)
        # vinculado ao contracheque (move_reversal_id) e move_id preservado
        self.assertEqual(self._scalar(
            "SELECT move_reversal_id FROM acct_hr_payslip WHERE id = 4"), rev_id)
        self.assertEqual(self._scalar(
            "SELECT move_id FROM acct_hr_payslip WHERE id = 4"), move_id)
        # sinais invertidos — estorno equilibrado (14.000 = 14.000)
        self.assertEqual(self._scalar(
            "SELECT sum(debit) FROM acct_account_move_line WHERE move_id = %s" % rev_id),
            TOTAL_EXEMPLO)
        self.assertEqual(self._scalar(
            "SELECT sum(credit) FROM acct_account_move_line WHERE move_id = %s" % rev_id),
            TOTAL_EXEMPLO)
        # espelho: débito do estorno = crédito do original (por regra)
        self.assertEqual(self._rows(
            "SELECT l.rule_id, l.account_id, l.debit "
            "FROM acct_account_move_line l "
            "JOIN acct_account_move m ON m.id = l.move_id "
            "WHERE m.id = %s AND l.debit > 0 ORDER BY l.rule_id" % rev_id),
            [(1, 2101, Decimal("10000.00")),
             (2, 2102, Decimal("2000.00")),
             (3, 2102, Decimal("900.00")),
             (4, 2103, Decimal("1100.00"))])

    def test_estorno_unico_por_contracheque(self):
        """Segundo estorno do mesmo contracheque é BLOQUEADO (decisão 5)."""
        self._scalar("SELECT acct_generate_move(8)")
        self._scalar("SELECT acct_reverse_move(8)")
        self._fails(
            "SELECT acct_reverse_move(8)",
            msg="já estornado")

    # ------------------------------------------------------------------
    # 7. ESTORNO — caso rascunho (RFC-002 §4.2) — contracheque 5 dedicado
    # ------------------------------------------------------------------
    def test_estorno_caso_rascunho(self):
        """Lançamento em rascunho é CANCELADO (nada no razão, sem estorno)."""
        # move 'entry' em rascunho (transitório durante a geração)
        self._run(
            "INSERT INTO acct_account_move (move_type, state, journal_id, payslip_id) "
            "VALUES ('entry', 'draft', 101, 5)")
        draft_id = self._scalar(
            "SELECT max(id) FROM acct_account_move WHERE payslip_id = 5 AND state = 'draft'")
        self._run(
            "UPDATE acct_hr_payslip SET move_id = %s WHERE id = 5" % draft_id)
        # estorno do rascunho → cancela o registro, sem criar estorno
        self.assertEqual(self._scalar("SELECT acct_reverse_move(5)"), None)
        self.assertEqual(self._scalar(
            "SELECT state FROM acct_account_move WHERE id = %s" % draft_id), "cancel")
        self.assertEqual(self._scalar(
            "SELECT move_reversal_id FROM acct_hr_payslip WHERE id = 5"), None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
