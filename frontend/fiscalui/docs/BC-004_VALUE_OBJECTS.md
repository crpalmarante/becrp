# Business Platform
# BC-004 — Value Objects (Objetos de Valor)

**Documento:** BC-004
**Título:** Objetos de Valor do BusinessCore
**Versão:** 1.0.0 (Draft)
**Dependências:** BC-003 (Entidades)

---

## Capítulo 1 — Objetivo

Definir todos os Objetos de Valor (Value Objects) utilizados pelo BusinessCore.

Um Value Object representa um conceito do domínio que:

- não possui identidade própria;
- é definido apenas pelos seus valores;
- é imutável;
- pode ser reutilizado em diversas entidades.

---

## Capítulo 2 — O que é um Value Object?

Diferente de uma entidade, um Value Object não possui identidade.

Exemplo:

**Endereço:** Rua A, Número 100, Cidade X. Se outro endereço possuir exatamente os mesmos valores, ambos são considerados equivalentes. Não importa "quem" ele é. Importa "o que" ele representa.

---

## Capítulo 3 — Diferença entre Entidade e Value Object

```
ENTIDADE                            VALUE OBJECT
───────                             ────────────
Cliente                             Endereço
  ID = 100                            Rua A
  Nome = João                         Número 100
                                      Cidade X
Mesmo alterando o nome,            Se qualquer informação mudar,
continua sendo o mesmo cliente.    é considerado um novo objeto.
```

---

## Capítulo 4 — Princípios

Todo Value Object deve obedecer às seguintes regras:

- Imutável
- Comparado por valor
- Sem identidade
- Sem ciclo de vida
- Sem histórico próprio
- Reutilizável

---

## Capítulo 5 — Catálogo Oficial

O BusinessCore possuirá um catálogo oficial de Value Objects:

```
Address
Phone
Email
Website
Money
Quantity
Percentage
Weight
Volume
Dimension
Coordinate
GeoLocation
Period
DateRange
TimeRange
Duration
Currency
Language
Country
Region
City
PostalCode
Identifier
DocumentNumber
PersonName
CompanyName
Color
ImageReference
FileReference
Barcode
QRCode
Measurement
Temperature
Distance
```

---

## Capítulo 6 — Address

Representa um endereço.

```
Address
├── Street
├── Number
├── Complement
├── District
├── City
├── Region
├── Country
└── PostalCode
```

O BusinessCore conhece apenas o conceito. CEP é apenas um código postal. Não há validação específica de países neste nível.

---

## Capítulo 7 — PersonName

Representa um nome completo.

```
PersonName
├── Prefix
├── GivenName
├── MiddleName
├── FamilyName
├── Suffix
└── DisplayName
```

Evita utilizar apenas um campo "Nome".

---

## Capítulo 8 — Money

O dinheiro é um Value Object. Nunca um número simples.

```
Money
├── Amount
├── Currency
└── Precision
```

Exemplo: `{ Amount: 100.00, Currency: BRL }` ou `{ Amount: 250.50, Currency: USD }`.

O BusinessCore não faz conversão cambial.

---

## Capítulo 9 — Quantity

Representa quantidades.

```
Quantity
├── Value
└── UnitOfMeasure
```

Exemplos: `10 UN`, `25 KG`, `15 L`.

---

## Capítulo 10 — Measurement

Medições físicas.

```
Measurement
├── Length
├── Width
├── Height
├── Area
├── Volume
└── Weight
```

---

## Capítulo 11 — Period

Representa intervalos de tempo.

```
Period
├── StartDate
└── EndDate
```

Utilizado em: contratos, promoções, vigências, projetos.

---

## Capítulo 12 — GeoLocation

```
GeoLocation
├── Latitude
├── Longitude
└── Altitude
```

Independente de provedores de mapas.

---

## Capítulo 13 — Identifier

Representa identificadores genéricos.

```
Identifier
├── Type
└── Value
```

Exemplos: Código Interno, Código Externo, Código ERP, Código Legado.

> CPF e CNPJ não pertencem ao BusinessCore. São especializações do FiscalCore para o contexto brasileiro.

---

## Capítulo 14 — Currency

Representa moedas.

```
Currency
├── ISOCode
├── Name
├── Symbol
└── DecimalPlaces
```

Exemplo: `{ ISOCode: BRL, Name: "Real Brasileiro", Symbol: "R$", DecimalPlaces: 2 }`.

---

## Capítulo 15 — FileReference

Representa arquivos.

```
FileReference
├── Identifier
├── FileName
├── MimeType
├── Size
├── Checksum
└── Location
```

Sem definir onde o arquivo está armazenado.

---

## Capítulo 16 — Relações

```
Party
  ├── Address
  ├── Phone
  ├── Email
  └── Money
```

As entidades utilizam Value Objects. Nunca o contrário.

---

## Capítulo 17 — Compartilhamento

O mesmo `Address` pode ser utilizado por Cliente, Fornecedor, Empresa, Filial, Transportadora.

O mesmo `Money` pode ser utilizado por Pedido, Produto, Contrato, Projeto, Nota de Pagamento.

---

## Capítulo 18 — Especializações

Os motores especializados podem ampliar um Value Object.

```
Money (BusinessCore)
  ├── FiscalMoney (FiscalCore — impostos, base de cálculo)
  └── AccountingMoney (AccountingCore — partidas, saldos)
```

O BusinessCore continua conhecendo apenas `Money`.

---

## Capítulo 19 — Benefícios

Essa abordagem oferece:

- reutilização;
- padronização;
- redução de duplicidade;
- maior consistência;
- testes simplificados;
- evolução controlada.

---

## Capítulo 20 — Arquitetura Geral

```
BusinessEntity
│
├── Party
│     ├── PersonName
│     ├── Address
│     ├── Phone
│     └── Email
│
├── Product
│     ├── Money
│     ├── Quantity
│     ├── Measurement
│     └── Dimension
│
├── Contract
│     ├── Period
│     ├── Money
│     └── DocumentReference
│
└── Project
      ├── Period
      ├── Budget (Money)
      └── Location
```

---

## Evolução da Arquitetura

```
BC-000  Manifesto
  │
  ▼
BC-001  Ontologia Empresarial
  │
  ▼
BC-002  Modelo Canônico
  │
  ▼
BC-003  Entidades
  │
  ▼
BC-004  Value Objects           ← estamos aqui
  │
  ▼
BC-005  Agregados
  │
  ▼
BC-006  Eventos
  │
  ▼
BC-007  Serviços de Domínio
```

---

**Arquivo:** `docs/BC-004_VALUE_OBJECTS.md`
**Versão:** 1.0.0
**Data:** 2026-07-25
