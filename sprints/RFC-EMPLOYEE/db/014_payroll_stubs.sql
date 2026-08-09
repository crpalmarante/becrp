-- ============================================================================
-- db/014_payroll_stubs.sql
-- RFC-007 — Holerite (v1.0.0 · Draft em revisão)
-- ----------------------------------------------------------------------------
-- Cria o DEMONSTRATIVO DE PAGAMENTO — o holerite como documento:
--   payroll_stubs (RFC-007 §2) — o DOCUMENTO emitido por funcionário × execução,
--                                 com o cabeçalho do RFC-007 §2.1 CONGELADO
--                                 (snapshot) e a referência ao resultado que o
--                                 originou:
--     run_id    → payroll_runs   (RFC-006 §3.2 — a execução que produziu o valor)
--     line_id   → payroll_lines  (RFC-006 §3.2 + RFC-007 §2.4/§2.5 — o resultado
--                                  consolidado por funcionário; UNIQUE — um
--                                  holerite por resultado, sem duplicidade)
--   Os valores monetários (bases, INSS/IRRF, proventos, descontos, líquido)
--   NÃO são duplicados aqui: o holerite os lê da payroll_lines referenciada
--   (que já é a matéria-prima do RFC-007 — ver db/012) — rastreabilidade
--   RFC-007 regra 2 (do holerite ao resultado e ao evento).
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- Pré-requisitos:
--   db/002 (employees/positions/departments) — cabeçalho (RFC-007 §2.1) + set_updated_at()
--   db/010 (payroll_periods)                 — competência (period_reference)
--   db/011 (permissions)                     — f_has_permission_guc()
--   db/012 (payroll_runs/payroll_lines)      — execução e resultado por funcionário
-- Ordem: 002 → 009 → 011 → 010 → 012 → 014.
--
-- AUTORIZAÇÃO POR AÇÃO (RFC-009 §3.1 via db/011 — autoridade única):
--   Emitir holerite é ATO DE PROCESSAMENTO → f_has_permission_guc('calcular')
--   (OPERADOR). O GUC de sessão é obrigatório (fail-closed):
--     SET app.actor_roles = 'OPERADOR';
--   Conferente/Aprovador/Tesouraria/Admin consultam (SELECT) — a emissão é do
--   Operador, que produziu o resultado (RFC-006 §5). A identidade real do ator
--   vive no audit_log (RFC-009 §5, camada de aplicação).
--
-- INVARIANTES PROTEGIDAS POR TRIGGER:
--   (1) O holerite só é emitido de execução CALCULADA (valores prontos e
--       congelados — RFC-006 regra 1); nada de documento de execução em
--       processamento (em_calculo) nem cancelada.
--   (2) A linha deve PERTENCER à execução informada (run_id = line.run_id).
--   (3) NADA é digitado no holerite (RFC-007 regra 1): o cabeçalho é SNAPSHOT
--       tirado do cadastro no momento da emissão — regenerar o documento
--       reproduz EXATAMENTE os mesmos valores (RFC-007 regra 4).
--   (4) Holerite IMUTÁVEL (RFC-007 regra 4): sem UPDATE/DELETE/TRUNCATE.
--       Correção/regeneração = NOVO processamento (recálculo → nova execução
--       → nova linha → novo holerite), preservando o histórico (RFC-006 regra
--       3 / RFC-015 regra 3). Por isso NÃO há updated_at aqui.
--   (5) Um holerite por resultado (UNIQUE line_id) — re-emissão = nova linha.
--
-- Fora do escopo (migration de acompanhamento): o DETALHAMENTO POR EVENTO do
-- corpo do holerite (RFC-007 §2.2/§2.3 — código/descrição/referência/valor por
-- evento) será tabela própria (payroll_entries) ligando funcionário ×
-- payroll_events (já previsto na db/012); aqui o documento é o consolidado.
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/014_payroll_stubs.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. PAYROLL_STUBS — RFC-007 §2 (documento do holerite)
--    Uma linha por resultado de execução (line_id UNIQUE). O cabeçalho é
--    snapshot (§2.1 — RFC-002); os valores monetários vêm da payroll_lines
--    referenciada (não duplicados — regra 2). Imutável (regra 4).
-- ============================================================================
CREATE TABLE payroll_stubs (
    id                     BIGSERIAL PRIMARY KEY,
    run_id                 BIGINT        NOT NULL REFERENCES payroll_runs (id) ON DELETE RESTRICT,
                                                             -- execução que produziu o valor (RFC-006 §3.2)
    line_id                BIGINT        NOT NULL REFERENCES payroll_lines (id) ON DELETE RESTRICT,
                                                             -- resultado consolidado por funcionário (RFC-007 §2.4/§2.5)
    period_reference       TEXT          NOT NULL
                           CHECK (period_reference ~ '^[0-9]{4}-[0-9]{2}$'),
                                                             -- competência do documento (RFC-007 §2.1) — snapshot
    employee_full_name     TEXT          NOT NULL,           -- nome (RFC-007 §2.1 — snapshot RFC-002)
    employee_cpf           TEXT          NOT NULL
                           CHECK (employee_cpf ~ '^[0-9]{11}$'),
                                                             -- CPF (RFC-007 §2.1) — snapshot; consulta do
                                                             -- autoatendimento (RFC-007 decisão 3)
    admission_date         DATE          NOT NULL,           -- data de admissão (RFC-007 §2.1) — snapshot
    position_description   TEXT          NOT NULL,           -- cargo (RFC-007 §2.1) — snapshot
    department_description TEXT          NOT NULL,           -- departamento (RFC-007 §2.1) — snapshot
    notes                  TEXT,                             -- observações livres (RFC-007 decisão 2) — opcional,
                                                             -- preenchido na emissão (documento imutável)
    issued_at              TIMESTAMPTZ   NOT NULL DEFAULT now(),  -- marco de emissão (regra 4: mesmo valor ao regenerar)
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT uq_stub_per_line UNIQUE (line_id)
                                                             -- um holerite por resultado (invariante 5)
);

