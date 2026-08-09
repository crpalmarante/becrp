-- ============================================================================
-- db/018_commission_global_rules.sql
-- RFC-COMISSION/RFC-008 — Taxa Padrão GLOBAL da Empresa (v1.0.0 · Draft)
-- ----------------------------------------------------------------------------
-- Cria a tabela commission_global_rules: a taxa percentual padrão GLOBAL da
-- empresa (não por funcionário) — o 4º nível da precedência:
--   produto → categoria → taxa padrão do funcionário → taxa padrão GLOBAL → 0
--
-- Evolução declarada no RFC-COMISSION/RFC-003 §7 e RFC-COMISSION/RFC-007 §6:
-- a db/016 modela regras SEMPRE por funcionário (commission_rules.employee_id
-- é NOT NULL); a taxa GLOBAL da empresa precisa de um vínculo único
-- empresa × taxa, sem funcionário → nova tabela.
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- Pré-requisitos:
--   db/002 (set_updated_at, prevent_hard_delete)
--   db/011 (f_has_permission_guc — RFC-009 §3.1)
--   db/016 (enforce_commission_write_permission — reutilizada aqui)
-- Ordem: 002 → 009 → 011 → 016 → 017 → 018.
--
-- AUTORIZAÇÃO POR AÇÃO (RFC-009 §3.1 via db/011 — autoridade única):
--   Manter a taxa padrão global é ATO DE CADASTRO →
--   f_has_permission_guc('manter_cadastros'). O GUC de sessão é obrigatório
--   (fail-closed):
--     SET app.actor_roles = 'OPERADOR';
--
-- INVARIANTES PROTEGIDAS POR TRIGGER:
--   (1) Escrita exige a ação manter_cadastros (reusa o trigger da db/016).
--   (2) UMA regra ATIVA por empresa (índice único parcial uq_commission_global_default
--       sobre expressão constante `true` — todas as linhas ATIVAS colidem na
--       mesma chave, então no máximo uma existe por vez).
--   (3) Vigência válida (valid_until >= valid_from, quando ambos informados).
--   (4) Nenhuma exclusão física (padrão RFC-008 (projeto) decisão 4 — inativação lógica).
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/018_commission_global_rules.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. COMMISSION_GLOBAL_RULES — RFC-COMISSION/RFC-008 §2/§6 (taxa padrão global)
--    Vínculo empresa × taxa percentual (fallback final da precedência),
--    SEM funcionário (diferente de commission_rules da db/016).
-- ============================================================================
CREATE TABLE commission_global_rules (
    id           BIGSERIAL PRIMARY KEY,
    rate_percent NUMERIC(5,2)  NOT NULL
                 CHECK (rate_percent >= 0 AND rate_percent <= 100),
                                                    -- taxa percentual da empresa (0–100)
    valid_from   DATE,                              -- vigência inicial (RFC-002 §5 regra 3)
    valid_until  DATE,                              -- vigência final (opcional)
    status       TEXT          NOT NULL DEFAULT 'ativo'
                 CHECK (status IN ('ativo', 'inativo')),  -- situação: ativa / inativa
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT ck_global_rule_validity CHECK (
        valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from
    )                                               -- vigência coerente (padrão RFC-004)
);

COMMENT ON TABLE  commission_global_rules IS 'RFC-COMISSION/RFC-008 §2/§6 — taxa padrão GLOBAL da empresa (fallback final da precedência: produto → categoria → funcionário → global); sem funcionário, uma única regra ATIVA por empresa' ;
COMMENT ON COLUMN commission_global_rules.rate_percent IS 'Taxa percentual padrão da empresa (0–100), aplicada aos itens vendidos por funcionários sem regra de produto/categoria/taxa padrão própria (ex.: 1,00 = 1%)' ;
COMMENT ON COLUMN commission_global_rules.valid_from IS 'Vigência inicial — a venda usa a regra vigente na data da venda (RFC-002 §5 regra 3)' ;
COMMENT ON COLUMN commission_global_rules.status IS 'Situação: ativa / inativa (inativação lógica — padrão RFC-008 (projeto) decisão 4)' ;

CREATE TRIGGER trg_commission_global_rules_updated_at
    BEFORE UPDATE ON commission_global_rules
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ============================================================================
-- 1.1 Índice único parcial — UMA regra ATIVA por empresa (RFC-008 §8 decisão 2).
--     O índice é sobre a expressão constante `true`: todas as linhas ATIVAS
--     têm a MESMA chave (true), então o UNIQUE garante no máximo uma ativa.
--     O filtro `status = 'ativo'` permite o VERSIONAMENTO por vigência
--     (RFC-002 §5 regra 3): para mudar a taxa, inativa-se a regra atual
--     (histórico preservado — nunca exclusão física) e cria-se a nova regra
--     com a nova vigência. A consulta de resolução (RFC-008 §6) usa apenas a
--     regra ativa, coerente com "a taxa da data da venda".
-- ============================================================================
CREATE UNIQUE INDEX uq_commission_global_default
    ON commission_global_rules ((true))
    WHERE status = 'ativo';

-- ============================================================================
-- 2. TRIGGERS DE ENFORCEMENT
--     (a) escrita (INSERT/UPDATE) → ação 'manter_cadastros' — REUSA a função
--         enforce_commission_write_permission da db/016 (fail-closed)
--     (b) sem exclusão física (DELETE/TRUNCATE) — padrão RFC-008 (projeto)
--         decisão 4 (reusa prevent_hard_delete da db/002)
-- ============================================================================
CREATE TRIGGER trg_commission_global_rules_write_perm
    BEFORE INSERT OR UPDATE ON commission_global_rules
    FOR EACH ROW EXECUTE FUNCTION enforce_commission_write_permission ();

CREATE TRIGGER trg_commission_global_rules_no_delete
    BEFORE DELETE ON commission_global_rules
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete ();

CREATE TRIGGER trg_commission_global_rules_no_truncate
    BEFORE TRUNCATE ON commission_global_rules
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_hard_delete ();

REVOKE DELETE, TRUNCATE ON commission_global_rules FROM PUBLIC;

-- ============================================================================
-- Índices de consulta
-- ============================================================================
CREATE INDEX idx_commission_global_rules_status ON commission_global_rules (status);

COMMIT;
