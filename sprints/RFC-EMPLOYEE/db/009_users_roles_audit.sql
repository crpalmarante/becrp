-- ============================================================================
-- db/009_users_roles_audit.sql
-- RFC-009 — Usuários, Papéis e Auditoria (v1.0.0 · Draft em revisão)
-- ----------------------------------------------------------------------------
-- Cria a base de governança do sistema:
--   users      (RFC-009 §2)  — quem opera o sistema
--   roles      (RFC-009 §3)  — papéis FIXOS da 1ª versão (decisão 1)
--   user_roles (RFC-009 §3)  — vínculo N:N, múltiplos papéis por usuário (decisão 2)
--   audit_log  (RFC-009 §5)  — trilha imutável de mutações relevantes
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- Pré-requisito: tabela `employees` (cadastro de funcionários — RFC-002,
-- PLAN_ERP §7.4) criada em migration anterior.
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/009_users_roles_audit.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. USERS — RFC-009 §2
-- ============================================================================
CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    login         TEXT        NOT NULL UNIQUE,             -- identificador único de acesso (✅)
    name          TEXT        NOT NULL,                    -- nome do usuário (✅)
    status        TEXT        NOT NULL DEFAULT 'ativo'
                  CHECK (status IN ('ativo', 'inativo')),  -- situação ativo/inativo (✅)
    employee_id   BIGINT      REFERENCES employees (id) ON DELETE RESTRICT,
                                                          -- vínculo com funcionário (🔸 opcional);
                                                          -- identidade cruzada pelo CPF (RFC-002 regra 1)
    password_hash TEXT        NOT NULL,                    -- infra: credencial p/ login (PLAN_ERP §4 — sessão c/ cookie assinado)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  users                    IS 'RFC-009 §2 — operador do sistema';
COMMENT ON COLUMN users.login              IS 'Identificador único de acesso';
COMMENT ON COLUMN users.status             IS 'Situação: ativo / inativo';
COMMENT ON COLUMN users.employee_id        IS 'Vínculo com funcionário (🔸 opcional) — se o operador também é funcionário da empresa; chave natural de ligação: CPF (RFC-002)';
COMMENT ON COLUMN users.password_hash      IS 'Assumido (fora do escopo do RFC-009): hash da senha para autenticação (PLAN_ERP §4)';

-- manutenção automática de updated_at
CREATE OR REPLACE FUNCTION set_users_updated_at ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_users_updated_at ();

-- ============================================================================
-- 2. ROLES — RFC-009 §3 (papéis fixos na 1ª versão — decisão 1)
-- ============================================================================
CREATE TABLE roles (
    id          BIGSERIAL PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE
                CHECK (code IN ('OPERADOR', 'CONFERENTE', 'APROVADOR', 'TESOURARIA', 'ADMINISTRADOR')),
    description TEXT NOT NULL
);

COMMENT ON TABLE roles IS 'RFC-009 §3 — papéis fixos da 1ª versão; sem criação de papéis customizados (decisão 1)';
COMMENT ON COLUMN roles.code IS 'Código estável do papel (chave usada pela aplicação)';

-- ============================================================================
-- MATRIZ DE PERMISSÕES POR AÇÃO — RFC-009 §3.1 (tabela única na 1ª versão)
-- Ação                | Operador | Conferente | Aprovador | Tesouraria | Admin
-- --------------------|----------|------------|-----------|------------|------
-- Abrir competência   |    ✅    |     —      |     —     |     —      |  ✅
-- Lançar eventos      |    ✅    |     —      |     —     |     —      |  —
-- Calcular            |    ✅    |     —      |     —     |     —      |  —
-- Validar             |    —     |     ✅     |     —     |     —      |  —
-- Fechar              |    —     |     —      |     ✅    |     —      |  —
-- Registrar pagamento |    —     |     —      |     —     |     ✅     |  —
-- Manter cad./tabelas |    —     |     —      |     —     |     —      |  ✅
-- Manter usuários     |    —     |     —      |     —     |     —      |  ✅
-- ----------------------------------------------------------------------------
-- A matriz é a autoridade única de permissões; a checagem roda na camada de
-- aplicação (RFC-009 §4 regra 1: "toda ação de estado exige o papel
-- correspondente"). A separação de funções (Aprovador ≠ Operador da
-- competência — RFC-009 §4.2/decisão 4) é regra de negócio sobre transições
-- de estado (RFC-006), não modelável por constraint aqui.
-- ============================================================================

-- Seed dos papéis (RFC-009 §3 — o que cada papel pode fazer)
INSERT INTO roles (code, description) VALUES
    ('OPERADOR',      'Lançar eventos variáveis, abrir competência, calcular'),
    ('CONFERENTE',    'Revisar e validar (estado "Validada")'),
    ('APROVADOR',     'Fechar a competência (estado "Fechada")'),
    ('TESOURARIA',    'Registrar pagamento (estado "Paga")'),
    ('ADMINISTRADOR', 'Gerir usuários, cadastros mestres e tabelas');

