import json
import os
from datetime import datetime
from lxml import etree

NS_NFSE = "http://www.abrasf.org.br/nfse"
NS_NFSE_XSD = "http://www.abrasf.org.br/nfse.xsd"


def _tag(tag: str) -> str:
    return f"{{{NS_NFSE}}}{tag}"


def _add(parent, tag: str, text: str = ""):
    el = etree.SubElement(parent, _tag(tag))
    if text:
        el.text = text
    return el


def _fmt_cnpj(cnpj: str) -> str:
    return "".join(c for c in cnpj if c.isdigit()).zfill(14)[:14]


def _fmt_cpf(cpf: str) -> str:
    return "".join(c for c in cpf if c.isdigit()).zfill(11)[:11]


def _fmt_tel(tel: str) -> str:
    return "".join(c for c in tel if c.isdigit())[:14]


def _get_empresa() -> dict:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "dados", "empresa.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _num_serie(numero: int, serie: int) -> str:
    return f"{numero:09d}"


def montar_nfse(nota: dict, empresa: dict = None, ambiente: int = 2, serie: int = 1, numero: int = 1) -> str:
    if empresa is None:
        empresa = _get_empresa()

    now = datetime.now()
    data_emissao = now.strftime("%Y-%m-%dT%H:%M:%S")

    cnpj_raw = _fmt_cnpj(empresa.get("cnpj", ""))
    cnpj_prest = cnpj_raw
    im = empresa.get("inscricao_mun", "").strip()
    cod_mun = int(empresa.get("cod_municipio", "4314100"))

    root = etree.Element(
        _tag("GerarNfseEnvio"),
        attrib={"xmlns": NS_NFSE, "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"},
    )

    rps = etree.SubElement(root, _tag("Rps"))
    inf = etree.SubElement(rps, _tag("InfDeclaracaoPrestacaoServico"), attrib={"Id": f"RPS{numero:09d}"})

    _add(inf, "Competencia", data_emissao[:10])

    serv = etree.SubElement(inf, _tag("Servico"))
    vs = etree.SubElement(serv, _tag("Valores"))
    total = float(nota.get("total", sum(
        float(i.get("subtotal", float(i.get("preco", 0)) * float(i.get("qtd", 1))))
        for i in nota.get("itens", [])
    )))
    _add(vs, "ValorServicos", f"{total:.2f}")
    _add(vs, "ValorDeducoes", "0.00")
    _add(vs, "ValorPis", "0.00")
    _add(vs, "ValorCofins", "0.00")
    _add(vs, "ValorInss", "0.00")
    _add(vs, "ValorIr", "0.00")
    _add(vs, "ValorCsll", "0.00")
    _add(vs, "IssRetido", "2")
    _add(vs, "ValorIss", "0.00")
    _add(vs, "ValorLiquido", f"{total:.2f}")

    issqn = etree.SubElement(serv, _tag("Issqn"))
    _add(issqn, "CodigoTributacaoMunicipio", str(nota.get("cod_tributacao", "")))
    _add(issqn, "ExigibilidadeISS", "1")
    _add(issqn, "MunicipioIncidencia", str(cod_mun))
    _add(issqn, "ItemListaServico", nota.get("item_lista", "01.01"))
    _add(issqn, "CodigoCnae", str(empresa.get("cnae_prim_codigo", ""))[:7])
    _add(issqn, "Tributavel", "S")

    _add(serv, "Discriminacao", (nota.get("descricao", "Serviços prestados")[:2000]))
    _add(serv, "CodigoMunicipio", str(cod_mun))

    prest = etree.SubElement(inf, _tag("Prestador"))
    _add(prest, "Cnpj", cnpj_prest)
    if im:
        _add(prest, "InscricaoMunicipal", im[:15])

    tomador = etree.SubElement(inf, _tag("Tomador"))
    doc_tom = nota.get("documento", "")
    if doc_tom:
        doc_clean = "".join(c for c in doc_tom if c.isdigit())
        ident = etree.SubElement(tomador, _tag("IdentificacaoTomador"))
        if len(doc_clean) == 14:
            _add(ident, "CpfCnpj").text = doc_clean[:14]
        else:
            _add(ident, "CpfCnpj").text = doc_clean[:11]
    nome_tom = etree.SubElement(tomador, _tag("RazaoSocial"))
    nome_tom.text = nota.get("cliente", "Tomador")[:60]
    end_tom = etree.SubElement(tomador, _tag("Endereco"))
    _add(end_tom, "Endereco", nota.get("endereco", ""))[:120]
    _add(end_tom, "Numero", nota.get("numero", "S/N"))
    _add(end_tom, "Bairro", nota.get("bairro", ""))[:60]
    _add(end_tom, "CodigoMunicipio", str(nota.get("cod_municipio_tomador", "")))
    _add(end_tom, "Uf", nota.get("uf", ""))
    _add(end_tom, "Cep", "".join(c for c in nota.get("cep", "") if c.isdigit())[:8])
    _add(end_tom, "Telefone", _fmt_tel(nota.get("telefone", "")))
    _add(end_tom, "Email", nota.get("email", ""))[:80]

    if im:
        _add(prest, "InscricaoMunicipal", im[:15])

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()
