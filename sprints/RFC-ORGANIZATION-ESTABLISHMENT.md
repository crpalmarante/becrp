# RFC: Organização, Estabelecimento e Escopo de Catálogo

| Campo | Valor |
|--------|--------|
| Status | Decisão (draft estruturante) |
| Data | 31/07/2026 |
| Escopo | Tenant / multi-filial / catálogo do POS |
| Relaciona | `PLANO_EXPERIENCIA_VENDEDOR.md`, POS, Fiscal, Inventário |

---

## 1. Filosofia

> Simple is always better than complex.

Um catálogo único. Fiscal e caixa sempre no estabelecimento. Visibilidade do SKU é exceção, não regra.

---

## 2. Níveis

| Nível | Nome | Papel |
|-------|------|--------|
| **Organização** | Grupo / tenant | Dono da conta no BECRP; usuários; catálogo mestre |
| **Estabelecimento** | Matriz ou filial (CNPJ/IE) | Emitente fiscal, CSC, certificado, estoque, PDV/Caixa |
| **Terminal** | PDV / Caixa | Opera **em um** estabelecimento; criado já vinculado a pessoa/papel |

### Regras

1. Venda e NFC-e nascem no **estabelecimento do terminal** (CNPJ emitente).
2. CNAE / regime / tributário → camada **Fiscal** do estabelecimento (e org quando aplicável).
3. POS = Varejo genérico; não escolhe “modo de loja”.
4. O operador **não troca filial na topbar**: o estabelecimento vem do **terminal** ao qual ele está vinculado.

---

## 2.1 Terminal × pessoa (decisão travada)

Ao **criar** um terminal PDV (ou Caixa), ele já nasce:

1. no **estabelecimento** (matriz/filial), e  
2. **vinculado** a um operador.

| Papel vinculado | Escopo operacional |
|-----------------|--------------------|
| **Vendedor** | Opera **aquele** PDV (atendimento / pedido). Não vê outros PDVs nem caixas. |
| **Gerente** ou **Caixa** | Pode ver / operar a visão de **todos os PDVs e Caixas** do estabelecimento (fila, supervisão, financeiro). |

### Implicações

- Criação de terminal = cadastro do ponto **+** vínculo pessoa (não são passos separados opcionais).
- Um vendedor típico = 1 PDV fixo na loja; sem seletor de filial.
- Gerente/Caixa = painel amplo (PDVs + Caixas) no mesmo estabelecimento do terminal/sessão.
- Troca de estabelecimento só via **outro terminal** (ou reconfiguração administrativa), nunca no fluxo de venda.

---

## 3. Catálogo (decisão travada)

- Catálogo é **único na organização**.
- Por padrão, **matriz e filiais compartilham** o mesmo catálogo.
- Estoque e preço operacional são **por estabelecimento**.
- Não duplicar cadastro de produto por filial.

### Campo no produto: `Disponível em` (`available_at`)

| Valor | Significado |
|-------|-------------|
| **Vazio** / “Todas” | Todas as filiais **ativas** do grupo veem o SKU |
| **Lista (multi-select)** | Só os estabelecimentos marcados veem o SKU |

- É **escopo de visibilidade**, não “dono fiscal” do produto.
- Multi-select obrigatório no desenho (1, N ou todas via vazio) — evita campo único “pertence a”.
- A NFC-e **não** usa esse campo para emitir; usa o estabelecimento logado no terminal.

### Exceções locais (por estabelecimento, depois)

Sem quebrar o catálogo único, a filial pode ter overlays:

- preço / tabela local  
- ativo/inativo na loja  
- sortimento (além ou em vez de `available_at`, se necessário)  
- estoque (sempre local)

---

## 4. Configurações — quem configura o quê

| Configuração | Nível |
|--------------|--------|
| Usuários master, branding, plano | Organização |
| Catálogo mestre + `available_at` | Organização |
| CNPJ, IE, endereço, CNAE | Estabelecimento |
| Certificado A1/A3, CSC, série/número NFC-e | Estabelecimento |
| Estoque, PDVs, Caixas | Estabelecimento |
| Preferências de terminal | Terminal / estabelecimento |

PDV **não** edita CSC/certificado.

---

## 5. Estado atual no código (gap)

| Hoje | Problema |
|------|----------|
| `data/empresas.json` | Matriz/filiais magras (login) |
| `dados/empresa.json` | Um emitente fiscal global |
| POS `/api/pos/*` | Ainda assume um contexto fiscal |

**Alvo:** unificar em Organização → Estabelecimentos, e POS carregar catálogo filtrado por `available_at` + estabelecimento ativo.

---

## 6. Em aberto (próximo debate)

1. Preço: lista única da org com override local, ou só local.  
2. Numeração NFC-e: sempre por estabelecimento (provável sim).  
3. Um vendedor pode ter mais de um PDV no mesmo estabelecimento? (default sugerido: **não**, 1:1).  
4. Gerente/Caixa: um terminal “hub” vs login com papel elevado em qualquer estação do estabelecimento.

---

## 7. Impacto no POS

Na boot do PDV, com estabelecimento ativo `E`:

```
catálogo_visível = produtos onde
  available_at vazio
  OR E ∈ available_at
```

Preço/estoque exibidos = da filial `E`.

---

## 8. Changelog

| Data | Nota |
|------|------|
| 31/07/2026 | Decisões: catálogo único; `available_at` multi-select; vazio = todas; fiscal no estabelecimento. |
| 31/07/2026 | Terminal criado já vinculado a vendedor (1 PDV) ou gerente/caixa (visão de todos PDVs/Caixas); sem troca de filial no fluxo. |
