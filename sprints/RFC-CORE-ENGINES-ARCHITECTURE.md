# RFC-0100 — Arquitetura dos Motores Centrais

| Campo | Valor |
|--------|-------|
| RFC | RFC-0100 |
| Título | Arquitetura dos Motores Centrais (Fiscal, Tax, Finance, Accounting, Compliance) |
| Categoria | Plataforma — Arquitetura |
| Status | Draft |
| Versão | 1.0 |
| Depende de | BC-000 a BC-101 (BusinessCore), TAX_ENGINE_CONTRACT |
| Integra com | Vendas, Receiving, WMS, Delivery, POS, Purchase, Inventory |

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

Definir a arquitetura oficial dos motores centrais da plataforma e o contrato de eventos que os integra.

Esta RFC estabelece:

- as fronteiras de responsabilidade de cada componente;
- o que é **domínio de negócio** e o que é **motor de processamento**;
- o contrato de eventos entre eles (quem publica, quem consome, o que o evento carrega);
- a regra de mapping financeiro → contábil;
- o papel do fechamento como critério de integridade.

---

# 2. Motivação

Uma operação de venda gera, a partir do **mesmo evento de negócio**, uma operação fiscal (documento, impostos) e lançamentos contábeis.

Cada módulo evolui em ritmo próprio. Evoluir separado é tecnicamente possível, mas incorreto **por causa do fechamento**: o fechamento fiscal, o fechamento contábil e o fechamento financeiro precisam concordar. Se Fiscal e Contábil evoluírem com contratos divergentes, a conciliação (SPED, DRE × apuração de impostos, caixa × razão) vira retrabalho manual.

A resposta não é acoplar os módulos, e sim separá-los em componentes com responsabilidade única, ligados por **um contrato de eventos único e versionado**.

---

# 3. Domínios × Motores (princípio estrutural)

A plataforma separa dois papéis fundamentais:

**Domínios de negócio** — produzem e consomem eventos:
- Vendas (POS), Receiving, Inventory, WMS, Delivery, Purchase
- **Fiscal Engine** (documentos fiscais)
- **Finance Engine** (ciclo financeiro operacional)

**Motores de processamento** — consumidores transversais, com responsabilidade única:
- **Tax Engine** (cálculo tributário — o único que calcula impostos)
- **Accounting Engine** (fatos contábeis — o único que conhece plano de contas)
- **Compliance Engine** (obrigações acessórias e auditoria fiscal)

### Regra de ouro

Nenhum domínio ou motor escreve o evento de outro. Cada componente **publica o seu próprio evento** e **consome apenas o que lhe diz respeito**.

Exemplos de fronteiras garantidas por essa regra:

- AR não escreve lançamento contábil.
- Accounting não gera título financeiro nem emite boleto.
- Fiscal Engine não calcula tributo.
- Finance Engine não conhece código de conta contábil.

---

# 4. Os Cinco Componentes

## 4.1 Fiscal Engine (domínio)

Responsável pelo ciclo de vida do documento fiscal:

- NF-e, NFC-e, CT-e, MDF-e, NFS-e, SAT, CF-e
- Eventos: autorização, cancelamento, carta de correção, inutilização, manifestação do destinatário

**Nunca calcula impostos.** Consome o bloco de tributos calculados produzido pelo Tax Engine para montar o documento.

## 4.2 Tax Engine (motor)

Responsável apenas pelo cálculo tributário:

- ICMS, ICMS-ST, FCP, DIFAL, FECP
- IPI, PIS, COFINS, ISS
- IBS, CBS (reforma tributária)
- Imposto de Importação, retenções

Entrada:

- Produto, Empresa, Cliente
- Origem, Destino, CFOP, NCM
- Quantidade e valores

Saída — o **bloco "tributos calculados"**, contrato único consumido por:

- **Fiscal Engine** (montagem do XML/danfe)
- **Accounting Engine** (posting: ICMS a recolher, PIS a recuperar, etc.)
- **Compliance Engine** (apuração SPED)

É o único componente que sabe "quanto de imposto".

## 4.3 Finance Engine (domínio)

Responsável pelo ciclo financeiro operacional:

- Accounts Receivable (AR), Accounts Payable (AP)
- Treasury, Cash Management, Cash Flow
- Contas bancárias, extratos, conciliação bancária
- Agendamento de pagamentos, cobranças, controle de crédito
- Meios de pagamento: PIX, TED, DOC, Boleto, Cartão de Débito, Cartão de Crédito

Conhece títulos financeiros, vencimentos, liquidações e saldos de caixa.

**Nunca conhece plano de contas.** Publica fatos financeiros neutros (ex.: `pagamento R$ 100, forma PIX, conta bancária X`).

## 4.4 Accounting Engine (motor)

Responsável apenas pelos fatos contábeis:

- Chart of Accounts (plano de contas)
- Journal Entries, General Ledger (diário e razão)
- Trial Balance (balancete)
- Balance Sheet (balanço), Income Statement / P&L (DRE)
- Centros de custo e rateios
- Períodos fiscais/contábeis, fechamento e abertura de exercício

**Nunca conhece NF-e, boleto, PIX ou meios de pagamento.** Apenas registra os lançamentos decorrentes dos eventos desses domínios.

A regra de **mapping financeiro → contábil** é responsabilidade deste motor (ver seção 7).

## 4.5 Compliance Engine (motor)

Responsável pelas obrigações acessórias e pela reconciliação com o fisco:

- SPED Fiscal (EFD), SPED Contribuições, SPED Contábil (ECD/ECF)
- DCTF, REINF, Sintegra
- Obrigações acessórias em geral

É o **lar do fechamento**: é aqui que a apuração fiscal e os lançamentos contábeis precisam concordar nos totais.

Escopo: **Auditoria não pertence a este motor.** Auditoria é capacidade transversal, apoiada na trilha de eventos do BusinessCore (BC-006), não uma obrigação acessória.

---

# 5. Contrato de Eventos (quem publica × quem consome)

O evento canônico é a língua comum entre os componentes. Ele segue o modelo do BusinessCore (BC-006) e carrega, por operação, **todos os ângulos** que os consumidores podem precisar.

| Evento | Publicado por | Consumido por |
|---|---|---|
| Venda finalizada | Vendas (POS) | Tax, Fiscal, Finance, Accounting, Compliance |
| Tributos calculados | Tax Engine | Fiscal, Accounting, Compliance |
| Documento autorizado | Fiscal Engine | Compliance |
| Título / parcela gerada | Finance Engine | Accounting, Compliance |
| Pagamento liquidado | Finance Engine | Accounting |
| Recebimento concluído | Receiving | Tax, Finance, Accounting |
| Fechamento de período | Accounting Engine | Compliance |
| Conciliação bancária | Finance Engine | Accounting, Compliance |

### Princípios do contrato

1. **Evento único, leitura seletiva.** Cada consumidor lê apenas o que lhe diz respeito (o financeiro lê parcelas; o contábil lê tributos e líquido).
2. **Não-bloqueante.** A operação não quebra se um motor falhar (princípio já adotado: "a operação não quebra se a contabilidade falhar").
3. **Versionado.** O contrato do evento é versionado de forma independente dos motores; mudanças de contrato são feitas em conjunto pelos consumidores.
4. **Imutável após publicado.** Eventos históricos não são reescritos; correções geram novos eventos (reversão + novo lançamento).

---

# 6. Exemplo: ciclo completo de uma venda

