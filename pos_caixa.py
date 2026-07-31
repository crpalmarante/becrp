"""
Caixa POS — movimentos (sangria/suprimento) + sessão/turno (abertura/fechamento).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CAIXA_FILE = os.path.join(DATA_DIR, "pos_caixa_movimentos.json")
SESSOES_FILE = os.path.join(DATA_DIR, "pos_caixa_sessoes.json")
VENDAS_FILE = os.path.join(BASE_DIR, "dados", "vendas.json")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_mov():
    if not os.path.exists(CAIXA_FILE):
        return {"movimentos": []}
    with open(CAIXA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"movimentos": []}
    if not isinstance(data.get("movimentos"), list):
        data["movimentos"] = []
    return data


def _save_mov(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CAIXA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_sessoes():
    if not os.path.exists(SESSOES_FILE):
        return {"sessoes": []}
    with open(SESSOES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"sessoes": []}
    if not isinstance(data.get("sessoes"), list):
        data["sessoes"] = []
    return data


def _save_sessoes(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SESSOES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_movimentos(terminal_id=None, estabelecimento_id=None, sessao_id=None, limit=50):
    rows = list(_load_mov().get("movimentos") or [])
    tid = str(terminal_id or "").strip()
    eid = str(estabelecimento_id or "").strip()
    sid = str(sessao_id or "").strip()
    if sid:
        rows = [m for m in rows if str(m.get("sessao_id") or "") == sid]
    if tid:
        rows = [m for m in rows if str(m.get("terminal_id") or "") == tid]
    if eid:
        rows = [m for m in rows if str(m.get("estabelecimento_id") or "") == eid]
    rows.sort(key=lambda m: m.get("at") or "", reverse=True)
    return rows[: max(1, min(int(limit or 50), 200))]


def add_movimento(payload, user_id=None):
    body = payload if isinstance(payload, dict) else {}
    kind = str(body.get("kind") or body.get("tipo") or "").strip().lower()
    if kind in ("sangria", "out", "saida", "saída"):
        kind = "out"
    elif kind in ("suprimento", "in", "entrada"):
        kind = "in"
    else:
        raise ValueError("kind deve ser in (suprimento) ou out (sangria)")
    try:
        value = float(body.get("value") or body.get("valor") or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        raise ValueError("valor deve ser > 0")
    reason = (body.get("reason") or body.get("motivo") or "").strip()
    if not reason:
        raise ValueError("motivo obrigatório")

    tid = str(body.get("terminal_id") or "").strip()
    eid = str(body.get("estabelecimento_id") or "").strip()
    sid = str(body.get("sessao_id") or "").strip()
    if not sid and tid:
        open_s = get_sessao_aberta(terminal_id=tid)
        if open_s:
            sid = open_s.get("id") or ""
            if not eid:
                eid = open_s.get("estabelecimento_id") or ""

    data = _load_mov()
    mid = int(datetime.now().timestamp() * 1000)
    entry = {
        "id": mid,
        "kind": kind,
        "value": round(value, 2),
        "reason": reason,
        "docType": body.get("docType") or body.get("doc_type") or "",
        "docRef": body.get("docRef") or body.get("doc_ref") or "",
        "terminal_id": tid,
        "estabelecimento_id": eid,
        "sessao_id": sid,
        "user_id": user_id,
        "user_nome": body.get("user_nome") or "",
        "at": _now(),
    }
    data["movimentos"].append(entry)
    if len(data["movimentos"]) > 500:
        data["movimentos"] = data["movimentos"][-500:]
    _save_mov(data)
    return entry


def get_sessao(sessao_id):
    sid = str(sessao_id or "").strip()
    for s in _load_sessoes().get("sessoes") or []:
        if str(s.get("id")) == sid:
            return s
    return None


def get_sessao_aberta(terminal_id=None, estabelecimento_id=None, user_id=None):
    tid = str(terminal_id or "").strip()
    eid = str(estabelecimento_id or "").strip()
    uid = str(user_id or "").strip()
    rows = [
        s for s in (_load_sessoes().get("sessoes") or [])
        if str(s.get("status")) == "aberta"
    ]
    if tid:
        rows = [s for s in rows if str(s.get("terminal_id") or "") == tid]
    if eid:
        rows = [s for s in rows if str(s.get("estabelecimento_id") or "") == eid]
    if uid and not tid:
        rows = [s for s in rows if str(s.get("user_id") or "") == uid]
    rows.sort(key=lambda s: s.get("opened_at") or "", reverse=True)
    return rows[0] if rows else None


def list_sessoes(terminal_id=None, estabelecimento_id=None, status=None, limit=50):
    rows = list(_load_sessoes().get("sessoes") or [])
    tid = str(terminal_id or "").strip()
    eid = str(estabelecimento_id or "").strip()
    st = str(status or "").strip().lower()
    if tid:
        rows = [s for s in rows if str(s.get("terminal_id") or "") == tid]
    if eid:
        rows = [s for s in rows if str(s.get("estabelecimento_id") or "") == eid]
    if st:
        rows = [s for s in rows if str(s.get("status") or "") == st]
    rows.sort(key=lambda s: s.get("opened_at") or "", reverse=True)
    return rows[: max(1, min(int(limit or 50), 200))]


def abrir_sessao(payload, user_id=None):
    body = payload if isinstance(payload, dict) else {}
    tid = str(body.get("terminal_id") or "").strip()
    eid = str(body.get("estabelecimento_id") or "").strip()
    if not tid:
        raise ValueError("terminal_id obrigatório")
    if not eid:
        raise ValueError("estabelecimento_id obrigatório")
    existing = get_sessao_aberta(terminal_id=tid)
    if existing:
        raise ValueError(f"já existe sessão aberta #{existing.get('id')} neste terminal")
    try:
        fundo = float(body.get("fundo_troco") or body.get("fundo") or 0)
    except (TypeError, ValueError):
        fundo = 0.0
    if fundo < 0:
        raise ValueError("fundo_troco inválido")

    data = _load_sessoes()
    sid = str(uuid.uuid4())[:8]
    sessao = {
        "id": sid,
        "terminal_id": tid,
        "estabelecimento_id": eid,
        "user_id": user_id,
        "user_nome": body.get("user_nome") or "",
        "status": "aberta",
        "fundo_troco": round(fundo, 2),
        "opened_at": _now(),
        "closed_at": None,
        "closed_by": None,
        "contado": None,
        "esperado": None,
        "diferenca": None,
        "totais_pg": {},
        "vendas_count": 0,
        "vendas_total": 0.0,
        "suprimentos": 0.0,
        "sangrias": 0.0,
        "nota": (body.get("nota") or "").strip(),
    }
    data["sessoes"].append(sessao)
    _save_sessoes(data)
    return sessao


def _norm_forma(fp):
    s = str(fp or "Dinheiro").strip().lower()
    if s in ("dinheiro", "cash", "especie", "espécie"):
        return "Dinheiro"
    if s in ("pix",):
        return "PIX"
    if s in ("debito", "débito", "debit"):
        return "Débito"
    if s in ("credito", "crédito", "credit"):
        return "Crédito"
    if s in ("voucher", "vale", "vr", "va"):
        return "Voucher"
    return str(fp or "Outro").strip() or "Outro"


def _vendas_da_sessao(sessao):
    sid = str(sessao.get("id") or "")
    eid = str(sessao.get("estabelecimento_id") or "")
    opened = str(sessao.get("opened_at") or "")
    closed = str(sessao.get("closed_at") or "") or "9999"
    if not os.path.exists(VENDAS_FILE):
        return []
    try:
        with open(VENDAS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    rows = data.get("vendas") if isinstance(data, dict) else []
    if not isinstance(rows, list):
        return []
    out = []
    for v in rows:
        if not isinstance(v, dict):
            continue
        if str(v.get("sessao_id") or "") == sid:
            out.append(v)
            continue
        # fallback legado: mesmo dia + estabelecimento (se marcado)
        if sid and str(v.get("sessao_id") or ""):
            continue
        v_eid = str(v.get("estabelecimento_id") or "")
        v_at = f"{v.get('data') or ''}T{v.get('hora') or '00:00:00'}"
        if eid and v_eid and v_eid != eid:
            continue
        if opened and v_at >= opened[:19] and v_at <= closed[:19]:
            # só usa fallback se venda tem estabelecimento ou terminal caixa
            if v_eid or v.get("terminal_caixa_id"):
                if str(v.get("terminal_caixa_id") or "") in ("", str(sessao.get("terminal_id") or "")):
                    out.append(v)
    return out


def resumo_sessao(sessao_or_id):
    """Calcula totais ao vivo da sessão (aberta ou fechada)."""
    if isinstance(sessao_or_id, dict):
        sessao = sessao_or_id
    else:
        sessao = get_sessao(sessao_or_id)
    if not sessao:
        raise ValueError("sessão não encontrada")

    vendas = _vendas_da_sessao(sessao)
    totais_pg = {}
    vendas_total = 0.0
    dinheiro = 0.0
    for v in vendas:
        total = float(v.get("total") or 0)
        vendas_total += total
        forma = _norm_forma(v.get("forma_pg"))
        totais_pg[forma] = round(totais_pg.get(forma, 0) + total, 2)
        if forma == "Dinheiro":
            dinheiro += total

    movs = list_movimentos(sessao_id=sessao.get("id"), limit=200)
    # se sessão antiga sem stamp, filtra por terminal + janela
    if not movs and sessao.get("status") == "aberta":
        movs = [
            m for m in list_movimentos(terminal_id=sessao.get("terminal_id"), limit=200)
            if (m.get("at") or "") >= (sessao.get("opened_at") or "")
            and (not m.get("sessao_id") or m.get("sessao_id") == sessao.get("id"))
        ]

    suprimentos = round(sum(float(m.get("value") or 0) for m in movs if m.get("kind") == "in"), 2)
    sangrias = round(sum(float(m.get("value") or 0) for m in movs if m.get("kind") == "out"), 2)
    fundo = float(sessao.get("fundo_troco") or 0)
    esperado = round(fundo + dinheiro + suprimentos - sangrias, 2)

    return {
        "sessao": sessao,
        "vendas_count": len(vendas),
        "vendas_total": round(vendas_total, 2),
        "totais_pg": totais_pg,
        "dinheiro_vendas": round(dinheiro, 2),
        "fundo_troco": fundo,
        "suprimentos": suprimentos,
        "sangrias": sangrias,
        "esperado_dinheiro": esperado,
        "movimentos": movs[:30],
        "contado": sessao.get("contado"),
        "diferenca": sessao.get("diferenca"),
    }


def fechar_sessao(sessao_id, payload=None, user_id=None):
    body = payload if isinstance(payload, dict) else {}
    data = _load_sessoes()
    sessao = None
    for s in data.get("sessoes") or []:
        if str(s.get("id")) == str(sessao_id):
            sessao = s
            break
    if not sessao:
        raise ValueError("sessão não encontrada")
    if sessao.get("status") != "aberta":
        raise ValueError(f"sessão já está {sessao.get('status')}")

    try:
        contado = float(body.get("contado") if body.get("contado") is not None else body.get("valor_contado"))
    except (TypeError, ValueError):
        raise ValueError("contado (dinheiro físico) obrigatório")
    if contado < 0:
        raise ValueError("contado inválido")

    resumo = resumo_sessao(sessao)
    esperado = float(resumo["esperado_dinheiro"])
    diferenca = round(contado - esperado, 2)

    sessao["status"] = "fechada"
    sessao["closed_at"] = _now()
    sessao["closed_by"] = user_id
    sessao["contado"] = round(contado, 2)
    sessao["esperado"] = esperado
    sessao["diferenca"] = diferenca
    sessao["totais_pg"] = resumo["totais_pg"]
    sessao["vendas_count"] = resumo["vendas_count"]
    sessao["vendas_total"] = resumo["vendas_total"]
    sessao["suprimentos"] = resumo["suprimentos"]
    sessao["sangrias"] = resumo["sangrias"]
    sessao["nota_fechamento"] = (body.get("nota") or body.get("nota_fechamento") or "").strip()
    _save_sessoes(data)

    return {
        "sessao": sessao,
        "resumo": resumo_sessao(sessao),
    }
