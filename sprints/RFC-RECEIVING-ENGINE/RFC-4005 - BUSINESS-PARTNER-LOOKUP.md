# RFC-4005 - Business Partner Lookup

| Campo | Valor |
|--------|-------|
| RFC | 4005 |
| Nome | Business Partner Lookup |
| Categoria | Core Business / Recebimento |
| Status | Draft |
| Versão | 1.0 |
| Nota | Numeração corrigida (estava duplicada como 4003). Slot 4005 = fornecedor/parceiro; Lookup localiza e não cria/atualiza. |

---

# 1. Objetivo

Esta RFC define o componente **Business Partner Lookup**, responsável por localizar um Parceiro de Negócio existente no Retail ERP.

O componente é reutilizável por qualquer módulo da plataforma e possui uma única responsabilidade:

**Localizar um Business Partner.**

Ele não cria, atualiza ou altera cadastros.

---

# 2. Motivação

Diversos módulos precisam localizar Parceiros de Negócio.

Exemplos:

- Recebimento
- Compras
- Vendas
- Financeiro
- Fiscal
- CRM
- Logística

Criar mecanismos diferentes para cada módulo aumenta a complexidade e gera duplicação.

Por isso, toda localização deve utilizar um único componente.

---

# 3. Responsabilidade

O Business Partner Lookup é responsável apenas por:

- localizar um Business Partner;
- informar quando não existir;
- informar quando existir duplicidade.

Ele **não**:

- cria parceiros;
- altera parceiros;
- sincroniza dados;
- remove parceiros.

---

# 4. Tipos de Business Partner

O componente deve ser capaz de localizar qualquer Parceiro de Negócio.

Exemplos:

- Supplier
- Customer
- Carrier
- Manufacturer
- Branch
- Employee
- Service Provider

O módulo chamador define qual papel espera localizar.

---

# 5. Dados de Pesquisa

Os critérios de busca podem incluir:

- CNPJ
- CPF
- Internal Code
- External Reference
- State Registration (IE), quando aplicável

Nome Fantasia e Razão Social não devem ser utilizados como chave principal de localização.

---

# 6. Ordem de Busca

A busca deve seguir uma ordem determinística.

1. External Reference
2. CNPJ
3. CPF
4. Internal Code

Caso nenhum critério retorne resultado, o parceiro será considerado inexistente.

---

# 7. Resultado

O componente possui apenas três resultados possíveis.

## Found

Um único Business Partner localizado.

↓

Retornar referência do parceiro.

---

## Not Found

Nenhum parceiro localizado.

↓

O módulo chamador decide a próxima ação.

Exemplo:

Recebimento → iniciar cadastro.

---

## Multiple Matches

Mais de um parceiro encontrado.

↓

Retornar inconsistência.

↓

Solicitar intervenção do usuário.

---

# 8. Fluxo

Business Module

↓

Business Partner Lookup

↓

Found ?

├── Yes → Return Partner
│
├── No → Return Not Found
│
└── Multiple → Return Conflict

---

# 9. Auditoria

Toda consulta deve registrar:

- data;
- módulo solicitante;
- critérios utilizados;
- resultado da pesquisa.

---

# 10. Casos Especiais

O componente deve suportar:

- Pessoa Física
- Pessoa Jurídica
- Parceiros estrangeiros
- Parceiros sem IE
- Órgãos públicos
- Cooperativas

As diferenças cadastrais pertencem ao módulo Business Partner.

---

# 11. Integração

Este componente pode ser utilizado por:

- Receiving
- Purchase
- Sales
- Inventory
- Fiscal
- Financial
- CRM

Sem necessidade de implementações específicas para cada módulo.

---

# 12. Fora do Escopo

Esta RFC não define:

- criação de parceiros;
- atualização de parceiros;
- validação de documentos;
- sincronização cadastral;
- regras fiscais.

Esses assuntos serão tratados em RFCs específicas.

---

# 13. Princípios Arquiteturais

Esta RFC segue os princípios definidos em:

- RFC-0001-ARCHITECTURE-PRINCIPLES.md

Especialmente:

- Simple is better than complex.
- Business before technology.
- One responsibility per module.
- Reuse before create.

---

# 14. Roadmap

Esta RFC serve como base para:

- RFC-2001-BUSINESS-PARTNER.md
- RFC-4002-NFE-RECEIVING.md
- RFC-4004-PRODUCT-LOOKUP.md
- RFC-4006-BUSINESS-PARTNER-UPDATE.md
