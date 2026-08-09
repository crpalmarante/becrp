#!/usr/bin/env bash
# ============================================================================
# tests/run_all.sh — roda TODOS os testes do ERP COBOL num único comando.
#
# Cobre os dois tipos de teste do projeto:
#   * COBOL via ctypes  — tests/test_ctypes_{taxcalc,calcevent,paycalc}.py
#                         (requer os .so compilados em cobol/ — o script
#                         recompila automaticamente quando faltam/desatualizam,
#                         ou sempre com --rebuild)
#   * Integração Postgres — tests/test_{permissions,state_machine,runs_lines,tax_tables,stubs,commission_rules,payroll_accounting,commission_accounting,commission_detail_accounting}_integration.py
#                         (cluster PostgreSQL temporário via tests/pg_bootstrap.py,
#                         ou banco existente via ERP_TEST_DATABASE_URL p/ CI;
#                         PULAM graciosamente sem psycopg2/binários do PG/URL)
#
# Uso:
#   bash tests/run_all.sh            # build incremental + suíte completa
#   bash tests/run_all.sh --rebuild  # força a recompilação dos .so COBOL
#
# Requisitos: python3 (stdlib). Opcionais: GnuCOBOL (cobc) p/ o build dos .so,
# psycopg2 e — p/ os testes de integração — binários do PostgreSQL OU a env
# ERP_TEST_DATABASE_URL (CI). Se os requisitos ausentes, os testes
# correspondentes são pulados — nunca falham por falta de ambiente.
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REBUILD=0
if [ "${1:-}" = "--rebuild" ]; then
    REBUILD=1
fi

# --- 1. Pré-requisito: python3 -------------------------------------------------
command -v python3 >/dev/null 2>&1 \
    || { echo "ERRO: python3 não encontrado" >&2; exit 1; }

# --- 2. Build do COBOL (incremental; forçado com --rebuild) -------------------
# PAYCALC chama CALCEVENT e TAXCALC como subprogramas (COB_LIBRARY_PATH), por
# isso os três módulos entram no build.
COBC="$(command -v cobc || true)"
COBOL_MODULES=(taxcalc calcevent paycalc)

NEED_BUILD=$REBUILD
if [ "$NEED_BUILD" -eq 0 ]; then
    for mod in "${COBOL_MODULES[@]}"; do
        so="cobol/$mod.so"
        src="cobol/$mod.cbl"
        if [ ! -f "$so" ] || [ "$src" -nt "$so" ]; then
            NEED_BUILD=1
            break
        fi
    done
fi

if [ "$NEED_BUILD" -eq 1 ]; then
    if [ -z "$COBC" ]; then
        echo "ERRO: cobc (GnuCOBOL) não encontrado e os .so precisam de build." >&2
        echo "      Compile manualmente: cd cobol && cobc -m -o taxcalc.so taxcalc.cbl &&" >&2
        echo "      cobc -m -o calcevent.so calcevent.cbl && cobc -m -o paycalc.so paycalc.cbl" >&2
        exit 1
    fi
    echo "==> Compilando módulos COBOL (cobc -m)..."
    (cd cobol \
         && cobc -m -o taxcalc.so taxcalc.cbl \
         && cobc -m -o calcevent.so calcevent.cbl \
         && cobc -m -o paycalc.so paycalc.cbl)
    echo "    OK: taxcalc.so calcevent.so paycalc.so"
else
    echo "==> Módulos COBOL em dia (use --rebuild para recompilar)"
fi

echo ""
echo "==> Rodando a suíte completa (COBOL ctypes + integração Postgres)..."
echo ""

# --- 3. unittest discover ------------------------------------------------------
# -s tests : diretório de busca — sem "-t .": o diretório é adicionado ao
#            sys.path e os módulos importam como test_* (os testes de
#            integração caem no fallback "from pg_bootstrap import ..." e o
#            helper resolve de qualquer forma).
# -p test_*.py : ignora helpers (pg_bootstrap.py) e qualquer outro arquivo.
# NÃO usar "-t ." aqui: o discover exige __init__.py no diretório de busca
# quando o top-level difere do start dir ("Start directory is not importable"
# — tests/ é namespace package, sem __init__.py).
python3 -m unittest discover -s tests -p "test_*.py" -v
