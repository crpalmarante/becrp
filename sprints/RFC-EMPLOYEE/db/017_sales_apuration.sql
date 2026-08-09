-- ============================================================================
-- db/017_sales_apuration.sql
-- RFC-COMISSION/RFC-005 — Apuração das Vendas do PDV e Comissão por Venda
--                        (v1.2.0 · Draft em revisão)
-- ----------------------------------------------------------------------------
-- Cria a APURAÇÃO das vendas do PDV e o DETALHAMENTO da comissão por venda:
--   pos_sales          (RFC-COMISSION/RFC-005 §3.1) — cabeçalho da venda:
--                        vendedor (employee_id), data, total e status
--   pos_sale_items     (RFC-COMISSION/RFC-005 §3.2) — itens da venda:
--                        produto, quantidade, preço e item_total
--   commission_details (RFC-COMISSION/RFC-005 §3.3) — detalhe da comissão
--                        POR ITEM APURADO: taxa resolvida pela precedência
--                        (produto → categoria → taxa padrão), origem da regra
--                        (rate_source) e valor — fecha a rastreabilidade da
--                        venda ao holerite (RFC-COMISSION/RFC-002 §5 regra 5)
--   commission_settlements (RFC-COMISSION/RFC-005 §3.5) — CONGELAMENTO do
--                        apurado por (funcionário × competência): o valor
--                        fechado que alimenta o evento 7 na folha
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- Pré-requisitos:
--   db/002 (employees)  — employees(id) + set_updated_at() + prevent_hard_delete()
--   db/011 (permissions)— f_has_permission_guc() (RFC-009 §3.1)
--   db/016 (commission module) — products/product_categories/commission_rules
-- Ordem: 002 → 009 → 011 → ... → 016 → 017.
--
-- AUTORIZAÇÃO POR AÇÃO (RFC-009 §3.1 via db/011 — autoridade única):
--   Registrar venda/item e apurar (commission_details) é LANÇAMENTO →
--   f_has_permission_guc('lancar_eventos') (RFC-COMISSION/RFC-005 §9 decisão 5).
--   O GUC de sessão é obrigatório (fail-closed):
--     SET app.actor_roles = 'OPERADOR';
--
-- INVARIANTES PROTEGIDAS POR TRIGGER:
--   (1) Venda/item/detalhe só são escritos com a ação lancar_eventos.
--   (2) commission_details é IMUTÁVEL (RFC-005 §5 regra 3): sem UPDATE/DELETE/
--       TRUNCATE. Estorno NÃO usa negativo: o cancelamento da venda vive no
--       status do cabeçalho (pos_sales.status = 'cancelada') e a DEVOLUÇÃO
--       PARCIAL vive no status do item (pos_sale_items.status = 'devolvido');
--       a apuração soma apenas detalhes de vendas NÃO canceladas E de itens
--       NÃO devolvidos (RFC-005 §5 regra 2).
--   (3) O detalhe pertence ao MESMO vendedor da venda (employee_id =
--       pos_sales.employee_id) e ao MESMO item (sale_item_id → item da venda
--       informada) — consistência (padrão db/015 invariante 2).
--   (4) rate_source coerente com o alvo da regra (RFC-005 §3.3): produto ⇒
--       rule_id com product_id; categoria ⇒ rule_id com category_id;
--       padrao ⇒ rule_id sem produto nem categoria.
--   (5) item_total = quantity × unit_price (CHECK) e commission_value =
--       item_total × rate_percent/100 (CHECK) — equações no banco (padrão
--       ck_liquid_equation da db/012).
--   (6) Sem exclusão física (padrão RFC-008 decisão 4) — estorno por status.
--   (7) commission_settlements (RFC-005 §3.5) é CONGELADO: uma linha 'fechado'
--       por (funcionário × competência) e colunas de negócio imutáveis (só o
--       status muda — estorno, que libera a regeração); sem exclusão física.
--
-- A APURAÇÃO CONSOLIDADA por funcionário × competência é derivada por consulta
-- sobre commission_details (RFC-005 §3.4); o FECHAMENTO da competência a
-- CONGELA na commission_settlements (RFC-005 §3.5), que passa a alimentar o
-- evento 7 (RFC-006).
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/017_sales_apuration.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. POS_SALES — RFC-005 §3.1 (cabeçalho da venda do PDV)
--    Uma linha por venda registrada no PDV, com o vendedor responsável e a
--    data — que define a regra de comissão vigente (RFC-002 §5 regra 3).
-- ============================================================================
CREATE TABLE pos_sales (
    id           BIGSERIAL PRIMARY KEY,
    code         TEXT         NOT NULL UNIQUE,       -- número/identificador da venda no PDV
    employee_id  BIGINT       NOT NULL REFERENCES employees (id) ON DELETE RESTRICT,
                                                     -- vendedor responsável (RFC-002)
    sale_date    DATE         NOT NULL,              -- data da venda — define a regra vigente
    total_value  NUMERIC(12,2) NOT NULL
                 CHECK (total_value >= 0),           -- total vendido
    status       TEXT         NOT NULL DEFAULT 'aberta'
                 CHECK (status IN ('aberta', 'cancelada', 'estornada')),
                                                     -- situação: cancelada/estornada saem da apuração
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE  pos_sales IS 'RFC-COMISSION/RFC-005 §3.1 — cabeçalho da venda do PDV: vendedor, data (define a regra vigente), total e status; cancelada/estornada saem da apuração da comissão' ;
COMMENT ON COLUMN pos_sales.code IS 'Número/identificador único da venda no PDV' ;
COMMENT ON COLUMN pos_sales.employee_id IS 'Vendedor responsável pela venda (employees — RFC-002); comissionado na 1ª versão (divisão de venda é evolução)' ;
COMMENT ON COLUMN pos_sales.status IS 'Situação: aberta / cancelada / estornada — cancelada e estornada NÃO entram na apuração (RFC-005 §5 regra 2)' ;

CREATE TRIGGER trg_pos_sales_updated_at
    BEFORE UPDATE ON pos_sales
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ============================================================================
-- 2. POS_SALE_ITEMS — RFC-005 §3.2 (itens da venda)
--    O item NÃO repete o vendedor (vem do cabeçalho). item_total é calculado
--    e conferido por CHECK (equação no banco — padrão da db/012). O item tem
--    status próprio: 'devolvido' representa DEVOLUÇÃO PARCIAL (o item sai da
--    apuração sem tocar no detalhe nem na venda — RFC-005 §5 regra 2).
-- ============================================================================
CREATE TABLE pos_sale_items (
    id           BIGSERIAL PRIMARY KEY,
    sale_id      BIGINT        NOT NULL REFERENCES pos_sales (id) ON DELETE RESTRICT,
                                                     -- venda a que pertence
    product_id   BIGINT        NOT NULL REFERENCES products (id) ON DELETE RESTRICT,
                                                     -- produto vendido (db/016)
    quantity     NUMERIC(12,3) NOT NULL
                 CHECK (quantity > 0),               -- quantidade
    unit_price   NUMERIC(12,2) NOT NULL
                 CHECK (unit_price >= 0),            -- preço unitário
    item_total   NUMERIC(12,2) NOT NULL
                 CHECK (item_total >= 0),
                 CHECK (item_total = ROUND(quantity * unit_price, 2)),
                                                     -- equação no banco (RFC-005 §3.2 —
                                                     -- padrão ck_liquid_equation da db/012)
    status       TEXT          NOT NULL DEFAULT 'ativo'
                 CHECK (status IN ('ativo', 'devolvido')),
                                                     -- situação do item: 'devolvido' =
                                                     -- DEVOLUÇÃO PARCIAL (sai da apuração;
                                                     -- RFC-005 §3.2/§5 regra 2)
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);

COMMENT ON TABLE  pos_sale_items IS 'RFC-COMISSION/RFC-005 §3.2 — itens da venda: produto, quantidade, preço e item_total (CHECK da equação); vendedor vem do cabeçalho (uma venda, um vendedor na 1ª versão)' ;
COMMENT ON COLUMN pos_sale_items.item_total IS '= quantity × unit_price (CHECK no banco — padrão ck_liquid_equation da db/012)' ;
COMMENT ON COLUMN pos_sale_items.status IS 'Situação do item: ativo / devolvido — DEVOLUÇÃO PARCIAL sai da apuração da comissão (RFC-005 §5 regra 2); a venda permanece aberta' ;

-- ============================================================================
-- 3. COMMISSION_DETAILS — RFC-005 §3.3 (detalhe da comissão POR ITEM APURADO)
--    Fecha a rastreabilidade da venda ao holerite: taxa resolvida pela
--    precedência (RFC-002 §3.1), origem da regra (rate_source) e valor.
--    IMUTÁVEL — estorno por status da venda, nunca negativo nem UPDATE.
-- ============================================================================
CREATE TABLE commission_details (
    id               BIGSERIAL PRIMARY KEY,
    sale_id          BIGINT        NOT NULL REFERENCES pos_sales (id) ON DELETE RESTRICT,
                                                     -- venda de origem
    sale_item_id     BIGINT        NOT NULL REFERENCES pos_sale_items (id) ON DELETE RESTRICT,
                                                     -- item apurado (UNIQUE abaixo: um detalhe por item)
    employee_id      BIGINT        NOT NULL REFERENCES employees (id) ON DELETE RESTRICT,
                                                     -- vendedor — deve ser o da venda (invariante 3)
    product_id       BIGINT        NOT NULL REFERENCES products (id) ON DELETE RESTRICT,
                                                     -- produto do item
    rate_source      TEXT          NOT NULL
                     CHECK (rate_source IN ('produto', 'categoria', 'padrao')),
                                                     -- nível da precedência que resolveu a taxa (RFC-002 §3.1)
    rule_id          BIGINT        REFERENCES commission_rules (id) ON DELETE RESTRICT,
                                                     -- regra aplicada (taxa padrão também é linha da db/016)
    rate_percent     NUMERIC(5,2)  NOT NULL
                     CHECK (rate_percent >= 0 AND rate_percent <= 100),
                                                     -- taxa efetivamente aplicada
    commission_value NUMERIC(12,2) NOT NULL
                     CHECK (commission_value >= 0),
                                                     -- nunca negativo (estorno por status da venda);
                                                     -- a EQUAÇÃO commission_value = item_total × taxa
                                                     -- é validada por TRIGGER (o item_total vem de
                                                     -- pos_sale_items — CHECK não aceita subselect)
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT uq_detail_per_item UNIQUE (sale_item_id)
                                                     -- um detalhe por item apurado (RFC-005 §3.3)
);

COMMENT ON TABLE  commission_details IS 'RFC-COMISSION/RFC-005 §3.3 — detalhe da comissão por item apurado: taxa resolvida pela precedência, origem da regra (rate_source) e valor; IMUTÁVEL (estorno por status da venda, nunca negativo nem UPDATE)' ;
COMMENT ON COLUMN commission_details.rate_source IS 'Nível da precedência que resolveu a taxa: produto / categoria / padrao (RFC-COMISSION/RFC-002 §3.1)' ;
COMMENT ON COLUMN commission_details.rule_id IS 'Regra aplicada (commission_rules da db/016) — taxa padrão também é linha da tabela (produto/categoria NULL)' ;
COMMENT ON COLUMN commission_details.commission_value IS '= item_total × rate_percent/100 (arredondado a centavos); nunca negativo — estorno por status da venda' ;

-- ============================================================================
-- 4. TRIGGERS DE ENFORCEMENT
--     (a) escrita (INSERT/UPDATE) → ação 'lancar_eventos' (RFC-009 §3.1 via
--         db/011; f_has_permission_guc é fail-closed)
--     (b) detalhe imutável (UPDATE/DELETE/TRUNCATE) — RFC-005 §5 regra 3
--     (c) consistência do detalhe: vendedor = da venda; item = da venda;
--         rate_source coerente com a regra; equação do commission_value
--     (d) itens congelados após a apuração (RFC-005 §5 regra 4)
--     (e) sem exclusão física (padrão RFC-008 decisão 4)
-- ============================================================================
CREATE OR REPLACE FUNCTION enforce_sales_write_permission ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- RFC-009 §3.1 via db/011: registrar venda/item e apurar é LANÇAMENTO
    -- (ação 'lancar_eventos' — RFC-COMISSION/RFC-005 §9 decisão 5).
    -- Fail-closed: GUC ausente/vazio → f_has_permission_guc() retorna FALSE.
    IF NOT f_has_permission_guc('lancar_eventos') THEN
        RAISE EXCEPTION 'Registrar vendas/apuração exige a ação lancar_eventos (RFC-009 §3.1, via db/011); app.actor_roles = %',
            COALESCE(current_setting('app.actor_roles', true), '<não definido>');
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION enforce_commission_detail_insert ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_sale_employee  BIGINT;
    v_item_sale      BIGINT;
    v_item_total     NUMERIC(12,2);
    v_rule_product   BIGINT;
    v_rule_category  BIGINT;
BEGIN
    -- (c1) vendedor do detalhe = vendedor da venda (RFC-005 §3.3 invariante 2)
    SELECT employee_id INTO v_sale_employee FROM pos_sales WHERE id = NEW.sale_id;
    IF v_sale_employee IS NULL THEN
        RAISE EXCEPTION 'Venda inexistente (sale_id = %)', NEW.sale_id;
    END IF;
    IF NEW.employee_id IS DISTINCT FROM v_sale_employee THEN
        RAISE EXCEPTION 'Vendedor do detalhe (%) difere do vendedor da venda (%) — RFC-005: a comissão é do vendedor da venda',
            NEW.employee_id, v_sale_employee;
    END IF;

    -- (c2) o item pertence à venda informada (RFC-005 §3.3)
    SELECT sale_id, item_total INTO v_item_sale, v_item_total
      FROM pos_sale_items WHERE id = NEW.sale_item_id;
    IF v_item_sale IS NULL THEN
        RAISE EXCEPTION 'Item inexistente (sale_item_id = %)', NEW.sale_item_id;
    END IF;
    IF v_item_sale <> NEW.sale_id THEN
        RAISE EXCEPTION 'Item % não pertence à venda % — RFC-005: o detalhe apura o item da própria venda',
            NEW.sale_item_id, NEW.sale_id;
    END IF;

    -- (c2.1) item DEVOLVIDO não pode ser apurado (RFC-005 §3.2/§5 regra 2):
    --        a devolução sai da apuração ANTES do detalhe existir
    IF (SELECT status FROM pos_sale_items WHERE id = NEW.sale_item_id) = 'devolvido' THEN
        RAISE EXCEPTION 'Item devolvido não pode ser apurado (RFC-005 §5 regra 2): sale_item_id % está com status devolvido',
            NEW.sale_item_id;
    END IF;

    -- (c3) produto do detalhe = produto do item (coerência)
    IF NEW.product_id IS DISTINCT FROM (SELECT product_id FROM pos_sale_items WHERE id = NEW.sale_item_id) THEN
        RAISE EXCEPTION 'Produto do detalhe difere do produto do item — RFC-005 §3.3';
    END IF;

    -- (c4) rate_source coerente com o alvo da regra (RFC-005 §5)
    IF NEW.rule_id IS NOT NULL THEN
        SELECT product_id, category_id INTO v_rule_product, v_rule_category
          FROM commission_rules WHERE id = NEW.rule_id;
        IF v_rule_product IS NULL AND v_rule_category IS NULL THEN
            IF NEW.rate_source <> 'padrao' THEN
                RAISE EXCEPTION 'rate_source % incompatível com regra de taxa padrão (RFC-005 §5)', NEW.rate_source;
            END IF;
        ELSIF v_rule_product IS NOT NULL THEN
            IF NEW.rate_source <> 'produto' THEN
                RAISE EXCEPTION 'rate_source % incompatível com regra de produto (RFC-005 §5)', NEW.rate_source;
            END IF;
        ELSE
            IF NEW.rate_source <> 'categoria' THEN
                RAISE EXCEPTION 'rate_source % incompatível com regra de categoria (RFC-005 §5)', NEW.rate_source;
            END IF;
        END IF;
    END IF;

    -- (c5) equação do commission_value = item_total × rate_percent/100
    --      (RFC-005 §3.3 — padrão de CHECKs de equação da db/012, aqui em
    --      trigger pois o item_total vem de outra tabela)
    IF NEW.commission_value <> ROUND(v_item_total * NEW.rate_percent / 100, 2) THEN
        RAISE EXCEPTION 'commission_value % não confere com item_total % × taxa % (RFC-005 §3.3)',
            NEW.commission_value, v_item_total, NEW.rate_percent;
    END IF;

    RETURN NEW;
END;
$$;

-- (d) congelamento após a apuração (RFC-005 §5 regra 4):
--     • item COM commission_details não muda as colunas de negócio (product_id/
--       quantity/unit_price/item_total) — o detalhe imutável ficaria órfão do
--       item_total; o STATUS é alterável para DEVOLUÇÃO PARCIAL ('devolvido'),
--       espelhando o cabeçalho (só o status muda após a apuração)
--     • venda com detalhes não muda as colunas de negócio (code/employee_id/
--       sale_date/total_value) — senão o detalhe ficaria com vendedor ≠ da
--       venda e a comissão mudaria de competência retroativamente
CREATE OR REPLACE FUNCTION enforce_item_frozen_after_apuration ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM commission_details WHERE sale_item_id = OLD.id)
       AND (   NEW.product_id  IS DISTINCT FROM OLD.product_id
            OR NEW.quantity    IS DISTINCT FROM OLD.quantity
            OR NEW.unit_price  IS DISTINCT FROM OLD.unit_price
            OR NEW.item_total  IS DISTINCT FROM OLD.item_total) THEN
        RAISE EXCEPTION 'Item já apurado (commission_details) não pode mudar colunas de negócio (RFC-005 §5 regra 4): só o status (devolução parcial) é alterável; correção = estorno da venda + nova venda';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION enforce_sale_frozen_after_apuration ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM commission_details WHERE sale_id = OLD.id)
       AND (   NEW.code        IS DISTINCT FROM OLD.code
            OR NEW.employee_id IS DISTINCT FROM OLD.employee_id
            OR NEW.sale_date   IS DISTINCT FROM OLD.sale_date
            OR NEW.total_value IS DISTINCT FROM OLD.total_value) THEN
        RAISE EXCEPTION 'Venda já apurada (commission_details) não pode mudar colunas de negócio (RFC-005 §5 regra 4): só o status (estorno) é alterável; correção = nova venda';
    END IF;
    RETURN NEW;
