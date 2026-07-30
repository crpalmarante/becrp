# Sprint 05 — Temas & Refinamento

**FiscalUI Framework v0.5.0**

**Data:** Julho 2026

---

## Índice

- [1. ThemeManager](#1-thememanager)
- [2. Tema Light](#2-tema-light)
- [3. Tema High Contrast](#3-tema-high-contrast)
- [4. Seletor Visual de Temas](#4-seletor-visual-de-temas)
- [5. Transições de Workspace](#5-transições-de-workspace)
- [6. Showcase](#6-showcase)
- [7. Arquivos Entregues](#7-arquivos-entregues)
- [8. Como Usar](#8-como-usar)

---

## 1. ThemeManager

**Arquivo:** `js/services/ThemeManager.js`

Classe responsável por gerenciar a troca de temas em tempo real, sem recarregar a página.

### API

| Método | Descrição |
|--------|-----------|
| `init()` | Restaura tema salvo, observa mudanças de estado |
| `list()` | Retorna array de temas disponíveis `[{id, label, icon, color}]` |
| `current()` | Retorna o ID do tema ativo |
| `set(themeId)` | Aplica tema (`dark`, `light`, `high-contrast`) |
| `renderPicker(container)` | Renderiza dropdown de seleção visual |

### Integração

O ThemeManager é instanciado automaticamente no `fiscalui.js`:

```js
const themeManager = new ThemeManager(events, state, storage);
FiscalUI.themeManager = themeManager;
window.themeManager = themeManager;
```

No `init()`, ele:
1. Restaura o tema do `localStorage` via `StorageService`
2. Aplica o tema com `[data-theme]` no `<html>`
3. Observa `state:theme` para mudanças em tempo real
4. Sincroniza o ícone do botão (`#theme-icon`)

### Temas Disponíveis

| ID | Label | Ícone | CSS Selector |
|----|-------|-------|-------------|
| `dark` | Escuro | `icon-moon` | `[data-theme="dark"]` |
| `light` | Claro | `icon-sun` | `[data-theme="light"]` |
| `high-contrast` | Alto Contraste | `icon-eye` | `[data-theme="high-contrast"]` |

---

## 2. Tema Light

**Arquivo:** `css/themes.css` (linhas 12–197)

Tema claro com fundo gradiente suave (`#f0f4f8` → `#cbd5e1`), glassmorphism adaptado com opacidade reduzida e texto escuro.

### Tokens Alterados

| Token | Dark | Light |
|-------|------|-------|
| `--bg-gradient` | escuro (`#06101f`...) | claro (`#f0f4f8`...) |
| `--glass-bg` | `rgba(255,255,255,.12)` | `rgba(255,255,255,.7)` |
| `--text-primary` | `#FFFFFF` | `#1a202c` |
| `--text-secondary` | `#DDDDDD` | `#4a5568` |
| `--color-primary` | `#14b8a6` | `#0f766e` |
| `--glass-shadow` | `0 25px 60px rgba(0,0,0,.4)` | `0 8px 30px rgba(0,0,0,.08)` |

### Overrides de Componentes

```
[data-theme="light"] #sidebar      → fundo branco 80%
[data-theme="light"] .topbar       → fundo branco 70%
[data-theme="light"] .menu-item    → hover com fundo preto 5%
[data-theme="light"] .quick-card   → fundo branco 65%
```

---

## 3. Tema High Contrast

**Arquivo:** `css/themes.css` (linhas 208–280)

Tema pensado para acessibilidade: fundo preto sólido, bordas brancas evidentes, sem blur/transparência.

### Tokens Alterados

| Token | Valor |
|-------|-------|
| `--bg-gradient` | `#000` (sólido) |
| `--glass-bg` | `#111` |
| `--glass-blur` | `blur(0)` (sem desfoque) |
| `--glass-border` | `#fff` (borda branca) |
| `--glass-shadow` | `none` |
| `--color-primary` | `#00e5ff` (ciano brilhante) |
| `--border-color` | `#fff` |

### Overrides de Componentes

```
[data-theme="high-contrast"] .glass-panel → border: 2px solid #fff
[data-theme="high-contrast"] .topbar      → border: 2px solid #fff
[data-theme="high-contrast"] #sidebar     → border-right: 2px solid #fff
```

---

## 4. Seletor Visual de Temas

**Local:** topbar, dentro de `#theme-picker-container`

Substitui o antigo botão `toggleTheme()` que ciclava cegamente entre temas.

### Estrutura DOM

```html
<div id="theme-picker-container">
    <button id="theme-toggle-btn" title="Tema: clique para trocar">
        <svg class="icon"><use href="#icon-palette"/></svg>
    </button>
    <div class="theme-dropdown" id="theme-picker">
        <div class="theme-opt active" data-theme="dark">
            <span class="theme-swatch" style="background:#0f172a"></span>
            <span class="theme-label">Escuro</span>
            <svg class="icon icon-check"><use href="#icon-check"/></svg>
        </div>
        <!-- ... light, high-contrast -->
    </div>
</div>
```

### CSS

- `.theme-dropdown` — posicionado absolutamente abaixo do botão, com glassmorphism
- `.theme-opt` — cada opção com swatch circular + label + checkmark
- `.theme-opt.active` — destaca com tom primary e exibe checkmark
- `#theme-picker-container` — `position: relative` para ancoragem

### Comportamento

- Clique no botão de paleta → abre/fecha dropdown
- Clique em uma opção → `themeManager.set(id)` → estado atualiza → todos os componentes reagem via `[data-theme]`
- Clique fora → fecha dropdown
- Tema ativo persiste no `localStorage`

---

## 5. Transições de Workspace

**Arquivo:** `js/app.js` — função `pageTransition()`

### pageTransition(showLaunchpad, callback)

```
pageTransition(true, () => {
    // código que modifica o DOM
});
```

### Fluxo

1. Opacity do container alvo → 0 (120ms fade out)
2. Executa callback (modifica DOM: troca conteúdo)
3. Adiciona classe `.page-enter` com animação `pageEnter`
4. Opacity → 1

### Keyframes CSS

```css
@keyframes pageEnter{
    from{opacity:0; transform:translateY(8px)}
    to{opacity:1; transform:translateY(0)}
}
@keyframes pageExit{
    from{opacity:1}
    to{opacity:0}
}
```

Aplicado em `renderLaunchpad()` e `renderWorkspace()`.

---

## 6. Showcase

**Rota:** `/showcase`

Página de demonstração que exibe todos os componentes implementados:

| Seção | Componentes |
|-------|-------------|
| Tabs | 3 abas (HTML, CSS, JS) com conteúdo textual |
| Accordion | 3 seções (FAQ sobre FiscalUI) |
| Badges & Tags | Variações default, primary, success, warning, danger, info + tags fixas/removíveis + status |
| Skeleton | kpi, card, widget — estáticos (demonstração visual) |
| Dialog | Botões Alert, Confirm, Prompt (usa `data-dialog` declarativo) |

### Como Adicionar ao Menu

Adicione no `menu.json`:

```json
{
    "id": "showcase",
    "label": "Showcase",
    "icon": "icon-grid",
    "href": "/showcase"
}
```

---

## 7. Arquivos Entregues

### Sprint 04 — Componentes

| Arquivo | Descrição |
|---------|-----------|
| `js/components/Tabs.js` | Abas navegáveis com header + painéis + eventos |
| `js/components/Dialog.js` | Overlay modal com alert/confirm/prompt |
| `js/components/Accordion.js` | Seções expansíveis com animação |
| `js/components/Skeleton.js` | Loading placeholders (card, table, kpi, widget) |
| `js/components/Badge.js` | Badges, tags, status indicators |
| `js/components/init.js` | Instância global `dialog` + binding `data-dialog` |
| `css/style.css` | Estilos para Tabs, Dialog, Accordion, Skeleton, Badge |

### Sprint 05 — Temas & Refinamento

| Arquivo | Descrição |
|---------|-----------|
| `js/services/ThemeManager.js` | Gerenciador de temas com renderização de seletor |
| `css/themes.css` | Definições Light e High Contrast via `[data-theme]` |
| `css/motion.css` | Keyframes, transições padrão, GLASS efeitos, reduced-motion |
| `js/app.js` | `pageTransition()` + rota `/showcase` |
| `css/style.css` | CSS do dropdown de temas + transições workspace |

### Modificados

| Arquivo | O que mudou |
|---------|-------------|
| `index4.html` | Adicionado `#theme-picker-container`, scripts dos componentes, ThemeManager |
| `js/core/fiscalui.js` | ThemeManager integrado, lógica de tema inline substituída |
| `js/app.js` | `toggleTheme()` removido, `pageTransition()` adicionado, rota `/showcase` |

---

## 8. Como Usar

### Trocar Tema

```js
// Via ThemeManager
FiscalUI.themeManager.set("light");
FiscalUI.themeManager.set("high-contrast");
FiscalUI.themeManager.set("dark");

// Via estado (dispara eventos)
FiscalUI.state.set("theme", "light");

// Obter tema atual
const current = FiscalUI.themeManager.current();
```

### Criar Novo Tema

1. Adicione o tema no array em `ThemeManager.js`:
```js
this._themes.push({id:"corporate", label:"Corporativo", icon:"icon-briefcase", color:"#1e3a5f"});
```

2. Crie o CSS em `themes.css`:
```css
[data-theme="corporate"]{
    --bg-gradient: linear-gradient(135deg, #1e3a5f, #2d5a87);
    --text-primary: #FFFFFF;
    --color-primary: #3b82f6;
    /* ... demais tokens ... */
}
```

3. O seletor dropdown aparecerá automaticamente.

### Mostrar Tabs

```js
const container = document.getElementById("meu-container");
const tabs = new Tabs(container);
tabs.define("tab1", "Primeira", "<p>Conteúdo 1</p>")
    .define("tab2", "Segunda", "<p>Conteúdo 2</p>")
    .render("tab1");
```

### Mostrar Dialog

```js
// Alert
await dialog.alert("Mensagem", "Título");

// Confirm
const ok = await dialog.confirm("Confirma?", "Pergunta");

// Prompt
const valor = await dialog.prompt("Digite algo:", "valor inicial", "Entrada");
```

### Mostrar Accordion

```js
const acc = new Accordion(document.getElementById("meu-accordion"));
acc.add("id1", "Título 1", "Conteúdo...")
   .add("id2", "Título 2", "Conteúdo...", true) // aberto
   .render();
```

### Mostrar Skeleton

```js
// Injetar skeleton
container.innerHTML = Skeleton.card(3);
container.innerHTML = Skeleton.table(5, 4);
container.innerHTML = Skeleton.kpi();
container.innerHTML = Skeleton.widget();

// Aplicar diretamente
Skeleton.apply(container, "card", {rows: 3});

// Remover quando carregar
Skeleton.remove(container);
```

### Mostrar Badges

```js
Badge.render("Ativo", "success");
Badge.render("Pendente", "warning");
Badge.render("Admin", "primary");

Badge.tag("removível", true);  // com botão de fechar
Badge.tag("fixa");              // sem botão

Badge.status("Online", "success");
```