```
1. Venda finalizada (POS)
     → publica evento "venda" (itens, qtd, preço, forma de pg, campanhas/troca)

2. Tax Engine
     → calcula tributos por item (ICMS, PIS, COFINS...)
     → publica "tributos calculados"

3. Finance Engine
     → gera título/parcelas (AR) conforme termos
     → publica "título gerado"

4. Fiscal Engine
     → monta e autoriza a NFC-e/NF-e usando o bloco de tributos
     → publica "documento autorizado"

5. Accounting Engine
     → posta receita líquida, ICMS a recolher, CMV, contas a receber/caixa
     → registra no razão, período corrente

6. Compliance Engine
     → alimenta EFD (dados fiscais) e ECD/ECF (dados contábeis)
     → concilia totais: apuração de impostos = lançamentos provisionados
```

Nenhum passo depende de outro para a operação **comercial** prosseguir; a consistência é garantida no fechamento.

---

# 7. Mapping Financeiro → Contábil

A Finance Engine publica **fatos neutros**; o Accounting Engine os converte em lançamentos.

O mapping é uma **regra de configuração do Accounting Engine**, persistida em
`dados/accounting_mapping.json` (`accounting_mapping.py`) — exposta em
`GET/PUT /api/admin/accounting/mapping`:

| Fato financeiro | Regra de mapping (Accounting) |
|---|---|
| Forma de pg / conta bancária | conta GL correspondente (caixa, banco, contas a receber...) |
| Recebimento de título | débito na conta do meio (caixa/banco) × crédito em AR |
| Pagamento de fornecedor | débito em AP × crédito na conta do meio |
| Ajuste de conciliação (taxa, juros) | conta de despesa/receita financeira definida no plano |

Exemplos ilustrativos com contas do plano referencial já usadas no repo:

- Dinheiro → `1.01.01.01.01` (Caixa)
- PIX/TED/Banco → `1.01.01.02.01` (Banco)
- Venda à vista → débito meio de pg × crédito `3.01.01.01.01.05` (Receita de Vendas)
- Compra a prazo → débito `1.01.03.01.01` (Estoques) × crédito `2.01.01.03.01` (Fornecedores)

Finance nunca precisa saber esses códigos. A troca de conta contábil de um meio de pagamento é uma mudança de configuração **contábil**, sem impacto no domínio financeiro.

O mapping implementado cobre hoje:

- `payment_methods`: forma de pagamento (fato financeiro) → evento/regra de posting + conta de débito (ex.: `Dinheiro → sale_cash → 1.01.01.01.01`, `PIX/Banco → sale_bank → 1.01.01.02.01`), com aliases por meio;
- `tax_accounts`: tributo (ICMS/PIS/COFINS/IPI) → conta a recolher (fallback para as regras de posting sem `contas_impostos` próprias).

O `_map_forma_pg` do `accounting_integration.py` e as contas de recolhimento do `posting_engine.py` passaram a ler dessa configuração — a troca de conta de um meio/tributo não exige mais mudança de código.

---

# 8. Fechamentos e Reconciliations

Cada fechamento é responsabilidade do seu componente, e todos se reconciliam no Compliance Engine:

| Fechamento | Dono | Saída |
|---|---|---|
| Fechamento financeiro | Finance Engine | AR/AP liquidados, saldos de caixa, conciliação bancária |
| Fechamento contábil | Accounting Engine | períodos encerrados, DRE/Balanço, abertura de exercício |
| Fechamento fiscal | Tax + Fiscal Engine | apuração de impostos do período |
| Conciliação com o fisco | Compliance Engine | EFD × ECD/ECF, DCTF, REINF concordantes |

O fechamento é o **critério de aceite** de qualquer mudança: uma alteração em Fiscal ou Tax ou Finance ou Accounting só passa se os fechamentos continuarem batendo.

---

# 9. Alinhamento com o estado atual do repositório

