"""
Quality Checks no receiving — inspeção de entrada de mercadoria.

Configuração de questionários por tipo de produto/fornecedor.
Resultado: approved / partial / rejected.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "dados", "quality_check_config.json")
RESULTS_FILE = os.path.join(BASE_DIR, "dados", "quality_check_results.json")

DEFAULT_CHECKS = [
    {"id": "qtd", "label": "Quantidade conforme", "tipo": "sim_nao", "critico": True},
    {"id": "embalagem", "label": "Embalagem íntegra", "tipo": "sim_nao", "critico": False},
    {"id": "lote_validade", "label": "Lote / validade identificados", "tipo": "sim_nao", "critico": True},
    {"id": "danos", "label": "Sem avarias", "tipo": "sim_nao", "critico": True},
    {"id": "documento", "label": "Documento/etiqueta conforme", "tipo": "sim_nao", "critico": False},
]


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"checks": DEFAULT_CHECKS, "updated_at": _now()}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"checks": DEFAULT_CHECKS, "updated_at": _now()}
    data.setdefault("checks", DEFAULT_CHECKS)
    return data


def _save_config(data):
    os.makedirs(os.path.dirname(CONFIG_FILE) or ".", exist_ok=True)
    data["updated_at"] = _now()
    jsonio.save(CONFIG_FILE, data)


def _load_results():
    if not os.path.exists(RESULTS_FILE):
        return {"results": []}
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"results": []}
    data.setdefault("results", [])
    return data


def _save_results(data):
    os.makedirs(os.path.dirname(RESULTS_FILE) or ".", exist_ok=True)
    data["updated_at"] = _now()
    jsonio.save(RESULTS_FILE, data)


def listar_checks():
    return list(_load_config().get("checks") or DEFAULT_CHECKS)


def salvar_config(checks):
    data = _load_config()
    data["checks"] = checks
    _save_config(data)
    return data


def avaliar(receiving_id, respostas, *, usuario=""):
    """
    respostas: dict {check_id: bool} ou list de dicts com check_id e ok.
    Retorna resultado approved/partial/rejected.
    """
    config = _load_config()
    checks = {c["id"]: c for c in (config.get("checks") or DEFAULT_CHECKS)}
    if isinstance(respostas, dict):
        respostas = [{"check_id": k, "ok": bool(v)} for k, v in respostas.items()]

    respostas_norm = []
    for r in respostas or []:
        if not isinstance(r, dict):
            continue
        cid = r.get("check_id") or r.get("id")
        if not cid:
            continue
        respostas_norm.append({
            "check_id": cid,
            "ok": bool(r.get("ok") or r.get("valor")),
            "obs": r.get("obs") or "",
        })

    critico_rejeitado = False
    for r in respostas_norm:
        c = checks.get(r["check_id"])
        if not c:
            continue
        if c.get("critico") and not r["ok"]:
            critico_rejeitado = True

    total = len(respostas_norm)
    ok_count = sum(1 for r in respostas_norm if r["ok"])
    if not total:
        resultado = "approved"
    elif critico_rejeitado:
        resultado = "rejected"
    elif ok_count < total:
        resultado = "partial"
    else:
        resultado = "approved"

    record = {
        "receiving_id": str(receiving_id),
        "respostas": respostas_norm,
        "resultado": resultado,
        "ok_count": ok_count,
        "total": total,
        "avaliado_em": _now(),
        "avaliado_por": usuario,
    }
    data = _load_results()
    data["results"] = [r for r in data["results"] if str(r.get("receiving_id")) != str(receiving_id)]
    data["results"].append(record)
    _save_results(data)
    return record


def get_resultado(receiving_id):
    for r in _load_results().get("results") or []:
        if str(r.get("receiving_id")) == str(receiving_id):
            return r
    return None
