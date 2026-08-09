# Layout Padrão — FiscalUI

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

## 1. App Shell

```
┌──────────────────────────────────────────────────────────────┐
│  .fl-topbar (56px)                                           │
│  ┌──────────┬─────────────────────────────────────────────┐  │
│  │  Fiscal  │  [Início] [Vendas] [Compras] [Estoque]     │  │
│  │  ERP     │                          🔔 ⚙️ 👤           │  │
│  └──────────┴─────────────────────────────────────────────┘  │
├────────┬─────────────────────────────────────────────────────┤
│.fl-sidebar│  .fl-workspace                                   │
│  240px  │                                                     │
│         │  .fl-workspace-header                               │
│ 👤      │  ┌─────────────────────────────────────────────┐   │
│ Pessoas │  │  Título                            [+ Novo]  │   │
│ 🏢      │  │  Subtítulo                                  │   │
│ Produtos│  └─────────────────────────────────────────────┘   │
│         │                                                     │
│ 📋      │  .fl-filters                                        │
│ Pedidos │  ┌─────────────────────────────────────────────┐   │
│         │  │ [Status ▼]   [Papel ▼]   [Filtrar]  [Limpar]│   │
│         │  └─────────────────────────────────────────────┘   │
│         │                                                     │
│         │  .fl-tabs                                           │
│         │  ┌─────────────────────────────────────────────┐   │
│         │  │ [Todos] [Ativos] [Inativos]                  │   │
│         │  └─────────────────────────────────────────────┘   │
│         │                                                     │
│         │  .fl-table                                          │
│         │  ┌─────────────────────────────────────────────┐   │
│         │  │ NOME    CPF           STATUS         AÇÕES  │   │
│         │  ├─────────────────────────────────────────────┤   │
│         │  │ João    000.000  [Ativo]       ✎  🗑        │   │
│         │  └─────────────────────────────────────────────┘   │
├────────┴─────────────────────────────────────────────────────┤
│  .fl-footer/statusbar                                         │
│  ● João  Ambiente: Dev                         14:30          │
└──────────────────────────────────────────────────────────────┘
```

### HTML Base

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FiscalERP — Módulo</title>
  <link rel="stylesheet" href="../fiscalui/dist/css/fiscalui.css">
</head>
<body>

  <!-- Topbar -->
  <header class="fl-topbar">
    <div class="fl-topbar-brand">Fiscal<span>ERP</span></div>
    <nav class="fl-topbar-nav">
      <a href="#" class="active">Início</a>
      <a href="#">Vendas</a>
      <a href="#">Compras</a>
      <a href="#">Estoque</a>
      <a href="#">Fiscal</a>
    </nav>
    <div style="margin-left:auto;display:flex;gap:var(--fl-space-sm);align-items:center;">
      <button class="fl-btn fl-btn-ghost fl-btn-icon">🔔</button>
      <button class="fl-btn fl-btn-ghost fl-btn-icon">⚙️</button>
      <div class="fl-badge fl-badge-info" style="border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;cursor:pointer;">JD</div>
    </div>
  </header>

  <!-- App Body -->
  <div class="fl-app">

    <!-- Sidebar -->
    <aside class="fl-sidebar">
      <div class="fl-sidebar-group">Cadastros</div>
      <a href="#" class="active">👤 Pessoas</a>
      <a href="#">🏢 Empresas</a>
      <a href="#">📦 Produtos</a>

      <div class="fl-sidebar-group">Operações</div>
      <a href="#">📋 Pedidos</a>
      <a href="#">💰 Financeiro</a>
      <a href="#">🚚 Logística</a>
    </aside>

    <!-- Workspace -->
    <main class="fl-workspace">
      <!-- Page content -->
    </main>

  </div>

  <script type="module">
    import FiscalUI from '../fiscalui/fiscalui.js';
    FiscalUI.init({ debug: true });
  </script>
