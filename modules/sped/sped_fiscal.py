import json
import os
from datetime import date, timedelta
from lxml import etree

NS = "http://www.portalfiscal.inf.br/nfe"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _digits(s):
    return "".join(c for c in str(s or "") if c.isdigit())


def _num_text(v, dec=2):
    try:
        return f"{float(v):.{dec}f}"
    except (TypeError, ValueError):
        return "0.00"


def _ultimo_dia(competencia):
    ano, mes = int(competencia[:4]), int(competencia[4:6])
    if mes == 12:
        return f"{ano}-12-31"
    return (date(ano, mes + 1, 1) - timedelta(days=1)).isoformat()


def _parse_endereco(endereco):
    if not endereco:
        return {"logradouro": "", "numero": "", "bairro": "", "cidade": "", "uf": ""}
    parts = [p.strip() for p in str(endereco).split(",")]
    r = {
        "logradouro": parts[0] if len(parts) > 0 else "",
        "numero": parts[1] if len(parts) > 1 else "",
        "bairro": parts[2] if len(parts) > 2 else "",
        "cidade": "",
        "uf": "",
    }
    cidade_uf = parts[3] if len(parts) > 3 else ""
    if "/" in cidade_uf:
        r["cidade"], r["uf"] = [p.strip() for p in cidade_uf.split("/", 1)]
    return r


