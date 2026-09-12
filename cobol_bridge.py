"""CobolBridge — Ponte Python para programas COBOL do FiscalBrasil ERP"""

import json
import jsonio
import os
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COBOL_BIN = os.path.join(BASE_DIR, "cobol", "bin")
COBOL_SRC = os.path.join(BASE_DIR, "cobol", "programs")
DADOS_DIR = os.path.join(BASE_DIR, "dados")

os.makedirs(COBOL_BIN, exist_ok=True)
os.makedirs(DADOS_DIR, exist_ok=True)

# Serializa a execução dos programas COBOL: os dados/*.dat são compartilhados
# e o servidor agora é multithread (ThreadingHTTPServer) — evita corrida de
# escrita entre requisições concorrentes.
_COBOL_LOCK = threading.Lock()


def _norm_ncm(value: str) -> str:
    """NCM no COBOL é PIC X(8): gravar só dígitos (ex.: 10063021)."""
    return re.sub(r"\D", "", value or "")[:8]

def _env():
    env = os.environ.copy()
    env["COB_LIBRARY_PATH"] = COBOL_SRC
    return env

def _run(program, env_vars):
    with _COBOL_LOCK:
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
        with _COBOL_LOCK:
            # re-checa dentro do lock: outra thread pode ter compilado entretanto
            if not os.path.exists(exe):
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
        "CEP": dados.get("cep", ""),
        "TELEFONE": dados.get("telefone", ""),
        "EMAIL": dados.get("email", ""),
        "IE": dados.get("ie", ""),
        "INSCRICAO_MUN": dados.get("inscricao_mun", ""),
        "CNAE": dados.get("cnae", ""),
        "CNAE_DESC": dados.get("cnae_desc", ""),
        "LOGO": dados.get("logo", ""),
    }
    if dados.get("id") not in (None, ""):
        env["ID"] = str(dados.get("id"))
    out, _ = _run("gerir_fornecedores", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), "")
    raise Exception(msg if msg else "Erro ao criar fornecedor: " + out.strip())

def fornecedores_alterar(id_val, dados):
    env = {
        "ACAO": "alterar",
        "ID": str(id_val),
        "NOME": dados.get("nome", ""),
        "CNPJ": dados.get("cnpj", ""),
        "ENDERECO": dados.get("endereco", ""),
        "CEP": dados.get("cep", ""),
        "TELEFONE": dados.get("telefone", ""),
        "EMAIL": dados.get("email", ""),
        "IE": dados.get("ie", ""),
        "INSCRICAO_MUN": dados.get("inscricao_mun", ""),
        "CNAE": dados.get("cnae", ""),
        "CNAE_DESC": dados.get("cnae_desc", ""),
        "LOGO": dados.get("logo", ""),
        "LOGO_CLEAR": "S" if dados.get("logo") == "" else "",
    }
    out, _ = _run("gerir_fornecedores", env)
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), "")
    if msg:
        raise Exception(msg)
    return "OK" in out

def fornecedores_excluir(id_val):
    out, _ = _run("gerir_fornecedores", {"ACAO": "excluir", "ID": str(id_val)})
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), "")
    if msg:
        raise Exception(msg)
    return "OK" in out

# ── Categorias ──────────────────────────────────────────────
# Fonte da verdade: dados/categorias.dat (programa gerir_categorias.cbl).


def categorias_listar():
    out, _ = _run("gerir_categorias", {"ACAO": "listar"})
    try:
        data = json.loads(out)
        return data.get("categorias", [])
    except json.JSONDecodeError:
        return []


def categorias_incluir(dados):
    env = {
        "ACAO": "incluir",
        "NOME": dados.get("nome", ""),
        "DESCRICAO": dados.get("descricao", ""),
        "ATIVO": "S" if dados.get("ativo", True) is not False else "N",
    }
    pai = dados.get("pai_id", dados.get("pai", 0))
    if pai not in (None, "", 0, "0"):
        env["PAI_ID"] = str(pai)
    if dados.get("id") not in (None, ""):
        env["ID"] = str(dados.get("id"))
    out, _ = _run("gerir_categorias", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), out.strip())
    raise Exception(msg)


def categorias_alterar(id_val, dados):
    env = {
        "ACAO": "alterar",
        "ID": str(id_val),
        "NOME": dados.get("nome", ""),
        "DESCRICAO": dados.get("descricao", ""),
    }
    if "ativo" in dados:
        env["ATIVO"] = "S" if dados["ativo"] is not False else "N"
    if "pai_id" in dados or "pai" in dados:
        pai = dados.get("pai_id", dados.get("pai"))
        if pai in (None, "", 0, "0"):
            env["PAI_ID"] = "0"
        else:
            env["PAI_ID"] = str(pai)
    out, _ = _run("gerir_categorias", env)
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), "")
    if msg:
        raise Exception(msg)
    return "OK" in out


def categorias_excluir(id_val):
    out, _ = _run("gerir_categorias", {"ACAO": "excluir", "ID": str(id_val)})
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), "")
    if msg:
        raise Exception(msg)
    return "OK" in out


# ── Variantes ───────────────────────────────────────────────
# Fonte da verdade: dados/variantes.dat (programa gerir_variantes.cbl).


def variantes_listar():
    out, _ = _run("gerir_variantes", {"ACAO": "listar"})
    try:
        data = json.loads(out)
        return data.get("variantes", [])
    except json.JSONDecodeError:
        return []


def variantes_incluir(dados):
    env = {
        "ACAO": "incluir",
        "PRODUTO_ID": str(dados.get("produto_id", dados.get("produto", ""))),
        "NOME": dados.get("nome", ""),
        "ATRIBUTOS": dados.get("atributos", ""),
        "CODIGO": dados.get("codigo", ""),
        "PRECO": str(dados.get("preco", "") or ""),
        "ATIVO": "S" if dados.get("ativo", True) is not False else "N",
    }
    if dados.get("id") not in (None, ""):
        env["ID"] = str(dados.get("id"))
    out, _ = _run("gerir_variantes", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), out.strip())
    raise Exception(msg)


def variantes_alterar(id_val, dados):
    env = {
        "ACAO": "alterar",
        "ID": str(id_val),
        "PRODUTO_ID": str(dados.get("produto_id", dados.get("produto", "")) or ""),
        "NOME": dados.get("nome", ""),
        "ATRIBUTOS": dados.get("atributos", ""),
        "CODIGO": dados.get("codigo", ""),
        "PRECO": str(dados.get("preco", "") or ""),
        "CODIGO_CLEAR": "S" if dados.get("codigo", "") == "" and "codigo" in dados else "",
        "ATRIBUTOS_CLEAR": "S" if dados.get("atributos", "") == "" and "atributos" in dados else "",
    }
    if "ativo" in dados:
        env["ATIVO"] = "S" if dados["ativo"] is not False else "N"
    out, _ = _run("gerir_variantes", env)
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), "")
    if msg:
        raise Exception(msg)
    return "OK" in out


def variantes_excluir(id_val):
    out, _ = _run("gerir_variantes", {"ACAO": "excluir", "ID": str(id_val)})
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), "")
    if msg:
        raise Exception(msg)
    return "OK" in out


def sync_variantes_for_produto(produto_id, variacoes, preco_base=0):
    """Sincroniza variantes inline do formulário com variantes.dat COBOL.

    Para cada variação do formulário, cria ou atualiza o registro
    correspondente em variantes.dat. Desativa variantes COBOL que não
    existem mais no formulário (soft-delete).
    """
    produto_id = int(produto_id)
    preco_base = float(preco_base or 0)

    # 1. Carregar variantes existentes no COBOL para este produto
    existing = variantes_listar()
    existing_for_product = [v for v in existing
                            if v.get("produto_id") == produto_id]

    # Mapear por nome normalizado
    existing_by_name = {}
    for v in existing_for_product:
        key = (v.get("nome") or "").strip().lower()
        if key:
            existing_by_name[key] = v

    used_names = set()

    for var in (variacoes or []):
        atributo = (var.get("atributo") or "").strip()
        valor = (var.get("valor") or "").strip()
        if atributo and valor:
            nome = f"{atributo}: {valor}"
        elif valor:
            nome = valor
        elif atributo:
            nome = atributo
        else:
            continue

        tipo_preco = var.get("tipo_preco") or "delta"
        valor_preco = float(var.get("valor_preco") or 0)
        if tipo_preco == "absoluto":
            preco_final = valor_preco
        else:
            preco_final = preco_base + valor_preco

        codigo = (var.get("ean") or "").strip()
        ativo = var.get("ativo", True)
        nome_norm = nome.strip().lower()
        used_names.add(nome_norm)

        if nome_norm in existing_by_name:
            cobol_var = existing_by_name[nome_norm]
            try:
                variantes_alterar(cobol_var["id"], {
                    "nome": nome,
                    "preco": preco_final,
                    "codigo": codigo,
                    "ativo": ativo,
                })
            except Exception:
                pass
        else:
            try:
                vid = variantes_incluir({
                    "produto_id": produto_id,
                    "nome": nome,
                    "preco": preco_final,
                    "codigo": codigo,
                    "ativo": ativo,
                })
                if vid:
                    existing_by_name[nome_norm] = {"id": vid, "nome": nome}
            except Exception:
                pass

    # Desativar variantes COBOL que não estão no formulário
    for v in existing_for_product:
        key = (v.get("nome") or "").strip().lower()
        if key and key not in used_names and v.get("ativo", True):
            try:
                variantes_alterar(v["id"], {"ativo": False})
            except Exception:
                pass


