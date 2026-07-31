# RFC: Organização, Estabelecimento e Escopo de Catálogo

| Campo | Valor |
|--------|--------|
| Status | **Plano aprovado** — seguir na implementação |
| Data | 31/07/2026 |
| Escopo | Tenant / multi-filial / catálogo do POS / hub Configurações |
| Relaciona | `PLANO_EXPERIENCIA_VENDEDOR.md`, POS, Fiscal, Inventário |

---

## 1. Filosofia

> Simple is always better than complex.

Um catálogo único. Fiscal e caixa sempre no estabelecimento. Visibilidade do SKU é exceção, não regra.

---

## 2. Níveis

| Nível | Nome | Papel |
|-------|------|--------|
| **Organização** | Grupo / tenant | Dono da conta no BECRP; usuários; catálogo mestre |
| **Estabelecimento** | Matriz ou filial (CNPJ/IE) | Emitente fiscal, CSC, certificado, estoque, PDV/Caixa |
| **Terminal** | PDV / Caixa | Opera **em um** estabelecimento; criado já vinculado a pessoa/papel |

### Regras

1. Venda e NFC-e nascem no **estabelecimento do terminal** (CNPJ emitente).
2. CNAE / regime / tributário → camada **Fiscal** do estabelecimento (e org quando aplicável).
3. POS = Varejo genérico; não escolhe “modo de loja”.
4. O operador **não troca filial na topbar**: o estabelecimento vem do **terminal** ao qual ele está vinculado.

---

## 2.1 Terminal × pessoa (decisão travada)

Ao **criar** um terminal PDV (ou Caixa), ele já nasce:

1. no **estabelecimento** (matriz/filial), e  
2. **vinculado** a um operador.

| Papel vinculado | Escopo operacional |
|-----------------|--------------------|
| **Vendedor** | Opera **aquele** PDV (atendimento / pedido). Não vê outros PDVs nem caixas. Relação **1:1** (um vendedor ↔ um PDV). |
| **Gerente** ou **Caixa** | Pode ver / operar a visão de **todos os PDVs e Caixas** do estabelecimento (fila, supervisão, financeiro). |

### Implicações

- Criação de terminal = cadastro do ponto **+** vínculo pessoa (não são passos separados opcionais).
- **Vendedor ↔ PDV = 1:1** — um vendedor não opera dois PDVs; um PDV não fica com dois vendedores titulares.
- Sem seletor de filial no fluxo de venda.
- Gerente/Caixa = painel amplo (PDVs + Caixas) no mesmo estabelecimento do terminal/sessão.
- Troca de estabelecimento só via **outro terminal** (ou reconfiguração administrativa), nunca no fluxo de venda.
- Cobertura eventual (férias/falta): reatribuir o vínculo do PDV (admin), não “logar em outro PDV” sem troca de vínculo.

---

## 2.2 Hub Configurações (decisão travada)

No menu principal existe o card **Configurações** (`pages/configuracoes.html`).

Esse hub **não** é “só PDV”. É o lugar único onde o **Administrador do sistema** faz as **configurações genéricas de todos os módulos instalados** na organização.

```
Menu principal
 └─ Configurações          ← hub Admin
     ├─ Organização / Estabelecimentos (Empresa, filiais, fiscal…)
     ├─ Usuários / Perfis
     ├─ POS: PDVs e Caixas  ← um dos módulos
     ├─ Fiscal / NFC-e      ← outro módulo (quando instalado)
     ├─ Contabilidade       ← …
     └─ … demais módulos instalados
```

### Shell da tela Configurações (UX travada)

```
Menu principal  →  card Configurações  →  tela hub

┌──────────────┬─────────────────────────────────────────┐
│  SIDEBAR     │  ÁREA DE CONTEXTO                       │
│              │                                         │
│  Gerais  ●   │  ← 1ª visão (default): o que é comum    │
│  POS         │     a TODOS os módulos                  │
│  Fiscal      │                                         │
│  …           │  demais itens: configs do módulo ativo  │
└──────────────┴─────────────────────────────────────────┘
```

1. Entra por **Configurações** no menu principal.  
2. Sidebar esquerda: **Gerais** (sempre) + **módulos instalados**.  
3. **Primeira visão (default) = Gerais** — só o que é transversal a todos os módulos.  
4. Ao clicar num módulo na sidebar, o contexto troca para as configs genéricas **daquele** módulo.  
5. Sidebar = índice; contexto = trabalho (não grade de cards como destino final).

### Gerais (primeira visão) — quadro da tela

Teste mental: *“Isso vale mesmo se a org só tivesse um módulo qualquer?”*  
**Sim** → Gerais. **Não** → sidebar do módulo.

Na área de contexto, blocos (abas ou seções empilhadas):

#### 1. Organização

