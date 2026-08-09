-- ============================================================================
-- db/013_tax_tables.sql
-- RFC-005 — Tabelas Fiscais: INSS e IRRF (v1.0.0 · Draft em revisão)
-- ----------------------------------------------------------------------------
-- Cria as tabelas fiscais versionadas por competência e a consulta no cálculo:
--   tax_tables           (RFC-005 §2/§3) — faixas INSS/IRRF por competência,
--                                           progressivas por faixa (regra 4)
--   tax_irrf_dependents  (RFC-005 §3)    — dedução por dependente do IRRF,
--                                           vigente na competência (decisão 3:
--                                           múltiplos tipos de dependência)
--   f_tax_inss / f_tax_irrf / f_tax_base_irrf — consulta NO NÍVEL DO BANCO das
--                                           tabelas vigentes na competência —
--                                           espelho das regras do RFC-005 que
--                                           o motor COBOL (taxcalc.cbl) executa;
--                                           materializa a regra 1: o cálculo da
--                                           folha da competência X usa a tabela
--                                           vigente em X (nunca a do dia).
--
-- Convenções (PLAN_ERP §6): SQL puro em db/, nomes de tabela em inglês plural.
-- Pré-requisito: db/002 (fornece set_updated_at()). Ordem: 002 → … → 013
-- (sem dependência das 009/010/011/012 — última da cadeia).
--
-- REGRAS DO RFC-005 IMPLEMENTADAS:
--   regra 1 — toda tabela tem competência de vigência (reference = 'YYYY-MM');
--   regra 2 — tabelas IMUTÁVEIS (UPDATE/DELETE/TRUNCATE bloqueados): alteração
--             gera NOVA VERSÃO com nova competência (INSERT); decisão 1:
--             todas as tabelas históricas são preservadas;
--   regra 4 — aplicação PROGRESSIVA por faixa (INSS soma parcelas de cada
--             faixa; IRRF usa a faixa da base com a dedução da faixa);
--   regra 5 — valores monetários EXATOS: sem arredondamento intermediário
--             (funções retornam precisão total; arredondamento só na exibição
--             do holerite — RFC-007);
--   §3      — base IRRF = base INSS − INSS − dedução por dependente
--             (f_tax_base_irrf), valor por dependente da competência.
--
-- TETO INSS (RFC-005 §2): quando a tabela tem teto, ele é o bracket_to da
-- última faixa; a base é limitada via LEAST() na função. Na tabela ilustrativa
-- do RFC-005 a última faixa é aberta (NULL).
--
-- SEED — tabelas ILUSTRATIVAS do RFC-005 §2/§3 (NÃO oficiais), idênticas às
-- usadas no EXEMPLO-competencia.md (competência 2026-08), + versão posterior
-- (2027-01) demonstrando o versionamento da regra 2. A fonte de atualização é
-- manual/administrada (regra 3): a empresa cadastra os valores oficiais.
--
-- Executar:
--   psql -v ON_ERROR_STOP=1 -f db/013_tax_tables.sql
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. TAX_TABLES — RFC-005 §2/§3 (faixas INSS/IRRF por competência)
--    Uma linha por faixa; faixa aberta (sem teto) = bracket_to NULL.
-- ============================================================================
CREATE TABLE tax_tables (
    id            BIGSERIAL PRIMARY KEY,
    table_type    TEXT         NOT NULL
                  CONSTRAINT ck_tax_type CHECK (table_type IN ('inss', 'irrf')),
    reference     TEXT         NOT NULL
                  CONSTRAINT ck_tax_reference CHECK (reference ~ '^[0-9]{4}-[0-9]{2}$'),
                                                                   -- competência de vigência (regra 1)
    year          SMALLINT     NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month         SMALLINT     NOT NULL CHECK (month BETWEEN 1 AND 12),
    bracket_from  NUMERIC(12,2) NOT NULL CHECK (bracket_from >= 0), -- início da faixa (inclusive)
    bracket_to    NUMERIC(12,2)
                  CONSTRAINT ck_tax_bracket_to
                  CHECK (bracket_to IS NULL OR bracket_to > bracket_from),
                                                                   -- fim (inclusive); NULL = aberta
    rate          NUMERIC(7,4) NOT NULL
                  CONSTRAINT ck_tax_rate CHECK (rate >= 0 AND rate <= 1),
                                                                   -- alíquota (0,075 = 7,5%)
    deduction     NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (deduction >= 0),
                                                                   -- IRRF: dedução da faixa (RFC-005 §3)
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_tax_bracket UNIQUE (table_type, reference, bracket_from)
                                                                   -- uma faixa por início na competência
);

