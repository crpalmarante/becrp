# RFC-1000 — BECRP Apps Platform (Base + Instalador)

| Campo | Valor |
|--------|--------|
| RFC | RFC-1000 |
| Título | BECRP Apps Platform — Base, Catálogo e Instalador de Módulos |
| Status | Draft |
| Versão | 1.0 |
| Domínio | Platform / Product Architecture |
| Depende de | RFC-ORGANIZATION-ESTABLISHMENT |
| Integra com | POS, Fiscal, Estoque, WMS, Delivery, Contabilidade, Folha, Compras, Receiving |
| UI | BusinessUI — Hub Configurações + App Store / Módulos |
| Autor | Business Platform Team |
| Data | 2026-08-02 |

---

# 1. Abstract

Esta RFC define a **filosofia e o contrato de produto** do BECRP como suite modular.

O cliente **não recebe o ERP inteiro**. Recebe uma **base** e **instala apps** conforme a necessidade da organização.

```text
Instalador
    │
    ▼
Base BECRP
    │
    ├── App: POS / Vendas
    ├── App: Estoque
    ├── App: Fiscal          ← default instalado
    ├── App: Compras         ← sob demanda
    ├── App: WMS             ← sob demanda
    ├── App: Delivery        ← sob demanda
    ├── App: Contabilidade   ← sob demanda
    ├── App: Folha           ← sob demanda
    └── …
```

Inspiração: a parte boa do Odoo — **núcleo magro + apps opcionais**.  
Não-objetivo desta RFC: clonar o mecanismo interno do Odoo (plugin loader, marketplace, ORM por módulo).

> **Simple is always better than complex.**  
> **Cada cliente monta o seu BECRP.**

---

# 2. Objetivos

Esta RFC responde:

* O que vem na instalação inicial?
* O que é “base” vs “app instalável”?
* Como uma organização liga / instala Folha, Delivery, WMS, etc.?
* Quais dependências existem entre apps?
* Como menu, Configurações e APIs respeitam apps instalados?
* O que é MVP técnico vs visão de longo prazo?
* Como as RFCs de domínio (Delivery 18xxx, WMS 9xxx, …) se encaixam no catálogo?

---

# 3. Problema que resolve

Hoje o BECRP cresce como suite com muitas superfícies (POS, estoque, WMS, delivery, fiscal, contabilidade…). Existe um embrião de `org.modulos` no hub Configurações, mas:

* o menu ainda é filtrado sobretudo por **papel/permissão**, não por **apps da empresa**;
* Delivery / WMS / Estoque nem sempre entram no catálogo de módulos;
* APIs não bloqueiam de forma uniforme um app “desligado”;
* o roadmap de RFCs parece “suite obrigatória”, embora a intenção de produto seja o oposto.

Sem esta plataforma de apps, cada novo domínio aumenta a sensação de monólito — mesmo quando o código já está relativamente separado.

---

# 4. Princípio central

```text
Base = o que toda organização precisa para existir no sistema

App  = capacidade de negócio que a organização escolhe instalar
```

Regras de ouro:

1. **App = valor sozinho** — POS funciona sem Delivery; Fiscal sem Contabilidade; Estoque sem WMS.
2. **Dependência só para frente e explícita** — nunca acoplamento escondido.
3. **Não instalado = invisível e inofensivo** — sem menu, sem obrigação de fluxo; API responde de forma clara.
4. **Admin decide por organização** — mesma base de código, footprints diferentes.
5. **Núcleo não engorda** — RFC de domínio nova = app ou extensão de app, não “mais uma aba obrigatória no Core”.

---

# 5. Escopo da decisão (por organização)

Apps são instalados no nível **Organização** (tenant), alinhado a `RFC-ORGANIZATION-ESTABLISHMENT`.

| Nível | Apps? | Notas |
|-------|-------|--------|
| Organização | **Sim** — fonte da verdade | “Esta empresa tem Folha?” |
| Estabelecimento | Em geral herda | Exceções futuras (ex.: só filial X usa WMS) ficam fora do MVP |
| Usuário / papel | Permissões **dentro** dos apps instalados | App off ⇒ usuário nenhum vê |
| Terminal PDV | Opera apps de venda/estoque/fiscal do estabelecimento | Não instala apps |

