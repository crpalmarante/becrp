"""CobolBridge — Ponte Python para programas COBOL do FiscalBrasil ERP"""

import json
import jsonio
import os
import re
import subprocess
import sys
import threading
import uuid

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
        "TELEFONE": dados.get("telefone", ""),
        "EMAIL": dados.get("email", ""),
        "IE": dados.get("ie", ""),
        "INSCRICAO_MUN": dados.get("inscricao_mun", ""),
    }
    if dados.get("id") not in (None, ""):
        env["ID"] = str(dados.get("id"))
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

# ── Funcionários ────────────────────────────────────────────

_FUNCIONARIO_ENV_KEYS = [
    "NOME", "USUARIO", "SENHA", "PERMISSOES", "CPF", "RG", "DATA_NASC",
    "CELULAR", "EMAIL", "ENDERECO", "DATA_ADM", "DATA_DEM", "SALARIO",
    "FILIAL_ID", "TRAB_SAB", "TRAB_DOM",
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


def folha_config_ler():
    out, _ = _run("folha_pagamento", {"ACAO": "config-ler"})
    return _folha_json(out)


def folha_config_salvar(dados):
    env = {"ACAO": "config-salvar"}
    for k, v in CONFIG_DEFAULTS.items():
        val = dados.get(k)
        env[k.upper()] = str(val if val is not None else v)
    out, _ = _run("folha_pagamento", env)
    _parse_saida(out)
    return True


def folha_config_seed():
    """Garante o arquivo dados/folha_config.dat no layout atual (idempotente)."""
    cfg_path = os.path.join(DADOS_DIR, "folha_config.dat")
    # o arquivo é só dígitos (sem labels): detectar layout antigo pelo tamanho
    # (novo = 179 bytes; antigo = 131). Nunca regravar config já no layout novo.
    try:
        with open(cfg_path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
        precisa = len(raw.strip()) < 170
    except OSError:
        precisa = True
    if precisa:
        folha_config_salvar({})
    return precisa


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
    "qtd_min_compra", "qtd_padrao", "lead_time", "garantia",
    "peso_liq", "peso_bruto", "tipo_embalagem", "embalagem_outro", "qtd_por_embalagem",
    "altura", "largura", "comprimento", "volume",
    "altura_emb", "largura_emb", "comprimento_emb", "volume_emb", "foto",
    "available_at",
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

def produtos_incluir(dados):
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
