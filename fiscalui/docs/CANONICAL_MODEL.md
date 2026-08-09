# BC-000 — Modelo Canônico de Negócio

**Versão:** 1.0
**Data:** 2026-07-25

## 1. Objetivo

O BusinessCore é o núcleo de domínio da plataforma.

Sua responsabilidade é representar as operações empresariais de forma independente da tecnologia utilizada na interface, no banco de dados ou nas regras fiscais.

> **O BusinessCore não pertence ao Brasil. Ele pertence ao negócio.**
>
> Cliente, Empresa, Pessoa, Produto, Serviço, Pedido, Venda, Compra, Documento — nenhum desses conceitos possui regra fiscal. Eles representam apenas conceitos empresariais. A tributação vem depois, no FiscalCore.

O BusinessCore não conhece HTML, JavaScript, Python, COBOL ou PostgreSQL.

Ele conhece apenas o negócio.

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

## 2. Missão

Centralizar todas as regras de negócio da plataforma.

Todo evento empresarial passa obrigatoriamente pelo BusinessCore.

---

## 3. Visão

O BusinessCore será a única fonte de verdade sobre o comportamento do ERP.

Nenhum outro módulo poderá definir regras de negócio de forma isolada.

---

## 4. Princípios

O BusinessCore foi projetado com base em dez princípios fundamentais:

| # | Princípio | Descrição |
|---|-----------|-----------|
| 1 | Linguagem única de domínio | Todos os motores compartilham o mesmo vocabulário definido neste documento |
| 2 | Independência tecnológica | O core não conhece interface, banco ou protocolo |
| 3 | Baixo acoplamento | Motores se comunicam por eventos, nunca por chamada direta |
| 4 | Alta coesão | Cada motor faz exclusivamente o que seu domínio define |
| 5 | Modularidade | Domínios são independentes e substituíveis |
| 6 | Extensibilidade | Novos comportamentos são adicionados sem modificar o existente |
| 7 | Auditabilidade | Todo evento é registrado e rastreável |
| 8 | Imutabilidade dos eventos | Eventos passados nunca são alterados — apenas compensados |
| 9 | Testabilidade | Regras são testáveis isoladamente, sem infraestrutura |
| 10 | Evolução contínua | O modelo evolui por novos contextos, sem reescrita |

---

## 5. Posicionamento na Plataforma

```
                    FiscalUI
               (Interface do Usuário)

                        │

                        ▼

                 BusinessCore

        ┌────────────┼────────────┐

        │            │            │

   FiscalCore   AccountingCore   WorkflowCore

        │            │            │

        └────────────┼────────────┘

                 Integration API

                        │

                 Python Services

                        │

                 COBOL Services

                        │

                  PostgreSQL
```

O BusinessCore coordena o fluxo das operações.

Os demais motores executam responsabilidades especializadas.

### Especialização por Motor

Cada motor **especializa** os conceitos do BusinessCore para seu domínio. A entidade raiz permanece a mesma — o que muda é o comportamento adicionado.

```
BusinessCore

Produto
  ├── Código
  ├── Descrição
  ├── Unidade
  └── Categoria

       │
       ▼

FiscalCore

Produto Fiscal
  ├── NCM
  ├── CEST
  ├── CFOP
  ├── CST
  ├── Origem
  ├── Benefício Fiscal
  └── Regra Tributária
```

```
BusinessCore

Empresa
  ├── Razão Social
  ├── CNPJ
  └── Filiais

       │
       ▼

FiscalCore

Empresa Fiscal
  ├── Inscrição Estadual
  ├── Inscrição Municipal
  ├── CRT
  ├── Regime Tributário
  ├── Certificados
  ├── CSC
  ├── Ambiente (produção/homologação)
  └── SEFAZ

       │
       ▼

AccountingCore

Empresa Contábil
  ├── Plano de Contas
  ├── Exercício Social
  └── Método de Escrituração
```

### A Regra de Ouro

**BusinessCore nunca terá campos fiscais. Nunca.**

**BusinessCore nunca terá campos contábeis. Nunca.**

```
Errado:

Produto
  ├── NCM              ← campo fiscal
  ├── CFOP             ← campo fiscal
  └── Conta Contábil   ← campo contábil
```

```
Correto:

BusinessCore → Produto (código, descrição, unidade, categoria)
       │
       ├── FiscalCore  → ProdutoFiscal (NCM, CEST, CFOP, CST, origem)
       │
       └── AccountingCore → ProdutoContabil (conta contábil, natureza)
```

**Isso vale para absolutamente todos os conceitos:**

| Conceito | BusinessCore | FiscalCore | AccountingCore |
|----------|-------------|------------|----------------|
| Produto | Código, descrição, unidade | NCM, CEST, CFOP, CST, origem | Conta contábil, natureza |
| Empresa | Razão social, CNPJ, filiais | IE, IM, CRT, regime, certificados | Plano de contas, exercício |
| Cliente | Nome, documento, contato | Regime, contribuinte ICMS, Suframa | Conta contábil padrão |
| Documento | Tipo, data, emissor, destinatário | Chave, protocolo, status SEFAZ | Lotes, competência |
| Movimento | Tipo, data, valor | CFOP, CST | Conta débito, conta crédito |

