# TODO — Módulo Fiscal ERP

## ✅ Feito (concluído)

### Motores Centrais (RFC-0100)

- [x] **Posting Engine tax-aware** (RFC-0100 passo 3)
  - Venda → débito caixa/banco × crédito receita líquida + ICMS/PIS/COFINS a recolher (`apply_event` multi-linha)
  - Compra → débito estoque líquido + débito ICMS/PIS/COFINS a recuperar × crédito fornecedor (créditos de entrada)

- [x] **Compliance Engine** (RFC-0060)
  - CP-01: fechamento `fechamento(ano, mes)` reconcilia apuração (Tax) × provisionado (Accounting) × caixa (Finance); `fechamento_valido`/`fechamento_divergente`; `/api/compliance/*`
  - CP-02: saldo a recolher = débitos (vendas) − créditos (entradas); NF-e de entrada vira débito em tributos a recuperar; checagem "saldo a recolher apurado × provisionado"

- [x] **Mapping financeiro → contábil** (RFC-0100 passo 5)
  - `accounting_mapping.py` + `dados/accounting_mapping.json` (payment_methods, tax_accounts)
  - GET/PUT `/api/accounting/mapping` + `/api/admin/accounting/mapping`

- [x] **CMV na venda** — regra `SALE_CMV` (débito CMV × crédito estoque) publicada em `on_pos_sale`

### Bank Integration (RFC-0070)

- [x] **BI-01: Importação OFX + CSV (MVP)**
  - Modelo canônico Statement/BankTransaction (Decimal), validação de balanço, idempotência por hash
  - `POST /api/bank/importar` + `GET /api/bank/{status,extratos,lancamentos,contas}`

- [x] **BI-02: CNAB 240 / 400 (retorno)**
  - Parser posicional Segmento T (FEBRABAN) + layout CNAB400 clássico
  - Conciliação de títulos: retorno mov 06 liquida e baixa título AR (ex.: AR-00002 → pago)

- [x] **NF-e modelo 55**
  - Builder XML (`nfe_xml.py`) com transporte, cobrança, info complementar
    (schema 4.00 validável: `vFCPST`/`vFCPSTRet`, `vTotTrib`, IPI por item,
    `xPag` para PIX, `indPag` removido — NT 2020.006)
  - SEFAZ: autorização (lote síncrono/assíncrono), consulta, cancelamento, inutilização
  - URLs p/ 27 UFs (NfeAutorizacaoService, NfeConsultaService, NfeCancelamentoService,
    NfeInutilizacaoService)
  - Endpoints REST (`/api/admin/fiscal/nfe/*`) + UI (`pages/nfe.html`)

- [x] **NFS-e** (padrão ABRASF)
  - Builder XML (`nfse_xml.py`) + comunicação (`nfse_service.py`)
  - Endpoints + UI (`pages/nfse.html`)
  - Obs.: padrão Nacional (PGM) ainda não coberto

- [x] **CT-e** (Conhecimento de Transporte eletrônico)
  - Estrutura básica (`cte_xml.py`) + endpoints

- [x] **MDF-e** (Manifesto de Documentos Fiscais eletrônico)
  - Estrutura básica (`mdfe_xml.py`) + endpoints

- [x] **SPED** (Sistema Público de Escrituração Digital)
  - SPED Fiscal (ICMS/IPI) — EFD leiaute 017: Blocos 0, C, E, G, H, 9
    (participantes, produtos, notas, apuração ICMS, inventário)
  - SPED PIS/COFINS / Contribuições — EFD-Contribuições leiaute 010: Blocos 0, M, 9
  - Endpoints (`/api/admin/fiscal/sped/fiscal`, `/sped/pis`) + UI (`pages/sped.html`)

- [x] **DANFE NF-e** — PDF modelo 55 (retrato A4) em `modules/sefaz/danfe.py`

- [x] **Importar XML** — entrada de NF-e de fornecedores via `nfe_inbound` + `nfe_monitor`

- [x] **`cnae_prim_codigo` no XML do emitente** (`CNAEFiscal`)

## Em andamento / parcial

- [ ] **Compliance CP-03** — fechamento financeiro: caixa/bancos (Finance) × escrituração (Accounting)
- [ ] **Compliance CP-04** — SPED Fiscal (EFD ICMS/IPI) e Contribuições (EFD PIS/COFINS)
- [ ] **Compliance CP-05** — SPED Contábil (ECD) e ECF
- [ ] **Compliance CP-06** — DCTF/DCTFWeb, REINF/eSocial, Sintegra

- [ ] **Bank Integration BI-03** — conciliação bancária completa (Finance): pareamento extrato × movimentos internos, ajustes (taxas, juros) → Accounting posta
- [ ] **Bank Integration BI-04** — XLSX, OFC, MT940 (SWIFT), CAMT.053 (ISO 20022)
- [ ] **Bank Integration BI-05** — Open Finance / Open Banking (API OAuth + consentimento)

- [ ] **Cálculo de tributos real** (`tributos.py` cobre ICMS interno/interestadual,
      difal, PIS/COFINS cumulativo/não-cumulativo, IPI, ISS)
  - ICMS: substituição tributária (ST) e partilha mais completa
  - Alíquotas por produto/UF

## Prioridade Baixa (pendente)

- [ ] **Cache de certificados** — limpeza automática de arquivos .tmp antigos
- [ ] **Reemissão** — botão na UI para reemitir NFC-e/NF-e com erro
- [ ] **Contingência** — SCAN, SVC-AN, SVC-RS, EPEC
- [ ] **Relatórios fiscais** — apuração ICMS, PIS, COFINS (dashboard)
- [ ] **Testes** — homologação com SEFAZ RS (NFC-e)

## Melhorias

- [x] Separar endereço/CRT do `empresa.json` em campos individuais (org_store + sync legado)
- [x] Busca automática NCM/CEST por produto (dados `ncm.json`, `cest.json`, `ncm_cest.json`)
- [ ] Tabela de CFOP por UF e operação
- [ ] Tabela de alíquotas interestaduais (hoje homogênea em `tributos.py`)

### Compras (MVP)

- [x] **CRUD de pedidos de compra** (`gerir_pedidos_compra` + `gerir_itens_ped_compra`)
- [x] **API e store Python** (`compras_store.py`) + endpoints `/api/compras`
- [x] **Tela `pages/compras.html`** com status, itens, aprovação e link para recebimento
- [x] **Acordos de Compra (Call for Tender)** (`gerir_acordos_compra` + `gerir_itens_acordo_compra`)
  - criação de acordo com itens a cotar
  - recebimento de propostas de fornecedores (preço, prazo, frete, condição)
  - fechamento e escolha da melhor cotação
  - conversão automática do vencedor em pedido de compra
- [x] **Tela `pages/acordos-compra.html`** para gerenciar acordos/cotações
