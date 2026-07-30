"""SEFAZ — Cliente de comunicação com webservices da SEFAZ (NF-e/NFC-e)"""

import base64
import os
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Optional
from lxml import etree
from cryptography.hazmat.primitives import serialization

from modules.certificate import cert_service
from modules.sefaz import nfce_xml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Cache de certificados (memória) ──
_CERT_CACHE = {}

# ── URLs dos webservices SEFAZ NFC-e por UF ──

_PADRAO_AUT = "/ws/NfceAutorizacaoService"
_PADRAO_CONS = "/ws/NfceConsultaService"
_PADRAO_CANC = "/ws/NfceCancelamentoService"

_HOM = "https://hom1.nfce.fazenda.{}.gov.br"
_PROD = "https://nfce.fazenda.{}.gov.br"

# ── URLs dos webservices SEFAZ NF-e (modelo 55) por UF ──
_NFE_PADRAO_AUT = "/ws/NfeAutorizacaoService"
_NFE_PADRAO_CONS = "/ws/NfeConsultaService"
_NFE_PADRAO_CANC = "/ws/NfeCancelamentoService"
_NFE_PADRAO_INUT = "/ws/NfeInutilizacaoService"

_NFE_HOM = "https://hom1.nfe.fazenda.{}.gov.br"
_NFE_PROD = "https://nfe.fazenda.{}.gov.br"

_NFE_EXCECOES = {
    "RS": ("https://hom1.nfe.fazenda.rs.gov.br/ws/NfeAutorizacaoService",
           "https://nfe.fazenda.rs.gov.br/ws/NfeAutorizacaoService",
           "https://hom1.nfe.fazenda.rs.gov.br/ws/NfeConsultaService",
           "https://nfe.fazenda.rs.gov.br/ws/NfeConsultaService",
           "https://hom1.nfe.fazenda.rs.gov.br/ws/NfeCancelamentoService",
           "https://nfe.fazenda.rs.gov.br/ws/NfeCancelamentoService",
           "https://hom1.nfe.fazenda.rs.gov.br/ws/NfeInutilizacaoService",
           "https://nfe.fazenda.rs.gov.br/ws/NfeInutilizacaoService"),
    "MG": ("https://hom1.nfe.fazenda.mg.gov.br/ws/NfeAutorizacaoService",
           "https://nfe.fazenda.mg.gov.br/ws/NfeAutorizacaoService",
           "https://hom1.nfe.fazenda.mg.gov.br/ws/NfeConsultaService",
           "https://nfe.fazenda.mg.gov.br/ws/NfeConsultaService",
           "https://hom1.nfe.fazenda.mg.gov.br/ws/NfeCancelamentoService",
           "https://nfe.fazenda.mg.gov.br/ws/NfeCancelamentoService",
           "https://hom1.nfe.fazenda.mg.gov.br/ws/NfeInutilizacaoService",
           "https://nfe.fazenda.mg.gov.br/ws/NfeInutilizacaoService"),
    "SP": ("https://hom1.nfe.fazenda.sp.gov.br/ws/NfeAutorizacaoService",
           "https://nfe.fazenda.sp.gov.br/ws/NfeAutorizacaoService",
           "https://hom1.nfe.fazenda.sp.gov.br/ws/NfeConsultaService",
           "https://nfe.fazenda.sp.gov.br/ws/NfeConsultaService",
           "https://hom1.nfe.fazenda.sp.gov.br/ws/NfeCancelamentoService",
           "https://nfe.fazenda.sp.gov.br/ws/NfeCancelamentoService",
           "https://hom1.nfe.fazenda.sp.gov.br/ws/NfeInutilizacaoService",
           "https://nfe.fazenda.sp.gov.br/ws/NfeInutilizacaoService"),
}

def _urls(uf):
    return (
        f"{_HOM.format(uf)}{_PADRAO_AUT}",
        f"{_PROD.format(uf)}{_PADRAO_AUT}",
        f"{_HOM.format(uf)}{_PADRAO_CONS}",
        f"{_PROD.format(uf)}{_PADRAO_CONS}",
        f"{_HOM.format(uf)}{_PADRAO_CANC}",
        f"{_PROD.format(uf)}{_PADRAO_CANC}",
    )