</body>
</html>
```

## 2. Page Templates

### 2.1 Lista (DataGrid)

```html
<main class="fl-workspace">
  <div class="fl-workspace-header">
    <div>
      <h1>Pessoas</h1>
      <p>Gerencie todas as pessoas cadastradas no sistema</p>
    </div>
    <div class="fl-btn-group">
      <button class="fl-btn">Exportar</button>
      <button class="fl-btn fl-btn-primary" onclick="abrirModal('pessoaModal')">+ Nova Pessoa</button>
    </div>
  </div>

  <!-- Filtros -->
  <div class="fl-filters">
    <select class="fl-select">
      <option>Todos os status</option>
      <option>Ativo</option>
      <option>Inativo</option>
    </select>
    <select class="fl-select">
      <option>Todos os papéis</option>
      <option>Cliente</option>
      <option>Fornecedor</option>
    </select>
    <input class="fl-input" placeholder="Buscar por nome, CPF..." style="max-width:280px;">
    <button class="fl-btn fl-btn-primary">Filtrar</button>
  </div>

  <!-- Tabs -->
  <div class="fl-tabs">
    <button class="fl-tab active" onclick="switchTab(event,'t1')">Todas</button>
    <button class="fl-tab" onclick="switchTab(event,'t2')">Ativas</button>
    <button class="fl-tab" onclick="switchTab(event,'t3')">Inativas</button>
  </div>

  <!-- Tab Content -->
  <div class="fl-tab-content active" id="t1">
    <table class="fl-table">
      <thead>
        <tr>
          <th>Nome</th>
          <th>CPF/CNPJ</th>
          <th>Email</th>
          <th>Papéis</th>
          <th>Status</th>
          <th style="width:80px;">Ações</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><span class="fl-font-medium">João da Silva</span></td>
          <td class="fl-text-muted">000.000.000-00</td>
          <td class="fl-text-muted">joao@email.com</td>
          <td>
            <span class="fl-badge fl-badge-info">Cliente</span>
            <span class="fl-badge fl-badge-success">Fornecedor</span>
          </td>
          <td><span class="fl-badge fl-badge-success">Ativo</span></td>
          <td>
            <button class="fl-btn fl-btn-ghost fl-btn-sm">✎</button>
            <button class="fl-btn fl-btn-ghost fl-btn-sm">🗑</button>
          </td>
        </tr>
        <tr>
          <td><span class="fl-font-medium">Maria Oliveira</span></td>
          <td class="fl-text-muted">111.111.111-11</td>
          <td class="fl-text-muted">maria@email.com</td>
          <td><span class="fl-badge fl-badge-warning">Funcionário</span></td>
          <td><span class="fl-badge fl-badge-warning">Inativo</span></td>
          <td>
            <button class="fl-btn fl-btn-ghost fl-btn-sm">✎</button>
            <button class="fl-btn fl-btn-ghost fl-btn-sm">🗑</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <div class="fl-tab-content" id="t2">
    <div class="fl-empty">
      <div class="fl-empty-icon">📭</div>
      <h3>Nenhum registro ativo</h3>
      <p>Não há pessoas com status "Ativo" no momento.</p>
      <button class="fl-btn fl-btn-primary">+ Nova Pessoa</button>
    </div>
  </div>
  <div class="fl-tab-content" id="t3">
    <div class="fl-empty">
      <div class="fl-empty-icon">📭</div>
      <h3>Nenhum registro inativo</h3>
    </div>
  </div>
