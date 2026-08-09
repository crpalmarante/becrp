"""
Reforma Tributária (IBS/CBS) — orquestração Python + cálculo COBOL.

Fonte da verdade dos cálculos: cobol/bin/calc_reforma_tributaria
Tabela de alíquotas: dados/fiscal_reforma_aliq.json
"""

from __future__ import annotations

import json
import os

import cobol_bridge
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALIQS_FILE = os.path.join(BASE_DIR, "dados", "fiscal_reforma_aliq.json")
HISTORY_FILE = os.path.join(BASE_DIR, "dados", "fiscal_reforma_history.json")

DEFAULT_ALIQS = {
    "padrao": {"cbs": 0.6, "ibs": 17.0, "reducao": 0.0},
    "por_ncm": {
        "8517.12.00": {"cbs": 0.6, "ibs": 17.0, "reducao": 0.0},
        "3004.90.99": {"cbs": 0.6, "ibs": 17.0, "reducao": 20.0},
    },
}


def _now():
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def _load_aliqs():
    if not os.path.exists(ALIQS_FILE):
        return dict(DEFAULT_ALIQS)
    with open(ALIQS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return dict(DEFAULT_ALIQS)
    data.setdefault("padrao", DEFAULT_ALIQS["padrao"])
    data.setdefault("por_ncm", DEFAULT_ALIQS["por_ncm"])
    return data


def _save_aliqs(data):
    os.makedirs(os.path.dirname(ALIQS_FILE) or ".", exist_ok=True)
    data["updated_at"] = _now()
    jsonio.save(ALIQS_FILE, data)


def _load_history():
    if not os.path.exists(HISTORY_FILE):
        return {"calculos": []}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"calculos": []}
    data.setdefault("calculos", [])
    return data


def _save_history(data):
    os.makedirs(os.path.dirname(HISTORY_FILE) or ".", exist_ok=True)
    data["updated_at"] = _now()
    jsonio.save(HISTORY_FILE, data)


def get_aliquotas(ncm=None):
    data = _load_aliqs()
    padrao = data.get("padrao", DEFAULT_ALIQS["padrao"])
    if not ncm:
        return padrao
    ncm = str(ncm).strip()
    return data.get("por_ncm", {}).get(ncm, padrao)


def listar_aliquotas():
    return _load_aliqs()


def salvar_aliquotas(padrao, por_ncm):
    data = _load_aliqs()
    data["padrao"] = {
        "cbs": float(padrao.get("cbs", 0.6)),
        "ibs": float(padrao.get("ibs", 17.0)),
        "reducao": float(padrao.get("reducao", 0.0)),
    }
    if isinstance(por_ncm, dict):
        data["por_ncm"] = por_ncm
    _save_aliqs(data)
    return data


def calcular(valor, ncm=None, aliquotas=None, *, usuario="", contexto=""):
    """
    Chama COBOL para calcular CBS/IBS.
    """
    if aliquotas is None:
        aliquotas = get_aliquotas(ncm)

    env = {
        "VALOR": str(float(valor)),
        "NCM": str(ncm or ""),
        "ALIQ_CBS": str(float(aliquotas.get("cbs", 0.6))),
        "ALIQ_IBS": str(float(aliquotas.get("ibs", 17.0))),
        "REDUCAO": str(float(aliquotas.get("reducao", 0.0))),
    }
    out, err = cobol_bridge._run("calc_reforma_tributaria", env)
    text = (out or "").strip()
    start = text.find("{")
    if start < 0:
        raise ValueError(f"COBOL não retornou JSON: {out} {err}")
    try:
        result = json.loads(text[start:])
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON inválido do COBOL: {text[start:]} {e}")

    record = {
        "valor": float(valor),
        "ncm": str(ncm or ""),
        "aliquotas": aliquotas,
        "resultado": result,
        "calculado_em": _now(),
        "calculado_por": usuario,
        "contexto": contexto,
    }
    data = _load_history()
    data["calculos"].insert(0, record)
    _save_history(data)
    return result
