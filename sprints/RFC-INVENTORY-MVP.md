# RFC: Inventário MVP (núcleo durável)

| Campo | Valor |
|--------|--------|
| Status | **Aprovado — passo B implementado** |
| Data | 31/07/2026 |
| Escopo | Modelo mínimo de estoque: movimentos, saldo, Promise, contrato Receiving |
| Relaciona | Promise POS (`estoque.json`), `RFC-4009`, `RFC-ORGANIZATION-ESTABLISHMENT` |
| Não é | WMS completo (`RFC-INVENTORY-ARCHITECTURE` fica como roadmap futuro) |

---

## 1. Filosofia

> Simple is always better than complex.

Inventário é **dono do estoque**. Ninguém mais altera quantidade “na mão”.

O Promise do POS **lê** disponibilidade. Receiving **pede** entrada. Venda **pede** saída. Só o Inventário executa.

---

## 2. Por que agora

Hoje o POS usa `data/estoque.json` com qty direta + baixa na finalização. Isso desbloqueou venda, mas:

- não há histórico auditável;
- Receiving (RFC-4009) espera *movements* e *transaction ids*;
- transferência / trânsito / ajuste vão virar gambiarras se não houver núcleo.

Definir o MVP **antes** do Receiving evita refatorar duas vezes.

---

## 3. Decisões travadas (MVP)

| # | Decisão |
|---|--------|
| 1 | **Warehouse = Estabelecimento** (1:1 no varejo). Sem corredor/bin agora. |
| 2 | **Toda alteração de qty = movimento** (nunca `qty = N` direto no saldo). |
| 3 | **Saldo** = derivado dos movimentos (cache permitido, fonte da verdade = ledger). |
| 4 | **Físico ≠ disponível** no modelo; no MVP disponível ≈ físico − 0 reservas (reserva formal fica depois). |
| 5 | **Trânsito** é estado de movimento (ou saldo `in_transit`), não campo solto eterno. |
| 6 | **Promise** continua a API de leitura do POS (`local` / `branch` / `transit` / `none`); passa a ler o ledger. |
| 7 | **Receiving não grava estoque** — só envia `InventoryRequest` (RFC-4009). |
| 8 | **POS / NFC-e** não grava estoque — chama saída de inventário na finalização. |

---

## 4. Fora do MVP (não misturar)

- Localizações internas (rua / prateleira / doca)
- Lotes / séries / validade
- Reserva formal de pedido / e-commerce
- Picking / packing / shipping / quality / replenishment
- Custo médio avançado / inventário contábil
- Contagem cíclica completa (ajuste manual simples **entra** no MVP)

Esses itens vivem nas RFCs grandes de arquitetura; só entram quando o núcleo estiver estável.

---

## 5. Tipos de movimento

| Tipo | Direção | Origem típica | Efeito |
|------|---------|---------------|--------|
| `sale` | − | POS / finalização venda | Baixa na loja do terminal |
| `receive` | + | Receiving (após conferência) | Entrada na warehouse do recebimento |
| `transfer_out` | − | Transferência entre lojas | Sai da origem |
| `transfer_in` | + | Conclusão da transferência | Entra no destino |
| `transit` | 0 / meta | Embarque CD→loja | Promise `transit` até `transfer_in` / `receive` |
| `adjust` | ± | Inventário / correção | Ajuste auditável com motivo |

Regras:

- Transferência loja↔loja = par `transfer_out` + `transfer_in` (mesmo `group_id`).
- Movimento sempre tem: `id`, `tipo`, `estabelecimento_id`, `produto_id`, `qty`, `at`, `ref` (venda / receiving / ajuste), `user_id` opcional.
- Qty sempre **positiva**; a direção vem do tipo.

---

## 6. Schema (proposta)

Arquivos sob `data/` (JSON no estágio atual; SQL depois sem mudar o contrato).

### 6.1 Ledger — `data/inventory_movements.json`

```json
{
  "next_id": 1,
  "movements": [
    {
      "id": 1,
      "tipo": "receive",
      "estabelecimento_id": "matriz",
      "produto_id": "1",
      "qty": 50,
      "at": "2026-07-31T10:00:00",
      "ref_tipo": "seed",
      "ref_id": "bootstrap",
      "group_id": null,
      "nota": "carga inicial"
    }
  ]
}
```

