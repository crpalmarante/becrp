"""
NF-e DistDFe (distribuição de DF-e) — Ambiente Nacional.

Baixa documentos destinados ao CNPJ do emitente (quando certificado A1 válido).
Salva XMLs em data/nfe_inbox/ para o nfe_monitor processar.
"""

from __future__ import annotations

import base64
import gzip
import json
import os
import ssl
import urllib.error
import urllib.request
import zlib
from datetime import datetime
from typing import Optional

from lxml import etree

from modules.certificate import cert_service
from modules.sefaz import sefaz_service

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "data", "nfe_distdfe_state.json")
INBOX_DIR = os.path.join(BASE_DIR, "data", "nfe_inbox")

NS_NFE = "http://www.portalfiscal.inf.br/nfe"
NS_WSDL = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe"

URLS = {
    1: "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
    2: "https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _digits(val):
    return "".join(c for c in str(val or "") if c.isdigit())


def _load_state():
    if not os.path.exists(STATE_FILE):
        return {"ultNSU": "0", "maxNSU": "0", "ambiente": 2, "atualizado_em": None}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"ultNSU": "0", "maxNSU": "0", "ambiente": 2}
    data.setdefault("ultNSU", "0")
    data.setdefault("maxNSU", "0")
    return data


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE) or ".", exist_ok=True)
    state["atualizado_em"] = _now()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _resolve_cert(cert_id=None, cert_senha=None):
    """Resolve cert A1: body → índice ativo com senha da empresa → erro claro."""
    cid = str(cert_id or "").strip()
    senha = str(cert_senha or "")
    if not cid:
        # tenta índice: preferir doc = CNPJ da empresa
        try:
            import org_store
            emp = org_store.resolve_empresa_fiscal()
            cnpj = _digits(emp.get("cnpj"))
            senha = senha or str(emp.get("cert_senha") or "")
        except Exception:
            cnpj = ""
        for c in cert_service.listar() or []:
            if not c.get("ativo") or not c.get("valido"):
                continue
            if cnpj and _digits(c.get("documento")) == cnpj:
                cid = str(c.get("id"))
                break
            if not cid:
                cid = str(c.get("id"))
        if not senha:
            try:
                import cobol_bridge
                out, _ = cobol_bridge._run("gerir_empresa", {"ACAO": "mostrar"})
                cur = json.loads(out[out.find("{"):])
                senha = str(cur.get("cert_senha") or "")
            except Exception:
                pass
    if not cid:
        raise ValueError(
            "Nenhum certificado A1 no índice. Importe o .pfx em Admin → Certificados."
        )
    if not senha:
        raise ValueError("Senha do certificado ausente (informe cert_senha ou grave na empresa).")
    return cid, senha


def _build_dist_xml(cnpj: str, ult_nsu: str, *, cuf_autor: int = 42) -> str:
    nsu = str(ult_nsu or "0").zfill(15)
    cnpj = _digits(cnpj)
    return (
        f'<distDFeInt xmlns="{NS_NFE}" versao="1.01">'
        f"<tpAmb>{{tpAmb}}</tpAmb>"
        f"<cUFAutor>{cuf_autor}</cUFAutor>"
        f"<CNPJ>{cnpj}</CNPJ>"
        f"<distNSU><ultNSU>{nsu}</ultNSU></distNSU>"
        f"</distDFeInt>"
    )


