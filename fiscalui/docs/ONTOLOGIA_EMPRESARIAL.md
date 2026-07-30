# Business Platform
# BC-001 — Ontologia Empresarial

**Versão:** 1.0
**Status:** Draft
**Tipo:** Documento de Linguagem Ubíqua

## Propósito

Este documento define o **significado** de cada conceito fundamental da plataforma. Não trata de código, arquitetura, tabelas ou classes. Trata apenas do que cada coisa **é** no mundo real do negócio.

A ontologia é anterior a qualquer modelo técnico. Ela materializa o **Artigo 2º** do manifesto: todo conceito empresarial possui um único significado.

Nenhum motor — BusinessCore, FiscalCore, AccountingCore, WorkflowCore ou FiscalUI — poderá reinterpretar ou estender o significado aqui definido. As especializações técnicas (fiscal, contábil, processo) ocorrem exclusivamente nos motores especializados, sem jamais alterar o conceito original.

---

## 1. Pessoa

### Definição

Sujeito de direitos reconhecido pelo ordenamento jurídico, capaz de adquirir direitos e contrair obrigações.

### Naturezas

**Pessoa Natural (Física):** Ser humano dotado de capacidade civil. Identificada por um documento de identidade civil universal (CPF no Brasil, SSN nos EUA, NIF em Portugal, etc.).

**Pessoa Jurídica (Coletiva):** Entidade abstrata com personalidade jurídica própria, distinta das pessoas naturais que a compõem. Identificada por um documento de registro empresarial (CNPJ no Brasil, EIN nos EUA, NIPC em Portugal, etc.).

### Atributos ontológicos

- Possui identidade (nome/razão social)
- Possui documento de identificação (o tipo varia por país)
- Pode ter endereço, contato, dados complementares
- É sujeito de direitos e obrigações
- É a unidade fundamental de relacionamento da plataforma

### O que não é

Pessoa não é cliente. Pessoa não é fornecedor. Pessoa não é funcionário. Pessoa é **Pessoa**. Os papéis que ela desempenha são outra coisa.

### Relações

- Uma Pessoa pode desempenhar **múltiplos papéis** simultaneamente
- Os papéis são: Cliente, Fornecedor, Transportador, Vendedor, Funcionário, Sócio, etc.
- O que muda é o **papel**, nunca a identidade da Pessoa

---

## 2. Organização

### Definição

Grupo estruturado de pessoas e recursos organizados para atingir um objetivo comum. A Organização é o **contexto operacional** da plataforma — é sob o guarda-chuva de uma Organização que todas as operações ocorrem.

### Atributos ontológicos

- Possui identidade jurídica própria
- Possui estrutura organizacional (departamentos, divisões)
- É a entidade que contrata, vende, compra, produz
- É o sujeito contábil primário
- Toda operação na plataforma pertence a uma Organização

### Diferenciação

**Organização ≠ Pessoa Jurídica.** Toda Pessoa Jurídica pode ser uma Organização, mas Organização é um conceito mais amplo: inclui a capacidade de operar, transacionar, contratar. Uma Pessoa Jurídica que não opera (ex: empresa inativa) é uma Pessoa Jurídica, mas não uma Organização ativa.

### O que não é

Organização não é filial. Organização não é departamento. Organização não é marca. Organização é a entidade operacional completa.

---

## 3. Estabelecimento (Filial)

### Definição

Unidade operacional da Organização com endereço próprio e inscrição fiscal própria (quando aplicável). Toda Organização possui ao menos um Estabelecimento: a matriz.

### Atributos ontológicos

- Possui endereço físico
- Possui inscrições fiscais próprias (Estadual, Municipal)
- É o local onde as operações ocorrem fisicamente
- Compartilha a mesma personalidade jurídica da Organização

### Relações

- Uma Organização **possui** um ou mais Estabelecimentos
- Um Estabelecimento **pertence a** exatamente uma Organização
- Estabelecimentos podem ser matriz ou filial

