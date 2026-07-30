# Business Platform
# BC-101C — Query Services

**Documento:** BC-101C
**Título:** Serviços de Consulta
**Versão:** 1.0.0 (Draft)
**Status:** Arquitetura Executável
**Dependências:** BC-101B (Repository Contracts)

---

## Capítulo 1 — Objetivo

Separar **leitura** de **escrita** no BusinessCore.

- Repositories persistem Aggregates (escrita)
- Query Services consultam dados (leitura)

Essa separação permite que consultas explorem SQL, views, índices e otimizações sem contaminar o domínio.

---

## Capítulo 2 — Filosofia

```
UseCase → Repository → Aggregate (escrita)
Dashboard → QueryService → SQL / View (leitura)
```

O domínio não precisa saber como uma consulta é otimizada.

---

## Capítulo 3 — Quando usar Query Service

| Use | Não use |
|-----|---------|
| Dashboard | Salvar Aggregate |
| Relatórios | Executar regras de negócio |
| Pesquisas | Validar domínio |
| KPIs | Gerar eventos |
| BI | Alterar estado |
| Exportação | |

---

## Capítulo 4 — Interface Base

```
IQueryService<T>
├── findById(id)
├── find(criteria)
├── list(criteria)
├── count(criteria)
└── exists(id)
```

Diferente do Repository, o Query Service retorna **Read Models**, não Aggregates.

---

## Capítulo 5 — Read Models

Read Models são objetos de **leitura** otimizados para a consulta.

```
Read Model: OrderSummary
├── OrderId
├── Number
├── CustomerName
├── TotalAmount
├── Status
├── ItemCount
└── CreatedAt
```

Read Models não possuem comportamento de domínio. São apenas dados.

---

## Capítulo 6 — Catálogo de Query Services

```
CustomerQueryService
├── findActive()
├── findByDocument(document)
├── findByRegion(regionId)
├── topByRevenue(limit, period)
└── creditAnalysis(customerId)

ProductQueryService
├── findActive()
├── findByCategory(categoryId)
├── findByNcm(ncm)
├── lowStock(threshold)
└── priceHistory(productId)

OrderQueryService
├── findPending()
├── findByCustomer(customerId)
├── findByPeriod(startDate, endDate)
├── byStatus(status)
├── overdue()
└── summary(criteria)

FiscalQueryService
├── pendingTransmission()
├── findByPeriod(period)
├── spedData(period)
└── taxSummary(period)

AccountingQueryService
├── trialBalance(period)
├── balanceSheet(date)
├── dre(period)
├── accountBalance(accountId, period)
└── costCenterSummary(periodId, costCenterId)
```

---

## Capítulo 7 — Organização Física

```
business_core/
  queries/
    interfaces/
      IQueryService.py
    party/
      CustomerQueryService.py
    product/
      ProductQueryService.py
    order/
      OrderQueryService.py
    fiscal/
      FiscalQueryService.py
    accounting/
      AccountingQueryService.py
```

Implementações concretas na camada de infraestrutura:

```
infrastructure/
  postgres/
    queries/
      OrderQueryService.py
      FiscalQueryService.py
```

---

## Capítulo 8 — Exemplo de Implementação

```python
# Interface (domínio)
class IOrderQueryService(ABC):
    def find_pending(self) -> list[OrderSummary]: ...
    def by_status(self, status: str) -> list[OrderSummary]: ...
    def summary(self, criteria: dict) -> OrderSummaryData: ...

# Implementação (infraestrutura)
class PostgresOrderQueryService(IOrderQueryService):
    def find_pending(self):
        result = db.execute("""
            SELECT id, number, customer_name,
                   total_amount, status, created_at
            FROM orders
            WHERE status = 'pending'
            ORDER BY created_at DESC
        """)
        return [OrderSummary(**row) for row in result]
```

O domínio conhece apenas a interface. O SQL fica na infraestrutura.

---

## Capítulo 9 — Query Services × COBOL

Para consultas executadas em COBOL:

```python
class CobolOrderQueryService(IOrderQueryService):
    def find_pending(self):
        cobol_program = CobolProgram('QRY_ORDERS')
        cobol_program.set_status('PENDING')
        cobol_program.execute()
        return [OrderSummary(**record) for record in cobol_program.results]
```

A interface permanece a mesma.

---

## Capítulo 10 — View Materializadas

Consultas pesadas podem usar views materializadas:

```sql
CREATE MATERIALIZED VIEW mv_order_summary AS
SELECT o.id, o.number, p.name AS customer_name,
       o.total_amount, o.status, o.created_at,
       COUNT(oi.id) AS item_count
FROM orders o
JOIN parties p ON o.customer_id = p.id
JOIN order_items oi ON oi.order_id = o.id
GROUP BY o.id, p.name;
```

O Query Service consulta a view como se fosse uma tabela. A infraestrutura decide quando refrescar.

---

## Capítulo 11 — Benefícios

- Domínio limpo (sem SQL, sem preocupações de performance)
- Consultas otimizadas sem afetar a escrita
- Read Models específicos para cada caso de uso
- Facilidade para dashboards e BI
- Suporte nativo a COBOL e PostgreSQL
- Preparação para CQRS no futuro (trocar implementação sem alterar contratos)

---

## Capítulo 12 — Arquitetura Geral

```
Escrita (Command Side)              Leitura (Query Side)
─────────────────────               ────────────────────
Command → UseCase                   Request → Controller
  → Aggregate                         → QueryService
  → Repository                        → SQL / View / COBOL
  → UnitOfWork                        → ReadModel
  → DomainEvent                       → Response
  → Dispatcher
```

Essa separação é a base para evoluir para CQRS completo no N3 sem reescrever o domínio.

---

**Arquivo:** `docs/BC-101C_QUERY_SERVICES.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
