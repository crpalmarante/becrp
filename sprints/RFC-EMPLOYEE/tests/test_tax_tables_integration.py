#!/usr/bin/env python3
"""Teste de integração — tabelas fiscais do RFC-005 (migration 013).

Valida as tabelas fiscais versionadas por competência e a CONSULTA NO CÁLCULO
de ponta a ponta via psycopg2, num cluster PostgreSQL 16 TEMPORÁRIO e
descartável (infra compartilhada em tests/pg_bootstrap.py):

  * aplica as migrations NA ORDEM do projeto: 002 → 009 → 011 → 010 → 012 → 013;
  * valida o SEED das tabelas ilustrativas do RFC-005 §2/§3 (competência
    2026-08 do EXEMPLO-competencia.md) e o versionamento por competência;
  * valida a CONSULTA POR COMPETÊNCIA (RFC-005 regra 1): f_tax_inss/f_tax_irrf/
    f_tax_base_irrf usam a tabela vigente DA competência — a mesma base dá
    resultados diferentes por competência e falta de tabela é fail-closed;
  * valida a PRECISÃO (regra 5): INSS progressivo por faixa e IRRF pela faixa
    reproduzem EXATAMENTE o EXEMPLO-competencia.md (INSS 464,31818184… e
    IRRF 322,936500024…, Decimal, sem arredondamento intermediário);
  * valida a IMUTABILIDADE (regra 2 + decisão 1): UPDATE/DELETE/TRUNCATE
    bloqueados — alteração gera NOVA VERSÃO com nova competência (INSERT);
  * valida a integridade do seed (UNIQUE de faixa, CHECKs de faixa/alíquota).

Executar:
  python3 -m unittest tests.test_tax_tables_integration -v
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
    "013_tax_tables.sql",
]

# --------------------------------------------------------------------------
# Referência independente — tabelas ILUSTRATIVAS do RFC-005 §2/§3 (2026-08),
# idênticas às usadas no EXEMPLO-competencia.md. A autoridade do TESTE.
# --------------------------------------------------------------------------
INSS_2026_08 = [  # (de, até, alíquota)
    (Decimal("0.00"),   Decimal("1500.00"), Decimal("0.075")),
    (Decimal("1500.00"), Decimal("3000.00"), Decimal("0.09")),
    (Decimal("3000.00"), Decimal("5000.00"), Decimal("0.12")),
    (Decimal("5000.00"), None,               Decimal("0.14")),
]
IRRF_2026_08 = [  # (de, até, alíquota, dedução da faixa)
    (Decimal("0.00"),   Decimal("2000.00"), Decimal("0.00"),  Decimal("0.00")),
    (Decimal("2000.00"), Decimal("4000.00"), Decimal("0.10"),  Decimal("100.00")),
    (Decimal("4000.00"), Decimal("6000.00"), Decimal("0.15"),  Decimal("300.00")),
    (Decimal("6000.00"), None,               Decimal("0.225"), Decimal("700.00")),
]
DEPENDENTE_2026_08 = Decimal("189.59")        # premissa do EXEMPLO (RFC-005 §3)

# Base do EXEMPLO-competencia.md: salário 4.500,00 + 10 h HE 50% (Etapa 1)
BASE_INSS_EXEMPLO = Decimal("4806.818182")


def inss_progressivo(base, tabela):
    """Espelho Decimal da regra do RFC-005 §2 (progressivo por faixa)."""
    total = Decimal("0")
    for de, ate, taxa in tabela:
        if base > de:
            topo = base if ate is None else min(base, ate)
            total += (topo - de) * taxa
    return total


def irrf_por_faixa(base, tabela):
    """Espelho Decimal da regra do RFC-005 §3 (imposto = base × taxa − dedução)."""
    for de, ate, taxa, deducao in tabela:
        if base > de and (ate is None or base <= ate):
            return max(base * taxa - deducao, Decimal("0"))
    raise AssertionError(f"base {base} fora das faixas")


class TestTaxTablesIntegration(unittest.TestCase):
    """Tabelas fiscais RFC-005 — seed, consulta por competência, precisão, imutabilidade."""

    @classmethod
    def setUpClass(cls):
        if not HAS_PSYCOPG:
            raise unittest.SkipTest("psycopg2 não instalado")
        if not test_backend_available():
            raise unittest.SkipTest(
                "sem PostgreSQL: defina ERP_TEST_DATABASE_URL (CI) ou instale initdb/pg_ctl")
        cls.cluster = TempCluster(db_name="erp_tax_test", migrations=MIGRATIONS)
        # Limpeza garantida MESMO se o start() falhar daqui em diante:
        # addClassCleanup roda também quando o setUpClass levanta (stop() é
        # idempotente — seguro em cluster não iniciado).
        cls.addClassCleanup(cls.cluster.stop)
        cls.cluster.start()

    # ------------------------------------------------------------------
    # Helpers — cada chamada abre sessão própria
    # ------------------------------------------------------------------
    def _run(self, sql):
        conn = self.cluster.connect()
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

    def _brackets(self, table_type, reference):
        """Faixas (de, até, alíquota[, dedução]) da tabela na ordem."""
        conn = self.cluster.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT bracket_from, bracket_to, rate, deduction "
                    "FROM tax_tables WHERE table_type = %s AND reference = %s "
                    "ORDER BY bracket_from", (table_type, reference))
                rows = cur.fetchall()
        finally:
            conn.close()
        return [
            (Decimal(r[0]),
             Decimal(r[1]) if r[1] is not None else None,
             Decimal(r[2]), Decimal(r[3]))
            for r in rows
        ]

    # ------------------------------------------------------------------
    # 1. Estrutura e restrições
    # ------------------------------------------------------------------
    def test_tabelas_e_restricoes(self):
        """tax_tables/tax_irrf_dependents existem com UNIQUE/CHECKs do RFC-005."""
        n = self._scalar(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_name IN ('tax_tables', 'tax_irrf_dependents')")
        self.assertEqual(n, 2)
        for conname in ("uq_tax_bracket", "uq_tax_dependent_deduction",
                        "ck_tax_bracket_to", "ck_tax_rate", "ck_tax_type"):
            self.assertEqual(self._scalar(
                f"SELECT count(*) FROM pg_constraint WHERE conname = '{conname}'"), 1)
        # imutabilidade por trigger (RFC-005 regra 2)
        for tgname in ("trg_tax_tables_immutable", "trg_tax_irrf_dependents_immutable",
                       "trg_tax_tables_no_truncate", "trg_tax_irrf_dependents_no_truncate"):
            self.assertEqual(self._scalar(
                f"SELECT count(*) FROM pg_trigger WHERE tgname = '{tgname}'"), 1)

    # ------------------------------------------------------------------
    # 2. Seed — tabelas ilustrativas do RFC-005 (2026-08 = EXEMPLO)
    # ------------------------------------------------------------------
    def test_seed_inss_bate_com_rfc005(self):
        """4 faixas INSS de 2026-08 com os limites/alíquotas do RFC-005 §2."""
        got = self._brackets("inss", "2026-08")
        self.assertEqual(len(got), 4)
        expected = [
            (Decimal("0.00"),   Decimal("1500.00"), Decimal("0.0750"), Decimal("0.00")),
            (Decimal("1500.00"), Decimal("3000.00"), Decimal("0.0900"), Decimal("0.00")),
            (Decimal("3000.00"), Decimal("5000.00"), Decimal("0.1200"), Decimal("0.00")),
            (Decimal("5000.00"), None,               Decimal("0.1400"), Decimal("0.00")),
        ]
        self.assertEqual(got, expected)

    def test_seed_irrf_bate_com_rfc005(self):
        """4 faixas IRRF de 2026-08 com limites/alíquotas/deduções do RFC-005 §3."""
        got = self._brackets("irrf", "2026-08")
        self.assertEqual(len(got), 4)
        expected = [
            (Decimal("0.00"),   Decimal("2000.00"), Decimal("0.0000"), Decimal("0.00")),
            (Decimal("2000.00"), Decimal("4000.00"), Decimal("0.1000"), Decimal("100.00")),
            (Decimal("4000.00"), Decimal("6000.00"), Decimal("0.1500"), Decimal("300.00")),
            (Decimal("6000.00"), None,               Decimal("0.2250"), Decimal("700.00")),
        ]
        self.assertEqual(got, expected)

    def test_dependente_deducao_seed(self):
        """Dedução por dependente de 2026-08 = 189,59 (premissa do EXEMPLO)."""
        self.assertEqual(self._scalar(
            "SELECT amount FROM tax_irrf_dependents "
            "WHERE reference = '2026-08' AND deduction_type = 'dependente'"),
            Decimal("189.59"))

    # ------------------------------------------------------------------
    # 3. Consulta no cálculo — precisão (regra 5) vs. EXEMPLO-competencia.md
    # ------------------------------------------------------------------
    def test_inss_progressivo_exemplo(self):
        """f_tax_inss(2026-08, 4.806,818182) == 464,31818184… (Etapa 3 do EXEMPLO)."""
        base = BASE_INSS_EXEMPLO
        got = self._scalar(f"SELECT f_tax_inss('2026-08', {base})")
        self.assertEqual(got, inss_progressivo(base, INSS_2026_08))
        # EXEMPLO Etapa 3: 112,50 + 135,00 + 216,81818184 = 464,31818184
        # (o documento exibe 464,318182 por arredondamento de apresentação)
        self.assertEqual(got, Decimal("464.31818184"))

    def test_irrf_do_exemplo(self):
        """Cadeia base IRRF → IRRF reproduz as Etapas 4–5 do EXEMPLO, em Decimal."""
        base = BASE_INSS_EXEMPLO
        inss = self._scalar(f"SELECT f_tax_inss('2026-08', {base})")
        base_irrf = self._scalar(
            f"SELECT f_tax_base_irrf('2026-08', {base}, {inss}, 1)")
        # Etapa 4: base IRRF = base INSS − INSS − 1 × 189,59
        self.assertEqual(base_irrf, base - inss - DEPENDENTE_2026_08)
        irrf = self._scalar(f"SELECT f_tax_irrf('2026-08', {base_irrf})")
        # Etapa 5: base × 15% − 300 = 322,936500024…
        self.assertEqual(irrf, irrf_por_faixa(base_irrf, IRRF_2026_08))
        self.assertEqual(irrf, Decimal("322.936500024"))

    # ------------------------------------------------------------------
    # 4. Consulta POR COMPETÊNCIA (RFC-005 regra 1) + versionamento (regra 2)
    # ------------------------------------------------------------------
    def test_consulta_por_competencia(self):
        """Mesma base → INSS/IRRF DIFERENTES por competência (tabela vigente em X)."""
        base = BASE_INSS_EXEMPLO
        inss_2026 = self._scalar(f"SELECT f_tax_inss('2026-08', {base})")
        inss_2027 = self._scalar(f"SELECT f_tax_inss('2027-01', {base})")
        self.assertNotEqual(inss_2026, inss_2027)
        # 2027-01: 1.500×8% + 1.500×10% + 1.806,818182×14% = 522,95454548
        self.assertEqual(inss_2027, Decimal("522.95454548"))

    def test_irrf_por_competencia(self):
        """Dedução da faixa e por dependente também são da competência (2027-01)."""
        base = BASE_INSS_EXEMPLO
        inss_2027 = self._scalar(f"SELECT f_tax_inss('2027-01', {base})")
        base_irrf_2027 = self._scalar(
            f"SELECT f_tax_base_irrf('2027-01', {base}, {inss_2027}, 1)")
        # 2027-01: dedução por dependente 200,00 (não 189,59) — versão nova
        self.assertEqual(base_irrf_2027, base - inss_2027 - Decimal("200.00"))
        irrf_2027 = self._scalar(f"SELECT f_tax_irrf('2027-01', {base_irrf_2027})")
        # faixa 15% com dedução 350 (não 300) — versão nova da tabela
        self.assertEqual(irrf_2027,
                         base_irrf_2027 * Decimal("0.15") - Decimal("350.00"))

    def test_tabela_ausente_fail_closed(self):
        """Competência sem tabela → EXCEÇÃO (folha não calcula sem a tabela)."""
        self._fails("SELECT f_tax_inss('1999-01', 5000.00)",
                    msg="não encontrada")
        self._fails("SELECT f_tax_irrf('1999-01', 5000.00)",
                    msg="não encontrada")

    # ------------------------------------------------------------------
    # 5. Regras de cálculo (faixas, isenção, limites)
    # ------------------------------------------------------------------
    def test_faixa_inss_abaixo_do_limite(self):
        """Base no meio da 1ª faixa → só a parcela da faixa atingida; base 0 → 0."""
        self.assertEqual(self._scalar("SELECT f_tax_inss('2026-08', 1500.00)"),
                         Decimal("112.50"))          # 1.500 × 7,5%
        self.assertEqual(self._scalar("SELECT f_tax_inss('2026-08', 0.00)"),
                         Decimal("0"))

    def test_irrf_isencao_e_faixa(self):
        """Até 2.000 isento; 2.000,01 enquadra na faixa de 10% (dedução 100)."""
        self.assertEqual(self._scalar("SELECT f_tax_irrf('2026-08', 1500.00)"),
                         Decimal("0"))
        self.assertEqual(self._scalar("SELECT f_tax_irrf('2026-08', 2000.00)"),
                         Decimal("0"))               # "até 2.000 isento"
        self.assertEqual(self._scalar("SELECT f_tax_irrf('2026-08', 2000.01)"),
                         Decimal("100.001"))         # 2.000,01 × 10% − 100

    # ------------------------------------------------------------------
    # 6. Imutabilidade (regra 2 + decisão 1) e integridade do seed
    # ------------------------------------------------------------------
    def test_imutabilidade_das_tabelas(self):
        """UPDATE/DELETE/TRUNCATE bloqueados; nova versão = novo INSERT."""
        self._fails("UPDATE tax_tables SET rate = 0.20 WHERE reference = '2026-08'",
                    msg="imutável")
        self._fails("DELETE FROM tax_tables WHERE reference = '2026-08'",
                    msg="imutável")
        self._fails("TRUNCATE tax_tables", msg="imutável")
        self._fails("UPDATE tax_irrf_dependents SET amount = 0 WHERE reference = '2026-08'",
                    msg="imutável")
        self._fails("DELETE FROM tax_irrf_dependents WHERE reference = '2026-08'",
                    msg="imutável")
        # nova versão = INSERT com nova competência (regra 2)
        self._run(
            "INSERT INTO tax_tables (table_type, reference, year, month, "
            "bracket_from, bracket_to, rate, deduction) VALUES "
            "('inss', '2027-02', 2027, 2, 0.00, 1500.00, 0.0750, 0.00)")
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM tax_tables WHERE reference = '2027-02'"), 1)

    def test_unicidade_e_checks(self):
        """Faixa duplicada (UNIQUE), intervalo inválido e alíquota > 1 rejeitados."""
        self._fails(
            "INSERT INTO tax_tables (table_type, reference, year, month, "
            "bracket_from, bracket_to, rate, deduction) VALUES "
            "('inss', '2026-08', 2026, 8, 0.00, 1500.00, 0.0750, 0.00)",
            err=psycopg2.errors.UniqueViolation)     # uq_tax_bracket
        self._fails(
            "INSERT INTO tax_tables (table_type, reference, year, month, "
            "bracket_from, bracket_to, rate, deduction) VALUES "
            "('inss', '2027-03', 2027, 3, 3000.00, 1500.00, 0.0750, 0.00)",
            err=psycopg2.errors.CheckViolation)      # ck_tax_bracket_to
        self._fails(
            "INSERT INTO tax_tables (table_type, reference, year, month, "
            "bracket_from, bracket_to, rate, deduction) VALUES "
            "('inss', '2027-03', 2027, 3, 0.00, 1500.00, 1.5000, 0.00)",
            err=psycopg2.errors.CheckViolation)      # ck_tax_rate
        self._fails(
            "INSERT INTO tax_irrf_dependents (reference, year, month, "
            "deduction_type, amount) VALUES "
            "('2026-08', 2026, 8, 'dependente', 190.00)",
            err=psycopg2.errors.UniqueViolation)     # uq_tax_dependent_deduction


if __name__ == "__main__":
    unittest.main(verbosity=2)
