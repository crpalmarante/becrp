# Plano: Evolução da Experiência do Vendedor (POS)

## Filosofia

> O vendedor não opera o sistema — o sistema serve o vendedor.

Cada clique, cada tela, cada atalho deve aproximar o vendedor do fechamento da venda.
Nada que não ajude a vender deve estar na frente do vendedor durante o atendimento.

---

## Diagnóstico do Estado Atual

O POS (`frontend/pages/pos.html`) é funcional, mas tem problemas estruturais:

| Aspecto | Problema |
|---------|----------|
| **Código** | 93KB inline (CSS + HTML + JS), difícil de manter |
| **Produtos** | Grade textual (nome + preço). Sem imagens, sem variações |
| **Fluxo** | Venda, cadastro, config, relatórios — tudo misturado na mesma barra |
| **Cliente** | Apenas um campo de texto. Sem contexto do cliente na venda |
| **Design System** | BusinessUI existe mas não é usado no POS |
| **Responsividade** | Grid fixo, não adapta para tablet ou mobile |

---

## Fase 1 — POS Renovado (Fundação Visual)

**Objetivo:** Aplicar o design system BusinessUI ao POS, melhorando a experiência visual e a usabilidade imediata.

### 1.1 Layout Limpo e Focado
Extrair o CSS do `pos.html` para um arquivo separado (`css/pos.css`), reutilizando variáveis e componentes do BusinessUI.

**Antes (atual):**
```
Header com logo | Filial | Ponto | Relógio
Nav: Vender | Produtos | Vendas | Relatórios | Caixa | Config | Faturamento
┌─────────────────────────────────────┐
│  Grade de produtos (texto+pisca)    │
│                                      │
├──────────────────────┬──────────────┤
│                      │   Pedido      │
│    Produtos          │   (textual)   │
│    em grid           │              │
│    (sem imagem)      │              │
└──────────────────────┴──────────────┘
```

**Depois:**
```
┌──────────────────────────────────────────────────────────┐
│  Nav: [PDV] [Caixa]                                      │
├────┬──────────────┬─────────────────┬────────────────────┤
│ SS │  Mostruário  │  Itens do       │  Smart Panel       │
│    │              │  Pedido         │  (contexto atual)  │
│    │              │                 │                    │
└────┴──────────────┴─────────────────┴────────────────────┘
```

### 1.2 Cards de Produto com Imagem
- Layout em grid com cards visuais (imagem grande, nome, preço, variações)
- Imagens do `gerir_imagens.cbl` / endpoint `/api/produto/imagens`
- Fallback: ícone/cor para produtos sem imagem
- Variações visíveis no card (cor, tamanho — quando houver)
- Indicador visual de stock (verde → normal, amarelo → baixo, vermelho → crítico)

### 1.3 Busca Visual com Preview
- Campo de busca com resultado em tempo real (já existe, mas sem preview)
- Preview do produto: imagem + descrição + preço + stock ao teclar Enter
- Resultados da busca em grid visual (não lista textual)
- Código de barras como fluxo principal (já existe, manter)

### 1.4 Atalhos de Teclado Ampliados
| Atalho | Função | Status |
|--------|--------|--------|
| F1 | Finalizar venda | ✅ Existe |
| F2 | Focar busca | ✅ Existe |
| F3 | Limpar pedido | ❌ Não usar F-keys — botão visual |
| F4 | Abrir mostruário completo | ⬜ Novo |
| F5 | Cancelar último item | ✅ Existe |
| F6 | Suspender venda | ✅ Existe |
| F7 | Buscar cliente | ⬜ Novo |
| F8 | Alternar modo venda/orçamento | ⬜ Novo |
| F9 | Abrir caixa rápido | ⬜ Novo |
| ESC | Fechar modal/overlay | ✅ Existe |
| Ctrl+Enter | Finalizar direto (pula confirmação) | ⬜ Novo |

---

## Fase 2 — Fluxo Centrado no Vendedor

**Objetivo:** Reduzir o atrito entre o vendedor e o fechamento da venda.

### 2.0 Smart Panel (console contextual)

> **Decisão de produto:** o lado direito **não** é um resumo estático nem “o numpad”.
> É o **Smart Panel** — console contextual do operador. Exibe exatamente a ferramenta da tarefa atual; o painel **muda por completo** ao trocar de tarefa.

**Durante a venda (contexto padrão — Resumo):**

```
┌─────────────────────────────────────┐
│ Resumo do Pedido                    │
├─────────────────────────────────────┤
│ Cliente                             │
│ João da Silva                       │
├─────────────────────────────────────┤
│ Itens                               │
│ 3 produtos                          │
├─────────────────────────────────────┤
│ Subtotal        R$ 350,00           │
│ Desconto ›      R$   0,00           │
│ Acréscimo ›     R$   0,00           │
│ Total           R$ 350,00           │
├─────────────────────────────────────┤
│ [Enviar ao caixa]                   │
└─────────────────────────────────────┘
```

