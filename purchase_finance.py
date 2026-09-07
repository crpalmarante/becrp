"""
Contas a Pagar (AP) — MVP a partir de NF-e de entrada / receiving.

Fonte: dados/titulos_ap.json (projeção).
Gera títulos pelas duplicatas da NF-e ou 1 parcela = valor total.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "titulos_ap.json")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _today():
    return datetime.now().date()


def _money(val):
    try:
        return Decimal(str(val or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _digits(val):
    return "".join(c for c in str(val or "") if c.isdigit())


def _load():
    if not os.path.exists(DATA_FILE):
        return {"titulos": [], "seq": 0}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"titulos": [], "seq": 0}
    data.setdefault("titulos", [])
    data.setdefault("seq", 0)
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("titulos") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def listar(status=None, partner_id=None):
    rows = list(_load().get("titulos") or [])
    if status:
        rows = [t for t in rows if t.get("status") == status]
    if partner_id:
        pid = str(partner_id)
        rows = [t for t in rows if str(t.get("partner_id") or "") == pid]
    return rows


def create_from_receiving(rec, *, usuario=""):
    """
    Idempotente por chave NF-e / receiving_id.
    Usa nfe.duplicatas se houver; senão 1 título à vista/30d.
    """
    rec = rec or {}
    nfe = rec.get("nfe") or {}
    chave = _digits(nfe.get("chave") or rec.get("documento_ref"))
    rid = rec.get("id")

    data = _load()
    existing = [
        t for t in data.get("titulos") or []
        if (chave and _digits(t.get("chave_nfe")) == chave)
        or (rid is not None and str(t.get("receiving_id")) == str(rid))
    ]
    if existing:
        return {"titulos": existing, "already": True}

    dups = list(nfe.get("duplicatas") or [])
    total = _money(nfe.get("valor_total"))
    if total <= 0:
        # soma itens
        for it in rec.get("items") or []:
            nx = it.get("nfe_item") or {}
            q = it.get("qty_verified")
            if q is None:
                q = it.get("qty_expected") or 0
            total += _money(q) * _money(nx.get("preco_unit"))

    if not dups:
        if total <= 0:
            raise ValueError("valor da NF-e inválido para AP")
        venc = (_today() + timedelta(days=30)).strftime("%Y-%m-%d")
        dups = [{"n_dup": "001", "vencimento": venc, "valor": float(total)}]

    created = []
    seq = int(data.get("seq") or 0)
    n = len(dups)
    for i, d in enumerate(dups, start=1):
        seq += 1
        valor = _money(d.get("valor") or d.get("vDup") or 0)
        if valor <= 0 and n == 1:
            valor = total
        venc = str(d.get("vencimento") or d.get("dVenc") or "")[:10]
        if not venc:
            venc = (_today() + timedelta(days=30 * i)).strftime("%Y-%m-%d")
        tid = f"AP-{seq:05d}"
        row = {
            "id": tid,
            "seq": seq,
            "partner_id": rec.get("fornecedor_id") or "",
            "fornecedor": rec.get("fornecedor_nome") or "",
            "cnpj": _digits(nfe.get("fornecedor_cnpj") or rec.get("fornecedor_cnpj")),
            "receiving_id": rid,
            "chave_nfe": chave,
            "nfe_numero": nfe.get("numero") or "",
            "nfe_serie": nfe.get("serie") or "",
            "parcela": i,
            "parcelas": n,
            "n_dup": str(d.get("n_dup") or d.get("nDup") or f"{i:03d}"),
            "valor": float(valor),
            "saldo": float(valor),
            "vencimento": venc,
            "status": "aberto",
            "usuario": str(usuario or ""),
            "criado_em": _now(),
        }
        created.append(row)
        data["titulos"].insert(0, row)

    data["seq"] = seq
    _save(data)
    return {"titulos": created, "already": False, "source": "titulos_ap.json"}


def create_from_commission(*, employee_id, employee_name, period, valor, vencimento=None,
                           comissao_ids=None, usuario=""):
    """
    Gera um título a pagar (AP) para um vendedor/operador a partir do total de
    comissões de um período. O vendedor é tratado como fornecedor de serviço de
    venda (commission payable).
    """
    if not employee_id:
        raise ValueError("employee_id é obrigatório")
    valor = _money(valor)
    if valor <= 0:
        raise ValueError("valor da comissão deve ser positivo")
    if not vencimento:
        vencimento = (_today() + timedelta(days=30)).strftime("%Y-%m-%d")
    vencimento = str(vencimento)[:10]

    data = _load()
    seq = int(data.get("seq") or 0)
    seq += 1
    tid = f"AP-{seq:05d}"
    row = {
        "id": tid,
        "seq": seq,
        "partner_id": str(employee_id),
        "fornecedor": str(employee_name or employee_id),
        "cnpj": "",
        "receiving_id": None,
        "chave_nfe": "",
        "nfe_numero": "",
        "nfe_serie": "",
        "parcela": 1,
        "parcelas": 1,
        "n_dup": "001",
        "valor": float(valor),
        "saldo": float(valor),
        "vencimento": vencimento,
        "status": "aberto",
        "origem": "comissao",
        "periodo": str(period or ""),
        "comissao_ids": list(comissao_ids or []),
        "usuario": str(usuario or ""),
        "criado_em": _now(),
    }
    data["titulos"].insert(0, row)
    data["seq"] = seq
    _save(data)
    return {"titulo": row, "already": False, "source": "titulos_ap.json"}