COMMENT ON TABLE  payroll_stubs IS 'RFC-007 §2 — documento do holerite: cabeçalho congelado (snapshot §2.1) + referência à execução (run) e ao resultado por funcionário (line); imutável (regra 4)' ;
COMMENT ON COLUMN payroll_stubs.run_id IS 'Execução do processamento que produziu o valor (payroll_runs da db/012)' ;
COMMENT ON COLUMN payroll_stubs.line_id IS 'Resultado consolidado por funcionário (payroll_lines da db/012) — fonte dos valores monetários exibidos (RFC-007 regra 2); UNIQUE: um holerite por resultado' ;
COMMENT ON COLUMN payroll_stubs.period_reference IS 'Competência do documento (RFC-007 §2.1) — snapshot no formato YYYY-MM' ;
COMMENT ON COLUMN payroll_stubs.employee_cpf IS 'CPF do funcionário (RFC-007 §2.1) — snapshot; usado na consulta do autoatendimento (RFC-007 decisão 3)' ;
COMMENT ON COLUMN payroll_stubs.position_description IS 'Cargo no momento da emissão (RFC-007 §2.1) — snapshot (RFC-008 regra 1)' ;
COMMENT ON COLUMN payroll_stubs.department_description IS 'Departamento no momento da emissão (RFC-007 §2.1) — snapshot' ;
COMMENT ON COLUMN payroll_stubs.notes IS 'Observações livres por holerite (RFC-007 decisão 2) — opcional; fixado na emissão (documento imutável)' ;
COMMENT ON COLUMN payroll_stubs.issued_at IS 'Marco de emissão — regenerar o documento reproduz o mesmo valor (RFC-007 regra 4)' ;

-- ============================================================================
-- 2. TRIGGERS DE ENFORCEMENT
--    (a) emitir holerite (INSERT) → ação 'calcular' (RFC-009 §3.1 via db/011);
--        linha pertence à execução; execução CALCULADA; snapshot do cabeçalho
--    (b) imutabilidade (UPDATE/DELETE/TRUNCATE) — RFC-007 regra 4
-- ============================================================================
CREATE OR REPLACE FUNCTION enforce_stub_emission ( )
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_run_status      TEXT;
    v_period_ref      TEXT;
    v_line_run        BIGINT;
    v_full_name       TEXT;
    v_cpf             TEXT;
    v_admission       DATE;
    v_position        TEXT;
    v_department      TEXT;