Essa decisão fará toda a diferença daqui a cinco ou dez anos. Um modelo de negócio puro evita que regras fiscais e contábeis contaminem o núcleo do ERP, permitindo que o sistema evolua independentemente das constantes mudanças na legislação.

---

## 6. Responsabilidades

O BusinessCore é responsável por:

- Modelar entidades de negócio
- Validar regras empresariais
- Coordenar processos
- Publicar eventos
- Orquestrar chamadas aos motores especializados
- Manter consistência do domínio

**O BusinessCore não calcula impostos.**

**O BusinessCore não gera lançamentos contábeis.**

**O BusinessCore não executa SQL.**

**O BusinessCore não renderiza interface.**

---

## 7. Domínios

O BusinessCore será organizado em domínios independentes.

```
BusinessCore
├── Cadastro
├── Comercial
├── Compras
├── Estoque
├── Financeiro
├── Produção
├── Serviços
├── Contratos
├── Projetos
├── Patrimônio
├── Logística
├── CRM
├── RH
├── Qualidade
├── BI
└── Integrações
```

Cada domínio possui suas próprias regras, entidades, eventos e políticas. A comunicação entre domínios ocorre exclusivamente por eventos publicados no barramento interno.

---

## 8. Fluxo de uma Operação

Exemplo: Venda.

```
Usuário
   │
   ▼
Pedido de Venda
   │
   ▼
BusinessCore
   │
   ▼
Validação
   │
   ▼
Reserva de Estoque
   │
   ▼
FiscalCore
   │
   ▼
AccountingCore
   │
   ▼
WorkflowCore
   │
   ▼
Confirmação
   │
   ▼
Eventos
   │
   ▼
Interface
```

O BusinessCore controla a sequência. Cada etapa é executada pelo motor especializado correspondente, e o BusinessCore orquestra o encadeamento.

---

## 9. Comunicação

Nenhum domínio conversa diretamente com outro.

Toda comunicação ocorre através do BusinessCore.

```
Comercial
   │
   ▼
BusinessCore
   │
   ▼
Estoque
```

**Nunca:**

```
Comercial
   │
   ▼
Estoque
```

Isso reduz o acoplamento entre módulos e garante que o BusinessCore mantenha a consistência geral do sistema.

---

## 10. Linguagem de Domínio

O BusinessCore estabelece um vocabulário comum.

```
Cliente
Fornecedor
Produto
Serviço
Pedido
Cotação
Compra
Venda
Documento
Pagamento
Recebimento
Movimento
Contrato
Projeto
```

Todos os motores utilizam exatamente esses conceitos, sem sinônimos ou interpretações divergentes.

---

## 11. Eventos

Toda alteração relevante gera um evento.

Exemplos:

```
ClienteCriado
ProdutoAtualizado
PedidoAprovado
PedidoCancelado
EstoqueReservado
EstoqueBaixado
DocumentoFiscalEmitido
PagamentoRecebido
PagamentoConfirmado
LançamentoContábilGerado
ContratoAssinado
CompraFinalizada
```

Esses eventos podem ser consumidos por outros motores para reagir sem acoplamento direto.

---

## 12. Benefícios

Essa arquitetura proporciona:

- Separação clara de responsabilidades
- Evolução independente dos motores
- Facilidade de testes
- Menor acoplamento
- Maior reutilização
- Melhor capacidade de auditoria
- Preparação para integrações futuras

---

## 13. Roadmap do BusinessCore

```
BC-000  Manifesto do BusinessCore          ← docs/BC-000_MANIFESTO.md
BC-001  Arquitetura
BC-002  Ontologia Empresarial              ← docs/ONTOLOGIA_EMPRESARIAL.md
BC-003  Modelo Canônico                    ← estamos aqui (docs/CANONICAL_MODEL.md)
BC-004  Entidades
BC-005  Value Objects
BC-006  Agregados
BC-007  Eventos
BC-008  Casos de Uso
BC-009  Políticas
BC-010  Serviços de Domínio
BC-011  Repositórios
BC-012  Especificações
BC-013  Máquina de Estados
BC-014  Orquestração
BC-015  Integrações
```

---

**Arquivo:** `docs/CANONICAL_MODEL.md`
**Versão:** 1.0
**Data:** 2026-07-25

---

## 3. Produto

*(aguardando definição)*

---

## 4. Serviço

*(aguardando definição)*

---

## 5. Venda

*(aguardando definição)*

---

## 6. Compra

*(aguardando definição)*

---

## 7. Documento

*(aguardando definição)*

---

## 8. Evento de Negócio

*(aguardando definição)*

---

## 9. Movimento de Estoque

*(aguardando definição)*

---

## 10. Lançamento Financeiro

*(aguardando definição)*

---

## 11. Lançamento Contábil

*(aguardando definição)*
