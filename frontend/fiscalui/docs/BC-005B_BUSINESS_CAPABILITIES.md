# Business Platform
# BC-005B — Catálogo Universal de Capacidades Empresariais

**Documento:** BC-005B
**Título:** Business Capabilities Catalog
**Versão:** 1.0.0 (Draft)
**Dependências:** BC-000, BC-001, BC-002, BC-003, BC-004, BC-004A, BC-005, BC-005A

---

## Capítulo 1 — Objetivo

Este documento define as **Capacidades Empresariais** da plataforma.

Uma capacidade responde apenas uma pergunta:

> "O que a organização é capaz de fazer?"

Ela não responde:

- Quem faz
- Como faz
- Em qual tela
- Em qual linguagem
- Em qual banco
- Em qual departamento

Essas respostas pertencem a outros documentos.

---

## Capítulo 2 — O que é uma Business Capability?

Uma Business Capability representa uma competência permanente da organização.

Ela continua existindo mesmo quando:

- muda o ERP;
- muda o processo;
- muda o departamento;
- muda a tecnologia;
- muda o país.

**Exemplo:** Uma empresa sempre precisará: vender, comprar, pagar, receber. O processo pode mudar. A capacidade permanece.

---

## Capítulo 3 — Princípios

Toda capacidade deve ser:

- estável
- independente da tecnologia
- independente da estrutura organizacional
- reutilizável
- mensurável
- evolutiva

---

## Capítulo 4 — Hierarquia das Capacidades

```
Business Platform
│
├── Estratégicas
├── Operacionais
├── Suporte
└── Governança
```

---

## Capítulo 5 — Camada Estratégica

Representa aquilo que direciona a empresa.

```
Planejamento Estratégico
Gestão Corporativa
Governança
Compliance
Gestão de Riscos
Indicadores
Performance
Inovação
```

---

## Capítulo 6 — Camada Comercial

```
Relacionamento
CRM
Marketing
Pré-venda
Vendas
Contratos
Pós-venda
Atendimento
Fidelização
```

---

## Capítulo 7 — Cadeia de Suprimentos

```
Compras
Cotação
Fornecedor
Importação
Recebimento
Almoxarifado
Inventário
Expedição
Distribuição
Logística
```

---

## Capítulo 8 — Produção

```
Engenharia
Planejamento
Produção
Qualidade
Manutenção
Rastreabilidade
Apontamentos
```

---

## Capítulo 9 — Financeiro

```
Contas a Receber
Contas a Pagar
Tesouraria
Fluxo de Caixa
Conciliação
Cobrança
Orçamento
Investimentos
```

---

## Capítulo 10 — Contabilidade

A Contabilidade é uma Business Capability, mas sua implementação ficará concentrada no **AccountingCore**.

```
Plano de Contas
Lançamentos
Partidas Dobradas
Centro de Custos
Rateios
Ativo Imobilizado
Depreciação
Conciliação Contábil
DRE
Balanço
Balancete
SPED Contábil
SPED ECF
Consolidação
```

---

## Capítulo 11 — Fiscal

A legislação pertence ao **FiscalCore**, mas a capacidade empresarial existe independentemente da implementação.

```
Tributação
Documentos Fiscais
Apuração
Obrigações Acessórias
Escrituração
Fiscalização
Auditoria Fiscal
SPED Fiscal
Reforma Tributária
IBS
CBS
Split Payment
```

---

## Capítulo 12 — Recursos Humanos

```
Recrutamento
Funcionários
Treinamentos
Folha
Benefícios
Férias
Ponto
Desempenho
```

---

## Capítulo 13 — Projetos

```
Projetos
Cronograma
Custos
Recursos
Planejamento
Execução
Encerramento
```

---

## Capítulo 14 — Governança

```
Auditoria
Logs
Compliance
LGPD
ISO
Segurança
Riscos
Qualidade
```

---

## Capítulo 15 — Analytics

```
BI
Dashboards
KPIs
Machine Learning
IA
Data Warehouse
Indicadores
```

---

## Capítulo 16 — Mapa Completo

```
Business Platform
│
├── Gestão Estratégica
├── Comercial
├── Compras
├── Logística
├── Produção
├── Financeiro
├── Contabilidade
├── Fiscal
├── Recursos Humanos
├── Projetos
├── Serviços
├── Workflow
├── Analytics
├── Segurança
├── Governança
└── Integração
```

---

## Capítulo 17 — Relação entre Capability e Core

Cada capacidade é implementada por um ou mais motores especializados.

```
Business Capability
         │
         ▼
BusinessCore
         │
 ┌───────┼────────┬─────────┬──────────┐
 ▼       ▼        ▼         ▼          ▼
Fiscal  Accounting Workflow Security Integration
 Core      Core      Core      Core       Core
```

O **BusinessCore** define *o que* precisa existir. Cada **Core** define *como* atender essa necessidade.

---

## Capítulo 18 — Mapa de Dependências

```
Comercial
    │
    ▼
Pedido
    │
    ▼
Estoque
    │
    ▼
Fiscal
    │
    ▼
Financeiro
    │
    ▼
Contabilidade
```

As capacidades colaboram entre si, mas permanecem desacopladas.

---

## Capítulo 19 — Maturidade das Capacidades

Cada capacidade pode evoluir de forma independente.

| Nível | Descrição |
|-------|-----------|
| 1 | Manual |
| 2 | Informatizada |
| 3 | Integrada |
| 4 | Automatizada |
| 5 | Inteligente (IA e automação) |

Essa classificação permite avaliar a evolução da plataforma e dos clientes ao longo do tempo.

---

## Capítulo 20 — Arquitetura de Capacidades

```
                  Business Platform
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
 BusinessCore         WorkflowCore      SecurityCore
        │                  │                  │
        ├──────────────┬───┴───────┬──────────┤
        ▼              ▼           ▼
 FiscalCore    AccountingCore   IntegrationCore
        │              │
        └──────────────┴──────────────┐
                                      ▼
                                 FiscalUI
```

A **FiscalUI** é apenas uma das interfaces possíveis. No futuro poderão existir interfaces Web, Desktop, Mobile, API, CLI ou integrações B2B, todas consumindo os mesmos serviços dos Cores.

---

## Capítulo 21 — Matriz Capability × Core

Esta matriz orientará toda a evolução da plataforma.

| Capability | BusinessCore | FiscalCore | AccountingCore | WorkflowCore | SecurityCore | IntegrationCore |
|---|---|---|---|---|---|---|
| Cadastro de Parties | ✓ | | | | | |
| Produtos e Serviços | ✓ | ✓ | ✓ | | | |
| Comercial | ✓ | ✓ | ✓ | ✓ | | |
| Compras | ✓ | ✓ | ✓ | ✓ | | |
| Estoque | ✓ | ✓ | ✓ | ✓ | | |
| Fiscal | | ✓ | | ✓ | | |
| Financeiro | ✓ | | ✓ | ✓ | | |
| Contabilidade | | | ✓ | ✓ | | |
| Projetos | ✓ | | | ✓ | | |
| Segurança | | | | | ✓ | |
| Integrações | | | | | | ✓ |

Essa matriz será a referência para definir responsabilidades e evitar sobreposição de funcionalidades entre os motores.

---

**Arquivo:** `docs/BC-005B_BUSINESS_CAPABILITIES.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
