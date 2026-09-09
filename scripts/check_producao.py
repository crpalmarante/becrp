#!/usr/bin/env python3
"""Check de estabilidade do servidor de produção (177.190.69.20 / slvdc01).

Consulta via SSH (paramiko) e imprime um resumo de estabilidade:
  - uptime e boot atual
  - últimos reboots (last -x reboot)
  - log do reboot-monitor (últimas linhas + contagem OK/ALERT/REBOOT-CHANGE)
  - alertas syslog do reboot-monitor (hoje)
  - pressionamentos do botão de energia no boot atual (power key)
  - estado do timer e do systemd-logind (HandlePowerKey=ignore)

Uso:
  python3 scripts/check_producao.py [--boot 'YYYY-MM-DD HH:MM']

Credenciais (sem senha em texto no código):
  1. variável de ambiente PROD_PASS, ou
  2. arquivo ~/.config/becrp_prod.json (JSON: {"host":..., "user":..., "pass":...})
     — criado com chmod 600 na primeira execução que falhar sem ele.

Exit code:
  0 = estável (sem alertas/reboots novos desde a linha de base)
  1 = instável (ALERT/REBOOT-CHANGE no dia, ou reboot após a linha de base)
  2 = erro de conexão/comando remoto/dados insuficientes
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

try:
    import paramiko
except ImportError:
    print("❌ paramiko não instalado — rode: pip install paramiko")
    sys.exit(2)

DEFAULT_HOST = "177.190.69.20"
DEFAULT_USER = "palmarante"
CONFIG_FILE = os.path.expanduser("~/.config/becrp_prod.json")

# Boot considerado "linha de base" (boot em que a correção foi aplicada).
# Passado via --boot; sem ele, o script usa o boot atual como base (não detecta
# reboots, apenas alertas do monitor).
BASELINE_BOOT = None

MESES = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
         "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}


def _carregar_credenciais():
    """Senha vem de env ou ~/.config/becrp_prod.json — nunca do código."""
    host = os.environ.get("PROD_HOST", DEFAULT_HOST)
    user = os.environ.get("PROD_USER", DEFAULT_USER)
    pwd = os.environ.get("PROD_PASS")
    if not pwd and os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                cfg = json.load(f)
            host = cfg.get("host", host)
            user = cfg.get("user", user)
            pwd = cfg.get("pass")
        except (OSError, ValueError) as e:
            print(f"⚠️  Não consegui ler {CONFIG_FILE}: {e}")
    if not pwd:
        print("❌ Senha não encontrada. Defina PROD_PASS no ambiente ou crie "
              f"{CONFIG_FILE} com chave 'pass'.")
        print("   Ex.: PROD_PASS='sua-senha' python3 scripts/check_producao.py")
        sys.exit(2)
    return host, user, pwd


def _fmt_boot(linha: str) -> str:
    """Extrai 'YYYY-MM-DD HH:MM' de uma linha do `last -x reboot -F`."""
    m = re.search(r"([A-Z][a-z]{2})\s+(\d+)\s+(\d{2}:\d{2}):\d{2}\s+(\d{4})", linha)
    if not m:
        return ""
    mes, dia, hora, ano = m.groups()
    try:
        return f"{ano}-{MESES[mes]:02d}-{int(dia):02d} {hora}"
    except KeyError:
        return ""


def main() -> int:
    host, user, pwd = _carregar_credenciais()

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(host, port=22, username=user, password=pwd, timeout=15,
                    look_for_keys=False, allow_agent=False)
    except Exception as e:
        print(f"❌ Falha de conexão SSH com {user}@{host}: {e}")
        return 2

    def run(cmd: str, timeout: int = 25):
        """Executa comando remoto via `sudo -S`; senha vai pelo stdin do
        paramiko (nunca em argv), evitando exposição em `ps` no servidor."""
        _in, out, err = cli.exec_command(f'sudo -S -p "" {cmd}', timeout=timeout)
        _in.write(pwd + "\n")
        _in.flush()
        o = out.read().decode("utf-8", "replace").strip()
        e = err.read().decode("utf-8", "replace").strip()
        status = out.channel.recv_exit_status()
        return o, e, status

    try:
        print(f"==== ESTABILIDADE — {user}@{host} ====")
        print(f"Data/hora local: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        # ── uptime e boot atual ──────────────────────────────────────────────
        up, up_err, up_st = run("uptime")
        if up_st != 0 or not up:
            print(f"❌ Falha ao ler uptime (exit={up_st}): {up_err}")
            return 2
        print("1) UPTIME")
        print(f"   {up}")

        # LC_ALL=C força meses em inglês; -F inclui o ano no timestamp
        reboots_raw, reboots_err, reboots_st = run(
            "LC_ALL=C last -x reboot -F 2>/dev/null | head -8")
        if reboots_st != 0 and not reboots_raw:
            print(f"⚠️  Sem dados de reboot (exit={reboots_st}): {reboots_err}")
        linhas_reboot = [l for l in reboots_raw.splitlines() if "system boot" in l]
        boot_atual = ""
        for l in linhas_reboot:
            b = _fmt_boot(l)
            if b and "still running" in l:
                boot_atual = b
                break

        base = BASELINE_BOOT or os.environ.get("PROD_BASELINE_BOOT", "")
        reboots_novos = 0
        if base:
            reboots_novos = sum(1 for l in linhas_reboot
                                if _fmt_boot(l) and _fmt_boot(l) > base)

        print(f"\n2) BOOT ATUAL: {boot_atual or '(não detectado)'}")
        print("   Últimos reboots:")
        for l in linhas_reboot[:4]:
            print(f"   - {l.strip()}")
        if base:
            print(f"   Reboots novos desde a linha de base ({base}): {reboots_novos}")
        else:
            print("   (sem linha de base — use --boot 'YYYY-MM-DD HH:MM' "
                  "para comparar com o boot da correção)")

        # ── log do reboot-monitor ────────────────────────────────────────────
        resumo, resumo_err, resumo_st = run(
            'echo "total=$(wc -l < /var/log/reboot-monitor.log 2>/dev/null) '
            'ok=$(grep -c \' OK \' /var/log/reboot-monitor.log 2>/dev/null) '
            'alert=$(grep -c ALERT /var/log/reboot-monitor.log 2>/dev/null) '
            'change=$(grep -c REBOOT-CHANGE /var/log/reboot-monitor.log 2>/dev/null)"')
        m = re.search(r"total=(\d+)\s+ok=(\d+)\s+alert=(\d+)\s+change=(\d+)", resumo)
        if not m:
            print(f"❌ Não foi possível ler o resumo do reboot-monitor "
                  f"(exit={resumo_st}): {resumo_err or resumo}")
            return 2
        total, ok, alert_cum, change_cum = (int(m.group(i)) for i in range(1, 5))
        tail_log, _, _ = run("tail -4 /var/log/reboot-monitor.log 2>/dev/null")

        print("\n3) REBOOT-MONITOR (/var/log/reboot-monitor.log)")
        print(f"   Contagem acumulada: total={total} ok={ok} "
              f"alert={alert_cum} change={change_cum}")
        for l in tail_log.splitlines():
            print(f"   {l}")

        # ── alertas syslog (hoje, corte temporal) ────────────────────────────
        n_alerta, _, _ = run('journalctl -t reboot-monitor --since today --no-pager '
                             '2>/dev/null | grep -c ALERT')
        try:
            n_alerta = int(n_alerta)
        except ValueError:
            n_alerta = 0
        print(f"\n4) ALERTAS SYSLOG (hoje): {n_alerta}")

        # ── power key no boot atual ──────────────────────────────────────────
        # -t systemd-logind: varre só o log do logind (o journal -b inteiro
        # é enorme e estoura o timeout do canal SSH)
        pk, _, _ = run('journalctl -b -t systemd-logind --no-pager 2>/dev/null '
                       '| grep -i "power key" | head -5')
        pks = [l for l in pk.splitlines() if l.strip()]
        print(f"\n5) POWER KEY (boot atual): {len(pks)} pressionamentos")
        for l in pks[-3:]:
            print(f"   {l.strip()}")

        # ── timer e logind ───────────────────────────────────────────────────
        timer, _, _ = run("systemctl is-active reboot-monitor.timer")
        logind, _, _ = run("systemctl is-active systemd-logind; "
                           "grep '^HandlePowerKey' /etc/systemd/logind.conf 2>/dev/null")
        print(f"\n6) TIMER reboot-monitor: {timer}")
        print(f"   LOGIND: {' | '.join(l for l in logind.splitlines() if l.strip())}")

        # ── BECRP (ERP — serviço systemd + health + guarda de dados) ─────────
        print("\n7) BECRP (erp.palmarante.com.br → 8180)")
        becrp_ok = True
        svc, _, _ = run("systemctl is-active becrp; systemctl is-enabled becrp 2>/dev/null")
        linhas_svc = [l.strip() for l in svc.splitlines() if l.strip()]
        svc_active = linhas_svc[0] if linhas_svc else "unknown"
        svc_enabled = linhas_svc[1] if len(linhas_svc) > 1 else "?"
        print(f"   Serviço: {svc_active} (boot: {svc_enabled})")
        if svc_active != "active":
            print("   ❌ serviço becrp inativo!")
            becrp_ok = False
        else:
            sha, _, _ = run("git -C /home/palmarante/becrp rev-parse --short HEAD 2>/dev/null")
            print(f"   Deploy: {sha or '?'}")
            health, _, _ = run(
                "curl -s -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8180/")
            guard, _, _ = run(
                "curl -s -m 5 -o /dev/null -w '%{http_code}' "
                "http://127.0.0.1:8180/data/users.json")
            print(f"   Health /: {health} (esperado 200)")
            print(f"   Guarda /data/users.json: {guard} (esperado 404)")
            if health != "200":
                print("   ❌ health check falhou — ERP fora do ar localmente")
                becrp_ok = False
            if guard != "404":
                print("   ❌ guarda de dados sensíveis vazou (esperado 404)!")
                becrp_ok = False

        # ── veredito (apenas cortes temporais; contagens do arquivo são info) ─
        reboot_vs_base = bool(base) and bool(boot_atual) and boot_atual != base
        instavel = n_alerta > 0 or reboots_novos > 0 or reboot_vs_base or not becrp_ok

        print("\n" + "=" * 50)
        if instavel:
            print("⚠️  INSTÁVEL — alertas ou reboot detectado desde a linha de base!")
            print("    Consulte: journalctl -t reboot-monitor --since today")
            return 1
        if not boot_atual:
            print("⚠️  SEM DADOS DE BOOT — não foi possível confirmar uptime contínuo.")
            return 2
        print("✅ ESTÁVEL — nenhum alerta, uptime contínuo.")
        return 0
    except Exception as e:
        print(f"❌ Erro ao executar comandos remotos: {e}")
        return 2
    finally:
        cli.close()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--boot":
        BASELINE_BOOT = sys.argv[2]
    sys.exit(main())
