"""
Mapping Financeiro → Contábil (RFC-0100, seção 7).

O mapping é uma regra de configuração do Accounting Engine:
fatos financeiros neutros (forma de pagamento, tributo) → contas GL / regras de posting.

O domínio financeiro nunca conhece esses códigos. Trocar a conta de um meio
de pagamento é mudança de configuração contábil, sem impacto no Finance.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import planocontas

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPPING_FILE = os.path.join(BASE_DIR, "dados", "accounting_mapping.json")

DEFAULT_MAPPING = {
    "versao": "1.0",
    "payment_methods": [
        {
            "forma": "Dinheiro",
            "aliases": ["dinheiro", "cash", "caixa", "especie", "espécie", "vista"],
            "evento": "sale_cash",
            "regra": "SALE_CASH",
            "conta_debito": "1.01.01.01.01",
        },
        {
            "forma": "PIX / Banco",
            "aliases": ["pix", "banco", "transfer", "transf", "ted", "doc", "cartao", "cartão", "debito", "débito", "credito", "crédito", "cart"],
            "evento": "sale_bank",
            "regra": "SALE_BANK",
            "conta_debito": "1.01.01.02.01",
        },
        {
            "forma": "Boleto",
            "aliases": ["boleto"],
            "evento": "sale_bank",
            "regra": "SALE_BANK",
            "conta_debito": "1.01.01.02.01",
        },
    ],
    "tax_accounts": {
        "ipi": "2.01.01.09.02",
        "icms": "2.01.01.09.03",
        "pis": "2.01.01.09.04",
        "cofins": "2.01.01.09.05",
    },
    "atualizado_em": None,
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load():
    if not os.path.exists(MAPPING_FILE):
        data = json.loads(json.dumps(DEFAULT_MAPPING))
        _save(data)
        return data
    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        data = json.loads(json.dumps(DEFAULT_MAPPING))
    data.setdefault("versao", DEFAULT_MAPPING["versao"])
    if not isinstance(data.get("payment_methods"), list):
        data["payment_methods"] = json.loads(json.dumps(DEFAULT_MAPPING["payment_methods"]))
    data["payment_methods"] = [
        {**json.loads(json.dumps(DEFAULT_MAPPING["payment_methods"][0])), **pm}
        for pm in data["payment_methods"]
    ]
    tax = data.get("tax_accounts") if isinstance(data.get("tax_accounts"), dict) else {}
    merged_tax = dict(DEFAULT_MAPPING["tax_accounts"])
    merged_tax.update({str(k).strip().lower(): v for k, v in tax.items()})
    data["tax_accounts"] = merged_tax
    return data


def _save(data):
    os.makedirs(os.path.dirname(MAPPING_FILE) or ".", exist_ok=True)
    data = dict(data or {})
    data["atualizado_em"] = _now()
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_mapping():
    return _load()


def tax_accounts():
    return dict(_load().get("tax_accounts") or {})


def resolve_forma_pg(forma):
    """Forma de pagamento (fato financeiro) → regra de posting (contábil)."""
    s = str(forma or "").strip().lower()
    if not s:
        return None
    for pm in _load().get("payment_methods") or []:
        for alias in pm.get("aliases") or []:
            if str(alias).strip().lower() in s:
                return dict(pm)
        if str(pm.get("forma") or "").strip().lower() == s:
            return dict(pm)
    return None


def update_mapping(payload):
    body = payload if isinstance(payload, dict) else {}
    data = _load()
    if isinstance(body.get("payment_methods"), list):
        rows = []
        for pm in body["payment_methods"]:
            if not isinstance(pm, dict):
                raise ValueError("cada payment_method deve ser um objeto")
            forma = str(pm.get("forma") or "").strip()
            if not forma:
                raise ValueError("forma obrigatória em cada payment_method")
            evento = str(pm.get("evento") or "").strip().lower()
            regra = str(pm.get("regra") or "").strip().upper()
            conta = str(pm.get("conta_debito") or "").strip()
            if not evento or not regra or not conta:
                raise ValueError(f"payment_method '{forma}': evento, regra e conta_debito obrigatórios")
            _resolve_conta(conta, f"payment_method '{forma}'.conta_debito")
            rows.append(
                {
                    "forma": forma,
                    "aliases": [str(a).strip().lower() for a in (pm.get("aliases") or []) if str(a).strip()],
                    "evento": evento,
                    "regra": regra,
                    "conta_debito": conta,
                }
            )
        if not rows:
            raise ValueError("payment_methods não pode ser vazio")
        data["payment_methods"] = rows
    if isinstance(body.get("tax_accounts"), dict):
        tax = {}
        for nome, conta in body["tax_accounts"].items():
            nome = str(nome).strip().lower()
            if not nome:
                continue
            if conta in (None, ""):
                tax.pop(nome, None)
                continue
            _resolve_conta(str(conta), f"tax_account '{nome}'")
            tax[nome] = str(conta)
        data["tax_accounts"] = tax
    _save(data)
    return data


def _resolve_conta(ref, label="conta"):
    key = str(ref or "").strip()
    if not key:
        raise ValueError(f"{label} obrigatória")
    conta = planocontas.get_conta(key)
    if not conta:
        raise ValueError(f"{label} não encontrada: {key}")
    if str(conta.get("tipo") or "").upper() != "A":
        raise ValueError(f"{label} deve ser analítica: {key}")
    return str(conta.get("classificacao") or conta.get("codigo")), conta