def variantes_listar_por_produto(produto_id):
    """Lista variantes COBOL de um produto específico."""
    all_v = variantes_listar()
    pid = int(produto_id)
    return [v for v in all_v if v.get("produto_id") == pid]


# ── Atributos de Produtos ────────────────────────────────────

def atributos_listar():
    out, _ = _run("gerir_atributos", {"ACAO": "listar"})
    try:
        data = json.loads(out)
        return data.get("atributos", [])
    except json.JSONDecodeError:
        return []


def atributos_listar_por_produto(produto_id):
    out, _ = _run("gerir_atributos", {
        "ACAO": "listar-por-produto",
        "PRODUTO_ID": str(produto_id),
    })
    try:
        data = json.loads(out)
        return data.get("atributos", [])
    except json.JSONDecodeError:
        return []


def atributos_incluir(dados):
    env = {
        "ACAO": "incluir",
        "PRODUTO_ID": str(dados.get("produto_id", "")),
        "NOME": dados.get("nome", ""),
        "VALOR": dados.get("valor", ""),
    }
    if dados.get("id") not in (None, ""):
        env["ID"] = str(dados.get("id"))
    out, _ = _run("gerir_atributos", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), out.strip())
    raise Exception(msg)


def atributos_alterar(id_val, dados):
    env = {
        "ACAO": "alterar",
        "ID": str(id_val),
        "NOME": dados.get("nome", ""),
        "VALOR": dados.get("valor", ""),
    }
    out, _ = _run("gerir_atributos", env)
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), "")
    if msg:
        if "nao encontrado" in msg.lower() or "não encontrado" in msg.lower():
            return False
        raise Exception(msg)
    return "OK" in out


def atributos_excluir(id_val):
    out, _ = _run("gerir_atributos", {"ACAO": "excluir", "ID": str(id_val)})
    msg = next((l.strip() for l in out.splitlines() if "ERRO:" in l), "")
    if msg:
        if "nao encontrado" in msg.lower() or "não encontrado" in msg.lower():
            return False
        raise Exception(msg)
    return "OK" in out


# ── Funcionários ────────────────────────────────────────────

_FUNCIONARIO_ENV_KEYS = [
    "NOME", "USUARIO", "SENHA", "PERMISSOES", "CPF", "RG", "DATA_NASC",
    "CELULAR", "EMAIL", "ENDERECO", "DATA_ADM", "DATA_DEM", "SALARIO",
    "EMPRESA_ID", "FILIAL_ID", "TRAB_SAB", "TRAB_DOM",
    "SEG_ENT", "SEG_ALM", "SEG_SAI",
    "TER_ENT", "TER_ALM", "TER_SAI",
    "QUA_ENT", "QUA_ALM", "QUA_SAI",
    "QUI_ENT", "QUI_ALM", "QUI_SAI",
    "SEX_ENT", "SEX_ALM", "SEX_SAI",
    "SAB_ENT", "SAB_SAI", "DOM_ENT", "DOM_SAI",
    "FOTO", "CONTATO_EMERG_NOME", "CONTATO_EMERG_TEL", "CURRICULO",
    "TIPO_SANGUINEO", "EMAIL_PARTICULAR", "TEL_COMERCIAL",
    "BANCO", "AGENCIA", "CONTA", "CONTA_DIGITO", "CONTA_TIPO", "PIX",
    "PIS", "CTPS", "CTPS_SERIE", "CTPS_UF", "CBO", "GRAU_INSTRUCAO",
    "TIPO_CONTRATO", "MOTIVO_DESLIG",
    "VT_DESCONTO", "VT_DIAS", "VR", "PLANO_SAUDE", "PLANO_SAUDE_VALOR", "VT_OPTANTE",
    "SUPERVISOR_ID",
    "SEXO", "ESTADO_CIVIL", "NACIONALIDADE", "RG_ORGAO", "RG_UF",
    "TITULO_ELEITOR", "CEP", "CIDADE", "UF", "SITUACAO_VINCULO",
    "DEPARTAMENTO", "DATA_POSSE_CARGO", "FORMA_PAGAMENTO", "MEIO_PAGAMENTO",
    "CARGA_HORARIA", "EXAME_ADM_VENC", "OBSERVACOES", "PENSAO_TIPO",
    "PENSAO_VALOR", "DEPARTAMENTO_ID", "CARGO_ID",
]

# mapa: nome no form da página (minúsculo/snake) -> env var COBOL
_FUNCIONARIO_FIELD_MAP = {k.lower(): k for k in _FUNCIONARIO_ENV_KEYS}
_FUNCIONARIO_FIELD_MAP["data_nasc"] = "DATA_NASC"
_FUNCIONARIO_FIELD_MAP["data_adm"] = "DATA_ADM"
_FUNCIONARIO_FIELD_MAP["data_dem"] = "DATA_DEM"
_FUNCIONARIO_FIELD_MAP["tipo_sanguineo"] = "TIPO_SANGUINEO"
_FUNCIONARIO_FIELD_MAP["grau_instrucao"] = "GRAU_INSTRUCAO"
_FUNCIONARIO_FIELD_MAP["tipo_contrato"] = "TIPO_CONTRATO"
_FUNCIONARIO_FIELD_MAP["motivo_deslig"] = "MOTIVO_DESLIG"
_FUNCIONARIO_FIELD_MAP["contato_emerg_nome"] = "CONTATO_EMERG_NOME"
_FUNCIONARIO_FIELD_MAP["contato_emerg_tel"] = "CONTATO_EMERG_TEL"


def _funcionario_env(acao, dados, id_val=None):
    env = {"ACAO": acao}
    for field, var in _FUNCIONARIO_FIELD_MAP.items():
        if field in dados and dados[field] is not None:
            env[var] = str(dados[field])
    if id_val not in (None, ""):
        env["ID"] = str(id_val)
    return env


def funcionarios_listar():
    out, _ = _run("gerir_funcionarios", {"ACAO": "listar"})
    try:
        return json.loads(out).get("funcionarios", [])
    except json.JSONDecodeError:
        return []


def funcionario_incluir(dados):
    out, _ = _run("gerir_funcionarios", _funcionario_env("incluir", dados))
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao criar funcionário: " + out.strip())


def funcionario_alterar(id_val, dados):
    out, _ = _run("gerir_funcionarios", _funcionario_env("alterar", dados, id_val))
    return "OK" in out


def funcionario_excluir(id_val):
    out, _ = _run("gerir_funcionarios", {"ACAO": "excluir", "ID": str(id_val)})
    return "OK" in out


# ── RFC-002 §3.3/Decisão 1 — Histórico de salários com vigência ──

def salario_incluir(funcionario_id, salario, data_inicio):
    """Registra uma alteração salarial com data de início de vigência.
    Retorna o id do novo registro do histórico."""
    out, _ = _run("gerir_salarios", {
        "ACAO": "incluir",
        "FUNCIONARIO_ID": str(funcionario_id),
        "SALARIO": str(salario),
        "DATA_INICIO": str(data_inicio),
    })
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao registrar salário: " + out.strip())


def salarios_listar(funcionario_id):
    """Histórico de salários de um funcionário (ativos)."""
    out, _ = _run("gerir_salarios", {
        "ACAO": "listar", "FUNCIONARIO_ID": str(funcionario_id)})
    try:
        return json.loads(out).get("salarios", [])
    except json.JSONDecodeError:
        return []


def salario_vigente(funcionario_id, competencia):
    """Salário vigente de um funcionário na competência (YYYY/MM).
    Retorna {"salario": float, "data_inicio": "YYYY-MM-DD"}; salario 0 se
    não houver registro ativo para a competência."""
    out, _ = _run("gerir_salarios", {
        "ACAO": "vigente",
        "FUNCIONARIO_ID": str(funcionario_id),
        "COMPETENCIA": str(competencia),
    })
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"salario": 0, "data_inicio": ""}


# ── RFC-016/RFC-002 §3.3 — Movimentações contratuais com vigência ──
# (cargo e departamento; cada tipo é uma movimentação independente)

def movimentacao_incluir(funcionario_id, tipo, valor_referencia, data_inicio):
    """Registra uma movimentação contratual (cargo|departamento) com data de
    início de vigência. Retorna o id do novo registro."""
    out, _ = _run("gerir_movimentacoes", {
        "ACAO": "incluir",
        "FUNCIONARIO_ID": str(funcionario_id),
        "TIPO": str(tipo),
        "VALOR_REFERENCIA": str(valor_referencia),
        "DATA_INICIO": str(data_inicio),
    })
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao registrar movimentação: " + out.strip())


def movimentacoes_listar(funcionario_id, tipo):
    """Histórico de movimentações de um tipo (cargo|departamento)."""
    out, _ = _run("gerir_movimentacoes", {
        "ACAO": "listar",
        "FUNCIONARIO_ID": str(funcionario_id),
        "TIPO": str(tipo),
    })
    try:
        return json.loads(out).get("movimentacoes", [])
    except json.JSONDecodeError:
        return []


