# TODO — Delivery Platform

Princípio:

> Simple is always better than complex.

Regra vigente:

- POS / Sales baixa estoque de venda
- WMS **não** baixa estoque de venda
- Delivery **nunca** move inventário

---

# Status geral

| Fase | RFCs | Status |
| ---- | ---- | ------ |
| 1 · Delivery Core | 18000–18008 | **Done** (MVP JSON + UI `pages/entregas.html`) |
| 2 · Operational Workspace | 18100–18108 | **Done** (`entregas-workspace.html` e demais) |
| 3 · Execution Lifecycle | 18110–18119 | **Done** (trip lifecycle + outcomes) |
| 4 · Mobile Operations | 18200–18207 | ⏳ Planned (RFCs 18200–18203 escritas) |
| 5 · Customer Experience | 18300–18305 | ⏳ Planned |
| 6 · Delivery Pricing | 18400–18406 | ⏳ Planned |
| 7 · Operational Resources | 18500–18504 | ⏳ Planned |
| 8 · Monitoring and Control | 18600–18604 | ⏳ Planned |
| 9 · Business Intelligence | 18700–18705 | ⏳ Planned |
| 10 · Future Extensions | 18800 | ⏳ Planned |
| Integração POS fulfillment | — | Opcional / depois |

---

# Done — Delivery Core (18000–18008)

| RFC | Módulo | Arquivo |
| --- | ------ | ------- |
| 18000 / 18001 | Orders + stops | `delivery_orders.py` |
| 18002 | Tasks | `delivery_tasks.py` |
| 18003 | Dispatch | `delivery_dispatch.py` |
| 18004 | Resources | `delivery_resources.py` |
| 18005 | Scheduling | `delivery_scheduling.py` |
| 18006 | Tracking | `delivery_tracking.py` |
| 18007 | Proof of Delivery | `delivery_pod.py` |
| 18008 | Analytics | `delivery_analytics.py` |

Integrações já ligadas:

- WMS expedição `dispatch` → DO idempotente
- Agenda → promise na DO
- Tracking sync nas transições
- POD obrigatório para `complete` da DO

UI: abas Pedidos · Agenda · Tracking · POD · Analytics · Despacho · Tarefas · Recursos  
Menu: módulo **Entregas**

---

# Done — Operational Workspace (18100–18108)

| RFC | Feature | Implementação |
| --- | ------- | ------------- |
| 18100 | Workspace (cockpit) | `delivery_workspace.py` + `pages/entregas-workspace.html` |
| 18101 | Dashboard (overview do dia) | `delivery_dashboard.py` + `pages/entregas-dashboard.html` |
| 18102 | Queue (fila acionável) | `delivery_queue.py` + `pages/entregas-fila.html` |
| 18103 | Planning Board | `delivery_planning.py` + `pages/entregas-planejamento.html` |
| 18104 | Calendar / Field | `delivery_calendar.py` + `pages/entregas-calendario.html` |
| 18105 | Manifest | `delivery_manifest.py` + `pages/entregas-manifesto.html` |
| 18106 | Trip | `delivery_trip.py` + `pages/entregas-viagem.html` |
| 18107 | Driver Workspace | `delivery_driver_workspace.py` + `pages/entregas-motorista.html` |
| 18108 | Stops | `delivery_stops.py` + `pages/entregas-paradas.html` |

Roles de escrita: `admin`, `gerente`, `supervisor` (`DELIVERY_WRITE_ROLES`)

---

# Done — Execution Lifecycle (18110–18119)

| RFC | Feature | Implementação |
| --- | ------- | ------------- |
| 18110 | Trip Start | `delivery_trip.transition(tid, "start")` — partida + manifest `start` + DO `depart` |
| 18111 | Stop Execution | `transition("arrive_stop" / "start_service" / "complete_stop")` |
| 18112 | Trip Progress | `_progress()` + auto `completed` quando restantes = 0 |
| 18113 | Delivery Exceptions | eventos independentes em `delivery_tracking.py` / `delivery_stops.py` |
| 18114 | Partial Deliveries | outcome parcial em `delivery_orders.transition` |
| 18115 | Failed Deliveries | `transition("fail_stop")` com motivo → `failed` |
| 18116 | Customer Refusal | outcome recusa em `delivery_orders.transition` |
| 18117 | Return to Warehouse (RTW) | retorno registrado em `delivery_orders.transition` |
| 18118 | Reverse Logistics | lifecycle de retorno em `delivery_orders.py` |
| 18119 | Trip Closing | `transition("complete" / "close")` + espelho no manifest |

UI de execução: `pages/entregas-motorista.html`

---

# Planejado — Mobile Operations (18200)

- ⏳ RFC-18200 — Driver Mobile Application
- ⏳ RFC-18201 — Offline Synchronization
- ⏳ RFC-18202 — GPS Integration
- ⏳ RFC-18203 — Barcode / QR Scanning
- ⏳ RFC-18204 — Camera Integration
- ⏳ RFC-18205 — Digital Signature
- ⏳ RFC-18206 — Push Notifications
- ⏳ RFC-18207 — Driver Messaging

Fases seguintes: 18300 Customer Experience · 18400 Pricing · 18500 Resources · 18600 Monitoring · 18700 BI · 18800 Future (detalhamento no roadmap do roadmap.md original).

---

# Depois (backlog)

- POS `fulfillment_mode` (retirada vs envio → WMS → Delivery)
- Hardening E2E UI do fluxo completo venda → expedição → DO → POD
- Custo/receita de frete (só quando houver motor real)

---

# Delivery Architecture Summary

```text
Sales / POS → Delivery Order → Manifest → Trip → Trip Start → Stop Execution
     → Delivery Outcome (Completed / Partial / Failed / Refusal / Return)
     → Trip Closing → Analytics
```

# Architectural Principles

- Delivery is execution, not inventory ownership.
- WMS owns inventory decisions.
- Sales owns commercial documents.
- Delivery owns physical movement.
- Exceptions are independent business entities.
- Partial delivery is normal execution, not failure.
- Documents remain immutable.
- Execution creates history.
- Every event is auditable.

---

# Notas

- RFCs: raiz = Core (18000), `RFC-DELIVERY-OPERATIONS/` = 18100–18108 + 18118–18119, `RFC-DELIVERY-EXECUTION/` = 18110–18117, `RFC-Mobile Operations (18200)/` = 18200–18203
- Dados: `dados/delivery_*.json`
- Reinício de server com exit 137 após `fuser -k` é esperado
