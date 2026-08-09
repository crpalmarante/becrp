# RFC-BUSINESS-RELATIONSHIP-MODEL.md

**Status:** Draft

**RFC:** 0015

**Categoria:** Business Core

**Módulo:** Business Relationship Engine (BRE)

**Prioridade:** Arquitetura Base

**Versão:** 1.0

**Dependências:**

* RFC-BUSINESS-CORE.md
* RFC-IDENTITY.md

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

Definir o modelo de dados oficial do **Business Relationship Engine (BRE)**.

Esta RFC estabelece como qualquer relacionamento entre entidades do ERP será representado, armazenado, versionado e consultado.

O modelo é genérico e não possui conhecimento específico sobre produtos, clientes, documentos ou tributos.

---

# 2. Princípios

O modelo segue cinco princípios fundamentais.

## P1 - Toda entidade possui identidade

Toda entidade do sistema deve possuir um identificador único.

Exemplos:

* Produto
* Cliente
* Fornecedor
* Empresa
* Filial
* Usuário
* Pedido
* Documento
* NCM
* CEST
* Município
* Banco

---

## P2 - Todo relacionamento é uma entidade

Relacionamentos possuem ciclo de vida.

Não são apenas Foreign Keys.

Exemplo

Produto A pertence à Categoria X.

Esse relacionamento possui:

* data de criação;
* usuário;
* vigência;
* prioridade;
* auditoria.

---

## P3 - Nenhum relacionamento é perdido

Relacionamentos nunca serão sobrescritos.

Sempre serão versionados.

---

## P4 - Todo relacionamento possui vigência

Uma relação pode existir apenas em determinado período.

Exemplo

Fornecedor preferencial válido:

01/01/2026

até

31/12/2026

---

## P5 - Toda alteração gera nova versão

Nunca utilizar UPDATE destrutivo.

---

# 3. Arquitetura

```text
BusinessEntity

        │

        ▼

BusinessRelationship

        │

        ▼

RelationshipRepository

        │

        ▼

RelationshipAPI
```

---

# 4. BusinessEntity

Representa qualquer entidade cadastrada no ERP.

Não importa o módulo.

## Estrutura

```text
BusinessEntity

id

entity_type

entity_key

company_id

status

created_at

updated_at
```

---

## id

Identificador único global.

Tipo:

UUID

---

## entity_type

Define o tipo da entidade.

Exemplos

```text
PRODUCT

CUSTOMER

SUPPLIER

COMPANY

BRANCH

USER

ORDER

DOCUMENT

NCM

CEST

CFOP

BANK

CITY

STATE

COUNTRY
```

---

## entity_key

Chave natural da entidade.

Exemplos

```text
SKU

CNPJ

CPF

Código NCM

Código CEST

Código CFOP
```

---

## company_id

Suporte a multiempresa.

---

## status

Estados possíveis

```text
ACTIVE

INACTIVE

ARCHIVED

BLOCKED
```

---

# 5. BusinessRelationship

Representa qualquer relacionamento entre duas entidades.

---

## Estrutura

```text
BusinessRelationship

id

source_entity_id

target_entity_id

relationship_type

priority

required

valid_from

valid_to

status

version

metadata

company_id

created_by

created_at
```

---

# 6. Campos

## id

UUID.

---

## source_entity_id

Entidade de origem.

---

## target_entity_id

Entidade de destino.

---

## relationship_type

Tipo do relacionamento.

---

## priority

Número inteiro.

Quanto maior, maior prioridade.

---

## required

Boolean.

Define obrigatoriedade.

---

## valid_from

Início da vigência.

---

## valid_to

Fim da vigência.

---

## status

```text
ACTIVE

EXPIRED

CANCELLED

PENDING
```

---

## version

Número sequencial.

---

## metadata

Campo JSON.

Permite armazenar informações específicas sem alterar o modelo.

Exemplo

```json
{
  "legal_basis":"Convênio ICMS 142/2018",
  "notes":"Aplicável apenas para operações internas",
  "default":true
}
```

---

# 7. RelationshipType

