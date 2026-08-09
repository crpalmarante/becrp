# FiscalUI — Documentos Fiscais: Ecossistema

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

## O Problema

Não basta emitir um documento. É preciso compreender o ecossistema completo. Cada documento tem **schema próprio, regras de validação distintas, leiaute específico, prazos de entrega e órgãos diferentes**.

```
NF-e     → SEFAZ (Secretaria da Fazenda Estadual)
NFC-e    → SEFAZ (consumidor final)
CT-e     → SEFAZ (transporte)
MDF-e    → SEFAZ (manifesto de carga)
NFS-e    → Prefeitura Municipal (5.570 municípios)
SAT      → SEFAZ SP (cupom fiscal)
CF-e     → SAT (Cupom Fiscal Eletrônico)
SPED     → Receita Federal
EFD      → SPED Fiscal (ICMS/IPI)
ECD      → SPED Contábil
ECF      → SPED Contábil Fiscal
```

## Mapa de Documentos

```
                        ┌──────────────────────────────────────────────────┐
                        │               RECEITA FEDERAL                    │
                        │                                                  │
                        │  SPED-ECD    → Contabilidade Digital             │
                        │  SPED-ECF    → Contabilidade Fiscal              │
                        │  eSocial     → Obrigações Trabalhistas           │
                        │  Reinf       → Retenções Previdenciárias         │
                        │  DCTFWeb     → Débitos Federais                  │
                        └──────────────────────────────────────────────────┘

                        ┌──────────────────────────────────────────────────┐
                        │               SEFAZ (27 estados)                 │
                        │                                                  │
                        │  NF-e        → Nota Fiscal Eletrônica           │
                        │  NFC-e       → Nota ao Consumidor               │
                        │  CT-e        → Conhecimento de Transporte       │
                        │  MDF-e       → Manifesto de Documentos Fiscais  │
                        │  SAT/CF-e    → Cupom Fiscal (SP)                │
                        │  EFD-ICMS/IPI → SPED Fiscal                     │
                        └──────────────────────────────────────────────────┘

                        ┌──────────────────────────────────────────────────┐
                        │               PREFEITURAS (5.570 municípios)     │
                        │                                                  │
                        │  NFS-e       → Nota Fiscal de Serviço           │
                        │  (cada município com seu leiaute)                │
                        └──────────────────────────────────────────────────┘

                        ┌──────────────────────────────────────────────────┐
                        │               MUNICÍPIOS (padrão nacional)       │
                        │                                                  │
                        │  NFS-e Padrão Nacional → padrão único            │
                        │  (em implantação gradual)                        │
                        └──────────────────────────────────────────────────┘
```

## Complexidade por Documento

### NF-e (Nota Fiscal Eletrônica — modelo 55)

```
Órgão:     SEFAZ estadual (27 ambientes diferentes)
Schema:    XSD oficial da Receita Federal (300+ campos)
Validação: ~300 regras de validação
Comunicação: WebService SOAP (WSDL oficial)
Ambientes: Produção + Homologação (por estado)
Versões:   4.00 (atual), 4.01 (em implantação)
Documento vinculado: DANFE (PDF/DOC)
Prazo:     Transmissão antes da circulação da mercadoria
```

### NFC-e (Nota Fiscal ao Consumidor — modelo 65)

```
Órgão:     SEFAZ estadual
Schema:    Simplificado (versão reduzida da NF-e)
Validação: ~150 regras
Comunicação: WebService SOAP
Específico: Consumidor final (CPF/CNPJ)
Documento vinculado: DANFE-NFC-e (formato A4/termica)
Forma de pagamento: Obrigatório informar meios
```

### CT-e (Conhecimento de Transporte — modelo 57)

```
Órgão:     SEFAZ estadual
Schema:    Específico para transporte
Modal:     Rodoviário, Ferroviário, Aéreo, Aquaviário, Dutoviário
Serviço:   Contratado, Subcontratado, Redespacho
Documento vinculado: DACTE (PDF)
Tomador:   Remetente, Destinatário, Expedidor, Recebedor
```

### MDF-e (Manifesto de Documentos Fiscais — modelo 58)

```
Órgão:     SEFAZ estadual
Função:    Vincular NF-e/CT-e a uma carga
Obrigatório: Quando carga > 1 NF-e
Prazo:     Antes do início da viagem
Encerramento: Quando carga é entregue
```

### NFS-e (Nota Fiscal de Serviço)

