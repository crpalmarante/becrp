# RFC-1001 — BECRP Installation Packages (Pacotes Básicos)

| Campo | Valor |
|--------|--------|
| RFC | RFC-1001 |
| Título | Pacotes Básicos de Instalação |
| Status | Draft |
| Versão | 1.2 |
| Domínio | Platform / Product Architecture |
| Depende de | RFC-1000 BECRP Apps Platform, RFC-ORGANIZATION-ESTABLISHMENT |
| Integra com | Instalador, Hub Configurações, App Registry |
| UI | BusinessUI — Wizard de 1ª instalação / Configurações → Módulos |
| Autor | Business Platform Team |
| Data | 2026-08-02 |

---

# 1. Abstract

Esta RFC define os **pacotes básicos** oferecidos na instalação (ou na ativação) de uma organização no BECRP.

Um **pacote** não é um app. É um **atalho**: um conjunto nomeado de apps que o admin ativa **depois** da base estar no ar.

```text
Pacote
   │
   ├── lista de app ids
   ├── label / descrição
   └── para quem (persona)
```

A fonte da verdade dos apps continua sendo a RFC-1000.  
Esta RFC decide **quais combinações** o produto oferece e **quando** o admin as escolhe.

> **Simple is always better than complex.**  
> Primeiro a base. Depois o admin escolhe os pacotes/apps.

---

# 1.1 Sequência de instalação (modelo Odoo — **travado**)

Igual à filosofia Odoo: **não** misturar “subir o sistema” com “escolher o suite comercial”.

```text
Fase 1 — Instalação da base
  · runtime / dependências (requirements.txt)
  · dados / store da organização
  · usuário Administrador
  · Configurações Gerais
  · App Registry (vazio ou só base)
        │
        ▼
Fase 2 — Admin logado
  · abre Apps / Pacotes
  · escolhe Loja | Atacado / B2B | Personalizado
  · (ou instala apps um a um)
        │
        ▼
Operação
  · menu só com o que foi instalado
```

| Fase | O que acontece | O que **não** acontece |
|------|----------------|------------------------|
| **1. Base** | DB/dados, admin, gerais, registry | Escolher Loja/Atacado; instalar WMS/Delivery |
| **2. Apps** | Admin escolhe pacote ou apps | Reinstalar a base |

**Default após Fase 1:** organização sobe **sem** pacote de comércio aplicado.  
O admin **entra** e só então aplica **Loja** (atalho recomendado) ou outro.

Isso evita o antipadrão “wizard de venda no meio do install técnico”.

---

# 2. Objetivos

* Listar os **poucos** pacotes oficiais do BECRP (v1).  
* Definir quais apps cada pacote instala.  
* Definir o default do wizard.  
* Deixar explícito o que **não** é pacote (WMS, Delivery, Folha, Contabilidade, etc.).  
* Separar POS e Vendas (D4b da RFC-1000).  
* Servir de contrato para UI do wizard e para seeds de organização nova.

---

# 3. Princípios

1. **Pacote = atalho, não entidade eterna** — depois da instalação, o que vale é `org.apps`.  
2. **O mínimo de pacotes que resolve** — v1 = **3** (Loja, Atacado/B2B, Personalizado).  
3. **Combinações extras não viram pacote** — Loja+B2B, Distribuição, Núcleo: Personalizado ou Instalar app depois.  
4. **Apps logísticos e de conformidade avançada não são pacote de entrada** — WMS, Delivery, Contabilidade, Folha, Compras, Loans.  
5. **POS ≠ Vendas** — dois pacotes de comércio distintos; não um “combo” na entrada.  
6. **Fiscal entra nos dois pacotes de comércio** — default BR (D3).

---

# 4. Relação com a base

Todo pacote **assume a base** já instalada (RFC-1000 §6):

* Organização / estabelecimentos  
* Usuários / auth  
* Parceiros e produtos (cadastro mínimo)  
* Configurações Gerais  
* App Registry  

O pacote só acrescenta **apps** em cima da base.

---

# 5. Catálogo de pacotes (v1) — **simples**

