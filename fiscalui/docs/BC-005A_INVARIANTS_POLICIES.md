# Business Platform
# BC-005A — Catálogo de Invariantes e Políticas do Domínio

**Documento:** BC-005A
**Título:** Catálogo de Invariantes e Políticas do Domínio
**Versão:** 2.0.0 (Draft)
**Dependências:** BC-000, BC-001, BC-002, BC-003, BC-004, BC-004A, BC-005

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

## Capítulo 1 — Objetivo

Definir todas as regras permanentes que garantem a integridade do domínio empresarial.

Este documento separa claramente:

- **Invariantes** (regras absolutas)
- **Políticas** (regras configuráveis)
- **Restrições temporais**
- **Restrições organizacionais**
- **Regras de autorização**

Essa separação evita que regras de negócio fiquem espalhadas por telas, APIs, banco de dados ou código de infraestrutura.

---

## Capítulo 2 — Conceitos Fundamentais

**Invariante**

Uma invariante é uma regra que nunca pode ser violada.

> Exemplo: Um pedido aprovado não pode voltar para "Rascunho".

Essa regra independe da empresa, do usuário ou da tecnologia.

**Política**

Uma política é uma regra configurável.

> Exemplo: Pedidos acima de R$ 50.000 exigem aprovação da diretoria.

Outra empresa pode configurar R$ 100.000.

**Restrição**

Uma restrição limita quando ou como uma operação pode ocorrer.

> Exemplo: Não cancelar documento após encerramento do período. Não alterar contrato vencido.

---

## Capítulo 3 — Classificação das Regras

```
Regras do Domínio
│
├── Invariantes
├── Políticas
├── Restrições
├── Autorizações
├── Validações
└── Governança
```

Cada categoria possui objetivos diferentes.

---

## Capítulo 4 — Invariantes Globais

As seguintes regras são válidas para todo o BusinessCore.

**INV-001 — Identidade Imutável**

Toda entidade possui uma identidade permanente. O identificador nunca muda.

**INV-002 — Histórico Preservado**

Nenhuma operação remove definitivamente uma entidade de negócio. O encerramento ocorre por mudança de estado ou exclusão lógica.

**INV-003 — Eventos Não São Alterados**

Eventos de domínio são imutáveis. Caso seja necessário corrigir uma situação, um novo evento deve ser gerado.

**INV-004 — Consistência dos Agregados**

Toda alteração em um agregado deve preservar suas invariantes antes de ser persistida.

**INV-005 — Estados Válidos**

Nenhuma entidade pode assumir um estado não definido em sua máquina de estados.

---

## Capítulo 5 — Invariantes por Agregado

**Order**

- Deve possuir pelo menos um item para ser confirmado
- Não pode ser faturado se estiver cancelado
- Não pode receber novos itens após faturamento
- Deve possuir uma Party responsável

**Contract**

- Deve possuir período de vigência válido
- Deve possuir ao menos duas partes relacionadas
- Não pode ser encerrado antes da data de início

**Product**

- Deve possuir unidade de medida
- Deve possuir nome
- Não pode existir sem categoria definida (quando a política organizacional exigir)

---

## Capítulo 6 — Políticas de Negócio

As políticas representam regras configuráveis.

| ID | Política | Descrição |
|----|----------|-----------|
| POL-001 | Valor máximo de desconto | Percentual máximo permitido |
| POL-002 | Limite de crédito | Valor máximo por Party |
| POL-003 | Aprovação por alçada | Valor que dispara aprovação |
| POL-004 | Estoque negativo permitido | Permite ou não saldo negativo |
| POL-005 | Dias para vencimento | Prazo padrão de pagamento |
| POL-006 | Tolerância de entrega | Dias de tolerância |
| POL-007 | Ordem de separação | Critério de separação de estoque |

Cada organização pode parametrizar esses valores.

---

## Capítulo 7 — Restrições Temporais

- Não alterar pedidos encerrados
- Não modificar contratos expirados
- Não registrar eventos com data anterior ao limite permitido
- Não alterar períodos fechados

