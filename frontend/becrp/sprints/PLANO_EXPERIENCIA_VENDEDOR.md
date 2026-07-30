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
│                      │   Carrinho    │
│    Produtos          │   (textual)   │
│    em grid           │              │
│    (sem imagem)      │              │
└──────────────────────┴──────────────┘
```

**Depois:**
```
┌──────────────────────────────────────────────┐
│  Nav minimalista: [Vender] [Pedidos] [Caixa] │
├──────────────────────┬───────────────────────┤
│                      │  Carrinho vazio       │
│  MOSTRUÁRIO          │  (ou com itens)       │
│  Cards com imagem    │                       │
│  Nome + Preço        │                       │
│  Variações visíveis  │                       │
│  Indicador de stock  │                       │
│                      │                       │
└──────────────────────┴───────────────────────┘
│ Barra inferior: F1 Finalizar | F2 Buscar | ...│
└──────────────────────────────────────────────┘
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
| F3 | Limpar carrinho | ✅ Existe |
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

### 2.1 Contexto do Cliente na Venda
- Painel lateral que abre ao selecionar/criar cliente
- Mostra: nome, telefone, histórico de compras, saldo crediário
- Permite criar cliente rápido (apenas nome + CPF) sem sair da venda
- Sugestão automática de cliente frequente (baseado em CPF ou telefone)

### 2.2 Carrinho Inteligente
- Agrupamento por variação (ex: "Camisa Azul - G" em vez de duas linhas separadas)
- Ações inline no item: alterar qtd (numpad), desconto, remover
- Totais parciais por tipo de tributação (para o vendedor ver)
- Indicador visual de itens com estoque crítico

### 2.3 Finalização Rápida
- Botão "Finalizar" sempre visível
- Resumo compacto antes de confirmar (já existe, simplificar)
- Opção "Finalizar e continuar" (venda em sequência, sem voltar ao grid)
- Atalho Ctrl+Enter para vendedores experientes pularem a confirmação

### 2.4 Gestão de Vendas Suspensas
- Painel visível na tela de venda (não precisa trocar de aba)
- Mínimo: lista de vendas suspensas com data, cliente, valor
- Um clique para retomar

---

## Fase 3 — Mostruário Eletrônico Integrado

**Objetivo:** O vendedor mostra o produto ao cliente sem sair do fluxo de venda.

### 3.1 Galeria no Contexto da Venda
- Ao clicar no card do produto, abre modal com:
  - Imagens em galeria (swipe ou setas)
  - Descrição completa
  - Variações (cor, tamanho) com seleção
  - Preço por variação
  - Botão "Adicionar ao carrinho" direto da galeria

### 3.2 Vitrine por Categoria (Visual)
- Categorias como abas visuais (não dropdown)
- Cada aba mostra os produtos daquela categoria em grid
- Subcategorias como badges/filtros dentro da aba
- Destaque para novidades e promoções (badge visual)

### 3.3 Busca com Fotos
- Resultados da busca em grid de imagens (não lista)
- Filtro por: categoria, faixa de preço, disponibilidade
- Ordenação: relevância, menor preço, maior preço, novidades

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
- Ao adicionar ao carrinho, mostra: "Entrega prevista: hoje 16h"
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
| **Fase 2** — Fluxo Centrado | 🔴 Alta | Média | Fase 1 concluída |
| **Fase 3** — Mostruário | 🟡 Média | Alta | Imagens já funcionam via API |
| **Fase 4** — Capacidades | 🟡 Média | Alta | Fase 1 + 2 concluídas |
| **Fase 5** — Promise Engine | 🟢 Baixa | Muito alta | Multi-filial operacional |

---

## Como Começar (Próximo Passo Imediato)

**Fase 1, Item 1.1 + 1.2:**

Extrair o CSS do `pos.html` para `frontend/css/pos.css`, reaplicar usando as variáveis e tokens do BusinessUI (`businessui/assets/css/`), e transformar a grade de produtos de cards textuais para cards com espaço para imagem.

Isso já dá uma cara nova ao POS sem mexer em nenhuma lógica de negócio.