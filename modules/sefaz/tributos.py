TABELA_ICMS_INTERNO = {
    "RS": {"reducao_pb": 0, "aliq": 17},
    "SC": {"reducao_pb": 0, "aliq": 17},
    "PR": {"reducao_pb": 0, "aliq": 18},
    "SP": {"reducao_pb": 0, "aliq": 18},
    "RJ": {"reducao_pb": 0, "aliq": 18},
    "MG": {"reducao_pb": 0, "aliq": 18},
    "default": {"reducao_pb": 0, "aliq": 17},
}

TABELA_ICMS_INTERESTADUAL = {
    "RO": 12, "AC": 12, "AM": 12, "RR": 12, "PA": 12, "AP": 12, "TO": 12,
    "MA": 12, "PI": 12, "CE": 12, "RN": 12, "PB": 12, "PE": 12, "AL": 12,
    "SE": 12, "BA": 12, "MG": 12, "ES": 12, "RJ": 12, "SP": 12, "PR": 12,
    "SC": 12, "RS": 12, "MS": 12, "MT": 12, "GO": 12, "DF": 12,
}

TABELA_PIS = {
    "cumulativo": 0.65,
    "nao_cumulativo": 1.65,
}

TABELA_COFINS = {
    "cumulativo": 3.0,
    "nao_cumulativo": 7.6,
}

TABELA_IPI = {
    "default": 5.0,
}

TABELA_ISS = {
    "default": 2.0,
    "RS": 2.0,
    "SP": 5.0,
    "RJ": 5.0,
}


def calcular_icms(valor_base: float, uf_origem: str, uf_destino: str, regime: str = "SN",
                  tem_st: bool = False, alq_st: float = 0, difal: bool = False) -> dict:
    alq_interna = TABELA_ICMS_INTERNO.get(uf_origem, TABELA_ICMS_INTERNO["default"])["aliq"]
    alq_interest = TABELA_ICMS_INTERESTADUAL.get(uf_origem, 12)

    if uf_origem == uf_destino:
        alq = alq_interna
        v_icms = valor_base * alq / 100
        return {"cst": "00" if regime != "SN" else "101", "alq": alq, "vBC": valor_base, "vICMS": v_icms,
                "vBCST": 0, "vST": 0, "regime": regime}

    alq = alq_interest
    v_icms = valor_base * alq / 100
    v_difal = 0
    if difal:
        dif_alq = alq_interna - alq_interest
        v_difal = valor_base * dif_alq / 100
    return {"cst": "00" if regime != "SN" else "101", "alq": alq, "vBC": valor_base, "vICMS": v_icms,
            "vBCST": 0, "vST": 0, "vDifal": v_difal, "regime": regime}


def calcular_pis_cofins(valor_base: float, regime: str = "cumulativo") -> dict:
    alq_pis = TABELA_PIS.get(regime, TABELA_PIS["cumulativo"])
    alq_cofins = TABELA_COFINS.get(regime, TABELA_COFINS["cumulativo"])
    return {
        "pis_cst": "01" if regime == "nao_cumulativo" else "99",
        "cofins_cst": "01" if regime == "nao_cumulativo" else "99",
        "vBC_PIS": valor_base, "pPIS": alq_pis, "vPIS": valor_base * alq_pis / 100,
        "vBC_COFINS": valor_base, "pCOFINS": alq_cofins, "vCOFINS": valor_base * alq_cofins / 100,
    }


def calcular_ipi(valor_base: float, alq: float = 0) -> dict:
    if not alq:
        alq = TABELA_IPI["default"]
    return {"vBC": valor_base, "pIPI": alq, "vIPI": valor_base * alq / 100}


def calcular_iss(valor_base: float, uf: str = "", alq: float = 0) -> dict:
    if not alq:
        alq = TABELA_ISS.get(uf, TABELA_ISS["default"])
    return {"vBC": valor_base, "pISS": alq, "vISS": valor_base * alq / 100}


def calcular_tributos(item: dict, uf_origem: str, uf_destino: str, regime: str = "SN",
                       regime_pis: str = "cumulativo") -> dict:
    valor = float(item.get("subtotal", float(item.get("preco", 0)) * float(item.get("qtd", 1))))
    icms = calcular_icms(valor, uf_origem, uf_destino, regime)
    pis_cofins = calcular_pis_cofins(valor, regime_pis)
    ipi = calcular_ipi(valor)
    return {**icms, **pis_cofins, **ipi}
