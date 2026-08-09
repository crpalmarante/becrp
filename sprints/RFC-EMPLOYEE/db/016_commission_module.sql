-- ============================================================================
-- db/016_commission_module.sql
-- RFC-COMISSION/RFC-003 — Modelo de Dados do Módulo de Comissões (v1.1.0 · Draft)
--           RFC-COMISSION/RFC-002 — Comissões no PDV (§2/§3 — produto, categoria e taxa)
-- ----------------------------------------------------------------------------
-- Cria o modelo de dados do módulo de comissões do PDV:
--   product_categories  (RFC-COMISSION/RFC-002 §3.2) — catálogo de categorias
--   products            (RFC-COMISSION/RFC-002 §2)   — catálogo de produtos do PDV
--   commission_rules    (RFC-COMISSION/RFC-002 §3)   — regras de comissão por
--                                                       funcionário × (produto |
--                                                       categoria | padrão) × taxa
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- Pré-requisitos:
--   db/002 (employees)        — employees(id) + set_updated_at() + prevent_hard_delete()
--   db/011 (permissions)      — f_has_permission_guc() (RFC-009 §3.1)
-- Ordem: 002 → 009 → 011 → ... → 016.
--
-- AUTORIZAÇÃO POR AÇÃO (RFC-009 §3.1 via db/011 — autoridade única):
--   Manter categorias, produtos e regras de comissão é ATO DE CADASTRO →
--   f_has_permission_guc('manter_cadastros'). O GUC de sessão é obrigatório
--   (fail-closed):
--     SET app.actor_roles = 'OPERADOR';
--
-- PRECEDÊNCIA (RFC-COMISSION/RFC-002 §3.1): produto → categoria → taxa padrão.
--   A regra mais específica vence: regra de PRODUTO sobrepõe a da CATEGORIA,
--   que sobrepõe a taxa PADRÃO do funcionário (product_id/category_id NULL).
--   A resolução é feita pela consulta da aplicação (exemplo no RFC-003 §5);
--   os índices únicos parciais garantem UMA regra ATIVA por (funcionário ×
--   alvo), sem conflito entre os três níveis; regras INATIVAS ficam como
--   histórico (versionamento por vigência — RFC-002 §5 regra 3).
--
-- INVARIANTES PROTEGIDAS POR TRIGGER:
--   (1) Escrita exige a ação manter_cadastros (RFC-009 §3.1 via db/011).
--   (2) Uma regra não pode mirar produto E categoria ao mesmo tempo
--       (CHECK ck_rule_target_exclusive) — ou produto, ou categoria, ou padrão.
--   (3) Vigência válida (valid_until >= valid_from, quando ambos informados).
--   (4) Nenhuma exclusão física (padrão RFC-008 decisão 4 — inativação lógica).
--
-- Fora do escopo (migrations de acompanhamento): a apuração das vendas do PDV
-- (venda × item × vendedor) e o detalhamento da comissão no holerite (RFC-007)
-- — o apurado entra na folha pelo evento 7 (Comissão/Vendas, RFC-004), e a
-- tabela de vendas pertence ao módulo comercial/PDV.
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/016_commission_module.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. PRODUCT_CATEGORIES — RFC-COMISSION/RFC-002 §3.2 (catálogo de categorias)
--    Agrupamento de produtos afins que compartilham uma mesma taxa de comissão.
-- ============================================================================
CREATE TABLE product_categories (
    id          BIGSERIAL PRIMARY KEY,
    code        TEXT        NOT NULL UNIQUE,        -- código (identificador único da categoria)
    description TEXT        NOT NULL,               -- nome (ex.: "Eletrônicos", "Serviços", "Acessórios")
    status      TEXT        NOT NULL DEFAULT 'ativo'
                CHECK (status IN ('ativo', 'inativo')),  -- situação: ativa / inativa (inativação lógica)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  product_categories IS 'RFC-COMISSION/RFC-002 §3.2 — catálogo de categorias de produto; grupo de produtos que compartilha taxa de comissão';
COMMENT ON COLUMN product_categories.status IS 'Situação: ativo / inativo (inativação lógica — padrão RFC-008 decisão 4)';

CREATE TRIGGER trg_product_categories_updated_at
    BEFORE UPDATE ON product_categories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ============================================================================
-- 2. PRODUCTS — RFC-COMISSION/RFC-002 §2 (catálogo de produtos do PDV)
--    Item do catálogo de vendas que pode ter comissão própria. TODO produto
--    pertence a UMA categoria (regra RFC-002 §3.2) — herda a taxa da categoria
--    salvo regra de produto específico (precedência §3.1).
-- ============================================================================
CREATE TABLE products (
    id           BIGSERIAL PRIMARY KEY,
    code         TEXT         NOT NULL UNIQUE,      -- código do produto
    description  TEXT         NOT NULL,             -- descrição (ex.: "Celular Modelo X")
    category_id  BIGINT       NOT NULL REFERENCES product_categories (id) ON DELETE RESTRICT,
                                                    -- categoria do produto (RFC-002 §3.2 regra 1)
    status       TEXT         NOT NULL DEFAULT 'ativo'
                 CHECK (status IN ('ativo', 'inativo')),  -- situação: ativo / inativo
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE  products IS 'RFC-COMISSION/RFC-002 §2 — catálogo de produtos do PDV; cada produto pertence a uma categoria e herda a taxa da categoria salvo regra específica';
COMMENT ON COLUMN products.category_id IS 'Categoria do produto (product_categories) — todo produto pertence a uma categoria (RFC-002 §3.2 regra 1)';
COMMENT ON COLUMN products.status IS 'Situação: ativo / inativo (inativação lógica — padrão RFC-008 decisão 4)';

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ============================================================================
-- 3. COMMISSION_RULES — RFC-COMISSION/RFC-002 §3 (regras de comissão)
--    Combinação funcionário × alvo × taxa que define o percentual aplicado.
--    Alvo: product_id (produto específico) OU category_id (categoria) OU nenhum
--    (taxa padrão do funcionário — fallback). Precedência §3.1 resolvida na
--    consulta da aplicação; os índices únicos parciais impedem regras duplicadas
--    no mesmo nível (funcionário × produto | funcionário × categoria | padrão).
-- ============================================================================
CREATE TABLE commission_rules (
    id           BIGSERIAL PRIMARY KEY,
    employee_id  BIGINT        NOT NULL REFERENCES employees (id) ON DELETE RESTRICT,
                                                    -- vendedor que recebe a comissão (RFC-002 Folha)
    product_id   BIGINT        REFERENCES products (id) ON DELETE RESTRICT,
                                                    -- produto específico (regra por produto)
    category_id  BIGINT        REFERENCES product_categories (id) ON DELETE RESTRICT,
                                                    -- categoria (regra por categoria)
    rate_percent NUMERIC(5,2)  NOT NULL
                 CHECK (rate_percent >= 0 AND rate_percent <= 100),
                                                    -- taxa percentual aplicada sobre o valor de venda
    valid_from   DATE,                              -- vigência inicial (RFC-002 §5 regra 3)
    valid_until  DATE,                              -- vigência final (opcional)
    status       TEXT          NOT NULL DEFAULT 'ativo'
                 CHECK (status IN ('ativo', 'inativo')),  -- situação: ativa / inativa
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT ck_rule_target_exclusive CHECK (
        NOT (product_id IS NOT NULL AND category_id IS NOT NULL)
    ),                                              -- RFC-002 §3: ou produto, ou categoria,
                                                    -- ou nenhum (taxa padrão) — nunca os dois
    CONSTRAINT ck_rule_validity CHECK (
        valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from
    )                                               -- vigência coerente (padrão RFC-004)
);

COMMENT ON TABLE  commission_rules IS 'RFC-COMISSION/RFC-002 §3 — regra de comissão: funcionário × (produto | categoria | padrão) × taxa percentual; precedência produto → categoria → padrão (RFC-002 §3.1) resolvida na consulta';
COMMENT ON COLUMN commission_rules.employee_id IS 'Vendedor que recebe a comissão (employees — RFC-002 Folha)';
COMMENT ON COLUMN commission_rules.product_id IS 'Produto específico coberto pela regra (precedência máxima)';
COMMENT ON COLUMN commission_rules.category_id IS 'Categoria coberta pela regra (precedência média) — taxa aplicada a todos os produtos da categoria';
COMMENT ON COLUMN commission_rules.rate_percent IS 'Taxa percentual de comissão (0–100), aplicada sobre o valor de venda (ex.: 2,50 = 2,5%)';
COMMENT ON COLUMN commission_rules.valid_from IS 'Vigência inicial — a venda usa a regra vigente na data da venda (RFC-002 §5 regra 3)';
COMMENT ON COLUMN commission_rules.status IS 'Situação: ativa / inativa (inativação lógica — padrão RFC-008 decisão 4)';

CREATE TRIGGER trg_commission_rules_updated_at
    BEFORE UPDATE ON commission_rules
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ============================================================================
-- 3.1 Índices únicos parciais — UMA regra ATIVA por (funcionário × alvo) em
--     cada nível da precedência (RFC-002 §3.1), sem conflito entre os níveis:
--       (employee_id, product_id)  — regra de produto: uma ATIVA por funcionário+produto
--       (employee_id, category_id) — regra de categoria: uma ATIVA por funcionário+categoria
--       (employee_id)              — taxa padrão: uma ATIVA por funcionário
--     O filtro `status = 'ativo'` permite o VERSIONAMENTO por vigência
--     (RFC-002 §5 regra 3): para mudar a taxa, inativa-se a regra atual
--     (histórico preservado — nunca exclusão física) e cria-se a nova regra
--     com a nova vigência. A consulta de resolução (RFC-003 §5) usa apenas
--     regras ativas, coerente com "a taxa da data da venda".
-- ============================================================================
CREATE UNIQUE INDEX uq_commission_rules_product
    ON commission_rules (employee_id, product_id)
    WHERE product_id IS NOT NULL AND status = 'ativo';

CREATE UNIQUE INDEX uq_commission_rules_category
    ON commission_rules (employee_id, category_id)
    WHERE category_id IS NOT NULL AND status = 'ativo';

CREATE UNIQUE INDEX uq_commission_rules_default
    ON commission_rules (employee_id)
    WHERE product_id IS NULL AND category_id IS NULL AND status = 'ativo';

-- ============================================================================
-- 4. TRIGGERS DE ENFORCEMENT
--     (a) escrita (INSERT/UPDATE) → ação 'manter_cadastros' (RFC-009 §3.1 via
--         db/011; f_has_permission_guc é fail-closed)
--     (b) sem exclusão física (DELETE/TRUNCATE) — padrão RFC-008 decisão 4
--         (reusa prevent_hard_delete da db/002)
-- ============================================================================
CREATE OR REPLACE FUNCTION enforce_commission_write_permission ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- RFC-009 §3.1 via db/011: manter categorias/produtos/regras é ato de
    -- cadastro (manter_cadastros). Fail-closed: GUC ausente/vazio → FALSE.
    IF NOT f_has_permission_guc('manter_cadastros') THEN
        RAISE EXCEPTION 'Manter cadastros de comissão exige a ação manter_cadastros (RFC-009 §3.1, via db/011); app.actor_roles = %',
            COALESCE(current_setting('app.actor_roles', true), '<não definido>');
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_product_categories_write_perm
    BEFORE INSERT OR UPDATE ON product_categories
    FOR EACH ROW EXECUTE FUNCTION enforce_commission_write_permission ();

CREATE TRIGGER trg_products_write_perm
    BEFORE INSERT OR UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION enforce_commission_write_permission ();

CREATE TRIGGER trg_commission_rules_write_perm
    BEFORE INSERT OR UPDATE ON commission_rules
    FOR EACH ROW EXECUTE FUNCTION enforce_commission_write_permission ();

-- (b) sem exclusão física — categorias/produtos/regras inativam, nunca apagam
--     (padrão RFC-008 decisão 4; função reutilizada da db/002). Cobre DELETE e
--     TRUNCATE (triggers de linha NÃO disparam em TRUNCATE — por isso os
--     statement-level abaixo).
CREATE TRIGGER trg_product_categories_no_delete
    BEFORE DELETE ON product_categories
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete ();

CREATE TRIGGER trg_product_categories_no_truncate
    BEFORE TRUNCATE ON product_categories
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_hard_delete ();

CREATE TRIGGER trg_products_no_delete
    BEFORE DELETE ON products
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete ();

CREATE TRIGGER trg_products_no_truncate
    BEFORE TRUNCATE ON products
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_hard_delete ();

CREATE TRIGGER trg_commission_rules_no_delete
    BEFORE DELETE ON commission_rules
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete ();

CREATE TRIGGER trg_commission_rules_no_truncate
    BEFORE TRUNCATE ON commission_rules
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_hard_delete ();

REVOKE DELETE, TRUNCATE ON product_categories, products, commission_rules FROM PUBLIC;

-- ============================================================================
-- Índices de consulta
-- ============================================================================
CREATE INDEX idx_products_category      ON products (category_id);
CREATE INDEX idx_products_status        ON products (status);
CREATE INDEX idx_product_categories_st  ON product_categories (status);
CREATE INDEX idx_commission_rules_emp   ON commission_rules (employee_id);
CREATE INDEX idx_commission_rules_prod  ON commission_rules (product_id);
CREATE INDEX idx_commission_rules_cat   ON commission_rules (category_id);
CREATE INDEX idx_commission_rules_status ON commission_rules (status);

COMMIT;
