# Business Platform
# BC-004A — Catálogo Universal de Tipos de Dados de Negócio

**Documento:** BC-004A
**Título:** Catálogo Universal de Tipos de Dados de Negócio
**Versão:** 2.0.0 (Draft)
**Dependências:** BC-004 (Value Objects)

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

## Capítulo 1 — Objetivo

Este documento define os **Business Data Types (BDT)** da plataforma.

Um *Business Data Type* representa um tipo semântico utilizado pelo domínio empresarial.

Ele é independente de:

- Linguagem
- Banco de Dados
- Framework
- Sistema Operacional
- API
- Interface

O BusinessCore nunca utiliza tipos primitivos diretamente na modelagem conceitual.

---

## Capítulo 2 — Filosofia

**Errado:**
```
Customer
  Name     : string
  Age      : integer
  Price    : decimal
```

**Correto:**
```
Customer
  Name        : BusinessName
  BirthDate   : BusinessDate
  CreditLimit : MonetaryAmount
```

O significado passa a ser explícito.

---

## Capítulo 3 — Estrutura de um Tipo

Todo Business Data Type possui:

```
BusinessDataType
├── Identifier
├── Name
├── Description
├── Category
├── PrimitiveMapping
├── ValidationRules
├── FormattingRules
├── SerializationRules
└── Version
```

---

## Capítulo 4 — Categorias

Os tipos são organizados por categorias:

```
Identity
Text
Numeric
Temporal
Financial
Measurement
Reference
Localization
Communication
Classification
Media
Security
Metadata
```

---

## Capítulo 5 — Tipos de Identidade

```
BusinessIdentifier
BusinessCode
BusinessReference
BusinessUUID
BusinessVersion
```

**Descrição:** Representam identificadores do domínio. Nunca possuem significado de negócio. São imutáveis.

---

## Capítulo 6 — Tipos Textuais

```
BusinessName
BusinessTitle
BusinessDescription
BusinessLabel
BusinessNote
BusinessComment
BusinessKeyword
```

Todos possuem regras próprias de tamanho, normalização e internacionalização.

---

## Capítulo 7 — Tipos Numéricos

```
BusinessInteger
BusinessDecimal
BusinessPercentage
BusinessRatio
BusinessSequence
BusinessPriority
```

Não representam dinheiro.

---

## Capítulo 8 — Tipos Financeiros

```
MonetaryAmount
CurrencyCode
ExchangeRate
TaxRate
DiscountRate
```

O tipo `MonetaryAmount` sempre contém:

- Value
- Currency
- Precision
- RoundingPolicy

O BusinessCore não realiza cálculos tributários ou contábeis.

---

## Capítulo 9 — Tipos Temporais

```
BusinessDate
BusinessTime
BusinessTimestamp
BusinessPeriod
BusinessDuration
```

Esses tipos são independentes de fuso horário e formato de armazenamento.

---

## Capítulo 10 — Tipos de Medida

```
BusinessQuantity
BusinessWeight
BusinessVolume
BusinessLength
BusinessArea
BusinessTemperature
BusinessDistance
```

Sempre acompanhados de uma unidade de medida.

---

## Capítulo 11 — Tipos de Comunicação

```
EmailAddress
PhoneNumber
WebsiteURL
IPAddress
CommunicationChannel
```

A validação específica de cada país ou padrão fica a cargo de serviços especializados.

---

## Capítulo 12 — Tipos de Localização

```
Address
CountryCode
RegionCode
CityName
PostalCode
GeoCoordinate
```

O BusinessCore define apenas a estrutura conceitual.

---

## Capítulo 13 — Tipos de Classificação

```
BusinessCategory
BusinessClassification
BusinessTag
BusinessStatus
BusinessRole
BusinessType
```

Esses tipos permitem categorizar entidades sem alterar sua estrutura.

---

## Capítulo 14 — Tipos de Referência

```
DocumentReference
EntityReference
ExternalReference
IntegrationReference
WorkflowReference
```

São utilizados para relacionar objetos do domínio.

---

## Capítulo 15 — Tipos de Mídia

```
ImageReference
FileReference
DocumentAttachment
BinaryContentReference
```

O BusinessCore não define onde os arquivos são armazenados.

---

## Capítulo 16 — Tipos de Segurança

```
DigitalSignature
HashValue
Checksum
SecurityToken
PermissionIdentifier
```

São utilizados para garantir autenticidade e integridade.

---

## Capítulo 17 — Tipos de Metadados

```
MetadataCollection
CustomAttribute
ExtensionValue
BusinessProperty
ConfigurationValue
```

Permitem extensibilidade sem modificar o modelo canônico.

---

## Capítulo 18 — Catálogo Consolidado

```
BusinessIdentifier
BusinessCode
BusinessReference
BusinessUUID
BusinessVersion

BusinessName
BusinessTitle
BusinessDescription
BusinessLabel
BusinessComment

BusinessInteger
BusinessDecimal
BusinessPercentage
BusinessRatio

MonetaryAmount
CurrencyCode
ExchangeRate

BusinessDate
BusinessTime
BusinessTimestamp
BusinessPeriod

BusinessQuantity
BusinessWeight
BusinessVolume
BusinessLength

Address
CountryCode
RegionCode
CityName
PostalCode

PhoneNumber
EmailAddress
WebsiteURL

DocumentReference
EntityReference
ExternalReference

ImageReference
FileReference

BusinessStatus
BusinessCategory
BusinessRole

MetadataCollection
CustomAttribute
ExtensionValue
```

---

## Capítulo 19 — Mapeamento Tecnológico

O Business Data Type é independente da implementação.

| Business Data Type | PostgreSQL | Python | COBOL |
|-------------------|------------|--------|-------|
| `BusinessIdentifier` | `UUID` | `UUID` | `CHAR(36)` |
| `BusinessName` | `VARCHAR` | `str` | `PIC X(200)` |
| `MonetaryAmount` | `NUMERIC(18,6)` | `Decimal` | `PIC S9(13)V9(6) COMP-3` |
| `BusinessDate` | `DATE` | `date` | `PIC 9(8)` |
| `BusinessTimestamp` | `TIMESTAMP` | `datetime` | `TIMESTAMP` |
| `BusinessQuantity` | `NUMERIC(18,6)` | `Decimal` | `PIC S9(13)V9(6) COMP-3` |
| `BusinessStatus` | `SMALLINT/VARCHAR` | `Enum` | `PIC X(20)` |

Essa tabela é apenas um exemplo de implementação; o modelo conceitual continua independente.

---

## Capítulo 20 — Benefícios

A adoção de Business Data Types proporciona:

- Linguagem uniforme em toda a plataforma
- Independência tecnológica
- Reutilização entre motores
- Padronização de validações
- Facilidade de integração
- Melhor documentação
- Evolução controlada do domínio

---

## Arquitetura Conceitual

```
BusinessCore
│
├── Ontologia
├── Modelo Canônico
├── Entidades
├── Value Objects
└── Business Data Types
        ├── BusinessName
        ├── MonetaryAmount
        ├── BusinessDate
        ├── Address
        ├── BusinessStatus
        ├── EntityReference
        └── MetadataCollection
```

Os Business Data Types tornam-se a base sobre a qual são construídos os Value Objects, que por sua vez compõem as Entidades e Agregados.

---

**Arquivo:** `docs/BC-004A_DATA_TYPES.md`
**Versão:** 2.0.0
**Data:** 2026-07-25