```
Órgão:     Prefeitura Municipal (5.570 municípios)
Problema:  Antes: 5.570 leiautes diferentes
Solução:   Padrão Nacional de NFS-e (em andamento)
Situação:  Coexistência de padrões durante a migração
Específico: ISS, retenções, deduções
```

### SAT / CF-e (Sistema de Autenticação e Transmissão)

```
Órgão:     SEFAZ SP (apenas SP)
Hardware:  SAT fiscal (equipamento certificado)
Função:    Emissão de Cupom Fiscal (CF-e)
Diferença: Sem XML trafegando — equipamento local
Modelo:   CF-e (modelo 59)
```

### SPED EFD (Escrituração Fiscal Digital)

```
Órgão:     Receita Federal + SEFAZ
Periodicidade: Mensal
Conteúdo:  Todas as NF-e emitidas e recebidas
           Apuração de ICMS e IPI
           Inventário
           Registros de apuração
Validação: PVA (Programa Validador e Assinador)
Prazo:     Dia 20 do mês subsequente
```

### SPED ECD (Escrituração Contábil Digital)

```
Órgão:     Receita Federal
Periodicidade: Anual
Conteúdo:  Livro Diário, Livro Razão, Balanços
Validação: PVA específico
Prazo:     Maio do ano subsequente
```

### SPED ECF (Escrituração Contábil Fiscal)

```
Órgão:     Receita Federal
Periodicidade: Anual
Conteúdo:  Apuração do IRPJ e CSLL
           LALUR (Livro de Apuração do Lucro Real)
           Controle de prejuízos fiscais
Prazo:     Julho do ano subsequente
```

## O Desafio Técnico

```
Cada documento representa:

1. Um schema XML/XSD diferente
2. Um conjunto de regras de validação diferente
3. Um webservice com protocolo diferente (SOAP, REST)
4. Um ambiente de homologação diferente
5. Um prazo de entrega diferente
6. Uma forma de assinatura digital diferente
7. Um leiaute de documento impresso diferente
8. Uma contingência diferente (SVC, EPEC, FSDA)

Tudo isso muda quando:
  - O governo publica uma nova versão do schema
  - Um estado altera suas regras de validação
  - Um município adere ao Padrão Nacional
  - Um novo documento é criado
```

## Como FiscalUI Lida com Isso

**Mesma resposta de sempre: delega tudo ao backend.**

```
┌────────────────────────────────────────────────────────────────────┐
│  FiscalUI                                                          │
│                                                                    │
│  ⊗ Não sabe o que é XSD, SOAP, SEFAZ, lote, contingência         │
│  ⊗ Não assina XML, não valida schema, não transmite               │
│                                                                    │
│  ✓ Sabe exibir formulários                                         │
│  ✓ Sabe mostrar o status de uma NF-e                              │
│  ✓ Sabe exibir uma DANFE em PDF                                   │
│  ✓ Sabe listar documentos emitidos                                │
│  ✓ Sabe mostrar erros de validação                                │
└────────────────────────────────────────────────────────────────────┘
```

### Fluxo de Emissão de NF-e

```
FiscalUI                                    Backend (Python/COBOL)
─────────                                   ──────────────────────
                                            │
   Preenche formulário de NF-e              │
   │                                        │
   ▼                                        │
   JSON → POST /api/nfe/emitir              │
                                            │
                 ┌──────────────────────────▼──────────────┐
                 │  1. Valida dados de negócio              │
                 │  2. Chama Tax Engine (calcular tributos) │
                 │  3. Monta XML da NF-e (modelo 55)       │
                 │  4. Assina digitalmente (certificado A1) │
                 │  5. Transmite para SEFAZ via SOAP       │
                 │  6. Recebe protocolo (NSU, chave, xml)  │
                 │  7. Salva no banco                      │
                 │  8. Gera DANFE (PDF)                    │
                 └─────────────────────────────────────────┘
                                            │
   JSON ← { status, chave, nsu,           │
            protocolo, danfeUrl, erros }    │
   │                                        │
   ▼                                        │
   Exibe:                                    │
   - Chave de acesso                        │
   - Status (autorizada/rejeitada)          │
   - Link para DANFE                        │
   - Erros (se houver)                      │
```

### Contrato API (Documentos)