### O que não é

Estabelecimento não é departamento. Estabelecimento não é centro de custo. Estabelecimento é uma unidade operacional com endereço e inscrição próprios.

---

## 4. Cliente

### Definição

**Papel** desempenhado por uma Pessoa (natural ou jurídica) que adquire ou contrata produtos, serviços ou direitos de uma Organização.

### Natureza ontológica

Cliente **não é uma entidade**. Cliente é um **papel** que uma Pessoa assume em uma relação comercial.

A mesma Pessoa pode ser Cliente hoje, Fornecedor amanhã, ou ambos simultaneamente.

### Atributos ontológicos

- É sempre uma Pessoa (nunca uma coisa)
- Pressupõe uma relação comercial com uma Organização
- Pode ter histórico de compras
- Pode ter condições comerciais próprias (prazo, desconto, limite)

### O que não é

Cliente não tem NCM. Cliente não tem CFOP. Cliente não tem regime tributário. Cliente não tem conta contábil. Essas especializações pertencem ao FiscalCore e AccountingCore.

---

## 5. Fornecedor

### Definição

**Papel** desempenhado por uma Pessoa (natural ou jurídica) que fornece produtos, mercadorias, serviços ou direitos para uma Organização.

### Natureza ontológica

Assim como Cliente, Fornecedor **não é uma entidade**. É um **papel**.

A mesma Pessoa pode ser Cliente e Fornecedor da mesma Organização.

### Atributos ontológicos

- É sempre uma Pessoa
- Pressupõe uma relação comercial com uma Organização
- Pode ter condições comerciais próprias

---

## 6. Produto

### Definição

Bem tangível, resultante de produção ou aquisição, que pode ser estocado, transferido, vendido, consumido ou transformado.

### Atributos ontológicos

- Possui existência física
- É estocável (tem quantidade, localização)
- Possui identidade (código, descrição)
- Possui unidade de medida (kg, un, l, m, etc.)
- Pode ter composição (insumos, componentes, kits)
- Pode ser rastreável (lote, série)

### O que não é

Produto não tem NCM. Produto não tem CEST. Produto não tem CFOP. Produto não tem CST. Produto não tem conta contábil. Essas especializações pertencem ao FiscalCore e AccountingCore.

Produto não é Serviço. Um item é Produto **ou** é Serviço. Não ambos.

---

## 7. Serviço

### Definição

Atividade intangível prestada a terceiros, que não resulta em bem físico estocável.

### Atributos ontológicos

- Não é estocável
- É prestado (não vendido como mercadoria)
- Pode ser contínuo (assinatura, contrato) ou pontual
- Possui identidade (código, descrição)
- Possui unidade de medida (hora, dia, mês, serviço)

### O que não é

Serviço não é Produto. Serviço não tem NCM. Serviço não tem CFOP de mercadoria. Serviço não tem conta contábil no BusinessCore.

---

## 8. Documento

### Definição

Registro formal de um ato ou fato empresarial, dotado de identidade própria, valor probatório e ciclo de vida.

### Atributos ontológicos

- Possui identidade única (tipo, número, série)
- Possui data de emissão
- Possui emissor e destinatário
- Possui um conjunto de itens (produtos, serviços, valores)
- Possui status (rascunho, emitido, cancelado)
- Formaliza um ou mais Eventos de Negócio

### Exemplos

Pedido de Venda, Pedido de Compra, Contrato, NF-e, Boleto, Recibo, Nota de Crédito, Orçamento, Cotação

### O que não é

Documento não é Evento. O Documento é o **registro formal** do Evento. O Evento é o **fato econômico** que ocorreu. O Documento pode ser cancelado; o Evento permanece.

Documento não tem chave de acesso. Documento não tem protocolo SEFAZ. Documento não tem NCM. Essas especializações pertencem ao FiscalCore.

---

## 9. Transação

### Definição

