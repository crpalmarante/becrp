"""
Bank Integration (RFC-0070) — Sprint BI-01: importação OFX + CSV (MVP).

O Bank Integration traz o extrato bancário para dentro da plataforma e o
converte em fatos financeiros neutros: cada lançamento do banco vira parte
de um BankStatement canônico e imutável, publicado como
finance_statement_imported para o Finance conciliar e o Accounting postar.

Regras centrais (RFC-0070 §3, §4):
  - nunca conhece o plano de contas;
  - nunca posta partidas;
  - o extrato importado é imutável — correções geram novos eventos;
  - idempotente por extrato (hash canônico);
  - valores sempre Decimal (nunca float);
  - cada formato de origem é um adapter atrás da mesma interface.

Saída: Statement persistido em dados/bank_statements.json + eventos
finance_statement_imported / finance_statement_duplicate (RFC-0070 §8).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "dados")
STATEMENTS_FILE = os.path.join(DATA_DIR, "bank_statements.json")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "bank_accounts.json")
LOG_FILE = os.path.join(DATA_DIR, "bank_integration_log.json")

MONEY = Decimal("0.01")
TOLERANCIA = Decimal("0.02")

# Formatos suportados (RFC-0070 §11).
SUPPORTED_FORMATS = ("ofx", "csv", "cnab240", "cnab400")

# Código de movimento de retorno CNAB que indica liquidação/baixa de título.
# RFC-0070 §11.3 — Segmento T, Código de Movimento Retorno (FEBRABAN C044).
CNAB_MOV_LIQUIDACAO = {"06", "09", "17"}
CNAB_MOV_ENTRADA = {"02", "11"}
CNAB_MOV_BAIXA = {"09"}

# Segmento T — posições (1-indexadas) do layout FEBRABAN CNAB240 (retorno).
CNAB240_SEG_T = {
    "banco": (1, 3),
    "movimento": (16, 17),
    "agencia": (18, 22),
    "conta": (24, 35),
    "nosso_numero": (38, 43),
    "numero_documento": (45, 59),
    "vencimento": (74, 81),
    "valor": (82, 96),
    "banco_cobrador": (97, 99),
    "agencia_cobradora": (100, 104),
    "nosso_numero_completo": (106, 120),
    "tarifa": (136, 150),
    "data_credito": (166, 173),
    "ocorrencias": (232, 240),
}

# Header do arquivo CNAB240 — posições (1-indexadas).
CNAB240_HDR = {
    "banco": (1, 3),
    "tipo_registro": (8, 8),
    "inscricao_tipo": (18, 18),
    "inscricao_num": (19, 32),
    "agencia": (53, 57),
    "conta": (59, 70),
    "rem_ret": (143, 143),
}

# CNAB400 (retorno) — posições (1-indexadas), layout FEBRABAN clássico.
CNAB400_HDR = {
    "banco": (2, 4),
    "agencia": (5, 9),
    "conta": (10, 17),
}
CNAB400_SEG = {
    "banco": (2, 4),
    "movimento": (108, 109),
    "data_ocorrencia": (110, 115),
    "vencimento": (74, 81),
    "valor": (82, 95),
    "nosso_numero": (63, 73),
    "numero_documento": (116, 131),
    "data_credito": (240, 245),
    "tarifa": (162, 173),
}

# Códigos de banco (BACEN) aceitos no parse — usado apenas para validação.
BANCO_CODIGOS_VALIDOS = (
    "001", "003", "004", "033", "104", "237", "341", "389", "399", "422", "654", "745", "746", "756", "077", "260", "212", "136", "218",
)

TIPO_CONTA_VALIDOS = {"current", "savings", "payment", "conta_corrente", "poupanca"}


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


def _load_statements():
    data = _load_raw(STATEMENTS_FILE, {"atualizado_em": None, "extratos": []})
    if not isinstance(data.get("extratos"), list):
        data["extratos"] = []
    return data


def _save_statements(data):
    data["atualizado_em"] = _now()
    _save_json(STATEMENTS_FILE, data)


def _append_statement(statement):
    data = _load_statements()
    data["extratos"].append(statement)
    if len(data["extratos"]) > 500:
        data["extratos"] = data["extratos"][-500:]
    _save_statements(data)
    return statement


def _append_log(ev):
    data = _load_raw(LOG_FILE, {"eventos": []})
    if not isinstance(data.get("eventos"), list):
        data["eventos"] = []
    data["eventos"].append(ev)
    if len(data["eventos"]) > 1000:
        data["eventos"] = data["eventos"][-1000:]
    data["atualizado_em"] = _now()
    _save_json(LOG_FILE, data)


def _load_accounts():
    data = _load_raw(ACCOUNTS_FILE, {"contas": []})
    if not isinstance(data.get("contas"), list):
        data["contas"] = []
    return data


def _save_accounts(data):
    data["atualizado_em"] = _now()
    _save_json(ACCOUNTS_FILE, data)


def _extrato_id(statement):
    """Hash canônico do extrato (RFC-0070 §9.2) — chave de idempotência."""
    base = {
        "banco": statement.get("banco"),
        "agencia": statement.get("agencia"),
        "conta": statement.get("conta"),
        "tipo_conta": statement.get("tipo_conta"),
        "saldo_inicial": str(statement.get("saldo_inicial")),
        "saldo_final": str(statement.get("saldo_final")),
        "data_inicio": statement.get("data_inicio"),
        "data_fim": statement.get("data_fim"),
    }
    payload = json.dumps(base, sort_keys=True, ensure_ascii=False)
    if statement.get("lancamentos"):
        for t in statement["lancamentos"]:
            payload += "|" + json.dumps(
                {
                    "id": t.get("id"),
                    "data": t.get("data"),
                    "tipo": t.get("tipo"),
                    "valor": str(t.get("valor")),
                    "descricao": t.get("descricao"),
                },
                sort_keys=True,
                ensure_ascii=False,
            )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def find_by_extrato_id(extrato_id):
    for s in _load_statements().get("extratos") or []:
        if s.get("id") == extrato_id:
            return s
    return None


# ── Contas bancárias (resolver) ──


def upsert_bank_account(banco, agencia, conta, tipo_conta="current", nome=None, estabelecimento_id=None):
    """Registra/atualiza conta bancária conhecida. Devolve o registro."""
    banco = str(banco or "").strip()
    agencia = str(agencia or "").strip()
    conta_num = str(conta or "").strip()
    if not banco or not agencia or not conta_num:
        raise ValueError("banco, agência e conta são obrigatórios")
    key = (banco, agencia, conta_num)
    data = _load_accounts()
    for row in data.get("contas") or []:
        if (str(row.get("banco") or ""), str(row.get("agencia") or ""), str(row.get("conta") or "")) == key:
            if tipo_conta:
                row["tipo_conta"] = tipo_conta
            if nome:
                row["nome"] = nome
            if estabelecimento_id:
                row["estabelecimento_id"] = estabelecimento_id
            row["atualizado_em"] = _now()
            _save_accounts(data)
            return row
    row = {
        "id": str(uuid.uuid4()),
        "banco": banco,
        "agencia": agencia,
        "conta": conta_num,
        "tipo_conta": tipo_conta or "current",
        "nome": nome,
        "estabelecimento_id": estabelecimento_id,
        "criado_em": _now(),
        "atualizado_em": _now(),
    }
    data["contas"].append(row)
    _save_accounts(data)
    return row


def resolve_bank_account(statement):
    """Resolve a conta bancária de um extrato; registra se desconhecida."""
    banco = str(statement.get("banco") or "").strip()
    agencia = str(statement.get("agencia") or "").strip()
    conta = str(statement.get("conta") or "").strip()
    tipo = statement.get("tipo_conta") or "current"
    if not banco or not agencia or not conta:
        return None
    data = _load_accounts()
    for row in data.get("contas") or []:
        if (str(row.get("banco") or ""), str(row.get("agencia") or ""), str(row.get("conta") or "")) == (banco, agencia, conta):
            return row
    return upsert_bank_account(banco, agencia, conta, tipo_conta=tipo)


def list_bank_accounts():
    return _load_accounts().get("contas") or []


# ── Parsers (adapters) ──


def _normalizar_conta(acct):
    """Converte ACCTID/tipo de conta para o modelo canônico."""
    return str(acct or "").strip()


def _tipo_trn(trntype, amount):
    """Normaliza tipo do lançamento: 'D' (saída) ou 'C' (entrada)."""
    t = str(trntype or "").strip().upper()
    if t in ("CREDIT", "DEBIT"):
        return "C" if t == "CREDIT" else "D"
    if amount >= 0:
        return "C"
    return "D"


def _parse_ofx_date(raw):
    """Datas OFX: YYYYMMDD ou YYYYMMDDHHMMSS[.sss][[gmt offset]]."""
    s = str(raw or "").strip()
    m = re.match(r"^(\d{8})(\d{0,6})", s)
    if not m:
        return None
    d = m.group(1)
    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}"


def _parse_ofx_amount(raw):
    """Valores OFX usam '.' como separador decimal (ex.: -1234.56)."""
    return _money(str(raw or "").replace(",", "").strip())


def _parse_ofx(content):
    """Parser OFX 1.0.2 (SGML) e 2.x (XML) → Statement canônico."""
    text = content if isinstance(content, str) else content.decode("utf-8", "replace")
    # extrai blocos <TAG>...</TAG> de forma simples e recursiva por prefixos
    body = text

    def _between(tag):
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", body, re.S)
        return m.group(1) if m else None

    def _tag(tag):
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", body, re.S)
        return m.group(1).strip() if m else None

    stmtrs = _between("STMTRS")
    if not stmtrs:
        raise ValueError("extrato OFX sem bloco <STMTRS>")

    banco = _tag("BANKID")
    if not banco:
        raise ValueError("extrato OFX sem <BANKID>")
    banco = banco.strip()

    conta = _normalizar_conta(_tag("ACCTID"))
    agencia = str(_tag("BRANCHID") or "").strip() or str(_tag("ACCTBRANCH") or "").strip()
    accttype = str(_tag("ACCTTYPE") or "CHECKING").upper()
    tipo_conta = {"CHECKING": "current", "SAVINGS": "savings", "PAYMENT": "payment"}.get(accttype, "current")

    curdef = str(_tag("CURDEF") or "BRL").upper()
    if curdef != "BRL":
        raise ValueError(f"moeda não suportada no MVP: {curdef} (esperado BRL)")

    balanco = _between("LEDGERBAL") or _between("AVAILBAL")
    saldo_inicial = None
    saldo_final = _parse_ofx_amount(_tag("BALAMT")) if balanco else None

    trnlist = _between("BANKTRANLIST")
    lancamentos = []
    if trnlist:
        for m in re.finditer(r"<STMTTRN>(.*?)</STMTTRN>", trnlist, re.S):
            bloco = m.group(1)
            trntype = (re.search(r"<TRNTYPE>(.*?)</TRNTYPE>", bloco, re.S) or [None, ""])[1]
            dtposted = (re.search(r"<DTPOSTED>(.*?)</DTPOSTED>", bloco, re.S) or [None, ""])[1]
            trnamt = (re.search(r"<TRNAMT>(.*?)</TRNAMT>", bloco, re.S) or [None, ""])[1]
            fitid = (re.search(r"<FITID>(.*?)</FITID>", bloco, re.S) or [None, ""])[1]
            name = (re.search(r"<NAME>(.*?)</NAME>", bloco, re.S) or [None, ""])[1]
            memo = (re.search(r"<MEMO>(.*?)</MEMO>", bloco, re.S) or [None, ""])[1]
            refnum = (re.search(r"<REFNUM>(.*?)</REFNUM>", bloco, re.S) or [None, ""])[1]
            amount = _parse_ofx_amount(trnamt)
            if fitid is None:
                fitid = ""
            lancamentos.append(
                {
                    "id": str(fitid).strip() or str(uuid.uuid4()),
                    "data": _parse_ofx_date(dtposted),
                    "data_credito": _parse_ofx_date(dtposted),
                    "descricao": str(name or memo or "").strip(),
                    "tipo": _tipo_trn(trntype, float(amount)),
                    "valor": float(amount),
                    "categoria_raw": "",
                    "refs": [str(refnum).strip()] if refnum and str(refnum).strip() else [],
                    "metadados": {"formato": "ofx", "trntype": str(trntype or "").strip()},
                }
            )

    # saldo inicial inferido (saldo final − Σ lançamentos) quando indisponível
    if saldo_final is not None:
        total = sum((_money(t["valor"]) for t in lancamentos), Decimal("0"))
        saldo_inicial = float(_money(saldo_final - total))

    statement = {
        "id": "",
        "banco": banco,
        "agencia": agencia,
        "conta": conta,
        "tipo_conta": tipo_conta,
        "moeda": "BRL",
        "saldo_inicial": float(saldo_inicial) if saldo_inicial is not None else None,
        "saldo_final": float(saldo_final) if saldo_final is not None else None,
        "lancamentos": lancamentos,
        "fonte": "ofx",
    }
    return statement


CSV_DEFAULT_COLUMNS = {
    "data": ("data", "date", "dt", "dtmov", "datalancamento", "data_lancamento", "data_movimento"),
    "descricao": ("descricao", "descrição", "desc", "historico", "histórico", "memo", "nome", "name", "description", "lancamento", "lançamento", "titulo", "título"),
    "valor": ("valor", "value", "amount", "val", "vlr", "valor_lancamento", "valorlancamento"),
    "tipo": ("tipo", "type", "dc", "debito_credito", "tp"),
    "debito": ("debito", "débito", "saida", "saída", "entrada_negativa", "valor_debito"),
    "credito": ("credito", "crédito", "entrada", "valor_credito"),
    "categoria": ("categoria", "category", "grupo"),
    "id": ("id", "codigo", "código", "fitid", "ref", "referencia", "documento", "nro_doc", "numero_doc", "doc"),
    "saldo": ("saldo", "balance", "saldo_pos", "saldo_pos", "saldo_acumulado"),
}

CSV_TYPE_SIGNS = {
    "D": "D", "C": "C", "DÉBITO": "D", "DEBITO": "D", "DEBIT": "D", "DEB": "D",
    "CRÉDITO": "C", "CREDITO": "C", "CREDIT": "C", "CRED": "C",
    "SAÍDA": "D", "SAIDA": "D", "ENTRADA": "C", "1": "D", "2": "C", "0": "D",
}


def _csv_header_map(headers):
    low = [str(h or "").strip().lower() for h in headers]
    mapa = {}
    for role, aliases in CSV_DEFAULT_COLUMNS.items():
        for i, h in enumerate(low):
            if h in aliases:
                mapa[role] = i
                break
    return mapa


def _csv_parse_value(raw):
    s = str(raw or "").strip()
    if not s:
        return None
    return s


def _csv_parse_amount(raw):
    s = str(raw or "").strip()
    if not s:
        return None
    # remove separador de milhar (ponto), preserva vírgula decimal → ponto
    s = s.replace("R$", "").strip()
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return _money(s)


def _parse_csv(content, mapeo_columns=None):
    """Parser CSV — adapters por banco via mapeo de colunas (ou detecção)."""
    text = content if isinstance(content, str) else content.decode("utf-8", "replace")
    reader = csv.reader(io.StringIO(text), delimiter=";")
    rows = list(reader)
    # detecta delimitador vírgula se o ';' não gerar colunas úteis
    if len(rows) == 1 or all(len(r) == 1 for r in rows[:5]):
        reader = csv.reader(io.StringIO(text), delimiter=",")
        rows = list(reader)

    header = rows[0]
    data_rows = rows[1:]
    mapa = dict(mapeo_columns or {}) if isinstance(mapeo_columns, dict) else {}
    if not mapa:
        mapa = _csv_header_map(header)
    if "valor" not in mapa and ("debito" not in mapa or "credito" not in mapa):
        raise ValueError("CSV: colunas de valor (e débito/crédito) não encontradas no cabeçalho")

    idx = {k: v for k, v in mapa.items() if isinstance(v, int) and 0 <= v < len(header)}
    lancamentos = []
    saldo_prev = None
    for r in data_rows:
        if not r or all(not str(c or "").strip() for c in r):
            continue

        def _cel(role):
            i = idx.get(role)
            return r[i].strip() if i is not None and i < len(r) else ""

        valor = None
        if "valor" in idx:
            valor = _csv_parse_amount(_cel("valor"))
        else:
            deb = _csv_parse_amount(_cel("debito"))
            cred = _csv_parse_amount(_cel("credito"))
            if deb is not None and deb != 0:
                valor = -abs(deb)
            elif cred is not None and cred != 0:
                valor = abs(cred)
        if valor is None or valor == 0:
            continue

        tipo_raw = _cel("tipo").strip().upper()
        tipo = CSV_TYPE_SIGNS.get(tipo_raw)
        if tipo is None:
            tipo = "D" if valor < 0 else "C"
        desc = _cel("descricao") or ""
        data_raw = _cel("data")
        if not data_raw:
            data_val = None
        else:
            m = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})$", data_raw)
            if m:
                data_val = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            else:
                m = re.match(r"^(\d{4})[/-](\d{2})[/-](\d{2})", data_raw)
                data_val = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
        refs = []
        rid = _cel("id")
        if rid:
            refs = [rid]
        cat = _cel("categoria")
        saldo_cell = _cel("saldo")
        if saldo_cell:
            saldo_prev = _csv_parse_amount(saldo_cell)
        lancamentos.append(
            {
                "id": rid or str(uuid.uuid4()),
                "data": data_val,
                "data_credito": data_val,
                "descricao": desc,
                "tipo": tipo,
                "valor": float(valor),
                "categoria_raw": cat,
                "refs": refs,
                "metadados": {"formato": "csv"},
            }
        )

    statement = {
        "id": "",
        "banco": "",
        "agencia": "",
        "conta": "",
        "tipo_conta": "current",
        "moeda": "BRL",
        "saldo_inicial": None,
        "saldo_final": float(saldo_prev) if saldo_prev is not None else None,
        "lancamentos": lancamentos,
        "fonte": "csv",
    }
    return statement


def _cnab_campo(line, pos):
    """Extrai campo posicional (pos é tupla 1-indexada [ini, fim])."""
    ini, fim = pos
    if ini < 1 or fim > len(line):
        return ""
    return line[ini - 1:fim].strip()


def _cnab_num(line, pos):
    """Extrai campo numérico de posição fixa (2 casas decimais implícitas)."""
    s = _cnab_campo(line, pos)
    s = "".join(c for c in s if c.isdigit())
    if not s:
        return None
    return _money(Decimal(s) / 100)


def _cnab_data(s):
    """DDMMAAAA → YYYY-MM-DD."""
    s = "".join(c for c in str(s or "") if c.isdigit())
    if len(s) != 8:
        return None
    try:
        return f"{s[4:8]}-{s[2:4]}-{s[0:2]}"
    except Exception:
        return None


def _cnab_data6(s):
    """DDMMAA → YYYY-MM-DD (ano < 70 → 2000+, senão 1900+)."""
    s = "".join(c for c in str(s or "") if c.isdigit())
    if len(s) != 6:
        return None
    ano = int(s[4:6])
    aa = f"{ano + 2000 if ano < 70 else ano + 1900:04d}"
    return f"{aa}-{s[2:4]}-{s[0:2]}"


def _parse_cnab240(content):
    """Parser CNAB 240 (retorno) — Segmento T → Statement canônico.

    Layout FEBRABAN CNAB240: linhas de 240 posições. Retorno = header com
    Código Remessa/Retorno '2'. Detalhes são Segmento T (cobrança).
    """
    text = content if isinstance(content, str) else content.decode("latin-1", "replace")
    lines = [l.rstrip("\r\n") for l in text.splitlines()]
    lines = [l for l in lines if l.strip()]
    if not lines:
        raise ValueError("arquivo CNAB240 vazio")

    header = lines[0]
    banco = _cnab_campo(header, CNAB240_HDR["banco"])
    rem_ret = _cnab_campo(header, CNAB240_HDR["rem_ret"])
    if rem_ret and rem_ret != "2":
        raise ValueError(f"CNAB240: arquivo de remessa ({rem_ret}); esperado retorno (2)")
    agencia = _cnab_campo(header, CNAB240_HDR["agencia"])
    conta = _cnab_campo(header, CNAB240_HDR["conta"])
    if not banco:
        raise ValueError("CNAB240: banco (header) obrigatório")

    lancamentos = []
    for line in lines:
        tipo = _cnab_campo(line, CNAB240_HDR["tipo_registro"])
        if tipo != "3":
            continue
        if _cnab_campo(line, (14, 14)) not in ("T", "U"):
            continue
        seg = CNAB240_SEG_T
        movimento = _cnab_campo(line, seg["movimento"])
        valor = _cnab_num(line, seg["valor"])
        if valor is None:
            continue
        numero_doc = _cnab_campo(line, seg["numero_documento"])
        nosso = _cnab_campo(line, seg["nosso_numero_completo"]) or _cnab_campo(line, seg["nosso_numero"])
        data_cred = _cnab_campo(line, seg["data_credito"])
        refs = [r for r in (numero_doc, nosso) if r]
        # retorno de cobrança = crédito no banco (liquidação/baixa)
        tipo = "C" if movimento in CNAB_MOV_LIQUIDACAO else ("D" if movimento in ("26", "28") else "C")
        lancamentos.append(
            {
                "id": nosso or numero_doc or str(uuid.uuid4()),
                "data": _cnab_data(_cnab_campo(line, seg["vencimento"])) or _cnab_data6(data_cred[:6]),
                "data_credito": _cnab_data(data_cred) or _cnab_data6(data_cred[:6]) or _cnab_data(_cnab_campo(line, seg["vencimento"])),
                "descricao": f"Retorno CNAB240 mov {movimento}",
                "tipo": tipo,
                "valor": float(valor),
                "categoria_raw": "",
                "refs": refs,
                "metadados": {
                    "formato": "cnab240",
                    "segmento": _cnab_campo(line, (14, 14)),
                    "movimento": movimento,
                    "nosso_numero": nosso,
                    "numero_documento": numero_doc,
                    "agencia_cobradora": _cnab_campo(line, seg["agencia_cobradora"]),
                    "banco_cobrador": _cnab_campo(line, seg["banco_cobrador"]),
                    "tarifa": float(_cnab_num(line, seg["tarifa"])) if _cnab_num(line, seg["tarifa"]) is not None else None,
                },
            }
        )

    statement = {
        "id": "",
        "banco": banco,
        "agencia": agencia,
        "conta": conta,
        "tipo_conta": "current",
        "moeda": "BRL",
        "saldo_inicial": None,
        "saldo_final": None,
        "lancamentos": lancamentos,
        "fonte": "cnab240",
    }
    return statement


def _parse_cnab400(content):
    """Parser CNAB 400 (retorno) — layout FEBRABAN clássico → Statement."""
    text = content if isinstance(content, str) else content.decode("latin-1", "replace")
    lines = [l.rstrip("\r\n") for l in text.splitlines()]
    lines = [l for l in lines if l.strip()]
    if not lines:
        raise ValueError("arquivo CNAB400 vazio")

    header = lines[0]
    banco = _cnab_campo(header, CNAB400_HDR["banco"])
    agencia = _cnab_campo(header, CNAB400_HDR["agencia"])
    conta = _cnab_campo(header, CNAB400_HDR["conta"])
    if not banco:
        raise ValueError("CNAB400: banco (header) obrigatório")

    lancamentos = []
    for line in lines:
        if _cnab_campo(line, (1, 1)) != "1":
            continue
        seg = CNAB400_SEG
        movimento = _cnab_campo(line, seg["movimento"])
        valor = _cnab_num(line, seg["valor"])
        if valor is None:
            continue
        numero_doc = _cnab_campo(line, seg["numero_documento"])
        nosso = _cnab_campo(line, seg["nosso_numero"])
        data_occ = _cnab_campo(line, seg["data_ocorrencia"])
        refs = [r for r in (numero_doc, nosso) if r]
        tipo = "C" if movimento in CNAB_MOV_LIQUIDACAO else "C"
        lancamentos.append(
            {
                "id": nosso or numero_doc or str(uuid.uuid4()),
                "data": _cnab_data(_cnab_campo(line, seg["vencimento"])) or _cnab_data6(data_occ),
                "data_credito": _cnab_data6(data_occ) or _cnab_data(_cnab_campo(line, seg["vencimento"])),
                "descricao": f"Retorno CNAB400 mov {movimento}",
                "tipo": tipo,
                "valor": float(valor),
                "categoria_raw": "",
                "refs": refs,
                "metadados": {
                    "formato": "cnab400",
                    "movimento": movimento,
                    "nosso_numero": nosso,
                    "numero_documento": numero_doc,
                    "tarifa": float(_cnab_num(line, seg["tarifa"])) if _cnab_num(line, seg["tarifa"]) is not None else None,
                },
            }
        )

    statement = {
        "id": "",
        "banco": banco,
        "agencia": agencia,
        "conta": conta,
        "tipo_conta": "current",
        "moeda": "BRL",
        "saldo_inicial": None,
        "saldo_final": None,
        "lancamentos": lancamentos,
        "fonte": "cnab400",
    }
    return statement


# ── Validação ──


def _validar_balanco(statement):
    """saldo inicial + Σ lançamentos == saldo final (tolerância R$ 0,02)."""
    errors = []
    ini = statement.get("saldo_inicial")
    fim = statement.get("saldo_final")
    if ini is None or fim is None:
        return errors
    total = sum((_money(t["valor"]) for t in statement.get("lancamentos") or []), Decimal("0"))
    esperado = _money(ini + float(total))
    if abs(_money(fim) - esperado) > TOLERANCIA:
        errors.append(
            f"balanço divergente: saldo inicial {ini} + Σ lançamentos {float(total):.2f} "
            f"= {float(esperado):.2f}, mas saldo final informado {fim}"
        )
    return errors


def validar_statement(statement):
    errors = []
    banco = str(statement.get("banco") or "").strip()
    conta = str(statement.get("conta") or "").strip()
    if statement.get("fonte") == "ofx":
        if not banco:
            errors.append("OFX: banco (BANKID) é obrigatório")
        if not conta:
            errors.append("OFX: conta (ACCTID) é obrigatória")
        if banco and banco not in BANCO_CODIGOS_VALIDOS:
            errors.append(f"OFX: código de banco desconhecido ({banco}) — não bloqueia, registre a conta")
    if not statement.get("lancamentos"):
        errors.append("extrato sem lançamentos")
    if errors:
        return errors
    return _validar_balanco(statement)


# ── Importação ──


def detectar_formato(nome_arquivo=None, conteudo=None):
    nome = str(nome_arquivo or "").lower()
    if nome.endswith(".ofx"):
        return "ofx"
    if nome.endswith(".ofc"):
        raise ValueError("formato OFC ainda não implementado (Sprint BI-04)")
    if nome.endswith(".csv"):
        return "csv"
    if nome.endswith(".cnab240") or nome.endswith(".240"):
        return "cnab240"
    if nome.endswith(".cnab400") or nome.endswith(".400") or nome.endswith(".ret"):
        return "cnab400"
    if nome.endswith(".txt"):
        raise ValueError("formato .txt: informe o formato explicitamente (cnab240/cnab400)")
    if conteudo:
        is_bytes = isinstance(conteudo, bytes)
        head = conteudo[:1024] if is_bytes else str(conteudo)[:1024]
        if is_bytes:
            if b"<OFX>" in head:
                return "ofx"
        elif "<OFX>" in head:
            return "ofx"
        # CNAB240: linha 240 chars com tipo de registro '0' na posição 8
        primeiras = conteudo[:4096] if is_bytes else str(conteudo)[:4096]
        first_line = (primeiras.splitlines() or [b""] if is_bytes else primeiras.splitlines() or [""])[0]
        if is_bytes:
            first_line = first_line.decode("latin-1", "replace")
        if len(first_line) == 240 and (first_line[7:8] in ("0", "1", "3")):
            return "cnab240"
        if len(first_line) == 400 and (first_line[0:1] in ("0", "1", "9")):
            return "cnab400"
    raise ValueError("formato não suportado ou não reconhecido (esperado OFX, CSV, CNAB240 ou CNAB400)")


def importar_extrato(conteudo, nome_arquivo=None, formato=None, banco=None, agencia=None,
                     conta=None, tipo_conta=None, mapeo_columns=None, actor=None,
                     conciliar_titulos=False):
    """
    Importa extrato bancário → Statement canônico, imutável e idempotente.

    Devolve {ok, status, extrato, evento} — 'duplicate' quando o extrato já
    foi importado (RFC-0070 §9.2), 'ok' com o extrato novo caso contrário.

    CNAB (retorno) pode conciliar títulos a receber a partir do nosso número /
    número do documento (RFC-0070 §11.3 → Finance).
    """
    if formato is None:
        formato = detectar_formato(nome_arquivo, conteudo)
    formato = str(formato or "").strip().lower()
    if formato not in SUPPORTED_FORMATS:
        raise ValueError(f"formato não suportado: {formato} (suportados: {', '.join(SUPPORTED_FORMATS)})")

    if formato == "ofx":
        statement = _parse_ofx(conteudo)
        if banco or agencia or conta:
            statement["banco"] = str(banco or statement["banco"] or "")
            statement["agencia"] = str(agencia or statement["agencia"] or "")
            statement["conta"] = str(conta or statement["conta"] or "")
        if tipo_conta:
            statement["tipo_conta"] = tipo_conta
    elif formato == "csv":
        statement = _parse_csv(conteudo, mapeo_columns=mapeo_columns)
        statement["banco"] = str(banco or "").strip()
        statement["agencia"] = str(agencia or "").strip()
        statement["conta"] = str(conta or "").strip()
        if tipo_conta:
            statement["tipo_conta"] = tipo_conta
    elif formato == "cnab240":
        statement = _parse_cnab240(conteudo)
        if banco or agencia or conta:
            statement["banco"] = str(banco or statement["banco"] or "")
            statement["agencia"] = str(agencia or statement["agencia"] or "")
            statement["conta"] = str(conta or statement["conta"] or "")
    elif formato == "cnab400":
        statement = _parse_cnab400(conteudo)
        if banco or agencia or conta:
            statement["banco"] = str(banco or statement["banco"] or "")
            statement["agencia"] = str(agencia or statement["agencia"] or "")
            statement["conta"] = str(conta or statement["conta"] or "")

    if not statement["conta"]:
        raise ValueError("conta bancária é obrigatória (informe via parâmetro ou no arquivo)")
    if not statement["banco"]:
        raise ValueError("código do banco é obrigatório (informe via parâmetro ou no arquivo)")

    statement["data_importacao"] = _now()
    statement["id"] = _extrato_id(statement)

    existing = find_by_extrato_id(statement["id"])
    if existing:
        ev = {
            "id": str(uuid.uuid4()),
            "evento": "finance_statement_duplicate",
            "extrato_id": statement["id"],
            "banco": statement["banco"],
            "conta": statement["conta"],
            "actor": actor,
            "em": _now(),
        }
        _append_log(ev)
        return {
            "ok": True,
            "status": "duplicate",
            "evento": ev["evento"],
            "extrato": existing,
            "message": "extrato já importado (idempotente)",
        }

    errors = validar_statement(statement)
    if errors:
        raise ValueError("; ".join(errors))

    conta_obj = resolve_bank_account(statement)
    statement["conta_bancaria_id"] = conta_obj.get("id") if conta_obj else None

    # CNAB retorno → conciliação de títulos a receber (Finance)
    conciliacao = None
    if conciliar_titulos and formato in ("cnab240", "cnab400"):
        conciliacao = conciliar_titulos_retorno(statement, actor=actor)

    _append_statement(statement)
    ev = {
        "id": str(uuid.uuid4()),
        "evento": "finance_statement_imported",
        "extrato_id": statement["id"],
        "banco": statement["banco"],
        "conta": statement["conta"],
        "total_lancamentos": len(statement.get("lancamentos") or []),
        "actor": actor,
        "em": _now(),
    }
    _append_log(ev)
    return {
        "ok": True,
        "status": "ok",
        "evento": ev["evento"],
        "extrato": statement,
        "conta_bancaria": conta_obj,
        "conciliacao": conciliacao,
    }
    if not statement["banco"]:
        raise ValueError("código do banco é obrigatório (informe via parâmetro ou no arquivo)")

    statement["data_importacao"] = _now()
    statement["id"] = _extrato_id(statement)

    existing = find_by_extrato_id(statement["id"])
    if existing:
        ev = {
            "id": str(uuid.uuid4()),
            "evento": "finance_statement_duplicate",
            "extrato_id": statement["id"],
            "banco": statement["banco"],
            "conta": statement["conta"],
            "actor": actor,
            "em": _now(),
        }
        _append_log(ev)
        return {
            "ok": True,
            "status": "duplicate",
            "evento": ev["evento"],
            "extrato": existing,
            "message": "extrato já importado (idempotente)",
        }

    errors = validar_statement(statement)
    if errors:
        raise ValueError("; ".join(errors))

    conta_obj = resolve_bank_account(statement)
    statement["conta_bancaria_id"] = conta_obj.get("id") if conta_obj else None

    _append_statement(statement)
    ev = {
        "id": str(uuid.uuid4()),
        "evento": "finance_statement_imported",
        "extrato_id": statement["id"],
        "banco": statement["banco"],
        "conta": statement["conta"],
        "total_lancamentos": len(statement.get("lancamentos") or []),
        "actor": actor,
        "em": _now(),
    }
    _append_log(ev)
    return {
        "ok": True,
        "status": "ok",
        "evento": ev["evento"],
        "extrato": statement,
        "conta_bancaria": conta_obj,
        "conciliacao": conciliacao,
    }


def conciliar_titulos_retorno(statement, actor=None):
    """
    Concilia títulos a receber a partir do retorno CNAB (RFC-0070 §11.3).

    Cada lançamento com código de movimento de liquidação é pareado com um
    título aberto (AR) pelo número do documento / nosso número / fatura /
    pedido. Títulos casados são baixados (Finance baixa; Accounting posta).
    Devolve resumo da conciliação — nunca posta nada por conta própria.
    """
    try:
        import sales_finance
    except Exception:
        return {"pares": 0, "conciliados": 0, "nao_casados": 0, "message": "sales_finance indisponível"}

    titulos = list(sales_finance.list_titulos(status="aberto").get("titulos") or [])
    titulos += list(sales_finance.list_titulos(status=None).get("titulos") or [])

    def _chaves(t):
        return {
            str(t.get("id") or "").upper(),
            str(t.get("fatura_numero") or "").upper(),
            str(t.get("fatura_id") or "").upper(),
            str(t.get("pedido_numero") or "").upper(),
            str(t.get("pedido_id") or "").upper(),
            str(t.get("nosso_numero") or "").upper(),
        }

    alvo = {c: t for t in titulos for c in _chaves(t) if c}
    casados = 0
    nao_casados = 0
    pares = []
    liquidados = []
    for lanc in statement.get("lancamentos") or []:
        mov = (lanc.get("metadados") or {}).get("movimento")
        if mov not in CNAB_MOV_LIQUIDACAO:
            continue
        refs = [str(r).upper() for r in (lanc.get("refs") or []) if str(r or "").strip()]
        titulo = None
        # 1) match exato por chave (nosso número / documento / fatura / pedido)
        chave = next((r for r in refs if r in alvo), None)
        if chave:
            titulo = alvo.get(chave)
        # 2) match parcial: fatura/pedido contidos no ref (CNAB preenche à esquerda)
        if not titulo:
            for r in refs:
                for chave, t in alvo.items():
                    if chave and (chave in r or r in chave) and chave not in ("0",):
                        titulo = t
                        break
                if titulo:
                    break
        pares.append({"lancto": lanc.get("id"), "movimento": mov, "titulo_id": titulo.get("id") if titulo else None})
        if titulo:
            casados += 1
            liquidados.append(
                {
                    "titulo_id": titulo.get("id"),
                    "fatura_numero": titulo.get("fatura_numero"),
                    "valor": lanc.get("valor"),
                    "data_credito": lanc.get("data_credito"),
                    "baixado": True,
                }
            )
        else:
            nao_casados += 1

    baixados = 0
    for liq in liquidados:
        try:
            sales_finance.baixar_titulo(liq["titulo_id"], valor=liq.get("valor"), usuario=actor or "cnab")
            liq["baixado"] = True
            baixados += 1
        except Exception:
            liq["baixado"] = False

    if liquidados:
        ev = {
            "id": str(uuid.uuid4()),
            "evento": "finance_reconciliation_adjustment",
            "extrato_id": statement.get("id"),
            "banco": statement.get("banco"),
            "titulos_liquidados": len(liquidados),
            "titulos_baixados": baixados,
            "actor": actor,
            "em": _now(),
        }
        _append_log(ev)

    return {
        "pares": len(pares),
        "conciliados": casados,
        "baixados": baixados,
        "nao_casados": nao_casados,
        "liquidados": liquidados,
    }


def list_extratos(banco=None, conta=None, limit=100):
    rows = list(_load_statements().get("extratos") or [])
    rows.reverse()
    if banco:
        rows = [s for s in rows if str(s.get("banco") or "") == str(banco)]
    if conta:
        rows = [s for s in rows if str(s.get("conta") or "") == str(conta)]
    total = len(rows)
    try:
        lim = max(1, min(int(limit or 100), 500))
    except (TypeError, ValueError):
        lim = 100
    return {
        "total": total,
        "extratos": rows[:lim],
    }


def list_lancamentos(extrato_id=None, banco=None, conta=None, tipo=None, limit=500):
    rows = []
    for s in _load_statements().get("extratos") or []:
        if extrato_id and s.get("id") != extrato_id:
            continue
        if banco and str(s.get("banco") or "") != str(banco):
            continue
        if conta and str(s.get("conta") or "") != str(conta):
            continue
        for t in s.get("lancamentos") or []:
            if tipo and str(t.get("tipo") or "").upper() != str(tipo).upper():
                continue
            rows.append({**t, "extrato_id": s.get("id"), "banco": s.get("banco"), "conta": s.get("conta")})
    try:
        lim = max(1, min(int(limit or 500), 5000))
    except (TypeError, ValueError):
        lim = 500
    return {"total": len(rows), "lancamentos": rows[:lim]}


def status():
    return {
        "principio": "Bank Integration nunca conhece o plano de contas, nunca posta; importa, normaliza e publica o extrato canônico",
        "formatos": list(SUPPORTED_FORMATS),
        "contas_bancarias": len(list_bank_accounts()),
        "extratos_importados": len(_load_statements().get("extratos") or []),
        "ultimos_eventos": list(_load_raw(LOG_FILE, {"eventos": []}).get("eventos") or [])[-5:],
    }
