"""CobolBridge — Ponte Python para programas COBOL do FiscalBrasil ERP"""

import json
import os
import re
import subprocess
import sys
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COBOL_BIN = os.path.join(BASE_DIR, "cobol", "bin")
COBOL_SRC = os.path.join(BASE_DIR, "cobol", "programs")
DADOS_DIR = os.path.join(BASE_DIR, "dados")

os.makedirs(COBOL_BIN, exist_ok=True)
os.makedirs(DADOS_DIR, exist_ok=True)


def _norm_ncm(value: str) -> str:
    """NCM no COBOL é PIC X(8): gravar só dígitos (ex.: 10063021)."""
    return re.sub(r"\D", "", value or "")[:8]

def _env():
    env = os.environ.copy()
    env["COB_LIBRARY_PATH"] = COBOL_SRC
    return env

def _run(program, env_vars):
    exe = os.path.join(COBOL_BIN, program)
    if not os.path.exists(exe):
        src = os.path.join(COBOL_SRC, program + ".cbl")
        if os.path.exists(src):
            subprocess.run(
                ["cobc", "-x", src, "-o", exe],
                cwd=BASE_DIR, capture_output=True
            )
        else:
            raise FileNotFoundError(f"COBOL program not found: {program}")
    env = _env()
    env.update(env_vars)
    r = subprocess.run([exe], env=env, cwd=BASE_DIR,
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0 and r.stderr:
        for line in r.stderr.splitlines():
            if "ERRO:" in line:
                raise Exception(line.strip())
    return r.stdout, r.stderr

def _compile_if_needed(program):
    exe = os.path.join(COBOL_BIN, program)
    src = os.path.join(COBOL_SRC, program + ".cbl")
    if not os.path.exists(exe) and os.path.exists(src):
        subprocess.run(["cobc", "-x", src, "-o", exe],
                       cwd=BASE_DIR, capture_output=True)

# ── Fornecedores ────────────────────────────────────────────

def fornecedores_listar():
    out, _ = _run("gerir_fornecedores", {"ACAO": "listar"})
    try:
        data = json.loads(out)
        return data.get("fornecedores", [])
    except json.JSONDecodeError:
        return []

def fornecedores_incluir(dados):
    env = {
        "ACAO": "incluir",
        "NOME": dados.get("nome", ""),
        "CNPJ": dados.get("cnpj", ""),
        "ENDERECO": dados.get("endereco", ""),
        "TELEFONE": dados.get("telefone", ""),
        "EMAIL": dados.get("email", ""),
        "IE": dados.get("ie", ""),
        "INSCRICAO_MUN": dados.get("inscricao_mun", ""),
    }
    out, _ = _run("gerir_fornecedores", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao criar fornecedor: " + out.strip())

def fornecedores_alterar(id_val, dados):
    env = {
        "ACAO": "alterar",
        "ID": str(id_val),
        "NOME": dados.get("nome", ""),
        "CNPJ": dados.get("cnpj", ""),
        "ENDERECO": dados.get("endereco", ""),
        "TELEFONE": dados.get("telefone", ""),
        "EMAIL": dados.get("email", ""),
        "IE": dados.get("ie", ""),
        "INSCRICAO_MUN": dados.get("inscricao_mun", ""),
    }
    out, _ = _run("gerir_fornecedores", env)
    return "OK" in out

def fornecedores_excluir(id_val):
    out, _ = _run("gerir_fornecedores", {"ACAO": "excluir", "ID": str(id_val)})
    return "OK" in out

# ── Produtos ────────────────────────────────────────────────

PRODUTOS_EXTRA_FILE = os.path.join(DADOS_DIR, "produtos_extra.json")

# Campos do .dat COBOL — não sobrescrever ao mesclar extras
_PRODUTO_CORE_KEYS = {
    "id", "nome", "preco", "preco_custo", "stock", "margem",
    "codigo_barras", "categoria", "sub_categoria", "unidade", "ncm",
    "fornecedor", "localizacao", "filial_id", "cst", "cfop",
    "icms_alq", "servico", "iss_alq", "cod_serv_mun", "ativo",
}

_PRODUTO_EXTRA_KEYS = {
    "nome_reduzido", "marca", "fabricante", "unidade_compra", "tipo", "modelo",
    "tags", "descricao", "preco_promo", "preco_min", "preco_max", "comissao",
    "modo_preco", "despesa_fixa", "despesa_pct", "custo_base", "variacoes",
    "estoque_min", "estoque_max", "cest", "origem",
    "vendavel", "compravel", "pdv", "usa_balanca",
    "controla_estoque", "estoque_negativo", "controla_lote", "controla_serie",
    "compra_ok", "venda_ok", "fracionado", "por_peso",
    "qtd_min_compra", "qtd_padrao", "lead_time", "garantia",
    "peso_liq", "peso_bruto", "tipo_embalagem", "embalagem_outro", "qtd_por_embalagem",
    "altura", "largura", "comprimento", "volume",
    "altura_emb", "largura_emb", "comprimento_emb", "volume_emb", "foto",
}


def _load_produtos_extra():
    if not os.path.exists(PRODUTOS_EXTRA_FILE):
        return {}
    try:
        with open(PRODUTOS_EXTRA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_produtos_extra(data):
    with open(PRODUTOS_EXTRA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def produtos_extra_get(id_val):
    return dict(_load_produtos_extra().get(str(id_val), {}) or {})


def produtos_extra_set(id_val, extra):
    if not isinstance(extra, dict):
        return
    store = _load_produtos_extra()
    cleaned = {k: v for k, v in extra.items() if k in _PRODUTO_EXTRA_KEYS or k == "ativo"}
    store[str(id_val)] = cleaned
    _save_produtos_extra(store)


def produtos_extra_delete(id_val):
    store = _load_produtos_extra()
    if str(id_val) in store:
        del store[str(id_val)]
        _save_produtos_extra(store)


def _extract_produto_extra(dados):
    """Puxa bloco extra do body da API (chave 'extra' ou campos soltos)."""
    if not isinstance(dados, dict):
        return {}
    if isinstance(dados.get("extra"), dict):
        base = dict(dados["extra"])
    else:
        base = {}
    for k in _PRODUTO_EXTRA_KEYS:
        if k in dados and k not in base:
            base[k] = dados[k]
    if "ativo" in dados and isinstance(dados["ativo"], bool):
        base["ativo"] = dados["ativo"]
    return base


def produtos_extra_import(extras_map, overwrite=False):
    """Importa mapa id->extra (ex.: migração do localStorage)."""
    if not isinstance(extras_map, dict):
        return 0
    store = _load_produtos_extra()
    n = 0
    for pid, extra in extras_map.items():
        if not isinstance(extra, dict):
            continue
        key = str(pid)
        if key in store and not overwrite:
            continue
        cleaned = {k: v for k, v in extra.items() if k in _PRODUTO_EXTRA_KEYS or k == "ativo"}
        store[key] = cleaned
        n += 1
    if n:
        _save_produtos_extra(store)
    return n


def _merge_produto_extra(produto, extra):
    if not extra:
        return produto
    out = dict(produto)
    for k, v in extra.items():
        if k in _PRODUTO_CORE_KEYS and k != "ativo":
            continue
        out[k] = v
    return out


def produtos_listar():
    _run("batch_json_produtos", {})
    json_path = os.path.join(DADOS_DIR, "produtos.json")
    if not os.path.exists(json_path):
        return []
    with open(json_path, "r") as f:
        data = json.load(f)
    produtos = data.get("produtos", [])
    extras = _load_produtos_extra()
    return [
        _merge_produto_extra(p, extras.get(str(p.get("id")), {}))
        for p in produtos
    ]

def produtos_incluir(dados):
    extra = _extract_produto_extra(dados)
    env = {
        "ACAO": "incluir",
        "NOME": dados.get("nome", ""),
        "PRECO": str(dados.get("preco", 0)),
        "PRECO_CUSTO": str(dados.get("preco_custo", 0)),
        "STOCK": str(dados.get("stock", 0)),
        "MARGEM": str(dados.get("margem", 0)),
        "CODIGO_BARRAS": dados.get("codigo_barras", ""),
        "CATEGORIA": dados.get("categoria", ""),
        "SUB_CATEGORIA": dados.get("sub_categoria", "") or dados.get("categoria", ""),
        "UNIDADE": dados.get("unidade", "UN"),
        "NCM": _norm_ncm(dados.get("ncm", "")),
        "FORNECEDOR": dados.get("fornecedor", ""),
        "LOCALIZACAO": dados.get("localizacao", ""),
        "FILIAL_ID": str(dados.get("filial_id", 0)),
        "CST": dados.get("cst", ""),
        "CFOP": dados.get("cfop", ""),
        "ICMS_ALQ": str(dados.get("icms_alq", 0)),
        "SERVICO": dados.get("servico", "N"),
        "ISS_ALQ": str(dados.get("iss_alq", 0)),
        "COD_SERV_MUN": dados.get("cod_serv_mun", ""),
    }
    out, _ = _run("cadastrar_produto", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            pid = int(line)
            if extra:
                produtos_extra_set(pid, extra)
            return pid
    raise Exception("Erro ao criar produto: " + out.strip())

def produtos_alterar(id_val, dados):
    extra = _extract_produto_extra(dados)
    env = {
        "ACAO": "alterar",
        "ID": str(id_val),
        "NOME": dados.get("nome", ""),
        "PRECO": str(dados.get("preco", "")),
        "PRECO_CUSTO": str(dados.get("preco_custo", "")),
        "STOCK": str(dados.get("stock", "")),
        "MARGEM": str(dados.get("margem", "")),
        "CODIGO_BARRAS": dados.get("codigo_barras", ""),
        "CATEGORIA": dados.get("categoria", ""),
        "SUB_CATEGORIA": dados.get("sub_categoria", "") or dados.get("categoria", ""),
        "UNIDADE": dados.get("unidade", ""),
        "NCM": _norm_ncm(dados.get("ncm", "")),
        "FORNECEDOR": dados.get("fornecedor", ""),
        "LOCALIZACAO": dados.get("localizacao", ""),
        "FILIAL_ID": str(dados.get("filial_id", "")),
        "CST": dados.get("cst", ""),
        "CFOP": dados.get("cfop", ""),
        "ICMS_ALQ": str(dados.get("icms_alq", "")),
        "SERVICO": dados.get("servico", ""),
        "ISS_ALQ": str(dados.get("iss_alq", "")),
        "COD_SERV_MUN": dados.get("cod_serv_mun", ""),
    }
    out, _ = _run("cadastrar_produto", env)
    ok = "OK" in out
    if ok and extra:
        produtos_extra_set(id_val, extra)
    return ok

def produtos_excluir(id_val):
    out, _ = _run("cadastrar_produto", {"ACAO": "excluir", "ID": str(id_val)})
    ok = "OK" in out
    if ok:
        produtos_extra_delete(id_val)
    return ok

# ── CT-e ──────────────────────────────────────────────────

def cte_listar():
    out, _ = _run("gerir_cte", {"ACAO": "listar"})
    try:
        data = json.loads(out)
        return data.get("cte", [])
    except json.JSONDecodeError:
        return []

def cte_incluir(dados):
    env = {"ACAO": "incluir",
           "NUMERO": str(dados.get("numero", 0)),
           "SERIE": str(dados.get("serie", 1)),
           "CHAVE": dados.get("chave", ""),
           "CNPJ_EMIT": dados.get("cnpj_emit", ""),
           "IE_EMIT": dados.get("ie_emit", ""),
           "NOME_EMIT": dados.get("nome_emit", ""),
           "CNPJ_DEST": dados.get("cnpj_dest", ""),
           "NOME_DEST": dados.get("nome_dest", ""),
           "MUN_INI": dados.get("mun_ini", ""),
           "UF_INI": dados.get("uf_ini", ""),
           "MUN_FIM": dados.get("mun_fim", ""),
           "UF_FIM": dados.get("uf_fim", ""),
           "VALOR": str(dados.get("valor", 0)),
           "CFOP": dados.get("cfop", ""),
           "STATUS": dados.get("status", ""),
           "PROTOCOLO": dados.get("protocolo", ""),
           "DATA_EMISSAO": dados.get("data_emissao", "")}
    out, _ = _run("gerir_cte", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao criar CT-e: " + out.strip())

def cte_alterar(id_val, dados):
    env = {"ACAO": "alterar", "ID": str(id_val)}
    for k in ("numero","serie","chave","cnpj_emit","ie_emit","nome_emit",
              "cnpj_dest","nome_dest","mun_ini","uf_ini","mun_fim","uf_fim",
              "valor","cfop","status","protocolo","data_emissao"):
        v = dados.get(k)
        if v is not None:
            env[k.upper()] = str(v)
    out, _ = _run("gerir_cte", env)
    return "OK" in out

def cte_excluir(id_val):
    out, _ = _run("gerir_cte", {"ACAO": "excluir", "ID": str(id_val)})
    return "OK" in out

# ── MDF-e ─────────────────────────────────────────────────

def mdfe_listar():
    out, _ = _run("gerir_mdfe", {"ACAO": "listar"})
    try:
        data = json.loads(out)
        return data.get("mdfe", [])
    except json.JSONDecodeError:
        return []

def mdfe_incluir(dados):
    env = {"ACAO": "incluir",
           "NUMERO": str(dados.get("numero", 0)),
           "SERIE": str(dados.get("serie", 1)),
           "CHAVE": dados.get("chave", ""),
           "CNPJ_EMIT": dados.get("cnpj_emit", ""),
           "NOME_EMIT": dados.get("nome_emit", ""),
           "MODAL": dados.get("modal", "1"),
           "UF_INI": dados.get("uf_ini", ""),
           "UF_FIM": dados.get("uf_fim", ""),
           "MUN_INI": dados.get("mun_ini", ""),
           "MUN_FIM": dados.get("mun_fim", ""),
           "VALOR_CARGA": str(dados.get("valor_carga", 0)),
           "QTD_DOCS": str(dados.get("qtd_docs", 0)),
           "PLACA_VEIC": dados.get("placa_veic", ""),
           "MOTORISTA": dados.get("motorista", ""),
           "CPF_MOTORISTA": dados.get("cpf_motorista", ""),
           "STATUS": dados.get("status", ""),
           "PROTOCOLO": dados.get("protocolo", ""),
           "DATA_EMISSAO": dados.get("data_emissao", "")}
    out, _ = _run("gerir_mdfe", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao criar MDF-e: " + out.strip())

def mdfe_alterar(id_val, dados):
    env = {"ACAO": "alterar", "ID": str(id_val)}
    for k in ("numero","serie","chave","cnpj_emit","nome_emit","modal",
              "uf_ini","uf_fim","mun_ini","mun_fim","valor_carga","qtd_docs",
              "placa_veic","motorista","cpf_motorista","status","protocolo","data_emissao"):
        v = dados.get(k)
        if v is not None:
            env[k.upper()] = str(v)
    out, _ = _run("gerir_mdfe", env)
    return "OK" in out

def mdfe_excluir(id_val):
    out, _ = _run("gerir_mdfe", {"ACAO": "excluir", "ID": str(id_val)})
    return "OK" in out

# ── Utilitários ──────────────────────────────────────────────

def sync_json():
    for prog in ["batch_json_produtos", "batch_json_fornecedores", "batch_json_vendas", "batch_json_numeracao"]:
        try:
            _compile_if_needed(prog)
            _run(prog, {})
        except Exception:
            pass
    return {"synced": True}
