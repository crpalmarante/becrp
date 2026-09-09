#!/usr/bin/env bash
# check_tracked_runtime.sh — falha se qualquer arquivo gitignore estiver versionado.
#
# Complemento da regra "dados runtime não vão para o git" (docs/STARTER_KIT_RUNTIME_DATA.md):
# lista arquivos em cache do git que casam com padrões do .gitignore e falha se houver algum.
# Uso: bash scripts/check_tracked_runtime.sh   (exit 1 se houver ofensores)
set -euo pipefail

offenders=$(git ls-files -ci --exclude-standard)

if [ -z "$offenders" ]; then
    echo "OK: nenhum arquivo ignorado pelo .gitignore está versionado"
    exit 0
fi

echo "FAIL: arquivos versionados que deveriam ser ignorados (git rm --cached):" >&2
echo "$offenders" >&2
exit 1
