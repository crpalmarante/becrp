"""
WMS — Aluguel / locação de produtos (RFC-9014 MVP).

Registra locações de produtos alugáveis, detecta vencimentos pelo prazo de
devolução e gera as movimentações automáticas de retorno (via rota tipo
'aluguel' + local padrão do produto como destino final).

Fonte: dados/wms_rental.json
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta

import cobol_bridge
import wms_routes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_rental.json")

LOCACAO_STATUS = {
    "ativo": "Ativa",
    "vencido": "Vencida",
    "devolucao_gerada": "Devolução gerada",
    "devolvido": "Devolvido",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _today():
    return date.today().isoformat()


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return _empty()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return _empty()
    if not isinstance(data.get("locacoes"), list):
        data["locacoes"] = []
    if data.get("seq") is None:
        data["seq"] = len(data["locacoes"])
    return data


def _empty():
    return {"seq": 0, "locacoes": [], "atualizado_em": _now(), "total": 0}


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("locacoes") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_id(data):
    seq = int(data.get("seq") or 0) + 1
    data["seq"] = seq
    return f"AL-{seq:02d}"


def _produtos_catalogo():
    out = {}
    for p in cobol_bridge.produtos_listar() or []:
        pid = str(p.get("id") or "").strip()
        if pid:
            out[pid] = p
    return out


def _build_row(payload, existing=None):
    body = payload if isinstance(payload, dict) else {}
    existing = existing or {}
    lid = str(existing.get("id") or body.get("id") or "").strip().upper()
    if not lid:
        raise ValueError("id obrigatório")

    pid = str(body.get("produto_id") if "produto_id" in body else existing.get("produto_id") or "").strip()
    if not pid:
        raise ValueError("produto_id obrigatório")
    catalogo = _produtos_catalogo()
    if pid not in catalogo:
        raise ValueError(f"produto {pid} não encontrado")

    try:
        qtd = float(body.get("qtd") if "qtd" in body else existing.get("qtd") or 0)
    except (TypeError, ValueError):
        raise ValueError("qtd deve ser número") from None
    if qtd <= 0:
        raise ValueError("qtd deve ser maior que zero")

    try:
        prazo = int(body.get("prazo_dias") if "prazo_dias" in body else existing.get("prazo_dias") or 0)
    except (TypeError, ValueError):
        raise ValueError("prazo_dias deve ser número") from None
    if prazo <= 0:
        raise ValueError("prazo_dias deve ser maior que zero")

    data_inicio = str(body.get("data_inicio") if "data_inicio" in body else existing.get("data_inicio") or _today()).strip()
    try:
        di = datetime.fromisoformat(data_inicio).date()
    except ValueError:
        raise ValueError("data_inicio inválida (use AAAA-MM-DD)") from None
    data_prevista = (di + timedelta(days=prazo)).isoformat()

    return {
        "id": lid,
        "produto_id": pid,
        "produto_nome": catalogo[pid].get("nome") or pid,
        "qtd": qtd,
        "cliente": str(body.get("cliente") if "cliente" in body else existing.get("cliente") or "").strip(),
        "data_inicio": di.isoformat(),
        "prazo_dias": prazo,
        "data_prevista": data_prevista,
        "status": str(body.get("status") if "status" in body else existing.get("status") or "ativo").strip(),
        "rota_devolucao_id": str(body.get("rota_devolucao_id") if "rota_devolucao_id" in body else existing.get("rota_devolucao_id") or "").strip(),
        "observacao": str(body.get("observacao") if "observacao" in body else existing.get("observacao") or "").strip(),
        "criado_em": existing.get("criado_em") or _now(),
        "atualizado_em": _now(),
        "devolucao": existing.get("devolucao"),
    }


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("locacoes") or []),
        "status": LOCACAO_STATUS,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_locacoes(q=None, status=None):
    data = _load_raw()
    rows = []
    for r in data.get("locacoes") or []:
        if q:
            blob = f"{r.get('id')} {r.get('produto_id')} {r.get('produto_nome')} {r.get('cliente')}".lower()
            if str(q).strip().lower() not in blob:
                continue
        if status and r.get("status") != str(status).strip().lower():
            continue
        rows.append(r)
    rows.sort(key=lambda r: (r.get("data_prevista") or "", str(r.get("id") or "")))
    return {"locacoes": rows, "total": len(rows)}


def get_locacao(lid):
    data = _load_raw()
    key = str(lid or "").strip().upper()
    for r in data.get("locacoes") or []:
        if str(r.get("id") or "").upper() == key:
            return r
    return None


def create_locacao(payload):
    data = _load_raw()
    body = dict(payload or {})
    lid = str(body.get("id") or "").strip().upper()
    if not lid:
        lid = _next_id(data)
        body["id"] = lid
    for r in data.get("locacoes") or []:
        if str(r.get("id") or "").upper() == lid:
            raise ValueError(f"locação {lid} já existe")
    row = _build_row(body)
    data["locacoes"].append(row)
    _save(data)
    return row


def update_locacao(lid, payload):
    data = _load_raw()
    key = str(lid or "").strip().upper()
    for i, r in enumerate(data.get("locacoes") or []):
        if str(r.get("id") or "").upper() == key:
            merged = {**r, **(payload or {})}
            merged["id"] = r.get("id")
            row = _build_row(merged, existing=r)
            data["locacoes"][i] = row
            _save(data)
            return row
    raise ValueError("locação não encontrada")


def delete_locacao(lid):
    data = _load_raw()
    key = str(lid or "").strip().upper()
    for i, r in enumerate(data.get("locacoes") or []):
        if str(r.get("id") or "").upper() == key:
            data["locacoes"].pop(i)
            _save(data)
            return True
    raise ValueError("locação não encontrada")


def set_status(lid, status, nota=None):
    data = _load_raw()
    key = str(lid or "").strip().upper()
    st = str(status or "").strip().lower()
    if st not in LOCACAO_STATUS:
        raise ValueError("status deve ser: " + ", ".join(LOCACAO_STATUS))
    for i, r in enumerate(data.get("locacoes") or []):
        if str(r.get("id") or "").upper() == key:
            r["status"] = st
            r["atualizado_em"] = _now()
            if nota:
                r["observacao"] = (r.get("observacao") or "") + (f" — {nota}" if r.get("observacao") else nota)
            data["locacoes"][i] = r
            _save(data)
            return r
    raise ValueError("locação não encontrada")


# ────────────────────────────── alugáveis / vencidas ──────────────────────────────

def produtos_alugaveis():
    """Produtos marcados como alugáveis no cadastro (extras)."""
    out = []
    for p in cobol_bridge.produtos_listar() or []:
        if p.get("alugavel"):
            out.append({
                "produto_id": str(p.get("id") or "").strip(),
                "nome": p.get("nome") or p.get("id"),
                "alugavel": True,
            })
    return out


def set_alugavel(produto_id, alugavel):
    pid = str(produto_id or "").strip()
    if pid not in _produtos_catalogo():
        raise ValueError(f"produto {pid} não encontrado")
    extra = cobol_bridge.produtos_extra_get(pid)
    extra["alugavel"] = bool(alugavel)
    cobol_bridge.produtos_extra_set(pid, extra)
    return {"produto_id": pid, "alugavel": bool(alugavel)}


def _marcar_vencidas(data):
    hoje = _today()
    marcadas = []
    for i, r in enumerate(data.get("locacoes") or []):
        if r.get("status") == "ativo" and r.get("data_prevista") and r.get("data_prevista") < hoje:
            r["status"] = "vencido"
            r["atualizado_em"] = _now()
            data["locacoes"][i] = r
            marcadas.append(r.get("id"))
    return marcadas


def check_vencidos():
    """Marca como vencidas as locações ativas com prazo estourado (job do boot)."""
    data = _load_raw()
    marcadas = _marcar_vencidas(data)
    if marcadas:
        _save(data)
    return {"marcadas": marcadas, "total": len(marcadas)}


def gerar_devolucoes_vencidas(usuario=""):
    """Gera as movimentações de retorno das locações vencidas.

    Para cada locação vencida: usa a rota de aluguel (rota_devolucao_id ou a
    ativa do armazém) com o local padrão do produto como destino final.
    Ao final marca a locação como 'devolucao_gerada'.
    """
    data = _load_raw()
    _marcar_vencidas(data)
    vencidas = [r for r in data.get("locacoes") or [] if r.get("status") == "vencido"]
    if not vencidas:
        _save(data)
        return {"geradas": [], "puladas": [], "resumo": {"vencidas": 0, "geradas": 0, "puladas": 0}}

    geradas = []
    puladas = []
    for r in vencidas:
        arm = "DC-01"
        try:
            out = wms_routes.wms_routes_devolucao_aluguel(
                arm,
                r.get("produto_id"),
                r.get("qtd"),
                rota_id=r.get("rota_devolucao_id") or None,
                local_atual="CLIENTE",
                usuario=usuario,
            )
            r["status"] = "devolucao_gerada"
            r["devolucao"] = {
                "gerado_em": _now(),
                "rota_id": out.get("rota_id"),
                "passos": out.get("passos"),
                "total": out.get("total"),
            }
            r["atualizado_em"] = _now()
            geradas.append({"locacao_id": r.get("id"), "produto_id": r.get("produto_id"), "total": out.get("total"), "rota_id": out.get("rota_id")})
        except ValueError as e:
            puladas.append({"locacao_id": r.get("id"), "produto_id": r.get("produto_id"), "motivo": str(e)})

    _save(data)
    return {
        "geradas": geradas,
        "puladas": puladas,
        "resumo": {"vencidas": len(vencidas), "geradas": len(geradas), "puladas": len(puladas)},
    }