COMMENT ON TABLE  tax_tables IS 'RFC-005 — faixas INSS/IRRF versionadas por competência; progressivas por faixa (regra 4); imutáveis (regra 2: nova versão = novo INSERT)' ;
COMMENT ON COLUMN tax_tables.reference IS 'Competência de vigência (ex.: ''2026-08'') — o cálculo da folha da competência X usa a tabela vigente em X (RFC-005 regra 1)' ;
COMMENT ON COLUMN tax_tables.bracket_to IS 'Fim da faixa (inclusive); NULL = faixa aberta (sem teto). Teto INSS (RFC-005 §2) = bracket_to da última faixa, quando aplicável' ;
COMMENT ON COLUMN tax_tables.rate IS 'Alíquota da faixa em decimal (0,075 = 7,5%) — aplicação progressiva (RFC-005 regra 4)' ;
COMMENT ON COLUMN tax_tables.deduction IS 'Dedução da faixa (RFC-005 §3 — IRRF): imposto = base × alíquota − dedução; INSS usa 0' ;

-- imutabilidade (RFC-005 regra 2 + decisão 1: tabelas históricas preservadas;
-- alteração gera NOVA VERSÃO com nova competência — nunca edita a usada)
CREATE OR REPLACE FUNCTION prevent_tax_table_mutation ()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Tabela fiscal é imutável (RFC-005 regra 2): alteração gera nova versão com nova competência — nunca edita a usada em folha';
END;
$$;

CREATE TRIGGER trg_tax_tables_immutable
    BEFORE UPDATE OR DELETE ON tax_tables
    FOR EACH ROW EXECUTE FUNCTION prevent_tax_table_mutation ();

CREATE TRIGGER trg_tax_tables_no_truncate
    BEFORE TRUNCATE ON tax_tables
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_tax_table_mutation ();

REVOKE UPDATE, DELETE, TRUNCATE ON tax_tables FROM PUBLIC;

-- ============================================================================
-- 2. TAX_IRRF_DEPENDENTS — RFC-005 §3 (dedução por dependente, por competência)
-- ============================================================================
CREATE TABLE tax_irrf_dependents (
    id             BIGSERIAL PRIMARY KEY,
    reference      TEXT         NOT NULL CHECK (reference ~ '^[0-9]{4}-[0-9]{2}$'),
    year           SMALLINT     NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month          SMALLINT     NOT NULL CHECK (month BETWEEN 1 AND 12),
    deduction_type TEXT         NOT NULL CHECK (btrim(deduction_type) <> ''),
                                                                   -- tipo de dependência (decisão 3)
    amount         NUMERIC(12,2) NOT NULL CHECK (amount >= 0),     -- valor dedutível por dependente
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_tax_dependent_deduction UNIQUE (reference, deduction_type)
);

COMMENT ON TABLE  tax_irrf_dependents IS 'RFC-005 §3 — dedução por dependente do IRRF, vigente na competência; múltiplos tipos de dependência (decisão 3)' ;
COMMENT ON COLUMN tax_irrf_dependents.deduction_type IS 'Tipo de dependência (ex.: ''dependente'', ''pensao'') — decisão 3: mais de um tipo com valor próprio' ;
COMMENT ON COLUMN tax_irrf_dependents.amount IS 'Valor dedutível por dependente (RFC-005 §3) — usado em f_tax_base_irrf' ;