Status: alinhado à filosofia — **3 pacotes**. Combinações a mais = Personalizado ou Instalar app.

## 5.1 Resumo

| id | Label | Default wizard | Apps |
|----|-------|----------------|------|
| `retail` | Loja | **sim** | `pos`, `inventory`, `fiscal` |
| `wholesale` | Atacado / B2B | não | `sales`, `inventory`, `fiscal` |
| `custom` | Personalizado | não | escolha manual |

Só isso.

## 5.2 Por que não os outros

| Ideia descartada como pacote | Em vez disso |
|------------------------------|--------------|
| Núcleo | Personalizado (nada marcado) ou só base sem wizard de comércio |
| Loja + B2B | Instala Loja **ou** Atacado; depois Instalar o outro app |
| Distribuição (WMS + Delivery) | Instala Atacado (ou Loja); depois Instalar WMS e Entregas |
| Contabilidade / Folha / Compras | Sempre “Instalar app” |

Regra: **se dá para resolver com um clique em Apps depois, não merece pacote na entrada.**

## 5.3 Detalhamento

### Pacote `retail` — Loja *(default)*

| | |
|--|--|
| **Para quem** | Varejo / balcão / consumidor final |
| **Apps** | `pos` + `inventory` + `fiscal` |
| **Não inclui** | `sales`, WMS, Delivery, Compras, Contabilidade, Folha |
| **Persona** | “Quero vender no PDV e emitir fiscal” |

### Pacote `wholesale` — Atacado / B2B

| | |
|--|--|
| **Para quem** | Venda CNPJ→CNPJ, pedidos, licitação |
| **Apps** | `sales` + `inventory` + `fiscal` |
| **Não inclui** | `pos`, WMS, Delivery |
| **Persona** | “Vendo para empresa, não tenho PDV de rua” |

### Pacote `custom` — Personalizado

| | |
|--|--|
| **Para quem** | Qualquer outro footprint |
| **Apps** | Checkboxes do catálogo RFC-1000 |
| **Sugestão na tela** | Pré-marcar `inventory` + `fiscal` (editável) |
| **Notas** | Caminho para WMS, Delivery, Folha, Contabilidade, POS+Vendas juntos, etc. |

---

# 6. O que **não** é pacote básico (v1)

Tudo que não está na §5.1. Em especial:

| App / ideia | Motivo |
|-------------|--------|
| `wms`, `delivery` | Logística = instalar depois |
| `accounting`, `hr_payroll` | Conformidade avançada |
| `purchases`, `receiving`, `loans` | Sob demanda |
| Combo Loja+B2B / Distribuição | Dois cliques depois > novo pacote |

---

# 7. UX — duas fases (não um único wizard)

## 7.1 Fase 1 — Instalador técnico (base)

```text
┌─────────────────────────────────────────────────────────┐
│  BECRP — Instalação                                     │
│                                                         │
│  1. Verificar Python / requirements                     │
│  2. Criar dados da organização                          │
│  3. Criar Administrador                                 │
│       usuário: ________  senha: ________                │
│  4. Configurações Gerais (nome, país, moeda…)           │
│                                                         │
│  Apps de negócio: você escolhe depois do login.         │
│                                                         │
│                         [ Instalar base ]               │
└─────────────────────────────────────────────────────────┘
```

Ao terminar → login do admin.  
Menu ainda **sem** POS/Vendas/WMS… (só shell + Configurações + Apps).

## 7.2 Fase 2 — Admin escolhe pacotes/apps

```text
Configurações → Apps
(ou tela Apps após primeiro login)

┌─────────────────────────────────────────────────────────┐
│  Apps BECRP                                             │
│                                                         │
│  Comece por um pacote                                   │
│                                                         │
│  [ Aplicar: Loja ]     POS + estoque + fiscal           │
│  [ Aplicar: Atacado ]  Vendas + estoque + fiscal        │
│  [ Personalizado… ]    marcar apps                      │
│                                                         │
│  Ou instale apps avulsos                                │
│  ○ WMS   ○ Entregas   ○ Folha   ○ Contabilidade  …      │
└─────────────────────────────────────────────────────────┘
```

