# RFC-BUSINESS-RELATIONSHIP-ENGINE.md

**Status:** Draft

**RFC:** 0014

**Categoria:** Business Core

**Prioridade:** Arquitetura Fundamental

**Dependências:**

* RFC-LOOKUP-AUTOCOMPLETE-ENGINE.md

**Módulo:**
BusinessCore

**Versão:** 1.0

---

# 1. Objetivo

Definir um mecanismo genérico para representar, consultar, versionar e validar qualquer relacionamento entre entidades do ERP.

O Business Relationship Engine (BRE) substitui centenas de tabelas específicas de relacionamento por uma infraestrutura única, reutilizável e extensível.

O BRE é um componente de infraestrutura do Business Core e poderá ser utilizado por todos os módulos do sistema.

---

# 2. Motivação

Sistemas ERP normalmente evoluem criando tabelas específicas para cada novo relacionamento.

Exemplos:

```text
produto_categoria

produto_marca

produto_fornecedor

produto_ncm

produto_anp

produto_cest

ncm_cest

cfop_cst

empresa_filial

usuario_empresa

pedido_transportadora
```

Após alguns anos existem centenas de tabelas semelhantes.

Isso gera:

* duplicação de código;
* APIs diferentes;
* consultas diferentes;
* regras repetidas;
* manutenção complexa.

---

# 3. Objetivos

O BRE deverá:

* representar qualquer relacionamento;
* suportar vigência;
* suportar versionamento;
* permitir prioridades;
* permitir múltiplos relacionamentos;
* possuir auditoria completa;
* permitir cache;
* possuir API única;
* suportar eventos.

---

# 4. Princípios

## 4.1 Toda relação é uma entidade

O relacionamento possui identidade própria.

Não é apenas uma Foreign Key.

---

## 4.2 Toda relação possui ciclo de vida

Uma relação pode:

* nascer;
* ser alterada;
* expirar;
* ser substituída.

---

## 4.3 Toda relação possui histórico

Nenhum relacionamento será sobrescrito.

Sempre será criada uma nova versão.

---

# 5. Arquitetura

```text
                  Business Core

                        │

        ┌───────────────┼───────────────┐

        ▼               ▼               ▼

 Lookup Engine   Relationship Engine   Event Engine

                        │

                        ▼

              Business Relationship API

                        │

                        ▼

             Relationship Repository
```

---

# 6. Entidades

## BusinessEntity

Representa qualquer entidade cadastrada.

Campos mínimos:

```text
id

entity_type

entity_key

company_id

status
```

---

Exemplos:

```text
Produto

Fornecedor

Cliente

Empresa

Filial

NCM

CEST

CFOP

Banco

Transportadora
```

---

# 7. BusinessRelationship

```text
id

source_entity

target_entity

relationship_type

priority

valid_from

valid_to

required

company_id

status

created_at

created_by

version
```

---

# 8. RelationshipType

Inicialmente:

```text
BELONGS_TO

USES

DEFAULT

OPTIONAL

REQUIRES

GENERATES

DEPENDS_ON

OWNS

SUPPLIES

SHIPS

SELLS

PURCHASES
```

Novos tipos poderão ser adicionados sem alterar o banco.

---

# 9. Exemplos

Produto → Marca

```text
Produto

↓

BELONGS_TO

↓

Marca
```

---

Produto → Categoria

```text
Produto

↓

BELONGS_TO

↓

Categoria
```

---

Produto → Fornecedor

```text
Produto

↓

SUPPLIES

↓

Fornecedor
```

---

Usuário → Empresa

```text
Usuário

↓

USES

↓

Empresa
```

---

Empresa → Filial

```text
Empresa

↓

OWNS

↓

Filial
```

---

NCM → CEST

```text
NCM

↓

DEFAULT

↓

CEST
```

---

# 10. API

```text
createRelationship()

updateRelationship()

closeRelationship()

deleteRelationship()

findRelationships()

findTargets()

findSources()

validateRelationship()

relationshipHistory()
```

---

# 11. Eventos