| Parâmetro | Configurável | Notas |
|-----------|--------------|--------|
| Razão social / nome fantasia do grupo | Sim | Identidade do tenant |
| Logo / branding (cores básicas) | Sim | Menu, login, relatórios |
| Documento raiz (CNPJ holding, se houver) | Sim | Opcional; filiais têm o delas |
| Contato admin (e-mail / telefone) | Sim | Suporte / alertas |
| Módulos instalados (liga/desliga) | Sim | Define o que aparece na sidebar |

#### 2. Estabelecimentos (matriz / filiais)

Lista + cadastro **estrutural** (não fiscal profundo):

| Parâmetro | Configurável | Notas |
|-----------|--------------|--------|
| Código / nome da filial | Sim | Ex.: MATRIZ, FILIAL-CENTRO |
| Tipo (matriz / filial) | Sim | |
| Ativo / inativo | Sim | Inativa some do POS e do `available_at` “todas” |
| Endereço / cidade / UF | Sim | Base operacional e fiscal depois |
| CNPJ / IE (identificação) | Sim | Cadastro; **CSC/cert/série** → módulo Fiscal |
| Fuso da loja (override) | Sim | Default = fuso da org |

#### 3. Usuários e perfis

| Parâmetro | Configurável | Notas |
|-----------|--------------|--------|
| Usuários (criar/editar/desativar) | Sim | Nome, login, e-mail |
| Perfil | Sim | Admin · Vendedor · Caixa · Gerente (mínimo) |
| Estabelecimento(s) de acesso | Sim | Onde a pessoa pode atuar |
| Vínculo PDV | Não aqui | Feito em **Configurações → POS** (1:1) |

#### 4. Preferências globais (UI / locale)

| Parâmetro | Configurável | Notas |
|-----------|--------------|--------|
| Idioma padrão | Sim | Hoje PT-BR; i18n depois |
| Fuso horário padrão | Sim | Ex.: America/Sao_Paulo |
| Formato data / hora / número | Sim | dd/mm/aaaa, 1.234,56 |
| Moeda padrão | Sim | BRL |
| Tema padrão (claro/escuro) | Sim | Usuário pode override pessoal depois |
| Página inicial pós-login | Sim | Menu / último módulo |

#### 5. Segurança e sessão

| Parâmetro | Configurável | Notas |
|-----------|--------------|--------|
| Timeout de sessão (minutos) | Sim | Global; terminal pode ter o seu no POS |
| Política de senha | Sim | Tamanho mínimo, troca periódica |
| Tentativas de login / bloqueio | Sim | |
| Exigir reauth em ações críticas | Sim | Ex.: desativar filial, mudar admin |

#### 6. Comunicação (opcional, fase 2)

| Parâmetro | Configurável | Notas |
|-----------|--------------|--------|
| E-mail SMTP / provedor | Sim | Avisos do sistema |
| Remetente padrão | Sim | |

---

**Fora de Gerais** (vai para o módulo):

| Assunto | Módulo |
|---------|--------|
| Criar PDV/Caixa, impressora, balança, fila | **POS** |
| Certificado, CSC, série/número NFC-e, ambiente SEFAZ | **Fiscal** |
| Plano de contas, diários | **Contabilidade** |
| Tabelas INSS/IRRF, cargos | **Folha / RH** |
| `available_at` no produto | **Cadastro / Produtos** (não Gerais) |

### Controles de UI em Gerais

É tela de formulário admin — não dashboard. Controles típicos:

| Tipo de controle | Onde usa |
|------------------|----------|
| **Texto** | Nome, razão social, e-mail, código da filial, endereço |
| **Caixa de seleção (select)** | Perfil, idioma, fuso, tema, moeda, matriz/filial, página inicial, UF |
| **País** (select ou lookup) | País da org / estabelecimento (default BR) |
| **Senha** (password + confirmar) | Nova senha de usuário; nunca mostrar senha salva |
| **Toggle / checkbox** | Módulo ligado, estabelecimento ativo, política “exigir troca de senha” |
| **Número** | Timeout (min), tentativas de login, tamanho mín. senha |
| **Upload** | Logo |
| **Lista + botão Novo/Editar** | Estabelecimentos, usuários (abre formulário no contexto ou painel) |
| **Máscara** | CNPJ, telefone, CEP |

Exemplos concretos na 1ª visão:

- **País** → select (Brasil…)  
- **UF / Município** → selects encadeados (após país = BR)  
- **Idioma / Fuso / Tema / Moeda** → selects  
- **Perfil do usuário** → select (Admin, Vendedor, Caixa, Gerente)  
- **Senha** → campos password ao criar/resetar usuário  
- **Módulos instalados** → checkboxes ou toggles  

Senhas de certificado A1 / CSC **não** ficam em Gerais → módulo **Fiscal**.

---

### Sequência (exato)

