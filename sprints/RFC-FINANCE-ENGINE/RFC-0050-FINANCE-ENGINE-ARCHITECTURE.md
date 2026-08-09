# RFC-0050 — Finance Engine Architecture

**Status:** Draft

**RFC:** 0050

**Categoria:** Finance Engine

**Módulo:** Finance Engine Core

**Prioridade:** Arquitetura Fundamental

**Versão:** 1.0

**Dependências:**

* RFC-0100 (Arquitetura dos Motores Centrais)
* RFC-0040 (Tax Engine)
* RFC-BUSINESS-PARTNER-MODEL.md

**Integra com:**

* Vendas (POS / B2B)
* Receiving / Purchase
* Accounting Engine (RFC-8000 a 8009)
* Compliance Engine

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

# 1. Objetivo

Definir a arquitetura oficial do Finance Engine.

O Finance Engine é um **domínio de negócio** responsável pelo ciclo financeiro operacional: títulos a receber e a pagar, caixa, bancos, conciliação, cobrança, controle de crédito e meios de pagamento.

Ele **não é um motor de processamento** como o Accounting ou o Tax. Ele é um consumidor dos mesmos eventos de negócio que alimentam a contabilidade — e publica fatos financeiros neutros para os motores consumirem.

**Regra central:** o Finance Engine **nunca conhece o plano de contas**. O mapping financeiro → contábil é regra do Accounting Engine (RFC-0100, seção 7).

Ele não pertence ao ERP.

Ele pode ser utilizado por qualquer aplicação.

---

# 2. Visão

O Finance Engine deve funcionar como uma biblioteca ou serviço.

Exemplos de consumidores.

```text
ERP

POS

Marketplace

E-commerce

API

Aplicativo Mobile

COBOL

CLI

Batch

Microserviços
```

Todos utilizam exatamente o mesmo motor.

---

# 3. Princípios

O projeto segue os princípios.

## P1

Não conhece banco de dados.

---

## P2

Não conhece PostgreSQL.

---

## P3

Não conhece COBOL.

---

## P4

Não conhece Odoo.

---

## P5

Não conhece telas.

---

## P6

Não conhece ORM.

---

## P7

Toda informação externa chega através de Interfaces.

---

## P8

Toda saída é independente do consumidor.

---

## P9

Nunca conhece o plano de contas. Publica fatos financeiros neutros (ex.: `pagamento R$ 100, forma PIX, conta bancária X`).

---

## P10

O mapping financeiro → contábil é responsabilidade do Accounting Engine, não deste domínio.

---

## P11

Meios de pagamento (PIX, TED, DOC, Boleto, cartões) são **conectores** — instrumentos que emitem eventos, não sub-domínios.

---

## P12

Conciliação bancária produz **ajustes como eventos** (taxas, juros, diferenças) — o Finance publica, o Accounting posta.

---

## P13

Título, vencimento, liquidação e saldo são a verdade financeira; nenhum outro componente reescreve esses fatos.

---

# 4. Arquitetura

```text
                   Aplicações

     ERP

     POS

     Marketplace

     API

     Mobile

     COBOL

             │

             ▼

     Finance Engine API

             │

┌─────────────────────────────────────┐

 Finance Engine Core

──────────────────────────────────────

 Accounts Receivable (AR)

 Accounts Payable (AP)

 Treasury

 Cash Management

 Cash Flow

 Bank Accounts

 Bank Statements

 Bank Reconciliation

 Payment Scheduling

 Collections

 Credit Control

──────────────────────────────────────

             │

      Interfaces (Ports)

──────────────────────────────────────

 Payment Provider

 Bank Integration Provider

 Reference Resolver

 Event Publisher

 Logger

 Clock

──────────────────────────────────────

             ▲

             │

 Implementações (Adapters)

 ERP

 PIX / TED / DOC

 Boleto

 Cartão (débito/crédito)

 Open Banking

 REST

 JSON

 Banco de Dados

 Microserviços
```