-- ============================================================================
-- 3. USER_ROLES — RFC-009 §3 regra 3 / decisão 2 (múltiplos papéis por usuário)
-- ============================================================================
CREATE TABLE user_roles (
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES roles (id) ON DELETE RESTRICT,
    PRIMARY KEY (user_id, role_id)
);

COMMENT ON TABLE user_roles IS 'RFC-009 §3 — um usuário pode ter múltiplos papéis, respeitada a separação de funções na prática (§4.2)';

-- ============================================================================
-- 4. AUDIT_LOG — RFC-009 §5 (trilha imutável)
-- ============================================================================
CREATE TABLE audit_log (
    id                 BIGSERIAL PRIMARY KEY,
    occurred_at        TIMESTAMPTZ NOT NULL DEFAULT now(),       -- Quando (data e hora)
    actor_id           BIGINT      REFERENCES users (id) ON DELETE RESTRICT,
                                                                 -- Quem (usuário autenticado)
    actor_label        TEXT        NOT NULL,                     -- Quem: login do usuário ou 'sistema' (ações automáticas)
    action             TEXT        NOT NULL,                     -- O quê: lançar, calcular, validar, fechar,
                                                                 --       alterar_cadastro, alterar_tabela,
                                                                 --       registrar_pagamento…
    before_data        JSONB,                                    -- Antes (estado anterior — valores alterados)
    after_data         JSONB,                                    -- Depois (estado posterior)
    context            JSONB        NOT NULL DEFAULT '{}'::jsonb, -- Contexto: competência, funcionário, evento ou tabela afetados
    tax_table_versions JSONB,                                     -- RFC-005 §5.1.2: versão das tabelas fiscais usadas no cálculo

    -- integridade do "Quem": ações de sistema não têm usuário; ações de usuário exigem o vínculo
    CONSTRAINT ck_audit_actor CHECK (
        length(btrim(actor_label)) > 0
        AND (
            (actor_label = 'sistema' AND actor_id IS NULL)
            OR
            (actor_label <> 'sistema' AND actor_id IS NOT NULL)
        )
    )
);

COMMENT ON TABLE  audit_log                    IS 'RFC-009 §5 — registro imutável de toda mutação relevante (rastreabilidade do RFC-001 regra 4)';
COMMENT ON COLUMN audit_log.actor_label        IS 'Quem: login do usuário autenticado ou ''sistema'' para ações automáticas (RFC-009 §5). Snapshot denormalizado: renomear um login não reescreve o histórico.';
COMMENT ON COLUMN audit_log.action             IS 'O quê: lançar, calcular, validar, fechar, alterar cadastro, alterar tabela, registrar pagamento… (RFC-009 §5)';
COMMENT ON COLUMN audit_log.before_data        IS 'Antes — estado anterior (valores alterados)';
COMMENT ON COLUMN audit_log.after_data         IS 'Depois — estado posterior';
COMMENT ON COLUMN audit_log.context            IS 'Contexto — competência, funcionário, evento ou tabela afetados';
COMMENT ON COLUMN audit_log.tax_table_versions IS 'RFC-005 §5.1.2 — versão das tabelas usadas, permitindo reproduzir o cálculo da competência';

-- ----------------------------------------------------------------------------
-- 4.1 Imutabilidade da trilha (RFC-009 §5.1.1: nenhum registro pode ser
--     editado, apagado ou truncado). Garantida em DOIS níveis:
--       (a) triggers que bloqueiam UPDATE/DELETE (linha) e TRUNCATE
--           (statement — triggers de linha NÃO disparam em TRUNCATE);
--           valem até p/ o dono da tabela;
--       (b) REVOKE de UPDATE/DELETE/TRUNCATE para o papel público.
-- Escopo: a proteção cobre as operações bloqueáveis por trigger
-- (UPDATE/DELETE/TRUNCATE). DDL destrutivo (DROP TABLE) por um superusuário
-- não é bloqueável por trigger.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_audit_log_mutation ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_log é imutável (RFC-009 §5.1.1): UPDATE/DELETE/TRUNCATE são proibidos';
END;
$$;

CREATE TRIGGER trg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation ();

CREATE TRIGGER trg_audit_log_no_truncate
    BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_audit_log_mutation ();

REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM PUBLIC;

-- ============================================================================
-- Índices de consulta
-- ============================================================================
CREATE INDEX idx_users_employee_id   ON users (employee_id);
CREATE INDEX idx_user_roles_role_id  ON user_roles (role_id);
CREATE INDEX idx_audit_log_when      ON audit_log (occurred_at DESC);
CREATE INDEX idx_audit_log_action    ON audit_log (action);
CREATE INDEX idx_audit_log_actor_id  ON audit_log (actor_id);
-- jsonb_path_ops otimiza @> (contém). NÃO suporta o operador ? (existência de
-- chave): se a app consultar `context ? 'competencia'`, usar GIN padrão (jsonb_ops).
CREATE INDEX idx_audit_log_context   ON audit_log USING GIN (context jsonb_path_ops);

COMMIT;
