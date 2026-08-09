"""
SPED Fiscal — wrapper sobre modules/sped/sped_fiscal.gerar_sped_fiscal.
"""

from __future__ import annotations

import json
import os

from modules.sped import sped_fiscal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def gerar(competencia=None):
    empresa = _load_json(os.path.join(BASE_DIR, "dados", "empresa.json"))
    nfe = _load_json(os.path.join(BASE_DIR, "dados", "nfe.json"))
    nfce = _load_json(os.path.join(BASE_DIR, "dados", "nfce.json"))
    produtos = _load_json(os.path.join(BASE_DIR, "dados", "produtos.json"))
    contatos = _load_json(os.path.join(BASE_DIR, "data", "contatos.json"))
    inv = _load_json(os.path.join(BASE_DIR, "data", "inventory_balances.json"))
    inventario = (inv.get("por_estabelecimento") or {}).get("matriz", {})
    return sped_fiscal.gerar_sped_fiscal(
        empresa=empresa,
        competencia=competencia,
        nfe_list=nfe.get("nfe", []),
        nfce_list=nfce.get("nfce", []),
        produtos=produtos.get("produtos", []),
        contatos=contatos,
        inventario=inventario,
    )