CREATE TRIGGER trg_tax_irrf_dependents_immutable
    BEFORE UPDATE OR DELETE ON tax_irrf_dependents
    FOR EACH ROW EXECUTE FUNCTION prevent_tax_table_mutation ();

CREATE TRIGGER trg_tax_irrf_dependents_no_truncate
    BEFORE TRUNCATE ON tax_irrf_dependents
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_tax_table_mutation ();

REVOKE UPDATE, DELETE, TRUNCATE ON tax_irrf_dependents FROM PUBLIC;

-- ============================================================================
-- 3. CONSULTA NO CÁLCULO — funções que usam a tabela DA COMPETÊNCIA (regra 1)
-- ============================================================================

-- INSS progressivo por faixa (RFC-005 §2 + regra 4): soma das parcelas de cada
-- faixa atingida pela base. Sem arredondamento intermediário (regra 5).
-- Fail-closed: sem tabela vigente para a competência → EXCEÇÃO (a folha não
-- pode calcular sem a tabela da competência).
CREATE OR REPLACE FUNCTION f_tax_inss (p_reference TEXT, p_base NUMERIC)
RETURNS NUMERIC
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_rows BIGINT;
    v_inss NUMERIC;
BEGIN
    SELECT count(*) INTO v_rows
      FROM tax_tables
     WHERE table_type = 'inss' AND reference = p_reference;
    IF v_rows = 0 THEN
        RAISE EXCEPTION 'Tabela INSS não encontrada para a competência % (RFC-005 regra 1)', p_reference;
    END IF;

    SELECT COALESCE(SUM((LEAST(p_base, COALESCE(bracket_to, p_base)) - bracket_from) * rate), 0)
      INTO v_inss
      FROM tax_tables
     WHERE table_type = 'inss'
       AND reference  = p_reference
       AND bracket_from < p_base;            -- faixas atingidas pela base

    RETURN v_inss;
END;
$$;

COMMENT ON FUNCTION f_tax_inss (TEXT, NUMERIC) IS
    'RFC-005 §2/regra 4 — INSS progressivo por faixa da competência p_reference; sem arredondamento intermediário (regra 5); falha sem tabela da competência (regra 1)' ;

-- IRRF pela faixa da base (RFC-005 §3): imposto = base × alíquota da faixa −
-- dedução da faixa. Faixa isenta (rate 0) devolve 0; GREATEST(…,0) impede
-- imposto negativo. Fail-closed idêntico ao INSS.
CREATE OR REPLACE FUNCTION f_tax_irrf (p_reference TEXT, p_base NUMERIC)
RETURNS NUMERIC
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_rows    BIGINT;
    v_bracket tax_tables%ROWTYPE;
BEGIN
    SELECT count(*) INTO v_rows
      FROM tax_tables
     WHERE table_type = 'irrf' AND reference = p_reference;
    IF v_rows = 0 THEN
        RAISE EXCEPTION 'Tabela IRRF não encontrada para a competência % (RFC-005 regra 1)', p_reference;
    END IF;

    SELECT * INTO v_bracket
      FROM tax_tables
     WHERE table_type = 'irrf'
       AND reference  = p_reference
       AND bracket_from < p_base
       AND (bracket_to IS NULL OR p_base <= bracket_to)
     ORDER BY bracket_from DESC
     LIMIT 1;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Base IRRF % não enquadrada em nenhuma faixa da competência %', p_base, p_reference;
    END IF;

    RETURN GREATEST(p_base * v_bracket.rate - v_bracket.deduction, 0);
END;
$$;

COMMENT ON FUNCTION f_tax_irrf (TEXT, NUMERIC) IS
    'RFC-005 §3 — IRRF pela faixa da base na competência p_reference: base × alíquota − dedução da faixa; isento → 0' ;

-- Base IRRF (RFC-005 §3): base INSS − INSS − dedução por dependente (valor da
-- competência). Sem linha de dependente na competência → sem dedução.
CREATE OR REPLACE FUNCTION f_tax_base_irrf (p_reference TEXT, p_base_inss NUMERIC,
                                            p_inss NUMERIC, p_dependents INTEGER)
