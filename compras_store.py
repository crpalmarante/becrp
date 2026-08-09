"""
Pedidos de Compra — store COBOL (fonte da verdade).

.dat SEQUENTIAL:
  dados/pedidos_compra.dat
  dados/itens_pedido_compra.dat

Projeção: dados/pedidos_compra.json (consulta/relatório).
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import cobol_bridge
import currency_store
import jsonio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "dados", "pedidos_compra.json")
DAT_HEADER = os.path.join(BASE_DIR, "dados", "pedidos_compra.dat")
DAT_ITENS = os.path.join(BASE_DIR, "dados", "itens_pedido_compra.dat")
APROV_FILE = os.path.join(BASE_DIR, "dados", "compra_aprovacoes.json")
WORKFLOW_FILE = os.path.join(BASE_DIR, "dados", "workflow.json")

STATUSES = ("rascunho", "pendente", "aprovado", "enviado", "recebido", "cancelado")
FLOW = {
    "rascunho": {"pendente", "aprovado", "enviado", "cancelado"},
    "pendente": {"aprovado", "cancelado"},
    "aprovado": {"enviado", "cancelado"},
    "enviado": {"recebido", "cancelado"},
    "recebido": set(),
    "cancelado": set(),
}


def _flow_with_settings():
    """Retorna fluxo considerando setting requer_aprovacao."""
    try:
        import settings_store
        requer = settings_store.get("compras", "requer_aprovacao", True)
    except Exception:
        requer = True
    flow = dict(FLOW)
    if not requer:
        flow["rascunho"] = {"aprovado", "enviado", "cancelado"}
    return flow


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _clip(val, n):
    s = str(val if val is not None else "")
    s = s.replace('"', "'").replace("\n", " ").replace("\r", " ")
    return s[:n]


def _parse_json_blob(out, key):
    text = (out or "").strip()
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
            if line.startswith("{") and ('"id"' in line or '"prod_id"' in line or '"pedido_id"' in line):
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return rows


def _header_env(pedido, *, with_id=True):
    p = pedido or {}
    smart = p.get("smart") or {}
    env = {
        "NUMERO": _clip(p.get("numero"), 12),
        "STATUS": _clip(p.get("status") or "rascunho", 12),
        "DATA": _clip(p.get("data"), 10),
        "PREVISAO": _clip(p.get("previsao") or p.get("validade"), 10),
        "FORNECEDOR_ID": _clip(p.get("fornecedor_id") or p.get("cliente_id"), 12),
        "RAZAO": _clip(p.get("razao_social") or p.get("razao") or p.get("fornecedor_nome"), 60),
        "CNPJ": _clip(p.get("cnpj"), 18),
        "IE": _clip(p.get("ie"), 20),
        "CIDADE": _clip(p.get("cidade"), 30),
        "UF": _clip(p.get("uf"), 2),
        "END_ENT": _clip(p.get("endereco_entrega") or p.get("endereco_entrega"), 80),
        "COMPRADOR": _clip(p.get("comprador") or p.get("vendedor"), 30),
        "TERMS": _clip(p.get("payment_terms") or p.get("condicao_pg"), 20),
        "FORMA_PG": _clip(p.get("forma_pg"), 20),
        "TOTAL": str(p.get("total") or 0),
        "RECEB_ID": _clip(p.get("recebimento_id") or p.get("receb_id"), 10),
        "RECEB_NUM": _clip(p.get("recebimento_num") or p.get("receb_num"), 12),
        "NFE_CHAVE": _clip(p.get("nfe_chave") or p.get("chave_nfe"), 44),
        "SMART_REC": str(smart.get("recebimentos") or 0),
        "NOTAS": _clip(p.get("notas"), 80),
    }
    if with_id and p.get("id") is not None:
        env["ID"] = str(p.get("id"))
    return env


def _normalize_header(h):
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
    smart = out.get("smart")
    if not isinstance(smart, dict):
        out["smart"] = {"recebimentos": 0}
    else:
        out["smart"] = {"recebimentos": int(smart.get("recebimentos") or 0)}
    if out.get("payment_terms") and not out.get("condicao_pg"):
        out["condicao_pg"] = out["payment_terms"]
    if out.get("recebimento_id"):
        out["receb_id"] = out["recebimento_id"]
    if out.get("recebimento_num"):
        out["receb_num"] = out["recebimento_num"]
    return out


def _normalize_item(it):
    qtd = float(it.get("qtd") or 0)
    preco = float(it.get("preco") or 0)
    desc = float(it.get("desconto") or 0)
    sub = qtd * preco * (1 - desc / 100.0)
    return {
        "prod_id": it.get("prod_id") or "",
        "produto": it.get("produto") or "",
        "qtd": qtd,
        "uom": it.get("uom") or "UN",
        "preco": preco,
        "desconto": desc,
        "imposto": float(it.get("imposto") or 0),
        "subtotal": round(sub, 2),
    }


def listar_cabecalhos():
    out, _ = cobol_bridge._run("gerir_pedidos_compra", {"ACAO": "listar"})
    return [_normalize_header(h) for h in _parse_json_blob(out, "pedidos")]


def listar_itens(pedido_id=None):
    if pedido_id is None:
        out, _ = cobol_bridge._run("gerir_itens_ped_compra", {"ACAO": "listar"})
    else:
        out, _ = cobol_bridge._run(
            "gerir_itens_ped_compra",
            {"ACAO": "listar-ped", "PEDIDO_ID": str(pedido_id)},
        )
    return [_normalize_item(i) for i in _parse_json_blob(out, "itens")]


def listar():
    headers = listar_cabecalhos()
    out, _ = cobol_bridge._run("gerir_itens_ped_compra", {"ACAO": "listar"})
    raw_items = _parse_json_blob(out, "itens")
    by_pid = {}
    for it in raw_items:
        pid = str(it.get("pedido_id") or "")
        by_pid.setdefault(pid, []).append(_normalize_item(it))
    pedidos = []
    for h in headers:
        p = dict(h)
        p["itens"] = by_pid.get(str(p.get("id")), [])
        p["aprova"] = _get_aprovacao(p.get("id"))
        pedidos.append(_enrich_currency(p))
    pedidos.sort(key=lambda x: int(x.get("id") or 0), reverse=True)
    return pedidos


def get(pedido_id):
    out, _ = cobol_bridge._run(
        "gerir_pedidos_compra", {"ACAO": "buscar", "ID": str(pedido_id)}
    )
    text = (out or "").strip()
    if '"status":"erro"' in text.replace(" ", ""):
        return None
    start = text.find('{"id":')
    if start < 0:
        return None
    line = text[start:].splitlines()[0].strip()
    try:
        h = _normalize_header(json.loads(line))
    except json.JSONDecodeError:
        return None
    h["itens"] = listar_itens(pedido_id)
    h["aprova"] = _get_aprovacao(pedido_id)
    return _enrich_currency(h)


def _replace_itens(pedido_id, itens):
    cobol_bridge._run(
        "gerir_itens_ped_compra",
        {"ACAO": "limpar", "PEDIDO_ID": str(pedido_id)},
    )
    for i, it in enumerate(itens or [], start=1):
        cobol_bridge._run(
            "gerir_itens_ped_compra",
            {
                "ACAO": "incluir",
                "PEDIDO_ID": str(pedido_id),
                "SEQ": str(i),
                "PROD_ID": _clip(it.get("prod_id"), 10),
                "PRODUTO": _clip(it.get("produto"), 40),
                "UOM": _clip(it.get("uom") or "UN", 4),
                "QTD": str(it.get("qtd") or 0),
                "PRECO": str(it.get("preco") or 0),
                "DESCONTO": str(it.get("desconto") or 0),
                "IMPOSTO": str(it.get("imposto") or 0),
            },
        )


def _recalc_total(p):
    total = 0.0
    for it in p.get("itens") or []:
        total += float(it.get("subtotal") or 0)
    return round(total, 2)


def _enrich_currency(p):
    """Adiciona moeda e valor convertido para BRL no pedido de compra."""
    if not p:
        return p
    cur = currency_store.get_pedido_moeda(p.get("id"))
    p["moeda"] = cur.get("moeda", "BRL")
    p["taxa_cambio"] = cur.get("taxa", 1.0)
    total_local = float(p.get("total") or 0)
    p["total_brl"] = round(currency_store.converter(total_local, p["moeda"], "BRL"), 2)
    for it in p.get("itens") or []:
        sub_local = float(it.get("subtotal") or 0)
        it["subtotal_brl"] = round(currency_store.converter(sub_local, p["moeda"], "BRL"), 2)
    return p


def _apply_compras_defaults(p, is_new=False):
    """Aplica defaults de settings na criação/edição de pedido."""
    try:
        import settings_store
    except Exception:
        return p
    if is_new:
        if not p.get("comprador"):
            p["comprador"] = settings_store.get("compras", "comprador_padrao", "")
        if not p.get("payment_terms"):
            p["payment_terms"] = settings_store.get("compras", "condicao_pg_padrao", "30")
        if not p.get("forma_pg"):
            p["forma_pg"] = settings_store.get("compras", "forma_pg_padrao", "Boleto")
        if not p.get("previsao"):
            dias = int(settings_store.get("compras", "dias_previsao_padrao", 7) or 7)
            from datetime import timedelta
            p["previsao"] = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
    return p


def save(pedido, *, is_new=False):
    p = dict(pedido or {})
    if not is_new and p.get("id") is not None:
        target = get(p["id"])
        if not target:
            raise ValueError("pedido não encontrado")
        try:
            import settings_store
            bloquear_enviado = settings_store.get("compras", "bloquear_edicao_pedido_enviado", True)
            bloquear_recebido = settings_store.get("compras", "bloquear_edicao_pedido_recebido", True)
            if bloquear_recebido and target.get("status") == "recebido":
                raise ValueError("pedido recebido não pode ser editado")
            if bloquear_enviado and target.get("status") == "enviado":
                raise ValueError("pedido enviado não pode ser editado")
        except Exception:
            pass
    if is_new or p.get("id") is None:
        p = _apply_compras_defaults(p, is_new=True)
        out, _ = cobol_bridge._run(
            "gerir_pedidos_compra", {"ACAO": "proximo-id"}
        )
        try:
            new_id = int((out or "").splitlines()[0].strip())
        except (ValueError, IndexError):
            new_id = 1
        p["id"] = new_id
        if not p.get("numero"):
            p["numero"] = f"PC{new_id:05d}"
    itens = p.get("itens") or []
    # normaliza itens e calcula total antes de gravar cabeçalho
    itens = [_normalize_item(i) for i in itens]
    p["itens"] = itens
    p["total"] = sum(float(i.get("subtotal") or 0) for i in itens)
    env = _header_env(p)
    env["ACAO"] = "incluir" if is_new or pedido.get("id") is None else "alterar"
    out, _ = cobol_bridge._run("gerir_pedidos_compra", env)
    if "ERRO" in (out or ""):
        raise Exception(out.strip())
    _replace_itens(p["id"], itens)
    # guarda moeda do pedido em JSON auxiliar (até campo no COBOL)
    if p.get("moeda"):
        currency_store.set_pedido_moeda(
            p["id"], p["moeda"], p.get("taxa_cambio"), usuario=p.get("comprador") or ""
        )
    updated = get(p["id"])
    sync_json()
    return updated


def delete(pedido_id):
    out, _ = cobol_bridge._run(
        "gerir_pedidos_compra", {"ACAO": "excluir", "ID": str(pedido_id)}
    )
    if "ERRO" in (out or ""):
        raise Exception(out.strip())
    sync_json()
    return True


# ── Aprovações de pedido de compra (JSON) ─────────────────────

def _load_aprovacoes():
    if not os.path.exists(APROV_FILE):
        return {"aprovacoes": [], "rejeicoes": []}
    with open(APROV_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"aprovacoes": [], "rejeicoes": []}
    data.setdefault("aprovacoes", [])
    data.setdefault("rejeicoes", [])
    return data


def _save_aprovacoes(data):
    os.makedirs(os.path.dirname(APROV_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    jsonio.save(APROV_FILE, data)


def _load_workflow():
    if not os.path.exists(WORKFLOW_FILE):
        return {}
    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    return data.get("compra", {})


def _user_can_approve(user, total, workflow_cfg):
    """Simplificado: aprovador se role permitida na transição pendente->aprovado ou valor abaixo do limite."""
    try:
        import settings_store
        limite = float(settings_store.get("compras", "aprovacao_limite_direto", 0))
    except Exception:
        limite = float((workflow_cfg.get("limites") or {}).get("aprovacao_direta", 0))
    if total <= limite:
        return True
    try:
        import settings_store
        allowed_settings = set(settings_store.get("compras", "aprovacao_roles", []))
    except Exception:
        allowed_settings = set()
    roles = set((user or {}).get("roles") or [])
    allowed = set((workflow_cfg.get("transitions") or {})
                  .get("pendente", {})
                  .get("aprovado", {})
                  .get("roles") or [])
    allowed.update(allowed_settings)
    return bool(roles & allowed) or (user or {}).get("admin") or (user or {}).get("role") in allowed


def aprovar(pedido_id, *, usuario="", user=None, motivo=""):
    cur = get(pedido_id)
    if not cur:
        raise ValueError("pedido não encontrado")
    if cur.get("status") not in ("rascunho", "pendente"):
        raise ValueError("somente rascunho ou pendente pode ser aprovado")
    total = float(cur.get("total") or 0)
    wf = _load_workflow()
    if not _user_can_approve(user, total, wf):
        raise ValueError("usuário sem permissão para aprovar este valor")

    data = _load_aprovacoes()
    data["aprovacoes"].insert(0, {
        "pedido_id": int(pedido_id),
        "usuario": usuario,
        "data": _now(),
        "motivo": motivo,
        "valor": total,
    })
    _save_aprovacoes(data)
    return _set_status_raw(pedido_id, "aprovado", usuario=usuario)


def rejeitar(pedido_id, *, usuario="", motivo=""):
    cur = get(pedido_id)
    if not cur:
        raise ValueError("pedido não encontrado")
    if cur.get("status") not in ("rascunho", "pendente"):
        raise ValueError("somente rascunho ou pendente pode ser rejeitado")
    data = _load_aprovacoes()
    data["rejeicoes"].insert(0, {
        "pedido_id": int(pedido_id),
        "usuario": usuario,
        "data": _now(),
        "motivo": motivo,
    })
    _save_aprovacoes(data)
    return _set_status_raw(pedido_id, "cancelado", usuario=usuario)


def _get_aprovacao(pedido_id):
    data = _load_aprovacoes()
    aprov = next((a for a in data.get("aprovacoes") if a["pedido_id"] == int(pedido_id)), None)
    reje = next((r for r in data.get("rejeicoes") if r["pedido_id"] == int(pedido_id)), None)
    return {"aprovacao": aprov, "rejeicao": reje}


def _set_status_raw(pedido_id, st, *, usuario=""):
    cur = get(pedido_id)
    if not cur:
        raise ValueError("pedido não encontrado")
    out, _ = cobol_bridge._run(
        "gerir_pedidos_compra",
        {
            "ACAO": "alterar",
            "ID": str(pedido_id),
            **_header_env(cur, with_id=True),
            "STATUS": st,
        },
    )
    if "ERRO" in (out or ""):
        raise Exception(out.strip())
    updated = get(pedido_id)
    updated["aprova"] = _get_aprovacao(pedido_id)
    sync_json()
    return updated


def set_status(pedido_id, novo_status, *, usuario="", user=None):
    st = str(novo_status or "").lower()
    if st not in STATUSES:
        raise ValueError(f"status inválido: {novo_status}")
    cur = get(pedido_id)
    if not cur:
        raise ValueError("pedido não encontrado")
    atual = cur.get("status") or "rascunho"
    if st == atual:
        cur["aprova"] = _get_aprovacao(pedido_id)
        return cur
    if st not in _flow_with_settings().get(atual, set()):
        raise ValueError(f"transição inválida: {atual} → {st}")

    if st == "aprovado":
        return aprovar(pedido_id, usuario=usuario, user=user)
    if st == "cancelado" and atual == "pendente":
        return rejeitar(pedido_id, usuario=usuario, motivo="Rejeitado na aprovação")

    return _set_status_raw(pedido_id, st, usuario=usuario)


def historico_precos(*, fornecedor_id=None, produto=None, prod_id=None, limite=50):
    """
    Retorna histórico de preços de compras aprovadas/recebidas e recebimentos manuais concluídos.
    Útil para conferência na criação de novo pedido/acordo.
    """
    rows = []
    for p in listar():
        if p.get("status") not in ("aprovado", "enviado", "recebido"):
            continue
        fid = str(p.get("fornecedor_id") or "").strip()
        for it in p.get("itens") or []:
            pid = str(it.get("prod_id") or "").strip()
            nome = str(it.get("produto") or "").strip()
            if not nome and not pid:
                continue
            if fornecedor_id and fid != str(fornecedor_id):
                continue
            if prod_id and pid != str(prod_id):
                continue
            if produto and produto.lower() not in nome.lower():
                continue
            rows.append({
                "pedido_id": p.get("id"),
                "pedido_num": p.get("numero"),
                "data": p.get("data"),
                "fornecedor_id": fid,
                "fornecedor": p.get("razao_social") or "",
                "prod_id": pid,
                "produto": nome,
                "uom": it.get("uom") or "UN",
                "qtd": float(it.get("qtd") or 0),
                "preco": float(it.get("preco") or 0),
                "status": p.get("status"),
                "origem": "pedido_compra",
            })

    # recebimentos manuais concluídos também entram no histórico de custo
    try:
        import receiving_mvp
        for r in receiving_mvp.list_receivings(status="completed"):
            if r.get("origem") not in ("manual", "nfe"):
                continue
            fid = str(r.get("fornecedor_id") or "").strip()
            for it in r.get("items") or []:
                pid = str(it.get("produto_id") or "").strip()
                nome = str(it.get("produto_nome") or "").strip()
                if not nome and not pid:
                    continue
                if fornecedor_id and fid != str(fornecedor_id):
                    continue
                if prod_id and pid != str(prod_id):
                    continue
                if produto and produto.lower() not in nome.lower():
                    continue
                if not float(it.get("preco") or 0):
                    continue
                rows.append({
                    "recebimento_id": r.get("id"),
                    "data": r.get("completed_at") or r.get("created_at"),
                    "fornecedor_id": fid,
                    "fornecedor": r.get("fornecedor_nome") or "",
                    "prod_id": pid,
                    "produto": nome,
                    "uom": it.get("unidade") or "UN",
                    "qtd": float(it.get("qty_verified") or it.get("qty_expected") or 0),
                    "preco": float(it.get("preco") or 0),
                    "status": "recebido",
                    "origem": "recebimento_" + str(r.get("origem") or "manual"),
                })
    except Exception:
        pass

    rows.sort(key=lambda r: r.get("data") or "", reverse=True)
    return rows[:limite]


def resumo_preco(produto, *, fornecedor_id=None, prod_id=None):
    """Retorna último, mínimo, média e fornecedores para um produto."""
    hist = historico_precos(fornecedor_id=fornecedor_id, produto=produto, prod_id=prod_id, limite=1000)
    if not hist:
        return None
    precos = [h["preco"] for h in hist if h["preco"] > 0]
    if not precos:
        return None
    by_forn = {}
    for h in hist:
        key = h["fornecedor"] or h["fornecedor_id"] or "—"
        by_forn.setdefault(key, []).append(h["preco"])
    return {
        "produto": produto,
        "prod_id": prod_id,
        "total_compras": len(hist),
        "ultimo_preco": hist[0]["preco"],
        "ultimo_data": hist[0]["data"],
        "ultimo_fornecedor": hist[0]["fornecedor"],
        "menor_preco": round(min(precos), 2),
        "maior_preco": round(max(precos), 2),
        "media_preco": round(sum(precos) / len(precos), 2),
        "fornecedores": [
            {"fornecedor": k, "media": round(sum(v) / len(v), 2), "compras": len(v)}
            for k, v in sorted(by_forn.items(), key=lambda x: sum(x[1]) / len(x[1]))
        ],
    }


def followup_entregas(*, atraso_minimo=0):
    """
    Follow-up de entregas: compara previsão do pedido com data efetiva do recebimento.
    Retorna pedidos atrasados, no prazo e pendentes de entrega.
    """
    try:
        import receiving_mvp
    except Exception:
        receiving_mvp = None

    hoje = datetime.now().strftime("%Y-%m-%d")
    rows = []
    for p in listar():
        if p.get("status") not in ("aprovado", "enviado", "recebido"):
            continue
        prev = p.get("previsao") or ""
        entrega = None
        atraso_dias = None
        no_prazo = None
        rid = p.get("recebimento_id") or ""

        # tenta vincular por recebimento_id
        if rid and receiving_mvp:
            r = receiving_mvp.get_receiving(rid)
            if r and r.get("status") == "completed":
                entrega = r.get("completed_at") or r.get("created_at")

        # tenta por pedido_compra_id no receiving
        if not entrega and receiving_mvp:
            for r in receiving_mvp.list_receivings(status="completed"):
                if str(r.get("pedido_compra_id")) == str(p.get("id")):
                    entrega = r.get("completed_at") or r.get("created_at")
                    break

        if prev:
            if entrega:
                d_prev = datetime.strptime(prev[:10], "%Y-%m-%d")
                d_ent = datetime.strptime(entrega[:10], "%Y-%m-%d")
                delta = (d_ent - d_prev).days
                atraso_dias = delta
                no_prazo = delta <= 0
            else:
                d_prev = datetime.strptime(prev[:10], "%Y-%m-%d")
                d_hoje = datetime.strptime(hoje, "%Y-%m-%d")
                atraso_dias = (d_hoje - d_prev).days
                no_prazo = atraso_dias <= 0

        if atraso_dias is not None and atraso_dias < atraso_minimo:
            continue

        rows.append({
            "pedido_id": p.get("id"),
            "pedido_num": p.get("numero"),
            "fornecedor": p.get("razao_social") or "",
            "fornecedor_id": p.get("fornecedor_id") or "",
            "previsao": prev,
            "entrega": entrega[:10] if entrega else None,
            "status_pedido": p.get("status"),
            "atraso_dias": atraso_dias,
            "no_prazo": no_prazo,
            "recebimento_id": rid,
        })
    rows.sort(key=lambda x: (x["atraso_dias"] or -9999), reverse=True)
    return rows


def scorecard_fornecedor(fornecedor_id=None):
    """Performance de entrega por fornecedor."""
    rows = followup_entregas(atraso_minimo=-9999)
    by_forn = {}
    for r in rows:
        fid = r.get("fornecedor_id") or r.get("fornecedor") or "—"
        if fornecedor_id and str(fid) != str(fornecedor_id):
            continue
        f = by_forn.setdefault(fid, {"fornecedor": r["fornecedor"], "entregas": 0, "atrasos": 0, "no_prazo": 0, "dias_atraso": []})
        f["entregas"] += 1
        if r["entrega"]:
            if r["atraso_dias"] is not None and r["atraso_dias"] > 0:
                f["atrasos"] += 1
                f["dias_atraso"].append(r["atraso_dias"])
            elif r["atraso_dias"] is not None and r["atraso_dias"] <= 0:
                f["no_prazo"] += 1
    out = []
    for fid, f in by_forn.items():
        total = f["entregas"]
        f["pct_atraso"] = round(f["atrasos"] / total * 100, 1) if total else 0
        f["pct_no_prazo"] = round(f["no_prazo"] / total * 100, 1) if total else 0
        f["media_atraso"] = round(sum(f["dias_atraso"]) / len(f["dias_atraso"]), 1) if f["dias_atraso"] else 0
        out.append(f)
    out.sort(key=lambda x: x["pct_atraso"])
    return out


def three_way_match(pedido_id):
    """
    Compara pedido de compra × recebimento × fatura (NF-e).
    Retorna estrutura com quantidades/valores e divergências.
    """
    pedido = get(pedido_id)
    if not pedido:
        raise ValueError("pedido não encontrado")

    recebimento = None
    fatura = None
    try:
        import receiving_mvp
        rid = pedido.get("recebimento_id")
        if rid:
            recebimento = receiving_mvp.get_receiving(rid)
    except Exception:
        pass

    # busca fatura via nfe_chave ou recebimento
    chave = pedido.get("nfe_chave") or ""
    if not chave and recebimento and (recebimento.get("nfe") or {}).get("chave"):
        chave = recebimento["nfe"]["chave"]
    if chave:
        try:
            import nfe_entrada_store
            fatura = nfe_entrada_store.find_by_chave(chave)
        except Exception:
            pass
    if not fatura and recebimento:
        # tenta por recebimento_id
        try:
            import nfe_entrada_store
            for fe in nfe_entrada_store.listar():
                if str(fe.get("receiving_id")) == str(recebimento.get("id")):
                    fatura = fe
                    break
        except Exception:
            pass

    # indexar por produto
    def key_prod(nome, prod_id):
        return str(prod_id or nome or "").strip().lower()

    pedido_itens = {}
    for it in pedido.get("itens") or []:
        k = key_prod(it.get("produto"), it.get("prod_id"))
        if k:
            pedido_itens[k] = {
                "produto": it.get("produto"),
                "prod_id": it.get("prod_id"),
                "qtd": float(it.get("qtd") or 0),
                "preco": float(it.get("preco") or 0),
                "subtotal": float(it.get("subtotal") or 0),
            }

    receb_itens = {}
    if recebimento:
        for it in recebimento.get("items") or []:
            k = key_prod(it.get("produto_nome"), it.get("produto_id"))
            if k:
                receb_itens[k] = {
                    "produto": it.get("produto_nome"),
                    "prod_id": it.get("produto_id"),
                    "qtd": float(it.get("qty_verified") or it.get("qty_expected") or 0),
                }

    fatura_itens = {}
    if fatura:
        for it in fatura.get("itens") or []:
            k = key_prod(it.get("nome"), it.get("produto_id"))
            if not k:
                k = key_prod(it.get("codigo"), "")
            if k:
                fatura_itens[k] = {
                    "produto": it.get("nome") or it.get("codigo"),
                    "prod_id": it.get("produto_id"),
                    "qtd": float(it.get("quantidade") or 0),
                    "preco": float(it.get("vl_unitario") or 0),
                    "subtotal": float(it.get("vl_total") or 0),
                }

    todos = set(pedido_itens.keys()) | set(receb_itens.keys()) | set(fatura_itens.keys())
    linhas = []
    divergencias = []
    for k in sorted(todos):
        p = pedido_itens.get(k, {})
        r = receb_itens.get(k, {})
        f = fatura_itens.get(k, {})
        qtd_ped = p.get("qtd") or 0
        qtd_rec = r.get("qtd") or 0
        qtd_fat = f.get("qtd") or 0
        val_ped = p.get("subtotal") or 0
        val_fat = f.get("subtotal") or 0

        dif_qtd_rec = qtd_rec - qtd_ped
        dif_qtd_fat = qtd_fat - qtd_ped if fatura else None
        dif_val = val_fat - val_ped if fatura else None

        linhas.append({
            "produto": p.get("produto") or r.get("produto") or f.get("produto") or k,
            "prod_id": p.get("prod_id") or r.get("prod_id") or f.get("prod_id"),
            "pedido_qtd": qtd_ped,
            "pedido_valor": round(val_ped, 2),
            "recebimento_qtd": qtd_rec,
            "fatura_qtd": qtd_fat,
            "fatura_valor": round(val_fat, 2),
            "dif_qtd_recebimento": round(dif_qtd_rec, 3),
            "dif_qtd_fatura": round(dif_qtd_fat, 3) if dif_qtd_fat is not None else None,
            "dif_valor": round(dif_val, 2) if dif_val is not None else None,
        })

        if abs(dif_qtd_rec) > 0.001:
            divergencias.append({"tipo": "qtd_recebimento", "produto": k, "esperado": qtd_ped, "recebido": qtd_rec})
        if fatura and dif_qtd_fat is not None and abs(dif_qtd_fat) > 0.001:
            divergencias.append({"tipo": "qtd_fatura", "produto": k, "esperado": qtd_ped, "faturado": qtd_fat})
        if fatura and dif_val is not None and abs(dif_val) > 0.01:
            divergencias.append({"tipo": "valor", "produto": k, "esperado": val_ped, "faturado": val_fat})

    total_ped = sum(p.get("subtotal") or 0 for p in pedido_itens.values())
    total_fat = sum(f.get("subtotal") or 0 for f in fatura_itens.values()) if fatura else 0

    return {
        "pedido": {"id": pedido.get("id"), "numero": pedido.get("numero"), "status": pedido.get("status")},
        "recebimento": recebimento and {"id": recebimento.get("id"), "status": recebimento.get("status")},
        "fatura": fatura and {"chave": fatura.get("chave"), "numero": fatura.get("numero"), "status": fatura.get("status")},
        "linhas": linhas,
        "totais": {
            "pedido": round(total_ped, 2),
            "fatura": round(total_fat, 2),
            "diferenca": round(total_fat - total_ped, 2),
        },
        "divergencias": divergencias,
        "ok": not divergencias,
    }


def relatorio(*, de=None, ate=None, fornecedor=None, status=None, produto=None):
    """
    Relatório de compras: filtros + resultado + totais.
    Segue padrão reports-UX: resultado na tela, impressão sob demanda.
    """
    rows = []
    for p in listar():
        dt = p.get("data") or ""
        if de and dt < str(de):
            continue
        if ate and dt > str(ate):
            continue
        forn = (p.get("razao_social") or "").lower()
        if fornecedor and fornecedor.lower() not in forn:
            continue
        if status and p.get("status") != status:
            continue
        itens = []
        for it in p.get("itens") or []:
            nome = (it.get("produto") or "").lower()
            if produto and produto.lower() not in nome:
                continue
            itens.append(it)
        if produto and not itens:
            continue
        total = sum(float(i.get("subtotal") or 0) for i in itens) if produto else float(p.get("total") or 0)
        rows.append({
            "pedido_id": p.get("id"),
            "numero": p.get("numero"),
            "data": p.get("data"),
            "fornecedor": p.get("razao_social") or "",
            "status": p.get("status"),
            "itens": itens if produto else (p.get("itens") or []),
            "total": round(total, 2),
        })
    rows.sort(key=lambda r: r.get("data") or "", reverse=True)

    total_geral = sum(r["total"] for r in rows)
    por_status = {}
    por_fornecedor = {}
    for r in rows:
        por_status[r["status"]] = por_status.get(r["status"], 0) + r["total"]
        fn = r["fornecedor"] or "—"
        por_fornecedor[fn] = por_fornecedor.get(fn, 0) + r["total"]

    return {
        "rows": rows,
        "total": round(total_geral, 2),
        "count": len(rows),
        "por_status": {k: round(v, 2) for k, v in sorted(por_status.items())},
        "por_fornecedor": [{"fornecedor": k, "total": round(v, 2)} for k, v in sorted(por_fornecedor.items(), key=lambda x: x[1], reverse=True)],
    }


def sync_json(data=None):
    payload = data if data is not None else {"pedidos": listar()}
    os.makedirs(os.path.dirname(JSON_FILE) or ".", exist_ok=True)
    jsonio.save(JSON_FILE, payload)
    return payload