Operação comercial entre duas Pessoas (ou entre uma Pessoa e a Organização) que envolve a troca de produtos, serviços ou valores.

### Atributos ontológicos

- Envolve ao menos duas partes
- Tem um objeto (produto, serviço, direito)
- Tem um valor econômico
- Gera obrigações para as partes
- Pode ser classificada por tipo (venda, compra, transferência, devolução)

### Exemplos

Venda, Compra, Devolução de Venda, Devolução de Compra, Transferência entre Estabelecimentos, Consignação, Empréstimo

### O que não é

Transação não tem CFOP. Transação não tem CST. Transação não tem partidas dobradas. Essas especializações pertencem ao FiscalCore e AccountingCore.

---

## 10. Evento de Negócio

### Definição

Ocorrência relevante que marca uma mudança de estado no ciclo de vida de uma entidade, transação ou documento.

### Atributos ontológicos

- Ocorre em um instante específico no tempo
- É imutável após consumado
- É originado por um comando (ação do usuário ou do sistema)
- Pode desencadear outros eventos
- É a unidade fundamental de rastreabilidade

### Exemplos

PedidoCriado, PedidoAprovado, PedidoCancelado, MercadoriaRecebida, NotaFiscalEmitida, PagamentoConfirmado, EstoqueBaixado

### Diferença entre Evento e Transação

A Transação é a operação comercial. O Evento é o marco temporal dentro do ciclo de vida da Transação. Uma Transação gera múltiplos Eventos.

### Princípio ontológico (Artigo 7º)

Eventos nunca são alterados. Correções ocorrem através de novos eventos. Nunca por modificação do passado.

---

## 11. Glossário

| Termo | Significado | Motor responsável |
|-------|-------------|-------------------|
| Pessoa | Sujeito de direitos (natural ou jurídica) | BusinessCore |
| Organização | Entidade operacional que transaciona | BusinessCore |
| Estabelecimento | Unidade operacional com endereço próprio | BusinessCore |
| Cliente | Papel de Pessoa que adquire | BusinessCore |
| Fornecedor | Papel de Pessoa que fornece | BusinessCore |
| Produto | Bem tangível estocável | BusinessCore |
| Serviço | Atividade intangível não estocável | BusinessCore |
| Documento | Registro formal de ato empresarial | BusinessCore |
| Transação | Operação comercial entre partes | BusinessCore |
| Evento | Marco temporal imutável no ciclo de vida | BusinessCore |
| Tributo (NCM, CFOP, CST) | Especialização fiscal do Produto | FiscalCore |
| Conta Contábil | Especialização contábil do Produto | AccountingCore |

---

## Relações Ontológicas Fundamentais

```
Pessoa
  ├── Pessoa Natural (identificada por documento civil)
  └── Pessoa Jurídica (identificada por registro empresarial)
       └── pode ser Organização (se operacional)

Organização
  ├── possui 1..N Estabelecimentos
  └── relaciona-se com Pessoas (como Cliente, Fornecedor, etc.)

Pessoa
  └── desempenha papéis → Cliente, Fornecedor, Transportador, etc.

Produto (é estocável)  |  Serviço (não é estocável)
  └── especializado por FiscalCore → ProdutoFiscal (NCM, CFOP, CST)
  └── especializado por AccountingCore → ProdutoContabil (conta)

Transação
  ├── envolve: Organização + Pessoa(s) + Itens (Produtos/Serviços)
  ├── gera Documento(s)
  └── gera Eventos ao longo do seu ciclo de vida

Evento
  └── é imutável (Artigo 7º)
  └── origina especializações nos motores:
       ├── FiscalCore → evento fiscal
       ├── AccountingCore → lançamento contábil
       └── WorkflowCore → transição de estado
```

---

**Arquivo:** `docs/ONTOLOGIA_EMPRESARIAL.md`
**Versão:** 2.0
**Data:** 2026-07-25
**Referência:** BC-000 Art. 2º, 3º, 4º, 5º, 12º
