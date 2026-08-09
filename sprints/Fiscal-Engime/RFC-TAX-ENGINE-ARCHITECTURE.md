# RFC-TAX-ENGINE-ARCHITECTURE.md

**Status:** Draft

**RFC:** 0040

**Categoria:** Tax Engine

**Módulo:** Tax Engine Core

**Prioridade:** Arquitetura Fundamental

**Versão:** 1.0

**Dependências:**

* RFC-0100 (Arquitetura dos Motores Centrais)
* RFC-BUSINESS-REFERENCE-COMPONENT.md
* RFC-BUSINESS-PARTNER-MODEL.md

**Dependências Futuras:**

* RFC-TAX-ENGINE-API.md
* RFC-TAX-ENGINE-RESOLVER.md
* RFC-TAX-RULE-ENGINE.md
* RFC-TAX-CALCULATION-PIPELINE.md

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

Definir a arquitetura oficial do Tax Engine.

O Tax Engine é o **único componente da plataforma que calcula tributos**. Ele recebe o contexto da operação e produz o bloco "tributos calculados" (TaxBreakdown), consumido por:

- **Fiscal Engine** (RFC-0030) — montagem do documento fiscal;
- **Accounting Engine** (RFC-8000 a 8009) — posting (ICMS a recolher, PIS a recuperar, etc.);
- **Compliance Engine** — apuração e obrigações acessórias.

Ele não pertence ao ERP.

Ele pode ser utilizado por qualquer aplicação.

> **Origem:** esta RFC absorve o núcleo de cálculo tributário que estava na RFC-0030 (Fiscal Engine), após a separação de responsabilidades definida na RFC-0100.

---

# 2. Visão

O Tax Engine deve funcionar como uma biblioteca ou serviço.

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

É o único componente que calcula tributos. Nenhum outro componente recalcula.

---

## P10

Toda decisão tributária é auditável (memória de cálculo + trilha de eventos, BC-006).

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

     Tax Engine API

             │

┌─────────────────────────────────────┐

 Tax Engine Core

──────────────────────────────────────

 Rule Engine

 Calculation Engine

 Validation Engine

 Simulation Engine

 TaxBreakdown Model

 Audit Engine

──────────────────────────────────────

             │

      Interfaces (Ports)

──────────────────────────────────────

 Reference Resolver

 Rule Provider

 Fiscal Configuration Provider

 Event Publisher

 Logger

 Clock

──────────────────────────────────────

             ▲

             │

 Implementações (Adapters)

 ERP

 XML

 REST

 JSON

 Banco de Dados

 Arquivos

 Cache

 Microserviços
```

---

# 5. Filosofia

O Tax Engine nunca consulta diretamente:

* tabelas;
* banco;
* APIs;
* arquivos.

Ele apenas solicita informações através das interfaces definidas.

---

# 6. Responsabilidades

O Tax Engine deve:

* calcular tributos (ICMS, ICMS-ST, FCP, DIFAL, FECP, IPI, PIS, COFINS, ISS, IBS, CBS, Imposto de Importação, retenções);
* interpretar regras tributárias;
* determinar bases de cálculo;
* aplicar benefícios fiscais;
* produzir memória de cálculo;
* simular cenários;
* gerar eventos fiscais de apuração;
* validar consistência.

---

# 7. Não Responsabilidades

O Tax Engine não deve:

* emitir NF-e ou qualquer documento fiscal;
* transmitir documentos ou acessar SEFAZ;
* montar XML/DANFE;
* emitir lançamentos contábeis;
* gerar títulos financeiros;
* armazenar cadastros;
* autenticar usuários.

Essas funções pertencem a outros componentes.

---

# 8. Entradas

O motor recebe apenas objetos de domínio.

Exemplo.

```text
TaxContext

TaxOperation

TaxPartner

TaxCompany

TaxItem
```

Nunca modelos específicos do ERP.

---

# 9. Saídas

O motor produz.

```text
TaxCalculation

TaxBreakdown

TaxResult

Messages

Warnings

Errors

AuditTrail
```

O bloco **TaxBreakdown** é o contrato consumido por Fiscal, Accounting e Compliance (RFC-0100).

Nunca objetos do ERP.

---

# 10. Interfaces

Toda dependência externa deve ser abstraída.

Interfaces previstas.

```text
ReferenceResolver