</main>
```

### 2.2 Formulário de Cadastro

```html
<main class="fl-workspace">
  <div class="fl-workspace-header">
    <div>
      <h1>Nova Pessoa</h1>
      <p>Preencha os campos para cadastrar uma nova pessoa</p>
    </div>
    <div class="fl-btn-group">
      <button class="fl-btn" onclick="history.back()">Cancelar</button>
      <button class="fl-btn fl-btn-primary" onclick="salvar()">Salvar</button>
    </div>
  </div>

  <div class="fl-card" style="max-width:800px;">
    <div class="fl-card-body">
      <!-- Campo único -->
      <div class="fl-field">
        <label>Nome completo <span style="color:var(--fl-danger)">*</span></label>
        <input class="fl-input" id="nome" required>
      </div>

      <!-- Linha com 2 colunas -->
      <div class="fl-form-row">
        <div class="fl-field">
          <label>CPF</label>
          <input class="fl-input" id="cpf" placeholder="000.000.000-00">
        </div>
        <div class="fl-field">
          <label>Data de Nascimento</label>
          <input class="fl-input" id="nascimento" type="date">
        </div>
      </div>

      <div class="fl-form-row">
        <div class="fl-field">
          <label>Email</label>
          <input class="fl-input" id="email" type="email">
          <span class="fl-hint">Informe um email válido</span>
        </div>
        <div class="fl-field">
          <label>Telefone</label>
          <input class="fl-input" id="telefone" placeholder="(00) 00000-0000">
        </div>
      </div>

      <!-- Fieldset (seção com borda) -->
      <fieldset class="fl-fieldset" style="margin-top:var(--fl-space-xl);">
        <legend>Endereço</legend>

        <div class="fl-form-row">
          <div class="fl-field">
            <label>CEP</label>
            <input class="fl-input" id="cep" placeholder="00000-000">
          </div>
          <div class="fl-field">
            <label>Cidade</label>
            <input class="fl-input" id="cidade">
          </div>
        </div>

        <div class="fl-form-row full">
          <div class="fl-field">
            <label>Logradouro</label>
            <input class="fl-input" id="logradouro">
          </div>
        </div>
      </fieldset>

      <!-- Footer -->
      <div class="fl-card-footer" style="padding-left:0;padding-right:0;">
        <button class="fl-btn" onclick="history.back()">Cancelar</button>
        <button class="fl-btn fl-btn-primary" onclick="salvar()">Salvar</button>
      </div>
    </div>
  </div>
</main>
```

### 2.3 Detalhe / Visualização

```html
<main class="fl-workspace">
  <div class="fl-workspace-header">
    <div>
      <h1>João da Silva</h1>
      <p>Cliente desde 15/01/2024</p>
    </div>
    <div class="fl-btn-group">
      <button class="fl-btn" onclick="history.back()">Voltar</button>
      <button class="fl-btn fl-btn-primary">Editar</button>
    </div>
  </div>

  <!-- Tabs -->
  <div class="fl-tabs">
    <button class="fl-tab active" onclick="switchTab(event,'d1')">Detalhes</button>
    <button class="fl-tab" onclick="switchTab(event,'d2')">Endereços</button>
    <button class="fl-tab" onclick="switchTab(event,'d3')">Contatos</button>
    <button class="fl-tab" onclick="switchTab(event,'d4')">Histórico</button>
  </div>

  <div class="fl-tab-content active" id="d1">
    <div class="fl-card">
      <div class="fl-card-header">
        <h3>Informações da Pessoa</h3>
        <span class="fl-badge fl-badge-success">Ativo</span>
      </div>
      <div class="fl-card-body">
        <div class="fl-detail-grid">
          <div class="fl-detail-field">
            <label>Nome</label>
            <div class="value">João da Silva</div>
          </div>
          <div class="fl-detail-field">
            <label>CPF</label>
            <div class="value">000.000.000-00</div>
          </div>
          <div class="fl-detail-field">
            <label>Email</label>
            <div class="value">joao@email.com</div>
          </div>
          <div class="fl-detail-field">
            <label>Telefone</label>
            <div class="value">(11) 99999-0001</div>
          </div>
          <div class="fl-detail-field">
            <label>Data Nascimento</label>
            <div class="value">15/03/1985</div>
          </div>
          <div class="fl-detail-field">
            <label>Papéis</label>
            <div class="value">
              <span class="fl-badge fl-badge-info">Cliente</span>
              <span class="fl-badge fl-badge-success">Fornecedor</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="fl-tab-content" id="d2">
    <div class="fl-card">
      <div class="fl-card-header">
        <h3>Endereços</h3>
        <button class="fl-btn fl-btn-sm fl-btn-primary">+ Novo</button>
      </div>
      <div class="fl-sub-list">
        <div class="fl-sub-item">
          <div>
            <div class="fl-font-medium">Rua das Flores, 123 — Centro</div>
            <div class="fl-text-muted" style="font-size:var(--fl-font-size-xs);">São Paulo, SP — 01001-000</div>
          </div>
          <span class="fl-badge fl-badge-info">Principal</span>
        </div>
      </div>
    </div>
  </div>