def _soap_envelope(xml_body: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDistDFeInteresse xmlns="{NS_WSDL}">
      <nfeDadosMsg>{xml_body}</nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap12:Body>
</soap12:Envelope>"""


def _decompress_doc(b64: str) -> bytes:
    raw = base64.b64decode(b64)
    try:
        return gzip.decompress(raw)
    except Exception:
        try:
            return zlib.decompress(raw)
        except Exception:
            return raw


def _post(url: str, envelope: str, cert_path: str, key_path: str, timeout: int = 90) -> str:
    ctx = ssl.create_default_context()
    ctx.load_cert_chain(cert_path, key_path)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    data = envelope.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/soap+xml; charset=utf-8",
            "SOAPAction": f'"{NS_WSDL}/nfeDistDFeInteresse"',
        },
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise sefaz_service.SefazError(f"HTTP {e.code}: {body[:500]}", e.code, body)
    except urllib.error.URLError as e:
        raise sefaz_service.SefazError(f"Erro de conexão DistDFe: {e.reason}", 0, str(e))


def consultar_e_baixar(
    *,
    cnpj=None,
    cert_id=None,
    cert_senha=None,
    ambiente=None,
    ult_nsu=None,
    max_loops=3,
    user_id=None,
):
    """
    Consulta DistDFe e grava XMLs de NF-e em data/nfe_inbox/.
    Retorna resumo; não processa receiving (use nfe_monitor.scan + process).
    """
    import org_store

    emp = org_store.resolve_empresa_fiscal()
    cnpj = _digits(cnpj or emp.get("cnpj"))
    if len(cnpj) != 14:
        raise ValueError("CNPJ do emitente inválido para DistDFe")

    state = _load_state()
    amb = int(ambiente if ambiente is not None else state.get("ambiente") or 2)
    if amb not in (1, 2):
        amb = 2
    nsu = str(ult_nsu if ult_nsu is not None else state.get("ultNSU") or "0")
    cid, senha = _resolve_cert(cert_id, cert_senha)
    cert_path, key_path, _loaded = sefaz_service._load_cert(cid, senha)

    uf = str(emp.get("uf") or "SC").upper()
    cuf = sefaz_service.CODIGOS_UF.get(uf, 42)
    url = URLS[amb]
    os.makedirs(INBOX_DIR, exist_ok=True)

    saved = []
    errors = []
    last_ret = {}
    loops = max(1, min(int(max_loops or 3), 10))

    for _ in range(loops):
        body = _build_dist_xml(cnpj, nsu, cuf_autor=cuf).replace("{tpAmb}", str(amb))
        # nfeDadosMsg espera o XML sem escapes extras — inserir como XML
        envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDistDFeInteresse xmlns="{NS_WSDL}">
      <nfeDadosMsg>{body}</nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap12:Body>
</soap12:Envelope>"""
        try:
            resp = _post(url, envelope, cert_path, key_path)
        except Exception as e:
            errors.append(str(e))
            break

        try:
            root = etree.fromstring(resp.encode("utf-8"))
        except etree.XMLSyntaxError as e:
            errors.append(f"XML DistDFe ilegível: {e}")
            break

        ret = None
        for el in root.iter():
            if el.tag.endswith("retDistDFeInt"):
                ret = el
                break
        if ret is None:
            errors.append("retDistDFeInt ausente na resposta SEFAZ")
            break

        def _t(tag):
            for c in ret.iter():
                if c.tag.endswith(tag):
                    return (c.text or "").strip()
            return ""

        c_stat = _t("cStat")
        x_motivo = _t("xMotivo")
        ult = _t("ultNSU") or nsu
        maxn = _t("maxNSU") or state.get("maxNSU") or "0"
        last_ret = {"cStat": c_stat, "xMotivo": x_motivo, "ultNSU": ult, "maxNSU": maxn}
        nsu = ult
        state["ultNSU"] = ult
        state["maxNSU"] = maxn
        state["ambiente"] = amb
        state["ultimo_cStat"] = c_stat
        state["ultimo_motivo"] = x_motivo

        lote = None
        for c in ret.iter():
            if c.tag.endswith("loteDistDFeInt"):
                lote = c
                break
        if lote is not None:
            for doc in lote:
                if not doc.tag.endswith("docZip"):
                    continue
                schema = doc.get("schema") or ""
                nsu_doc = doc.get("NSU") or ""
                try:
                    content = _decompress_doc(doc.text or "")
                except Exception as e:
                    errors.append(f"NSU {nsu_doc}: falha ao descompactar ({e})")
                    continue
                # só NF-e proc / NFe
                text = content.decode("utf-8", errors="replace")
                if "infNFe" not in text and "nfeProc" not in text:
                    continue
                fname = f"distdfe_{nsu_doc or '0'}_{_now().replace(':','').replace('-','')}.xml"
                path = os.path.join(INBOX_DIR, fname)
                with open(path, "wb") as f:
                    f.write(content if isinstance(content, (bytes, bytearray)) else text.encode("utf-8"))
                saved.append({
                    "nsu": nsu_doc,
                    "schema": schema,
                    "path": path,
                    "filename": fname,
                })

        # 137 = nenhum doc; 138 = doc localizado — continua se ult < max
        if c_stat not in ("138", "137"):
            if c_stat:
                errors.append(f"SEFAZ cStat={c_stat}: {x_motivo}")
            break
        if c_stat == "137":
            break
        try:
            if int(ult or 0) >= int(maxn or 0):
                break
        except ValueError:
            break

    _save_state(state)

    # ingest automático dos baixados
    ingested = []
    try:
        import nfe_monitor
        scan = nfe_monitor.scan_inbox(user_id=user_id)
        ingested = scan.get("created") or []
    except Exception as e:
        errors.append(f"scan inbox: {e}")

    return {
        "ok": not errors or bool(saved),
        "ambiente": amb,
        "cnpj": cnpj,
        "cert_id": cid,
        "retorno": last_ret,
        "saved": saved,
        "saved_count": len(saved),
        "ingested": ingested,
        "ingested_count": len(ingested),
        "state": {"ultNSU": state.get("ultNSU"), "maxNSU": state.get("maxNSU")},
        "errors": errors,
        "message": (
            f"DistDFe: {len(saved)} XML(s) baixado(s), {len(ingested)} no monitor"
            if saved or ingested
            else (errors[0] if errors else (last_ret.get("xMotivo") or "sem documentos novos"))
        ),
    }
