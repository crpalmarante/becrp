#!/usr/bin/env python3
"""Teste de integração — camada analítica de ligação por venda de origem (RFC-Payroll/004).

Valida, em SQL puro no cluster PostgreSQL temporário, a **camada analítica de
ligação** `commission_move_line_detail` do RFC-Payroll/004 (✅ decisões da §8
aprovadas) — o **detalhamento contábil por venda de origem** no lançamento da
comissão (evento 7):

  * RAZÃO CONSOLIDADO PRESERVADO (decisão 1) — as linhas do lançamento não
    mudam: o exemplo do RFC-003 §6 continua com **10 linhas e 16.400 = 16.400**;
    a ligação é uma camada analítica, não linha adicional do razão;
  * TABELA DE LIGAÇÃO (decisão 2/§4) — `commission_move_line_detail`
    (move_line_id → linha da regra 7; `commission_detail_id` UNIQUE → item
    apurado; `sale_id` denormalizado; `amount > 0`) — única exceção a "sem
    models próprios" da série;
  * GERAÇÃO IDEMPOTENTE E VALIDADA (decisão 3/§5) — uma ligação por
    `commission_detail_id` (UNIQUE); invariante: soma das ligações = valor da
    linha = apurado congelado; divergência **BLOQUEIA** a geração;
  * ESTORNO HERDADO (decisão 4/§5) — o estorno **não cria ligações novas**: a
    rastreabilidade segue `reversed_entry_id` → original → ligações; rascunho
    cancelado **descarta** as ligações (CASCADE);
  * ESCOPO RESTRITO À COMISSÃO (decisão 5) — só a linha da regra do evento 7
    recebe ligações; as demais regras permanecem sem detalhe de origem;
  * RELATÓRIO INTEGRADO (decisão 6/§5) — da venda de origem → o lançamento
    (`move_id`), vínculo reverso do RFC-015 §2.1;
  * INVARIANTE 5 (§4) — consistência da denormalização: `sale_id` da ligação =
    `commission_details.sale_id` (trigger).

A série RFC-Payroll NÃO define migration SQL própria (a tabela é criada pelo
model ORM do módulo — RFC-004 §4); o schema simulado (`acct_*`) é REUTILIZADO
de tests/test_payroll_accounting_integration.py (SCHEMA_SIMULADO — mecânica
001/002) e complementado aqui com a simulação da camada analítica
(LINKAGE_SCHEMA — `commission_details`, tabela de ligação, trigger e função de
geração do RFC-004).

Nota sobre isolamento: cada teste que gera/estorna usa um CONTROCHEQUE próprio
e dedicado (1–9) — nenhum teste depende de estado deixado por outro (rodagens
parciais com -k também funcionam).

Executar:
  python3 -m unittest tests.test_commission_detail_accounting_integration -v
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

# A camada analítica (RFC-004 §4) estende a MESMA mecânica da série (001/002/003):
# o schema simulado de base é compartilhado com o teste irmão (import direto).
try:
    from tests.test_payroll_accounting_integration import SCHEMA_SIMULADO
except ImportError:
    from test_payroll_accounting_integration import SCHEMA_SIMULADO

HAS_PSYCOPG = HAS_PSYCOPG and _HAS_PG

MIGRATIONS = []   # a série não adiciona migration ao db/ (RFC-Payroll/001 decisão 1)

# --------------------------------------------------------------------------
# Extensão da simulação — camada analítica do RFC-Payroll/004 (§4/§5)
# --------------------------------------------------------------------------
LINKAGE_SCHEMA = """
-- =====================================================================
-- commission_details (db/017) — colunas relevantes para a ligação
-- (detalhe da comissão POR ITEM APURADO: venda de origem + valor)
-- =====================================================================
CREATE TABLE acct_commission_details (
    id               bigserial PRIMARY KEY,
    sale_id          bigint NOT NULL,
    employee_id      bigint NOT NULL,
    commission_value numeric(14,2) NOT NULL CHECK (commission_value > 0)
);

-- =====================================================================
-- commission_move_line_detail (RFC-004 §4) — único model próprio da série
-- liga a LINHA da regra 7 no lançamento ao ITEM APURADO de origem.
-- =====================================================================
CREATE TABLE acct_commission_move_line_detail (
    id                   bigserial PRIMARY KEY,
    move_line_id         bigint NOT NULL REFERENCES acct_account_move_line(id) ON DELETE CASCADE,
    commission_detail_id bigint NOT NULL REFERENCES acct_commission_details(id) ON DELETE RESTRICT,
    sale_id              bigint NOT NULL,                       -- denormalizado (§4)
    amount               numeric(14,2) NOT NULL CHECK (amount > 0),
    CONSTRAINT uq_acct_commission_move_line_detail UNIQUE (commission_detail_id)  -- decisão 3
);

