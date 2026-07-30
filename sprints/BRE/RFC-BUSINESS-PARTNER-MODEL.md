# RFC-BUSINESS-PARTNER-MODEL.md

**Status:** Draft

**RFC:** 0020

**Categoria:** Business Core

**Módulo:** Business Partner (BP)

**Prioridade:** Arquitetura Fundamental

**Versão:** 1.0

**Dependências:**

* RFC-BUSINESS-RELATIONSHIP-MODEL.md
* RFC-BUSINESS-RELATIONSHIP-API.md
* RFC-BUSINESS-REFERENCE-COMPONENT.md
* RFC-IDENTITY.md

---

# 1. Objetivo

Definir o modelo de dados do **Business Partner (BP)**, a entidade central responsável por representar qualquer pessoa física, pessoa jurídica ou organização com a qual a empresa mantém relacionamento.

O Business Partner elimina a necessidade de manter cadastros separados para clientes, fornecedores, transportadoras, representantes, bancos e demais entidades de negócio.

---

# 2. Motivação

Em ERPs tradicionais é comum existirem tabelas distintas para:

* Clientes
* Fornecedores
* Transportadoras
* Funcionários
* Representantes
* Bancos
* Seguradoras

Na prática, todas representam parceiros de negócio.

Duplicar essas informações aumenta a complexidade e dificulta a manutenção.

---

# 3. Princípios

O modelo segue os seguintes princípios:

* um parceiro possui identidade única;
* um parceiro pode desempenhar múltiplos papéis;
* contatos pertencem ao parceiro;
* endereços pertencem ao parceiro;
* documentos pertencem ao parceiro;
* relacionamentos são tratados pelo BRE;
* histórico nunca é perdido.

---

# 4. Arquitetura

```text
                   Business Partner

                          │

      ┌───────────────────┼────────────────────┐

      ▼                   ▼                    ▼

 Business Roles      Business Contacts    Business Addresses

      │                   │                    │

      └───────────────┬────┴────────────────────┘

                      ▼

        Business Relationship Engine
```

---

# 5. BusinessPartner

Representa qualquer parceiro de negócio.

Estrutura:

```text
BusinessPartner

id

partner_code

legal_type

person_type

display_name

legal_name

trade_name

status

company_id

created_at

updated_at
```

---

# 6. Identificação

## partner_code

Código interno.

Exemplo

```text
BP000000123
```

Nunca reutilizado.

---

## person_type

Valores permitidos.

```text
PERSON

COMPANY

GOVERNMENT

NON_PROFIT
```

---

## legal_type

Classificação jurídica.

Exemplos.

```text
MEI

LTDA

SA

EI

ASSOCIATION

FOUNDATION

PUBLIC_ENTITY
```

Configurável por país.

---

# 7. Nome

Campos.

```text
display_name

legal_name

trade_name
```

Exemplo.

```text
Display Name

Dell Brasil

Legal Name

Dell Computadores do Brasil Ltda.

Trade Name

Dell
```

---

# 8. Papéis

Um parceiro pode possuir qualquer combinação de papéis.

Exemplos.

```text
CUSTOMER

SUPPLIER

CARRIER

EMPLOYEE

REPRESENTATIVE

BANK

INSURANCE

MANUFACTURER

DISTRIBUTOR

MARKETPLACE

GOVERNMENT
```

Não existe limite.

---

# 9. BusinessPartnerRole

Estrutura.

```text
BusinessPartnerRole

id

partner_id

role

status

valid_from

valid_to

priority
```

Papéis também possuem vigência.

---

# 10. Documentos

Cada parceiro pode possuir diversos documentos.

```text
CPF

CNPJ

IE

IM

SUFRAMA

Passaporte

RG
```

Modelo.

```text
BusinessDocument

id

partner_id

document_type

document_number

issuer

issue_date

expiration_date
```

---

# 11. Endereços

Modelo.

```text
BusinessAddress

id

partner_id

address_type

country

state

city

district

street

number

zip_code
```

Tipos.

```text
Billing

Shipping

Headquarters

Branch

Warehouse

Office
```

---

# 12. Contatos

Cada parceiro pode possuir diversos contatos.

Modelo.

```text
BusinessContact

id

partner_id

name

department

job_title

email

phone

mobile

preferred
```

Exemplo.

```text
Dell

↓

Maria

Financeiro

↓

Carlos

Compras

↓

João

Suporte
```

---

# 13. Meios de Comunicação

Modelo.

```text
BusinessCommunication

id

partner_id

type

value

preferred
```

Tipos.

* Telefone
* Celular
* E-mail
* WhatsApp
* Site
* LinkedIn
* Instagram

---

# 14. Dados Comerciais

Informações comerciais opcionais.

Exemplos.

* limite de crédito;
* tabela de preços;
* condição de pagamento;
* prazo médio;
* classificação;
* segmento.

Esses dados podem variar conforme o papel desempenhado.

---

# 15. Dados Fiscais

Exemplos.

* regime tributário;
* indicador IE;
* contribuinte ICMS;
* CNAE principal;
* CNAEs secundários.

---

# 16. Dados Bancários

Modelo.

```text
BusinessBankAccount

id

partner_id

bank

branch

account

pix_key

preferred
```

---

# 17. Relacionamentos

Todos os relacionamentos utilizam o BRE.

Exemplos.

```text
Cliente

↓

Representante
```

```text
Fornecedor

↓

Produto
```

```text
Empresa

↓

Filial
```

O Business Partner não implementa relacionamentos próprios.

---

# 18. Auditoria

Registrar.

* usuário;
* data;
* operação;
* empresa;
* origem;
* versão.

---

# 19. Status

Estados.

```text
ACTIVE

INACTIVE

BLOCKED

ARCHIVED
```

---

# 20. API Conceitual

Serviços previstos.

```text
createPartner()

updatePartner()

activatePartner()

blockPartner()

archivePartner()

assignRole()

removeRole()

addContact()

addAddress()

addDocument()
```

---

# 21. Integrações

Consumidores.

* Compras
* Vendas
* Financeiro
* Fiscal
* Estoque
* POS
* Delivery
* CRM
* Workflow
* Document Engine

Todos acessam o mesmo Business Partner.

---

# 22. Casos de Uso

Empresa que compra e vende.

Papéis.

```text
CUSTOMER

SUPPLIER
```

---

Transportadora que também presta serviços.

Papéis.

```text
CARRIER

SUPPLIER
```

---

Banco parceiro.

Papéis.

```text
BANK

SUPPLIER
```

---

# 23. Benefícios

* cadastro único para todas as entidades;
* eliminação de duplicidade;
* múltiplos papéis;
* integração nativa com o BRE;
* histórico completo;
* suporte multiempresa;
* expansão sem alterações estruturais.

---

# 24. Não Objetivos

O Business Partner não controla:

* autenticação;
* permissões;
* workflow;
* documentos fiscais;
* regras tributárias.

Essas responsabilidades pertencem a outros componentes do Business Core.

---

# 25. Roadmap

## Sprint BP-01

* BusinessPartner
* BusinessPartnerRole
* CRUD básico

## Sprint BP-02

* Documentos
* Endereços
* Contatos

## Sprint BP-03

* Comunicações
* Dados bancários
* Auditoria

## Sprint BP-04

* Integração com BRE
* Integração com Business Reference Component
* Integração com Lookup Engine

## Sprint BP-05

* Histórico completo
* Versionamento
* Operação offline
* Cache compartilhado