Fórmula do que o usuário vê:

```text
visível = apps_instalados(organização) ∩ permissões(papel) ∩ escopo(estabelecimento/terminal)
```

---

# 6. Base (sempre na instalação)

A base **não** é “quase o suite”. É o mínimo para o sistema existir.

## 6.1 Componentes da base

| Componente | Responsabilidade |
|------------|------------------|
| Organização / Estabelecimentos | Tenant, filiais, CNPJ operacional |
| Usuários / papéis / auth | Login, roles |
| Parceiros (cadastro básico) | Cliente / fornecedor mínimo |
| Produtos (cadastro básico) | SKU mestre simples |
| Hub Configurações (Gerais) | Preferências transversais |
| App Registry / Instalador | Catálogo + estado instalado |
| Shell de menu | Só mostra o que está instalado |

## 6.2 O que a base **não** inclui

* Fluxos de Compras avançadas  
* WMS  
* Delivery  
* Contabilidade  
* Folha / RH  
* Receiving Engine completo  
* Analytics avançado de domínio  
* Mobile de campo  

Esses são **apps**.

---

# 7. Pacote inicial (defaults na 1ª instalação)

**Fonte dos pacotes:** [`RFC-1001 - BECRP Installation Packages`](./RFC-1001%20-%20BECRP%20Installation%20Packages.md).

Filosofia (modelo Odoo):

1. **Instala a base** (dados, admin, configurações gerais)  
2. **Admin loga e escolhe** pacote/apps  

| Pacote (Fase 2) | Apps |
|-----------------|------|
| Loja *(atalho recomendado)* | `pos`, `inventory`, `fiscal` |
| Atacado / B2B | `sales`, `inventory`, `fiscal` |
| Personalizado | checkboxes |

Nenhum pacote de comércio é aplicado na Fase 1.  
Tudo o mais (WMS, Delivery, Contabilidade, Folha, …) = **Instalar app**.

### Decisão travada: POS ≠ Vendas

`pos` e `sales` são **apps distintos**. Nunca fundir num único `commerce`.

| | `pos` | `sales` |
|---|--------|---------|
| Público | Consumidor final (B2C) | Empresa / órgão (B2B, CNPJ→CNPJ, licitação) |
| Canal | PDV / caixa / terminal | Pedido, cotação, contrato, ordem de venda |
| Fiscal típico | NFC-e / cupom | NF-e / pedidos com CNPJ |
| Pode compartilhar | Produtos, armazéns/estoque, parceiros, fiscal engine | Idem |
| Não compartilha | Fluxo de caixa PDV, sangria, terminal 1:1 | Fluxo de pedido B2B, condições comerciais, licitação |

Podem coexistir na mesma organização.  
Um não implica o outro.  
Estoque e cadastros mestres são da **base / app inventory** — compartilhados; o **fluxo de venda** é de cada app.

---

# 8. Catálogo de apps (v1)

Cada app tem `id` estável. Nomes de exibição podem mudar; ids não.

## 8.1 Apps de operação

| id | Label | Depende de | Notas |
|----|-------|------------|--------|
| `pos` | POS | base, `inventory` (recomendado) | Venda ao **consumidor final** — PDV / caixa / terminal |
| `sales` | Vendas | base, `inventory` (recomendado) | Venda **B2B** — CNPJ→CNPJ, pedidos, licitação; **não** é POS |
| `inventory` | Estoque | base | Saldo, movimentos, promise básica — compartilhado por POS e Vendas |
| `purchases` | Compras | base, `inventory` | Pedidos a fornecedor |
| `receiving` | Recebimento | `inventory` | Engine de receiving / XML |
| `wms` | WMS | `inventory` | Armazém avançado — **não** baixa estoque de venda |
| `delivery` | Entregas | base | Pedido de entrega / POD — **nunca** move inventário |

