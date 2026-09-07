"""
Comissões do PDV — cálculo por venda.

Persistência leve em JSON (legado BECRP) enquanto o módulo RFC-EMPLOYEE
não é integrado ao PostgreSQL. A regra de precedência segue o RFC-005:

    produto específico → categoria → taxa padrão do vendedor → taxa padrão global → 0

Cada item de venda gera uma linha de comissão com a taxa efetiva, origem
da regra e valor. Vendas canceladas/estornadas e itens devolvidos são
ignorados no cálculo (a apuração futura filtrará por status).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, date
from typing import Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RULES_FILE = os.path.join(DATA_DIR, "commission_rules.json")
COMMISSIONS_FILE = os.path.join(BASE_DIR, "dados", "pos_commissions.json")

DEFAULT_EMPTY_RULES = {
    "version": 1,
    "global_rate": 0.0,
    "users": {},
}


def _today() -> str:
    return date.today().isoformat()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return default
    return data


def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_rules() -> dict:
    """Carrega regras de comissão do arquivo JSON."""
    data = _load_json(RULES_FILE, dict(DEFAULT_EMPTY_RULES))
    if "users" not in data:
        data["users"] = {}
    if "global_rate" not in data:
        data["global_rate"] = 0.0
    return data


def save_rules(data: dict) -> None:
    _save_json(RULES_FILE, data)


def load_commissions() -> dict:
    """Carrega comissões já calculadas."""
    data = _load_json(COMMISSIONS_FILE, {"comissoes": []})
    if "comissoes" not in data:
        data["comissoes"] = []
    return data


def save_commissions(data: dict) -> None:
    _save_json(COMMISSIONS_FILE, data)


def _rule_is_active(rule: dict, sale_date: str) -> bool:
    """Verifica vigência de uma regra na data da venda."""
    if rule.get("active") is False:
        return False
    valid_from = rule.get("valid_from") or ""
    valid_until = rule.get("valid_until") or ""
    if valid_from and sale_date < valid_from:
        return False
    if valid_until and sale_date > valid_until:
        return False
    return True


def _normalize_category(category: str) -> str:
    """Normaliza nome de categoria para comparação."""
    return " ".join(str(category or "").lower().split())


def _find_rate_for_item(item: dict, rules: dict, user_id: str) -> tuple[float, str]:
    """
    Resolve a taxa de comissão de um item pela precedência.

    Retorna (rate_percent, source) onde source é:
    'produto', 'categoria', 'padrao' ou 'global'.
    """
    sale_date = item.get("sale_date") or _today()
    product_id = str(item.get("prod_id") or item.get("id") or "").strip()
    category = _normalize_category(item.get("categoria") or item.get("category") or "")

    user_rules = rules.get("users", {}).get(user_id, {})
    if not isinstance(user_rules, dict):
        user_rules = {}

    # 1. Regra por produto específico
    for rule in user_rules.get("rules", []) or []:
        if rule.get("type") != "produto":
            continue
        if not _rule_is_active(rule, sale_date):
            continue
        target = str(rule.get("target") or "").strip()
        if target and str(product_id) == target:
            return float(rule.get("rate_percent") or 0), "produto"

    # 2. Regra por categoria
    for rule in user_rules.get("rules", []) or []:
        if rule.get("type") != "categoria":
            continue
        if not _rule_is_active(rule, sale_date):
            continue
        target = _normalize_category(rule.get("target") or "")
        if target and category == target:
            return float(rule.get("rate_percent") or 0), "categoria"

    # 3. Taxa padrão do vendedor
    default_rate = user_rules.get("default_rate")
    if default_rate is not None:
        return float(default_rate), "padrao"

    # 4. Taxa padrão global
    global_rate = float(rules.get("global_rate") or 0)
    if global_rate > 0:
        return global_rate, "global"

    return 0.0, "padrao"


def calculate_sale_commission(
    venda: dict,
    pedido: dict,
    user_id: str,
    rules: dict | None = None,
) -> dict:
    """
    Calcula comissão para uma venda fechada.

    Recebe o dicionário da venda (`venda`), o pedido da fila (`pedido`) e o
    identificador do vendedor (`user_id` — geralmente `pedido["pdvUserId"]`).
    Retorna um dicionário com os detalhes da comissão, sem persistir.
    """
    if rules is None:
        rules = load_rules()

    sale_date = venda.get("data") or _today()
    itens = []
    total_commission = 0.0

    for line in venda.get("itens") or []:
        if not isinstance(line, dict):
            continue
        qtd = float(line.get("qtd") or 0)
        preco = float(line.get("preco") or 0)
        subtotal = round(qtd * preco, 2)
        if subtotal <= 0:
            continue

        enriched_item = dict(line)
        enriched_item["sale_date"] = sale_date
        rate, source = _find_rate_for_item(enriched_item, rules, user_id)
        commission_value = round(subtotal * rate / 100.0, 2)

        itens.append({
            "prod_id": line.get("prod_id") or line.get("id"),
            "produto": line.get("produto") or "Produto",
            "categoria": line.get("categoria") or "",
            "qtd": qtd,
            "preco": preco,
            "subtotal": subtotal,
            "rate_percent": rate,
            "rate_source": source,
            "commission_value": commission_value,
        })
        total_commission = round(total_commission + commission_value, 2)

    return {
        "venda_id": venda.get("id"),
        "pedido_id": pedido.get("id"),
        "sale_date": sale_date,
        "employee_id": user_id,
        "caixa_user_id": pedido.get("caixaUserId") or pedido.get("caixaUser") or "",
        "estabelecimento_id": venda.get("estabelecimento_id") or "",
        "terminal_id": pedido.get("terminal_id") or "",
        "terminal_caixa_id": pedido.get("terminal_caixa_id") or "",
        "forma_pg": venda.get("forma_pg") or "Dinheiro",
        "total_venda": float(venda.get("total") or 0),
        "total_commission": total_commission,
        "status": "aberta",
        "items": itens,
        "created_at": _now(),
    }


def record_commission(commission: dict) -> dict:
    """Persiste uma comissão calculada, evitando duplicidade por venda_id."""
    data = load_commissions()
    comissoes = data.get("comissoes", [])
    venda_id = commission.get("venda_id")
    if venda_id is not None:
        comissoes = [c for c in comissoes if c.get("venda_id") != venda_id]
    comissoes.append(commission)
    data["comissoes"] = comissoes
    save_commissions(data)
    return commission


def get_commission_by_sale(venda_id: Any) -> dict | None:
    """Retorna a comissão de uma venda específica."""
    data = load_commissions()
    for c in data.get("comissoes", []):
        if c.get("venda_id") == venda_id:
            return c
    return None


def list_commissions(employee_id: str | None = None, period: str | None = None) -> list:
    """Lista comissões, opcionalmente filtradas por vendedor e competência (YYYY-MM)."""
    data = load_commissions()
    rows = list(data.get("comissoes", []))
    if employee_id:
        rows = [r for r in rows if r.get("employee_id") == employee_id]
    if period:
        rows = [r for r in rows if str(r.get("sale_date") or "").startswith(period)]
    rows.sort(key=lambda r: r.get("sale_date") or "", reverse=True)
    return rows


def cancel_sale_commission(venda_id: Any) -> dict | None:
    """Marca a comissão de uma venda como cancelada (para estorno/devolução)."""
    data = load_commissions()
    for c in data.get("comissoes", []):
        if c.get("venda_id") == venda_id:
            c["status"] = "cancelada"
            save_commissions(data)
            return c
    return None


def build_report(employee_id: str | None = None, period: str | None = None) -> dict:
    """
    Gera relatório consolidado de comissões.

    Retorna resumo geral, ranking de vendedores, ranking de produtos e lista
    detalhada de comissões por venda.
    """
    rows = list_commissions(employee_id=employee_id, period=period)

    total_commission = 0.0
    total_sales = 0.0
    by_employee = {}
    by_product = {}
    detail = []

    for r in rows:
        if r.get("status") == "cancelada":
            continue
        emp = r.get("employee_id") or "sem_vendedor"
        emp_name = r.get("employee_name") or emp
        sale_total = float(r.get("total_venda") or 0)
        comm_total = float(r.get("total_commission") or 0)
        total_commission = round(total_commission + comm_total, 2)
        total_sales = round(total_sales + sale_total, 2)

        if emp not in by_employee:
            by_employee[emp] = {"employee_id": emp, "employee_name": emp_name, "vendas": 0, "comissao": 0.0}
        by_employee[emp]["vendas"] += 1
        by_employee[emp]["comissao"] = round(by_employee[emp]["comissao"] + comm_total, 2)

        for item in r.get("items") or []:
            pid = item.get("prod_id") or item.get("produto") or "?"
            pname = item.get("produto") or "Produto"
            key = str(pid)
            if key not in by_product:
                by_product[key] = {"prod_id": key, "produto": pname, "qtd": 0.0, "comissao": 0.0}
            by_product[key]["qtd"] = round(by_product[key]["qtd"] + float(item.get("qtd") or 0), 3)
            by_product[key]["comissao"] = round(by_product[key]["comissao"] + float(item.get("commission_value") or 0), 2)

        detail.append({
            "venda_id": r.get("venda_id"),
            "pedido_id": r.get("pedido_id"),
            "sale_date": r.get("sale_date"),
            "employee_id": emp,
            "employee_name": emp_name,
            "total_venda": sale_total,
            "total_commission": comm_total,
            "forma_pg": r.get("forma_pg") or "Dinheiro",
            "items": r.get("items") or [],
        })

    return {
        "period": period or "todos",
        "count": len(detail),
        "total_vendas": total_sales,
        "total_commission": total_commission,
        "por_vendedor": sorted(by_employee.values(), key=lambda x: x["comissao"], reverse=True),
        "por_produto": sorted(by_product.values(), key=lambda x: x["comissao"], reverse=True),
        "detalhes": detail,
    }
