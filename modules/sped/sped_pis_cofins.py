import json
import os
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def gerar_sped_pis(empresa: dict, competencia: str = "", nfce_list: list = None, nfe_list: list = None) -> str:
    if not competencia:
        competencia = date.today().strftime("%Y%m")
    cnpj = "".join(c for c in empresa.get("cnpj", "") if c.isdigit()).zfill(14)
    nome = empresa.get("nome", "")[:60]
    crt = empresa.get("crt", 1)

    lines = []
    lines.append(f"|0000|001|1|{competencia}|0|{nome}|{cnpj}|||1|PIS|\n")

    if nfce_list:
        for n in nfce_list:
            valor = float(n.get("vNF", n.get("valor", 0)))
            data = n.get("data", "")[:10]
            lines.append(f"|0100|1|{n.get('numero', 0)}|{data}|{valor:.2f}|{valor:.2f}|0.00|0.00|0.00|\n")

    if nfe_list:
        for n in nfe_list:
            valor = float(n.get("vNF", n.get("valor", 0)))
            data = n.get("data", "")[:10]
            lines.append(f"|0100|0|{n.get('numero', 0)}|{data}|{valor:.2f}|0.00|0.00|0.00|\n")

    lines.append(f"|9990|{len(lines)}|\n")
    lines.append(f"|9999|{len(lines) + 2}|\n")

    return "".join(lines)
