# RFC-4003 - Monitor de XML

| Campo | Valor |
|--------|-------|
| RFC | 4003 |
| Nome | Monitor de XML |
| Categoria | Recebimento |
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

Esta RFC define o módulo **Monitor de XML** do Retail ERP.

O Monitor de XML é responsável por controlar o ciclo de vida dos documentos XML recebidos pelo sistema.

Seu papel é receber, armazenar, identificar, acompanhar e disponibilizar XMLs para processamento pelos módulos responsáveis.

O Monitor de XML não realiza interpretação fiscal ou movimentação operacional.

Ele funciona como uma camada de controle e gerenciamento dos documentos recebidos.

---

# 2. Motivação

Documentos fiscais eletrônicos possuem um ciclo de vida próprio.

Antes de um XML ser utilizado pelo sistema, é necessário controlar:

- recebimento do arquivo;
- armazenamento seguro;
- identificação do documento;
- validação inicial;
- duplicidade;
- processamento;
- erros;
- reprocessamento;
- auditoria.

Centralizar esse controle evita que cada módulo implemente sua própria lógica de gerenciamento de documentos.

---

# 3. Responsabilidades

O Monitor de XML é responsável por:

- receber arquivos XML;
- armazenar documentos originais;
- identificar tipo de documento;
- controlar status de processamento;
- registrar eventos;
- detectar duplicidades;
- controlar tentativas de processamento;
- disponibilizar documentos para os módulos consumidores;
- manter histórico completo.

---

# 4. Não é responsabilidade do Monitor de XML

O módulo não executa:

- interpretação completa da NF-e;
- cálculo de impostos;
- criação de recebimento;
- movimentação de estoque;
- geração de contas;
- validação comercial;
- atualização de produtos.

Essas responsabilidades pertencem aos módulos especializados.

---

# 5. Tipos de Documento

Inicialmente suportados:

- NF-e (modelo 55)
- NFC-e (modelo 65)
- CT-e
- MDF-e
- XMLs auxiliares

Novos documentos poderão ser adicionados futuramente sem alteração da arquitetura.

---

# 6. Fluxo Geral

Todo XML segue o fluxo:
