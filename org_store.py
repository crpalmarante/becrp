"""
Organização + Estabelecimentos — fonte única (RFC unificação).

- data/organizacao.json     → tenant / grupo
- data/empresas.json        → estabelecimentos (identidade cadastral)
- data/estabelecimentos_fiscal.json → CSC / cert / série / ambiente (overlay)

dados/empresa.json = espelho legado para módulos SEFAZ que ainda leem o arquivo.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ORG_FILE = os.path.join(DATA_DIR, "organizacao.json")
EMPRESAS_FILE = os.path.join(DATA_DIR, "empresas.json")
FISCAL_FILE = os.path.join(DATA_DIR, "estabelecimentos_fiscal.json")
LEGACY_EMPRESA = os.path.join(BASE_DIR, "dados", "empresa.json")

# campos cadastrais do estabelecimento (não são “só fiscal”)
ESTAB_IDENTITY_KEYS = (
    "nome", "nome_razao", "nome_fantasia", "cnpj", "ie", "inscricao_est",
    "cidade", "municipio", "uf", "endereco", "cep", "telefone", "email",
    "cod_municipio", "ativo", "tipo",
    "default_price_list_id",
)

# overlay fiscal típico
FISCAL_KEYS = (
    "csc", "csc_id", "serie_nfce", "numero_nfce", "ambiente",
    "certificado", "cert_senha", "crt", "tipo_fiscal",
    "inscricao_mun", "cnae_prim_codigo", "cnae_prim_desc",
    "cnae_sec_codigos", "cnae_sec_desc", "chave_pix", "logo",
)


def _load(path, default):
    if not os.path.exists(path):
        return default() if callable(default) else default
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else (default() if callable(default) else default)


def _save(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def digits(val):
    return "".join(ch for ch in str(val or "") if ch.isdigit())


def load_organizacao():
    data = _load(ORG_FILE, lambda: {
        "id": "org",
        "nome": "Organização",
        "estabelecimento_padrao": "matriz",
    })
    if not data.get("estabelecimento_padrao"):
        data["estabelecimento_padrao"] = "matriz"
    return data


def save_organizacao(data):
    _save(ORG_FILE, data if isinstance(data, dict) else {})


def load_empresas():
    data = _load(EMPRESAS_FILE, dict)
    return data if isinstance(data, dict) else {}


def save_empresas(data):
    _save(EMPRESAS_FILE, data if isinstance(data, dict) else {})


def load_fiscal_store():
    data = _load(FISCAL_FILE, dict)
    return data if isinstance(data, dict) else {}


def save_fiscal_store(data):
    _save(FISCAL_FILE, data if isinstance(data, dict) else {})


def estabelecimento_padrao_id():
    org = load_organizacao()
    eid = str(org.get("estabelecimento_padrao") or "matriz").strip()
    empresas = load_empresas()
    if eid in empresas:
        return eid
    if "matriz" in empresas:
        return "matriz"
    return next(iter(empresas.keys()), "")


def resolve_empresa_fiscal(estabelecimento_id=None):
    """
    Emitente = estabelecimento (+ overlay fiscal).
    Sem depender de dados/empresa.json como fonte.
    """
    empresas = load_empresas()
    eid = str(estabelecimento_id or "").strip() or estabelecimento_padrao_id()
    estab = dict(empresas.get(eid, {}) or {})
    overlay = dict(load_fiscal_store().get(eid, {}) or {})

    out = {}
    # identidade
    razao = estab.get("nome_razao") or overlay.get("nome") or estab.get("nome") or ""
    fantasia = (
        estab.get("nome_fantasia")
        or overlay.get("nome_fantasia")
        or estab.get("nome")
        or razao
    )
    if razao:
        out["nome"] = razao
    if fantasia:
        out["nome_fantasia"] = fantasia
    cnpj = overlay.get("cnpj") or estab.get("cnpj")
    if cnpj:
        out["cnpj"] = digits(cnpj) or str(cnpj)
    ie = overlay.get("inscricao_est") or overlay.get("ie") or estab.get("ie") or estab.get("inscricao_est")
    if ie:
        out["inscricao_est"] = ie
        out["ie"] = ie
    municipio = overlay.get("municipio") or estab.get("municipio") or estab.get("cidade")
    if municipio:
        out["municipio"] = municipio
    if estab.get("cidade") and not out.get("municipio"):
        out["municipio"] = estab["cidade"]
    for key in ("endereco", "cep", "telefone", "email", "cod_municipio"):
        val = overlay.get(key) if overlay.get(key) not in (None, "") else estab.get(key)
        if val not in (None, ""):
            out[key] = val

    uf = overlay.get("uf") if overlay.get("uf") not in (None, "") else estab.get("uf")
    if uf not in (None, ""):
        out["uf"] = uf

    # overlay fiscal / demais
    for k, v in overlay.items():
        if v is None or v == "":
            continue
        if k == "cnpj":
            out[k] = digits(v) or out.get(k)
        elif k == "nome" and out.get("nome"):
            # já temos razão; overlay nome só se vazio
            continue
        else:
            out[k] = v

    out["estabelecimento_id"] = eid or None
    org = load_organizacao()
    out["organizacao_id"] = org.get("id")
    out["organizacao_nome"] = org.get("nome")
    return out


def load_empresa_fiscal():
    """Compat: emitente padrão = estabelecimento_padrao."""
    return resolve_empresa_fiscal(estabelecimento_padrao_id())


def sync_legacy_empresa_json(estabelecimento_id=None):
    """Espelho para SEFAZ/_get_empresa() — não é fonte da verdade."""
    emp = resolve_empresa_fiscal(estabelecimento_id)
    mirror = {k: v for k, v in emp.items() if k not in ("organizacao_id", "organizacao_nome")}
    mirror["_meta"] = {
        "deprecated": True,
        "nota": "ESPELHO — fonte = data/empresas.json + estabelecimentos_fiscal.json + organizacao.json",
        "synced_at": datetime.now().isoformat(timespec="seconds"),
        "estabelecimento_id": emp.get("estabelecimento_id"),
    }
    os.makedirs(os.path.dirname(LEGACY_EMPRESA), exist_ok=True)
    _save(LEGACY_EMPRESA, mirror)
    return mirror


def save_emitente_padrao(updates):
    """POST legado /api/admin/fiscal/empresa → grava no estabelecimento padrão."""
    eid = estabelecimento_padrao_id()
    return update_estabelecimento(eid, updates, also_fiscal=True)


def update_estabelecimento(eid, updates, also_fiscal=True):
    eid = str(eid or "").strip()
    if not eid:
        raise ValueError("estabelecimento_id obrigatório")
    empresas = load_empresas()
    if eid not in empresas:
        empresas[eid] = {"nome": eid, "ativo": True}
    estab = dict(empresas.get(eid) or {})
    fiscal = load_fiscal_store()
    overlay = dict(fiscal.get(eid) or {})

    body = updates if isinstance(updates, dict) else {}
    for key, val in body.items():
        if val is None:
            continue
        if key in ("ie",):
            estab["ie"] = val
            overlay["inscricao_est"] = val
            continue
        if key in ESTAB_IDENTITY_KEYS or key in ("nome_razao", "nome_fantasia"):
            if key == "cnpj":
                estab[key] = digits(val) or val
            elif key == "nome" and not estab.get("nome_razao"):
                # nome curto da loja vs razão
                estab["nome"] = val
            else:
                estab[key] = val
            if key in ("nome_razao", "cnpj", "endereco", "cep", "telefone", "email", "cod_municipio", "municipio"):
                overlay[key if key != "nome_razao" else "nome"] = val if key != "nome_razao" else val
            if key == "cidade" and not body.get("municipio"):
                overlay.setdefault("municipio", val)
            continue
        if also_fiscal and (key in FISCAL_KEYS or key in ("serie_nfce", "numero_nfce", "ambiente", "crt")):
            if key == "crt":
                try:
                    overlay[key] = int(val)
                except (TypeError, ValueError):
                    overlay[key] = val
            elif key == "cnpj":
                overlay[key] = digits(val) or val
            else:
                overlay[key] = val
            continue
        # demais campos vão para overlay se also_fiscal
        if also_fiscal:
            overlay[key] = val

    empresas[eid] = estab
    fiscal[eid] = overlay
    save_empresas(empresas)
    save_fiscal_store(fiscal)
    if eid == estabelecimento_padrao_id():
        sync_legacy_empresa_json(eid)
    return resolve_empresa_fiscal(eid)


def migrate_if_needed(force=False):
    """
    Une empresa.json legado + empresas magras + fiscal.
    Idempotente.
    """
    org = load_organizacao()
    if org.get("unificado") and not force:
        # ainda garante espelho
        sync_legacy_empresa_json()
        return {"migrated": False, "reason": "já unificado"}

    legacy = _load(LEGACY_EMPRESA, dict)
    empresas = load_empresas()
    fiscal = load_fiscal_store()

    if not empresas:
        empresas = {
            "matriz": {"nome": "Matriz", "ativo": True, "tipo": "matriz"},
        }

    # matriz recebe identidade Fabieli / legado
    matriz = dict(empresas.get("matriz") or {"nome": "Matriz", "ativo": True, "tipo": "matriz"})
    if legacy:
        if legacy.get("nome"):
            matriz["nome_razao"] = legacy.get("nome")
        if legacy.get("nome_fantasia"):
            matriz["nome_fantasia"] = legacy.get("nome_fantasia")
        if legacy.get("cnpj"):
            matriz["cnpj"] = digits(legacy.get("cnpj")) or legacy.get("cnpj")
        if legacy.get("inscricao_est") or legacy.get("ie"):
            matriz["ie"] = legacy.get("inscricao_est") or legacy.get("ie")
        if legacy.get("municipio"):
            matriz["cidade"] = legacy.get("municipio")
            matriz["municipio"] = legacy.get("municipio")
        if legacy.get("endereco"):
            matriz["endereco"] = legacy.get("endereco")
        if legacy.get("cep"):
            matriz["cep"] = legacy.get("cep")
        if legacy.get("telefone"):
            matriz["telefone"] = legacy.get("telefone")
        if legacy.get("email"):
            matriz["email"] = legacy.get("email")
        if legacy.get("cod_municipio"):
            matriz["cod_municipio"] = legacy.get("cod_municipio")
        # UF: preferir string se legado for código IBGE
        uf = legacy.get("uf")
        if uf is not None:
            matriz["uf"] = uf
        matriz["nome"] = matriz.get("nome") or "Matriz"
        matriz["tipo"] = "matriz"
        matriz["ativo"] = True

        # fiscal overlay matriz: preencher o que faltar a partir do legado
        ov = dict(fiscal.get("matriz") or {})
        for k in FISCAL_KEYS:
            if k in legacy and legacy[k] not in (None, "") and ov.get(k) in (None, ""):
                ov[k] = legacy[k]
        for k in ("nome", "nome_fantasia", "cnpj", "inscricao_est", "endereco", "cep",
                  "telefone", "email", "cod_municipio", "municipio", "uf", "crt"):
            if k in legacy and legacy[k] not in (None, "") and ov.get(k) in (None, ""):
                ov[k] = legacy[k]
        fiscal["matriz"] = ov

    empresas["matriz"] = matriz

    # filiais: marcar tipo
    for eid, e in list(empresas.items()):
        if eid == "matriz":
            continue
        e = dict(e or {})
        e.setdefault("tipo", "filial")
        e.setdefault("ativo", True)
        empresas[eid] = e
        fiscal.setdefault(eid, fiscal.get(eid) or {
            "csc_id": "1", "csc": "", "serie_nfce": 1, "numero_nfce": 1, "ambiente": 2,
        })

    org_nome = (
        (legacy.get("nome_fantasia") if legacy else None)
        or (legacy.get("nome") if legacy else None)
        or "Organização BECRP"
    )
    org = {
        "id": "org",
        "nome": org_nome if "FABIELI" in str(org_nome).upper() or legacy else "Organização BECRP",
        "estabelecimento_padrao": "matriz",
        "unificado": True,
        "unificado_em": datetime.now().isoformat(timespec="seconds"),
    }
    if legacy and legacy.get("nome"):
        org["nome"] = legacy.get("nome_fantasia") or legacy.get("nome")

    save_organizacao(org)
    save_empresas(empresas)
    save_fiscal_store(fiscal)
    sync_legacy_empresa_json("matriz")
    return {"migrated": True, "estabelecimentos": list(empresas.keys()), "org": org.get("nome")}


# bootstrap
_BOOT = migrate_if_needed()