END;
$$;

-- (e) sem exclusão física — venda cancelada/estornada por status, nunca apagada
--     (reusa prevent_hard_delete da db/002); o detalhe apurado é imutável
CREATE OR REPLACE FUNCTION prevent_sales_apuration_delete ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Exclusão física de pos_sales/pos_sale_items/commission_details proibida (RFC-005 §5 regra 5 — padrão RFC-008 decisão 4): estorno por status, nunca DELETE/TRUNCATE';
END;
$$;

-- (f) detalhe apurado IMUTÁVEL (RFC-005 §5 regra 3): UPDATE bloqueado com
--     mensagem própria (padrão db/015) — correção = estorno da venda + nova
--     venda; o DELETE/TRUNCATE fica com a prevent_sales_apuration_delete
CREATE OR REPLACE FUNCTION prevent_commission_detail_update ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Detalhe de comissão apurado é imutável (RFC-005 §5 regra 3): nenhuma alteração — estorno da venda (status) + nova venda';
END;
$$;

-- Triggers de permissão (INSERT/UPDATE)
CREATE TRIGGER trg_pos_sales_write_perm
    BEFORE INSERT OR UPDATE ON pos_sales
    FOR EACH ROW EXECUTE FUNCTION enforce_sales_write_permission ();

CREATE TRIGGER trg_pos_sale_items_write_perm
    BEFORE INSERT OR UPDATE ON pos_sale_items
    FOR EACH ROW EXECUTE FUNCTION enforce_sales_write_permission ();

