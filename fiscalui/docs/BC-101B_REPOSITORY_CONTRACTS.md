# Business Platform
# BC-101B — Repository Architecture & Contracts

**Documento:** BC-101B
**Título:** Repository Architecture & Contracts
**Versão:** 1.0.0 (Draft)
**Status:** Arquitetura Executável
**Dependências:** BC-101A (Aggregate Catalog)

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

Definir como o BusinessCore acessa dados sem conhecer:

- PostgreSQL
- COBOL
- REST
- Arquivos
- Cache
- Event Store

O domínio conhece apenas **Repositórios**.

```
BusinessCore → Repository → Persistence Adapter → PostgreSQL
```

---

## Capítulo 2 — Filosofia

Um Repository representa uma coleção de **Aggregates**.

Nunca tabelas. Nunca SQL. Nunca JOINs.

```
Certo:                    Errado:
OrderRepository           order_item_table
CustomerRepository        customer_table
ProductRepository         stock_table
```

O domínio trabalha com objetos de negócio.

---

## Capítulo 3 — Responsabilidade

**Repository deve:**
- ✔ Carregar Aggregates
- ✔ Persistir Aggregates
- ✔ Remover Aggregates
- ✔ Buscar por identidade
- ✔ Consultar por critérios

**Repository não deve:**
- ✘ Calcular impostos
- ✘ Executar regras
- ✘ Validar negócio
- ✘ Gerar eventos

---

## Capítulo 4 — Interface Base

```
IRepository<T>
├── save(T)
├── findById(id)
├── exists(id)
├── delete(T)
├── list(criteria)
└── count(criteria)
```

---

## Capítulo 5 — Repositórios Oficiais

| Aggregate | Repository |
|---|---|
| Party | `PartyRepository` |
| Product | `ProductRepository` |
| Customer | `CustomerRepository` |
| Supplier | `SupplierRepository` |
| Warehouse | `WarehouseRepository` |
| Stock | `StockRepository` |
| Order | `OrderRepository` |
| Purchase | `PurchaseOrderRepository` |
| Fiscal | `FiscalDocumentRepository` |
| Accounting | `JournalRepository` |

---

## Capítulo 6 — Interface Canônica

Exemplo: `OrderRepository`

```
save(order)
findById(id)
findByNumber(number)
findByCustomer(customerId)
findPending()
exists(number)
delete(order)
```

Cada Aggregate possui apenas operações pertinentes ao domínio.

---

## Capítulo 7 — Separação entre Escrita e Leitura

Nem toda consulta precisa carregar um Aggregate.

```
Repository → persistência (escrita)
QueryService → dashboards, relatórios, pesquisas (leitura)
```

Isso melhora desempenho e mantém o domínio limpo.

---

## Capítulo 8 — Adaptadores de Persistência

A implementação concreta fica fora do domínio.

```
BusinessCore → OrderRepository → PostgreSQLAdapter
BusinessCore → OrderRepository → COBOLAdapter
```

O domínio permanece inalterado.

---

## Capítulo 9 — Unidade de Trabalho

Todos os Repositories participam de uma mesma transação.

```
UseCase → IUnitOfWork → Repositories → Commit / Rollback
```

```
IUnitOfWork
├── begin()
├── commit()
├── rollback()
├── flush()
└── close()
```

---

## Capítulo 10 — Repositório Base

Todos herdam de uma estrutura comum.

```
AbstractRepository
├── CRUD
├── Identity Map
├── Optimistic Lock
└── Version Control
```

---

## Capítulo 11 — Identity Map

Durante um Use Case, o mesmo Aggregate é lido uma única vez.

```
Order #100 → Repository → Memória
Order #100 → Mesmo objeto (evita múltiplas leituras)
```

---

## Capítulo 12 — Controle de Concorrência

Cada Aggregate possui `Version`.

```
Versão 10 → Alteração → Versão 11
Versão 10 → ConcurrencyException (outro processo)
```

Implementação por **Optimistic Locking**.

---

## Capítulo 13 — Organização Física

```
business_core/
  repositories/
    interfaces/
      IRepository.py
      IUnitOfWork.py
    party/
      PartyRepository.py
    product/
      ProductRepository.py
    order/
      OrderRepository.py
    purchase/
      PurchaseRepository.py
    fiscal/
      FiscalRepository.py
    accounting/
      JournalRepository.py

infrastructure/
  postgres/
    repositories/
  cobol/
    repositories/
```

---

## Capítulo 14 — Fluxo Completo

```
Frontend → Command → UseCase → Aggregate → Repository → UnitOfWork → PostgreSQL
  ↓
Commit → Domain Events → Dispatcher → Listeners
```

O Use Case conhece apenas contratos. Nunca SQL, tabelas ou cursores.

---

## Capítulo 15 — Regras Arquiteturais

- Todo Aggregate Root possui um Repository
- Repositórios retornam Aggregates completos
- Consultas analíticas usam Query Services
- Nenhum Aggregate acessa banco diretamente
- Nenhum Repository contém regra de negócio
- Toda persistência passa pela Unit of Work
- Toda implementação deve ser substituível sem alterar o BusinessCore

---

## Capítulo 16 — Estrutura Consolidada do BusinessCore

```
BusinessCore
├── Commands
├── UseCases
├── Aggregates
├── Entities
├── ValueObjects
├── DomainServices
├── Repositories
├── Events
├── Policies
├── Specifications
└── Shared
```

---

**Arquivo:** `docs/BC-101B_REPOSITORY_CONTRACTS.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
