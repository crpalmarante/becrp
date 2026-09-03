# Incidente — Reinicializações intermitentes no servidor de produção

> **Servidor:** `177.190.69.20` (`slvdc01`) · Dell OptiPlex 790 (físico, ~2011)
> **SO:** Ubuntu (kernel 6.8.0-137-generic)
> **Período do incidente:** 10/08/2026 → 11/08/2026 (40+ reinicializações)
> **Status:** ✅ Resolvido (mitigação em produção) · manutenção física pendente
> **Data do relatório:** 11/08/2026

---

## 1. Sintoma

O servidor passou a **desligar e religar sozinho** em horários irregulares. Em 2 dias foram **40+ reinicializações** — antes disso o servidor ficava estável por **31 e 45 dias** sem reiniciar.

---

## 2. Diagnóstico (metodologia de exclusão)

| Teste | Resultado | Verdict |
|---|---|---|
| Conectividade (ping + portas 22/80/443) | Host responde, portas abertas | — |
| Uptime / histórico de reboots | 10+ reboots só em 11/08 | ⚠️ anormal |
| Memória / OOM killer | 30 GiB livres, zero OOM | ❌ descartado |
| Kernel panic / MCE / hardware error | Nenhum registro | ❌ descartado |
| Temperatura | CPU a 33 °C (crítico 102 °C) | ❌ descartado |
| Cron / systemd timers / unattended-upgrades | Nenhum agendamento de reboot | ❌ descartado |
| `reboot`/`poweroff` via SSH | Nada no `/var/log/auth.log` | ❌ descartado |
| Natureza dos desligamentos | **Graciosos** (systemd, não queda de energia) | ✅ pista |
| **Botão de energia ACPI** | **`Power key pressed short` antes de cada desligamento** | ✅ **CAUSA RAIZ** |

### Evidência principal (journal do systemd-logind, boots anteriores)

```
Aug 11 15:54:11 slvdc01 systemd-logind[789]: Power key pressed short.
Aug 11 15:54:11 slvdc01 systemd-logind[789]: System is powering down.
```

**Todos** os desligamentos foram precedidos de `Power key pressed short` → o **botão de energia físico do gabinete** está sendo acionado sozinho (contato/curto intermitente), por alguém apertando, ou por algo encostando nele.

### Linha do tempo

- **Antes de 09/08:** estável — uptimes de 31 e 45 dias.
- **10/08:** começam as reinicializações; o usuário instala `lm-sensors` e `smartmontools` (início da investigação de hardware).
- **11/08:** dezenas de reboots; instalado `evtest`/`evemu` (ferramentas de diagnóstico de botões/input) — sinais de que o problema é físico.
- **11/08 (tarde):** diagnóstico concluído com a confirmação do `Power key pressed short`.

---

## 3. Correção aplicada (produção)

### `HandlePowerKey=ignore` no systemd-logind

| Etapa | Comando | Resultado |
|---|---|---|
| Backup | `cp /etc/systemd/logind.conf /etc/systemd/logind.conf.bak-20260811` | ✅ `/etc/systemd/logind.conf.bak-20260811` |
| Aplicação | `sed -i 's/^#*HandlePowerKey=.*/HandlePowerKey=ignore/' /etc/systemd/logind.conf` | ✅ linha 27 |
| Reinício | `systemctl restart systemd-logind` | ✅ `OK-RESTART` |
| Estado | `systemctl is-active systemd-logind` | ✅ `active` |

**Efeito:** o SO ignora o botão de energia. O desligamento via software (`poweroff`/`reboot`) e a queda de energia real **continuam funcionando normalmente** — a correção só desativa o gatilho ACPI do botão.

---

## 4. Monitoramento de reboots (instalado 11/08)

| Componente | Local | Detalhe |
|---|---|---|
| Script | `/usr/local/sbin/reboot-monitor.sh` | root, 0755 |
| Serviço | `reboot-monitor.service` | `Type=oneshot` |
| Timer | `reboot-monitor.timer` | **enabled + active**, a cada **5 min** (1ª execução 2 min após boot) |
| Log persistente | `/var/log/reboot-monitor.log` | linhas `OK` / `ALERT` / `REBOOT-CHANGE` |
| Estado | `/var/run/reboot-monitor.lastboot` | marca o último boot |
| Alerta syslog | `logger -t reboot-monitor` | aparece em `journalctl -t reboot-monitor` |

### Regras do alerta

1. **Uptime curto (< 15 min)** → grava `ALERT ... reboot detectado` no log **e** no syslog.
2. **Mudança de boot** entre execuções → grava `REBOOT-CHANGE` + syslog (captura reboot mesmo que a volta demore > 15 min).
3. **Execução normal** → linha `OK uptime=... boot=...` para histórico.

