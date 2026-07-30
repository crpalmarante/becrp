"""NFC-e XML Builder — Monta o XML de NFC-e (modelo 65) para envio à SEFAZ"""

import hashlib
import json
import os
import re
from datetime import datetime
from typing import Optional
from lxml import etree


NS_NFE = "http://www.portalfiscal.inf.br/nfe"
NS_DSIG = "http://www.w3.org/2000/09/xmldsig#"

# QR Code base URLs (produção). Homologação usa variante quando disponível.
QRCODE_URLS = {
    "RS": {
        1: "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx",
        2: "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx",
    },
    "SP": {
        1: "https://www.nfce.fazenda.sp.gov.br/qrcode",
        2: "https://www.homologacao.nfce.fazenda.sp.gov.br/qrcode",
    },
    "MG": {
        1: "https://portalsped.fazenda.mg.gov.br/portalnfce/sistema/qrcode.xhtml",
        2: "https://portalsped.fazenda.mg.gov.br/portalnfce/sistema/qrcode.xhtml",
    },
    "PR": {
        1: "http://www.fazenda.pr.gov.br/nfce/qrcode",
        2: "http://www.fazenda.pr.gov.br/nfce/qrcode",
    },
    "SC": {
        1: "https://sat.sef.sc.gov.br/nfce/consulta",
        2: "https://hom.sat.sef.sc.gov.br/nfce/consulta",
    },
    # SVRS-style / estados autorizadores via SVRS
    "SVRS": {
        1: "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx",
        2: "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx",
    },
    "AC": {
        1: "http://www.sefaznet.ac.gov.br/nfce/qrcode",
        2: "http://www.sefaznet.ac.gov.br/nfce/qrcode",
    },
    "AL": {
        1: "http://nfce.sefaz.al.gov.br/QRCode/consultarNFCe.jsp",
        2: "http://nfce.sefaz.al.gov.br/QRCode/consultarNFCe.jsp",
    },
    "AP": {
        1: "https://www.sefaz.ap.gov.br/nfce/nfcep.php",
        2: "https://www.sefaz.ap.gov.br/nfce/nfcep.php",
    },
    "AM": {
        1: "http://sistemas.sefaz.am.gov.br/nfceweb/consultarNFCe.jsp",
        2: "http://homnfce.sefaz.am.gov.br/nfceweb/consultarNFCe.jsp",
    },
    "BA": {
        1: "http://nfe.sefaz.ba.gov.br/servicos/nfce/qrcode.aspx",
        2: "http://hnfe.sefaz.ba.gov.br/servicos/nfce/qrcode.aspx",
    },
    "CE": {
        1: "http://nfce.sefaz.ce.gov.br/pages/ShowNFCe.html",
        2: "http://nfceh.sefaz.ce.gov.br/pages/ShowNFCe.html",
    },
    "DF": {
        1: "http://www.fazenda.df.gov.br/nfce/qrcode",
        2: "http://www.fazenda.df.gov.br/nfce/qrcode",
    },
    "ES": {
        1: "http://app.sefaz.es.gov.br/ConsultaNFCe/QRCode.aspx",
        2: "http://homologacao.sefaz.es.gov.br/ConsultaNFCe/QRCode.aspx",
    },
    "GO": {
        1: "http://nfe.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe",
        2: "http://homolog.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe",
    },
    "MA": {
        1: "http://www.nfce.sefaz.ma.gov.br/portal/consultarNFCe.jsp",
        2: "http://www.hom.nfce.sefaz.ma.gov.br/portal/consultarNFCe.jsp",
    },
    "MT": {
        1: "http://www.sefaz.mt.gov.br/nfce/consultanfce",
        2: "http://homologacao.sefaz.mt.gov.br/nfce/consultanfce",
    },
    "MS": {
        1: "http://www.dfe.ms.gov.br/nfce/qrcode",
        2: "http://www.dfe.ms.gov.br/nfce/qrcode",
    },
    "PA": {
        1: "https://appnfc.sefa.pa.gov.br/portal/view/consultas/nfce/nfceForm.seam",
        2: "https://appnfc.sefa.pa.gov.br/portal/view/consultas/nfce/nfceForm.seam",
    },
    "PB": {
        1: "http://www.receita.pb.gov.br/nfce",
        2: "http://www.receita.pb.gov.br/nfcehom",
    },
    "PE": {
        1: "http://nfce.sefaz.pe.gov.br/nfce/consulta",
        2: "http://nfcehomologacao.sefaz.pe.gov.br/nfce/consulta",
    },
    "PI": {
        1: "http://www.sefaz.pi.gov.br/nfce/qrcode",
        2: "http://www.sefaz.pi.gov.br/nfce/qrcode",
    },
    "RJ": {
        1: "https://consultadfe.fazenda.rj.gov.br/consultaNFCe/QRCode",
        2: "https://consultadfe.fazenda.rj.gov.br/consultaNFCe/QRCode",
    },
    "RN": {
        1: "http://nfce.set.rn.gov.br/consultarNFCe.aspx",
        2: "http://hom.nfce.set.rn.gov.br/consultarNFCe.aspx",
    },
    "RO": {
        1: "http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp",
        2: "http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp",
    },
    "RR": {
        1: "https://www.sefaz.rr.gov.br/nfce/servlet/qrcode",
        2: "http://200.100.51.102/nfce/servlet/qrcode",
    },
    "SE": {
        1: "http://www.nfce.se.gov.br/nfce/qrcode",
        2: "http://www.hom.nfe.se.gov.br/nfce/qrcode",
    },
    "TO": {
        1: "http://www.sefaz.to.gov.br/nfce/qrcode",
        2: "http://homologacao.sefaz.to.gov.br/nfce/qrcode",
    },
}

