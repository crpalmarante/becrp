import io
import os
import base64
from datetime import datetime
from weasyprint import HTML
import qrcode

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _qr_code_b64(chave: str, ambiente: int, uf: str = "RS", modelo: str = "65",
                  qr_url: str = "", empresa: dict = None) -> str:
    url = (qr_url or "").strip()
    if not url and modelo != "55":
        try:
            from modules.sefaz import nfce_xml
            emp = empresa or {}
            if not emp.get("csc"):
                # fallback: carrega empresa.json via nfce_xml
                emp = nfce_xml._get_empresa()
            if emp.get("uf") is None and uf:
                emp = dict(emp)
                emp["uf"] = uf
            url = nfce_xml.gerar_url_qrcode(chave, ambiente, emp)
        except Exception:
            url = ""
    if not url:
        url = f"https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx?p={chave}|2|{ambiente}|1"
        if ambiente == 2:
            url = f"https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx?p={chave}|2|{ambiente}|1"
    img = qrcode.make(url, box_size=4)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _format_cnpj(v: str) -> str:
    d = "".join(c for c in v if c.isdigit()).zfill(14)
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def _format_cpf(v: str) -> str:
    d = "".join(c for c in v if c.isdigit()).zfill(11)
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def _format_cep(v: str) -> str:
    d = "".join(c for c in v if c.isdigit()).zfill(8)
    return f"{d[:5]}-{d[5:]}"


def _format_telefone(v: str) -> str:
    d = "".join(c for c in v if c.isdigit())[:11]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return d


def _parse_endereco(endereco: str) -> dict:
    if not endereco:
        return {"logradouro": "RUA", "numero": "S/N", "bairro": "CENTRO", "cidade": "", "uf": ""}
    parts = [p.strip() for p in endereco.split(",")]
    logradouro = parts[0] if len(parts) > 0 else "RUA"
    numero = parts[1] if len(parts) > 1 else "S/N"
    bairro = parts[2] if len(parts) > 2 else "CENTRO"
    cidade = ""
    uf = ""
    if len(parts) > 3 and "/" in parts[3]:
        cidade, uf = [p.strip() for p in parts[3].split("/", 1)]
    return {"logradouro": logradouro, "numero": numero, "bairro": bairro, "cidade": cidade, "uf": uf}


