# RFC-4002-NFE-RECEIVING.md

| Campo | Valor |
|--------|-------|
| RFC | 4002 |
| Nome | NF-e Receiving |
| Categoria | Receiving |
| Status | Draft |
| Versão | 1.0 |

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

Esta RFC define como uma Nota Fiscal Eletrônica (NF-e) de entrada inicia um processo de Recebimento no Retail ERP.

O objetivo desta RFC é estabelecer um fluxo único para recebimento de documentos fiscais de fornecedores, independentemente da forma como chegam ao sistema.

Esta RFC não define regras de estoque, financeiro ou fiscal. Essas responsabilidades pertencem aos respectivos módulos.

---

# 2. Escopo

Esta RFC cobre exclusivamente:

- Recebimento de NF-e modelo 55.
- Identificação da empresa destinatária.
- Validação inicial do documento.
- Criação do processo de Recebimento.
- Encaminhamento para os próximos módulos.

Não faz parte desta RFC:

- Atualização de produtos.
- Atualização de fornecedores.
- Entrada em estoque.
- Contas a pagar.
- Escrituração fiscal.

---

# 3. Formas de Entrada

O sistema deve aceitar diferentes formas de recebimento.

## Manual

O usuário seleciona um ou mais arquivos da NF-e.

Exemplos:

- XML salvo no computador.
- Arquivo recebido por e-mail.
- Pasta local.

---

## Assistido

O sistema identifica automaticamente novas NF-es.

O usuário apenas revisa e confirma.

Exemplos:

- Pasta monitorada.
- Download automático.
- Integração com serviços externos.

---

## Automático

Todo o processo ocorre sem intervenção do usuário.

Exemplos:

- API.
- Scheduler.
- Integração entre sistemas.

---

# 4. Fluxo

Todo recebimento segue o mesmo fluxo.

```text
NF-e

↓

Validação Inicial

↓

Empresa Destinatária

↓

Fornecedor

↓

Criar Recebimento

↓

Encaminhar
```

---

# 5. Validação Inicial

Antes de iniciar o Recebimento, o sistema deve validar:

- Arquivo legível.
- Estrutura válida.
- Modelo do documento.
- Empresa destinatária.
- Chave de acesso.
- Duplicidade.
- Situação da NF-e.

Caso alguma validação falhe, o Recebimento não será iniciado.

---

# 6. Identificação da Empresa

O sistema identifica automaticamente para qual empresa ou filial a NF-e foi emitida.

Caso nenhuma empresa seja encontrada:

Status:

**Pending Company**

Nenhuma integração será executada.

---

# 7. Identificação do Fornecedor

Após identificar a empresa destinatária, o sistema tenta localizar o fornecedor.

As regras de localização serão definidas em:

RFC-4003-SUPPLIER-IDENTIFICATION.md

---

# 8. Criação do Recebimento

Após a validação inicial, o sistema cria um novo Recebimento.

Neste momento apenas informações gerais são registradas.

Exemplos:

- Chave da NF-e.
- Número.
- Série.
- Emissão.
- Fornecedor.
- Empresa.
- Valor Total.
- Quantidade de Itens.

Os itens ainda não são vinculados aos produtos.

---

# 9. Estados

O Recebimento pode assumir os seguintes estados iniciais:

- New
- Validating
- Pending Company
- Pending Supplier
- Pending Review
- Ready
- Rejected

As transições completas serão definidas na RFC do módulo Recebimento.

---

# 10. Encaminhamento

Quando o Recebimento estiver pronto, os próximos módulos poderão processá-lo.

A sequência padrão será:

```text
Recebimento

↓

Fornecedor

↓

Produtos

↓

Financeiro

↓

Inventário

↓

Fiscal
```

Cada módulo executa apenas sua própria responsabilidade.

---

# 11. Auditoria

Toda etapa deve gerar eventos de auditoria.

Exemplos:

- Documento recebido.
- Documento rejeitado.
- Empresa localizada.
- Fornecedor localizado.
- Recebimento criado.
- Recebimento cancelado.

Os eventos são imutáveis.

---

# 12. Casos de Exceção

O processo deve tratar, entre outros:

- Documento duplicado.
- Empresa inexistente.
- Fornecedor inexistente.
- XML inválido.
- Modelo diferente de NF-e.
- Documento cancelado.
- Documento denegado.

O sistema nunca deve interromper o processamento de outros recebimentos devido a erro em um documento.

---

# 13. Princípios

Esta RFC segue os princípios definidos em:

- RFC-0001-ARCHITECTURE-PRINCIPLES.md
- RFC-4001-RECEIVING.md

Especialmente:

- Simple is better than complex.
- One responsibility per module.
- Business before technology.

---

# 14. Roadmap

As próximas RFCs detalham este processo:

- RFC-4003-SUPPLIER-IDENTIFICATION.md
- RFC-4004-PRODUCT-IDENTIFICATION.md
- RFC-4005-PRODUCT-UPDATE.md
- RFC-4006-SUPPLIER-UPDATE.md
- RFC-4007-ACCOUNTS-PAYABLE.md
- RFC-4008-STOCK-RECEIVING.md
- RFC-4009-FISCAL-INTEGRATION.md
- RFC-4010-RECEIVING-AUDIT.md
