# RFC-0060 — Compliance Engine Architecture

**Status:** Draft

**RFC:** 0060

**Categoria:** Compliance Engine

**Módulo:** Compliance Engine Core

**Prioridade:** Arquitetura Fundamental

**Versão:** 1.0

**Dependências:**

* RFC-0100 (Arquitetura dos Motores Centrais)
* RFC-0030 (Fiscal Engine)
* RFC-0040 (Tax Engine)
* RFC-0050 (Finance Engine)
* RFC-8000 a RFC-8009 (Accounting Engine)

**Integra com:**

* Fiscal Engine
* Tax Engine
* Finance Engine
* Accounting Engine
* Plataforma (BC-006 — trilha de eventos)

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

Definir a arquitetura oficial do Compliance Engine.

O Compliance Engine é o **motor de fechamento e de obrigações acessórias**: ele consome os fatos produzidos pelos demais motores, reconcilia os totais e gera as declarações e escriturações oficiais exigidas pelo fisco.

Ele **não é um motor de processamento primário**. Ele é o único componente responsável por **provar que os motores concordam entre si** — o fechamento é o seu critério de aceite.

**Regra central:** o Compliance Engine **nunca calcula tributos** (isso é do Tax Engine), **nunca posta partidas** (isso é do Accounting Engine) e **nunca emite documentos fiscais** (isso é do Fiscal Engine). Ele concilia e declara.

Ele não pertence ao ERP.

Ele pode ser utilizado por qualquer aplicação.

---

# 2. Visão

O Compliance Engine deve funcionar como uma biblioteca ou serviço.

Exemplos de consumidores.

```text
ERP

Contabilidade

Escritório de Contabilidade

Auditoria

CFO / Financeiro

Fiscal

Fisco (via arquivos oficiais)

API

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

Nunca calcula tributos. Consome o resultado da apuração do Tax Engine.

---

## P10

Nunca posta lançamentos. Consome os lançamentos e saldos do Accounting Engine.

---

## P11

Nunca emite documentos fiscais (NF-e, NFC-e). Consome os totais do Fiscal Engine.

---

## P12

O fechamento é o critério de aceite: EFD × ECD/ECF × caixa precisam bater. Se uma mudança em qualquer motor quebrar a reconciliação, ela não passa.

---

## P13

Nunca reescreve um fato de outro motor. Correções geram novos eventos (reversão + novo fato) nos motores de origem.

---

## P14

Auditoria é **transversal** (trilha de eventos BC-006), não é obrigação acessória. O Compliance consome a trilha como evidência, mas não é o dono dela.

---

## P15

Declarações e arquivos oficiais (SPED, DCTF, ECF) são **saída**, nunca fonte da verdade. A fonte da verdade são os eventos dos motores de origem.

---

# 4. Arquitetura

```text
                   Aplicações

     ERP

     Contabilidade

     Fiscal

     CFO / Financeiro

     Fisco (arquivos oficiais)

             │

             ▼

     Compliance Engine API

             │

┌─────────────────────────────────────┐

 Compliance Engine Core

──────────────────────────────────────

 Fechamento (reconciliação)

 Obrigações Acessórias

 SPED Fiscal (EFD ICMS/IPI)

 SPED Contribuições (EFD PIS/COFINS)

 SPED Contábil (ECD)

 ECF

 DCTF / DCTFWeb

 REINF / eSocial

 Sintegra

──────────────────────────────────────

             │

      Interfaces (Ports)

──────────────────────────────────────

 Tax Result Provider

 Accounting Books Provider

 Fiscal Totals Provider

 Finance Balances Provider

 Entity Profile Provider

 Event Publisher

 Logger

 Clock

──────────────────────────────────────

             ▲

             │

 Implementações (Adapters)

 ERP

 Banco de Dados

 Arquivos (SPED / DCTF / ECF)

 REST

 JSON

 COBOL

 Microserviços
```

---

# 5. Filosofia

O Compliance Engine nunca consulta diretamente:

* tabelas;
* banco;
* APIs;
* arquivos.

Ele apenas solicita informações através das interfaces definidas.

---

# 6. Responsabilidades

O Compliance Engine deve:

* reconciliar os totais dos motores (fechamento fiscal, contábil e financeiro);
* gerar e validar as obrigações acessórias (SPED Fiscal, SPED Contribuições, SPED Contábil, ECF, DCTF/DCTFWeb, REINF/eSocial, Sintegra);
* apontar divergências entre apuração (Tax), escrituração (Accounting) e movimento (Finance);
* registrar a posição de cada obrigação por período e situação (em dia, pendente, emitida, validada);
* consumir a trilha de eventos (BC-006) como evidência dos fechamentos;
* expor relatórios de conciliação para contabilidade, fiscal, CFO e auditoria.

---

# 7. Não Responsabilidades

O Compliance Engine não deve:

* **calcular tributos** — pertence ao Tax Engine;
* **postar lançamentos contábeis** — pertence ao Accounting Engine;
* **emitir documentos fiscais** (NF-e, NFC-e) — pertence ao Fiscal Engine;
* **decidir mapping financeiro → contábil** — pertence ao Accounting Engine;
* **ser o dono da trilha de auditoria** — ela é transversal (BC-006), não obrigação acessória;
* armazenar cadastros;
* autenticar usuários.

Essas funções pertencem a outros componentes.

---

# 8. Entradas

O motor recebe apenas resultados de apuração, totais e eventos canônicos.

Objetos de domínio.

```text
ComplianceEntity (estabelecimento / regime)

