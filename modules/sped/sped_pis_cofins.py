import json
import os
from datetime import date

from modules.sped.sped_fiscal import (
    _digits, _parse_endereco, _parse_nota, _uf_str, _num_text, _ultimo_dia,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _desc_unidade(u):
    mapa = {
        "UN": "UNIDADE", "UNID": "UNIDADE", "PC": "PECA", "PCT": "PACOTE",
        "CX": "CAIXA", "CXA": "CAIXA", "KG": "QUILOGRAMA", "GR": "GRAMA",
        "G": "GRAMA", "LT": "LITRO", "ML": "MILILITRO", "M": "METRO",
        "MT": "METRO", "M2": "METRO QUADRADO", "M3": "METRO CUBICO",
        "DZ": "DUZIA", "FD": "FARDO", "RL": "ROLO", "L": "LITRO",
    }
    return mapa.get(u, u or "UNIDADE")


def gerar_sped_pis(empresa=None, competencia="", nfce_list=None, nfe_list=None,
                   produtos=None, contatos=None) -> str:
    if empresa is None:
        empresa = _load_json(os.path.join(BASE_DIR, "dados", "empresa.json"))
    if not competencia:
        competencia = date.today().strftime("%Y%m")
    if produtos is None:
        produtos = _load_json(os.path.join(BASE_DIR, "dados", "produtos.json")).get("produtos", [])
    if contatos is None:
        contatos = _load_json(os.path.join(BASE_DIR, "data", "contatos.json"))

    notas = [(_parse_nota(n), "65") for n in (nfce_list or [])]
    notas += [(_parse_nota(n), "55") for n in (nfe_list or [])]

    cnpj = _digits(empresa.get("cnpj", "")).zfill(14)
    ie = (empresa.get("inscricao_est") or "").strip()
    uf = _uf_str(empresa.get("uf"))
    nome = (empresa.get("nome") or "")[:60]
    cod_mun = str(empresa.get("cod_municipio") or empresa.get("cod_mun") or "0000000").zfill(7)[:7]
    cnae = str(empresa.get("cnae_prim_codigo") or "")[:7]
    cep = _digits(empresa.get("cep", "")).zfill(8)[:8]
    end = _parse_endereco(empresa.get("endereco"))

    dt_ini = f"{competencia[:4]}-{competencia[4:6]}-01"
    dt_fim = _ultimo_dia(competencia)

    unidades = {}
    for nota, _ in notas:
        for it in nota["itens"]:
            unidades[it["u"] or "UN"] = _desc_unidade(it["u"] or "UN")

    participantes = []
    if isinstance(contatos, dict):
        for cod, c in contatos.items():
            if not isinstance(c, dict):
                continue
            doc = _digits(c.get("documento"))
            endc = _parse_endereco(c.get("endereco"))
            participantes.append({
                "cod": str(cod),
                "nome": (c.get("nome") or "")[:60],
                "cnpj": doc if len(doc) == 14 else "",
                "cpf": doc if len(doc) == 11 else "",
                "ie": _digits(c.get("ie"))[:14],
                "end": endc["logradouro"][:60],
                "num": endc["numero"][:10],
                "bairro": endc["bairro"][:60],
            })

    # ── Bloco 0 ──
    b0 = []
    b0.append(f"|0000|010|1|{dt_ini}|{dt_fim}|{nome}|{cnpj}|{uf}|{ie}|{cod_mun}|{empresa.get('im','')[:9]}|{empresa.get('suframa','')[:9]}|0|1|{cod_mun}|")
    b0.append("|0001|0|")
    b0.append("|0100|||||||||||")
    b0.append(f"|0140|0|{nome}|{cnpj}|{uf}|{ie}|{cod_mun}|{empresa.get('im','')[:9]}|{empresa.get('suframa','')[:9]}|{cnae}|{cep}|")
    for p in participantes:
        b0.append(f"|0150|{p['cod']}|{p['nome']}|1058|{p['cnpj']}|{p['cpf']}|{p['ie']}|||{p['end']}|{p['num']}||{p['bairro']}|")
    for u, desc in unidades.items():
        b0.append(f"|0190|{u}|{desc}|")
    for pr in produtos:
        if not isinstance(pr, dict):
            continue
        cod_item = str(pr.get("id", pr.get("cod_item", "")))
        desc = (pr.get("nome") or pr.get("descricao") or "")[:120]
        ncm = _digits(pr.get("ncm", ""))[:8]
        barra = _digits(pr.get("codigo_barras", ""))[:14]
        un = (pr.get("unidade") or "UN")[:6]
        vl_unit = _num_text(pr.get("preco_custo", pr.get("preco", 0)))
        b0.append(f"|0200|{cod_item}|{desc}|00|{ncm}|{pr.get('ex_ipi','')[:3]}|{barra}|{un}|{vl_unit}||||0|")
    b0.append("|0400|VENDA|VENDA DE MERCADORIAS|")
    b0.append(f"|0990|{len(b0) + 1}|")

    # ── Bloco M (apuração PIS/COFINS) ──
    bm = []
    bm.append("|M001|0|")
    grupos = {}
    for nota, _ in notas:
        for it in nota["itens"]:
            cst = it["cst"] or "99"
            g = grupos.setdefault(cst, {"bc": 0.0, "pis": 0.0, "cofins": 0.0})
            g["bc"] += it["vProd"]
    for cst, g in sorted(grupos.items()):
        bm.append(
            f"|M100|1||{_num_text(g['bc'])}|0.00||0.00|0.00|{cst}|||0.00|0.00|0.00|0.00|0.00|0.00|"
        )
        bm.append(
            f"|M500|1||{_num_text(g['bc'])}|0.00||0.00|0.00|{cst}|||0.00|0.00|0.00|0.00|0.00|0.00|"
        )
    if not grupos:
        bm.append("|M100|1||0.00|0.00||0.00|0.00|99|||||")
        bm.append("|M500|1||0.00|0.00||0.00|0.00|99|||||")
    bm.append(f"|M990|{len(bm) + 1}|")

    # ── Bloco 9 ──
    linhas = b0 + bm
    counts = {}
    for ln in linhas:
        reg = ln.split("|")[1]
        if reg and reg not in ("0990", "M990", "9900", "9990", "9999"):
            counts[reg] = counts.get(reg, 0) + 1
    b9 = ["|9001|0|"]
    for reg in sorted(counts):
        b9.append(f"|9900|{reg}|{counts[reg]}|")
    b9.append(f"|9990|{len(b9) + 1}|")

    linhas += b9
    linhas.append(f"|9999|{len(linhas) + 1}|")
    return "\n".join(linhas) + "\n"