## 8.2 Apps de conformidade

| id | Label | Depende de | Notas |
|----|-------|------------|--------|
| `fiscal` | Fiscal | base | NFC-e / NF-e / motor fiscal — **default ON** |
| `accounting` | Contabilidade | base | Plano, diários, períodos |
| `hr_payroll` | Folha | base | RH / folha — módulo clássico “instalar depois” |

## 8.3 Apps de extensão (fase posterior)

| id | Label | Depende de | Notas |
|----|-------|------------|--------|
| `delivery_ops` | Entregas — Operação | `delivery` | Fila, quadro, calendário, manifesto |
| `delivery_field` | Entregas — Campo | `delivery` | Trip, stops, workspace motorista |
| `delivery_mobile` | Entregas — Mobile | `delivery_field` | Offline, GPS, captura |
| `analytics_*` | Analytics por domínio | app pai | Só quando houver dor |

No MVP do instalador, **subapps** de Delivery podem ser flags internas do app `delivery`. Na visão completa, tornam-se apps filhos.

---

# 9. Contrato do app (manifest)

Todo app declara um manifesto estável (arquivo ou registro no registry).

```json
{
  "id": "hr_payroll",
  "name": "Folha de Pagamento",
  "version": "1.0.0",
  "summary": "Folha e rotinas de RH básicas",
  "depends": [],
  "recommends": [],
  "default_install": false,
  "category": "conformidade",
  "menus": ["folha", "funcionarios"],
  "config_panel": "folha",
  "api_prefixes": ["/api/folha", "/api/admin/folha"],
  "permissions": ["folha.read", "folha.write"],
  "seed": "hr_payroll.ensure_seed",
  "migrate": "hr_payroll.migrate",
  "uninstall_policy": "disable_only"
}
```

### Campos obrigatórios (MVP)

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| `id` | sim | Identificador estável |
| `name` | sim | Label |
| `depends` | sim | Lista de app ids (pode ser vazia) |
| `default_install` | sim | Se entra no pacote inicial |
| `menus` | sim | Entradas de `menu.json` controladas |
| `api_prefixes` | sim | Prefixo(s) guardados quando off |
| `uninstall_policy` | sim | Ver §12 |

### Campos da visão completa

* `seed` / `migrate` / `uninstall` hooks  
* `recommends` (não bloqueia)  
* `category`, ícone, documentação  
* `license` / `edition` (futuro comercial)

---

# 10. Ciclo de vida — Instalador

## 10.1 Estados

```text
available
    │ install
    ▼
installed
    │ uninstall (MVP = disable)
    ▼
disabled
    │ (fase 2) purge
    ▼
purged / available
```

No MVP:

* **install** = ativa app + roda seed mínimo + registra versão  
* **uninstall** = desativa (disable) — **não apaga dados**  
* **purge** = fase 2, com confirmação forte e backup

## 10.2 Ações

| Ação | Quem | Efeito |
|------|------|--------|
| Instalar | Admin da organização | `installed=true`, seed, menus/APIs liberados |
| Atualizar | Admin / processo de deploy | migrate do app |
| Desinstalar | Admin | `installed=false`, menus/APIs bloqueados; dados preservados |
| Purgar | Admin + confirmação | remove dados do app (fase 2) |

## 10.3 Dependências na instalação

```text
Instalar WMS
  → exige inventory instalado
  → se inventory off, instalador oferece instalar inventory primeiro
```

Regras:

* Não instalar app se `depends` não estiverem instalados.  
* Desinstalar app pai só se filhos forem desinstalados antes (ou em cascata explícita com aviso).  
* `recommends` gera sugestão, não bloqueio.

## 10.4 Experiência do admin (App Store interna)

Tela sugerida: **Configurações → Módulos / Apps**

