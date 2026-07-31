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
| **Terminal** | PDV / Caixa | Opera **em um** estabelecimento |

### Regras

1. Venda e NFC-e nascem no **estabelecimento do terminal** (CNPJ emitente).
2. CNAE / regime / tributário → camada **Fiscal** do estabelecimento (e org quando aplicável).
3. POS = Varejo genérico; não escolhe “modo de loja”.

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

1. Terminal **fixo** a uma filial vs operador **troca** filial no login/topbar.  
2. Preço: lista única da org com override local, ou só local.  
3. Numeração NFC-e: sempre por estabelecimento (provável sim).

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
