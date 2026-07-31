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

- [ ] Refatorar `pages/configuracoes.html` para o shell aprovado
  - Sidebar: **Gerais** (default) + módulos instalados
  - Área de contexto: formulário do item ativo (sem grade de cards como destino)
- [ ] Sidebar alimentada pelos módulos ativos da organização
- [ ] Restringir acesso ao papel Administrador

### 2. Gerais (primeira visão)

- [ ] Bloco **Organização** — nome, logo, contato, módulos ligados
- [ ] Bloco **Estabelecimentos** — lista/criar matriz-filiais (código, nome, ativo, endereço, CNPJ/IE, país/UF)
- [ ] Bloco **Usuários e perfis** — CRUD + perfis (Admin, Vendedor, Caixa, Gerente)
- [ ] Bloco **Preferências** — idioma, fuso, formato data/número, moeda, tema
- [ ] Bloco **Segurança** — timeout, política de senha, bloqueio de login
- [ ] Controles: select, país, password, toggle, máscaras CNPJ/CEP, upload logo
- [ ] **Não** colocar CSC/certificado/série NFC-e aqui

### 3. Módulo POS (dentro de Configurações)

- [ ] Seção **Terminais** — listar PDVs e Caixas por estabelecimento
- [ ] Wizard: tipo → estabelecimento → código/nome → vínculo → configs → ativo
- [ ] Vendedor 1:1; gerente/caixa com visão ampla
- [ ] Configs genéricas POS (impressora, balança, treino, timeout, fila destino…)
- [ ] Reatribuição de vínculo só via Admin (cobertura)

### 4. Módulo Fiscal (dentro de Configurações)

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

1. Shell Configurações (Gerais + sidebar)  
2. Gerais mínimos (org + estabelecimentos + usuários)  
3. POS → terminais (wizard)  
4. Fiscal por estabelecimento  
5. Ligar POS operacional ao estabelecimento/terminal  

---

*Pausa — continuar a partir daqui.*