# Exceções conhecidas de padrão de URL
_EXCECOES = {
    "RS": ("https://hom1.nfce.fazenda.rs.gov.br/ws/NfceAutorizacaoService",
           "https://nfce.fazenda.rs.gov.br/ws/NfceAutorizacaoService",
           "https://hom1.nfce.fazenda.rs.gov.br/ws/NfceConsultaService",
           "https://nfce.fazenda.rs.gov.br/ws/NfceConsultaService",
           "https://hom1.nfce.fazenda.rs.gov.br/ws/NfceCancelamentoService",
           "https://nfce.fazenda.rs.gov.br/ws/NfceCancelamentoService"),
    "MG": ("https://hom1.nfce.fazenda.mg.gov.br/ws/NfceAutorizacaoService",
           "https://nfce.fazenda.mg.gov.br/ws/NfceAutorizacaoService",
           "https://hom1.nfce.fazenda.mg.gov.br/ws/NfceConsultaService",
           "https://nfce.fazenda.mg.gov.br/ws/NfceConsultaService",
           "https://hom1.nfce.fazenda.mg.gov.br/ws/NfceCancelamentoService",
           "https://nfce.fazenda.mg.gov.br/ws/NfceCancelamentoService"),
    "SP": ("https://hom1.nfce.fazenda.sp.gov.br/ws/NfceAutorizacaoService",
           "https://nfce.fazenda.sp.gov.br/ws/NfceAutorizacaoService",
           "https://hom1.nfce.fazenda.sp.gov.br/ws/NfceConsultaService",
           "https://nfce.fazenda.sp.gov.br/ws/NfceConsultaService",
           "https://hom1.nfce.fazenda.sp.gov.br/ws/NfceCancelamentoService",
           "https://nfce.fazenda.sp.gov.br/ws/NfceCancelamentoService"),
}

SEFAZ_NFCE_AUTORIZACAO = {}
SEFAZ_NFCE_CONSULTA = {}
SEFAZ_NFCE_CANCELAMENTO = {}

TODAS_UFS = [
    "RO","AC","AM","RR","PA","AP","TO","MA","PI","CE","RN","PB","PE","AL",
    "SE","BA","MG","ES","RJ","SP","PR","SC","RS","MS","MT","GO","DF",
]
for uf_sigla in TODAS_UFS:
    if uf_sigla in _EXCECOES:
        ha, pa, hc, pc, hcan, pcan = _EXCECOES[uf_sigla]
    else:
        ha, pa, hc, pc, hcan, pcan = _urls(uf_sigla)
    SEFAZ_NFCE_AUTORIZACAO[uf_sigla] = {"homologacao": ha, "producao": pa}
    SEFAZ_NFCE_CONSULTA[uf_sigla] = {"homologacao": hc, "producao": pc}
    SEFAZ_NFCE_CANCELAMENTO[uf_sigla] = {"homologacao": hcan, "producao": pcan}

SEFAZ_NFE_AUTORIZACAO = {}
SEFAZ_NFE_CONSULTA = {}
SEFAZ_NFE_CANCELAMENTO = {}
SEFAZ_NFE_INUTILIZACAO = {}

for uf_sigla in TODAS_UFS:
    if uf_sigla in _NFE_EXCECOES:
        ha, pa, hc, pc, hcan, pcan, hin, pin = _NFE_EXCECOES[uf_sigla]
    else:
        ha = f"{_NFE_HOM.format(uf_sigla)}{_NFE_PADRAO_AUT}"
        pa = f"{_NFE_PROD.format(uf_sigla)}{_NFE_PADRAO_AUT}"
        hc = f"{_NFE_HOM.format(uf_sigla)}{_NFE_PADRAO_CONS}"
        pc = f"{_NFE_PROD.format(uf_sigla)}{_NFE_PADRAO_CONS}"
        hcan = f"{_NFE_HOM.format(uf_sigla)}{_NFE_PADRAO_CANC}"
        pcan = f"{_NFE_PROD.format(uf_sigla)}{_NFE_PADRAO_CANC}"
        hin = f"{_NFE_HOM.format(uf_sigla)}{_NFE_PADRAO_INUT}"
        pin = f"{_NFE_PROD.format(uf_sigla)}{_NFE_PADRAO_INUT}"
    SEFAZ_NFE_AUTORIZACAO[uf_sigla] = {"homologacao": ha, "producao": pa}
    SEFAZ_NFE_CONSULTA[uf_sigla] = {"homologacao": hc, "producao": pc}
    SEFAZ_NFE_CANCELAMENTO[uf_sigla] = {"homologacao": hcan, "producao": pcan}
    SEFAZ_NFE_INUTILIZACAO[uf_sigla] = {"homologacao": hin, "producao": pin}

