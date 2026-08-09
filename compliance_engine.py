"""
Compliance Engine (RFC-0060) — Sprint CP-01: fechamento (reconciliação).

O Compliance Engine nunca calcula tributos, nunca posta lançamentos e nunca
emite documentos. Ele consome os totais dos demais motores através de
Providers (interfaces) e reconcilia: apuração (Tax) × escrituração
(Accounting) × caixa (Finance).

Saída: ComplianceReport com status valido/divergente + eventos
fechamento_valido / fechamento_divergente (RFC-0060, seção 12).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

import accounting_periods
import journal_entries
import ledger
import org_store
import planocontas
from modules.sefaz import tributos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "dados")
FECHAMENTOS_FILE = os.path.join(DATA_DIR, "compliance_fechamentos.json")
VENDAS_FILE = os.path.join(DATA_DIR, "vendas.json")
NFE_ENTRADA_FILE = os.path.join(DATA_DIR, "nfe_entrada.json")

MONEY = Decimal("0.01")
TOLERANCIA = Decimal("0.02")

# Contas de recolhimento por tributo — espelham dados/accounting_mapping.json.
TAX_ACCOUNTS = {
    "icms": "2.01.01.09.03",
    "pis": "2.01.01.09.04",
    "cofins": "2.01.01.09.05",
    "ipi": "2.01.01.09.02",
}

# Contas de crédito de entrada (débito em tributos a recuperar).
TAX_RECUPERAR_ACCOUNTS = {
    "icms": "1.01.02.03.02",
    "pis": "1.01.02.03.03",
    "cofins": "1.01.02.03.05",
}

CONTAS_CAIXA_BANCO = ("1.01.01.01.01", "1.01.01.02")

CONTA_RECEITA = "3.01.01.01.01.05"
CONTA_CMV = "3.01.01.03.01.02"
CONTA_ESTOQUE = "1.01.03.01.01"

# ── Infra ──


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _money(val):
    try:
        d = Decimal(str(val if val is not None else "0"))
    except Exception:
        return Decimal("0")
    return d.quantize(MONEY, rounding=ROUND_HALF_UP)


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _load_raw(path, empty):
    if not os.path.exists(path):
        return empty
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else empty


def _save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_fechamentos():
    data = _load_raw(FECHAMENTOS_FILE, {"atualizado_em": None, "fechamentos": []})
    if not isinstance(data.get("fechamentos"), list):
        data["fechamentos"] = []
    return data


def _append_fechamento(fechamento):
    data = _load_fechamentos()
    data["fechamentos"].append(fechamento)
    if len(data["fechamentos"]) > 500:
        data["fechamentos"] = data["fechamentos"][-500:]
    data["atualizado_em"] = _now()
    _save_json(FECHAMENTOS_FILE, data)
    return fechamento


# ── Interfaces (Ports) — implementações padrão (adapters do repo) ──


def tax_apuracao_periodo(ano, mes):
    """Tax Result Provider: apuração de ICMS/PIS/COFINS do período.

    Débitos (vendas) − créditos (entradas/compras) = saldo a recolher.
    Consome o embrião do Tax Engine (modules/sefaz/tributos) da mesma forma
    que o Accounting provisionou — apurado deve bater com o provisionado.
    """
    de, ate = _range_periodo(ano, mes)
    vendas = _vendas_do_periodo(de, ate)
    deb = {"icms": Decimal("0"), "pis": Decimal("0"), "cofins": Decimal("0")}
    base = Decimal("0")
    for venda in vendas:
        empresa = _empresa(venda)
        uf = str(empresa.get("uf") or "").strip().upper()
        if len(uf) != 2:
            uf = "RS"
        crt = _crt(empresa)
        regime = "normal" if crt == 3 else "SN"
        regime_pis = "nao_cumulativo" if crt == 3 else "cumulativo"
        for it in venda.get("itens") or []:
            if not isinstance(it, dict):
                continue
            subtotal = _safe_float(it.get("subtotal"), 0)
            if subtotal <= 0:
                continue
            base += _money(subtotal)
            r_icms = tributos.calcular_icms(subtotal, uf, uf, regime)
            r_pc = tributos.calcular_pis_cofins(subtotal, regime_pis)
            deb["icms"] += _money(r_icms.get("vICMS"))
            deb["pis"] += _money(r_pc.get("vPIS"))
            deb["cofins"] += _money(r_pc.get("vCOFINS"))

    cred = {"icms": Decimal("0"), "pis": Decimal("0"), "cofins": Decimal("0")}
    entradas = _entradas_do_periodo(de, ate)
    for e in entradas:
        tot = (e.get("total") or {}) if isinstance(e, dict) else {}
        for nome, key in (("icms", "vICMS"), ("pis", "vPIS"), ("cofins", "vCOFINS")):
            v = _safe_float(tot.get(key), 0)
            if v > 0:
                cred[nome] += _money(v)

    def _q(d):
        return float(d.quantize(MONEY, rounding=ROUND_HALF_UP))

    saldo = {n: _q(deb[n] - cred[n]) for n in ("icms", "pis", "cofins")}
    return {
        "vendas": len(vendas),
        "entradas": len(entradas),
        "base": _q(base),
        "debitos": {n: _q(deb[n]) for n in ("icms", "pis", "cofins")},
        "creditos": {n: _q(cred[n]) for n in ("icms", "pis", "cofins")},
        "saldo_a_recolher": saldo,
        "icms": saldo["icms"],
        "pis": saldo["pis"],
        "cofins": saldo["cofins"],
    }


def accounting_totais_periodo(ano, mes):
    """Accounting Books Provider: saldos provisionados no período (só postados)."""
    de, ate = _range_periodo(ano, mes)
    out = {}
    # crédito nas contas de recolhimento = imposto provisionado
    for nome, conta in TAX_ACCOUNTS.items():
        out[nome] = _movimentacao_conta(conta, de, ate).get("credito", 0.0)
    # débito nas contas de recuperação = crédito de entrada provisionado
    for nome, conta in TAX_RECUPERAR_ACCOUNTS.items():
        out[f"{nome}_recuperar"] = _movimentacao_conta(conta, de, ate).get("debito", 0.0)
    out["receita"] = _movimentacao_conta(CONTA_RECEITA, de, ate).get("credito", 0.0)
    out["cmv"] = _movimentacao_conta(CONTA_CMV, de, ate).get("debito", 0.0)
    out["estoque_baixa"] = _movimentacao_conta(CONTA_ESTOQUE, de, ate).get("credito", 0.0)
    # saldo a recolher provisionado = recolher − recuperar
    out["saldo_a_recolher"] = {
        nome: round(
            _safe_float(out.get(nome), 0) - _safe_float(out.get(f"{nome}_recuperar"), 0),
            2,
        )
        for nome in ("icms", "pis", "cofins")
    }
    # débito em caixa/banco = recebimentos do período
    receb = Decimal("0")
    for conta in _listar_contas_caixa_banco():
        receb += _money(_movimentacao_conta(conta, de, ate).get("debito"))
    out["recebimentos"] = float(receb.quantize(MONEY, rounding=ROUND_HALF_UP))
    return out


def finance_recebimentos_periodo(ano, mes):
    """Finance Balances Provider: recebimentos (débitos em caixa/bancos)."""
    return accounting_totais_periodo(ano, mes).get("recebimentos", 0.0)


# ── Core: fechamento (reconciliação) ──


def fechamento(ano, mes):
    """
    Reconcilia o período: apuração (Tax) × provisionado (Accounting) × caixa (Finance).

    Critério de aceite (RFC-0100 §8 / RFC-0060 §13):
    EFD (apuração) == ECD/ECF (escrituração) == Caixa (Finance).
    """
    ano = int(ano)
    mes = int(mes)
    de, ate = _range_periodo(ano, mes)

    apurado = tax_apuracao_periodo(ano, mes)
    contabil = accounting_totais_periodo(ano, mes)
    finance = finance_recebimentos_periodo(ano, mes)

    checks = []
    # 1) saldo a recolher (débito − crédito apurado) × provisionado (recolher − recuperar)
    for nome in ("icms", "pis", "cofins"):
        a = _money(apurado.get("saldo_a_recolher", {}).get(nome))
        p = _money(contabil.get("saldo_a_recolher", {}).get(nome))
        checks.append(
            _check(f"{nome} saldo a recolher (apurado × provisionado)", a, p, "Tax × Accounting")
        )
    # 2) receita bruta (base) = receita líquida + impostos a recolher
    receita_bruta = _money(apurado.get("base"))
    receita_liquida = _money(contabil.get("receita"))
    impostos_total = sum(
        (_money(contabil.get(n)) for n in ("icms", "pis", "cofins")), Decimal("0")
    )
    checks.append(
        _check("receita bruta = receita líquida + impostos", receita_bruta, receita_liquida + impostos_total, "Tax × Accounting")
    )
    # 3) caixa (Finance) × escrituração: recebimentos = receita bruta
    checks.append(
        _check("caixa/bancos (recebimentos) × receita bruta", _money(finance), receita_bruta, "Finance × Tax")
    )
    # 4) CMV interno: débito CMV × crédito estoque
    checks.append(
        _check("CMV (débito) × baixa de estoque (crédito)", _money(contabil.get("cmv")), _money(contabil.get("estoque_baixa")), "Accounting (interno)")
    )

    divergencias = [c for c in checks if not c["ok"]]
    valido = len(divergencias) == 0

    relatorio = {
        "tipo": "fechamento",
        "titulo": "Fechamento do período (reconciliação)",
        "periodo": {"ano": ano, "mes": mes, "label": f"{ano}-{mes:02d}"},
        "filtros": {"data_de": de, "data_ate": ate},
        "apurado_fiscal": apurado,
        "provisionado_contabil": contabil,
        "caixa_finance": finance,
        "checagens": checks,
        "divergencias": divergencias,
        "total_checagens": len(checks),
        "total_divergencias": len(divergencias),
        "status": "valido" if valido else "divergente",
        "evento": "fechamento_valido" if valido else "fechamento_divergente",
        "em": _now(),
    }

    _append_fechamento(
        {
            "id": str(uuid.uuid4()),
            "evento": relatorio["evento"],
            "periodo": relatorio["periodo"],
            "status": relatorio["status"],
            "divergencias": [
                {"check": c["check"], "apurado": float(c["apurado"]), "provisionado": float(c["provisionado"]), "origem": c["origem"]}
                for c in divergencias
            ],
            "em": _now(),
        }
    )
    return relatorio


def list_fechamentos(limit=100):
    rows = list(_load_fechamentos().get("fechamentos") or [])
    rows.reverse()
    try:
        lim = max(1, min(int(limit or 100), 500))
    except (TypeError, ValueError):
        lim = 100
    return {"total": len(_load_fechamentos().get("fechamentos") or []), "fechamentos": rows[:lim]}


def status():
    return {
        "principio": "Compliance Engine nunca calcula, posta ou emite; reconcilia totais dos motores via Providers",
        "interface": "Providers: tax_apuracao_periodo, accounting_totais_periodo, finance_recebimentos_periodo",
        "critério_de_aceite": "EFD (apuração) == ECD/ECF (escrituração) == Caixa (Finance)",
        "ultimos_fechamentos": list_fechamentos(limit=5).get("fechamentos") or [],
    }


# ── Helpers (adapters) ──


def _range_periodo(ano, mes):
    from calendar import monthrange
    ultimo = monthrange(ano, mes)[1]
    return f"{ano}-{mes:02d}-01", f"{ano}-{mes:02d}-{ultimo:02d}"


def _vendas_do_periodo(de, ate):
    data = _load_raw(VENDAS_FILE, {"vendas": []})
    vendas = data.get("vendas") if isinstance(data.get("vendas"), list) else []
    out = []
    for v in vendas:
        if not isinstance(v, dict):
            continue
        d = str(v.get("data") or "")[:10]
        if d and de <= d <= ate:
            out.append(v)
    return out


def _entradas_do_periodo(de, ate):
    """NF-e de entrada (compras) do período — fonte dos créditos fiscais."""
    data = _load_raw(NFE_ENTRADA_FILE, {"nfe_entradas": []})
    entradas = data.get("nfe_entradas") if isinstance(data.get("nfe_entradas"), list) else []
    out = []
    for e in entradas:
        if not isinstance(e, dict):
            continue
        d = str(e.get("data_emissao") or "")[:10]
        if d and de <= d <= ate:
            out.append(e)
    return out


def _empresa(venda):
    try:
        return org_store.resolve_empresa_fiscal(venda.get("estabelecimento_id")) or {}
    except Exception:
        return {}


def _crt(empresa):
    try:
        return int(empresa.get("crt") or 1)
    except (TypeError, ValueError):
        return 1


def _movimentacao_conta(conta, de, ate):
    try:
        rz = ledger.razao(conta, data_de=de, data_ate=ate)
        return rz.get("periodo") or {"debito": 0.0, "credito": 0.0, "saldo": 0.0}
    except ValueError:
        return {"debito": 0.0, "credito": 0.0, "saldo": 0.0}


def _listar_contas_caixa_banco():
    contas = []
    for conta in (planocontas.list_contas(q=None, analiticas=True).get("contas") or []):
        classif = str(conta.get("classificacao") or conta.get("codigo") or "")
        if classif.startswith(CONTAS_CAIXA_BANCO) or classif == "1.01.01.01.01":
            contas.append(classif)
    if not contas:
        contas = ["1.01.01.01.01", "1.01.01.02.01"]
    return contas


def _check(nome, apurado, provisionado, origem):
    a = _money(apurado)
    p = _money(provisionado)
    dif = (a - p).quantize(MONEY, rounding=ROUND_HALF_UP)
    ok = abs(dif) <= TOLERANCIA
    return {
        "check": nome,
        "apurado": float(a),
        "provisionado": float(p),
        "diferenca": float(dif),
        "origem": origem,
        "ok": ok,
    }