**Ao tocar em Desconto — o painel muda completamente:**

```
┌─────────────────────────────────────┐
│ Desconto                            │
├─────────────────────────────────────┤
│ Tipo                                │
│ (•) Valor                           │
│ ( ) Percentual                      │
├─────────────────────────────────────┤
│ Valor                               │
│ R$ 15,00                            │
├─────────────────────────────────────┤
│  7  8  9                            │
│  4  5  6                            │
│  1  2  3                            │
│ 00  0  ←                            │
├─────────────────────────────────────┤
│ Cancelar            Aplicar         │
└─────────────────────────────────────┘
```

**Ao tocar em Acréscimo — mesmo painel, ferramenta Majoração:**

```
┌─────────────────────────────────────┐
│ Majoração                           │
├─────────────────────────────────────┤
│ Tipo                                │
│ (•) Valor                           │
│ ( ) Percentual                      │
├─────────────────────────────────────┤
│ Valor + teclado (00 0 ←)            │
├─────────────────────────────────────┤
│ Cancelar            Aplicar         │
└─────────────────────────────────────┘
```

**Parcelamento — muda a ferramenta (não é o mesmo que Majoração):**

```
┌─────────────────────────────────────┐
│ Parcelamento                        │
├─────────────────────────────────────┤
│ Valor Total                         │
│ R$ 1.250,00                         │
├─────────────────────────────────────┤
│ Parcelas                            │
│ 10                                  │
├─────────────────────────────────────┤
│ Juros                               │
│ 2%                                  │
├─────────────────────────────────────┤
│ Resultado                           │
│ 10 × R$ 137,49                      │
├─────────────────────────────────────┤
│ teclado (edita o campo focado)      │
│ Cancelar            Aplicar         │
└─────────────────────────────────────┘
```

**Quantidade / Peso / Valor Manual — teclado com rótulo da ferramenta:**

```
Quantidade → display 25
Peso       → display 1,275 kg
Valor Manual → Preço Unitário → R$ 42,80
```

**Observação — teclado desaparece; entra editor de texto.**

| Tarefa atual | Contexto do Smart Panel |
|--------------|-------------------------|
| Durante a venda (padrão) | **Resumo do Pedido** |
| Selecionar cliente | **Pesquisa de Clientes** |
| Desconto | **Desconto** (Valor/Percentual + teclado) |
| Acréscimo | **Majoração** (mesmo painel do desconto) |
| Parcelamento | **Parcelamento** (total, parcelas, juros, resultado) |
| Quantidade | **Quantidade** + teclado |
| Peso | **Peso** + teclado |
| Valor manual | **Valor Manual** (Preço Unitário) + teclado |
| Observação | **Observação** (editor de texto, sem numpad) |
| Pagar (caixa) | **Pagamento** |
| Consultar estoque | **Estoque** |

Regras:

- Um contexto ativo por vez; a troca é **substituição total** do conteúdo do painel.
- Cancelar / Aplicar / Esc → volta ao **Resumo do Pedido**.
- Sem F-keys. Teclado físico só enquanto houver entrada numérica aberta.
- Coluna central = **itens do Pedido**; Smart Panel = console da tarefa (não duplica a lista).

### 2.1 Contexto: Pesquisa de Clientes
- Abre no Smart Panel ao tocar no cliente / “Selecionar cliente”
- Mostra: busca, resultados, nome, telefone, histórico, saldo crediário
- Permite criar cliente rápido (nome + CPF) sem sair da venda
- Sugestão de cliente frequente (CPF ou telefone)

### 2.2 Pedido (coluna central)
> **Decisão:** o conceito de “carrinho” não é usado. A lista é **Pedido** (itens da venda em curso).

- Agrupamento por variação (ex: "Camisa Azul - G")
- Ações inline: `+`/`−`, toque na qtd → Teclado Numérico, desconto, remover, observação → Editor de Texto
- Indicador visual de itens com estoque crítico

### 2.2.1 Contexto: Desconto / Majoração
Mesmo painel. Título **Desconto** ou **Majoração**. Tipo (valor / percentual), display, teclado `00 0 ←`, Cancelar / Aplicar.

### 2.2.2 Contexto: Parcelamento
Ferramenta própria: Valor Total (pedido), Parcelas, Juros %, Resultado (`N × R$ …`). Teclado edita o campo focado.

### 2.2.3 Contextos com teclado: Quantidade, Peso, Valor Manual
| Contexto | Rótulo do campo | Display |
|----------|-----------------|---------|
| Quantidade | Quantidade | `25` |
| Peso | Peso | `1,275 kg` |
| Valor Manual | Preço Unitário | `R$ 42,80` |