### Como consultar

```bash
tail -f /var/log/reboot-monitor.log          # histórico de checagens
journalctl -t reboot-monitor --since today   # alertas (syslog)
systemctl status reboot-monitor.timer        # estado do timer
```

---

## 5. Validação pós-correção

Verificação realizada ~5h após a correção (boot 17:01):

| Verificação | Estado |
|---|---|
| Uptime | **4h58m** e subindo — sem reboots desde a correção |
| `reboot-monitor.log` | 100% `OK` a cada 5 min, sempre `boot='2026-08-11 17:01'`, **zero alertas** |
| Alertas syslog | `No entries` |
| Timer | `active`, executando a cada 5 min |
| **Power key no boot atual** | **5 novos `Power key pressed short` (19:13–21:25)** — e **o servidor não desligou em nenhum deles** |

> **Interpretação:** o botão **continua com defeito** (disparando sozinho), mas o `HandlePowerKey=ignore` está segurando — o logind registra o pressionamento e ignora. Isso confirma duplamente o diagnóstico e a eficácia da mitigação.

---

## 5.1 Acompanhamento (monitoring log)

Registro das verificações periódicas de estabilidade. **Cada nova verificação deve ser adicionada como uma nova linha** na tabela abaixo.

### Comando de verificação (resumo)

```bash
uptime
last -x reboot | head -5
# resumo do monitor:
echo "total=$(wc -l < /var/log/reboot-monitor.log) ok=$(grep -c ' OK ' /var/log/reboot-monitor.log) alert=$(grep -c ALERT /var/log/reboot-monitor.log) change=$(grep -c REBOOT-CHANGE /var/log/reboot-monitor.log)"
journalctl -t reboot-monitor --since today | grep -c ALERT   # 0 = nenhum alerta
journalctl -b | grep -i 'power key pressed' | tail -5        # pressionamentos do botão no boot atual
```

| # | Data/hora (verificação) | Uptime | Reboots novos | Monitor (total/OK/ALERT/CHANGE) | Power key (boot atual) | Observação |
|---|---|---|---|---|---|---|
| 1 | 11/08 22:00 | 4h58m | 0 (desde 17:01) | 35/35/0/0 | 5 (19:13–21:25) | Estável; botão disparando sem efeito |
| 2 | 11/08 22:02 | 5h00m | 0 (desde 17:01) | 35/35/0/0 | 6 (19:13–21:27) | Novo pressionamento 21:27; sistema de pé |

> **Critério de encerramento:** quando a manutenção física for feita (botão limpo/trocado), registrar na tabela e, se o monitor seguir sem `ALERT`/`REBOOT-CHANGE` por 7 dias consecutivos, o incidente pode ser encerrado e esta seção arquivada.

---

## 6. Recomendações (manutenção física pendente)

1. **Limpar contatos do botão do painel frontal** com álcool isopropílico (≥ 90%) + ar comprimido, e limpar também os pinos do header na placa-mãe (defeito conhecido no OptiPlex 790 — micro-switch oxida/perde contato e dispara sozinho).
2. **Testar com o journal aberto** antes de fechar o gabinete: `journalctl -u systemd-logind -f` e apertar o botão algumas vezes para ver se registra sem o usuário apertar.
3. **Trocar o módulo do botão** (peça Dell) ou um micro-switch genérico compatível se a limpeza não resolver.
4. **Alternativa definitiva:** desconectar o cabo do botão de power da placa-mãe — com o AC Power Recovery na BIOS (ligar ao religar energia) ou Wake-on-LAN o servidor liga normalmente.
5. **Manutenção preventiva:** trocar a **bateria CMOS** (CR2032, ~2011 — provável no fim da vida útil).
6. **Verificar o local físico** — se há acesso de terceiros, alguém pode estar apertando o botão sem saber.

**Enquanto isso:** o servidor está protegido pelo `HandlePowerKey=ignore` + monitoramento. Se surgir um `ALERT`/`REBOOT-CHANGE` no monitor, a causa **não** será o botão de energia — vale investigar outra origem (e o horário exato estará registrado).

---

## 7. Referência rápida dos arquivos no servidor

| Arquivo | Função |
|---|---|
| `/etc/systemd/logind.conf` | config do logind (linha 27: `HandlePowerKey=ignore`) |
| `/etc/systemd/logind.conf.bak-20260811` | backup pré-correção |
| `/usr/local/sbin/reboot-monitor.sh` | script de monitoramento |
| `/etc/systemd/system/reboot-monitor.service` | serviço oneshot |
| `/etc/systemd/system/reboot-monitor.timer` | timer (5 min) |
| `/var/log/reboot-monitor.log` | log persistente |
| `/var/run/reboot-monitor.lastboot` | marca do último boot |