---

# 5. Filosofia

O Finance Engine nunca consulta diretamente:

* tabelas;
* banco;
* APIs;
* arquivos.

Ele apenas solicita informações através das interfaces definidas.

---

# 6. Responsabilidades

O Finance Engine deve:

* gerar títulos a receber (AR) a partir de vendas e títulos a pagar (AP) a partir de compras/recebimentos;
* controlar vencimentos, liquidações e saldos;
* administrar caixa e bancos;
* agendar e executar pagamentos e cobranças;
* conciliar extratos bancários com movimentos internos;
* controlar crédito e limites por parceiro;
* projetar e acompanhar o fluxo de caixa;
* emitir eventos financeiros para consumidores (Accounting, Compliance).

---

# 7. Não Responsabilidades

O Finance Engine não deve:

* **emitir lançamentos contábeis** (não conhece contas débito/crédito);
* decidir ou calcular tributos;
* emitir documentos fiscais;
* montar XML/DANFE;
* armazenar cadastros;
* autenticar usuários.

Essas funções pertencem a outros componentes.

---

# 8. Entradas

O motor recebe apenas objetos de domínio e eventos canônicos.

Objetos de domínio.

```text
FinancePartner

FinanceCompany

FinanceTitle

FinanceAccount (banco / caixa)

PaymentInstruction
```

Eventos consumidos (RFC-0100, seção 5).

```text
Venda finalizada        → gera AR (título/parcelas)
Recebimento concluído   → gera AP (fornecedor a pagar)
Compra aprovada         → gera AP
```

Nunca modelos específicos do ERP.

---

# 9. Saídas

O motor produz fatos financeiros neutros e eventos.

```text
FinanceTitle (título)

FinanceTransaction (movimento)

ReconciliationResult

CashFlowProjection

CreditAssessment

Events:
  title_created
  title_settled
  payment_scheduled
  payment_executed
  reconciliation_adjustment
```

Nunca objetos do ERP.

---

# 10. Interfaces

Toda dependência externa deve ser abstraída.

Interfaces previstas.

```text
PaymentProvider

BankIntegrationProvider

ReferenceResolver

PartnerCreditProvider

EventPublisher

AuditProvider

ClockProvider

LoggerProvider
```

---

# 11. Sub-domínios

## 11.1 Accounts Receivable (AR)

- Títulos gerados no faturamento (parcelas por termos de pagamento).
- Vencimentos, baixas, quitações, renegociações.
- Cobrança e disputa de cartão.

## 11.2 Accounts Payable (AP)

- Títulos de fornecedores gerados no recebimento/compra.
- Vencimentos, baixas, agendamento de pagamento.
- Programação de pagamentos por fornecedor.

## 11.3 Treasury / Cash Management

- Posição de caixa e bancos.
- Saldos disponíveis e reservados.
- Regras de segurança (valor em caixa, limites).

## 11.4 Bank Accounts / Statements / Reconciliation

- Contas bancárias por estabelecimento.
- Extratos importados ou via integração.
- Conciliação: extrato × movimentos internos.
- Ajustes (taxas, juros, diferenças) publicados como eventos.

## 11.5 Payment Scheduling

- Agenda de pagamentos e cobranças.
- Execução por lote.
- Reprocessamento e falhas.

## 11.6 Collections

- Campanhas de cobrança (boleto, PIX, cartão).
- Controle de inadimplência.

## 11.7 Credit Control

- Limite de crédito por parceiro (AR aberto + pedidos aprovados).
- Avaliação na venda a prazo.
- Bloqueio/liberação automática.

## 11.8 Cash Flow

- **Projeção:** títulos futuros (Finance).
- **Realizado:** conciliação com o razão (Accounting).
- Dois ângulos do mesmo fluxo, nunca a mesma fonte.

---

# 12. Meios de Pagamento (conectores)

Cada meio é um adaptador que emite um evento de pagamento — nunca um sub-domínio próprio.