### 6.2 Saldo cache — `data/inventory_balances.json` (opcional mas recomendado)

```json
{
  "por_estabelecimento": {
    "matriz": { "1": 50, "2": 80 }
  },
  "atualizado_em": "2026-07-31T10:00:00"
}
```

- Reconstruível a qualquer momento a partir do ledger.
- Promise e telas leem o cache; escrita **só** via API de movimento.

### 6.3 Trânsito aberto — `data/inventory_transit.json`

```json
{
  "itens": [
    {
      "id": "t1",
      "produto_id": "4",
      "qty": 40,
      "origem": "CD Central",
      "destino_estabelecimento_id": "matriz",
      "eta_horas": 24,
      "status": "open",
      "movement_id": 12
    }
  ]
}
```

Substitui o bloco `transito` de `estoque.json`.

### 6.4 Deprecação

| Antes | Depois |
|-------|--------|
| `data/estoque.json` | migrado → seed de movimentos + balances + transit |
| `baixar_estoque_local()` | `inventory_apply_sale(...)` (movimento `sale`) |
| Promise lê `estoque.json` | Promise lê balances + transit |

---

## 7. API interna (contrato estável)

```
inventory_apply_movement(tipo, estabelecimento_id, produto_id, qty, ref_tipo, ref_id, ...)
inventory_apply_sale(estabelecimento_id, linhas, venda_id)
inventory_apply_receive(InventoryRequest)          → InventoryResponse  (RFC-4009)
inventory_transfer(origem, destino, linhas, ...)  → group_id + out/in
inventory_balance(estabelecimento_id, produto_id) → int
inventory_promise(estabelecimento_id, produto_id) → local|branch|transit|none
```

HTTP (quando exposto):

| Método | Rota | Uso |
|--------|------|-----|
| GET | `/api/inventory/balance?estabelecimento_id=&produto_id=` | Consulta |
| GET | `/api/pos/promise` | Mantém (já existe) |
| POST | `/api/inventory/adjust` | Admin / inventário |
| POST | `/api/inventory/transfer` | Admin / logística |

Receiving chama a API interna / evento — **não** grava JSON de estoque.

---

## 8. Promise (inalterado na UX)

Ordem de resolução (já implementada):

1. saldo local > 0 → `local`
2. saldo em outra loja ativa > 0 → `branch` (~SLA h)
3. trânsito aberto para a loja → `transit`
4. senão → `none`

Só muda a **fonte** dos números (ledger/cache).

---

## 9. Alinhamento RFC-4009

| Receiving envia | Inventário faz |
|-----------------|----------------|
| `receiving_id`, warehouse, itens verificados | Gera `receive` por item |
| | Retorna `movement_ids` + status |
| Erro de inventário | **Não** reescreve histórico do Receiving |

Warehouse no MVP = `estabelecimento_id`.

---

## 10. Ordem de execução

| # | Passo | Resultado |
|---|--------|-----------|
| **1** | Aprovar esta RFC | Contrato travado |
| **2** | Implementar ledger + migrate seed de `estoque.json` | POS Promise continua igual |
| **3** | Trocar baixa de venda → `sale` | Sem qty direta |
| **4** | Só então: Receiving Engine | Pluga em `inventory_apply_receive` |

Não abrir WMS nem Receiving em paralelo ao passo 2–3.

---

## 11. Critério de pronto (MVP)

- [x] Nenhum código de domínio grava qty sem movimento (`inventory_mvp.py`)
- [x] Seed atual (matriz / SP / RJ + trânsito açúcar) reproduz os mesmos badges no POS
- [x] Finalizar venda cria movimento `sale` e atualiza saldo
- [x] Função pronta para `receive` (mesmo sem UI de Receiving)
- [x] `estoque.json` legado (deprecated); fonte = `inventory_movements` / `balances` / `transit`

---

## 12. Relação com RFCs grandes

`RFC-INVENTORY-ARCHITECTURE` e `RFC-INVENTORY-MODERN-ERP-ARCHITECTURE` = **visão futura**.

Esta RFC = **o que construímos agora**. Em conflito, vale o MVP até nova decisão explícita.

---

*Passo B feito. Próximo: passo C — Receiving Engine pluga em `inventory_apply_receive`.*
