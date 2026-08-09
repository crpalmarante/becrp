# FiscalUI — Regras de Negócio: Matriz de Decisão Fiscal

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

## O Problema

Uma venda não é uma venda. Cada operação fiscal é o resultado de uma **combinação de variáveis independentes**. Trocar uma delas muda tudo.

## Cadeia de Dependência

```
                  ┌──────────┐
                  │ Empresa  │  ← Matriz, regime nacional
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │  Filial  │  ← UF, IE, regime estadual
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │ Cliente  │  ← UF, IE, regime, contribuinte ICMS?
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │ Produto  │  ← NCM, CEST, origem, aliquota interna
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │    UF    │  ← Origem → Destino (interestadual?)
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │   CFOP   │  ← Natureza da operação
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │   NCM    │  ← Classificação fiscal do produto
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │  Regime  │  ← Simples, Presunto, Real
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │Operação  │  ← Venda, devolução, transferência
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │   Data   │  ← Legislação vigente na data
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │ CST/     │  ← Resultado: tributação aplicada
                  │  CSOSN   │
                  └──────────┘
```

## Matriz de Combinações

Cada nó da cadeia tem valores possíveis. A combinação gera o resultado tributário:

```json
{
    "empresa": "EMPRESA_A",
    "filial": "FILIAL_SP",
    "cliente": {
        "uf": "RJ",
        "regime": "REGIME_NORMAL",
        "contribuinteICMS": true
    },
    "produto": {
        "ncm": "7318.15.00",
        "cest": "21.023.00",
        "origem": 0
    },
    "cfop": "5101",
    "operacao": "VENDA",
    "data": "2026-07-24",
    "regimeEmitente": "REGIME_NORMAL"
}
```

### Cenário 1: Venda Simples SP → SP

```
Empresa: EMPRESA_A
Filial:  FILIAL_SP (SP)
Cliente: SP, REGIME_NORMAL, contribuinte ICMS
Produto: NCM 7318.15.00, origem 0
CFOP:    5101 (Venda dentro do estado)
Operação: VENDA

→ CST ICMS: 00 (Tributada integralmente)
→ Alíquota ICMS: 18% (interna SP)
→ CST IPI: 50 (Tributada)
→ IPI: 5%
→ Não há ST
→ Não há FCP
→ Não há DIFAL
```

### Cenário 2: Mesmo produto, SP → RJ

```
Empresa: EMPRESA_A
Filial:  FILIAL_SP (SP)
Cliente: RJ, REGIME_NORMAL, contribuinte ICMS
Produto: NCM 7318.15.00, origem 0
CFOP:    6101 (Venda interestadual)
Operação: VENDA

→ CST ICMS: 00 (Tributada)
→ Alíquota ICMS: 12% (interestadual SP→RJ)
→ DIFAL: 6% (18% RJ - 12% interestadual), devido ao destino
→ CST IPI: 50
→ IPI: 5%
→ Não há ST (depende do CEST)
```

### Cenário 3: Mesmo produto, SP → MT (contribuinte)

```
Empresa: EMPRESA_A
Filial:  FILIAL_SP (SP)
Cliente: MT, REGIME_NORMAL, contribuinte ICMS
Produto: NCM 7318.15.00, origen 0, CEST 21.023.00
CFOP:    6101 (Venda interestadual)
Operação: VENDA

→ CST ICMS: 00 (Tributada)
→ Alíquota ICMS: 7% (interestadual SP→MT)
→ DIFAL: 10% (17% MT - 7% interestadual)
→ ICMS-ST: BASE * (ALIQ_MT - ALIQ_INTER) — CEST ativo em MT
→ FCP: 2% sobre a base de ST
→ CST IPI: 50
→ IPI: 5%
```

### Cenário 4: Cliente Simples Nacional

```
Empresa: EMPRESA_A
Filial:  FILIAL_SP (SP)
Cliente: SP, SIMPLES_NACIONAL, contribuinte ICMS
Produto: NCM 7318.15.00, origem 0
CFOP:    5101 (Venda dentro do estado)
Operação: VENDA

→ CST ICMS (para emitente): 00
→ CSOSN (para destinatario Simples): 102
→ Alíquota ICMS: 18%
→ Observação: NF-e sem destaque de ICMS na DANFE
→ Cliente Simples não se credita do ICMS
```

### Cenário 5: Devolução de venda

```
Empresa: EMPRESA_A
Filial:  FILIAL_SP (SP)
Cliente: RJ, REGIME_NORMAL
Produto: NCM 7318.15.00, origem 0
CFOP:    1201 (Devolução dentro do estado) / 2201 (interestadual)
Operação: DEVOLUCAO

→ CFOP diferente (devolução)
→ ICMS: mesma tributação da venda original
→ IPI: creditamento
→ PIS/COFINS: não cumulativo (crédito)
```

