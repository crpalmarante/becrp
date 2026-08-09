# RFC-SUPPLIER-IMPORT-ENGINE.md

# RFC: Supplier Import Engine

**Status:** Proposta

**Versão:** 1.0

**Data:** 29/07/2026

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

Definir a arquitetura do **Supplier Import Engine**, responsável por importar documentos, catálogos e informações fornecidas por parceiros comerciais para o ERP.

Este módulo é independente do formato dos arquivos e centraliza todo o processo de importação, validação, transformação e integração com os demais módulos.

---

# 2. Motivação

Fornecedores utilizam diferentes meios para compartilhar informações:

* NF-e XML
* Catálogos de produtos
* Planilhas Excel
* Arquivos CSV
* APIs REST
* Web Services
* EDI
* GS1

Todos esses formatos representam a mesma intenção de negócio: importar informações de um fornecedor.

---

# 3. Princípios

* O formato não define o domínio.
* Todo processo de importação passa pelo mesmo pipeline.
* Cada formato é implementado como um conector independente.
* O núcleo do ERP não conhece formatos de arquivo.
* Toda importação é auditável.

---

# 4. Arquitetura

```text
Supplier Import Engine

├── Import Manager
├── Connector Manager
├── Validation Engine
├── Matching Engine
├── Preview Engine
├── Import Engine
├── Post Processing
└── Audit
```

---

# 5. Pipeline

Todo processo seguirá as etapas:

```text
Fonte

↓

Connector

↓

Extract

↓

Normalize

↓

Validate

↓

Matching

↓

Preview

↓

Import

↓

Post Processing

↓

Audit
```

---

# 6. Connectors

Os conectores suportados inicialmente serão:

* Supplier XML Import
* Supplier Excel Import
* Supplier CSV Import
* Supplier API Import

Novos conectores poderão ser adicionados sem alterações no núcleo.

---

# 7. Matching Engine

Responsável por localizar entidades existentes:

* fornecedor;
* produto;
* unidade;
* NCM;
* código interno;
* código do fornecedor;
* código de barras (GTIN/EAN);
* tributação.

Nenhuma entidade será criada automaticamente sem configuração.

---

# 8. Preview

Antes da importação, o usuário poderá visualizar:

* produtos encontrados;
* produtos não encontrados;
* divergências;
* impostos;
* quantidades;
* custos;
* documentos relacionados.

---

# 9. Importação

O Engine poderá gerar:

* Recebimento
* Movimentos de Estoque
* Atualização de Custos
* Atualização de Cadastro
* Contas a Pagar
* Eventos de Auditoria

---

# 10. Pós-processamento

Após a importação poderão ser executadas ações automáticas:

* atualização de custo médio;
* atualização de preços;
* geração de etiquetas;
* notificações;
* workflows internos.

---

# 11. Integrações

* Purchase
* Receiving
* Inventory
* Fiscal
* Finance
* Product Catalog
* Audit

---

# 12. RFCs Derivadas

Esta RFC serve como base para:

* RFC-SUPPLIER-XML-IMPORT.md
* RFC-SUPPLIER-CSV-IMPORT.md
* RFC-SUPPLIER-EXCEL-IMPORT.md
* RFC-SUPPLIER-API-IMPORT.md
* RFC-SUPPLIER-EDI-IMPORT.md

---

# 13. Conclusão

O Supplier Import Engine estabelece um ponto único de entrada para informações provenientes de fornecedores, desacoplando formatos de arquivo das regras de negócio e permitindo a evolução contínua das integrações do ERP.
