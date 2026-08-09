# FiscalUI Framework

## Documento 028 — Divider

**Nível 2 — Basic Components**

**Versão 1.0**

Linha de separação horizontal ou vertical. Usada para dividir seções de conteúdo.

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

```js
class UIDivider extends UIComponent {
    constructor(options = {}) {
        super(options);
        this.orientation = options.orientation || 'horizontal';  // horizontal, vertical
        this.label = options.label || '';                        // label opcional no centro
        this.spacing = options.spacing || 'md';                  // none, sm, md, lg
    }

    template() {
        if (this.label) {
            return `<div class="ui-divider ui-divider--label ui-divider--${this.spacing}">
                        <span class="ui-divider__label">${this.label}</span>
                    </div>`;
        }
        return `<hr class="ui-divider ui-divider--${this.orientation} ui-divider--${this.spacing}">`;
    }
}
```

```css
.ui-divider {
    border: none;
    background: var(--color-border);
    margin: 0;
}

.ui-divider--horizontal { height: 1px; width: 100%; }
.ui-divider--vertical   { width: 1px; height: 100%; align-self: stretch; }

.ui-divider--none { margin: 0; }
.ui-divider--sm   { margin: var(--spacing-sm) 0; }
.ui-divider--md   { margin: var(--spacing-md) 0; }
.ui-divider--lg   { margin: var(--spacing-lg) 0; }

.ui-divider--label {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    border: none;
}
.ui-divider--label::before,
.ui-divider--label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--color-border);
}
.ui-divider__label {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    white-space: nowrap;
}
```

---

# Histórico de Revisões

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0 | 2026-07-24 | FiscalUI Team | Versão inicial |
