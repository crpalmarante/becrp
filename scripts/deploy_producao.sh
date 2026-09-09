#!/usr/bin/env bash
# deploy_producao.sh — atualiza o BECRP em produção (slvdc01) em um comando.
#
#   bash scripts/deploy_producao.sh
#
# Fluxo:
#   1. Pré-requisitos locais (paramiko, ~/.config/becrp_prod.json chmod 600)
#   2. git bundle (HEAD + main) enviado via SFTP — nenhuma credencial no servidor
#   3. Serviço parado → git fetch/reset --hard no bundle (arquivos runtime não
#      rastreados — dados, .venv — são preservados) → pip install idempotente
#   4. pytest com o servidor parado (sem disputa pelos arquivos de dados)
#   5. Serviço iniciado + health check (/, guard de dados sensíveis)
#   Em qualquer falha: rollback automático para o SHA anterior e serviço no ar.
#
# Downtime esperado: ~1-2 min (tempo de testes + boot). O serviço é systemd
# (becrp.service, porta 8180) e o nginx proxya erp.palmarante.com.br → 8180.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CREDS="$HOME/.config/becrp_prod.json"
BUNDLE="/tmp/becrp_deploy.bundle"
PORT=8180

# ── 1. Pré-requisitos ────────────────────────────────────────────
[ -r "$CREDS" ] || { echo "FAIL: $CREDS não encontrado (host/user/pass, chmod 600)"; exit 1; }
[ "$(stat -c %a "$CREDS")" = "600" ] || { echo "FAIL: $CREDS deve ter chmod 600"; exit 1; }
python3 -c "import paramiko" 2>/dev/null || { echo "FAIL: pip install paramiko"; exit 1; }

echo "▶ Criando bundle do repo…"
git -C "$ROOT" bundle create "$BUNDLE" HEAD main --quiet
echo "  $(git -C "$ROOT" log --oneline -1)"

# ── 2-5. Remoto ──────────────────────────────────────────────────
python3 - "$BUNDLE" "$PORT" <<'PYEOF'
import json
import sys
import time

import paramiko

bundle, port = sys.argv[1], int(sys.argv[2])
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
        # NUNCA ecoar a senha (comandos sudo a embutem) — sanitiza tudo
        pwd = c["pass"]
        safe_cmd = cmd.replace(pwd, "***")
        safe_out = "\n".join((out or err).splitlines()[-5:])
        safe_out = safe_out.replace(pwd, "***")
        tag = "OK " if code == 0 else "ERR"
        print(f"  [{tag}] exit {code}: {safe_cmd[:76]}")
        for l in safe_out.splitlines():
            print(f"        {l[:110]}")
    return code, out, err


def sudo(cmd, timeout=120):
    return run(f'echo "{c["pass"]}" | sudo -S {cmd} 2>/dev/null', timeout)


def die(msg):
    print(f"FAIL: {msg}")
    cli.close()
    sys.exit(1)


def healthy():
    code, out, _ = run(f"curl -s -m 4 -o /dev/null -w '%{{http_code}}' "
                       f"http://127.0.0.1:{port}/", show=False)
    guard, gout, _ = run(f"curl -s -m 4 -o /dev/null -w '%{{http_code}}' "
                         f"http://127.0.0.1:{port}/data/users.json", show=False)
    return out == "200" and gout == "404"


# upload do bundle
print("▶ SFTP bundle")
sftp = cli.open_sftp()
sftp.put(bundle, "/home/palmarante/becrp_deploy.bundle")
sftp.close()

# estado atual (para rollback)
code, prev_sha, _ = run("git -C /home/palmarante/becrp rev-parse --short HEAD", show=False)
prev_sha = prev_sha if code == 0 else "desconhecido"
print(f"▶ Versão atual em produção: {prev_sha}")

# 3. parar serviço + atualizar in-place (runtime/.venv preservados)
print("▶ Parando becrp.service")
sudo("systemctl stop becrp")

print("▶ Atualizando código (fetch + reset --hard)")
code, out, err = run(
    "cd /home/palmarante/becrp && git fetch -q /home/palmarante/becrp_deploy.bundle main && "
    "git reset --hard FETCH_HEAD && git log --oneline -1")
if code != 0:
    die(f"reset falhou — restaurando: {err}")

print("▶ Dependências (pip idempotente)")
code, _, _ = run("cd /home/palmarante/becrp && .venv/bin/python -m pip install -q -r requirements.txt",
                 timeout=600)
if code != 0:
    die("pip install falhou")

# 4. testes com o servidor parado
print("▶ pytest (servidor parado)")
code, out, _ = run("cd /home/palmarante/becrp && .venv/bin/python -m pytest tests/ -q 2>&1 | tail -1",
                   timeout=600)
if code != 0 or "failed" in out.lower():
    die("testes falharam — código NÃO entrou no ar")

# 5. subir + health
print("▶ Iniciando becrp.service")
sudo("systemctl start becrp")
for _ in range(30):
    time.sleep(2)
    if healthy():
        break
else:
    print("▶ Health check falhou — ROLLBACK para", prev_sha)
    sudo("systemctl stop becrp")
    run(f"cd /home/palmarante/becrp && git reset --hard {prev_sha}", show=False)
    run("cd /home/palmarante/becrp && .venv/bin/python -m pip install -q -r requirements.txt",
        timeout=600, show=False)
    sudo("systemctl start becrp")
    time.sleep(10)
    if healthy():
        print(f"ROLLBACK concluído — produção de volta em {prev_sha}")
        cli.close()
        sys.exit(1)
    die("rollback também falhou — serviço PARADO, investigar manualmente")

print(f"✔ Deploy OK — {port} saudável, guard 404, nginx → erp.palmarante.com.br")
run("rm -f /home/palmarante/becrp_deploy.bundle", show=False)
cli.close()
PYEOF

rm -f "$BUNDLE"
echo "✔ Deploy concluído. Externo: http://erp.palmarante.com.br (requer DNS A: erp → 177.190.69.20)"
exit 0