</main>
```

### 2.4 Dashboard

```html
<main class="fl-workspace">
  <div class="fl-workspace-header">
    <div>
      <h1>Dashboard</h1>
      <p>Indicadores do período</p>
    </div>
  </div>

  <!-- KPI Cards -->
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:var(--fl-space-xl);margin-bottom:var(--fl-space-xl);">
    <div class="fl-card">
      <div class="fl-card-body">
        <div class="fl-text-muted" style="font-size:var(--fl-font-size-sm);">Receita Mensal</div>
        <div style="font-size:var(--fl-font-size-2xl);font-weight:var(--fl-font-weight-bold);margin:var(--fl-space-sm) 0;">R$ 847.250</div>
        <div style="font-size:var(--fl-font-size-sm);color:var(--fl-success);">▲ 12,5% vs mês anterior</div>
      </div>
    </div>
    <div class="fl-card">
      <div class="fl-card-body">
        <div class="fl-text-muted" style="font-size:var(--fl-font-size-sm);">Pedidos Abertos</div>
        <div style="font-size:var(--fl-font-size-2xl);font-weight:var(--fl-font-weight-bold);margin:var(--fl-space-sm) 0;">342</div>
        <div style="font-size:var(--fl-font-size-sm);color:var(--fl-text-secondary);">7 aguardando aprovação</div>
      </div>
    </div>
  </div>

  <!-- Two-column layout -->
  <div style="display:grid;grid-template-columns:2fr 1fr;gap:var(--fl-space-xl);">
    <!-- Tabela -->
    <div class="fl-card">
      <div class="fl-card-header"><h3>Últimos Pedidos</h3></div>
      <table class="fl-table" style="border:none;box-shadow:none;border-radius:0;">
        <thead>
          <tr>
            <th>#</th>
            <th>Cliente</th>
            <th>Valor</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>4521</td><td>João Silva</td><td>R$ 1.250</td><td><span class="fl-badge fl-badge-success">Aprovado</span></td></tr>
          <tr><td>4520</td><td>Maria Oliveira</td><td>R$ 3.400</td><td><span class="fl-badge fl-badge-warning">Pendente</span></td></tr>
        </tbody>
      </table>
    </div>

    <!-- Timeline -->
    <div class="fl-card">
      <div class="fl-card-header"><h3>Atividades</h3></div>
      <div class="fl-card-body">
        <div class="fl-sub-list" style="border:none;">
          <div class="fl-sub-item">
            <span>Pedido #4521 aprovado</span>
            <span class="fl-text-muted">5 min</span>
          </div>
          <div class="fl-sub-item">
            <span>Cliente cadastrado</span>
            <span class="fl-text-muted">18 min</span>
          </div>
          <div class="fl-sub-item">
            <span>NF-e 000.487 emitida</span>
            <span class="fl-text-muted">42 min</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</main>
```

### 2.5 Modal (Dialog)

```html
<div class="fl-modal-backdrop" id="pessoaModal">
  <div class="fl-modal">
    <div class="fl-modal-header">
      <h2>Nova Pessoa</h2>
      <button class="fl-btn fl-btn-ghost fl-btn-icon" onclick="fecharModal('pessoaModal')">✕</button>
    </div>
    <div class="fl-modal-body">
      <div class="fl-form-row">
        <div class="fl-field">
          <label>Nome <span style="color:var(--fl-danger)">*</span></label>
          <input class="fl-input" required>
        </div>
        <div class="fl-field">
          <label>CPF</label>
          <input class="fl-input" placeholder="000.000.000-00">
        </div>
      </div>
      <div class="fl-form-row full">
        <div class="fl-field">
          <label>Email</label>
          <input class="fl-input" type="email">
        </div>
      </div>
    </div>
    <div class="fl-modal-footer">
      <button class="fl-btn" onclick="fecharModal('pessoaModal')">Cancelar</button>
      <button class="fl-btn fl-btn-primary">Salvar</button>
    </div>
  </div>
