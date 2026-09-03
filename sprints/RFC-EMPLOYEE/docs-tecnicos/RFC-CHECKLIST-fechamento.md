# Checklist de Fechamento — RFCs do Módulo de Folha (RFC-001 a 016)

> Tabela única para auditar o **status** (implementação) e a **aprovação** de
> todos os RFCs de `rfcs/` de uma vez. Gerado em 10/08/2026; RFC-009, RFC-014 e
> RFC-015 atualizados em 11/08/2026. Atualize as linhas
> quando um RFC mudar de estado (o resumo do status vive no cabeçalho do próprio
> RFC; este documento é o painel agregado).

## 1. Painel Geral

| RFC | Título | Status | Aprovação | Fechado? |
|---|---|---|---|---|
| RFC-001 | Conceitos gerais do sistema de Folha de Pagamento | ✅ Concluído (11/08/2026) — conceitual, sem código | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-002 | Cadastro de Funcionário: o que cadastrar | ✅ Implementado (31/07/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-003 | Processos de Admissão e Demissão (Rescisão) | ✅ Implementado (09/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-004 | Conceito de Evento: proventos, descontos e sua aplicação | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-005 | Conceito de tabelas fiscais: INSS, IRRF e salário-família | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-006 | O processo mensal: do fechamento ao pagamento | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-007 | Conceito e conteúdo do holerite | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-008 | Cadastros mestres: Empresa, Departamentos e Cargos | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-009 | Usuários, papéis, autorização e trilha de auditoria | ✅ Implementado (11/08/2026) | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-010 | Processo de férias: aquisição, gozo e pagamento | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-011 | Processo de 13º salário (gratificação natalina) | ✅ Implementado (10/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |
| RFC-012 | Afastamentos, licenças e suspensões do vínculo | ✅ Implementado (11/08/2026) | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-013 | Folha complementar: ajustes de competência fechada | ✅ Implementado (11/08/2026) | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-014 | Encargos patronais: FGTS, INSS patronal, RAT e terceiros | ✅ Implementado (11/08/2026) | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-015 | Relatórios gerenciais e fechamento da competência | ✅ Implementado (11/08/2026) | ✅ Aprovado (11/08/2026) | ✅ |
| RFC-016 | Movimentações contratuais: alterações com vigência | ✅ Implementado (09/08/2026) | ✅ Aprovado (10/08/2026) | ✅ |

**Resumo:** 16/16 Aprovado · 16 RFCs totalmente fechados (001 a 016). 🎉

> O RFC-001 (conceitual) foi formalmente encerrado em 11/08/2026: sem código
> próprio por natureza, seu conteúdo está materializado nos RFCs 002–016 e
> aprovado como documento de referência do módulo.

## 2. O que falta para fechar cada RFC

| RFC | Status | Bloqueio para o fechamento |
|---|---|---|
| RFC-001 | ✅ Fechado | Documento conceitual aprovado como referência do módulo (11/08/2026); conteúdo materializado nos RFCs 002–016 |
| RFC-002 | ✅ Fechado | — |
| RFC-003 | ✅ Fechado | — |
| RFC-004 | ✅ Fechado | — |
| RFC-005 | ✅ Fechado | — |
| RFC-006 | ✅ Fechado | — |
| RFC-007 | ✅ Fechado | — |
| RFC-008 | ✅ Fechado | — |
| RFC-009 | ✅ Fechado | — |
| RFC-010 | ✅ Fechado | — |
| RFC-011 | ✅ Fechado | — |
| RFC-012 | ✅ Fechado | — |
| RFC-013 | ✅ Fechado | — |
| RFC-014 | ✅ Fechado | — |
| RFC-015 | ✅ Fechado | — |
| RFC-016 | ✅ Fechado | — |

## 3. Critérios usados nesta auditoria

- **✅ Implementado** = evidência de implementação real no código + cobertura no
  CI (smoke/review/check Node). Ex.: RFC-006/007/008 têm smoke dedicado
  (`smoke_rfc006_folha`, `smoke_rfc007_holerite`, `smoke_rfc008_empresa`).
- **✅ Concluído** = RFC-001 (conceitual): sem código próprio por natureza;
  encerrado como documento de referência quando todo o restante do módulo foi
  implementado (cada conceito materializado em um RFC 002–016). Os RFCs
  operacionais (002–016) seguem o critério **Implementado** (evidência de código
  + cobertura no CI) + **Aprovado** (voto).
- **Fechado ✅** = Implementado **e** Aprovado (voto registrado na tabela §8 do RFC).
- A aprovação é voto do revisor humano na tabela de Aprovação do próprio RFC;
  o autor pode aprovar (padrão usado no RFC-010/011).

### Como rodar o CI (run_ci.py)

O pipeline de CI do módulo é `scripts/run_ci.py` (build COBOL → seed → smokes
RFC → reviews de tela via HTTP → checks de render Node → restauração do seed):

```bash
python3 scripts/run_ci.py             # suíte completa
python3 scripts/run_ci.py --no-build  # pula a recompilação do COBOL
python3 scripts/run_ci.py --browser   # adiciona o passo 9 (cenários visuais)
```

O **passo 9 (opcional, `--browser`)** sobe os mesmos cenários usados com
browser-use para conferência visual em navegador real e valida o seed via HTTP
antes de encerrar (com restauração dos dados):

| Cenário | Porta | Seed validado | GET |
|---|---|---|---|
| `cenario_complementar_browser.py` | 8141 | 4 complementares nos estados C/V/F/P (aba Complementar, RFC-013) | `/api/folha/complementares` |
| `cenario_rescisao_browser.py` | 8142 | 2 rescisões — 1 com `ferias_venc_dobro=True` (EM DOBRO) + 1 normal (aba Rescisão, RFC-003) | `/api/folha/rescisoes` |

Para conferência visual manual (badges de situação, botões por estado, badge
EM DOBRO, modais), rode o cenário diretamente e deixe o servidor vivo:
`python3 scripts/cenario_complementar_browser.py --port 8141` (ou o da
rescisão, porta 8192 por padrão) — Ctrl+C encerra e restaura os dados.

---

*Checklist gerado em 10/08/2026 a partir dos cabeçalhos/seções de `rfcs/`
(status + aprovação) e da auditoria contra o código (COBOL, server.py,
cobol_bridge.py, pages e scripts/run_ci.py).*

