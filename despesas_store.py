"""
Despesas do RH — reembolsos com aprovação (workflow do dashboard).

Seguem o mesmo fluxo das licenças: status D/S/A/R/C (workflow.json), com
"pendentes" = status S (enviadas para aprovação). Fonte: dados/despesas.json
"""

from __future__ import annotations

import os
from datetime import datetime

import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DESPESAS_FILE = os.path.join(BASE_DIR, "dados", "despesas.json")


def _load() -> dict:
    data = jsonio.load(DESPESAS_FILE, None)
    if not isinstance(data, dict) or not isinstance(data.get("despesas"), list):
        return {"despesas": [], "atualizado_em": ""}
    return data


def _save(data: dict) -> None:
    data["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    jsonio.save(DESPESAS_FILE, data)


def _proximo_id(despesas: list) -> int:
    return max((int(d.get("id") or 0) for d in despesas), default=0) + 1


def listar() -> list:
    return _load()["despesas"]


def pendentes() -> list:
    """Despesas enviadas aguardando aprovação (status S)."""
    return [d for d in listar() if str(d.get("status") or "").upper() == "S"]


def incluir(dados: dict) -> dict:
    """Registra uma despesa (status padrão S = enviada para aprovação)."""
    despesas = listar()
    registro = {
        "id": _proximo_id(despesas),
        "funcionario_id": dados.get("funcionario_id") or 0,
        "data": dados.get("data") or "",
        "categoria": dados.get("categoria") or "",
        "descricao": dados.get("descricao") or "",
        "valor": float(dados.get("valor") or 0),
        "status": (dados.get("status") or "S").upper(),
        "aprovado_por": "",
        "data_aprovacao": "",
        "observacoes": dados.get("observacoes") or "",
    }
    despesas.append(registro)
    _save({"despesas": despesas})
    return registro


def _set_status(id_val, status: str, aprovado_por: str = "", data_aprovacao: str = "") -> bool:
    despesas = listar()
    achou = False
    for d in despesas:
        if str(d.get("id")) == str(id_val):
            d["status"] = status.upper()
            if aprovado_por:
                d["aprovado_por"] = aprovado_por
            if data_aprovacao:
                d["data_aprovacao"] = data_aprovacao
            achou = True
            break
    if achou:
        _save({"despesas": despesas})
    return achou


def aprovar(id_val, aprovado_por: str = "", data_aprovacao: str = "") -> bool:
    return _set_status(id_val, "A", aprovado_por, data_aprovacao)


def rejeitar(id_val, aprovado_por: str = "", data_aprovacao: str = "") -> bool:
    return _set_status(id_val, "R", aprovado_por, data_aprovacao)


def transitar(id_val, status: str, aprovado_por: str = "", data_aprovacao: str = "") -> bool:
    return _set_status(id_val, status, aprovado_por, data_aprovacao)