### 2.2.4 Observação
Teclado numérico **desaparece**. Entra editor de texto + Cancelar / Aplicar.

### 2.2.5 Demais
- **Pagamento** — terminal Caixa
- **Estoque** — disponibilidade / promise

### 2.3 Finalização Rápida
- CTA “Enviar ao caixa” no **Resumo do Pedido** (Smart Panel)
- Resumo compacto sempre visível no contexto padrão
- Opção "Finalizar e continuar" (venda em sequência)
- Sem depender de atalhos F-key

### 2.4 Gestão de Vendas Suspensas
- Faixa de sessões à esquerda (já no layout)
- Lista de vendas suspensas com data, cliente, valor
- Um clique para retomar

### 2.5 Produtividade do vendedor (PDV)

Implementado em `pages/pos.html` + `js/pos-pdv.js` + `css/pos.css` (mock/local):

1. **Suspender/retomar sessões** — trilho esquerdo com sessões ativas e suspensas (cliente, itens, total, tempo relativo); Suspender grava e abre sessão nova; toque retoma; botão **+** cria sessão.
2. **Cliente recorrente rápido** — busca por nome/CPF/telefone com parceiros mock (João da Silva com crediário e última compra); chip do resumo atualiza com hint contextual.
3. **Favoritos / últimos produtos** — abas Todos | Favoritos | Últimos; persistência em `localStorage`; estrela ou long-press no card; adicionar ao pedido alimenta recentes.
4. **Variações no Smart Panel** — Camisa Polo (cores/tamanhos); contexto **Variação** no painel; ativo em modo Moda ou sempre para esse SKU.
5. **Linguagem humana de estoque** — consulta e badge nos cards (`stockStatus`: na loja, filial ~2h, trânsito, sem previsão).
6. **Desfazer último item** — botão **Desfazer** com pilha simples (add/remove/qty/preço/obs).
7. **Frases rápidas de observação** — chips na contexto Observação que appendam ao textarea.
8. **Orçamento ↔ Pedido** — toggle no painel central; CTA **Salvar orçamento** / **Virar pedido**; envio ao caixa só em Pedido.
9. **Feedback pós-envio ao caixa** — banner no resumo + status bar; estados mock Aguardando → Em pagamento → Pago; item entra na fila do Caixa; permanece no PDV.
10. **Perfil da loja** — seletor Mercearia | Moda | Serviço na topbar; filtra ênfase do catálogo; persistido; label na barra de status.

### 2.6 Produtividade avançada (PDV — lote 2)

Implementado em `pages/pos.html` + `js/pos-pdv.js` + `css/pos.css` (mock/local):

1. **Consulta de preço** — toggle **Consulta** ao lado da busca; quando ativo, toque/scan abre contexto **Consulta de Preço** no Smart Panel (nome, preço, badge de estoque) sem adicionar ao pedido; botão **Adicionar ao pedido** opcional; Enter na busca também respeita o modo.
2. **Troca / devolução** — botão **Troca/devolução** no resumo; contexto **Troca / Devolução** com busca por NFC-e ou CPF; 3 vendas mock; seleção carrega linhas negativas/tagged `troca: true` com observação da NFC-e; permanece no PDV.
3. **Lista de espera / camarim** — botão **Espera** junto a Suspender; sessão marcada `espera` com label (primeiro nome) e badge de prioridade; trilho renderiza badge **espera**; retomar funciona como suspensa.
4. **Meta / comissão do dia** — `#status-goal` na barra de status (ex. **Meta 72%**); meta mock R$ 5.000/dia; progresso soma pedidos enviados ao caixa (localStorage); não incrementa em modo treinamento.
5. **Produto similar na falta** — Sabão em pó `stockStatus: none` com `similares: [7, 2]`; contexto **Produtos Similares** e bloco no painel Estoque com botões **Trocar**; dispara ao adicionar produto indisponível ou consultar estoque.
6. **Kit / promoção automática** — regras mock: 3+ Detergentes −10%; Leite 3 por 2; linha **Promo** no resumo com desconto aplicado ao total; recalculado em `renderOrder`.
7. **Histórico do cliente** — `historico` e `tamanhoUsual` nos parceiros mock; hint enriquecido ao selecionar; bloco `#client-history` sob o chip com últimas compras e dica de tamanho (moda).
8. **Bip composto** — Enter em `#prod-search` interpreta `2*SKU`, `SKU*2`, `2xSKU` (case insensitive); busca por sku/id/ean; adiciona quantidade; limpa busca; Enter simples = primeiro filtrado (ou consulta se toggle ativo).
9. **Modo treinamento** — toggle **Treino** na topbar; classes `training` no body/app; status **TREINO**; banner no resumo; envio simula fila com badge Treino sem ciclo de pagamento real nem meta.
10. **Avisos operacionais** — produtos com `alertas: ["promo","recall"]`; badges nos cards; recall exige confirmação antes de adicionar; promo badge visual (Leite, Detergente promo; Sabão recall).

