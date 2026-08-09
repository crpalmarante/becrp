-- ============================================================================
-- db/015_payroll_entries.sql
-- RFC-007 — Holerite (v1.0.0 · Draft em revisão)
--           RFC-004 — Eventos: Proventos e Descontos (v1.0.0 · Draft em revisão)
-- ----------------------------------------------------------------------------
-- Cria o DETALHAMENTO POR EVENTO do holerite (previsto na db/012 e na db/014
-- como "migration de acompanhamento"):
--   payroll_entries (RFC-007 §2.2/§2.3) — uma linha por evento do CORPO do
--     demonstrativo: código, descrição, referência (horas, cotas, % ou —) e
--     valor. Liga o FUNCIONÁRIO (employee_id → employees) ao EVENTO do
--     catálogo (event_id → payroll_events, RFC-004) e ao DOCUMENTO
--     (stub_id → payroll_stubs, RFC-007 §2) que o exibe.
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- Pré-requisitos:
--   db/002 (employees)                     — funcionário do lançamento
--   db/010 (payroll_events)                — catálogo de eventos (RFC-004)
--   db/011 (permissions)                   — f_has_permission_guc()
--   db/012 (payroll_runs/payroll_lines)    — execução e resultado consolidado
--   db/014 (payroll_stubs)                 — documento do holerite
-- Ordem: 002 → 009 → 011 → 010 → 012 → 014 → 015.
--
-- AUTORIZAÇÃO POR AÇÃO (RFC-009 §3.1 via db/011 — autoridade única):
--   Gravar lançamentos do holerite é ATO DE PROCESSAMENTO →
--   f_has_permission_guc('calcular') (OPERADOR). O GUC de sessão é obrigatório
--   (fail-closed):
--     SET app.actor_roles = 'OPERADOR';
--
-- INVARIANTES PROTEGIDAS POR TRIGGER:
--   (1) Lançamentos só entram em holerite de execução CALCULADA (RFC-006
--       regra 1) — o stub já garante isso na 014; aqui é defensivo (a linha
--       pertence a um stub de execução calculada).
--   (2) O lançamento pertence ao FUNCIONÁRIO do holerite (employee_id =
--       employee_id da payroll_lines do stub) — consistência do documento.
--   (3) NADA é digitado no holerite (RFC-007 regra 1): código/descrição/tipo
--       do evento são SNAPSHOT tirados do catálogo (payroll_events) no
--       momento do INSERT — regenerar o documento reproduz EXATAMENTE os
--       mesmos valores (RFC-007 regra 4). Só o que é DO LANÇAMENTO é
--       informado: reference (horas/cotas/%) e value (resultado do cálculo).
--   (4) Entradas IMUTÁVEIS (RFC-007 regra 4): sem UPDATE/DELETE/TRUNCATE.
--       Correção = NOVO processamento (recálculo → nova execução → nova linha
--       → novo holerite → novas entradas), preservando o histórico (RFC-006
--       regra 3 / RFC-015 regra 3). Por isso NÃO há updated_at aqui.
--   (5) Uma entrada por evento por holerite (UNIQUE stub_id, event_id).
--   (6) valor do lançamento NÃO-negativo (o sinal vem do bloco provento/
--       desconto — event_type do catálogo).
--
-- Fora do escopo (decisão, não gap): a CONFERÊNCIA de rastreabilidade
-- (RFC-007 regra 2 — soma das entradas por bloco = total_proventos /
-- total_descontos da payroll_lines) fica para a camada de aplicação no
-- momento da emissão (ou um trigger futuro); aqui cada entrada é validada
-- isoladamente (snapshot + consistência + imutabilidade).
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/015_payroll_entries.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. PAYROLL_ENTRIES — RFC-007 §2.2/§2.3 (corpo do holerite, por evento)
--    Uma linha por evento exibido no demonstrativo. O código/descrição/tipo
--    são snapshot do catálogo (regra 1/4); o lançamento carrega a referência
--    (horas, cotas, % ou —) e o valor do cálculo.
-- ============================================================================
CREATE TABLE payroll_entries (
    id              BIGSERIAL PRIMARY KEY,
    stub_id         BIGINT        NOT NULL REFERENCES payroll_stubs (id) ON DELETE RESTRICT,
                                                             -- documento do holerite que exibe o lançamento (RFC-007 §2)
    employee_id     BIGINT        NOT NULL REFERENCES employees (id) ON DELETE RESTRICT,
                                                             -- funcionário do lançamento (RFC-002)
    event_id        BIGINT        NOT NULL REFERENCES payroll_events (id) ON DELETE RESTRICT,
                                                             -- evento do catálogo (RFC-004 §2/§3)
    code            INTEGER       NOT NULL,                 -- código do evento (RFC-007 §2.2) — SNAPSHOT
    description     TEXT          NOT NULL,                 -- descrição do evento (RFC-007 §2.2) — SNAPSHOT
    event_type      TEXT          NOT NULL
                    CHECK (event_type IN ('provento', 'desconto', 'informativo')),
                                                             -- bloco do holerite (RFC-007 §2.2 proventos /
                                                             -- §2.3 descontos) — SNAPSHOT (RFC-004 decisão 1)
    reference       TEXT,                                   -- referência (RFC-007 §2.2): horas, cotas, % ou — (nulo)
    value           NUMERIC(12,2) NOT NULL
                    CHECK (value >= 0),                     -- valor do lançamento (RFC-007 §2.2) — resultado do cálculo
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT uq_entry_per_stub_event UNIQUE (stub_id, event_id)
                                                             -- uma entrada por evento por holerite (invariante 5)
);

