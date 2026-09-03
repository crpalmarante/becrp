#!/usr/bin/env bash
# Cria a role e os bancos PostgreSQL da camada WMS/Inventário.
#
# Rode como usuário com acesso de superusuário ao PostgreSQL (ex.: postgres):
#   sudo -u postgres bash scripts/setup_db.sh
# ou ajuste a variável PG_SUPERUSER conforme sua instalação.
#
# Depois, exporte DATABASE_URL no ambiente do servidor (ou crie um .env):
#   export DATABASE_URL=postgresql://becrp:becrp@localhost:5432/becrp
#
# Para os testes (opcional):
#   export BECRP_TEST_DATABASE_URL=postgresql://becrp:becrp@localhost:5432/becrp_test

set -euo pipefail

PG_SUPERUSER="${PG_SUPERUSER:-postgres}"
BECRP_PASSWORD="${BECRP_PASSWORD:-becrp}"

run_sql() {
    if [ "$(id -un)" = "$PG_SUPERUSER" ]; then
        psql -v ON_ERROR_STOP=1 "$@"
    else
        sudo -u "$PG_SUPERUSER" psql -v ON_ERROR_STOP=1 "$@"
    fi
}

run_sql <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'becrp') THEN
        CREATE ROLE becrp WITH LOGIN PASSWORD '${BECRP_PASSWORD}';
    END IF;
END
\$\$;
SQL

for db in becrp becrp_test; do
    if ! run_sql -tAc "SELECT 1 FROM pg_database WHERE datname='${db}'" | grep -q 1; then
        run_sql -c "CREATE DATABASE ${db} OWNER becrp"
        echo "✓ banco ${db} criado (owner becrp)"
    else
        echo "• banco ${db} já existe"
    fi
done

echo ""
echo "Pronto. Conecte com:"
echo "  psql postgresql://becrp:becrp@localhost:5432/becrp"