---

## Fase 3 — Mostruário Eletrônico Integrado

**Objetivo:** O vendedor mostra o produto ao cliente sem sair do fluxo de venda.

Implementado em `pages/pos.html` + `js/pos-pdv.js` + `css/pos.css` (mock/local):

### 3.1 Galeria no Contexto da Venda
- Toque no card abre o overlay **Mostruário** (`#showcase`): galeria com setas, dots e swipe; descrição; estoque; badges Novo/Promo/Recall.
- Variações (cor/tamanho) no próprio mostruário com **preço por combinação** (`ajusteCor` / `ajusteTam`).
- CTA **Adicionar ao pedido** e **Consultar preço**; ESC / backdrop fecha; setas do teclado trocam foto.
- Bip (Enter na busca) continua adicionando direto, sem abrir galeria.
- Modo Consulta: toque no card ainda abre consulta de preço (sem mostruário).

### 3.2 Vitrine por Categoria (Visual)
- Abas visuais `#prod-cats` (`.vitrine-cat`) com ícone, nome e contagem — não é dropdown.
- Subcategorias (`.vitrine-sub`) quando a categoria tem `subcat` (ex. Mercearia → Grãos / Óleos).
- Badges **Novo**, **Promo** e **Recall** nos cards e no mostruário.

### 3.3 Busca com Fotos
- Resultados permanecem em **grid de imagens** (`#prod-grid`).
- Toolbar: ordenar (relevância / menor / maior preço / novidades); faixa de preço; disponibilidade.
- Label dinâmico (ex. “3 resultados · fotos”) quando há busca.

---

## Fase 4 — Capacidades Ativáveis

**Objetivo:** O mesmo POS se adapta ao segmento sem mudar a experiência.

### 4.1 Modo Alimentação / Mercearia
- Campo de peso (balança integrada ou manual)
- Unidade KG como default para produtos cadastrados como KG
- Agrupamento por seção (hortifrúti, padaria, frios, mercearia)

### 4.2 Modo Moda / Vestuário
- Grade de tamanhos (P/M/G/GG ou numérico) visível no card
- Variações de cor com swatch visual
- Agrupamento por coleção/temporada

### 4.3 Modo Serviço
- Campo de descrição do serviço na venda
- Duração e agendamento (version 2)
- Comissão por serviço (já existe estrutura de RH)

### 4.4 Ativação por Perfil do Vendedor
- O vendedor tem um perfil que define quais modos estão ativos
- A tela inicial já carrega no modo correto
- O vendedor não precisa configurar nada — o sistema sabe

---

## Fase 5 — Promisse Engine & Fulfillment (Preview)

**Objetivo:** O vendedor sabe, na hora, se pode prometer o produto ao cliente.

### 5.1 Indicador de Disponibilidade
- **Verde:** em estoque na filial → entrega imediata
- **Amarelo:** em estoque em outra filial → retirada em X horas
- **Azul:** em trânsito / fornecedor → previsão de chegada
- **Vermelho:** indisponível → sugestão de similar

### 5.2 Promessa ao Cliente
- Ao adicionar ao pedido, mostra: "Entrega prevista: hoje 16h"
- Se for retirada em outra filial: "Disponível em Filial X em 2h"
- Mensagem clara, não técnica

### 5.3 Sugestão Inteligente
- Quando produto está indisponível, sugere similar da mesma categoria
- "Cliente também comprou" baseado em histórico local (simples, sem ML)
- Upgrade: "Leve 2 por R$ X" (promoção ativa)

---

## Roadmap

| Fase | Prioridade | Esforço | Dependências |
|------|-----------|---------|-------------|
| **Fase 1** — POS Renovado | 🔴 Alta | Média | BusinessUI já existe |
| **Fase 2** — Fluxo Centrado | ✅ Feita | Média | Smart Panel + produtividade |
| **Fase 3** — Mostruário | ✅ Feita | Alta | Galeria + vitrine + busca com fotos |
| **Fase 4** — Capacidades | 🟡 Média | Alta | Fase 1 + 2 concluídas |
| **Fase 5** — Promise Engine | 🟢 Baixa | Muito alta | Multi-filial operacional |

---

## Como Começar (Próximo Passo Imediato)

**Fase 3 concluída (mostruário).** Próximo natural:

- **Fase 4** — aprofundar modos Mercearia (peso/balança), Moda (grade no card) e Serviço; ou
- **APIs reais** — produtos/imagens/parceiros no lugar do mock `SAMPLE`.