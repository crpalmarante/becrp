-- ============================================================================
-- db/012_payroll_runs_lines.sql
-- RFC-006 — Processamento da Folha (v1.0.0 · Draft em revisão)
--           RFC-007 — Holerite (v1.0.0 · Draft em revisão)
--           RFC-015 — Relatórios e Fechamento (v1.0.0 · Draft em revisão)
-- ----------------------------------------------------------------------------
-- Cria a EXECUÇÃO do processamento e o RESULTADO POR FUNCIONÁRIO (PLAN_ERP §7.4):
--   payroll_runs   (RFC-006 §3.2) — uma execução do cálculo de uma competência.
--                                   Cada recálculo (calculada → em_calculo,
--                                   RFC-015 §3.1) abre UMA NOVA execução com
--                                   run_number sequencial — histórico auditável
--                                   (RFC-006 regra 3: todo valor tem origem).
--   payroll_lines  (RFC-006 §3.2 + RFC-007 §2.4/§2.5) — resultado consolidado
--                                   por funcionário de uma execução: bases de
--                                   cálculo, INSS, IRRF, proventos, descontos e
--                                   o líquido — matéria-prima do holerite
--                                   (RFC-007) e do resumo por funcionário
--                                   (RFC-015 §2).
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- Pré-requisitos:
--   db/002 (employees/departments/positions) — employees(id) + set_updated_at()
--   db/010 (payroll_periods)                 — payroll_periods(id) (competência)
--   db/011 (permissions)                     — f_has_permission_guc()
-- Ordem: 002 → 009 → 011 → 010 → 012.
--
-- AUTORIZAÇÃO POR AÇÃO (RFC-009 §3.1 via db/011 — autoridade única):
--   Escrever execução/resultado é ATO DE CÁLCULO → f_has_permission_guc('calcular')
--   (OPERADOR). O GUC de sessão é obrigatório (fail-closed):
--     SET app.actor_roles = 'OPERADOR';
--   Conferente/Aprovador/Tesouraria/Admin NÃO escrevem resultado — só o Operador
--   calcula (RFC-006 §5). A identidade real do ator vive no audit_log (RFC-009
--   §5, camada de aplicação — o GUC carrega papéis, não o actor_id).
--
-- INVARIANTES PROTEGIDAS POR TRIGGER:
--   (1) Execução/resultado só são ESCRITOS com a competência 'aberta' ou
--       'em_calculo' — de 'calculada' em diante congela (RFC-006 regra 1);
--       recálculo volta a 'em_calculo' e abre NOVA execução (run_number+1).
--   (2) Funcionário 'desligado' não entra em processamento novo (RFC-002
--       §3 regra 5 → RFC-003).
--   (3) Líquido = proventos − descontos (RFC-007 regra 3) — CHECK no banco.
--   (4) Nenhuma exclusão física de execução/resultado (rastreabilidade
--       RFC-001 regra 4 / RFC-015 regra 3; padrão RFC-008 decisão 4).
--   (5) Resultado só entra em execução EM PROCESSAMENTO (status 'em_calculo')
--       — nada de gravar em run calculada/cancelada. A competência vira
--       'calculada' apenas com a run vigente 'calculada' (orquestração da
--       aplicação: a máquina de estados da 010 não enxerga payroll_runs).
--
-- Fora do escopo (migration de acompanhamento): o DETALHAMENTO POR EVENTO do
-- holerite (RFC-007 §2.2/§2.3 — código/descrição/referência/valor por evento)
-- será tabela própria (payroll_entries) ligando funcionário × payroll_events;
-- aqui o resultado é consolidado por funcionário.
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/012_payroll_runs_lines.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. PAYROLL_RUNS — RFC-006 §3.2 (execução do processamento)
--    Uma linha por execução do cálculo de uma competência. O estado da máquina
--    de estados fica na competência (payroll_periods, db/010); aqui guardamos
--    o CICLO de processamento (1ª execução, recálculos...) com seus marcos.
-- ============================================================================
CREATE TABLE payroll_runs (
    id            BIGSERIAL PRIMARY KEY,
    period_id     BIGINT      NOT NULL REFERENCES payroll_periods (id) ON DELETE RESTRICT,
                                                             -- competência processada (RFC-006 §2)
    run_number    INTEGER     NOT NULL,                      -- 1ª execução, 2ª (recálculo)...
    status        TEXT        NOT NULL DEFAULT 'em_calculo'
                  CHECK (status IN ('em_calculo', 'calculada', 'cancelada')),
                                                             -- em_calculo → calculada | cancelada
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),        -- início do processamento
    calculated_at TIMESTAMPTZ,                               -- marco: valores prontos (calculada)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_run_per_period UNIQUE (period_id, run_number)
);