```text
RelationshipCreated

RelationshipUpdated

RelationshipExpired

RelationshipDeleted

RelationshipValidated
```

---

# 12. Versionamento

Nunca utilizar UPDATE.

Fluxo:

```text
Versão 1

↓

Expirada

↓

Versão 2

↓

Versão 3
```

Todo histórico permanece disponível.

---

# 13. Vigência

Toda consulta deve considerar:

```text
CURRENT_DATE

>= valid_from

<= valid_to
```

Relacionamentos expirados não participam das consultas padrão.

---

# 14. Prioridade

Quando existirem múltiplos relacionamentos:

```text
Fornecedor A

prioridade 10

Fornecedor B

prioridade 20
```

O motor retorna o de maior prioridade.

---

# 15. Múltiplos Relacionamentos

Permitido.

Exemplo:

Produto

↓

Fornecedor A

Fornecedor B

Fornecedor C

---

# 16. Obrigatoriedade

Cada relacionamento poderá ser:

Obrigatório

ou

Opcional

---

# 17. Auditoria

Registrar:

* usuário;
* data;
* origem;
* estação;
* importação;
* motivo;
* versão.

---

# 18. Cache

O BRE deverá possuir cache para:

* relacionamentos ativos;
* relacionamentos mais utilizados;
* catálogos.

---

# 19. Segurança

As permissões serão avaliadas por:

* empresa;
* filial;
* perfil;
* módulo;
* operação.

---

# 20. Integração

Consumidores previstos:

* Produtos
* Compras
* Vendas
* Estoque
* Financeiro
* Fiscal
* CRM
* Documentos
* Workflow
* POS
* Delivery
* E-commerce

Todos utilizarão exatamente a mesma API.

---

# 21. Casos de Uso

### Produto

Produto

↓

Categoria

↓

Marca

↓

Fornecedor

↓

NCM

↓

CEST

---

### Pedido

Pedido

↓

Cliente

↓

Transportadora

↓

Forma de Pagamento

↓

Entrega

---

### Fiscal

NCM

↓

CEST

↓

Benefício Fiscal

↓

ANP

↓

EX TIPI

---

### Usuários

Usuário

↓

Empresa

↓

Filial

↓

Perfil

---

# 22. Performance

Objetivos:

Consulta:

< 20 ms

Lookup:

< 50 ms

Cache Hit:

< 5 ms

---

# 23. Benefícios

* Elimina dezenas de tabelas de relacionamento.
* API única para todos os módulos.
* Versionamento nativo.
* Auditoria centralizada.
* Redução de código duplicado.
* Suporte a múltiplos relacionamentos.
* Preparado para evolução legislativa e de negócio.

---

# 24. Limites do BRE

O BRE representa **relações estruturais** entre entidades.

Ele **não substitui**:

* Workflow Engine (estado e transições);
* Rule Engine (cálculo e decisões);
* Permission Engine (autorização);
* Document Engine (ciclo documental).

Esses motores podem consultar o BRE, mas possuem responsabilidades distintas.

---

# 25. Roadmap

## Sprint BRE-01

* Modelo BusinessEntity.
* Modelo BusinessRelationship.
* CRUD.
* API de consulta.
* Versionamento inicial.

## Sprint BRE-02

* Cache.
* Eventos.
* Auditoria.
* Lookup integrado.

## Sprint BRE-03

* AutoFill.
* Relacionamentos compostos.
* Prioridades.
* Vigência.

## Sprint BRE-04

* Integração com Produtos.
* Integração com Compras.
* Integração com Vendas.
* Integração com Fiscal.

## Sprint BRE-05

* Integração com Workflow.
* Integração com Document Engine.
* Consultas gráficas de relacionamentos.
* Ferramentas de diagnóstico.

---

# 26. Critérios de Adoção

Todo novo módulo do ERP que necessite relacionar entidades deverá avaliar primeiro o uso do BRE.

A criação de uma nova tabela de relacionamento específica somente será permitida quando houver justificativa técnica documentada demonstrando que o BRE não atende ao caso de uso.