| Componente | Estado atual |
|---|---|
| Tax Engine | Já especificado em `fiscalui/docs/TAX_ENGINE_CONTRACT.md` e `TAX_RULES_MATRIX.md`; **RFC-0040** (`RFC-TAX-ENGINE-ARCHITECTURE.md`) consolida a arquitetura; embrião em `modules/sefaz/tributos.py` |
| Fiscal Engine | **RFC-0030 v2.0** (`RFC-FISCAL-ENGINE-ARCHITECTURE.md`) — separado do cálculo; só documentos fiscais, consumindo o TaxBreakdown do Tax Engine |
| Accounting Engine | `RFC-8000` a `RFC-8009`; implementado em `accounting_*.py`, `posting_engine.py`, `journals.py`, `ledger.py`; mapping financeiro→contábil em `accounting_mapping.py` |
| Finance Engine | **RFC-0050** (`RFC-FINANCE-ENGINE-ARCHITECTURE.md`) — arquitetura definida; embriões existentes: `sales_finance.py` (AR), `purchase_finance.py` (AP) |
| Compliance Engine | **RFC-0060** (`RFC-COMPLIANCE-ENGINE/RFC-0060-COMPLIANCE-ENGINE-ARCHITECTURE.md`) — motor de fechamento e obrigações acessórias; nunca calcula, posta ou emite |
| Contrato de eventos | `accounting_integration.py` publica eventos de `pos_sale`, `receiving`, `inventory_adjust` via Posting Engine; o evento de venda carrega o bloco de tributos (posting tax-aware: receita líquida + impostos a recolher) **e o CMV** (baixa de estoque pelo custo, lançamento próprio no diário EST via regra `SALE_CMV`) |

---

# 10. Próximos passos

1. ✅ Revisar e separar a RFC-0030 em **Fiscal Engine** (documentos) e **Tax Engine** (cálculo) — **concluído**: RFC-0030 v2.0 (documentos) e RFC-0040 (Tax Engine).
2. ✅ Definir a RFC do **Finance Engine** (AR/AP/Treasury/Cash/Conciliação/Meios de pagamento) — **concluído**: RFC-0050.
3. ✅ Evoluir o **evento canônico de venda** para carregar o bloco de tributos (sair do posting "só pelo total") — **concluído**: `on_pos_sale` computa tributos via `modules/sefaz/tributos.py`; `apply_event` gera posting multi-linha (receita líquida + ICMS/PIS/COFINS a recolher).
4. ✅ Definir a **RFC do Compliance Engine** com o fechamento como critério de aceite — **concluído**: RFC-0060.
5. ✅ Formalizar o **mapping financeiro → contábil** como configuração do Accounting Engine — **concluído**: `accounting_mapping.py` + `dados/accounting_mapping.json` (formas de pagamento → regra/conta; tributos → contas a recolher), exposto na API.

---

# 11. Referências

- `fiscalui/docs/BC-000_MANIFESTO.md` — BusinessCore (fonte única das regras de negócio)
- `fiscalui/docs/BC-006_DOMAIN_EVENTS.md` — eventos de domínio
- `fiscalui/docs/TAX_ENGINE_CONTRACT.md` — contrato do Tax Engine
- `sprints/Fiscal-Engime/RFC-FISCAL-ENGINE-ARCHITECTURE.md` — RFC-0030 v2.0 (Fiscal Engine, documentos)
- `sprints/Fiscal-Engime/RFC-TAX-ENGINE-ARCHITECTURE.md` — RFC-0040 (Tax Engine, cálculo)
- `sprints/RFC-FINANCE-ENGINE/RFC-0050-FINANCE-ENGINE-ARCHITECTURE.md` — RFC-0050 (Finance Engine)
- `sprints/RFC-COMPLIANCE-ENGINE/RFC-0060-COMPLIANCE-ENGINE-ARCHITECTURE.md` — RFC-0060 (Compliance Engine, fechamento e obrigações acessórias)
- `sprints/RFC-ACCOUNTING-ARCHITECTURE/` — RFC-8000 a RFC-8009 (Accounting Core)
- `sprints/PHILOSOPHY.md` — filosofia da plataforma