TaxRuleProvider

FiscalConfigurationProvider

EventPublisher

AuditProvider

ClockProvider

LoggerProvider
```

---

# 11. Reference Resolver

Responsável por localizar informações necessárias ao cálculo.

Exemplos.

```text
resolver.resolveNCM()

resolver.resolveCEST()

resolver.resolveCFOP()

resolver.resolveOperation()

resolver.resolvePartner()

resolver.resolveCompany()
```

O Tax Engine desconhece a origem dessas informações.

---

# 12. Rule Provider

Fornece regras tributárias.

Exemplos.

* ICMS
* ICMS-ST
* FCP
* IPI
* PIS
* COFINS
* ISS
* IBS
* CBS
* Imposto de Importação
* Retenções
* Benefícios Fiscais

As regras podem estar em:

* banco;
* arquivo;
* serviço remoto;
* cache;
* memória.

---

# 13. Calculation Pipeline

O cálculo ocorre em etapas.

```text
Validação

↓

Resolução de referências

↓

Identificação da operação

↓

Carregamento das regras

↓

Determinação da tributação

↓

Cálculo

↓

Validação

↓

Resultado
```

Cada etapa é isolada.

---

# 14. Rule Engine

Responsável apenas por interpretar regras.

Não realiza cálculos diretamente.

---

# 15. Calculation Engine

Executa os cálculos matemáticos.

Responsável por:

* bases;
* alíquotas;
* reduções;
* arredondamentos;
* totais.

---

# 16. Validation Engine

Executa validações.

Exemplos.

* NCM inexistente.
* CEST incompatível.
* CFOP inválido.
* CST incompatível.
* Benefício vencido.

---

# 17. Simulation Engine

Permite simulações.

Exemplo.

```text
Trocar NCM

↓

Novo ICMS

↓

Novo IBS

↓

Nova CBS
```

Sem alterar documentos.

---

# 18. Audit Engine

Toda decisão tributária deve ser auditável.

Registrar.

* regra utilizada;
* versão;
* parâmetros;
* memória de cálculo;
* horário;
* origem.

---

# 19. TaxBreakdown (contrato)

Bloco de saída com a projeção tributária da operação.

```text
Por tributo:
  base de cálculo
  alíquota efetiva
  valor
  CST / origem
  retenção
Totais por tributo e geral
```

É este bloco que garante a paridade entre o documento fiscal, o lançamento contábil e a apuração (RFC-0100, seção 6).

---

# 20. Extensibilidade

Novos tributos podem ser adicionados sem alterar o núcleo.

Exemplos.

* imposto ambiental;
* tributos municipais;
* taxas estaduais.

---

# 21. Performance

Metas.

Cálculo de item:

< 2 ms

Documento com 100 itens:

< 250 ms

Simulação:

< 500 ms

---

# 22. Observabilidade

Métricas.

* tempo por etapa;
* cache hit;
* cache miss;
* regras carregadas;
* validações executadas;
* erros;
* avisos.

---

# 23. Compatibilidade

Implementações previstas.

* Python
* COBOL
* REST
* gRPC
* CLI
* Docker

Todas compartilham o mesmo núcleo lógico.

---

# 24. Roadmap

## Sprint TX-01

Arquitetura.

Interfaces.

Modelos básicos.

---

## Sprint TX-02

Reference Resolver.

Calculation Pipeline.

Rule Engine.

---

## Sprint TX-03

ICMS.

IPI.

PIS.

COFINS.

---

## Sprint TX-04

IBS.

CBS.

Benefícios Fiscais.

---

## Sprint TX-05

TaxBreakdown.

Simulation.

Audit.

---

# 25. Objetivo Final

O Tax Engine deve ser capaz de ser utilizado por qualquer sistema, independentemente de sua tecnologia.

Ele deve ser distribuído como um componente independente, consumindo apenas interfaces públicas e objetos de domínio, e produzindo o TaxBreakdown como contrato único para Fiscal, Accounting e Compliance — sem dependência direta de bancos de dados, frameworks ou implementações específicas de ERP.