BEGIN
    -- (a1) RFC-009 §3.1 via db/011: emitir holerite é ato de processamento
    --      (ação 'calcular' — OPERADOR). Fail-closed (GUC ausente → FALSE).
    IF NOT f_has_permission_guc('calcular') THEN
        RAISE EXCEPTION 'Emitir holerite exige a ação calcular (RFC-009 §3.1, via db/011); app.actor_roles = %',
            COALESCE(current_setting('app.actor_roles', true), '<não definido>');
    END IF;

    -- (a2) a linha deve existir e PERTENCER à execução informada (invariante 2);
    --      o join já traz o estado da execução e o cadastro p/ o snapshot
    SELECT pr.status, pp.reference, pl.run_id, e.full_name, e.cpf,
           e.admission_date, pos.description, dep.description
      INTO v_run_status, v_period_ref, v_line_run, v_full_name, v_cpf,
           v_admission, v_position, v_department
      FROM payroll_lines pl
      JOIN payroll_runs pr        ON pr.id = pl.run_id
      JOIN payroll_periods pp     ON pp.id = pr.period_id
      JOIN employees e            ON e.id = pl.employee_id
      JOIN positions pos          ON pos.id = e.position_id
      JOIN departments dep        ON dep.id = e.department_id
     WHERE pl.id = NEW.line_id;

    IF v_run_status IS NULL THEN
        RAISE EXCEPTION 'Linha de resultado inexistente (line_id = %)', NEW.line_id;
    END IF;
    IF v_line_run <> NEW.run_id THEN
        RAISE EXCEPTION 'Linha % não pertence à execução % (RFC-007: o holerite é emitido da linha da própria execução)', NEW.line_id, NEW.run_id;
    END IF;

    -- (a3) invariante 1: valores prontos e congelados — emissão só de
    --      execução CALCULADA (RFC-006 regra 1); em_calculo/cancelada não
    IF v_run_status <> 'calculada' THEN
        RAISE EXCEPTION 'Holerite só é emitido de execução CALCULADA (RFC-006 regra 1 — valores prontos); execução % está %',
            NEW.run_id, v_run_status;
    END IF;

    -- (a4) invariante 3: nada é digitado no holerite (RFC-007 regra 1) — o
    --      cabeçalho é SNAPSHOT do cadastro no momento da emissão (regra 4)
    NEW.period_reference        := v_period_ref;
    NEW.employee_full_name      := v_full_name;
    NEW.employee_cpf            := v_cpf;
    NEW.admission_date          := v_admission;
    NEW.position_description    := v_position;
    NEW.department_description  := v_department;
    NEW.issued_at               := now();

    RETURN NEW;
END;
$$;

-- (b) invariante 4: holerite imutável (RFC-007 regra 4) — correção via novo
--     processamento (recálculo → nova execução → nova linha → novo holerite),
--     preservando o histórico. Cobre DELETE e TRUNCATE (statement-level:
--     triggers de linha NÃO disparam em TRUNCATE) e também o UPDATE.
CREATE OR REPLACE FUNCTION prevent_stub_mutation ( )
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Holerite é imutável (RFC-007 regra 4): correção/regeneração via novo processamento (recálculo → nova execução → nova linha → novo holerite), nunca edição';
END;
$$;

CREATE TRIGGER trg_payroll_stubs_emission
    BEFORE INSERT ON payroll_stubs
    FOR EACH ROW EXECUTE FUNCTION enforce_stub_emission ();

CREATE TRIGGER trg_payroll_stubs_no_update
    BEFORE UPDATE ON payroll_stubs
    FOR EACH ROW EXECUTE FUNCTION prevent_stub_mutation ();

CREATE TRIGGER trg_payroll_stubs_no_delete
    BEFORE DELETE ON payroll_stubs
    FOR EACH ROW EXECUTE FUNCTION prevent_stub_mutation ();

CREATE TRIGGER trg_payroll_stubs_no_truncate
    BEFORE TRUNCATE ON payroll_stubs
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_stub_mutation ();

REVOKE UPDATE, DELETE, TRUNCATE ON payroll_stubs FROM PUBLIC;

-- ============================================================================
-- Índices de consulta
-- ============================================================================
CREATE INDEX idx_payroll_stubs_run      ON payroll_stubs (run_id);
CREATE INDEX idx_payroll_stubs_employee ON payroll_stubs (employee_cpf);
                                                             -- autoatendimento do funcionário (RFC-007 decisão 3)

COMMIT;
