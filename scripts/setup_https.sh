#!/usr/bin/env bash
# setup_https.sh — emite o certificado Let's Encrypt para erp.palmarante.com.br.
#
#   bash scripts/setup_https.sh <email-para-aviso-letsencrypt>
#
# Pré-requisitos:
#   - Registro DNS A: erp → 177.190.69.20 (o script confere antes de rodar)
#   - ~/.config/becrp_prod.json (host/user/pass, chmod 600) + pip install paramiko
#   - vhost /etc/nginx/sites-enabled/becrp (já instalado) e certbot no servidor
#
# O script: 1) valida o DNS localmente e no servidor; 2) roda certbot --nginx
# (emite o cert, edita o vhost para 443 e liga o redirect HTTP→HTTPS);
# 3) valida https:// (200) e o redirect (301) via curl --resolve.
set -euo pipefail

DOMAIN="erp.palmarante.com.br"
SERVER_IP="177.190.69.20"
CREDS="$HOME/.config/becrp_prod.json"

EMAIL="${1:-${CERTBOT_EMAIL:-}}"
[ -n "$EMAIL" ] || { echo "Uso: bash scripts/setup_https.sh <email>"; exit 1; }
[ -r "$CREDS" ] || { echo "FAIL: $CREDS não encontrado"; exit 1; }
python3 -c "import paramiko" 2>/dev/null || { echo "FAIL: pip install paramiko"; exit 1; }

echo "▶ Conferindo DNS de $DOMAIN…"
resolved=$(dig +short "$DOMAIN" @8.8.8.8 2>/dev/null | tail -1 || true)
if [ "$resolved" != "$SERVER_IP" ]; then
    echo "FAIL: $DOMAIN ainda não aponta para $SERVER_IP (hoje: ${resolved:-sem registro})."
    echo "      Crie o registro A no provedor do domínio e rode este script de novo."
    exit 1
fi
echo "  DNS OK ($DOMAIN → $SERVER_IP)"

python3 - "$DOMAIN" "$EMAIL" "$SERVER_IP" <<'PYEOF'
import json
import sys

import paramiko

domain, email, server_ip = sys.argv[1], sys.argv[2], sys.argv[3]
c = json.load(open("/home/palmarante/.config/becrp_prod.json"))
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(c["host"], username=c["user"], password=c["pass"], timeout=15)


def run(cmd, timeout=300, show=True):
    stdin, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace").strip()
    err = stderr.read().decode("utf-8", "replace").strip()
    code = stdout.channel.recv_exit_status()
    if show:
        pwd = c["pass"]
        safe = (out or err).replace(pwd, "***")
        tag = "OK " if code == 0 else "ERR"
        print(f"  [{tag}] exit {code}: {cmd.replace(pwd, '***')[:70]}")
        for l in safe.splitlines()[-6:]:
            print(f"        {l[:110]}")
    return code, out, err


def sudo(cmd, timeout=300):
    return run(f'echo "{c["pass"]}" | sudo -S {cmd} 2>/dev/null', timeout)


# DNS visto de dentro do servidor (o Let's Encrypt valida de fora; dois pontos
# de vista conferidos reduzem surpresas de propagação/cache)
code, out, _ = run(f"dig +short {domain} @8.8.8.8 | tail -1", show=False)
if out != server_ip:
    print(f"FAIL: DNS no servidor ainda mostra {out!r} — aguarde propagação.")
    cli.close()
    sys.exit(1)

print("▶ Emitindo certificado (certbot --nginx)")
code, out, err = sudo(
    f"certbot --nginx -d {domain} -m {email} --agree-tos "
    f"--non-interactive --redirect", timeout=300)
if code != 0:
    print(f"FAIL: certbot falhou — {err or out}")
    cli.close()
    sys.exit(1)

print("▶ Validando HTTPS e redirect")
code, https_code, _ = run(
    f"curl -s -m 8 -o /dev/null -w '%{{http_code}}' https://{domain}/", show=False)
code2, redirect_code, _ = run(
    f"curl -s -m 8 -o /dev/null -w '%{{http_code}}' http://{domain}/", show=False)
print(f"  https://{domain}/ → {https_code} (esperado 200)")
print(f"  http://{domain}/  → {redirect_code} (esperado 301)")

if https_code == "200" and redirect_code == "301":
    print(f"✔ HTTPS ativo em https://{domain} (renovação automática via certbot.timer)")
else:
    print("⚠️  cert saiu, mas validação inesperada — conferir vhost nginx")
cli.close()
PYEOF
