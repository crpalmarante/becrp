# Business Platform
# BC-005 — Agregados (Aggregates)

**Documento:** BC-005
**Título:** Modelo de Agregados do BusinessCore
**Versão:** 1.0.0 (Draft)
**Dependências:** BC-003 (Entidades), BC-004 (Value Objects)

---

## Capítulo 1 — Objetivo

Definir como as entidades do BusinessCore são agrupadas em Agregados (Aggregates).

Um agregado representa uma unidade de consistência do domínio. Todas as regras de negócio devem ser garantidas dentro dos limites de um agregado.

---

## Capítulo 2 — O que é um Agregado?

Um agregado é um conjunto de entidades e Value Objects tratados como uma única unidade de negócio.

Ele possui:

- uma raiz (Aggregate Root);
- entidades internas;
- objetos de valor;
- regras próprias;
- limites bem definidos.

Nenhuma entidade externa pode modificar diretamente uma entidade interna do agregado.

---

## Capítulo 3 — Aggregate Root

Todo agregado possui uma raiz.

```
Pedido
  ├── Itens
  ├── Descontos
  ├── Observações
  ├── Anexos
  └── Histórico
```

O **Pedido** é a raiz. Os itens nunca são alterados diretamente. Toda alteração passa pelo Pedido.

---

## Capítulo 4 — Limite de Consistência

Toda validação ocorre dentro do agregado.

```
Pedido
  │
  ├── Adicionar Item
  ├── Validar Produto
  ├── Validar Quantidade
  ├── Atualizar Totais
  └── Publicar Evento
```

Nunca existirá atualização parcial.

---

## Capítulo 5 — Comunicação entre Agregados

Um agregado nunca modifica outro diretamente. Comunicação ocorre por:

- Eventos de Domínio
- Serviços de Domínio
- Casos de Uso

```
Pedido → PedidoAprovado (Evento) → Estoque → Reserva de Estoque
```

Pedido não chama Estoque diretamente.

---

## Capítulo 6 — Catálogo Inicial de Agregados

O BusinessCore possuirá inicialmente os seguintes agregados:

```
Party
Organization
Product
Service
Order
Contract
Project
InventoryMovement
Payment
Receipt
Process
Task
Document
Asset
```

Cada um possui sua própria raiz.

---

## Capítulo 7 — Agregado Party

```
Party
├── Identificações
├── Endereços
├── Contatos
├── Papéis
├── Preferências
├── Documentos
└── Anexos
```

Somente a raiz **Party** pode alterar seus componentes.

---

## Capítulo 8 — Agregado Product

```
Product
├── Descrições
├── Categorias
├── Unidade de Medida
├── Atributos
├── Imagens
├── Arquivos
└── Classificações
```

Informações fiscais serão adicionadas posteriormente pelo FiscalCore, sem alterar a estrutura do agregado.

---

## Capítulo 9 — Agregado Order

```
Order
├── Itens
├── Endereço de Entrega
├── Condições Comerciais
├── Descontos
├── Observações
├── Anexos
└── Histórico
```

Toda operação sobre itens deve passar pela raiz **Order**.

---

## Capítulo 10 — Agregado Contract

```
Contract
├── Partes
├── Vigência
├── Cláusulas
├── Anexos
├── Valores
└── Histórico
```

---

## Capítulo 11 — Agregado Project

```
Project
├── Etapas
├── Tarefas
├── Recursos
├── Cronograma
├── Custos
└── Documentos
```

---

## Capítulo 12 — Estados do Agregado

Todo agregado possui um ciclo de vida.

```
Draft → Open → In Progress → Completed → Archived
```

Cada agregado define seus próprios estados válidos.

---

## Capítulo 13 — Regras de Consistência

Um agregado deve garantir:

- Integridade dos dados
- Regras de negócio
- Coerência interna
- Publicação de eventos
- Controle de concorrência
- Auditoria

---

## Capítulo 14 — Invariantes

As invariantes são regras que nunca podem ser violadas.

Exemplo para **Order**:

- Deve possuir pelo menos um item para ser confirmado
- Não pode ser faturado se estiver cancelado
- Não pode receber novos itens após o faturamento
- Não pode ser encerrado sem estado final válido

Essas regras pertencem ao agregado.

---

## Capítulo 15 — Transações

Toda alteração em um agregado deve ser atômica.

```
Adicionar Item → Recalcular Totais → Atualizar Estado → Registrar Histórico → Gerar Evento → Commit
```

Se qualquer etapa falhar:

```
Rollback
```

Nenhum estado intermediário é persistido.

---

## Capítulo 16 — Especializações

Os motores especializados ampliam os agregados sem alterar sua essência.

```
Order (BusinessCore)
  ├── FiscalOrder (FiscalCore)
  ├── AccountingOrder (AccountingCore)
  └── WorkflowOrder (WorkflowCore)
```

Cada motor adiciona apenas seu comportamento específico.

---

## Capítulo 17 — Eventos do Agregado

Cada agregado publica eventos de domínio.

```
OrderCreated
OrderItemAdded
OrderApproved
OrderCancelled
OrderCompleted
```

Esses eventos serão consumidos por outros motores.

---

## Capítulo 18 — Governança

Somente a raiz do agregado pode:

- alterar entidades internas;
- criar novos componentes;
- remover componentes;
- validar regras;
- publicar eventos.

Isso preserva a consistência do domínio.

---

## Capítulo 19 — Benefícios

A adoção de agregados proporciona:

- Regras de negócio centralizadas
- Baixo acoplamento
- Alta coesão
- Transações consistentes
- Facilidade de testes
- Evolução independente dos módulos

---

## Capítulo 20 — Visão Geral

```
BusinessCore
├── Party Aggregate
├── Product Aggregate
├── Service Aggregate
├── Order Aggregate
├── Contract Aggregate
├── Project Aggregate
├── Inventory Aggregate
├── Payment Aggregate
├── Receipt Aggregate
└── Document Aggregate
```

Cada agregado representa um limite claro de responsabilidade e consistência.

---

**Arquivo:** `docs/BC-005_AGGREGATES.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
