# TODO — Organização, Estabelecimentos e Hub Configurações

**Status:** plano aprovado (31/07/2026)  
**Fonte:** [`RFC-ORGANIZATION-ESTABLISHMENT.md`](./RFC-ORGANIZATION-ESTABLISHMENT.md)  
**Filosofia:** Simple is always better than complex.

---

## Ordem de ataque (POS — travada 31/07/2026)

Atacar o que **desbloqueia venda hoje**. Se não impede *pedido → caixa → NFC-e*, fica depois.

| # | Foco | Status |
|---|------|--------|
| **1** | **Terminal → POS** (login, estabelecimento, papel/modo) | ✅ |
| **2** | **Produtos + `available_at`** (catálogo por filial) | ✅ |
| **3** | **Fiscal por estabelecimento** (cert/CSC/série = emitente da loja) | ✅ |
| **4** | **Usuários operacionais** (vendedor/caixa/gerente) — não RH Funcionários | ✅ |
| **5** | **Inventário** / Promise Engine | ✅ |

**Fora do caminho crítico do POS agora:** Funcionários (folha/RH), Receiving (depois do Inventário MVP), balança física, CSC SEFAZ ponta a ponta (recurso externo).

---

## Ordem seguinte (Inventário → Receiving)

| # | Foco | Status |
|---|------|--------|
| **A** | **RFC Inventário MVP** — [`RFC-INVENTORY-MVP.md`](./RFC-INVENTORY-MVP.md) | ✅ |
| **B** | Migrar `estoque.json` → movimentos + saldo + Promise na nova fonte | ✅ |
| **C** | Receiving Engine (pluga em `inventory_apply_receive`) | ✅ |

Fonte das verdades: warehouse = estabelecimento; toda qty = movimento; Promise só lê.

**Não agora:** Inventário “puro” / WMS ([`RFC-5000`](./RFC-INVENTORY-ENGINE/RFC-5000%20-%20INVENTORY-ARCHITECTURE.md)) — lote, bin, reserva formal, contagem cíclica. O MVP **é** o inventário operacional. Só aprofundar se surgir dor (transferir / ajustar / ver saldo).

Próximos ganhos possíveis (escolher por dor, não por RFC):
- ~~UI fina de inventário (saldo + transfer + adjust)~~ ✅ `pages/estoque.html`
- ~~Endurecer POS (interno)~~ ✅ estoque bloqueia · troca via `/api/pos/vendas` · sangria/suprimento persistidos
- ~~Unificar org/estabelecimentos~~ ✅ `org_store.py`
- Receiving mais útil (XML/NF-e) — se entrada manual doer  
  **Decisão:** XML de entrada ≠ Inventário ≠ Faturamento.  
  Fluxo: `XML → Fiscal/Documentos (parse) → Receiving (conferência) → Inventory (receive)`.  
  UI: Recebimento / Compras, não Estoque nem Faturamento.  
  ✅ **RFC-4002 MVP:** `nfe_inbound.py` · `POST /api/receiving/from-xml` · upload em `pages/recebimento.html`  
  ✅ **RFC-4004 MVP:** `product_localization.py` · vínculo fornecedor×produto · busca UI · match `supplier_ref`/`ean`/`codigo`  
  ✅ **RFC-4008 MVP:** conferência física com Δ/avaria/notas · bip EAN · reabrir · `verification` no receiving  
  ✅ **RFC-4003 MVP:** `nfe_monitor.py` · inbox `data/nfe_inbox/` · fila UI · process → receiving  
  ✅ **RFC-4005 MVP:** `partner_lookup.py` · CNPJ→fornecedor · link manual · sem criar cadastro  
  ✅ **RFC-4007 MVP:** `receiving_pending.py` · fila produto/fornecedor/conferência/XML · resolve/ignore  
  (Receiving “útil” fechado no essencial)
- ✅ **Fechamento de caixa (turno):** `pos_caixa.py` sessão · Abrir/Fechar no POS · esperado = fundo + dinheiro + supr. − sangria · Δ no fechamento · pagamento exige sessão aberta
- ✅ **Listas de preço (MVP Odoo-like):** `price_lists.py` · preço fixo por item · `default_price_list_id` no estabelecimento · POS resolve lista→base · UI `pages/listas-preco.html`
- ✅ **Troca/devolução + gerente:** `POST /api/pos/autorizar-gerente` · carimbo na fila/venda · UI senha no Smart Panel · treino auto-autoriza
- NFC-e SEFAZ / balança física — força externa (não agora)
- Campanha (categoria + período + forma pgto) — depois; não misturar no MVP de lista

**Próximo ataque interno (ordem):** (1) ~~caixa~~ ✅ → (2) ~~preço/listas~~ ✅ → (3) ~~troca + gerente~~ ✅

---

## Decisões travadas (não reabrir sem motivo)