CODIGOS_UF = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41,
    "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}


def _nfe_url_autorizacao(uf: str, ambiente: int) -> str:
    dados = SEFAZ_NFE_AUTORIZACAO.get(uf.upper())
    if not dados:
        raise ValueError(f"UF não configurada: {uf}")
    return dados["producao"] if ambiente == 1 else dados["homologacao"]


def _nfe_url_consulta(uf: str, ambiente: int) -> str:
    return SEFAZ_NFE_CONSULTA.get(uf.upper(), SEFAZ_NFE_AUTORIZACAO.get(uf.upper(), {}))\
        .get("producao" if ambiente == 1 else "homologacao", "")


def _nfe_url_cancelamento(uf: str, ambiente: int) -> str:
    return SEFAZ_NFE_CANCELAMENTO.get(uf.upper(), SEFAZ_NFE_AUTORIZACAO.get(uf.upper(), {}))\
        .get("producao" if ambiente == 1 else "homologacao", "")


def _nfe_url_inutilizacao(uf: str, ambiente: int) -> str:
    return SEFAZ_NFE_INUTILIZACAO.get(uf.upper(), SEFAZ_NFE_AUTORIZACAO.get(uf.upper(), {}))\
        .get("producao" if ambiente == 1 else "homologacao", "")


def _url_autorizacao(uf: str, ambiente: int) -> str:
    dados = SEFAZ_NFCE_AUTORIZACAO.get(uf.upper())
    if not dados:
        raise ValueError(f"UF não configurada: {uf}")
    return dados["producao"] if ambiente == 1 else dados["homologacao"]


def _url_consulta(uf: str, ambiente: int) -> str:
    dados = SEFAZ_NFCE_CONSULTA.get(uf.upper())
    if not dados:
        dados = SEFAZ_NFCE_AUTORIZACAO.get(uf.upper())
    if not dados:
        raise ValueError(f"UF não configurada: {uf}")
    return dados["producao"] if ambiente == 1 else dados["homologacao"]


def _url_cancelamento(uf: str, ambiente: int) -> str:
    dados = SEFAZ_NFCE_CANCELAMENTO.get(uf.upper())
    if not dados:
        dados = SEFAZ_NFCE_AUTORIZACAO.get(uf.upper())
    if not dados:
        raise ValueError(f"UF não configurada: {uf}")
    return dados["producao"] if ambiente == 1 else dados["homologacao"]


