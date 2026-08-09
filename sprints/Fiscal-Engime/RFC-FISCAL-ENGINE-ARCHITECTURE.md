# RFC-FISCAL-ENGINE-ARCHITECTURE.md

**Status:** Draft

**RFC:** 0030

**Categoria:** Fiscal Engine

**Módulo:** Fiscal Engine Core

**Prioridade:** Arquitetura Fundamental

**Versão:** 2.0

**Dependências:**

* RFC-BUSINESS-REFERENCE-COMPONENT.md
* RFC-BUSINESS-PARTNER-MODEL.md
* RFC-0040 (Tax Engine)

**Dependências Futuras:**

* RFC-FISCAL-ENGINE-API.md
* RFC-FISCAL-ENGINE-DOCUMENT-BUILDER.md
* RFC-FISCAL-ENGINE-TRANSMISSION.md
* RFC-FISCAL-ENGINE-EVENTS.md

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

Definir a arquitetura oficial do Fiscal Engine.

O Fiscal Engine é um componente independente responsável pelo **ciclo de vida do documento fiscal**: montagem, assinatura, transmissão, retorno, contingência e eventos.

Ele **nunca calcula tributos**. O cálculo é responsabilidade exclusiva do Tax Engine (RFC-0040), cuja saída (bloco "tributos calculados") é consumida pelo Fiscal Engine para montar o documento.

Ele não pertence ao ERP.

Ele pode ser utilizado por qualquer aplicação.

> **Nota de versão:** a versão 2.0 separa as responsabilidades que antes estavam misturadas. Todo o conteúdo de cálculo tributário migrou para a RFC-0040 (Tax Engine).

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

## P9

Nunca calcula tributos. Consome o bloco "tributos calculados" do Tax Engine (RFC-0040).

---

## P10

Toda operação documental é auditável (trilha de eventos, BC-006).

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

 Document Builder

 Signer

 Transmission Engine

 Receipt / Return Processor

 Contingency Engine

 Event Registry

 Status / Tracking

──────────────────────────────────────

             │

      Interfaces (Ports)

──────────────────────────────────────

 Tax Result Provider     (Tax Engine)

 Certificate Provider

 SEFAZ / Portal Provider

 Reference Resolver

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

 SEFAZ (WebServices)

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

* montar o documento fiscal (NF-e, NFC-e, CT-e, MDF-e, NFS-e, SAT, CF-e);
* assinar digitalmente o documento (certificado digital);
* transmitir e processar o retorno (autorização, denegação, contingência);
* gerenciar eventos: cancelamento, carta de correção, inutilização, manifestação;
* manter o rastreamento de status do documento;
* operar em contingência (offline → retransmissão);
* validar consistência estrutural do documento;
* registrar trilha de auditoria de cada operação.

---

# 7. Não Responsabilidades

O Fiscal Engine não deve:

* **calcular tributos** (responsabilidade do Tax Engine, RFC-0040);
* decidir regra tributária ou benefício fiscal;
* emitir lançamentos contábeis;
* gerar títulos financeiros;
* armazenar cadastros;
* autenticar usuários;
* controlar permissões.

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

TaxBreakdown      → bloco de tributos calculados (Tax Engine)
```

Nunca modelos específicos do ERP.

---

# 9. Saídas

O motor produz.

```text
FiscalDocument

FiscalDocumentStatus

AuthorizationResult

EventResult (cancelamento, CCe, inutilização, manifestação)

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
TaxResultProvider

CertificateProvider

SEFAZProvider

ReferenceResolver

FiscalConfigurationProvider

EventPublisher

AuditProvider

ClockProvider

LoggerProvider
```

---

# 11. Tax Result Provider

Consome a saída do Tax Engine (RFC-0040).

O Fiscal Engine solicita e recebe o bloco "tributos calculados" para o documento e o incorpora ao XML sem re-calcular.

O Fiscal Engine desconhece como o tributo foi calculado.

---

# 12. Certificate Provider

Fornece o certificado digital.

Responsável por:

* localizar o certificado por estabelecimento;
* validar vigência e senha;
* fornecer a chave para assinatura.

---

# 13. SEFAZ Provider

Abstrai os WebServices de autorização e recepção de eventos.

```text
autorizarDocumento()

consultarStatus()

consultarRecibo()

recepcionarEvento()

inutilizarNumeracao()
```

O Fiscal Engine desconhece o transportador (SEFAZ, Portal, integrador).

---

# 14. Document Builder

Monta o documento fiscal a partir do objeto de domínio e do bloco de tributos.

Etapas.

```text
Montagem da estrutura

↓

Inclusão dos tributos (TaxBreakdown)

↓

Serialização (XML / DFe)

↓

Assinatura

↓

Validação estrutural
```

---

# 15. Transmission Engine

Executa a transmissão.

```text
Enviar

↓

Aguardar recibo

↓

Consultar resultado

↓

Autorizado / Denegado / Contingência
```

---

# 16. Receipt / Return Processor

Processa o retorno do fisco.

* protocolo de autorização;
* mensagens (cStat, xMotivo);
* rejeições;
* contingência.

---

# 17. Contingency Engine

Opera quando a autorização não é possível.

```text
Offline (EPEC / FS-DA)

↓

Autorização posterior

↓

Retransmissão / validação
```

---

# 18. Event Registry

Gerencia eventos do documento.

* cancelamento;
* carta de correção;
* inutilização;
* manifestação do destinatário.

Cada evento é um registro de auditoria imutável.

---

# 19. Status / Tracking

Mantém o estado do documento ao longo do ciclo.

```text
Rascunho

→ Em validação

→ Assinado

→ Transmitido

→ Autorizado / Denegado / Contingência

→ Cancelado / Substituído
```

---

# 20. Performance

Metas.

Montagem de documento com 100 itens:

< 150 ms

Transmissão + processamento de retorno:

< 2 s

Evento (cancelamento, CCe):

< 500 ms

---

# 21. Observabilidade

Métricas.

* tempo por etapa;
* transmissões por status;
* erros e rejeições por motivo;
* tempo de contingência;
* certificados expirados.

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

## Sprint FD-01

Arquitetura.

Interfaces.

Modelos básicos.

---

## Sprint FD-02

Document Builder.

Signer.

Validação estrutural.

---

## Sprint FD-03

Transmission Engine.

Receipt / Return Processor.

---

## Sprint FD-04

Event Registry (cancelamento, CCe, inutilização, manifestação).

---

## Sprint FD-05

Contingency Engine.

Status / Tracking.

Audit.

---

# 24. Objetivo Final

O Fiscal Engine deve ser capaz de ser utilizado por qualquer sistema, independentemente de sua tecnologia.

Ele deve ser distribuído como um componente independente, consumindo apenas interfaces públicas e objetos de domínio, sem dependência direta de bancos de dados, frameworks ou implementações específicas de ERP — e sem jamais calcular tributos, que é responsabilidade do Tax Engine (RFC-0040).
