# RFC-NCM-CEST-LOOKUP.md

**Status:** Draft

**RFC:** 0013

**Categoria:** Fiscal Core

**Dependência:**

* RFC-LOOKUP-AUTOCOMPLETE-ENGINE.md

**Prioridade:** Crítica

**Versão:** 1.0

---

# 1. Objetivo

Definir a arquitetura oficial para gerenciamento, pesquisa, relacionamento e validação entre **NCM** e **CEST**, utilizada por todos os módulos do ERP.

Esta RFC estabelece:

* modelo de dados;
* relacionamento NCM × CEST;
* atualização das tabelas oficiais;
* regras de vigência;
* preenchimento automático;
* validações fiscais;
* integração com NF-e, NFC-e, Compras, Estoque e Cadastro de Produtos.

---

# 2. Motivação

O NCM identifica a classificação fiscal da mercadoria.

O CEST identifica mercadorias sujeitas à Substituição Tributária (ST).

Na legislação brasileira:

* um NCM pode possuir diversos CEST;
* um CEST pode abranger diversos NCM;
* alguns NCM não possuem qualquer CEST;
* a relação muda conforme Convênios ICMS e alterações legais.

Portanto, **NCM e CEST não podem ser tratados como simples campos de texto**.

---

# 3. Objetivos

O sistema deverá:

✓ impedir inconsistências

✓ impedir códigos inválidos

✓ controlar vigência

✓ permitir atualização oficial

✓ manter histórico

✓ funcionar offline

✓ permitir auditoria

---

# 4. Arquitetura

```text
Cadastro Produto
        │
        ▼
 Lookup NCM
        │
        ▼
NCM Service
        │
        ▼
Tabela NCM
        │
        ▼
Tabela NCM_CEST
        │
        ▼
Tabela CEST
        │
        ▼
AutoFill Engine
        │
        ▼
Produto
```

---

# 5. Modelo de Dados

## Tabela NCM

Campos obrigatórios

| Campo           | Tipo       |
| --------------- | ---------- |
| id              | UUID       |
| codigo          | varchar(8) |
| descricao       | text       |
| capitulo        | varchar(2) |
| posicao         | varchar(4) |
| subposicao      | varchar(6) |
| item            | varchar(8) |
| vigencia_inicio | date       |
| vigencia_fim    | date       |
| ativo           | boolean    |

---

## Índices

* código
* descrição
* vigência

---

# 6. Tabela CEST

| Campo           | Tipo       |
| --------------- | ---------- |
| id              | UUID       |
| codigo          | varchar(9) |
| descricao       | text       |
| segmento        | varchar    |
| vigencia_inicio | date       |
| vigencia_fim    | date       |
| ativo           | boolean    |

---

# 7. Tabela NCM_CEST

Esta é a tabela mais importante.

| Campo               | Tipo    |
| ------------------- | ------- |
| id                  | UUID    |
| ncm_id              | FK      |
| cest_id             | FK      |
| descricao_aplicacao | text    |
| fundamento_legal    | varchar |
| obrigatorio         | boolean |
| vigencia_inicio     | date    |
| vigencia_fim        | date    |

---

# 8. Cardinalidade

```text
NCM

1

↓

N

NCM_CEST

N

↓

1

CEST
```

Representa um relacionamento muitos-para-muitos.

---

# 9. Cadastro do Produto

O produto armazenará apenas referências.

```text
produto

id

descricao

ncm_id

cest_id
```

Nunca:

```text
produto.ncm_codigo

produto.cest_codigo
```

O código sempre será obtido pela entidade relacionada.

---

# 10. Lookup NCM

O usuário poderá pesquisar por:

* código
* descrição
* parte da descrição
* capítulo

Exemplo

```text
8418

geladeira

refrigerador

freezer
```

---

# 11. Seleção

Após selecionar:

```text
84181000

Refrigeradores domésticos
```

o sistema executa:

```text
Lookup

↓

NCM Service

↓

Relacionamento

↓

AutoFill
```

---

# 12. AutoFill

Caso exista apenas um relacionamento válido.

```text
NCM

↓

1 relacionamento

↓

CEST

↓

Preencher automaticamente
```

---

# 13. Múltiplos Relacionamentos

Exemplo

```text
84181000
```

retorna

```text
21.001.00

21.002.00

21.004.00
```

O sistema abre um diálogo.

```text
Escolha o CEST

○ 21.001.00

○ 21.002.00

○ 21.004.00
```

---