1. **Gerais** — transversal a todos os módulos (primeira visão).  
2. Em seguida, **cada módulo instalado** na sidebar tem **suas próprias** configurações genéricas no contexto — sem misturar com outro módulo.

| Item sidebar | Contexto |
|--------------|----------|
| **Gerais** | Transversal — default ao abrir |
| **POS** | Só POS: PDVs, Caixas, vínculos, impressora/balança… |
| **Fiscal** | Só Fiscal: certificado, CSC, série/numeração… |
| **…** | Só aquele módulo |

### Princípios

1. **Um hub** — configs genéricas entram por Configurações, não pela tela operacional do módulo.  
2. **Por módulo instalado** — a sidebar só lista módulos que a org contratou/ativou.  
3. **Só Administrador** — vendedor/caixa/gerente operam o módulo; não cadastram estrutura genérica.  
4. **Genérico ≠ operação** — criar PDV, CSC, numeração, usuários = Configurações; vender/pagar = PDV/Caixa.

### Onde fica o POS dentro disso

| Área | Quem | O quê |
|------|------|--------|
| **Configurações → POS (PDVs / Caixas)** | Administrador | Criar terminal, vínculo pessoa, configs genéricas do POS, ativar/desativar |
| **Configurações → Estabelecimento / Fiscal** | Administrador | CNPJ, IE, certificado, CSC, série/número NFC-e (nível estabelecimento) |
| **PDV / Caixa (operação)** | Vendedor / Caixa / Gerente | Vender, fila, pagar, abrir/fechar sessão — **sem** cadastro de terminal |

> Simple: operação vende; Configurações estrutura.

### Pré-requisitos para criar um terminal

1. Organização ativa  
2. Estabelecimento ativo (matriz/filial)  
3. Usuário destino já cadastrado (vendedor **ou** gerente/caixa)  
4. (Recomendado) fiscal mínimo do estabelecimento preenchido — senão o Caixa avisa na hora de emitir NFC-e, mas o terminal pode existir

### Fluxo de criação (wizard Admin)

```
1. Tipo          → PDV | Caixa
2. Estabelecimento → matriz/filial (fixo após salvar)
3. Identidade    → código (único na org), nome amigável
4. Vínculo       → usuário
                 · se PDV + Vendedor → 1:1 obrigatório
                 · se Caixa/Gerente  → visão ampla no estabelecimento
5. Configs genéricas (abaixo)
6. Status        → Ativo | Inativo
```

Criar = identidade + estabelecimento + vínculo + configs. Não há “terminal órfão” sem vínculo.

### Configurações genéricas (só Admin)

Aplicam a qualquer varejo; não dependem de CNAE nem de “modo de loja”.

#### Comuns (PDV e Caixa)

| Config | Notas |
|--------|--------|
| Código / nome | Ex.: `PDV-01`, “Balcão frente” |
| Estabelecimento | Imutável no dia a dia; mudança = admin |
| Usuário titular | Reatribuição = admin (cobertura) |
| Ativo / Inativo | Inativo não autentica naquele ponto |
| Fuso / idioma UI | Default da org; override opcional |
| Modo treino permitido | Sim/não (treino não grava fila/NFC-e reais) |
| Timeout de sessão / bloqueio | Minutos de ociosidade |
| Impressora padrão | Nome/fila do SO ou “sem impressora” |
| Estação / device id | Opcional: amarrar browser/dispositivo ao terminal |

#### Só PDV

| Config | Notas |
|--------|--------|
| Balança | Nenhuma / mock / driver (quando houver) |
| Leitor código de barras | Padrão teclado-wedge; flag se usa |
| Caixa(s) destino da fila | Default: todos os caixas ativos do estabelecimento; opcional restringir |
| Capacidade local | Ex.: permitir serviço / KG — espelha mix; não recria “modo loja” |

#### Só Caixa

| Config | Notas |
|--------|--------|
| Emite NFC-e | Sim/não (loja pode ter caixa só recebimento + outro fiscal) |
| Ambiente fiscal default | Homologação / Produção (herda estabelecimento; override admin) |
| Gaveta / PIN pad | Opcional |
| Limite sangria / alerta | Thresholds operacionais |
| PDVs que alimentam a fila | Default: todos do estabelecimento |

### O que **não** é config de terminal

Fica no **estabelecimento** (ainda só Admin), não no wizard do PDV:

- CNPJ, IE, endereço, CNAE  
- Certificado A1/A3, senha, CSC, idToken  
- Série e numeração NFC-e  
- Regime tributário  

PDV/Caixa **consomem** esses dados; nunca editam.

### O que Gerente/Caixa **podem** fazer (operação, não cadastro)

- Abrir / fechar sessão de caixa  
- Suprimento / sangria  
- Ver todos os PDVs/Caixas do estabelecimento  
- Reatribuir pedido na fila (se política permitir)  