# URL de consulta por chave (urlChave)
URL_CHAVE = {
    "RS": "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx",
    "SP": "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica",
    "MG": "https://portalsped.fazenda.mg.gov.br/portalnfce",
    "PR": "http://www.fazenda.pr.gov.br/nfce/consulta",
    "SC": "https://sat.sef.sc.gov.br/nfce/consulta",
    "SVRS": "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx",
}

HOMOLOG_XNOME = "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
HOMOLOG_XPROD = "NOTA FISCAL EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"


def _tag(tag: str) -> str:
    return f"{{{NS_NFE}}}{tag}"


def _add(parent, tag: str, text: str = ""):
    el = etree.SubElement(parent, _tag(tag))
    if text is not None and text != "":
        el.text = str(text)
    return el


def _add_i(parent, tag: str, val: int):
    return _add(parent, tag, str(val))


def _add_d(parent, tag: str, val: float):
    return _add(parent, tag, f"{val:.2f}")


def _fmt_cnpj(cnpj: str) -> str:
    return "".join(c for c in str(cnpj) if c.isdigit()).zfill(14)[:14]


def _fmt_tel(tel: str) -> str:
    return "".join(c for c in tel if c.isdigit())[:14]


def _clean_ie(ie: str) -> str:
    """Remove pontuação da IE; preserva ISENTO."""
    if not ie:
        return ""
    ie = str(ie).strip()
    if ie.upper() == "ISENTO":
        return "ISENTO"
    return re.sub(r"[^0-9A-Za-z]", "", ie)[:14]


def _fmt_cest(cest) -> str:
    digits = "".join(c for c in str(cest) if c.isdigit())
    return digits.zfill(7)[:7] if digits else ""


def _fmt_ean(ean) -> str:
    raw = "".join(c for c in str(ean or "") if c.isdigit())
    return raw if raw else "SEM GTIN"


def _calc_dv(chave: str) -> str:
    pesos = [4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(c) * pesos[i % 11] for i, c in enumerate(chave))
    dv = 11 - (soma % 11)
    return str(0 if dv > 9 else dv)


def gerar_chave(cUF: int, dh_emi: str, cnpj: str, mod: str, serie: int, nNF: int, tpEmis: int, cNF: int) -> str:
    data = datetime.fromisoformat(dh_emi)
    ano_mes = data.strftime("%y%m")
    chave = f"{cUF:02d}{ano_mes}{_fmt_cnpj(cnpj)}{mod}{serie:03d}{nNF:09d}{tpEmis:01d}{cNF:08d}"
    return chave + _calc_dv(chave)


