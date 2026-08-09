import json
import os
import re
from datetime import datetime
from typing import Optional
from lxml import etree

from .tributos import calcular_ibs_cbs

NS_NFE = "http://www.portalfiscal.inf.br/nfe"


def _tag(tag: str) -> str:
    return f"{{{NS_NFE}}}{tag}"


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
    return cnpj.zfill(14)[:14]


def _fmt_cpf(cpf: str) -> str:
    return cpf.zfill(11)[:11]


def _fmt_tel(tel: str) -> str:
    return "".join(c for c in tel if c.isdigit())[:14]


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


def _uf_str(empresa) -> str:
    uf = empresa.get("uf", "RS")
    if isinstance(uf, int):
        uf_map = {11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",
                   21:"MA",22:"PI",23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",
                   28:"SE",29:"BA",31:"MG",32:"ES",33:"RJ",35:"SP",41:"PR",
                   42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF"}
        uf = uf_map.get(uf, "RS")
    return str(uf)


def _csosn_por_cst(cst: str, crt: int) -> str:
    if crt != 1:
        return cst
    tabela = {
        "00": "101", "10": "102", "20": "103", "30": "300", "40": "400",
        "41": "400", "50": "500", "51": "500", "60": "600", "70": "900",
        "90": "900",
    }
    return tabela.get(cst, "400")


def montar_envi_nfe(
    venda: dict,
    empresa: Optional[dict] = None,
    ambiente: int = 2,
    serie: int = 1,
    numero: int = 1,
    sincrono: bool = False,
) -> str:
    if empresa is None:
        empresa = _get_empresa()

    now = datetime.now()
    dh_emi = now.strftime("%Y-%m-%dT%H:%M:%S-03:00")

    cUF = int(empresa.get("cod_municipio", "4314902")[:2])
    cnpj_raw = _fmt_cnpj(empresa.get("cnpj", ""))
    mod = "55"
    tpEmis = 1
    cNF = (now.timetuple().tm_yday * 1000 + now.hour * 10) % 100000000
    chave = gerar_chave(cUF, now.isoformat(), cnpj_raw, mod, serie, numero, tpEmis, cNF)

    end = _parse_endereco(empresa.get("endereco", ""))
    uf_str = _uf_str(empresa)
    crt = int(empresa.get("crt", 1))

    root = etree.Element(_tag("enviNFe"), attrib={"xmlns": NS_NFE, "versao": "4.00"})
    _add_i(root, "idLote", venda.get("id", 1))
    _add(root, "indSinc", "1" if sincrono else "0")

    nfe = etree.SubElement(root, _tag("NFe"))
    inf = etree.SubElement(nfe, _tag("infNFe"), attrib={"Id": f"NFe{chave}", "versao": "4.00"})

    ide = etree.SubElement(inf, _tag("ide"))
    _add_i(ide, "cUF", cUF)
    _add_i(ide, "cNF", cNF)
    _add(ide, "natOp", venda.get("natOp", "VENDA"))
    _add(ide, "mod", mod)
    _add_i(ide, "serie", serie)
    _add_i(ide, "nNF", numero)
    _add(ide, "dhEmi", dh_emi)
    _add(ide, "dhSaiEnt", dh_emi)
    _add(ide, "tpNF", str(venda.get("tpNF", "1")))
    _add(ide, "idDest", str(venda.get("idDest", "1")))
    _add_i(ide, "cMunFG", int(empresa.get("cod_municipio", "4314902")))
    _add(ide, "tpImp", "1")
    _add(ide, "tpEmis", str(tpEmis))
    _add(ide, "cDV", chave[-1])
    _add_i(ide, "tpAmb", ambiente)
    _add(ide, "finNFe", venda.get("finNFe", "1"))
    _add(ide, "indFinal", venda.get("indFinal", "1"))
    _add(ide, "indPres", venda.get("indPres", "1"))
    _add(ide, "procEmi", "0")
    _add(ide, "verProc", "FiscalBrasil ERP 1.0")

    emit = etree.SubElement(inf, _tag("emit"))
    _add(emit, "CNPJ", cnpj_raw)
    _add(emit, "xNome", empresa.get("nome", "")[:60])
    _add(emit, "xFant", (empresa.get("nome", "")[:60]))
    ee = etree.SubElement(emit, _tag("enderEmit"))
    _add(ee, "xLgr", end["logradouro"][:60])
    _add(ee, "nro", end["numero"][:10])
    _add(ee, "xBairro", end["bairro"][:60])
    _add_i(ee, "cMun", int(empresa.get("cod_municipio", "4314902")))
    _add(ee, "xMun", (end["cidade"] or empresa.get("municipio", ""))[:60])
    _add(ee, "UF", uf_str)
    cep = empresa.get("cep", "").replace("-", "")
    if not cep or len(cep.strip()) < 8:
        cep = "99000000"
    _add(ee, "CEP", cep.zfill(8)[:8])
    _add(ee, "cPais", "1058")
    _add(ee, "xPais", "BRASIL")
    _add(ee, "fone", _fmt_tel(empresa.get("telefone", "")))
    _add(emit, "IE", empresa.get("inscricao_est", "").replace(".", "").replace("/", "").strip()[:14])
    ie_substituto = empresa.get("inscricao_est_substituto", "")
    if ie_substituto:
        _add(emit, "IEST", ie_substituto.strip()[:14])
    cnae = empresa.get("cnae_prim_codigo", "")
    if cnae:
        _add(emit, "CNAEFiscal", str(cnae).strip()[:7])
    _add_i(emit, "CRT", crt)

    dest = etree.SubElement(inf, _tag("dest"))
    cliente = venda.get("cliente", "")
    doc_dest = venda.get("documento", "")

    if doc_dest:
        doc_clean = "".join(c for c in doc_dest if c.isdigit())
        if len(doc_clean) == 14:
            _add(dest, "CNPJ", doc_clean)
            _add(dest, "xNome", cliente[:60] if cliente else "Destinatário")
        elif len(doc_clean) == 11:
            _add(dest, "CPF", doc_clean)
            _add(dest, "xNome", cliente[:60] if cliente else "Consumidor")
        else:
            _add(dest, "CPF", doc_clean.zfill(11)[:11])
            _add(dest, "xNome", cliente[:60] if cliente else "Consumidor Final")
    else:
        _add(dest, "CPF", "00000000000")
        _add(dest, "xNome", cliente[:60] if cliente else "Consumidor Final")

    if not doc_dest or len(doc_clean) == 11:
        _add(dest, "indIEDest", "9")
    else:
        ie_dest = venda.get("ie_dest", "")
        if ie_dest:
            _add(dest, "IE", ie_dest.strip()[:14])
            _add(dest, "indIEDest", "1")
        else:
            _add(dest, "indIEDest", "2")

    end_dest = venda.get("endereco_dest", "")
    if end_dest:
        ed = _parse_endereco(end_dest)
        if ed.get("logradouro") or ed.get("cidade"):
            de = etree.SubElement(dest, _tag("enderDest"))
            _add(de, "xLgr", ed["logradouro"][:60])
            _add(de, "nro", ed["numero"][:10])
            _add(de, "xBairro", ed["bairro"][:60])
            _add(de, "xMun", (ed["cidade"] or "DESCONHECIDA")[:60])
            _add(de, "UF", ed["uf"] if ed["uf"] else uf_str)
            _add(de, "cPais", "1058")
            _add(de, "xPais", "BRASIL")
            if venda.get("cep_dest"):
                _add(de, "CEP", "".join(c for c in venda["cep_dest"] if c.isdigit())[:8])

    total_prod = 0.0
    total_desc = 0.0
    total_ipi = 0.0
    total_trib = 0.0
    total_cbs = 0.0
    total_ibs = 0.0

    for idx, item in enumerate(venda.get("itens", []), 1):
        prod_id = item.get("prod_id", idx)
        produto = item.get("produto", f"Produto {prod_id}")
        qtd = float(item.get("qtd", 1))
        preco = float(item.get("preco", 0))
        subtotal = float(item.get("subtotal", qtd * preco))
        desconto_item = float(item.get("desconto", 0))
        valor_liquido = subtotal - desconto_item
        cst_item = str(item.get("cst", "400"))
        cfop_item = str(item.get("cfop", "5102"))

        det = etree.SubElement(nfe, _tag("det"), attrib={"nItem": str(idx)})
        pe = etree.SubElement(det, _tag("prod"))
        _add(pe, "cProd", str(prod_id))
        _add(pe, "cEAN", str(item.get("ean", item.get("codigo_barras", "")))[:14])
        _add(pe, "xProd", produto[:120])
        ncm_raw = str(item.get("ncm", "19069000")).replace(".", "").ljust(8, "0")[:8]
        _add(pe, "NCM", ncm_raw)
        cest = item.get("cest", "")
        if cest:
            _add(pe, "CEST", str(cest)[:7])
        _add(pe, "CFOP", cfop_item if cfop_item else "5102")
        ucom = str(item.get("unidade", "UN"))[:6]
        _add(pe, "uCom", ucom)
        _add_d(pe, "qCom", qtd)
        _add_d(pe, "vUnCom", preco)
        _add_d(pe, "vProd", subtotal)
        _add(pe, "cEANTrib", str(item.get("ean_trib", ""))[:14])
        _add(pe, "uTrib", ucom)
        _add_d(pe, "qTrib", qtd)
        _add_d(pe, "vUnTrib", preco)
        if desconto_item > 0:
            _add_d(pe, "vDesc", desconto_item)
        _add(pe, "indTot", "1")

        imp = etree.SubElement(det, _tag("imposto"))
        _add_d(imp, "vTotTrib", 0)

        icms = etree.SubElement(imp, _tag("ICMS"))
        if crt == 1:
            csosn = _csosn_por_cst(cst_item, crt)
            if csosn in ("101", "102", "103", "201", "202", "203"):
                sn = etree.SubElement(icms, _tag(f"ICMSSN{csosn}"))
                _add(sn, "orig", "0")
                _add(sn, "CSOSN", csosn)
                if csosn in ("101", "201"):
                    _add_d(sn, "pCredSN", 0)
                    _add_d(sn, "vCredICMSSN", 0)
            elif csosn in ("300", "400", "500"):
                sn = etree.SubElement(icms, _tag(f"ICMSSN{csosn}"))
                _add(sn, "orig", "0")
                _add(sn, "CSOSN", csosn)
                if csosn == "500":
                    _add_d(sn, "vBCSTRet", 0)
                    _add_d(sn, "pST", 0)
                    _add_d(sn, "vICMSSubstituto", 0)
            elif csosn == "900":
                sn = etree.SubElement(icms, _tag("ICMSSN900"))
                _add(sn, "orig", "0")
                _add(sn, "CSOSN", "900")
                _add_d(sn, "pICMS", 0)
                _add_d(sn, "vICMS", 0)
                _add_d(sn, "modBC", 0)
                _add_d(sn, "vBC", 0)
            else:
                sn = etree.SubElement(icms, _tag("ICMS40"))
                _add(sn, "orig", "0")
                _add(sn, "CST", cst_item)
        else:
            if cst_item in ("00", "10", "20", "30", "40", "41", "50", "51", "60", "70", "90"):
                icms_tag = f"ICMS{cst_item}"
                icms_el = etree.SubElement(icms, _tag(icms_tag))
                _add(icms_el, "orig", "0")
                _add(icms_el, "CST", cst_item)
                if cst_item in ("00", "20"):
                    alq = float(item.get("icms_alq", 0))
                    _add_i(icms_el, "modBC", 3)
                    _add_d(icms_el, "vBC", valor_liquido)
                    _add_d(icms_el, "pICMS", alq)
                    _add_d(icms_el, "vICMS", valor_liquido * alq / 100)
                else:
                    _add_d(icms_el, "vICMSDeson", 0)
                    _add(icms_el, "motDesICMS", "6")
            else:
                icms_el = etree.SubElement(icms, _tag("ICMS40"))
                _add(icms_el, "orig", "0")
                _add(icms_el, "CST", cst_item)
                _add_d(icms_el, "vICMSDeson", 0)
                _add(icms_el, "motDesICMS", "6")

        pis = etree.SubElement(imp, _tag("PIS"))
        pis_cst = str(item.get("pis_cst", "99"))
        if pis_cst in ("01", "02", "03", "04", "05", "06", "07", "08", "09"):
            pis_alq = etree.SubElement(pis, _tag(f"PIS{pis_cst}"))
            _add(pis_alq, "CST", pis_cst)
            _add_d(pis_alq, "vBC", valor_liquido)
            _add_d(pis_alq, "pPIS", 0)
            _add_d(pis_alq, "vPIS", 0)
        else:
            pis_outr = etree.SubElement(pis, _tag("PISOutr"))
            _add(pis_outr, "CST", pis_cst)
            _add_d(pis_outr, "vBC", 0)
            _add_d(pis_outr, "pPIS", 0)
            _add_d(pis_outr, "vPIS", 0)

        cofins = etree.SubElement(imp, _tag("COFINS"))
        cof_cst = str(item.get("cofins_cst", "99"))
        if cof_cst in ("01", "02", "03", "04", "05", "06", "07", "08", "09"):
            cof_alq = etree.SubElement(cofins, _tag(f"COFINS{cof_cst}"))
            _add(cof_alq, "CST", cof_cst)
            _add_d(cof_alq, "vBC", valor_liquido)
            _add_d(cof_alq, "pCOFINS", 0)
            _add_d(cof_alq, "vCOFINS", 0)
        else:
            cof_outr = etree.SubElement(cofins, _tag("COFINSOutr"))
            _add(cof_outr, "CST", cof_cst)
            _add_d(cof_outr, "vBC", 0)
            _add_d(cof_outr, "pCOFINS", 0)
            _add_d(cof_outr, "vCOFINS", 0)

        if item.get("ipi_cst") or item.get("ipi_alq") or item.get("ipi"):
            ipi_alq = float(item.get("ipi_alq") or item.get("ipi") or 0)
            ipi = etree.SubElement(imp, _tag("IPI"))
            _add(ipi, "cEnq", str(item.get("ipi_enquadramento", "999")))
            if ipi_alq > 0:
                trib = etree.SubElement(ipi, _tag("IPITrib"))
                _add(trib, "CST", str(item.get("ipi_cst", "50")))
                _add_d(trib, "vBC", valor_liquido)
                _add_d(trib, "pIPI", ipi_alq)
                valor_ipi = valor_liquido * ipi_alq / 100
                _add_d(trib, "vIPI", valor_ipi)
                total_ipi += valor_ipi
            else:
                pin = etree.SubElement(ipi, _tag("IPINT"))
                _add(pin, "CST", str(item.get("ipi_cst", "53")))

        # Reforma Tributária: IBS/CBS (informado em infAdProd)
        ibs_cbs = calcular_ibs_cbs(valor_liquido, ncm=ncm_raw)
        total_cbs += float(ibs_cbs.get("vCBS", 0))
        total_ibs += float(ibs_cbs.get("vIBS", 0))
        total_trib += float(ibs_cbs.get("vCBS", 0)) + float(ibs_cbs.get("vIBS", 0))
        inf_ad_prod = etree.SubElement(det, _tag("infAdProd"))
        inf_ad_prod.text = (
            f"IBS/CBS: BC {ibs_cbs['vBC_ibs_cbs']:.2f}; "
            f"CBS {ibs_cbs['pCBS']:.2f}% = {ibs_cbs['vCBS']:.2f}; "
            f"IBS {ibs_cbs['pIBS']:.2f}% = {ibs_cbs['vIBS']:.2f}"
        )

        total_prod += subtotal
        total_desc += desconto_item
        total_trib += float(item.get("vTotTrib", 0))

    total = etree.SubElement(nfe, _tag("total"))
    it = etree.SubElement(total, _tag("ICMSTot"))
    _add_d(it, "vBC", 0)
    _add_d(it, "vICMS", 0)
    _add_d(it, "vICMSDeson", 0)
    _add_d(it, "vFCP", 0)
    _add_d(it, "vBCST", 0)
    _add_d(it, "vST", 0)
    _add_d(it, "vFCPST", float(venda.get("vFCPST", 0)))
    _add_d(it, "vFCPSTRet", float(venda.get("vFCPSTRet", 0)))
    _add_d(it, "vProd", total_prod)
    _add_d(it, "vFrete", float(venda.get("frete", 0)))
    _add_d(it, "vSeg", float(venda.get("seguro", 0)))
    _add_d(it, "vDesc", total_desc)
    _add_d(it, "vII", 0)
    _add_d(it, "vIPI", total_ipi)
    _add_d(it, "vIPIDevol", 0)
    _add_d(it, "vPIS", 0)
    _add_d(it, "vCOFINS", 0)
    _add_d(it, "vOutro", float(venda.get("outras_despesas", 0)))
    vnf = total_prod - total_desc + float(venda.get("frete", 0)) + float(venda.get("seguro", 0)) + float(venda.get("outras_despesas", 0))
    _add_d(it, "vNF", vnf)
    _add_d(it, "vTotTrib", total_trib)

    # Armazena IBS/CBS em extensão do total para consumo interno (não enviado ao SEFAZ como tag oficial)
    venda["_ibs_cbs"] = {
        "vBC_ibs_cbs": round(vnf, 2),
        "vCBS": round(total_cbs, 2),
        "vIBS": round(total_ibs, 2),
        "pCBS": ibs_cbs.get("pCBS", 0.6),
        "pIBS": ibs_cbs.get("pIBS", 17.0),
    }

    transp = etree.SubElement(nfe, _tag("transp"))
    _add(transp, "modFrete", str(venda.get("modFrete", "9")))

    transporta = venda.get("transporta", {})
    if transporta and transporta.get("cnpj", ""):
        tr = etree.SubElement(transp, _tag("transporta"))
        cnpj_transp = "".join(c for c in transporta["cnpj"] if c.isdigit())
        _add(tr, "CNPJ", cnpj_transp[:14])
        _add(tr, "xNome", transporta.get("nome", "")[:60])
        if transporta.get("ie"):
            _add(tr, "IE", transporta["ie"].strip()[:14])
        _add(tr, "xEnder", transporta.get("endereco", "")[:60])
        _add(tr, "xMun", transporta.get("cidade", "")[:60])
        _add(tr, "UF", transporta.get("uf", uf_str))

    cobranca = venda.get("cobranca", {})
    if cobranca or venda.get("fatura"):
        cob = etree.SubElement(nfe, _tag("cob"))
        fat = cobranca.get("fatura", venda.get("fatura", {}))
        if fat:
            f = etree.SubElement(cob, _tag("fat"))
            _add_d(f, "nFat", fat.get("numero", str(numero)))
            _add_d(f, "vOrig", vnf)
            _add_d(f, "vDesc", 0)
            _add_d(f, "vLiq", vnf)
        for dup in cobranca.get("duplicatas", []):
            d = etree.SubElement(cob, _tag("dup"))
            _add(d, "nDup", str(dup.get("numero", ""))[:60])
            _add(d, "dVenc", dup.get("vencimento", now.strftime("%Y-%m-%d")))
            _add_d(d, "vDup", float(dup.get("valor", vnf)))

    pag = etree.SubElement(nfe, _tag("pag"))
    dp = etree.SubElement(pag, _tag("detPag"))
    tpag = "01"
    fp = venda.get("forma_pg", "")
    mapa_pag = {"DINHEIRO":"01","CHEQUE":"02","CARTAO":"03","CREDITO":"03","DEBITO":"03",
                "PIX":"17","BOLETO":"15","CREDIARIO":"15"}
    for chave_pg, cod in mapa_pag.items():
        if chave_pg in fp.upper().replace("Ã","A").replace("Ç","C"):
            tpag = cod
            break
    _add(dp, "tPag", tpag)
    if tpag == "17" and venda.get("pix_chave"):
        _add(dp, "xPag", str(venda["pix_chave"])[:60])
    _add_d(dp, "vPag", vnf)

    inf_adic = etree.SubElement(nfe, _tag("infAdic"))
    inf_cpl = f"Venda #{venda.get('id', '')} - {fp}"
    if venda.get("infCpl"):
        inf_cpl += f" - {venda['infCpl']}"
    inf_cpl += (
        f" | IBS/CBS: BC {venda['_ibs_cbs']['vBC_ibs_cbs']:.2f};"
        f" CBS {venda['_ibs_cbs']['pCBS']:.2f}%={venda['_ibs_cbs']['vCBS']:.2f};"
        f" IBS {venda['_ibs_cbs']['pIBS']:.2f}%={venda['_ibs_cbs']['vIBS']:.2f}"
    )
    _add(inf_adic, "infCpl", inf_cpl[:5000])
    if venda.get("infAdFisco"):
        _add(inf_adic, "infAdFisco", venda["infAdFisco"][:2000])

    compra = venda.get("compra", {})
    if compra and (compra.get("xPed") or compra.get("nPed")):
        comp = etree.SubElement(nfe, _tag("compra"))
        if compra.get("xPed"):
            _add(comp, "xPed", compra["xPed"][:60])
        if compra.get("nPed"):
            _add(comp, "nPed", str(compra["nPed"])[:60])

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()


def montar_lote_nfe(notas: list, empresa: Optional[dict] = None, ambiente: int = 2, sincrono: bool = False) -> str:
    if empresa is None:
        empresa = _get_empresa()

    root = etree.Element(_tag("enviNFe"), attrib={"xmlns": NS_NFE, "versao": "4.00"})
    id_lote = int(datetime.now().timestamp() * 1000) % 100000000
    _add_i(root, "idLote", id_lote)
    _add(root, "indSinc", "1" if sincrono else "0")

    for venda in notas:
        nfe_str = montar_envi_nfe(venda, empresa, ambiente, sincrono=sincrono)
        nfe_root = etree.fromstring(nfe_str.encode())
        for nfe in nfe_root.findall(_tag("NFe")):
            root.append(nfe)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()
