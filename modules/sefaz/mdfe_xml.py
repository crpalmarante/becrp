import json
import os
from datetime import datetime
from lxml import etree

NS_MDFE = "http://www.portalfiscal.inf.br/mdfe"


def _tag(tag: str) -> str:
    return f"{{{NS_MDFE}}}{tag}"


def _add(parent, tag: str, text: str = ""):
    el = etree.SubElement(parent, _tag(tag))
    if text:
        el.text = text
    return el


def _add_i(parent, tag: str, val: int):
    return _add(parent, tag, str(val))


def _get_empresa() -> dict:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "dados", "empresa.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def montar_mdfe(manifesto: dict, empresa: dict = None, ambiente: int = 2, serie: int = 1, numero: int = 1) -> str:
    if empresa is None:
        empresa = _get_empresa()

    now = datetime.now()
    dh_emi = now.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    cnpj_raw = "".join(c for c in empresa.get("cnpj", "") if c.isdigit()).zfill(14)[:14]

    root = etree.Element(_tag("mdfeProc"), attrib={"xmlns": NS_MDFE, "versao": "3.00"})
    mdfe = etree.SubElement(root, _tag("MDFe"))
    inf = etree.SubElement(mdfe, _tag("infMDFe"), attrib={"versao": "3.00", "Id": f"MDFe{numero:09d}"})

    ide = etree.SubElement(inf, _tag("ide"))
    _add(ide, "cUF", str(empresa.get("cod_municipio", "43")[:2]))
    _add(ide, "tpAmb", str(ambiente))
    _add(ide, "tpEmit", "1")
    _add(ide, "tpTransp", "1")
    _add(ide, "mod", "58")
    _add_i(ide, "serie", serie)
    _add_i(ide, "nMDF", numero)
    _add(ide, "cMDF", str(numero).zfill(8))
    _add(ide, "cDV", "0")
    _add(ide, "modal", manifesto.get("modal", "1"))
    _add(ide, "dhEmi", dh_emi)
    _add(ide, "tpEmis", "1")
    _add(ide, "procEmi", "0")
    _add(ide, "verProc", "FiscalBrasil ERP 1.0")
    _add(ide, "ufIni", manifesto.get("uf_ini", "RS"))
    _add(ide, "ufFim", manifesto.get("uf_fim", "RS"))
    _add(ide, "cMunIni", str(manifesto.get("cod_mun_ini", empresa.get("cod_municipio", "4314902"))))
    _add(ide, "xMunIni", manifesto.get("mun_ini", ""))
    _add(ide, "cMunFim", str(manifesto.get("cod_mun_fim", "")))
    _add(ide, "xMunFim", manifesto.get("mun_fim", ""))
    for uf_percurso in manifesto.get("uf_percurso", []):
        _add(ide, "UFPer", uf_percurso)

    emit = etree.SubElement(inf, _tag("emit"))
    _add(emit, "CNPJ", cnpj_raw)
    _add(emit, "IE", empresa.get("inscricao_est", "").strip()[:14] or "ISENTO")
    _add(emit, "xNome", empresa.get("nome", "")[:60])
    _add(emit, "xFant", empresa.get("nome", "")[:60])
    ee = etree.SubElement(emit, _tag("enderEmit"))
    _add(ee, "xLgr", "RUA")
    _add(ee, "nro", "S/N")
    _add(ee, "xBairro", "CENTRO")
    _add(ee, "cMun", str(empresa.get("cod_municipio", "4314902")))
    _add(ee, "xMun", empresa.get("municipio", ""))
    _add(ee, "CEP", "99000000")
    _add(ee, "UF", empresa.get("uf", "RS")[:2])
    _add(ee, "fone", "0000000000")

    inf_cte = etree.SubElement(inf, _tag("infContratante"))
    _add(inf_cte, "xNome", manifesto.get("contratante", {}).get("nome", ""))
    cpf_cnpj_cont = etree.SubElement(inf_cte, "CPF_CNPJ")
    doc_cont = "".join(c for c in manifesto.get("contratante", {}).get("documento", "") if c.isdigit())
    if len(doc_cont) == 14:
        _add(inf_cte, "CNPJ", doc_cont[:14])
    else:
        _add(inf_cte, "CPF", doc_cont[:11] or "00000000000")

    for doc in manifesto.get("documentos", []):
        inf_doc = etree.SubElement(inf, _tag("infDoc"))
        chaves = etree.SubElement(inf_doc, _tag("chNFe"))
        for chave in doc.get("chaves", []):
            _add(chaves, "chNFe", chave)

    tot = etree.SubElement(inf, _tag("tot"))
    _add_d(tot, "qCTe", len(manifesto.get("documentos", [])))
    _add_d(tot, "qNFe", len(manifesto.get("documentos", [])))
    _add_d(tot, "vCarga", float(manifesto.get("valor_carga", 0)))
    _add(tot, "cUnid", manifesto.get("unidade_carga", "01"))
    _add(tot, "xNome", manifesto.get("descricao_carga", ""))[:60]

    veic = manifesto.get("veiculo", {})
    if veic:
        veiculo = etree.SubElement(inf, _tag("veiculo"))
        _add(veiculo, "cInt", veic.get("codigo", ""))
        _add(veiculo, "placa", veic.get("placa", ""))
        _add(veiculo, "RENAVAM", veic.get("renavam", ""))
        _add(veiculo, "tara", veic.get("tara", "0"))
        _add(veiculo, "capKG", veic.get("capacidade_kg", "0"))
        _add(veiculo, "capM3", veic.get("capacidade_m3", "0"))
        _add(veiculo, "prop", "3")
        condutor = etree.SubElement(veiculo, _tag("condutor"))
        _add(condutor, "xNome", veic.get("motorista", ""))[:60]
        _add(condutor, "CPF", "".join(c for c in veic.get("cpf_motorista", "") if c.isdigit())[:11])

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()