def _parse_endereco(endereco: str) -> dict:
    """Parse 'RUA RIO GRANDE DO SUL, 372, CENTRO, PASSO FUNDO/RS'"""
    if not endereco:
        return {"logradouro": "RUA", "numero": "S/N", "bairro": "CENTRO", "cidade": "", "uf": ""}
    parts = [p.strip() for p in endereco.split(",")]
    logradouro = parts[0] if len(parts) > 0 else "RUA"
    numero = parts[1] if len(parts) > 1 else "S/N"
    bairro = parts[2] if len(parts) > 2 else "CENTRO"
    cidade_uf = parts[3] if len(parts) > 3 else ""
    cidade = ""
    uf = ""
    if "/" in cidade_uf:
        cidade, uf = [p.strip() for p in cidade_uf.split("/", 1)]
    return {"logradouro": logradouro, "numero": numero, "bairro": bairro, "cidade": cidade, "uf": uf}


def _get_empresa() -> dict:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "dados", "empresa.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _uf_str(empresa: dict) -> str:
    uf_str = empresa.get("uf", "RS")
    if isinstance(uf_str, int):
        uf_map = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
                  21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
                  28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
                  42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}
        return uf_map.get(uf_str, "RS")
    return str(uf_str).upper()


def _csosn_por_cst(cst: str, crt: int) -> str:
    """Mapeia CST (regime normal) para CSOSN (Simples Nacional)."""
    if crt != 1:
        return cst
    tabela = {
        "00": "101", "10": "102", "20": "103", "30": "300", "40": "400",
        "41": "400", "50": "500", "51": "500", "60": "600", "70": "900",
        "90": "900",
    }
    return tabela.get(cst, "400")


def _cfop_nfce(uf_emit: str, uf_dest: str = "") -> str:
    """CFOP para NFC-e: 5102 (venda interna) ou 6102 (venda interestadual)."""
    if uf_dest and uf_dest != uf_emit:
        return "6102"
    return "5102"


def _csc_id(empresa: dict) -> str:
    raw = str(empresa.get("csc_id", "1") or "1").strip()
    cleaned = raw.lstrip("0") or "1"
    return cleaned


def _base_qr(uf: str, ambiente: int) -> str:
    uf = (uf or "RS").upper()
    urls = QRCODE_URLS.get(uf) or QRCODE_URLS.get("SVRS") or QRCODE_URLS["RS"]
    return urls.get(int(ambiente), urls.get(1))


def _url_chave(uf: str) -> str:
    uf = (uf or "RS").upper()
    return URL_CHAVE.get(uf) or URL_CHAVE.get("SVRS") or URL_CHAVE["RS"]


def gerar_url_qrcode(chave: str, ambiente: int, empresa: dict,
                     tp_emis: int = 1, dh_emi: str = "",
                     v_nf: float = 0.0, dig_val_b64: str = "") -> str:
    """
    Gera URL do QR Code NFC-e (versão 2).

    Online (tpEmis=1): chave|2|amb|csc_id + SHA1(params+csc)
    Offline: chave|2|amb|dia|vNF|digVal|csc_id + SHA1(params+csc)
    """
    if not empresa:
        empresa = _get_empresa()

    csc = str(empresa.get("csc", "") or "").strip()
    if not csc:
        raise ValueError("CSC não configurado na empresa (campo csc)")

    csc_id = _csc_id(empresa)
    uf = _uf_str(empresa)
    base = _base_qr(uf, ambiente)
    chave = "".join(c for c in str(chave) if c.isdigit())
    amb = str(int(ambiente))

    if int(tp_emis) == 1:
        params = f"{chave}|2|{amb}|{csc_id}"
    else:
        dia = "01"
        if dh_emi:
            try:
                dia = datetime.fromisoformat(dh_emi.replace("Z", "+00:00")[:19]).strftime("%d")
            except Exception:
                m = re.search(r"\d{4}-\d{2}-(\d{2})", dh_emi)
                if m:
                    dia = m.group(1)
        v_str = f"{float(v_nf):.2f}"
        dig = dig_val_b64 or ""
        params = f"{chave}|2|{amb}|{dia}|{v_str}|{dig}|{csc_id}"

    digest = hashlib.sha1((params + csc).encode("utf-8")).hexdigest().upper()
    sep = "&" if "?" in base else "?"
    # Bases que já terminam com ? ou &
    if base.endswith("?") or base.endswith("&"):
        return f"{base}p={params}|{digest}"
    return f"{base}{sep}p={params}|{digest}"


