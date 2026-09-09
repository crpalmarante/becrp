# BECRP · ERP

[![CI](https://github.com/crpalmarante/becrp/actions/workflows/ci.yml/badge.svg)](https://github.com/crpalmarante/becrp/actions/workflows/ci.yml)

Sistema de gestão (PDV, estoque/WMS, fiscal NF-e/NFC-e/SPED, financeiro, folha
de pagamento, entregas) operado pela **COMERCIAL FABIELI LTDA**.

- **Backend:** Python 3 (stdlib, `server.py`) + bridge COBOL (GnuCOBOL) para
  rotinas de RH/parceiros/atributos (`cobol/`)
- **Frontend:** páginas HTML/JS servidas estaticamente, marca dinâmica via
  `js/brand.js` + `/api/organizacao/nome`
- **Dados:** JSON/DAT em `data/` e `dados/` — estado runtime **não versionado**
  (ver [docs/STARTER_KIT_RUNTIME_DATA.md](docs/STARTER_KIT_RUNTIME_DATA.md))

## Quickstart

```bash
git clone https://github.com/crpalmarante/becrp.git
cd becrp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# libs de sistema (Ubuntu/Debian) — PDF/DANFE e build COBOL:
sudo apt-get install -y gnucobol libpango-1.0-0 libpangocairo-1.0-0 \
  libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info

python3 server.py            # default: porta 8080 (ou: python3 server.py 9000)
```

No primeiro acesso o próprio sistema abre o fluxo de configuração inicial
(usuário admin + identidade da empresa via **Configurações → Empresas**).

## Testes

```bash
python3 -m pytest tests/ -q
```

## CI

O workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) roda dois jobs
a cada push/PR:

| Job | O que faz |
|---|---|
| `test` | Build COBOL + seed + smokes RFC + reviews de tela (`scripts/run_ci.py --force-build`) |
| `bootstrap` | Prova de clone fresco: guarda de arquivos versionados + bootstrap completo |

## Scripts para contribuidores

| Script | Uso | O que valida |
|---|---|---|
| `scripts/bootstrap_check.sh` | `bash scripts/bootstrap_check.sh` | Clona o repo em diretório temporário, confere que nenhum dado runtime vem versionado, roda a suíte completa de testes e sobe o servidor para smoke HTTP (páginas 200, API 401 sem token, dados sensíveis 404). `SKIP_SERVER=1` pula o smoke; `PORT=n` fixa a porta. |
| `scripts/check_tracked_runtime.sh` | `bash scripts/check_tracked_runtime.sh` | Guarda rápida: falha (exit 1) se qualquer arquivo casado pelo `.gitignore` estiver versionado no git. Rode após criar qualquer arquivo novo de dados. |
| `scripts/run_ci.py` | `python3 scripts/run_ci.py` | Suíte completa de CI local (build COBOL, seed idempotente, smokes, reviews). `--no-build` pula recompilação; `--browser` adiciona cenários visuais. |
| `scripts/deploy_producao.sh` | `bash scripts/deploy_producao.sh` | Atualiza produção (slvdc01, serviço `becrp.service` na porta 8180) em um comando: bundle via SFTP → update in-place → testes → restart → health. Falha em qualquer etapa = rollback automático. Requer `~/.config/becrp_prod.json` (chmod 600) + `paramiko`. |

## Produção

O ERP roda no servidor **slvdc01** como serviço systemd (`becrp.service`, porta
8180), atrás do nginx (`erp.palmarante.com.br` → 8180). Atualização:

```bash
bash scripts/deploy_producao.sh
```

## Segurança e dados

- `data/`, `dados/`, uploads, certificados e fontes `.py` **não** são servidos
  estaticamente (guarda em `server._is_sensitive_static_path`).
- `data/users.json` (tokens/hashes) e os `.dat` de RH são runtime — nunca
  versionar; a guarda de CI bloqueia regressões.
- Novos arquivos runtime: adicione ao `.gitignore` **e** à tabela em
  [docs/STARTER_KIT_RUNTIME_DATA.md](docs/STARTER_KIT_RUNTIME_DATA.md).
