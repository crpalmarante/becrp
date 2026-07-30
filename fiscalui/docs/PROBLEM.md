# FiscalUI — O Problema: Legislação Fiscal Brasileira

## Contexto

O maior desafio de qualquer ERP no Brasil é a **legislação fiscal brasileira**. Não é só complexa — é **mutante**. Mudanças ocorrem com frequência imprevisível em todas as esferas:

### Três Esferas Tributárias

```
Federal:     IRPJ, CSLL, IPI, PIS, COFINS
Estadual:    ICMS (27 legislações diferentes — uma por UF)
Municipal:   ISS (5.570 municípios, cada um com sua lei)
```

### Obrigações Acessórias (SPED + outras)

```
SPED ECD      → Escrituração Contábil Digital
SPED ECF      → Escrituração Contábil Fiscal
SPED EFD      → Escrituração Fiscal Digital (ICMS/IPI)
NF-e          → Nota Fiscal Eletrônica (modelo 55)
NFS-e         → Nota Fiscal de Serviço Eletrônica
CT-e          → Conhecimento de Transporte Eletrônico
MDF-e         → Manifesto Eletrônico de Documentos Fiscais
eSocial       → Obrigações Trabalhistas e Previdenciárias
ECD           → Escrituração Contábil Digital
Reinf         → Escrituração Fiscal Digital de Retenções
```

### Regimes Tributários

```
Simples Nacional     → Unificado, mas com anexos que mudam
Lucro Presumido      → Presunção por atividade
Lucro Real           → Apuração real do lucro
```

## Por Que o ERP Tradicional Sofre

Sistemas monolíticos têm as regras fiscais **espalhadas** por todo o código. Quando uma legislação muda:

```
1. Precisa alterar o monolito inteiro (risco alto)
2. Precisa rebuildar e redeployar tudo
3. Testes de regressão em todo o sistema
4. Atualização obrigatória de todos os clientes
5. Uma mudança no ICMS de SP pode quebrar uma tela no MT
```

## Como a Arquitetura FiscalUI Resolve

```
┌──────────────────────────────────────────────────┐
│  FiscalUI                                        │
│  ⚡ NUNCA PRECISA SER ALTERADO                   │
│  As telas, componentes e interações              │
│  permanecem as mesmas                            │
│  Mudança de legislação = 0 impacto no frontend   │
├──────────────────────────────────────────────────┤
│         ↑ JSON (mesmos contratos)                │
├──────────────────────────────────────────────────┤
│  Python (API)                                    │
│  ⚡ PODE PRECISAR DE AJUSTES                     │
│  Alterações em endpoints, validações,            │
│  orquestração de novos fluxos                    │
├──────────────────────────────────────────────────┤
│         ↑ chamadas internas                      │
├──────────────────────────────────────────────────┤
│  COBOL                                           │
│  ⚡ ONDE A MUDANÇA REALMENTE IMPACTA            │
│  Cálculo de impostos, validação fiscal           │
│  regras de negócio críticas                      │
│  (já são alteradas há décadas, processo maduro)  │
├──────────────────────────────────────────────────┤
│  PostgreSQL                                      │
│  ⚡ NOVOS CAMPOS, NOVAS TABELAS                  │
│  Adaptação de schema para novas obrigações       │
└──────────────────────────────────────────────────┘
```

### Princípio Fundamental

> **O FiscalUI não sabe o que é ICMS, SPED, ou NFS-e.**
> Ele só sabe renderizar formulários, tabelas, e dashboards.
> Se a legislação muda, o backend se adapta — o frontend continua igual.

### Benefício Concreto

Quando o governo publica uma nova regra:

| Abordagem Tradicional | FiscalUI + Camadas |
|----------------------|-------------------|
| Dias/semanas de alteração no frontend | **Zero** alteração no frontend |
| Testes de regressão em toda UI | Testes apenas na camada alterada |
| Risco de introduzir bugs na interface | Risco contido na API/COBOL |
| Cliente precisa atualizar o sistema | Backend muda, frontend continua |

---

**Arquivo:** `docs/PROBLEM.md`
**Versão:** 1.0
**Data:** 2026-07-24
