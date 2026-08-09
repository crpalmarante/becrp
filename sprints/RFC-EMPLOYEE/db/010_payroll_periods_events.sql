-- ============================================================================
-- db/010_payroll_periods_events.sql
-- RFC-006 — Processamento da Folha (v1.0.0 · Draft em revisão)
--           RFC-004 — Eventos: Proventos e Descontos (v1.0.0 · Draft em revisão)
-- ----------------------------------------------------------------------------
-- Cria as competências (períodos de folha) com a MÁQUINA DE ESTADOS do RFC-006
-- e o catálogo de eventos do RFC-004:
--   payroll_periods                (RFC-006 §2)  — competência mês/ano/tipo com
--                                                   estados: aberta → em_calculo
--                                                   → calculada → validada →
--                                                   fechada → paga
--   payroll_period_status_transitions (RFC-006 §4/§5 + RFC-009 §3.1)
--                                 — tabela dirigida por dados das transições
--                                   permitidas e a AÇÃO da matriz §3.1
--                                   exigida em cada uma
--   payroll_events                 (RFC-004 §2/§3) — catálogo de proventos e
--                                                   descontos com incidências
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- Pré-requisitos:
--   db/002 (employees/departments/positions) — fornece set_updated_at()
--   db/009 (users/roles/audit_log)           — base de usuários e papéis
--   db/011 (permissions)                     — matriz RFC-009 §3.1 com
--                                              f_has_permission_guc()
-- Ordem: 002 → 009 → 011 → 010.
--
-- MÁQUINA DE ESTADOS (RFC-006 §2 + regra 4 — estados sequenciais):
--   aberta → em_calculo → calculada → validada → fechada → paga
--   Fechada é IMUTÁVEL (regra 1): correções geram folha complementar (RFC-013),
--   nunca edição da fechada. A única transição saindo de fechada é fechada→paga.
--   Transições regressivas (†) são derivação consistente com o loop
--   "corrigir e reverificar" do RFC-015 §3.1.
--
-- REGRAS DE TRANSIÇÃO POR PAPEL (RFC-009 §3.1 + RFC-006 §5):
--   A aplicação autenticada DEFINE O PAPEL em TODA sessão via GUC de sessão
--   (obrigatório — fail-closed: INSERT/UPDATE de status sem o GUC é rejeitado):
--     SET app.actor_roles = 'OPERADOR,CONFERENTE';
--   Os triggers da competência validam a transição contra a tabela
--   payroll_period_status_transitions (sequência — RFC-006 regra 4) e a
--   AUTORIZAÇÃO contra a MATRIZ DE PERMISSÕES materializada na db/011
--   (f_has_permission_guc — RFC-009 §3.1, regra 5). Cada transição carrega
--   apenas a AÇÃO da matriz exigida (required_action); o papel em si vive só
--   na 011 (autoridade única — nada de required_role duplicado aqui).
--   Abrir competência exige a ação 'abrir_competencia' (OPERADOR ou
--   ADMINISTRADOR — RFC-009 §3.1: ✅ duplo).
--
-- RASTREABILIDADE (RFC-009 §5 + RFC-006 regra 5): cada transição de estado
-- deve gerar um registro em audit_log (action = 'calcular'/'validar'/'fechar'/
-- 'registrar_pagamento', context = {"competencia": reference}). A gravação é
-- responsabilidade da camada de aplicação (o GUC carrega os papéis do ator;
-- o actor_id autenticado vive na sessão do app).
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/010_payroll_periods_events.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. PAYROLL_PERIODS — RFC-006 §2 (competência)
-- ============================================================================
CREATE TABLE payroll_periods (
    id           BIGSERIAL PRIMARY KEY,
    reference    TEXT        NOT NULL UNIQUE,      -- ex.: '2026-08' (identificador estável p/ auditoria)
    year         SMALLINT    NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month        SMALLINT    NOT NULL CHECK (month BETWEEN 1 AND 12),
    kind         TEXT        NOT NULL DEFAULT 'mensal'
                 CHECK (kind IN ('mensal', 'complementar', 'decimo_terceiro',
                                 'ferias', 'adiantamento', 'rescisao')),
                                                   -- RFC-006 §6: folhas especiais são competências próprias
    status       TEXT        NOT NULL DEFAULT 'aberta'
                 CHECK (status IN ('aberta', 'em_calculo', 'calculada',
                                   'validada', 'fechada', 'paga')),
                                                   -- RFC-006 §2: máquina de estados da competência
    opened_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    calculated_at TIMESTAMPTZ,                     -- marco: transição → calculada
    validated_at TIMESTAMPTZ,                      -- marco: transição → validada
    closed_at    TIMESTAMPTZ,                      -- marco: transição → fechada
    paid_at      TIMESTAMPTZ,                      -- marco: transição → paga
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_period UNIQUE (year, month, kind)  -- RFC-006 §7 decisão 2: uma competência por mês/tipo
);