def _load_cert(cert_id: str, senha: str) -> tuple:
    if cert_id in _CERT_CACHE:
        return _CERT_CACHE[cert_id]

    index = cert_service._load_index()
    if cert_id not in index:
        raise ValueError("Certificado não encontrado")

    info = index[cert_id]
    caminho = os.path.join(cert_service.CERT_DIR, info["arquivo"])
    if not os.path.exists(caminho):
        raise ValueError(f"Arquivo do certificado não encontrado: {caminho}")

    with open(caminho, "rb") as f:
        pfx_data = f.read()

    loaded = cert_service.carregar(pfx_data, senha)
    cert_pem = loaded["cert"].public_bytes(encoding=serialization.Encoding.PEM)
    key_pem = loaded["key"].private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    tmp_dir = os.path.join(BASE_DIR, "dados", "certificados", ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    cert_path = os.path.join(tmp_dir, f"cert_{cert_id}.pem")
    key_path = os.path.join(tmp_dir, f"key_{cert_id}.pem")

    if not os.path.exists(cert_path):
        with open(cert_path, "wb") as f:
            f.write(cert_pem)
    if not os.path.exists(key_path):
        with open(key_path, "wb") as f:
            f.write(key_pem)

    result = (cert_path, key_path, loaded)
    _CERT_CACHE[cert_id] = result
    return result


def _build_soap_envelope(xml_body: str, uf: str, versao: str = "4.00") -> str:
    cuf = CODIGOS_UF.get(uf.upper(), 43)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NfceAutorizacaoService">
      <cUF>{cuf}</cUF>
      <versaoDados>{versao}</versaoDados>
    </nfeCabecMsg>
  </soap:Header>
  <soap:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NfceAutorizacaoService">
{xml_body}
    </nfeDadosMsg>
  </soap:Body>
</soap:Envelope>"""


def _soap_request(url: str, xml_envelope: str, cert_path: str, key_path: str, timeout: int = 60) -> str:
    context = ssl.create_default_context()
    context.load_cert_chain(cert_path, key_path)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    data = xml_envelope.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/soap+xml;charset=utf-8",
            "Content-Length": str(len(data)),
        },
    )

    try:
        resp = urllib.request.urlopen(req, context=context, timeout=timeout)
        return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SefazError(f"HTTP {e.code}: {body}", e.code, body)
    except urllib.error.URLError as e:
        raise SefazError(f"Erro de conexão: {e.reason}", 0, str(e))


class SefazError(Exception):
    def __init__(self, message, codigo=0, resposta=""):
        super().__init__(message)
        self.codigo = codigo
        self.resposta = resposta


def _extrair_retorno(resposta_soap: str) -> dict:
    if not resposta_soap or resposta_soap.strip() == "":
        return {"status": "ERRO", "xMotivo": "Resposta vazia da SEFAZ"}
    try:
        root = etree.fromstring(resposta_soap.encode())
    except etree.XMLSyntaxError as e:
        return {"status": "ERRO", "xMotivo": f"Erro ao parsear XML: {e}"}

    body = root.find(".//{http://www.w3.org/2003/05/soap-envelope}Body")
    if body is None:
        body = root.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Body")
    if body is None:
        return {"status": "ERRO", "xMotivo": "Corpo SOAP não encontrado"}

    for child in body.iter():
        if child.tag.endswith("retEnviNFe"):
            return _parse_ret_envi_nfe(child)
        if child.tag.endswith("retConsSitNFe"):
            return _parse_ret_cons_sit(child)
        if child.tag.endswith("retEvento"):
            return _parse_ret_evento(child)

    body_text = etree.tostring(body, encoding="unicode")[:500]
    return {"status": "ERRO", "xMotivo": f"Tag de retorno não reconhecida: {body_text}"}


def _parse_ret_envi_nfe(node) -> dict:
    ns = {"ns": "http://www.portalfiscal.inf.br/nfe"}
    result = {
        "status": "ERRO",
        "cStat": "",
        "xMotivo": "",
        "protocolo": "",
        "chave": "",
        "nProt": "",
    }
    for tag in ["tpAmb", "cUF", "cStat", "xMotivo", "cMsg", "xMsg", "dhRecbto"]:
        el = node.find(f".//ns:{tag}", ns)
        if el is not None:
            result[tag] = el.text or ""

    prot = node.find(".//ns:protNFe", ns)
    if prot is not None:
        inf = prot.find("ns:infProt", ns)
        if inf is not None:
            for tag in ["tpAmb", "cStat", "xMotivo", "chNFe", "nProt", "dhRecbto", "digVal"]:
                el = inf.find(f"ns:{tag}", ns)
                if el is not None:
                    result[tag] = el.text or ""
                    if tag == "chNFe":
                        result["chave"] = el.text or ""
                    if tag == "nProt":
                        result["protocolo"] = el.text or ""

    cstat = result.get("cStat", "")
    if cstat in ("100", "150", "110"):
        result["status"] = "AUTORIZADO"
    elif cstat in ("301", "302"):
        result["status"] = "DENEGADO"
    elif cstat in ("204", "205"):
        result["status"] = "REJEITADO"
    else:
        result["status"] = cstat
    return result


def _parse_ret_cons_sit(node) -> dict:
    ns = {"ns": "http://www.portalfiscal.inf.br/nfe"}
    result = {"status": "CONSULTA", "cStat": "", "xMotivo": "", "chave": "", "nProt": ""}
    for tag in ["cStat", "xMotivo", "chNFe", "nProt", "tpAmb", "cUF"]:
        el = node.find(f".//ns:{tag}", ns)
        if el is not None:
            result[tag.replace("chNFe", "chave")] = el.text or ""
    if "chave" not in result:
        el = node.find(".//ns:chNFe", ns)
        if el is not None:
            result["chave"] = el.text or ""
    return result


def _parse_ret_evento(node) -> dict:
    ns = {"ns": "http://www.portalfiscal.inf.br/nfe"}
    result = {"status": "EVENTO", "cStat": "", "xMotivo": "", "nProt": ""}
    inf = node.find(".//ns:infEvento", ns)
    if inf is not None:
        for tag in ["cStat", "xMotivo", "chNFe", "nProt", "tpEvento", "xEvento"]:
            el = inf.find(f"ns:{tag}", ns)
            if el is not None:
                result[tag] = el.text or ""
    return result


def autorizar_nfce(xml_envi_nfe: str, uf: str, ambiente: int, cert_id: str, cert_senha: str,
                   empresa: dict = None) -> dict:
    xml_assinado = cert_service.assinar_xml(xml_envi_nfe, cert_id, cert_senha)
    xml_assinado = nfce_xml.anexar_inf_nfe_supl(xml_assinado, empresa, ambiente)
    soap_env = _build_soap_envelope(xml_assinado, uf)
    url = _url_autorizacao(uf, ambiente)
    cert_path, key_path, _ = _load_cert(cert_id, cert_senha)

    try:
        resposta = _soap_request(url, soap_env, cert_path, key_path)
        return _extrair_retorno(resposta)
    except SefazError as e:
        return {"status": "ERRO_TRANSMISSAO", "cStat": str(e.codigo), "xMotivo": str(e)}
    except Exception as e:
        return {"status": "ERRO_TRANSMISSAO", "cStat": "999", "xMotivo": f"{type(e).__name__}: {e}"}


def consultar_nfce(chave: str, uf: str, ambiente: int, cert_id: str, cert_senha: str) -> dict:
    xml_consulta = f"""<?xml version="1.0" encoding="UTF-8"?>
<consSitNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <tpAmb>{ambiente}</tpAmb>
  <xServ>CONSULTAR</xServ>
  <chNFe>{chave}</chNFe>
</consSitNFe>"""

    xml_assinado = cert_service.assinar_xml(xml_consulta, cert_id, cert_senha)
    soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NfceConsultaService">
{xml_assinado}
    </nfeDadosMsg>
  </soap:Body>
</soap:Envelope>"""

    url = _url_consulta(uf, ambiente)
    cert_path, key_path, _ = _load_cert(cert_id, cert_senha)

    try:
        resposta = _soap_request(url, soap, cert_path, key_path)
        return _extrair_retorno(resposta)
    except SefazError as e:
        return {"status": "ERRO_CONSULTA", "cStat": str(e.codigo), "xMotivo": str(e)}
    except Exception as e:
        return {"status": "ERRO_CONSULTA", "cStat": "999", "xMotivo": f"{type(e).__name__}: {e}"}


def cancelar_nfce(chave: str, protocolo: str, uf: str, ambiente: int, cert_id: str, cert_senha: str,
                  cnpj: str = "", justificativa: str = "Cancelamento manual") -> dict:
    cuf = CODIGOS_UF.get(uf.upper(), 43)
    sequencia = 1
    data_evento = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
    cnpj_tag = f"<CNPJ>{cnpj}</CNPJ>" if cnpj else "<CNPJ></CNPJ>"

    xml_evento = f"""<?xml version="1.0" encoding="UTF-8"?>
<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <infEvento Id="ID110111{chave}{sequencia:02d}">
    <cOrgao>{cuf}</cOrgao>
    <tpAmb>{ambiente}</tpAmb>
    {cnpj_tag}
    <chNFe>{chave}</chNFe>
    <dhEvento>{data_evento}</dhEvento>
    <tpEvento>110111</tpEvento>
    <nSeqEvento>{sequencia}</nSeqEvento>
    <verEvento>1.00</verEvento>
    <detEvento versao="1.00">
      <descEvento>Cancelamento</descEvento>
      <nProt>{protocolo}</nProt>
      <xJust>{justificativa[:255]}</xJust>
    </detEvento>
  </infEvento>
</evento>"""

    xml_assinado = cert_service.assinar_xml(xml_evento, cert_id, cert_senha)
    soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NfceCancelamentoService">
{xml_assinado}
    </nfeDadosMsg>
  </soap:Body>
</soap:Envelope>"""

    url = _url_cancelamento(uf, ambiente)
    cert_path, key_path, _ = _load_cert(cert_id, cert_senha)

    try:
        resposta = _soap_request(url, soap, cert_path, key_path)
        return _extrair_retorno(resposta)
    except SefazError as e:
        return {"status": "ERRO_CANCELAMENTO", "cStat": str(e.codigo), "xMotivo": str(e)}
    except Exception as e:
        return {"status": "ERRO_CANCELAMENTO", "cStat": "999", "xMotivo": f"{type(e).__name__}: {e}"}


def _nfe_build_soap_envelope(xml_body: str, uf: str, servico: str = "NfeAutorizacaoService", versao: str = "4.00") -> str:
    cuf = CODIGOS_UF.get(uf.upper(), 43)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/{servico}">
      <cUF>{cuf}</cUF>
      <versaoDados>{versao}</versaoDados>
    </nfeCabecMsg>
  </soap:Header>
  <soap:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/{servico}">
{xml_body}
    </nfeDadosMsg>
  </soap:Body>
</soap:Envelope>"""


def autorizar_nfe(xml_envi_nfe: str, uf: str, ambiente: int, cert_id: str, cert_senha: str) -> dict:
    xml_assinado = cert_service.assinar_xml(xml_envi_nfe, cert_id, cert_senha)
    soap_env = _nfe_build_soap_envelope(xml_assinado, uf, "NfeAutorizacaoService")
    url = _nfe_url_autorizacao(uf, ambiente)
    cert_path, key_path, _ = _load_cert(cert_id, cert_senha)

    try:
        resposta = _soap_request(url, soap_env, cert_path, key_path)
        return _extrair_retorno(resposta)
    except SefazError as e:
        return {"status": "ERRO_TRANSMISSAO", "cStat": str(e.codigo), "xMotivo": str(e)}
    except Exception as e:
        return {"status": "ERRO_TRANSMISSAO", "cStat": "999", "xMotivo": f"{type(e).__name__}: {e}"}


def consultar_nfe(chave: str, uf: str, ambiente: int, cert_id: str, cert_senha: str) -> dict:
    xml_consulta = f"""<?xml version="1.0" encoding="UTF-8"?>
<consSitNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <tpAmb>{ambiente}</tpAmb>
  <xServ>CONSULTAR</xServ>
  <chNFe>{chave}</chNFe>
</consSitNFe>"""

    xml_assinado = cert_service.assinar_xml(xml_consulta, cert_id, cert_senha)
    soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NfeConsultaService">
{xml_assinado}
    </nfeDadosMsg>
  </soap:Body>
</soap:Envelope>"""

    url = _nfe_url_consulta(uf, ambiente)
    cert_path, key_path, _ = _load_cert(cert_id, cert_senha)

    try:
        resposta = _soap_request(url, soap, cert_path, key_path)
        return _extrair_retorno(resposta)
    except SefazError as e:
        return {"status": "ERRO_CONSULTA", "cStat": str(e.codigo), "xMotivo": str(e)}
    except Exception as e:
        return {"status": "ERRO_CONSULTA", "cStat": "999", "xMotivo": f"{type(e).__name__}: {e}"}


def cancelar_nfe(chave: str, protocolo: str, uf: str, ambiente: int, cert_id: str, cert_senha: str,
                 cnpj: str = "", justificativa: str = "Cancelamento manual") -> dict:
    cuf = CODIGOS_UF.get(uf.upper(), 43)
    sequencia = 1
    data_evento = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
    cnpj_tag = f"<CNPJ>{cnpj}</CNPJ>" if cnpj else "<CNPJ></CNPJ>"

    xml_evento = f"""<?xml version="1.0" encoding="UTF-8"?>
<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <infEvento Id="ID110111{chave}{sequencia:02d}">
    <cOrgao>{cuf}</cOrgao>
    <tpAmb>{ambiente}</tpAmb>
    {cnpj_tag}
    <chNFe>{chave}</chNFe>
    <dhEvento>{data_evento}</dhEvento>
    <tpEvento>110111</tpEvento>
    <nSeqEvento>{sequencia}</nSeqEvento>
    <verEvento>1.00</verEvento>
    <detEvento versao="1.00">
      <descEvento>Cancelamento</descEvento>
      <nProt>{protocolo}</nProt>
      <xJust>{justificativa[:255]}</xJust>
    </detEvento>
  </infEvento>
</evento>"""

    xml_assinado = cert_service.assinar_xml(xml_evento, cert_id, cert_senha)
    soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NfeCancelamentoService">
{xml_assinado}
    </nfeDadosMsg>
  </soap:Body>
</soap:Envelope>"""

    url = _nfe_url_cancelamento(uf, ambiente)
    cert_path, key_path, _ = _load_cert(cert_id, cert_senha)

    try:
        resposta = _soap_request(url, soap, cert_path, key_path)
        return _extrair_retorno(resposta)
    except SefazError as e:
        return {"status": "ERRO_CANCELAMENTO", "cStat": str(e.codigo), "xMotivo": str(e)}
    except Exception as e:
        return {"status": "ERRO_CANCELAMENTO", "cStat": "999", "xMotivo": f"{type(e).__name__}: {e}"}


def inutilizar_nfe(cnpj: str, uf: str, ambiente: int, serie: int, nnf_ini: int, nnf_fim: int,
                   cert_id: str, cert_senha: str, justificativa: str = "Inutilização") -> dict:
    cuf = CODIGOS_UF.get(uf.upper(), 43)
    mod = "55"
    nfe_mod = "55"
    ano = datetime.now().strftime("%y")

    id_inut = f"ID000000{cuf:02d}{ano}{cnpj.zfill(14)}{mod}{serie:03d}{nnf_ini:09d}{nnf_fim:09d}"

    xml_inut = f"""<?xml version="1.0" encoding="UTF-8"?>
<inutNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <infInut Id="{id_inut}">
    <tpAmb>{ambiente}</tpAmb>
    <xServ>INUTILIZAR</xServ>
    <cUF>{cuf}</cUF>
    <ano>{ano}</ano>
    <CNPJ>{cnpj.zfill(14)}</CNPJ>
    <mod>{mod}</mod>
    <serie>{serie}</serie>
    <nNFIni>{nnf_ini}</nNFIni>
    <nNFFin>{nnf_fim}</nNFFin>
    <xJust>{justificativa[:255]}</xJust>
  </infInut>
</inutNFe>"""

    xml_assinado = cert_service.assinar_xml(xml_inut, cert_id, cert_senha)
    soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NfeInutilizacaoService">
{xml_assinado}
    </nfeDadosMsg>
  </soap:Body>
</soap:Envelope>"""

    url = _nfe_url_inutilizacao(uf, ambiente)
    cert_path, key_path, _ = _load_cert(cert_id, cert_senha)

    try:
        resposta = _soap_request(url, soap, cert_path, key_path)
        return _extrair_retorno(resposta)
    except SefazError as e:
        return {"status": "ERRO_INUTILIZACAO", "cStat": str(e.codigo), "xMotivo": str(e)}
    except Exception as e:
        return {"status": "ERRO_INUTILIZACAO", "cStat": "999", "xMotivo": f"{type(e).__name__}: {e}"}