CREATE TRIGGER trg_commission_details_write_perm
    BEFORE INSERT ON commission_details
    FOR EACH ROW EXECUTE FUNCTION enforce_sales_write_permission ();

-- Triggers de consistência do detalhe
CREATE TRIGGER trg_commission_details_integrity
    BEFORE INSERT ON commission_details
    FOR EACH ROW EXECUTE FUNCTION enforce_commission_detail_insert ();

-- Trigger de congelamento dos itens após a apuração
CREATE TRIGGER trg_pos_sale_items_frozen
    BEFORE UPDATE ON pos_sale_items
    FOR EACH ROW EXECUTE FUNCTION enforce_item_frozen_after_apuration ();

CREATE TRIGGER trg_pos_sales_frozen
    BEFORE UPDATE ON pos_sales
    FOR EACH ROW EXECUTE FUNCTION enforce_sale_frozen_after_apuration ();

-- Triggers de imutabilidade do detalhe (UPDATE/DELETE/TRUNCATE)
CREATE TRIGGER trg_commission_details_no_update
    BEFORE UPDATE ON commission_details
    FOR EACH ROW EXECUTE FUNCTION prevent_commission_detail_update ();

CREATE TRIGGER trg_commission_details_no_delete
    BEFORE DELETE ON commission_details
    FOR EACH ROW EXECUTE FUNCTION prevent_sales_apuration_delete ();