COMMENT ON TABLE  payroll_periods IS 'RFC-006 §2 — competência (período de folha) com máquina de estados: aberta → em_calculo → calculada → validada → fechada → paga';
COMMENT ON COLUMN payroll_periods.reference IS 'Identificador estável da competência (ex.: ''2026-08'') — usado no contexto da trilha de auditoria (RFC-009 §5)';
COMMENT ON COLUMN payroll_periods.kind IS 'Tipo de folha (RFC-006 §6): mensal, complementar (RFC-013), 13º, férias, adiantamento, rescisão — cada uma é uma competência própria';
COMMENT ON COLUMN payroll_periods.status IS 'Estado da máquina de estados (RFC-006 §2); fechada/paga são imutáveis (regra 1)';

CREATE TRIGGER trg_payroll_periods_updated_at
    BEFORE UPDATE ON payroll_periods
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ============================================================================
-- 2. PAYROLL_PERIOD_STATUS_TRANSITIONS — RFC-006 §4/§5 + RFC-009 §3.1
--    Tabela dirigida por dados: cada transição permitida e a AÇÃO da matriz
--    §3.1 exigida (required_action). O CHECK abaixo espelha a lista de ações
--    de permissions (db/011) — manter as duas em sincronia ao alterar a matriz.
-- ============================================================================
CREATE TABLE payroll_period_status_transitions (
    from_status     TEXT NOT NULL
                    CHECK (from_status IN ('aberta', 'em_calculo', 'calculada',
                                           'validada', 'fechada', 'paga')),
    to_status       TEXT NOT NULL
                    CHECK (to_status IN ('aberta', 'em_calculo', 'calculada',
                                         'validada', 'fechada', 'paga')),
    required_action TEXT NOT NULL
                    CHECK (required_action IN ('abrir_competencia', 'lancar_eventos',
                                               'calcular', 'validar', 'fechar',
                                               'registrar_pagamento', 'manter_cadastros',
                                               'manter_usuarios')),
                                                   -- AÇÃO da matriz RFC-009 §3.1 (db/011)
                                                   -- exigida na transição; a autorização é
                                                   -- resolvida por f_has_permission_guc()
    description     TEXT NOT NULL,
    PRIMARY KEY (from_status, to_status)
);

COMMENT ON TABLE payroll_period_status_transitions IS 'RFC-006 §4/§5 + RFC-009 §3.1 — transições permitidas da máquina de estados e a AÇÃO da matriz de permissões (db/011) exigida em cada uma; a sequência (regra 4) e a autorização (regra 5) são validadas por trigger via f_has_permission_guc';

