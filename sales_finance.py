"""
Sales B2B — Crédito + Contas a Receber (MVP).

- Crédito: limite no parceiro; open AR + pedidos aprovados.
- AR: títulos gerados no faturamento (parcelas por termos).
Fonte da verdade: COBOL dados/titulos_ar.dat (gerir_titulos_ar).
Projeção: dados/sales_ar.json (consulta/relatório).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

import cobol_bridge
import pedidos_b2b_store

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "sales_ar.json")
PARTNERS_FILE = os.path.join(BASE_DIR, "data", "partners.json")
PEDIDOS_FILE = os.path.join(BASE_DIR, "dados", "pedidos_b2b.json")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _money(val):
    try:
        return Decimal(str(val or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _load():
    """Lê títulos do COBOL (fonte da verdade)."""
    try:
        rows = cobol_bridge.titulos_ar_listar()
        return {"titulos": rows or [], "source": "cobol"}
    except Exception:
        # fallback só se COBOL ainda não migrado
        if not os.path.exists(DATA_FILE):
            return {"titulos": [], "source": "empty"}
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"titulos": [], "source": "empty"}
        data.setdefault("titulos", [])
        data["source"] = "json-fallback"
        return data


def _save_projection(titulos=None):
    """Atualiza JSON de projeção a partir do COBOL."""
    try:
        cobol_bridge.titulos_ar_sync_json()
    except Exception:
        if titulos is not None:
            os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"titulos": titulos, "total": len(titulos), "atualizado_em": _now()},
                    f, indent=2, ensure_ascii=False,
                )

def _load_partners():
    try:
        import partners_store
        return partners_store.as_dict()
    except Exception:
        if not os.path.exists(PARTNERS_FILE):
            return {}
        with open(PARTNERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}


def _load_pedidos():
    try:
        return pedidos_b2b_store.listar()
    except Exception:
        if not os.path.exists(PEDIDOS_FILE):
            return []
        with open(PEDIDOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("pedidos") or []
        return data if isinstance(data, list) else []


def parse_payment_terms(terms):
    """
    '30' → [30]
    '30/60/90' → [30, 60, 90]
    'à vista' / vazio → [0]
    """
    s = str(terms or "").strip().lower()
    if not s or s in ("avista", "à vista", "a vista", "0"):
        return [0]
    parts = re.findall(r"\d+", s)
    days = [int(p) for p in parts if int(p) >= 0]
    return days or [0]


def partner_credit(partner_id):
    """Retorna config de crédito do parceiro."""
    pid = str(partner_id or "").strip()
    p = (_load_partners().get(pid) or {}) if pid else {}
    try:
        limit = float(p.get("credit_limit") if p.get("credit_limit") is not None else 0)
    except (TypeError, ValueError):
        limit = 0.0
    return {
        "partner_id": pid,
        "credit_limit": limit,
        "payment_terms": str(p.get("payment_terms") or "30").strip() or "30",
        "credit_blocked": bool(p.get("credit_blocked")),
    }


def open_ar_balance(partner_id):
    """Soma títulos em aberto do cliente."""
    pid = str(partner_id or "").strip()
    total = Decimal("0.00")
    for t in _load().get("titulos") or []:
        if str(t.get("partner_id") or "") != pid:
            continue
        if t.get("status") in ("pago", "cancelado"):
            continue
        total += _money(t.get("saldo") if t.get("saldo") is not None else t.get("valor"))
    return float(total)


def overdue_ar(partner_id):
    """Títulos em aberto com vencimento < hoje → (valor, qtd)."""
    pid = str(partner_id or "").strip()
    today = _today()
    total = Decimal("0.00")
    count = 0
    for t in _load().get("titulos") or []:
        if str(t.get("partner_id") or "") != pid:
            continue
        if t.get("status") in ("pago", "cancelado"):
            continue
        venc = str(t.get("vencimento") or "").strip()[:10]
        if not venc or venc >= today:
            continue
        total += _money(t.get("saldo") if t.get("saldo") is not None else t.get("valor"))
        count += 1
    return float(total), count


def approved_orders_exposure(partner_id, exclude_pedido_id=None):
    """Pedidos aprovados ainda não faturados contam no crédito."""
    pid = str(partner_id or "").strip()
    excl = str(exclude_pedido_id or "").strip()
    total = Decimal("0.00")
    for p in _load_pedidos():
        if str(p.get("cliente_id") or "") != pid:
            continue
        if str(p.get("id") or "") == excl:
            continue
        if p.get("status") not in ("aprovado",):
            continue
        if p.get("tipo") == "cotacao":
            continue
        total += _pedido_total(p)
    return float(total)


def pedido_total(pedido):
    total = Decimal("0.00")
    for i in (pedido or {}).get("itens") or []:
        qtd = _money(i.get("qtd"))
        preco = _money(i.get("preco"))
        desc = _money(i.get("desconto"))
        line = qtd * preco * (Decimal("1") - desc / Decimal("100"))
        total += line
        total += line * (_money(i.get("imposto")) / Decimal("100"))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# alias legado
_pedido_total = pedido_total


def check_credit(partner_id, pedido_valor, exclude_pedido_id=None):
    """
    Retorna {ok, limit, used, available, overdue, message}.
    limit=0 → sem limite de valor (ainda bloqueia se houver título vencido).
    """
    cfg = partner_credit(partner_id)
    overdue_val, overdue_count = overdue_ar(partner_id)
    if cfg.get("credit_blocked"):
        return {
            "ok": False,
            "blocked": True,
            "limit": cfg["credit_limit"],
            "used": 0,
            "available": 0,
            "overdue": overdue_val,
            "overdue_count": overdue_count,
            "pedido_valor": float(_money(pedido_valor)),
            "message": "Cliente com crédito bloqueado",
        }
    limit = float(cfg["credit_limit"] or 0)
    used = open_ar_balance(partner_id) + approved_orders_exposure(partner_id, exclude_pedido_id)
    pedido_v = float(_money(pedido_valor))
    if overdue_count > 0:
        return {
            "ok": False,
            "blocked": False,
            "limit": limit,
            "used": round(used, 2),
            "available": max(0.0, round(limit - used, 2)) if limit > 0 else None,
            "overdue": overdue_val,
            "overdue_count": overdue_count,
            "pedido_valor": pedido_v,
            "message": (
                f"Cliente com {overdue_count} título(s) vencido(s) "
                f"(R$ {overdue_val:.2f}) — aprovação financeira necessária"
            ),
        }
    if limit <= 0:
        return {
            "ok": True,
            "blocked": False,
            "limit": 0,
            "used": used,
            "available": None,
            "overdue": 0.0,
            "overdue_count": 0,
            "pedido_valor": pedido_v,
            "message": "Sem limite cadastrado — liberado",
        }
    available = max(0.0, round(limit - used, 2))
    ok = (used + pedido_v) <= (limit + 0.009)
    return {
        "ok": ok,
        "blocked": False,
        "limit": limit,
        "used": round(used, 2),
        "available": available,
        "overdue": 0.0,
        "overdue_count": 0,
        "pedido_valor": pedido_v,
        "message": (
            "Crédito OK"
            if ok
            else f"Crédito insuficiente: limite {limit:.2f}, em uso {used:.2f}, pedido {pedido_v:.2f}"
        ),
    }


def create_from_invoice(pedido, fatura, usuario=""):
    """Gera títulos a receber a partir da fatura B2B."""
    pid = str((pedido or {}).get("cliente_id") or "").strip()
    cfg = partner_credit(pid)
    terms = (pedido or {}).get("payment_terms") or cfg.get("payment_terms") or "30"
    days_list = parse_payment_terms(terms)
    total = _money((fatura or {}).get("total") or _pedido_total(pedido))
    if total <= 0:
        raise ValueError("valor da fatura inválido")

    n = len(days_list)
    base = (total / n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    parcels = [base] * n
    # ajusta centavos na última
    diff = total - sum(parcels)
    parcels[-1] = (parcels[-1] + diff).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    data = _load()
    # idempotente: se já existem títulos desta fatura, retorna
    fid = (fatura or {}).get("id")
    existing = [
        t for t in data.get("titulos") or []
        if str(t.get("fatura_id") or "") == str(fid) and t.get("status") != "cancelado"
    ]
    if existing:
        return {"titulos": existing, "already": True}

    created = []
    base_date = datetime.now().date()
    for i, days in enumerate(days_list, start=1):
        venc = base_date + timedelta(days=int(days))
        row = {
            "partner_id": pid,
            "cliente": (pedido or {}).get("razao_social") or (fatura or {}).get("cliente") or "",
            "cnpj": (pedido or {}).get("cnpj") or (fatura or {}).get("cnpj") or "",
            "pedido_id": (pedido or {}).get("id"),
            "pedido_numero": (pedido or {}).get("numero") or "",
            "fatura_id": fid,
            "fatura_numero": (fatura or {}).get("numero") or "",
            "parcela": i,
            "parcelas": n,
            "valor": float(parcels[i - 1]),
            "saldo": float(parcels[i - 1]),
            "vencimento": venc.strftime("%Y-%m-%d"),
            "status": "aberto",
            "payment_terms": terms,
            "usuario": str(usuario or "").strip(),
        }
        tid = cobol_bridge.titulos_ar_incluir(row)
        row["id"] = tid
        created.append(row)
    _save_projection()
    return {"titulos": created, "already": False, "payment_terms": terms, "source": "cobol"}


def list_titulos(partner_id=None, status=None, q=None):
    rows = list(_load().get("titulos") or [])
    if partner_id:
        pid = str(partner_id).strip()
        rows = [t for t in rows if str(t.get("partner_id") or "") == pid]
    if status:
        st = str(status).strip().lower()
        rows = [t for t in rows if str(t.get("status") or "").lower() == st]
    qq = str(q or "").strip().lower()
    if qq:
        rows = [
            t for t in rows
            if qq in str(t.get("id") or "").lower()
            or qq in str(t.get("cliente") or "").lower()
            or qq in str(t.get("fatura_numero") or "").lower()
            or qq in str(t.get("pedido_numero") or "").lower()
        ]
    rows.sort(key=lambda t: (t.get("vencimento") or "", t.get("id") or ""))
    aberto = sum(_money(t.get("saldo")) for t in rows if t.get("status") == "aberto")
    return {
        "total": len(rows),
        "saldo_aberto": float(aberto),
        "titulos": rows,
    }


def baixar_titulo(titulo_id, valor=None, usuario=""):
    try:
        row = cobol_bridge.titulos_ar_baixar(
            titulo_id,
            valor=float(valor) if valor is not None else None,
            usuario=usuario,
        )
        _save_projection()
        return row
    except Exception as e:
        raise ValueError(str(e)) from e


def migrate_json_to_cobol(force=False):
    """
    Importa sales_ar.json → titulos_ar.dat (uma vez).
    Se o .dat já tem registros e force=False, não sobrescreve.
    """
    dat = os.path.join(BASE_DIR, "dados", "titulos_ar.dat")
    if os.path.exists(dat) and os.path.getsize(dat) > 0 and not force:
        return {"migrated": 0, "message": "dat ja existe"}
    if not os.path.exists(DATA_FILE):
        return {"migrated": 0, "message": "sem json"}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("titulos") if isinstance(data, dict) else []
    n = 0
    for t in rows or []:
        if t.get("status") == "cancelado":
            continue
        try:
            cobol_bridge.titulos_ar_incluir({
                "id": t.get("id") or "",
                "partner_id": t.get("partner_id"),
                "cliente": t.get("cliente"),
                "cnpj": t.get("cnpj"),
                "pedido_id": t.get("pedido_id"),
                "pedido_numero": t.get("pedido_numero"),
                "fatura_id": t.get("fatura_id"),
                "fatura_numero": t.get("fatura_numero"),
                "parcela": t.get("parcela") or 1,
                "parcelas": t.get("parcelas") or 1,
                "valor": t.get("valor") or t.get("saldo") or 0,
                "vencimento": t.get("vencimento"),
                "payment_terms": t.get("payment_terms"),
                "usuario": t.get("usuario"),
            })
            # reaplicar status/saldo se parcial/pago
            st = t.get("status") or "aberto"
            if st in ("pago", "parcial") and float(t.get("saldo") or 0) == 0:
                cobol_bridge.titulos_ar_baixar(t.get("id"), usuario="migrate")
            n += 1
        except Exception:
            continue
    _save_projection()
    return {"migrated": n, "message": "ok"}