CREATE TRIGGER trg_commission_details_no_truncate
    BEFORE TRUNCATE ON commission_details
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_sales_apuration_delete ();

-- Triggers de proteção contra exclusão física das vendas e itens
CREATE TRIGGER trg_pos_sales_no_delete
    BEFORE DELETE ON pos_sales
    FOR EACH ROW EXECUTE FUNCTION prevent_sales_apuration_delete ();

CREATE TRIGGER trg_pos_sales_no_truncate
    BEFORE TRUNCATE ON pos_sales
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_sales_apuration_delete ();

CREATE TRIGGER trg_pos_sale_items_no_delete
    BEFORE DELETE ON pos_sale_items
    FOR EACH ROW EXECUTE FUNCTION prevent_sales_apuration_delete ();

CREATE TRIGGER trg_pos_sale_items_no_truncate
    BEFORE TRUNCATE ON pos_sale_items
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_sales_apuration_delete ();

REVOKE DELETE, TRUNCATE ON pos_sales, pos_sale_items, commission_details FROM PUBLIC;
REVOKE UPDATE ON commission_details FROM PUBLIC;

-- ============================================================================
-- 5. COMMISSION_SETTLEMENTS — RFC-005 §3.5 (congelamento do apurado)
--    Fechamento da competência: uma linha por (funcionário × competência) com
--    o total apurado CONGELADO — a partir daí alimenta o evento 7 na folha,
--    imune a devoluções/cancelamentos posteriores (RFC-005 §5 regra 8).
-- ============================================================================
CREATE TABLE commission_settlements (
    id           BIGSERIAL PRIMARY KEY,
    employee_id  BIGINT        NOT NULL REFERENCES employees (id) ON DELETE RESTRICT,
                                                    -- funcionário comissionado (RFC-002 Folha)
    competence   DATE          NOT NULL,           -- competência (1º dia do mês de apuração)
    total_value  NUMERIC(12,2) NOT NULL
                 CHECK (total_value >= 0),         -- comissão consolidada e congelada (pré-DSR)
    status       TEXT          NOT NULL DEFAULT 'fechado'
                 CHECK (status IN ('fechado', 'estornado')),
                                                    -- fechado (válido) / estornado (correção → regerar)
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);

