"""
Acordos de Compra (Purchase Agreements / Call for Tender).

Fonte COBOL:
  dados/acordos_compra.dat
  dados/itens_acordo_compra.dat

Cotações de fornecedores (propostas) ficam em JSON:
  dados/cotacoes_acordo_compra.json

Fluxo: acordo rascunho → em cotação → fechado → pedido de compra.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import cobol_bridge
import compras_store
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "dados", "acordos_compra.json")
COTACOES_FILE = os.path.join(BASE_DIR, "dados", "cotacoes_acordo_compra.json")
BLANKET_FILE = os.path.join(BASE_DIR, "dados", "blanket_saldos.json")

TIPOS = ("tender", "blanket")
STATUSES = ("rascunho", "em_cotacao", "fechado", "cancelado")
FLOW = {
    "rascunho": {"em_cotacao", "fechado", "cancelado"},
    "em_cotacao": {"fechado", "cancelado"},
    "fechado": set(),
    "cancelado": set(),
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _clip(val, n):
    s = str(val if val is not None else "")
    s = s.replace('"', "'").replace("\n", " ").replace("\r", " ")
    return s[:n]


def _parse_json_blob(out, key):
    text = (out or "").replace("\x00", "")
    marker = '{"' + key + '":'
    start = text.find(marker)
    if start < 0:
        return []
    try:
        data = json.loads(text[start:])
        return data.get(key) or []
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip().rstrip(",")
            if line.startswith("{") and ('"id"' in line or '"acordo_id"' in line):
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return rows


def _load_cotacoes():
    if not os.path.exists(COTACOES_FILE):
        return {"next_id": 1, "cotacoes": []}
    with open(COTACOES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"next_id": 1, "cotacoes": []}
    data.setdefault("cotacoes", [])
    data.setdefault("next_id", 1)
    return data


def _save_cotacoes(data):
    os.makedirs(os.path.dirname(COTACOES_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("cotacoes") or [])
    jsonio.save(COTACOES_FILE, data)


def _normalize_acordo(h):
    if not isinstance(h, dict):
        return {}
    out = dict(h)
    try:
        out["id"] = int(out.get("id") or 0)
    except (TypeError, ValueError):
        out["id"] = out.get("id")
    st = str(out.get("status") or "rascunho").lower()
    if st not in STATUSES:
        st = "rascunho"
    out["status"] = st
    tipo = str(out.get("tipo") or "tender").lower()
    if tipo not in TIPOS:
        tipo = "tender"
    out["tipo"] = tipo
    if out.get("payment_terms") and not out.get("condicao_pg"):
        out["condicao_pg"] = out["payment_terms"]
    return out


def _normalize_item(it):
    return {
        "acordo_id": it.get("acordo_id") or 0,
        "seq": it.get("seq") or 0,
        "prod_id": it.get("prod_id") or "",
        "produto": it.get("produto") or "",
        "qtd": float(it.get("qtd") or 0),
        "uom": it.get("uom") or "UN",
        "descricao": it.get("descricao") or "",
    }


def listar_cabecalhos():
    out, _ = cobol_bridge._run("gerir_acordos_compra", {"ACAO": "listar"})
    return [_normalize_acordo(h) for h in _parse_json_blob(out, "acordos")]


def listar_itens(acordo_id=None):
    if acordo_id is None:
        out, _ = cobol_bridge._run("gerir_itens_acordo_compra", {"ACAO": "listar"})
    else:
        out, _ = cobol_bridge._run(
            "gerir_itens_acordo_compra",
            {"ACAO": "listar-ac", "ACORDO_ID": str(acordo_id)},
        )
    return [_normalize_item(i) for i in _parse_json_blob(out, "itens")]


def listar():
    headers = listar_cabecalhos()
    out, _ = cobol_bridge._run("gerir_itens_acordo_compra", {"ACAO": "listar"})
    raw_items = _parse_json_blob(out, "itens")
    by_aid = {}
    for it in raw_items:
        aid = str(it.get("acordo_id") or "")
        by_aid.setdefault(aid, []).append(_normalize_item(it))
    rows = []
    for h in headers:
        a = dict(h)
        a["itens"] = by_aid.get(str(a.get("id")), [])
        a["cotacoes"] = listar_cotacoes(a.get("id"))
        a["blanket"] = blanket_saldo(a.get("id"))
        rows.append(a)
    rows.sort(key=lambda x: int(x.get("id") or 0), reverse=True)
    return rows


def get(acordo_id):
    out, _ = cobol_bridge._run(
        "gerir_acordos_compra", {"ACAO": "buscar", "ID": str(acordo_id)}
    )
    text = (out or "").strip()
    if '"status":"erro"' in text.replace(" ", ""):
        return None
    start = text.find('{"id":')
    if start < 0:
        return None
    line = text[start:].splitlines()[0].strip()
    try:
        a = _normalize_acordo(json.loads(line))
    except json.JSONDecodeError:
        return None
    a["itens"] = listar_itens(acordo_id)
    a["cotacoes"] = listar_cotacoes(acordo_id)
    a["blanket"] = blanket_saldo(acordo_id)
    if a.get("status") == "fechado" and a.get("cotacoes"):
        vencedora = next((c for c in a["cotacoes"] if c.get("vencedora")), None)
        if not vencedora:
            vencedora = min(a["cotacoes"], key=lambda c: float(c.get("valor_total") or 0))
        a["vencedor"] = {
            "cotacao_id": vencedora.get("id"),
            "fornecedor": vencedora.get("fornecedor"),
            "valor_total": vencedora.get("valor_total"),
        }
    return a


def _replace_itens(acordo_id, itens):
    cobol_bridge._run(
        "gerir_itens_acordo_compra",
        {"ACAO": "limpar", "ACORDO_ID": str(acordo_id)},
    )
    for i, it in enumerate(itens or [], start=1):
        cobol_bridge._run(
            "gerir_itens_acordo_compra",
            {
                "ACAO": "incluir",
                "ACORDO_ID": str(acordo_id),
                "SEQ": str(i),
                "PROD_ID": _clip(it.get("prod_id"), 10),
                "PRODUTO": _clip(it.get("produto"), 40),
                "UOM": _clip(it.get("uom") or "UN", 4),
                "QTD": str(it.get("qtd") or 0),
            },
        )


def _header_env(a, *, with_id=True):
    env = {
        "NUMERO": _clip(a.get("numero"), 12),
        "TIPO": _clip(a.get("tipo") or "tender", 12),
        "STATUS": _clip(a.get("status") or "rascunho", 12),
        "DATA": _clip(a.get("data"), 10),
        "FECHAMENTO": _clip(a.get("fechamento"), 10),
        "DESCRICAO": _clip(a.get("descricao") or a.get("titulo"), 60),
        "COMPRADOR": _clip(a.get("comprador"), 30),
        "TERMS": _clip(a.get("payment_terms") or a.get("condicao_pg"), 20),
        "FORMA_PG": _clip(a.get("forma_pg"), 20),
        "TOTAL": str(a.get("total") or 0),
        "PEDIDO_ID": _clip(a.get("pedido_id"), 10),
        "PEDIDO_NUM": _clip(a.get("pedido_num"), 12),
        "NOTAS": _clip(a.get("notas"), 80),
    }
    if with_id and a.get("id") is not None:
        env["ID"] = str(a.get("id"))
    return env


def save(acordo, *, is_new=False):
    a = _normalize_acordo(dict(acordo or {}))
    if is_new or a.get("id") is None:
        out, _ = cobol_bridge._run(
            "gerir_acordos_compra", {"ACAO": "proximo-id"}
        )
        try:
            new_id = int((out or "").splitlines()[0].strip())
        except (ValueError, IndexError):
            new_id = 1
        a["id"] = new_id
        if not a.get("numero"):
            prefix = "CT" if (a.get("tipo") or "").lower() == "tender" else "AC"
            a["numero"] = f"{prefix}{new_id:05d}"
    itens = a.get("itens") or []
    a.setdefault("total", 0)
    env = _header_env(a)
    env["ACAO"] = "incluir" if is_new or acordo.get("id") is None else "alterar"
    out, _ = cobol_bridge._run("gerir_acordos_compra", env)
    if "ERRO" in (out or ""):
        raise Exception(out.strip())
    _replace_itens(a["id"], itens)
    updated = get(a["id"])
    sync_json()
    return updated


def delete(acordo_id):
    out, _ = cobol_bridge._run(
        "gerir_acordos_compra", {"ACAO": "excluir", "ID": str(acordo_id)}
    )
    if "ERRO" in (out or ""):
        raise Exception(out.strip())
    sync_json()
    return True


def set_status(acordo_id, novo_status, *, usuario=""):
    st = str(novo_status or "").lower()
    if st not in STATUSES:
        raise ValueError(f"status inválido: {novo_status}")
    cur = get(acordo_id)
    if not cur:
        raise ValueError("acordo não encontrado")
    atual = cur.get("status") or "rascunho"
    if st == atual:
        return cur
    if st not in FLOW.get(atual, set()):
        raise ValueError(f"transição inválida: {atual} → {st}")
    if st == "em_cotacao":
        if not cur.get("itens"):
            raise ValueError("acordo sem itens — não abre cotação")
    if st == "fechado":
        if cur.get("tipo") != "blanket" and not cur.get("cotacoes"):
            raise ValueError("nenhuma cotação recebida — não fecha")
        # marca melhor cotação (somente se houver cotações)
        if cur.get("cotacoes"):
            melhor = min(
                cur["cotacoes"],
                key=lambda c: float(c.get("valor_total") or 0),
            )
            cur["vencedor"] = {
                "cotacao_id": melhor.get("id"),
                "fornecedor": melhor.get("fornecedor"),
                "valor_total": melhor.get("valor_total"),
            }
            # salva marca no JSON de cotações
            data = _load_cotacoes()
            for c in data.get("cotacoes") or []:
                if c.get("acordo_id") == acordo_id:
                    c["vencedora"] = c.get("id") == melhor.get("id")
            _save_cotacoes(data)
    if st == "fechado" and not cur.get("fechamento"):
        cur["fechamento"] = _today()
    env = _header_env(cur, with_id=True)
    env["STATUS"] = st
    env["FECHAMENTO"] = cur.get("fechamento") or ""
    env["ACAO"] = "alterar"
    out, _ = cobol_bridge._run("gerir_acordos_compra", env)
    if "ERRO" in (out or ""):
        raise Exception(out.strip())
    updated = get(acordo_id)
    sync_json()
    return updated


# ── Cotações de fornecedores (JSON) ─────────────────────────────

def listar_cotacoes(acordo_id=None):
    data = _load_cotacoes()
    rows = list(data.get("cotacoes") or [])
    if acordo_id is not None:
        aid = str(acordo_id)
        rows = [c for c in rows if str(c.get("acordo_id")) == aid]
    rows.sort(key=lambda c: c.get("id") or 0, reverse=True)
    return rows


def get_cotacao(cotacao_id):
    data = _load_cotacoes()
    for c in data.get("cotacoes") or []:
        if str(c.get("id")) == str(cotacao_id):
            return c
    return None


def add_cotacao(acordo_id, cotacao, *, usuario=""):
    cur = get(acordo_id)
    if not cur:
        raise ValueError("acordo não encontrado")
    if cur.get("status") not in ("rascunho", "em_cotacao"):
        raise ValueError("só adiciona cotação em acordo rascunho ou em cotação")
    data = _load_cotacoes()
    nid = int(data.get("next_id") or 1)
    itens = []
    for it in cotacao.get("itens") or []:
        itens.append({
            "prod_id": it.get("prod_id") or "",
            "produto": it.get("produto") or "",
            "qtd": float(it.get("qtd") or 0),
            "preco": float(it.get("preco") or 0),
            "subtotal": float(it.get("subtotal") or 0),
        })
    total = sum(i["subtotal"] for i in itens)
    row = {
        "id": nid,
        "acordo_id": int(acordo_id),
        "fornecedor_id": str(cotacao.get("fornecedor_id") or ""),
        "fornecedor": str(cotacao.get("fornecedor") or cotacao.get("razao_social") or ""),
        "cnpj": "".join(c for c in str(cotacao.get("cnpj") or "") if c.isdigit()),
        "prazo": str(cotacao.get("prazo") or ""),
        "payment_terms": str(cotacao.get("payment_terms") or "30"),
        "forma_pg": str(cotacao.get("forma_pg") or "Boleto"),
        "frete": float(cotacao.get("frete") or 0),
        "valor_total": total + float(cotacao.get("frete") or 0),
        "itens": itens,
        "vencedora": False,
        "criado_em": _now(),
        "criado_por": usuario,
    }
    data["cotacoes"].insert(0, row)
    data["next_id"] = nid + 1
    _save_cotacoes(data)
    # se acordo estava rascunho, abre cotação automaticamente
    if cur.get("status") == "rascunho":
        set_status(acordo_id, "em_cotacao", usuario=usuario)
    sync_json()
    return row


def delete_cotacao(cotacao_id):
    data = _load_cotacoes()
    data["cotacoes"] = [c for c in data.get("cotacoes") or [] if str(c.get("id")) != str(cotacao_id)]
    _save_cotacoes(data)
    sync_json()
    return True


def converter_vencedor(acordo_id, *, usuario=""):
    """Converte a cotação vencedora em pedido de compra."""
    cur = get(acordo_id)
    if not cur:
        raise ValueError("acordo não encontrado")
    if cur.get("status") != "fechado":
        raise ValueError("acordo precisa estar fechado")
    venc = cur.get("vencedor")
    if not venc:
        raise ValueError("sem cotação vencedora")
    cot = None
    for c in cur.get("cotacoes") or []:
        if str(c.get("id")) == str(venc.get("cotacao_id")):
            cot = c
            break
    if not cot:
        raise ValueError("cotação vencedora não encontrada")
    pedido = {
        "tipo": "pedido",
        "status": "rascunho",
        "data": _today(),
        "razao_social": cot.get("fornecedor") or cur.get("descricao") or "",
        "cnpj": cot.get("cnpj") or "",
        "comprador": cur.get("comprador") or usuario,
        "payment_terms": cot.get("payment_terms") or "30",
        "forma_pg": cot.get("forma_pg") or "Boleto",
        "notas": f"Gerado do acordo {cur.get('numero')} (vencedor: {cot.get('fornecedor')})",
        "itens": [
            {
                "prod_id": it.get("prod_id"),
                "produto": it.get("produto"),
                "qtd": it.get("qtd"),
                "uom": it.get("uom") or "UN",
                "preco": it.get("preco"),
                "desconto": 0,
                "subtotal": it.get("subtotal"),
            }
            for it in cot.get("itens") or []
        ],
        "acordo_id": cur.get("id"),
        "acordo_numero": cur.get("numero"),
    }
    saved = compras_store.save(pedido, is_new=True)
    # atualiza acordo com pedido gerado
    env = _header_env(cur, with_id=True)
    env["PEDIDO_ID"] = str(saved.get("id") or "")
    env["PEDIDO_NUM"] = str(saved.get("numero") or "")
    env["ACAO"] = "alterar"
    cobol_bridge._run("gerir_acordos_compra", env)
    sync_json()
    return {"acordo": get(acordo_id), "pedido": saved}


# ── Blanket / Compras recorrentes ─────────────────────────────

def _load_blanket():
    if not os.path.exists(BLANKET_FILE):
        return {"saldos": {}}
    with open(BLANKET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"saldos": {}}
    data.setdefault("saldos", {})
    return data


def _save_blanket(data):
    os.makedirs(os.path.dirname(BLANKET_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    jsonio.save(BLANKET_FILE, data)


def blanket_saldo(acordo_id):
    data = _load_blanket()
    return data.get("saldos", {}).get(str(acordo_id), {})


def blanket_setup(acordo_id, *, valor_total=None, qtd_total=None, usuario=""):
    cur = get(acordo_id)
    if not cur:
        raise ValueError("acordo não encontrado")
    if cur.get("tipo") != "blanket":
        raise ValueError("só acordo do tipo blanket tem saldo")
    data = _load_blanket()
    sid = str(acordo_id)
    s = data["saldos"].get(sid, {})
    s.setdefault("liberacoes", [])
    if valor_total is not None:
        s["valor_total"] = float(valor_total)
        s["saldo_valor"] = float(valor_total) - sum(l.get("valor") or 0 for l in s.get("liberacoes", []))
    if qtd_total is not None:
        s["qtd_total"] = float(qtd_total)
        s["saldo_qtd"] = float(qtd_total) - sum(l.get("qtd") or 0 for l in s.get("liberacoes", []))
    s["atualizado_por"] = usuario
    s["atualizado_em"] = _now()
    data["saldos"][sid] = s
    _save_blanket(data)
    return s


def liberar_blanket(acordo_id, payload, *, usuario=""):
    cur = get(acordo_id)
    if not cur:
        raise ValueError("acordo não encontrado")
    if cur.get("tipo") != "blanket":
        raise ValueError("só acordo do tipo blanket pode ser liberado")
    if cur.get("status") != "fechado":
        raise ValueError("blanket precisa estar fechado")

    data = _load_blanket()
    sid = str(acordo_id)
    s = data["saldos"].get(sid, {})
    if not s:
        raise ValueError("blanket sem saldo configurado")

    valor = float(payload.get("valor") or 0)
    qtd = float(payload.get("qtd") or 0)
    if valor <= 0 and qtd <= 0:
        raise ValueError("informe valor ou quantidade a liberar")

    if "saldo_valor" in s and valor > s.get("saldo_valor", 0):
        raise ValueError(f"saldo valor insuficiente: {s.get('saldo_valor')} < {valor}")
    if "saldo_qtd" in s and qtd > s.get("saldo_qtd", 0):
        raise ValueError(f"saldo quantidade insuficiente: {s.get('saldo_qtd')} < {qtd}")

    # cria pedido de compra vinculado ao blanket
    itens = []
    for it in payload.get("itens") or cur.get("itens") or []:
        itens.append({
            "prod_id": it.get("prod_id") or "",
            "produto": it.get("produto") or "",
            "qtd": qtd or it.get("qtd") or 1,
            "uom": it.get("uom") or "UN",
            "preco": it.get("preco") or 0,
            "desconto": 0,
            "subtotal": (qtd or it.get("qtd") or 1) * (it.get("preco") or 0),
        })
    pedido = {
        "tipo": "pedido",
        "status": "rascunho",
        "data": _today(),
        "razao_social": payload.get("fornecedor") or cur.get("fornecedor") or cur.get("descricao") or "",
        "comprador": cur.get("comprador") or usuario,
        "payment_terms": cur.get("payment_terms") or "30",
        "forma_pg": cur.get("forma_pg") or "Boleto",
        "notas": f"Liberação do blanket {cur.get('numero')} (acordo {acordo_id})",
        "itens": itens,
        "acordo_id": cur.get("id"),
        "acordo_numero": cur.get("numero"),
    }
    saved = compras_store.save(pedido, is_new=True)

    lib = {
        "pedido_id": saved.get("id"),
        "pedido_num": saved.get("numero"),
        "valor": valor,
        "qtd": qtd,
        "data": _now(),
        "usuario": usuario,
    }
    s.setdefault("liberacoes", []).insert(0, lib)
    if "saldo_valor" in s:
        s["saldo_valor"] = max(0, s["saldo_valor"] - valor)
    if "saldo_qtd" in s:
        s["saldo_qtd"] = max(0, s["saldo_qtd"] - qtd)
    s["atualizado_por"] = usuario
    s["atualizado_em"] = _now()
    data["saldos"][sid] = s
    _save_blanket(data)
    sync_json()
    return {"acordo": get(acordo_id), "pedido": saved, "saldo": s}


def mapa_cotacao(acordo_id):
    """
    Retorna estrutura de comparação de cotações para o acordo.
    Fornecedores x Itens com preços, prazos, frete e totais.
    """
    a = get(acordo_id)
    if not a:
        raise ValueError("acordo não encontrado")
    itens = a.get("itens") or []
    cotacoes = a.get("cotacoes") or []
    fornecedores = sorted({c.get("fornecedor") or c.get("fornecedor_id") or "—" for c in cotacoes})

    # matriz: produto x fornecedor = preco
    matriz = []
    for it in itens:
        prod = it.get("produto") or it.get("prod_id") or "—"
        qtd = float(it.get("qtd") or 0)
        row = {"produto": prod, "qtd": qtd, "uom": it.get("uom") or "UN", "precos": {}}
        for c in cotacoes:
            forn = c.get("fornecedor") or c.get("fornecedor_id") or "—"
            ci = next((i for i in c.get("itens") or [] if (i.get("produto") or "").lower() == prod.lower() or (i.get("prod_id") or "").lower() == str(it.get("prod_id") or "").lower()), {})
            row["precos"][forn] = {
                "preco": ci.get("preco") if ci.get("preco") else None,
                "subtotal": ci.get("subtotal") if ci.get("subtotal") else None,
            }
        matriz.append(row)

    resumo = []
    for c in cotacoes:
        forn = c.get("fornecedor") or c.get("fornecedor_id") or "—"
        resumo.append({
            "fornecedor": forn,
            "prazo": c.get("prazo"),
            "forma_pg": c.get("forma_pg"),
            "frete": c.get("frete"),
            "valor_total": c.get("valor_total"),
            "vencedora": bool(c.get("vencedora")),
        })
    resumo.sort(key=lambda x: float(x.get("valor_total") or 0))

    return {
        "acordo": {"id": a.get("id"), "numero": a.get("numero"), "descricao": a.get("descricao")},
        "fornecedores": fornecedores,
        "itens": itens,
        "matriz": matriz,
        "resumo": resumo,
        "vencedor": a.get("vencedor"),
    }


def sync_json(data=None):
    payload = data if data is not None else {"acordos": listar()}
    os.makedirs(os.path.dirname(JSON_FILE) or ".", exist_ok=True)
    jsonio.save(JSON_FILE, payload)
    return payload