def anexar_inf_nfe_supl(xml_assinado: str, empresa: Optional[dict] = None,
                        ambiente: int = 2) -> str:
    """
    Anexa <infNFeSupl> com qrCode (CDATA) e urlChave em cada NFe.
    Ordem do schema TNFe: infNFe → Signature → infNFeSupl.
    """
    if empresa is None:
        empresa = _get_empresa()

    root = etree.fromstring(xml_assinado.encode("utf-8") if isinstance(xml_assinado, str) else xml_assinado)

    nfes = root.xpath(".//*[local-name()='NFe']")
    if not nfes and etree.QName(root).localname == "NFe":
        nfes = [root]

    for nfe in nfes:
        for old in nfe.xpath("./*[local-name()='infNFeSupl']"):
            nfe.remove(old)

        inf = None
        for child in nfe:
            if etree.QName(child).localname == "infNFe":
                inf = child
                break
        if inf is None:
            continue

        chave = (inf.get("Id") or "").replace("NFe", "")
        if not chave:
            continue

        ide = None
        total_el = None
        for child in inf:
            ln = etree.QName(child).localname
            if ln == "ide":
                ide = child
            elif ln == "total":
                total_el = child

        tp_emis = 1
        dh_emi = ""
        if ide is not None:
            for child in ide:
                ln = etree.QName(child).localname
                if ln == "tpEmis" and child.text:
                    tp_emis = int(child.text)
                elif ln == "dhEmi" and child.text:
                    dh_emi = child.text
                elif ln == "tpAmb" and child.text:
                    ambiente = int(child.text)

        v_nf = 0.0
        if total_el is not None:
            for icms_tot in total_el:
                if etree.QName(icms_tot).localname == "ICMSTot":
                    for v in icms_tot:
                        if etree.QName(v).localname == "vNF" and v.text:
                            v_nf = float(v.text)
                            break

        dig_val = ""
        for sig in nfe.xpath(".//*[local-name()='DigestValue']"):
            dig_val = sig.text or ""
            break

        url = gerar_url_qrcode(chave, ambiente, empresa, tp_emis=tp_emis,
                               dh_emi=dh_emi, v_nf=v_nf, dig_val_b64=dig_val)
        url_chave = _url_chave(_uf_str(empresa))

        supl = etree.Element(_tag("infNFeSupl"))
        qr = etree.SubElement(supl, _tag("qrCode"))
        qr.text = etree.CDATA(url)
        _add(supl, "urlChave", url_chave)

        signature = None
        for child in nfe:
            if etree.QName(child).localname == "Signature":
                signature = child
                break
        if signature is not None:
            signature.addnext(supl)
        else:
            nfe.append(supl)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()