CompliancePeriod (competência)

ComplianceReport (reconciliação)

ObrigacaoDeclaracao (obrigação acessória)

TaxResultSummary (do Tax Engine)

AccountingTotals (do Accounting Engine)

FinanceBalances (do Finance Engine)

FiscalTotals (do Fiscal Engine)
```

Eventos consumidos (RFC-0100, seção 5).

```text
Venda finalizada        → alimenta o fechamento de vendas
Pagamento executado     → alimenta o fechamento financeiro
Apuração do período     → alimenta EFD / ECF / DCTF
Período fechado         → gatilho de validação do fechamento
```

Nunca modelos específicos do ERP.

---

# 9. Saídas

O motor produz declarações, arquivos oficiais e relatórios de conciliação.

```text
ObrigacaoDeclaracao (obrigação acessória)

SPED Fiscal (EFD ICMS/IPI)

SPED Contribuições (EFD PIS/COFINS)

SPED Contábil (ECD)

ECF

DCTF / DCTFWeb

REINF / eSocial

Sintegra

Fechamento (report de reconciliação)

Events:
  fechamento_valido
  fechamento_divergente
  obrigacao_emitida
  obrigacao_validada
```

Nunca objetos do ERP.

---

# 10. Interfaces

Toda dependência externa deve ser abstraída.

Interfaces previstas.

```text
TaxResultProvider

AccountingBooksProvider

FiscalTotalsProvider

FinanceBalancesProvider

EntityProfileProvider

EventPublisher

AuditTrailProvider

ClockProvider

LoggerProvider
```

---

# 11. Sub-domínios

## 11.1 Fechamento (reconciliação)

O coração do Compliance Engine.

```text
Apuração (Tax Engine)

↓

Escrituração (Accounting Engine)

↓

Movimento (Finance Engine)

↓

Conciliação dos totais do período

↓

Fechamento válido / divergente
```

Uma divergência é um evento `fechamento_divergente`, não um erro silencioso.

## 11.2 SPED Fiscal (EFD ICMS/IPI)

- Consome a apuração do Tax Engine (registros C100, C170, C190, C500, D100 etc.).
- Layout por UF, versão e regime (normal / Simples Nacional).

## 11.3 SPED Contribuições (EFD PIS/COFINS)

- Consome a apuração de PIS/COFINS do Tax Engine (cumulativo e não-cumulativo).

## 11.4 SPED Contábil (ECD)

- Consome os livros e saldos do Accounting Engine (razão, diário, balancetes).
- Requer a escrituração contábil digital dos lançamentos.

## 11.5 ECF

- Reconcilia o resultado contábil (ECD/Accounting) com o resultado fiscal (EFD/Tax).
- É a prova final de que contábil e fiscal concordam.

## 11.6 DCTF / DCTFWeb

- Consome os totais apurados e os pagamentos/recolhimentos do período.

## 11.7 REINF / eSocial

- Obrigações acessórias relacionadas a trabalhadores e serviços (retidos, previdência).
- Consumo de fatos da folha e de serviços — sem conhecer as telas de RH.

## 11.8 Sintegra

- Alternativa ao SPED Fiscal onde a UF ainda exige (parcial ou integralmente).

---

# 12. Contrato de Eventos do Compliance

| Evento | Publicado por | Consumido por |
|---|---|---|
| `fechamento_valido` | Compliance Engine | Contabilidade, Fiscal, CFO |
| `fechamento_divergente` | Compliance Engine | Contabilidade, Fiscal, CFO |
| `obrigacao_emitida` | Compliance Engine | Contabilidade, Fiscal |
| `obrigacao_validada` | Compliance Engine | Contabilidade, Fiscal |

Regras:

- eventos são imutáveis após publicados;
- correções geram novos eventos (reversão + novo fato);
- o Compliance nunca corrige o fato na origem — ele apenas sinaliza a divergência e indica o motor de origem.

---

# 13. O Fechamento como Critério de Aceite

Qualquer mudança em Fiscal, Tax, Finance ou Accounting só passa se o fechamento continuar conciliando.

```text
EFD (apuração)  ==  ECD/ECF (escrituração)  ==  Caixa (Finance)
```

Exemplo de reconciliação de um período:

```text
Vendas brutas do período           100.000,00

