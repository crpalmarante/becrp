"""Certificado A1 — Serviço de gestão de certificados digitais ICP-Brasil"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID, ObjectIdentifier
from lxml import etree
from signxml import XMLSigner, methods

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CERT_DIR = os.path.join(BASE_DIR, "dados", "certificados")
CERTS_INDEX = os.path.join(CERT_DIR, "index.json")

ICP_BRASIL_CNPJ_OID = ObjectIdentifier("2.16.76.1.3.1")
ICP_BRASIL_CPF_OID = ObjectIdentifier("2.16.76.1.3.2")

os.makedirs(CERT_DIR, exist_ok=True)


def _load_index():
    if not os.path.exists(CERTS_INDEX):
        return {}
    with open(CERTS_INDEX, "r") as f:
        return json.load(f)


def _save_index(index):
    with open(CERTS_INDEX, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def _next_id(index):
    ids = [int(k) for k in index.keys() if k.isdigit()]
    return str(max(ids) + 1) if ids else "1"


def _extract_cnpj(cert: x509.Certificate) -> str:
    for attr in cert.subject:
        if attr.oid == ICP_BRASIL_CNPJ_OID:
            return attr.value
        if attr.oid == NameOID.SERIAL_NUMBER:
            val = attr.value
            digits = re.sub(r"\D", "", val)
            if len(digits) == 14:
                return digits
        if attr.oid.dotted_string == "2.16.76.1.3.1":
            return attr.value
    for attr in cert.subject.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME):
        m = re.search(r"(\d{14})", attr.value)
        if m:
            return m.group(1)
    return ""


def _extract_cpf(cert: x509.Certificate) -> str:
    for attr in cert.subject:
        if attr.oid == ICP_BRASIL_CPF_OID:
            return attr.value
        if attr.oid.dotted_string == "2.16.76.1.3.2":
            return attr.value
    return ""


def carregar(arquivo_pfx: bytes, senha: str) -> dict:
    try:
        key_and_cert = pkcs12.load_pkcs12(arquivo_pfx, senha.encode())
    except Exception as e:
        raise ValueError(f"Erro ao carregar PFX: {e}")

    if key_and_cert.cert is None:
        raise ValueError("PFX não contém certificado")

    raw_cert = key_and_cert.cert
    if hasattr(raw_cert, "certificate"):
        cert = raw_cert.certificate
    else:
        cert = raw_cert
    chave_privada = key_and_cert.key

    if chave_privada is None:
        raise ValueError("PFX não contém chave privada")

    agora = datetime.now(timezone.utc)
    valido_de = cert.not_valid_before_utc
    valido_ate = cert.not_valid_after_utc
    dias_restantes = (valido_ate - agora).days

    cnpj = _extract_cnpj(cert)
    cpf = _extract_cpf(cert)
    nome = ""
    for attr in cert.subject:
        if attr.oid == NameOID.COMMON_NAME:
            nome = attr.value
            break
    razao_social = ""
    for attr in cert.subject:
        if attr.oid == NameOID.ORGANIZATION_NAME:
            razao_social = attr.value
            break

    emissor = ""
    for attr in cert.issuer:
        if attr.oid == NameOID.COMMON_NAME:
            emissor = attr.value
            break

    return {
        "cert": cert,
        "key": chave_privada,
        "info": {
            "nome": nome,
            "razao_social": razao_social,
            "cnpj": cnpj,
            "cpf": cpf,
            "emissor": emissor,
            "valido_de": valido_de.isoformat(),
            "valido_ate": valido_ate.isoformat(),
            "dias_restantes": dias_restantes,
            "valido": dias_restantes > 0,
            "serial": format(cert.serial_number, "X"),
        },
        "additional_certs": key_and_cert.additional_certs or [],
    }


def listar() -> list:
    index = _load_index()
    resultados = []
    for cid, info in index.items():
        item = dict(info)
        item["id"] = cid
        resultados.append(item)
    return sorted(resultados, key=lambda x: x.get("nome", "").lower())


def obter(cert_id: str) -> Optional[dict]:
    index = _load_index()
    if cert_id not in index:
        return None
    item = dict(index[cert_id])
    item["id"] = cert_id
    return item


def upload(arquivo_pfx: bytes, senha: str, nome_arquivo: str = "") -> dict:
    if len(arquivo_pfx) > 10 * 1024 * 1024:
        raise ValueError("Arquivo muito grande (máx 10MB)")

    loaded = carregar(arquivo_pfx, senha)
    info = loaded["info"]

    if not info["valido"]:
        raise ValueError(f"Certificado expirado em {info['valido_ate']}")

    if not info["cnpj"] and not info["cpf"]:
        raise ValueError("Certificado não contém CNPJ/CPF ICP-Brasil")

    index = _load_index()

    documento = info.get("cnpj") or info.get("cpf")
    for cid, existing in index.items():
        if existing.get("documento") == documento:
            raise ValueError(f"Já existe um certificado para este documento ({documento})")

    cid = _next_id(index)
    ext = os.path.splitext(nome_arquivo)[1] if nome_arquivo else ".pfx"
    if ext.lower() not in (".pfx", ".p12"):
        ext = ".pfx"
    dest_name = f"{cid}_{documento}{ext}"
    dest_path = os.path.join(CERT_DIR, dest_name)

    with open(dest_path, "wb") as f:
        f.write(arquivo_pfx)

    index[cid] = {
        "nome": info["nome"],
        "razao_social": info["razao_social"],
        "documento": documento,
        "emissor": info["emissor"],
        "valido_de": info["valido_de"],
        "valido_ate": info["valido_ate"],
        "dias_restantes": info["dias_restantes"],
        "valido": info["valido"],
        "serial": info["serial"],
        "arquivo": dest_name,
        "ativo": True,
    }
    _save_index(index)
    return {"id": cid, **index[cid]}


def remover(cert_id: str) -> bool:
    index = _load_index()
    if cert_id not in index:
        return False
    arquivo = index[cert_id].get("arquivo", "")
    if arquivo:
        caminho = os.path.join(CERT_DIR, arquivo)
        if os.path.exists(caminho):
            os.remove(caminho)
    del index[cert_id]
    _save_index(index)
    return True


def validar(cert_id: str) -> dict:
    index = _load_index()
    if cert_id not in index:
        raise ValueError("Certificado não encontrado")

    info = index[cert_id]
    agora = datetime.now(timezone.utc)
    try:
        valido_ate = datetime.fromisoformat(info["valido_ate"])
    except (KeyError, ValueError):
        valido_ate = agora

    dias_restantes = (valido_ate - agora).days
    valido = dias_restantes > 0

    info["valido"] = valido
    info["dias_restantes"] = dias_restantes
    _save_index(index)

    return {
        "valido": valido,
        "dias_restantes": dias_restantes,
        "valido_ate": info.get("valido_ate", ""),
        "emissor": info.get("emissor", ""),
        "nome": info.get("nome", ""),
        "cnpj": info.get("documento", ""),
    }


def info_detalhada(cert_id: str) -> Optional[dict]:
    index = _load_index()
    if cert_id not in index:
        return None
    info = index[cert_id]
    arquivo = info.get("arquivo", "")
    caminho = os.path.join(CERT_DIR, arquivo)
    return {
        **info,
        "id": cert_id,
        "arquivo_disponivel": os.path.exists(caminho),
    }


def assinar_xml(xml_string: str, cert_id: str, senha: str = "", reference_uri: Optional[str] = None) -> str:
    index = _load_index()
    if cert_id not in index:
        raise ValueError("Certificado não encontrado")

    info = index[cert_id]
    arquivo = info.get("arquivo", "")
    caminho = os.path.join(CERT_DIR, arquivo)
    if not os.path.exists(caminho):
        raise ValueError(f"Arquivo do certificado não encontrado: {arquivo}")

    with open(caminho, "rb") as f:
        pfx_data = f.read()

    loaded = carregar(pfx_data, senha)
    cert = loaded["cert"]
    key = loaded["key"]

    root = etree.fromstring(xml_string.encode())

    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
    )

    ns = {}
    if reference_uri:
        ns["reference_uri"] = reference_uri

    signed_xml = signer.sign(root, key=key, cert=cert)
    return etree.tostring(signed_xml, xml_declaration=True, encoding="UTF-8").decode()


def alternar_ativo(cert_id: str) -> Optional[bool]:
    index = _load_index()
    if cert_id not in index:
        return None
    index[cert_id]["ativo"] = not index[cert_id].get("ativo", True)
    _save_index(index)
    return index[cert_id]["ativo"]


def definir_empresa(cert_id: str, empresa_id: str = "") -> bool:
    index = _load_index()
    if cert_id not in index:
        return False
    if empresa_id:
        for cid in index:
            index[cid].pop("empresa_id", None)
        index[cert_id]["empresa_id"] = empresa_id
    else:
        index[cert_id].pop("empresa_id", None)
    _save_index(index)
    return True