COMMENT ON TABLE  payroll_runs IS 'RFC-006 §3.2 — execução do processamento de uma competência; cada recálculo (RFC-015 §3.1) abre nova execução (run_number) preservando o histórico auditável (RFC-006 regra 3)';
COMMENT ON COLUMN payroll_runs.period_id IS 'Competência processada (payroll_periods da db/010)';
COMMENT ON COLUMN payroll_runs.run_number IS 'Nº da execução (1ª, 2ª recálculo...) — UNIQUE por competência; a execução vigente é a de maior run_number';
COMMENT ON COLUMN payroll_runs.status IS 'Estado da execução: em_calculo → calculada (valores prontos) | cancelada (execução abandonada/superada)';

-- ============================================================================
-- 2. PAYROLL_LINES — RFC-006 §3.2 + RFC-007 §2.4/§2.5 (resultado por funcionário)
--    Uma linha por funcionário por execução: o RESULTADO do cálculo consolidado
--    (bases + encargos + totais + líquido) — o que o holerite (RFC-007) exibe
--    e o resumo por funcionário (RFC-015 §2) consolida.
-- ============================================================================
CREATE TABLE payroll_lines (
    id              BIGSERIAL PRIMARY KEY,
    run_id          BIGINT        NOT NULL REFERENCES payroll_runs (id) ON DELETE RESTRICT,
                                                             -- execução que produziu o resultado
    employee_id     BIGINT        NOT NULL REFERENCES employees (id) ON DELETE RESTRICT,
                                                             -- funcionário (RFC-002)
    base_salary     NUMERIC(12,2) NOT NULL
                    CHECK (base_salary >= 0),                -- salário de referência SNAPSHOT
                                                             -- (RFC-006 regra 2: tabela da competência,
                                                             -- não o cadastro do dia)
    total_proventos NUMERIC(12,2) NOT NULL DEFAULT 0
                    CHECK (total_proventos >= 0),            -- soma dos créditos (RFC-007 §2.5)
    total_descontos NUMERIC(12,2) NOT NULL DEFAULT 0
                    CHECK (total_descontos >= 0),            -- soma dos débitos (RFC-007 §2.5)
    base_inss       NUMERIC(12,2) NOT NULL DEFAULT 0
                    CHECK (base_inss >= 0),                  -- base INSS (RFC-006 §3.2 passo 7)
    inss            NUMERIC(12,2) NOT NULL DEFAULT 0
                    CHECK (inss >= 0),                       -- INSS calculado (RFC-006 §3.2 passo 8)
    base_irrf       NUMERIC(12,2) NOT NULL DEFAULT 0
                    CHECK (base_irrf >= 0),                  -- base IRRF (RFC-006 §3.2 passo 9)
    irrf            NUMERIC(12,2) NOT NULL DEFAULT 0
                    CHECK (irrf >= 0),                       -- IRRF calculado (RFC-006 §3.2 passo 10)
    base_fgts       NUMERIC(12,2) NOT NULL DEFAULT 0
                    CHECK (base_fgts >= 0),                  -- base FGTS (RFC-007 §2.4) — o encargo
                                                             -- de 8% é do empregador e sai no
                                                             -- relatório de encargos (RFC-014)
    liquid_value    NUMERIC(12,2) NOT NULL DEFAULT 0,        -- líquido a receber (RFC-007 §2.5)
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT uq_line_per_employee UNIQUE (run_id, employee_id),
    CONSTRAINT ck_liquid_equation CHECK (liquid_value = total_proventos - total_descontos)
                                                             -- RFC-007 regra 3: líquido = proventos − descontos
);