def _gerar_nfce(nota: dict, empresa: dict) -> bytes:
    chave = nota.get("chave", "")
    ambiente = int(nota.get("ambiente", 2))
    numero = nota.get("numero", 0)
    serie = nota.get("serie", 1)
    protocolo = nota.get("protocolo", nota.get("nProt", ""))
    data_str = nota.get("data", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    total = float(nota.get("vNF", nota.get("valor", 0)))
    status = nota.get("status", "AUTORIZADO")
    qr_url = nota.get("qr_code") or nota.get("qrCode") or nota.get("url_qrcode") or ""
    if not qr_url and nota.get("xml"):
        try:
            from lxml import etree
            root = etree.fromstring(nota["xml"].encode("utf-8") if isinstance(nota["xml"], str) else nota["xml"])
            for el in root.xpath(".//*[local-name()='qrCode']"):
                qr_url = (el.text or "").strip()
                if qr_url:
                    break
        except Exception:
            pass
    uf_str = empresa.get("uf", "RS")
    if isinstance(uf_str, int):
        uf_map = {11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",21:"MA",22:"PI",23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",28:"SE",29:"BA",31:"MG",32:"ES",33:"RJ",35:"SP",41:"PR",42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF"}
        uf_str = uf_map.get(uf_str, "RS")
    qr_b64 = _qr_code_b64(chave, ambiente, uf=uf_str, modelo="65",
                          qr_url=qr_url, empresa=empresa)

    end = _parse_endereco(empresa.get("endereco", ""))
    cnpj = _format_cnpj(empresa.get("cnpj", ""))
    cep = _format_cep(empresa.get("cep", "99000000"))
    tel = _format_telefone(empresa.get("telefone", ""))

    if not total and nota.get("itens"):
        total = sum(float(item.get("subtotal", item.get("vProd", 0))) for item in nota["itens"])

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
    @page {{ size: 80mm 297mm; margin: 2mm; }}
    body {{ font-family: 'Courier New', monospace; font-size: 10px; line-height: 1.3; margin: 0; padding: 0; color: #000; }}
    .center {{ text-align: center; }}
    .bold {{ font-weight: bold; }}
    .header {{ font-size: 12px; margin-bottom: 4px; }}
    .line {{ border-top: 1px dashed #000; margin: 4px 0; }}
    .tot {{ font-size: 14px; font-weight: bold; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 9px; }}
    td {{ padding: 1px 2px; }}
    .item-qtd {{ text-align: right; width: 50px; }}
    .item-val {{ text-align: right; width: 70px; }}
    .qr {{ text-align: center; margin: 6px 0; }}
    .qr img {{ width: 120px; height: 120px; }}
    .chave {{ font-size: 11px; letter-spacing: 1px; word-break: break-all; }}
    .proto {{ font-size: 9px; }}
</style></head><body>
<div class="center header">
    <div class="bold">{empresa.get("nome", "")[:40]}</div>
    <div>{cnpj}</div>
    <div>{end["logradouro"]}, {end["numero"]} - {end["bairro"]}</div>
    <div>{end["cidade"]} {uf_str} - CEP {cep}</div>
    <div>Tel: {tel}</div>
</div>
<div class="line"></div>
<div class="center"><span class="bold">DANFE NFC-e</span> - Documento Auxiliar</div>
<div class="center" style="font-size:8px">NFC-e - Modelo 65 - Emitido em {data_str}</div>
<div class="line"></div>
<table>
    <tr><td><b>Número:</b> {serie:03d}-{numero:09d}</td><td><b>Série:</b> {serie:03d}</td></tr>
    <tr><td><b>Status:</b> {status}</td><td><b>Ambiente:</b> {"Produção" if ambiente==1 else "Homologação"}</td></tr>
</table>
<div class="line"></div>
"""
    itens = nota.get("itens", [])
    if itens:
        html += '<table><tr><th style="text-align:left">Item</th><th style="text-align:right">Qtd</th><th style="text-align:right">Valor</th></tr>'
        for i, item in enumerate(itens, 1):
            nome = item.get("produto", item.get("xProd", f"Item {i}"))[:35]
            qtd = float(item.get("qtd", item.get("qCom", 1)))
            val = float(item.get("subtotal", item.get("vProd", 0)))
            html += f'<tr><td>{i}. {nome}</td><td class="item-qtd">{qtd:.3f}</td><td class="item-val">R$ {val:.2f}</td></tr>'
        html += "</table>"

    html += f"""
<div class="line"></div>
<table>
    <tr><td><b>Forma de pagamento:</b> {nota.get("tPag", nota.get("forma_pg", "N/A"))}</td></tr>
</table>
<div class="tot center">Valor Total: R$ {total:.2f}</div>
<div class="line"></div>
<div class="center"><b>Chave de Acesso</b></div>
<div class="center chave">{chave}</div>
<div class="center proto">Protocolo: {protocolo}</div>
<div class="qr"><img src="data:image/png;base64,{qr_b64}" alt="QR Code"></div>
<div class="center" style="font-size:7px;color:#666">
    Consulte pela chave em www.sefaz.rs.gov.br/NFCE<br>
    Ou pelo QR Code acima<br>
    {datetime.now().strftime('%d/%m/%Y %H:%M')} | FiscalBrasil ERP
</div>
</body></html>"""

    return HTML(string=html).write_pdf()


def _gerar_nfe(nota: dict, empresa: dict) -> bytes:
    chave = nota.get("chave", "")
    ambiente = int(nota.get("ambiente", 2))
    numero = nota.get("numero", 0)
    serie = nota.get("serie", 1)
    protocolo = nota.get("protocolo", nota.get("nProt", ""))
    data_str = nota.get("data", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    total = float(nota.get("vNF", nota.get("valor", 0)))
    status = nota.get("status", "AUTORIZADO")

    end = _parse_endereco(empresa.get("endereco", ""))
    cnpj = _format_cnpj(empresa.get("cnpj", ""))
    cep = _format_cep(empresa.get("cep", "99000000"))
    tel = _format_telefone(empresa.get("telefone", ""))
    uf_str = empresa.get("uf", "RS")
    if isinstance(uf_str, int):
        uf_map = {11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",21:"MA",22:"PI",23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",28:"SE",29:"BA",31:"MG",32:"ES",33:"RJ",35:"SP",41:"PR",42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF"}
        uf_str = uf_map.get(uf_str, "RS")

    if not total and nota.get("itens"):
        total = sum(float(item.get("subtotal", item.get("vProd", 0))) for item in nota["itens"])

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
    @page {{ size: A4; margin: 1.5cm; }}
    body {{ font-family: 'Courier New', monospace; font-size: 11px; line-height: 1.4; margin: 0; padding: 0; color: #000; }}
    .center {{ text-align: center; }}
    .bold {{ font-weight: bold; }}
    .header {{ border: 2px solid #000; padding: 10px; margin-bottom: 8px; }}
    .header .nome {{ font-size: 16px; }}
    .header .info {{ font-size: 10px; }}
    .line {{ border-top: 1px solid #000; margin: 6px 0; }}
    .tot {{ font-size: 14px; font-weight: bold; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 9px; }}
    th {{ border: 1px solid #000; padding: 3px; background: #eee; font-size: 9px; }}
    td {{ border: 1px solid #000; padding: 2px 4px; }}
    .right {{ text-align: right; }}
    .chave {{ font-size: 12px; letter-spacing: 1px; word-break: break-all; text-align: center; margin: 8px 0; }}
    .proto {{ font-size: 9px; text-align: center; }}
    .qrcode {{ text-align: right; }}
    .qrcode img {{ width: 80px; height: 80px; }}
</style></head><body>
<div class="header center">
    <div class="nome bold">{empresa.get("nome", "")[:60]}</div>
    <div class="info">CNPJ: {cnpj} | IE: {empresa.get("inscricao_est", "ISENTO")}</div>
    <div class="info">{end["logradouro"]}, {end["numero"]} - {end["bairro"]} - {end["cidade"]}/{uf_str} - CEP {cep}</div>
    <div class="info">Tel: {tel}</div>
</div>
<div class="center" style="font-size:14px;font-weight:bold;margin:8px 0">DANFE - Documento Auxiliar da Nota Fiscal Eletrônica</div>
<div class="center" style="font-size:10px;margin-bottom:8px">NF-e - Modelo 55 - Série {serie:03d} - Número {numero:09d}</div>
<table>
    <tr><td><b>Chave de Acesso:</b></td><td colspan="3">{chave}</td></tr>
    <tr><td><b>Data/Hora Emissão:</b></td><td>{data_str}</td><td><b>Status:</b></td><td>{status}</td></tr>
    <tr><td><b>Protocolo:</b></td><td>{protocolo}</td><td><b>Ambiente:</b></td><td>{"Produção" if ambiente==1 else "Homologação"}</td></tr>
</table>
<div class="line"></div>
<h4 style="margin:4px 0">Itens</h4>
<table>
    <tr><th>#</th><th>Código</th><th>Descrição</th><th>NCM</th><th>CFOP</th><th>Qtd</th><th>Un</th><th>Vl. Unit</th><th>Vl. Total</th></tr>
"""
    itens = nota.get("itens", [])
    for i, item in enumerate(itens, 1):
        nome = item.get("produto", item.get("xProd", f"Item {i}"))[:40]
        cod = str(item.get("prod_id", item.get("cProd", i)))
        ncm = str(item.get("ncm", ""))[:8]
        cfop = str(item.get("cfop", ""))
        qtd = float(item.get("qtd", item.get("qCom", 1)))
        un = str(item.get("unidade", "UN"))[:3]
        preco = float(item.get("preco", item.get("vUnCom", 0)))
        subtotal = float(item.get("subtotal", item.get("vProd", qtd * preco)))
        html += f'<tr><td>{i}</td><td>{cod}</td><td>{nome}</td><td>{ncm}</td><td>{cfop}</td><td class="right">{qtd:.3f}</td><td>{un}</td><td class="right">{preco:.2f}</td><td class="right">{subtotal:.2f}</td></tr>'

    html += f"""</table>
<div class="line"></div>
<table>
    <tr><td style="width:70%"><b>Valor Total dos Produtos:</b></td><td class="right" style="width:30%">R$ {float(nota.get("vProd", total)):.2f}</td></tr>
    <tr><td><b>Valor Total da Nota:</b></td><td class="right">R$ {total:.2f}</td></tr>
</table>
<div class="line"></div>
<div class="center" style="font-size:8px;color:#666;margin-top:20px">
    Consulte pela chave em www.sefaz.rs.gov.br/NFCe<br>
    {datetime.now().strftime('%d/%m/%Y %H:%M')} | FiscalBrasil ERP
</div>
</body></html>"""

    return HTML(string=html).write_pdf()


def gerar(nota: dict, empresa: dict, modelo: str = "65") -> bytes:
    if modelo == "55":
        return _gerar_nfe(nota, empresa)
    return _gerar_nfce(nota, empresa)