```text
+--------------------------------------------------+
| Apps BECRP                                       |
|--------------------------------------------------|
| Instalados                                       |
|  ✓ POS                                           |
|  ✓ Estoque                                       |
|  ✓ Fiscal                                        |
|                                                  |
| Disponíveis                                      |
|  ○ Compras          [Instalar]                   |
|  ○ WMS              [Instalar]                   |
|  ○ Entregas         [Instalar]                   |
|  ○ Contabilidade    [Instalar]                   |
|  ○ Folha            [Instalar]                   |
+--------------------------------------------------+
```

Mesma filosofia Odoo para o **usuário admin**; implementação interna pode ser simples (§15).

---

# 11. Integração com menu e Configurações

## 11.1 Menu principal

`menu.json` (ou equivalente) passa a declarar `app` em cada módulo/card:

```json
{
  "id": "delivery",
  "label": "Entregas",
  "app": "delivery",
  "apps": [ … ]
}
```

Regra:

```text
se organização não tem app instalado → card/grupo some
```

Permissões de papel continuam valendo **depois** do filtro de app.

## 11.2 Hub Configurações

Alinhado a `RFC-ORGANIZATION-ESTABLISHMENT` §2.2:

* Sidebar = **Gerais** (sempre) + **painéis dos apps instalados**  
* App não instalado ⇒ painel não aparece  
* Instalar app ⇒ painel surge sem redeploy mental do admin

O embrião atual em `js/configuracoes.js` (`MODULES` + `org.modulos`) é o ponto de partida — deve migrar de `localStorage` para **estado persistido da organização**.

## 11.3 Persistência (fonte da verdade)

Estado canônico por organização, exemplo:

```json
{
  "organizacao_id": "org-1",
  "apps": {
    "pos":        { "installed": true,  "version": "1.0.0", "installed_at": "…" },
    "inventory":  { "installed": true,  "version": "1.0.0", "installed_at": "…" },
    "fiscal":     { "installed": true,  "version": "1.0.0", "installed_at": "…" },
    "delivery":   { "installed": false },
    "wms":        { "installed": false },
    "accounting": { "installed": false },
    "hr_payroll": { "installed": false }
  }
}
```

Local sugerido no MVP JSON: `dados/org_apps.json` (ou campo em store de organização já existente).  
Não usar apenas `localStorage` do browser como fonte da verdade.

---

# 12. APIs e segurança

## 12.1 Guard de app

Todo request a prefixo de app não instalado:

```text
HTTP 403
{
  "status": "error",
  "code": "APP_NOT_INSTALLED",
  "app": "delivery",
  "message": "Módulo Entregas não está instalado nesta organização"
}
```

Admin autenticado ainda pode chamar endpoints do **instalador** (`/api/admin/apps/...`).

## 12.2 Papéis vs apps

| Camada | Pergunta |
|--------|----------|
| App instalado? | A organização contratou / ligou essa capacidade? |
| Papel permite? | Este usuário pode operar essa capacidade? |

As duas são necessárias. App off ganha de qualquer role.

## 12.3 Integrações cruzadas

Quando um app chama outro:

* Se o alvo não está instalado, a integração **degrada com graça** (no-op ou mensagem), nunca corrompe dados.  
* Exemplo: WMS expedição → Delivery só cria DO se `delivery` instalado; senão, expedição segue sem DO.

Regras de domínio já decididas permanecem:

* POS / Sales baixa estoque de venda  
* WMS **não** baixa estoque de venda  
* Delivery **nunca** move inventário  

Essas regras são **contratos entre apps**, não desculpa para fundir apps.

---

# 13. Dados por app

| Política | MVP | Fase 2 |
|----------|-----|--------|
| Prefixo de arquivos / tabelas por app | Preferir (`delivery_*.json`, etc.) | Manter |
| Desinstalar | Disable; dados ficam | Idem |
| Purgar | Não | Job com backup + confirmação |
| Reinstalar | Reativa; seed só se vazio | Migrate idempotente |

Apps não devem escrever no “miolo” da base sem contrato. Cadastros mestres (parceiro, produto) são da base; documentos de domínio são do app.

---

# 14. Relação com RFCs de domínio existentes

As RFCs de Delivery, WMS, Contabilidade, etc. **continuam válidas** como especificação de capacidade.