```json
// POST /api/nfe/emitir
// Request (FiscalUI → Backend)
{
    "tipoDocumento": "NFE",
    "operacao": "VENDA",
    "emitente": { "cnpj": "11.222.333/0001-44" },
    "destinatario": { "cnpj": "99.888.777/0001-11" },
    "itens": [ ... ],
    "transporte": { ... },
    "pagamento": { ... }
}

// Response (Backend → FiscalUI)
{
    "status": "AUTORIZADA",
    "chave": "35200611222333000144550010000012341000012345",
    "nfe": {
        "numero": 1234,
        "serie": 1,
        "dataEmissao": "2026-07-24T10:30:00-03:00",
        "dataAutorizacao": "2026-07-24T10:30:15-03:00"
    },
    "protocolo": "135240000123456",
    "nsu": 123456789,
    "xmlUrl": "https://api.fiscalui.com/nfe/352006.../xml",
    "danfeUrl": "https://api.fiscalui.com/nfe/352006.../danfe.pdf",
    "qrcodeUrl": "https://api.fiscalui.com/nfe/352006.../qrcode",
    "erros": [],
    "alertas": [
        "NF-e autorizada em contingência (SVC-RS)"
    ],
    "custo": {
        "tempoProcessamento": 2.3,
        "tentativas": 1,
        "sefaz": "SP"
    }
}
```

### Contrato de Consulta

```json
// GET /api/nfe/35200611222333000144550010000012341000012345
// Response
{
    "chave": "35200611222333000144550010000012341000012345",
    "status": "AUTORIZADA",
    "emitente": { "cnpj": "11.222.333/0001-44", "nome": "EMPRESA A" },
    "destinatario": { "cnpj": "99.888.777/0001-11", "nome": "EMPRESA B" },
    "valores": {
        "baseCalculoICMS": 1450.00,
        "valorICMS": 261.00,
        "valorTotal": 1711.00
    },
    "itens": [ ... ],
    "eventos": [
        { "tipo": "AUTORIZACAO", "data": "2026-07-24T10:30:15-03:00", "protocolo": "135240000123456" },
        { "tipo": "CIENCIA_EMISSAO", "data": "2026-07-24T10:30:10-03:00" }
    ],
    "manifestacoes": [],
    "xmlUrl": "...",
    "danfeUrl": "..."
}
```

### Endpoints por Documento

```
NF-e:
  POST   /api/nfe/emitir         → Emitir NF-e
  GET    /api/nfe/{chave}         → Consultar NF-e
  POST   /api/nfe/{chave}/cancelar → Cancelar NF-e
  POST   /api/nfe/{chave}/corrigir → Carta de Correção
  POST   /api/nfe/{chave}/inutilizar → Inutilizar numeração
  GET    /api/nfe/{chave}/danfe   → Download DANFE
  GET    /api/nfe/{chave}/xml     → Download XML

CT-e:
  POST   /api/cte/emitir
  GET    /api/cte/{chave}
  POST   /api/cte/{chave}/encerrar

MDF-e:
  POST   /api/mdfe/emitir
  POST   /api/mdfe/{chave}/encerrar
  POST   /api/mdfe/{chave}/alterar

NFS-e:
  POST   /api/nfse/emitir
  GET    /api/nfse/{codigo}
  POST   /api/nfse/{codigo}/cancelar

SPED:
  POST   /api/sped/efd/gerar      → Gerar EFD (ICMS/IPI)
  POST   /api/sped/ecd/gerar      → Gerar ECD (contábil)
  POST   /api/sped/ecf/gerar      → Gerar ECF (fiscal)
  GET    /api/sped/{id}/download   → Download do arquivo
```

## Resumo

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   O FiscalUI NÃO emite documentos fiscais.                   ║
║   O FiscalUI exibe o resultado da emissão.                   ║
║                                                              ║
║   Quem emite é o backend (Python/COBOL).                     ║
║   Quem valida com a SEFAZ é o backend.                       ║
║   Quem assina XML é o backend.                               ║
║   Quem gera DANFE é o backend.                               ║
║                                                              ║
║   Se o leiaute da NF-e mudar (versão 4.01):                  ║
║   → Backend se adapta                                        ║
║   → FiscalUI: zero alteração                                 ║
║                                                              ║
║   Se um município aderir ao Padrão Nacional:                 ║
║   → Backend se adapta                                        ║
║   → FiscalUI: zero alteração                                 ║
║                                                              ║
║   Se um novo documento for criado (ex: NF-e de Serviço):     ║
║   → Backend implementa novo módulo                           ║
║   → FiscalUI: form dinâmico + listagem genérica             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

**Arquivo:** `docs/TAX_DOCUMENTS.md`
**Versão:** 1.0
**Data:** 2026-07-24