COMMENT ON TABLE  commission_settlements IS 'RFC-COMISSION/RFC-005 §3.5 — congelamento do apurado por (funcionário × competência): valor que alimenta o evento 7 após o fechamento, imune a devoluções/cancelamentos posteriores' ;
COMMENT ON COLUMN commission_settlements.competence IS 'Competência da apuração (1º dia do mês) — mesma granularidade da consolidação derivada (RFC-005 §3.4)' ;
COMMENT ON COLUMN commission_settlements.status IS 'Situação: fechado / estornado — estorno por status libera a regeração (RFC-005 §3.5)' ;

CREATE TRIGGER trg_commission_settlements_updated_at
    BEFORE UPDATE ON commission_settlements
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- Índice único parcial: uma linha 'fechado' por (funcionário × competência);
-- 'estornado' libera a regeração (mesmo padrão da db/016 — RFC-003 §3.3).
CREATE UNIQUE INDEX uq_settlement_per_competence
    ON commission_settlements (employee_id, competence)
    WHERE status = 'fechado';

-- (a) escrita (INSERT/UPDATE) exige a ação lancar_eventos (fail-closed — RFC-005 §3.5)
CREATE TRIGGER trg_commission_settlements_write_perm
    BEFORE INSERT OR UPDATE ON commission_settlements
    FOR EACH ROW EXECUTE FUNCTION enforce_sales_write_permission ();