COMMENT ON TABLE  payroll_lines IS 'RFC-006 §3.2 + RFC-007 §2.4/§2.5 — resultado consolidado por funcionário de uma execução: bases, INSS/IRRF, proventos, descontos e líquido; matéria-prima do holerite (RFC-007) e do resumo por funcionário (RFC-015)';
COMMENT ON COLUMN payroll_lines.base_salary IS 'Salário de referência SNAPSHOT usado no cálculo (RFC-006 regra 2 — a folha usa a tabela da competência, não o cadastro do dia)';
COMMENT ON COLUMN payroll_lines.base_fgts IS 'Base FGTS (RFC-007 §2.4); o encargo de 8% é do empregador e sai no relatório de encargos (RFC-014)';
COMMENT ON COLUMN payroll_lines.liquid_value IS 'Líquido a receber = total_proventos − total_descontos (RFC-007 regra 3) — CHECK no banco';

CREATE TRIGGER trg_payroll_runs_updated_at
    BEFORE UPDATE ON payroll_runs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

CREATE TRIGGER trg_payroll_lines_updated_at
    BEFORE UPDATE ON payroll_lines
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ============================================================================
-- 3. TRIGGERS DE ENFORCEMENT
--     (a) executar a folha (INSERT/UPDATE de payroll_runs) → ação 'calcular'
--         (RFC-009 §3.1 via db/011); nova execução nasce 'em_calculo' com
--         run_number sequencial; só com competência aberta/em_calculo
--     (b) gravar resultado (INSERT/UPDATE de payroll_lines) → ação 'calcular';
--         competência aberta/em_calculo; funcionário não desligado
--     (c) sem exclusão física (DELETE/TRUNCATE) — rastreabilidade
-- ============================================================================
CREATE OR REPLACE FUNCTION enforce_run_permission ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_period_status TEXT;
    v_period_ref    TEXT;
BEGIN
    -- (a1) RFC-009 §3.1 via db/011: escrever execução é ato de cálculo (OPERADOR).
    --      f_has_permission_guc é fail-closed (GUC ausente/vazio → FALSE).
    IF NOT f_has_permission_guc('calcular') THEN
        RAISE EXCEPTION 'Escrever payroll_runs exige a ação calcular (RFC-009 §3.1, via db/011); app.actor_roles = %',
            COALESCE(current_setting('app.actor_roles', true), '<não definido>');
    END IF;

    SELECT status, reference INTO v_period_status, v_period_ref
      FROM payroll_periods WHERE id = NEW.period_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Competência inexistente (period_id = %)', NEW.period_id;
    END IF;

    -- (a2) invariant 1: competência aberta/em_calculo aceita escrita
    IF v_period_status NOT IN ('aberta', 'em_calculo') THEN
        RAISE EXCEPTION 'Competência % (estado %) não aceita execução (RFC-006 regra 1): só aberta/em_calculo; correções via recálculo ou folha complementar (RFC-013)',
            v_period_ref, v_period_status;
    END IF;

    IF TG_OP = 'INSERT' THEN
        -- (a3) toda execução nasce 'em_calculo'; run_number sequencial por
        --      competência (RFC-015 §3.1 — recálculo = nova execução)
        SELECT COALESCE(MAX(run_number), 0) + 1 INTO NEW.run_number
          FROM payroll_runs WHERE period_id = NEW.period_id;
        NEW.status := 'em_calculo';
        NEW.started_at := now();
    ELSE
        IF NEW.status = OLD.status THEN
            RETURN NEW;  -- atualização de metadados, sem transição
        END IF;
        -- (a4) transições válidas: em_calculo → calculada | em_calculo → cancelada
        IF NOT (OLD.status = 'em_calculo' AND NEW.status IN ('calculada', 'cancelada')) THEN
            RAISE EXCEPTION 'Transição de execução inválida: % → % (valores prontos em calculada; nova correção abre NOVA execução)', OLD.status, NEW.status;
        END IF;
        IF NEW.status = 'calculada' THEN
            NEW.calculated_at := now();
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION enforce_line_permission ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_period_status TEXT;
    v_period_ref    TEXT;
    v_run_status    TEXT;
    v_emp_status    TEXT;
