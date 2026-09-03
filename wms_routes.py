"""
WMS — Rotas (coleção de regras push/pull) RFC-9013 MVP.

Uma rota é uma sequência nomeada de localizações (etapas) que representa um
fluxo dentro do armazém segundo uma necessidade de negócio:

- armazenagem:           Recebimento → Qualidade → Armazenagem
- qualidade:             fluxo de inspeção / controle de qualidade
- pos_venda:             pós-venda / reparo
- devolucao_fornecedor:  devoluções a fornecedores
- fabricacao:            cadeia de fabricação de produtos
- aluguel:               ciclo de locação (com devolução automatizada)

Recursos:
- Config "rotas_multiplas_etapas" (Configuração → Definições → Estoque)
  libera rotas com mais de 2 etapas.
- Locais padrão por produto: onde o produto costuma ficar.
- Gerar regras: cria regras pull entre etapas consecutivas da rota.
- Devolução de aluguel: gera movimentações automáticas de retorno.

Fonte: dados/wms_routes.json
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

import settings_store
import wms_locations
import wms_operations
import wms_rules

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_routes.json")
DATA_FILE = os.path.join(BASE_DIR, "dados", "wms_routes.json")

ROUTE_TYPES = {
    "armazenagem": "Armazenagem",
    "qualidade": "Controle de qualidade",
    "pos_venda": "Pós-venda",
    "devolucao_fornecedor": "Devolução a fornecedor",
    "fabricacao": "Cadeia de fabricação",
    "aluguel": "Aluguel / locação",
}

PAPEIS = {
    "recebimento": "Recebimento",
    "qualidade": "Qualidade / inspeção",
    "armazenagem": "Armazenagem",
    "picking": "Picking",
    "expedicao": "Expedição",
    "devolucao": "Devolução",
    "producao": "Produção",
    "cliente": "Cliente (virtual)",
    "outro": "Outro",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load_raw():
    if not os.path.exists(DATA_FILE):
        return _empty()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return _empty()
    if not isinstance(data.get("rotas"), list):
        data["rotas"] = []
    if data.get("seq") is None:
        data["seq"] = len(data["rotas"])
    if not isinstance(data.get("locais_padrao"), dict):
        data["locais_padrao"] = {}
    return data


def _empty():
    return {"seq": 0, "rotas": [], "locais_padrao": {}, "atualizado_em": _now(), "total": 0}


def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE) or ".", exist_ok=True)
    data["atualizado_em"] = _now()
    data["total"] = len(data.get("rotas") or [])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_id(data):
    seq = int(data.get("seq") or 0) + 1
    data["seq"] = seq
    return f"RT-{seq:02d}"


def _hist(rota, usuario="", nota=""):
    hist = list(rota.get("historico") or [])
    hist.append({
        "em": _now(),
        "usuario": str(usuario or "").strip(),
        "nota": str(nota or "").strip(),
    })
    return hist


def _norm_tipo(val):
    t = str(val or "").strip().lower()
    if t not in ROUTE_TYPES:
        raise ValueError("tipo deve ser: " + ", ".join(ROUTE_TYPES))
    return t


def _norm_etapas(body, existing=None):
    raw = body.get("etapas") if "etapas" in body else (existing or {}).get("etapas")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("etapas deve ser uma lista")
    out = []
    vistos = set()
    for i, item in enumerate(raw, start=1):
        if isinstance(item, str):
            loc = item.strip().upper()
            papel = ""
        elif isinstance(item, dict):
            loc = str(item.get("localizacao") or item.get("loc") or "").strip().upper()
            papel = str(item.get("papel") or "").strip()
        else:
            continue
        if not loc:
            raise ValueError(f"etapa {i}: localização obrigatória")
        if loc in vistos:
            raise ValueError(f"etapa {i}: localização {loc} repetida na rota")
        if not wms_locations.get_localizacao(loc):
            raise ValueError(f"etapa {i}: localização {loc} não encontrada")
        vistos.add(loc)
        out.append({"ordem": i, "localizacao": loc, "papel": papel})
    return out


def _opt_str(body, existing, key, default=""):
    if key in body:
        return str(body.get(key) or "").strip()
    return str((existing or {}).get(key) or default).strip()


def _build_row(payload, existing=None):
    body = payload if isinstance(payload, dict) else {}
    existing = existing or {}
    rid = str(existing.get("id") or body.get("id") or "").strip().upper()
    if not rid:
        raise ValueError("id obrigatório")

    tipo = _norm_tipo(
        body.get("tipo") if body.get("tipo") is not None else existing.get("tipo") or "armazenagem"
    )
    armazem = _opt_str(body, existing, "armazem", "DC-01").upper()
    if not armazem:
        raise ValueError("armazém obrigatório")
    etapas = _norm_etapas(body, existing)
    if not etapas:
        raise ValueError("informe ao menos uma etapa (localização)")

    return {
        "id": rid,
        "nome": _opt_str(body, existing, "nome") or f"Rota {rid}",
        "tipo": tipo,
        "armazem": armazem,
        "produto_id": _opt_str(body, existing, "produto_id"),
        "categoria": _opt_str(body, existing, "categoria"),
        "descricao": _opt_str(body, existing, "descricao"),
        "etapas": etapas,
        "ativo": bool(body.get("ativo") if "ativo" in body else existing.get("ativo", True)),
        "criado_em": existing.get("criado_em") or _now(),
        "atualizado_em": _now(),
        "historico": _hist(existing, nota="criação/edição"),
    }


def config_rotas():
    """Lê a configuração de rotas (Configuração → Definições → Estoque)."""
    multi = bool(settings_store.get("estoque", "rotas_multiplas_etapas", False))
    return {
        "rotas_multiplas_etapas": multi,
        "max_etapas": None if multi else 2,
    }


def meta():
    data = _load_raw()
    return {
        "total": len(data.get("rotas") or []),
        "tipos": ROUTE_TYPES,
        "papeis": PAPEIS,
        "config": config_rotas(),
        "locais_padrao": len(data.get("locais_padrao") or {}),
        "atualizado_em": data.get("atualizado_em"),
    }


def list_rotas(q=None, tipo=None, ativo=None):
    data = _load_raw()
    rows = []
    for r in data.get("rotas") or []:
        if q:
            blob = f"{r.get('id')} {r.get('nome')} {r.get('tipo')} {r.get('armazem')}".lower()
            if str(q).strip().lower() not in blob:
                continue
        if tipo and r.get("tipo") != str(tipo).strip().lower():
            continue
        if ativo is not None:
            want = str(ativo).strip().lower() in ("1", "true", "sim", "on")
            if bool(r.get("ativo")) != want:
                continue
        rows.append(r)
    return {"rotas": rows, "total": len(rows), "config": config_rotas()}


def get_rota(rid):
    data = _load_raw()
    key = str(rid or "").strip().upper()
    for r in data.get("rotas") or []:
        if str(r.get("id") or "").upper() == key:
            return r
    return None


def create_rota(payload):
    data = _load_raw()
    body = dict(payload or {})
    rid = str(body.get("id") or "").strip().upper()
    if not rid:
        rid = _next_id(data)
        body["id"] = rid
    for r in data.get("rotas") or []:
        if str(r.get("id") or "").upper() == rid:
            raise ValueError(f"rota {rid} já existe")
    row = _build_row(body)
    _validar_multietapas(row)
    data["rotas"].append(row)
    _save(data)
    return row


def _validar_multietapas(rota):
    cfg = config_rotas()
    n = len(rota.get("etapas") or [])
    max_etapas = cfg.get("max_etapas")
    if max_etapas is not None and n > max_etapas:
        raise ValueError(
            f"rota com {n} etapas exige 'Rotas com várias etapas' ativo "
            "(Configuração → Definições → Estoque)"
        )


def update_rota(rid, payload):
    data = _load_raw()
    key = str(rid or "").strip().upper()
    for i, r in enumerate(data.get("rotas") or []):
        if str(r.get("id") or "").upper() == key:
            merged = {**r, **(payload or {})}
            merged["id"] = r.get("id")
            row = _build_row(merged, existing=r)
            _validar_multietapas(row)
            data["rotas"][i] = row
            _save(data)
            return row
    raise ValueError("rota não encontrada")


def delete_rota(rid):
    data = _load_raw()
    key = str(rid or "").strip().upper()
    for i, r in enumerate(data.get("rotas") or []):
        if str(r.get("id") or "").upper() == key:
            data["rotas"].pop(i)
            _save(data)
            return True
    raise ValueError("rota não encontrada")


def set_ativo(rid, ativo, motivo=None):
    data = _load_raw()
    key = str(rid or "").strip().upper()
    for i, r in enumerate(data.get("rotas") or []):
        if str(r.get("id") or "").upper() == key:
            r["ativo"] = bool(ativo)
            r["atualizado_em"] = _now()
            r["historico"] = _hist(
                r,
                nota=f"{'ativada' if r['ativo'] else 'pausada'}"
                + (f" — {motivo}" if motivo else ""),
            )
            data["rotas"][i] = r
            _save(data)
            return r
    raise ValueError("rota não encontrada")


# ───────────────────────────── locais padrão por produto ─────────────────────────────

def list_locais_padrao(produto_id=None):
    data = _load_raw()
    mapa = data.get("locais_padrao") or {}
    if produto_id:
        pid = str(produto_id).strip()
        return {"produto_id": pid, "padrao": mapa.get(pid) or {}}
    return {"locais": mapa, "total": len(mapa)}


def set_local_padrao(produto_id, armazem, localizacao):
    pid = str(produto_id or "").strip()
    if not pid:
        raise ValueError("produto_id obrigatório")
    loc = str(localizacao or "").strip().upper()
    if not loc:
        raise ValueError("localização obrigatória")
    if not wms_locations.get_localizacao(loc):
        raise ValueError(f"localização {loc} não encontrada")
    arm = str(armazem or "").strip().upper() or "DC-01"
    data = _load_raw()
    data.setdefault("locais_padrao", {})[pid] = {"armazem": arm, "localizacao": loc}
    _save(data)
    return {"produto_id": pid, "padrao": data["locais_padrao"][pid]}


def delete_local_padrao(produto_id):
    pid = str(produto_id or "").strip()
    data = _load_raw()
    if pid in (data.get("locais_padrao") or {}):
        del data["locais_padrao"][pid]
        _save(data)
        return True
    raise ValueError("local padrão não encontrado")


# ───────────────────────────── gerar regras da rota ─────────────────────────────

def wms_routes_gerar_regras(rota_id, usuario=""):
    """Cria regras pull entre etapas consecutivas da rota.

    Rota [E1, E2, E3] → regras E1→E2 e E2→E3 (pull, mesma direção do fluxo).
    """
    rota = get_rota(rota_id)
    if not rota:
        raise ValueError("rota não encontrada")
    etapas = rota.get("etapas") or []
    if len(etapas) < 2:
        raise ValueError("rota precisa de ao menos 2 etapas para gerar regras")
    criadas = []
    for i in range(len(etapas) - 1):
        origem = etapas[i]["localizacao"]
        destino = etapas[i + 1]["localizacao"]
        payload = {
            "nome": f"{rota.get('nome')} · {origem} → {destino}",
            "tipo": "pull",
            "armazem": rota.get("armazem"),
            "origem": origem,
            "destino": destino,
            "produto_id": rota.get("produto_id") or "",
            "categoria": rota.get("categoria") or "",
            "nivel_min": 1,
            "qtd_reposicao": 1,
            "prioridade": "normal",
        }
        regra = wms_rules.create_regra(payload)
        criadas.append({"etapa": i + 1, "origem": origem, "destino": destino, "regra": regra})
    return {"rota_id": rota.get("id"), "criadas": criadas, "total": len(criadas)}


# ───────────────────────────── devolução de aluguel ─────────────────────────────

def wms_routes_devolucao_aluguel(armazem, produto_id, qtd, *, rota_id=None, local_atual=None, destino_final=None, usuario=""):
    """Gera movimentações automáticas de retorno de produto alugado.

    Usa uma rota ativa tipo 'aluguel' (ou a rota_id informada). O produto volta
    pela sequência de etapas da rota: cada par consecutivo gera uma operação
    TRF-INT (ou transferência direta) na ordem de execução.

    destino_final: localização sugerida para o fim da devolução. Se não for
    informada, usa o LOCAL PADRÃO do produto (locais_padrao) quando existir e
    ainda não fizer parte do trajeto.
    """
    arm = str(armazem or "").strip().upper() or "DC-01"
    pid = str(produto_id or "").strip()
    try:
        q = float(qtd or 0)
    except (TypeError, ValueError):
        raise ValueError("qtd deve ser número") from None
    if not pid or q <= 0:
        raise ValueError("produto_id e qtd > 0 obrigatórios")

    data = _load_raw()
    rota = None
    if rota_id:
        rota = get_rota(rota_id)
        if not rota:
            raise ValueError("rota não encontrada")
    else:
        for r in data.get("rotas") or []:
            if r.get("ativo") and r.get("tipo") == "aluguel" and str(r.get("armazem") or "").upper() == arm:
                rota = r
                break
        if not rota:
            raise ValueError("nenhuma rota ativa tipo 'aluguel' para o armazém " + arm)

    path = [e["localizacao"] for e in (rota.get("etapas") or [])]
    if local_atual:
        cur = str(local_atual).strip().upper()
        if cur and cur not in path:
            path = [cur] + path
    # destino final automático: informado ou local padrão do produto
    final = None
    if destino_final:
        final = str(destino_final).strip().upper()
        if not wms_locations.get_localizacao(final):
            raise ValueError(f"localização {final} não encontrada")
    else:
        padrao = list_locais_padrao(produto_id).get("padrao") or {}
        if padrao.get("localizacao"):
            final = str(padrao["localizacao"]).strip().upper()
    if final and final not in path:
        path.append(final)
    if len(path) < 2:
        raise ValueError("rota de aluguel precisa de ao menos 2 etapas")

    ts = int(datetime.now().timestamp()) % 1000000
    uid = uuid.uuid4().hex[:4]
    passos = []
    for i in range(len(path) - 1):
        origem, destino = path[i], path[i + 1]
        op = wms_operations.create_operacao(
            {
                "id": f"OP-RET-{ts:06d}-{uid}-{i + 1:02d}",
                "tipo": "TRF-INT",
                "armazem": arm,
                "prioridade": "alta",
                "documento_tipo": "ALUGUEL",
                "documento_ref": rota.get("id"),
                "observacao": f"devolução de aluguel: {rota.get('nome')} · {produto_id}",
                "origem": "rota:aluguel",
                "linhas": [{
                    "produto_id": pid,
                    "produto": pid,
                    "qtd": q,
                    "loc_origem": origem,
                    "loc_destino": destino,
                }],
            },
            usuario=usuario,
        )
        passos.append({
            "etapa": i + 1,
            "origem": origem,
            "destino": destino,
            "produto_id": pid,
            "qtd": q,
            "operacao_id": op.get("id"),
        })

    return {
        "rota_id": rota.get("id"),
        "rota_nome": rota.get("nome"),
        "produto_id": pid,
        "qtd": q,
        "passos": passos,
        "total": len(passos),
        "gerado_em": _now(),
    }
