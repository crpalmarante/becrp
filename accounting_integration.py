"""
Integração contábil (RFC-8008 MVP).

Domínios operacionais publicam eventos; Accounting Core gera lançamentos
via Posting Engine. Operação não quebra se a contabilidade falhar.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime

import journal_entries
import posting_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "dados", "accounting_integration.json")
LOG_FILE = os.path.join(BASE_DIR, "dados", "accounting_integration_log.json")

DEFAULT_CONFIG = {
    "enabled": True,
    "domains": {
        "pos_sale": True,
        "receiving": True,
        "inventory_adjust": True,
        "fatura_venda": True,
        "devolucao": True,
        # RFC-014: encargos da folha geram lançamentos no fechamento
        "folha": True,
    },
    "atualizado_em": None,
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = dict(DEFAULT_CONFIG)
        cfg["domains"] = dict(DEFAULT_CONFIG["domains"])
        _save_config(cfg)
        return cfg
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        data = dict(DEFAULT_CONFIG)
    data.setdefault("enabled", True)
    domains = data.get("domains") if isinstance(data.get("domains"), dict) else {}
    merged = dict(DEFAULT_CONFIG["domains"])
    merged.update({k: bool(v) for k, v in domains.items()})
    data["domains"] = merged
    return data


def _save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE) or ".", exist_ok=True)
    cfg = dict(cfg or {})
    cfg["atualizado_em"] = _now()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_config():
    return _load_config()


def update_config(payload):
    body = payload if isinstance(payload, dict) else {}
    cfg = _load_config()
    if "enabled" in body:
        cfg["enabled"] = bool(body.get("enabled"))
    if isinstance(body.get("domains"), dict):
        for k, v in body["domains"].items():
            cfg["domains"][k] = bool(v)
    _save_config(cfg)
    return cfg


def _load_log():
    if not os.path.exists(LOG_FILE):
        return {"atualizado_em": None, "eventos": []}
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"atualizado_em": None, "eventos": []}
    if not isinstance(data.get("eventos"), list):
        data["eventos"] = []
    return data


def _append_log(event):
    data = _load_log()
    data["eventos"].append(event)
    if len(data["eventos"]) > 500:
        data["eventos"] = data["eventos"][-500:]
    data["atualizado_em"] = _now()
    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return event


def list_log(limit=100):
    rows = list(_load_log().get("eventos") or [])
    rows.reverse()
    try:
        lim = max(1, min(int(limit or 100), 500))
    except (TypeError, ValueError):
        lim = 100
    return {"total": len(_load_log().get("eventos") or []), "eventos": rows[:lim]}


def find_by_origem_ref(ref):
    key = str(ref or "").strip()
    if not key:
        return None
    for r in journal_entries._load_raw().get("lancamentos") or []:
        if str(r.get("origem_ref") or "") == key:
            return r
    return None


def _domain_on(name):
    cfg = _load_config()
    if not cfg.get("enabled", True):
        return False
    return bool((cfg.get("domains") or {}).get(name))


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _map_forma_pg(forma_pg):
    s = str(forma_pg or "").strip().lower()
    if any(x in s for x in ("credi", "prazo", "boleto", "uplic")):
        return "sale_credit"
    if any(x in s for x in ("pix", "cart", "crédito", "credito", "débito", "debito", "banco", "transfer")):
        return "sale_bank"
    return "sale_cash"


def _with_message(ev):
    """Mensagem curta para UI (POS / recebimento)."""
    out = dict(ev or {})
    if out.get("ok") and not out.get("skipped") and out.get("numero"):
        st = out.get("status") or ""
        suf = " (rascunho)" if st == "draft" else ""
        out["message"] = f"Lançamento {out['numero']}{suf}"
    elif out.get("ok") and out.get("skipped"):
        out["message"] = out.get("reason") or "sem lançamento"
    elif not out.get("ok"):
        out["message"] = out.get("error") or out.get("reason") or "falha contábil"
    else:
        out["message"] = ""
    return out


def publish(domain, evento, valor, referencia, historico=None, data=None, actor=None, auto_post=None):
    """
    Publica evento operacional → Posting Engine.
    Idempotente por referencia (origem_ref).
    """
    ref = str(referencia or "").strip()
    base = {
        "id": str(uuid.uuid4()),
        "domain": domain,
        "evento": evento,
        "referencia": ref,
        "valor": float(valor or 0),
        "actor": actor,
        "em": _now(),
    }
    if not _domain_on(domain):
        ev = _with_message({**base, "ok": True, "skipped": True, "reason": "domínio desligado"})
        _append_log(ev)
        return ev

    if ref:
        existing = find_by_origem_ref(ref)
        if existing:
            ev = _with_message(
                {
                    **base,
                    "ok": True,
                    "skipped": True,
                    "reason": "já integrado",
                    "lancamento_id": existing.get("id"),
                    "numero": existing.get("numero"),
                    "status": existing.get("status"),
                }
            )
            _append_log(ev)
            return ev

    try:
        payload = {
            "evento": evento,
            "valor": valor,
            "referencia": ref,
            "historico": historico or f"{domain}:{evento}",
            "data": data or date.today().isoformat(),
        }
        if auto_post is not None:
            payload["auto_post"] = bool(auto_post)
        out = posting_engine.apply_event(payload, actor=actor)
        lanc = out.get("lancamento") or {}
        ev = _with_message(
            {
                **base,
                "ok": True,
                "skipped": False,
                "lancamento_id": lanc.get("id"),
                "numero": lanc.get("numero"),
                "status": lanc.get("status"),
                "regra": (out.get("regra") or {}).get("codigo"),
            }
        )
        _append_log(ev)
        return ev
    except Exception as e:
        ev = _with_message({**base, "ok": False, "skipped": False, "error": str(e)})
        _append_log(ev)
        return ev


def on_commission_payable(titulo, actor=None):
    """Hook: gera lançamento contábil para comissão a pagar (fatura de fornecedor)."""
    titulo = titulo if isinstance(titulo, dict) else {}
    valor = _safe_float(titulo.get("valor") or titulo.get("total_commission"), 0)
    if valor <= 0:
        return _with_message({
            "ok": True, "skipped": True, "reason": "valor zero",
            "domain": "commission_payable",
        })
    data = str(titulo.get("vencimento") or titulo.get("criado_em") or date.today().isoformat())[:10]
    ref = titulo.get("id") or titulo.get("fatura_ap_id") or ""
    historico = f"Comissão a pagar — {titulo.get('fornecedor') or titulo.get('employee_name') or 'vendedor'} (período {titulo.get('periodo') or ''})"
    return publish(
        domain="commission_payable",
        evento="commission_payable",
        valor=valor,
        referencia=ref,
        historico=historico,
        data=data,
        actor=actor,
        auto_post=False,
    )


def on_commission_payable_reversal(titulo, actor=None):
    """Hook: estorno de fatura de comissão (lançamento contábil reverso)."""
    titulo = titulo if isinstance(titulo, dict) else {}
    valor = _safe_float(titulo.get("valor") or titulo.get("total_commission"), 0)
    if valor <= 0:
        return _with_message({
            "ok": True, "skipped": True, "reason": "valor zero",
            "domain": "commission_payable_reversal",
        })
    data = str(titulo.get("cancelado_em") or titulo.get("vencimento") or date.today().isoformat())[:10]
    ref = titulo.get("id") or ""
    historico = f"Estorno de fatura de comissão — {titulo.get('fornecedor') or titulo.get('employee_name') or 'vendedor'} (período {titulo.get('periodo') or ''})"
    return publish(
        domain="commission_payable",
        evento="commission_payable_reversal",
        valor=valor,
        referencia=ref,
        historico=historico,
        data=data,
        actor=actor,
        auto_post=False,
    )


def on_pos_sale(venda, forma_pg=None, actor=None):
    """Hook: venda POS finalizada."""
    venda = venda if isinstance(venda, dict) else {}
    vid = venda.get("id")
    total = _safe_float(venda.get("total"), 0)
    if total <= 0:
        return _with_message(
            {
                "ok": True,
                "skipped": True,
                "reason": "total zero (troca/devolução)",
                "domain": "pos_sale",
            }
        )
    forma = forma_pg or venda.get("forma_pg") or "Dinheiro"
    evento = _map_forma_pg(forma)
    data = str(venda.get("data") or venda.get("createdAt") or date.today().isoformat())[:10]
    return publish(
        domain="pos_sale",
        evento=evento,
        valor=total,
        referencia=f"POS-VENDA-{vid}",
        historico=f"Venda POS #{vid} ({forma})",
        data=data,
        actor=actor,
    )


def on_fatura_venda(fatura, actor=None):
    """
    Hook: fatura de venda emitida → gera lançamento de receita.
    No regime Continental, COGS já foi reconhecido na compra.
    """
    fat = fatura if isinstance(fatura, dict) else {}
    fid = fat.get("id") or fat.get("fatura_id") or ""
    total = _safe_float(fat.get("total") or fat.get("valor_total"), 0)
    if total <= 0:
        return _with_message({
            "ok": True, "skipped": True, "reason": "total zero",
            "domain": "fatura_venda", "referencia": f"FAT-VENDA-{fid}",
        })
    forma = fat.get("forma_pg") or fat.get("payment_method") or "Dinheiro"
    evento = _map_forma_pg(forma)
    data = str(fat.get("data") or fat.get("emissao") or date.today().isoformat())[:10]
    return publish(
        domain="fatura_venda",
        evento=evento,
        valor=total,
        referencia=f"FAT-VENDA-{fid}",
        historico=f"Fatura venda #{fid} — receita",
        data=data,
        actor=actor,
    )


def _receiving_valor(rec):
    total = 0.0
    for it in (rec or {}).get("items") or []:
        if not isinstance(it, dict):
            continue
        q = _safe_float(it.get("qty_verified") or it.get("qty_good") or it.get("qty"), 0)
        if q <= 0:
            continue
        p = _safe_float(
            it.get("unit_price")
            or it.get("preco_unit")
            or it.get("preco")
            or it.get("vuncom")
            or it.get("valor_unitario")
            or it.get("valor_unit"),
            0,
        )
        total += q * p
    # fallback: totais do documento
    if total <= 0:
        total = _safe_float(
            (rec or {}).get("total")
            or (rec or {}).get("valor_total")
            or ((rec or {}).get("nfe") or {}).get("valor_total"),
            0,
        )
    return round(total, 2)


def on_receiving_complete(rec, actor=None):
    """Hook: recebimento concluído → compra (rascunho por padrão da regra)."""
    rec = rec if isinstance(rec, dict) else {}
    rid = rec.get("id")
    valor = _receiving_valor(rec)
    if valor <= 0:
        return _with_message(
            {
                "ok": True,
                "skipped": True,
                "reason": "sem valor monetário nos itens",
                "domain": "receiving",
                "referencia": f"RCV-{rid}",
            }
        )
    data = str(rec.get("completed_at") or rec.get("data") or date.today().isoformat())[:10]
    return publish(
        domain="receiving",
        evento="purchase",
        valor=valor,
        referencia=f"RCV-{rid}",
        historico=f"Recebimento #{rid}",
        data=data,
        actor=actor,
    )


def on_inventory_adjust(movimento, actor=None):
    """Hook opcional: ajuste de estoque positivo."""
    mov = movimento if isinstance(movimento, dict) else {}
    mid = mov.get("id") or mov.get("movement_id") or ""
    valor = _safe_float(mov.get("valor") or mov.get("amount"), 0)
    qty = _safe_float(mov.get("qty"), 0)
    if valor <= 0 and qty > 0:
        # sem custo: não gera lançamento
        return {
            "ok": True,
            "skipped": True,
            "reason": "ajuste sem valor",
            "domain": "inventory_adjust",
        }
    if valor <= 0:
        return {"ok": True, "skipped": True, "reason": "valor zero", "domain": "inventory_adjust"}
    return publish(
        domain="inventory_adjust",
        evento="inventory_adjust_up",
        valor=valor,
        referencia=f"INV-ADJ-{mid}",
        historico=f"Ajuste estoque {mid}",
        data=str(mov.get("data") or date.today().isoformat())[:10],
        actor=actor,
    )


def on_return_stock(devolucao, actor=None):
    """
    Hook: retorno físico de devolução → D:Estoque / C:COGS (regime Continental).
    O custo unitário original deve ser informado em 'custo_unit'.
    """
    dev = devolucao if isinstance(devolucao, dict) else {}
    did = dev.get("id") or dev.get("devolucao_id") or ""
    qty = _safe_float(dev.get("qty") or dev.get("quantidade"), 0)
    custo_unit = _safe_float(dev.get("custo_unit") or dev.get("custo_unitario") or dev.get("cost"), 0)
    valor = qty * custo_unit
    if valor <= 0:
        return _with_message({
            "ok": True, "skipped": True, "reason": "qty ou custo zero",
            "domain": "devolucao", "referencia": f"DEV-STOCK-{did}",
        })
    data = str(dev.get("data") or date.today().isoformat())[:10]
    return publish(
        domain="devolucao",
        evento="return_stock",
        valor=valor,
        referencia=f"DEV-STOCK-{did}",
        historico=f"Devolução #{did} — retorno estoque ({qty} un × ${custo_unit})",
        data=data,
        actor=actor,
    )


def on_return_revenue(devolucao, actor=None):
    """
    Hook: nota de crédito (reversão receita) → D:Receita / C:Clientes.
    """
    dev = devolucao if isinstance(devolucao, dict) else {}
    did = dev.get("id") or dev.get("devolucao_id") or ""
    valor = _safe_float(dev.get("valor") or dev.get("total"), 0)
    if valor <= 0:
        return _with_message({
            "ok": True, "skipped": True, "reason": "valor zero",
            "domain": "devolucao", "referencia": f"DEV-REC-{did}",
        })
    data = str(dev.get("data") or date.today().isoformat())[:10]
    cliente = dev.get("cliente") or dev.get("partner_id") or ""
    hist = f"Devolução #{did} — nota de crédito"
    if cliente:
        hist += f" ({cliente})"
    return publish(
        domain="devolucao",
        evento="return_revenue",
        valor=valor,
        referencia=f"DEV-REC-{did}",
        historico=hist,
        data=data,
        actor=actor,
    )


def status():
    cfg = _load_config()
    log = list_log(limit=5)
    return {
        "config": cfg,
        "regras_disponiveis": [r.get("evento") for r in posting_engine.list_rules(ativos=True).get("regras") or []],
        "ultimos": log.get("eventos") or [],
        "principio": "domínios operacionais publicam eventos; Accounting Core gera a verdade contábil",
    }