**Não** podem: criar terminal, mudar vínculo titular, alterar impressora/balança/CSC.

### Modelo mental (Configurações → POS)

```
Configurações
 └─ POS — Terminais
     └─ Estabelecimento: [Filial Centro]
         ├─ + Novo PDV
         ├─ + Novo Caixa
         ├─ PDV-01 → Ana (Vendedor) · Ativo
         ├─ PDV-02 → Bruno (Vendedor) · Ativo
         └─ CX-01  → Carla (Caixa) · Ativo · vê todos
```

(Fiscal CSC/cert continua em Configurações → Empresa/Filiais ou seção Fiscal do mesmo hub.)

---

## 3. Catálogo (decisão travada)

- Catálogo é **único na organização**.
- Por padrão, **matriz e filiais compartilham** o mesmo catálogo.
- Estoque e preço operacional são **por estabelecimento**.
- Não duplicar cadastro de produto por filial.

### Campo no produto: `Disponível em` (`available_at`)

| Valor | Significado |
|-------|-------------|
| **Vazio** / “Todas” | Todas as filiais **ativas** do grupo veem o SKU |
| **Lista (multi-select)** | Só os estabelecimentos marcados veem o SKU |

- É **escopo de visibilidade**, não “dono fiscal” do produto.
- Multi-select obrigatório no desenho (1, N ou todas via vazio) — evita campo único “pertence a”.
- A NFC-e **não** usa esse campo para emitir; usa o estabelecimento logado no terminal.

### Exceções locais (por estabelecimento, depois)

Sem quebrar o catálogo único, a filial pode ter overlays:

- preço / tabela local  
- ativo/inativo na loja  
- sortimento (além ou em vez de `available_at`, se necessário)  
- estoque (sempre local)

---

## 4. Configurações — quem configura o quê

| Configuração | Nível |
|--------------|--------|
| Usuários master, branding, plano | Organização |
| Catálogo mestre + `available_at` | Organização |
| CNPJ, IE, endereço, CNAE | Estabelecimento |
| Certificado A1/A3, CSC, série/número NFC-e | Estabelecimento |
| Estoque | Estabelecimento |
| Configs genéricas de módulos instalados (incl. PDVs/Caixas) | Hub **Configurações** · **só Administrador** (ver §2.2) |
| Abrir/fechar sessão, fila, pagamento | Terminal · operação (Caixa/Gerente/Vendedor) |

PDV **não** edita CSC/certificado nem cadastro de terminal.

---

## 5. Estado atual no código (gap)

| Hoje | Problema |
|------|----------|
| `data/empresas.json` | Matriz/filiais magras (login) |
| `dados/empresa.json` | Um emitente fiscal global |
| POS `/api/pos/*` | Ainda assume um contexto fiscal |

**Alvo:** unificar em Organização → Estabelecimentos, e POS carregar catálogo filtrado por `available_at` + estabelecimento ativo.

---

## 6. Em aberto (próximo debate)

1. Preço: lista única da org com override local, ou só local.  
2. Numeração NFC-e: sempre por estabelecimento (provável sim).  
3. Gerente/Caixa no login: terminal **Caixa/hub** próprio vs papel elevado em qualquer estação do estabelecimento.  
4. Amarrar `device id` ao terminal (1 browser/máquina) ou permitir o titular logar em qualquer máquina com o código do terminal?

---

## 7. Impacto no POS

Na boot do PDV, com estabelecimento ativo `E`:

```
catálogo_visível = produtos onde
  available_at vazio
  OR E ∈ available_at
```

Preço/estoque exibidos = da filial `E`.

---

## 8. Changelog

| Data | Nota |
|------|------|
| 31/07/2026 | Decisões: catálogo único; `available_at` multi-select; vazio = todas; fiscal no estabelecimento. |
| 31/07/2026 | Terminal criado já vinculado a vendedor (1 PDV) ou gerente/caixa (visão de todos PDVs/Caixas); sem troca de filial no fluxo. |
| 31/07/2026 | Relação vendedor ↔ PDV travada em **1:1**. |
| 31/07/2026 | Admin-only: wizard criar PDV/Caixa + configs genéricas; fiscal no estabelecimento; operação sem cadastro de terminal. |
| 31/07/2026 | Hub **Configurações** = configs genéricas de **todos** os módulos instalados; POS é uma seção, não o hub inteiro. |
| 31/07/2026 | UX Configurações: sidebar esquerda = módulos; área de contexto = configs genéricas do módulo selecionado. |
| 31/07/2026 | 1ª visão Configurações = **Gerais** (transversal a todos os módulos); módulos na sidebar abaixo. |
| 31/07/2026 | Plano confirmado pelo produto: Organização/Estabelecimento + hub Configurações (Gerais → por módulo) é o caminho a seguir. |