def _uf_str(uf):
    if isinstance(uf, int):
        uf_map = {11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",
                   21:"MA",22:"PI",23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",
                   28:"SE",29:"BA",31:"MG",32:"ES",33:"RJ",35:"SP",41:"PR",
                   42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF"}
        uf = uf_map.get(uf, "")
    return str(uf or "")


def _txt(parent, tag):
    if parent is None:
        return ""
    el = parent.find(f"{{{NS}}}{tag}")
    return (el.text or "").strip() if el is not None else ""


def _num(parent, tag):
    try:
        return float(_txt(parent, tag) or 0)
    except ValueError:
        return 0.0


def _parse_nota(n):
    """Normaliza registro de NF-e/NFC-e (dict estruturado ou XML) para uso no SPED."""
    if not isinstance(n, dict):
        n = {}

    if n.get("itens"):
        itens = []
        for it in n["itens"]:
            itens.append({
                "cProd": it.get("prod_id", it.get("cProd", "")),
                "xProd": (it.get("produto") or it.get("xProd") or "")[:120],
                "ncm": _digits(it.get("ncm") or it.get("NCM"))[:8],
                "cfop": str(it.get("cfop") or it.get("CFOP") or "5102"),
                "u": (it.get("unidade") or it.get("uCom") or "UN")[:6],
                "qtd": float(it.get("qtd") or it.get("qCom") or 1),
                "vProd": float(it.get("subtotal") or it.get("vProd") or 0),
                "cst": str(it.get("cst") or it.get("CST") or ""),
                "pICMS": float(it.get("icms_alq") or 0),
                "vICMS": float(it.get("vICMS") or it.get("icms_valor") or 0),
            })
        return {
            "chave": n.get("chave", ""),
            "numero": n.get("numero", 0),
            "serie": n.get("serie", 1),
            "data": (n.get("data") or "")[:10],
            "vNF": float(n.get("vNF") or n.get("valor") or sum(i["vProd"] for i in itens)),
            "vICMS": sum(i["vICMS"] for i in itens),
            "itens": itens,
        }

    res = {
        "chave": n.get("chave", ""),
        "numero": n.get("numero", 0),
        "serie": n.get("serie", 1),
        "data": (n.get("data") or "")[:10],
        "vNF": float(n.get("vNF") or n.get("valor") or 0),
        "vICMS": 0.0,
        "itens": [],
    }
    xml = n.get("xml") or ""
    if not xml:
        return res
    try:
        root = etree.fromstring(xml.encode())
    except Exception:
        return res

    inf = root.find(f".//{{{NS}}}infNFe")
    if inf is None:
        return res

    ide = inf.find(f"{{{NS}}}ide")
    if ide is not None:
        res["numero"] = int(_txt(ide, "nNF") or res["numero"])
        res["serie"] = int(_txt(ide, "serie") or res["serie"])
        dh = _txt(ide, "dhEmi") or _txt(ide, "dhSaiEnt")
        if dh:
            res["data"] = dh[:10]

    total = inf.find(f".//{{{NS}}}ICMSTot")
    if total is not None and _num(total, "vNF"):
        res["vNF"] = _num(total, "vNF")

    for det in inf.findall(f"{{{NS}}}det"):
        prod = det.find(f"{{{NS}}}prod")
        if prod is None:
            continue
        imp = det.find(f"{{{NS}}}imposto")
        icms = imp.find(f"{{{NS}}}ICMS") if imp is not None else None
        cst, pICMS, vICMS = "", 0.0, 0.0
        if icms is not None and len(icms):
            g = icms[0]
            cst = _txt(g, "CST") or _txt(g, "CSOSN")
            pICMS = _num(g, "pICMS")
            vICMS = _num(g, "vICMS")
        res["itens"].append({
            "cProd": _txt(prod, "cProd"),
            "xProd": _txt(prod, "xProd")[:120],
            "ncm": _digits(_txt(prod, "NCM"))[:8],
            "cfop": _txt(prod, "CFOP") or "5102",
            "u": _txt(prod, "uCom")[:6] or "UN",
            "qtd": _num(prod, "qCom"),
            "vProd": _num(prod, "vProd"),
            "cst": cst,
            "pICMS": pICMS,
            "vICMS": vICMS,
        })
        res["vICMS"] += vICMS
    return res


def _desc_unidade(u):
    mapa = {
        "UN": "UNIDADE", "UNID": "UNIDADE", "PC": "PECA", "PCT": "PACOTE",
        "CX": "CAIXA", "CXA": "CAIXA", "KG": "QUILOGRAMA", "GR": "GRAMA",
        "G": "GRAMA", "LT": "LITRO", "ML": "MILILITRO", "M": "METRO",
        "MT": "METRO", "M2": "METRO QUADRADO", "M3": "METRO CUBICO",
        "DZ": "DUZIA", "FD": "FARDO", "RL": "ROLO", "L": "LITRO",
    }
    return mapa.get(u, u or "UNIDADE")


def gerar_sped_fiscal(empresa=None, competencia="", nfce_list=None, nfe_list=None,
                      produtos=None, contatos=None, inventario=None) -> str:
    if empresa is None:
        empresa = _load_json(os.path.join(BASE_DIR, "dados", "empresa.json"))
    if not competencia:
        competencia = date.today().strftime("%Y%m")
    if produtos is None:
        produtos = _load_json(os.path.join(BASE_DIR, "dados", "produtos.json")).get("produtos", [])
    if contatos is None:
        contatos = _load_json(os.path.join(BASE_DIR, "data", "contatos.json"))
    if inventario is None:
        inv = _load_json(os.path.join(BASE_DIR, "data", "inventory_balances.json"))
        inventario = (inv.get("por_estabelecimento") or {}).get("matriz", {})

    notas = [(_parse_nota(n), "65") for n in (nfce_list or [])]
    notas += [(_parse_nota(n), "55") for n in (nfe_list or [])]

    cnpj = _digits(empresa.get("cnpj", "")).zfill(14)
    ie = (empresa.get("inscricao_est") or "").strip()
    uf = _uf_str(empresa.get("uf"))
    nome = (empresa.get("nome") or "")[:60]
    fantasia = (empresa.get("nome_fantasia") or "")[:60]
    cod_mun = str(empresa.get("cod_municipio") or empresa.get("cod_mun") or "0000000").zfill(7)[:7]
    end = _parse_endereco(empresa.get("endereco"))
    cep = _digits(empresa.get("cep", "")).zfill(8)[:8]
    fone = _digits(empresa.get("telefone", ""))[:11]
    email = (empresa.get("email") or "")[:60]

    dt_ini = f"{competencia[:4]}-{competencia[4:6]}-01"
    dt_fim = _ultimo_dia(competencia)

    # ── unidades e participantes ──
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
            cnpj_p = doc if len(doc) == 14 else ""
            cpf_p = doc if len(doc) == 11 else ""
            endc = _parse_endereco(c.get("endereco"))
            participantes.append({
                "cod": str(cod),
                "nome": (c.get("nome") or "")[:60],
                "cnpj": cnpj_p,
                "cpf": cpf_p,
                "ie": _digits(c.get("ie"))[:14],
                "end": endc["logradouro"][:60],
                "num": endc["numero"][:10],
                "bairro": endc["bairro"][:60],
            })

    # ── Bloco 0 ──
    b0 = []
    b0.append(f"|0000|017|0|{dt_ini}|{dt_fim}|{nome}|{cnpj}|{uf}|{ie}|{cod_mun}|{empresa.get('im','')[:9]}|{empresa.get('suframa','')[:9]}|0|0|1|")
    b0.append("|0001|0|")
    b0.append(f"|0005|{fantasia}|{cep}|{end['logradouro'][:60]}|{end['numero'][:10]}|{end.get('complemento','')[:60]}|{end['bairro'][:60]}|{fone}|{email}|")
    b0.append("|0100|||||||||||")
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
    b0.append(f"|0990|{len(b0) + 1}|")

    # ── Bloco C ──
    bc = []
    if notas:
        bc.append("|C001|0|")
        for nota, mod in notas:
            data = nota["data"] or f"{competencia[:4]}-{competencia[4:6]}-01"
            bc.append(
                f"|C100|1|0||{mod}|100|{nota['serie']}|{nota['numero']}|{nota['chave']}|"
                f"{data}|{data}|{_num_text(nota['vNF'])}|0|0.00|0.00|0.00|"
                f"{_num_text(nota['vICMS'])}|0.00|0.00|0.00|0.00|0.00|0.00|0.00|"
            )
            for i, it in enumerate(nota["itens"], 1):
                bc.append(
                    f"|C170|{i}|{it['cProd']}|{it['xProd']}|{_num_text(it['qtd'], 4)}|{it['u']}|"
                    f"{_num_text(it['vProd'])}|0.00|0|{it['cst'] or '00'}|{it['cfop']}|"
                    f"|{_num_text(it['vProd'])}|{_num_text(it['pICMS'])}|{_num_text(it['vICMS'])}|"
                    f"0.00|0.00|0.00|0|||0.00|0.00|0.00|99|0.00|0.00|0.00|99|0.00|0.00|0.00||"
                )
            resumo = {}
            for it in nota["itens"]:
                chave = (it["cst"] or "00", it["cfop"])
                r = resumo.setdefault(chave, {"vl": 0.0, "bc": 0.0, "icms": 0.0, "aliq": it.get("pICMS", 0)})
                r["vl"] += it["vProd"]
                r["bc"] += it["vProd"]
                r["icms"] += it["vICMS"]
            for (cst, cfop), r in resumo.items():
                bc.append(
                    f"|C190|{cst}|{cfop}|{_num_text(r['aliq'])}|{_num_text(r['vl'])}|"
                    f"{_num_text(r['bc'])}|{_num_text(r['icms'])}|0.00|0.00|0.00|0.00|"
                )
        bc.append(f"|C990|{len(bc) + 1}|")
    else:
        bc.append("|C001|1|")

    # ── Bloco E (apuração ICMS) ──
    be = []
    vl_deb = sum(nota["vICMS"] for nota, _ in notas if nota["itens"])
    vl_cred = 0.0
    for en in (_load_json(os.path.join(BASE_DIR, "dados", "nfe_entrada.json")).get("nfe_entradas", []) or []):
        try:
            vl_cred += float((en.get("total") or {}).get("vICMS") or 0)
        except (TypeError, ValueError):
            pass
    vl_recolher = max(0.0, vl_deb - vl_cred)
    be.append("|E001|0|")
    be.append(f"|E100|{dt_ini}|{dt_fim}|")
    be.append(
        f"|E110|{dt_ini}|{dt_fim}|{_num_text(vl_deb)}|{_num_text(vl_cred)}|0.00|0.00|0.00|0.00|"
        f"0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|{_num_text(vl_recolher)}|"
        f"0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|"
    )
    be.append(f"|E990|{len(be) + 1}|")

    # ── Bloco E300: Apuração por UF ──
    be300 = []
    if vl_deb or vl_cred:
        be300.append(f"|E300|{uf}|{dt_ini}|{dt_fim}|")
        be300.append(
            f"|E310|{uf}|0|{_num_text(vl_deb)}|{_num_text(vl_cred)}|0.00|0.00|0.00|0.00|"
            f"0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|{_num_text(vl_recolher)}|0.00|0.00|"
        )
        be.append(f"|E990|{len(be300) + len(be)}|")
        be = be[:1] + be300 + be[1:]

    # ── Bloco G (crédito ativo imobilizado — sem dados) ──
    bg = ["|G001|1|"]

    # ── Bloco H (inventário) ──
    bh = []
    if inventario:
        bh.append("|H001|0|")
        bh.append(f"|H005|{dt_fim}|0.00|01|")
        produtos_por_id = {str(pr.get("id")): pr for pr in produtos if isinstance(pr, dict)}
        for cod_item, qtd in (inventario.items() if isinstance(inventario, dict) else []):
            try:
                qtd = float(qtd)
            except (TypeError, ValueError):
                continue
            if qtd <= 0:
                continue
            pr = produtos_por_id.get(str(cod_item), {})
            un = (pr.get("unidade") or "UN")[:6]
            vl_unit = float(pr.get("preco_custo") or pr.get("preco") or 0)
            ind_prop = "0" if vl_unit else "1"
            bh.append(
                f"|H010|{cod_item}|{un}|{_num_text(qtd, 4)}|{_num_text(vl_unit)}|"
                f"{_num_text(qtd * vl_unit)}|{ind_prop}||0||"
            )
        bh.append(f"|H990|{len(bh) + 1}|")
    else:
        bh.append("|H001|1|")

    # ── Bloco K (estoque escriturado) ──
    bk = []
    if produtos:
        bk.append("|K001|0|")
        bk.append(f"|K100|{dt_ini}|{dt_fim}|")
        produtos_por_id = {str(pr.get("id")): pr for pr in produtos if isinstance(pr, dict)}
        for cod_item, qtd in (inventario.items() if isinstance(inventario, dict) else []):
            try:
                qtd = float(qtd)
            except (TypeError, ValueError):
                continue
            if qtd <= 0:
                continue
            pr = produtos_por_id.get(str(cod_item), {})
            un = (pr.get("unidade") or "UN")[:6]
            vl_unit = float(pr.get("preco_custo") or pr.get("preco") or 0)
            bk.append(
                f"|K200|{cod_item}|{dt_fim}|{un}|{_num_text(qtd, 4)}|{_num_text(vl_unit)}|"
                f"{_num_text(qtd * vl_unit)}|01|"
            )
        bk.append(f"|K990|{len(bk) + 1}|")
    else:
        bk.append("|K001|1|")

    # ── Bloco 9 ──
    linhas = b0 + bc + be + bg + bh + bk
    counts = {}
    for ln in linhas:
        reg = ln.split("|")[1]
        if reg and reg not in ("0990", "C990", "E990", "G990", "H990", "K990", "9900", "9990", "9999"):
            counts[reg] = counts.get(reg, 0) + 1
    b9 = ["|9001|0|"]
    for reg in sorted(counts):
        b9.append(f"|9900|{reg}|{counts[reg]}|")
    b9.append(f"|9990|{len(b9) + 1}|")

    linhas += b9
    linhas.append(f"|9999|{len(linhas) + 1}|")
    return "\n".join(linhas) + "\n"
