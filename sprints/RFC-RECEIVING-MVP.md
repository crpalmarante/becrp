# RFC: Receiving MVP (entrada que pluga no Inventário)

| Campo | Valor |
|--------|--------|
| Status | **Implementação (passo C)** |
| Data | 31/07/2026 |
| Escopo | Coordenar recebimento manual → conferência → `inventory_apply_receive` |
| Relaciona | `RFC-INVENTORY-MVP`, `RFC-4001`, `RFC-4009` |
| Não é | XML NF-e, Fiscal, Financeiro, Pending Items, Workspace completo |

---

## Filosofia

> Simple is always better than complex.

Receiving **coordena**. Inventário **move estoque**. Fiscal/Financeiro ficam para depois.

---

## Fluxo MVP

```
draft  →  verified  →  completed
   ↘ cancel
```

1. Criar recebimento (loja + itens + qty esperada)
2. Conferir (qty verificada; default = esperada)
3. Concluir → `inventory_mvp.inventory_apply_receive` → movimentos `receive`

---

## Fora do MVP

- Monitor XML / parser NF-e
- Integração Fiscal (RFC-4011) e Financeira (RFC-4010)
- Pending items (RFC-4007)
- Workspace completo (RFC-4006)
- Lotes / séries / localização interna

---

## API

| Método | Rota | Ação |
|--------|------|------|
| GET | `/api/receiving` | Lista (`?estabelecimento_id=&status=`) |
| GET | `/api/receiving/{id}` | Detalhe |
| POST | `/api/receiving` | Cria (`draft`) |
| POST | `/api/receiving/{id}/verify` | Conferência |
| POST | `/api/receiving/{id}/complete` | Inventário + `completed` |
| POST | `/api/receiving/{id}/cancel` | Cancela (não se já completed) |

---

## Dados

`data/receivings.json` — ledger do recebimento (não é estoque).

Warehouse = `estabelecimento_id`.

---

## UI

`pages/recebimento.html` — lista, novo, conferir, concluir.

Menu: **Inventário → Recebimento**.

---

*RFCs 4001–4012 = visão completa. Esta RFC = fatia que desbloqueia entrada real no ledger.*
