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
| **2** | **Produtos + `available_at`** (catálogo por filial) | 🔄 próximo |
| **3** | **Fiscal por estabelecimento** (cert/CSC/série = emitente da loja) | pendente |
| **4** | **Usuários operacionais** (vendedor/caixa/gerente) — não RH Funcionários | pendente |
| **5** | **Inventário** / Promise Engine | depois |

**Fora do caminho crítico do POS agora:** Funcionários (folha/RH), Receiving, balança física, CSC SEFAZ ponta a ponta (recurso externo).

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
- [ ] Restringir acesso ao papel Administrador (ainda sem guard de auth)

### 2. Gerais (primeira visão)

- [x] Blocos Organização / Estabelecimentos (cards) / Preferências / Segurança
- [x] Controles: select, país, password, toggle, upload logo
- [x] **Não** colocar CSC/certificado/série NFC-e aqui

### 3. Módulo POS (Configurações + operacional)

- [x] Wizard terminais + API `/api/admin/pos/terminais` + 1:1
- [x] **#1** Ligar terminal ao login do PDV (`GET /api/pos/contexto` + UI topbar / modo)
- [ ] **#2** Catálogo `available_at` + filtro no POS
- [ ] **#3** Fiscal por estabelecimento (cert/CSC/série)
- [ ] **#5** Inventário real (depois)

### 4. Modelo de dados / APIs

- [ ] Unificar `data/empresas.json` + `dados/empresa.json` → Organização + Estabelecimentos
- [x] Persistência de terminais (PDV/Caixa) + vínculo usuário
- [ ] `available_at` no cadastro de produto
- [ ] POS filtrar catálogo por estabelecimento + `available_at`
- [ ] Emitente NFC-e = estabelecimento do terminal

### 5. Em aberto (decidir depois)

- [ ] Preço: lista única da org com override local, ou só local?
- [ ] Gerente/Caixa: terminal hub vs papel elevado em qualquer estação?
- [ ] Amarrar `device id` ao terminal ou login do titular em qualquer máquina?
- [ ] Numeração NFC-e: confirmar sempre por estabelecimento

### 6. Fora deste plano (não misturar)

- CSC real / SEFAZ ponta a ponta (recurso externo)
- Promise Engine multi-filial
- Balança física (hoje mock)
- RFCs de Receiving (`RFC-RECEIVING-ENGINE/`) — pasta local
- Módulo RH Funcionários completo (não é pré-requisito do POS)

---

## Ordem sugerida (execução)

1. ~~Shell + Gerais + wizard terminais~~ ✅  
2. ~~Terminal → POS operacional~~ ✅ (`/api/pos/contexto`)  
3. **Produtos + `available_at`** ← próximo  
4. Fiscal por estabelecimento  
5. Usuários operacionais (perfis)  
6. Inventário / Promise  

---

*Usuários demo POS: `ana` / `carla` (senha `123`) → PDV-01 / CX-01 na matriz.*
