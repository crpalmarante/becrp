import json
import os
from datetime import datetime
from lxml import etree

NS_CTE = "http://www.portalfiscal.inf.br/cte"


def _tag(tag: str) -> str:
    return f"{{{NS_CTE}}}{tag}"


def _add(parent, tag: str, text: str = ""):
    el = etree.SubElement(parent, _tag(tag))
    if text:
        el.text = text
    return el


def _add_i(parent, tag: str, val: int):
    return _add(parent, tag, str(val))


def _add_d(parent, tag: str, val: float):
    return _add(parent, tag, f"{val:.2f}")


def _fmt_cnpj(cnpj: str) -> str:
    return "".join(c for c in cnpj if c.isdigit()).zfill(14)[:14]


def _fmt_cpf(cpf: str) -> str:
    return "".join(c for c in cpf if c.isdigit()).zfill(11)[:11]


def _get_empresa() -> dict:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "dados", "empresa.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def montar_cte(frete: dict, empresa: dict = None, ambiente: int = 2, serie: int = 1, numero: int = 1) -> str:
    if empresa is None:
        empresa = _get_empresa()

    now = datetime.now()
    dh_emi = now.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    cnpj_raw = _fmt_cnpj(empresa.get("cnpj", ""))

    root = etree.Element(_tag("cteProc"), attrib={"xmlns": NS_CTE, "versao": "4.00"})
    cte = etree.SubElement(root, _tag("CTe"))
    inf = etree.SubElement(cte, _tag("infCte"), attrib={"versao": "4.00", "Id": f"CTe{numero:09d}"})

    ide = etree.SubElement(inf, _tag("ide"))
    _add(ide, "cUF", str(empresa.get("cod_municipio", "43")[:2]))
    _add(ide, "cCT", str(numero).zfill(8))
    _add(ide, "CFOP", frete.get("cfop", "5351"))
    _add(ide, "natOp", frete.get("natOp", "PRESTACAO DE SERVICO DE TRANSPORTE"))
    _add(ide, "mod", "57")
    _add_i(ide, "serie", serie)
    _add_i(ide, "nCT", numero)
    _add(ide, "dhEmi", dh_emi)
    _add(ide, "tpImp", "1")
    _add(ide, "tpEmis", "1")
    _add(ide, "cDV", "0")
    _add_i(ide, "tpAmb", ambiente)
    _add(ide, "tpCTe", "0")
    _add(ide, "procEmi", "0")
    _add(ide, "verProc", "FiscalBrasil ERP 1.0")
    _add(ide, "cMunFG", str(empresa.get("cod_municipio", "4314902")))
    _add(ide, "xMunFG", empresa.get("municipio", ""))
    _add(ide, "UF", empresa.get("uf", "RS" if isinstance(empresa.get("uf"), str) else "RS")[:2])
    _add(ide, "tpServ", "0")
    _add(ide, "cMunIni", frete.get("cod_mun_ini", ""))
    _add(ide, "xMunIni", frete.get("mun_ini", ""))
    _add(ide, "UFIni", frete.get("uf_ini", ""))
    _add(ide, "cMunFim", frete.get("cod_mun_fim", ""))
    _add(ide, "xMunFim", frete.get("mun_fim", ""))
    _add(ide, "UFFim", frete.get("uf_fim", ""))
    _add(ide, "retira", "0")

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

    rem = etree.SubElement(inf, _tag("rem"))
    doc_rem = frete.get("remetente", {}).get("documento", "")
    if doc_rem:
        dclean = "".join(c for c in doc_rem if c.isdigit())
        if len(dclean) == 14:
            _add(rem, "CNPJ", dclean[:14])
        else:
            _add(rem, "CPF", dclean[:11])
    _add(rem, "IE", frete.get("remetente", {}).get("ie", ""))
    _add(rem, "xNome", frete.get("remetente", {}).get("nome", "")[:60])
    _add(rem, "xFant", frete.get("remetente", {}).get("fantasia", "")[:60])
    re = etree.SubElement(rem, _tag("enderReme"))
    _add(re, "xLgr", frete.get("remetente", {}).get("endereco", "RUA"))
    _add(re, "nro", frete.get("remetente", {}).get("numero", "S/N"))
    _add(re, "xBairro", frete.get("remetente", {}).get("bairro", "CENTRO"))
    _add(re, "cMun", frete.get("remetente", {}).get("cod_mun", ""))
    _add(re, "xMun", frete.get("remetente", {}).get("cidade", ""))
    _add(re, "CEP", "".join(c for c in frete.get("remetente", {}).get("cep", "") if c.isdigit())[:8])
    _add(re, "UF", frete.get("remetente", {}).get("uf", "RS"))
    _add(re, "fone", "".join(c for c in frete.get("remetente", {}).get("fone", "") if c.isdigit())[:14])

    dest = etree.SubElement(inf, _tag("dest"))
    doc_dest = frete.get("destinatario", {}).get("documento", "")
    if doc_dest:
        dclean = "".join(c for c in doc_dest if c.isdigit())
        if len(dclean) == 14:
            _add(dest, "CNPJ", dclean[:14])
        else:
            _add(dest, "CPF", dclean[:11])
    _add(dest, "IE", frete.get("destinatario", {}).get("ie", ""))
    _add(dest, "xNome", frete.get("destinatario", {}).get("nome", "")[:60])
    de = etree.SubElement(dest, _tag("enderDest"))
    _add(de, "xLgr", frete.get("destinatario", {}).get("endereco", "RUA"))
    _add(de, "nro", frete.get("destinatario", {}).get("numero", "S/N"))
    _add(de, "xBairro", frete.get("destinatario", {}).get("bairro", "CENTRO"))
    _add(de, "cMun", frete.get("destinatario", {}).get("cod_mun", ""))
    _add(de, "xMun", frete.get("destinatario", {}).get("cidade", ""))
    _add(de, "CEP", "".join(c for c in frete.get("destinatario", {}).get("cep", "") if c.isdigit())[:8])
    _add(de, "UF", frete.get("destinatario", {}).get("uf", "RS"))
    _add(de, "fone", "".join(c for c in frete.get("destinatario", {}).get("fone", "") if c.isdigit())[:14])

    vp = etree.SubElement(inf, _tag("vPrest"))
    _add_d(vp, "vTPrest", float(frete.get("valor", 0)))
    _add(vp, "vRec", str(float(frete.get("valor", 0))))

    imp = etree.SubElement(inf, _tag("imp"))
    icms = etree.SubElement(imp, _tag("ICMS"))
    icms00 = etree.SubElement(icms, _tag("ICMS00"))
    _add(icms00, "CST", "00")
    _add_d(icms00, "vBC", float(frete.get("valor", 0)))
    _add_d(icms00, "pICMS", 12)
    _add_d(icms00, "vICMS", float(frete.get("valor", 0)) * 0.12)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()