def movimentacao_vigente(funcionario_id, tipo, competencia):
    """Valor (id de cargo/departamento) vigente na competência (YYYY/MM).
    Retorna {"valor_referencia": int, "data_inicio": "YYYY-MM-DD"};
    valor_referencia 0 se não houver registro ativo."""
    out, _ = _run("gerir_movimentacoes", {
        "ACAO": "vigente",
        "FUNCIONARIO_ID": str(funcionario_id),
        "TIPO": str(tipo),
        "COMPETENCIA": str(competencia),
    })
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"valor_referencia": 0, "data_inicio": ""}


# ── RFC-003 — Admissão/Demissão (Rescisão) ─────────────────

RESCISAO_MOTIVOS = [
    "sem-justa-causa",
    "com-justa-causa",
    "pedido-demissao",
    "acordo",
    "termino-contrato",
]

_RESCISAO_FIELD_MAP = {
    "funcionario_id": "FUNCIONARIO_ID",
    "nome": "NOME",
    "motivo": "MOTIVO",
    "data_deslig": "DATA_DESLIG",
    "tipo_aviso": "TIPO_AVISO",
    "dias_aviso": "DIAS_AVISO",
    "saldo_dias": "SALDO_DIAS",
    "ferias_venc_dias": "FERIAS_VENC_DIAS",
    "ferias_prop_meses": "FERIAS_PROP_MESES",
    "13_prop_meses": "13_PROP_MESES",
    "salario_base": "SALARIO_BASE",
}


def _rescisao_env(acao, dados):
    env = {"ACAO": acao}
    for field, var in _RESCISAO_FIELD_MAP.items():
        val = dados.get(field)
        if val is not None and val != "":
            env[var] = str(val)
    return env


def _parse_saida(out):
    """Levanta Exception com a mensagem do COBOL quando há ERRO na saída."""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("ERRO:"):
            raise Exception(line.strip())
    return out


def rescisao_calcular(dados):
    out, _ = _run("folha_pagamento", _rescisao_env("rescisao-calcular", dados))
    out = _parse_saida(out)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL: " + out.strip()[:200])


def rescisao_incluir(dados):
    # O form da tela não envia nome; deriva do funcionário para a tabela
    # mostrar o nome (não "#id"). Cobrindo aqui, todos os callers (server e
    # diretos) ganham — ver smoke_rfc003 seção 8.
    if not dados.get("nome"):
        fid = dados.get("funcionario_id")
        for f in funcionarios_listar():
            if str(f.get("id")) == str(fid):
                dados["nome"] = f.get("nome", "")
                break
    out, _ = _run("folha_pagamento", _rescisao_env("rescisao-incluir", dados))
    out = _parse_saida(out)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL: " + out.strip()[:200])


def rescisao_listar():
    out, _ = _run("folha_pagamento", {"ACAO": "rescisao-listar"})
    try:
        return json.loads(out).get("rescisoes", [])
    except json.JSONDecodeError:
        # não engole o erro: JSON corrompido = dados inconsistentes (bug real
        # de buffer já aconteceu aqui e ficou mascarado por lista vazia)
        raise Exception("Saída inesperada do COBOL (rescisao-listar): " + out.strip()[:200])


def rescisao_pagar(id_val, data_pagamento=None):
    env = {"ACAO": "rescisao-pagar", "ID": str(id_val)}
    if data_pagamento:
        env["DATA_PAGAMENTO"] = data_pagamento
    out, _ = _run("folha_pagamento", env)
    _parse_saida(out)
    return "OK" in out


def rescisao_excluir(id_val):
    out, _ = _run("folha_pagamento", {"ACAO": "rescisao-excluir", "ID": str(id_val)})
    _parse_saida(out)
    return "OK" in out


def funcionario_desligar(id_val, data_dem, motivo):
    out, _ = _run("gerir_funcionarios", {
        "ACAO": "desligar",
        "ID": str(id_val),
        "DATA_DEM": data_dem or "",
        "MOTIVO_DESLIG": motivo or "",
    })
    _parse_saida(out)
    return "OK" in out


# ── RFC-010 — Férias (cálculo no COBOL, padrão rescisão) ──
# O COBOL calcula a partir dos dados brutos (dias, abono, salário) e devolve
# JSON com valor base, 1/3, abono, INSS/IRRF e líquido. Incluir calcula e grava.

_FERIAS_FIELD_MAP = {
    "funcionario_id": "FUNCIONARIO_ID",
    "nome": "NOME",
    "aquis_inicio": "AQUIS_INICIO",
    "aquis_fim": "AQUIS_FIM",
    "inicio": "INICIO",
    "fim": "FIM",
    "dias": "DIAS",
    "dias_abono": "DIAS_ABONO",
    "salario_base": "SALARIO_BASE",
}


def _ferias_env(acao, dados):
    env = {"ACAO": acao}
    for field, var in _FERIAS_FIELD_MAP.items():
        val = dados.get(field)
        if val is not None and val != "":
            env[var] = str(val)
    return env


def _ferias_json(out):
    """Parseia a linha JSON do cálculo/registro de férias."""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise Exception("Saída inesperada do COBOL (férias): " + out.strip()[:200])


def ferias_calcular(dados):
    out, _ = _run("folha_pagamento", _ferias_env("ferias-calcular", dados))
    out = _parse_saida(out)
    return _ferias_json(out)


def ferias_incluir(dados):
    out, _ = _run("folha_pagamento", _ferias_env("ferias-incluir", dados))
    out = _parse_saida(out)
    return _ferias_json(out)


def ferias_listar():
    out, _ = _run("folha_pagamento", {"ACAO": "ferias-listar"})
    try:
        return json.loads(out).get("ferias", [])
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (ferias-listar): " + out.strip()[:200])


def ferias_pagar(id_val, data_pagamento=None):
    env = {"ACAO": "ferias-pagar", "ID": str(id_val)}
    if data_pagamento:
        env["DATA_PAGAMENTO"] = data_pagamento
    out, _ = _run("folha_pagamento", env)
    _parse_saida(out)
    return "OK" in out


def ferias_excluir(id_val):
    out, _ = _run("folha_pagamento", {"ACAO": "ferias-excluir", "ID": str(id_val)})
    _parse_saida(out)
    return "OK" in out


# ── RFC-011 — 13º Salário (cálculo no COBOL, padrão rescisão) ──
# 1ª parcela sem descontos; 2ª parcela/única com INSS e IRRF das tabelas.

_DECIMO_FIELD_MAP = {
    "funcionario_id": "FUNCIONARIO_ID",
    "nome": "NOME",
    "ano": "ANO",
    "parcela": "PARCELA",
    "meses": "MESES",
    "salario_base": "SALARIO_BASE",
}


def _decimo_env(acao, dados):
    env = {"ACAO": acao}
    for field, var in _DECIMO_FIELD_MAP.items():
        val = dados.get(field)
        if val is not None and val != "":
            env[var] = str(val)
    return env


def _decimo_json(out):
    """Parseia a linha JSON do cálculo/registro de 13º."""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise Exception("Saída inesperada do COBOL (13º): " + out.strip()[:200])


def decimo_calcular(dados):
    out, _ = _run("folha_pagamento", _decimo_env("decimo-calcular", dados))
    out = _parse_saida(out)
    return _decimo_json(out)


def decimo_incluir(dados):
    out, _ = _run("folha_pagamento", _decimo_env("decimo-incluir", dados))
    out = _parse_saida(out)
    return _decimo_json(out)


def decimos_listar():
    out, _ = _run("folha_pagamento", {"ACAO": "decimo-listar"})
    try:
        return json.loads(out).get("decimos", [])
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (decimo-listar): " + out.strip()[:200])


def decimo_pagar(id_val, data_pagamento=None):
    env = {"ACAO": "decimo-pagar", "ID": str(id_val)}
    if data_pagamento:
        env["DATA_PAGAMENTO"] = data_pagamento
    out, _ = _run("folha_pagamento", env)
    _parse_saida(out)
    return "OK" in out


def decimo_excluir(id_val):
    out, _ = _run("folha_pagamento", {"ACAO": "decimo-excluir", "ID": str(id_val)})
    _parse_saida(out)
    return "OK" in out


# ── RFC-013 — Folha Complementar (ajuste de competência fechada) ──
# Ajusta diferenças de uma competência já fechada sem tocar a folha original.
# Cálculo no COBOL: diferença a favor (positiva) tributa INSS/IRRF sobre a
# diferença; diferença contra (negativa) exige motivo específico validado
# (erro comprovado, devolução, decisão judicial) e respeita o limite legal de
# desconto de 70% do salário. Fluxo de estados: C → V → F → P.

_COMP_FIELD_MAP = {
    "funcionario_id": "FUNCIONARIO_ID",
    "nome": "NOME",
    "competencia": "COMPETENCIA",
    "competencia_ref": "COMPETENCIA_REF",
    "motivo": "MOTIVO",
    "valor": "VALOR",
    "salario_base": "SALARIO_BASE",
}

# Motivos válidos para diferença negativa (RFC-013 Decisão 2).
COMP_NEGATIVO_MOTIVOS = ("erro comprovado", "devolucao", "decisao judicial")


def _comp_env(acao, dados):
    env = {"ACAO": acao}
    for field, var in _COMP_FIELD_MAP.items():
        val = dados.get(field)
        if val is not None and val != "":
            env[var] = str(val)
    return env


def _comp_json(out):
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise Exception("Saída inesperada do COBOL (complementar): " + out.strip()[:200])


