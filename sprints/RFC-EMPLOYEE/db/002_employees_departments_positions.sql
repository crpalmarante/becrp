-- ============================================================================
-- db/002_employees_departments_positions.sql
-- RFC-002 — Cadastro de Funcionário (v1.0.0 · Draft em revisão)
--           RFC-008 — Empresa, Departamentos e Cargos (v1.0.0 · Draft em revisão)
-- ----------------------------------------------------------------------------
-- Cria os cadastros base da folha (PLAN_ERP §7.4):
--   employees    (RFC-002 §2)  — a pessoa com vínculo empregatício; fonte única
--                                 de verdade dos dados usados no processamento
--   departments  (RFC-008 §3)  — departamento / centro de custo
--   positions    (RFC-008 §4)  — cargo ocupado (tabela de cargos do RFC-002)
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- É pré-requisito da db/009_users_roles_audit.sql (users.employee_id → employees).
--
-- VÍNCULO USUÁRIO ↔ FUNCIONÁRIO (RFC-009 §2) — CPF como CHAVE NATURAL:
--   users.employee_id referencia employees(id) (FK), e a identidade é cruzada
--   pelo CPF (RFC-002 regra 1: "CPF é único"). Por isso employees.cpf é
--   NOT NULL + UNIQUE com máscara normalizada (somente dígitos) — a formatação
--   exibida (000.000.000-00) fica na camada web (PLAN_ERP §5 — máscaras caseiras).
--
-- Fora do escopo (migrations de acompanhamento): dependentes (RFC-002 §2.6,
-- decisão 3 — múltiplos tipos por dependente), histórico salarial com vigência
-- (RFC-002 §3 regra 3 → RFC-016) e a tabela `companies` (RFC-008 §2).
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/002_employees_departments_positions.sql
-- ============================================================================

BEGIN;

-- função genérica de updated_at (reutilizada nas 3 tabelas)
CREATE OR REPLACE FUNCTION set_updated_at ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