-- Seed das transições (RFC-006 §3/§5 + RFC-009 §3.1). Cada transição aponta
-- a AÇÃO da matriz exigida; o papel é resolvido pela db/011 (f_has_permission_guc):
--   calcular=OPERADOR · validar=CONFERENTE · fechar=APROVADOR · registrar_pagamento=TESOURARIA
-- 'validada → calculada' (devolução) usa 'validar' porque é ato do CONFERENTE
-- que validou e encontrou inconsistência (RFC-015 §3.1).
INSERT INTO payroll_period_status_transitions (from_status, to_status, required_action, description) VALUES
    ('aberta',       'em_calculo', 'calcular',            'Iniciar processamento (calcular) — RFC-006 §3.2'),
    ('em_calculo',   'calculada',  'calcular',            'Cálculo concluído — valores prontos para conferência'),
    ('calculada',    'validada',   'validar',             'Revisar e validar — RFC-006 §3.3'),
    ('validada',     'fechada',    'fechar',              'Fechar competência — imutável a partir daqui (RFC-006 regra 1; RFC-009 §4.2 Aprovador ≠ Operador)'),
    ('fechada',      'paga',       'registrar_pagamento', 'Registrar pagamento — RFC-006 §3.3'),
    ('calculada',    'em_calculo', 'calcular',            'Recalcular † (correção — RFC-015 §3.1)'),
    ('validada',     'calculada',  'validar',             'Devolver p/ correção † (RFC-015 §3.1)');

-- ============================================================================
-- 2.1 MÁQUINA DE ESTADOS — triggers de enforcement
--     (a) abrir competência: exige a ação 'abrir_competencia' da matriz §3.1
--         (OPERADOR ou ADMINISTRADOR — resolvida pela db/011) e FORÇA status
--         inicial 'aberta' (regra 4 — nada de injetar estado no INSERT)
--     (b) transição: deve existir na tabela (RFC-006 regra 4) e a ação exigida
--         (required_action) deve ser autorizada ao ator pela matriz da db/011
--         via f_has_permission_guc (regra 5 — GUC app.actor_roles)
--     (c) fechada/paga imutáveis (regra 1) — exceção única: fechada → paga;
--         trigger em TODAS as colunas (um "OF status" não dispararia em
--         UPDATE que não menciona status, ex.: SET year)
--     (d) marcos temporais (calculated_at/validated_at/closed_at/paid_at)
-- ============================================================================
CREATE OR REPLACE FUNCTION enforce_period_open_role ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- RFC-009 §3.1 + RFC-006 regra 5: a autorização é resolvida pela MATRIZ
    -- de permissões (db/011) — ação 'abrir_competencia' (OPERADOR/ADMINISTRADOR).
    -- Fail-closed: GUC ausente/vazio → f_has_permission_guc() retorna FALSE.
    IF NOT f_has_permission_guc('abrir_competencia') THEN
        RAISE EXCEPTION 'Abrir competência exige a ação abrir_competencia (RFC-009 §3.1, via db/011); app.actor_roles = %',
            COALESCE(current_setting('app.actor_roles', true), '<não definido>');
    END IF;
    -- RFC-006 regra 4: toda competência nasce 'aberta'; o estado não pode ser
    -- injetado no INSERT (impede pular a máquina de estados)
    NEW.status := 'aberta';
    NEW.opened_at := now();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION enforce_period_status_machine ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_required_action TEXT;
BEGIN
    IF NEW.status = OLD.status THEN
        RETURN NEW;  -- sem transição de estado (ex.: atualização de metadados em competência aberta)
    END IF;

    -- (b1) a transição deve existir na tabela (RFC-006 regra 4 — estados sequenciais)
    SELECT required_action INTO v_required_action
      FROM payroll_period_status_transitions
     WHERE from_status = OLD.status AND to_status = NEW.status;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transição inválida de estado: % → % (RFC-006 regra 4 — estados sequenciais)',
            OLD.status, NEW.status;
    END IF;

    -- (b2) autorização: a ação exigida (required_action) precisa ser autorizada
    --      ao ator pela MATRIZ de permissões da db/011 (RFC-009 §3.1, regra 5).
    --      f_has_permission_guc é fail-closed (GUC ausente/vazio → FALSE).
    IF NOT f_has_permission_guc(v_required_action) THEN
        RAISE EXCEPTION 'Transição % → % exige a ação % (RFC-009 §3.1, via db/011); app.actor_roles = %',
            OLD.status, NEW.status, v_required_action,
            COALESCE(current_setting('app.actor_roles', true), '<não definido>');
    END IF;

    -- (d) marcos temporais do estado de destino
    IF NEW.status = 'calculada' THEN
        NEW.calculated_at := now();
    ELSIF NEW.status = 'validada' THEN
        NEW.validated_at := now();
    ELSIF NEW.status = 'fechada' THEN
        NEW.closed_at := now();
    ELSIF NEW.status = 'paga' THEN
        NEW.paid_at := now();
    END IF;

    RETURN NEW;
