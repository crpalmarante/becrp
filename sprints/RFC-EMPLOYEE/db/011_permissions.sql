-- ============================================================================
-- db/011_permissions.sql
-- RFC-009 — Usuários, Papéis e Auditoria (v1.0.0 · Draft em revisão)
-- ----------------------------------------------------------------------------
-- MATERIALIZA a matriz de permissões por ação (RFC-009 §3.1) como tabela no
-- banco, permitindo checagem de permissões NO NÍVEL DO BANCO (além da camada
-- de aplicação): a aplicação consulta f_has_permission() com os papéis do
-- ator (GUC app.actor_roles, mesmo padrão da migration 010).
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- Pré-requisito: db/009 (roles.code é a FK). Ordem: 002 → 009 → 011 → 010
-- (a 010 passa a DEPENDER desta migration: as transições da máquina de
-- estados consultam f_has_permission_guc() para autorizar cada transição).
--
-- NOTA DE ALINHAMENTO: a máquina de estados (010) autoriza cada transição
-- consultando ESTA matriz via f_has_permission_guc(): as transições carregam
-- apenas a AÇÃO exigida (required_action em payroll_period_status_transitions)
-- e o papel vive somente aqui (autoridade única — ex.: a transição
-- validada→fechada exige a ação 'fechar', autorizada ao APROVADOR nesta
-- tabela; nada de required_role duplicado na 010).
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/011_permissions.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. PERMISSIONS — RFC-009 §3.1 (matriz ação × papel)
--    Uma linha por célula ✅ da matriz. Papéis fixos da 1ª versão (decisão 1).
--    A matriz é a autoridade única de permissões; agora consultável no banco.
-- ============================================================================
CREATE TABLE permissions (
    action      TEXT NOT NULL
                CHECK (action IN ('abrir_competencia', 'lancar_eventos',
                                  'calcular', 'validar', 'fechar',
                                  'registrar_pagamento', 'manter_cadastros',
                                  'manter_usuarios')),
                                           -- ação (linha da matriz §3.1)
    role_code   TEXT NOT NULL REFERENCES roles (code) ON DELETE RESTRICT,
                                           -- papel autorizado (coluna da matriz §3.1)
    PRIMARY KEY (action, role_code)        -- célula ✅ única por ação × papel
                                           -- (padrão user_roles da 009: sem id extra)
);

COMMENT ON TABLE  permissions IS 'RFC-009 §3.1 — matriz de permissões por ação (ação × papel) materializada no banco para checagem no nível do banco';
COMMENT ON COLUMN permissions.action    IS 'Ação (linha da matriz §3.1): abrir_competencia, lancar_eventos, calcular, validar, fechar, registrar_pagamento, manter_cadastros, manter_usuarios';
COMMENT ON COLUMN permissions.role_code IS 'Papel autorizado a executar a ação (coluna da matriz §3.1) — FK roles.code (RFC-009 §3)';

-- Seed — células ✅ da matriz RFC-009 §3.1
INSERT INTO permissions (action, role_code) VALUES
    -- Abrir competência   | Operador ✅ | Admin ✅
    ('abrir_competencia',    'OPERADOR'),
    ('abrir_competencia',    'ADMINISTRADOR'),
    -- Lançar eventos / Calcular | Operador ✅
    ('lancar_eventos',       'OPERADOR'),
    ('calcular',             'OPERADOR'),
    -- Validar | Conferente ✅
    ('validar',              'CONFERENTE'),
    -- Fechar | Aprovador ✅
    ('fechar',               'APROVADOR'),
    -- Registrar pagamento | Tesouraria ✅
    ('registrar_pagamento',  'TESOURARIA'),
    -- Manter cadastros/tabelas · Manter usuários | Admin ✅
    ('manter_cadastros',     'ADMINISTRADOR'),
    ('manter_usuarios',      'ADMINISTRADOR');

-- ============================================================================
-- 2. CHECAGEM NO NÍVEL DO BANCO — f_has_permission()
--    Fail-closed: papel ausente/vazio/nulo → FALSE. A aplicação autenticada
--    define o ator via GUC de sessão (mesmo padrão da 010):
--      SET app.actor_roles = 'OPERADOR,CONFERENTE';
--      SELECT f_has_permission('fechar', current_setting('app.actor_roles', true));
-- ============================================================================
CREATE OR REPLACE FUNCTION f_has_permission (p_action TEXT, p_roles TEXT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
          FROM permissions
         WHERE action    = p_action
           AND role_code = ANY (string_to_array(replace(p_roles, ' ', ''), ','))
    );
$$;

COMMENT ON FUNCTION f_has_permission (TEXT, TEXT) IS
    'RFC-009 §3.1 — true se algum papel de p_roles (lista CSV de codes, espaços tolerados) executa p_action; fail-closed (NULL/vazio → false)';

CREATE OR REPLACE FUNCTION f_has_permission_guc (p_action TEXT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT f_has_permission(p_action, current_setting('app.actor_roles', true));
$$;

COMMENT ON FUNCTION f_has_permission_guc (TEXT) IS
    'RFC-009 §3.1 — f_has_permission() lendo os papéis do ator do GUC de sessão app.actor_roles';

COMMIT;
