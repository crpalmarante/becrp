"""
Central de configurações (Settings) — geral e por módulo.

Inspirado no Odoo: cada módulo expõe suas chaves de configuração.
Fonte: dados/settings.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "dados", "settings.json")

DEFAULTS = {
    "geral": {
        # vazio = identidade vem de data/organizacao.json + matriz em
        # data/empresas.json (org_store). Preenchido só para override manual.
        "empresa_nome": "",
        "moeda": "BRL",
        "idioma": "pt-BR",
        "fuso_horario": "America/Sao_Paulo",
        "casas_decimais_valor": 2,
        "casas_decimais_qtd": 3,
    },
    "compras": {
        "aprovacao_limite_direto": 5000.0,
        "aprovacao_roles": ["manager", "admin", "aprovador_compras"],
        "status_inicial_pedido": "rascunho",
        "requer_aprovacao": True,
        "permitir_pedido_sem_aprovacao": False,
        "bloquear_edicao_pedido_enviado": True,
        "bloquear_edicao_pedido_recebido": True,
        "comprador_padrao": "",
        "condicao_pg_padrao": "30",
        "forma_pg_padrao": "Boleto",
        "unidade_padrao": "UN",
        "dias_previsao_padrao": 7,
        "email_notificacao_aprovacao": "",
        "numero_itens_por_pedido": 0,
    },
    "fiscal": {
        "ambiente_sefaz": "homologacao",
        "serie_nfe": 1,
        "serie_nfce": 1,
        "regime_tributario": "simples_nacional",
    },
    "estoque": {
        "controle_lote": False,
        "controle_serie": False,
        "estoque_negativo": False,
        "rotas_multiplas_etapas": False,
    },
    "wms": {
        "contagem_requer_aprovacao": True,
        "contagem_dupla_divergencia": False,
    },
    "vendas": {
        "pedido_precisa_aprovacao": False,
        "limite_credito_auto": True,
    },
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load():
    if not os.path.exists(SETTINGS_FILE):
        return {"modulos": {}}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"modulos": {}}
    data.setdefault("modulos", {})
    return data


def _save(data):
    data["atualizado_em"] = _now()
    jsonio.save(SETTINGS_FILE, data)  # jsonio.save garante o diretório


def listar():
    """Retorna todas as configurações com defaults aplicados."""
    data = _load()
    out = {}
    for mod, defaults in DEFAULTS.items():
        cfg = dict(defaults)
        cfg.update(data.get("modulos", {}).get(mod, {}))
        out[mod] = cfg
    return {"modulos": out, "atualizado_em": data.get("atualizado_em")}


def get(modulo, chave=None, default=None):
    data = _load()
    cfg = data.get("modulos", {}).get(modulo, {})
    if chave is None:
        # merge com defaults
        out = dict(DEFAULTS.get(modulo, {}))
        out.update(cfg)
        return out
    if chave in cfg:
        return cfg[chave]
    if chave in (DEFAULTS.get(modulo) or {}):
        return DEFAULTS[modulo][chave]
    return default


def set_key(modulo, chave, valor, *, usuario=""):
    data = _load()
    data.setdefault("modulos", {}).setdefault(modulo, {})
    data["modulos"][modulo][chave] = valor
    data.setdefault("history", []).insert(0, {
        "modulo": modulo,
        "chave": chave,
        "valor": valor,
        "usuario": usuario,
        "data": _now(),
    })
    _save(data)
    return get(modulo)


def set_modulo(modulo, valores, *, usuario=""):
    data = _load()
    data.setdefault("modulos", {}).setdefault(modulo, {})
    for k, v in valores.items():
        data["modulos"][modulo][k] = v
        data.setdefault("history", []).insert(0, {
            "modulo": modulo,
            "chave": k,
            "valor": v,
            "usuario": usuario,
            "data": _now(),
        })
    _save(data)
    return get(modulo)


def reset_modulo(modulo):
    data = _load()
    if modulo in data.get("modulos", {}):
        del data["modulos"][modulo]
    _save(data)
    return get(modulo)


def modulos_disponiveis():
    return sorted(DEFAULTS.keys())