```text
PIX

TED / DOC

Boleto

Cartão de Débito

Cartão de Crédito
```

O evento de pagamento carrega o fato neutro:

```text
valor
forma (PIX / TED / DOC / Boleto / cartão)
conta bancária / caixa
títulos liquidados (referências)
taxas (se houver)
```

O Accounting Engine resolve a conta contábil a partir da forma e da conta (mapping, RFC-0100 seção 7).

---

# 13. Contrato de Eventos do Finance

| Evento | Publicado por | Consumido por |
|---|---|---|
| `title_created` | Finance Engine | Accounting, Compliance |
| `title_settled` | Finance Engine | Accounting |
| `payment_scheduled` | Finance Engine | — |
| `payment_executed` | Finance Engine | Accounting, Compliance |
| `reconciliation_adjustment` | Finance Engine | Accounting |
| `credit_assessment` | Finance Engine | Sales (POS / B2B) |

Regras:

- eventos são imutáveis após publicados;
- correções geram novos eventos (reversão + novo fato);
- nenhum outro componente reescreve um fato financeiro.

---

# 14. Conciliação Bancária e Ajustes

Processo.

```text
Importar extrato

↓

Conciliar com movimentos internos

↓

Pareamento automático (títulos, valores, datas)

↓

Divergências → análise

↓

Ajustes aprovados → evento de ajuste → Accounting posta
```

Taxas bancárias e juros são eventos de ajuste que viram despesa/receita financeira no plano de contas — sem que o Finance conheça a conta.

---

# 15. Relação com o Accounting Engine

O Finance publica fatos neutros; o Accounting converte em partidas dobradas.

```text
Finance: payment_executed R$ 100, PIX, conta bancária X
Accounting (mapping):
  Débito  1.01.01.02.01  Banco           100,00
  Crédito 1.01.02.01.01  Contas a Receber 100,00
```

A troca da conta contábil de um meio de pagamento é mudança de configuração **contábil**, sem impacto no Finance.

---

# 16. Fechamento Financeiro

Responsabilidade do Finance Engine.

```text
AR/AP liquidados do período

↓

Posição de caixa e bancos

↓

Conciliação bancária concluída

↓

Saldo final do período
```

O fechamento financeiro é conciliado com o fechamento contábil (período) e validado no Compliance Engine (RFC-0100, seção 8). São fechamentos distintos que se reconciliam — não se confundem.

---

# 17. Performance

Metas.

Criação de título:

< 10 ms

Processamento de lote (100 títulos):

< 1 s

Conciliação de extrato (500 linhas):

< 2 s

---

# 18. Observabilidade

Métricas.

* títulos criados/liquidados por período;
* inadimplência por parceiro;
* saldos de caixa e bancos;
* reconciliação: taxa de pareamento automático;
* pagamentos por status (agendado, executado, falhou).

---

# 19. Compatibilidade

Implementações previstas.

* Python
* COBOL
* REST
* gRPC
* CLI
* Docker

Todas compartilham o mesmo núcleo lógico.

---

# 20. Roadmap

## Sprint FN-01

Arquitetura.

Interfaces.

Modelos básicos.

---

## Sprint FN-02

Accounts Receivable (AR).

Accounts Payable (AP).

---

## Sprint FN-03

Treasury / Cash Management.

Cash Flow.

---

## Sprint FN-04

Bank Accounts.

Statements.

Reconciliation.

---

## Sprint FN-05

Payment Scheduling.

Collections.

Credit Control.

---

## Sprint FN-06

Meios de pagamento (PIX, TED/DOC, Boleto, Cartão).

---

# 21. Objetivo Final

O Finance Engine deve ser capaz de ser utilizado por qualquer sistema, independentemente de sua tecnologia.

Ele deve ser distribuído como um componente independente, consumindo apenas interfaces públicas e objetos de domínio, publicando fatos financeiros neutros — e jamais conhecendo o plano de contas, que pertence ao Accounting Engine.