ICMS apurado (Tax)                  17.000,00  → EFD C190
PIS/COFINS apurados (Tax)            3.650,00  → EFD Contribuições
Receita líquida contábil            79.350,00  → ECD
Saldo bancos/caixa (Finance)        79.350,00  → fechamento financeiro
```

Se algum desses totais não fechar, a mudança que o causou é rejeitada no fluxo de desenvolvimento — **a reconciliação é o critério de aceite da evolução dos motores**.

---

# 14. Auditoria Transversal (fora do escopo)

Auditoria é uma capacidade transversal da plataforma (trilha de eventos BC-006), **não** uma obrigação acessória.

O Compliance Engine:

* **consome** a trilha como evidência do fechamento (quem publicou o quê, quando);
* **não é dono** da trilha;
* não implementa auditoria interna por conta própria — isso pertence à plataforma.

A separação evita duplicidade: o Compliance declara, a plataforma prova.

---

# 15. Relação com os Outros Motores

O Compliance é o único componente que enxerga a saída de todos os motores ao mesmo tempo.

```text
Fiscal Engine  → totais dos documentos
Tax Engine     → apuração (impostos por período)
Accounting     → lançamentos e saldos
Finance        → caixa, bancos, títulos
      │
      ▼
Compliance Engine → reconcilia e declara
```

Nenhum outro motor depende do Compliance.

---

# 16. Performance

Metas.

Reconciliação de um período (fechamento):

< 2 s

Geração de SPED Fiscal (competência completa):

< 30 s

Validação de ECF (resultado contábil × fiscal):

< 5 s

---

# 17. Observabilidade

Métricas.

* fechamentos válidos / divergentes por período;
* posição das obrigações acessórias (em dia, pendente, emitida, validada);
* tempo de geração de cada SPED/ECF/DCTF;
* divergências por motor de origem;
* ordem de grandeza dos totais reconciliados.

---

# 18. Compatibilidade

Implementações previstas.

* Python
* COBOL
* REST
* gRPC
* CLI
* Docker

Todas compartilham o mesmo núcleo lógico.

---

# 19. Roadmap

## Sprint CP-01 ✅

Arquitetura — **concluído**: `compliance_engine.py`.

Interfaces — **concluído**: Providers (`tax_apuracao_periodo`, `accounting_totais_periodo`, `finance_recebimentos_periodo`).

Contrato de fechamento (reconciliação) — **concluído**: `fechamento(ano, mes)` reconcilia apuração × provisionado × caixa; emite `fechamento_valido` / `fechamento_divergente`; exposto em `/api/compliance/fechamento`, `/api/compliance/fechamentos`, `/api/compliance/status`.

---

## Sprint CP-02 ✅

Fechamento: apuração (Tax) × escrituração (Accounting) — **concluído**:

- **Créditos de entrada**: `_creditos_da_entrada` (ICMS/PIS/COFINS a recuperar) derivados dos totais da NF-e de entrada (`rec.nfe.total.vICMS/vPIS/vCOFINS`); `on_receiving_complete` incorpora os créditos na compra (débito estoque líquido + débito tributos a recuperar × crédito fornecedor) via `creditos` do Posting Engine (`TAX_RECUPERAR_ACCOUNTS`).
- **Apuração com débitos − créditos**: `tax_apuracao_periodo` retorna `debitos`, `creditos` (entradas do período em `nfe_entrada.json`) e `saldo_a_recolher` por imposto.
- **Provisionado com recuperação**: `accounting_totais_periodo` lê também o débito em `TAX_RECUPERAR_ACCOUNTS` e expõe `saldo_a_recolher` provisionado (= recolher − recuperar).
- **Checagem**: "saldo a recolher (apurado × provisionado)" por imposto; regra de receita bruta e caixa mantidas.
- **Validação**: `scripts/smoke_compliance_e2e.py` agora inclui recebimento com NF-e de entrada (vICMS 34/vPIS 3/vCOFINS 10), confere débito em `1.01.02.03.02` (ICMS a Recuperar) e fechamento `valido` com saldo icms 17.00 (51 débito − 34 crédito).

---

## Sprint CP-03

Fechamento financeiro: caixa/bancos (Finance) × escrituração (Accounting).

---

## Sprint CP-04

SPED Fiscal (EFD ICMS/IPI).

SPED Contribuições (EFD PIS/COFINS).

---

## Sprint CP-05

SPED Contábil (ECD).

ECF.

---

## Sprint CP-06

DCTF / DCTFWeb.

REINF / eSocial.

Sintegra.

---

# 20. Objetivo Final

O Compliance Engine deve ser capaz de provar que a plataforma está fiscal, contábil e financeiramente correta — sem calcular, sem postar e sem emitir nada. Ele é o motor do fechamento: a última linha de defesa entre o fato de negócio e o fisco.
