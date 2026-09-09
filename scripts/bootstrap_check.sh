#!/usr/bin/env bash
# bootstrap_check.sh — valida bootstrap de clone fresco de ponta a ponta.
#
# Clona o repo para um diretório temporário (sem dados runtime versionados),
# roda a suíte de testes e sobe o servidor para smoke HTTP. Falha (exit 1)
# se qualquer etapa não passar.
#
# Presupõe que o ambiente já tem as dependências (requirements.txt + pytest).
# Uso:
#   bash scripts/bootstrap_check.sh                  # fluxo completo
#   SKIP_SERVER=1 bash scripts/bootstrap_check.sh    # pula o smoke do servidor
#   PORT=9800 bash scripts/bootstrap_check.sh        # porta do smoke (default: aleatória 8900-8999)
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-$((8900 + RANDOM % 100))}"
SERVER_PID=""
TMP=""
LOG_KEEP="/tmp/becrp_fresh_server.log"

cleanup() {
    [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
    # preserva o log do servidor fora do TMP (p/ artifact de CI em falha)
    [ -f "$TMP/server.log" ] && cp "$TMP/server.log" "$LOG_KEEP" 2>/dev/null || true
    [ -n "$TMP" ] && rm -rf "$TMP"
}
trap cleanup EXIT

fail() {
    echo "FAIL: $*" >&2
    cp "$TMP/server.log" "$LOG_KEEP" 2>/dev/null || true
    exit 1
}

# ── 1. Clone fresco ──────────────────────────────────────────────
TMP="$(mktemp -d)"
git clone --quiet "$SRC" "$TMP/repo"
cd "$TMP/repo"
echo "clone: $(git log --oneline -1)"

# ── 2. Nenhum dado runtime versionado deve existir no clone ─────
RUNTIME_PATHS=(
    data/inventory_balances.json
    data/inventory_movements.json
    data/partner_lookup_audit.json
    data/receiving_pending.json
    data/titulos_ap.json
    dados/atributos.dat
    dados/empresa.json
    dados/pos_commission_payroll.json
    dados/titulos_ap.json
    dados/wms_receiving.json
    dados/quality_check_results.json
    dados/fiscal_reforma_history.json
    dados/accounting_integration_log.json
    data/nfe_inbound
    data/users.json
    dados/departamentos.dat
    dados/cargos.dat
    dados/funcionarios.dat
)
present=0
for f in "${RUNTIME_PATHS[@]}"; do
    [ -e "$f" ] && { echo "  presente no clone: $f"; present=$((present + 1)); }
done
[ "$present" -eq 0 ] || fail "$present arquivo(s) runtime versionado(s) no clone"
echo "OK: clone fresco sem dados runtime"

# ── 3. Suíte de testes (cria os arquivos sob demanda) ────────────
python3 -m pytest tests/ -q 2>&1 | tail -2
created=0
for f in "${RUNTIME_PATHS[@]}"; do
    [ -e "$f" ] && created=$((created + 1))
done
[ "$created" -gt 0 ] || fail "nenhum arquivo runtime foi auto-criado pelos loaders"
echo "OK: testes passaram; loaders auto-criaram $created arquivo(s) runtime"

# ── 4. Smoke do servidor ─────────────────────────────────────────
if [ "${SKIP_SERVER:-0}" = "1" ]; then
    echo "SKIP_SERVER=1 — smoke do servidor pulado"
    exit 0
fi

python3 server.py "$PORT" > "$TMP/server.log" 2>&1 &
SERVER_PID=$!

ready=0
for _ in $(seq 1 60); do
    curl -s -o /dev/null "http://127.0.0.1:$PORT/" 2>/dev/null && { ready=1; break; }
    kill -0 "$SERVER_PID" 2>/dev/null || { cat "$TMP/server.log" >&2; fail "servidor morreu antes de subir"; }
    sleep 1
done
[ "$ready" -eq 1 ] || fail "servidor não ficou pronto em 60s"

check_url() {
    local url="$1" expect="$2" code
    code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT$url")
    if [ "$code" = "$expect" ]; then
        echo "OK: $url → $code"
    else
        fail "$url → $code (esperado $expect)"
    fi
}
check_url "/" "200"
check_url "/pages/configuracoes.html" "200"
check_url "/js/brand.js" "200"
check_url "/api/settings" "401"
check_url "/data/users.json" "404"

echo "PASS: bootstrap de clone fresco validado (testes + servidor)"
