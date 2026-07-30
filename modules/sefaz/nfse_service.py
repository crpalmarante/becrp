import base64
import json
import os
import ssl
import urllib.error
import urllib.request
from datetime import datetime
from lxml import etree

from modules.certificate import cert_service
from modules.sefaz import nfse_xml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CIDADES_NFSE = {
    "4314100": {  # Passo Fundo/RS
        "nome": "Passo Fundo",
        "uf": "RS",
        "homologacao": "https://homologacao.passofundo.rs.gov.br/nfse/services/NFSeService",
        "producao": "https://passofundo.rs.gov.br/nfse/services/NFSeService",
    },
    "4314902": {  # Porto Alegre/RS
        "nome": "Porto Alegre",
        "uf": "RS",
        "homologacao": "https://homologacao.portoalegre.rs.gov.br/nfse/services/NFSeService",
        "producao": "https://portoalegre.rs.gov.br/nfse/services/NFSeService",
    },
}

DEFAULT_CIDADE = "4314100"


def _url_nfse(cod_municipio: str, ambiente: int) -> str:
    dados = CIDADES_NFSE.get(cod_municipio)
    if not dados:
        raise ValueError(f"Cidade não configurada: {cod_municipio}")
    return dados["producao"] if ambiente == 1 else dados["homologacao"]


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
        raise Exception(f"HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        raise Exception(f"Erro de conexão: {e.reason}")


def autorizar_nfse(xml_nfse: str, cod_municipio: str, ambiente: int, cert_id: str, cert_senha: str) -> dict:
    xml_assinado = cert_service.assinar_xml(xml_nfse, cert_id, cert_senha)
    url = _url_nfse(cod_municipio, ambiente)
    cert_path, key_path, _ = _load_cert(cert_id, cert_senha)

    soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soap:Body>
    <GerarNfse xmlns="http://www.abrasf.org.br/nfse">
      {xml_assinado}
    </GerarNfse>
  </soap:Body>
</soap:Envelope>"""

    try:
        resposta = _soap_request(url, soap, cert_path, key_path)
        return {"status": "ENVIADO", "resposta": resposta[:1000], "completo": True}
    except Exception as e:
        return {"status": "ERRO", "xMotivo": str(e)}


def consultar_nfse(numero_rps: str, cod_municipio: str, ambiente: int, cert_id: str, cert_senha: str) -> dict:
    url = _url_nfse(cod_municipio, ambiente)
    cert_path, key_path, _ = _load_cert(cert_id, cert_senha)

    xml_consulta = f"""<?xml version="1.0" encoding="UTF-8"?>
<ConsultarNfseRps xmlns="http://www.abrasf.org.br/nfse">
  <IdentificacaoRps>
    <Numero>{numero_rps}</Numero>
    <Serie>1</Serie>
    <Tipo>1</Tipo>
  </IdentificacaoRps>
</ConsultarNfseRps>"""

    soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ConsultarNfseRps xmlns="http://www.abrasf.org.br/nfse">
      {xml_consulta}
    </ConsultarNfseRps>
  </soap:Body>
</soap:Envelope>"""

    try:
        resposta = _soap_request(url, soap, cert_path, key_path)
        return {"status": "CONSULTADO", "resposta": resposta[:1000]}
    except Exception as e:
        return {"status": "ERRO", "xMotivo": str(e)}


_CERT_CACHE = {}


def _load_cert(cert_id: str, senha: str) -> tuple:
    if cert_id in _CERT_CACHE:
        return _CERT_CACHE[cert_id]
    index = cert_service._load_index()
    if cert_id not in index:
        raise ValueError("Certificado não encontrado")
    info = index[cert_id]
    caminho = os.path.join(cert_service.CERT_DIR, info["arquivo"])
    with open(caminho, "rb") as f:
        pfx_data = f.read()
    loaded = cert_service.carregar(pfx_data, senha)
    from cryptography.hazmat.primitives import serialization
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
