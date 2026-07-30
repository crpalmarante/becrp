# RFC-FISCAL-ENGINE-ARCHITECTURE.md

**Status:** Draft

**RFC:** 0030

**Categoria:** Fiscal Engine

**Módulo:** Fiscal Engine Core

**Prioridade:** Arquitetura Fundamental

**Versão:** 1.0

**Dependências:**

* RFC-BUSINESS-REFERENCE-COMPONENT.md
* RFC-BUSINESS-PARTNER-MODEL.md

**Dependências Futuras:**

* RFC-FISCAL-ENGINE-API.md
* RFC-FISCAL-ENGINE-RESOLVER.md
* RFC-FISCAL-RULE-ENGINE.md
* RFC-FISCAL-CALCULATION-PIPELINE.md

---

# 1. Objetivo

Definir a arquitetura oficial do Fiscal Engine.

O Fiscal Engine é um componente independente responsável por interpretar regras tributárias, calcular tributos, validar operações fiscais e produzir informações utilizadas por documentos fiscais.

Ele não pertence ao ERP.

Ele pode ser utilizado por qualquer aplicação.

---

# 2. Visão

O Fiscal Engine deve funcionar como uma biblioteca ou serviço.

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

     Fiscal Engine API

             │

┌─────────────────────────────────────┐

 Fiscal Engine Core

──────────────────────────────────────

 Rule Engine

 Calculation Engine

 Validation Engine

 Simulation Engine

 Document Model

 Audit Engine

──────────────────────────────────────

             │

      Interfaces (Ports)

──────────────────────────────────────

 Reference Resolver

 Rule Provider

 Tax Provider

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

O Fiscal Engine nunca consulta diretamente:

* tabelas;
* banco;
* APIs;
* arquivos.

Ele apenas solicita informações através das interfaces definidas.

---

# 6. Responsabilidades

O Fiscal Engine deve:

* calcular tributos;
* validar regras fiscais;
* determinar bases de cálculo;
* aplicar benefícios fiscais;
* produzir memória de cálculo;
* simular cenários;
* gerar eventos fiscais;
* validar consistência.

---

# 7. Não Responsabilidades

O Fiscal Engine não deve:

* emitir NF-e;
* transmitir documentos;
* acessar SEFAZ;
* armazenar cadastros;
* consultar banco;
* autenticar usuários;
* controlar permissões;
* imprimir DANFE.

Essas funções pertencem a outros componentes.

---

# 8. Entradas

O motor recebe apenas objetos de domínio.

Exemplo.

```text
FiscalContext

FiscalOperation

FiscalPartner

FiscalCompany

FiscalItem
```

Nunca modelos específicos do ERP.

---

# 9. Saídas

O motor produz.

```text
FiscalCalculation

FiscalResult

TaxBreakdown

Messages

Warnings

Errors

AuditTrail
```

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

O Fiscal Engine desconhece a origem dessas informações.

---

# 12. Rule Provider

Fornece regras tributárias.

Exemplos.

* ICMS
* IPI
* PIS
* COFINS
* IBS
* CBS
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

Toda decisão fiscal deve ser auditável.

Registrar.

* regra utilizada;
* versão;
* parâmetros;
* memória de cálculo;
* horário;
* origem.

---

# 19. Extensibilidade

Novos tributos podem ser adicionados sem alterar o núcleo.

Exemplos.

* imposto ambiental;
* tributos municipais;
* taxas estaduais.

---

# 20. Performance

Metas.

Cálculo de item:

< 2 ms

Documento com 100 itens:

< 250 ms

Simulação:

< 500 ms

---

# 21. Observabilidade

Métricas.

* tempo por etapa;
* cache hit;
* cache miss;
* regras carregadas;
* validações executadas;
* erros;
* avisos.

---

# 22. Compatibilidade

Implementações previstas.

* Python
* COBOL
* REST
* gRPC
* CLI
* Docker

Todas compartilham o mesmo núcleo lógico.

---

# 23. Roadmap

## Sprint FE-01

Arquitetura.

Interfaces.

Modelos básicos.

---

## Sprint FE-02

Reference Resolver.

Calculation Pipeline.

Rule Engine.

---

## Sprint FE-03

ICMS.

IPI.

PIS.

COFINS.

---

## Sprint FE-04

IBS.

CBS.

Benefícios Fiscais.

---

## Sprint FE-05

Document Model.

Simulation.

Audit.

---

# 24. Objetivo Final

O Fiscal Engine deve ser capaz de ser utilizado por qualquer sistema, independentemente de sua tecnologia.

Ele deve ser distribuído como um componente independente, consumindo apenas interfaces públicas e objetos de domínio, sem dependência direta de bancos de dados, frameworks ou implementações específicas de ERP.
