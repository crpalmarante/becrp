# Sprint 10 — Autenticação Real + Mult-Empresa

**FiscalBrasil ERP v1.0.0**

**Data:** Julho 2026

---

## Índice

- [1. Visão Geral](#1-visão-geral)
- [2. Backend (server.py)](#2-backend-serverpy)
- [3. Login / Setup](#3-login--setup)
- [4. Validação de Token no App](#4-validação-de-token-no-app)
- [5. Gerenciamento de Usuários](#5-gerenciamento-de-usuários)
- [6. Mult-Empresa](#6-multi-empresa)
- [7. Seletor de Empresa no Topbar](#7-seletor-de-empresa-no-topbar)
- [8. Filtro de Menu por Permissão](#8-filtro-de-menu-por-permissão)
- [9. Arquivos Entregues](#9-arquivos-entregues)
- [10. Estrutura de Dados](#10-estrutura-de-dados)

---

## 1. Visão Geral

A Sprint 10 substitui o mock de autenticação por um sistema real com mult-empresa:

- Login com validação de credenciais (SHA-256)
- Token de sessão por usuário
- Setup inicial (primeiro acesso cria admin master)
- CRUD de usuários (admin)
- CRUD de empresas/filiais (admin)
- Vínculo de usuário a empresas com role por empresa
- Seletor de empresa ativa no topbar
- Filtro de menu por permissão da empresa/role atual
- Roles: `admin`, `supervisor`, `operador`
- Bloqueio de acesso sem token válido

---

## 2. Backend (server.py)

**Arquivo:** `server.py`

### Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/auth/check-setup` | Verifica se existe admin configurado |
| `GET` | `/api/auth/me` | Retorna dados do usuário logado (valida token) + `empresas` |
| `GET` | `/api/auth/minhas-empresas` | Retorna empresas que o usuário tem acesso (com role) |
| `POST` | `/api/auth/setup` | Cria admin master (apenas primeiro acesso) |
| `POST` | `/api/auth/login` | Login com usuário/senha, devolve token + empresas |
| `POST` | `/api/auth/logout` | Invalida token |
| `GET` | `/api/admin/users` | Lista todos os usuários (admin) com `empresas` |
| `POST` | `/api/admin/users` | Cria novo usuário com vínculo de empresas (admin) |
| `POST` | `/api/admin/users/:id` | Update / toggle ativo / empresas (admin) |
| `GET` | `/api/admin/empresas` | Lista todas as empresas (admin) |
| `POST` | `/api/admin/empresas` | Cria nova empresa (admin) |
| `POST` | `/api/admin/empresas/:id` | Update / toggle ativo (admin) |
| `GET` | `/api/admin/permissions` | Lista permissões por role (admin) |

### Fluxo de Setup

```
GET /api/auth/check-setup → { setup: true }
  ↓
POST /api/auth/setup { nome, usuario, senha, email }
  ↓
{ status: "ok", id, token, nome, usuario, role: "admin" }
```

### Fluxo de Login

```
POST /api/auth/login { usuario, senha }
  ↓
{ status: "ok", id, token, nome, usuario, role }
```

### Segurança

- Senhas armazenadas como hash SHA-256 (nunca em texto plano)
- Token aleatório gerado por `secrets.token_hex(16)`
- Armazenamento em `data/users.json`
- Rotas admin protegidas por verificação de role

---

## 3. Login / Setup

**Arquivos:** `login.html`, `js/login.js`

### login.html

- Dois painéis mutuamente exclusivos: login e setup
- Setup exibido apenas quando não há admin no sistema
- CSS limpo, sem referências a signup público

### login.js

- Ao carregar, verifica `auth_token` no localStorage; se existe, redireciona para `index4.html`
- Chama `GET /api/auth/check-setup` para decidir qual painel exibir
- Login: envia JSON com `usuario`/`senha`, recebe token + user_data
- Setup: envia JSON com `nome`/`usuario`/`senha`/`email`, valida senhas coincidirem
- Em caso de sucesso, persiste `auth_token` e `user_data` no localStorage e redireciona para `index4.html`

---

## 4. Validação de Token no App

**Arquivo:** `js/app.js`

### Fluxo de inicialização

```
1. Ler user_data do localStorage
2. Verificar se auth_token e user_data existem (redirect se não)
3. Chamar GET /api/auth/me com token
4. Se resposta inválida → limpar token + redirect para login.html
5. Se resposta OK → atualizar userData, header.setUser()
6. Prosseguir com carregamento do menu e inicialização da UI
```

### userData global

```js
userData = {
  id: "bbfef80a",
  usuario: "admin",
  nome: "Administrador",
  email: "admin@example.com",
  role: "admin",
  ativo: true
}
```

Disponível globalmente em `userData` para componentes e páginas.

---

## 5. Gerenciamento de Usuários

**Arquivo:** `pages/usuarios.html`

Página standalone de administração de usuários, acessível via menu Configurações > Usuários.

### Funcionalidades

| Funcionalidade | Descrição |
|---------------|-----------|
| **Listagem** | Tabela com todos os usuários, colunas: #, Nome, Usuário, Perfil, Status, Ações |
| **Busca** | Filtro por nome ou usuário em tempo real |
| **Criar** | Modal com formulário: nome, usuário, email, perfil, senha |
| **Editar** | Modal preenchido com dados atuais, permite alterar nome, perfil, email, senha |
| **Ativar/Desativar** | Toggle por botão, usuário desativado não pode fazer login |
| **Badges** | Perfil colorido (admin=primary, supervisor=info, operador=default); Status (Ativo=success, Inativo=danger) |

### API consumida

- `GET /api/admin/users` — listar
- `POST /api/admin/users` — criar
- `POST /api/admin/users/:id` — update (com `action: "update"`) ou toggle (com `action: "toggle"`)

---

## 6. Mult-Empresa

O modelo de permissão é baseado em **empresa + role por empresa**:

- **Admin global** — `role: "admin"` tem acesso a todas as empresas com role admin
- **Usuário com vinculo** — `role: "supervisor"` ou `"operador"` só acessa empresas listadas em `empresas`
- **Role por empresa** — cada empresa no vínculo pode ter uma role diferente

### Modelo de dados

```json
// data/users.json
{
  "71cfdb54": {
    "usuario": "joao",
    "nome": "João",
    "role": "supervisor",
    "empresas": {
      "matriz": "supervisor",
      "filial_sp": "operador"
    }
  }
}

// data/empresas.json
{
  "matriz": {
    "nome": "Matriz",
    "cnpj": "00.000.000/0001-00",
    "ie": "123.456.789.000",
    "cidade": "São Paulo",
    "uf": "SP",
    "ativo": true
  }
}
```

### API de empresas

| Rota | Descrição |
|------|-----------|
| `GET /api/auth/minhas-empresas` | Empresas que o usuário logado pode acessar |
| `GET /api/admin/empresas` | Todas as empresas (admin) |
| `POST /api/admin/empresas` | Criar empresa |
| `POST /api/admin/empresas/:id` | Atualizar / ativar/desativar empresa |

### Seed data

Ao iniciar o servidor, se não houver empresas cadastradas, cria automaticamente:
- **Matriz** (SP)
- **Filial São Paulo** (SP)
- **Filial Rio de Janeiro** (RJ)

---

## 7. Seletor de Empresa no Topbar

**Arquivo:** `js/app.js`

- Após validar o token, carrega `/api/auth/minhas-empresas`
- Exibe dropdown `<select>` no topbar com as empresas disponíveis
- Empresa selecionada persiste em `localStorage("current_empresa_id")`
- Ao trocar de empresa, o menu é re-filtrado e a launchpad é re-renderizada
- Status bar exibe o nome da empresa ativa

### Fluxo

```
Login OK → GET /api/auth/me → GET /api/auth/minhas-empresas
  ↓
Renderiza seletor no topbar com empresas do usuário
  ↓
Usuário troca → currentEmpresaId atualizado → filterMenu() → renderLaunchpad()
```

---

## 8. Filtro de Menu por Permissão

**Arquivo:** `js/app.js`

### Regras

```js
ROLE_MODULES = {
  admin:       "*" (todos os módulos),
  supervisor:  ["dashboard","nfe","nfce","clientes","produtos","relatorios","folha","contabilidade"],
  operador:    ["dashboard","nfe","nfce"]
}
```

- `hasPermission(id)` — verifica se o módulo `id` está na lista da role atual
- `getCurrentCompanyRole()` — retorna a role do usuário na empresa selecionada
- Usuário admin (global) sempre retorna admin independente da empresa
- Módulos `configuracoes` / `admin` são sempre restritos a admin global
- Menu é filtrado em `filterMenu(menuData)` e re-aplicado ao trocar de empresa

---

## 9. Arquivos Entregues

| Arquivo | Alteração |
|---------|-----------|
| `server.py` | Adicionados endpoints de auth real, CRUD de usuários + empresas, seed de dados |
| `login.html` | Simplificado: login + setup (sem signup público) |
| `js/login.js` | Reescreito: integração com nova API, JSON, setup flow |
| `js/app.js` | Validação de token, carregamento de empresas, seletor no topbar, filtro de menu por role+empresa |
| `pages/usuarios.html` | **Novo** — página de gerenciamento de usuários com vínculo de empresas |
| `pages/empresas.html` | **Novo** — página de CRUD de empresas/filiais |
| `pages/configuracoes.html` | Adicionado link para Usuários |
| `index4.html` | Adicionado container do seletor de empresas no topbar |
| `assets/data/menu.json` | Adicionado link para Empresas no módulo Configurações |
| `data/users.json` | Armazenamento persistente de usuários (criado no primeiro setup) |
| `data/empresas.json` | Armazenamento persistente de empresas (criado no primeiro setup + seed) |

---

## 10. Estrutura de Dados

### users.json

```json
{
  "71cfdb54": {
    "usuario": "admin",
    "nome": "Administrador",
    "senha": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
    "email": "admin@example.com",
    "role": "admin",
    "empresas": {},
    "ativo": true,
    "token": "f8d0a006470d9530d1b49cfa06d98a5b"
  }
}
```

### empresas.json

```json
{
  "matriz": {
    "nome": "Matriz",
    "cnpj": "00.000.000/0001-00",
    "ie": "123.456.789.000",
    "cidade": "São Paulo",
    "uf": "SP",
    "ativo": true
  }
}
```

### Roles

| Role | Label | Acesso (módulos) |
|------|-------|-------------------|
| `admin` | Administrador | `*` (tudo) |
| `supervisor` | Supervisor | dashboard, nfe, nfce, clientes, produtos, relatorios, folha, contabilidade |
| `operador` | Operador | dashboard, nfe, nfce |
