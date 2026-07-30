import json
import os
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _reg(line: str) -> str:
    return f"{line}\n"


def gerar_sped_fiscal(empresa: dict, competencia: str = "", nfce_list: list = None, nfe_list: list = None) -> str:
    if not competencia:
        competencia = date.today().strftime("%Y%m")
    ano, mes = competencia[:4], competencia[4:6]
    cnpj = "".join(c for c in empresa.get("cnpj", "") if c.isdigit()).zfill(14)
    ie = empresa.get("inscricao_est", "").strip() or "ISENTO"
    nome = empresa.get("nome", "")[:60]
    mun = empresa.get("municipio", empresa.get("endereco", "RUA,0,CENTRO").split(",")[3].split("/")[0].strip() if "/" in empresa.get("endereco", "") else "")
    uf = empresa.get("uf", "RS")
    if isinstance(uf, int):
        uf_map = {11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",21:"MA",22:"PI",23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",28:"SE",29:"BA",31:"MG",32:"ES",33:"RJ",35:"SP",41:"PR",42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF"}
        uf = uf_map.get(uf, "RS")

    lines = []
    lines.append(_reg(f"|0000|001|2|{competencia}|0|{nome}|{cnpj}|{ie}|{uf}|{ie}|1|"))
    lines.append(_reg(f"|0001|0|"))
    lines.append(_reg(f"|9900|0000|1|"))

    if nfce_list:
        for n in nfce_list:
            chave = n.get("chave", "")
            valor = n.get("vNF", n.get("valor", 0))
            data = n.get("data", "")[:10]
            cfop = "5102"
            lines.append(_reg(f"|C100|0|1|{n.get('numero', 0)}|{n.get('serie', 1)}|0|{n.get('numero', 0)}|{data}|{data}||{valor}|{cfop}|0.00|"))
            for i, item in enumerate(n.get("itens", []), 1):
                prod_name = item.get("produto", item.get("xProd", ""))[:60]
                ncm = str(item.get("ncm", ""))[:8]
                qtd = float(item.get("qtd", item.get("qCom", 1)))
                vprod = float(item.get("subtotal", item.get("vProd", 0)))
                lines.append(_reg(f"|C170|0|{i}|{item.get('prod_id', i)}|{prod_name}|{ncm}|{ncm}||{cfop}|{qtd:.4f}|UN|{vprod:.2f}|{vprod:.2f}|1|{vprod:.2f}|0.00|0.00|0.00|0.00|0.00|"))
            lines.append(_reg(f"|C190|0|{cfop}|0|0.00|{valor:.2f}|0.00|{valor:.2f}|0.00|0.00|0.00|0.00|"))

    if nfe_list:
        for n in nfe_list:
            chave = n.get("chave", "")
            valor = n.get("vNF", n.get("valor", 0))
            data = n.get("data", "")[:10]
            lines.append(_reg(f"|C100|1|0|{n.get('numero', 0)}|{n.get('serie', 1)}|0|{chave}|{data}|{data}||0.00|0.00|0.00|"))
            lines.append(_reg(f"|C190|1|5102|0|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|"))

    lines.append(_reg(f"|9900|C100|{lines.count('|C100|')}|"))
    lines.append(_reg(f"|9900|C170|{lines.count('|C170|')}|"))
    lines.append(_reg(f"|9900|C190|{lines.count('|C190|')}|"))
    lines.append(_reg(f"|9990|{len(lines)}|"))
    lines.append(_reg(f"|9999|{len(lines) + 2}|"))

    return "".join(lines)