# 14. Nenhum Relacionamento

Caso não exista CEST válido.

```text
CEST

vazio
```

O sistema registra:

```text
Produto sem CEST.
```

Sem impedir o cadastro, salvo configuração específica da empresa.

---

# 15. Vigência

Toda consulta deverá considerar:

```text
data atual
```

Relacionamentos expirados

↓

ignorar

Relacionamentos futuros

↓

ignorar

---

# 16. Atualização Oficial

As tabelas serão importadas de arquivos oficiais.

Importações suportadas:

* CSV
* XML
* XLSX
* JSON

Cada importação gera:

* nova versão
* histórico
* auditoria

---

# 17. Versionamento

Nenhum registro será sobrescrito.

Sempre:

```text
Nova vigência

↓

Nova versão
```

Mantendo histórico completo.

---

# 18. Auditoria

Registrar:

* usuário
* data
* origem
* versão
* importação

---

# 19. Cache

O Lookup utilizará:

Cache memória

↓

Cache persistente

↓

Banco

---

# 20. Offline

Caso a estação esteja offline.

Lookup

↓

Cache Local

↓

Pesquisa continua funcionando.

---

# 21. Integração NF-e

Na emissão.

Produto

↓

NCM

↓

CEST

↓

XML

```xml
<NCM>84181000</NCM>

<CEST>2100100</CEST>
```

---

# 22. Integração Compras

Importação XML

↓

Extrair NCM

↓

Extrair CEST

↓

Comparar cadastro

↓

Atualizar produto (conforme política)

---

# 23. Integração Estoque

Nenhuma regra específica.

O estoque apenas referencia o produto.

---

# 24. Integração Fiscal

Motores consumidores:

* ICMS
* ICMS ST
* IBS
* CBS
* IPI
* PIS
* COFINS

Todos obtêm NCM e CEST exclusivamente através da entidade Produto.

---

# 25. API

```text
search()

get()

validate()

findByCode()

findByDescription()

findCEST()

listRelationships()
```

---

# 26. Eventos

```text
onNCMSelected

onCESTSelected

onRelationshipFound

onRelationshipMissing

onRelationshipMultiple

onAutoFill
```

---

# 27. Regras de Negócio

RN-001

O NCM deve existir.

---

RN-002

O NCM deve estar vigente.

---

RN-003

O CEST deve estar vigente.

---

RN-004

O relacionamento deve estar vigente.

---

RN-005

Relacionamentos expirados são ignorados.

---

RN-006

Mais de um relacionamento exige confirmação do usuário.

---

RN-007

A ausência de CEST não implica erro, exceto quando exigido pela configuração fiscal da empresa ou pela legislação aplicável.

---

RN-008

O usuário não poderá informar manualmente um CEST incompatível com o NCM selecionado.

---

RN-009

Toda alteração de NCM em um produto invalida a seleção anterior de CEST e obriga nova validação do relacionamento.

---

# 28. Segurança

Somente usuários autorizados poderão:

* importar tabelas oficiais;
* alterar vínculos NCM × CEST;
* criar exceções internas.

O cadastro de produtos utilizará apenas os registros oficiais, salvo permissões específicas.

---

# 29. Extensibilidade

A arquitetura foi projetada para suportar futuros relacionamentos utilizando o mesmo padrão, como:

* NCM × EX TIPI
* NCM × ANP
* NCM × Benefício Fiscal
* NCM × FCI
* NCM × Regra IBS/CBS
* NCM × Tributação Estadual

---

# 30. Roadmap

### Sprint 1

* Tabelas NCM, CEST e NCM_CEST.
* Lookup de NCM.
* AutoFill simples.

### Sprint 2

* Vigência.
* Auditoria.
* Importador de tabelas oficiais.

### Sprint 3

* Cache persistente.
* Funcionamento offline.
* API pública.

### Sprint 4

* Versionamento completo.
* Integração com NF-e/NFC-e.
* Integração com motores tributários.

---

# Anexo A — Fluxo Completo

```text
Usuário abre Cadastro de Produto

        │

        ▼

Pesquisa NCM

        │

        ▼

Seleciona NCM

        │

        ▼

Consulta tabela NCM_CEST

        │

 ┌──────┼───────────────┐
 │      │               │
 ▼      ▼               ▼

0      1              N

CEST   CEST          CEST

 │      │             │

 ▼      ▼             ▼

Vazio AutoFill    Escolha usuário

        │

        ▼

Validação

        │

        ▼

Produto salvo
```
