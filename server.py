#!/usr/bin/env python3
"""FiscalBrasil ERP — Servidor de Desenvolvimento com autenticação real e mult-empresa"""

import http.server
import json
import os
import sys
import urllib.parse
import hashlib
import re
import uuid
from datetime import datetime
import jsonio
import cobol_bridge
import inventory_mvp
import receiving_mvp
import receiving_pending
import nfe_inbound
import nfe_monitor
import product_localization
import partner_lookup
import sales_reservation
import sales_finance
import faturas_store
import pedidos_b2b_store
import contratos_b2b_store
import compras_store
import acordos_compra_store
import devolucao_compra_store
import settings_store
import vendor_pricelist_store
import currency_store
import quality_checks_store
import fiscal_reforma_store
import sped_livros_store
import sped_fiscal_store
import tax_apuracao_store
from modules.lookup import fiscal_tables_service
import partners_store
import pos_caixa
import price_lists
import campaigns
import planocontas
import journals
import journal_entries
import ledger
import posting_engine
import accounting_periods
import accounting_reports
import accounting_integration
import accounting_analytics
import wms_warehouses
import wms_locations
import wms_operation_types
import wms_operations
import wms_tasks
import wms_picking
import wms_receiving
import wms_shipping
import wms_sales_bridge
import wms_analytics
import wms_workspace
import delivery_orders
import delivery_resources
import delivery_tasks
import delivery_dispatch
import delivery_scheduling
import delivery_tracking
import delivery_pod
import delivery_analytics
import delivery_workspace
import delivery_dashboard
import delivery_queue
import delivery_planning
import delivery_calendar
import delivery_manifest
import delivery_trip
import delivery_driver_workspace
import delivery_stops
import app_registry
import platform_setup
import org_store
from modules.certificate import cert_service
from modules.sefaz import sefaz_service
from modules.sefaz import nfce_xml
from modules.sefaz import nfe_xml
from modules.sefaz import nfse_service
from modules.sefaz import nfse_xml
from modules.sefaz import tributos
from modules.sped import sped_fiscal
from modules.sped import sped_pis_cofins
from modules.sefaz import danfe
from modules.lookup import ncm_cest_service

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
HOST = "0.0.0.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
EMPRESAS_FILE = os.path.join(DATA_DIR, "empresas.json")
CATEGORIAS_FILE = os.path.join(DATA_DIR, "categorias.json")
MARCAS_FILE = os.path.join(DATA_DIR, "marcas.json")
FABRICANTES_FILE = os.path.join(DATA_DIR, "fabricantes.json")
CONTATOS_FILE = os.path.join(DATA_DIR, "contatos.json")
PARTNERS_FILE = os.path.join(DATA_DIR, "partners.json")
POS_FILA_FILE = os.path.join(DATA_DIR, "pos_fila.json")
POS_TERMINAIS_FILE = os.path.join(DATA_DIR, "pos_terminais.json")

os.makedirs(DATA_DIR, exist_ok=True)

EMPRESA_JSON = os.path.join(BASE_DIR, "dados", "empresa.json")
ESTAB_FISCAL_FILE = os.path.join(DATA_DIR, "estabelecimentos_fiscal.json")

def load_empresa_fiscal():
    """Emitente padrão — fonte = org_store (estabelecimento_padrao)."""
    return org_store.load_empresa_fiscal()

def load_estab_fiscal_store():
    return org_store.load_fiscal_store()

def save_estab_fiscal_store(data):
    org_store.save_fiscal_store(data)
    try:
        org_store.sync_legacy_empresa_json()
    except Exception:
        pass

def _digits(val):
    return org_store.digits(val)

def resolve_empresa_fiscal(estabelecimento_id=None):
    """Emitente NFC-e = estabelecimento (+ overlay fiscal)."""
    return org_store.resolve_empresa_fiscal(estabelecimento_id)

def _terminal_do_usuario(uid):
    if not uid:
        return None
    for t in load_pos_terminais().get("terminais", []):
        if t.get("ativo", True) and t.get("usuario_id") == uid:
            return t
    return None

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    jsonio.save(USERS_FILE, users)

def load_empresas():
    return org_store.load_empresas()

def save_empresas(empresas):
    org_store.save_empresas(empresas)

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    jsonio.save(path, data)

def load_pos_terminais():
    data = load_json(POS_TERMINAIS_FILE)
    if not isinstance(data, dict) or "terminais" not in data:
        return {"terminais": []}
    if not isinstance(data.get("terminais"), list):
        data["terminais"] = []
    return data

def save_pos_terminais(data):
    if not isinstance(data, dict):
        data = {"terminais": []}
    if not isinstance(data.get("terminais"), list):
        data["terminais"] = []
    save_json(POS_TERMINAIS_FILE, data)

def _pdv_user_conflict(terminais, usuario_id, exclude_id=None):
    """Vendedor ↔ PDV 1:1 — retorna terminal conflitante ou None."""
    if not usuario_id:
        return None
    for t in terminais:
        if t.get("tipo") != "pdv":
            continue
        if not t.get("ativo", True):
            continue
        if t.get("usuario_id") == usuario_id and t.get("id") != exclude_id:
            return t
    return None

def promise_produto(estabelecimento_id, produto_id, empresas=None):
    """Promise Engine (POS) — lê ledger/cache do Inventário MVP."""
    return inventory_mvp.inventory_promise(
        estabelecimento_id,
        produto_id,
        empresas=empresas if empresas is not None else load_empresas(),
    )

def enriquecer_produtos_com_promise(produtos, estabelecimento_id):
    return inventory_mvp.enriquecer_produtos_com_promise(
        produtos, estabelecimento_id, empresas=load_empresas()
    )

def baixar_estoque_local(estabelecimento_id, linhas, venda_id=None):
    """Compat: delega para inventory_apply_sale (movimento sale)."""
    return inventory_mvp.inventory_apply_sale(estabelecimento_id, linhas, venda_id=venda_id)

def load_pos_fila():
    data = load_json(POS_FILA_FILE)
    if not isinstance(data, dict) or "pedidos" not in data:
        return {"next_num": 1000, "pedidos": []}
    if not isinstance(data.get("pedidos"), list):
        data["pedidos"] = []
    if not isinstance(data.get("next_num"), int):
        data["next_num"] = 1000
    return data

def save_pos_fila(data):
    save_json(POS_FILA_FILE, data)

def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return float(default)

def _digits(val):
    return "".join(c for c in str(val or "") if c.isdigit())

def _resolve_cert_id(empresa, preferred_id=""):
    preferred_id = str(preferred_id or "").strip()
    if preferred_id and cert_service.obter(preferred_id):
        return preferred_id
    certs = cert_service.listar()
    if not certs:
        return ""
    arq = (empresa or {}).get("certificado") or ""
    cnpj = _digits((empresa or {}).get("cnpj"))
    for c in certs:
        if arq and c.get("arquivo") == arq:
            return c.get("id") or ""
    for c in certs:
        nome = (c.get("nome") or "").upper()
        if cnpj and cnpj in nome:
            return c.get("id") or ""
        if "FABIELI" in nome:
            return c.get("id") or ""
    for c in certs:
        if c.get("valido") and c.get("ativo", True):
            return c.get("id") or ""
    return certs[0].get("id") or ""

def _pedido_para_venda(pedido, forma_pg="Dinheiro"):
    """Converte pedido da fila POS no formato esperado por nfce_xml / vendas.json."""
    agora = datetime.now()
    client = pedido.get("client") or {}
    itens = []
    catalog = {}
    try:
        for p in cobol_bridge.produtos_listar() or []:
            catalog[str(p.get("id"))] = p
    except Exception:
        catalog = {}
    for line in pedido.get("lines") or []:
        qtd = _safe_float(line.get("qtd"), 1)
        if qtd <= 0 or line.get("troca"):
            # troca/devolução não entra na NFC-e de venda
            continue
        pid = line.get("id")
        prod = catalog.get(str(pid), {})
        preco = _safe_float(line.get("preco"), 0)
        subtotal = round(qtd * preco, 2)
        itens.append({
            "prod_id": pid,
            "produto": line.get("nome") or prod.get("nome") or f"Produto {pid}",
            "qtd": qtd,
            "preco": preco,
            "subtotal": subtotal,
            "unidade": "KG" if line.get("peso") else (prod.get("unidade") or "UN"),
            "ncm": prod.get("ncm") or "00000000",
            "ean": prod.get("codigo_barras") or line.get("ean") or "",
            "cfop": prod.get("cfop") or "5102",
            "cst": prod.get("cst") or "400",
            "filial_id": 0,
        })
    return {
        "id": pedido.get("orderNum") or pedido.get("id"),
        "data": agora.strftime("%Y-%m-%d"),
        "hora": agora.strftime("%H:%M:%S"),
        "cliente": client.get("nome") or "Consumidor Final",
        "cliente_id": client.get("id") or "cf",
        "cliente_cpf": client.get("cpf") or "",
        "total": _safe_float(pedido.get("total"), 0),
        "forma_pg": forma_pg or "Dinheiro",
        "filial_id": 0,
        "estabelecimento_id": pedido.get("estabelecimento_id") or "",
        "terminal_caixa_id": pedido.get("terminal_caixa_id") or "",
        "sessao_id": pedido.get("sessao_id") or "",
        "caixaUser": pedido.get("caixaUser") or "",
        "pos_pedido_id": pedido.get("id"),
        "itens": itens,
    }

def _avancar_numero_nfce(estabelecimento_id=None):
    eid = str(estabelecimento_id or "").strip()
    if eid:
        store = load_estab_fiscal_store()
        entry = dict(store.get(eid) or {})
        n = int(entry.get("numero_nfce") or 0) + 1
        entry["numero_nfce"] = n
        if "serie_nfce" not in entry:
            entry["serie_nfce"] = 1
        store[eid] = entry
        save_estab_fiscal_store(store)
        return n
    cobol_bridge._compile_if_needed("gerir_numeracao")
    out, _ = cobol_bridge._run("gerir_numeracao", {"ACAO": "avancar-nfce"})
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    return 0