def comp_calcular(dados):
    """Calcula a diferença da folha complementar sem gravar (RFC-013)."""
    out, _ = _run("folha_pagamento", _comp_env("comp-calcular", dados))
    out = _parse_saida(out)
    return _comp_json(out)


def comp_incluir(dados):
    """Valida (motivo obrigatório + regras de valor negativo) e grava."""
    out, _ = _run("folha_pagamento", _comp_env("comp-incluir", dados))
    out = _parse_saida(out)
    return _comp_json(out)


def complementares_listar():
    """Todas as folhas complementares registradas."""
    out, _ = _run("folha_pagamento", {"ACAO": "comp-listar"})
    try:
        return json.loads(out).get("complementares", [])
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (comp-listar): " + out.strip()[:200])


def comp_transicao(id_val, destino, data_pagamento=None):
    """Avança o fluxo de estados (C→V→F→P). Retorna True em OK."""
    acao = {"V": "comp-validar", "F": "comp-fechar", "P": "comp-pagar"}.get(destino)
    if not acao:
        return False
    env = {"ACAO": acao, "ID": str(id_val)}
    if data_pagamento:
        env["DATA_PAGAMENTO"] = str(data_pagamento)
    out, _ = _run("folha_pagamento", env)
    _parse_saida(out)
    return "OK" in out


def comp_validar(id_val):
    return comp_transicao(id_val, "V")


def comp_fechar(id_val):
    return comp_transicao(id_val, "F")


def comp_pagar(id_val, data_pagamento=None):
    return comp_transicao(id_val, "P", data_pagamento)


def comp_excluir(id_val):
    out, _ = _run("folha_pagamento", {"ACAO": "comp-excluir", "ID": str(id_val)})
    _parse_saida(out)
    return "OK" in out


def comp_encargos(competencia, regime=None):
    """RFC-013 Decisão 4: encargos/recolhimentos apenas sobre a diferença
    das complementares fechadas/pagas da competência. regime 'simples' zera
    INSS patronal/RAT/terceiros (DAS) — igual RFC-014. Não grava em
    encargos.dat (a folha mensal já tem o seu registro)."""
    env = {"ACAO": "comp-encargos", "COMPETENCIA": str(competencia)}
    if regime:
        env["REGIME"] = str(regime)
    out, _ = _run("folha_pagamento", env)
    _parse_saida(out)
    return _comp_json(out)


# ── Licenças (RH) — aprovações via COBOL (cobol/programs/licenca.cbl) ──
# Status: P=pendente (padrão), S=enviado, A=aprovado, R=rejeitado, C=concluído.
# O dashboard do RH (workflow) trabalha com D/S/A/C/R — o COBOL usa P no
# cadastro; "pendentes" lista as de status S (enviadas para aprovação).

_LICENCA_FIELD_MAP = {
    "funcionario_id": "FUNCIONARIO_ID",
    "tipo": "TIPO",
    "data_inicio": "DATA_INICIO",
    "data_fim": "DATA_FIM",
    "dias": "DIAS",
    "motivo": "MOTIVO",
    "status": "STATUS",
    "observacoes": "OBSERVACOES",
}


def _licenca_env(acao, dados):
    env = {"ACAO": acao}
    for field, var in _LICENCA_FIELD_MAP.items():
        val = dados.get(field)
        if val is not None and val != "":
            env[var] = str(val)
    return env


def licenca_incluir(dados):
    """Registra uma licença. Retorna o id do novo registro."""
    out, _ = _run("licenca", _licenca_env("incluir", dados))
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao registrar licença: " + out.strip())


def licencas_listar():
    """Todas as licenças (JSON do COBOL)."""
    out, _ = _run("licenca", {"ACAO": "listar"})
    try:
        return json.loads(out).get("licencas", [])
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (licenca-listar): " + out.strip()[:200])


def licencas_pendentes():
    """Licenças enviadas aguardando aprovação (status S)."""
    out, _ = _run("licenca", {"ACAO": "pendentes"})
    try:
        return json.loads(out).get("licencas", [])
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (licenca-pendentes): " + out.strip()[:200])


def _licenca_transicao(acao, id_val, status=None, aprovado_por="", data_aprovacao=""):
    env = {"ACAO": acao, "ID": str(id_val)}
    if status is not None:
        env["STATUS"] = str(status)
    if aprovado_por:
        env["APROVADO_POR"] = aprovado_por
    if data_aprovacao:
        env["DATA_APROVACAO"] = data_aprovacao
    out, _ = _run("licenca", env)
    return "OK" in out


def licenca_aprovar(id_val, aprovado_por="", data_aprovacao=""):
    return _licenca_transicao("aprovar", id_val, aprovado_por=aprovado_por,
                              data_aprovacao=data_aprovacao)


def licenca_rejeitar(id_val, aprovado_por="", data_aprovacao=""):
    return _licenca_transicao("rejeitar", id_val, aprovado_por=aprovado_por,
                              data_aprovacao=data_aprovacao)


def licenca_transitar(id_val, status, aprovado_por="", data_aprovacao=""):
    """Transição genérica de status (usada pelo workflow do dashboard)."""
    return _licenca_transicao("transitar", id_val, status=status,
                              aprovado_por=aprovado_por,
                              data_aprovacao=data_aprovacao)


def licenca_alterar(id_val, dados):
    """Altera dados de uma licença (ex.: datas/dias/motivo antes da aprovação).
    Campos vazios não são sobrescritos (padrão do COBOL alterar)."""
    out, _ = _run("licenca", _licenca_env("alterar", dados) | {"ID": str(id_val)})
    return "OK" in out


def licenca_excluir(id_val):
    """Remove uma licença (apenas não aprovadas — guard na tela)."""
    out, _ = _run("licenca", {"ACAO": "excluir", "ID": str(id_val)})
    return "OK" in out


def licencas_por_funcionario(funcionario_id):
    """Licenças de um funcionário (JSON do COBOL listar-por-func)."""
    out, _ = _run("licenca", {"ACAO": "listar-por-func",
                              "FUNCIONARIO_ID": str(funcionario_id)})
    try:
        return json.loads(out).get("licencas", [])
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (licenca-por-func): " + out.strip()[:200])


# ── RFC-012 Decisão 3 — dias de afastamento na competência ──
# Tipos com pagamento integral (não geram pró-rata): maternidade, paternidade.
# Auxílio-doença: a empresa paga os 15 primeiros dias (CLT 476 §3) — os dias
# além de 15 não são pagos pelo empregador. Licença não remunerada: nenhum dia
# é pago. O cálculo da folha usa os dias efetivamente trabalhados (pró-rata).

_LICENCA_TIPOS_SEM_PRORATA = ("licenca-maternidade", "licenca-paternidade",
                              "maternidade", "paternidade")
_LICENCA_TIPOS_AUXILIO = ("auxilio-doenca", "auxilio-doença",
                          "auxilio-doença-acidentario", "auxilio-doenca-acidentario",
                          "acidente-trabalho", "acidente de trabalho")
_LICENCA_TIPOS_SEM_PAGAMENTO = ("licenca-nao-remunerada", "licenca não remunerada",
                                "nao-remunerada", "suspensao", "suspensão")


