# RFC-0070 — Bank Integration Architecture

**Status:** Draft

**RFC:** 0070

**Categoria:** Finance Engine

**Módulo:** Bank Integration Core

**Prioridade:** Arquitetura Fundamental

**Versão:** 1.0

**Dependências:**

* RFC-0100 (Arquitetura dos Motores Centrais)
* RFC-0050 (Finance Engine)
* RFC-8000 a RFC-8009 (Accounting Engine)
* RFC-0060 (Compliance Engine)

**Integra com:**

* Finance Engine
* Accounting Engine
* Compliance Engine
* Plataforma (BC-006 — trilha de eventos)

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

Definir a arquitetura oficial do Bank Integration.

O Bank Integration é o **canal que traz o extrato bancário para dentro da plataforma** e o converte em **fatos financeiros neutros**: cada lançamento do banco vira um evento que o Finance Engine concilia com os movimentos internos e o Accounting Engine posta.

Ele **não é um motor de processamento** como o Accounting ou o Tax. Ele é o **adapter universal** do banco: importa, normaliza, classifica e entrega o extrato em um único modelo canônico.

**Regra central:** o Bank Integration **nunca conhece o plano de contas**, **nunca posta partidas** e **nunca decide** o que é receita/despesa. Ele importa e normaliza; a classificação contábil é do mapping (RFC-0100, seção 7) e a conciliação é do Finance.

Ele não pertence ao ERP.

Ele pode ser utilizado por qualquer aplicação.

---

# 2. Visão

O Bank Integration deve funcionar como uma biblioteca ou serviço.

Exemplos de consumidores.

```text
ERP

Financeiro / Tesouraria

Contabilidade

Auditoria

CFO

API

CLI

Batch

Microserviços
```

Todos utilizam exatamente o mesmo motor.

---

# 3. Princípios

O projeto segue os princípios.

## P1

Não conhece banco de dados.

---

## P2

Não conhece PostgreSQL.

---

## P3

Não conhece COBOL.

---

## P4

Não conhece Odoo.

---

## P5

Não pertence ao ERP.

---

## P6

O extrato importado é **imutável**: o que o banco diz é a verdade de origem. Correções são eventos novos, nunca edição do importado.

---

## P7

Cada formato de origem é um **adapter** atrás de uma mesma interface de parser. Adicionar um banco/formato nunca altera o núcleo.

---

## P8

O resultado do parse é um **modelo canônico neutro** (Bank Statement): sem contas contábeis, sem partidas, sem julgamento de negócio.

---

# 4. Regras

* nunca conhece o plano de contas;
* nunca posta partidas;
* nunca decide classificação contábil;
* nunca reescreve um extrato importado;
* idempotente por extrato (chave de banco);
* toda conversão de valor usa aritmética decimal (`Decimal`), nunca float;
* datas sempre normalizadas com fuso e referência de tempo (BC-006).

---

# 5. Compatibilidade

Implementações previstas.

```text
Python

COBOL

REST

gRPC

CLI

Docker
```

Todas compartilham o mesmo núcleo lógico.

---

# 6. Arquitetura

## 6.1 Visão de camadas

```text
Fontes (importação / integração)

OFX   OFC   CNAB240   CNAB400   CSV   XLSX   MT940   CAMT.053   Open Finance/Banking
 │      │      │         │       │     │       │        │              │
 └──────┴──────┴─────────┴───────┴─────┴───────┴────────┴──────────────┘
                                     │
                            Parsers (adapters)
                                     │
                                     ▼
                        Modelo canônico (Statement)
                                     │
                                     ▼
                  Normalização / enriquecimento / classificação
                                     │
                                     ▼
                        Bank Statement Store (imutável)
                                     │
                                     ▼
                Eventos publicados (finance_statement_imported)
                                     │
                                     ▼
                 Finance (conciliação) → Accounting (postagem)
```

## 6.2 Ports (interfaces)

```text
Statement Parser       → importar_bytes → Statement

Statement Normalizer   → normalizar(Statement) → Statement

Statement Validator    → validar(Statement) → erros

Statement Publisher    → publicar(Statement) → eventos

Bank Account Resolver  → resolver(bank_code, agency, account) → BankAccount

Logger / Clock / Event Bus (BC-006)
```

## 6.3 Adapters (implementações)

```text
OFX (1.0.2 / 2.x)

OFC

CNAB 240 (retorno)

CNAB 400 (retorno)

CSV (por banco)

XLSX (por banco)

MT940 (SWIFT)

CAMT.053 (ISO 20022)

Open Finance / Open Banking (API)
```