def montar_envi_nfe(venda: dict, empresa: Optional[dict] = None,
                    ambiente: int = 2, serie: int = 1, numero: int = 1) -> str:
    if empresa is None:
        empresa = _get_empresa()

    now = datetime.now()
    dh_emi = now.strftime("%Y-%m-%dT%H:%M:%S-03:00")

    cUF = int(str(empresa.get("cod_municipio", "4314902"))[:2])
    cnpj_raw = _fmt_cnpj(empresa.get("cnpj", ""))
    mod = "65"
    tpEmis = 1
    cNF = (now.timetuple().tm_yday * 1000 + now.hour * 10) % 100000000
    chave = gerar_chave(cUF, now.isoformat(), cnpj_raw, mod, serie, numero, tpEmis, cNF)

    end = _parse_endereco(empresa.get("endereco", ""))
    uf_str = _uf_str(empresa)
    crt = int(empresa.get("crt", 1))

    root = etree.Element(_tag("enviNFe"), attrib={"xmlns": NS_NFE, "versao": "4.00"})
    _add_i(root, "idLote", venda.get("id", 1))
    _add(root, "indSinc", "1")

    nfe = etree.SubElement(root, _tag("NFe"))
    inf = etree.SubElement(nfe, _tag("infNFe"),
                           attrib={"Id": f"NFe{chave}", "versao": "4.00"})

    # ── ide ──
    ide = etree.SubElement(inf, _tag("ide"))
    _add_i(ide, "cUF", cUF)
    _add_i(ide, "cNF", cNF)
    _add(ide, "natOp", "VENDA")
    _add(ide, "mod", mod)
    _add_i(ide, "serie", serie)
    _add_i(ide, "nNF", numero)
    _add(ide, "dhEmi", dh_emi)
    # NFC-e: dhSaiEnt não é típico / omitido
    _add(ide, "tpNF", "1")
    _add(ide, "idDest", "1")
    _add_i(ide, "cMunFG", int(empresa.get("cod_municipio", "4314902")))
    _add(ide, "tpImp", "4")
    _add(ide, "tpEmis", str(tpEmis))
    _add(ide, "cDV", chave[-1])
    _add_i(ide, "tpAmb", ambiente)
    _add(ide, "finNFe", "1")
    _add(ide, "indFinal", "1")
    _add(ide, "indPres", "1")
    _add(ide, "procEmi", "0")
    _add(ide, "verProc", "FiscalBrasil ERP 1.0")

    # ── emit ──
    emit = etree.SubElement(inf, _tag("emit"))
    _add(emit, "CNPJ", cnpj_raw)
    nome_emit = empresa.get("nome", "")[:60]
    if ambiente == 2:
        nome_emit = HOMOLOG_XNOME
    _add(emit, "xNome", nome_emit)
    xfant = (empresa.get("nome_fantasia") or empresa.get("nome") or "")[:60]
    if xfant:
        _add(emit, "xFant", xfant)
    ee = etree.SubElement(emit, _tag("enderEmit"))
    _add(ee, "xLgr", end["logradouro"][:60])
    _add(ee, "nro", end["numero"][:10])
    _add(ee, "xBairro", end["bairro"][:60])
    _add_i(ee, "cMun", int(empresa.get("cod_municipio", "4314902")))
    _add(ee, "xMun", (empresa.get("municipio") or end["cidade"] or "")[:60])
    _add(ee, "UF", uf_str)
    cep = "".join(c for c in str(empresa.get("cep", "")) if c.isdigit())
    if not cep or len(cep) < 8:
        cep = "99000000"
    _add(ee, "CEP", cep.zfill(8)[:8])
    _add(ee, "cPais", "1058")
    _add(ee, "xPais", "BRASIL")
    fone = _fmt_tel(empresa.get("telefone", ""))
    if fone:
        _add(ee, "fone", fone)
    ie_raw = empresa.get("ie") or empresa.get("inscricao_est", "")
    ie = _clean_ie(ie_raw)
    if ie:
        _add(emit, "IE", ie)
    ie_substituto = empresa.get("inscricao_est_substituto", "")
    if ie_substituto:
        _add(emit, "IEST", _clean_ie(ie_substituto))
    cnae = empresa.get("cnae_prim_codigo", "")
    if cnae:
        cnae_digits = "".join(c for c in str(cnae) if c.isdigit())[:7]
        if cnae_digits:
            _add(emit, "CNAE", cnae_digits)
    _add_i(emit, "CRT", crt)

    # ── dest (Consumidor Final) ──
    dest = etree.SubElement(inf, _tag("dest"))
    cliente = venda.get("cliente", "Consumidor Final")
    if ambiente == 2:
        _add(dest, "CPF", "00000000000")
        _add(dest, "xNome", HOMOLOG_XNOME)
    elif cliente and cliente != "Consumidor Final":
        _add(dest, "CPF", "00000000000")
        _add(dest, "xNome", cliente[:60])
    else:
        _add(dest, "CPF", "00000000000")
        _add(dest, "xNome", "Consumidor Final")
    _add(dest, "indIEDest", "9")

    # ── det (itens) — sob infNFe ──
    total_prod = 0.0
    total_desc = 0.0
    itens = venda.get("itens", [])
    for idx, item in enumerate(itens, 1):
        prod_id = item.get("prod_id", idx)
        produto = item.get("produto", f"Produto {prod_id}")
        if ambiente == 2 and idx == 1:
            produto = HOMOLOG_XPROD
        qtd = float(item.get("qtd", 1))
        preco = float(item.get("preco", 0))
        subtotal = float(item.get("subtotal", qtd * preco))
        cst_item = str(item.get("cst", "400"))
        cfop_item = str(item.get("cfop", "5102"))
        origem = str(item.get("origem", item.get("orig", "0")))

        det = etree.SubElement(inf, _tag("det"), attrib={"nItem": str(idx)})
        pe = etree.SubElement(det, _tag("prod"))
        _add(pe, "cProd", str(prod_id))
        ean = _fmt_ean(item.get("ean", item.get("codigo_barras", "")))
        _add(pe, "cEAN", ean)
        _add(pe, "xProd", produto[:120])
        ncm_raw = str(item.get("ncm", "19069000")).replace(".", "").ljust(8, "0")[:8]
        _add(pe, "NCM", ncm_raw)
        cest = _fmt_cest(item.get("cest", ""))
        if cest:
            _add(pe, "CEST", cest)
        _add(pe, "CFOP", cfop_item if cfop_item else _cfop_nfce(uf_str))
        ucom = str(item.get("unidade", "UN"))[:6]
        _add(pe, "uCom", ucom)
        _add_d(pe, "qCom", qtd)
        _add_d(pe, "vUnCom", preco)
        _add_d(pe, "vProd", subtotal)
        ean_trib = _fmt_ean(item.get("ean_trib", item.get("ean", item.get("codigo_barras", ""))))
        _add(pe, "cEANTrib", ean_trib)
        _add(pe, "uTrib", ucom)
        _add_d(pe, "qTrib", qtd)
        _add_d(pe, "vUnTrib", preco)
        _add(pe, "indTot", "1")

        # ── imposto ──
        imp = etree.SubElement(det, _tag("imposto"))
        _add_d(imp, "vTotTrib", 0)

        icms = etree.SubElement(imp, _tag("ICMS"))
        if crt == 1:
            csosn = _csosn_por_cst(cst_item, crt)
            if csosn in ("101", "102", "103", "201", "202", "203"):
                sn = etree.SubElement(icms, _tag(f"ICMSSN{csosn}"))
                _add(sn, "orig", origem)
                _add(sn, "CSOSN", csosn)
                if csosn in ("101", "201"):
                    _add_d(sn, "pCredSN", 0)
                    _add_d(sn, "vCredICMSSN", 0)
            elif csosn in ("300", "400", "500"):
                sn = etree.SubElement(icms, _tag(f"ICMSSN{csosn}"))
                _add(sn, "orig", origem)
                _add(sn, "CSOSN", csosn)
                if csosn == "500":
                    _add_d(sn, "vBCSTRet", 0)
                    _add_d(sn, "pST", 0)
                    _add_d(sn, "vICMSSubstituto", 0)
            elif csosn == "900":
                sn = etree.SubElement(icms, _tag("ICMSSN900"))
                _add(sn, "orig", origem)
                _add(sn, "CSOSN", "900")
                _add_d(sn, "pICMS", 0)
                _add_d(sn, "vICMS", 0)
                _add_d(sn, "modBC", 0)
                _add_d(sn, "vBC", 0)
            else:
                sn = etree.SubElement(icms, _tag("ICMS40"))
                _add(sn, "orig", origem)
                _add(sn, "CST", cst_item)
        else:
            if cst_item in ("00", "10", "20", "30", "40", "41", "50", "51", "60", "70", "90"):
                icms_tag = f"ICMS{cst_item}"
                icms_el = etree.SubElement(icms, _tag(icms_tag))
                _add(icms_el, "orig", origem)
                _add(icms_el, "CST", cst_item)
                if cst_item in ("00", "20"):
                    alq = float(item.get("icms_alq", 0))
                    _add_i(icms_el, "modBC", 3)
                    _add_d(icms_el, "vBC", subtotal)
                    _add_d(icms_el, "pICMS", alq)
                    _add_d(icms_el, "vICMS", subtotal * alq / 100)
                else:
                    _add_d(icms_el, "vICMSDeson", 0)
                    _add(icms_el, "motDesICMS", "6")
            else:
                icms_el = etree.SubElement(icms, _tag("ICMS40"))
                _add(icms_el, "orig", origem)
                _add(icms_el, "CST", cst_item)
                _add_d(icms_el, "vICMSDeson", 0)
                _add(icms_el, "motDesICMS", "6")

        # PIS
        pis = etree.SubElement(imp, _tag("PIS"))
        pis_cst = str(item.get("pis_cst", "99"))
        if pis_cst in ("01", "02", "03", "04", "05", "06", "07", "08", "09"):
            pis_alq = etree.SubElement(pis, _tag(f"PIS{pis_cst}"))
            _add(pis_alq, "CST", pis_cst)
            _add_d(pis_alq, "vBC", subtotal)
            _add_d(pis_alq, "pPIS", 0)
            _add_d(pis_alq, "vPIS", 0)
        else:
            pis_outr = etree.SubElement(pis, _tag("PISOutr"))
            _add(pis_outr, "CST", pis_cst)
            _add_d(pis_outr, "vBC", 0)
            _add_d(pis_outr, "pPIS", 0)
            _add_d(pis_outr, "vPIS", 0)

        # COFINS
        cofins = etree.SubElement(imp, _tag("COFINS"))
        cof_cst = str(item.get("cofins_cst", "99"))
        if cof_cst in ("01", "02", "03", "04", "05", "06", "07", "08", "09"):
            cof_alq = etree.SubElement(cofins, _tag(f"COFINS{cof_cst}"))
            _add(cof_alq, "CST", cof_cst)
            _add_d(cof_alq, "vBC", subtotal)
            _add_d(cof_alq, "pCOFINS", 0)
            _add_d(cof_alq, "vCOFINS", 0)
        else:
            cof_outr = etree.SubElement(cofins, _tag("COFINSOutr"))
            _add(cof_outr, "CST", cof_cst)
            _add_d(cof_outr, "vBC", 0)
            _add_d(cof_outr, "pCOFINS", 0)
            _add_d(cof_outr, "vCOFINS", 0)

        total_prod += subtotal

    # ── total ──
    total = etree.SubElement(inf, _tag("total"))
    it = etree.SubElement(total, _tag("ICMSTot"))
    _add_d(it, "vBC", 0)
    _add_d(it, "vICMS", 0)
    _add_d(it, "vICMSDeson", 0)
    _add_d(it, "vFCP", 0)
    _add_d(it, "vBCST", 0)
    _add_d(it, "vST", 0)
    _add_d(it, "vFCPST", 0)
    _add_d(it, "vFCPSTRet", 0)
    _add_d(it, "vProd", total_prod)
    _add_d(it, "vFrete", 0)
    _add_d(it, "vSeg", 0)
    _add_d(it, "vDesc", total_desc)
    _add_d(it, "vII", 0)
    _add_d(it, "vIPI", 0)
    _add_d(it, "vIPIDevol", 0)
    _add_d(it, "vPIS", 0)
    _add_d(it, "vCOFINS", 0)
    _add_d(it, "vOutro", 0)
    _add_d(it, "vNF", total_prod - total_desc)

    # ── transp ──
    transp = etree.SubElement(inf, _tag("transp"))
    _add(transp, "modFrete", "9")

    # ── pag ──
    pag = etree.SubElement(inf, _tag("pag"))
    dp = etree.SubElement(pag, _tag("detPag"))
    _add(dp, "indPag", "0")
    tpag = "01"
    fp = venda.get("forma_pg", "") or ""
    mapa_pag = {"DINHEIRO": "01", "CHEQUE": "02", "CARTAO": "03", "CREDITO": "03", "DEBITO": "03",
                "PIX": "17", "BOLETO": "15", "CREDIARIO": "15"}
    for chave_pg, cod in mapa_pag.items():
        if chave_pg in fp.upper().replace("Ã", "A").replace("Ç", "C"):
            tpag = cod
            break
    _add(dp, "tPag", tpag)
    _add_d(dp, "vPag", total_prod - total_desc)

    # ── infAdic ──
    inf_adic = etree.SubElement(inf, _tag("infAdic"))
    _add(inf_adic, "infCpl", f"Venda #{venda.get('id', '')} - {fp}")

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()