-- (b) congelamento: colunas de negócio imutáveis após o fechamento; só o
--     status é alterável (estorno) — espelha o cabeçalho (RFC-005 §5 regra 4)
CREATE OR REPLACE FUNCTION enforce_settlement_frozen_after_close ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF (   NEW.employee_id IS DISTINCT FROM OLD.employee_id
        OR NEW.competence  IS DISTINCT FROM OLD.competence
        OR NEW.total_value IS DISTINCT FROM OLD.total_value) THEN
        RAISE EXCEPTION 'Settlement fechado não pode mudar colunas de negócio (RFC-005 §3.5): só o status (estorno) é alterável; correção = estorno + regeração';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_commission_settlements_frozen
    BEFORE UPDATE ON commission_settlements
    FOR EACH ROW EXECUTE FUNCTION enforce_settlement_frozen_after_close ();

-- (c) sem exclusão física (padrão RFC-008 decisão 4 — reusa prevent da db/017)
CREATE TRIGGER trg_commission_settlements_no_delete
    BEFORE DELETE ON commission_settlements
    FOR EACH ROW EXECUTE FUNCTION prevent_sales_apuration_delete ();

CREATE TRIGGER trg_commission_settlements_no_truncate
    BEFORE TRUNCATE ON commission_settlements
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_sales_apuration_delete ();

REVOKE DELETE, TRUNCATE ON commission_settlements FROM PUBLIC;

-- ============================================================================
-- Índices de consulta
-- ============================================================================
CREATE INDEX idx_settlements_emp ON commission_settlements (employee_id, competence);
CREATE INDEX idx_pos_sales_employee   ON pos_sales (employee_id, sale_date);
CREATE INDEX idx_pos_sales_status     ON pos_sales (status);
CREATE INDEX idx_pos_sale_items_sale  ON pos_sale_items (sale_id);
CREATE INDEX idx_pos_sale_items_prod  ON pos_sale_items (product_id);
CREATE INDEX idx_pos_sale_items_status ON pos_sale_items (status);
CREATE INDEX idx_comm_details_emp     ON commission_details (employee_id, sale_id);
CREATE INDEX idx_comm_details_rule    ON commission_details (rule_id);

COMMIT;
