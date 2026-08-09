#!/usr/bin/env python3
"""Teste de integração — módulo de comissões (migrations 016, 017 e 018).

Valida o módulo de comissões do PDV (RFC-COMISSION 002–008) de ponta a ponta
via psycopg2, num cluster PostgreSQL 16 TEMPORÁRIO e descartável (infra
compartilhada em tests/pg_bootstrap.py):

  * aplica as migrations NA ORDEM do projeto: 002 → 009 → 011 → 016 → 017 → 018;
  * migração 016 (db/016 — RFC-COMISSION/RFC-003):
      - product_categories / products / commission_rules existem com as
        constraints do modelo (ck_rule_target_exclusive, ck_rule_validity,
        índices únicos parciais da precedência — uma regra ATIVA por
        (funcionário × alvo), com versionamento por inativação — RFC-002 §5
        regra 3);
      - escrita exige a ação manter_cadastros (RFC-009 §3.1 via db/011) —
        fail-closed sem GUC;
      - a PRECEDÊNCIA produto → categoria → taxa padrão (RFC-COMISSION/RFC-002
        §3.1) resolve a taxa correta na consulta de referência (RFC-003 §5);
      - sem exclusão física (padrão RFC-008 decisão 4).
  * tela de produtos e regras por produto (RFC-COMISSION/RFC-006 — interface sobre
    a db/016): o formulário de regra por produto grava product_id com category_id
    NULL (exclusividade de alvo) e o índice único parcial uq_commission_rules_product
    bloqueia a 2ª regra ATIVA por (funcionário × produto); a inativação em cascata
    (produto + regras do produto) tira a regra da resolução (cai para categoria/
    taxa padrão) preservando o histórico — RFC-006 §4.2/§5.2.
  * tela de taxa padrão do funcionário (RFC-COMISSION/RFC-007 — interface sobre
    a db/016): o formulário grava a regra com product_id/category_id NULL e o
    índice único parcial uq_commission_rules_default bloqueia a 2ª regra ATIVA
    por funcionário; o versionamento por inativação tira o fallback da
    resolução (produtos sem regra deixam de gerar comissão — taxa 0)
    preservando o histórico — RFC-007 §3.2/§4.2.
  * tela de taxa padrão GLOBAL da empresa (RFC-COMISSION/RFC-008 — nova tabela
    commission_global_rules, db/018): o formulário grava a regra SEM funcionário
    (empresa × taxa) e o índice único parcial uq_commission_global_default
    bloqueia a 2ª regra ATIVA por empresa; o versionamento por inativação tira o
    fallback FINAL da resolução (funcionário sem taxa padrão própria deixa de
    gerar comissão — taxa 0) preservando o histórico — RFC-008 §3.2/§4.2.
  * migração 017 (db/017 — RFC-COMISSION/RFC-005):
      - pos_sales / pos_sale_items / commission_details com os CHECKs de
        equação (item_total = quantity × unit_price; commission_value =
        item_total × taxa, validado por trigger);
      - escrita exige a ação lancar_eventos (RFC-COMISSION/RFC-005 §9
        decisão 5) — fail-closed sem GUC;
      - consistência do detalhe: vendedor = da venda, item = da venda,
        rate_source coerente com o alvo da regra;
      - UNIQUE (sale_item_id) — um detalhe por item apurado;
      - apuração consolidada soma só vendas abertas com itens ativos (estorno
        da venda e devolução parcial por status, nunca negativos — RFC-005 §5
        regra 2);
      - imutabilidade: detalhe sem UPDATE/DELETE/TRUNCATE; itens e colunas de
        negócio do cabeçalho congelados após a apuração (RFC-005 §5 regra 4);
      - congelamento do apurado: commission_settlements por (funcionário ×
        competência), fechamento idempotente, imutável (estorno por status) —
        RFC-005 §3.5/§5 regra 8;
      - relatório de comissões por venda de origem (RFC-015 §2.1) lê
        commission_details com elegibilidade por status (conferência vs
        auditoria);
      - sem exclusão física.

NOTA: o cluster é COMPARTILHADO entre todos os testes (setUpClass roda uma
vez), então os helpers de seed são IDEMPOTENTES (ON CONFLICT DO NOTHING) e os
IDs são resolvidos por código via subselect — nunca IDs fixos.

Executar:
  python3 -m unittest tests.test_commission_rules_integration -v
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
    "016_commission_module.sql",
    "017_sales_apuration.sql",
    "018_commission_global_rules.sql",
]

CPF_A = "12345678901"
CPF_B = "98765432100"


class TestCommissionIntegration(unittest.TestCase):
    """Módulo de comissões (016/017/018) — estrutura, permissões, precedência, constraints,
    estorno, imutabilidade, telas de regras por produto (RFC-006), de taxa padrão
    do funcionário (RFC-007) e de taxa padrão GLOBAL (RFC-008)."""

    @classmethod
    def setUpClass(cls):
        if not HAS_PSYCOPG:
            raise unittest.SkipTest("psycopg2 não instalado")
        if not test_backend_available():
            raise unittest.SkipTest(
                "sem PostgreSQL: defina ERP_TEST_DATABASE_URL (CI) ou instale initdb/pg_ctl")
        cls.cluster = TempCluster(db_name="erp_comm_test", migrations=MIGRATIONS)
        # Limpeza garantida MESMO se o start() falhar (stop() idempotente).
        cls.addClassCleanup(cls.cluster.stop)
        cls.cluster.start()

        # --- Cadastros base (ADMINISTRADOR — manter_cadastros) ---
        cls._run("INSERT INTO departments (code, description) VALUES ('COM', 'Comercial')",
                 guc="ADMINISTRADOR")
        cls._run("INSERT INTO positions (code, description) VALUES ('VEND', 'Vendedor')",
                 guc="ADMINISTRADOR")
        cls._run(
            "INSERT INTO employees (full_name, birth_date, gender, nationality, cpf, "
            "address_cep, address_street, address_number, address_neighborhood, "
            "address_city, address_uf, ctps_number, ctps_series, ctps_uf, "
            "admission_date, position_id, department_id, contract_type, base_salary, "
            "payment_form, bank_code, bank_agency, bank_account) VALUES "
            f"('Vendedor A', '1990-05-10', 'M', 'Brasileira', '{CPF_A}', "
            "'01001-000', 'Rua A', '10', 'Centro', 'Sao Paulo', 'SP', '1234567', "
            "'001', 'SP', '2020-01-05', 1, 1, 'CLT', 1500.00, 'mensalista', "
            "'001', '0001', '12345-6')", guc="ADMINISTRADOR")
        cls._run(
            "INSERT INTO employees (full_name, birth_date, gender, nationality, cpf, "
            "address_cep, address_street, address_number, address_neighborhood, "
            "address_city, address_uf, ctps_number, ctps_series, ctps_uf, "
            "admission_date, position_id, department_id, contract_type, base_salary, "
            "payment_form, bank_code, bank_agency, bank_account) VALUES "
            f"('Vendedor B', '1991-01-01', 'M', 'Brasileira', '{CPF_B}', "
            "'01001-000', 'Rua B', '20', 'Centro', 'Sao Paulo', 'SP', '7654321', "
            "'002', 'SP', '2021-01-05', 1, 1, 'CLT', 1500.00, 'mensalista', "
            "'001', '0001', '12345-6')", guc="ADMINISTRADOR")

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
        """Executa esperando erro; valida a classe (ou tupla de classes) e
        (opcional) fragmento da mensagem."""
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
    # Helpers de seed IDEMPOTENTES (cluster compartilhado entre os testes)
    # ------------------------------------------------------------------
    def _categorias(self):
        self._run(
            "INSERT INTO product_categories (code, description) VALUES "
            "('ELETRO', 'Eletrônicos'), ('SERV', 'Serviços') "
            "ON CONFLICT (code) DO NOTHING", guc="ADMINISTRADOR")

    def _produtos(self):
        self._run(
            "INSERT INTO products (code, description, category_id) "
            "SELECT v.code, v.descricao, c.id FROM (VALUES "
            "('CEL-X', 'Celular Modelo X', 'ELETRO'), "
            "('PLANO', 'Plano de serviço', 'SERV'), "
            "('ACES', 'Acessório', 'ELETRO')) AS v(code, descricao, cat) "
            "JOIN product_categories c ON c.code = v.cat "
            "ON CONFLICT (code) DO NOTHING", guc="ADMINISTRADOR")

    def _regras_precedencia(self):
        """Produto CEL-X 5% · categoria SERV 3% · taxa padrão 1,5% (RFC-002 §3.1)."""
        self._run(
            "INSERT INTO commission_rules (employee_id, product_id, rate_percent, "
            "valid_from) SELECT e.id, p.id, 5.00, '2026-08-01' "
            "FROM employees e, products p WHERE e.cpf = '" + CPF_A + "' "
            "AND p.code = 'CEL-X' ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")
        self._run(
            "INSERT INTO commission_rules (employee_id, category_id, rate_percent, "
            "valid_from) SELECT e.id, c.id, 3.00, '2026-08-01' "
            "FROM employees e, product_categories c WHERE e.cpf = '" + CPF_A + "' "
            "AND c.code = 'SERV' ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")
        self._run(
            "INSERT INTO commission_rules (employee_id, rate_percent, valid_from) "
            "SELECT id, 1.50, '2026-08-01' FROM employees WHERE cpf = '" + CPF_A + "' "
            "ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")

    def _venda_exemplo(self):
        """Venda V-0001 com 3 itens (exemplo RFC-005 §6) — idempotente."""
        self._run(
            "INSERT INTO pos_sales (code, employee_id, sale_date, total_value) "
            "SELECT 'V-0001', id, '2026-08-26', 2600.00 "
            "FROM employees WHERE cpf = '" + CPF_A + "' "
            "ON CONFLICT (code) DO NOTHING", guc="OPERADOR")
        self._run(
            "INSERT INTO pos_sale_items (sale_id, product_id, quantity, unit_price, "
            "item_total) SELECT s.id, p.id, v.qtd, v.preco, v.total "
            "FROM (VALUES "
            "('CEL-X', 1, 2000.00, 2000.00), "
            "('PLANO', 1, 500.00, 500.00), "
            "('ACES', 1, 100.00, 100.00)) AS v(prod, qtd, preco, total) "
            "JOIN pos_sales s ON s.code = 'V-0001' "
            "JOIN products p ON p.code = v.prod "
            "WHERE NOT EXISTS (SELECT 1 FROM pos_sale_items i "
            "WHERE i.sale_id = s.id AND i.product_id = p.id)", guc="OPERADOR")

    def _detalhes_exemplo(self):
        """Apura os 3 itens da venda (produto/categoria/padrão) — idempotente."""
        # item CEL-X → regra de PRODUTO (5%): 2000 × 5% = 100,00
        self._run(
            "INSERT INTO commission_details (sale_id, sale_item_id, employee_id, "
            "product_id, rate_source, rule_id, rate_percent, commission_value) "
            "SELECT s.id, i.id, s.employee_id, i.product_id, 'produto', r.id, 5.00, 100.00 "
            "FROM pos_sales s JOIN pos_sale_items i ON i.sale_id = s.id "
            "JOIN commission_rules r ON r.product_id = i.product_id "
            "AND r.employee_id = s.employee_id "
            "JOIN products p ON p.id = i.product_id WHERE p.code = 'CEL-X' "
            "ON CONFLICT (sale_item_id) DO NOTHING", guc="OPERADOR")
        # item PLANO → regra de CATEGORIA (3%): 500 × 3% = 15,00
        self._run(
            "INSERT INTO commission_details (sale_id, sale_item_id, employee_id, "
            "product_id, rate_source, rule_id, rate_percent, commission_value) "
            "SELECT s.id, i.id, s.employee_id, i.product_id, 'categoria', r.id, 3.00, 15.00 "
            "FROM pos_sales s JOIN pos_sale_items i ON i.sale_id = s.id "
            "JOIN products p ON p.id = i.product_id "
            "JOIN commission_rules r ON r.category_id = p.category_id "
            "AND r.employee_id = s.employee_id WHERE p.code = 'PLANO' "
            "ON CONFLICT (sale_item_id) DO NOTHING", guc="OPERADOR")
        # item ACES → TAXA PADRÃO (1,5%): 100 × 1,5% = 1,50
        self._run(
            "INSERT INTO commission_details (sale_id, sale_item_id, employee_id, "
            "product_id, rate_source, rule_id, rate_percent, commission_value) "
            "SELECT s.id, i.id, s.employee_id, i.product_id, 'padrao', r.id, 1.50, 1.50 "
            "FROM pos_sales s JOIN pos_sale_items i ON i.sale_id = s.id "
            "JOIN commission_rules r ON r.product_id IS NULL AND r.category_id IS NULL "
            "AND r.employee_id = s.employee_id "
            "JOIN products p ON p.id = i.product_id WHERE p.code = 'ACES' "
            "ON CONFLICT (sale_item_id) DO NOTHING", guc="OPERADOR")

    def _setup_completo(self):
        """Seed completo idempotente (categorias → produtos → regras → venda → detalhes)."""
        self._categorias()
        self._produtos()
        self._regras_precedencia()
        self._venda_exemplo()
        self._detalhes_exemplo()

    def _emp_id(self, cpf):
        return self._scalar(f"SELECT id FROM employees WHERE cpf = '{cpf}'")

    def _prod_id(self, code):
        return self._scalar(f"SELECT id FROM products WHERE code = '{code}'")

    def _resolve_rate(self, emp_cpf, prod_code, sale_date='2026-08-26'):
        """Consulta de referência da precedência (RFC-003 §5 + RFC-008 §6):
        resolve a taxa do produto na data da venda — produto → categoria →
        taxa padrão do funcionário → taxa padrão GLOBAL da empresa (0 se não
        houver regra vigente)."""
        return self._scalar(
            "SELECT COALESCE("
            "(SELECT rate_percent FROM commission_rules WHERE employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{emp_cpf}') AND product_id = "
            f"(SELECT id FROM products WHERE code = '{prod_code}') AND status = 'ativo' "
            f"AND (valid_from IS NULL OR valid_from <= '{sale_date}') "
            f"AND (valid_until IS NULL OR valid_until >= '{sale_date}')),"
            "(SELECT rate_percent FROM commission_rules WHERE employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{emp_cpf}') AND category_id = "
            f"(SELECT category_id FROM products WHERE code = '{prod_code}') "
            "AND status = 'ativo' "
            f"AND (valid_from IS NULL OR valid_from <= '{sale_date}') "
            f"AND (valid_until IS NULL OR valid_until >= '{sale_date}')),"
            "(SELECT rate_percent FROM commission_rules WHERE employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{emp_cpf}') AND product_id IS NULL "
            "AND category_id IS NULL AND status = 'ativo' "
            f"AND (valid_from IS NULL OR valid_from <= '{sale_date}') "
            f"AND (valid_until IS NULL OR valid_until >= '{sale_date}')),"
            "(SELECT rate_percent FROM commission_global_rules "
            "WHERE status = 'ativo' "
            f"AND (valid_from IS NULL OR valid_from <= '{sale_date}') "
            f"AND (valid_until IS NULL OR valid_until >= '{sale_date}')), 0)")

    # ------------------------------------------------------------------
    # 1. Estrutura e restrições (016)
    # ------------------------------------------------------------------
    def test_estrutura_migration_016(self):
        """016: tabelas do módulo existem com constraints do RFC-003."""
        for t in ("product_categories", "products", "commission_rules"):
            self.assertEqual(self._scalar(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = "
                f"'{t}'"), 1)
        # exclusividade de alvo (produto OU categoria OU padrão — nunca os dois)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_constraint WHERE conname = "
            "'ck_rule_target_exclusive'"), 1)
        # índices únicos parciais da precedência
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_indexes WHERE indexname = "
            "'uq_commission_rules_product'"), 1)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_indexes WHERE indexname = "
            "'uq_commission_rules_category'"), 1)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_indexes WHERE indexname = "
            "'uq_commission_rules_default'"), 1)

    def test_estrutura_migration_017(self):
        """017: tabelas de apuração existem com UNIQUE/CHECKs do RFC-005."""
        for t in ("pos_sales", "pos_sale_items", "commission_details"):
            self.assertEqual(self._scalar(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = "
                f"'{t}'"), 1)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_constraint WHERE conname = 'uq_detail_per_item'"), 1)
        # equação item_total = quantity × unit_price (CHECK table-level — o
        # nome automático não é confiável; validamos pelo conteúdo da definição;
        # pg_get_constraintdef normaliza para minúsculas, daí lower())
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid "
            "WHERE t.relname = 'pos_sale_items' AND c.contype = 'c' "
            "AND lower(pg_get_constraintdef(c.oid)) LIKE '%item_total = round(%quantity%unit_price%'"), 1)

    # ------------------------------------------------------------------
    # 2. Permissões por ação (RFC-009 §3.1 via db/011)
    # ------------------------------------------------------------------
    def test_permissao_cadastros_manter_cadastros(self):
        """016: escrever regras exige manter_cadastros — fail-closed sem GUC."""
        self._fails(
            "INSERT INTO product_categories (code, description) VALUES ('X', 'X')",
            msg="exige a ação manter_cadastros")
        self._fails(
            "INSERT INTO product_categories (code, description) VALUES ('X', 'X')",
            guc="OPERADOR", msg="exige a ação manter_cadastros")
        self._run(
            "INSERT INTO product_categories (code, description) VALUES ('EXTRA', 'Extra') "
            "ON CONFLICT (code) DO NOTHING", guc="ADMINISTRADOR")

    def test_permissao_apuracao_lancar_eventos(self):
        """017: registrar venda/apuração exige lancar_eventos — fail-closed sem GUC."""
        self._fails(
            "INSERT INTO pos_sales (code, employee_id, sale_date, total_value) "
            f"SELECT 'V-FAKE', id, '2026-08-26', 10.00 FROM employees WHERE cpf = '{CPF_A}'",
            msg="exige a ação lancar_eventos")
        self._fails(
            "INSERT INTO pos_sales (code, employee_id, sale_date, total_value) "
            f"SELECT 'V-FAKE', id, '2026-08-26', 10.00 FROM employees WHERE cpf = '{CPF_A}'",
            guc="ADMINISTRADOR", msg="exige a ação lancar_eventos")
        self._run(
            "INSERT INTO pos_sales (code, employee_id, sale_date, total_value) "
            f"SELECT 'V-FAKE', id, '2026-08-26', 10.00 FROM employees WHERE cpf = '{CPF_A}' "
            "ON CONFLICT (code) DO NOTHING", guc="OPERADOR")

    # ------------------------------------------------------------------
    # 3. Precedência produto → categoria → taxa padrão (RFC-002 §3.1)
    # ------------------------------------------------------------------
    def test_precedencia_produto_categoria_padrao(self):
        """A consulta de referência (RFC-003 §5) resolve a taxa por precedência."""
        self._categorias()
        self._produtos()
        self._regras_precedencia()
        emp, celx, plano, aces = (self._emp_id(CPF_A), self._prod_id("CEL-X"),
                                  self._prod_id("PLANO"), self._prod_id("ACES"))

        def rate_for(emp_id, prod_id):
            return self._scalar(
                "SELECT COALESCE("
                "(SELECT rate_percent FROM commission_rules WHERE employee_id = "
                f"{emp_id} AND product_id = {prod_id} AND status = 'ativo' "
                "AND (valid_from IS NULL OR valid_from <= '2026-08-26') "
                "AND (valid_until IS NULL OR valid_until >= '2026-08-26')),"
                "(SELECT rate_percent FROM commission_rules WHERE employee_id = "
                f"{emp_id} AND category_id = (SELECT category_id FROM products "
                f"WHERE id = {prod_id}) AND status = 'ativo' "
                "AND (valid_from IS NULL OR valid_from <= '2026-08-26') "
                "AND (valid_until IS NULL OR valid_until >= '2026-08-26')),"
                "(SELECT rate_percent FROM commission_rules WHERE employee_id = "
                f"{emp_id} AND product_id IS NULL AND category_id IS NULL "
                "AND status = 'ativo' "
                "AND (valid_from IS NULL OR valid_from <= '2026-08-26') "
                "AND (valid_until IS NULL OR valid_until >= '2026-08-26')), 0)")

        # CEL-X tem regra de produto → 5% (vence a categoria ELETRO e o padrão)
        self.assertEqual(rate_for(emp, celx), 5.00)
        # PLANO tem regra de categoria SERV → 3% (sem regra de produto)
        self.assertEqual(rate_for(emp, plano), 3.00)
        # ACES: sem regra de produto nem da categoria ELETRO → taxa padrão 1,5%
        self.assertEqual(rate_for(emp, aces), 1.50)

    # ------------------------------------------------------------------
    # 4. Constraints da regra (016)
    # ------------------------------------------------------------------
    def test_regra_alvo_exclusivo(self):
        """ck_rule_target_exclusive: regra não pode mirar produto E categoria."""
        self._categorias()
        self._produtos()
        self._fails(
            "INSERT INTO commission_rules (employee_id, product_id, category_id, "
            "rate_percent) SELECT e.id, p.id, c.id, 9.00 "
            f"FROM employees e, products p, product_categories c "
            f"WHERE e.cpf = '{CPF_A}' AND p.code = 'CEL-X' AND c.code = 'ELETRO'",
            guc="ADMINISTRADOR", err=psycopg2.errors.CheckViolation,
            msg="ck_rule_target_exclusive")

    def test_regra_taxa_fora_do_intervalo(self):
        """rate_percent fora de 0–100 é rejeitado pelo CHECK."""
        self._categorias()
        self._fails(
            "INSERT INTO commission_rules (employee_id, category_id, rate_percent) "
            f"SELECT id, (SELECT id FROM product_categories WHERE code = 'ELETRO'), 150.00 "
            f"FROM employees WHERE cpf = '{CPF_A}'",
            guc="ADMINISTRADOR", err=psycopg2.errors.CheckViolation)

    def test_regra_vigencia_invalida(self):
        """ck_rule_validity: valid_until >= valid_from."""
        self._categorias()
        self._fails(
            "INSERT INTO commission_rules (employee_id, category_id, rate_percent, "
            "valid_from, valid_until) SELECT id, "
            "(SELECT id FROM product_categories WHERE code = 'ELETRO'), 2.00, "
            f"'2026-08-01', '2026-07-01' FROM employees WHERE cpf = '{CPF_A}'",
            guc="ADMINISTRADOR", err=psycopg2.errors.CheckViolation,
            msg="ck_rule_validity")

    def test_regra_duplicada_ativa_rejeitada(self):
        """db/016: uma única regra ATIVA por (funcionário × alvo) — duplicata rejeitada."""
        self._categorias()
        self._produtos()
        self._run(
            "INSERT INTO commission_rules (employee_id, product_id, rate_percent, "
            "valid_from) SELECT e.id, p.id, 5.00, '2026-08-01' "
            f"FROM employees e, products p WHERE e.cpf = '{CPF_B}' AND p.code = 'CEL-X' "
            "ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")
        # segunda regra ATIVA para o mesmo funcionário × produto → bloqueada pelo
        # índice único parcial (uq_commission_rules_product)
        self._fails(
            "INSERT INTO commission_rules (employee_id, product_id, rate_percent, "
            "valid_from) SELECT e.id, p.id, 7.00, '2026-09-01' "
            f"FROM employees e, products p WHERE e.cpf = '{CPF_B}' AND p.code = 'CEL-X'",
            guc="ADMINISTRADOR", err=psycopg2.errors.UniqueViolation,
            msg="uq_commission_rules_product")
        # idem para regra de CATEGORIA (uq_commission_rules_category)
        self._run(
            "INSERT INTO commission_rules (employee_id, category_id, rate_percent) "
            f"SELECT e.id, c.id, 3.00 FROM employees e, product_categories c "
            f"WHERE e.cpf = '{CPF_B}' AND c.code = 'ELETRO' "
            "ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")
        self._fails(
            "INSERT INTO commission_rules (employee_id, category_id, rate_percent) "
            f"SELECT e.id, c.id, 4.00 FROM employees e, product_categories c "
            f"WHERE e.cpf = '{CPF_B}' AND c.code = 'ELETRO'",
            guc="ADMINISTRADOR", err=psycopg2.errors.UniqueViolation,
            msg="uq_commission_rules_category")
        # idem para a TAXA PADRÃO (uq_commission_rules_default)
        self._run(
            "INSERT INTO commission_rules (employee_id, rate_percent) "
            f"SELECT id, 1.50 FROM employees WHERE cpf = '{CPF_B}' "
            "ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")
        self._fails(
            "INSERT INTO commission_rules (employee_id, rate_percent) "
            f"SELECT id, 2.00 FROM employees WHERE cpf = '{CPF_B}'",
            guc="ADMINISTRADOR", err=psycopg2.errors.UniqueViolation,
            msg="uq_commission_rules_default")

    def test_regra_versionamento_por_inativacao(self):
        """db/016: inativar a regra atual permite versionar (nova regra ATIVA com
        nova vigência) — a resolução passa a usar apenas a regra ativa."""
        self._categorias()
        self._produtos()
        # usa o Vendedor B (isolado do seed de precedência do Vendedor A)
        self._run(
            "INSERT INTO commission_rules (employee_id, product_id, rate_percent, "
            "valid_from, valid_until) SELECT e.id, p.id, 5.00, '2026-01-01', '2026-06-30' "
            f"FROM employees e, products p WHERE e.cpf = '{CPF_B}' AND p.code = 'CEL-X' "
            "ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")
        # regra atual fica INATIVA (histórico preservado — sem exclusão física)
        self._run(
            "UPDATE commission_rules SET status = 'inativo' WHERE employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_B}') AND product_id = "
            "(SELECT id FROM products WHERE code = 'CEL-X')", guc="ADMINISTRADOR")
        # nova regra ATIVA com a nova vigência → permitida (versionamento)
        self._run(
            "INSERT INTO commission_rules (employee_id, product_id, rate_percent, "
            "valid_from) SELECT e.id, p.id, 7.00, '2026-07-01' "
            f"FROM employees e, products p WHERE e.cpf = '{CPF_B}' AND p.code = 'CEL-X' "
            "ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")
        # a consulta de resolução (RFC-003 §5) usa apenas a regra ATIVA (7%)
        self.assertEqual(self._scalar(
            "SELECT rate_percent FROM commission_rules WHERE employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_B}') AND product_id = "
            "(SELECT id FROM products WHERE code = 'CEL-X') AND status = 'ativo'"), 7.00)

    # ------------------------------------------------------------------
    # 4.1 Tela de produtos e regras por produto (RFC-COMISSION/RFC-006)
    # ------------------------------------------------------------------
    def test_tela_regra_produto_duplicidade_bloqueada(self):
        """RFC-006 §4.2: o formulário de regra por produto grava product_id com
        category_id NULL (exclusividade de alvo) e o índice único parcial
        uq_commission_rules_product bloqueia a 2ª regra ATIVA para o mesmo
        (funcionário × produto) — a tela aponta a regra existente."""
        self._categorias()
        self._produtos()
        self._regras_precedencia()
        # a regra de produto de A × CEL-X existe como alvo exclusivo de produto
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_rules WHERE product_id IS NOT NULL "
            "AND category_id IS NULL AND status = 'ativo' AND employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_A}') AND product_id = "
            "(SELECT id FROM products WHERE code = 'CEL-X')"), 1)
        # duplicata ATIVA para o mesmo (funcionário × produto) → bloqueada pelo
        # índice único parcial MESMO com permissão válida (fail-closed no banco)
        self._fails(
            "INSERT INTO commission_rules (employee_id, product_id, rate_percent, "
            "valid_from) SELECT e.id, p.id, 7.00, '2026-09-01' "
            f"FROM employees e, products p WHERE e.cpf = '{CPF_A}' "
            "AND p.code = 'CEL-X'",
            guc="ADMINISTRADOR", err=psycopg2.errors.UniqueViolation,
            msg="uq_commission_rules_product")

    def test_tela_produto_inativacao_cascata_regras(self):
        """RFC-006 §5.2: inativar produto com regras → a TELA inativa o produto
        E as regras do produto (cascata lógica com confirmação): a regra deixa
        de resolver (cai para categoria/padrão), nada é apagado (histórico) e
        uma nova regra ATIVA pode ser criada (versionamento)."""
        self._categorias()
        self._produtos()
        self._regras_precedencia()
        # produto PRÓPRIO do teste (TEL-9, categoria ELETRO) + regra 4% para A.
        # TEL-9 não é usado por nenhum outro teste: a inativação permanente e a
        # nova regra 7% ao final NÃO contaminam o estado compartilhado do cluster.
        self._run(
            "INSERT INTO products (code, description, category_id) "
            "SELECT 'TEL-9', 'Telefone Fixo', id FROM product_categories "
            "WHERE code = 'ELETRO' ON CONFLICT (code) DO NOTHING",
            guc="ADMINISTRADOR")
        self._run(
            "INSERT INTO commission_rules (employee_id, product_id, rate_percent, "
            "valid_from) SELECT e.id, p.id, 4.00, '2026-08-01' "
            f"FROM employees e, products p WHERE e.cpf = '{CPF_A}' "
            "AND p.code = 'TEL-9' ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")

        # regra de produto resolve antes da inativação (4% vence categoria/padrão)
        self.assertEqual(self._resolve_rate(CPF_A, "TEL-9"), 4.00)
        # a cascata é responsabilidade da TELA (RFC-006 §5.2 — confirmação):
        # inativar SÓ o produto NÃO desativa a regra no banco
        self._run("UPDATE products SET status = 'inativo' WHERE code = 'TEL-9'",
                  guc="ADMINISTRADOR")
        self.assertEqual(self._resolve_rate(CPF_A, "TEL-9"), 4.00)
        # cascata completa (o que a tela faz após a confirmação): produto + regras
        self._run(
            "UPDATE commission_rules SET status = 'inativo' WHERE product_id = "
            "(SELECT id FROM products WHERE code = 'TEL-9') AND employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_A}')", guc="ADMINISTRADOR")
        # a regra deixa de resolver → cai para a TAXA PADRÃO (ELETRO sem regra de A)
        self.assertEqual(self._resolve_rate(CPF_A, "TEL-9"), 1.50)
        # inativação lógica: produto e regra continuam gravados (histórico)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM products WHERE code = 'TEL-9'"), 1)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_rules WHERE product_id = "
            "(SELECT id FROM products WHERE code = 'TEL-9') AND status = 'inativo'"), 1)
        # após a cascata, uma nova regra ATIVA para o mesmo produto é permitida
        # (versionamento — RFC-006 §8 decisão 4), com a NOVA vigência
        self._run(
            "INSERT INTO commission_rules (employee_id, product_id, rate_percent, "
            "valid_from) SELECT e.id, p.id, 7.00, '2026-09-01' "
            f"FROM employees e, products p WHERE e.cpf = '{CPF_A}' "
            "AND p.code = 'TEL-9' ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")
        # a taxa é da DATA DA VENDA (RFC-002 §5 regra 3): antes da nova vigência
        # o fallback continua valendo; dentro dela a nova regra resolve (7%)
        self.assertEqual(self._resolve_rate(CPF_A, "TEL-9"), 1.50)
        self.assertEqual(self._resolve_rate(CPF_A, "TEL-9", "2026-09-15"), 7.00)

    # ------------------------------------------------------------------
    # 4.2 Tela de taxa padrão do funcionário (RFC-COMISSION/RFC-007)
    # ------------------------------------------------------------------
    def test_tela_taxa_padrao_duplicidade_bloqueada(self):
        """RFC-007 §3.2: o formulário de taxa padrão grava a regra com product_id e
        category_id NULL (exclusividade de alvo) e o índice único parcial
        uq_commission_rules_default bloqueia a 2ª regra ATIVA para o mesmo
        funcionário — a tela aponta a regra existente."""
        self._categorias()
        self._produtos()
        self._regras_precedencia()
        # a taxa padrão de A existe como regra de alvo exclusivo (produto/categoria NULL)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_rules WHERE product_id IS NULL "
            "AND category_id IS NULL AND status = 'ativo' AND employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_A}')"), 1)
        # duplicata ATIVA para o mesmo funcionário → bloqueada pelo índice único
        # parcial MESMO com permissão válida (fail-closed no banco)
        self._fails(
            "INSERT INTO commission_rules (employee_id, rate_percent, valid_from) "
            f"SELECT id, 2.00, '2026-09-01' FROM employees WHERE cpf = '{CPF_A}'",
            guc="ADMINISTRADOR", err=psycopg2.errors.UniqueViolation,
            msg="uq_commission_rules_default")

    def test_tela_taxa_padrao_versionamento_por_inativacao(self):
        """RFC-007 §3.2/§4.2: para mudar a taxa padrão, a TELA inativa a regra
        atual (histórico preservado) e o gestor cria a nova com a nova vigência:
        a regra inativa deixa de resolver (produtos sem regra deixam de gerar
        comissão — taxa 0) e a nova vigora apenas dentro da vigência."""
        self._categorias()
        self._produtos()
        self._regras_precedencia()
        # ACES (ELETRO) não tem regra de produto nem de categoria para A — resolve
        # pela TAXA PADRÃO de A (1,5%) antes da inativação
        self.assertEqual(self._resolve_rate(CPF_A, "ACES"), 1.50)
        # fluxo da tela (RFC-007 §4.2 — confirmação): inativar a taxa padrão de A
        self._run(
            "UPDATE commission_rules SET status = 'inativo' WHERE employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_A}') "
            "AND product_id IS NULL AND category_id IS NULL AND status = 'ativo'",
            guc="ADMINISTRADOR")
        # restaura o estado original MESMO se uma asserção falhar (não contamina o
        # cluster compartilhado): re-ativa a 1,5% e inativa a nova regra 7%.
        # addCleanup roda em LIFO → primeiro inativa a 7%, depois re-ativa a 1,5%.
        self.addCleanup(self._run,
            "UPDATE commission_rules SET status = 'ativo' WHERE employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_A}') "
            "AND product_id IS NULL AND category_id IS NULL AND rate_percent = 1.50",
            guc="ADMINISTRADOR")
        self.addCleanup(self._run,
            "UPDATE commission_rules SET status = 'inativo' WHERE employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_A}') "
            "AND product_id IS NULL AND category_id IS NULL AND rate_percent = 7.00",
            guc="ADMINISTRADOR")
        # inativação lógica: a regra continua gravada (histórico — sem exclusão física)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_rules WHERE product_id IS NULL "
            "AND category_id IS NULL AND status = 'inativo' AND employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_A}')"), 1)
        # sem fallback: ACES deixa de gerar comissão (taxa resolvida = 0)
        self.assertEqual(self._resolve_rate(CPF_A, "ACES"), 0)
        # nova regra ATIVA com a NOVA vigência → permitida (versionamento)
        self._run(
            "INSERT INTO commission_rules (employee_id, rate_percent, valid_from) "
            f"SELECT id, 7.00, '2026-09-01' FROM employees WHERE cpf = '{CPF_A}' "
            "ON CONFLICT DO NOTHING", guc="ADMINISTRADOR")
        # a taxa é da DATA DA VENDA (RFC-002 §5 regra 3): antes da nova vigência o
        # fallback continua zerado; dentro dela a nova taxa resolve (7%)
        self.assertEqual(self._resolve_rate(CPF_A, "ACES"), 0)
        self.assertEqual(self._resolve_rate(CPF_A, "ACES", "2026-09-15"), 7.00)

    # ------------------------------------------------------------------
    # 4.3 Tela de taxa padrão GLOBAL da empresa (RFC-COMISSION/RFC-008)
    # ------------------------------------------------------------------
    def test_tela_taxa_global_duplicidade_bloqueada(self):
        """RFC-008 §3.2: o formulário de taxa padrão GLOBAL grava a regra SEM
        funcionário (empresa × taxa) e o índice único parcial
        uq_commission_global_default bloqueia a 2ª regra ATIVA — a tela aponta
        a regra existente."""
        # estrutura da db/018 (RFC-008 §6): tabela própria SEM employee_id + o
        # índice único parcial singleton (uma ATIVA por empresa)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = "
            "'commission_global_rules'"), 1)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM pg_indexes WHERE indexname = "
            "'uq_commission_global_default'"), 1)
        self._categorias()
        self._produtos()
        self._regras_precedencia()
        # seed idempotente da taxa padrão GLOBAL ativa (1,00% — sem funcionário);
        # a taxa 1,00 é de uso EXCLUSIVO deste teste (a 2,50 do teste de
        # versionamento é distinta), então o cleanup não contamina o cluster
        self._run(
            "INSERT INTO commission_global_rules (rate_percent, valid_from) "
            "SELECT 1.00, '2026-08-01' WHERE NOT EXISTS ("
            "SELECT 1 FROM commission_global_rules WHERE status = 'ativo')",
            guc="ADMINISTRADOR")
        # limpa MESMO se uma asserção falhar (não deixa global ativa no cluster)
        self.addCleanup(self._run,
            "UPDATE commission_global_rules SET status = 'inativo' "
            "WHERE rate_percent = 1.00 AND status = 'ativo'",
            guc="ADMINISTRADOR")
        # existe exatamente UMA regra global ATIVA (sem funcionário — RFC-008 §8 decisão 2)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_global_rules WHERE status = 'ativo'"), 1)
        # duplicata ATIVA → bloqueada pelo índice único parcial MESMO com
        # permissão válida (fail-closed no banco)
        self._fails(
            "INSERT INTO commission_global_rules (rate_percent, valid_from) "
            "VALUES (2.00, '2026-09-01')",
            guc="ADMINISTRADOR", err=psycopg2.errors.UniqueViolation,
            msg="uq_commission_global_default")

    def test_tela_taxa_global_versionamento_por_inativacao(self):
        """RFC-008 §3.2/§4.2: para mudar a taxa GLOBAL, a TELA inativa a regra
        atual (histórico preservado) e cria a nova com a nova vigência: a regra
        inativa deixa de resolver (funcionários sem taxa padrão própria deixam
        de gerar comissão — taxa 0) e a nova vigora apenas dentro da vigência."""
        self._categorias()
        self._produtos()
        self._regras_precedencia()
        # seed idempotente da taxa padrão GLOBAL ativa (2,50% — taxa exclusiva
        # deste teste, distinta da 1,00 do teste de duplicidade e da 7,00 final)
        self._run(
            "INSERT INTO commission_global_rules (rate_percent, valid_from) "
            "SELECT 2.50, '2026-08-01' WHERE NOT EXISTS ("
            "SELECT 1 FROM commission_global_rules WHERE status = 'ativo')",
            guc="ADMINISTRADOR")
        # ACES resolve pela taxa padrão de A (1,5% — A TEM taxa própria; a
        # GLOBAL não entra: precedência RFC-008 §2)
        self.assertEqual(self._resolve_rate(CPF_A, "ACES"), 1.50)
        # fluxo da tela (RFC-008 §4.2): sem taxa padrão própria (inativa a de A),
        # o fallback FINAL passa a ser a GLOBAL (2,50%)
        self._run(
            "UPDATE commission_rules SET status = 'inativo' WHERE employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_A}') "
            "AND product_id IS NULL AND category_id IS NULL AND status = 'ativo'",
            guc="ADMINISTRADOR")
        # restaura a taxa padrão de A MESMO se uma asserção falhar (não contamina
        # o teste de duplicidade do RFC-007, que conta 1 regra ATIVA de A)
        self.addCleanup(self._run,
            "UPDATE commission_rules SET status = 'ativo' WHERE employee_id = "
            f"(SELECT id FROM employees WHERE cpf = '{CPF_A}') "
            "AND product_id IS NULL AND category_id IS NULL AND rate_percent = 1.50",
            guc="ADMINISTRADOR")
        self.assertEqual(self._resolve_rate(CPF_A, "ACES"), 2.50)
        # inativar a taxa GLOBAL → sem fallback: ACES deixa de gerar comissão (0)
        self._run(
            "UPDATE commission_global_rules SET status = 'inativo' "
            "WHERE status = 'ativo'", guc="ADMINISTRADOR")
        # inativação lógica: a regra global continua gravada (histórico — RFC-008
        # §8 decisão 3; sem exclusão física)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_global_rules "
            "WHERE status = 'inativo' AND rate_percent = 2.50"), 1)
        self.assertEqual(self._resolve_rate(CPF_A, "ACES"), 0)
        # nova regra ATIVA com a NOVA vigência → permitida (versionamento)
        self._run(
            "INSERT INTO commission_global_rules (rate_percent, valid_from) "
            "VALUES (7.00, '2026-09-01')", guc="ADMINISTRADOR")
        # limpa a regra 7% MESMO se uma asserção falhar (LIFO: roda antes da
        # restauração da taxa padrão de A — linhas distintas, ordem não importa)
        self.addCleanup(self._run,
            "UPDATE commission_global_rules SET status = 'inativo' "
            "WHERE rate_percent = 7.00 AND status = 'ativo'",
            guc="ADMINISTRADOR")
        # a taxa é da DATA DA VENDA (RFC-002 §5 regra 3): antes da nova vigência
        # o fallback segue zerado; dentro dela a nova taxa global resolve (7%)
        self.assertEqual(self._resolve_rate(CPF_A, "ACES"), 0)
        self.assertEqual(self._resolve_rate(CPF_A, "ACES", "2026-09-15"), 7.00)

    # ------------------------------------------------------------------
    # 5. Equações no banco (017)
    # ------------------------------------------------------------------
    def test_item_total_equacao(self):
        """pos_sale_items: item_total deve ser quantity × unit_price."""
        self._venda_exemplo()
        self._fails(
            "INSERT INTO pos_sale_items (sale_id, product_id, quantity, unit_price, "
            "item_total) SELECT s.id, p.id, 1, 100.00, 1500.00 "
            "FROM pos_sales s, products p WHERE s.code = 'V-0001' AND p.code = 'ACES'",
            guc="OPERADOR", err=psycopg2.errors.CheckViolation)

    def test_commission_value_equacao(self):
        """commission_details: commission_value deve ser item_total × taxa/100."""
        self._venda_exemplo()
        self._fails(
            "INSERT INTO commission_details (sale_id, sale_item_id, employee_id, "
            "product_id, rate_source, rate_percent, commission_value) "
            "SELECT s.id, i.id, s.employee_id, i.product_id, 'categoria', 3.00, 999.00 "
            "FROM pos_sales s JOIN pos_sale_items i ON i.sale_id = s.id "
            "JOIN products p ON p.id = i.product_id WHERE p.code = 'PLANO'",
            guc="OPERADOR", msg="não confere")

    # ------------------------------------------------------------------
    # 6. Consistência do detalhe (017)
    # ------------------------------------------------------------------
    def test_detalhe_vendedor_da_venda(self):
        """commission_details.employee_id deve ser o vendedor da venda."""
        self._venda_exemplo()
        self._fails(
            "INSERT INTO commission_details (sale_id, sale_item_id, employee_id, "
            "product_id, rate_source, rate_percent, commission_value) "
            f"SELECT s.id, i.id, {self._emp_id(CPF_B)}, i.product_id, 'produto', 5.00, 100.00 "
            "FROM pos_sales s JOIN pos_sale_items i ON i.sale_id = s.id "
            "JOIN products p ON p.id = i.product_id WHERE p.code = 'CEL-X'",
            guc="OPERADOR", msg="difere do vendedor da venda")

    def test_detalhe_item_da_venda(self):
        """commission_details.sale_item_id deve pertencer à venda informada."""
        self._venda_exemplo()
        self._run(
            "INSERT INTO pos_sales (code, employee_id, sale_date, total_value) "
            f"SELECT 'V-0002', id, '2026-08-27', 10.00 FROM employees WHERE cpf = '{CPF_A}' "
            "ON CONFLICT (code) DO NOTHING", guc="OPERADOR")
        self._fails(
            "INSERT INTO commission_details (sale_id, sale_item_id, employee_id, "
            "product_id, rate_source, rate_percent, commission_value) "
            "SELECT s2.id, i.id, s1.employee_id, i.product_id, 'produto', 5.00, 100.00 "
            "FROM pos_sales s1 JOIN pos_sale_items i ON i.sale_id = s1.id "
            "JOIN pos_sales s2 ON s2.code = 'V-0002' "
            "JOIN products p ON p.id = i.product_id WHERE p.code = 'CEL-X'",
            guc="OPERADOR", msg="não pertence")

    def test_detalhe_duplicado_por_item(self):
        """UNIQUE (sale_item_id): um detalhe por item apurado."""
        self._venda_exemplo()
        self._run(
            "INSERT INTO commission_details (sale_id, sale_item_id, employee_id, "
            "product_id, rate_source, rate_percent, commission_value) "
            "SELECT s.id, i.id, s.employee_id, i.product_id, 'produto', 5.00, 100.00 "
            "FROM pos_sales s JOIN pos_sale_items i ON i.sale_id = s.id "
            "JOIN products p ON p.id = i.product_id WHERE p.code = 'CEL-X' "
            "ON CONFLICT (sale_item_id) DO NOTHING", guc="OPERADOR")
        self._fails(
            "INSERT INTO commission_details (sale_id, sale_item_id, employee_id, "
            "product_id, rate_source, rate_percent, commission_value) "
            "SELECT s.id, i.id, s.employee_id, i.product_id, 'padrao', 1.50, 30.00 "
            "FROM pos_sales s JOIN pos_sale_items i ON i.sale_id = s.id "
            "JOIN products p ON p.id = i.product_id WHERE p.code = 'CEL-X'",
            guc="OPERADOR", err=psycopg2.errors.UniqueViolation, msg="uq_detail_per_item")

    def test_detalhe_rate_source_coerente(self):
        """rate_source deve ser coerente com o alvo da regra (RFC-005 §5)."""
        self._setup_completo()
        # regra de PRODUTO (da CEL-X) declarada como 'padrao' → rejeitada
        self._fails(
            "INSERT INTO commission_details (sale_id, sale_item_id, employee_id, "
            "product_id, rate_source, rule_id, rate_percent, commission_value) "
            "SELECT s.id, i.id, s.employee_id, i.product_id, 'padrao', "
            "(SELECT id FROM commission_rules WHERE product_id = i.product_id "
            "LIMIT 1), 5.00, 100.00 "
            "FROM pos_sales s JOIN pos_sale_items i ON i.sale_id = s.id "
            "JOIN products p ON p.id = i.product_id WHERE p.code = 'CEL-X'",
            guc="OPERADOR", msg="incompatível")

    # ------------------------------------------------------------------
    # 7. Apuração consolidada + estorno por status (RFC-005 §3.4/§5)
    # ------------------------------------------------------------------
    def test_apuracao_consolidada(self):
        """Soma dos detalhes de vendas abertas com itens ativos = 116,50 (RFC-005 §3.4/§6)."""
        self._setup_completo()
        self.assertEqual(self._scalar(
            "SELECT SUM(cd.commission_value) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id "
            "JOIN pos_sale_items i ON i.id = cd.sale_item_id "
            "WHERE s.status = 'aberta' AND i.status = 'ativo'"),
            116.50)

    def test_devolucao_parcial_por_status_do_item(self):
        """017: devolução parcial por status do item — sai da apuração sem
        negativos, detalhe preservado (RFC-005 §3.2/§5 regra 2)."""
        self._setup_completo()
        # devolve o item PLANO da venda V-0001 (devolução PARCIAL — venda segue aberta)
        self._run(
            "UPDATE pos_sale_items SET status = 'devolvido' WHERE id = "
            "(SELECT i.id FROM pos_sale_items i JOIN products p ON p.id = i.product_id "
            "JOIN pos_sales s ON s.id = i.sale_id WHERE p.code = 'PLANO' "
            "AND s.code = 'V-0001' LIMIT 1)", guc="OPERADOR")
        # restaura o status MESMO se uma asserção falhar (não contamina os demais)
        self.addCleanup(self._run,
            "UPDATE pos_sale_items SET status = 'ativo' WHERE id = "
            "(SELECT i.id FROM pos_sale_items i JOIN products p ON p.id = i.product_id "
            "JOIN pos_sales s ON s.id = i.sale_id WHERE p.code = 'PLANO' "
            "AND s.code = 'V-0001' LIMIT 1)", guc="OPERADOR")
        # apuração consolidada = CEL-X (100,00) + ACES (1,50) = 101,50 (PLANO sai)
        self.assertEqual(self._scalar(
            "SELECT SUM(cd.commission_value) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id "
            "JOIN pos_sale_items i ON i.id = cd.sale_item_id "
            "WHERE s.status = 'aberta' AND i.status = 'ativo'"), 101.50)
        # o detalhe do item devolvido permanece (auditoria preservada, sem negativos)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_details cd "
            "JOIN pos_sale_items i ON i.id = cd.sale_item_id "
            "WHERE i.status = 'devolvido'"), 1)
        # item devolvido NÃO pode ser apurado depois (fail-closed, RFC-005 §5 regra 2)
        self._fails(
            "INSERT INTO commission_details (sale_id, sale_item_id, employee_id, "
            "product_id, rate_source, rate_percent, commission_value) "
            "SELECT s.id, i.id, s.employee_id, i.product_id, 'categoria', 3.00, 15.00 "
            "FROM pos_sales s JOIN pos_sale_items i ON i.sale_id = s.id "
            "JOIN products p ON p.id = i.product_id WHERE p.code = 'PLANO' "
            "AND s.code = 'V-0001'", guc="OPERADOR", msg="Item devolvido")
        # colunas de negócio do item continuam congeladas (regra 4)
        self._fails(
            "UPDATE pos_sale_items SET quantity = 2 WHERE id = "
            "(SELECT i.id FROM pos_sale_items i JOIN products p ON p.id = i.product_id "
            "JOIN pos_sales s ON s.id = i.sale_id WHERE p.code = 'PLANO' "
            "AND s.code = 'V-0001' LIMIT 1)",
            guc="OPERADOR", msg="Item já apurado")

    def test_estorno_por_status(self):
        """Venda cancelada sai da apuração — sem negativos, detalhe preservado."""
        self._setup_completo()
        # fail-closed: alterar status (estorno) também exige lancar_eventos
        self._fails("UPDATE pos_sales SET status = 'cancelada' WHERE code = 'V-0001'",
                    msg="exige a ação lancar_eventos")
        self._run("UPDATE pos_sales SET status = 'cancelada' WHERE code = 'V-0001'",
                  guc="OPERADOR")
        # restaura MESMO se uma asserção falhar no meio (não contamina os demais)
        self.addCleanup(self._run,
                        "UPDATE pos_sales SET status = 'aberta' WHERE code = 'V-0001'",
                        guc="OPERADOR")
        # apuração vazia (cancelada não conta)
        self.assertEqual(self._scalar(
            "SELECT COALESCE(SUM(commission_value), 0) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id WHERE s.status = 'aberta'"), 0)
        # o detalhe permanece (auditoria preservada)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id WHERE s.code = 'V-0001'"), 3)

    # ------------------------------------------------------------------
    # 7.1 Relatório de comissões por venda de origem (RFC-015 §2.1)
    # ------------------------------------------------------------------
    def test_relatorio_comissoes_por_venda_de_origem(self):
        """RFC-015 §2.1: relatório por venda de origem sobre commission_details —
        modo conferência totaliza o evento 7 (elegíveis); estornos/devoluções
        saem da conferência e permanecem no modo auditoria."""
        self._setup_completo()
        # modo conferência (default): vendas abertas + itens ativos → 3 linhas, 116,50
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id "
            "JOIN pos_sale_items i ON i.id = cd.sale_item_id "
            "WHERE DATE_TRUNC('month', s.sale_date)::date = '2026-08-01' "
            "AND s.status = 'aberta' AND i.status = 'ativo'"), 3)
        self.assertEqual(self._scalar(
            "SELECT SUM(cd.commission_value) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id "
            "JOIN pos_sale_items i ON i.id = cd.sale_item_id "
            "WHERE DATE_TRUNC('month', s.sale_date)::date = '2026-08-01' "
            "AND s.status = 'aberta' AND i.status = 'ativo'"), 116.50)
        # as 3 origens da regra (produto/categoria/padrao) aparecem no detalhe
        self.assertEqual(self._scalar(
            "SELECT count(DISTINCT cd.rate_source) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id "
            "JOIN pos_sale_items i ON i.id = cd.sale_item_id "
            "WHERE DATE_TRUNC('month', s.sale_date)::date = '2026-08-01' "
            "AND s.status = 'aberta' AND i.status = 'ativo'"), 3)
        # devolução parcial: sai do modo conferência, permanece no modo auditoria
        self._run(
            "UPDATE pos_sale_items SET status = 'devolvido' WHERE id = "
            "(SELECT i.id FROM pos_sale_items i JOIN products p ON p.id = i.product_id "
            "JOIN pos_sales s ON s.id = i.sale_id WHERE p.code = 'PLANO' "
            "AND s.code = 'V-0001' LIMIT 1)", guc="OPERADOR")
        self.addCleanup(self._run,
            "UPDATE pos_sale_items SET status = 'ativo' WHERE id = "
            "(SELECT i.id FROM pos_sale_items i JOIN products p ON p.id = i.product_id "
            "JOIN pos_sales s ON s.id = i.sale_id WHERE p.code = 'PLANO' "
            "AND s.code = 'V-0001' LIMIT 1)", guc="OPERADOR")
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id "
            "JOIN pos_sale_items i ON i.id = cd.sale_item_id "
            "WHERE DATE_TRUNC('month', s.sale_date)::date = '2026-08-01' "
            "AND s.status = 'aberta' AND i.status = 'ativo'"), 2)
        # modo auditoria: todos os detalhes da competência (inclui o devolvido)
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id "
            "WHERE DATE_TRUNC('month', s.sale_date)::date = '2026-08-01'"), 3)

    # ------------------------------------------------------------------
    # 7.2 Congelamento do apurado — commission_settlements (RFC-005 §3.5)
    # ------------------------------------------------------------------
    def test_settlement_congela_apurado(self):
        """017: fechamento grava commission_settlements (funcionário × competência)
        e CONGELA o valor — idempotente e imune a devolução posterior."""
        self._setup_completo()
        # fechamento da competência 2026-08 (valor consolidado = 116,50)
        self._run(
            "INSERT INTO commission_settlements (employee_id, competence, total_value) "
            "SELECT cd.employee_id, DATE_TRUNC('month', s.sale_date)::date, "
            "SUM(cd.commission_value) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id "
            "JOIN pos_sale_items i ON i.id = cd.sale_item_id "
            "WHERE s.status = 'aberta' AND i.status = 'ativo' "
            "GROUP BY cd.employee_id, DATE_TRUNC('month', s.sale_date)::date "
            "ON CONFLICT (employee_id, competence) WHERE status = 'fechado' DO NOTHING",
            guc="OPERADOR")
        # valor congelado = 116,50
        self.assertEqual(self._scalar(
            f"SELECT total_value FROM commission_settlements WHERE competence = "
            f"'2026-08-01' AND employee_id = (SELECT id FROM employees WHERE cpf = '{CPF_A}')"), 116.50)
        # segundo fechamento NÃO duplica nem sobrescreve (idempotente)
        self._run(
            "INSERT INTO commission_settlements (employee_id, competence, total_value) "
            "SELECT cd.employee_id, DATE_TRUNC('month', s.sale_date)::date, "
            "SUM(cd.commission_value) FROM commission_details cd "
            "JOIN pos_sales s ON s.id = cd.sale_id "
            "JOIN pos_sale_items i ON i.id = cd.sale_item_id "
            "WHERE s.status = 'aberta' AND i.status = 'ativo' "
            "GROUP BY cd.employee_id, DATE_TRUNC('month', s.sale_date)::date "
            "ON CONFLICT (employee_id, competence) WHERE status = 'fechado' DO NOTHING",
            guc="OPERADOR")
        self.assertEqual(self._scalar(
            "SELECT count(*) FROM commission_settlements WHERE competence = "
            "'2026-08-01' AND status = 'fechado'"), 1)
        # devolução APÓS o fechamento NÃO altera o valor congelado
        self._run(
            "UPDATE pos_sale_items SET status = 'devolvido' WHERE id = "
            "(SELECT i.id FROM pos_sale_items i JOIN products p ON p.id = i.product_id "
            "JOIN pos_sales s ON s.id = i.sale_id WHERE p.code = 'PLANO' "
            "AND s.code = 'V-0001' LIMIT 1)", guc="OPERADOR")
        self.addCleanup(self._run,
            "UPDATE pos_sale_items SET status = 'ativo' WHERE id = "
            "(SELECT i.id FROM pos_sale_items i JOIN products p ON p.id = i.product_id "
            "JOIN pos_sales s ON s.id = i.sale_id WHERE p.code = 'PLANO' "
            "AND s.code = 'V-0001' LIMIT 1)", guc="OPERADOR")
        self.assertEqual(self._scalar(
            f"SELECT total_value FROM commission_settlements WHERE competence = "
            f"'2026-08-01' AND employee_id = (SELECT id FROM employees WHERE cpf = '{CPF_A}')"), 116.50)

    def test_settlement_imutavel_e_estorno_por_status(self):
        """017: settlement congelado — colunas de negócio imutáveis, status
        (estorno) alterável e regeração liberada; sem exclusão física."""
        self._setup_completo()
        self._run(
            "INSERT INTO commission_settlements (employee_id, competence, total_value) "
            f"SELECT id, '2026-08-01', 116.50 FROM employees WHERE cpf = '{CPF_A}' "
            "ON CONFLICT (employee_id, competence) WHERE status = 'fechado' DO NOTHING",
            guc="OPERADOR")
        sid = self._scalar(
            "SELECT id FROM commission_settlements WHERE competence = '2026-08-01' "
            f"AND employee_id = (SELECT id FROM employees WHERE cpf = '{CPF_A}')")
        self.assertIsNotNone(sid)
        # colunas de negócio congeladas (fail-closed mesmo com permissão)
        self._fails(f"UPDATE commission_settlements SET total_value = 999.00 WHERE id = {sid}",
                    guc="OPERADOR", msg="Settlement fechado")
        self._fails(f"UPDATE commission_settlements SET competence = '2026-09-01' WHERE id = {sid}",
                    guc="OPERADOR", msg="Settlement fechado")
        # status alterável (estorno) → libera a regeração
        self._run(f"UPDATE commission_settlements SET status = 'estornado' WHERE id = {sid}",
                  guc="OPERADOR")
        self.assertEqual(self._scalar(f"SELECT status FROM commission_settlements WHERE id = {sid}"),
                         "estornado")
        # regeração permitida (índice único parcial só bloqueia 'fechado')
        self._run(
            "INSERT INTO commission_settlements (employee_id, competence, total_value) "
            f"SELECT id, '2026-08-01', 116.50 FROM employees WHERE cpf = '{CPF_A}'",
            guc="OPERADOR")
        # sem exclusão física
        self._fails(f"DELETE FROM commission_settlements WHERE id = {sid}",
                    guc="ADMINISTRADOR", msg="proibida")

    def test_settlement_permissao_lancar_eventos(self):
        """017: fechar a competência (gravar settlement) exige lancar_eventos — fail-closed."""
        self._setup_completo()
        self._fails(
            "INSERT INTO commission_settlements (employee_id, competence, total_value) "
            f"SELECT id, '2026-08-01', 10.00 FROM employees WHERE cpf = '{CPF_A}'",
            msg="exige a ação lancar_eventos")
        # semear linha própria (autossuficiente — não depende da ordem dos testes)
        self._run(
            "INSERT INTO commission_settlements (employee_id, competence, total_value) "
            f"SELECT id, '2026-08-01', 10.00 FROM employees WHERE cpf = '{CPF_A}' "
            "ON CONFLICT (employee_id, competence) WHERE status = 'fechado' DO NOTHING",
            guc="OPERADOR")
        # estorno (UPDATE) também exige lancar_eventos — fail-closed
        self._fails(
            "UPDATE commission_settlements SET status = 'estornado' WHERE id = "
            f"(SELECT id FROM commission_settlements WHERE competence = '2026-08-01' "
            f"AND employee_id = (SELECT id FROM employees WHERE cpf = '{CPF_A}') LIMIT 1)",
            msg="exige a ação lancar_eventos")

    # ------------------------------------------------------------------
    # 8. Imutabilidade e congelamento (RFC-005 §5 regras 3–4)
    # ------------------------------------------------------------------
    def test_detalhe_imutavel(self):
        """commission_details sem UPDATE/DELETE/TRUNCATE (mesmo p/ ADMINISTRADOR)."""
        self._setup_completo()
        # ID resolvido por subselect — nunca ID fixo (cluster compartilhado)
        did = self._scalar("SELECT id FROM commission_details ORDER BY id LIMIT 1")
        self.assertIsNotNone(did)
        self._fails(f"UPDATE commission_details SET rate_percent = 9.0 WHERE id = {did}",
                    guc="OPERADOR", msg="imutável")
        self._fails(f"DELETE FROM commission_details WHERE id = {did}",
                    guc="ADMINISTRADOR", msg="proibida")
        self._fails("TRUNCATE commission_details", msg="proibida")

    def test_item_congelado_apos_apuracao(self):
        """pos_sale_items não se edita após a apuração do item."""
        self._setup_completo()
        self._fails(
            "UPDATE pos_sale_items SET quantity = 2 WHERE id = "
            f"(SELECT i.id FROM pos_sale_items i JOIN products p ON p.id = i.product_id "
            "JOIN pos_sales s ON s.id = i.sale_id WHERE p.code = 'CEL-X' "
            "AND s.code = 'V-0001' LIMIT 1)",
            guc="OPERADOR", msg="Item já apurado")

    def test_cabecalho_congelado_apos_apuracao(self):
        """pos_sales: colunas de negócio congeladas; só o status é alterável."""
        self._setup_completo()
        self._fails("UPDATE pos_sales SET sale_date = '2026-09-01' WHERE code = 'V-0001'",
                    guc="OPERADOR", msg="Venda já apurada")
        self._fails("UPDATE pos_sales SET total_value = 999.00 WHERE code = 'V-0001'",
                    guc="OPERADOR", msg="Venda já apurada")
        # status continua alterável (estorno) — restaura com addCleanup para
        # não contaminar os demais testes mesmo se uma asserção falhar
        self._run("UPDATE pos_sales SET status = 'estornada' WHERE code = 'V-0001'",
                  guc="OPERADOR")
        self.addCleanup(self._run,
                        "UPDATE pos_sales SET status = 'aberta' WHERE code = 'V-0001'",
                        guc="OPERADOR")

    # ------------------------------------------------------------------
    # 9. Sem exclusão física (padrão RFC-008 decisão 4)
    # ------------------------------------------------------------------
    def test_sem_exclusao_fisica(self):
        """DELETE/TRUNCATE de vendas/itens/categorias/regras bloqueados."""
        self._setup_completo()
        self._fails("DELETE FROM product_categories WHERE code = 'ELETRO'",
                    guc="ADMINISTRADOR", msg="proibida")
        self._fails("DELETE FROM pos_sales WHERE code = 'V-0001'",
                    guc="ADMINISTRADOR", msg="proibida")
        # TRUNCATE em tabelas referenciadas por FK: o próprio Postgres bloqueia
        # ANTES da trigger (FeatureNotSupported — cannot truncate a table
        # referenced in a foreign key constraint). Qualquer bloqueio vale como
        # sem exclusão física; a trigger só é alcançada em commission_details
        # (testado em test_detalhe_imutavel).
        for tbl in ("pos_sale_items", "pos_sales"):
            self._fails(f"TRUNCATE {tbl}",
                        err=(psycopg2.errors.FeatureNotSupported,
                             psycopg2.errors.RaiseException))


if __name__ == "__main__":
    unittest.main(verbosity=2)