def _autorizar_nfce_de_venda(venda, empresa, cert_id, cert_senha, ambiente=2, serie=1, numero=0):
    uf = empresa.get("uf", "RS")
    if isinstance(uf, int) or (isinstance(uf, str) and uf.isdigit()):
        uf_codes = {
            11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
            21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
            28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
            42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF",
        }
        uf = uf_codes.get(int(uf), "RS")
    elif isinstance(uf, str) and len(uf) == 2:
        uf = uf.upper()
    eid = empresa.get("estabelecimento_id")
    if not numero:
        numero = _avancar_numero_nfce(eid)
    if not numero:
        raise ValueError("Erro ao obter numeração NFC-e")
    xml_envi = nfce_xml.montar_envi_nfe(venda, empresa, ambiente, serie, numero)
    resultado = sefaz_service.autorizar_nfce(
        xml_envi, uf, ambiente, cert_id, cert_senha, empresa=empresa
    )
    nfce_path = os.path.join(BASE_DIR, "dados", "nfce.json")
    nfce_data = load_json(nfce_path)
    if not isinstance(nfce_data, dict):
        nfce_data = {"nfce": []}
    notas = nfce_data.get("nfce") or []
    notas.append({
        "venda_id": venda.get("id"),
        "pos_pedido_id": venda.get("pos_pedido_id"),
        "estabelecimento_id": eid,
        "numero": numero,
        "serie": serie,
        "chave": resultado.get("chave", ""),
        "ambiente": ambiente,
        "status": resultado.get("status", "ERRO"),
        "protocolo": resultado.get("nProt", resultado.get("protocolo", "")),
        "cStat": resultado.get("cStat", ""),
        "xMotivo": resultado.get("xMotivo", ""),
        "xml": xml_envi,
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    nfce_data["nfce"] = notas
    save_json(nfce_path, nfce_data)
    return {"resultado": resultado, "numero": numero, "serie": serie, "chave": resultado.get("chave", "")}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def make_token():
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32]


def _pedido_tem_troca(lines):
    for line in lines or []:
        if not isinstance(line, dict):
            continue
        if line.get("troca") or _safe_float(line.get("qtd"), 0) < 0:
            return True
    return False


def _load_pedidos_b2b():
    """Fonte: COBOL (.dat); fallback JSON legado."""
    try:
        return pedidos_b2b_store.listar()
    except Exception:
        data = load_json(os.path.join(BASE_DIR, "dados", "pedidos_b2b.json"))
        if isinstance(data, dict):
            return data.get("pedidos") or []
        return data if isinstance(data, list) else []


def _save_pedidos_b2b(pedidos, changed=None):
    """Persiste no COBOL o pedido alterado; JSON vira projeção."""
    if changed is not None:
        try:
            saved = pedidos_b2b_store.save(changed)
            # atualiza referência in-place se lista vier do caller
            if isinstance(pedidos, list) and saved:
                for i, p in enumerate(pedidos):
                    if str(p.get("id")) == str(saved.get("id")):
                        pedidos[i] = saved
                        break
            return saved
        except Exception as e:
            # não engolir — UI precisa saber
            raise
    try:
        pedidos_b2b_store.sync_json(pedidos)
    except Exception:
        save_json(os.path.join(BASE_DIR, "dados", "pedidos_b2b.json"), {"pedidos": pedidos})


def _save_faturas_venda(faturas):
    """Compat: persiste via COBOL (faturas_store) + projeção JSON."""
    import faturas_store
    # legado: alguns callers passam a lista completa — sync só projeção
    if isinstance(faturas, list):
        faturas_store.sync_json(faturas)
    else:
        faturas_store.sync_json()


# Workflow B2B (CNPJ→CNPJ): rascunho → pendente → aprovado → faturado.
# Cotação convertida → status terminal "convertida".
# cancelado/bloqueado: bloqueado retorna a pendente.
_B2B_FLOW = {
    "rascunho": {"pendente", "cancelado", "bloqueado", "convertida"},
    "pendente": {"aprovado", "cancelado", "bloqueado", "convertida"},
    "aprovado": {"faturado", "cancelado", "bloqueado", "convertida"},
    "bloqueado": {"pendente"},
    "faturado": set(),
    "cancelado": set(),
    "convertida": set(),
}
_B2B_LOCKED = {"faturado", "cancelado", "bloqueado", "convertida"}

# RFC §6 — teto de desconto por papel (% na linha)
_B2B_DISCOUNT_LIMIT = {
    "vendedor": 5.0,
    "operador": 5.0,
    "caixa": 5.0,
    "supervisor": 15.0,
    "gerente": 100.0,
    "admin": 100.0,
    "fiscal": 15.0,
    "contabil": 15.0,
}


def _b2b_discount_limit(role):
    return float(_B2B_DISCOUNT_LIMIT.get(str(role or "").lower(), 5.0))


def _b2b_max_line_discount(pedido):
    mx = 0.0
    for i in (pedido or {}).get("itens") or []:
        try:
            mx = max(mx, float(i.get("desconto") or 0))
        except (TypeError, ValueError):
            pass
    return mx


def _b2b_check_discount(pedido, user, body=None):
    """Retorna (erro_dict|None). force_discount só gerente/admin."""
    body = body or {}
    role = str((user or {}).get("role") or "").lower()
    limit = _b2b_discount_limit(role)
    requested = _b2b_max_line_discount(pedido)
    force = bool(body.get("force_discount")) and role in ("admin", "gerente")
    if requested <= limit + 0.001 or force:
        return None
    return {
        "status": "error",
        "code": "desconto_excedido",
        "message": (
            f"Desconto {requested:.1f}% acima do limite do perfil "
            f"({limit:.0f}%). Solicite aprovação de gerente."
        ),
        "desconto": requested,
        "limite": limit,
    }


def _b2b_cnpj_valido(valor):
    if not valor:
        return False
    return len(re.sub(r"\D", "", str(valor))) == 14


def _nfe_load_lista():
    path = os.path.join(BASE_DIR, "dados", "nfe.json")
    data = load_json(path)
    lista = data.get("nfe") if isinstance(data, dict) else []
    if not isinstance(lista, list):
        lista = []
    return path, lista


def _nfe_find_draft(*, numero=None, chave=None, pedido_b2b_id=None, venda_id=None):
    """Localiza NF-e rascunho (índice, row) em dados/nfe.json."""
    _, lista = _nfe_load_lista()
    for i, row in enumerate(lista):
        if not isinstance(row, dict):
            continue
        if numero is not None and str(row.get("numero") or "") == str(numero):
            return i, row
        if chave and str(row.get("chave") or "") == str(chave):
            return i, row
        if pedido_b2b_id is not None and str(row.get("pedido_b2b_id") or "") == str(pedido_b2b_id):
            return i, row
        if venda_id and str(row.get("venda_id") or "") == str(venda_id):
            return i, row
    return None, None


def _b2b_criar_nfe_rascunho(pedido, fatura, total):
    """
    Gera registro NF-e modelo 55 (rascunho) a partir do pedido B2B.
    Não autoriza na SEFAZ — só prepara o documento no repositório fiscal.
    """
    path, lista = _nfe_load_lista()
    # idempotente: já existe rascunho deste pedido
    for row in lista:
        if str(row.get("pedido_b2b_id") or "") == str(pedido.get("id")) and row.get("status") == "RASCUNHO":
            return {
                "numero": row.get("numero"),
                "serie": row.get("serie") or 1,
                "chave": row.get("chave") or "",
                "status": "RASCUNHO",
                "ambiente": row.get("ambiente") or 2,
                "already": True,
            }
    numeros = []
    for n in lista:
        try:
            numeros.append(int(n.get("numero") or 0))
        except (TypeError, ValueError):
            pass
    numero = (max(numeros) if numeros else 0) + 1
    serie = 1
    ambiente = 2
    try:
        empresa = load_empresa_fiscal()
    except Exception:
        empresa = {}

    # shape compatível com montar_envi_nfe (espera venda POS-like)
    venda = {
        "id": f"b2b-{pedido.get('id')}",
        "natOp": "VENDA",
        "cliente": pedido.get("razao_social") or pedido.get("cliente_nome") or "",
        "cnpj": pedido.get("cnpj") or "",
        "itens": [
            {
                "id": i.get("prod_id") or i.get("id"),
                "produto": i.get("produto") or "",
                "qtd": i.get("qtd"),
                "preco": i.get("preco"),
                "ncm": i.get("ncm") or "",
            }
            for i in (pedido.get("itens") or [])
        ],
        "total": total,
        "indFinal": 0,
    }
    xml = ""
    chave = ""
    try:
        xml = nfe_xml.montar_envi_nfe(venda, empresa, ambiente=ambiente, serie=serie, numero=numero)
        # extrai chave se presente
        m = re.search(r'Id="NFe(\d{44})"', xml or "")
        if m:
            chave = m.group(1)
    except Exception:
        xml = ""

    row = {
        "venda_id": f"b2b-{pedido.get('id')}",
        "pedido_b2b_id": pedido.get("id"),
        "fatura_id": fatura.get("id"),
        "numero": numero,
        "serie": serie,
        "chave": chave,
        "ambiente": ambiente,
        "status": "RASCUNHO",
        "protocolo": "",
        "xml": xml,
        "cliente": pedido.get("razao_social") or "",
        "cnpj": pedido.get("cnpj") or "",
        "total": total,
        "origem": "sales_b2b",
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    lista.insert(0, row)
    save_json(path, {"nfe": lista})
    return {
        "numero": numero,
        "serie": serie,
        "chave": chave,
        "status": "RASCUNHO",
        "ambiente": ambiente,
    }


def _b2b_autorizar_nfe(body):
    """
    Autoriza NF-e rascunho B2B (ou qualquer RASCUNHO em nfe.json).
    - SEFAZ real: cert_id + cert_senha
    - Homologação sem cert: simular=true → AUTORIZADO local (só ambiente 2)
    """
    body = body or {}
    numero = body.get("numero") or body.get("nfe_numero")
    chave = (body.get("chave") or "").strip()
    pedido_b2b_id = body.get("pedido_b2b_id") or body.get("id")
    venda_id = (body.get("venda_id") or "").strip()
    simular = bool(body.get("simular"))
    cert_id = (body.get("cert_id") or "").strip()
    cert_senha = body.get("cert_senha") or ""

    idx, row = _nfe_find_draft(
        numero=numero, chave=chave or None,
        pedido_b2b_id=pedido_b2b_id, venda_id=venda_id or None,
    )
    if row is None:
        raise ValueError("NF-e rascunho não encontrada")
    if str(row.get("status") or "").upper() not in ("RASCUNHO", "REJEITADO", "ERRO_TRANSMISSAO", "ERRO"):
        raise ValueError(f"NF-e já processada (status: {row.get('status')})")

    xml_envi = row.get("xml") or ""
    if not xml_envi and not simular:
        raise ValueError("XML do rascunho ausente — refature o pedido")

    ambiente = int(row.get("ambiente") or body.get("ambiente") or 2)
    resultado = None

    if simular:
        if ambiente != 2:
            raise ValueError("simular só permitido em homologação (ambiente=2)")
        chave_ok = row.get("chave") or ("9" * 44)
        resultado = {
            "status": "AUTORIZADO",
            "cStat": "100",
            "xMotivo": "Autorizado o uso da NF-e (simulado homologação)",
            "nProt": f"SIM{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "protocolo": f"SIM{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "chave": chave_ok,
            "simulado": True,
        }
    else:
        if not cert_id:
            raise ValueError("cert_id obrigatório (ou use simular=true em homologação)")
        try:
            empresa = load_empresa_fiscal()
        except Exception:
            empresa = {}
        uf = empresa.get("uf", "RS")
        if isinstance(uf, int):
            uf_codes = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
                        21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
                        28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
                        42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}
            uf = uf_codes.get(int(uf), "RS")
        resultado = sefaz_service.autorizar_nfe(xml_envi, uf, ambiente, cert_id, cert_senha)

    path, lista = _nfe_load_lista()
    # re-find index (lista reloaded)
    idx, row = _nfe_find_draft(
        numero=row.get("numero"), chave=row.get("chave") or None,
        pedido_b2b_id=row.get("pedido_b2b_id"), venda_id=row.get("venda_id"),
    )
    if idx is None:
        raise ValueError("NF-e sumiu durante autorização")

    st = (resultado or {}).get("status") or "ERRO"
    row = dict(lista[idx])
    row["status"] = st
    row["protocolo"] = (resultado or {}).get("nProt") or (resultado or {}).get("protocolo") or ""
    row["cStat"] = (resultado or {}).get("cStat") or ""
    row["xMotivo"] = (resultado or {}).get("xMotivo") or ""
    if (resultado or {}).get("chave"):
        row["chave"] = resultado["chave"]
    row["autorizado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if simular:
        row["simulado"] = True
    lista[idx] = row
    save_json(path, {"nfe": lista})

    # sync pedido B2B
    pid = row.get("pedido_b2b_id")
    if pid is not None:
        try:
            p = pedidos_b2b_store.get(pid)
            if p:
                p["nfe_numero"] = row.get("numero")
                p["nfe_status"] = st
                p["nfe_chave"] = row.get("chave") or ""
                p["nfe_protocolo"] = row.get("protocolo") or ""
                _save_pedidos_b2b(None, changed=p)
        except Exception:
            pass

    return {"nfe": row, "resultado": resultado}


def _b2b_apply_server_prices(doc):
    """
    Resolve preços das linhas no servidor (lista → base).
    - Se linha tem preco_manual=True, mantém o preço enviado.
    - Persiste lista_precos_id + nome da lista.
    """
    if not isinstance(doc, dict):
        return doc
    lid = str(doc.get("lista_precos_id") or "").strip()
    if lid:
        try:
            pl = price_lists.get_list(lid)
            if pl:
                doc["lista_precos"] = pl.get("name") or lid
                if not pl.get("active", True):
                    lid = ""
                    doc["lista_precos_id"] = ""
        except Exception:
            pass
    elif doc.get("lista_precos") and not lid:
        # tenta casar nome → id
        name = str(doc.get("lista_precos") or "").strip().lower()
        for pl in price_lists.list_all(active_only=True) or []:
            if str(pl.get("name") or "").strip().lower() == name:
                lid = str(pl.get("id") or "")
                doc["lista_precos_id"] = lid
                break

    by_id = {}
    try:
        for p in cobol_bridge.produtos_listar() or []:
            by_id[str(p.get("id"))] = p
    except Exception:
        by_id = {}

    itens = list(doc.get("itens") or [])
    out = []
    for line in itens:
        if not isinstance(line, dict):
            continue
        row = dict(line)
        if row.get("preco_manual") is True:
            out.append(row)
            continue
        pid = str(row.get("prod_id") or row.get("produto_id") or row.get("id") or "").strip()
        base = by_id.get(pid) or {
            "id": pid,
            "preco": row.get("preco") or 0,
        }
        # se não achou produto, usa preço da linha como base
        if pid and pid not in by_id and row.get("produto"):
            # tenta por nome
            nome = str(row.get("produto") or "").strip().lower()
            for p in by_id.values():
                if str(p.get("nome") or "").strip().lower() == nome:
                    base = p
                    pid = str(p.get("id"))
                    row["prod_id"] = pid
                    break
        resolved = price_lists.resolve_price(base, lid or None)
        row["preco"] = resolved["preco"]
        row["preco_base"] = resolved["preco_base"]
        row["price_source"] = resolved["price_source"]
        if resolved.get("price_list_id"):
            row["price_list_id"] = resolved["price_list_id"]
        if pid and not row.get("prod_id"):
            row["prod_id"] = pid
        out.append(row)
    doc["itens"] = out
    return doc


def _validar_troca_aprovacao(aprov):
    """Exige carimbo de gerente/admin na troca."""
    if not isinstance(aprov, dict):
        raise ValueError("troca exige aprovação do gerente")
    role = str(aprov.get("role") or "").lower()
    if role not in ("gerente", "admin"):
        raise ValueError("aprovação deve ser de gerente ou admin")
    if not (aprov.get("usuario") or aprov.get("user_id") or aprov.get("nome")):
        raise ValueError("aprovação de troca incompleta")
    return {
        "user_id": aprov.get("user_id") or "",
        "usuario": aprov.get("usuario") or "",
        "nome": aprov.get("nome") or aprov.get("usuario") or "",
        "role": role,
        "at": aprov.get("at") or datetime.now().isoformat(timespec="seconds"),
        "motivo": (aprov.get("motivo") or "").strip(),
        "venda_ref": aprov.get("venda_ref") or aprov.get("nfce") or "",
    }


def autorizar_gerente(usuario, senha, users, motivo=""):
    """Valida senha de gerente/admin para override operacional (troca etc.)."""
    user_login = str(usuario or "").strip()
    if not user_login or senha is None or senha == "":
        raise ValueError("informe usuário e senha do gerente")
    for uid, u in (users or {}).items():
        if str(u.get("usuario") or "") != user_login:
            continue
        if u.get("senha") != hash_password(senha):
            raise ValueError("usuário ou senha incorretos")
        if not u.get("ativo", True):
            raise ValueError("usuário desativado")
        role = str(u.get("role") or "").lower()
        if role not in ("gerente", "admin"):
            raise ValueError("apenas gerente ou admin pode autorizar")
        return {
            "user_id": uid,
            "usuario": u.get("usuario") or user_login,
            "nome": u.get("nome") or u.get("usuario") or user_login,
            "role": role,
            "at": datetime.now().isoformat(timespec="seconds"),
            "motivo": str(motivo or "").strip(),
        }
    raise ValueError("usuário ou senha incorretos")


ROLES = {
    # Administração / sistema
    "admin": {
        "label": "Administrador",
        "grupo": "sistema",
        "permissoes": "*",
        "pos": "hub",
        "descricao": "Configurações, usuários, terminais e todos os módulos",
    },
    # Operação POS (plano RFC)
    "vendedor": {
        "label": "Vendedor",
        "grupo": "pos",
        "permissoes": ["dashboard", "pos", "produtos"],
        "pos": "pdv",
        "descricao": "Opera um PDV (vínculo 1:1). Não acessa Caixa nem Configurações.",
    },
    "caixa": {
        "label": "Caixa",
        "grupo": "pos",
        "permissoes": ["dashboard", "pos", "nfce"],
        "pos": "caixa",
        "descricao": "Terminal Caixa: fila, pagamento e NFC-e. Vê PDVs da loja.",
    },
    "gerente": {
        "label": "Gerente",
        "grupo": "pos",
        "permissoes": ["dashboard", "pos", "nfce", "produtos", "relatorios"],
        "pos": "ambos",
        "descricao": "Supervisão da loja: PDVs e Caixas do estabelecimento.",
    },
    # Legado (mantidos)
    "supervisor": {
        "label": "Supervisor",
        "grupo": "legado",
        "permissoes": ["dashboard", "nfe", "nfce", "nfse", "clientes", "produtos", "relatorios", "folha", "contabilidade"],
        "pos": "ambos",
        "descricao": "Perfil legado — preferir Gerente no POS.",
    },
    "operador": {
        "label": "Operador",
        "grupo": "legado",
        "permissoes": ["dashboard", "nfe", "nfce", "pos"],
        "pos": "pdv",
        "descricao": "Perfil legado — preferir Vendedor no POS.",
    },
    "fiscal": {
        "label": "Fiscal",
        "grupo": "fiscal",
        "permissoes": ["dashboard", "nfe", "nfce", "nfse", "certificados", "sped", "contabilidade"],
        "pos": None,
        "descricao": "Documentos fiscais e visão contábil (não opera PDV).",
    },
    "contabil": {
        "label": "Responsável Contábil",
        "grupo": "fiscal",
        "permissoes": ["dashboard", "contabilidade", "relatorios", "sped"],
        "pos": None,
        "descricao": "Dono técnico do plano de contas (CRUD; exclusão exclusiva deste perfil + admin).",
    },
}

# Quem pode criar/editar plano de contas
PLAN_CONTAS_WRITE_ROLES = frozenset({"admin", "contabil", "fiscal"})
# Exclusão: só responsável contábil/fiscal (termo técnico) — admin só como break-glass
PLAN_CONTAS_DELETE_ROLES = frozenset({"contabil", "fiscal", "admin"})
# Diários: mesmas regras do plano
JOURNALS_WRITE_ROLES = PLAN_CONTAS_WRITE_ROLES
JOURNALS_DELETE_ROLES = PLAN_CONTAS_DELETE_ROLES
# WMS estrutura: admin / gerente / supervisor
WMS_WRITE_ROLES = frozenset({"admin", "gerente", "supervisor"})
WMS_DELETE_ROLES = WMS_WRITE_ROLES
DELIVERY_WRITE_ROLES = WMS_WRITE_ROLES
DELIVERY_DELETE_ROLES = WMS_DELETE_ROLES

ROLE_IDS = set(ROLES.keys())

def role_label(role):
    return (ROLES.get(role) or {}).get("label") or role or "—"

def user_empresas(user):
    if user.get("role") == "admin":
        return list(load_empresas().keys())
    return list(user.get("empresas", {}).keys())

class AuthHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/auth/me":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            for uid, u in users.items():
                if u.get("token") == token:
                    data = dict(u)
                    data.pop("senha", None)
                    data.pop("token", None)
                    data["id"] = uid
                    data["empresas"] = user_empresas(u)
                    data["pos"] = (ROLES.get(data.get("role")) or {}).get("pos")
                    return self._json({"status": "ok", "conta": data})
            return self._json({"status": "error", "message": "Token inválido"}, 401)

        if parsed.path == "/api/auth/check-setup":
            users = load_users()
            has_admin = any(u.get("role") == "admin" for u in users.values())
            return self._json({"status": "ok", "setup": not has_admin})

        if parsed.path == "/api/apps":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            out = app_registry.catalog()
            return self._json({
                "status": "ok",
                **out,
                "menu_module_app": app_registry.MENU_MODULE_APP,
                "accounting_menu_ids": sorted(app_registry.ACCOUNTING_MENU_APP_IDS),
                "base_menu_ids": sorted(app_registry.BASE_MENU_IDS),
            })

        if parsed.path == "/api/platform/setup":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            try:
                out = platform_setup.status()
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out})

        if parsed.path == "/api/system/parameters":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            return self._json({"status": "ok", "parameters": platform_setup.load_parameters()})

        if parsed.path == "/api/system/backup":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            if not users:
                return self._json({"status": "error", "message": "Sem usuários cadastrados"}, 401)
            if not self._find_user(token, users) or self._find_user(token, users).get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            return self._json({"status": "ok", "backups": platform_setup.list_backups()})

        if parsed.path == "/api/system/lifecycle":
            return self._json({"status": "ok", "lifecycle": platform_setup.status()["lifecycle"]})

        if parsed.path == "/api/system/log":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                limit = int((qs.get("limit") or ["100"])[0])
            except ValueError:
                limit = 100
            return self._json({"status": "ok", **platform_setup.load_log(limit)})

        if parsed.path == "/api/auth/logout":
            return self._json({"status": "ok"})

        if parsed.path == "/api/auth/minhas-empresas":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            empresas = load_empresas()
            lista = []
            for eid in user_empresas(current):
                if eid in empresas:
                    e = dict(empresas[eid])
                    e["id"] = eid
                    e["role"] = current.get("empresas", {}).get(eid, current["role"])
                    lista.append(e)
            return self._json({"status": "ok", "empresas": lista})

        if parsed.path == "/api/admin/users":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            lista = []
            for uid, u in users.items():
                role = u.get("role", "operador")
                item = {"id": uid, "usuario": u["usuario"], "nome": u.get("nome", ""),
                        "role": role, "role_label": role_label(role),
                        "ativo": u.get("ativo", True),
                        "email": u.get("email", ""), "empresas": u.get("empresas", {})}
                lista.append(item)
            return self._json({"status": "ok", "users": lista, "roles": ROLES})

        if parsed.path == "/api/admin/empresas":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            empresas = load_empresas()
            lista = []
            for eid, e in empresas.items():
                item = dict(e)
                item["id"] = eid
                lista.append(item)
            org = org_store.load_organizacao()
            return self._json({
                "status": "ok",
                "organizacao": org,
                "empresas": lista,
            })

        if parsed.path == "/api/admin/organizacao":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "organizacao": org_store.load_organizacao()})

        if parsed.path == "/api/folha/empresa":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            emp = org_store.resolve_empresa_fiscal()
            pronta, faltantes = org_store.folha_prontida()
            return self._json({
                "status": "ok",
                "empresa": emp,
                "folha_pronta": pronta,
                "faltantes": faltantes,
            })

        if parsed.path == "/api/folha/rescisoes":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "rescisoes": cobol_bridge.rescisao_listar()})

        if parsed.path in ("/api/folha/config", "/api/folha/competencias"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                cobol_bridge.folha_config_seed()
                if parsed.path == "/api/folha/config":
                    return self._json(cobol_bridge.folha_config_ler())
                return self._json({"competencias": cobol_bridge.folha_listar()})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/folha/holerites":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                return self._json({"status": "ok",
                                   "holerites": cobol_bridge.holerite_listar()})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/folha/holerite/detalhes":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            qs = urllib.parse.parse_qs(parsed.query)
            hid = (qs.get("id") or [""])[0]
            if not hid:
                return self._json({"status": "error", "message": "ID do holerite obrigatorio"}, 400)
            try:
                return self._json({"status": "ok", **cobol_bridge.holerite_mostrar(hid)})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/folha/competencia":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            qs = urllib.parse.parse_qs(parsed.query)
            competencia = (qs.get("competencia") or [""])[0]
            if not competencia:
                return self._json({"status": "error", "message": "Competencia obrigatoria"}, 400)
            try:
                return self._json({"status": "ok", **cobol_bridge.folha_mostrar(competencia)})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/permissions":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "roles": ROLES})

        if parsed.path == "/api/admin/pos/terminais":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            data = load_pos_terminais()
            return self._json({"status": "ok", "terminais": data.get("terminais", [])})

        if parsed.path == "/api/admin/fiscal/estabelecimentos":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            empresas = load_empresas()
            store = load_estab_fiscal_store()
            lista = []
            for eid, e in empresas.items():
                merged = resolve_empresa_fiscal(eid)
                item = {
                    "id": eid,
                    "nome": e.get("nome"),
                    "cnpj_cadastro": e.get("cnpj"),
                    "ativo": e.get("ativo", True),
                    "fiscal": {
                        "csc_id": merged.get("csc_id", "1"),
                        "csc": merged.get("csc", ""),
                        "serie_nfce": int(merged.get("serie_nfce") or 1),
                        "numero_nfce": int(merged.get("numero_nfce") or 0),
                        "ambiente": int(merged.get("ambiente") or 2),
                        "certificado": merged.get("certificado", ""),
                        "cert_senha_set": bool(merged.get("cert_senha")),
                        "crt": merged.get("crt", 1),
                        "uf": merged.get("uf"),
                        "inscricao_est": merged.get("inscricao_est", ""),
                        "cod_municipio": merged.get("cod_municipio", ""),
                        "municipio": merged.get("municipio", ""),
                        "has_overlay": eid in store,
                    },
                }
                lista.append(item)
            return self._json({"status": "ok", "estabelecimentos": lista})

        if parsed.path.startswith("/api/admin/fiscal/estabelecimentos/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            eid = parsed.path.rstrip("/").split("/")[-1]
            if eid not in load_empresas():
                return self._json({"status": "error", "message": "Estabelecimento não encontrado"}, 404)
            return self._json({
                "status": "ok",
                "id": eid,
                "empresa": resolve_empresa_fiscal(eid),
                "overlay": load_estab_fiscal_store().get(eid, {}),
            })

        if parsed.path.startswith("/api/admin/pos/terminais/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            tid = parsed.path.rstrip("/").split("/")[-1]
            data = load_pos_terminais()
            for t in data.get("terminais", []):
                if t.get("id") == tid:
                    return self._json({"status": "ok", "terminal": t})
            return self._json({"status": "error", "message": "Terminal não encontrado"}, 404)

        if parsed.path == "/api/pos/contexto":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uid = None
            for k, u in users.items():
                if u.get("token") == token:
                    uid = k
                    break
            role = (current.get("role") or "operador").lower()
            empresas = load_empresas()
            data = load_pos_terminais()
            terminais = [
                t for t in data.get("terminais", [])
                if t.get("ativo", True) and t.get("usuario_id") == uid
            ]
            # Gerente/caixa/admin no mesmo estabelecimento: listar todos os terminais da loja
            loja_ids = {t.get("estabelecimento_id") for t in terminais if t.get("estabelecimento_id")}
            visao_ampla = []
            if role in ("caixa", "gerente", "admin") and loja_ids:
                visao_ampla = [
                    t for t in data.get("terminais", [])
                    if t.get("ativo", True) and t.get("estabelecimento_id") in loja_ids
                ]
            elif role == "admin" and not terminais:
                # Admin sem terminal: contexto da matriz (demo / supervisão)
                visao_ampla = [t for t in data.get("terminais", []) if t.get("ativo", True)]

            primary = terminais[0] if terminais else None
            if not primary and role == "admin":
                # fallback estabelecimento matriz
                mid = "matriz" if "matriz" in empresas else (next(iter(empresas), None))
                estab = dict(empresas.get(mid or "", {}) or {})
                if mid:
                    estab["id"] = mid
                return self._json({
                    "status": "ok",
                    "role": role,
                    "usuario_id": uid,
                    "terminal": None,
                    "estabelecimento": estab or None,
                    "terminais": visao_ampla,
                    "modo_sugerido": "pdv",
                    "pode_trocar_modo": True,
                    "aviso": "Admin sem terminal vinculado — modo supervisão/demo",
                })

            if not primary:
                return self._json({
                    "status": "ok",
                    "role": role,
                    "usuario_id": uid,
                    "terminal": None,
                    "estabelecimento": None,
                    "terminais": [],
                    "modo_sugerido": "pdv",
                    "pode_trocar_modo": False,
                    "aviso": "Nenhum terminal ativo vinculado a este usuário. Peça ao Admin em Configurações → POS.",
                })

            eid = primary.get("estabelecimento_id")
            estab = dict(empresas.get(eid, {}) or {})
            estab["id"] = eid
            tipo = (primary.get("tipo") or "pdv").lower()
            pode_trocar = role in ("admin", "gerente") or (
                any(t.get("tipo") == "pdv" for t in terminais)
                and any(t.get("tipo") == "caixa" for t in terminais)
            )
            return self._json({
                "status": "ok",
                "role": role,
                "usuario_id": uid,
                "terminal": primary,
                "estabelecimento": estab,
                "terminais": visao_ampla if visao_ampla else terminais,
                "modo_sugerido": "caixa" if tipo == "caixa" else "pdv",
                "pode_trocar_modo": pode_trocar,
                "aviso": None,
            })

        # ── POS: leitura (qualquer usuário autenticado) ──
        if parsed.path == "/api/pos/produtos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            estab = (qs.get("estabelecimento_id") or [""])[0].strip()
            if not estab:
                # Inferir do terminal do usuário
                users = load_users()
                current = self._find_user(token, users)
                uid = None
                for k, u in users.items():
                    if u.get("token") == token:
                        uid = k
                        break
                if uid:
                    for t in load_pos_terminais().get("terminais", []):
                        if t.get("ativo", True) and t.get("usuario_id") == uid:
                            estab = (t.get("estabelecimento_id") or "").strip()
                            break
            produtos = cobol_bridge.produtos_para_pos(estab or None)
            produtos = enriquecer_produtos_com_promise(produtos, estab or None)
            pl_id = None
            if estab:
                try:
                    pl_id = (load_empresas().get(estab) or {}).get("default_price_list_id") or None
                except Exception:
                    pl_id = None
            produtos = price_lists.apply_to_produtos(produtos, estabelecimento_id=estab or None, list_id=pl_id)
            return self._json({
                "status": "ok",
                "source": "api",
                "estabelecimento_id": estab or None,
                "price_list_id": pl_id,
                "promise": True,
                "produtos": produtos,
            })

        if parsed.path == "/api/pos/promise":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            estab = (qs.get("estabelecimento_id") or [""])[0].strip()
            pid = (qs.get("produto_id") or [""])[0].strip()
            if not pid:
                return self._json({"status": "error", "message": "produto_id obrigatório"}, 400)
            if not estab:
                users = load_users()
                uid = next((k for k, u in users.items() if u.get("token") == token), None)
                term = _terminal_do_usuario(uid)
                if term:
                    estab = (term.get("estabelecimento_id") or "").strip()
            prom = promise_produto(estab, pid)
            return self._json({
                "status": "ok",
                "estabelecimento_id": estab or None,
                "produto_id": pid,
                **prom,
            })

        if parsed.path == "/api/pos/vendas":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            q = (qs.get("q") or [""])[0].strip().lower()
            q_digits = "".join(ch for ch in q if ch.isdigit())
            try:
                limit = int((qs.get("limit") or ["40"])[0])
            except (TypeError, ValueError):
                limit = 40
            limit = max(1, min(limit, 100))
            vendas = load_json(os.path.join(BASE_DIR, "dados", "vendas.json"))
            lista = list((vendas.get("vendas") if isinstance(vendas, dict) else []) or [])
            # NFC-e números por venda_id (se houver)
            nfce_by_venda = {}
            try:
                for n in (load_json(os.path.join(BASE_DIR, "dados", "nfce.json")).get("nfce") or []):
                    vid = n.get("venda_id")
                    if vid is not None:
                        nfce_by_venda[str(vid)] = n.get("numero") or n.get("nNF") or ""
            except Exception:
                pass
            out = []
            for v in reversed(lista):
                if not isinstance(v, dict):
                    continue
                vid = v.get("id")
                cliente = str(v.get("cliente") or "")
                cpf = str(v.get("cliente_doc") or v.get("cpf") or "")
                nfce_num = str(
                    v.get("nfce")
                    or v.get("numero_nfce")
                    or nfce_by_venda.get(str(vid))
                    or vid
                    or ""
                )
                nfce_pad = str(nfce_num).zfill(9) if str(nfce_num).isdigit() else str(nfce_num)
                blob = (cliente + " " + cpf + " " + nfce_pad + " " + str(vid)).lower()
                blob_digits = "".join(ch for ch in blob if ch.isdigit())
                if q:
                    if q not in blob and not (q_digits and q_digits in blob_digits):
                        continue
                lines = []
                for it in v.get("itens") or []:
                    if not isinstance(it, dict):
                        continue
                    qtd = float(it.get("qtd") or 0)
                    if qtd <= 0:
                        continue
                    lines.append({
                        "id": it.get("prod_id") or it.get("id"),
                        "nome": it.get("produto") or it.get("nome") or "Item",
                        "preco": float(it.get("preco") or 0),
                        "qtd": qtd,
                    })
                if not lines:
                    continue
                data = str(v.get("data") or "")
                try:
                    if len(data) >= 10:
                        y, m, d = data[:10].split("-")
                        data_fmt = f"{d}/{m}/{y}"
                    else:
                        data_fmt = data
                except Exception:
                    data_fmt = data
                out.append({
                    "id": vid,
                    "nfce": nfce_pad,
                    "cpf": cpf,
                    "client": cliente or "Consumidor",
                    "date": data_fmt,
                    "total": float(v.get("total") or 0),
                    "lines": lines,
                    "estabelecimento_id": v.get("estabelecimento_id") or "",
                })
                if len(out) >= limit:
                    break
            return self._json({"status": "ok", "vendas": out, "total": len(out)})

        if parsed.path == "/api/pos/caixa/movimentos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            tid = (qs.get("terminal_id") or [""])[0].strip() or None
            eid = (qs.get("estabelecimento_id") or [""])[0].strip() or None
            sid = (qs.get("sessao_id") or [""])[0].strip() or None
            try:
                limit = int((qs.get("limit") or ["50"])[0])
            except (TypeError, ValueError):
                limit = 50
            rows = pos_caixa.list_movimentos(
                terminal_id=tid, estabelecimento_id=eid, sessao_id=sid, limit=limit
            )
            return self._json({"status": "ok", "movimentos": rows, "total": len(rows)})

        if parsed.path == "/api/pos/caixa/sessao":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uid = next((k for k, u in users.items() if u.get("token") == token), None)
            qs = urllib.parse.parse_qs(parsed.query or "")
            tid = (qs.get("terminal_id") or [""])[0].strip()
            eid = (qs.get("estabelecimento_id") or [""])[0].strip()
            if not tid or not eid:
                term = _terminal_do_usuario(uid)
                if term:
                    tid = tid or (term.get("id") or "")
                    eid = eid or (term.get("estabelecimento_id") or "")
            sessao = pos_caixa.get_sessao_aberta(terminal_id=tid or None, estabelecimento_id=eid or None)
            if not sessao:
                return self._json({
                    "status": "ok",
                    "sessao": None,
                    "resumo": None,
                    "message": "nenhuma sessão aberta",
                })
            resumo = pos_caixa.resumo_sessao(sessao)
            return self._json({"status": "ok", "sessao": sessao, "resumo": resumo})

        if parsed.path == "/api/pos/caixa/sessoes":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                limit = int((qs.get("limit") or ["30"])[0] or 30)
            except (TypeError, ValueError):
                limit = 30
            rows = pos_caixa.list_sessoes(
                terminal_id=(qs.get("terminal_id") or [""])[0].strip() or None,
                estabelecimento_id=(qs.get("estabelecimento_id") or [""])[0].strip() or None,
                status=(qs.get("status") or [""])[0].strip() or None,
                limit=limit,
            )
            return self._json({"status": "ok", "sessoes": rows, "total": len(rows)})

        # ── WMS armazéns (RFC-9001 MVP) ──
        if parsed.path == "/api/wms/armazens":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            ativos = None
            a_raw = (qs.get("ativos") or [""])[0].strip().lower()
            if a_raw in ("1", "true", "yes"):
                ativos = True
            elif a_raw in ("0", "false", "no"):
                ativos = False
            try:
                out = wms_warehouses.list_armazens(
                    q=(qs.get("q") or [""])[0],
                    tipo=(qs.get("tipo") or [""])[0] or None,
                    ativos=ativos,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in WMS_WRITE_ROLES,
                    "pode_excluir": role in WMS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/wms/armazens/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **wms_warehouses.meta()})
            row = wms_warehouses.get_armazem(key)
            if not row:
                return self._json({"status": "error", "message": "Armazém não encontrado"}, 404)
            return self._json({"status": "ok", "armazem": row})

        # ── WMS localizações (RFC-9002 MVP) ──
        if parsed.path == "/api/wms/localizacoes":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = wms_locations.list_localizacoes(
                    q=(qs.get("q") or [""])[0],
                    armazem=(qs.get("armazem") or [""])[0] or None,
                    area=(qs.get("area") or [""])[0] or None,
                    tipo=(qs.get("tipo") or [""])[0] or None,
                    status=(qs.get("status") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in WMS_WRITE_ROLES,
                    "pode_excluir": role in WMS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/wms/localizacoes/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **wms_locations.meta()})
            row = wms_locations.get_localizacao(key)
            if not row:
                return self._json({"status": "error", "message": "Localização não encontrada"}, 404)
            return self._json({"status": "ok", "localizacao": row})

        # ── WMS tipos de operação (RFC-9003 MVP) ──
        if parsed.path == "/api/wms/tipos-operacao":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            ativos = None
            a_raw = (qs.get("ativos") or [""])[0].strip().lower()
            if a_raw in ("1", "true", "yes"):
                ativos = True
            elif a_raw in ("0", "false", "no"):
                ativos = False
            try:
                out = wms_operation_types.list_tipos(
                    q=(qs.get("q") or [""])[0],
                    direcao=(qs.get("direcao") or [""])[0] or None,
                    template=(qs.get("template") or [""])[0] or None,
                    ativos=ativos,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in WMS_WRITE_ROLES,
                    "pode_excluir": role in WMS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/wms/tipos-operacao/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **wms_operation_types.meta()})
            row = wms_operation_types.get_tipo(key)
            if not row:
                return self._json({"status": "error", "message": "Tipo de operação não encontrado"}, 404)
            return self._json({"status": "ok", "tipo": row})

        # ── WMS operações (RFC-9004 MVP) ──
        if parsed.path == "/api/wms/operacoes":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = wms_operations.list_operacoes(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    tipo=(qs.get("tipo") or [""])[0] or None,
                    armazem=(qs.get("armazem") or [""])[0] or None,
                    prioridade=(qs.get("prioridade") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in WMS_WRITE_ROLES,
                    "pode_excluir": role in WMS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/wms/operacoes/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **wms_operations.meta()})
            row = wms_operations.get_operacao(key)
            if not row:
                return self._json({"status": "error", "message": "Operação não encontrada"}, 404)
            return self._json({"status": "ok", "operacao": row})

        # ── WMS tarefas (RFC-9005 MVP) ──
        if parsed.path == "/api/wms/tarefas":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = wms_tasks.list_tarefas(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    tipo=(qs.get("tipo") or [""])[0] or None,
                    armazem=(qs.get("armazem") or [""])[0] or None,
                    operacao_id=(qs.get("operacao_id") or [""])[0] or None,
                    operador=(qs.get("operador") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in WMS_WRITE_ROLES,
                    "pode_excluir": role in WMS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/wms/tarefas/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **wms_tasks.meta()})
            row = wms_tasks.get_tarefa(key)
            if not row:
                return self._json({"status": "error", "message": "Tarefa não encontrada"}, 404)
            return self._json({"status": "ok", "tarefa": row})

        # ── WMS picking & packing (RFC-9006 MVP) ──
        if parsed.path == "/api/wms/picking":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = wms_picking.list_pick_lists(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    armazem=(qs.get("armazem") or [""])[0] or None,
                    estrategia=(qs.get("estrategia") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in WMS_WRITE_ROLES,
                    "pode_excluir": role in WMS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/wms/picking/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **wms_picking.meta()})
            row = wms_picking.get_pick_list(key)
            if not row:
                return self._json({"status": "error", "message": "Lista de picking não encontrada"}, 404)
            return self._json({"status": "ok", "pick_list": row})

        if parsed.path == "/api/wms/packages":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = wms_picking.list_packages(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    pick_list_id=(qs.get("pick_list_id") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in WMS_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/wms/packages/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            row = wms_picking.get_package(key)
            if not row:
                return self._json({"status": "error", "message": "Volume não encontrado"}, 404)
            return self._json({"status": "ok", "package": row})

        # ── WMS receiving process (RFC-9007 MVP) ──
        if parsed.path == "/api/wms/recebimentos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = wms_receiving.list_recebimentos(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    origem=(qs.get("origem") or [""])[0] or None,
                    armazem=(qs.get("armazem") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in WMS_WRITE_ROLES,
                    "pode_excluir": role in WMS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/wms/recebimentos/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **wms_receiving.meta()})
            row = wms_receiving.get_recebimento(key)
            if not row:
                return self._json({"status": "error", "message": "Recebimento WMS não encontrado"}, 404)
            return self._json({"status": "ok", "recebimento": row})

        # ── WMS shipping process (RFC-9008 MVP) ──
        if parsed.path == "/api/wms/expedicoes":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = wms_shipping.list_expedicoes(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    destino=(qs.get("destino") or [""])[0] or None,
                    armazem=(qs.get("armazem") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in WMS_WRITE_ROLES,
                    "pode_excluir": role in WMS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/wms/expedicoes/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **wms_shipping.meta()})
            row = wms_shipping.get_expedicao(key)
            if not row:
                return self._json({"status": "error", "message": "Expedição WMS não encontrada"}, 404)
            return self._json({"status": "ok", "expedicao": row})

        # ── WMS analytics (RFC-9009) + workspace (RFC-9010) — read-only ──
        if parsed.path == "/api/wms/analytics":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = wms_analytics.dashboard(
                    armazem=(qs.get("armazem") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out, "meta": wms_analytics.meta()})

        if parsed.path == "/api/wms/workspace":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = wms_workspace.workspace(
                    armazem=(qs.get("armazem") or [""])[0] or None,
                    operador=(qs.get("operador") or [""])[0] or None,
                    perfil=(qs.get("perfil") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in WMS_WRITE_ROLES,
                    "role": role,
                },
            })

        # ── Delivery Platform (RFC-18000/18001/18002/18004 MVP) ──
        if parsed.path == "/api/delivery/orders":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_orders.list_orders(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    parceiro=(qs.get("parceiro") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "pode_excluir": role in DELIVERY_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/delivery/orders/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **delivery_orders.meta()})
            row = delivery_orders.get_order(key)
            if not row:
                return self._json({"status": "error", "message": "Entrega não encontrada"}, 404)
            return self._json({"status": "ok", "order": row})

        if parsed.path == "/api/delivery/tarefas":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_tasks.list_tarefas(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    entrega_id=(qs.get("entrega_id") or [""])[0] or None,
                    operador=(qs.get("operador") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/delivery/tarefas/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **delivery_tasks.meta()})
            row = delivery_tasks.get_tarefa(key)
            if not row:
                return self._json({"status": "error", "message": "Tarefa de entrega não encontrada"}, 404)
            return self._json({"status": "ok", "tarefa": row})

        if parsed.path == "/api/delivery/recursos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            ativos = None
            if (qs.get("ativos") or [""])[0] in ("1", "true", "yes"):
                ativos = True
            try:
                out = delivery_resources.list_recursos(
                    q=(qs.get("q") or [""])[0],
                    tipo=(qs.get("tipo") or [""])[0] or None,
                    status=(qs.get("status") or [""])[0] or None,
                    ativos=ativos,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/delivery/recursos/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **delivery_resources.meta()})
            row = delivery_resources.get_recurso(key)
            if not row:
                return self._json({"status": "error", "message": "Recurso não encontrado"}, 404)
            return self._json({"status": "ok", "recurso": row})

        if parsed.path == "/api/delivery/dispatch":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_dispatch.list_dispatches(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    data=(qs.get("data") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path == "/api/delivery/dispatch/queue":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_dispatch.queue(
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    status=(qs.get("status") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out})

        if parsed.path.startswith("/api/delivery/dispatch/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **delivery_dispatch.meta()})
            row = delivery_dispatch.get_dispatch(key)
            if not row:
                return self._json({"status": "error", "message": "Despacho não encontrado"}, 404)
            return self._json({"status": "ok", "dispatch": row})

        if parsed.path == "/api/delivery/scheduling":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_scheduling.list_slots(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    data=(qs.get("data") or [""])[0] or None,
                    data_de=(qs.get("data_de") or [""])[0] or None,
                    data_ate=(qs.get("data_ate") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path == "/api/delivery/scheduling/availability":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_scheduling.availability(
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    data_de=(qs.get("data_de") or [""])[0] or None,
                    data_ate=(qs.get("data_ate") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out})

        if parsed.path.startswith("/api/delivery/scheduling/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **delivery_scheduling.meta()})
            row = delivery_scheduling.get_slot(key)
            if not row:
                return self._json({"status": "error", "message": "Slot não encontrado"}, 404)
            return self._json({"status": "ok", "slot": row})

        if parsed.path == "/api/delivery/tracking":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_tracking.list_tracks(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    fonte=(qs.get("fonte") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/delivery/tracking/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            parts = parsed.path.rstrip("/").split("/")
            key = urllib.parse.unquote(parts[-1])
            if key == "meta":
                return self._json({"status": "ok", **delivery_tracking.meta()})
            sub = None
            track_key = key
            if len(parts) >= 6 and parts[-2] != "tracking":
                sub = parts[-1]
                track_key = urllib.parse.unquote(parts[-2])
            try:
                if sub == "timeline":
                    return self._json({"status": "ok", **delivery_tracking.timeline(track_key)})
                if sub == "customer":
                    return self._json({
                        "status": "ok",
                        "customer": delivery_tracking.customer_view(track_key),
                    })
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            row = delivery_tracking.get_track(track_key)
            if not row:
                return self._json({"status": "error", "message": "Tracking não encontrado"}, 404)
            return self._json({"status": "ok", "track": row})

        if parsed.path == "/api/delivery/pod":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_pod.list_pods(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    entrega_id=(qs.get("entrega_id") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/delivery/pod/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            parts = parsed.path.rstrip("/").split("/")
            key = urllib.parse.unquote(parts[-1])
            qs = urllib.parse.parse_qs(parsed.query or "")
            if key == "meta":
                return self._json({"status": "ok", **delivery_pod.meta()})
            if key == "summary":
                eid = (qs.get("entrega_id") or [""])[0]
                try:
                    return self._json({"status": "ok", **delivery_pod.summary(eid)})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if len(parts) >= 6 and parts[-1] == "summary":
                eid = urllib.parse.unquote(parts[-2])
                try:
                    return self._json({"status": "ok", **delivery_pod.summary(eid)})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            row = delivery_pod.get_pod(key)
            if not row:
                return self._json({"status": "error", "message": "POD não encontrado"}, 404)
            return self._json({"status": "ok", "pod": row})

        if parsed.path == "/api/delivery/analytics":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_analytics.dashboard(
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    data_de=(qs.get("data_de") or [""])[0] or None,
                    data_ate=(qs.get("data_ate") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({
                "status": "ok",
                **out,
                "meta": delivery_analytics.meta(),
            })

        if parsed.path == "/api/delivery/workspace":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_workspace.workspace(
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    perfil=(qs.get("perfil") or [""])[0] or None,
                    periodo=(qs.get("periodo") or ["today"])[0] or "today",
                    motorista=(qs.get("motorista") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path == "/api/delivery/dashboard":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_dashboard.dashboard(
                    fonte=(qs.get("fonte") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out})

        if parsed.path == "/api/delivery/queue":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_queue.queue(
                    categoria=(qs.get("categoria") or [""])[0] or None,
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    status=(qs.get("status") or [""])[0] or None,
                    prioridade=(qs.get("prioridade") or [""])[0] or None,
                    motorista=(qs.get("motorista") or [""])[0] or None,
                    q=(qs.get("q") or [""])[0] or None,
                    regiao=(qs.get("regiao") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path == "/api/delivery/planning":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_planning.board(
                    mode=(qs.get("mode") or ["driver"])[0] or "driver",
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    data=(qs.get("data") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path == "/api/delivery/calendar":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_calendar.calendar(
                    view=(qs.get("view") or ["day"])[0] or "day",
                    data=(qs.get("data") or [""])[0] or None,
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    motorista=(qs.get("motorista") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path == "/api/delivery/manifest":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_manifest.list_manifests(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    data=(qs.get("data") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path == "/api/delivery/manifest/candidates":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_manifest.candidates(
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    data=(qs.get("data") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out})

        if parsed.path.startswith("/api/delivery/manifest/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **delivery_manifest.meta()})
            if key == "candidates":
                qs = urllib.parse.parse_qs(parsed.query or "")
                out = delivery_manifest.candidates(
                    fonte=(qs.get("fonte") or [""])[0] or None,
                    data=(qs.get("data") or [""])[0] or None,
                )
                return self._json({"status": "ok", **out})
            parts = parsed.path.rstrip("/").split("/")
            # /api/delivery/manifest/{id}/document
            if len(parts) >= 5 and parts[-1] == "document":
                mid = urllib.parse.unquote(parts[-2])
                try:
                    out = delivery_manifest.document(mid)
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
                return self._json({"status": "ok", **out})
            row = delivery_manifest.get_manifest(key)
            if not row:
                return self._json({"status": "error", "message": "Manifesto não encontrado"}, 404)
            return self._json({"status": "ok", "manifest": row})

        if parsed.path == "/api/delivery/trip":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_trip.list_trips(
                    q=(qs.get("q") or [""])[0],
                    status=(qs.get("status") or [""])[0] or None,
                    data=(qs.get("data") or [""])[0] or None,
                    manifesto_id=(qs.get("manifesto_id") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in DELIVERY_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/delivery/trip/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **delivery_trip.meta()})
            row = delivery_trip.get_trip(key)
            if not row:
                return self._json({"status": "error", "message": "Trip não encontrado"}, 404)
            return self._json({"status": "ok", "trip": row})

        if parsed.path == "/api/delivery/driver":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_driver_workspace.cockpit(
                    recurso_id=(qs.get("recurso_id") or [""])[0] or None,
                    motorista=(qs.get("motorista") or [""])[0] or None,
                    trip_id=(qs.get("trip_id") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": True,  # execução de campo — qualquer autenticado
                    "role": role,
                },
            })

        if parsed.path == "/api/delivery/stops":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = delivery_stops.list_stops(
                    trip_id=(qs.get("trip_id") or [""])[0] or None,
                    status=(qs.get("status") or [""])[0] or None,
                    q=(qs.get("q") or [""])[0] or None,
                    data=(qs.get("data") or [""])[0] or None,
                    only_active_trips=(qs.get("ativas") or [""])[0] in ("1", "true", "yes"),
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": True,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/delivery/stops/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            # /api/delivery/stops/{trip_id}/{seq}
            parts = parsed.path.rstrip("/").split("/")
            if len(parts) < 6:
                return self._json({"status": "error", "message": "Use /api/delivery/stops/{trip}/{seq}"}, 400)
            tid = urllib.parse.unquote(parts[-2])
            seq = urllib.parse.unquote(parts[-1])
            try:
                row = delivery_stops.get_stop(tid, seq)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 404)
            return self._json({"status": "ok", "stop": row})

        if parsed.path == "/api/inventory/balance":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            estab = (qs.get("estabelecimento_id") or [""])[0].strip()
            pid = (qs.get("produto_id") or [""])[0].strip()
            balances = inventory_mvp.load_balances()
            if not estab:
                return self._json({
                    "status": "ok",
                    "por_estabelecimento": balances.get("por_estabelecimento") or {},
                    "atualizado_em": balances.get("atualizado_em"),
                })
            if pid:
                return self._json({
                    "status": "ok",
                    "estabelecimento_id": estab,
                    "produto_id": pid,
                    "balance": inventory_mvp.inventory_balance(estab, pid, balances=balances),
                })
            loja = (balances.get("por_estabelecimento") or {}).get(estab) or {}
            return self._json({
                "status": "ok",
                "estabelecimento_id": estab,
                "balances": loja,
            })

        if parsed.path == "/api/inventory/movements":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                limit = int((qs.get("limit") or ["50"])[0])
            except (TypeError, ValueError):
                limit = 50
            estab = (qs.get("estabelecimento_id") or [""])[0].strip() or None
            pid = (qs.get("produto_id") or [""])[0].strip() or None
            rows = inventory_mvp.list_recent_movements(limit=limit, estabelecimento_id=estab, produto_id=pid)
            return self._json({"status": "ok", "movements": rows, "total": len(rows)})

        if parsed.path == "/api/inventory/transit":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            itens = [
                t for t in (inventory_mvp.load_transit().get("itens") or [])
                if t.get("status") == "open"
            ]
            return self._json({"status": "ok", "itens": itens})

        if parsed.path == "/api/receiving/pending":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            status = (qs.get("status") or [""])[0].strip() or None
            rid = (qs.get("receiving_id") or [""])[0].strip() or None
            cat = (qs.get("category") or [""])[0].strip() or None
            open_only = (qs.get("open") or [""])[0].strip() in ("1", "true", "yes")
            try:
                limit = int((qs.get("limit") or ["200"])[0])
            except ValueError:
                limit = 200
            rows = receiving_pending.list_pending(
                status=status,
                receiving_id=rid,
                category=cat,
                open_only=open_only,
                limit=limit,
            )
            return self._json({
                "status": "ok",
                "items": rows,
                "total": len(rows),
                "open_count": receiving_pending.open_count(rid),
            })

        if parsed.path.startswith("/api/receiving/pending/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            pid = parsed.path.rstrip("/").split("/")[-1]
            if pid in ("resolve", "ignore", "cancel", "assign"):
                return self._json({"status": "error", "message": "id obrigatório"}, 400)
            item = receiving_pending.get_pending(pid)
            if not item:
                return self._json({"status": "error", "message": "Pendência não encontrada"}, 404)
            return self._json({"status": "ok", "item": item})

        if parsed.path == "/api/partners/lookup":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            result = partner_lookup.lookup(
                cnpj=(qs.get("cnpj") or [""])[0],
                cpf=(qs.get("cpf") or [""])[0],
                partner_code=(qs.get("partner_code") or [""])[0],
                external_ref=(qs.get("external_ref") or [""])[0],
                partner_id=(qs.get("id") or qs.get("partner_id") or [""])[0],
                role=(qs.get("role") or ["SUPPLIER"])[0] or None,
                module=(qs.get("module") or ["api"])[0],
            )
            return self._json({"status": "ok", **result})

        if parsed.path == "/api/partners/search":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            q = (qs.get("q") or [""])[0].strip()
            role = (qs.get("role") or ["SUPPLIER"])[0] or None
            try:
                limit = int((qs.get("limit") or ["20"])[0])
            except ValueError:
                limit = 20
            rows = partner_lookup.search(q, role=role, limit=limit)
            return self._json({"status": "ok", "partners": rows, "total": len(rows)})

        if parsed.path == "/api/nfe-monitor":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            status = (qs.get("status") or [""])[0].strip() or None
            try:
                limit = int((qs.get("limit") or ["100"])[0])
            except ValueError:
                limit = 100
            rows = nfe_monitor.list_documents(status=status, limit=limit)
            return self._json({"status": "ok", "documents": rows, "total": len(rows)})

        if parsed.path.startswith("/api/nfe-monitor/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            parts = parsed.path.rstrip("/").split("/")
            # /api/nfe-monitor/{id}
            if len(parts) == 4 and parts[3].isdigit():
                doc = nfe_monitor.get_document(parts[3])
                if not doc:
                    return self._json({"status": "error", "message": "Documento não encontrado"}, 404)
                return self._json({"status": "ok", "document": doc})
            return self._json({"status": "error", "message": "Rota inválida"}, 400)

        if parsed.path == "/api/receiving":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            estab = (qs.get("estabelecimento_id") or [""])[0].strip() or None
            status = (qs.get("status") or [""])[0].strip() or None
            rows = receiving_mvp.list_receivings(estabelecimento_id=estab, status=status)
            return self._json({"status": "ok", "receivings": rows, "total": len(rows)})

        if parsed.path == "/api/receiving/product-search":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            q = (qs.get("q") or [""])[0].strip()
            try:
                limit = int((qs.get("limit") or ["20"])[0])
            except ValueError:
                limit = 20
            rows = product_localization.search_products(q, limit=limit)
            return self._json({"status": "ok", "produtos": rows, "total": len(rows)})

        if parsed.path == "/api/receiving/product-refs":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            cnpj = (qs.get("supplier_cnpj") or qs.get("cnpj") or [""])[0].strip()
            rows = product_localization.list_refs(supplier_cnpj=cnpj or None)
            return self._json({"status": "ok", "refs": rows, "total": len(rows)})

        if parsed.path.startswith("/api/receiving/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            rid = parsed.path.rstrip("/").split("/")[-1]
            if rid in (
                "verify", "complete", "cancel", "product-search", "product-refs",
                "from-xml", "link-product", "scan", "start-verify", "reopen-verify",
                "link-partner", "resolve-partner", "pending", "sync-pending",
            ):
                return self._json({"status": "error", "message": "id obrigatório"}, 400)
            rec = receiving_mvp.get_receiving(rid)
            if not rec:
                return self._json({"status": "error", "message": "Recebimento não encontrado"}, 404)
            return self._json({"status": "ok", "receiving": rec})

        if parsed.path == "/api/pos/parceiros":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            try:
                data = partners_store.as_dict()
            except Exception:
                data = load_json(PARTNERS_FILE)
            role_filter = self._get_query_param(parsed.query, "role", "CUSTOMER").upper().strip()
            lista = []
            for eid, e in data.items():
                item = dict(e)
                item["id"] = eid
                if item.get("ativo") is False or str(item.get("status", "")).upper() == "INACTIVE":
                    continue
                roles = [str(r).upper() for r in (item.get("roles") or [])]
                if role_filter and role_filter not in roles:
                    continue
                lista.append(item)
            return self._json({"status": "ok", "source": "cobol", "parceiros": lista})

        # ── POS: fila PDV → Caixa ──
        if parsed.path == "/api/pos/fila":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            fila = load_pos_fila()
            pid = self._get_query_param(parsed.query, "id", "").strip()
            if pid:
                hit = next((p for p in fila["pedidos"] if str(p.get("id")) == pid), None)
                if not hit:
                    return self._json({"status": "error", "message": "Pedido não encontrado"}, 404)
                return self._json({"status": "ok", "pedido": hit})
            states_raw = self._get_query_param(parsed.query, "state", "aguardando,pagamento")
            states = {s.strip().lower() for s in states_raw.split(",") if s.strip()}
            pedidos = [p for p in fila["pedidos"] if str(p.get("state", "")).lower() in states]
            pedidos.sort(key=lambda p: p.get("createdAt") or "", reverse=True)
            return self._json({"status": "ok", "pedidos": pedidos, "next_num": fila.get("next_num")})

        if parsed.path == "/api/pos/campaigns":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            return self._json({
                "status": "ok",
                "campaigns": campaigns.active_campaigns(),
                "all": campaigns.list_all(),
            })

        # ── Plano de contas (sistema) ──
        if parsed.path == "/api/planocontas":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            analiticas = None
            a_raw = (qs.get("analiticas") or [""])[0].strip().lower()
            if a_raw in ("1", "true", "yes", "a"):
                analiticas = True
            elif a_raw in ("0", "false", "no", "s"):
                analiticas = False
            try:
                limit = int((qs.get("limit") or ["500"])[0] or 500)
            except (TypeError, ValueError):
                limit = 500
            out = planocontas.list_contas(
                q=(qs.get("q") or [""])[0],
                tipo=(qs.get("tipo") or [""])[0] or None,
                analiticas=analiticas,
                limit=limit,
            )
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "meta": planocontas.meta(),
                "permissoes": {
                    "pode_escrever": role in PLAN_CONTAS_WRITE_ROLES,
                    "pode_excluir": role in PLAN_CONTAS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/planocontas/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = parsed.path.rstrip("/").split("/")[-1]
            if key == "meta":
                return self._json({"status": "ok", **planocontas.meta()})
            conta = planocontas.get_conta(urllib.parse.unquote(key))
            if not conta:
                return self._json({"status": "error", "message": "Conta não encontrada"}, 404)
            return self._json({"status": "ok", "conta": conta})

        # ── Diários contábeis (RFC-8002 MVP) ──
        if parsed.path == "/api/diarios":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            ativos = None
            a_raw = (qs.get("ativos") or [""])[0].strip().lower()
            if a_raw in ("1", "true", "yes"):
                ativos = True
            elif a_raw in ("0", "false", "no"):
                ativos = False
            try:
                out = journals.list_diarios(
                    q=(qs.get("q") or [""])[0],
                    tipo=(qs.get("tipo") or [""])[0] or None,
                    ativos=ativos,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "lancamentos": [],  # stub até RFC-8003
                "permissoes": {
                    "pode_escrever": role in JOURNALS_WRITE_ROLES,
                    "pode_excluir": role in JOURNALS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/diarios/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            row = journals.get_diario(key)
            if not row:
                return self._json({"status": "error", "message": "Diário não encontrado"}, 404)
            return self._json({"status": "ok", "diario": row})

        # ── Lançamentos contábeis (RFC-8003 MVP) ──
        if parsed.path == "/api/lancamentos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                limit = int((qs.get("limit") or ["200"])[0] or 200)
            except (TypeError, ValueError):
                limit = 200
            try:
                out = journal_entries.list_lancamentos(
                    q=(qs.get("q") or [""])[0],
                    diario=(qs.get("diario") or [""])[0] or None,
                    status=(qs.get("status") or [""])[0] or None,
                    limit=limit,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in JOURNALS_WRITE_ROLES,
                    "pode_excluir": role in JOURNALS_DELETE_ROLES,
                    "pode_postar": role in JOURNALS_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/lancamentos/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            row = journal_entries.get_lancamento(key)
            if not row:
                return self._json({"status": "error", "message": "Lançamento não encontrado"}, 404)
            return self._json({"status": "ok", "lancamento": row})

        # ── Razão / saldos (RFC-8005 MVP) ──
        if parsed.path == "/api/razao":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            conta = (qs.get("conta") or [""])[0]
            try:
                limit = int((qs.get("limit") or ["2000"])[0] or 2000)
            except (TypeError, ValueError):
                limit = 2000
            try:
                out = ledger.razao(
                    conta=conta,
                    data_de=(qs.get("data_de") or [""])[0] or None,
                    data_ate=(qs.get("data_ate") or [""])[0] or None,
                    diario=(qs.get("diario") or [""])[0] or None,
                    limit=limit,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out, "meta": ledger.meta()})

        if parsed.path == "/api/saldos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            so_mov = (qs.get("so_movimentadas") or ["1"])[0].strip().lower() not in (
                "0", "false", "no",
            )
            try:
                limit = int((qs.get("limit") or ["500"])[0] or 500)
            except (TypeError, ValueError):
                limit = 500
            try:
                out = ledger.saldos(
                    data_ate=(qs.get("data_ate") or [""])[0] or None,
                    q=(qs.get("q") or [""])[0] or None,
                    so_movimentadas=so_mov,
                    limit=limit,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out, "meta": ledger.meta()})

        # ── Posting Engine (RFC-8004 MVP) ──
        if parsed.path == "/api/posting/rules":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            ativos = None
            a_raw = (qs.get("ativos") or [""])[0].strip().lower()
            if a_raw in ("1", "true", "yes"):
                ativos = True
            elif a_raw in ("0", "false", "no"):
                ativos = False
            out = posting_engine.list_rules(
                q=(qs.get("q") or [""])[0],
                evento=(qs.get("evento") or [""])[0] or None,
                ativos=ativos,
            )
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "permissoes": {
                    "pode_escrever": role in JOURNALS_WRITE_ROLES,
                    "pode_excluir": role in JOURNALS_DELETE_ROLES,
                    "role": role,
                },
            })

        if parsed.path == "/api/posting/history":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                limit = int((qs.get("limit") or ["100"])[0] or 100)
            except (TypeError, ValueError):
                limit = 100
            return self._json({"status": "ok", **posting_engine.list_history(limit=limit)})

        if parsed.path.startswith("/api/posting/validate/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            entry = journal_entries.get_lancamento(key)
            if not entry:
                return self._json({"status": "error", "message": "Lançamento não encontrado"}, 404)
            result = posting_engine.validate_entry(entry)
            return self._json({"status": "ok", "lancamento": entry, **result})

        # ── Períodos contábeis (RFC-8006 MVP) ──
        if parsed.path == "/api/periodos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = accounting_periods.list_periodos(
                    exercicio=(qs.get("exercicio") or [""])[0] or None,
                    status=(qs.get("status") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **out,
                "meta": accounting_periods.meta(),
                "permissoes": {
                    "pode_escrever": role in JOURNALS_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path.startswith("/api/periodos/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "meta":
                return self._json({"status": "ok", **accounting_periods.meta()})
            row = accounting_periods.get_periodo(key)
            if not row:
                return self._json({"status": "error", "message": "Período não encontrado"}, 404)
            return self._json({"status": "ok", "periodo": row})

        # ── Relatórios contábeis (RFC-8007 MVP) ──
        if parsed.path.startswith("/api/relatorios/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            kind = parsed.path.rstrip("/").split("/")[-1]
            try:
                if kind == "balancete":
                    try:
                        limit = int((qs.get("limit") or ["500"])[0] or 500)
                    except (TypeError, ValueError):
                        limit = 500
                    out = accounting_reports.trial_balance(
                        data_ate=(qs.get("data_ate") or [""])[0] or None,
                        q=(qs.get("q") or [""])[0] or None,
                        limit=limit,
                    )
                elif kind == "balanco":
                    out = accounting_reports.balance_sheet(
                        data_ate=(qs.get("data_ate") or [""])[0] or None,
                    )
                elif kind == "dre":
                    out = accounting_reports.income_statement(
                        data_de=(qs.get("data_de") or [""])[0] or None,
                        data_ate=(qs.get("data_ate") or [""])[0] or None,
                    )
                elif kind == "diario":
                    try:
                        limit = int((qs.get("limit") or ["300"])[0] or 300)
                    except (TypeError, ValueError):
                        limit = 300
                    out = accounting_reports.journal_book(
                        diario=(qs.get("diario") or [""])[0] or None,
                        data_de=(qs.get("data_de") or [""])[0] or None,
                        data_ate=(qs.get("data_ate") or [""])[0] or None,
                        limit=limit,
                    )
                elif kind == "razao":
                    try:
                        limit = int((qs.get("limit") or ["2000"])[0] or 2000)
                    except (TypeError, ValueError):
                        limit = 2000
                    out = accounting_reports.general_ledger(
                        conta=(qs.get("conta") or [""])[0],
                        data_de=(qs.get("data_de") or [""])[0] or None,
                        data_ate=(qs.get("data_ate") or [""])[0] or None,
                        diario=(qs.get("diario") or [""])[0] or None,
                        limit=limit,
                    )
                else:
                    return self._json({
                        "status": "error",
                        "message": "Relatório inválido (balancete|balanco|dre|diario|razao)",
                    }, 404)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out})

        # ── Integração contábil (RFC-8008 MVP) ──
        if parsed.path == "/api/accounting/integration":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            role = self._user_role(token)
            return self._json({
                "status": "ok",
                **accounting_integration.status(),
                "permissoes": {
                    "pode_escrever": role in JOURNALS_WRITE_ROLES,
                    "role": role,
                },
            })

        if parsed.path == "/api/accounting/integration/log":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                limit = int((qs.get("limit") or ["100"])[0] or 100)
            except (TypeError, ValueError):
                limit = 100
            return self._json({"status": "ok", **accounting_integration.list_log(limit=limit)})

        # ── Analytics contábil (RFC-8009 MVP) ──
        if parsed.path == "/api/accounting/analytics":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                meses = int((qs.get("meses") or ["6"])[0] or 6)
            except (TypeError, ValueError):
                meses = 6
            try:
                top = int((qs.get("top") or ["10"])[0] or 10)
            except (TypeError, ValueError):
                top = 10
            try:
                out = accounting_analytics.dashboard(
                    data_de=(qs.get("data_de") or [""])[0] or None,
                    data_ate=(qs.get("data_ate") or [""])[0] or None,
                    meses=meses,
                    top=top,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out})

        if parsed.path == "/api/accounting/analytics/compare":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                out = accounting_analytics.compare_periods(
                    periodo_a=(qs.get("a") or qs.get("periodo_a") or [""])[0] or None,
                    periodo_b=(qs.get("b") or qs.get("periodo_b") or [""])[0] or None,
                )
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            return self._json({"status": "ok", **out})

        # ── Listas de preço ──
        if parsed.path == "/api/admin/price-lists":
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "lists": price_lists.list_all()})

        if parsed.path == "/api/admin/campaigns":
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "campaigns": campaigns.list_all()})

        if parsed.path.startswith("/api/admin/campaigns/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            cid = parsed.path.rstrip("/").split("/")[-1]
            camp = campaigns.get_campaign(cid)
            if not camp:
                return self._json({"status": "error", "message": "Campanha não encontrada"}, 404)
            return self._json({"status": "ok", "campaign": camp})

        if parsed.path.startswith("/api/admin/price-lists/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            lid = parsed.path.rstrip("/").split("/")[-1]
            pl = price_lists.get_list(lid)
            if not pl:
                return self._json({"status": "error", "message": "Lista não encontrada"}, 404)
            return self._json({"status": "ok", "list": pl})

        # ── COBOL: Produtos ──
        if parsed.path == "/api/admin/produtos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "produtos": cobol_bridge.produtos_listar()})

        if parsed.path == "/api/admin/produtos/sync":
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", **cobol_bridge.sync_json()})

        # ── COBOL: Fornecedores ──
        if parsed.path == "/api/admin/fornecedores":
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "fornecedores": cobol_bridge.fornecedores_listar()})

        # ── Certificados ──
        if parsed.path == "/api/admin/certificados":
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "certificados": cert_service.listar()})

        if parsed.path.startswith("/api/admin/certificados/") and parsed.path.count("/") == 4:
            token = self.headers.get("X-Auth-Token", "")
            if not self._is_admin(token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            cid = parsed.path.split("/")[-1]
            action = body.get("action", "") if self.command == "POST" else ""
            if parsed.path.endswith("/info"):
                cid = parsed.path.split("/")[-2]
                info = cert_service.info_detalhada(cid)
                if not info:
                    return self._json({"status": "error", "message": "Certificado não encontrado"}, 404)
                return self._json({"status": "ok", "certificado": info})
            # GET single cert
            cert = cert_service.obter(cid)
            if not cert:
                return self._json({"status": "error", "message": "Certificado não encontrado"}, 404)
            return self._json({"status": "ok", "certificado": cert})

        # ── Fiscal: NFC-e ──
        # ── Lookup NCM / CEST (RFC 0012 + 0013) ──
        if parsed.path == "/api/lookup/ncm":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            q = self._get_query_param(parsed.query, "q", "")
            limit = int(self._get_query_param(parsed.query, "limit", "20") or "20")
            return self._json({"status": "ok", "items": ncm_cest_service.search_ncm(q, limit)})

        if parsed.path.startswith("/api/lookup/ncm/") and parsed.path.endswith("/cest"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            codigo = parsed.path.split("/")[4]
            autofill = ncm_cest_service.resolve_cest_autofill(codigo)
            return self._json({"status": "ok", "ncm": ncm_cest_service.get_ncm(codigo), **autofill})

        if parsed.path.startswith("/api/lookup/ncm/"):
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            codigo = parsed.path.rstrip("/").split("/")[-1]
            item = ncm_cest_service.get_ncm(codigo)
            if not item:
                return self._json({"status": "error", "message": "NCM não encontrado"}, 404)
            return self._json({"status": "ok", "item": item})

        if parsed.path == "/api/lookup/cest":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            q = self._get_query_param(parsed.query, "q", "")
            ncm = self._get_query_param(parsed.query, "ncm", "") or None
            limit = int(self._get_query_param(parsed.query, "limit", "20") or "20")
            return self._json({"status": "ok", "items": ncm_cest_service.search_cest(q, limit, ncm=ncm)})

        if parsed.path == "/api/lookup/cfop":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            q = self._get_query_param(parsed.query, "q", "")
            tipo = self._get_query_param(parsed.query, "tipo", "") or None
            limit = int(self._get_query_param(parsed.query, "limit", "20") or "20")
            return self._json({"status": "ok", "items": fiscal_tables_service.search_cfop(q, tipo=tipo, limit=limit)})

        if parsed.path == "/api/lookup/cst":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            q = self._get_query_param(parsed.query, "q", "")
            tipo = self._get_query_param(parsed.query, "tipo", "") or None
            regime = self._get_query_param(parsed.query, "regime", "") or None
            limit = int(self._get_query_param(parsed.query, "limit", "20") or "20")
            return self._json({"status": "ok", "items": fiscal_tables_service.search_cst(q, tipo=tipo, regime=regime, limit=limit)})

        if parsed.path == "/api/lookup/ncm-cest/validate":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            ncm = self._get_query_param(parsed.query, "ncm", "")
            cest = self._get_query_param(parsed.query, "cest", "")
            result = ncm_cest_service.validate_ncm_cest(ncm, cest)
            return self._json({"status": "ok" if result.get("ok") else "error", **result})

        # ── Vendas B2B (CNPJ → CNPJ) ──
        if parsed.path == "/api/vendas/b2b":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            pedidos = _load_pedidos_b2b()
            return self._json({
                "status": "ok",
                "pedidos": pedidos,
                "total": len(pedidos),
                "source": "cobol",
            })

        # ── Vendas B2B: faturas de venda (CNPJ → CNPJ) ──
        if parsed.path == "/api/vendas/b2b/faturas":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            try:
                payload = faturas_store.sync_json()
            except Exception:
                payload = {"faturas": faturas_store.listar(), "total": 0}
            return self._json({"status": "ok", **payload})

        # ── Admin: tabelas fiscais (CFOP / CST) ──
        if parsed.path.startswith("/api/admin/fiscal/tabelas/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            parts = parsed.path.rstrip("/").split("/")
            tabela = parts[5] if len(parts) > 5 else ""
            if tabela not in ("cfop", "cst"):
                return self._json({"status": "error", "message": "Tabela inválida"}, 400)
            if method == "GET":
                q = self._get_query_param(parsed.query, "q", "")
                if tabela == "cfop":
                    items = fiscal_tables_service.search_cfop(q)
                else:
                    items = fiscal_tables_service.search_cst(q)
                return self._json({"status": "ok", "items": items})
            if method == "POST":
                acao = (body or {}).get("acao")
                codigo = str((body or {}).get("codigo") or "").strip()
                if not codigo:
                    return self._json({"status": "error", "message": "código obrigatório"}, 400)
                if acao == "delete":
                    if tabela == "cfop":
                        fiscal_tables_service.delete_cfop(codigo)
                    else:
                        fiscal_tables_service.delete_cst(codigo)
                    return self._json({"status": "ok", "codigo": codigo})
                dados = (body or {}).get("dados") or {}
                if tabela == "cfop":
                    item = fiscal_tables_service.save_cfop(codigo, dados)
                else:
                    item = fiscal_tables_service.save_cst(codigo, dados)
                return self._json({"status": "ok", "item": item})
            return self._json({"status": "error", "message": "Método inválido"}, 400)

        # ── Fiscal: Apuração de Impostos ──
        if parsed.path == "/api/fiscal/apuracao":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            dt_ini = (qs.get("dt_ini") or [""])[0]
            dt_fim = (qs.get("dt_fim") or [""])[0]
            hist = (qs.get("historico") or [""])[0]
            if hist:
                return self._json({"status": "ok", "historico": tax_apuracao_store.historico()})
            result = tax_apuracao_store.apurar(dt_ini=dt_ini or None, dt_fim=dt_fim or None, usuario=user.get("nome") or user.get("usuario") or "")
            return self._json({"status": "ok", "apuracao": result})

        # ── Fiscal: Livros / SPED ──
        if parsed.path == "/api/fiscal/livros":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            dt_ini = (qs.get("dt_ini") or [""])[0]
            dt_fim = (qs.get("dt_fim") or [""])[0]
            tipo = (qs.get("tipo") or [""])[0]
            parceiro = (qs.get("parceiro") or [""])[0]
            livro = sped_livros_store.livro(dt_ini=dt_ini or None, dt_fim=dt_fim or None, tipo=tipo or None, parceiro=parceiro or None)
            return self._json({"status": "ok", **livro})

        if parsed.path == "/api/fiscal/sped":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            competencia = (qs.get("competencia") or [""])[0]
            texto = sped_fiscal_store.gerar(competencia=competencia or None)
            return self._json({"status": "ok", "sped": texto, "linhas": len(texto.splitlines())})

        # ── Fiscal: Reforma Tributária (IBS/CBS) ──
        if parsed.path == "/api/fiscal/reforma-tributaria/history":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            data = fiscal_reforma_store._load_history()
            return self._json({"status": "ok", "historico": data.get("calculos", [])[:50]})

        if parsed.path == "/api/fiscal/reforma-tributaria":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            if method == "GET":
                return self._json({"status": "ok", "aliquotas": fiscal_reforma_store.listar_aliquotas()})
            if method == "POST":
                acao = (body or {}).get("acao")
                if acao == "config":
                    padrao = (body or {}).get("padrao", {})
                    por_ncm = (body or {}).get("por_ncm", {})
                    fiscal_reforma_store.salvar_aliquotas(padrao, por_ncm)
                    return self._json({"status": "ok", "aliquotas": fiscal_reforma_store.listar_aliquotas()})
                if acao == "calcular":
                    valor = (body or {}).get("valor")
                    ncm = (body or {}).get("ncm")
                    aliq = (body or {}).get("aliquotas")
                    contexto = (body or {}).get("contexto", "")
                    if valor is None:
                        return self._json({"status": "error", "message": "valor obrigatório"}, 400)
                    try:
                        result = fiscal_reforma_store.calcular(
                            valor, ncm=ncm, aliquotas=aliq, usuario=user.get("nome") or user.get("usuario") or "", contexto=contexto
                        )
                        return self._json({"status": "ok", "calculo": result})
                    except Exception as e:
                        return self._json({"status": "error", "message": str(e)}, 500)
                return self._json({"status": "error", "message": "acao inválida"}, 400)

        # ── Quality Checks (receiving) ──
        if parsed.path == "/api/quality-checks/config":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            if method == "GET":
                return self._json({"status": "ok", "config": quality_checks_store.listar_checks()})
            if method == "POST":
                checks = (body or {}).get("checks")
                if not isinstance(checks, list):
                    return self._json({"status": "error", "message": "checks deve ser lista"}, 400)
                quality_checks_store.salvar_config(checks)
                return self._json({"status": "ok", "config": quality_checks_store.listar_checks()})

        if parsed.path.startswith("/api/quality-checks/result/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            rid = parsed.path.rstrip("/").split("/")[-1]
            if method == "GET":
                res = quality_checks_store.get_resultado(rid)
                return self._json({"status": "ok", "result": res})
            if method == "POST":
                res = quality_checks_store.avaliar(rid, body.get("respostas") or [], usuario=user.get("nome") or user.get("usuario") or "")
                return self._json({"status": "ok", "result": res})

        # ── Currency / Multi Currency ──
        if parsed.path == "/api/currency":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uname = user.get("usuario") or user.get("nome") or ""
            if method == "GET":
                return self._json({"status": "ok", "moeda_base": currency_store.BASE_CURRENCY, "rates": currency_store.listar_moedas()})
            if method == "POST":
                moeda = (body or {}).get("moeda")
                taxa = (body or {}).get("taxa")
                if not moeda or taxa is None:
                    return self._json({"status": "error", "message": "moeda e taxa obrigatórios"}, 400)
                try:
                    rates = currency_store.set_rate(moeda, taxa, usuario=uname)
                    return self._json({"status": "ok", "rates": rates})
                except Exception as e:
                    return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/currency/convert":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            try:
                valor = float((qs.get("valor") or ["0"])[0])
                de = (qs.get("de") or ["BRL"])[0]
                para = (qs.get("para") or ["BRL"])[0]
                converted = currency_store.converter(valor, de, para)
                return self._json({"status": "ok", "valor": valor, "de": de, "para": para, "convertido": round(converted, 2)})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Vendor Pricelist ──
        if parsed.path == "/api/vendor-pricelist":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uname = user.get("usuario") or user.get("nome") or ""
            if method == "GET":
                qs = urllib.parse.parse_qs(parsed.query or "")
                rows = vendor_pricelist_store.listar(
                    fornecedor_id=(qs.get("fornecedor_id") or [""])[0] or None,
                    produto_id=(qs.get("produto_id") or [""])[0] or None,
                    ativo=(qs.get("ativo") or [""])[0] == "1",
                )
                return self._json({"status": "ok", "pricelists": rows, "total": len(rows)})
            if method == "POST":
                action = str((body or {}).get("action") or "save").lower()
                try:
                    if action == "save":
                        row = vendor_pricelist_store.save(body or {}, usuario=uname)
                        return self._json({"status": "ok", "pricelist": row, "message": "Salvo"}, 201)
                    if action == "delete":
                        plid = (body or {}).get("id")
                        if not plid:
                            return self._json({"status": "error", "message": "id obrigatório"}, 400)
                        vendor_pricelist_store.delete(plid)
                        return self._json({"status": "ok", "message": "Excluído"})
                    if action == "melhor_preco":
                        prod = (body or {}).get("produto_id")
                        forn = (body or {}).get("fornecedor_id")
                        qtd = (body or {}).get("qtd")
                        row = vendor_pricelist_store.melhor_preco(prod, fornecedor_id=forn, qtd=qtd)
                        return self._json({"status": "ok", "pricelist": row})
                    return self._json({"status": "error", "message": f"ação desconhecida: {action}"}, 400)
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
                except Exception as e:
                    return self._json({"status": "error", "message": str(e)}, 500)

        # ── Settings / Configurações ──
        if parsed.path == "/api/settings":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uname = user.get("usuario") or user.get("nome") or ""
            if method == "GET":
                return self._json({"status": "ok", "settings": settings_store.listar(), "modulos": settings_store.modulos_disponiveis()})
            if method == "POST":
                modulo = (body or {}).get("modulo")
                valores = (body or {}).get("valores")
                chave = (body or {}).get("chave")
                valor = (body or {}).get("valor")
                if not modulo:
                    return self._json({"status": "error", "message": "modulo obrigatório"}, 400)
                try:
                    if isinstance(valores, dict):
                        cfg = settings_store.set_modulo(modulo, valores, usuario=uname)
                    elif chave is not None:
                        cfg = settings_store.set_key(modulo, chave, valor, usuario=uname)
                    else:
                        return self._json({"status": "error", "message": "valores ou chave obrigatório"}, 400)
                    return self._json({"status": "ok", "modulo": modulo, "config": cfg})
                except Exception as e:
                    return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path.startswith("/api/settings/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            parts = parsed.path.rstrip("/").split("/")
            if len(parts) >= 4:
                modulo = parts[3]
                if method == "GET":
                    return self._json({"status": "ok", "modulo": modulo, "config": settings_store.get(modulo)})
                if method == "DELETE":
                    cfg = settings_store.reset_modulo(modulo)
                    return self._json({"status": "ok", "modulo": modulo, "config": cfg})
            return self._json({"status": "error", "message": "Rota inválida"}, 400)

        # ── Devolução de Compra ──
        if parsed.path == "/api/devolucoes-compra":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uname = user.get("usuario") or user.get("nome") or ""
            if method == "GET":
                qs = urllib.parse.parse_qs(parsed.query or "")
                rows = devolucao_compra_store.listar(
                    status=(qs.get("status") or [""])[0] or None,
                    pedido_id=(qs.get("pedido_id") or [""])[0] or None,
                    recebimento_id=(qs.get("recebimento_id") or [""])[0] or None,
                )
                return self._json({"status": "ok", "devolucoes": rows, "total": len(rows)})
            if method == "POST":
                action = str((body or {}).get("action") or "create").lower()
                try:
                    if action == "create":
                        d = dict(body or {})
                        d.pop("action", None)
                        row = devolucao_compra_store.criar(d, usuario=uname)
                        return self._json({"status": "ok", "devolucao": row, "message": "Devolução criada"}, 201)
                    did = (body or {}).get("id")
                    if did is None:
                        return self._json({"status": "error", "message": "id obrigatório"}, 400)
                    if action == "concluir":
                        row = devolucao_compra_store.concluir(did, usuario=uname)
                        return self._json({"status": "ok", "devolucao": row, "message": "Devolução concluída"})
                    if action == "cancelar":
                        row = devolucao_compra_store.cancelar(did, usuario=uname)
                        return self._json({"status": "ok", "devolucao": row, "message": "Devolução cancelada"})
                    return self._json({"status": "error", "message": f"ação desconhecida: {action}"}, 400)
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
                except Exception as e:
                    return self._json({"status": "error", "message": str(e)}, 500)

        # ── Acordos de Compra (Purchase Agreements / Call for Tender) ──
        if parsed.path == "/api/acordos-compra":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            rows = acordos_compra_store.listar()
            st = (qs.get("status") or [""])[0]
            q = (qs.get("q") or [""])[0].strip().lower()
            if st:
                rows = [r for r in rows if r.get("status") == st]
            if q:
                rows = [r for r in rows if q in str(r.get("numero") or "").lower()
                        or q in str(r.get("descricao") or "").lower()]
            return self._json({"status": "ok", "acordos": rows, "total": len(rows)})

        if parsed.path.startswith("/api/acordos-compra/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            parts = parsed.path.rstrip("/").split("/")
            if len(parts) >= 4 and parts[3].isdigit():
                if len(parts) >= 5 and parts[4] == "mapa":
                    try:
                        return self._json({"status": "ok", "mapa": acordos_compra_store.mapa_cotacao(parts[3])})
                    except ValueError as e:
                        return self._json({"status": "error", "message": str(e)}, 404)
                row = acordos_compra_store.get(parts[3])
                if not row:
                    return self._json({"status": "error", "message": "Acordo não encontrado"}, 404)
                return self._json({"status": "ok", "acordo": row})
            return self._json({"status": "error", "message": "Rota inválida"}, 400)

        # ── Compras (three-way match) ──
        if parsed.path.startswith("/api/compras/three-way-match/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            parts = parsed.path.rstrip("/").split("/")
            if len(parts) >= 5 and parts[4].isdigit():
                try:
                    match = compras_store.three_way_match(parts[4])
                    return self._json({"status": "ok", "match": match})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 404)
            return self._json({"status": "error", "message": "Rota inválida"}, 400)

        # ── Compras (relatório) ──
        if parsed.path == "/api/compras/relatorio":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            params = {
                "de": (qs.get("de") or [""])[0] or None,
                "ate": (qs.get("ate") or [""])[0] or None,
                "fornecedor": (qs.get("fornecedor") or [""])[0] or None,
                "status": (qs.get("status") or [""])[0] or None,
                "produto": (qs.get("produto") or [""])[0] or None,
            }
            params = {k: v for k, v in params.items() if v}
            return self._json({"status": "ok", "relatorio": compras_store.relatorio(**params)})

        # ── Compras (follow-up de entregas) ──
        if parsed.path == "/api/compras/followup":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            atraso = (qs.get("atraso_minimo") or ["0"])[0]
            try:
                atraso = int(atraso)
            except ValueError:
                atraso = 0
            rows = compras_store.followup_entregas(atraso_minimo=atraso)
            score = compras_store.scorecard_fornecedor()
            return self._json({"status": "ok", "followup": rows, "scorecard": score, "total": len(rows)})

        # ── Compras (histórico de preços) ──
        if parsed.path == "/api/compras/precos":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            prod = (qs.get("produto") or [""])[0]
            pid = (qs.get("prod_id") or [""])[0]
            fid = (qs.get("fornecedor_id") or [""])[0]
            if prod or pid:
                resumo = compras_store.resumo_preco(prod, fornecedor_id=fid or None, prod_id=pid or None)
                return self._json({"status": "ok", "resumo": resumo})
            hist = compras_store.historico_precos(
                fornecedor_id=fid or None,
                produto=prod or None,
                prod_id=pid or None,
            )
            return self._json({"status": "ok", "historico": hist, "total": len(hist)})

        # ── Compras (pedidos de compra) ──
        if parsed.path == "/api/compras":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            rows = compras_store.listar()
            st = (qs.get("status") or [""])[0]
            q = (qs.get("q") or [""])[0].strip().lower()
            if st:
                rows = [r for r in rows if r.get("status") == st]
            if q:
                rows = [r for r in rows if q in str(r.get("numero") or "").lower()
                        or q in str(r.get("razao_social") or "").lower()]
            return self._json({"status": "ok", "pedidos": rows, "total": len(rows)})

        if parsed.path.startswith("/api/compras/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            parts = parsed.path.rstrip("/").split("/")
            if len(parts) >= 4 and parts[3].isdigit():
                row = compras_store.get(parts[3])
                if not row:
                    return self._json({"status": "error", "message": "Pedido não encontrado"}, 404)
                return self._json({"status": "ok", "pedido": row})
            return self._json({"status": "error", "message": "Rota inválida"}, 400)

        # ── Vendas B2B: contratos ──
        if parsed.path == "/api/vendas/b2b/contratos":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            rows = contratos_b2b_store.listar(
                status=(qs.get("status") or [""])[0] or None,
                cliente_id=(qs.get("cliente_id") or qs.get("partner_id") or [""])[0] or None,
                q=(qs.get("q") or [""])[0] or None,
            )
            return self._json({
                "status": "ok",
                "contratos": rows,
                "total": len(rows),
                "source": "contratos_b2b.json",
            })

        if parsed.path.startswith("/api/vendas/b2b/contratos/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            parts = parsed.path.rstrip("/").split("/")
            # /api/vendas/b2b/contratos/{id}
            if len(parts) >= 5 and parts[4].isdigit():
                row = contratos_b2b_store.get(parts[4])
                if not row:
                    return self._json({"status": "error", "message": "Contrato não encontrado"}, 404)
                return self._json({"status": "ok", "contrato": row})
            return self._json({"status": "error", "message": "Rota inválida"}, 400)

        # ── Vendas B2B: clientes = partners CUSTOMER (RFC-0020) ──
        if parsed.path == "/api/vendas/b2b/clientes":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            out = partner_lookup.list_customers_b2b("CUSTOMER")
            return self._json({
                "status": "ok",
                "clientes": out,
                "source": "partners",
                "total": len(out),
            })

        # ── Vendas B2B: contas a receber ──
        if parsed.path == "/api/vendas/b2b/receber":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            out = sales_finance.list_titulos(
                partner_id=(qs.get("partner_id") or [""])[0] or None,
                status=(qs.get("status") or [""])[0] or None,
                q=(qs.get("q") or [""])[0] or None,
            )
            return self._json({"status": "ok", **out})

        if parsed.path == "/api/vendas/b2b/credito":
            token = self.headers.get("X-Auth-Token", "")
            if not self._find_user(token, load_users()):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            pid = (qs.get("partner_id") or [""])[0]
            valor = _safe_float((qs.get("valor") or ["0"])[0], 0)
            return self._json({
                "status": "ok",
                "credit": sales_finance.check_credit(pid, valor),
                "config": sales_finance.partner_credit(pid),
            })
        # ── Vendas B2B: catálogo (listas + produtos filtrados, preço no servidor) ──
        if parsed.path == "/api/vendas/b2b/catalog":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            qs = urllib.parse.parse_qs(parsed.query or "")
            estab = ((qs.get("estabelecimento_id") or qs.get("estab") or [""])[0] or "").strip()
            list_id = ((qs.get("lista_precos_id") or qs.get("list_id") or [""])[0] or "").strip()
            pl_meta = [{"id": r.get("id"), "name": r.get("name"), "code": r.get("code"),
                        "items": r.get("items") or {}}
                       for r in price_lists.list_all(active_only=True)]
            produtos = []
            try:
                raw = cobol_bridge.produtos_para_vendas(estab or None)
                priced = price_lists.apply_to_produtos(
                    raw, estabelecimento_id=estab or None, list_id=list_id or None
                )
                for p in priced:
                    produtos.append({
                        "id": p.get("id"),
                        "nome": p.get("nome") or p.get("name") or "",
                        "preco": _safe_float(p.get("preco"), 0),
                        "preco_base": _safe_float(p.get("preco_base"), _safe_float(p.get("preco"), 0)),
                        "price_list_id": p.get("price_list_id"),
                        "price_source": p.get("price_source") or "base",
                        "unidade": p.get("unidade") or "UN",
                        "ncm": p.get("ncm") or "",
                    })
            except Exception:
                produtos = []
            return self._json({
                "status": "ok",
                "price_lists": pl_meta,
                "produtos": produtos,
                "estabelecimento_id": estab or None,
                "lista_precos_id": list_id or None,
                "filtrado": True,
                "total": len(produtos),
            })

        # ── Vendas (para NFC-e) ──
        if parsed.path == "/api/vendas":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            cobol_bridge.sync_json()
            vendas = load_json(os.path.join(BASE_DIR, "dados", "vendas.json"))
            return self._json(vendas)

        if parsed.path == "/api/admin/fiscal/nfce/listar":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfce"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            nfce_data = load_json(os.path.join(BASE_DIR, "dados", "nfce.json"))
            return self._json({"status": "ok", "nfce": nfce_data.get("nfce", [])})

        if parsed.path == "/api/admin/fiscal/nfce/empresa":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfce"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            emp = load_empresa_fiscal()
            certs = cert_service.listar()
            return self._json({"status": "ok", "empresa": emp, "certificados": certs})

        # ── Fiscal: NF-e (modelo 55) ──
        if parsed.path == "/api/admin/fiscal/nfe/listar":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            nfe_data = load_json(os.path.join(BASE_DIR, "dados", "nfe.json"))
            return self._json({"status": "ok", "nfe": nfe_data.get("nfe", [])})

        if parsed.path == "/api/admin/fiscal/nfe/empresa":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            emp = load_empresa_fiscal()
            certs = cert_service.listar()
            return self._json({"status": "ok", "empresa": emp, "certificados": certs})

        # ── Fiscal: NFS-e ──
        if parsed.path == "/api/admin/fiscal/nfse/listar":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfse"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            nfse_data = load_json(os.path.join(BASE_DIR, "dados", "nfse.json"))
            return self._json({"status": "ok", "nfse": nfse_data.get("nfse", [])})

        if parsed.path == "/api/admin/fiscal/nfse/empresa":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfse"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            emp = load_empresa_fiscal()
            certs = cert_service.listar()
            return self._json({"status": "ok", "empresa": emp, "certificados": certs})

        if parsed.path == "/api/admin/fiscal/nfse/cidades":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfse"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "cidades": nfse_service.CIDADES_NFSE})

        # ── SPED ──
        if parsed.path == "/api/admin/fiscal/sped/fiscal":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "sped"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            empresa = load_empresa_fiscal()
            nfce = load_json(os.path.join(BASE_DIR, "dados", "nfce.json")).get("nfce", [])
            nfe = load_json(os.path.join(BASE_DIR, "dados", "nfe.json")).get("nfe", [])
            qs = urllib.parse.parse_qs(parsed.query or "")
            competencia = (qs.get("competencia") or [""])[0]
            conteudo = sped_fiscal.gerar_sped_fiscal(empresa, competencia=competencia, nfce_list=nfce, nfe_list=nfe)
            return self._json({"status": "ok", "conteudo": conteudo, "filename": f"SPED_FISCAL_{empresa.get('cnpj','')}.txt"})

        if parsed.path == "/api/admin/fiscal/sped/pis":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "sped"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            empresa = load_empresa_fiscal()
            nfce = load_json(os.path.join(BASE_DIR, "dados", "nfce.json")).get("nfce", [])
            nfe = load_json(os.path.join(BASE_DIR, "dados", "nfe.json")).get("nfe", [])
            qs = urllib.parse.parse_qs(parsed.query or "")
            competencia = (qs.get("competencia") or [""])[0]
            conteudo = sped_pis_cofins.gerar_sped_pis(empresa, competencia=competencia, nfce_list=nfce, nfe_list=nfe)
            return self._json({"status": "ok", "conteudo": conteudo, "filename": f"SPED_PIS_{empresa.get('cnpj','')}.txt"})

        # ── CT-e (COBOL) ──
        if parsed.path == "/api/admin/fiscal/cte":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "cte": cobol_bridge.cte_listar()})

        # ── MDF-e (COBOL) ──
        if parsed.path == "/api/admin/fiscal/mdfe":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            return self._json({"status": "ok", "mdfe": cobol_bridge.mdfe_listar()})

        # ── Tributos ──
        if parsed.path == "/api/admin/fiscal/calcular-tributos":
            token = self.headers.get("X-Auth-Token", "")
            if not self._has_permission(token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            uf_origem = self._get_query_param(parsed.query, "uf_origem", "RS")
            uf_destino = self._get_query_param(parsed.query, "uf_destino", "RS")
            regime = self._get_query_param(parsed.query, "regime", "SN")
            regime_pis = self._get_query_param(parsed.query, "regime_pis", "cumulativo")
            return self._json({"status": "ok", "tabelas": {
                "icms_interno": tributos.TABELA_ICMS_INTERNO,
                "icms_interestadual": tributos.TABELA_ICMS_INTERESTADUAL,
                "pis": tributos.TABELA_PIS,
                "cofins": tributos.TABELA_COFINS,
                "ipi": tributos.TABELA_IPI,
                "iss": tributos.TABELA_ISS,
            }})

        # CRUD GET routes (JSON)
        for prefix, data_file, list_key in [
            ("/api/admin/categorias", CATEGORIAS_FILE, "categorias"),
            ("/api/admin/marcas", MARCAS_FILE, "marcas"),
            ("/api/admin/fabricantes", FABRICANTES_FILE, "fabricantes"),
            ("/api/admin/contatos", CONTATOS_FILE, "contatos"),
            ("/api/admin/partners", PARTNERS_FILE, "partners"),
        ]:
            if parsed.path == prefix:
                token = self.headers.get("X-Auth-Token", "")
                if not self._is_admin(token):
                    return self._json({"status": "error", "message": "Acesso negado"}, 403)
                data = load_json(data_file)
                lista = []
                role_filter = self._get_query_param(parsed.query, "role", "").upper().strip()
                for eid, e in data.items():
                    item = dict(e)
                    item["id"] = eid
                    if role_filter:
                        roles = [str(r).upper() for r in (item.get("roles") or [])]
                        # legado contatos: tipo=cliente
                        if list_key == "contatos" and not roles:
                            t = (item.get("tipo") or "").lower()
                            tipo_map = {
                                "cliente": "CUSTOMER",
                                "fornecedor": "SUPPLIER",
                                "transportador": "CARRIER",
                            }
                            if tipo_map.get(t):
                                roles = [tipo_map[t]]
                        if role_filter not in roles:
                            continue
                    lista.append(item)
                return self._json({"status": "ok", list_key: lista})

        # ── RH: Funcionários / Dependentes / Filiais / Departamentos / Cargos (CRUD COBOL) ──
        if parsed.path == "/api/funcionarios":
            funcs = cobol_bridge.funcionarios_listar()
            filiais = cobol_bridge.filiais_listar()
            filial_map = {str(f.get("id")): f for f in filiais}
            func_map = {str(f.get("id")): f for f in funcs}
            dep_map = {str(d.get("id")): d for d in cobol_bridge.departamentos_listar()}
            car_map = {str(c.get("id")): c for c in cobol_bridge.cargos_listar()}
            for f in funcs:
                filial = filial_map.get(str(f.get("filial_id") or 0))
                f["filial_nome"] = (filial or {}).get("nome", "Matriz")
                f["empresa_id"] = (filial or {}).get("empresa_id", 0)
                f["empresa_nome"] = self._empresa_nome(f.get("empresa_id") or (filial or {}).get("empresa_id", 0))
                sup = func_map.get(str(f.get("supervisor_id") or 0))
                f["supervisor_nome"] = (sup or {}).get("nome", "") if f.get("supervisor_id") else ""
                dep = dep_map.get(str(f.get("departamento_id") or 0))
                f["departamento_nome"] = (dep or {}).get("descricao", "")
                car = car_map.get(str(f.get("cargo_id") or 0))
                f["cargo_nome"] = (car or {}).get("descricao", "")
            return self._json({"status": "ok", "funcionarios": funcs})

        if parsed.path == "/api/departamentos":
            qs = urllib.parse.parse_qs(parsed.query or "")
            ativos_only = (qs.get("ativos") or [""])[0] == "1"
            return self._json({"status": "ok", "departamentos": cobol_bridge.departamentos_listar(ativos_only)})

        if parsed.path == "/api/cargos":
            qs = urllib.parse.parse_qs(parsed.query or "")
            ativos_only = (qs.get("ativos") or [""])[0] == "1"
            return self._json({"status": "ok", "cargos": cobol_bridge.cargos_listar(ativos_only)})

        if parsed.path == "/api/eventos":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            qs = urllib.parse.parse_qs(parsed.query or "")
            ativos_only = (qs.get("ativos") or [""])[0] == "1"
            try:
                if not ativos_only:
                    # seed lazy: garante o catálogo inicial (RFC-004 §3)
                    cobol_bridge.eventos_seed_catalogo()
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)
            return self._json({"status": "ok", "eventos": cobol_bridge.eventos_listar(ativos_only)})

        if parsed.path == "/api/filiais":
            return self._json({"status": "ok", "filiais": cobol_bridge.filiais_listar()})

        if parsed.path == "/api/dependentes":
            qs = urllib.parse.parse_qs(parsed.query or "")
            fid = (qs.get("funcionario_id") or [""])[0]
            return self._json({"status": "ok", "dependentes": cobol_bridge.dependentes_listar(fid)})

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode() if length else ""
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {}

        # RFC-0000 §21 — guarda de manutenção / arquivamento (POST + PUT)
        guard_msg = platform_setup.lifecycle_guard(parsed.path)
        if guard_msg:
            return self._json({"status": "error", "message": guard_msg}, 503)

        if parsed.path == "/api/vendas/b2b":
            token = self.headers.get("X-Auth-Token", "")
            return self._vendas_b2b_post(body, token)

        if parsed.path == "/api/acordos-compra":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uname = user.get("usuario") or user.get("nome") or ""
            action = str((body or {}).get("action") or "create").lower()
            try:
                if action == "create":
                    a = dict(body or {})
                    a.pop("id", None)
                    a.pop("action", None)
                    a.setdefault("status", "rascunho")
                    a.setdefault("data", datetime.now().strftime("%Y-%m-%d"))
                    a.setdefault("tipo", "tender")
                    a.setdefault("itens", [])
                    row = acordos_compra_store.save(a, is_new=True)
                    return self._json({"status": "ok", "acordo": row, "message": "Acordo criado"}, 201)
                aid = (body or {}).get("id")
                if aid is None:
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                if action == "update":
                    target = acordos_compra_store.get(aid)
                    if not target:
                        return self._json({"status": "error", "message": "Não encontrado"}, 404)
                    if target.get("status") in ("fechado", "cancelado"):
                        return self._json({"status": "error", "message": "Status bloqueia edição"}, 400)
                    for k, v in (body or {}).items():
                        if k in ("action", "id"):
                            continue
                        if v is not None:
                            target[k] = v
                    row = acordos_compra_store.save(target)
                    return self._json({"status": "ok", "acordo": row, "message": "Atualizado"})
                if action == "delete":
                    acordos_compra_store.delete(aid)
                    return self._json({"status": "ok", "message": "Excluído"})
                if action == "status":
                    st = (body or {}).get("status")
                    row = acordos_compra_store.set_status(aid, st, usuario=uname)
                    return self._json({"status": "ok", "acordo": row, "doc_status": st})
                if action == "add_cotacao":
                    row = acordos_compra_store.add_cotacao(aid, body or {}, usuario=uname)
                    return self._json({"status": "ok", "cotacao": row, "message": "Cotação adicionada"}, 201)
                if action == "delete_cotacao":
                    cid = (body or {}).get("cotacao_id")
                    if not cid:
                        return self._json({"status": "error", "message": "cotacao_id obrigatório"}, 400)
                    acordos_compra_store.delete_cotacao(cid)
                    return self._json({"status": "ok", "message": "Cotação removida"})
                if action == "converter":
                    out = acordos_compra_store.converter_vencedor(aid, usuario=uname)
                    return self._json({"status": "ok", "acordo": out["acordo"], "pedido": out["pedido"], "message": "Pedido gerado"}, 201)
                if action == "blanket_setup":
                    s = acordos_compra_store.blanket_setup(
                        aid,
                        valor_total=(body or {}).get("valor_total"),
                        qtd_total=(body or {}).get("qtd_total"),
                        usuario=uname,
                    )
                    return self._json({"status": "ok", "saldo": s, "message": "Blanket configurado"})
                if action == "liberar_blanket":
                    out = acordos_compra_store.liberar_blanket(aid, body or {}, usuario=uname)
                    return self._json({"status": "ok", "acordo": out["acordo"], "pedido": out["pedido"], "saldo": out["saldo"], "message": "Liberação criada"}, 201)
                return self._json({"status": "error", "message": f"ação desconhecida: {action}"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/compras":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uname = user.get("usuario") or user.get("nome") or ""
            action = str((body or {}).get("action") or "create").lower()
            try:
                if action == "create":
                    p = dict(body or {})
                    p.pop("id", None)
                    p.pop("action", None)
                    p.setdefault("status", "rascunho")
                    p.setdefault("data", datetime.now().strftime("%Y-%m-%d"))
                    p.setdefault("itens", [])
                    p.setdefault("smart", {"recebimentos": 0})
                    row = compras_store.save(p, is_new=True)
                    return self._json({"status": "ok", "pedido": row, "message": "Criado"}, 201)
                pid = (body or {}).get("id")
                if pid is None:
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                if action == "update":
                    target = compras_store.get(pid)
                    if not target:
                        return self._json({"status": "error", "message": "Não encontrado"}, 404)
                    if target.get("status") in ("recebido", "cancelado"):
                        return self._json({"status": "error", "message": "Status bloqueia edição"}, 400)
                    for k, v in (body or {}).items():
                        if k in ("action", "id"):
                            continue
                        if v is not None:
                            target[k] = v
                    row = compras_store.save(target)
                    return self._json({"status": "ok", "pedido": row, "message": "Atualizado"})
                if action == "delete":
                    compras_store.delete(pid)
                    return self._json({"status": "ok", "message": "Excluído"})
                if action == "status":
                    st = (body or {}).get("status")
                    row = compras_store.set_status(pid, st, usuario=uname, user=user)
                    return self._json({"status": "ok", "pedido": row, "doc_status": st})
                if action == "aprovar":
                    row = compras_store.aprovar(pid, usuario=uname, user=user, motivo=(body or {}).get("motivo", ""))
                    return self._json({"status": "ok", "pedido": row, "doc_status": "aprovado"})
                if action == "rejeitar":
                    row = compras_store.rejeitar(pid, usuario=uname, motivo=(body or {}).get("motivo", ""))
                    return self._json({"status": "ok", "pedido": row, "doc_status": "cancelado"})
                return self._json({"status": "error", "message": f"ação desconhecida: {action}"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/vendas/b2b/contratos":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uname = user.get("usuario") or user.get("nome") or ""
            action = str((body or {}).get("action") or "create").lower()
            try:
                if action == "create":
                    row = contratos_b2b_store.create(body or {}, usuario=uname)
                    return self._json({"status": "ok", "contrato": row, "message": "Contrato criado"}, 201)
                if action == "from_pedido":
                    pid = (body or {}).get("pedido_id") or (body or {}).get("id")
                    pedido = pedidos_b2b_store.get(pid) if pid is not None else None
                    if not pedido:
                        return self._json({"status": "error", "message": "Pedido não encontrado"}, 404)
                    row = contratos_b2b_store.create_from_pedido(pedido, usuario=uname)
                    return self._json({"status": "ok", "contrato": row, "message": "Contrato gerado do pedido"}, 201)
                cid = (body or {}).get("id")
                if cid is None:
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                if action == "update":
                    row = contratos_b2b_store.update(cid, body or {}, usuario=uname)
                    return self._json({"status": "ok", "contrato": row, "message": "Atualizado"})
                status_map = {
                    "ativar": "ativo", "activate": "ativo",
                    "suspender": "suspenso", "suspend": "suspenso",
                    "encerrar": "encerrado", "complete": "encerrado", "completar": "encerrado",
                    "cancelar": "cancelado", "cancel": "cancelado",
                }
                if action in status_map:
                    row = contratos_b2b_store.set_status(cid, status_map[action], usuario=uname)
                    return self._json({"status": "ok", "contrato": row, "message": f"Status: {row.get('status')}"})
                if action == "status":
                    row = contratos_b2b_store.set_status(cid, (body or {}).get("status"), usuario=uname)
                    return self._json({"status": "ok", "contrato": row, "message": f"Status: {row.get('status')}"})
                if action in ("gerar_pedido", "create_order"):
                    out = contratos_b2b_store.gerar_pedido(cid, usuario=uname)
                    return self._json({
                        "status": "ok",
                        "contrato": out["contrato"],
                        "pedido": out["pedido"],
                        "message": f"Pedido {out['pedido'].get('numero')} gerado",
                    }, 201)
                return self._json({"status": "error", "message": f"ação desconhecida: {action}"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/vendas/b2b/receber":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            tid = (body or {}).get("id") or (body or {}).get("titulo_id")
            if not tid:
                return self._json({"status": "error", "message": "id do título é obrigatório"}, 400)
            try:
                row = sales_finance.baixar_titulo(
                    tid,
                    valor=(body or {}).get("valor"),
                    usuario=(user.get("usuario") or user.get("nome") or ""),
                )
                return self._json({"status": "ok", "titulo": row, "message": "Baixa registrada"})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/system/maintenance":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            action = str((body or {}).get("action") or "").lower()
            try:
                if action == "enter":
                    out = platform_setup.enter_maintenance(
                        usuario=user.get("usuario") or user.get("nome") or "")
                elif action == "exit":
                    out = platform_setup.exit_maintenance(
                        usuario=user.get("usuario") or user.get("nome") or "")
                else:
                    return self._json({"status": "error", "message": "informe action enter|exit"}, 400)
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/system/archive":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            action = str((body or {}).get("action") or "").lower()
            try:
                if action == "archive":
                    out = platform_setup.archive_instance(
                        usuario=user.get("usuario") or user.get("nome") or "")
                elif action == "unarchive":
                    out = platform_setup.unarchive_instance(
                        usuario=user.get("usuario") or user.get("nome") or "")
                else:
                    return self._json({"status": "error", "message": "informe action archive|unarchive"}, 400)
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/system/backup":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            action = str((body or {}).get("action") or "").lower()
            try:
                if action == "create":
                    out = platform_setup.create_backup(
                        usuario=user.get("usuario") or user.get("nome") or "")
                elif action == "restore":
                    out = platform_setup.restore_backup(
                        (body or {}).get("backup_id") or "",
                        usuario=user.get("usuario") or user.get("nome") or "")
                else:
                    return self._json({"status": "error", "message": "informe action create|restore (+ backup_id)"}, 400)
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/auth/setup":
            users = load_users()
            if any(u.get("role") == "admin" for u in users.values()):
                return self._json({"status": "error", "message": "Admin já configurado"}, 400)
            nome = body.get("nome", "").strip()
            usuario = body.get("usuario", "").strip()
            senha = body.get("senha", "")
            email = body.get("email", "").strip()
            instance_name = (body.get("instance_name") or body.get("business_name") or "").strip()
            instance_description = (body.get("instance_description") or body.get("description") or "").strip()
            localization = body.get("localization") if isinstance(body.get("localization"), dict) else {
                "country": (body.get("country") or "BR"),
                "language": (body.get("language") or "pt-BR"),
                "timezone": (body.get("timezone") or "America/Sao_Paulo"),
                "currency": (body.get("currency") or "BRL"),
            }
            if not nome or not usuario or not senha:
                return self._json({"status": "error", "message": "Preencha nome, usuário e senha"}, 400)
            uid = str(uuid.uuid4())[:8]
            token = make_token()
            users[uid] = {
                "usuario": usuario,
                "nome": nome,
                "senha": hash_password(senha),
                "email": email or "",
                "role": "admin",
                "empresas": {},
                "ativo": True,
                "token": token
            }
            if not instance_name:
                return self._json({"status": "error", "message": "Nome da Business Instance obrigatório"}, 400)
            save_users(users)
            # RFC-0000: instalação → init → login → Business Setup
            init_progress = []
            try:
                app_registry.init_base()
            except Exception:
                pass
            try:
                out = platform_setup.init_after_admin(
                    instance_name=instance_name or nome,
                    instance_description=instance_description,
                    localization=localization,
                    usuario=usuario,
                )
                init_progress = (out or {}).get("init_progress") or []
            except Exception:
                pass
            return self._json({
                "status": "ok",
                "id": uid,
                "nome": nome,
                "usuario": usuario,
                "role": "admin",
                "next": "login",
                "init_progress": init_progress,
                "message": "Instalação concluída. Faça login com o administrador criado.",
            })

        if parsed.path == "/api/platform/setup/step":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            try:
                out = platform_setup.save_step(
                    (body or {}).get("step") or (body or {}).get("step_id"),
                    payload=(body or {}).get("data") or body or {},
                    usuario=user.get("usuario") or user.get("nome") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/platform/setup/goto":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            try:
                out = platform_setup.set_step((body or {}).get("step") or (body or {}).get("step_id"))
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/platform/setup/go-live":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            try:
                out = platform_setup.go_live(
                    usuario=user.get("usuario") or user.get("nome") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/platform/setup/reopen":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            try:
                out = platform_setup.reopen_business_setup(
                    usuario=user.get("usuario") or user.get("nome") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/platform/setup/factory-reset":
            # Admin autenticado OU sistema ainda sem admin (já vazio)
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users) if token else None
            has_admin = any(u.get("role") == "admin" for u in users.values())
            if has_admin and (not user or user.get("role") != "admin"):
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            try:
                out = platform_setup.factory_reset(
                    confirm=(body or {}).get("confirm") or "",
                    usuario=(user or {}).get("usuario") or (user or {}).get("nome") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/apps/package":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            try:
                out = app_registry.apply_package(
                    (body or {}).get("package_id") or (body or {}).get("package"),
                    app_ids=(body or {}).get("apps") or (body or {}).get("app_ids"),
                    usuario=user.get("usuario") or user.get("nome") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/apps/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key in ("package",):
                return self._json({"status": "error", "message": "use POST /api/admin/apps/package"}, 400)
            try:
                installed = (body or {}).get("installed")
                if installed is None:
                    action = str((body or {}).get("action") or "").lower()
                    if action in ("install", "instalar"):
                        installed = True
                    elif action in ("uninstall", "desinstalar", "disable"):
                        installed = False
                    else:
                        return self._json({"status": "error", "message": "informe installed ou action"}, 400)
                out = app_registry.set_app(
                    key,
                    bool(installed),
                    usuario=user.get("usuario") or user.get("nome") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/apps/setup":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            state = app_registry.load_state()
            ss = app_registry.load_setup_state()
            lista = []
            for aid in app_registry.APP_CATALOG:
                if not app_registry.is_installed(aid, state):
                    continue
                desc = app_registry.setup_descriptor(aid)
                lista.append({
                    "app_id": aid,
                    "name": (app_registry.APP_CATALOG.get(aid) or {}).get("name", aid),
                    "label": (desc or {}).get("label", ""),
                    "url": (desc or {}).get("url", ""),
                    "required": bool((desc or {}).get("required")),
                    "done": app_registry.setup_done(aid, ss),
                })
            return self._json({"status": "ok", "apps": lista,
                               "pending": [x for x in lista if not x["done"]]})

        if parsed.path == "/api/apps/setup/done":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user or user.get("role") != "admin":
                return self._json({"status": "error", "message": "Apenas administrador"}, 403)
            try:
                out = app_registry.mark_setup_done(
                    (body or {}).get("app_id") or (body or {}).get("app"),
                    usuario=user.get("usuario") or user.get("nome") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Inventory MVP: transfer / adjust ──
        if parsed.path in ("/api/inventory/transfer", "/api/inventory/adjust"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uid = next((k for k, u in users.items() if u.get("token") == token), None)
            try:
                if parsed.path == "/api/inventory/transfer":
                    result = inventory_mvp.inventory_transfer(
                        body.get("origem") or body.get("from"),
                        body.get("destino") or body.get("to"),
                        body.get("items") or body.get("linhas") or [],
                        user_id=uid,
                        nota=body.get("nota"),
                    )
                    return self._json({"status": "ok", **result})
                # adjust
                result = inventory_mvp.inventory_adjust(
                    body.get("estabelecimento_id") or body.get("warehouse_id"),
                    body.get("produto_id") or body.get("id"),
                    body.get("qty") or body.get("quantidade"),
                    direcao=body.get("direcao") or body.get("sign") or "in",
                    nota=body.get("nota"),
                    user_id=uid,
                )
                return self._json({"status": "ok", **result})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/pos/caixa/movimentos":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uid = next((k for k, u in users.items() if u.get("token") == token), None)
            try:
                payload = dict(body or {})
                if not payload.get("terminal_id") or not payload.get("estabelecimento_id"):
                    term = _terminal_do_usuario(uid)
                    if term:
                        payload.setdefault("terminal_id", term.get("id") or "")
                        payload.setdefault("estabelecimento_id", term.get("estabelecimento_id") or "")
                payload.setdefault("user_nome", user.get("nome") or user.get("usuario") or "")
                # amarra à sessão aberta
                open_s = pos_caixa.get_sessao_aberta(terminal_id=payload.get("terminal_id"))
                if open_s:
                    payload.setdefault("sessao_id", open_s.get("id"))
                entry = pos_caixa.add_movimento(payload, user_id=uid)
                return self._json({"status": "ok", "movimento": entry}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/pos/caixa/sessao":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uid = next((k for k, u in users.items() if u.get("token") == token), None)
            role = (user.get("role") or "").lower()
            if role not in ("caixa", "gerente", "admin"):
                return self._json({"status": "error", "message": "sem permissão para abrir caixa"}, 403)
            try:
                payload = dict(body or {})
                term = _terminal_do_usuario(uid)
                if term:
                    payload.setdefault("terminal_id", term.get("id") or "")
                    payload.setdefault("estabelecimento_id", term.get("estabelecimento_id") or "")
                payload.setdefault("user_nome", user.get("nome") or user.get("usuario") or "")
                sessao = pos_caixa.abrir_sessao(payload, user_id=uid)
                return self._json({"status": "ok", "sessao": sessao, "resumo": pos_caixa.resumo_sessao(sessao)}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/pos/caixa/sessao/fechar":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uid = next((k for k, u in users.items() if u.get("token") == token), None)
            role = (user.get("role") or "").lower()
            if role not in ("caixa", "gerente", "admin"):
                return self._json({"status": "error", "message": "sem permissão para fechar caixa"}, 403)
            try:
                sid = body.get("sessao_id") or body.get("id")
                if not sid:
                    term = _terminal_do_usuario(uid)
                    open_s = pos_caixa.get_sessao_aberta(
                        terminal_id=(term or {}).get("id") if term else None
                    )
                    if not open_s:
                        return self._json({"status": "error", "message": "nenhuma sessão aberta"}, 400)
                    sid = open_s.get("id")
                out = pos_caixa.fechar_sessao(sid, body, user_id=uid)
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Receiving MVP ──
        if parsed.path == "/api/receiving" or parsed.path.startswith("/api/receiving/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            uid = next((k for k, u in users.items() if u.get("token") == token), None)

            if parsed.path == "/api/receiving/from-xml":
                try:
                    xml_text = body.get("xml") or body.get("xml_text") or ""
                    if body.get("xml_base64") and not xml_text:
                        import base64
                        xml_text = base64.b64decode(body["xml_base64"]).decode("utf-8", errors="replace")
                    if not xml_text and body.get("sample") == "demo":
                        sample = os.path.join(BASE_DIR, "data", "samples", "nfe-entrada-demo.xml")
                        with open(sample, "r", encoding="utf-8") as f:
                            xml_text = f.read()
                    if not xml_text:
                        return self._json({"status": "error", "message": "xml ou xml_base64 obrigatório"}, 400)
                    # RFC-4003: passa pelo monitor (ingest + process)
                    ing = nfe_monitor.ingest_xml(
                        xml_text,
                        filename=body.get("filename") or "upload.xml",
                        source="from-xml",
                        user_id=uid,
                    )
                    doc = ing["document"]
                    if ing.get("duplicate"):
                        if doc.get("status") == "done" and doc.get("receiving_id"):
                            rec = receiving_mvp.get_receiving(doc["receiving_id"])
                            return self._json({
                                "status": "error",
                                "message": ing.get("message") or "XML duplicado no monitor",
                                "document": doc,
                                "receiving": rec,
                            }, 400)
                        if doc.get("status") == "new":
                            pass  # process below
                        else:
                            return self._json({
                                "status": "error",
                                "message": ing.get("message") or "XML duplicado",
                                "document": doc,
                            }, 400)
                    if doc.get("status") == "error":
                        return self._json({
                            "status": "error",
                            "message": doc.get("error") or "XML rejeitado pelo monitor",
                            "document": doc,
                        }, 400)
                    doc = nfe_monitor.process_document(
                        doc["id"],
                        estabelecimento_id=body.get("estabelecimento_id"),
                        user_id=uid,
                    )
                    rec = doc.pop("_receiving", None) or receiving_mvp.get_receiving(doc.get("receiving_id"))
                    return self._json({"status": "ok", "receiving": rec, "document": doc}, 201)
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
                except Exception as e:
                    return self._json({"status": "error", "message": f"falha ao importar XML: {e}"}, 500)

            # ── Monitor XML (RFC-4003) ──
            if parsed.path == "/api/nfe-monitor/ingest":
                try:
                    xml_text = body.get("xml") or body.get("xml_text") or ""
                    if body.get("xml_base64") and not xml_text:
                        import base64
                        xml_text = base64.b64decode(body["xml_base64"]).decode("utf-8", errors="replace")
                    if not xml_text:
                        return self._json({"status": "error", "message": "xml obrigatório"}, 400)
                    out = nfe_monitor.ingest_xml(
                        xml_text,
                        filename=body.get("filename"),
                        source=body.get("source") or "upload",
                        user_id=uid,
                    )
                    code = 200 if out.get("duplicate") else 201
                    return self._json({
                        "status": "ok" if not out.get("duplicate") else "duplicate",
                        "document": out["document"],
                        "message": out.get("message"),
                    }, code)
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)

            if parsed.path == "/api/nfe-monitor/scan":
                out = nfe_monitor.scan_inbox(user_id=uid)
                return self._json({"status": "ok", **out})

            if parsed.path == "/api/nfe-monitor/distdfe":
                try:
                    from modules.sefaz import nfe_distdfe
                    out = nfe_distdfe.consultar_e_baixar(
                        cnpj=body.get("cnpj"),
                        cert_id=body.get("cert_id"),
                        cert_senha=body.get("cert_senha") or body.get("senha"),
                        ambiente=body.get("ambiente"),
                        ult_nsu=body.get("ult_nsu") or body.get("ultNSU"),
                        max_loops=body.get("max_loops") or 3,
                        user_id=uid,
                    )
                    code = 200 if out.get("ok") else 502
                    return self._json({"status": "ok" if out.get("ok") else "error", **out}, code)
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
                except Exception as e:
                    return self._json({
                        "status": "error",
                        "message": f"DistDFe indisponível: {e}",
                    }, 502)

            if parsed.path == "/api/nfe-monitor/process-pending":
                out = nfe_monitor.process_pending(
                    estabelecimento_id=body.get("estabelecimento_id"),
                    user_id=uid,
                    limit=body.get("limit") or 20,
                )
                return self._json({"status": "ok", **out})

            if parsed.path.startswith("/api/receiving/pending/"):
                parts = parsed.path.rstrip("/").split("/")
                # /api/receiving/pending/{id}/resolve|ignore|cancel|assign
                if len(parts) >= 6 and parts[4].isdigit():
                    pid = parts[4]
                    action = parts[5]
                    try:
                        if action == "resolve":
                            item = receiving_pending.resolve(
                                pid, user_id=uid,
                                note=body.get("note"),
                                resolution=body.get("resolution"),
                            )
                        elif action == "ignore":
                            item = receiving_pending.ignore(pid, user_id=uid, note=body.get("note"))
                        elif action == "cancel":
                            item = receiving_pending.cancel(pid, user_id=uid, note=body.get("note"))
                        elif action == "assign":
                            item = receiving_pending.assign(
                                pid, body.get("assigned_to") or uid, user_id=uid
                            )
                        else:
                            return self._json({"status": "error", "message": f"ação desconhecida: {action}"}, 400)
                        return self._json({"status": "ok", "item": item})
                    except ValueError as e:
                        return self._json({"status": "error", "message": str(e)}, 400)
                return self._json({"status": "error", "message": "Rota inválida"}, 400)

            if parsed.path.startswith("/api/nfe-monitor/"):
                parts = parsed.path.rstrip("/").split("/")
                # /api/nfe-monitor/{id}/process|retry
                if len(parts) >= 5 and parts[3].isdigit():
                    doc_id = parts[3]
                    action = parts[4]
                    try:
                        if action == "process":
                            doc = nfe_monitor.process_document(
                                doc_id,
                                estabelecimento_id=body.get("estabelecimento_id"),
                                user_id=uid,
                            )
                        elif action == "retry":
                            doc = nfe_monitor.retry_document(
                                doc_id,
                                estabelecimento_id=body.get("estabelecimento_id"),
                                user_id=uid,
                            )
                        else:
                            return self._json({"status": "error", "message": f"ação desconhecida: {action}"}, 400)
                        rec = doc.pop("_receiving", None)
                        payload = {"status": "ok", "document": doc}
                        if rec:
                            payload["receiving"] = rec
                        return self._json(payload)
                    except ValueError as e:
                        return self._json({"status": "error", "message": str(e)}, 400)
                return self._json({"status": "error", "message": "Rota inválida"}, 400)

            if parsed.path == "/api/receiving":
                try:
                    rec = receiving_mvp.create_receiving(body, user_id=uid)
                    return self._json({"status": "ok", "receiving": rec}, 201)
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)

            parts = parsed.path.rstrip("/").split("/")
            # /api/receiving/{id}/{action?}
            if len(parts) < 4:
                return self._json({"status": "error", "message": "Rota inválida"}, 400)
            rid = parts[3]
            action = parts[4] if len(parts) > 4 else (body.get("action") or "update")
            try:
                if action == "verify":
                    rec = receiving_mvp.verify_receiving(rid, body, user_id=uid)
                    return self._json({"status": "ok", "receiving": rec})
                if action == "start-verify":
                    rec = receiving_mvp.start_verification(
                        rid, user_id=uid, method=body.get("method") or "manual"
                    )
                    return self._json({"status": "ok", "receiving": rec})
                if action == "reopen-verify":
                    rec = receiving_mvp.reopen_verification(rid, user_id=uid)
                    return self._json({"status": "ok", "receiving": rec})
                if action == "scan":
                    out = receiving_mvp.scan_receiving_item(
                        rid,
                        body.get("barcode") or body.get("ean") or body.get("code"),
                        qty=body.get("qty") or 1,
                        user_id=uid,
                    )
                    return self._json({
                        "status": "ok",
                        "receiving": out["receiving"],
                        "item_index": out["item_index"],
                        "item": out["item"],
                        "barcode": out["barcode"],
                    })
                if action == "complete":
                    auto = bool(body.get("auto_verify"))
                    qc = body.get("quality_respostas") or body.get("quality") or None
                    force = bool(body.get("force_quality"))
                    rec = receiving_mvp.complete_receiving(rid, user_id=uid, auto_verify=auto, quality_respostas=qc, force_quality=force)
                    contab = None
                    try:
                        contab = accounting_integration.on_receiving_complete(rec, actor=uid)
                    except Exception as e:
                        contab = {"ok": False, "error": str(e), "domain": "receiving"}
                    return self._json({"status": "ok", "receiving": rec, "contabilidade": contab})
                if action == "cancel":
                    rec = receiving_mvp.cancel_receiving(rid, user_id=uid, motivo=body.get("motivo"))
                    return self._json({"status": "ok", "receiving": rec})
                if action == "link-product":
                    rem = body.get("remember")
                    remember = True if rem is None else bool(rem)
                    rec = receiving_mvp.link_item_product(
                        rid,
                        body.get("item_index"),
                        body.get("produto_id") or body.get("id"),
                        produto_nome=body.get("produto_nome") or body.get("nome"),
                        user_id=uid,
                        remember=remember,
                    )
                    return self._json({"status": "ok", "receiving": rec})
                if action == "link-partner":
                    rec = receiving_mvp.link_partner(
                        rid,
                        body.get("partner_id") or body.get("fornecedor_id") or body.get("id"),
                        user_id=uid,
                    )
                    return self._json({"status": "ok", "receiving": rec})
                if action == "resolve-partner":
                    rec = receiving_mvp.resolve_partner_on_receiving(rid, user_id=uid)
                    return self._json({"status": "ok", "receiving": rec})
                if action == "sync-pending":
                    rec = receiving_mvp.get_receiving(rid)
                    if not rec:
                        return self._json({"status": "error", "message": "Recebimento não encontrado"}, 404)
                    created = receiving_pending.sync_from_receiving(rec, user_id=uid)
                    return self._json({
                        "status": "ok",
                        "created": created,
                        "open_count": receiving_pending.open_count(rid),
                        "items": receiving_pending.list_pending(receiving_id=rid, open_only=True),
                    })
                return self._json({"status": "error", "message": f"ação desconhecida: {action}"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── POS: criar pedido na fila ──
        if parsed.path == "/api/pos/fila":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            lines = body.get("lines") or []
            if not isinstance(lines, list) or not lines:
                return self._json({"status": "error", "message": "Pedido sem itens"}, 400)
            if body.get("training"):
                return self._json({"status": "error", "message": "Treino não grava na fila"}, 400)
            total = _safe_float(body.get("total"), 0)
            tem_troca = _pedido_tem_troca(lines)
            if total <= 0 and not tem_troca:
                return self._json({"status": "error", "message": "Total inválido"}, 400)
            troca_aprov = None
            if tem_troca:
                try:
                    troca_aprov = _validar_troca_aprovacao(body.get("troca_aprovacao"))
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 403)
            fila = load_pos_fila()
            order_num = int(fila.get("next_num") or 1000)
            fila["next_num"] = order_num + 1
            now = datetime.now().isoformat(timespec="seconds")
            client = body.get("client") if isinstance(body.get("client"), dict) else {}
            pdv_uid = next(
                    (uid for uid, u in users.items() if u.get("token") == token),
                    "",
                )
            term = _terminal_do_usuario(pdv_uid)
            estab_id = (body.get("estabelecimento_id") or "").strip()
            term_id = (body.get("terminal_id") or "").strip()
            if term:
                if not estab_id:
                    estab_id = (term.get("estabelecimento_id") or "").strip()
                if not term_id:
                    term_id = term.get("id") or ""
            pedido = {
                "id": str(uuid.uuid4())[:12],
                "orderNum": order_num,
                "state": "aguardando",
                "training": False,
                "createdAt": now,
                "updatedAt": now,
                "pdvUser": user.get("nome") or user.get("usuario") or "",
                "pdvUserId": pdv_uid,
                "estabelecimento_id": estab_id,
                "terminal_id": term_id,
                "sessionId": body.get("sessionId") or "",
                "client": {
                    "id": client.get("id") or "cf",
                    "nome": client.get("nome") or "Consumidor final",
                    "av": client.get("av") or "CF",
                    "cpf": client.get("cpf") or "",
                    "hint": client.get("hint") or "",
                },
                "lines": lines,
                "subtotal": _safe_float(body.get("subtotal"), 0),
                "discount": _safe_float(body.get("discount"), 0),
                "surcharge": _safe_float(body.get("surcharge"), 0),
                "promo": _safe_float(body.get("promo"), 0),
                "promo_kits": _safe_float(body.get("promo_kits"), 0),
                "total": round(total, 2),
                "orderDisc": body.get("orderDisc") or {"type": "val", "value": 0},
                "orderAcr": body.get("orderAcr") or {"type": "val", "value": 0},
                "orderParc": body.get("orderParc"),
                "troca_aprovacao": troca_aprov,
            }
            fila["pedidos"].append(pedido)
            # mantém no máximo 200 pedidos no arquivo
            if len(fila["pedidos"]) > 200:
                fila["pedidos"] = fila["pedidos"][-200:]
            save_pos_fila(fila)
            return self._json({"status": "ok", "pedido": pedido})

        if parsed.path.startswith("/api/pos/fila/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            user = self._find_user(token, users)
            if not user:
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            pid = parsed.path.rstrip("/").split("/")[-1]
            fila = load_pos_fila()
            pedido = next((p for p in fila["pedidos"] if str(p.get("id")) == pid), None)
            if not pedido:
                return self._json({"status": "error", "message": "Pedido não encontrado"}, 404)
            action = (body.get("action") or "").strip().lower()

            if action == "finalizar":
                cur = str(pedido.get("state") or "aguardando").lower()
                if cur == "pago":
                    return self._json({
                        "status": "ok",
                        "pedido": pedido,
                        "nfce": pedido.get("nfce"),
                        "message": "Pedido já estava pago",
                    })
                if cur == "cancelado":
                    return self._json({"status": "error", "message": "Pedido cancelado"}, 400)

                forma_pg = (body.get("forma_pg") or pedido.get("forma_pg") or "Dinheiro").strip()
                emitir = body.get("emitir_nfce", True)
                if isinstance(emitir, str):
                    emitir = emitir.lower() not in ("0", "false", "nao", "não", "no")

                # sessão de caixa (turno)
                caixa_uid = next(
                    (uid for uid, u in users.items() if u.get("token") == token),
                    "",
                )
                term_cx = _terminal_do_usuario(caixa_uid)
                sessao = None
                if term_cx:
                    sessao = pos_caixa.get_sessao_aberta(terminal_id=term_cx.get("id"))
                if not sessao and not body.get("training"):
                    return self._json({
                        "status": "error",
                        "message": "Abra o caixa (fundo de troco) antes de receber pagamentos",
                    }, 400)

                if _pedido_tem_troca(pedido.get("lines") or []):
                    try:
                        pedido["troca_aprovacao"] = _validar_troca_aprovacao(
                            body.get("troca_aprovacao") or pedido.get("troca_aprovacao")
                        )
                    except ValueError as e:
                        return self._json({"status": "error", "message": str(e)}, 403)

                pedido["state"] = "pagamento"
                pedido["forma_pg"] = forma_pg
                pedido["caixaUser"] = user.get("nome") or user.get("usuario") or ""
                if term_cx:
                    pedido["terminal_caixa_id"] = term_cx.get("id") or ""
                    if not pedido.get("estabelecimento_id"):
                        pedido["estabelecimento_id"] = term_cx.get("estabelecimento_id") or ""
                if sessao:
                    pedido["sessao_id"] = sessao.get("id")
                pedido["updatedAt"] = datetime.now().isoformat(timespec="seconds")

                # Campanhas: total final = sub − desc + acrésc − kits − campanhas(forma)
                try:
                    catalog = {str(p.get("id")): p for p in (cobol_bridge.produtos_listar() or [])}
                except Exception:
                    catalog = {}
                camp_out = campaigns.apply_campaigns(
                    pedido.get("lines") or [],
                    catalog_by_id=catalog,
                    forma_pg=forma_pg,
                    provisional=False,
                )
                base_sub = _safe_float(pedido.get("subtotal"), 0)
                if base_sub <= 0:
                    base_sub = round(
                        sum(
                            max(0.0, _safe_float(l.get("qtd"), 0) * _safe_float(l.get("preco"), 0))
                            for l in (pedido.get("lines") or [])
                            if isinstance(l, dict) and not l.get("troca")
                        ),
                        2,
                    )
                disc = _safe_float(pedido.get("discount"), 0)
                acr = _safe_float(pedido.get("surcharge"), 0)
                kits = _safe_float(pedido.get("promo_kits"), 0)
                camp_disc = _safe_float(camp_out.get("discount"), 0)
                total_final = round(max(0.0, base_sub - disc + acr - kits - camp_disc), 2)
                pedido["promo"] = round(kits + camp_disc, 2)
                pedido["campaigns"] = camp_out.get("applied") or []
                pedido["total"] = total_final

                venda = _pedido_para_venda(pedido, forma_pg)
                if pedido.get("campaigns"):
                    venda["campaigns"] = pedido["campaigns"]
                if pedido.get("troca_aprovacao"):
                    venda["troca_aprovacao"] = pedido["troca_aprovacao"]
                vendas_path = os.path.join(BASE_DIR, "dados", "vendas.json")
                vendas_data = load_json(vendas_path)
                if not isinstance(vendas_data, dict):
                    vendas_data = {"vendas": [], "total_vendas": 0}
                lista_v = vendas_data.get("vendas") or []
                # id numérico sequencial para compat com tela NFC-e
                try:
                    next_vid = max([int(v.get("id") or 0) for v in lista_v] or [0]) + 1
                except Exception:
                    next_vid = len(lista_v) + 1
                venda["id"] = next_vid
                lista_v.append(venda)
                vendas_data["vendas"] = lista_v
                vendas_data["total_vendas"] = len(lista_v)
                save_json(vendas_path, vendas_data)
                pedido["venda_id"] = next_vid

                # Inventário MVP: movimento sale (ledger)
                try:
                    baixar_estoque_local(
                        pedido.get("estabelecimento_id"),
                        pedido.get("lines") or [],
                        venda_id=next_vid,
                    )
                except Exception:
                    pass

                # Contabilidade (RFC-8008): evento → posting (não bloqueia venda)
                contab = None
                try:
                    user = self._find_user(token, load_users()) or {}
                    actor = user.get("usuario") or user.get("nome") or ""
                    contab = accounting_integration.on_pos_sale(
                        venda, forma_pg=forma_pg, actor=actor
                    )
                except Exception as e:
                    contab = {"ok": False, "error": str(e), "domain": "pos_sale"}

                nfce_out = None
                aviso = ""
                if emitir and not (venda.get("itens") or []):
                    emitir = False
                    aviso = "Devolução/troca sem itens de venda — NFC-e de venda não emitida."
                if emitir:
                    estab_id = (pedido.get("estabelecimento_id") or body.get("estabelecimento_id") or "").strip()
                    if not estab_id:
                        # fallback: terminal do caixa logado
                        caixa_uid = next(
                            (uid for uid, u in load_users().items() if u.get("token") == token),
                            "",
                        )
                        term_cx = _terminal_do_usuario(caixa_uid)
                        if term_cx:
                            estab_id = (term_cx.get("estabelecimento_id") or "").strip()
                    empresa = resolve_empresa_fiscal(estab_id or None)
                    csc = str(empresa.get("csc") or "").strip()
                    if not csc or "ALTERAR" in csc.upper() or csc == "HOMOLOGACAO-CSC-ALTERAR":
                        aviso = (
                            f"CSC não configurado para o estabelecimento "
                            f"'{estab_id or 'legado'}' (Configurações → Fiscal)."
                        )
                    cert_id = _resolve_cert_id(empresa, body.get("cert_id", ""))
                    cert_senha = body.get("cert_senha") or empresa.get("cert_senha") or ""
                    ambiente = int(body.get("ambiente", empresa.get("ambiente", 2) or 2))
                    serie = int(body.get("serie", empresa.get("serie_nfce", 1) or 1))
                    if not cert_id:
                        aviso = (aviso + " " if aviso else "") + "Nenhum certificado válido no índice."
                    elif not cert_senha:
                        aviso = (aviso + " " if aviso else "") + "Senha do certificado ausente."
                    else:
                        try:
                            nfce_out = _autorizar_nfce_de_venda(
                                venda, empresa, cert_id, cert_senha, ambiente=ambiente, serie=serie
                            )
                            pedido["nfce"] = {
                                "numero": nfce_out.get("numero"),
                                "serie": nfce_out.get("serie"),
                                "chave": nfce_out.get("chave"),
                                "estabelecimento_id": estab_id,
                                "cStat": (nfce_out.get("resultado") or {}).get("cStat"),
                                "xMotivo": (nfce_out.get("resultado") or {}).get("xMotivo"),
                                "status": (nfce_out.get("resultado") or {}).get("status"),
                                "protocolo": (nfce_out.get("resultado") or {}).get(
                                    "nProt", (nfce_out.get("resultado") or {}).get("protocolo", "")
                                ),
                                "ambiente": ambiente,
                            }
                        except Exception as e:
                            aviso = (aviso + " " if aviso else "") + f"Falha NFC-e: {e}"
                            pedido["nfce"] = {"status": "ERRO", "xMotivo": str(e), "estabelecimento_id": estab_id}

                pedido["state"] = "pago"
                pedido["updatedAt"] = datetime.now().isoformat(timespec="seconds")
                save_pos_fila(fila)
                return self._json({
                    "status": "ok",
                    "pedido": pedido,
                    "venda_id": next_vid,
                    "nfce": nfce_out,
                    "aviso": aviso.strip(),
                    "contabilidade": contab,
                })

            if action != "status":
                return self._json({"status": "error", "message": "Ação inválida"}, 400)
            new_state = str(body.get("state") or "").strip().lower()
            allowed = {
                "aguardando": {"pagamento", "cancelado"},
                "pagamento": {"pago", "aguardando", "cancelado"},
                "pago": set(),
                "cancelado": set(),
            }
            cur = str(pedido.get("state") or "aguardando").lower()
            if new_state not in allowed.get(cur, set()) and new_state != cur:
                return self._json(
                    {
                        "status": "error",
                        "message": f"Transição inválida: {cur} → {new_state}",
                    },
                    400,
                )
            pedido["state"] = new_state
            pedido["updatedAt"] = datetime.now().isoformat(timespec="seconds")
            pedido["caixaUser"] = user.get("nome") or user.get("usuario") or ""
            save_pos_fila(fila)
            return self._json({"status": "ok", "pedido": pedido})

        if parsed.path == "/api/pos/autorizar-gerente":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            if not self._find_user(token, users):
                return self._json({"status": "error", "message": "Não autenticado"}, 401)
            try:
                aprov = autorizar_gerente(
                    body.get("usuario"),
                    body.get("senha"),
                    users,
                    motivo=body.get("motivo") or body.get("motivo_aprovacao") or "",
                )
                return self._json({"status": "ok", "aprovacao": aprov})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 403)

        if parsed.path == "/api/auth/login":
            usuario = body.get("usuario", "").strip()
            senha = body.get("senha", "")
            users = load_users()
            for uid, u in users.items():
                if u["usuario"] == usuario and u["senha"] == hash_password(senha):
                    if not u.get("ativo", True):
                        return self._json({"status": "error", "message": "Usuário desativado"}, 403)
                    u["token"] = make_token()
                    save_users(users)
                    role = u.get("role", "operador")
                    return self._json({
                        "status": "ok", "token": u["token"],
                        "nome": u["nome"], "usuario": u["usuario"],
                        "role": role, "id": uid,
                        "pos": (ROLES.get(role) or {}).get("pos"),
                        "empresas": user_empresas(u)
                    })
            return self._json({"status": "error", "message": "Usuário ou senha incorretos"}, 401)

        if parsed.path == "/api/admin/users":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            usuario = body.get("usuario", "").strip()
            nome = body.get("nome", "").strip()
            senha = body.get("senha", "")
            role = body.get("role", "vendedor")
            if role not in ROLE_IDS:
                return self._json({"status": "error", "message": f"Perfil inválido: {role}"}, 400)
            empresas = body.get("empresas", {})
            if not usuario or not nome or not senha:
                return self._json({"status": "error", "message": "Preencha todos os campos"}, 400)
            for uid, u in users.items():
                if u["usuario"] == usuario:
                    return self._json({"status": "error", "message": "Usuário já existe"}, 400)
            uid = str(uuid.uuid4())[:8]
            users[uid] = {
                "usuario": usuario,
                "nome": nome,
                "senha": hash_password(senha),
                "email": body.get("email", ""),
                "role": role,
                "empresas": empresas,
                "ativo": True,
                "token": ""
            }
            save_users(users)
            return self._json({"status": "ok", "id": uid, "message": "Usuário criado"})

        if parsed.path.startswith("/api/admin/users/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            uid = parsed.path.split("/")[-1]
            if uid not in users:
                return self._json({"status": "error", "message": "Usuário não encontrado"}, 404)
            if body.get("action") == "toggle":
                users[uid]["ativo"] = not users[uid].get("ativo", True)
                save_users(users)
                return self._json({"status": "ok", "ativo": users[uid]["ativo"]})
            if body.get("action") == "delete" and uid != list(users.keys())[0]:
                del users[uid]
                save_users(users)
                return self._json({"status": "ok", "message": "Usuário removido"})
            if body.get("action") == "update":
                if body.get("nome"): users[uid]["nome"] = body["nome"]
                if body.get("role"):
                    if body["role"] not in ROLE_IDS:
                        return self._json({"status": "error", "message": f"Perfil inválido: {body['role']}"}, 400)
                    users[uid]["role"] = body["role"]
                if body.get("senha"): users[uid]["senha"] = hash_password(body["senha"])
                if "empresas" in body:
                    users[uid]["empresas"] = body["empresas"]
                if "email" in body:
                    users[uid]["email"] = body.get("email") or ""
                save_users(users)
                return self._json({"status": "ok", "message": "Usuário atualizado"})

        if parsed.path == "/api/admin/empresas":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            nome = body.get("nome", "").strip()
            cnpj = body.get("cnpj", "").strip()
            if not nome:
                return self._json({"status": "error", "message": "Nome é obrigatório"}, 400)
            empresas = load_empresas()
            eid = str(uuid.uuid4())[:8]
            empresas[eid] = {
                "nome": nome,
                "cnpj": cnpj,
                "ie": body.get("ie", ""),
                "cidade": body.get("cidade", ""),
                "uf": body.get("uf", ""),
                "ativo": True,
                "tipo": body.get("tipo") or "filial",
                "default_price_list_id": (body.get("default_price_list_id") or "").strip(),
            }
            save_empresas(empresas)
            fiscal = load_estab_fiscal_store()
            fiscal.setdefault(eid, {
                "csc_id": "1", "csc": "", "serie_nfce": 1, "numero_nfce": 1, "ambiente": 2,
            })
            save_estab_fiscal_store(fiscal)
            return self._json({"status": "ok", "id": eid, "message": "Estabelecimento criado"})

        if parsed.path == "/api/folha/empresa":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                allowed = [
                    "nome", "nome_fantasia", "nome_razao", "cnpj", "ie", "inscricao_est",
                    "inscricao_mun", "uf", "cep", "endereco", "logradouro", "numero",
                    "complemento", "bairro", "cidade", "municipio", "cod_municipio",
                    "telefone", "email", "cnae_prim_codigo", "cnae_prim_desc",
                    "tipo_fiscal", "crt", "ativo",
                ]
                # vazio explícito ("") = limpar campo — regra 3 exige CNAE/regime sempre
                updates = {k: body[k] for k in allowed if k in body}
                if not updates:
                    return self._json({"status": "error", "message": "Nenhum campo para atualizar"}, 400)
                if "nome" in updates and "nome_razao" not in updates:
                    updates["nome_razao"] = updates["nome"]
                emp, pronta, faltantes = org_store.salvar_empresa_folha(updates)
                return self._json({
                    "status": "ok",
                    "empresa": emp,
                    "folha_pronta": pronta,
                    "faltantes": faltantes,
                    "message": "Dados da empresa atualizados" if pronta
                               else f"Faltam: {', '.join(faltantes)}",
                })
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path in (
            "/api/folha/rescisao/calcular",
            "/api/folha/rescisao/incluir",
            "/api/folha/rescisao/pagar",
            "/api/folha/rescisao/excluir",
            "/api/funcionarios/desligar",
            "/api/funcionarios/reativar",
        ):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            # do_POST parseia JSON apenas; o frontend da folha envia form-urlencoded
            dados = dict(body or {})
            if "x-www-form-urlencoded" in self.headers.get("Content-Type", ""):
                qs = urllib.parse.parse_qs(raw)
                dados = {k: v[0] for k, v in qs.items()}
            mapa = {
                "funcionario_id": "funcionario_id",
                "nome": "nome",
                "motivo": "motivo",
                "data_desligamento": "data_deslig",
                "data_deslig": "data_deslig",
                "tipo_aviso": "tipo_aviso",
                "dias_aviso": "dias_aviso",
                "saldo_dias": "saldo_dias",
                "ferias_vencidas_dias": "ferias_venc_dias",
                "ferias_proporcionais_meses": "ferias_prop_meses",
                "13_meses": "13_prop_meses",
                "decimo_meses": "13_prop_meses",
                "salario_base": "salario_base",
            }
            cobol_dados = {}
            for k_orig, k_dest in mapa.items():
                if dados.get(k_orig) is not None:
                    cobol_dados[k_dest] = dados[k_orig]
            try:
                if parsed.path == "/api/folha/rescisao/calcular":
                    resultado = cobol_bridge.rescisao_calcular(cobol_dados)
                    return self._json({"status": "ok", **resultado})

                if parsed.path == "/api/folha/rescisao/incluir":
                    motivo = (dados.get("motivo") or "").strip()
                    if motivo not in cobol_bridge.RESCISAO_MOTIVOS:
                        return self._json({"status": "error",
                                           "message": "Motivo de desligamento obrigatorio ou invalido"}, 400)
                    func_id = dados.get("funcionario_id")
                    funcs = {str(f.get("id")): f for f in cobol_bridge.funcionarios_listar()}
                    f = funcs.get(str(func_id))
                    if f and (f.get("situacao_vinculo") or "").strip() == "desligado":
                        return self._json({"status": "error",
                                           "message": "Funcionario ja desligado"}, 400)
                    resultado = cobol_bridge.rescisao_incluir(cobol_dados)
                    data_deslig = dados.get("data_desligamento") or dados.get("data_deslig") or ""
                    try:
                        cobol_bridge.funcionario_desligar(func_id, data_deslig, motivo)
                    except Exception:
                        # rollback best-effort: remove a rescisão recém-criada
                        try:
                            cobol_bridge.rescisao_excluir(resultado.get("id"))
                        except Exception:
                            pass
                        raise
                    return self._json({"status": "ok",
                                       "message": "Rescisao registrada e funcionario desligado",
                                       **resultado})

                if parsed.path == "/api/folha/rescisao/pagar":
                    if not dados.get("id"):
                        return self._json({"status": "error", "message": "ID da rescisao obrigatorio"}, 400)
                    ok = cobol_bridge.rescisao_pagar(dados.get("id"), dados.get("data_pagamento"))
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Rescisao paga" if ok else "Erro ao pagar rescisao"})

                if parsed.path == "/api/folha/rescisao/excluir":
                    if not dados.get("id"):
                        return self._json({"status": "error", "message": "ID da rescisao obrigatorio"}, 400)
                    rid = dados.get("id")
                    func_id = None
                    for r in cobol_bridge.rescisao_listar():
                        if str(r.get("id")) == str(rid):
                            func_id = r.get("funcionario_id")
                            break
                    ok = cobol_bridge.rescisao_excluir(rid)
                    msg = "Rescisao excluida e funcionario reativado" if ok else "Erro ao excluir rescisao"
                    if ok and func_id:
                        try:
                            if not cobol_bridge.funcionario_reativar(func_id):
                                msg = "Rescisao excluida, mas falha ao reativar o funcionario"
                        except Exception:
                            msg = "Rescisao excluida, mas falha ao reativar o funcionario"
                    return self._json({"status": "ok" if ok else "error", "message": msg})

                if parsed.path == "/api/funcionarios/desligar":
                    if not dados.get("id"):
                        return self._json({"status": "error", "message": "ID do funcionario obrigatorio"}, 400)
                    motivo = (dados.get("motivo") or "").strip()
                    if motivo not in cobol_bridge.RESCISAO_MOTIVOS:
                        return self._json({"status": "error",
                                           "message": "Motivo de desligamento obrigatorio ou invalido"}, 400)
                    ok = cobol_bridge.funcionario_desligar(dados.get("id"),
                                                           dados.get("data_dem") or "",
                                                           motivo)
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Funcionario desligado" if ok else "Erro ao desligar funcionario"})

                if parsed.path == "/api/funcionarios/reativar":
                    if not dados.get("id"):
                        return self._json({"status": "error", "message": "ID do funcionario obrigatorio"}, 400)
                    ok = cobol_bridge.funcionario_reativar(dados.get("id"))
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Funcionario reativado" if ok else "Erro ao reativar funcionario"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/folha/config/salvar":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            fbody = dict(body or {})
            if "x-www-form-urlencoded" in self.headers.get("Content-Type", ""):
                qs = urllib.parse.parse_qs(raw)
                fbody = {k: v[0] for k, v in qs.items()}
            try:
                cobol_bridge.folha_config_seed()
                cobol_bridge.folha_config_salvar(fbody)
                return self._json({"status": "ok", "message": "Configuracao salva"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path in (
            "/api/folha/competencia/abrir",
            "/api/folha/competencia/calcular",
            "/api/folha/competencia/concluir",
            "/api/folha/competencia/validar",
            "/api/folha/competencia/fechar",
            "/api/folha/competencia/pagar",
        ):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            fbody = dict(body or {})
            if "x-www-form-urlencoded" in self.headers.get("Content-Type", ""):
                qs = urllib.parse.parse_qs(raw)
                fbody = {k: v[0] for k, v in qs.items()}
            try:
                cobol_bridge.folha_config_seed()
                competencia = (fbody.get("competencia") or "").strip()
                if parsed.path == "/api/folha/competencia/abrir":
                    if not competencia:
                        return self._json({"status": "error", "message": "Competencia obrigatoria"}, 400)
                    ok = cobol_bridge.folha_abrir(competencia)
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Competencia aberta" if ok else "Erro ao abrir competencia"})
                if parsed.path == "/api/folha/competencia/calcular":
                    if not competencia or not fbody.get("funcionario_id"):
                        return self._json({"status": "error",
                                           "message": "Competencia e funcionario obrigatorios"}, 400)
                    dados = {"competencia": competencia, "funcionario_id": fbody.get("funcionario_id")}
                    for campo in ("nome", "salario_base", "horas_extras", "dsr", "faltas",
                                  "dependentes", "outros_proventos", "outros_descontos"):
                        if fbody.get(campo) not in (None, ""):
                            dados[campo] = fbody.get(campo)
                    resultado = cobol_bridge.folha_calcular(dados)
                    return self._json({"status": "ok", **resultado})
                if parsed.path == "/api/folha/competencia/concluir":
                    ok = cobol_bridge.folha_concluir(competencia)
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Competencia calculada" if ok else "Erro ao concluir"})
                if parsed.path == "/api/folha/competencia/validar":
                    ok = cobol_bridge.folha_validar(competencia)
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Competencia validada" if ok else "Erro ao validar"})
                if parsed.path == "/api/folha/competencia/fechar":
                    ok = cobol_bridge.folha_fechar(competencia)
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Competencia fechada" if ok else "Erro ao fechar"})
                if parsed.path == "/api/folha/competencia/pagar":
                    if not competencia:
                        return self._json({"status": "error", "message": "Competencia obrigatoria"}, 400)
                    ok = cobol_bridge.folha_pagar(competencia, fbody.get("data_pagamento") or "")
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Pagamento registrado" if ok else "Erro ao registrar pagamento"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path in (
            "/api/folha/holerite/gerar",
            "/api/folha/holerite/pagar",
            "/api/folha/holerite/excluir",
            "/api/folha/holerite/detalhes/salvar",
        ):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            fbody = dict(body or {})
            if "x-www-form-urlencoded" in self.headers.get("Content-Type", ""):
                qs = urllib.parse.parse_qs(raw)
                fbody = {k: v[0] for k, v in qs.items()}
            try:
                if parsed.path == "/api/folha/holerite/gerar":
                    competencia = (fbody.get("competencia") or "").strip()
                    if not competencia:
                        return self._json({"status": "error", "message": "Competencia obrigatoria"}, 400)
                    return self._json(cobol_bridge.holerite_gerar(competencia))
                if parsed.path == "/api/folha/holerite/pagar":
                    if not fbody.get("id"):
                        return self._json({"status": "error", "message": "ID do holerite obrigatorio"}, 400)
                    ok = cobol_bridge.holerite_pagar(fbody.get("id"),
                                                     fbody.get("data_pagamento") or "")
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Holerite pago" if ok else "Erro ao pagar holerite"})
                if parsed.path == "/api/folha/holerite/excluir":
                    if not fbody.get("id"):
                        return self._json({"status": "error", "message": "ID do holerite obrigatorio"}, 400)
                    ok = cobol_bridge.holerite_excluir(fbody.get("id"))
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Holerite excluido" if ok else "Erro ao excluir holerite"})
                if parsed.path == "/api/folha/holerite/detalhes/salvar":
                    if not fbody.get("id"):
                        return self._json({"status": "error", "message": "ID do holerite obrigatorio"}, 400)
                    ok = cobol_bridge.holerite_obs(fbody.get("id"),
                                                   fbody.get("observacoes") or "")
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Observacoes salvas" if ok else "Erro ao salvar observacoes"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/organizacao":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            org = org_store.load_organizacao()
            if body.get("nome"):
                org["nome"] = str(body["nome"]).strip()
            if body.get("estabelecimento_padrao"):
                padrao = str(body["estabelecimento_padrao"]).strip()
                if padrao not in load_empresas():
                    return self._json({"status": "error", "message": "estabelecimento_padrao inválido"}, 400)
                org["estabelecimento_padrao"] = padrao
            org_store.save_organizacao(org)
            org_store.sync_legacy_empresa_json()
            return self._json({"status": "ok", "organizacao": org})

        if parsed.path.startswith("/api/admin/empresas/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            eid = parsed.path.split("/")[-1]
            empresas = load_empresas()
            if eid not in empresas:
                return self._json({"status": "error", "message": "Empresa não encontrada"}, 404)
            if body.get("action") == "toggle":
                empresas[eid]["ativo"] = not empresas[eid].get("ativo", True)
                save_empresas(empresas)
                return self._json({"status": "ok", "ativo": empresas[eid]["ativo"]})
            if body.get("action") == "update":
                updates = {}
                for k in ("nome", "cnpj", "ie", "cidade", "uf", "nome_fantasia", "nome_razao",
                          "endereco", "cep", "telefone", "email", "default_price_list_id"):
                    if k in body and body[k] is not None:
                        updates[k] = body[k]
                org_store.update_estabelecimento(eid, updates, also_fiscal=True)
                return self._json({"status": "ok", "message": "Estabelecimento atualizado"})

        if parsed.path.startswith("/api/admin/fiscal/estabelecimentos/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            eid = parsed.path.rstrip("/").split("/")[-1]
            if eid not in load_empresas():
                return self._json({"status": "error", "message": "Estabelecimento não encontrado"}, 404)
            fields = (
                "csc", "csc_id", "serie_nfce", "numero_nfce", "ambiente",
                "certificado", "cert_senha", "crt", "uf", "inscricao_est", "ie",
                "cod_municipio", "municipio", "nome", "nome_fantasia", "nome_razao", "cnpj",
                "endereco", "cep", "telefone", "email", "tipo_fiscal",
            )
            updates = {f: body[f] for f in fields if f in body}
            if "serie_nfce" in updates:
                updates["serie_nfce"] = int(updates.get("serie_nfce") or 1)
            if "numero_nfce" in updates:
                updates["numero_nfce"] = int(updates.get("numero_nfce") or 0)
            if "ambiente" in updates:
                updates["ambiente"] = int(updates.get("ambiente") or 2)
            emp = org_store.update_estabelecimento(eid, updates, also_fiscal=True)
            return self._json({
                "status": "ok",
                "id": eid,
                "overlay": load_estab_fiscal_store().get(eid, {}),
                "empresa": emp,
                "message": "Fiscal do estabelecimento salvo",
            })

        if parsed.path == "/api/admin/pos/terminais":
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            tipo = (body.get("tipo") or "").strip().lower()
            codigo = (body.get("codigo") or "").strip().upper()
            nome = (body.get("nome") or "").strip()
            estabelecimento_id = (body.get("estabelecimento_id") or "").strip()
            usuario_id = (body.get("usuario_id") or "").strip()
            if tipo not in ("pdv", "caixa"):
                return self._json({"status": "error", "message": "Tipo deve ser pdv ou caixa"}, 400)
            if not codigo or not nome or not estabelecimento_id:
                return self._json({"status": "error", "message": "Código, nome e estabelecimento são obrigatórios"}, 400)
            if not usuario_id:
                return self._json({"status": "error", "message": "Vínculo com usuário é obrigatório"}, 400)
            if usuario_id not in users:
                return self._json({"status": "error", "message": "Usuário não encontrado"}, 400)
            data = load_pos_terminais()
            terminais = data.get("terminais", [])
            if any(t.get("codigo", "").upper() == codigo for t in terminais):
                return self._json({"status": "error", "message": "Código de terminal já existe"}, 400)
            if tipo == "pdv":
                conflict = _pdv_user_conflict(terminais, usuario_id)
                if conflict:
                    return self._json({
                        "status": "error",
                        "message": f"Vendedor já vinculado ao PDV {conflict.get('codigo')} (relação 1:1)"
                    }, 400)
            tid = "t-" + str(uuid.uuid4())[:8]
            terminal = {
                "id": tid,
                "tipo": tipo,
                "codigo": codigo,
                "nome": nome,
                "estabelecimento_id": estabelecimento_id,
                "usuario_id": usuario_id,
                "usuario_nome": users[usuario_id].get("nome", ""),
                "ativo": True,
                "treino": bool(body.get("treino", True)),
                "impressora": (body.get("impressora") or "").strip(),
                "balanca": (body.get("balanca") or ("mock" if tipo == "pdv" else "nenhuma")).strip(),
                "timeout_min": int(body.get("timeout_min") or 30),
                "emite_nfce": bool(body.get("emite_nfce", tipo == "caixa")),
                "criado_em": datetime.now().isoformat(timespec="seconds"),
            }
            terminais.append(terminal)
            data["terminais"] = terminais
            save_pos_terminais(data)
            return self._json({"status": "ok", "id": tid, "terminal": terminal, "message": "Terminal criado"})

        if parsed.path.startswith("/api/admin/pos/terminais/"):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            tid = parsed.path.rstrip("/").split("/")[-1]
            data = load_pos_terminais()
            terminais = data.get("terminais", [])
            idx = next((i for i, t in enumerate(terminais) if t.get("id") == tid), None)
            if idx is None:
                return self._json({"status": "error", "message": "Terminal não encontrado"}, 404)
            action = body.get("action") or "update"
            if action == "delete":
                terminais.pop(idx)
                data["terminais"] = terminais
                save_pos_terminais(data)
                return self._json({"status": "ok", "message": "Terminal removido"})
            if action == "toggle":
                terminais[idx]["ativo"] = not terminais[idx].get("ativo", True)
                data["terminais"] = terminais
                save_pos_terminais(data)
                return self._json({"status": "ok", "ativo": terminais[idx]["ativo"], "terminal": terminais[idx]})
            # update / reassign
            t = terminais[idx]
            if body.get("nome") is not None:
                t["nome"] = str(body.get("nome") or "").strip() or t["nome"]
            if body.get("estabelecimento_id"):
                t["estabelecimento_id"] = str(body["estabelecimento_id"]).strip()
            if "treino" in body:
                t["treino"] = bool(body["treino"])
            if "impressora" in body:
                t["impressora"] = str(body.get("impressora") or "").strip()
            if "balanca" in body:
                t["balanca"] = str(body.get("balanca") or "").strip()
            if "timeout_min" in body:
                t["timeout_min"] = int(body.get("timeout_min") or 30)
            if "emite_nfce" in body:
                t["emite_nfce"] = bool(body["emite_nfce"])
            if "ativo" in body:
                t["ativo"] = bool(body["ativo"])
            if body.get("usuario_id"):
                uid = str(body["usuario_id"]).strip()
                if uid not in users:
                    return self._json({"status": "error", "message": "Usuário não encontrado"}, 400)
                if t.get("tipo") == "pdv":
                    conflict = _pdv_user_conflict(terminais, uid, exclude_id=tid)
                    if conflict:
                        return self._json({
                            "status": "error",
                            "message": f"Vendedor já vinculado ao PDV {conflict.get('codigo')} (relação 1:1)"
                        }, 400)
                t["usuario_id"] = uid
                t["usuario_nome"] = users[uid].get("nome", "")
            terminais[idx] = t
            data["terminais"] = terminais
            save_pos_terminais(data)
            return self._json({"status": "ok", "terminal": t, "message": "Terminal atualizado"})

        crud_token = self.headers.get("X-Auth-Token", "")

        # ── Plano de contas: CRUD + reimport ──
        if parsed.path == "/api/admin/planocontas/import":
            if not self._can_write_planocontas(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode reimportar",
                }, 403)
            try:
                meta = planocontas.import_from_xls((body or {}).get("path") if isinstance(body, dict) else None)
                return self._json({"status": "ok", **meta, "message": f"{meta.get('total', 0)} contas importadas"})
            except FileNotFoundError as e:
                return self._json({"status": "error", "message": str(e)}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/planocontas":
            if not self._can_write_planocontas(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode criar contas",
                }, 403)
            try:
                row = planocontas.create_conta(body or {})
                return self._json({"status": "ok", "conta": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if (
            parsed.path.startswith("/api/admin/planocontas/")
            and not parsed.path.rstrip("/").endswith("/import")
        ):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if isinstance(body, dict) and body.get("action") == "delete":
                if not self._can_delete_planocontas(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Exclusão permitida apenas ao responsável contábil/fiscal",
                    }, 403)
                try:
                    planocontas.delete_conta(key)
                    return self._json({"status": "ok", "message": "Conta excluída"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if not self._can_write_planocontas(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode editar contas",
                }, 403)
            try:
                row = planocontas.update_conta(key, body or {})
                return self._json({"status": "ok", "conta": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── WMS armazéns: CRUD (RFC-9001) ──
        if parsed.path == "/api/admin/wms/armazens":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar armazéns",
                }, 403)
            try:
                row = wms_warehouses.create_armazem(body or {})
                return self._json({"status": "ok", "armazem": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/wms/armazens/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if isinstance(body, dict) and body.get("action") == "delete":
                if not self._can_delete_wms(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Apenas admin, gerente ou supervisor pode excluir armazéns",
                    }, 403)
                try:
                    wms_warehouses.delete_armazem(key)
                    return self._json({"status": "ok", "message": "Armazém excluído"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode editar armazéns",
                }, 403)
            try:
                if isinstance(body, dict) and body.get("action") == "set_areas":
                    row = wms_warehouses.set_areas(key, body.get("areas") or [])
                else:
                    row = wms_warehouses.update_armazem(key, body or {})
                return self._json({"status": "ok", "armazem": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── WMS localizações: CRUD (RFC-9002) ──
        if parsed.path == "/api/admin/wms/localizacoes":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar localizações",
                }, 403)
            try:
                row = wms_locations.create_localizacao(body or {})
                return self._json({"status": "ok", "localizacao": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/wms/localizacoes/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if isinstance(body, dict) and body.get("action") == "delete":
                if not self._can_delete_wms(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Apenas admin, gerente ou supervisor pode excluir localizações",
                    }, 403)
                try:
                    wms_locations.delete_localizacao(key)
                    return self._json({"status": "ok", "message": "Localização excluída"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode editar localizações",
                }, 403)
            try:
                if isinstance(body, dict) and body.get("action") == "set_status":
                    row = wms_locations.set_status(
                        key,
                        body.get("status"),
                        motivo=body.get("bloqueio_motivo") or body.get("motivo"),
                    )
                else:
                    row = wms_locations.update_localizacao(key, body or {})
                return self._json({"status": "ok", "localizacao": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── WMS tipos de operação: CRUD (RFC-9003) ──
        if parsed.path == "/api/admin/wms/tipos-operacao":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar tipos de operação",
                }, 403)
            try:
                row = wms_operation_types.create_tipo(body or {})
                return self._json({"status": "ok", "tipo": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/wms/tipos-operacao/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if isinstance(body, dict) and body.get("action") == "delete":
                if not self._can_delete_wms(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Apenas admin, gerente ou supervisor pode excluir tipos de operação",
                    }, 403)
                try:
                    wms_operation_types.delete_tipo(key)
                    return self._json({"status": "ok", "message": "Tipo de operação excluído"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode editar tipos de operação",
                }, 403)
            try:
                row = wms_operation_types.update_tipo(key, body or {})
                return self._json({"status": "ok", "tipo": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── WMS operações: CRUD / lifecycle (RFC-9004) ──
        if parsed.path == "/api/admin/wms/operacoes":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar operações",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            try:
                row = wms_operations.create_operacao(
                    body or {},
                    usuario=user.get("usuario") or user.get("nome") or "",
                )
                return self._json({"status": "ok", "operacao": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/wms/operacoes/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            action = (body or {}).get("action") if isinstance(body, dict) else None
            if action == "delete":
                if not self._can_delete_wms(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Apenas admin, gerente ou supervisor pode excluir operações",
                    }, 403)
                try:
                    wms_operations.delete_operacao(key)
                    return self._json({"status": "ok", "message": "Operação excluída"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if action in (
                "plan", "ready", "start", "complete", "validate", "close", "cancel",
            ):
                if not self._can_write_wms(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Apenas admin, gerente ou supervisor pode avançar operações",
                    }, 403)
                try:
                    row = wms_operations.transition(
                        key,
                        action,
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or (body or {}).get("nota") or "",
                    )
                    return self._json({"status": "ok", "operacao": row})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode editar operações",
                }, 403)
            try:
                row = wms_operations.update_operacao(key, body or {}, usuario=uname)
                return self._json({"status": "ok", "operacao": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── WMS tarefas: CRUD / lifecycle / generate (RFC-9005) ──
        if parsed.path == "/api/admin/wms/tarefas":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar tarefas",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if isinstance(body, dict) and body.get("action") == "generate":
                try:
                    out = wms_tasks.generate_from_operation(
                        body.get("operacao_id"),
                        usuario=uname,
                    )
                    return self._json({"status": "ok", **out}, 201)
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            try:
                row = wms_tasks.create_tarefa(body or {}, usuario=uname)
                return self._json({"status": "ok", "tarefa": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/wms/tarefas/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            action = (body or {}).get("action") if isinstance(body, dict) else None
            if action == "delete":
                if not self._can_delete_wms(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Apenas admin, gerente ou supervisor pode excluir tarefas",
                    }, 403)
                try:
                    wms_tasks.delete_tarefa(key)
                    return self._json({"status": "ok", "message": "Tarefa excluída"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if action in (
                "assign", "start", "execute", "complete", "validate", "close", "cancel",
            ):
                if not self._can_write_wms(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Apenas admin, gerente ou supervisor pode avançar tarefas",
                    }, 403)
                try:
                    row = wms_tasks.transition(
                        key,
                        action,
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or (body or {}).get("nota") or "",
                        operador=(body or {}).get("operador"),
                        qtd_feita=(body or {}).get("qtd_feita"),
                    )
                    return self._json({"status": "ok", "tarefa": row})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode editar tarefas",
                }, 403)
            try:
                row = wms_tasks.update_tarefa(key, body or {}, usuario=uname)
                return self._json({"status": "ok", "tarefa": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── WMS picking & packing (RFC-9006) ──
        if parsed.path == "/api/admin/wms/picking/from-venda":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode gerar picking",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                venda = pedidos_b2b_store.get((body or {}).get("venda_id"))
                if not venda:
                    return self._json({"status": "error", "message": "Pedido de venda não encontrado"}, 404)
                out = wms_sales_bridge.create_wms_from_pedido(venda, usuario=uname)
                return self._json({"status": "ok", **out}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/wms/picking":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar picking",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                row = wms_picking.create_pick_list(body or {}, usuario=uname)
                return self._json({"status": "ok", "pick_list": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/wms/picking/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar picking",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action == "confirm_line":
                    row = wms_picking.confirm_line(
                        key,
                        (body or {}).get("linha"),
                        (body or {}).get("qtd_feita"),
                        usuario=uname,
                    )
                    return self._json({"status": "ok", "pick_list": row})
                if action in (
                    "start_pick", "complete_pick", "start_pack",
                    "complete_pack", "ready_ship", "close", "cancel",
                ):
                    row = wms_picking.transition_pick(
                        key,
                        action,
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or "",
                    )
                    return self._json({"status": "ok", "pick_list": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/wms/packages":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar volumes",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                row = wms_picking.create_package(body or {}, usuario=uname)
                return self._json({"status": "ok", "package": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/wms/packages/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar volumes",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action in ("seal", "ready", "ship", "cancel"):
                    row = wms_picking.transition_package(
                        key,
                        action,
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or "",
                    )
                    return self._json({"status": "ok", "package": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── WMS receiving process (RFC-9007) ──
        if parsed.path == "/api/admin/wms/recebimentos":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar recebimentos WMS",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                row = wms_receiving.create_recebimento(body or {}, usuario=uname)
                return self._json({"status": "ok", "recebimento": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/wms/recebimentos/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar recebimentos WMS",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action == "confirm_line":
                    row = wms_receiving.confirm_line(
                        key,
                        (body or {}).get("linha"),
                        (body or {}).get("qtd_recebida"),
                        usuario=uname,
                        lote=(body or {}).get("lote") or "",
                        serie=(body or {}).get("serie") or "",
                    )
                    return self._json({"status": "ok", "recebimento": row})
                if action == "inspect_line":
                    row = wms_receiving.inspect_line(
                        key,
                        (body or {}).get("linha"),
                        (body or {}).get("resultado"),
                        usuario=uname,
                        qtd_aprovada=(body or {}).get("qtd_aprovada"),
                    )
                    return self._json({"status": "ok", "recebimento": row})
                if action == "putaway_line":
                    row = wms_receiving.putaway_line(
                        key,
                        (body or {}).get("linha"),
                        (body or {}).get("loc_destino"),
                        usuario=uname,
                    )
                    return self._json({"status": "ok", "recebimento": row})
                if action in (
                    "arrive", "unload", "start_check", "start_inspect",
                    "start_putaway", "complete", "cancel",
                ):
                    row = wms_receiving.transition(
                        key,
                        action,
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or "",
                        transportadora=(body or {}).get("transportadora"),
                        veiculo=(body or {}).get("veiculo"),
                        operador=(body or {}).get("operador"),
                    )
                    return self._json({"status": "ok", "recebimento": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── WMS shipping process (RFC-9008) ──
        if parsed.path == "/api/admin/wms/expedicoes":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar expedições WMS",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                row = wms_shipping.create_expedicao(body or {}, usuario=uname)
                return self._json({"status": "ok", "expedicao": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/wms/expedicoes/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar expedições WMS",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action == "confirm_line":
                    row = wms_shipping.confirm_line(
                        key,
                        (body or {}).get("linha"),
                        (body or {}).get("qtd_conferida"),
                        usuario=uname,
                    )
                    return self._json({"status": "ok", "expedicao": row})
                if action == "set_loading":
                    row = wms_shipping.set_loading(
                        key,
                        usuario=uname,
                        transportadora=(body or {}).get("transportadora"),
                        veiculo=(body or {}).get("veiculo"),
                        motorista=(body or {}).get("motorista"),
                        rota=(body or {}).get("rota"),
                        package_ids=(body or {}).get("package_ids"),
                    )
                    return self._json({"status": "ok", "expedicao": row})
                if action in (
                    "plan", "start_pick", "start_check", "start_pack",
                    "start_load", "dispatch", "complete", "cancel",
                ):
                    row = wms_shipping.transition(
                        key,
                        action,
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or "",
                        transportadora=(body or {}).get("transportadora"),
                        veiculo=(body or {}).get("veiculo"),
                        motorista=(body or {}).get("motorista"),
                        rota=(body or {}).get("rota"),
                    )
                    return self._json({"status": "ok", "expedicao": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── WMS workspace quick actions (RFC-9010) ──
        if parsed.path == "/api/admin/wms/workspace":
            if not self._can_write_wms(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode executar ações do workspace",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                out = wms_workspace.quick_action(
                    (body or {}).get("kind"),
                    (body or {}).get("id"),
                    (body or {}).get("action"),
                    usuario=uname,
                    operador=(body or {}).get("operador") or uname,
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Delivery Platform (RFC-18000+) ──
        if parsed.path == "/api/admin/delivery/planning/move":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode planejar entregas",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                out = delivery_planning.move(
                    (body or {}).get("entrega_id"),
                    (body or {}).get("mode") or "driver",
                    (body or {}).get("target_id"),
                    usuario=uname,
                    motorista=(body or {}).get("motorista") or "",
                    veiculo=(body or {}).get("veiculo") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/calendar/reschedule":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode reagendar entregas",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                out = delivery_calendar.reschedule(
                    (body or {}).get("entrega_id"),
                    data=(body or {}).get("data"),
                    periodo=(body or {}).get("periodo") or (body or {}).get("janela"),
                    slot_id=(body or {}).get("slot_id") or (body or {}).get("novo_slot_id") or "",
                    usuario=uname,
                    motivo=(body or {}).get("motivo") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/manifest":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar manifestos",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                row = delivery_manifest.create_manifest(body or {}, usuario=uname)
                return self._json({"status": "ok", "manifest": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/delivery/manifest/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar manifestos",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                row = delivery_manifest.transition(
                    key,
                    action,
                    usuario=uname,
                    motivo=(body or {}).get("motivo") or "",
                    recurso_id=(body or {}).get("recurso_id"),
                    motorista=(body or {}).get("motorista"),
                    veiculo=(body or {}).get("veiculo"),
                    entrega_ids=(body or {}).get("entrega_ids"),
                )
                return self._json({"status": "ok", "manifest": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/trip":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar trips",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                mid = (body or {}).get("manifesto_id") or (body or {}).get("manifest_id")
                row = delivery_trip.create_from_manifest(mid, usuario=uname)
                return self._json({"status": "ok", "trip": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/delivery/trip/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar trips",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                row = delivery_trip.transition(
                    key,
                    action,
                    usuario=uname,
                    motivo=(body or {}).get("motivo") or "",
                )
                return self._json({"status": "ok", "trip": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/driver":
            # execução de campo — autenticado pode agir (demo motorista)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                out = delivery_driver_workspace.action(
                    (body or {}).get("trip_id"),
                    (body or {}).get("action"),
                    usuario=uname,
                    motivo=(body or {}).get("motivo") or "",
                    tipo=(body or {}).get("tipo") or "",
                    receptor_nome=(body or {}).get("receptor_nome") or "",
                    receptor_doc=(body or {}).get("receptor_doc") or "",
                    observacao=(body or {}).get("observacao") or "",
                    assinatura=(body or {}).get("assinatura") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/stops":
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                out = delivery_stops.action(
                    (body or {}).get("trip_id"),
                    (body or {}).get("seq"),
                    (body or {}).get("action"),
                    usuario=uname,
                    motivo=(body or {}).get("motivo") or "",
                    tipo=(body or {}).get("tipo") or "",
                    nota=(body or {}).get("nota") or "",
                    observacao=(body or {}).get("observacao") or "",
                    receptor_nome=(body or {}).get("receptor_nome") or "",
                    assinatura=(body or {}).get("assinatura") or "",
                    lat=(body or {}).get("lat"),
                    lng=(body or {}).get("lng"),
                    seq_order=(body or {}).get("seq_order"),
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/delivery/queue/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar a fila",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                out = delivery_queue.action(
                    key,
                    (body or {}).get("action"),
                    usuario=uname,
                    prioridade=(body or {}).get("prioridade"),
                    priority=(body or {}).get("priority"),
                    motorista=(body or {}).get("motorista") or "",
                    veiculo=(body or {}).get("veiculo") or "",
                    recurso_id=(body or {}).get("recurso_id") or "",
                    motivo=(body or {}).get("motivo") or "",
                    dispatch_id=(body or {}).get("dispatch_id") or "",
                    slot_id=(body or {}).get("slot_id") or (body or {}).get("novo_slot_id") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/workspace":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode executar ações do workspace",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                out = delivery_workspace.quick_action(
                    (body or {}).get("kind"),
                    (body or {}).get("id"),
                    (body or {}).get("action"),
                    usuario=uname,
                    motorista=(body or {}).get("motorista") or "",
                    veiculo=(body or {}).get("veiculo") or "",
                    recurso_id=(body or {}).get("recurso_id") or "",
                    motivo=(body or {}).get("motivo") or "",
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/orders":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar entregas",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                row = delivery_orders.create_order(body or {}, usuario=uname)
                return self._json({"status": "ok", "order": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/delivery/orders/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar entregas",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action == "update_stop":
                    row = delivery_orders.update_stop(
                        key,
                        (body or {}).get("parada"),
                        body or {},
                        usuario=uname,
                    )
                    return self._json({"status": "ok", "order": row})
                if action in (
                    "confirm", "wait_stock", "ready", "assign",
                    "depart", "deliver", "complete", "cancel",
                ):
                    row = delivery_orders.transition(
                        key,
                        action,
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or "",
                        recurso_id=(body or {}).get("recurso_id"),
                        motorista=(body or {}).get("motorista"),
                        veiculo=(body or {}).get("veiculo"),
                        data_agendada=(body or {}).get("data_agendada"),
                        janela=(body or {}).get("janela"),
                        force=(body or {}).get("force"),
                    )
                    return self._json({"status": "ok", "order": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/tarefas/gerar":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode gerar tarefas",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                out = delivery_tasks.generate_from_order(
                    (body or {}).get("entrega_id"),
                    usuario=uname,
                )
                return self._json({"status": "ok", **out})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/delivery/tarefas/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar tarefas de entrega",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action in ("assign", "start", "complete", "fail", "cancel"):
                    row = delivery_tasks.transition(
                        key,
                        action,
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or "",
                        operador=(body or {}).get("operador") or "",
                    )
                    return self._json({"status": "ok", "tarefa": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/recursos":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar recursos",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                row = delivery_resources.create_recurso(body or {}, usuario=uname)
                return self._json({"status": "ok", "recurso": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/delivery/recursos/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar recursos",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action == "set_status":
                    row = delivery_resources.set_status(
                        key,
                        (body or {}).get("status"),
                        usuario=(self._find_user(crud_token, load_users()) or {}).get("usuario") or "",
                    )
                    return self._json({"status": "ok", "recurso": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/dispatch":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar despachos",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                row = delivery_dispatch.create_dispatch(body or {}, usuario=uname)
                return self._json({"status": "ok", "dispatch": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/delivery/dispatch/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar despachos",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action == "add_entregas":
                    row = delivery_dispatch.add_entregas(
                        key,
                        (body or {}).get("entrega_ids"),
                        usuario=uname,
                    )
                    return self._json({"status": "ok", "dispatch": row})
                if action in ("plan", "assign", "release", "start", "complete", "close", "cancel"):
                    row = delivery_dispatch.transition(
                        key,
                        action,
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or "",
                        recurso_id=(body or {}).get("recurso_id"),
                        motorista=(body or {}).get("motorista"),
                        veiculo=(body or {}).get("veiculo"),
                    )
                    return self._json({"status": "ok", "dispatch": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/scheduling":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar slots",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action == "generate_week":
                    out = delivery_scheduling.generate_week(body or {}, usuario=uname)
                    return self._json({"status": "ok", **out}, 201)
                row = delivery_scheduling.create_slot(body or {}, usuario=uname)
                return self._json({"status": "ok", "slot": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/delivery/scheduling/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar agenda",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action == "reserve":
                    row = delivery_scheduling.reserve(
                        key,
                        (body or {}).get("entrega_id"),
                        usuario=uname,
                        status=(body or {}).get("status") or "scheduled",
                        motivo=(body or {}).get("motivo") or "",
                    )
                    return self._json({"status": "ok", "slot": row})
                if action == "confirm":
                    row = delivery_scheduling.confirm_booking(
                        key,
                        (body or {}).get("entrega_id"),
                        usuario=uname,
                    )
                    return self._json({"status": "ok", "slot": row})
                if action == "cancel_booking":
                    row = delivery_scheduling.cancel_booking(
                        key,
                        (body or {}).get("entrega_id"),
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or "",
                    )
                    return self._json({"status": "ok", "slot": row})
                if action == "reschedule":
                    row = delivery_scheduling.reschedule(
                        (body or {}).get("entrega_id"),
                        (body or {}).get("novo_slot_id") or (body or {}).get("slot_id") or key,
                        usuario=uname,
                        motivo=(body or {}).get("motivo") or "",
                    )
                    return self._json({"status": "ok", "slot": row})
                if action == "close":
                    row = delivery_scheduling.close_slot(
                        key, usuario=uname, motivo=(body or {}).get("motivo") or "",
                    )
                    return self._json({"status": "ok", "slot": row})
                if action == "cancel":
                    row = delivery_scheduling.cancel_slot(
                        key, usuario=uname, motivo=(body or {}).get("motivo") or "",
                    )
                    return self._json({"status": "ok", "slot": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/tracking":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode iniciar tracking",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            try:
                row = delivery_tracking.ensure_track(
                    (body or {}).get("entrega_id"), usuario=uname,
                )
                return self._json({"status": "ok", "track": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/delivery/tracking/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode registrar eventos",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action in ("arrived", "failed", "location", "note", "in_transit", "departed",
                              "prepared", "assigned", "delivered", "event"):
                    tipo = action if action != "event" else ((body or {}).get("tipo") or "note")
                    row = delivery_tracking.add_event(
                        (body or {}).get("entrega_id") or key,
                        tipo,
                        usuario=uname,
                        mensagem=(body or {}).get("mensagem") or (body or {}).get("motivo") or "",
                        parada=(body or {}).get("parada"),
                        lat=(body or {}).get("lat"),
                        lng=(body or {}).get("lng"),
                        visivel_cliente=(body or {}).get("visivel_cliente", True),
                        status=(body or {}).get("status"),
                    )
                    return self._json({"status": "ok", "track": row})
                if action == "ensure":
                    row = delivery_tracking.ensure_track(key, usuario=uname)
                    return self._json({"status": "ok", "track": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/delivery/pod":
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode criar POD",
                }, 403)
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action == "ensure":
                    out = delivery_pod.ensure_for_order(
                        (body or {}).get("entrega_id"), usuario=uname,
                    )
                    return self._json({"status": "ok", **out}, 201)
                row = delivery_pod.create_pod(body or {}, usuario=uname)
                return self._json({"status": "ok", "pod": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/delivery/pod/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            user = self._find_user(crud_token, load_users()) or {}
            uname = user.get("usuario") or user.get("nome") or ""
            if self._user_role(crud_token) not in DELIVERY_WRITE_ROLES:
                return self._json({
                    "status": "error",
                    "message": "Apenas admin, gerente ou supervisor pode alterar POD",
                }, 403)
            action = (body or {}).get("action") if isinstance(body, dict) else None
            try:
                if action == "capture":
                    row = delivery_pod.capture(key, body or {}, usuario=uname)
                    return self._json({"status": "ok", "pod": row})
                if action == "confirm":
                    row = delivery_pod.confirm(key, body or {}, usuario=uname)
                    return self._json({"status": "ok", "pod": row})
                if action == "reject":
                    row = delivery_pod.reject(key, body or {}, usuario=uname)
                    return self._json({"status": "ok", "pod": row})
                if action in ("review", "close", "wait"):
                    row = delivery_pod.transition(
                        key, action, usuario=uname,
                        motivo=(body or {}).get("motivo") or "",
                    )
                    return self._json({"status": "ok", "pod": row})
                return self._json({"status": "error", "message": "ação inválida"}, 400)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Diários: CRUD ──
        if parsed.path == "/api/admin/diarios":
            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode criar diários",
                }, 403)
            try:
                row = journals.create_diario(body or {})
                return self._json({"status": "ok", "diario": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/diarios/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if isinstance(body, dict) and body.get("action") == "delete":
                if not self._can_delete_journals(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Exclusão permitida apenas ao responsável contábil/fiscal",
                    }, 403)
                try:
                    journals.delete_diario(key)
                    return self._json({"status": "ok", "message": "Diário excluído"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode editar diários",
                }, 403)
            try:
                row = journals.update_diario(key, body or {})
                return self._json({"status": "ok", "diario": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Lançamentos: CRUD / post / estorno ──
        if parsed.path == "/api/admin/lancamentos":
            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode criar lançamentos",
                }, 403)
            try:
                row = journal_entries.create_lancamento(body or {})
                return self._json({"status": "ok", "lancamento": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/lancamentos/"):
            parts = [p for p in parsed.path.rstrip("/").split("/") if p]
            # /api/admin/lancamentos/{key}[/{action}]
            key = urllib.parse.unquote(parts[3]) if len(parts) >= 4 else ""
            action = urllib.parse.unquote(parts[4]) if len(parts) >= 5 else ""
            if isinstance(body, dict) and not action:
                action = str(body.get("action") or "").strip().lower()

            if action == "post":
                if not self._can_write_journals(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Apenas responsável contábil/fiscal ou admin pode postar",
                    }, 403)
                try:
                    user = self._find_user(crud_token, load_users()) or {}
                    actor = user.get("usuario") or user.get("nome") or ""
                    row = posting_engine.post(key, actor=actor, source="api")
                    return self._json({"status": "ok", "lancamento": row, "message": "Lançamento postado"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)

            if action in ("reverse", "estorno", "cancel"):
                if not self._can_write_journals(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Apenas responsável contábil/fiscal ou admin pode estornar",
                    }, 403)
                try:
                    user = self._find_user(crud_token, load_users()) or {}
                    actor = user.get("usuario") or user.get("nome") or ""
                    row = posting_engine.reverse(key, body or {}, actor=actor, source="api")
                    return self._json({"status": "ok", "lancamento": row, "message": "Estorno gerado"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)

            if action == "delete":
                if not self._can_delete_journals(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Exclusão permitida apenas ao responsável contábil/fiscal",
                    }, 403)
                try:
                    journal_entries.delete_lancamento(key)
                    return self._json({"status": "ok", "message": "Lançamento excluído"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)

            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode editar lançamentos",
                }, 403)
            try:
                row = journal_entries.update_lancamento(key, body or {})
                return self._json({"status": "ok", "lancamento": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Posting: regras + apply_event ──
        if parsed.path == "/api/admin/posting/apply":
            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode aplicar eventos",
                }, 403)
            try:
                user = self._find_user(crud_token, load_users()) or {}
                actor = user.get("usuario") or user.get("nome") or ""
                out = posting_engine.apply_event(body or {}, actor=actor)
                return self._json({"status": "ok", **out}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/posting/rules":
            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode criar regras",
                }, 403)
            try:
                row = posting_engine.create_rule(body or {})
                return self._json({"status": "ok", "regra": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/posting/rules/"):
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if isinstance(body, dict) and body.get("action") == "delete":
                if not self._can_delete_journals(crud_token):
                    return self._json({
                        "status": "error",
                        "message": "Exclusão permitida apenas ao responsável contábil/fiscal",
                    }, 403)
                try:
                    posting_engine.delete_rule(key)
                    return self._json({"status": "ok", "message": "Regra excluída"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode editar regras",
                }, 403)
            try:
                row = posting_engine.update_rule(key, body or {})
                return self._json({"status": "ok", "regra": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Integração contábil: config ──
        if parsed.path == "/api/admin/accounting/integration":
            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode alterar integração",
                }, 403)
            try:
                cfg = accounting_integration.update_config(body or {})
                return self._json({"status": "ok", "config": cfg})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/admin/accounting/integration/publish":
            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode republicar eventos",
                }, 403)
            try:
                user = self._find_user(crud_token, load_users()) or {}
                actor = user.get("usuario") or user.get("nome") or ""
                b = body or {}
                out = accounting_integration.publish(
                    domain=str(b.get("domain") or "manual"),
                    evento=b.get("evento"),
                    valor=b.get("valor"),
                    referencia=b.get("referencia"),
                    historico=b.get("historico"),
                    data=b.get("data"),
                    actor=actor,
                    auto_post=b.get("auto_post"),
                )
                code = 200 if out.get("ok") else 400
                return self._json({"status": "ok" if out.get("ok") else "error", **out}, code)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Períodos: ensure-year + status ──
        if parsed.path == "/api/admin/periodos/ensure-year":
            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode criar exercício",
                }, 403)
            try:
                ano = (body or {}).get("exercicio") or (body or {}).get("ano")
                st = (body or {}).get("status") or "open"
                out = accounting_periods.ensure_year(ano, status=st)
                return self._json({"status": "ok", **out, "message": f"Exercício {out.get('exercicio')} pronto"})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/periodos/"):
            if not self._can_write_journals(crud_token):
                return self._json({
                    "status": "error",
                    "message": "Apenas responsável contábil/fiscal ou admin pode alterar períodos",
                }, 403)
            key = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
            if key == "ensure-year":
                return self._json({"status": "error", "message": "use POST /api/admin/periodos/ensure-year"}, 400)
            st = None
            if isinstance(body, dict):
                st = body.get("status") or body.get("action")
            if not st:
                return self._json({"status": "error", "message": "informe status (open|closing|closed|locked)"}, 400)
            # map action aliases
            aliases = {
                "open": "open",
                "abrir": "open",
                "closing": "closing",
                "fechar": "closed",
                "close": "closed",
                "closed": "closed",
                "lock": "locked",
                "locked": "locked",
                "bloquear": "locked",
            }
            st = aliases.get(str(st).strip().lower(), str(st).strip().lower())
            try:
                user = self._find_user(crud_token, load_users()) or {}
                actor = user.get("usuario") or user.get("nome") or ""
                row = accounting_periods.set_status(key, st, actor=actor)
                return self._json({"status": "ok", "periodo": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Campanhas (POST) ──
        if parsed.path == "/api/admin/campaigns":
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                row = campaigns.upsert_campaign(body or {})
                return self._json({"status": "ok", "campaign": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/campaigns/"):
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            parts = parsed.path.rstrip("/").split("/")
            cid = parts[4] if len(parts) > 4 else ""
            if isinstance(body, dict) and body.get("action") == "delete":
                try:
                    campaigns.delete_campaign(cid)
                    return self._json({"status": "ok"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 404)
            try:
                row = campaigns.upsert_campaign(body or {}, campaign_id=cid)
                return self._json({"status": "ok", "campaign": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Listas de preço (POST) ──
        if parsed.path == "/api/admin/price-lists":
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                row = price_lists.upsert_list(body or {})
                return self._json({"status": "ok", "list": row}, 201)
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/price-lists/"):
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            parts = parsed.path.rstrip("/").split("/")
            lid = parts[4] if len(parts) > 4 else ""
            action = parts[5] if len(parts) > 5 else None
            if action == "delete" or (isinstance(body, dict) and body.get("action") == "delete"):
                try:
                    price_lists.delete_list(lid)
                    return self._json({"status": "ok"})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 404)
            if action == "set-item":
                try:
                    row = price_lists.set_item(lid, body.get("produto_id"), body.get("preco"))
                    return self._json({"status": "ok", "list": row})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            if action == "remove-item":
                try:
                    row = price_lists.remove_item(lid, body.get("produto_id"))
                    return self._json({"status": "ok", "list": row})
                except ValueError as e:
                    return self._json({"status": "error", "message": str(e)}, 400)
            try:
                row = price_lists.upsert_list(body or {}, list_id=lid)
                return self._json({"status": "ok", "list": row})
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── COBOL: Produtos (POST) ──
        if parsed.path == "/api/admin/produtos":
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                pid = cobol_bridge.produtos_incluir(body)
                return self._json({"status": "ok", "id": pid, "message": "Produto criado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/produtos/"):
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            eid = parsed.path.split("/")[-1]
            if eid == "sync":
                return self._json({"status": "ok", **cobol_bridge.sync_json()})
            if eid == "migrate-extras":
                n = cobol_bridge.produtos_extra_import(body.get("extras") or {}, overwrite=False)
                return self._json({"status": "ok", "imported": n, "message": f"{n} extras importados"})
            try:
                pid = int(eid)
                if body.get("action") == "toggle":
                    cobol_bridge.produtos_alterar(pid, {"ativo": ""})
                    return self._json({"status": "ok", "message": "Toggle não suportado via COBOL"})
                if body.get("action") == "update":
                    cobol_bridge.produtos_alterar(pid, body)
                    return self._json({"status": "ok", "message": "Produto atualizado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── COBOL: Fornecedores (POST) ──
        if parsed.path == "/api/admin/fornecedores":
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                fid = cobol_bridge.fornecedores_incluir(body)
                return self._json({"status": "ok", "id": fid, "message": "Fornecedor criado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/fornecedores/"):
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            eid = parsed.path.split("/")[-1]
            try:
                fid = int(eid)
                if body.get("action") == "toggle":
                    cobol_bridge.fornecedores_alterar(fid, {"nome": ""})
                    return self._json({"status": "ok", "message": "Fornecedor atualizado"})
                if body.get("action") == "update":
                    cobol_bridge.fornecedores_alterar(fid, body)
                    return self._json({"status": "ok", "message": "Fornecedor atualizado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        # ── Certificados (POST) ──
        if parsed.path == "/api/admin/certificados/upload":
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                pfx_b64 = body.get("arquivo", "")
                senha = body.get("senha", "")
                nome = body.get("nome_arquivo", "certificado.pfx")
                import base64
                pfx_data = base64.b64decode(pfx_b64)
                result = cert_service.upload(pfx_data, senha, nome)
                return self._json({"status": "ok", "certificado": result, "message": "Certificado importado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path.startswith("/api/admin/certificados/") and parsed.path != "/api/admin/certificados/upload":
            parts = parsed.path.rstrip("/").split("/")
            # parts = ['', 'api', 'admin', 'certificados', '<id>', ...]
            action = parts[-1] if len(parts) > 5 else ""
            cid = parts[-2] if action else parts[-1]

            if action == "validate":
                if not self._is_admin(crud_token):
                    return self._json({"status": "error", "message": "Acesso negado"}, 403)
                try:
                    result = cert_service.validar(cid)
                    return self._json({"status": "ok", **result})
                except Exception as e:
                    return self._json({"status": "error", "message": str(e)}, 400)

            if action == "toggle":
                if not self._is_admin(crud_token):
                    return self._json({"status": "error", "message": "Acesso negado"}, 403)
                novo = cert_service.alternar_ativo(cid)
                if novo is None:
                    return self._json({"status": "error", "message": "Não encontrado"}, 404)
                return self._json({"status": "ok", "ativo": novo})

            if action == "empresa":
                if not self._is_admin(crud_token):
                    return self._json({"status": "error", "message": "Acesso negado"}, 403)
                empresa_id = body.get("empresa_id", "")
                ok = cert_service.definir_empresa(cid, empresa_id)
                if not ok:
                    return self._json({"status": "error", "message": "Não encontrado"}, 404)
                return self._json({"status": "ok", "message": "Certificado vinculado à empresa"})

            if body.get("action") == "delete":
                if not self._is_admin(crud_token):
                    return self._json({"status": "error", "message": "Acesso negado"}, 403)
                ok = cert_service.remover(cid)
                if not ok:
                    return self._json({"status": "error", "message": "Não encontrado"}, 404)
                return self._json({"status": "ok", "message": "Certificado removido"})

        # ── Fiscal: salvar emitente (estabelecimento padrão + espelho legado) ──
        if parsed.path == "/api/admin/fiscal/empresa":
            if not self._is_admin(crud_token):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                allowed = [
                    "nome", "nome_fantasia", "nome_razao", "cnpj", "ie", "crt", "csc_id", "csc",
                    "cod_municipio", "municipio", "uf", "cep", "endereco", "telefone",
                    "email", "cnae_prim_codigo", "inscricao_mun", "tipo_fiscal",
                    "inscricao_est",
                ]
                updates = {k: body[k] for k in allowed if k in body and body[k] is not None}
                if "nome" in updates and "nome_razao" not in updates:
                    updates["nome_razao"] = updates["nome"]
                emp = org_store.save_emitente_padrao(updates)
                return self._json({
                    "status": "ok",
                    "empresa": emp,
                    "message": "Emitente salvo no estabelecimento padrão",
                })
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── Fiscal: NFC-e ──
        if parsed.path == "/api/admin/fiscal/nfce/autorizar":
            if not self._has_permission(crud_token, "nfce"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                venda_id = body.get("venda_id", "")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                serie = int(body.get("serie", 1))
                numero = int(body.get("numero", 0))

                if not venda_id or not cert_id:
                    return self._json({"status": "error", "message": "venda_id e cert_id são obrigatórios"}, 400)

                vendas = load_json(os.path.join(BASE_DIR, "dados", "vendas.json"))
                venda = None
                for v in vendas.get("vendas", []):
                    if str(v.get("id")) == str(venda_id):
                        venda = v
                        break
                if not venda:
                    return self._json({"status": "error", "message": "Venda não encontrada"}, 404)

                empresa = load_empresa_fiscal()
                uf = empresa.get("uf", "RS")
                if isinstance(uf, int):
                    uf_codes = {11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",21:"MA",22:"PI",23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",28:"SE",29:"BA",31:"MG",32:"ES",33:"RJ",35:"SP",41:"PR",42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF"}
                    uf = uf_codes.get(int(uf), "RS")

                if not numero:
                    cobol_bridge._compile_if_needed("gerir_numeracao")
                    out, _ = cobol_bridge._run("gerir_numeracao", {"ACAO": "avancar-nfce"})
                    for line in out.splitlines():
                        line = line.strip()
                        if line.isdigit():
                            numero = int(line)
                            break
                    if not numero:
                        return self._json({"status": "error", "message": "Erro ao obter numeração"}, 500)

                xml_envi = nfce_xml.montar_envi_nfe(venda, empresa, ambiente, serie, numero)
                resultado = sefaz_service.autorizar_nfce(xml_envi, uf, ambiente, cert_id, cert_senha, empresa=empresa)

                nfce_path = os.path.join(BASE_DIR, "dados", "nfce.json")
                nfce_data = load_json(nfce_path)
                notas = nfce_data.get("nfce", [])
                notas.append({
                    "venda_id": venda_id,
                    "numero": numero,
                    "serie": serie,
                    "chave": resultado.get("chave", ""),
                    "ambiente": ambiente,
                    "status": resultado.get("status", "ERRO"),
                    "protocolo": resultado.get("nProt", resultado.get("protocolo", "")),
                    "cStat": resultado.get("cStat", ""),
                    "xMotivo": resultado.get("xMotivo", ""),
                    "xml": xml_envi,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                nfce_data["nfce"] = notas
                save_json(nfce_path, nfce_data)

                return self._json({"status": "ok", "resultado": resultado, "numero": numero, "chave": resultado.get("chave", "")})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfce/consultar":
            if not self._has_permission(crud_token, "nfce"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                chave = body.get("chave", "")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                uf = body.get("uf", "RS")
                if not chave or not cert_id:
                    return self._json({"status": "error", "message": "chave e cert_id são obrigatórios"}, 400)
                resultado = sefaz_service.consultar_nfce(chave, uf, ambiente, cert_id, cert_senha)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfce/cancelar":
            if not self._has_permission(crud_token, "nfce"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                chave = body.get("chave", "")
                protocolo = body.get("protocolo", "")
                justificativa = body.get("justificativa", "Cancelamento manual")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                uf = body.get("uf", "RS")
                if not chave or not protocolo or not cert_id:
                    return self._json({"status": "error", "message": "chave, protocolo e cert_id são obrigatórios"}, 400)
                resultado = sefaz_service.cancelar_nfce(chave, protocolo, uf, ambiente, cert_id, cert_senha, justificativa)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── Fiscal: NF-e (modelo 55) ──
        if parsed.path == "/api/admin/fiscal/nfe/autorizar":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                # B2B / rascunho existente: autoriza XML já salvo
                if body.get("simular") or body.get("pedido_b2b_id") or body.get("nfe_numero") \
                        or (body.get("venda_id") or "").startswith("b2b-") \
                        or body.get("from_draft"):
                    out = _b2b_autorizar_nfe(body)
                    return self._json({
                        "status": "ok",
                        "resultado": out.get("resultado"),
                        "numero": (out.get("nfe") or {}).get("numero"),
                        "chave": (out.get("nfe") or {}).get("chave") or "",
                        "nfe": out.get("nfe"),
                    })

                venda_id = body.get("venda_id", "")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                serie = int(body.get("serie", 1))
                numero = int(body.get("numero", 0))
                sincrono = body.get("sincrono", False)

                if not venda_id or not cert_id:
                    return self._json({"status": "error", "message": "venda_id e cert_id são obrigatórios"}, 400)

                vendas = load_json(os.path.join(BASE_DIR, "dados", "vendas.json"))
                venda = None
                for v in vendas.get("vendas", []):
                    if str(v.get("id")) == str(venda_id):
                        venda = v
                        break
                if not venda:
                    # tenta rascunho B2B com venda_id sintético
                    idx, draft = _nfe_find_draft(venda_id=venda_id)
                    if draft:
                        out = _b2b_autorizar_nfe(body)
                        return self._json({
                            "status": "ok",
                            "resultado": out.get("resultado"),
                            "numero": (out.get("nfe") or {}).get("numero"),
                            "chave": (out.get("nfe") or {}).get("chave") or "",
                            "nfe": out.get("nfe"),
                        })
                    return self._json({"status": "error", "message": "Venda não encontrada"}, 404)

                empresa = load_empresa_fiscal()
                uf = empresa.get("uf", "RS")
                if isinstance(uf, int):
                    uf_codes = {11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",21:"MA",22:"PI",23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",28:"SE",29:"BA",31:"MG",32:"ES",33:"RJ",35:"SP",41:"PR",42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF"}
                    uf = uf_codes.get(int(uf), "RS")

                if not numero:
                    cobol_bridge._compile_if_needed("gerir_numeracao")
                    out, _ = cobol_bridge._run("gerir_numeracao", {"ACAO": "avancar-nfe"})
                    for line in out.splitlines():
                        line = line.strip()
                        if line.isdigit():
                            numero = int(line)
                            break
                    if not numero:
                        return self._json({"status": "error", "message": "Erro ao obter numeração"}, 500)

                xml_envi = nfe_xml.montar_envi_nfe(venda, empresa, ambiente, serie, numero, sincrono=sincrono)
                resultado = sefaz_service.autorizar_nfe(xml_envi, uf, ambiente, cert_id, cert_senha)

                nfe_path = os.path.join(BASE_DIR, "dados", "nfe.json")
                nfe_data = load_json(nfe_path)
                notas = nfe_data.get("nfe", [])
                notas.append({
                    "venda_id": venda_id,
                    "numero": numero,
                    "serie": serie,
                    "chave": resultado.get("chave", ""),
                    "ambiente": ambiente,
                    "status": resultado.get("status", "ERRO"),
                    "protocolo": resultado.get("nProt", resultado.get("protocolo", "")),
                    "cStat": resultado.get("cStat", ""),
                    "xMotivo": resultado.get("xMotivo", ""),
                    "xml": xml_envi,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                nfe_data["nfe"] = notas
                save_json(nfe_path, nfe_data)

                return self._json({"status": "ok", "resultado": resultado, "numero": numero, "chave": resultado.get("chave", "")})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfe/consultar":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                chave = body.get("chave", "")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                uf = body.get("uf", "RS")
                if not chave or not cert_id:
                    return self._json({"status": "error", "message": "chave e cert_id são obrigatórios"}, 400)
                resultado = sefaz_service.consultar_nfe(chave, uf, ambiente, cert_id, cert_senha)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfe/cancelar":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                chave = body.get("chave", "")
                protocolo = body.get("protocolo", "")
                justificativa = body.get("justificativa", "Cancelamento manual")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                uf = body.get("uf", "RS")
                if not chave or not protocolo or not cert_id:
                    return self._json({"status": "error", "message": "chave, protocolo e cert_id são obrigatórios"}, 400)
                resultado = sefaz_service.cancelar_nfe(chave, protocolo, uf, ambiente, cert_id, cert_senha, justificativa=justificativa)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfe/preview-xml":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                venda_id = body.get("venda_id", "")
                ambiente = int(body.get("ambiente", 2))
                serie = int(body.get("serie", 1))
                numero = int(body.get("numero", 1))
                vendas = load_json(os.path.join(BASE_DIR, "dados", "vendas.json"))
                venda = next((v for v in vendas.get("vendas", []) if str(v.get("id")) == str(venda_id)), {})
                empresa = load_empresa_fiscal()
                xml = nfe_xml.montar_envi_nfe(venda, empresa, ambiente, serie, numero, sincrono=True)
                return self._json({"status": "ok", "xml": xml})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfe/inutilizar":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                cnpj = body.get("cnpj", "")
                serie = int(body.get("serie", 1))
                nnf_ini = int(body.get("nnf_ini", 0))
                nnf_fim = int(body.get("nnf_fim", 0))
                justificativa = body.get("justificativa", "Inutilização")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                uf = body.get("uf", "RS")
                if not cnpj or not cert_id:
                    return self._json({"status": "error", "message": "cnpj e cert_id são obrigatórios"}, 400)
                resultado = sefaz_service.inutilizar_nfe(cnpj, uf, ambiente, serie, nnf_ini, nnf_fim, cert_id, cert_senha, justificativa)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── Fiscal: NFS-e ──
        if parsed.path == "/api/admin/fiscal/nfse/autorizar":
            if not self._has_permission(crud_token, "nfse"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                numero = int(body.get("numero", 0))

                if not cert_id:
                    return self._json({"status": "error", "message": "cert_id é obrigatório"}, 400)

                empresa = load_empresa_fiscal()
                cod_mun = str(empresa.get("cod_municipio", nfse_service.DEFAULT_CIDADE))
                nota = {
                    "cliente": body.get("cliente", "Tomador"),
                    "documento": body.get("documento", ""),
                    "descricao": body.get("descricao", "Serviços prestados"),
                    "total": float(body.get("total", 0)),
                    "itens": body.get("itens", []),
                    "cod_tributacao": body.get("cod_tributacao", ""),
                    "item_lista": body.get("item_lista", "01.01"),
                }

                xml_nfse = nfse_xml.montar_nfse(nota, empresa, ambiente, 1, numero)
                resultado = nfse_service.autorizar_nfse(xml_nfse, cod_mun, ambiente, cert_id, cert_senha)

                nfse_path = os.path.join(BASE_DIR, "dados", "nfse.json")
                nfse_data = load_json(nfse_path)
                notas = nfse_data.get("nfse", [])
                notas.append({
                    "numero": numero,
                    "serie": 1,
                    "ambiente": ambiente,
                    "cliente": nota["cliente"],
                    "total": nota["total"],
                    "status": resultado.get("status", "ERRO"),
                    "xml": xml_nfse,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                nfse_data["nfse"] = notas
                save_json(nfse_path, nfse_data)

                return self._json({"status": "ok", "resultado": resultado, "numero": numero})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── CT-e CRUD (COBOL) ──
        if parsed.path == "/api/admin/fiscal/cte":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                action = body.get("action", "incluir")
                if action == "incluir":
                    pid = cobol_bridge.cte_incluir(body)
                    return self._json({"status": "ok", "id": pid})
                elif action == "alterar":
                    ok = cobol_bridge.cte_alterar(body.get("id"), body)
                    return self._json({"status": "ok" if ok else "error", "message": "Atualizado" if ok else "Falha"})
                elif action == "excluir":
                    ok = cobol_bridge.cte_excluir(body.get("id"))
                    return self._json({"status": "ok" if ok else "error", "message": "Excluido" if ok else "Nao encontrado"})
                return self._json({"status": "error", "message": "Acao invalida"}, 400)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── MDF-e CRUD (COBOL) ──
        if parsed.path == "/api/admin/fiscal/mdfe":
            if not self._has_permission(crud_token, "nfe"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                action = body.get("action", "incluir")
                if action == "incluir":
                    pid = cobol_bridge.mdfe_incluir(body)
                    return self._json({"status": "ok", "id": pid})
                elif action == "alterar":
                    ok = cobol_bridge.mdfe_alterar(body.get("id"), body)
                    return self._json({"status": "ok" if ok else "error", "message": "Atualizado" if ok else "Falha"})
                elif action == "excluir":
                    ok = cobol_bridge.mdfe_excluir(body.get("id"))
                    return self._json({"status": "ok" if ok else "error", "message": "Excluido" if ok else "Nao encontrado"})
                return self._json({"status": "error", "message": "Acao invalida"}, 400)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if parsed.path == "/api/admin/fiscal/nfse/consultar":
            if not self._has_permission(crud_token, "nfse"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            try:
                numero_rps = body.get("numero_rps", "")
                cert_id = body.get("cert_id", "")
                cert_senha = body.get("cert_senha", "")
                ambiente = int(body.get("ambiente", 2))
                empresa = load_empresa_fiscal()
                cod_mun = str(empresa.get("cod_municipio", nfse_service.DEFAULT_CIDADE))
                resultado = nfse_service.consultar_nfse(numero_rps, cod_mun, ambiente, cert_id, cert_senha)
                return self._json({"status": "ok", "resultado": resultado})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── DANFE ──
        modelo = body.get("modelo", "65")

        if parsed.path == "/api/admin/fiscal/danfe":
            token = self.headers.get("X-Auth-Token", "")
            permission = "nfe" if modelo == "55" else "nfce"
            if not self._has_permission(token, permission):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            chave = body.get("chave", "")
            if not chave:
                return self._json({"status": "error", "message": "chave é obrigatória"}, 400)

            if modelo == "55":
                nf_data = load_json(os.path.join(BASE_DIR, "dados", "nfe.json"))
                nota = next((n for n in nf_data.get("nfe", []) if n.get("chave") == chave), None)
                if not nota:
                    return self._json({"status": "error", "message": "NF-e não encontrada"}, 404)
            else:
                nf_data = load_json(os.path.join(BASE_DIR, "dados", "nfce.json"))
                nota = next((n for n in nf_data.get("nfce", []) if n.get("chave") == chave), None)
                if not nota:
                    return self._json({"status": "error", "message": "NFC-e não encontrada"}, 404)

            empresa = load_empresa_fiscal()
            try:
                pdf_bytes = danfe.gerar(nota, empresa, modelo=modelo)
                nome_arq = f"DANFE-{'NFe' if modelo=='55' else 'NFCe'}-{chave}.pdf"
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f'attachment; filename="{nome_arq}"')
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(pdf_bytes)
                return None
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        # ── CRUD Genérico: Categorias, Marcas, Fabricantes, Contatos, Partners (JSON) ──
        for cfg in [self._crud_categorias, self._crud_marcas, self._crud_fabricantes, self._crud_contatos, self._crud_partners]:
            result = cfg(parsed.path, body, crud_token)
            if result is not None:
                return result

        # ── RH: Funcionários / Dependentes / Filiais (CRUD COBOL) ──
        if parsed.path == "/api/filial/incluir":
            try:
                fbody = self._form_body(raw) or {}
                fid = cobol_bridge.filiais_incluir(fbody)
                return self._json({"status": "ok", "id": fid, "message": "Filial criada"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/filial/alterar":
            try:
                fbody = self._form_body(raw) or {}
                fid = fbody.get("id")
                if fid in (None, ""):
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                ok = cobol_bridge.filiais_alterar(fid, fbody)
                if ok:
                    return self._json({"status": "ok", "message": "Filial atualizada"})
                return self._json({"status": "error", "message": "Filial não encontrada"}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/filial/excluir":
            try:
                fbody = self._form_body(raw) or {}
                fid = fbody.get("id")
                if fid in (None, ""):
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                ok = cobol_bridge.filiais_excluir(fid)
                if ok:
                    return self._json({"status": "ok", "message": "Filial excluída"})
                return self._json({"status": "error", "message": "Filial não encontrada"}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/departamento/incluir":
            try:
                fbody = self._form_body(raw) or {}
                did = cobol_bridge.departamento_incluir(fbody)
                return self._json({"status": "ok", "id": did, "message": "Departamento criado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/departamento/alterar":
            try:
                fbody = self._form_body(raw) or {}
                did = fbody.get("id")
                if did in (None, ""):
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                ok = cobol_bridge.departamento_alterar(did, fbody)
                if ok:
                    return self._json({"status": "ok", "message": "Departamento atualizado"})
                return self._json({"status": "error", "message": "Departamento não encontrado"}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/departamento/excluir":
            try:
                fbody = self._form_body(raw) or {}
                did = fbody.get("id")
                if did in (None, ""):
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                ok = cobol_bridge.departamento_excluir(did)
                if ok:
                    return self._json({"status": "ok", "message": "Departamento inativado"})
                return self._json({"status": "error", "message": "Departamento não encontrado"}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/cargo/incluir":
            try:
                fbody = self._form_body(raw) or {}
                cid = cobol_bridge.cargo_incluir(fbody)
                return self._json({"status": "ok", "id": cid, "message": "Cargo criado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/cargo/alterar":
            try:
                fbody = self._form_body(raw) or {}
                cid = fbody.get("id")
                if cid in (None, ""):
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                ok = cobol_bridge.cargo_alterar(cid, fbody)
                if ok:
                    return self._json({"status": "ok", "message": "Cargo atualizado"})
                return self._json({"status": "error", "message": "Cargo não encontrado"}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/cargo/excluir":
            try:
                fbody = self._form_body(raw) or {}
                cid = fbody.get("id")
                if cid in (None, ""):
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                ok = cobol_bridge.cargo_excluir(cid)
                if ok:
                    return self._json({"status": "ok", "message": "Cargo inativado"})
                return self._json({"status": "error", "message": "Cargo não encontrado"}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path in (
            "/api/evento/incluir",
            "/api/evento/alterar",
            "/api/evento/excluir",
            "/api/eventos/seed",
        ):
            token = self.headers.get("X-Auth-Token", "")
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") not in ("admin", "instrutor"):
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            # do_POST parseia JSON no topo; fallback form-urlencoded (padrão RFC-003)
            fbody = dict(body or {})
            if "x-www-form-urlencoded" in self.headers.get("Content-Type", ""):
                qs = urllib.parse.parse_qs(raw)
                fbody = {k: v[0] for k, v in qs.items()}
            try:
                if parsed.path == "/api/evento/incluir":
                    eid = cobol_bridge.evento_incluir(fbody)
                    return self._json({"status": "ok", "id": eid, "message": "Evento criado"})
                if parsed.path == "/api/evento/alterar":
                    eid = fbody.get("id")
                    if eid in (None, ""):
                        return self._json({"status": "error", "message": "ID do evento obrigatorio"}, 400)
                    ok = cobol_bridge.evento_alterar(eid, fbody)
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Evento atualizado" if ok else "Nao encontrado"})
                if parsed.path == "/api/evento/excluir":
                    eid = fbody.get("id")
                    if eid in (None, ""):
                        return self._json({"status": "error", "message": "ID do evento obrigatorio"}, 400)
                    ok = cobol_bridge.evento_excluir(eid)
                    return self._json({"status": "ok" if ok else "error",
                                       "message": "Evento inativado" if ok else "Nao encontrado"})
                if parsed.path == "/api/eventos/seed":
                    criados = cobol_bridge.eventos_seed_catalogo()
                    return self._json({"status": "ok", "criados": criados,
                                       "message": f"{len(criados)} eventos do catalogo criados"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/funcionario/incluir":
            try:
                fbody = self._form_body(raw) or {}
                fid = cobol_bridge.funcionario_incluir(fbody)
                return self._json({"status": "ok", "id": fid, "message": "Funcionário criado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/funcionario/alterar":
            try:
                fbody = self._form_body(raw) or {}
                fid = fbody.get("id")
                if fid in (None, ""):
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                ok = cobol_bridge.funcionario_alterar(fid, fbody)
                if ok:
                    return self._json({"status": "ok", "message": "Funcionário atualizado"})
                return self._json({"status": "error", "message": "Funcionário não encontrado"}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/funcionario/excluir":
            try:
                fbody = self._form_body(raw) or {}
                fid = fbody.get("id")
                if fid in (None, ""):
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                ok = cobol_bridge.funcionario_excluir(fid)
                if ok:
                    return self._json({"status": "ok", "message": "Funcionário excluído"})
                return self._json({"status": "error", "message": "Funcionário não encontrado"}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/funcionario/upload":
            try:
                import base64
                up = json.loads(raw) if raw else {}
                data_b64 = up.get("data") or ""
                ext = (up.get("ext") or "jpg").lower()
                fname = uuid.uuid4().hex + "." + ext
                up_dir = os.path.join(BASE_DIR, "uploads", "funcionarios")
                os.makedirs(up_dir, exist_ok=True)
                payload = base64.b64decode(data_b64) if data_b64 else b""
                if not payload:
                    return self._json({"status": "error", "message": "Dados vazios"}, 400)
                with open(os.path.join(up_dir, fname), "wb") as f:
                    f.write(payload)
                url = "/uploads/funcionarios/" + fname
                return self._json({"status": "ok", "filename": fname, "url": url,
                                   "message": "Arquivo enviado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/dependente/incluir":
            try:
                fbody = self._form_body(raw) or {}
                did = cobol_bridge.dependente_incluir(fbody)
                return self._json({"status": "ok", "id": did, "message": "Dependente criado"})
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/dependente/alterar":
            try:
                fbody = self._form_body(raw) or {}
                did = fbody.get("id")
                if did in (None, ""):
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                ok = cobol_bridge.dependente_alterar(did, fbody)
                if ok:
                    return self._json({"status": "ok", "message": "Dependente atualizado"})
                return self._json({"status": "error", "message": "Dependente não encontrado"}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        if parsed.path == "/api/dependente/excluir":
            try:
                fbody = self._form_body(raw) or {}
                did = fbody.get("id")
                if did in (None, ""):
                    return self._json({"status": "error", "message": "id é obrigatório"}, 400)
                ok = cobol_bridge.dependente_excluir(did)
                if ok:
                    return self._json({"status": "ok", "message": "Dependente excluído"})
                return self._json({"status": "error", "message": "Dependente não encontrado"}, 404)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 400)

        return self._json({"status": "error", "message": "Not found"}, 404)

    def do_PUT(self):
        self.do_POST()

    # ── CRUD Genérico ──

    def _crud_config(self, prefix, data_file, schema, list_key):
        """Retorna (GET_list, POST_create, POST_item) handlers."""
        import copy
        def get_list(token):
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            data = load_json(data_file)
            lista = []
            for eid, e in data.items():
                item = dict(e)
                item["id"] = eid
                lista.append(item)
            return self._json({"status": "ok", list_key: lista})

        def create(token, body):
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            entry = {}
            for field, default in schema.items():
                if field.startswith("_"):
                    continue
                val = body.get(field)
                if val is not None:
                    entry[field] = val if not isinstance(default, bool) else val
                else:
                    entry[field] = copy.deepcopy(default) if isinstance(default, (list, dict)) else default
            if not entry.get(schema.get("_required", "nome")):
                return self._json({"status": "error", "message": "Nome é obrigatório"}, 400)
            data = load_json(data_file)
            eid = str(uuid.uuid4())[:8]
            data[eid] = entry
            save_json(data_file, data)
            return self._json({"status": "ok", "id": eid, "message": "Criado com sucesso"})

        def item_action(token, eid, body):
            users = load_users()
            current = self._find_user(token, users)
            if not current or current.get("role") != "admin":
                return self._json({"status": "error", "message": "Acesso negado"}, 403)
            data = load_json(data_file)
            if eid not in data:
                return self._json({"status": "error", "message": "Não encontrado"}, 404)
            if body.get("action") == "toggle":
                data[eid]["ativo"] = not data[eid].get("ativo", True)
                save_json(data_file, data)
                return self._json({"status": "ok", "ativo": data[eid]["ativo"]})
            if body.get("action") == "update":
                for field in schema:
                    if field.startswith("_"):
                        continue
                    val = body.get(field)
                    if val is not None:
                        data[eid][field] = val
                save_json(data_file, data)
                return self._json({"status": "ok", "message": "Atualizado com sucesso"})
            return self._json({"status": "error", "message": "Ação inválida"}, 400)

        return get_list, create, item_action

    def _handle_crud(self, path, body, token, prefix, data_file, schema, list_key):
        get_list, create, item_action = self._crud_config(prefix, data_file, schema, list_key)
        if path == prefix:
            if self.command == "GET":
                return get_list(token)
            return create(token, body)
        if path.startswith(prefix + "/"):
            eid = path.split("/")[-1]
            return item_action(token, eid, body)
        return None

    _CRUD_SCHEMAS = {
        "categorias": {
            "_required": "nome",
            "nome": "", "descricao": "", "ativo": True
        },
        "marcas": {
            "_required": "nome",
            "nome": "", "descricao": "", "ativo": True
        },
        "fabricantes": {
            "_required": "nome",
            "nome": "", "descricao": "", "ativo": True
        },
        "contatos": {
            "_required": "nome",
            "nome": "", "nome_fantasia": "", "tipo": "cliente", "pessoa": "PJ",
            "documento": "", "ie": "", "im": "",
            "telefone": "", "email": "",
            "cep": "", "endereco": "", "numero": "", "bairro": "",
            "cidade": "", "uf": "",
            "regime": "SN", "contribuinte_icms": "1",
            "observacao": "", "ativo": True
        },
        "partners": {
            "_required": "legal_name",
            "partner_code": "",
            "person_type": "COMPANY",
            "display_name": "",
            "legal_name": "",
            "trade_name": "",
            "status": "ACTIVE",
            "roles": [],
            "documents": [],
            "addresses": [],
            "contacts": [],
            "bank_accounts": [],
            "default_price_list_id": "",
            "credit_limit": 0,
            "payment_terms": "30",
            "credit_blocked": False,
            "regime": "SN",
            "contribuinte_icms": "1",
            "observacao": "",
            "ativo": True
        }
    }

    def _crud_categorias(self, path, body, token):
        return self._handle_crud(path, body, token, "/api/admin/categorias",
            CATEGORIAS_FILE, self._CRUD_SCHEMAS["categorias"], "categorias")

    def _crud_marcas(self, path, body, token):
        return self._handle_crud(path, body, token, "/api/admin/marcas",
            MARCAS_FILE, self._CRUD_SCHEMAS["marcas"], "marcas")

    def _crud_fabricantes(self, path, body, token):
        return self._handle_crud(path, body, token, "/api/admin/fabricantes",
            FABRICANTES_FILE, self._CRUD_SCHEMAS["fabricantes"], "fabricantes")

    def _crud_contatos(self, path, body, token):
        return self._handle_crud(path, body, token, "/api/admin/contatos",
            CONTATOS_FILE, self._CRUD_SCHEMAS["contatos"], "contatos")

    def _crud_partners(self, path, body, token):
        """CRUD parceiros — fonte COBOL (partners_store)."""
        prefix = "/api/admin/partners"
        if not path.startswith(prefix):
            return None
        users = load_users()
        current = self._find_user(token, users)
        if not current or current.get("role") != "admin":
            return self._json({"status": "error", "message": "Acesso negado"}, 403)

        if path == prefix and self.command == "GET":
            data = partners_store.as_dict()
            lista = []
            for eid, e in data.items():
                item = dict(e)
                item["id"] = eid
                lista.append(item)
            return self._json({"status": "ok", "partners": lista, "source": "cobol"})

        if path == prefix and self.command == "POST":
            body = dict(body or {})
            if not (body.get("partner_code") or "").strip():
                n = len(partners_store.as_dict()) + 1
                body["partner_code"] = f"BP{n:09d}"
            if not (body.get("display_name") or "").strip():
                body["display_name"] = body.get("trade_name") or body.get("legal_name") or ""
            if body.get("ativo") is False:
                body["status"] = "INACTIVE"
            elif not body.get("status"):
                body["status"] = "ACTIVE"
            if not body.get("roles"):
                body["roles"] = ["CUSTOMER"]
            if not body.get("legal_name"):
                return self._json({"status": "error", "message": "legal_name é obrigatório"}, 400)
            try:
                saved = partners_store.save(body, is_new=True)
                return self._json({
                    "status": "ok", "id": saved.get("id"),
                    "message": "Criado com sucesso", "partner": saved,
                })
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if path.startswith(prefix + "/"):
            eid = path.rstrip("/").split("/")[-1]
            existing = partners_store.get(eid)
            if not existing:
                return self._json({"status": "error", "message": "Não encontrado"}, 404)
            action = (body or {}).get("action") or "update"
            if action == "toggle":
                existing["ativo"] = not existing.get("ativo", True)
                existing["status"] = "ACTIVE" if existing["ativo"] else "INACTIVE"
                try:
                    saved = partners_store.save(existing, partner_id=eid)
                    return self._json({"status": "ok", "ativo": saved.get("ativo")})
                except Exception as e:
                    return self._json({"status": "error", "message": str(e)}, 500)
            if action in ("update", "delete") or self.command in ("PUT", "POST"):
                if action == "delete" or (body or {}).get("action") == "delete":
                    try:
                        partners_store.delete(eid)
                        return self._json({"status": "ok", "message": "Excluído"})
                    except Exception as e:
                        return self._json({"status": "error", "message": str(e)}, 500)
                for field in self._CRUD_SCHEMAS["partners"]:
                    if field.startswith("_"):
                        continue
                    if field in (body or {}) and body[field] is not None:
                        existing[field] = body[field]
                try:
                    partners_store.save(existing, partner_id=eid)
                    return self._json({"status": "ok", "message": "Atualizado com sucesso"})
                except Exception as e:
                    return self._json({"status": "error", "message": str(e)}, 500)
            return self._json({"status": "error", "message": "Ação inválida"}, 400)
        return None

    def _find_user(self, token, users):
        if not token:
            return None
        for u in users.values():
            if u.get("token") == token:
                return u
        return None

    def _vendas_b2b_post(self, body, token):
        users = load_users()
        user = self._find_user(token, users)
        if not user:
            return self._json({"status": "error", "message": "Não autenticado"}, 401)
        pedidos = _load_pedidos_b2b()
        action = str((body or {}).get("action") or "create").lower()

        if action == "create":
            tipo = "cotacao" if (body or {}).get("tipo") == "cotacao" else "pedido"
            novo = dict(body or {})
            novo.pop("id", None)
            novo.pop("action", None)
            if not (novo.get("numero") or "").strip():
                prefix = "S" if tipo == "cotacao" else "PV"
                same = [p for p in pedidos
                        if p.get("tipo") == tipo or (not p.get("tipo") and tipo == "pedido")]
                novo["numero"] = prefix + str(len(same) + 1).zfill(5)
            novo.setdefault("tipo", tipo)
            novo.setdefault("status", "rascunho")
            novo.setdefault("data", datetime.now().strftime("%Y-%m-%d"))
            novo.setdefault("itens", [])
            novo.setdefault("smart", {"entregas": 0, "faturas": 0, "compras": 0,
                                      "assinaturas": 0, "projetos": 0, "tarefas": 0})
            _b2b_apply_server_prices(novo)
            try:
                saved = pedidos_b2b_store.save(novo, is_new=True)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)
            return self._json({"status": "ok", "id": saved["id"], "numero": saved.get("numero"),
                               "pedido": saved,
                               "message": "Criado com sucesso"})

        pid = (body or {}).get("id")
        if pid is None:
            return self._json({"status": "error", "message": "id é obrigatório"}, 400)
        target = next((p for p in pedidos if str(p.get("id")) == str(pid)), None)
        if not target:
            return self._json({"status": "error", "message": "Não encontrado"}, 404)

        if action == "update":
            if target.get("status") in _B2B_LOCKED:
                return self._json({"status": "error",
                                   "message": f"Documento {target.get('status')} — edição bloqueada"}, 400)
            for k, v in (body or {}).items():
                if k in ("action", "id"):
                    continue
                if v is not None:
                    target[k] = v
            _b2b_apply_server_prices(target)
            try:
                target = _save_pedidos_b2b(pedidos, changed=target) or target
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)
            return self._json({"status": "ok", "id": target["id"], "pedido": target,
                               "message": "Atualizado"})

        if action == "status":
            novo_status = (body or {}).get("status")
            if not novo_status:
                return self._json({"status": "error", "message": "status é obrigatório"}, 400)
            atual = target.get("status") or "rascunho"
            if novo_status != atual and novo_status not in _B2B_FLOW.get(atual, set()):
                return self._json({"status": "error",
                                   "message": f"Transição inválida: {atual} → {novo_status}"}, 400)
            if target.get("tipo") != "cotacao" and novo_status in ("pendente", "aprovado"):
                if not _b2b_cnpj_valido(target.get("cnpj")):
                    return self._json({"status": "error",
                                       "message": "Pedido B2B requer CNPJ válido (14 dígitos)"}, 400)
            if novo_status in ("pendente", "aprovado") and target.get("tipo") != "cotacao":
                derr = _b2b_check_discount(target, user, body)
                if derr:
                    return self._json(derr, 400)
            extras = {}
            if novo_status == "aprovado" and target.get("tipo") != "cotacao":
                err, extras = self._b2b_approve_side_effects(target, user, body)
                if err:
                    return self._json(err, 400)
            target["status"] = novo_status
            if novo_status == "cancelado":
                sales_reservation.release_for_order(target.get("id"), motivo="cancelled")
                target.pop("reserva_id", None)
            try:
                target = _save_pedidos_b2b(pedidos, changed=target) or target
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)
            return self._json({
                "status": "ok", "id": target["id"], "doc_status": novo_status,
                **extras, "message": "Status atualizado",
            })

        if action == "aprovar":
            atual = target.get("status") or "rascunho"
            if atual not in ("rascunho", "pendente"):
                return self._json({"status": "error",
                                   "message": f"Aprovação requer status rascunho/pendente (atual: {atual})"}, 400)
            if target.get("tipo") != "cotacao" and not _b2b_cnpj_valido(target.get("cnpj")):
                return self._json({"status": "error",
                                   "message": "Pedido B2B requer CNPJ válido (14 dígitos)"}, 400)
            if not target.get("itens"):
                return self._json({"status": "error", "message": "Adicione ao menos uma linha ao pedido"}, 400)
            if target.get("tipo") != "cotacao":
                derr = _b2b_check_discount(target, user, body)
                if derr:
                    return self._json(derr, 400)
            extras = {}
            if target.get("tipo") != "cotacao":
                err, extras = self._b2b_approve_side_effects(target, user, body)
                if err:
                    return self._json(err, 400)
            target["status"] = "aprovado"
            try:
                target = _save_pedidos_b2b(pedidos, changed=target) or target
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)
            return self._json({
                "status": "ok", "id": target["id"], "doc_status": "aprovado",
                **extras, "message": "Pedido aprovado",
            })
        if action == "converter":
            return self._b2b_converter_cotacao(pedidos, target, user, body)
        if action == "faturar":
            atual = target.get("status") or "rascunho"
            if atual != "aprovado":
                return self._json({"status": "error",
                                   "message": f"Faturamento requer status aprovado (atual: {atual})"}, 400)
            return self._b2b_faturar(pedidos, target, body)

        if action == "autorizar_nfe":
            try:
                payload = dict(body or {})
                payload.setdefault("pedido_b2b_id", pid)
                if target.get("nfe_numero"):
                    payload.setdefault("numero", target.get("nfe_numero"))
                out = _b2b_autorizar_nfe(payload)
                target2 = pedidos_b2b_store.get(pid) or target
                return self._json({
                    "status": "ok",
                    "pedido": target2,
                    **out,
                    "message": f"NF-e {(out.get('nfe') or {}).get('status') or 'processada'}",
                })
            except ValueError as e:
                return self._json({"status": "error", "message": str(e)}, 400)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)

        if action == "delete":
            if target.get("status") == "faturado":
                return self._json({"status": "error", "message": "Pedido faturado não pode ser excluído"}, 400)
            sales_reservation.release_for_order(pid, motivo="deleted")
            try:
                pedidos_b2b_store.delete(pid)
            except Exception as e:
                return self._json({"status": "error", "message": str(e)}, 500)
            return self._json({"status": "ok", "message": "Excluído"})
        return self._json({"status": "error", "message": "Ação inválida"}, 400)
    def _has_permission(self, token, permission):
        users = load_users()
        user = self._find_user(token, users)
        if not user:
            return False
        role = user.get("role", "")
        if role == "admin":
            return True
        perms = ROLES.get(role, {}).get("permissoes", [])
        return permission in perms

    def _b2b_approve_side_effects(self, target, user, body=None):
        """Crédito + reserva + handoff Delivery. Falha aborta aprovação (com rollback)."""
        body = body or {}
        uname = (user or {}).get("usuario") or (user or {}).get("nome") or ""
        role = str((user or {}).get("role") or "").lower()
        valor = float(sales_finance.pedido_total(target))
        credit = sales_finance.check_credit(
            target.get("cliente_id"),
            valor,
            exclude_pedido_id=target.get("id"),
        )
        force = bool(body.get("force_credit")) and role in ("admin", "gerente")
        if not credit.get("ok") and not force:
            return ({
                "status": "error",
                "code": "credito",
                "message": credit.get("message") or "Crédito insuficiente",
                "credit": credit,
            }, {})
        target["credit_check"] = credit
        if force and not credit.get("ok"):
            target["credit_forced_by"] = uname
        if not target.get("payment_terms"):
            cfg = sales_finance.partner_credit(target.get("cliente_id"))
            target["payment_terms"] = cfg.get("payment_terms") or "30"

        allow_partial = bool(body.get("allow_partial"))
        reserva = None
        try:
            reserva = sales_reservation.reserve_for_order(
                target, usuario=uname, allow_partial=allow_partial,
            )
            target["reserva_id"] = reserva.get("id")
            target["reserva_warnings"] = reserva.get("warnings") or []
            target["reserva_parcial"] = bool(reserva.get("parcial"))
        except Exception as e:
            code = getattr(e, "code", None) or "reserva"
            return ({
                "status": "error",
                "code": code,
                "message": str(e),
                "warnings": getattr(e, "warnings", None) or [str(e)],
                "shortfalls": getattr(e, "shortfalls", None) or [],
                "credit": credit,
            }, {})

        entrega = None
        try:
            entrega = delivery_orders.create_from_pedido_b2b(target, usuario=uname)
            target["entrega_id"] = entrega.get("id")
            smart = target.setdefault("smart", {})
            smart["entregas"] = max(int(smart.get("entregas") or 0), 1)
            target.pop("entrega_error", None)
        except Exception as e:
            # rollback reserva se DO falhar
            try:
                sales_reservation.release_for_order(target.get("id"), motivo="rollback_do")
            except Exception:
                pass
            target.pop("reserva_id", None)
            return ({
                "status": "error",
                "code": "entrega",
                "message": f"Falha ao gerar Delivery Order: {e}",
                "credit": credit,
                "reserva": reserva,
            }, {})

        return None, {
            "credit": credit,
            "reserva": reserva,
            "entrega": entrega,
        }

    def _b2b_converter_cotacao(self, pedidos, target, user, body=None):
        """Cotação → novo Pedido de Venda (herda linhas/preços/cliente)."""
        if target.get("tipo") != "cotacao":
            return self._json({"status": "error", "message": "Apenas cotações podem ser convertidas"}, 400)
        st = target.get("status") or "rascunho"
        if st in ("convertida", "cancelado", "faturado"):
            return self._json({"status": "error",
                               "message": f"Cotação {st} não pode ser convertida"}, 400)
        if target.get("pedido_gerado_id"):
            return self._json({
                "status": "error",
                "message": f"Já convertida no pedido {target.get('pedido_gerado_id')}",
                "pedido_id": target.get("pedido_gerado_id"),
            }, 400)
        if not target.get("itens"):
            return self._json({"status": "error", "message": "Cotação sem linhas"}, 400)

        same = [p for p in pedidos if p.get("tipo") == "pedido" or not p.get("tipo")]
        pedido = {
            "tipo": "pedido",
            "numero": "PV" + str(len(same) + 1).zfill(5),
            "status": "rascunho",
            "data": datetime.now().strftime("%Y-%m-%d"),
            "validade": target.get("validade") or "",
            "cliente_id": target.get("cliente_id") or "",
            "cliente_nome": target.get("cliente_nome") or "",
            "razao_social": target.get("razao_social") or "",
            "cnpj": target.get("cnpj") or "",
            "ie": target.get("ie") or "",
            "cidade": target.get("cidade") or "",
            "uf": target.get("uf") or "",
            "endereco_cobranca": target.get("endereco_cobranca") or "",
            "endereco_entrega": target.get("endereco_entrega") or "",
            "lista_precos": target.get("lista_precos") or "",
            "lista_precos_id": target.get("lista_precos_id") or "",
            "payment_terms": target.get("payment_terms") or target.get("condicao_pg") or "30",
            "condicao_pg": target.get("condicao_pg") or "",
            "forma_pg": target.get("forma_pg") or "",
            "vendedor": target.get("vendedor") or "",
            "estabelecimento_id": target.get("estabelecimento_id") or "",
            "notas": (
                (str(target.get("notas") or "").strip() + " · " if target.get("notas") else "")
                + f"origem cotação {target.get('numero') or target.get('id')}"
            )[:80],
            "info_extra": target.get("info_extra") or "",
            "cotacao_origem_id": target.get("id"),
            "cotacao_origem_numero": target.get("numero") or "",
            "itens": [dict(i) for i in (target.get("itens") or [])],
            "smart": {"entregas": 0, "faturas": 0, "compras": 0,
                      "assinaturas": 0, "projetos": 0, "tarefas": 0},
        }
        _b2b_apply_server_prices(pedido)
        try:
            saved = pedidos_b2b_store.save(pedido, is_new=True)
        except Exception as e:
            return self._json({"status": "error", "message": str(e)}, 500)

        target["status"] = "convertida"
        target["pedido_gerado_id"] = saved.get("id")
        target["pedido_gerado_numero"] = saved.get("numero")
        try:
            target = _save_pedidos_b2b(pedidos, changed=target) or target
        except Exception as e:
            return self._json({
                "status": "error",
                "message": f"Pedido {saved.get('numero')} criado, falha ao marcar cotação: {e}",
                "pedido": saved,
            }, 500)

        return self._json({
            "status": "ok",
            "cotacao": target,
            "pedido": saved,
            "pedido_id": saved.get("id"),
            "pedido_numero": saved.get("numero"),
            "message": f"Cotação convertida no pedido {saved.get('numero')}",
        })

    def _b2b_faturar(self, pedidos, target, body):
        """
        Faturamento comercial: FV + AR (+ NF-e rascunho).
        Não baixa estoque nem consome reserva — stock move na DO (depart).
        """
        itens = target.get("itens") or []
        if not itens:
            return self._json({"status": "error", "message": "Adicione ao menos uma linha ao pedido"}, 400)
        if target.get("fatura_id"):
            return self._json({
                "status": "error",
                "message": f"Pedido já faturado ({target.get('fatura_numero')})",
                "fatura_id": target.get("fatura_id"),
            }, 400)

        # DO obrigatória no faturar (handoff se faltar)
        if not target.get("entrega_id"):
            try:
                uname = (body or {}).get("usuario") or ""
                entrega = delivery_orders.create_from_pedido_b2b(target, usuario=uname)
                target["entrega_id"] = entrega.get("id")
                smart = target.setdefault("smart", {})
                smart["entregas"] = max(int(smart.get("entregas") or 0), 1)
            except Exception as e:
                return self._json({
                    "status": "error",
                    "code": "entrega",
                    "message": f"Faturamento exige Delivery Order: {e}",
                }, 400)

        subtotal = 0.0
        impostos = 0.0
        for i in itens:
            qtd = _safe_float(i.get("qtd"), 0)
            preco = _safe_float(i.get("preco"), 0)
            desc = _safe_float(i.get("desconto"), 0)
            line = qtd * preco * (1 - desc / 100)
            subtotal += line
            impostos += line * (_safe_float(i.get("imposto"), 0) / 100)
        subtotal = round(subtotal, 2)
        impostos = round(impostos, 2)
        total = round(subtotal + impostos, 2)

        next_id = faturas_store.max_id() + 1
        fatura = {
            "id": next_id,
            "numero": "FV" + str(next_id).zfill(5),
            "pedido_id": target.get("id"),
            "pedido_numero": target.get("numero"),
            "partner_id": target.get("cliente_id") or "",
            "cliente": target.get("razao_social") or "",
            "cnpj": target.get("cnpj") or "",
            "data_emissao": datetime.now().strftime("%Y-%m-%d"),
            "data_vencimento": target.get("validade") or "",
            "subtotal": subtotal,
            "impostos": impostos,
            "total": total,
            "status": "PENDENTE",
            "itens_count": len(itens),
            "entrega_id": target.get("entrega_id"),
        }

        # AR é obrigatório — se falhar, não marca faturado / não grava fatura
        try:
            ar_info = sales_finance.create_from_invoice(
                target, fatura,
                usuario=(body or {}).get("usuario") or "",
            )
        except Exception as e:
            return self._json({
                "status": "error",
                "code": "ar",
                "message": f"Falha ao gerar Contas a Receber: {e}",
            }, 400)

        tids = [t.get("id") for t in (ar_info.get("titulos") or [])]
        fatura["ar_titulos"] = tids
        try:
            fatura = faturas_store.save(fatura, is_new=True)
        except Exception as e:
            return self._json({
                "status": "error",
                "code": "fatura",
                "message": f"AR ok, falha ao gravar fatura COBOL: {e}",
                "ar": ar_info,
            }, 500)
        fid = fatura.get("id")

        target["status"] = "faturado"
        target["fatura_id"] = fid
        target["fatura_numero"] = fatura.get("numero")
        target["ar_titulos"] = tids
        smart = target.setdefault("smart", {})
        smart["faturas"] = max(int(smart.get("faturas") or 0), 1)

        # NF-e 55 rascunho — best-effort (não desfaz fatura/AR)
        nfe_info = None
        try:
            nfe_info = _b2b_criar_nfe_rascunho(target, fatura, total)
            if nfe_info:
                target["nfe_numero"] = nfe_info.get("numero")
                target["nfe_status"] = nfe_info.get("status")
                fatura["nfe_numero"] = nfe_info.get("numero")
                fatura["nfe_status"] = nfe_info.get("status")
                fatura["ar_titulos"] = tids
                try:
                    fatura = faturas_store.save(fatura, is_new=False)
                except Exception:
                    pass
        except Exception as e:
            nfe_info = {"status": "erro", "message": str(e)}

        # Gera WMS picking/packing/expedição a partir do pedido faturado
        wms_info = None
        try:
            wms_info = wms_sales_bridge.create_wms_from_pedido(target, usuario=(body or {}).get("usuario") or "")
        except Exception as e:
            wms_info = {"error": str(e)}

        try:
            target = _save_pedidos_b2b(pedidos, changed=target) or target
        except Exception as e:
            return self._json({
                "status": "error",
                "message": f"AR/fatura ok, falha ao gravar pedido: {e}",
                "fatura_id": fid,
                "ar": ar_info,
            }, 500)

        return self._json({
            "status": "ok",
            "fatura_id": fid,
            "fatura_numero": fatura.get("numero"),
            "total": total,
            "nfe": nfe_info,
            "ar": ar_info,
            "entrega_id": target.get("entrega_id"),
            "wms": wms_info,
            "estoque": "na_entrega",
            "source": "cobol:faturas_venda.dat",
            "message": "Fatura e AR criados — estoque será baixado na saída da entrega",
        })

    def _is_admin(self, token):
        return self._has_permission(token, "admin")

    def _user_role(self, token):
        user = self._find_user(token, load_users())
        if not user:
            return ""
        return str(user.get("role") or "").lower()

    def _can_write_planocontas(self, token):
        return self._user_role(token) in PLAN_CONTAS_WRITE_ROLES

    def _can_delete_planocontas(self, token):
        """Exclusão: responsável contábil/fiscal (termo técnico)."""
        return self._user_role(token) in PLAN_CONTAS_DELETE_ROLES

    def _can_write_journals(self, token):
        return self._user_role(token) in JOURNALS_WRITE_ROLES

    def _can_delete_journals(self, token):
        return self._user_role(token) in JOURNALS_DELETE_ROLES

    def _can_write_wms(self, token):
        return self._user_role(token) in WMS_WRITE_ROLES

    def _can_delete_wms(self, token):
        return self._user_role(token) in WMS_DELETE_ROLES

    @staticmethod
    def _get_query_param(query_string: str, key: str, default: str = "") -> str:
        params = urllib.parse.parse_qs(query_string)
        vals = params.get(key, [])
        return vals[0] if vals else default

    def _form_body(self, raw=""):
        """Interpreta o corpo de POST como application/x-www-form-urlencoded (campos únicos)."""
        try:
            if not raw:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode() if length else ""
        except Exception:
            return {}
        if not raw:
            return {}
        params = urllib.parse.parse_qs(raw)
        return {k: (v[0] if v else "") for k, v in params.items()}

    def _empresa_nome(self, empresa_id):
        """Resolve empresa_id numérico (1-based, ordem de data/empresas.json) → nome."""
        try:
            empresas = load_empresas()
        except Exception:
            empresas = {}
        if not isinstance(empresas, dict) or not empresas:
            return ""
        items = list(empresas.items())
        try:
            idx = int(empresa_id or 0) - 1
        except (TypeError, ValueError):
            return ""
        if 0 <= idx < len(items):
            e = items[idx][1] or {}
            return e.get("nome_fantasia") or e.get("nome_razao") or e.get("nome") or items[idx][0]
        return ""

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()

    def log_message(self, fmt, *args):
        try:
            print(f"[SERVER] {fmt % args}")
        except Exception:
            print(f"[SERVER] {fmt} {args}")

def seed_empresas():
    empresas = load_empresas()
    if not empresas:
        empresas["matriz"] = {"nome":"Matriz","cnpj":"00.000.000/0001-00","ie":"123.456.789.000","cidade":"São Paulo","uf":"SP","ativo":True}
        empresas["filial_sp"] = {"nome":"Filial São Paulo","cnpj":"00.000.000/0002-00","ie":"123.456.789.001","cidade":"São Paulo","uf":"SP","ativo":True}
        empresas["filial_rj"] = {"nome":"Filial Rio de Janeiro","cnpj":"00.000.000/0003-00","ie":"123.456.789.002","cidade":"Rio de Janeiro","uf":"RJ","ativo":True}
        save_empresas(empresas)
        print("   ✓ Empresas padrão criadas")

if __name__ == "__main__":
    os.chdir(BASE_DIR)
    seed_empresas()
    server = http.server.ThreadingHTTPServer((HOST, PORT), AuthHandler)
    print(f"✦ BECRP Dev Server")
    print(f"   → Login:  http://localhost:{PORT}/")
    print(f"   → Menu:   http://localhost:{PORT}/index4.html")
    if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) < 10:
        print(f"   ⚠ Nenhum admin. Acesse / para configurar o primeiro usuário.")
    else:
        print(f"   ✓ Admin configurado. Faça login em /")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n Server stopped.")
        server.server_close()
