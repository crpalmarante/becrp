# RFC-WAREHOUSE-ROUTING.md

# RFC: Warehouse Routing Engine

**Status:** Proposta

**Versão:** 1.0

**Data:** 29/07/2026

---

# 1. Objetivo

Definir a arquitetura do **Warehouse Routing Engine**, responsável por controlar os fluxos operacionais de movimentação de mercadorias dentro e entre armazéns.

Uma rota representa a sequência de etapas (Steps) que uma mercadoria percorre desde sua origem até seu destino.

O objetivo é permitir que o ERP suporte diferentes modelos logísticos sem necessidade de alterações no código.

---

# 2. Motivação

Cada empresa possui processos logísticos próprios.

Exemplos:

* Loja de varejo
* Centro de distribuição
* Indústria
* Atacadista
* Marketplace
* Operador Logístico (3PL)

Todos movimentam produtos de forma diferente.

Em vez de codificar cada cenário, o ERP deve permitir configurar rotas.

---

# 3. Conceitos

## Route

Uma Route representa um fluxo logístico.

Exemplo:

```text
Recebimento

↓

Conferência

↓

Qualidade

↓

Armazenagem
```

---

## Step

Cada Route é composta por vários Steps.

Exemplo:

```text
Step 1

Receber
```

↓

```text
Step 2

Conferir
```

↓

```text
Step 3

Armazenar
```

Cada Step executa uma única responsabilidade.

---

# 4. Estrutura

```text
Warehouse Routing

├── Route
│
├── Route Step
│
├── Step Actions
│
├── Step Conditions
│
├── Step Rules
│
├── Route Templates
│
└── Route Execution
```

---

# 5. Modelo de Dados

## Warehouse Route

Campos sugeridos:

* Código
* Nome
* Tipo
* Empresa
* Filial
* Ativa
* Descrição

Exemplo:

```text
ROUTE-001

Recebimento Completo
```

---

## Warehouse Route Step

Campos:

* Sequência
* Nome
* Tipo
* Área
* Localização
* Operação
* Responsável
* Obrigatório
* Automático
* Próximo Step

---

# 6. Tipos de Steps

Exemplos:

* Receiving
* Inspection
* Quality
* Put Away
* Storage
* Picking
* Packing
* Shipping
* Transfer
* Loading
* Unloading
* Counting
* Quarantine
* Returns
* Cross Dock

O sistema deve permitir novos tipos no futuro.

---

# 7. Tipos de Rotas

## 7.1 Recebimento Direto (1 Passo)

```text
Fornecedor

↓

Estoque
```

Utilizado em pequenas operações.

---

## 7.2 Recebimento em Dois Passos

```text
Fornecedor

↓

Recebimento

↓

Estoque
```

---

## 7.3 Recebimento em Três Passos

```text
Fornecedor

↓

Recebimento

↓

Qualidade

↓

Estoque
```

---

## 7.4 Expedição em Um Passo

```text
Estoque

↓

Cliente
```

---

## 7.5 Expedição em Dois Passos

```text
Estoque

↓

Expedição

↓

Cliente
```

---

## 7.6 Expedição em Três Passos

```text
Estoque

↓

Picking

↓

Packing

↓

Cliente
```

---

## 7.7 Cross Dock

```text
Fornecedor

↓

Recebimento

↓

Expedição

↓

Cliente
```

Sem armazenamento intermediário.

---

## 7.8 Drop Shipping

```text
Fornecedor

↓

Cliente
```

Não existe movimentação física dentro do Warehouse.

O ERP acompanha apenas o fluxo documental.

---

## 7.9 Click & Collect

```text
Estoque

↓

Separação

↓

Balcão

↓

Cliente
```

---

## 7.10 Transferência

```text
Warehouse A

↓

Expedição

↓

Transporte

↓

Recebimento

↓

Warehouse B
```

---

## 7.11 Produção

```text
Matéria-Prima

↓

Produção

↓

Produto Acabado

↓

Estoque
```

---

## 7.12 Logística Reversa

```text
Cliente

↓

Recebimento

↓

Inspeção

↓

Estoque
```

Ou:

```text
Cliente

↓

Inspeção

↓

Descarte
```

---

# 8. Regras das Rotas

Cada rota poderá definir:

* obrigatoriedade dos Steps;
* execução automática;
* execução manual;
* aprovação obrigatória;
* operador responsável;
* perfil autorizado;
* SLA;
* horário permitido.

---

# 9. Condições

Uma rota poderá possuir condições.

Exemplos:

* tipo de produto;
* categoria;
* peso;
* volume;
* temperatura;
* lote;
* número de série;
* empresa;
* filial;
* Warehouse;
* cliente;
* fornecedor.

---

# 10. Templates

O sistema deverá possuir templates.

Exemplos:

* Loja
* Centro de Distribuição
* Indústria
* Farmácia
* Mercado
* Operador Logístico
* E-commerce
* Assistência Técnica

---

# 11. Execução

Cada execução de rota gera uma instância.

Exemplo:

```text
Route

↓

Execution

↓

Step 1

↓

Step 2

↓

Step 3
```

Cada execução deverá registrar:

* data;
* operador;
* localização;
* duração;
* resultado;
* observações.

---

# 12. Estados

Uma execução poderá estar em:

* Waiting
* Ready
* Running
* Blocked
* Suspended
* Completed
* Cancelled
* Failed

---

# 13. Auditoria

Toda alteração deverá registrar:

* usuário;
* data;
* localização;
* Step;
* operação executada;
* origem;
* destino.

Nenhuma execução poderá ser removida.

---

# 14. Integrações

## Inventory

Recebe confirmação das movimentações concluídas para atualizar saldos.

---

## Warehouse

Fornece as localizações físicas e os recursos utilizados em cada Step.

---

## Purchase

Inicia rotas de recebimento.

---

## Sales

Inicia rotas de separação e expedição.

---

## Manufacturing

Inicia rotas relacionadas à produção.

---

## Logistics

Recebe volumes e confirmações de expedição.

---

# 15. Princípios Arquiteturais

* Rotas são configuráveis.
* Steps são reutilizáveis.
* Fluxos não devem estar codificados.
* Novas rotas não exigem alterações estruturais.
* Todo Step deve ser auditável.
* Cada Step executa apenas uma responsabilidade.

---

# 16. Evoluções Futuras

O Routing Engine foi projetado para suportar:

* Workflow visual
* BPMN
* Regras baseadas em IA
* Otimização automática de rotas
* Balanceamento de carga
* Voice Picking
* RFID
* AGV
* Robôs autônomos
* Digital Twin
* Simulação logística

---

# 17. RFCs Relacionadas

* RFC-INVENTORY-ARCHITECTURE.md
* RFC-WAREHOUSE.md
* RFC-RECEIVING.md
* RFC-PICKING.md
* RFC-PACKING.md
* RFC-SHIPPING.md
* RFC-TRANSFER.md
* RFC-LOGISTICS.md

---

# 18. Conclusão

O Warehouse Routing Engine é o componente responsável por orquestrar os fluxos logísticos do ERP, permitindo que diferentes modelos operacionais coexistam na mesma plataforma.

Ao representar os processos como rotas compostas por etapas reutilizáveis, o ERP torna-se flexível, escalável e adaptável a operações que vão desde pequenas lojas até centros de distribuição, indústrias e operadores logísticos, sem depender de lógica fixa no código-fonte.