-- ============================================================================
-- 1. DEPARTMENTS — RFC-008 §3 (departamento / centro de custo)
-- ============================================================================
CREATE TABLE departments (
    id          BIGSERIAL PRIMARY KEY,
    code        TEXT        NOT NULL UNIQUE,        -- código (✅ identificador único)
    description TEXT        NOT NULL,               -- descrição (✅) ex.: "TI", "Comercial"
    cost_center TEXT,                               -- centro de custo (🔸) — rateio e relatórios (RFC-015)
    responsible TEXT,                               -- responsável (🔸)
    status      TEXT        NOT NULL DEFAULT 'ativo'
                CHECK (status IN ('ativo', 'inativo')),  -- situação (✅)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  departments            IS 'RFC-008 §3 — departamento/centro de custo; usado em rateio e relatórios (RFC-015)';
COMMENT ON COLUMN departments.code       IS 'Código único do departamento';
COMMENT ON COLUMN departments.cost_center IS 'Centro de custo (🔸) — opcional na 1ª versão (decisão RFC-008 nº 2)';
COMMENT ON COLUMN departments.status     IS 'Situação: ativo / inativo (inativação lógica — RFC-008 regra 2 e decisão 4)';

CREATE TRIGGER trg_departments_updated_at
    BEFORE UPDATE ON departments
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ============================================================================
-- 2. POSITIONS — RFC-008 §4 (cargo)
-- ============================================================================
CREATE TABLE positions (
    id               BIGSERIAL PRIMARY KEY,
    code             TEXT         NOT NULL UNIQUE,  -- código (✅ identificador único)
    description      TEXT         NOT NULL,         -- descrição (✅) ex.: "Analista de Sistemas"
    cbo              TEXT,                          -- CBO (🔸) — Classificação Brasileira de Ocupações
    reference_salary NUMERIC(12,2) CHECK (reference_salary IS NULL OR reference_salary >= 0),
                                                     -- salário de referência (🔸) — informativo;
                                                     -- o salário real é do funcionário (RFC-002)
    status           TEXT         NOT NULL DEFAULT 'ativo'
                     CHECK (status IN ('ativo', 'inativo')),  -- situação (✅)
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE  positions             IS 'RFC-008 §4 — cargo; tabela de cargos referenciada pelo RFC-002 §2.4';
COMMENT ON COLUMN positions.cbo         IS 'CBO (🔸) — obrigar só se formos usar relatórios/eSocial no futuro (decisão RFC-008 nº 3)';
COMMENT ON COLUMN positions.reference_salary IS 'Salário de referência (🔸) — informativo; o salário real vem do funcionário (RFC-002 §2.5)';
COMMENT ON COLUMN positions.status      IS 'Situação: ativo / inativo (inativação lógica — RFC-008 regra 2 e decisão 4)';

CREATE TRIGGER trg_positions_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ----------------------------------------------------------------------------
-- 2.1 Inativação lógica (RFC-008 decisão 4: NUNCA exclusão física de cargo ou
--     departamento — preserva o histórico de funcionários que os ocuparam).
--     O DELETE é bloqueado por trigger; a aplicação usa status='inativo'.
-- Escopo: a proteção cobre as operações bloqueáveis por trigger
-- (DELETE e TRUNCATE — triggers de linha NÃO disparam em TRUNCATE, por isso
-- os statement-level abaixo). DDL destrutivo (DROP TABLE) por um superusuário
-- não é bloqueável por trigger.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_hard_delete ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Exclusão física (DELETE/TRUNCATE) proibida (RFC-008 decisão 4): use inativação lógica (status = ''inativo'')';
END;
$$;

CREATE TRIGGER trg_departments_no_delete
    BEFORE DELETE ON departments
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete ();

CREATE TRIGGER trg_departments_no_truncate
    BEFORE TRUNCATE ON departments
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_hard_delete ();

CREATE TRIGGER trg_positions_no_delete
    BEFORE DELETE ON positions
    FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete ();

CREATE TRIGGER trg_positions_no_truncate
    BEFORE TRUNCATE ON positions
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_hard_delete ();

REVOKE DELETE, TRUNCATE ON departments, positions FROM PUBLIC;

-- ============================================================================
-- 3. EMPLOYEES — RFC-002 §2 (cadastro do funcionário)
-- ============================================================================
CREATE TABLE employees (
    id                  BIGSERIAL PRIMARY KEY,

    -- §2.1 Dados pessoais
    full_name           TEXT         NOT NULL,      -- nome completo (✅)
    birth_date          DATE         NOT NULL,      -- data de nascimento (✅) — férias, aniversariantes, IRRF
    gender              TEXT         NOT NULL
                        CHECK (gender IN ('M', 'F')),       -- sexo (✅) — M/F assumido na 1ª versão
                                                             -- (RFC-002 não enumera valores)
    marital_status      TEXT,                        -- estado civil (🔸)
    nationality         TEXT         NOT NULL,      -- nacionalidade (✅)
    cpf                 TEXT         NOT NULL UNIQUE
                        CHECK (cpf ~ '^[0-9]{11}$'),
                                                     -- CPF (✅) — CHAVE NATURAL do vínculo usuário↔funcionário
                                                     -- (RFC-002 regra 1: CPF é único); armazenado sem máscara,
                                                     -- formatação na camada web (PLAN_ERP §5)
    rg                  TEXT,                        -- RG (🔸)
    rg_issuer           TEXT,                        -- órgão emissor do RG (🔸)
    rg_uf               TEXT,                        -- UF do RG (🔸)
    voter_registration  TEXT,                        -- título de eleitor (🔸)
    pis_pasep           TEXT,                        -- PIS/PASEP (🔸) — benefícios e FGTS

    -- §2.2 Contato e endereço
    address_cep         TEXT         NOT NULL,      -- CEP (✅)
    address_street      TEXT         NOT NULL,      -- logradouro (✅)
    address_number      TEXT         NOT NULL,      -- nº (✅) — texto p/ aceitar "S/N"
    address_complement  TEXT,                        -- complemento (🔸)
    address_neighborhood TEXT        NOT NULL,      -- bairro (✅)
    address_city        TEXT         NOT NULL,      -- cidade (✅)
    address_uf          TEXT         NOT NULL,      -- UF (✅)
    phone               TEXT,                        -- telefone / celular (🔸)
    email               TEXT,                        -- e-mail (🔸) — holerite eletrônico (RFC-007)

    -- §2.3 Dados trabalhistas (CTPS)
    ctps_number         TEXT         NOT NULL,      -- nº CTPS (✅)
    ctps_series         TEXT         NOT NULL,      -- série (✅)
    ctps_uf             TEXT         NOT NULL,      -- UF da CTPS (✅)
    admission_date      DATE         NOT NULL,      -- data de admissão (✅) — início do vínculo (RFC-003)
    termination_date    DATE,                        -- data de demissão (🔸) — preenchida na rescisão (RFC-003)
    employment_status   TEXT         NOT NULL DEFAULT 'ativo'
                        CHECK (employment_status IN ('ativo', 'afastado', 'em_aviso', 'desligado')),
                                                     -- situação do vínculo (✅): desligado bloqueia
                                                     -- novos processamentos (RFC-002 §3 regra 5)

    -- §2.4 Cargo e departamento (referenciados, não copiados — RFC-008 regra 1)
    position_id         BIGINT       NOT NULL REFERENCES positions (id) ON DELETE RESTRICT,
    department_id       BIGINT       NOT NULL REFERENCES departments (id) ON DELETE RESTRICT,
    position_start_date DATE,                        -- data de posse no cargo (🔸)
    contract_type       TEXT         NOT NULL
                        CHECK (contract_type IN ('CLT', 'estagiario', 'aprendiz', 'temporario')),
                                                     -- tipo de vínculo (✅)

    -- §2.5 Dados salariais e de pagamento
    base_salary         NUMERIC(12,2) NOT NULL
                        CHECK (base_salary >= 0),   -- salário base ou valor hora (✅) — base do cálculo
    payment_form        TEXT         NOT NULL
                        CHECK (payment_form IN ('mensalista', 'horista', 'diarista')),
                                                     -- forma de pagamento (✅)
    bank_code           TEXT         NOT NULL,      -- banco (✅) — p/ pagamento e holerite (RFC-007)
    bank_agency         TEXT         NOT NULL,      -- agência (✅)
    bank_account        TEXT         NOT NULL,      -- conta (✅)
    payment_method      TEXT,                        -- meio de pagamento (🔸): depósito, TED, PIX
    work_schedule       TEXT,                        -- jornada / escala (🔸) — base p/ horas extras
    monthly_hours       NUMERIC(5,2)
                        CHECK (monthly_hours IS NULL OR monthly_hours > 0),
                                                     -- carga horária mensal contratual (🔸) — valor da hora

    -- §2.7 Benefícios (optante por VT é obrigatório; demais 🔸 em JSONB flexível)
    transit_benefit     BOOLEAN      NOT NULL DEFAULT FALSE,
                                                     -- optante por vale-transporte (✅) — afeta desconto de 6%
    benefits            JSONB        NOT NULL DEFAULT '{}'::jsonb,
                                                     -- vale-refeição/alimentação, plano de saúde/odonto,
                                                     -- outros (🔸) — chaves livres na 1ª versão

    -- §2.8 Informações complementares
    education_level     TEXT,                        -- escolaridade (🔸)
    medical_exam_due_date DATE,                      -- exame médico admissional — vencimento (🔸, RFC-003)
    notes               TEXT,                        -- restrições / observações (🔸)

    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE  employees IS 'RFC-002 — cadastro do funcionário; fonte única de verdade dos dados da folha (§1)';
COMMENT ON COLUMN employees.cpf IS 'CPF (✅) — identificador único do funcionário e CHAVE NATURAL do vínculo usuário↔funcionário (RFC-009 §2); armazenado só com dígitos (11), formatação na camada web';
COMMENT ON COLUMN employees.employment_status IS 'Situação do vínculo: ativo / afastado / em_aviso / desligado — desligado bloqueia novos processamentos (RFC-002 §3 regra 5 → RFC-003)';
COMMENT ON COLUMN employees.position_id IS 'Cargo ocupado — referenciado, não copiado (RFC-008 regra 1); alteração via movimentação contratual (RFC-016)';
COMMENT ON COLUMN employees.department_id IS 'Departamento / centro de custo — referenciado, não copiado (RFC-008 regra 1)';
COMMENT ON COLUMN employees.base_salary IS 'Salário base ou valor hora (✅) — base do cálculo; histórico com vigência registrado via RFC-016 (RFC-002 §3 regra 3)';
COMMENT ON COLUMN employees.transit_benefit IS 'Optante por vale-transporte (✅) — Sim/não; afeta o desconto de 6% (RFC-004)';
COMMENT ON COLUMN employees.benefits IS 'Benefícios 🔸: vale-refeição/alimentação, plano de saúde/odontológico, outros — JSONB flexível na 1ª versão (RFC-002 §2.7)';

CREATE TRIGGER trg_employees_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW EXECUTE FUNCTION set_updated_at ();

-- ============================================================================
-- Índices de consulta
-- ============================================================================
CREATE INDEX idx_employees_department_id ON employees (department_id);
CREATE INDEX idx_employees_position_id   ON employees (position_id);
CREATE INDEX idx_employees_status        ON employees (employment_status);
CREATE INDEX idx_departments_status      ON departments (status);
CREATE INDEX idx_positions_status        ON positions (status);

COMMIT;