- [x] Organização (tenant) × Estabelecimento (matriz/filial fiscal) × Terminal
- [x] Catálogo único; `available_at` multi-select; **vazio = todas** as filiais ativas
- [x] NFC-e / caixa no estabelecimento do terminal (não no escopo do produto)
- [x] Terminal criado já vinculado a pessoa; vendedor ↔ PDV **1:1**
- [x] Gerente/Caixa vê todos os PDVs e Caixas do estabelecimento
- [x] Só **Administrador** cria/edita terminais e configs genéricas
- [x] Hub **Configurações** (menu principal) = configs genéricas dos módulos instalados
- [x] UX: sidebar = Gerais + módulos; contexto = formulário do item ativo
- [x] **1ª visão = Gerais** (transversal); depois cada módulo com as configs dele
- [x] Gerais = formulário (selects, país, senhas, toggles, upload logo…)
- [x] Ordem de ataque acima (Terminal→POS → Produtos → Fiscal → Usuários ops → Inventário)

---

## TODO — implementação

### 1. Hub Configurações (shell)

- [x] Refatorar `pages/configuracoes.html` para o shell aprovado
- [x] Sidebar alimentada pelos módulos ativos da organização
- [x] Restringir acesso ao papel Administrador (guard em `configuracoes.js`)

### 2. Gerais (primeira visão)

- [x] Blocos Organização / Estabelecimentos (cards) / Preferências / Segurança
- [x] Controles: select, país, password, toggle, upload logo
- [x] **Não** colocar CSC/certificado/série NFC-e aqui

### 3. Módulo POS (Configurações + operacional)

- [x] Wizard terminais + API `/api/admin/pos/terminais` + 1:1
- [x] **#2** Catálogo `available_at` + filtro no POS (`produtos_para_pos`, UI em Produtos)
- [x] **#3** Fiscal por estabelecimento (cert/CSC/série) — `data/estabelecimentos_fiscal.json` + Configurações → Fiscal
- [x] **#5** Inventário / Promise (`data/estoque.json`, enrich `/api/pos/produtos`, `GET /api/pos/promise`, baixa na finalização)

### 4. Modelo de dados / APIs

- [x] Unificar `data/empresas.json` + `dados/empresa.json` → Organização + Estabelecimentos (`org_store.py`; `empresa.json` = espelho legado)
- [x] Persistência de terminais (PDV/Caixa) + vínculo usuário
- [x] `available_at` no cadastro de produto
- [x] POS filtrar catálogo por estabelecimento + `available_at`
- [x] Emitente NFC-e = estabelecimento do terminal
- [x] Promise Engine multi-filial (local / branch / transit / none)

### 5. Em aberto (decidir depois)

- [x] Preço: listas da org + lista padrão por estabelecimento (fixo; fallback `produto.preco`)
- [ ] Gerente/Caixa: terminal hub vs papel elevado em qualquer estação?
- [ ] Amarrar `device id` ao terminal ou login do titular em qualquer máquina?
- [ ] Numeração NFC-e: confirmar sempre por estabelecimento

### 6. Fora deste plano (não misturar)

- CSC real / SEFAZ ponta a ponta (recurso externo)
- Balança física (hoje mock)
- RFCs de Receiving (`RFC-RECEIVING-ENGINE/`) — pasta local
- Módulo RH Funcionários completo (não é pré-requisito do POS)

---

## Ordem sugerida (execução)

1. ~~Shell + Gerais + wizard terminais~~ ✅  
2. ~~Terminal → POS operacional~~ ✅ (`/api/pos/contexto`)  
3. ~~Produtos + `available_at`~~ ✅  
4. ~~Fiscal por estabelecimento~~ ✅  
5. ~~Usuários operacionais (perfis)~~ ✅  
6. ~~Inventário / Promise~~ ✅ (`estoque.json` + badges no POS)  
7. ~~Inventário MVP~~ ✅ (`inventory_mvp.py` + ledger JSON)  
8. ~~Receiving~~ ✅ ([`RFC-RECEIVING-MVP.md`](./RFC-RECEIVING-MVP.md) · `receiving_mvp.py` · `/pages/recebimento.html`)  
9. ~~NF-e XML inbound (RFC-4002)~~ ✅ (`nfe_inbound.py` · `POST /api/receiving/from-xml` · link-product)  
10. ~~Localização de produtos (RFC-4004)~~ ✅ (`product_localization.py` · refs · product-search)  
11. ~~Conferência física (RFC-4008)~~ ✅ (verify/scan/reopen · qty boa vs avaria · inventário só no complete)  
12. ~~Monitor XML (RFC-4003)~~ ✅ (`nfe_monitor.py` · inbox · `/api/nfe-monitor`)  
13. ~~Business Partner Lookup (RFC-4005)~~ ✅ (`partner_lookup.py` · `/api/partners/lookup`)  
14. ~~Pendências Receiving (RFC-4007)~~ ✅ (`receiving_pending.py` · `/api/receiving/pending`)  
15. ~~Fechamento de caixa~~ ✅ (`pos_caixa` sessão · `/api/pos/caixa/sessao` · Abrir/Fechar no `pages/pos.html`)  
16. ~~Listas de preço~~ ✅ (`price_lists.py` · `/api/admin/price-lists` · `pages/listas-preco.html` · POS `/api/pos/produtos`)  
17. ~~Troca/devolução com gerente~~ ✅ (`/api/pos/autorizar-gerente` · `troca_aprovacao` na fila)  

---

*Perfis POS: admin · vendedor · caixa · gerente. Demo: `ana` / `carla` / `bruno` / `admin` · senha `123`.*