END;
$$;

-- (c) imutabilidade de fechada/paga em trigger de UPDATE de TODAS as colunas:
--     o "BEFORE UPDATE OF status" só dispararia se status estivesse no SET,
--     então um UPDATE de outra coluna (ex.: year) não passaria pela regra 1.
CREATE OR REPLACE FUNCTION enforce_period_immutability ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- exceção única: fechada → paga (registro do pagamento, RFC-006 §3.3)
    IF OLD.status IN ('fechada', 'paga')
       AND NOT (OLD.status = 'fechada' AND NEW.status = 'paga') THEN
        RAISE EXCEPTION 'Competência % é imutável (RFC-006 regra 1): correções via folha complementar (RFC-013)',
            OLD.status;
    END IF;
    -- blindagem: mesmo na transição fechada → paga, as colunas de negócio
    -- (reference/year/month/kind) não podem mudar — só status e marcos
    IF OLD.status = 'fechada' AND NEW.status = 'paga'
       AND (   NEW.reference IS DISTINCT FROM OLD.reference
            OR NEW.year      IS DISTINCT FROM OLD.year
            OR NEW.month     IS DISTINCT FROM OLD.month
            OR NEW.kind      IS DISTINCT FROM OLD.kind) THEN
        RAISE EXCEPTION 'Competência fechada é imutável (RFC-006 regra 1): colunas de negócio não podem mudar na transição fechada → paga';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_payroll_periods_immutable
    BEFORE UPDATE ON payroll_periods
    FOR EACH ROW EXECUTE FUNCTION enforce_period_immutability ();

CREATE TRIGGER trg_payroll_periods_open_role
    BEFORE INSERT ON payroll_periods
    FOR EACH ROW EXECUTE FUNCTION enforce_period_open_role ();

CREATE TRIGGER trg_payroll_periods_status_machine
    BEFORE UPDATE OF status ON payroll_periods
    FOR EACH ROW EXECUTE FUNCTION enforce_period_status_machine ();

