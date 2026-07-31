# TODO — Organização, Estabelecimentos e Hub Configurações

**Status:** plano aprovado (31/07/2026)  
**Fonte:** [`RFC-ORGANIZATION-ESTABLISHMENT.md`](./RFC-ORGANIZATION-ESTABLISHMENT.md)  
**Filosofia:** Simple is always better than complex.

---

## Decisões travadas (não reabrir sem motivo)

- [x] Organização (tenant) × Estabelecimento (matriz/filial fiscal) × Terminal
- [x] Catálogo único; `available_at` multi-select; **vazio = todas** as filiais ativas
- [x] NFC-e / caixa no estabelecimento do terminal (não no escopo do produto)
- [x] Terminal criado já vinculado a pessoa; vendedor ↔ PDV **1:1**
- [x] Gerente/Caixa vê todos os PDVs e Caixas do estabelecimento
- [x] Só **Administrador** cria/edita terminais e configs genéricas
- [x] Hub **Configurações** (menu principal) = configs genéricas dos módulos instalados
- [x] UX: sidebar = Gerais + módulos; contexto = formulário do item selecionado
- [x] **1ª visão = Gerais** (transversal); depois cada módulo com as configs dele
- [x] Gerais = formulário (selects, país, senhas, toggles, upload logo…)

---

## TODO — implementação

### 1. Hub Configurações (shell)

- [x] Refatorar `pages/configuracoes.html` para o shell aprovado
  - Sidebar: **Gerais** (default) + módulos instalados
  - Área de contexto: formulário do item ativo (sem grade de cards como destino)
- [x] Sidebar alimentada pelos módulos ativos da organização (`js/configuracoes.js`)
- [ ] Restringir acesso ao papel Administrador (ainda sem guard de auth)

### 2. Gerais (primeira visão)

- [x] Bloco **Organização** — nome, logo, contato, módulos ligados (localStorage demo)
- [x] Bloco **Estabelecimentos** — lista (API admin ou `data/empresas.json`); CRUD completo ainda em `empresas.html`
- [x] Bloco **Usuários e perfis** — campos demo + link para `usuarios.html` (CRUD completo depois)
- [x] Bloco **Preferências** — idioma, fuso, formato data, moeda, tema, país
- [x] Bloco **Segurança** — timeout, política de senha, bloqueio, reauth
- [x] Controles: select, país, password, toggle, upload logo
- [x] **Não** colocar CSC/certificado/série NFC-e aqui

### 3. Módulo POS (dentro de Configurações)

- [x] Placeholder na sidebar / painel POS
- [x] Seção **Terminais** — listar PDVs e Caixas (`/api/admin/pos/terminais` + fallback local)
- [x] Wizard: tipo → estabelecimento → código/nome → vínculo → configs → ativo
- [x] Vendedor 1:1 enforced na API; gerente/caixa no select do Caixa
- [x] Configs genéricas POS (impressora, balança, treino, timeout, emite NFC-e)
- [x] Reatribuição de vínculo só via Admin (editar titular no wizard)
- [ ] Ligar terminal ao login do PDV operacional (`pos.html`)

### 4. Módulo Fiscal (dentro de Configurações)

- [x] Placeholder + atalhos certificados / NFC-e
- [ ] Certificado, CSC, série/número NFC-e por estabelecimento
- [ ] Ambiente homologação/produção
- [ ] Consumido pelo Caixa; nunca editado no PDV

### 5. Modelo de dados / APIs

- [ ] Unificar `data/empresas.json` + `dados/empresa.json` → Organização + Estabelecimentos
- [ ] Persistência de terminais (PDV/Caixa) + vínculo usuário
- [ ] `available_at` no cadastro de produto
- [ ] POS filtrar catálogo por estabelecimento + `available_at`
- [ ] Emitente NFC-e = estabelecimento do terminal

### 6. Em aberto (decidir depois)

- [ ] Preço: lista única da org com override local, ou só local?
- [ ] Gerente/Caixa: terminal hub vs papel elevado em qualquer estação?
- [ ] Amarrar `device id` ao terminal ou login do titular em qualquer máquina?
- [ ] Numeração NFC-e: confirmar sempre por estabelecimento

### 7. Fora deste plano (não misturar)

- CSC real / SEFAZ ponta a ponta (recurso externo)
- Promise Engine multi-filial
- Balança física (hoje mock)
- RFCs de Receiving (`RFC-RECEIVING-ENGINE/`) — pasta local, não misturar neste TODO

---

## Ordem sugerida ao voltar

1. ~~Shell Configurações (Gerais + sidebar)~~ ✅  
2. ~~Gerais mínimos (formulário)~~ ✅  
3. ~~POS → terminais (wizard)~~ ✅  
4. **Fiscal por estabelecimento** ← próximo  
5. Ligar POS operacional ao estabelecimento/terminal  
6. Guard Admin na página Configurações  

---

*POS terminais: Configurações → POS → + Novo terminal (`data/pos_terminais.json`).*