def _dias_no_mes(data_inicio, data_fim, competencia):
    """Dias de interseção entre [data_inicio, data_fim] e a competência
    (YYYY/MM). Retorna 0 quando não há sobreposição."""
    try:
        ano, mes = (int(x) for x in competencia.split("/"))
        ini = datetime.strptime(str(data_inicio)[:10], "%Y-%m-%d").date()
        fim = datetime.strptime(str(data_fim)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0
    import calendar
    from datetime import date
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    primeiro = ini if (ini.year, ini.month) == (ano, mes) else date(ano, mes, 1)
    fim_mes_d = date(ano, mes, ultimo_dia)
    if fim < primeiro or ini > fim_mes_d:
        return 0
    return max(0, (min(fim, fim_mes_d) - max(ini, primeiro)).days + 1)


def dias_afastamento_na_competencia(funcionario_id, competencia):
    """RFC-012 Decisão 3 — dias NÃO pagos por afastamento na competência.

    Considera apenas licenças aprovadas (status A). Regras por tipo:
      - maternidade/paternidade: 0 dias (pagamento integral — empresa/INSS)
      - auxílio-doença/acidente: dias além dos 15 primeiros (empresa paga os
        15; INSS assume após) — acumula o saldo excedente da licença
      - licença não remunerada/suspensão: todos os dias da licença no mês
    Funcionário sem licença aprovada no período retorna 0.
    """
    try:
        licencas = licencas_por_funcionario(funcionario_id)
    except Exception:
        return 0
    total = 0
    for lic in licencas:
        if (lic.get("status") or "").strip().upper() != "A":
            continue
        tipo = (lic.get("tipo") or "").strip().lower()
        if tipo in _LICENCA_TIPOS_SEM_PRORATA:
            continue
        dias_mes = _dias_no_mes(lic.get("data_inicio"), lic.get("data_fim"), competencia)
        if dias_mes <= 0:
            continue
        if tipo in _LICENCA_TIPOS_AUXILIO:
            # Os 15 primeiros dias DA LICENÇA (contados do data_inicio, não por
            # mês) são pagos pela empresa; o excedente não entra na folha (INSS
            # assume). Em licenças que atravessam meses, os dias pagos em meses
            # anteriores reduzem a cota restante do mês corrente.
            from datetime import date as _date
            try:
                l_ini = datetime.strptime(str(lic.get("data_inicio"))[:10], "%Y-%m-%d").date()
                l_fim = datetime.strptime(str(lic.get("data_fim"))[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                l_ini = l_fim = None
            ano, mes = (int(x) for x in competencia.split("/"))
            if not (l_ini and l_fim):
                continue
            import calendar as _cal
            ultimo_dia = _cal.monthrange(ano, mes)[1]
            # dias da licença antes do início do mês (já pagos pela empresa)
            antes_mes = _date(ano, mes, 1) - timedelta(days=1)
            if l_ini <= antes_mes:
                pagos_antes = max(0, (min(l_fim, antes_mes) - l_ini).days + 1)
            else:
                pagos_antes = 0
            cota_restante = max(0, 15 - pagos_antes)
            total += max(0, dias_mes - cota_restante)
            continue
        # licença não remunerada / suspensão: pró-rata total no mês
        total += dias_mes
    return total


def dias_afastamento_no_periodo(funcionario_id, data_inicio, data_fim):
    """RFC-012 Decisão 4 — dias de afastamento aprovado dentro de um intervalo
    de datas (ex.: período aquisitivo de férias). Conta todos os dias de
    licenças aprovadas (qualquer tipo) que intersectam o período — o gatilho
    de suspensão é >30 dias (RFC-010)."""
    try:
        licencas = licencas_por_funcionario(funcionario_id)
    except Exception:
        return 0
    try:
        p_ini = datetime.strptime(str(data_inicio)[:10], "%Y-%m-%d").date()
        p_fim = datetime.strptime(str(data_fim)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0
    total = 0
    for lic in licencas:
        if (lic.get("status") or "").strip().upper() != "A":
            continue
        try:
            l_ini = datetime.strptime(str(lic.get("data_inicio"))[:10], "%Y-%m-%d").date()
            l_fim = datetime.strptime(str(lic.get("data_fim"))[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if l_fim < p_ini or l_ini > p_fim:
            continue
        total += max(0, (min(l_fim, p_fim) - max(l_ini, p_ini)).days + 1)
    return total


# ── Timesheets (RH) — apontamento de horas via COBOL ──

_TIMESHEET_FIELD_MAP = {
    "funcionario_id": "FUNCIONARIO_ID",
    "data": "DATA",
    "projeto": "PROJETO",
    "tarefa": "TAREFA",
    "horas": "HORAS",
    "descricao": "DESCRICAO",
    "status": "STATUS",
}


def _timesheet_env(acao, dados):
    env = {"ACAO": acao}
    for field, var in _TIMESHEET_FIELD_MAP.items():
        val = dados.get(field)
        if val is not None and val != "":
            env[var] = str(val)
    return env


def timesheet_incluir(dados):
    """Registra um apontamento de horas. Retorna o id."""
    out, _ = _run("timesheet", _timesheet_env("incluir", dados))
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao registrar timesheet: " + out.strip())


def timesheets_listar():
    """Apontamentos de horas (JSON do COBOL)."""
    out, _ = _run("timesheet", {"ACAO": "listar"})
    try:
        return json.loads(out).get("timesheets", [])
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (timesheet-listar): " + out.strip()[:200])


CONFIG_DEFAULTS = {
    "salario_minimo": 1518.00, "inss_f1_teto": 1518.00, "inss_f1_aliq": 7.50,
    "inss_f2_teto": 2793.88, "inss_f2_aliq": 9.00,
    "inss_f3_teto": 4190.83, "inss_f3_aliq": 12.00,
    "inss_f4_teto": 8157.41, "inss_f4_aliq": 14.00,
    "irrf_ded_dep": 189.59, "irrf_f1_teto": 2259.20, "irrf_f1_aliq": 0.00,
    "irrf_f2_teto": 2826.65, "irrf_f2_aliq": 7.50,
    "irrf_f3_teto": 3751.05, "irrf_f3_aliq": 15.00,
    "irrf_f4_teto": 4664.68, "irrf_f4_aliq": 22.50,
    "irrf_f1_ded": 0.00, "irrf_f2_ded": 169.44,
    "irrf_f3_ded": 381.44, "irrf_f4_ded": 662.77,
    "irrf_f5_teto": 0.00, "irrf_f5_aliq": 27.50, "irrf_f5_ded": 896.00,
    "fgts_aliquota": 8.00, "hora_extra_aliq": 50.00,
    # RFC-005 §4 — Salário-Família (2 faixas: teto + valor por cota)
    "sf_f1_teto": 1905.52, "sf_f1_valor": 62.04,
    "sf_f2_teto": 3047.00, "sf_f2_valor": 43.17,
    # RFC-014 — Encargos patronais (INSS patronal 20%, RAT/SAT 2% risco
    # médio, terceiros configurável) — versionados por competência
    "inss_patronal_aliq": 20.00, "rat_aliq": 2.00, "terceiros_aliq": 0.00,
}

_FOLHA_FIELD_MAP = {
    "competencia": "COMPETENCIA",
    "funcionario_id": "FUNCIONARIO_ID",
    "nome": "NOME",
    "salario_base": "SALARIO_BASE",
    "horas_extras": "HORAS_EXTRAS",
    "dsr": "DSR",
    "faltas": "FALTAS",
    "dependentes": "DEPENDENTES",
    "outros_proventos": "OUTROS_PROV",
    "outros_descontos": "OUTROS_DESC",
    "cotas_sf": "COTAS_SF",
}


def _folha_env(acao, dados, extra=None):
    env = {"ACAO": acao}
    for field, var in _FOLHA_FIELD_MAP.items():
        val = dados.get(field)
        if val is not None and val != "":
            env[var] = str(val)
    if extra:
        env.update({k: str(v) for k, v in extra.items() if v is not None})
    return env


def _folha_json(out):
    """Extrai a linha JSON da saída do folha_pagamento (cálculo)."""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise Exception("Saída inesperada do COBOL (folha): " + out.strip()[:200])


def folha_config_ler(competencia=None):
    """Tabela vigente da competência (RFC-005 Regra 1). Sem competencia,
    retorna a última versão gravada; o JSON traz também 'versoes' (histórico
    de competências preservado, separado por vírgula)."""
    env = {"ACAO": "config-ler"}
    if competencia:
        env["COMPETENCIA"] = str(competencia)
    out, _ = _run("folha_pagamento", env)
    data = _folha_json(out)
    # 'versoes' é uma string CSV de competências no COBOL; normaliza para lista
    if isinstance(data.get("versoes"), str):
        data["versoes"] = [c for c in data["versoes"].split(",") if c.strip()]
    return data


def folha_config_salvar(dados):
    """Grava (ou substitui) a tabela da competência; guard Regra 2 no COBOL
    impede sobrescrever competência já fechada/paga."""
    env = {"ACAO": "config-salvar"}
    competencia = dados.get("competencia") or datetime.now().strftime("%Y/%m")
    env["COMPETENCIA"] = str(competencia)
    for k, v in CONFIG_DEFAULTS.items():
        val = dados.get(k)
        env[k.upper()] = str(val if val is not None else v)
    out, _ = _run("folha_pagamento", env)
    _parse_saida(out)
    return True


def folha_config_seed():
    """Garante o arquivo dados/folha_config.dat no layout novo (idempotente).
    Layout novo = 230 bytes por linha (competência X(7) + 31 campos numéricos:
    4 faixas INSS + 5 IRRF + FGTS/HE + 2 faixas SF + 3 encargos RFC-014).
    Arquivo antigo/sem competência é descartado e re-seedado com as tabelas
    padrão."""
    cfg_path = os.path.join(DADOS_DIR, "folha_config.dat")
    try:
        with open(cfg_path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
        linhas = [l for l in raw.splitlines() if l.strip()]
        precisa = not linhas or any(len(l.strip()) != 230 for l in linhas)
    except OSError:
        precisa = True
    if precisa:
        # remove qualquer arquivo em layout antigo (o salvar preserva versões
        # válidas; um arquivo corrompido seria mantido junto)
        try:
            os.remove(cfg_path)
        except OSError:
            pass
        folha_config_salvar({})
    return precisa


def folha_encargos(competencia, regime=None):
    """Encargos patronais consolidados da competência (RFC-014). Calcula no
    COBOL (mesma lógica do fechamento) e retorna o JSON consolidado.
    regime: 'simples' zera INSS patronal/RAT/terceiros (DAS) no COBOL."""
    env = {"ACAO": "encargos-calcular", "COMPETENCIA": str(competencia)}
    if regime:
        env["REGIME"] = str(regime)
    out, _ = _run("folha_pagamento", env)
    _parse_saida(out)
    return _folha_json(out)


def folha_encargos_mostrar(competencia):
    """Lê o registro de encargos gravado no fechamento (sem recalcular)."""
    out, _ = _run("folha_pagamento", {"ACAO": "encargos-mostrar",
                                      "COMPETENCIA": str(competencia)})
    _parse_saida(out)
    return _folha_json(out)


def folha_abrir(competencia):
    out, _ = _run("folha_pagamento", _folha_env("folha-abrir", {"competencia": competencia}))
    _parse_saida(out)
    return "OK" in out


def folha_calcular(dados):
    out, _ = _run("folha_pagamento", _folha_env("folha-calcular", dados))
    _parse_saida(out)
    return _folha_json(out)


def folha_concluir(competencia):
    out, _ = _run("folha_pagamento", _folha_env("folha-concluir", {"competencia": competencia}))
    _parse_saida(out)
    return "OK" in out


def folha_validar(competencia):
    out, _ = _run("folha_pagamento", _folha_env("folha-validar", {"competencia": competencia}))
    _parse_saida(out)
    return "OK" in out


def folha_fechar(competencia):
    out, _ = _run("folha_pagamento", _folha_env("folha-fechar", {"competencia": competencia}))
    _parse_saida(out)
    return "OK" in out


def folha_pagar(competencia, data_pagamento):
    out, _ = _run("folha_pagamento", _folha_env("folha-pagar", {"competencia": competencia},
                                                extra={"DATA_PAGAMENTO": data_pagamento}))
    _parse_saida(out)
    return "OK" in out


def folha_listar():
    out, _ = _run("folha_pagamento", {"ACAO": "folha-listar"})
    try:
        return json.loads(out).get("competencias", [])
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (folha-listar): " + out.strip()[:200])


def folha_mostrar(competencia):
    out, _ = _run("folha_pagamento", _folha_env("folha-mostrar", {"competencia": competencia}))
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (folha-mostrar): " + out.strip()[:200])


def holerite_gerar(competencia):
    """Gera os holerites da competência a partir do processamento (RFC-007)."""
    out, _ = _run("folha_pagamento", _folha_env("holerite-gerar", {"competencia": competencia}))
    out = _parse_saida(out)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (holerite-gerar): " + out.strip()[:200])


def holerite_listar():
    out, _ = _run("folha_pagamento", {"ACAO": "holerite-listar"})
    try:
        return json.loads(out).get("holerites", [])
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (holerite-listar): " + out.strip()[:200])


def holerite_mostrar(holerite_id):
    out, _ = _run("folha_pagamento", _folha_env("holerite-mostrar", {},
                                                extra={"ID": str(holerite_id)}))
    out = _parse_saida(out)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (holerite-mostrar): " + out.strip()[:200])


def holerite_pagar(holerite_id, data_pagamento):
    out, _ = _run("folha_pagamento", _folha_env("holerite-pagar", {},
                                                extra={"ID": str(holerite_id),
                                                       "DATA_PAGAMENTO": data_pagamento or ""}))
    _parse_saida(out)
    return "OK" in out


def holerite_excluir(holerite_id):
    out, _ = _run("folha_pagamento", _folha_env("holerite-excluir", {},
                                                extra={"ID": str(holerite_id)}))
    _parse_saida(out)
    return "OK" in out


def holerite_obs(holerite_id, observacoes):
    out, _ = _run("folha_pagamento", _folha_env("holerite-obs", {},
                                                extra={"ID": str(holerite_id),
                                                       "OBSERVACOES": observacoes or ""}))
    _parse_saida(out)
    return "OK" in out


def funcionario_reativar(id_val):
    out, _ = _run("gerir_funcionarios", {"ACAO": "reativar", "ID": str(id_val)})
    _parse_saida(out)
    return "OK" in out


# ── RFC-004 — Eventos: Proventos e Descontos ───────────────

EVENTO_TIPOS = ("provento", "desconto", "informativo")

# Catálogo inicial (RFC-004 §3) — (código, descrição, tipo, categoria,
# referência, fórmula, incide INSS, incide IRRF, incide FGTS, ordem, uso)
CATALOGO_EVENTOS = [
    (1, "Salário Base", "provento", "remuneracao", "valor",
     "Valor do cadastro do funcionario (RFC-002)", "S", "S", "S", 1, "todos"),
    (2, "Horas Extras 50%", "provento", "remuneracao", "horas",
     "Valor da hora normal x quantidade x 1,50", "S", "S", "S", 2, "mensal"),
    (3, "Horas Extras 100%", "provento", "remuneracao", "horas",
     "Valor da hora normal x quantidade x 2,00 (domingos/feriados)", "S", "S", "S", 3, "mensal"),
    (4, "Adicional Noturno", "provento", "remuneracao", "percentual",
     "Percentual sobre o salario base (22h-5h)", "S", "S", "S", 4, "mensal"),
    (5, "Adicional de Insalubridade", "provento", "remuneracao", "percentual",
     "10/20/40% conforme grau (RFC-005)", "S", "S", "S", 5, "mensal"),
    (6, "Adicional de Periculosidade", "provento", "remuneracao", "percentual",
     "30% sobre o salario base", "S", "S", "S", 6, "mensal"),
    (7, "Comissão / Vendas", "provento", "remuneracao", "percentual",
     "Valor ou percentual conforme politica", "S", "S", "S", 7, "mensal"),
    (8, "DSR (Descanso Semanal)", "provento", "remuneracao", "valor",
     "Reflexo de horas extras", "S", "S", "S", 8, "mensal"),
    (9, "Salário-Família", "provento", "beneficio", "cotas",
     "Qtde de cotas conforme tabela (RFC-005)", "N", "N", "N", 9, "mensal"),
    (10, "Férias + 1/3", "provento", "remuneracao", "periodo",
     "Em competencia de ferias (1/3 constitucional)", "S", "S", "S", 10, "ferias"),
    (20, "INSS", "desconto", "encargo", "automatica",
     "Tabela progressiva (RFC-005)", "N", "N", "N", 20, "todos"),
    (21, "IRRF", "desconto", "encargo", "automatica",
     "Tabela progressiva (RFC-005)", "N", "N", "N", 21, "todos"),
    (22, "Vale-Transporte", "desconto", "beneficio", "percentual",
     "6% do salario base, limitado ao custo real do transporte (teto no evento)",
     "N", "N", "N", 22, "mensal"),
    (23, "Vale-Refeição", "desconto", "beneficio", "percentual",
     "Valor ou % de participacao", "N", "N", "N", 23, "mensal"),
    (24, "Plano de Saúde", "desconto", "beneficio", "valor",
     "Valor da coparticipacao", "N", "N", "N", 24, "mensal"),
    (25, "Faltas / Atrasos", "desconto", "remuneracao", "dias",
     "Desconto sobre o valor do dia/hora", "N", "N", "N", 25, "mensal"),
    (26, "Adiantamento", "desconto", "remuneracao", "valor",
     "Desconto do adiantamento feito", "N", "N", "N", 26, "mensal"),
    (27, "Pensão Alimentícia", "desconto", "remuneracao", "percentual",
     "% ou valor fixo conforme decisao judicial", "N", "N", "N", 27, "mensal"),
    (28, "Contribuição Sindical", "desconto", "encargo", "valor",
     "Valor quando aplicavel", "N", "N", "N", 28, "mensal"),
]

_EVENTO_FIELD_MAP = {
    "codigo": "CODIGO",
    "descricao": "DESCRICAO",
    "tipo": "TIPO",
    "categoria": "CATEGORIA",
    "referencia": "REFERENCIA",
    "formula": "FORMULA",
    "incide_inss": "INCIDE_INSS",
    "incide_irrf": "INCIDE_IRRF",
    "incide_fgts": "INCIDE_FGTS",
    "ordem": "ORDEM",
    "uso": "USO",
    "teto": "TETO",
    "status": "STATUS",
}


def _evento_env(acao, dados, id_val=None):
    env = {"ACAO": acao}
    for field, var in _EVENTO_FIELD_MAP.items():
        val = dados.get(field)
        if val is not None and val != "":
            env[var] = str(val)
    if id_val not in (None, ""):
        env["ID"] = str(id_val)
    return env


def eventos_listar(ativos_only=False):
    env = {"ACAO": "listar-ativos" if ativos_only else "listar"}
    out, _ = _run("gerir_eventos", env)
    try:
        return json.loads(out).get("eventos", [])
    except json.JSONDecodeError:
        raise Exception("Saída inesperada do COBOL (eventos): " + out.strip()[:200])


def evento_incluir(dados):
    out, _ = _run("gerir_eventos", _evento_env("incluir", dados))
    _parse_saida(out)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao criar evento: " + out.strip())


def evento_alterar(id_val, dados):
    out, _ = _run("gerir_eventos", _evento_env("alterar", dados, id_val))
    _parse_saida(out)
    return "OK" in out


def evento_excluir(id_val):
    out, _ = _run("gerir_eventos", {"ACAO": "excluir", "ID": str(id_val)})
    _parse_saida(out)
    return "OK" in out


def eventos_seed_catalogo():
    """Garante o catálogo inicial do RFC-004 §3 (idempotente).

    Só inclui os códigos ainda não presentes como ativos. Códigos
    inativados podem ser recriados (a validação COBOL permite código
    duplicado apenas entre ativos).
    """
    existentes = {int(e.get("codigo")) for e in eventos_listar()
                  if (e.get("status") or "") == "ativo"}
    criados = []
    for cod, desc, tipo, cat, ref, form, iinss, iirrf, ifgts, ordem, uso in CATALOGO_EVENTOS:
        if cod in existentes:
            continue
        evento_incluir({
            "codigo": cod,
            "descricao": desc,
            "tipo": tipo,
            "categoria": cat,
            "referencia": ref,
            "formula": form,
            "incide_inss": iinss,
            "incide_irrf": iirrf,
            "incide_fgts": ifgts,
            "ordem": ordem,
            "uso": uso,
            "teto": 0,
        })
        criados.append(cod)
    return criados


def filiais_listar():
    out, _ = _run("gerir_filiais", {"ACAO": "listar"})
    try:
        return json.loads(out).get("filiais", [])
    except json.JSONDecodeError:
        return []


def filiais_incluir(dados):
    env = {"ACAO": "incluir",
           "NOME": dados.get("nome", ""),
           "ENDERECO": dados.get("endereco", ""),
           "RESPONSAVEL": dados.get("responsavel", ""),
           "EMPRESA_ID": dados.get("empresa_id", "")}
    out, _ = _run("gerir_filiais", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao criar filial: " + out.strip())


def filiais_alterar(id_val, dados):
    env = {"ACAO": "alterar",
           "ID": str(id_val),
           "NOME": dados.get("nome", ""),
           "ENDERECO": dados.get("endereco", ""),
           "RESPONSAVEL": dados.get("responsavel", ""),
           "EMPRESA_ID": dados.get("empresa_id", "")}
    out, _ = _run("gerir_filiais", env)
    return "OK" in out


def filiais_excluir(id_val):
    out, _ = _run("gerir_filiais", {"ACAO": "excluir", "ID": str(id_val)})
    return "OK" in out


def dependentes_listar(funcionario_id=None):
    env = {"ACAO": "listar-por-func"}
    if funcionario_id not in (None, ""):
        env["FUNCIONARIO_ID"] = str(funcionario_id)
    out, _ = _run("dependentes", env)
    try:
        return json.loads(out).get("dependentes", [])
    except json.JSONDecodeError:
        return []


def dependente_incluir(dados):
    env = {"ACAO": "incluir", "NOME": dados.get("nome", ""),
           "CPF": dados.get("cpf", ""), "DATA_NASC": dados.get("data_nasc", ""),
           "TIPO": dados.get("tipo", ""),
           "GRAU_PARENTESCO": dados.get("grau_parentesco", ""),
           "TIPO_IRRF": dados.get("irrf", ""),
           "TIPO_SAL_FAMILIA": dados.get("sal_familia", "")}
    if dados.get("funcionario_id") not in (None, ""):
        env["FUNCIONARIO_ID"] = str(dados.get("funcionario_id"))
    out, _ = _run("dependentes", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao criar dependente: " + out.strip())


def dependente_alterar(id_val, dados):
    env = {"ACAO": "alterar", "ID": str(id_val),
           "NOME": dados.get("nome", ""),
           "CPF": dados.get("cpf", ""), "DATA_NASC": dados.get("data_nasc", ""),
           "TIPO": dados.get("tipo", ""),
           "GRAU_PARENTESCO": dados.get("grau_parentesco", ""),
           "TIPO_IRRF": dados.get("irrf", ""),
           "TIPO_SAL_FAMILIA": dados.get("sal_familia", "")}
    if dados.get("funcionario_id") not in (None, ""):
        env["FUNCIONARIO_ID"] = str(dados.get("funcionario_id"))
    out, _ = _run("dependentes", env)
    return "OK" in out


def dependente_excluir(id_val):
    out, _ = _run("dependentes", {"ACAO": "excluir", "ID": str(id_val)})
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
    "qtd_min_compra", "qtd_padrao", "lead_time", "garantia", "validade_dias",
    "peso_liq", "peso_bruto", "tipo_embalagem", "embalagem_outro", "qtd_por_embalagem",
    "altura", "largura", "comprimento", "volume",
    "altura_emb", "largura_emb", "comprimento_emb", "volume_emb", "foto",
    "available_at", "alugavel",
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
    jsonio.save(PRODUTOS_EXTRA_FILE, data)


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


def produto_visivel_no_estabelecimento(produto, estabelecimento_id):
    """
    Escopo de catálogo (RFC):
    - available_at vazio / ausente → todas as filiais
    - available_at lista → só esses estabelecimentos
    - legado: filial_id 0/ausente = todas; senão compara com estabelecimento_id
    - pdv=false → fora do POS
    """
    if not isinstance(produto, dict):
        return False
    if produto.get("pdv") is False:
        return False
    if produto.get("vendavel") is False:
        return False
    if produto.get("ativo") is False:
        return False
    eid = str(estabelecimento_id or "").strip()
    if not eid:
        return True

    avail = produto.get("available_at")
    if isinstance(avail, str):
        avail = [x.strip() for x in avail.split(",") if x.strip()]
    if isinstance(avail, list):
        if len(avail) == 0:
            return True
        return eid in {str(x).strip() for x in avail}

    fid = produto.get("filial_id")
    if fid in (None, "", 0, "0"):
        return True
    return str(fid) == eid


def produtos_para_pos(estabelecimento_id=None):
    produtos = produtos_listar()
    if not estabelecimento_id:
        return [p for p in produtos if p.get("pdv") is not False and p.get("vendavel") is not False]
    return [
        p for p in produtos
        if produto_visivel_no_estabelecimento(p, estabelecimento_id)
    ]


def produto_vendavel_b2b(produto, estabelecimento_id=None):
    """
    Catálogo B2B: vendável + ativo + escopo de estabelecimento.
    Não exige pdv=true (produto pode ser só atacado).
    """
    if not isinstance(produto, dict):
        return False
    if produto.get("vendavel") is False:
        return False
    if produto.get("ativo") is False:
        return False
    eid = str(estabelecimento_id or "").strip()
    if not eid:
        return True
    avail = produto.get("available_at")
    if isinstance(avail, str):
        avail = [x.strip() for x in avail.split(",") if x.strip()]
    if isinstance(avail, list):
        if len(avail) == 0:
            return True
        return eid in {str(x).strip() for x in avail}
    fid = produto.get("filial_id")
    if fid in (None, "", 0, "0"):
        return True
    return str(fid) == eid


def produtos_para_vendas(estabelecimento_id=None):
    """Produtos elegíveis para Sales B2B (filtro alinhado ao POS, sem exigir PDV)."""
    return [
        p for p in produtos_listar()
        if produto_vendavel_b2b(p, estabelecimento_id)
    ]

def _validar_produto(dados, obrigatorios=True, flexivel=False):
    """Valida preço/NCM/CFOP.

    - Inclusão (obrigatorios=True): preço e NCM são obrigatórios.
    - Edição (obrigatorios=False): valida apenas os campos presentes no payload.
    - Importação (flexivel=True): dados vindos de NF-e já validada pela SEFAZ
      não travam o cadastro — aceita preço 0 (bonificação) e NCM ausente.
      Formato continua validado quando houver valor.
    - CFOP é sempre OPCIONAL: é contextual (compra/venda) e, na importação
      de NF-e de fornecedor via XML, vem da nota, não do cadastro do produto.
      Quando informado, o formato é validado (4 dígitos).
    """
    if not isinstance(dados, dict):
        raise ValueError("ERRO: dados invalidos")

    # Preço: numérico e > 0 (flexivel aceita 0, ex.: bonificação na importação)
    if obrigatorios or "preco" in dados:
        preco = dados.get("preco")
        if preco in (None, ""):
            if not flexivel:
                raise ValueError("ERRO: preco obrigatorio")
        else:
            try:
                preco_num = float(str(preco).replace(",", ".").strip())
            except (TypeError, ValueError):
                raise ValueError("ERRO: preco deve ser numerico")
            if preco_num <= 0 and not flexivel:
                raise ValueError("ERRO: preco deve ser maior que zero")

    # NCM: exatamente 8 dígitos quando informado (obrigatório na inclusão).
    # No modo flexível (importação NF-e), NCM ausente OU curto é aceito —
    # a nota já passou pela validação da SEFAZ e não deve travar o cadastro.
    if obrigatorios or "ncm" in dados:
        ncm = re.sub(r"\D", "", str(dados.get("ncm", "")))
        if not ncm:
            if not flexivel:
                raise ValueError("ERRO: NCM obrigatorio")
        elif len(ncm) != 8 and not flexivel:
            raise ValueError("ERRO: NCM deve ter 8 digitos")

    # CFOP: OPCIONAL (contextual compra/venda; na importação de NF-e via XML
    # vem da nota). Quando informado, exige 4 dígitos.
    cfop = str(dados.get("cfop", "") or "").strip()
    if cfop and not re.fullmatch(r"\d{4}", cfop):
        raise ValueError("ERRO: CFOP deve ter 4 digitos")


def produtos_incluir(dados, importacao=False):
    _validar_produto(dados, obrigatorios=not importacao, flexivel=importacao)
    extra = _extract_produto_extra(dados)
    env = {
        "ACAO": "incluir",
        "NOME": dados.get("nome", ""),
        "PRECO": str(dados.get("preco", 0)),
        "PRECO_CUSTO": str(dados.get("preco_custo", 0)),
        "STOCK": str(dados.get("stock", 0)),
        "MARGEM": str(dados.get("margem", 0)),
        "ATIVO": "S" if dados.get("ativo", True) not in (False, "N", "n", 0, "0") else "N",
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
    if dados.get("id") not in (None, ""):
        env["ID"] = str(dados.get("id"))
    out, _ = _run("cadastrar_produto", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            pid = int(line)
            if extra:
                produtos_extra_set(pid, extra)
                # Sincronizar variantes inline com COBOL variantes.dat
                vars_raw = extra.get("variacoes") or []
                if vars_raw:
                    sync_variantes_for_produto(
                        pid, vars_raw, dados.get("preco", 0))
            return pid
    raise Exception("Erro ao criar produto: " + out.strip())

def produtos_alterar(id_val, dados):
    _validar_produto(dados, obrigatorios=False)
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
    if "ativo" in dados:
        env["ATIVO"] = (
            "N"
            if dados.get("ativo") in (False, "", "N", "n", 0, "0", None)
            else "S"
        )
    out, _ = _run("cadastrar_produto", env)
    ok = "OK" in out
    if ok and extra:
        produtos_extra_set(id_val, extra)
        # Sincronizar variantes inline com COBOL variantes.dat
        vars_raw = extra.get("variacoes") or []
        if vars_raw:
            sync_variantes_for_produto(
                id_val, vars_raw, dados.get("preco", 0))
        else:
            # Sem variantes no form — desativar todas no COBOL
            for v in variantes_listar_por_produto(id_val):
                if v.get("ativo", True):
                    try:
                        variantes_alterar(v["id"], {"ativo": False})
                    except Exception:
                        pass
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

# ── Contas a Receber (CRUD COBOL — fonte da verdade) ────────

def titulos_ar_listar():
    """Lista títulos do .dat COBOL (JSON stdout)."""
    out, _ = _run("gerir_titulos_ar", {"ACAO": "listar"})
    # stdout pode ter linhas; junta e extrai o objeto JSON
    text = (out or "").strip()
    try:
        # listar emite várias DISPLAY; reconstruir
        start = text.find('{"titulos":')
        if start < 0:
            return []
        data = json.loads(text[start:])
        return data.get("titulos") or []
    except json.JSONDecodeError:
        # fallback: parse linha a linha se quebrado
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("{") and '"id"' in line and not line.startswith('{"titulos"'):
                try:
                    rows.append(json.loads(line.rstrip(",")))
                except json.JSONDecodeError:
                    pass
        return rows


def titulos_ar_incluir(dados):
    env = {
        "ACAO": "incluir",
        "ID": str(dados.get("id") or ""),
        "PARTNER_ID": str(dados.get("partner_id") or ""),
        "CLIENTE": str(dados.get("cliente") or "")[:60],
        "CNPJ": str(dados.get("cnpj") or "")[:18],
        "PEDIDO_ID": str(dados.get("pedido_id") or "")[:10],
        "PEDIDO_NUM": str(dados.get("pedido_numero") or "")[:12],
        "FATURA_ID": str(dados.get("fatura_id") or "")[:10],
        "FATURA_NUM": str(dados.get("fatura_numero") or "")[:12],
        "PARCELA": str(dados.get("parcela") or 1),
        "PARCELAS": str(dados.get("parcelas") or 1),
        "VALOR": str(dados.get("valor") or "0"),
        "VENCIMENTO": str(dados.get("vencimento") or "")[:10],
        "PAYMENT_TERMS": str(dados.get("payment_terms") or "")[:20],
        "USUARIO": str(dados.get("usuario") or "")[:30],
    }
    out, err = _run("gerir_titulos_ar", env)
    for line in (out or "").splitlines():
        line = line.strip()
        if line.startswith("AR-"):
            return line
        if line.startswith("ERRO:"):
            raise Exception(line)
    raise Exception("Erro ao criar título AR: " + (out or err or "").strip())


def titulos_ar_baixar(titulo_id, valor=None, usuario=""):
    env = {
        "ACAO": "baixar",
        "ID": str(titulo_id or "").strip(),
        "USUARIO": str(usuario or "")[:30],
    }
    if valor is not None:
        env["VALOR"] = str(valor)
    out, err = _run("gerir_titulos_ar", env)
    text = (out or "").strip()
    if "ERRO:" in text:
        raise Exception(next((l for l in text.splitlines() if "ERRO:" in l), text))
    # última linha JSON do título
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and '"id"' in line:
            return json.loads(line)
    raise Exception("Baixa sem retorno: " + text)


def titulos_ar_sync_json():
    """Projeção JSON para consultas/relatórios (não é fonte da verdade)."""
    rows = titulos_ar_listar()
    path = os.path.join(DADOS_DIR, "sales_ar.json")
    payload = {
        "titulos": rows,
        "total": len(rows),
        "source": "cobol:titulos_ar.dat",
        "atualizado_em": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    jsonio.save(path, payload)
    return payload


# ── Departamentos (RFC-008 §3) ──────────────────────────────

def departamentos_listar(ativos_only=False):
    env = {"ACAO": "listar-ativos" if ativos_only else "listar"}
    out, _ = _run("gerir_departamentos", env)
    try:
        return json.loads(out).get("departamentos", [])
    except json.JSONDecodeError:
        return []


def departamento_incluir(dados):
    env = {
        "ACAO": "incluir",
        "CODIGO": dados.get("codigo", ""),
        "DESCRICAO": dados.get("descricao", ""),
        "CENTRO_CUSTO": dados.get("centro_custo", ""),
        "RESPONSAVEL": dados.get("responsavel", ""),
    }
    out, _ = _run("gerir_departamentos", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao criar departamento: " + out.strip())


def departamento_alterar(id_val, dados):
    env = {
        "ACAO": "alterar",
        "ID": str(id_val),
        "CODIGO": dados.get("codigo", ""),
        "DESCRICAO": dados.get("descricao", ""),
        "CENTRO_CUSTO": dados.get("centro_custo", ""),
        "RESPONSAVEL": dados.get("responsavel", ""),
        "STATUS": dados.get("status", ""),
    }
    out, _ = _run("gerir_departamentos", env)
    return "OK" in out


def departamento_excluir(id_val):
    # Inativação lógica (RFC-008 decisão 4 — nunca exclusão física)
    out, _ = _run("gerir_departamentos", {"ACAO": "excluir", "ID": str(id_val)})
    return "OK" in out


# ── Cargos (RFC-008 §4) ──────────────────────────────────────

def cargos_listar(ativos_only=False):
    env = {"ACAO": "listar-ativos" if ativos_only else "listar"}
    out, _ = _run("gerir_cargos", env)
    try:
        return json.loads(out).get("cargos", [])
    except json.JSONDecodeError:
        return []


def cargo_incluir(dados):
    env = {
        "ACAO": "incluir",
        "CODIGO": dados.get("codigo", ""),
        "DESCRICAO": dados.get("descricao", ""),
        "CBO": dados.get("cbo", ""),
        "SALARIO_REFERENCIA": dados.get("salario_referencia", ""),
    }
    out, _ = _run("gerir_cargos", env)
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    raise Exception("Erro ao criar cargo: " + out.strip())


def cargo_alterar(id_val, dados):
    env = {
        "ACAO": "alterar",
        "ID": str(id_val),
        "CODIGO": dados.get("codigo", ""),
        "DESCRICAO": dados.get("descricao", ""),
        "CBO": dados.get("cbo", ""),
        "SALARIO_REFERENCIA": dados.get("salario_referencia", ""),
        "STATUS": dados.get("status", ""),
    }
    out, _ = _run("gerir_cargos", env)
    return "OK" in out


def cargo_excluir(id_val):
    # Inativação lógica (RFC-008 decisão 4 — nunca exclusão física)
    out, _ = _run("gerir_cargos", {"ACAO": "excluir", "ID": str(id_val)})
    return "OK" in out


# ── Utilitários ──────────────────────────────────────────────

def sync_json():
    for prog in ["batch_json_produtos", "batch_json_fornecedores", "batch_json_vendas", "batch_json_numeracao"]:
        try:
            _compile_if_needed(prog)
            _run(prog, {})
        except Exception:
            pass
    try:
        titulos_ar_sync_json()
    except Exception:
        pass
    return {"synced": True}

# ── Localizações WMS (gerir_localizacoes.cbl) ────────────────────────────
# Fonte da verdade: dados/localizacoes.dat (programa COBOL). Isolamento em
# testes via env vars LOCALIZACOES_DAT / LOCALIZACOES_TMP.

_LOC_FIELD_MAP = {
    "capacidade_qtd": "CAPACIDADE",
    "peso_max_kg": "PESO_MAX",
    "volume_max_m3": "VOLUME_MAX",
    "bloqueio_motivo": "BLOQUEIO",
    "atualizado_em": "ATUALIZADO",
}


def _loc_env(acao, dados):
    env = {"ACAO": acao}
    for key, val in (dados or {}).items():
        ekey = _LOC_FIELD_MAP.get(key, str(key).upper())
        env[ekey] = "" if val is None else str(val)
    return env


def _loc_check(out):
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    err = next((l for l in lines if l.startswith("ERRO:")), None)
    if err:
        raise ValueError(err)
    return lines[-1] if lines else ""


def localizacoes_listar():
    out, _ = _run("gerir_localizacoes", {"ACAO": "listar"})
    try:
        data = json.loads(out)
        return data.get("localizacoes", [])
    except json.JSONDecodeError:
        return []


def localizacoes_buscar(codigo):
    out, _ = _run("gerir_localizacoes", _loc_env("buscar", {"codigo": codigo}))
    try:
        data = json.loads(out)
        return data if data.get("status") != "erro" else None
    except json.JSONDecodeError:
        return None


def localizacoes_incluir(dados):
    out, _ = _run("gerir_localizacoes", _loc_env("incluir", dados))
    return _loc_check(out)


def localizacoes_alterar(dados):
    out, _ = _run("gerir_localizacoes", _loc_env("alterar", dados))
    return _loc_check(out)


def localizacoes_excluir(codigo):
    out, _ = _run("gerir_localizacoes", _loc_env("excluir", {"codigo": codigo}))
    return _loc_check(out)
