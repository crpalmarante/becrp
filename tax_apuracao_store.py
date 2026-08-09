"""
Apuração de impostos — consolida entradas e saídas para cálculo de créditos/débitos.

Fontes:
  - Entradas: dados/nfe_entrada.json
  - Saídas: dados/nfe.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import sped_livros_store
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "dados", "tax_apuracao_history.json")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_history():
    if not os.path.exists(HISTORY_FILE):
        return {"apuracoes": []}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"apuracoes": []}
    data.setdefault("apuracoes", [])
    return data


def _save_history(data):
    os.makedirs(os.path.dirname(HISTORY_FILE) or ".", exist_ok=True)
    data["updated_at"] = _now()
    jsonio.save(HISTORY_FILE, data)


def _parse_competencia(data_str):
    if not data_str or len(data_str) < 7:
        return ""
    return data_str[:7]


def apurar(dt_ini=None, dt_fim=None, *, usuario=""):
    livro = sped_livros_store.livro(dt_ini=dt_ini, dt_fim=dt_fim)
    rows = livro.get("rows", [])

    # consolida por competência (YYYY-MM)
    by_comp = {}
    for row in rows:
        comp = _parse_competencia(row.get("data"))
        if not comp:
            comp = "sem_data"
        bucket = by_comp.setdefault(comp, {
            "entradas": {"qtd": 0, "valor": 0.0, "icms_cred": 0.0, "pis_cred": 0.0, "cofins_cred": 0.0, "cbs_cred": 0.0, "ibs_cred": 0.0},
            "saidas": {"qtd": 0, "valor": 0.0, "icms_deb": 0.0, "pis_deb": 0.0, "cofins_deb": 0.0, "cbs_deb": 0.0, "ibs_deb": 0.0},
        })
        if row.get("tipo") == "entrada":
            b = bucket["entradas"]
            b["qtd"] += 1
            b["valor"] += row.get("valor_total") or 0
            b["icms_cred"] += row.get("valor_icms") or 0
            b["pis_cred"] += 0.0
            b["cofins_cred"] += 0.0
            b["cbs_cred"] += row.get("valor_cbs") or 0
            b["ibs_cred"] += row.get("valor_ibs") or 0
        else:
            b = bucket["saidas"]
            b["qtd"] += 1
            b["valor"] += row.get("valor_total") or 0
            b["icms_deb"] += row.get("valor_icms") or 0
            b["pis_deb"] += 0.0
            b["cofins_deb"] += 0.0
            b["cbs_deb"] += row.get("valor_cbs") or 0
            b["ibs_deb"] += row.get("valor_ibs") or 0

    # PIS/COFINS simplificado: assume alíquota cumulativa sobre base de entradas/saídas
    pis_alq = 0.65
    cofins_alq = 3.0
    for comp, bucket in by_comp.items():
        if comp == "sem_data":
            continue
        bucket["entradas"]["pis_cred"] = round(bucket["entradas"]["valor"] * pis_alq / 100, 2)
        bucket["entradas"]["cofins_cred"] = round(bucket["entradas"]["valor"] * cofins_alq / 100, 2)
        bucket["saidas"]["pis_deb"] = round(bucket["saidas"]["valor"] * pis_alq / 100, 2)
        bucket["saidas"]["cofins_deb"] = round(bucket["saidas"]["valor"] * cofins_alq / 100, 2)
        for grupo in ("entradas", "saidas"):
            for k in bucket[grupo]:
                if isinstance(bucket[grupo][k], float):
                    bucket[grupo][k] = round(bucket[grupo][k], 2)

    result = {
        "periodo": {"dt_ini": dt_ini or "", "dt_fim": dt_fim or ""},
        "competencias": {k: v for k, v in sorted(by_comp.items())},
        "total_geral": {
            "icms": round(sum(b["saidas"]["icms_deb"] - b["entradas"]["icms_cred"] for b in by_comp.values()), 2),
            "pis": round(sum(b["saidas"]["pis_deb"] - b["entradas"]["pis_cred"] for b in by_comp.values()), 2),
            "cofins": round(sum(b["saidas"]["cofins_deb"] - b["entradas"]["cofins_cred"] for b in by_comp.values()), 2),
            "cbs": round(sum(b["saidas"]["cbs_deb"] - b["entradas"]["cbs_cred"] for b in by_comp.values()), 2),
            "ibs": round(sum(b["saidas"]["ibs_deb"] - b["entradas"]["ibs_cred"] for b in by_comp.values()), 2),
        },
        "apurado_em": _now(),
        "apurado_por": usuario,
    }
    data = _load_history()
    data["apuracoes"].insert(0, result)
    _save_history(data)
    return result


def historico(limit=50):
    return list(_load_history().get("apuracoes", []))[:limit]
