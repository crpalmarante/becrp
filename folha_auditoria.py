"""folha_auditoria.py — Trilha de auditoria da folha (RFC-009 §5).

Registro **imutável** (append-only) de toda mutação relevante do módulo de
folha: lançamento, cálculo, mudança de estado, alteração de cadastro e de
tabela (RFC-009 §5.1.3 / Decisão 3).

Campos por evento (RFC-009 §5):
  - quando  (data e hora)
  - quem    (login do usuário autenticado ou 'sistema' para ações automáticas)
  - acao    (abrir_competencia, calcular, concluir, validar, fechar, pagar,
             alterar_cadastro, alterar_tabela, lancar…)
  - antes   (estado anterior — valores alterados)
  - depois  (estado posterior)
  - contexto (competência, funcionário, evento ou tabela afetados)
  - tax_table_versions (RFC-005 §5.1.2 — versão das tabelas usadas no cálculo,
             permitindo reproduzir o cálculo da competência)

Imutabilidade (RFC-009 §5.1.1): o arquivo é JSONL em modo append — cada evento
é UMA linha e linhas antigas **nunca** são reescritas, editadas ou apagadas.
Não há API de update/delete: a trilha só cresce.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime

DADOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")
AUDITORIA_FILE = os.path.join(DADOS_DIR, "folha_auditoria.jsonl")

# O servidor é multithread (ThreadingHTTPServer): serializa o append.
_LOCK = threading.Lock()


def _quando():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _proximo_id(eventos):
    max_id = 0
    for e in eventos:
        try:
            max_id = max(max_id, int(e.get("id") or 0))
        except (TypeError, ValueError):
            continue
    return max_id + 1


def _iter_eventos():
    """Lê a trilha (ordem de gravação). Linhas corrompidas são ignoradas."""
    if not os.path.exists(AUDITORIA_FILE):
        return []
    eventos = []
    with open(AUDITORIA_FILE, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                eventos.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
    return eventos


def registrar(acao, quem, contexto=None, antes=None, depois=None,
              tax_table_versions=None):
    """Append de um evento na trilha. Nunca edita/apaga eventos anteriores.

    O ciclo ler-máximo-id + append roda INTEIRO sob o lock: o servidor é
    multithread (ThreadingHTTPServer) e duas requisições concorrentes não podem
    gerar eventos com o mesmo id."""
    with _LOCK:
        eventos = _iter_eventos()
        evento = {
            "id": _proximo_id(eventos),
            "quando": _quando(),
            "quem": quem or "sistema",
            "acao": acao,
            "contexto": contexto or {},
            "antes": antes,
            "depois": depois,
            "tax_table_versions": tax_table_versions,
        }
        os.makedirs(DADOS_DIR, exist_ok=True)
        with open(AUDITORIA_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")
    return evento


def listar(competencia=None, acao=None, quem=None, limite=200):
    """Consulta da trilha (mais recentes primeiro). Filtros opcionais."""
    eventos = _iter_eventos()
    filtrados = []
    for e in reversed(eventos):
        ctx = e.get("contexto") or {}
        if competencia and str(ctx.get("competencia") or "") != str(competencia):
            continue
        if acao and e.get("acao") != acao:
            continue
        if quem and str(e.get("quem") or "") != str(quem):
            continue
        filtrados.append(e)
        if limite and len(filtrados) >= limite:
            break
    return filtrados


def operador_da_competencia(competencia):
    """Login do usuário que abriu/calculou a competência (RFC-009 §4.2/Decisão 4).

    O fechamento (Aprovador) deve ser feito por usuário **diferente** do
    Operador da competência. Retorna None quando a competência não tem operação
    registrada na trilha (fluxo legado/migração) — nesse caso o fechamento fica
    liberado para qualquer usuário autorizado.
    """
    for e in _iter_eventos():
        ctx = e.get("contexto") or {}
        if str(ctx.get("competencia") or "") != str(competencia):
            continue
        if e.get("acao") in ("abrir_competencia", "calcular"):
            return e.get("quem") or None
    return None


def aprovador_da_competencia(competencia):
    """Login do usuário que FECHOU a competência (RFC-009 §4.2 — Tesouraria).

    O registro de pagamento (Tesouraria) deve ser feito por usuário **diferente**
    do Aprovador da competência (quem fechou). Retorna None quando a competência
    não tem fechamento registrado na trilha — nesse caso o pagamento fica
    liberado para qualquer usuário autorizado.
    """
    for e in reversed(_iter_eventos()):
        ctx = e.get("contexto") or {}
        if str(ctx.get("competencia") or "") != str(competencia):
            continue
        if e.get("acao") == "fechar":
            return e.get("quem") or None
    return None


def operador_da_complementar(comp_id):
    """Login de quem LANÇOU a folha complementar (RFC-013/Decisão 1).

    O fechamento da complementar (Aprovador) exige usuário **diferente** do
    Operador (quem incluiu) — mesma regra do RFC-009 §4.2 aplicada à
    complementar. Retorna None quando não há lançamento registrado.
    """
    for e in _iter_eventos():
        ctx = e.get("contexto") or {}
        if str(ctx.get("tipo") or "") != "complementar":
            continue
        if str(ctx.get("id") or "") != str(comp_id):
            continue
        if e.get("acao") in ("lancar", "incluir_complementar"):
            return e.get("quem") or None
    return None


def aprovador_da_complementar(comp_id):
    """Login de quem FECHOU a folha complementar (RFC-013 + RFC-009 §4.2).

    O pagamento (Tesouraria) da complementar exige usuário **diferente** do
    Aprovador (quem fechou)."""
    for e in reversed(_iter_eventos()):
        ctx = e.get("contexto") or {}
        if str(ctx.get("tipo") or "") != "complementar":
            continue
        if str(ctx.get("id") or "") != str(comp_id):
            continue
        if e.get("acao") == "fechar_complementar":
            return e.get("quem") or None
    return None


def versao_tabela_usada(competencia):
    """Última versão de tabela registrada no cálculo da competência
    (RFC-005 §5.1.2) — o que permite reproduzir o cálculo."""
    for e in reversed(_iter_eventos()):
        ctx = e.get("contexto") or {}
        if str(ctx.get("competencia") or "") != str(competencia):
            continue
        if e.get("acao") == "calcular" and e.get("tax_table_versions"):
            return e["tax_table_versions"]
    return None