Os tipos são cadastráveis.

Exemplos iniciais.

```text
BELONGS_TO

DEFAULT

OPTIONAL

REQUIRES

DEPENDS_ON

SUPPLIES

SHIPS

USES

GENERATES

OWNS

SELLS

PURCHASES

APPLIES_TO

ALLOWS

PROHIBITS
```

---

# 8. Cardinalidade

O BRE suporta.

```text
1 → 1

1 → N

N → 1

N → N
```

Sem alteração estrutural.

---

# 9. Versionamento

Nunca modificar um relacionamento existente.

Fluxo

```text
Versão 1

↓

EXPIRADA

↓

Versão 2

↓

ATIVA
```

---

# 10. Vigência

Toda consulta deverá considerar.

```text
CURRENT_DATE

>= valid_from

<= valid_to
```

---

# 11. Relacionamentos Compostos

Exemplo

Produto

↓

Fornecedor

↓

Empresa

↓

Centro de Distribuição

O BRE deve permitir navegar entre múltiplos níveis.

---

# 12. Herança

Relacionamentos podem ser herdados.

Exemplo

Empresa

↓

Filial

↓

Produto

O produto herda configurações da empresa quando permitido pela regra de negócio.

---

# 13. Prioridade

Quando existirem múltiplos relacionamentos.

```text
Fornecedor A

prioridade 100

Fornecedor B

prioridade 80

Fornecedor C

prioridade 50
```

O mecanismo poderá retornar automaticamente o relacionamento prioritário.

---

# 14. Restrições

Relacionamentos podem possuir restrições.

Exemplos

Empresa

Filial

Estado

Perfil

Canal

Tipo Documento

Essas restrições são armazenadas no campo metadata ou em tabelas auxiliares especializadas quando necessário.

---

# 15. Auditoria

Cada relacionamento registra.

* usuário
* data
* origem
* estação
* aplicação
* motivo
* versão

---

# 16. Integridade

Não será permitido.

* entidade inexistente
* relacionamento circular proibido
* vigência inválida
* versão duplicada

---

# 17. Índices

Obrigatórios.

```text
source_entity_id

target_entity_id

relationship_type

company_id

status

valid_from

valid_to
```

Índices compostos.

```text
(source_entity_id, relationship_type)

(target_entity_id, relationship_type)

(company_id, relationship_type)
```

---

# 18. Exemplos

## Produto → Categoria

```text
Produto

↓

BELONGS_TO

↓

Categoria
```

---

## Produto → Marca

```text
Produto

↓

BELONGS_TO

↓

Marca
```

---

## Produto → NCM

```text
Produto

↓

USES

↓

NCM
```

---

## NCM → CEST

```text
NCM

↓

DEFAULT

↓

CEST
```

---

## Cliente → Empresa

```text
Cliente

↓

BELONGS_TO

↓

Empresa
```

---

## Usuário → Empresa

```text
Usuário

↓

USES

↓

Empresa
```

---

# 19. Não Objetivos

O BRE não calcula impostos.

O BRE não executa workflows.

O BRE não controla permissões.

O BRE apenas representa relacionamentos.

---

# 20. Benefícios

* Modelo único para todo o ERP.
* Elimina centenas de tabelas específicas.
* Versionamento nativo.
* Multiempresa.
* Auditoria centralizada.
* Suporte à legislação fiscal.
* Preparado para evolução futura.
* API uniforme para todos os módulos.

---

# 21. Próximas RFCs

Esta RFC define apenas o **modelo de dados**.

As responsabilidades complementares serão tratadas em documentos separados:

* **RFC-BUSINESS-RELATIONSHIP-API.md** — serviços, consultas e eventos.
* **RFC-BUSINESS-RELATIONSHIP-LOOKUP.md** — integração com Lookup, AutoComplete e AutoFill.
* **RFC-BUSINESS-RELATIONSHIP-CACHE.md** — cache, sincronização e operação offline.
* **RFC-BUSINESS-RELATIONSHIP-RULES.md** — resolução de conflitos, prioridades, herança e regras de seleção.