Três atalhos de pacote. Resto = instalar app. Fim.

### Comportamento

1. Fase 1 **nunca** aplica Loja/Atacado sozinha.  
2. Fase 2: admin aplica pacote → `org.apps` (RFC-1000).  
3. Menu e Config hub refletem só o instalado.  
4. Depois: Instalar o que faltar, app a app.  
5. Pacote é **preset**, não plano permanente.

### Exemplos

```text
Base instalada → admin aplica Loja
  ⇒ pos + inventory + fiscal

Depois precisa Entregas
  ⇒ Instalar app `delivery`

Quer Atacado + WMS
  ⇒ Aplicar Atacado, depois Instalar `wms`
```

---

# 8. Contrato técnico do pacote

```json
{
  "id": "retail",
  "name": "Loja",
  "summary": "PDV para consumidor final com estoque e fiscal",
  "default": true,
  "apps": ["pos", "inventory", "fiscal"],
  "persona": "Varejo / balcão",
  "excludes_note": "Não inclui Vendas B2B, WMS nem Delivery"
}
```

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `id` | sim | Estável |
| `name` | sim | Label |
| `apps` | sim | Lista de app ids (RFC-1000) |
| `default` | sim | No máximo um `true` no catálogo |
| `summary` | sim | Uma linha no wizard |
| `persona` | não | Ajuda de UX |

Arquivo sugerido (MVP): `dados/app_packages.json` ou constante em módulo `app_registry`.

---

# 9. Matriz pacote × app

| App \ Pacote | retail | wholesale | custom |
|--------------|--------|-----------|--------|
| `pos` | ✓ | | ? |
| `sales` | | ✓ | ? |
| `inventory` | ✓ | ✓ | ? |
| `fiscal` | ✓ | ✓ | ? |
| `wms` | | | ? |
| `delivery` | | | ? |
| `purchases` | | | ? |
| `receiving` | | | ? |
| `accounting` | | | ? |
| `hr_payroll` | | | ? |
| `loans` | | | ? |

`?` = checkbox em Personalizado ou Instalar app depois.

---

# 10. Decisões (filosofia aplicada)

| # | Decisão | Status |
|---|---------|--------|
| P0 | **Fase 1 = base** (dados + admin + gerais); **Fase 2 = admin escolhe pacotes/apps** (modelo Odoo) | **Aprovado** |
| P1 | Atalho recomendado na Fase 2 = **Loja** (`retail`) — não auto-aplicado na Fase 1 | **Aprovado** |
| P2 | Só **3 pacotes**: Loja, Atacado/B2B, Personalizado | **Aprovado** |
| P3 | Sem pacotes Núcleo, Loja+B2B, Distribuição no v1 | **Aprovado** |
| P4 | WMS / Delivery / Folha / Contabilidade / Compras = Instalar app | **Aprovado** |
| P5 | Pacote = preset, não plano permanente | **Aprovado** |
| P6 | POS e Vendas em pacotes separados | **Aprovado** |

---

# 11. Fora de escopo

* Preço / SKU comercial por pacote  
* Feature flags dentro de um app (ex.: “POS com balança”)  
* Pacotes por estabelecimento (só organização no MVP)  
* Migração automática Loja → Distribuição  

---

# 12. Critérios de pronto (documental)

* [x] Pacotes v1 reduzidos a 3 (filosofia)  
* [x] Matriz §9 alinhada  
* [x] RFC-1000 §7 aponta para esta RFC  
* [ ] Implementar wizard (código) — quando priorizado  

---

# 13. Próximos passos

1. Confirmar com product owner o texto da §5 (já alinhado à filosofia).  
2. Implementar: `app_packages` + wizard + seed da org (P1 da RFC-1000).  

---

# 14. Regra final

```text
Base     → sempre
Pacote   → só 3 atalhos na entrada (Loja | Atacado | Personalizado)
App      → tudo o mais se instala depois (RFC-1000)
```

> **Simple is always better than complex.**