Mudança de leitura:

| Antes (implícito) | Depois (esta RFC) |
|-------------------|-------------------|
| “Implementar o suite Delivery” | “Implementar o **app** `delivery` (e extensões)” |
| Roadmap com dezenas de ✅ aspiracionais | Catálogo: o que está **instalável**, não o que todo cliente tem |
| Página sempre no menu | Página só se app instalado |

Mapeamento inicial:

| Família RFC | App id |
|-------------|--------|
| POS / Caixa | `pos` |
| Inventário MVP / 5xxx (básico) | `inventory` |
| WMS 9xxx | `wms` |
| Delivery 18xxx | `delivery` (+ subapps depois) |
| Receiving 4xxx | `receiving` |
| Fiscal Engine | `fiscal` |
| Accounting 8xxx | `accounting` |
| Loan 7xxx | `loans` |
| Folha / Funcionários | `hr_payroll` |

Delivery Core (18000–18008) + Operations (18100–18105) já feitos = **código do app `delivery`**, que no produto modular fica **disponível para instalar**, não obrigatório para toda organização.

---

# 15. Estratégia de implementação (dois horizontes)

## 15.1 Horizonte A — MVP (filosofia real, mecanismo simples)

Objetivo: o admin e o cliente **sentem** o modelo Odoo sem construir framework.

Entregáveis:

1. Catálogo estático de apps (manifests em JSON ou Python).  
2. `empresa/org.apps` persistido.  
3. Defaults: `pos` + `inventory` + `fiscal` ON.  
4. Filtro de menu por app.  
5. Hub Configurações só lista apps instalados.  
6. Guard de API por `api_prefixes`.  
7. Tela **Instalar / Desinstalar** (disable).  
8. Seed mínimo ao instalar (quando aplicável).

**Não** inclui neste horizonte:

* loader dinâmico de código  
* desinstalação com drop físico de arquivos  
* marketplace externo  
* dependências versionadas complexas  

## 15.2 Horizonte B — Instalador completo

Quando o catálogo e o uso real estabilizarem:

* hooks `install` / `migrate` / `uninstall` / `purge`  
* versões e upgrade path por app  
* subapps formais (`delivery_ops`, `delivery_field`, …)  
* edição comercial / licenciamento por app (se houver)  
* instalação por estabelecimento (se surgir dor real)

O Horizonte B **não** bloqueia o A. A filosofia já vale no A.

---

# 16. Fases sugeridas de ataque

| Fase | Entrega | Critério de pronto |
|------|---------|--------------------|
| **P0** | Esta RFC aprovada + catálogo v1 | Time alinhado no norte |
| **P1** | Persistência `org.apps` + defaults | Org nova nasce Loja (POS+Estoque+Fiscal) |
| **P2** | Menu + Config hub respeitam apps | Org sem Delivery não vê Entregas |
| **P3** | Guard API + tela Instalar/Desinstalar | Folha/Delivery “Instalar” funciona de ponta a ponta no UX |
| **P4** | Seeds por app + degradação de integração | WMS sem Delivery não quebra |
| **P5** | Horizonte B (hooks/migrate/purge) | Só com dor real |

P1–P3 já materializam a ideia de produto.  
Delivery Trip (18106+) continua podendo avançar **como código do app `delivery`**, independentemente de P1 — mas o menu Delivery deve eventualmente depender de `delivery` instalado.

---

# 17. Não-objetivos

Esta RFC **não** define:

* Precificação comercial por módulo (pode vir depois)  
* Marketplace público de terceiros  
* Reescrita do monólito Python em microserviços  
* Isolamento de processo por app  
* Paridade feature-a-feature com Odoo  

Também **não** obriga parar o desenvolvimento de domínio (Delivery, WMS…) até o instalador existir. Obriga apenas a **classificar** o trabalho como app.

---

# 18. Critérios de sucesso

A plataforma está no caminho certo quando:

1. Uma organização pode operar **só com POS + Estoque + Fiscal**.  
2. Instalar **Folha** é uma ação explícita do admin — e só então Folha aparece.  
3. Desligar **Delivery** remove Entregas do menu e bloqueia APIs `/api/delivery*`.  
4. Novas RFCs de domínio declaram **em qual app** vivem.  
5. Ninguém precisa “engolir o suite” para usar o BECRP.

---

# 19. Decisões travadas (desta conversa de produto)

| # | Decisão |
|---|--------|
| D1 | Filosofia: cada cliente monta o seu BECRP (base + apps). |
| D2 | Base magra; não instalar Contabilidade/Folha/WMS/Delivery por default. |
| D2b | **Modelo Odoo:** Fase 1 = base (dados + admin + gerais); Fase 2 = admin escolhe pacotes/apps. |
| D3 | **Fiscal** entra no pacote Loja/Atacado (Fase 2), não na base sozinha. |
| D4 | Atalho recomendado Fase 2 = **Loja** (POS + Estoque + Fiscal). `sales` é app separado. |
| D4b | **POS ≠ Vendas**: POS = consumidor final; Vendas = B2B/CNPJ/licitação. Compartilham produtos/armazéns; fluxos separados. |
| D5 | Folha, Contabilidade, WMS, Delivery, Compras = módulos de instalação. |
| D6 | MVP = registry + flags + menu + API guard + UX Instalar; não clonar engine Odoo. |
| D7 | Apps no nível Organização; permissões de usuário são camada seguinte. |
| D8 | Uninstall MVP = disable (dados preservados). |
| D9 | Regras de estoque entre POS / WMS / Delivery permanecem contratos entre apps. |

---

# 20. Exemplos de footprint

### Empresa A — Loja (consumidor final)

```text
Instalados: pos, inventory, fiscal
Off: sales, purchases, wms, delivery, accounting, hr_payroll
```

### Empresa B — Atacado / B2B (CNPJ)

```text
Instalados: sales, inventory, fiscal
Off: pos (a menos que também tenha balcão), wms, delivery, hr_payroll
```

### Empresa C — CD com frota

```text
Instalados: sales, inventory, fiscal, wms, delivery
Off: pos, hr_payroll, accounting (até precisar)
```

### Empresa D — Serviços + folha

```text
Instalados: sales, fiscal, hr_payroll, accounting
Off: pos, inventory, wms, delivery
```

Mesmo produto. Três BECRPs diferentes.

---

# 21. Open questions (resolver na implementação P1)

1. ~~`pos` e `sales` são um app só?~~ **Resolvido (D4b):** dois apps distintos.  
2. Estoque mínimo fica na base ou sempre como app `inventory`? (**Recomendação:** app `inventory`, default ON.)  
3. Onde persistir: `org_store` vs `dados/org_apps.json`?  
4. Subapps de Delivery entram já no catálogo v1 ou só flags internas até 18106+?  
5. Wizard da 1ª instalação é tela dedicada ou passo dentro de Configurações → Gerais?  
6. Pacote “Atacado / B2B” instala só `sales` ou `sales`+`pos`? (**Recomendação:** só `sales` + inventory + fiscal; POS opcional.)

---

# 22. Arquitetura final (regra)

```text
                    ┌─────────────┐
                    │  Instalador │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Base     │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   Apps default      Apps sob demanda   Extensões
   POS/Vendas        Compras            Mobile
   Estoque           WMS                Analytics
   Fiscal            Delivery
                     Contabilidade
                     Folha
```

O BECRP não é um ERP monolítico com descontos.  
É um **agregador de capacidades** — a organização instala o que a operação aguenta.

> **Simple is always better than complex.**  
> Instale a base. Instale o resto só quando precisar.

---

# 23. Próximo passo documental

* Aprovar esta RFC (P0).  
* Atualizar `sprints/TODO.md` com fase Platform Apps (P1–P3) quando for prioridade de ataque.  
* Em cada RFC de domínio nova: campo **`App`** no cabeçalho (`delivery`, `wms`, …).  

Implementação de código **só** após priorização explícita de P1 — esta RFC é o norte compartilhado (humano + agentes).