---

## Capítulo 8 — Restrições Organizacionais

- Usuário só altera documentos da própria empresa
- Filiais não acessam documentos de outras filiais, salvo permissão
- Projetos pertencem a uma organização responsável

---

## Capítulo 9 — Regras de Autorização

As autorizações são avaliadas antes da execução de um caso de uso.

| ID | Ação |
|----|------|
| AUTH-001 | Criar Pedido |
| AUTH-002 | Aprovar Pedido |
| AUTH-003 | Cancelar Pedido |
| AUTH-004 | Encerrar Projeto |
| AUTH-005 | Liberar Pagamento |

As autorizações não definem a regra de negócio; apenas verificam quem pode executá-la.

---

## Capítulo 10 — Validações

Validações garantem que os dados estejam consistentes.

- Nome obrigatório
- Data inicial menor que data final
- Quantidade maior que zero
- Valor monetário não negativo
- Unidade de medida válida

---

## Capítulo 11 — Governança

Toda regra deverá possuir:

```
RuleID
Nome
Categoria
Descrição
Objetivo
Escopo
Severidade
Versão
Responsável
Data de Vigência
```

Isso permite rastreabilidade e auditoria.

---

## Capítulo 12 — Catálogo Inicial de Regras

```
INV-001  Identidade Imutável
INV-002  Histórico Preservado
INV-003  Eventos Imutáveis
INV-004  Consistência dos Agregados
INV-005  Estados Válidos

POL-001  Limite de Crédito
POL-002  Política de Desconto
POL-003  Aprovação por Alçada
POL-004  Estoque Negativo
POL-005  Vigência Contratual

RES-001  Período Encerrado
RES-002  Projeto Finalizado
RES-003  Contrato Expirado

AUTH-001  Criar Pedido
AUTH-002  Aprovar Pedido
AUTH-003  Cancelar Pedido
```

---

## Capítulo 13 — Integração com Outros Motores

O BusinessCore publica regras que podem ser especializadas.

```
BusinessCore
│
├── INV-005 — Estados Válidos
│
├── FiscalCore
│   └── Estado "Transmitido" para documentos fiscais
│
└── AccountingCore
    └── Estado "Conciliado" para lançamentos contábeis
```

Cada motor amplia, mas não modifica a regra original.

---

## Capítulo 14 — Avaliação das Regras

Toda operação segue uma ordem previsível.

```
Caso de Uso
    │
    ▼
Autorização
    │
    ▼
Validações
    │
    ▼
Invariantes
    │
    ▼
Políticas
    │
    ▼
Persistência
    │
    ▼
Evento de Domínio
```

Essa sequência garante previsibilidade e consistência.

---

## Capítulo 15 — Versionamento

Regras também evoluem. Cada alteração gera uma nova versão, preservando o histórico e permitindo auditoria.

---

## Capítulo 16 — Benefícios

- Regras centralizadas
- Baixo acoplamento
- Governança do domínio
- Parametrização sem alterar código
- Auditoria completa
- Evolução controlada

---

## Capítulo 17 — Arquitetura das Regras

```
BusinessCore
│
├── Ontologia
├── Modelo Canônico
├── Entidades
├── Value Objects
├── Business Data Types
├── Agregados
└── Catálogo de Regras
      ├── Invariantes
      ├── Políticas
      ├── Restrições
      ├── Autorizações
      └── Validações
```

---

## Visão Estratégica

Com o BC-005A concluído, o BusinessCore deixa de ser apenas um modelo de dados e passa a representar um modelo de comportamento empresarial.

```
BC-006  Eventos de Domínio
BC-007  Casos de Uso
BC-008  Serviços de Domínio
BC-009  Máquina de Estados
BC-010  Motor de Regras
BC-011  Workflow Semântico
BC-012  Auditoria e Event Store
```

---

**Arquivo:** `docs/BC-005A_INVARIANTS_POLICIES.md`
**Versão:** 2.0.0
**Data:** 2026-07-25