-- ============================================================================
-- 3. PAYROLL_EVENTS — RFC-004 §2/§3 (catálogo de proventos e descontos)
-- ============================================================================
CREATE TABLE payroll_events (
    id             BIGSERIAL PRIMARY KEY,
    code           INTEGER     NOT NULL UNIQUE,    -- identificador numérico único (RFC-004 §2)
    description    TEXT        NOT NULL,           -- nome exibido no holerite (RFC-007)
    event_type     TEXT        NOT NULL
                   CHECK (event_type IN ('provento', 'desconto', 'informativo')),
                                                   -- RFC-004 §2 + decisão 1 (informativo existe)
    category       TEXT        NOT NULL,           -- remuneração, encargo, benefício, dedução, verba rescisória (RFC-004 §2)
    ref_unit       TEXT        NOT NULL,           -- grandeza que alimenta o cálculo: valor_fixo, horas,
                                                   -- percentual, valor, cota, periodo, automatica (RFC-004 §2)
    calc_rule      TEXT,                           -- fórmula/regra de cálculo (RFC-004 §4)
    incide_inss    BOOLEAN     NOT NULL DEFAULT FALSE,  -- compõe a base INSS (RFC-004 §5)
    incide_irrf    BOOLEAN     NOT NULL DEFAULT FALSE,  -- compõe a base IRRF (RFC-004 §5)
    incide_fgts    BOOLEAN     NOT NULL DEFAULT FALSE,  -- compõe a base FGTS (RFC-004 §5)
    calc_order     INTEGER     NOT NULL DEFAULT 0, -- ordem de cálculo (RFC-004 §2/§4 regra 8):
                                                   -- proventos → INSS → IRRF → demais descontos → líquido
    usage_payroll  TEXT        NOT NULL DEFAULT 'mensal'
                   CHECK (usage_payroll IN ('mensal', 'rescisao', 'decimo_terceiro',
                                            'ferias', 'todos')),
                                                   -- uso (RFC-004 §2): mensal, rescisão, 13º, férias — ou todos
    cap_value      NUMERIC(12,2)
                   CHECK (cap_value IS NULL OR cap_value >= 0),
                                                   -- teto no evento (RFC-004 §6 decisão 3): descontos com
                                                   -- limite carregam o teto e o cálculo o respeita
    valid_from     DATE,                           -- vigência inicial (RFC-004 §2)
    valid_until    DATE,                           -- vigência final / descontinuação (RFC-004 §2)
    status         TEXT        NOT NULL DEFAULT 'ativo'
                   CHECK (status IN ('ativo', 'inativo')),
                                                   -- inativação lógica (padrão do projeto — RFC-008 decisão 4)
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_event_validity CHECK (valid_from IS NULL OR valid_until IS NULL
                                        OR valid_until >= valid_from)
);

COMMENT ON TABLE  payroll_events IS 'RFC-004 — catálogo de eventos (proventos/descontos/informativos) aplicados na folha (RFC-006) e exibidos no holerite (RFC-007)';
COMMENT ON COLUMN payroll_events.code IS 'Código numérico único (RFC-004 §3): 1–10 proventos, 20–28 descontos';
COMMENT ON COLUMN payroll_events.event_type IS 'Provento (crédito), desconto (débito) ou informativo (RFC-004 decisão 1)';
COMMENT ON COLUMN payroll_events.incide_inss IS 'Se o valor compõe a base INSS (RFC-004 §5)';
COMMENT ON COLUMN payroll_events.incide_irrf IS 'Se o valor compõe a base IRRF (RFC-004 §5)';
COMMENT ON COLUMN payroll_events.incide_fgts IS 'Se o valor compõe a base FGTS (RFC-004 §5)';
COMMENT ON COLUMN payroll_events.calc_order IS 'Ordem de cálculo (RFC-004 §4 regra 8): proventos → base INSS → INSS → base IRRF → IRRF → demais descontos → líquido';
COMMENT ON COLUMN payroll_events.cap_value IS 'Teto do evento (RFC-004 §6 decisão 3) — ex.: VT limitado ao custo real do transporte';

CREATE TRIGGER trg_payroll_events_updated_at
    BEFORE UPDATE ON payroll_events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ----------------------------------------------------------------------------