COMMENT ON TABLE  payroll_entries IS 'RFC-007 §2.2/§2.3 — corpo do holerite por evento: código/descrição/referência/valor; snapshot do catálogo no INSERT (regra 1); imutável (regra 4)' ;
COMMENT ON COLUMN payroll_entries.stub_id IS 'Holerite que exibe o lançamento (payroll_stubs da db/014)' ;
COMMENT ON COLUMN payroll_entries.employee_id IS 'Funcionário do lançamento (RFC-002) — deve ser o do holerite (invariante 2)' ;
COMMENT ON COLUMN payroll_entries.event_id IS 'Evento do catálogo (payroll_events da db/010 — RFC-004)' ;
COMMENT ON COLUMN payroll_entries.code IS 'Código do evento exibido no holerite (RFC-007 §2.2) — snapshot do catálogo no momento do INSERT' ;
COMMENT ON COLUMN payroll_entries.description IS 'Descrição do evento exibida no holerite (RFC-007 §2.2) — snapshot' ;
COMMENT ON COLUMN payroll_entries.event_type IS 'Bloco do holerite: provento (§2.2) ou desconto (§2.3); informativo (RFC-004 decisão 1) — snapshot' ;
COMMENT ON COLUMN payroll_entries.reference IS 'Referência do lançamento (RFC-007 §2.2): horas, cotas, % ou — (NULL quando não se aplica, ex.: INSS)' ;
COMMENT ON COLUMN payroll_entries.value IS 'Valor do lançamento (RFC-007 §2.2) — resultado do cálculo, não-negativo; o sinal vem do bloco (event_type)' ;

-- ============================================================================
-- 2. TRIGGERS DE ENFORCEMENT
--    (a) gravar lançamento (INSERT) → ação 'calcular' (RFC-009 §3.1 via db/011);
--        holerite de execução calculada; funcionário do lançamento = do
--        holerite; snapshot do catálogo no INSERT
--    (b) imutabilidade (UPDATE/DELETE/TRUNCATE) — RFC-007 regra 4
-- ============================================================================
CREATE OR REPLACE FUNCTION enforce_entry_insert ( )
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_run_status     TEXT;
    v_stub_employee  BIGINT;
    v_code           INTEGER;
    v_description    TEXT;
    v_event_type     TEXT;