---

# 7. Modelo Canônico (Statement)

Todos os formatos convergem para o mesmo modelo.

```text
BankStatement
├── id (chave imutável do extrato na origem)
├── banco          (código BACEN, ex.: 001, 341, 237)
├── agencia
├── conta          (número + dígito)
├── tipo_conta     (corrente / poupança / pagamento)
├── moeda          (BRL)
├── data_importacao
├── saldo_inicial
├── saldo_final
├── lancamentos[]  (BankTransaction)
│     ├── id (chave única na origem — memo/ref do banco)
│     ├── data
│     ├── data_credito (validação)
│     ├── descricao    (memo do banco)
│     ├── tipo (D/C / entrada/saída)
│     ├── valor         (Decimal, nunca float)
│     ├── categoria_raw (campo do banco, se houver)
│     ├── refs[]        (identificadores: PIX, boleto, cheque, doc/ted)
│     └── metadados     (por formato, preservados)
└── fonte (formato de origem)
```

Regras do modelo:

- valores são `Decimal`;
- `lancamentos` preservam a ordem do extrato;
- nenhum campo contábil existe aqui — classificação é downstream;
- os `metadados` preservam o que o formato trouxe (para auditoria e re-importação).

---

# 8. Contrato de Eventos

| Evento | Publicado por | Consumido por |
|---|---|---|
| `finance_statement_imported` | Bank Integration | Finance (conciliação) |
| `finance_statement_duplicate` | Bank Integration | — (log) |
| `finance_reconciliation_adjustment` | Finance | Accounting |

Regras:

- eventos são imutáveis após publicados;
- um extrato importado gera um único `finance_statement_imported`;
- importação duplicada não re-emite evento — retorna `duplicate`.

---

# 9. Importação

## 9.1 Fluxo

```text
bytes do arquivo (ou payload de API)
        │
        ▼
detecta formato (extensão / conteúdo / autodescrição)
        │
        ▼
parse → Statement canônico
        │
        ▼
valida (balanço: saldo inicial + Σ lançamentos == saldo final)
        │
        ▼
idempotência (já importado? → duplicate)
        │
        ▼
persistência imutável
        │
        ▼
publica finance_statement_imported
```

## 9.2 Idempotência

Chave de idempotência: hash canônico do extrato (banco + agência + conta + data + saldos + lista de lançamentos) ou a chave nativa do formato (ex.: `BANKMSGSRSV1` de OFX).

---

# 10. Conciliação (relação com o Finance)

O Bank Integration entrega o extrato; a **conciliação** é do Finance Engine (RFC-0050 §11.4, §14):

```text
Extrato (Bank Integration)
        │
        ▼
Pareamento automático com movimentos internos
(títulos, PIX, boletos, docs, valores, datas)
        │
        ▼
Casado → conciliado
        │
Divergente / sem par → análise
        │
        ▼
Ajustes aprovados → reconciliation_adjustment → Accounting posta
```

O pareamento é heurístico e configurável (parâmetros por banco/forma), nunca posta partidas.

---

# 11. Formatos (roadmap de adapters)

## 11.1 OFX — MVP ✅ prioridade

Formato XML aberto (1.0.2 e 2.x). Padrão de exportação da maioria dos bancos BR (BB, Bradesco, Itaú, Santander, Caixa, Nubank etc.).

## 11.2 CSV — MVP ✅ prioridade

Layout por banco; cada banco tem seu próprio adapter de CSV. É o formato mais comum de download manual.

## 11.3 CNAB 240 / 400 — MVP ✅ prioridade

Retornos bancários (cobrança, pagamentos). Segmentos definidos por posição fixa; necessário parse posicional.

## 11.4 XLSX

Exports de planilha; mesma estratégia do CSV (adapter por banco).

## 11.5 OFC

Antecessor do OFX (texto). Baixa demanda; adapter dedicado.

## 11.6 MT940 (SWIFT)

Padrão internacional para bancos corporativos (câmbio, contas globais).

## 11.7 CAMT.053 (ISO 20022)

Sucessor do MT940; XML corporativo. Alta demanda em contas globais.

## 11.8 Open Finance / Open Banking (API)

Integração direta por API (BR Open Finance / UK Open Banking). Exige certificação, token e consentimento; arquitetura de client OAuth.

---

# 12. Segurança e Privacidade