-- Seed do catálogo inicial (RFC-004 §3 — folha mensal). Incidências:
--   Salário-Família NÃO incide INSS/IRRF/FGTS (RFC-004 §5);
--   Periculosidade incide nas três bases (RFC-004 §5).
-- ----------------------------------------------------------------------------
INSERT INTO payroll_events
    (code, description, event_type, category, ref_unit, calc_rule,
     incide_inss, incide_irrf, incide_fgts, calc_order, usage_payroll) VALUES
    -- 3.1 Proventos
    (1,  'Salário Base',            'provento', 'remuneracao', 'valor_fixo',
     'Valor informado no cadastro do funcionário (RFC-002 §2.5)', TRUE, TRUE, TRUE, 10, 'mensal'),
    (2,  'Horas Extras 50%',        'provento', 'remuneracao', 'horas',
     'Valor da hora normal × qtd × 1,5 (RFC-004 §4 regra 4)', TRUE, TRUE, TRUE, 11, 'mensal'),
    (3,  'Horas Extras 100%',       'provento', 'remuneracao', 'horas',
     'Valor da hora normal × qtd × 2,0 (RFC-004 §4 regra 4)', TRUE, TRUE, TRUE, 12, 'mensal'),
    (4,  'Adicional Noturno',       'provento', 'remuneracao', 'horas',
     'Valor da hora × horas noturnas (22h–5h)', TRUE, TRUE, TRUE, 13, 'mensal'),
    (5,  'Adicional de Insalubridade', 'provento', 'remuneracao', 'percentual',
     'Percentual 10/20/40% sobre a base, conforme grau', TRUE, TRUE, TRUE, 14, 'mensal'),
    (6,  'Adicional de Periculosidade', 'provento', 'remuneracao', 'percentual',
     '30% sobre o salário base', TRUE, TRUE, TRUE, 15, 'mensal'),
    (7,  'Comissão / Vendas',       'provento', 'remuneracao', 'valor',
     'Valor ou percentual conforme política', TRUE, TRUE, TRUE, 16, 'mensal'),
    (8,  'DSR (descanso semanal)',  'provento', 'remuneracao', 'valor',
     'Reflexo de horas extras no descanso semanal', TRUE, TRUE, TRUE, 17, 'mensal'),
    (9,  'Salário-Família',         'provento', 'beneficio', 'cota',
     'Cotas × valor da cota (tabela RFC-005)', FALSE, FALSE, FALSE, 18, 'mensal'),
    (10, 'Férias + 1/3',            'provento', 'remuneracao', 'periodo',
     'Férias + 1/3 constitucional (competência de férias); férias gozadas incidem, 1/3 isento — tratado no cálculo',
     TRUE, TRUE, TRUE, 19, 'ferias'),
    -- 3.2 Descontos
    (20, 'INSS',                    'desconto', 'encargo', 'automatica',
     'Tabela progressiva INSS sobre a base INSS (RFC-005 §3.2)', FALSE, FALSE, FALSE, 20, 'mensal'),
    (21, 'IRRF',                    'desconto', 'encargo', 'automatica',
     'Tabela progressiva IRRF sobre a base IRRF (RFC-005 §3.3)', FALSE, FALSE, FALSE, 21, 'mensal'),
    (22, 'Vale-Transporte',         'desconto', 'beneficio', 'percentual',
     '6% do salário base, limitado ao custo real do transporte (RFC-004 §4 regra 7; decisão 3)', FALSE, FALSE, FALSE, 30, 'mensal'),
    (23, 'Vale-Refeição',           'desconto', 'beneficio', 'valor',
     'Valor ou % de participação', FALSE, FALSE, FALSE, 31, 'mensal'),
    (24, 'Plano de Saúde',          'desconto', 'beneficio', 'valor',
     'Valor da coparticipação', FALSE, FALSE, FALSE, 32, 'mensal'),
    (25, 'Faltas / Atrasos',        'desconto', 'deducao', 'horas',
     'Valor do dia/hora × qtd (RFC-004 §4 regras 2–3)', FALSE, FALSE, FALSE, 33, 'mensal'),
    (26, 'Adiantamento',            'desconto', 'deducao', 'valor',
     'Valor do adiantamento concedido', FALSE, FALSE, FALSE, 34, 'mensal'),
    (27, 'Pensão Alimentícia',      'desconto', 'deducao', 'percentual',
     '% ou valor fixo conforme decisão judicial', FALSE, FALSE, FALSE, 35, 'mensal'),
    (28, 'Contribuição Sindical',   'desconto', 'encargo', 'valor',
     'Valor da contribuição, quando aplicável', FALSE, FALSE, FALSE, 36, 'mensal');

-- ============================================================================
-- Índices de consulta
-- ============================================================================
CREATE INDEX idx_payroll_periods_status ON payroll_periods (status);
CREATE INDEX idx_payroll_events_type    ON payroll_events (event_type);
CREATE INDEX idx_payroll_events_status  ON payroll_events (status);

COMMIT;