</div>
```

## 3. Component Reference

### Botões

| Classe | Quando usar |
|--------|-------------|
| `fl-btn` | Ação secundária (padrão outline) |
| `fl-btn fl-btn-primary` | Ação principal da tela |
| `fl-btn fl-btn-success` | Confirmar / Ativar |
| `fl-btn fl-btn-warning` | Atenção / Suspender |
| `fl-btn fl-btn-danger` | Excluir / Desativar |
| `fl-btn fl-btn-ghost` | Ação terciária, toolbar |
| `fl-btn-sm` | Tamanho pequeno (28px) |
| `fl-btn-icon` | Botão apenas com ícone |
| `fl-btn-group` | Grupo de botões alinhados |

### Tabela

```html
<table class="fl-table">
  <thead><tr><th>Coluna</th></tr></thead>
  <tbody><tr><td>Valor</td></tr></tbody>
</table>
```

### Badges (Status)

| Classe | Significado |
|--------|-------------|
| `fl-badge fl-badge-success` | Ativo, Aprovado, Concluído |
| `fl-badge fl-badge-warning` | Pendente, Suspenso, Revisão |
| `fl-badge fl-badge-danger` | Bloqueado, Rejeitado, Erro |
| `fl-badge fl-badge-info` | Informação, Tag |
| `fl-badge fl-badge-neutral` | Rascunho, Neutro |

### Formulário

| Elemento | Descrição |
|----------|-----------|
| `fl-field` | Wrapper label + input + hints |
| `fl-input` | Input de texto, email, date |
| `fl-select` | Select estilizado |
| `fl-form-row` | Grid 2 colunas |
| `fl-form-row.full` | Grid 1 coluna |
| `fl-hint` | Texto de ajuda |
| `fl-error` | Mensagem de erro |
| `fl-fieldset` | Agrupamento com legenda |

### Utilitários

| Classe | Propriedade |
|--------|-------------|
| `fl-flex` | `display:flex` |
| `fl-flex-col` | `flex-direction:column` |
| `fl-items-center` | `align-items:center` |
| `fl-justify-between` | `justify-content:space-between` |
| `fl-gap-sm/md/lg` | gap |
| `fl-mt-sm/md/lg` | margin-top |
| `fl-mb-sm/md/lg` | margin-bottom |
| `fl-truncate` | ellipsis |
| `fl-text-sm` | font-size:13px |
| `fl-text-muted` | cor secundária |
| `fl-font-medium` | font-weight:500 |

## 4. Responsivo

| Breakpoint | Sidebar | Grid | Tabela |
|------------|---------|------|--------|
| < 576px | Drawer | 1 col | Cards |
| 576-767 | Ícones | 1 col | Cards |
| 768-1023 | Ícones | 2 col | Compacta |
| 1024+ | Aberta | Normal | Normal |

## 5. Checklist para Novas Telas

- [ ] `<link rel="stylesheet" href="../fiscalui/dist/css/fiscalui.css">`
- [ ] Estrutura: `fl-topbar > fl-app > fl-sidebar + fl-workspace`
- [ ] Workspace header com título + subtítulo + ações
- [ ] Filtros no `fl-filters` (quando aplicável)
- [ ] Tabs no `fl-tabs` (quando aplicável)
- [ ] Tabela no `fl-table` com `<thead>` e `<tbody>`
- [ ] Formulário: `fl-field > fl-input` dentro de `fl-form-row`
- [ ] Modal: `fl-modal-backdrop > fl-modal > header/body/footer`
- [ ] Badges de status: `fl-badge-{success/warning/danger/info/neutral}`
- [ ] Botão primário: `fl-btn-primary`
- [ ] Import `FiscalUI.init()` no `<script type="module">`
