"""
Currency / Multi Currency — taxas de câmbio e conversão.

Moeda base: BRL.
Fonte: dados/currency_rates.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RATES_FILE = os.path.join(BASE_DIR, "dados", "currency_rates.json")
PEDIDO_MOEDAS_FILE = os.path.join(BASE_DIR, "dados", "pedido_moedas.json")

BASE_CURRENCY = "BRL"

DEFAULT_RATES = {
    "BRL": 1.0,
    "USD": 5.0,
    "EUR": 5.5,
    "ARS": 0.02,
    "CNY": 0.75,
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_rates():
    if not os.path.exists(RATES_FILE):
        return {"moeda_base": BASE_CURRENCY, "rates": dict(DEFAULT_RATES), "updated_at": _now()}
    with open(RATES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"moeda_base": BASE_CURRENCY, "rates": dict(DEFAULT_RATES), "updated_at": _now()}
    data.setdefault("moeda_base", BASE_CURRENCY)
    data.setdefault("rates", dict(DEFAULT_RATES))
    return data


def _save_rates(data):
    os.makedirs(os.path.dirname(RATES_FILE) or ".", exist_ok=True)
    data["updated_at"] = _now()
    jsonio.save(RATES_FILE, data)


def listar_moedas():
    data = _load_rates()
    return data.get("rates", {})


def get_rate(moeda):
    rates = listar_moedas()
    return rates.get(str(moeda).upper(), 1.0)


def set_rate(moeda, taxa, *, usuario=""):
    data = _load_rates()
    data["rates"][str(moeda).upper()] = float(taxa)
    data.setdefault("history", []).insert(0, {
        "moeda": str(moeda).upper(), "taxa": float(taxa), "usuario": usuario, "data": _now(),
    })
    _save_rates(data)
    return data["rates"]


def converter(valor, de_moeda, para_moeda="BRL"):
    """Converte valor usando taxas baseadas em BRL."""
    de = str(de_moeda).upper()
    para = str(para_moeda).upper()
    if de == para:
        return float(valor)
    rates = listar_moedas()
    base = rates.get(BASE_CURRENCY, 1.0)
    de_rate = rates.get(de, base)
    para_rate = rates.get(para, base)
    valor_brl = float(valor) * (de_rate / base) if de_rate else 0
    return valor_brl * (base / para_rate) if para_rate else 0


# ── Moeda por pedido de compra (até ter campo no COBOL) ───────

def _load_pedido_moedas():
    if not os.path.exists(PEDIDO_MOEDAS_FILE):
        return {"pedidos": {}}
    with open(PEDIDO_MOEDAS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"pedidos": {}}
    data.setdefault("pedidos", {})
    return data


def _save_pedido_moedas(data):
    os.makedirs(os.path.dirname(PEDIDO_MOEDAS_FILE) or ".", exist_ok=True)
    data["updated_at"] = _now()
    jsonio.save(PEDIDO_MOEDAS_FILE, data)


def get_pedido_moeda(pedido_id):
    data = _load_pedido_moedas()
    return data.get("pedidos", {}).get(str(pedido_id), {"moeda": BASE_CURRENCY, "taxa": 1.0})


def set_pedido_moeda(pedido_id, moeda, taxa=None, *, usuario=""):
    data = _load_pedido_moedas()
    m = str(moeda).upper()
    t = float(taxa) if taxa is not None else get_rate(m)
    data["pedidos"][str(pedido_id)] = {
        "moeda": m,
        "taxa": t,
        "updated_at": _now(),
        "updated_by": usuario,
    }
    _save_pedido_moedas(data)
    return data["pedidos"][str(pedido_id)]