BEGIN
    -- (b1) RFC-009 §3.1 via db/011: gravar resultado é ato de cálculo (OPERADOR)
    IF NOT f_has_permission_guc('calcular') THEN
        RAISE EXCEPTION 'Escrever payroll_lines exige a ação calcular (RFC-009 §3.1, via db/011); app.actor_roles = %',
            COALESCE(current_setting('app.actor_roles', true), '<não definido>');
    END IF;

    -- (b2) estado da competência da execução + estado da própria execução
    --      + situação do funcionário
    SELECT pp.status, pp.reference, pr.status, e.employment_status
      INTO v_period_status, v_period_ref, v_run_status, v_emp_status
      FROM payroll_runs pr
      JOIN payroll_periods pp ON pp.id = pr.period_id
      JOIN employees e       ON e.id = NEW.employee_id
     WHERE pr.id = NEW.run_id;

    IF v_period_status IS NULL OR v_emp_status IS NULL THEN
        RAISE EXCEPTION 'Execução (run_id = %) ou funcionário (employee_id = %) inexistente', NEW.run_id, NEW.employee_id;
    END IF;
    IF v_period_status NOT IN ('aberta', 'em_calculo') THEN
        RAISE EXCEPTION 'Competência % (estado %) não aceita resultado (RFC-006 regra 1): só aberta/em_calculo; correções via recálculo ou folha complementar (RFC-013)',
            v_period_ref, v_period_status;
    END IF;
    -- (b2b) resultado só entra em execução EM PROCESSAMENTO (não calculada/cancelada)
    IF v_run_status <> 'em_calculo' THEN
        RAISE EXCEPTION 'Execução % está % — resultado só é gravado em execução em_calculo', NEW.run_id, v_run_status;
    END IF;
    -- (b3) RFC-002 §3 regra 5: desligado bloqueia novos processamentos
    IF v_emp_status = 'desligado' THEN
        RAISE EXCEPTION 'Funcionário desligado não entra em processamento novo (RFC-002 §3 regra 5 → RFC-003)';
    END IF;

    RETURN NEW;
END;
$$;

-- (c) sem exclusão física — o resultado da folha é imutável por delete
--     (rastreabilidade RFC-001 regra 4 / RFC-015 regra 3; padrão RFC-008
--     decisão 4: inativação/correção, nunca apagar). Cobre DELETE e TRUNCATE
--     (triggers de linha NÃO disparam em TRUNCATE — por isso statement-level).
CREATE OR REPLACE FUNCTION prevent_payroll_delete ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Exclusão física de payroll_runs/payroll_lines proibida (RFC-015 regra 3 — rastreabilidade): resultado só se corrige por novo processamento (recálculo)';
END;
$$;

CREATE TRIGGER trg_payroll_runs_permission
    BEFORE INSERT OR UPDATE ON payroll_runs
    FOR EACH ROW EXECUTE FUNCTION enforce_run_permission ();

CREATE TRIGGER trg_payroll_lines_permission
    BEFORE INSERT OR UPDATE ON payroll_lines
    FOR EACH ROW EXECUTE FUNCTION enforce_line_permission ();

CREATE TRIGGER trg_payroll_runs_no_delete
    BEFORE DELETE ON payroll_runs
    FOR EACH ROW EXECUTE FUNCTION prevent_payroll_delete ();

CREATE TRIGGER trg_payroll_runs_no_truncate
    BEFORE TRUNCATE ON payroll_runs
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_payroll_delete ();

CREATE TRIGGER trg_payroll_lines_no_delete
    BEFORE DELETE ON payroll_lines
    FOR EACH ROW EXECUTE FUNCTION prevent_payroll_delete ();

CREATE TRIGGER trg_payroll_lines_no_truncate
    BEFORE TRUNCATE ON payroll_lines
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_payroll_delete ();

REVOKE DELETE, TRUNCATE ON payroll_runs, payroll_lines FROM PUBLIC;

-- ============================================================================
-- Índices de consulta
-- ============================================================================
CREATE INDEX idx_payroll_runs_period    ON payroll_runs (period_id, run_number);
CREATE INDEX idx_payroll_lines_run      ON payroll_lines (run_id);
CREATE INDEX idx_payroll_lines_employee ON payroll_lines (employee_id);

COMMIT;