- dados bancários são **sensíveis**: criptografia em repouso para extratos importados;
- consentimento e escopo de acesso por conta (Open Finance/Banking);
- credenciais/segredos nunca em código nem em logs;
- trilha de auditoria de cada importação (quem, quando, formato, hash);
- exposição por API restrita a roles (financeiro/auditoria).

---

# 13. Performance

Metas.

Importação e parse de extrato (até 10.000 lançamentos):

< 2 s

Validação de balanço do extrato:

< 500 ms

Pareamento de conciliação (extrato do mês × movimentos do mês):

< 5 s

---

# 14. Observabilidade

Métricas.

* extratos importados por banco/formato/dia;
* duplicatas detectadas;
* tempo de parse por formato;
* taxa de conciliação automática (casado/total);
* divergências em aberto por banco.

---

# 15. Relação com os Outros Motores

```text
Banco (arquivo/API)
        │
        ▼
Bank Integration → extrato canônico (fato neutro)
        │
        ▼
Finance → conciliação (casamento com títulos/movimentos)
        │
        ▼
Accounting → postagem (mapping financeiro → contábil)
        │
        ▼
Compliance → fechamento financeiro (CP-03)
```

O Bank Integration fica **antes** do Finance: ele não concilia nem posta. Ele é a ponte entre o banco e o modelo financeiro da plataforma.

---

# 16. Roadmap

## Sprint BI-01 ✅

**Importação OFX + CSV — MVP — concluído.**

* modelo canônico `Statement`/`BankTransaction` (valores `Decimal`, nunca float);
* parsers OFX (1.0.2/2.x) e CSV (adapters por banco via mapeo de colunas com detecção automática);
* validação de balanço (`saldo inicial + Σ lançamentos == saldo final`, tolerância R$ 0,02);
* idempotência por hash canônico do extrato (`finance_statement_duplicate`);
* persistência imutável (`dados/bank_statements.json`) + eventos `finance_statement_imported`;
* resolver de contas bancárias (`dados/bank_accounts.json`);
* endpoints REST: `POST /api/bank/importar`, `GET /api/bank/status`, `GET /api/bank/extratos`, `GET /api/bank/lancamentos`, `GET /api/bank/contas`;
* smoke E2E (`scripts/smoke_bank_integration_e2e.py`) com OFX e CSV de teste (auto + débito/crédito + refs), validação de balanço e idempotência.

## Sprint BI-02 ✅

**CNAB 240 / 400 (retorno) — concluído.**

* parser posicional CNAB240 (Segmento T, layout FEBRABAN) e CNAB400 (layout clássico) → modelo canônico;
* normalização: banco/agência/conta do header, movimento, vencimento (DDMMAAAA), data de crédito, valor (Decimal), nosso número, número do documento, tarifa;
* código de movimento de retorno normalizado para tipo D/C (liquidação 06/09/17);
* detecção automática de formato por conteúdo (linha 240 com tipo '0'/'1'/'3', ou 400);
* conciliação de títulos a partir dos retornos (Finance): casamento por nosso número / documento / fatura / pedido (match exato + parcial) e baixa do título AR aberto;
* evento finance_reconciliation_adjustment quando há liquidações;
* smoke E2E estendido (scripts/smoke_bank_integration_e2e.py): retorno CNAB240 liquida e baixa AR-00002 (FV99001, 32,90 → pago), CNAB400 parse, idempotência e detecção automática.

---## Sprint BI-03

**Conciliação bancária (Finance Engine).**

* pareamento automático extrato × movimentos internos (títulos, PIX, boleto);
* sugestão de ajustes (taxas, juros, diferenças);
* aprovação → `reconciliation_adjustment` → Accounting posta;
* smoke E2E de conciliação completa.

## Sprint BI-04

**XLSX, OFC, MT940, CAMT.053.**

* adapters adicionais sobre o mesmo núcleo;
* validação com amostras reais de cada formato.

## Sprint BI-05

**Open Finance / Open Banking (API).**

* cliente OAuth com consentimento;
* sincronização automática de extratos;
* certificação e sandbox.

---

# 17. Objetivo Final

O Bank Integration deve ser capaz de transformar **qualquer fonte bancária** — arquivo ou API, nacional ou internacional — em um único extrato canônico, imutável e auditável, que o Finance concilia e o Accounting posta. Ele é a ponte entre o banco e a verdade contábil: o ponto em que "o banco diz" vira fato de negócio dentro da plataforma.