-- Invariante 5 (§4): sale_id da ligação = commission_details.sale_id
CREATE OR REPLACE FUNCTION acct_check_linkage_sale_consistency()
RETURNS trigger AS $$
DECLARE
    v_sale bigint;
BEGIN
    SELECT sale_id INTO v_sale
      FROM acct_commission_details
     WHERE id = NEW.commission_detail_id;
    IF v_sale IS DISTINCT FROM NEW.sale_id THEN
        RAISE EXCEPTION 'sale_id da ligação diverge do commission_details (invariante 5)';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_acct_linkage_sale_consistency
    BEFORE INSERT OR UPDATE ON acct_commission_move_line_detail
    FOR EACH ROW EXECUTE FUNCTION acct_check_linkage_sale_consistency();

-- =====================================================================
-- GERAÇÃO da ligação (RFC-004 §5) — dentro da geração do lançamento (002 §3)
-- Escopo restrito à comissão (decisão 5): só a linha da regra do evento 7.
-- Uma ligação por commission_detail_id (decisão 3 — UNIQUE).
-- Invariante 1 (decisão 3): soma das ligações = valor da linha (senão, BLOQUEIA).
-- =====================================================================
CREATE OR REPLACE FUNCTION acct_generate_linkages(p_payslip_id bigint, p_move_id bigint)
RETURNS void AS $$
DECLARE
    v_employee bigint;
    v_line     record;
    v_detail   record;
    v_soma     numeric(14,2);
BEGIN
    SELECT employee_id INTO v_employee FROM acct_hr_payslip WHERE id = p_payslip_id;

    -- linha da regra do evento 7 (comissão) no lançamento — débito
    SELECT l.id, l.debit INTO v_line
      FROM acct_account_move_line l
      JOIN acct_hr_salary_rule r ON r.id = l.rule_id
     WHERE l.move_id = p_move_id
       AND r.code LIKE 'COMM%'
       AND l.debit > 0
     LIMIT 1;

    -- escopo restrito à comissão (decisão 5): sem linha do evento 7, nada a ligar
    IF v_line IS NULL THEN
        RETURN;
    END IF;

    -- uma ligação por item apurado da competência (RFC-004 §3/§4)
    FOR v_detail IN
        SELECT id, sale_id, commission_value
          FROM acct_commission_details
         WHERE employee_id = v_employee
         ORDER BY id
    LOOP
        INSERT INTO acct_commission_move_line_detail
            (move_line_id, commission_detail_id, sale_id, amount)
        VALUES (v_line.id, v_detail.id, v_detail.sale_id, v_detail.commission_value);
    END LOOP;

    -- invariante 1 (decisão 3): soma das ligações = valor da linha da regra 7
    SELECT COALESCE(sum(amount), 0) INTO v_soma
      FROM acct_commission_move_line_detail
     WHERE move_line_id = v_line.id;
    IF v_soma <> v_line.debit THEN
        RAISE EXCEPTION 'soma das ligações (%) diverge do valor da linha (%) — geração bloqueada',
            v_soma, v_line.debit;
    END IF;
END $$ LANGUAGE plpgsql;
"""

# --------------------------------------------------------------------------
# Folha do RFC-Payroll/003 §6 (exemplo numérico) — com a comissão (evento 7).
# Regras (código, categoria, conta débito, conta crédito):
#   1. Salário base         (Despesa, 3101, 2101) — 10.000,00
#   2. INSS empregador      (Encargos, 3102, 2102) — 2.400,00
#   3. INSS empregado       (Dedução, 2101, 2102) — 900,00
#   4. IRRF                 (Dedução, 2101, 2103) — 1.100,00
#   6. Comissão (evento 7)  (Despesa, 3103, 2104) — 2.000,00   ← par 3.1.03/2.1.04
# Total débito = Total crédito = 16.400,00 (razão INALTERADO — RFC-004 decisão 1)
# --------------------------------------------------------------------------
TOTAL_EXEMPLO = Decimal("16400.00")
COMISSAO_VALOR = Decimal("2000.00")


class TestCommissionDetailAccountingIntegration(unittest.TestCase):
    """Camada analítica de ligação por venda de origem (RFC-Payroll/004) — SQL puro."""

    @classmethod
    def setUpClass(cls):
        if not HAS_PSYCOPG:
            raise unittest.SkipTest("psycopg2 não instalado")
        if not test_backend_available():
            raise unittest.SkipTest(
                "sem PostgreSQL: defina ERP_TEST_DATABASE_URL (CI) ou instale initdb/pg_ctl")
        cls.cluster = TempCluster(db_name="erp_commission_detail_acct_test", migrations=MIGRATIONS)
        cls.addClassCleanup(cls.cluster.stop)
        cls.cluster.start()
        # schema simulado: base (RFC-001 §4, da série) + camada analítica (RFC-004 §4)
        cls._run(SCHEMA_SIMULADO)
        cls._run(LINKAGE_SCHEMA)
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
    # Seed — folha do RFC-003 §6 + apurado por funcionário (db/017)
    # ------------------------------------------------------------------
    @classmethod
    def _seed(cls):
        # regras: folha base + comissão do evento 7 (mapeada)
        cls._run(
            "INSERT INTO acct_hr_salary_rule (id, code, name, category, debit_account_id, "
            "credit_account_id) VALUES "
            "(1, 'BASE',    'Salário base',        'Despesa',  3101, 2101),"
            "(2, 'INSS-EMP','INSS empregador',     'Encargos', 3102, 2102),"
            "(3, 'INSS-DEP','INSS empregado',      'Dedução',  2101, 2102),"
            "(4, 'IRRF',    'IRRF',                'Dedução',  2101, 2103),"
            "(6, 'COMM7',   'Comissão (evento 7)', 'Despesa',  3103, 2104)")
        # contracheques dedicados por cenário (isolamento entre testes):
        #   1 razão preservado · 2 ligações por venda · 3 consistência denormalização ·
        #   4 geração validada (bloqueio) · 5 idempotência UNIQUE · 6 escopo restrito ·
        #   7 estorno postado herdado · 8 estorno rascunho (descarta) · 9 relatório integrado
        cls._run(
            "INSERT INTO acct_hr_payslip (id, employee_id, journal_id, "
            "default_debit_account_id, default_credit_account_id) VALUES "
            "(1, 100, 101, 3101, 2101), (2, 200, 101, 3101, 2101),"
            "(3, 300, 101, 3101, 2101), (4, 400, 101, 3101, 2101),"
            "(5, 500, 101, 3101, 2101), (6, 600, 101, 3101, 2101),"
            "(7, 700, 101, 3101, 2101), (8, 800, 101, 3101, 2101),"
            "(9, 900, 101, 3101, 2101)")
        cls._run(
            "INSERT INTO acct_hr_payslip_line (payslip_id, rule_id, amount) VALUES "
            "(1, 1, 10000.00), (1, 2, 2400.00), (1, 3, 900.00), (1, 4, 1100.00), (1, 6, 2000.00),"
            "(2, 1, 10000.00), (2, 2, 2400.00), (2, 3, 900.00), (2, 4, 1100.00), (2, 6, 2000.00),"
            "(3, 1, 10000.00), (3, 2, 2400.00), (3, 3, 900.00), (3, 4, 1100.00), (3, 6, 2000.00),"
            "(4, 1, 10000.00), (4, 2, 2400.00), (4, 3, 900.00), (4, 4, 1100.00), (4, 6, 2000.00),"
            "(5, 1, 10000.00), (5, 2, 2400.00), (5, 3, 900.00), (5, 4, 1100.00), (5, 6, 2000.00),"
            "(6, 1, 10000.00), (6, 2, 2400.00), (6, 3, 900.00), (6, 4, 1100.00), (6, 6, 2000.00),"
            "(7, 1, 10000.00), (7, 2, 2400.00), (7, 3, 900.00), (7, 4, 1100.00), (7, 6, 2000.00),"
            "(8, 1, 10000.00), (8, 2, 2400.00), (8, 3, 900.00), (8, 4, 1100.00), (8, 6, 2000.00),"
            "(9, 1, 10000.00), (9, 2, 2400.00), (9, 3, 900.00), (9, 4, 1100.00), (9, 6, 2000.00)")
        # apurado da comissão por funcionário (commission_details — db/017):
        #   emp 100–300, 500–900 → 500 + 700 + 800 = 2.000 (RFC-004 §6);
        #   emp 400 → 500 + 1000 = 1.500 ≠ 2.000 (cenário de BLOQUEIO — decisão 3)
        cls._run(
            "INSERT INTO acct_commission_details (id, sale_id, employee_id, commission_value) VALUES "
            "(1, 1001, 100, 500.00), (2, 1002, 100, 700.00), (3, 1003, 100, 800.00),"
            "(4, 2001, 200, 500.00), (5, 2002, 200, 700.00), (6, 2003, 200, 800.00),"
            "(7, 3001, 300, 500.00), (8, 3002, 300, 700.00), (9, 3003, 300, 800.00),"
            "(10, 4001, 400, 500.00), (11, 4002, 400, 1000.00),"
            "(12, 5001, 500, 500.00), (13, 5002, 500, 700.00), (14, 5003, 500, 800.00),"
            "(15, 6001, 600, 500.00), (16, 6002, 600, 700.00), (17, 6003, 600, 800.00),"
            "(18, 7001, 700, 500.00), (19, 7002, 700, 700.00), (20, 7003, 700, 800.00),"
            "(21, 8001, 800, 500.00), (22, 8002, 800, 700.00), (23, 8003, 800, 800.00),"
            "(24, 9001, 900, 500.00), (25, 9002, 900, 700.00), (26, 9003, 900, 800.00)")

    # ------------------------------------------------------------------
    # 1. Estrutura da camada analítica (§4 / decisões 2 e 3)
    # ------------------------------------------------------------------
    def test_estrutura_camada_analitica(self):
        """A tabela de ligação tem as colunas do §4, UNIQUE e CHECK (amount > 0)."""
        for col in ["move_line_id", "commission_detail_id", "sale_id", "amount"]:
            self.assertEqual(self._scalar(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'acct_commission_move_line_detail' "
                "AND column_name = '%s'" % col), 1)
        # UNIQUE (commission_detail_id) — idempotência (decisão 3)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_constraint "
            "WHERE conname = 'uq_acct_commission_move_line_detail'"), 1)
        # CHECK (amount > 0)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_constraint "
            "WHERE conname = 'acct_commission_move_line_detail_amount_check' "
            "AND pg_get_constraintdef(oid) LIKE '%amount > (0)%'"), 1)

    # ------------------------------------------------------------------
    # 2. Razão consolidado PRESERVADO (decisão 1) — contracheque 1 dedicado
    # ------------------------------------------------------------------
    def test_geracao_razao_consolidado_preservado(self):
        """A ligação não altera o razão: 10 linhas e 16.400 = 16.400 permanecem."""
        move_id = self._scalar("SELECT acct_generate_move(1)")
        self._run("SELECT acct_generate_linkages(1, %s)" % move_id)
        # razão INALTERADO (decisão 1): 10 linhas (par por regra), equilibrado, postado
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_account_move_line WHERE move_id = %s" % move_id), 10)
        self.assertEqual(self._scalar(
            "SELECT sum(debit) FROM acct_account_move_line WHERE move_id = %s" % move_id),
            TOTAL_EXEMPLO)
        self.assertEqual(self._scalar(
            "SELECT sum(credit) FROM acct_account_move_line WHERE move_id = %s" % move_id),
            TOTAL_EXEMPLO)
        self.assertEqual(self._scalar(
            "SELECT state FROM acct_account_move WHERE id = %s" % move_id), "posted")
        # camada analítica: 3 ligações (500 + 700 + 800 = 2.000) — FORA do razão
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_commission_move_line_detail d "
            "JOIN acct_account_move_line l ON l.id = d.move_line_id "
            "WHERE l.move_id = %s" % move_id), 3)

    # ------------------------------------------------------------------
    # 3. Ligações por venda de origem (decisão 3/§6) — contracheque 2 dedicado
    # ------------------------------------------------------------------
    def test_ligacoes_por_venda_de_origem(self):
        """Cada item apurado vira uma ligação com a venda de origem e o valor."""
        move_id = self._scalar("SELECT acct_generate_move(2)")
        self._run("SELECT acct_generate_linkages(2, %s)" % move_id)
        self.assertEqual(self._rows(
            "SELECT d.sale_id, d.amount FROM acct_commission_move_line_detail d "
            "JOIN acct_account_move_line l ON l.id = d.move_line_id "
            "WHERE l.move_id = %s ORDER BY d.sale_id" % move_id),
            [(2001, Decimal("500.00")), (2002, Decimal("700.00")), (2003, Decimal("800.00"))])
        # soma das ligações = valor da linha da regra 7 (2.000, débito 3.1.03)
        self.assertEqual(self._scalar(
            "SELECT sum(d.amount) FROM acct_commission_move_line_detail d "
            "JOIN acct_account_move_line l ON l.id = d.move_line_id "
            "WHERE l.move_id = %s" % move_id), COMISSAO_VALOR)
        self.assertEqual(self._scalar(
            "SELECT l.debit FROM acct_account_move_line l "
            "WHERE l.move_id = %s AND l.account_id = 3103" % move_id), COMISSAO_VALOR)

    # ------------------------------------------------------------------
    # 4. Invariante 5 — consistência da denormalização (contracheque 3 dedicado)
    # ------------------------------------------------------------------
    def test_consistencia_denormalizacao(self):
        """sale_id da ligação = commission_details.sale_id (trigger bloqueia divergência)."""
        move_id = self._scalar("SELECT acct_generate_move(3)")
        self._run("SELECT acct_generate_linkages(3, %s)" % move_id)
        # ligações geradas: denormalização sempre consistente
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_commission_move_line_detail d "
            "JOIN acct_commission_details c ON c.id = d.commission_detail_id "
            "WHERE d.sale_id <> c.sale_id"), 0)
        # INSERT direto com sale_id errado → trigger BLOQUEIA (invariante 5)
        line_id = self._scalar(
            "SELECT l.id FROM acct_account_move_line l "
            "WHERE l.move_id = %s AND l.account_id = 3103" % move_id)
        self._fails(
            "INSERT INTO acct_commission_move_line_detail "
            "(move_line_id, commission_detail_id, sale_id, amount) "
            "VALUES (%s, 7, 9999, 500.00)" % line_id,
            msg="invariante 5")
        # CHECK (amount > 0) — comportamento (detalhe 7 = venda 3001, valor 0 → violação)
        self._fails(
            "INSERT INTO acct_commission_move_line_detail "
            "(move_line_id, commission_detail_id, sale_id, amount) "
            "VALUES (%s, 7, 3001, 0.00)" % line_id,
            err=psycopg2.errors.CheckViolation)

    # ------------------------------------------------------------------
    # 5. Geração VALIDADA (decisão 3) — bloqueio (contracheque 4 dedicado)
    # ------------------------------------------------------------------
    def test_geracao_validada_bloqueia(self):
        """Apurado divergente (1.500 ≠ 2.000) BLOQUEIA a geração das ligações."""
        move_id = self._scalar("SELECT acct_generate_move(4)")
        self._fails(
            "SELECT acct_generate_linkages(4, %s)" % move_id,
            msg="geração bloqueada")
        # falha atômica: nenhuma ligação ficou gravada no lançamento
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_commission_move_line_detail d "
            "JOIN acct_account_move_line l ON l.id = d.move_line_id "
            "WHERE l.move_id = %s" % move_id), 0)

    # ------------------------------------------------------------------
    # 6. IDEMPOTÊNCIA (decisão 3) — UNIQUE (contracheque 5 dedicado)
    # ------------------------------------------------------------------
    def test_idempotencia_unique_ligacao(self):
        """Segunda geração de ligações do mesmo lançamento é BLOQUEADA (UNIQUE)."""
        move_id = self._scalar("SELECT acct_generate_move(5)")
        self._run("SELECT acct_generate_linkages(5, %s)" % move_id)
        self._fails(
            "SELECT acct_generate_linkages(5, %s)" % move_id,
            err=psycopg2.errors.UniqueViolation)

    # ------------------------------------------------------------------
    # 7. ESCOPO RESTRITO À COMISSÃO (decisão 5) — contracheque 6 dedicado
    # ------------------------------------------------------------------
    def test_escopo_restrito_comissao(self):
        """Só a linha da regra do evento 7 recebe ligações; as demais, nenhuma."""
        move_id = self._scalar("SELECT acct_generate_move(6)")
        self._run("SELECT acct_generate_linkages(6, %s)" % move_id)
        self.assertEqual(self._rows(
            "SELECT l.rule_id, count(d.id) FROM acct_account_move_line l "
            "LEFT JOIN acct_commission_move_line_detail d ON d.move_line_id = l.id "
            "WHERE l.move_id = %s GROUP BY l.rule_id ORDER BY l.rule_id" % move_id),
            [(1, 0), (2, 0), (3, 0), (4, 0), (6, 3)])
        # uma única linha do razão carrega as ligações (a débito da comissão)
        self.assertEqual(self._scalar(
            "SELECT count(DISTINCT d.move_line_id) FROM acct_commission_move_line_detail d "
            "JOIN acct_account_move_line l ON l.id = d.move_line_id "
            "WHERE l.move_id = %s" % move_id), 1)

    # ------------------------------------------------------------------
    # 8. ESTORNO HERDADO — caso postado (decisão 4) — contracheque 7 dedicado
    # ------------------------------------------------------------------
    def test_estorno_herdado_postado(self):
        """Estorno não cria ligações novas; rastreabilidade via reversed_entry_id."""
        move_id = self._scalar("SELECT acct_generate_move(7)")
        self._run("SELECT acct_generate_linkages(7, %s)" % move_id)
        rev_id = self._scalar("SELECT acct_reverse_move(7)")
        # estorno NÃO cria ligações novas (decisão 4)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_commission_move_line_detail d "
            "JOIN acct_account_move_line l ON l.id = d.move_line_id "
            "WHERE l.move_id = %s" % rev_id), 0)
        # original preservado (move_id) com o estorno vinculado; ligações intactas
        self.assertEqual(self._scalar(
            "SELECT move_id FROM acct_hr_payslip WHERE id = 7"), move_id)
        self.assertEqual(self._scalar(
            "SELECT move_reversal_id FROM acct_hr_payslip WHERE id = 7"), rev_id)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_commission_move_line_detail d "
            "JOIN acct_account_move_line l ON l.id = d.move_line_id "
            "WHERE l.move_id = %s" % move_id), 3)
        # rastreabilidade herdada: linhas do estorno → reversed_entry_id → original → ligações
        self.assertEqual(self._rows(
            "SELECT d.sale_id FROM acct_commission_move_line_detail d "
            "JOIN acct_account_move_line l ON l.id = d.move_line_id "
            "JOIN acct_account_move m ON m.id = l.move_id "
            "JOIN acct_account_move r ON r.reversed_entry_id = m.id "
            "WHERE r.id = %s ORDER BY d.sale_id" % rev_id),
            [(7001,), (7002,), (7003,)])

    # ------------------------------------------------------------------
    # 9. ESTORNO HERDADO — rascunho cancela e descarta (decisão 4) — contracheque 8
    # ------------------------------------------------------------------
    def test_estorno_rascunho_descarta_ligacoes(self):
        """Rascunho cancelado descarta as ligações junto (CASCADE — nada no razão)."""
        # move 'entry' em rascunho (transitório durante a geração) + linha da comissão
        self._run(
            "INSERT INTO acct_account_move (move_type, state, journal_id, payslip_id) "
            "VALUES ('entry', 'draft', 101, 8)")
        draft_id = self._scalar(
            "SELECT max(id) FROM acct_account_move WHERE payslip_id = 8 AND state = 'draft'")
        line_id = self._scalar(
            "INSERT INTO acct_account_move_line "
            "(move_id, rule_id, category, account_id, debit) "
            "VALUES (%s, 6, 'Despesa', 3103, 2000.00) RETURNING id" % draft_id)
        # ligações do rascunho (emp 800 — detalhes 21/22/23)
        self._run(
            "INSERT INTO acct_commission_move_line_detail "
            "(move_line_id, commission_detail_id, sale_id, amount) VALUES "
            "(%s, 21, 8001, 500.00), (%s, 22, 8002, 700.00), (%s, 23, 8003, 800.00)"
            % (line_id, line_id, line_id))
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_commission_move_line_detail "
            "WHERE move_line_id = %s" % line_id), 3)
        # cancelamento do rascunho → o módulo descarta as linhas; ligações vão junto
        self._run("DELETE FROM acct_account_move_line WHERE move_id = %s" % draft_id)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM acct_commission_move_line_detail "
            "WHERE move_line_id = %s" % line_id), 0)

    # ------------------------------------------------------------------
    # 10. RELATÓRIO INTEGRADO (decisão 6) — venda → lançamento (contracheque 9)
    # ------------------------------------------------------------------
    def test_relatorio_integrado_venda_ao_lancamento(self):
        """Vínculo reverso do RFC-015 §2.1: da venda de origem → o move_id."""
        move_id = self._scalar("SELECT acct_generate_move(9)")
        self._run("SELECT acct_generate_linkages(9, %s)" % move_id)
        self.assertEqual(self._rows(
            "SELECT d.sale_id, m.id FROM acct_commission_move_line_detail d "
            "JOIN acct_account_move_line l ON l.id = d.move_line_id "
            "JOIN acct_account_move m ON m.id = l.move_id "
            "WHERE d.sale_id IN (9001, 9002, 9003) ORDER BY d.sale_id"),
            [(9001, move_id), (9002, move_id), (9003, move_id)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