### Cenário 6: Venda para não contribuinte ICMS (consumidor final)

```
Empresa: EMPRESA_A
Filial:  FILIAL_SP (SP)
Cliente: RJ, REGIME_NORMAL, NAO_CONTRIBUINTE
Produto: NCM 7318.15.00
CFOP:    6102 (Venda interestadual para não contribuinte)
Operação: VENDA

→ CFOP: 6102 (difere de 6101)
→ ICMS: DIFAL integral para o destino
→ EC 87/2015: DIFAL devido ao destino
→ Cliente não se credita
```

## Motor de Regras

A decisão tributária é uma **árvore de decisão**:

```
Entrada: { empresa, filial, cliente, produto, cfop, data }
                │
                ▼
   ┌─── Regime do emitente? ───┐
   │                           │
 SIMPLES                  REGIME NORMAL
   │                           │
   ▼                           ▼
CSOSN                       CST
   │                           │
   │                  ┌─── UF destino? ───┐
   │                  │                  │
   │              Mesma UF           UF diferente
   │                  │                  │
   │                  ▼                  ▼
   │              Interna          Interestadual
   │                  │                  │
   │                  ▼                  ▼
   │          ┌─── Cliente? ───┐   ┌─── Cliente? ───┐
   │          │              │    │              │
   │      Contribuinte   Não       Contribuinte   Não
   │                      │                      │
   │          │              │    │              │
   │          ▼              ▼    ▼              ▼
   │      CFOP 5101    CFOP 5102    CFOP 6101    CFOP 6102
   │          │              │         │              │
   │          │              │         │              │
   │          ▼              ▼         ▼              ▼
   │      ICMS 18%       ICMS 18%    ICMS 12%    DIFAL
   │                                    │          total
   │                                    ▼
   │                            ┌─── CEST? ───┐
   │                            │            │
   │                            Sim          Não
   │                            │            │
   │                            ▼            ▼
   │                       ICMS-ST      Sem ST
   │                        + FCP
   │
   └── ... continua para IPI, PIS, COFINS, ISS
```

## Implementação no Backend

### Tabelas Essenciais (PostgreSQL)

```sql
-- Alíquotas internas por UF
CREATE TABLE aliquota_interna (
    uf CHAR(2) PRIMARY KEY,
    aliquota DECIMAL(5,2) NOT NULL
);
-- SP=18, RJ=18, MG=18, PR=18, SC=17, RS=18, MT=17, MS=17, GO=17, ...

-- Alíquotas interestaduais
CREATE TABLE aliquota_interestadual (
    uf_origem CHAR(2),
    uf_destino CHAR(2),
    aliquota DECIMAL(5,2) NOT NULL,
    PRIMARY KEY (uf_origem, uf_destino)
);
-- SP→RJ=12, SP→MT=7, SP→MG=12, SP→PR=12, ...

-- CEST (Substituição Tributária)
CREATE TABLE cest (
    cest VARCHAR(10) PRIMARY KEY,
    descricao TEXT,
    ncm_inicio VARCHAR(8),
    ncm_fim VARCHAR(8),
    uf CHAR(2),
    vigencia_inicio DATE,
    vigencia_fim DATE,
    aliquota_st DECIMAL(5,2),
    margem_st DECIMAL(5,3)
);

-- Benefícios fiscais por UF
CREATE TABLE beneficio_fiscal (
    uf CHAR(2),
    ncm VARCHAR(8),
    tipo VARCHAR(50),      -- reducao_base, credito_presumido, isencao
    percentual DECIMAL(5,2),
    fundamento_legal TEXT,
    vigencia_inicio DATE,
    vigencia_fim DATE
);

-- CST por regra
CREATE TABLE regra_cst (
    id SERIAL PRIMARY KEY,
    uf_origem CHAR(2),
    uf_destino CHAR(2),
    regime_destino VARCHAR(20),
    contribuinte BOOLEAN,
    cfop_inicio INTEGER,
    cfop_fim INTEGER,
    ncm_inicio VARCHAR(8),
    ncm_fim VARCHAR(8),
    cst_icms VARCHAR(3),
    cst_ipi VARCHAR(3),
    prioridade INTEGER,
    vigencia_inicio DATE,
    vigencia_fim DATE
);
```

---

## Princípio FiscalUI

FiscalUI **não implementa** nenhuma dessas regras. Ele:

```
1. Coleta os dados via formulário
2. Envia para o endpoint /api/tax-engine/calcular
3. Recebe o resultado tributário pronto (CST, alíquotas, valores)
4. Exibe na tela e usa na geração do documento fiscal
```

**Toda a complexidade da matriz de decisão fica no backend.**

---

**Arquivo:** `docs/TAX_RULES_MATRIX.md`
**Versão:** 1.0
**Data:** 2026-07-24
