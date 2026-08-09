"""
Vendor Pricelists — tabela de preços por fornecedor/produto.

Armazena:
  - produto_id / produto_nome
  - fornecedor_id / fornecedor
  - codigo_fornecedor (Vendor Product Code)
  - preco / moeda
  - lead_time (dias)
  - qtd_minima
  - validade_de / validade_ate

Fonte: dados/vendor_pricelists.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "vendor_pricelists.json")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _load():
    if not os.path.exists(DATA_FILE):
        return {"next_id": 1, "pricelists": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"next_id": 1, "pricelists": []}
    data.setdefault("pricelists", [])
    data.setdefault("next_id", 1)
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("pricelists") or [])
    jsonio.save(DATA_FILE, data)


def listar(*, fornecedor_id=None, produto_id=None, ativo=None):
    data = _load()
    rows = list(data.get("pricelists") or [])
    if fornecedor_id is not None:
        rows = [r for r in rows if str(r.get("fornecedor_id")) == str(fornecedor_id)]
    if produto_id is not None:
        rows = [r for r in rows if str(r.get("produto_id")) == str(produto_id)]
    if ativo:
        hoje = _today()
        rows = [r for r in rows if (r.get("validade_de") or "") <= hoje and (r.get("validade_ate") or "9999-12-31") >= hoje]
    rows.sort(key=lambda r: (r.get("fornecedor") or "", r.get("produto") or "", r.get("preco") or 0))
    return rows


def get(pl_id):
    for r in _load().get("pricelists") or []:
        if str(r.get("id")) == str(pl_id):
            return r
    return None


def melhor_preco(produto_id, *, fornecedor_id=None, qtd=None):
    rows = listar(produto_id=produto_id, ativo=True)
    if fornecedor_id is not None:
        rows = [r for r in rows if str(r.get("fornecedor_id")) == str(fornecedor_id)]
    if qtd is not None:
        rows = [r for r in rows if (r.get("qtd_minima") or 0) <= float(qtd)]
    if not rows:
        return None
    rows.sort(key=lambda r: (r.get("preco") or 0, r.get("lead_time") or 9999))
    return rows[0]


def save(payload, *, usuario=""):
    body = payload if isinstance(payload, dict) else {}
    data = _load()
    pid = body.get("id")
    if pid is None:
        pid = int(data.get("next_id") or 1)
        data["next_id"] = pid + 1
    else:
        pid = int(pid)
        data["pricelists"] = [r for r in data.get("pricelists") or [] if str(r.get("id")) != str(pid)]

    row = {
        "id": pid,
        "produto_id": str(body.get("produto_id") or "").strip(),
        "produto": str(body.get("produto") or "").strip(),
        "fornecedor_id": str(body.get("fornecedor_id") or "").strip(),
        "fornecedor": str(body.get("fornecedor") or "").strip(),
        "codigo_fornecedor": str(body.get("codigo_fornecedor") or "").strip(),
        "preco": float(body.get("preco") or 0),
        "moeda": str(body.get("moeda") or "BRL").strip().upper(),
        "lead_time": int(body.get("lead_time") or 0),
        "qtd_minima": float(body.get("qtd_minima") or 0),
        "validade_de": str(body.get("validade_de") or "")[:10] or _today(),
        "validade_ate": str(body.get("validade_ate") or "")[:10] or "9999-12-31",
        "updated_at": _now(),
        "updated_by": usuario,
    }
    data["pricelists"].insert(0, row)
    _save(data)
    return row


def delete(pl_id):
    data = _load()
    data["pricelists"] = [r for r in data.get("pricelists") or [] if str(r.get("id")) != str(pl_id)]
    _save(data)
    return True


def fornecedores_do_produto(produto_id):
    rows = listar(produto_id=produto_id, ativo=True)
    return sorted({r["fornecedor"] or r["fornecedor_id"] for r in rows if r.get("fornecedor") or r.get("fornecedor_id")})


def produtos_do_fornecedor(fornecedor_id):
    rows = listar(fornecedor_id=fornecedor_id, ativo=True)
    return sorted({r["produto"] or r["produto_id"] for r in rows if r.get("produto") or r.get("produto_id")})
