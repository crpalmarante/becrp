"""
WMS — Rotas e regras push/pull (RFC-9012 MVP).

Regras automatizam a movimentação de produtos entre localizações
(internas ou externas) com base em condições de nível de estoque:

- PULL (reposição): quando o saldo na localização DESTINO fica abaixo do
  nível mínimo, puxa `qtd_reposicao` da ORIGEM para o DESTINO.
- PUSH (escoamento): quando o saldo na localização ORIGEM ultrapassa o
  nível máximo, empurra o excedente para o DESTINO.

A avaliação compara os saldos por localização (data/inventory_balances.json)
e devolve sugestões. O apply materializa as sugestões como operações WMS
(TRF-INT) ou como transferência direta de estoque (modo_aplicar).

Fonte: dados/wms_rules.json
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

import inventory_mvp
import wms_locations
import wms_operations

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_rules.json")

RULE_TYPES = {"pull": "Reposição (pull)", "push": "Escoamento (push)"}
PRIORITIES = {"alta": "Alta", "normal": "Normal", "baixa": "Baixa"}
APPLY_MODES = {"operacao": "Operação WMS", "direto": "Transferência direta"}
STATUS_SUGGESTION = {
    "ok": "Pronto para aplicar",
    "parcial": "Parcial (estoque/capacidade limitada)",
    "sem_estoque_origem": "Sem estoque na origem",
    "destino_sem_capacidade": "Destino sem capacidade",
}

SEED = (
    {
        "id": "R01",
        "nome": "Reposição da face de picking",
        "tipo": "pull",
        "armazem": "DC-01",
        "origem": "A01-01-01",
        "destino": "PCK-01",
        "produto_id": "1",
        "categoria": "",
        "nivel_min": 5,
        "nivel_max": 0,
        "qtd_reposicao": 10,
        "prioridade": "alta",
        "modo_aplicar": "operacao",
        "ativo": True,
    },
    {
        "id": "R02",
        "nome": "Escoamento da doca de recebimento",
        "tipo": "push",
        "armazem": "DC-01",
        "origem": "REC-DOCK-01",
        "destino": "A01-01-02",
        "produto_id": "2",
        "categoria": "",
        "nivel_min": 0,
        "nivel_max": 20,
        "qtd_reposicao": 0,
        "prioridade": "normal",
        "modo_aplicar": "operacao",
        "ativo": True,
    },
)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return ensure_seed()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return ensure_seed()
    if not isinstance(data.get("regras"), list):
        data["regras"] = []
    if data.get("seq") is None:
        data["seq"] = len(data["regras"])
    if not data["regras"]:
        return ensure_seed()
    return data


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("regras") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_id(data):
    seq = int(data.get("seq") or 0) + 1
    data["seq"] = seq
    return f"R{seq:02d}"


def _hist(regra, usuario="", nota=""):
    hist = list(regra.get("historico") or [])
    hist.append({
        "em": _now(),
        "usuario": str(usuario or "").strip(),
        "nota": str(nota or "").strip(),
    })
    return hist


def _norm_tipo(val):
    t = str(val or "").strip().lower()
    if t not in RULE_TYPES:
        raise ValueError("tipo deve ser: pull ou push")
    return t


def _norm_prioridade(val):
    p = str(val or "normal").strip().lower()
    if p not in PRIORITIES:
        raise ValueError("prioridade deve ser: alta, normal ou baixa")
    return p


def _norm_modo(val):
    m = str(val or "operacao").strip().lower()
    if m not in APPLY_MODES:
        raise ValueError("modo_aplicar deve ser: operacao ou direto")
    return m


def _opt_str(body, existing, key, default=""):
    if key in body:
        return str(body.get(key) or "").strip()
    return str((existing or {}).get(key) or default).strip()


def _validate_rule_refs(tipo, armazem, origem, destino, body=None):
    body = body or {}
    if not armazem:
        raise ValueError("armazém obrigatório")
    if not origem or not destino:
        raise ValueError("origem e destino obrigatórios")
    if origem == destino:
        raise ValueError("origem e destino devem ser diferentes")
    for cod in (origem, destino):
        loc = wms_locations.get_localizacao(cod)
        if not loc:
            raise ValueError(f"localização {cod} não encontrada")
        if loc.get("status") == "inactive":
            raise ValueError(f"localização {cod} está inativa")
        loc_arm = str(loc.get("armazem") or "").strip().upper()
        if loc_arm and loc_arm != str(armazem).strip().upper():
            raise ValueError(
                f"localização {cod} pertence ao armazém {loc_arm}, não a {armazem}"
            )
    if tipo == "pull":
        if not _num(body, "nivel_min", 0):
            raise ValueError("regra pull exige nivel_min > 0")
        if not _num(body, "qtd_reposicao", 0):
            raise ValueError("regra pull exige qtd_reposicao > 0")
    else:
        if not _num(body, "nivel_max", 0):
            raise ValueError("regra push exige nivel_max > 0")


def _num(body, key, default=0):
    try:
        return float(body.get(key) if body.get(key) is not None else default)
    except (TypeError, ValueError):
        return default


def _build_row(payload, existing=None):
    body = payload if isinstance(payload, dict) else {}
    existing = existing or {}
    rid = str(existing.get("id") or body.get("id") or "").strip().upper()
    if not rid:
        raise ValueError("id obrigatório")

    tipo = _norm_tipo(
        body.get("tipo") if body.get("tipo") is not None else (existing or {}).get("tipo") or ""
    )
    armazem = _opt_str(body, existing, "armazem", "DC-01").upper()
    origem = _opt_str(body, existing, "origem").upper()
    destino = _opt_str(body, existing, "destino").upper()

    _validate_rule_refs(tipo, armazem, origem, destino, body)

    produto_id = _opt_str(body, existing, "produto_id")
    categoria = _opt_str(body, existing, "categoria")
    # sem produto/categoria a regra monitora todos os produtos com saldo na rota

    return {
        "id": rid,
        "nome": _opt_str(body, existing, "nome") or f"Regra {rid}",
        "tipo": tipo,
        "armazem": armazem,
        "origem": origem,
        "destino": destino,
        "produto_id": produto_id,
        "categoria": categoria,
        "nivel_min": _num(body, "nivel_min", (existing or {}).get("nivel_min") or 0),
        "nivel_max": _num(body, "nivel_max", (existing or {}).get("nivel_max") or 0),
        "qtd_reposicao": _num(body, "qtd_reposicao", (existing or {}).get("qtd_reposicao") or 0),
        "prioridade": _norm_prioridade(
            body.get("prioridade")
            if body.get("prioridade") is not None
            else (existing or {}).get("prioridade") or "normal"
        ),
        "modo_aplicar": _norm_modo(
            body.get("modo_aplicar")
            if body.get("modo_aplicar") is not None
            else (existing or {}).get("modo_aplicar") or "operacao"
        ),
        "ativo": bool(body.get("ativo") if "ativo" in body else (existing or {}).get("ativo", True)),
        "criado_em": (existing or {}).get("criado_em") or _now(),
        "atualizado_em": _now(),
        "ultima_avaliacao": (existing or {}).get("ultima_avaliacao"),
        "ultimo_resultado": (existing or {}).get("ultimo_resultado") or "",
        "historico": _hist(existing or {}, nota="criação/edição"),
    }


def ensure_seed():
    rows = [_build_row(s) for s in SEED]
    data = {"seq": len(rows), "regras": rows, "atualizado_em": _now(), "total": len(rows)}
    _save(data)
    return data


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("regras") or []),
        "tipos": RULE_TYPES,
        "prioridades": PRIORITIES,
        "modos": APPLY_MODES,
        "status_sugestao": STATUS_SUGGESTION,
        "atualizado_em": data.get("atualizado_em"),
    }


def list_regras(q=None, tipo=None, ativo=None):
    data = _load_raw()
    rows = []
    for r in data.get("regras") or []:
        if q:
            blob = f"{r.get('id')} {r.get('nome')} {r.get('origem')} {r.get('destino')} {r.get('produto_id')} {r.get('categoria')}".lower()
            if str(q).strip().lower() not in blob:
                continue
        if tipo and r.get("tipo") != str(tipo).strip().lower():
            continue
        if ativo is not None:
            want = str(ativo).strip().lower() in ("1", "true", "sim", "on")
            if bool(r.get("ativo")) != want:
                continue
        rows.append(r)
    return {"regras": rows, "total": len(rows)}


def get_regra(rid):
    data = _load_raw()
    key = str(rid or "").strip().upper()
    for r in data.get("regras") or []:
        if str(r.get("id") or "").upper() == key:
            return r
    return None


def create_regra(payload):
    data = _load_raw()
    body = dict(payload or {})
    rid = str(body.get("id") or "").strip().upper()
    if not rid:
        rid = _next_id(data)
        body["id"] = rid
    for r in data.get("regras") or []:
        if str(r.get("id") or "").upper() == rid:
            raise ValueError(f"regra {rid} já existe")
    row = _build_row(body)
    data["regras"].append(row)
    _save(data)
    return row


def update_regra(rid, payload):
    data = _load_raw()
    key = str(rid or "").strip().upper()
    for i, r in enumerate(data.get("regras") or []):
        if str(r.get("id") or "").upper() == key:
            merged = {**r, **(payload or {})}
            merged["id"] = r.get("id")
            row = _build_row(merged, existing=r)
            data["regras"][i] = row
            _save(data)
            return row
    raise ValueError("regra não encontrada")


def delete_regra(rid):
    data = _load_raw()
    key = str(rid or "").strip().upper()
    for i, r in enumerate(data.get("regras") or []):
        if str(r.get("id") or "").upper() == key:
            data["regras"].pop(i)
            _save(data)
            return True
    raise ValueError("regra não encontrada")


def set_ativo(rid, ativo, motivo=None):
    data = _load_raw()
    key = str(rid or "").strip().upper()
    for i, r in enumerate(data.get("regras") or []):
        if str(r.get("id") or "").upper() == key:
            r["ativo"] = bool(ativo)
            r["atualizado_em"] = _now()
            r["historico"] = _hist(
                r,
                nota=f"{'ativada' if r['ativo'] else 'pausada'}"
                + (f" — {motivo}" if motivo else ""),
            )
            data["regras"][i] = r
            _save(data)
            return r
    raise ValueError("regra não encontrada")


# ─────────────────────────────── motor push/pull ───────────────────────────────

def _produtos_catalogo():
    """{id: {nome, categoria}} a partir da projeção COBOL."""
    out = {}
    path = os.path.join(BASE_DIR, "dados", "produtos.json")
    if not os.path.exists(path):
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return out
    rows = data if isinstance(data, list) else (data.get("produtos") or [])
    for p in rows:
        pid = str(p.get("id") or "").strip()
        if not pid:
            continue
        out[pid] = {
            "nome": str(p.get("nome") or pid),
            "categoria": str(p.get("categoria") or "").strip(),
        }
    return out


def _produtos_da_regra(rule, balances):
    """Produtos que a regra monitora."""
    cat = _catalogo = None
    if rule.get("produto_id"):
        pid = str(rule.get("produto_id")).strip()
        cat = _produtos_catalogo()
        return [(pid, (cat.get(pid) or {}).get("nome") or pid)]
    if rule.get("categoria"):
        cat = _produtos_catalogo()
        return [
            (pid, info.get("nome") or pid)
            for pid, info in cat.items()
            if info.get("categoria") == str(rule.get("categoria")).strip()
        ]
    # sem filtro: produtos com saldo em origem ou destino
    arm = str(rule.get("armazem") or "").strip()
    locs = (balances.get("por_localizacao") or {}).get(arm) or {}
    pids = {}
    for loc in (str(rule.get("origem") or ""), str(rule.get("destino") or "")):
        for pid, qtd in (locs.get(loc) or {}).items():
            if qtd:
                pids[str(pid)] = True
    return [(pid, pid) for pid in sorted(pids)]


def _saldo(armazem, pid, loc, balances):
    return inventory_mvp.inventory_balance(
        armazem, pid, balances=balances, location_id=loc
    )


def _capacidade_destino(loc):
    row = wms_locations.get_localizacao(loc)
    if not row:
        return None
    cap = row.get("capacidade_qtd")
    try:
        return float(cap) if cap is not None else None
    except (TypeError, ValueError):
        return None


def wms_rules_evaluate(armazem=None):
    """Avalia as regras ativas contra os saldos atuais por localização."""
    data = _load_raw()
    balances = inventory_mvp.load_balances()
    sugestoes = []
    avaliadas = 0

    for rule in data.get("regras") or []:
        if not rule.get("ativo"):
            continue
        arm = str(rule.get("armazem") or "").strip()
        if armazem and str(armazem).strip().upper() != arm.upper():
            continue
        tipo = rule.get("tipo")
        origem = str(rule.get("origem") or "").strip()
        destino = str(rule.get("destino") or "").strip()
        avaliadas += 1

        for pid, pnome in _produtos_da_regra(rule, balances):
            so = _saldo(arm, pid, origem, balances)
            sd = _saldo(arm, pid, destino, balances)

            if tipo == "pull":
                nivel_min = float(rule.get("nivel_min") or 0)
                if sd >= nivel_min:
                    continue
                alvo = float(rule.get("qtd_reposicao") or 0)
                qtd = alvo  # repõe a quantidade configurada
                if qtd <= 0:
                    continue
                if so <= 0:
                    status = "sem_estoque_origem"
                elif so < qtd:
                    qtd = so
                    status = "parcial"
                else:
                    status = "ok"
                nivel = nivel_min
                obs = f"destino {sd:g} abaixo do mínimo {nivel_min:g}"
            else:  # push
                nivel_max = float(rule.get("nivel_max") or 0)
                if so <= nivel_max:
                    continue
                excedente = so - nivel_max
                cap = _capacidade_destino(destino)
                if cap is not None:
                    livre = cap - sd
                    if livre <= 0:
                        status = "destino_sem_capacidade"
                        qtd = 0
                    elif livre < excedente:
                        qtd = livre
                        status = "parcial"
                    else:
                        qtd = excedente
                        status = "ok"
                else:
                    qtd = excedente
                    status = "ok"
                if qtd <= 0:
                    continue
                nivel = nivel_max
                obs = f"origem {so:g} acima do máximo {nivel_max:g}"

            sugestoes.append({
                "regra_id": rule.get("id"),
                "regra_nome": rule.get("nome"),
                "tipo": tipo,
                "produto_id": pid,
                "produto": pnome,
                "origem": origem,
                "destino": destino,
                "armazem": arm,
                "saldo_origem": so,
                "saldo_destino": sd,
                "nivel": nivel,
                "qtd": qtd,
                "status": status,
                "observacao": obs,
            })

    resumo = {
        "regras_avaliadas": avaliadas,
        "sugestoes": len(sugestoes),
        "ok": sum(1 for s in sugestoes if s["status"] == "ok"),
        "parciais": sum(1 for s in sugestoes if s["status"] == "parcial"),
        "sem_estoque_origem": sum(1 for s in sugestoes if s["status"] == "sem_estoque_origem"),
        "destino_sem_capacidade": sum(1 for s in sugestoes if s["status"] == "destino_sem_capacidade"),
    }
    return {
        "sugestoes": sugestoes,
        "resumo": resumo,
        "avaliado_em": _now(),
    }


def _transfer_direto(rule, sug, usuario=""):
    """Move estoque entre localizações via movements (location_id)."""
    arm = str(rule.get("armazem") or "").strip()
    origem = str(sug.get("origem") or "").strip()
    destino = str(sug.get("destino") or "").strip()
    pid = str(sug.get("produto_id") or "").strip()
    qtd = float(sug.get("qtd") or 0)
    if qtd <= 0:
        raise ValueError("qtd deve ser positiva")

    movements = inventory_mvp.load_movements()
    balances = inventory_mvp.load_balances()
    transit = inventory_mvp.load_transit()
    group_id = str(uuid.uuid4())[:8]
    nota = f"regra {rule.get('id')} ({rule.get('tipo')}): {rule.get('nome')}"

    atual = inventory_mvp.inventory_balance(
        arm, pid, balances=balances, location_id=origem
    )
    if atual < qtd:
        raise ValueError(
            f"estoque insuficiente em {origem} para produto {pid} (tem {atual:g}, pediu {qtd:g})"
        )

    r_out = inventory_mvp.inventory_apply_movement(
        "transfer_out", arm, pid, qtd,
        ref_tipo="wms_rule", ref_id=rule.get("id"), group_id=group_id,
        nota=nota, user_id=usuario,
        location_id=origem,
        movements=movements, balances=balances, transit=transit, persist=False,
    )
    r_in = inventory_mvp.inventory_apply_movement(
        "transfer_in", arm, pid, qtd,
        ref_tipo="wms_rule", ref_id=rule.get("id"), group_id=group_id,
        nota=nota, user_id=usuario,
        location_id=destino,
        movements=movements, balances=balances, transit=transit, persist=False,
    )
    inventory_mvp.save_movements(movements)
    inventory_mvp.save_balances(balances)
    inventory_mvp.save_transit(transit)
    return {"group_id": group_id, "movement_ids": [r_out["movement_id"], r_in["movement_id"]]}


# ──────────────────────── pull por demanda (cascata) ────────────────────────

def _encontrar_regra_pull(armazem, destino, produto_id):
    """Melhor regra pull ativa cujo destino == `destino` para o produto.

    Prioridade de escopo: produto específico > categoria > qualquer produto.
    """
    data = _load_raw()
    produto_id = str(produto_id or "").strip()
    candidatas = []
    for r in data.get("regras") or []:
        if not r.get("ativo") or r.get("tipo") != "pull":
            continue
        if str(r.get("armazem") or "").strip().upper() != str(armazem or "").strip().upper():
            continue
        if str(r.get("destino") or "").strip().upper() != str(destino or "").strip().upper():
            continue
        escopo = 0
        if r.get("produto_id") and str(r.get("produto_id")).strip() == produto_id:
            escopo = 3
        elif r.get("categoria"):
            cat = _produtos_catalogo().get(produto_id, {}).get("categoria", "")
            if str(r.get("categoria")).strip() == str(cat).strip():
                escopo = 2
            else:
                continue
        elif r.get("produto_id"):
            continue  # regra de outro produto
        else:
            escopo = 1  # qualquer produto
        candidatas.append((escopo, r))
    if not candidatas:
        return None
    candidatas.sort(key=lambda x: x[0], reverse=True)
    return candidatas[0][1]


def wms_rules_pull_demand(armazem, destino_final, itens):
    """Resolve uma demanda de trás para frente pela cadeia de regras pull.

    Ex.: rota em duas etapas Estoque → Envio → Cliente. A demanda no destino
    final (Cliente) é coberta primeiro por regra cujo destino é o Cliente
    (Envio → Cliente); o que faltar em Envio sobe para a regra seguinte
    (Estoque → Envio), e assim por diante.

    Retorna um plano de passos JÁ ORDENADO PARA EXECUÇÃO (separação upstream
    primeiro, envio por último) + resumo.

    itens: [{produto_id, qtd}]
    """
    arm = str(armazem or "").strip().upper()
    destino_final = str(destino_final or "").strip().upper()
    if not arm or not destino_final:
        raise ValueError("armazem e destino obrigatórios")

    balances = inventory_mvp.load_balances()
    passos = []  # ordem de criação (downstream primeiro)
    nao_resolvido = []

    for item in itens or []:
        pid = str(item.get("produto_id") or item.get("id") or "").strip()
        try:
            qtd = float(item.get("qtd") or item.get("quantidade") or 0)
        except (TypeError, ValueError):
            raise ValueError("qtd da demanda deve ser número") from None
        if not pid or qtd <= 0:
            continue

        falta = qtd
        destino = destino_final
        # estoque já disponível no destino final cobre parte da demanda
        disp = _saldo(arm, pid, destino_final, balances)
        falta -= min(disp, falta)

        visitados = set()
        cadeia = []
        while falta > 0:
            if destino in visitados:
                break
            visitados.add(destino)
            regra = _encontrar_regra_pull(arm, destino, pid)
            if not regra:
                break
            origem = str(regra.get("origem") or "").strip().upper()
            if not origem or origem == destino:
                break
            disp_origem = _saldo(arm, pid, origem, balances)
            mover = min(falta, disp_origem)
            if mover > 0:
                etapa = "envio" if destino == destino_final else "separacao"
                cadeia.append({
                    "origem": origem,
                    "destino": destino,
                    "produto_id": pid,
                    "produto": _produtos_catalogo().get(pid, {}).get("nome") or pid,
                    "qtd": mover,
                    "etapa": etapa,
                    "regra_id": regra.get("id"),
                    "regra_nome": regra.get("nome"),
                    "modo_aplicar": regra.get("modo_aplicar") or "operacao",
                })
                falta -= mover
            if falta <= 0:
                break
            destino = origem  # sobe um nível na cadeia

        if falta > 0:
            nao_resolvido.append({
                "produto_id": pid,
                "produto": _produtos_catalogo().get(pid, {}).get("nome") or pid,
                "falta": falta,
                "destino": destino,
            })
        # executa na ordem inversa: upstream (separação) primeiro
        passos.extend(reversed(cadeia))

    resumo = {
        "passos": len(passos),
        "separacao": sum(1 for p in passos if p["etapa"] == "separacao"),
        "envio": sum(1 for p in passos if p["etapa"] == "envio"),
        "nao_resolvido": len(nao_resolvido),
    }
    return {
        "destino_final": destino_final,
        "armazem": arm,
        "passos": passos,
        "nao_resolvido": nao_resolvido,
        "resumo": resumo,
        "resolvido_em": _now(),
    }


def wms_rules_pull_demand_apply(armazem, destino_final, itens, usuario=""):
    """Resolve a demanda e materializa cada passo como operação WMS
    (ou transferência direta, conforme o modo da regra), na ordem de execução:
    separação (upstream) primeiro, envio por último.
    """
    plano = wms_rules_pull_demand(armazem, destino_final, itens)
    aplicados = []
    pulados = []
    uid = uuid.uuid4().hex[:6]
    for i, passo in enumerate(plano["passos"], start=1):
        try:
            if passo.get("modo_aplicar") == "direto":
                regra = get_regra(passo.get("regra_id"))
                if not regra:
                    raise ValueError("regra não encontrada")
                res = _transfer_direto(regra, passo, usuario=usuario)
                aplicados.append({**passo, "resultado": res})
            else:
                op = wms_operations.create_operacao(
                    {
                        "id": f"OP-PULL-{uid}-{i:02d}",
                        "tipo": "TRF-INT",
                        "armazem": armazem,
                        "prioridade": "alta" if passo.get("etapa") == "envio" else "normal",
                        "documento_tipo": "DEMANDA",
                        "documento_ref": destino_final,
                        "observacao": (
                            f"pull demanda: {passo.get('regra_nome')} — {passo.get('etapa')}"
                        ),
                        "origem": f"demanda:{passo.get('etapa')}",
                        "linhas": [{
                            "produto_id": passo.get("produto_id"),
                            "produto": passo.get("produto"),
                            "qtd": passo.get("qtd"),
                            "loc_origem": passo.get("origem"),
                            "loc_destino": passo.get("destino"),
                        }],
                    },
                    usuario=usuario,
                )
                aplicados.append({**passo, "resultado": {"operacao_id": op.get("id")}})
        except ValueError as e:
            pulados.append({**passo, "motivo": str(e)})

    return {
        **plano,
        "aplicados": aplicados,
        "pulados": pulados,
        "resumo": {
            **plano["resumo"],
            "aplicados": len(aplicados),
            "pulados": len(pulados),
        },
    }


def wms_rules_apply(regra_ids=None, armazem=None, usuario=""):
    """Materializa as sugestões atuais.

    - modo 'operacao': cria operação WMS (TRF-INT) para o operador executar;
    - modo 'direto': executa a transferência de estoque imediatamente.
    Se regra_ids for informado, aplica só as sugestões dessas regras.
    """
    result = wms_rules_evaluate(armazem=armazem)
    sugestoes = result["sugestoes"]
    if regra_ids:
        wanted = {str(x).strip().upper() for x in regra_ids}
        sugestoes = [s for s in sugestoes if str(s.get("regra_id") or "").upper() in wanted]

    aplicadas = []
    puladas = []
    data = _load_raw()

    for sug in sugestoes:
        if sug.get("status") not in ("ok", "parcial") or not sug.get("qtd"):
            puladas.append({**sug, "motivo": f"status '{sug.get('status')}'"})
            continue
        rule = get_regra(sug.get("regra_id"))
        if not rule:
            puladas.append({**sug, "motivo": "regra não encontrada"})
            continue
        try:
            if rule.get("modo_aplicar") == "direto":
                res = _transfer_direto(rule, sug, usuario=usuario)
                aplicadas.append({**sug, "resultado": res})
            else:
                op = wms_operations.create_operacao(
                    {
                        "id": f"OP-REGRA-{sug['regra_id']}-{uuid.uuid4().hex[:6]}",
                        "tipo": "TRF-INT",
                        "armazem": rule.get("armazem"),
                        "prioridade": rule.get("prioridade"),
                        "documento_tipo": "REGRA",
                        "documento_ref": sug.get("regra_id"),
                        "observacao": f"{rule.get('nome')} — {sug.get('observacao')}",
                        "origem": f"regra:{sug.get('tipo')}",
                        "linhas": [{
                            "produto_id": sug.get("produto_id"),
                            "produto": sug.get("produto"),
                            "qtd": sug.get("qtd"),
                            "loc_origem": sug.get("origem"),
                            "loc_destino": sug.get("destino"),
                        }],
                    },
                    usuario=usuario,
                )
                aplicadas.append({**sug, "resultado": {"operacao_id": op.get("id")}})
        except ValueError as e:
            puladas.append({**sug, "motivo": str(e)})

    # registra avaliação nas regras envolvidas
    ids = {s.get("regra_id") for s in sugestoes}
    for i, r in enumerate(data.get("regras") or []):
        if r.get("id") in ids:
            r["ultima_avaliacao"] = result["avaliado_em"]
            r["ultimo_resultado"] = (
                f"{len(aplicadas)} aplicada(s), {len(puladas)} pulada(s) em {result['avaliado_em']}"
            )
            r["atualizado_em"] = _now()
            data["regras"][i] = r
    _save(data)

    return {
        "aplicadas": aplicadas,
        "puladas": puladas,
        "resumo": {
            "total_sugestoes": len(sugestoes),
            "aplicadas": len(aplicadas),
            "puladas": len(puladas),
        },
        "avaliado_em": result["avaliado_em"],
    }