BEGIN
    -- (a1) RFC-009 §3.1 via db/011: gravar lançamento do holerite é ato de
    --      processamento (ação 'calcular' — OPERADOR). Fail-closed.
    IF NOT f_has_permission_guc('calcular') THEN
        RAISE EXCEPTION 'Gravar lançamentos do holerite exige a ação calcular (RFC-009 §3.1, via db/011); app.actor_roles = %',
            COALESCE(current_setting('app.actor_roles', true), '<não definido>');
    END IF;

    -- (a2) invariante 1/2: o stub deve existir, ser de execução CALCULADA e o
    --      funcionário do lançamento deve ser o do holerite (via payroll_lines)
    SELECT pr.status, pl.employee_id
      INTO v_run_status, v_stub_employee
      FROM payroll_stubs ps
      JOIN payroll_runs pr        ON pr.id = ps.run_id
      JOIN payroll_lines pl       ON pl.id = ps.line_id
     WHERE ps.id = NEW.stub_id;

    IF v_run_status IS NULL THEN
        RAISE EXCEPTION 'Holerite inexistente (stub_id = %)', NEW.stub_id;
    END IF;
    IF v_run_status <> 'calculada' THEN
        RAISE EXCEPTION 'Holerite de execução não CALCULADA (RFC-006 regra 1); stub % está %', NEW.stub_id, v_run_status;
    END IF;
    IF NEW.employee_id IS DISTINCT FROM v_stub_employee THEN
        RAISE EXCEPTION 'Lançamento do funcionário % não pertence ao holerite (funcionário %) — RFC-007: o corpo do holerite é do funcionário do documento',
            NEW.employee_id, v_stub_employee;
    END IF;

    -- (a3) invariante 3: snapshot do catálogo no INSERT (RFC-007 regra 1/4)
    -- code é NOT NULL UNIQUE no catálogo (db/010) — NULL aqui só significa
    -- "evento não encontrado" (SELECT INTO sem linha zera as variáveis)
    SELECT code, description, event_type
      INTO v_code, v_description, v_event_type
      FROM payroll_events
     WHERE id = NEW.event_id;

    IF v_code IS NULL THEN
        RAISE EXCEPTION 'Evento inexistente (event_id = %)', NEW.event_id;
    END IF;

    NEW.code        := v_code;
    NEW.description := v_description;
    NEW.event_type  := v_event_type;

    RETURN NEW;
END;
$$;

-- (b) invariante 4: entradas imutáveis (RFC-007 regra 4) — correção via novo
--     processamento; cobre DELETE e TRUNCATE (statement-level) e o UPDATE.
CREATE OR REPLACE FUNCTION prevent_entry_mutation ( )
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Entradas do holerite são imutáveis (RFC-007 regra 4): correção via novo processamento (recálculo → novo holerite → novas entradas), nunca edição';
END;
$$;

CREATE TRIGGER trg_payroll_entries_insert
    BEFORE INSERT ON payroll_entries
    FOR EACH ROW EXECUTE FUNCTION enforce_entry_insert ();

CREATE TRIGGER trg_payroll_entries_no_update
    BEFORE UPDATE ON payroll_entries
    FOR EACH ROW EXECUTE FUNCTION prevent_entry_mutation ();

CREATE TRIGGER trg_payroll_entries_no_delete
    BEFORE DELETE ON payroll_entries
    FOR EACH ROW EXECUTE FUNCTION prevent_entry_mutation ();

CREATE TRIGGER trg_payroll_entries_no_truncate
    BEFORE TRUNCATE ON payroll_entries
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_entry_mutation ();

REVOKE UPDATE, DELETE, TRUNCATE ON payroll_entries FROM PUBLIC;

-- ============================================================================
-- Índices de consulta
-- ============================================================================
CREATE INDEX idx_payroll_entries_stub     ON payroll_entries (stub_id);
CREATE INDEX idx_payroll_entries_employee ON payroll_entries (employee_id);
                                                             -- autoatendimento do funcionário (RFC-007 decisão 3)

COMMIT;
