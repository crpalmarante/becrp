# Business Platform
# BC-003 — Entidades Fundamentais do BusinessCore

**Documento:** BC-003
**Título:** Entidades Fundamentais do BusinessCore
**Versão:** 1.0.0 (Draft)
**Dependências:** BC-000, BC-001, BC-002

---

## Capítulo 1 — Objetivo

Definir as entidades fundamentais do domínio empresarial.

Estas entidades representam conceitos que possuem:

- identidade própria;
- ciclo de vida;
- estado;
- comportamento;
- histórico.

Uma entidade continua sendo a mesma mesmo que seus atributos mudem.

---

## Capítulo 2 — O que é uma Entidade?

Uma entidade é um objeto do domínio cuja identidade é mais importante que seus atributos.

Exemplo:

- Um cliente muda de endereço. Continua sendo o mesmo cliente.
- Um produto muda de descrição. Continua sendo o mesmo produto.

A identidade permanece.

---

## Capítulo 3 — A Hierarquia das Entidades

Todas as entidades derivam de uma única raiz.

```
BusinessEntity
        │
        ├── Party
        ├── Organization
        ├── Resource
        ├── Process
        ├── Document
        ├── Transaction
        ├── Asset
        └── Event
```

Nenhuma entidade poderá existir fora desta hierarquia.

---

## Capítulo 4 — BusinessEntity

Toda entidade herda obrigatoriamente:

```
BusinessEntity
├── EntityId
├── BusinessCode
├── Name
├── Status
├── Version
├── CreatedAt
├── UpdatedAt
├── CreatedBy
├── UpdatedBy
├── Metadata
└── Extensions
```

Esta é a estrutura mínima obrigatória.

---

## Capítulo 5 — Party (A Entidade Mais Importante)

A primeira entidade do ERP não será Cliente. Será **Party**.

```
Party
│
├── Pessoa Física
├── Pessoa Jurídica
├── Órgão Público
├── Organização
├── Parceiro
├── Transportadora
├── Fornecedor
├── Cliente
├── Funcionário
├── Representante
├── Contato
├── Fabricante
└── Prestador de Serviço
```

Todos derivam de Party.

### Por que Party?

Porque uma empresa pode ser:

- Fornecedor hoje.
- Cliente amanhã.
- Transportadora depois.
- Parceira comercial no futuro.

Não faz sentido possuir quatro cadastros. Existe apenas uma **Party**. Os papéis mudam. A identidade permanece.

---

## Capítulo 6 — Organization

Organization representa uma organização.

```
Organization
│
├── Empresa
├── Filial
├── Holding
├── Matriz
├── Departamento
├── Unidade
└── Centro Operacional
```

---

## Capítulo 7 — Resource

Representa tudo aquilo que possui valor econômico.

```
Resource
│
├── Produto
├── Serviço
├── Matéria-prima
├── Mercadoria
├── Equipamento
├── Veículo
├── Software
├── Licença
└── Ativo
```

---

## Capítulo 8 — Process

Representa processos empresariais.

```
Process
│
├── Venda
├── Compra
├── Produção
├── Logística
├── Financeiro
├── Contrato
├── Projeto
└── Atendimento
```

---

## Capítulo 9 — Document

Representa qualquer documento empresarial.

```
Document
│
├── Pedido
├── Cotação
├── Contrato
├── Orçamento
├── Proposta
├── Ordem de Serviço
├── Requisição
└── Romaneio
```

> **Observação importante:** NF-e, NFC-e, CT-e e SPED não pertencem ao BusinessCore. Esses documentos pertencem ao FiscalCore.

---

## Capítulo 10 — Transaction

Representa movimentos econômicos.

```
Transaction
│
├── Venda
├── Compra
├── Recebimento
├── Pagamento
├── Transferência
├── Movimentação
├── Baixa
└── Ajuste
```

---

## Capítulo 11 — Asset

Representa patrimônio.

```
Asset
│
├── Máquina
├── Veículo
├── Imóvel
├── Equipamento
├── Computador
└── Ferramenta
```

---

## Capítulo 12 — Event

Representa acontecimentos.

```
Event
│
├── ClienteCriado
├── PedidoCriado
├── PedidoAprovado
├── VendaRealizada
├── PagamentoRecebido
└── ProdutoMovimentado
```

Eventos são imutáveis.

---

## Capítulo 13 — Relações Entre Entidades

```
Party
  │
  ▼ realiza
  │
Process
  │
  ▼ gera
  │
Document
  │
  ▼ origina
  │
Transaction
  │
  ▼ produz
  │
Event
```

Todo ERP poderá ser explicado por esse fluxo.

---

## Capítulo 14 — Especializações

Cada motor especializa as entidades.

```
BusinessCore → Product
                   │
                   ├── FiscalCore      → FiscalProduct (NCM, CFOP, CST)
                   ├── AccountingCore  → AccountingProduct (conta contábil)
                   └── WorkflowCore    → WorkflowProduct (regras de aprovação)
```

A entidade `Product` nunca é duplicada.

---

## Capítulo 15 — Estados

Todas as entidades possuem estados.

```
Draft → Active → Inactive → Suspended → Cancelled → Archived
```

Cada entidade poderá restringir os estados permitidos.

---

## Capítulo 16 — Identidade

A identidade nunca muda. Mesmo que nome, código, descrição, categoria ou responsável sejam alterados.

---

## Capítulo 17 — Auditoria

Toda entidade deverá registrar:

- criação;
- alteração;
- exclusão lógica;
- responsável;
- versão;
- origem.

---

## Capítulo 18 — Extensibilidade

Toda entidade suporta extensões.

```
Party
  │
  ├── Campos adicionais
  ├── Plugins
  ├── Verticalizações
  ├── Integrações
  └── Customizações
```

Sem alterar o modelo canônico.

---

## Capítulo 19 — Catálogo Oficial de Entidades

O catálogo inicial do BusinessCore será composto por:

```
Party
Organization
Company
Branch
Department
Employee
CustomerRole
SupplierRole
PartnerRole
Product
Service
Asset
Warehouse
Location
Project
Contract
Process
Order
Document
Transaction
Event
Attachment
Comment
Task
Calendar
Currency
Language
Country
Region
City
UnitOfMeasure
PriceList
Catalog
Classification
```

Este catálogo poderá crescer por versões, mas nenhuma nova entidade poderá ser criada sem respeitar a Ontologia (BC-001) e o Modelo Canônico (BC-002).

---

## Capítulo 20 — Arquitetura Geral

```
                 BusinessCore
                      │
        ┌─────────────┼─────────────┐
        │             │             │
      Party      Resource      Process
        │             │             │
        └──────┬──────┴──────┬──────┘
               │             │
          Document      Transaction
               │
             Event
```

Essa é a espinha dorsal do domínio.

---

**Arquivo:** `docs/BC-003_ENTIDADES.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