RETURNS NUMERIC
LANGUAGE sql
STABLE
AS $$
    SELECT p_base_inss - p_inss
         - p_dependents * COALESCE((
               SELECT amount FROM tax_irrf_dependents
                WHERE reference = p_reference AND deduction_type = 'dependente'
           ), 0);
$$;

COMMENT ON FUNCTION f_tax_base_irrf (TEXT, NUMERIC, NUMERIC, INTEGER) IS
    'RFC-005 §3 — base IRRF = base INSS − INSS − (dependentes × dedução por dependente da competência)' ;

-- ============================================================================
-- Seed — tabelas ILUSTRATIVAS do RFC-005 §2/§3 (não oficiais), idênticas às
-- do EXEMPLO-competencia.md para a competência 2026-08 + 2027-01 (nova versão,
-- demonstrando o versionamento da regra 2).
-- ============================================================================
INSERT INTO tax_tables (table_type, reference, year, month, bracket_from, bracket_to, rate, deduction) VALUES
    -- INSS 2026-08 — RFC-005 §2 (ilustrativa; teto não aplicável no exemplo)
    ('inss', '2026-08', 2026, 8,    0.00, 1500.00, 0.0750, 0.00),   -- até 1.500,00 → 7,5%
    ('inss', '2026-08', 2026, 8, 1500.00, 3000.00, 0.0900, 0.00),   -- 1.500,01 – 3.000 → 9%
    ('inss', '2026-08', 2026, 8, 3000.00, 5000.00, 0.1200, 0.00),   -- 3.000,01 – 5.000 → 12%
    ('inss', '2026-08', 2026, 8, 5000.00,    NULL, 0.1400, 0.00),   -- acima de 5.000 → 14%
    -- IRRF 2026-08 — RFC-005 §3 (ilustrativa)
    ('irrf', '2026-08', 2026, 8,    0.00, 2000.00, 0.0000,   0.00), -- até 2.000 → isento
    ('irrf', '2026-08', 2026, 8, 2000.00, 4000.00, 0.1000, 100.00), -- 10% · dedução 100
    ('irrf', '2026-08', 2026, 8, 4000.00, 6000.00, 0.1500, 300.00), -- 15% · dedução 300
    ('irrf', '2026-08', 2026, 8, 6000.00,    NULL, 0.2250, 700.00), -- 22,5% · dedução 700
    -- INSS 2027-01 — nova versão (regra 2: alteração = nova competência)
    ('inss', '2027-01', 2027, 1,    0.00, 1500.00, 0.0800, 0.00),
    ('inss', '2027-01', 2027, 1, 1500.00, 3000.00, 0.1000, 0.00),
    ('inss', '2027-01', 2027, 1, 3000.00, 5000.00, 0.1400, 0.00),
    ('inss', '2027-01', 2027, 1, 5000.00,    NULL, 0.1500, 0.00),
    -- IRRF 2027-01 — nova versão (deduções alteradas)
    ('irrf', '2027-01', 2027, 1,    0.00, 2000.00, 0.0000,   0.00),
    ('irrf', '2027-01', 2027, 1, 2000.00, 4000.00, 0.1000, 100.00),
    ('irrf', '2027-01', 2027, 1, 4000.00, 6000.00, 0.1500, 350.00),
    ('irrf', '2027-01', 2027, 1, 6000.00,    NULL, 0.2250, 750.00);

INSERT INTO tax_irrf_dependents (reference, year, month, deduction_type, amount) VALUES
    ('2026-08', 2026, 8, 'dependente', 189.59),   -- premissa do EXEMPLO-competencia.md
    ('2027-01', 2027, 1, 'dependente', 200.00);

-- ============================================================================
-- Índices de consulta
-- ============================================================================
CREATE INDEX idx_tax_tables_reference ON tax_tables (reference);
CREATE INDEX idx_tax_tables_type_ref  ON tax_tables (table_type, reference);
CREATE INDEX idx_tax_dependents_ref   ON tax_irrf_dependents (reference);

COMMIT;
