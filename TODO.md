# TODO — Módulo Fiscal ERP

## Prioridade Alta

- [ ] **NF-e modelo 55**
  - Builder XML (`nfe_xml.py`) com transporte, cobrança, info complementar
  - SEFAZ: autorização (lote síncrono/assíncrono), consulta, cancelamento, inutilização
  - URLs p/ 27 UFs (NfeAutorizacaoService, NfeConsultaService, NfeCancelamentoService)
  - Endpoints REST + UI

- [ ] **NFS-e** (Nota Fiscal de Serviços eletrônica)
  - Padrão ABRASF (cidades) vs Padrão Nacional (PGM)
  - Builder XML + comunicação com prefeituras
  - Endpoints + UI

## Prioridade Média

- [ ] **CT-e** (Conhecimento de Transporte eletrônico)
  - Estrutura básica + endpoints

- [ ] **MDF-e** (Manifesto de Documentos Fiscais eletrônico)
  - Estrutura básica + endpoints

- [ ] **SPED** (Sistema Público de Escrituração Digital)
  - SPED Fiscal (ICMS/IPI)
  - SPED PIS/COFINS
  - SPED Contribuições

- [ ] **Cálculo de tributos real**
  - ICMS: substituição tributária, difal, partilha
  - PIS/COFINS: regimes cumulativo/não-cumulativo
  - IPI
  - ISS

## Prioridade Baixa

- [ ] **DANFE NF-e** — PDF para modelo 55 (formato retrato A4)
- [ ] **Cache de certificados** — limpeza automática de arquivos .tmp antigos
- [ ] **Reemissão** — botão na UI para reemitir NFC-e/NF-e com erro
- [ ] **Importar XML** — endpoint para importar XML de terceiros
- [ ] **Contingência** — SCAN, SVC-AN, SVC-RS, EPEC
- [ ] **Relatórios fiscais** — apuração ICMS, PIS, COFINS
- [ ] **Testes** — homologação com SEFAZ RS (NFC-e)

## Melhorias

- [ ] Separar `CRT` do `empresa.json` em campos individuais (logradouro, numero, bairro, cidade, uf, cep)
- [ ] Adicionar campo `cnae_prim_codigo` e `cnae_prim_desc` no XML do emitente
- [ ] Busca automática de NCM/CEST por produto
- [ ] Tabela de CFOP por UF e operação
- [ ] Tabela de alíquotas interestaduais
