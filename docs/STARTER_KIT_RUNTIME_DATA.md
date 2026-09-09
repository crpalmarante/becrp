# Starter Kit — Dados Runtime

Estado mutável da aplicação **não é versionado** (ver `.gitignore` e commit `9b36860`).
Cada módulo cria seu próprio arquivo com defaults/seeds quando ele não existe —
um clone fresco funciona sem nenhuma etapa manual de dados.

## Prova (clone fresco)

Verificado no commit `9b36860`:

```bash
git clone <repo> /tmp/fresh && cd /tmp/fresh
python3 -m pytest tests/ -q          # 253 passed
python3 server.py 8972               # sobe limpo, sem erros
```

Resultados do smoke em clone fresco:

| Verificação | Resultado |
|---|---|
| 253 testes | ✅ pass (criaram os arquivos abaixo sob demanda) |
| `/`, `/pages/configuracoes.html`, `/js/brand.js`, `/assets/data/menu.json` | ✅ 200 |
| `/api/settings`, `/api/organizacao/nome` sem token | ✅ 401 |
| `/data/users.json` (guarda estática) | ✅ 404 |
| 13 arquivos runtime antes do teste | ✅ inexistentes |

## Arquivos auto-criados por módulo

| Arquivo (caminho) | Módulo criador | Criado quando |
|---|---|---|
| `data/inventory_movements.json` | `inventory_mvp.py` | `load_movements()` → default `{"next_id": 1, "movements": []}` |
| `data/inventory_balances.json` | `inventory_mvp.py` | `load_balances()` → saldos vazios por estabelecimento |
| `data/receiving_pending.json` | `receiving_pending.py` | `_load()` → `{"next_id": 1, "items": []}` |
| `data/partner_lookup_audit.json` | `partner_lookup.py` | auditoria de lookups (mantém últimas 200 entradas) |
| `dados/empresa.json` | `org_store.py` | `sync_legacy_empresa_json()` — espelho legado p/ módulos SEFAZ |
| `dados/wms_receiving.json` | `wms_receiving.py` | `_load_raw()` → `ensure_seed()` |
| `dados/pos_commission_payroll.json` | `pos_commission.py` | folha de comissões do PDV |
| `dados/titulos_ap.json` | `purchase_finance.py` | contas a pagar de fornecedores |
| `dados/fiscal_reforma_history.json` | `fiscal_reforma_store.py` | histórico de cálculos da reforma fiscal |
| `dados/quality_check_results.json` | `quality_checks_store.py` | resultados de conferência (quality check) |
| `dados/accounting_integration_log.json` | `accounting_integration.py` | log de eventos enviados ao contabilidade |
| `dados/atributos.dat` | `cobol_bridge.py` | runtime COBOL (`gerir_atributos.cbl`); ausente → lista vazia |
| `*.json.lock` (qualquer diretório) | stores com escrita atômica | lock de concorrência durante escrita |
| `data/nfe_inbound/` | `nfe_inbound.py` | inbox de XMLs NF-e recebidos |
| `data/nfe_inbox/processed/` | processamento NF-e | XMLs já processados |

> Nota: pode existir um `data/titulos_ap.json` vazio (`{}`) criado por testes antigos
> (path legado). Ambos os caminhos estão no `.gitignore`; o módulo real usa `dados/`.

## O que É versionado (config, não runtime)

- `data/organizacao.json` — tenant/organização (bootstrap)
- `data/empresas.json` — estabelecimentos (matriz/filiais)
- `data/estabelecimentos_fiscal.json` — overlay fiscal por estabelecimento
  ⚠️ contém dados sensíveis (ex.: CSC NFC-e). O servidor bloqueia esse path
  por acesso estático (`server._is_sensitive_static_path`); não distribuir o repo.
- `dados/settings.json` — preferências de módulos
- Tabelas fiscais estáticas: `dados/Tabela_NCM.json`, etc.

## Regras para novos módulos

1. Nenhum dado de negócio/estado em JSON versionado — use `data/` ou `dados/` + `.gitignore`.
2. Loader tolerante: arquivo ausente → default/seed (nunca `FileNotFoundError`).
3. Escrita atômica com lock (`*.json.lock`) para concorrência entre threads/CGI.
4. Ao introduzir um novo arquivo runtime, adicione-o ao `.gitignore` **e** a esta tabela.
