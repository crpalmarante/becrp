# RFC-POS-CENTRALIZED-CASHIER-ARCHITECTURE.md

# RFC: Arquitetura POS com PDVs Distribuídos e Caixas Centralizados

## Status

Proposta (atualizada com decisões de UX POS / Caixa)

## Versão

1.1

## Data

30/07/2026

## Autor

Equipe ERP / POS Brasil

---

# 1. Resumo

Este RFC propõe uma arquitetura de Point of Sale (POS) onde os terminais de venda (PDVs) são separados dos terminais financeiros (Caixas).

O objetivo é permitir operações de varejo com múltiplos vendedores, múltiplos terminais de atendimento e um ou mais caixas responsáveis exclusivamente pelo recebimento financeiro.

A arquitetura separa:

- Venda;
- Pagamento;
- Documento fiscal;
- Contabilidade.

---

# 2. Motivação

O modelo tradicional de POS mistura:

- atendimento;
- venda;
- recebimento;
- fechamento de caixa;
- emissão fiscal.

Esse modelo funciona para pequenos estabelecimentos, porém possui limitações em operações maiores.

Exemplos:

- lojas de móveis;
- materiais de construção;
- supermercados;
- lojas com vendedores especializados;
- redes de filiais.

Nesses cenários, o vendedor não deve controlar o caixa.

---

# 3. Objetivos

## Objetivos principais

- Permitir múltiplos PDVs de atendimento.
- Permitir múltiplos caixas financeiros.
- Separar responsabilidade operacional e financeira.
- Melhorar auditoria.
- Permitir crescimento horizontal.
- Centralizar pagamentos.
- Controlar permissões por função.

---

# 4. Arquitetura proposta

## Visão geral
             Loja

              |
    ---------------------
    |                   |
  PDVs              Caixas

      |                   |

Pedido Venda       Pagamento

    |                   |

    ------ Sistema ERP -----

             |

          Fiscal

             |

        Contabilidade
      
---

# 5. Conceito de PDV

O PDV representa o terminal utilizado pelo vendedor.

## Responsabilidades

Permitido:

- Criar pedidos.
- Criar cotações.
- Consultar produtos.
- Consultar estoque.
- Selecionar cliente.
- Enviar pedido para caixa.
- Acompanhar status.

Não permitido:

- Receber pagamento.
- Abrir caixa.
- Fechar caixa.
- Fazer sangria.
- Fazer suprimento.
- Alterar movimentação financeira.

## UI do PDV (Operator Console / Smart Panel)

O lado direito do PDV **não** é um “carrinho” nem um numpad fixo.

É o **Operator Console** (Smart Panel): painel contextual que exibe a ferramenta da tarefa atual.

| Tarefa | Contexto |
|--------|----------|
| Venda (padrão) | Resumo do Pedido |
| Cliente | Pesquisa de Clientes |
| Desconto | Desconto (valor / %) |
| Acréscimo | Majoração (mesmo painel do desconto) |
| Parcelamento | Parcelamento (total, parcelas, juros, resultado) |
| Quantidade / Peso / Valor manual | Teclado numérico |
| Observação | Editor de texto (sem numpad) |
| Estoque | Disponibilidade em linguagem humana |

Regras de UI no PDV:

- Coluna central = itens do **Pedido** (não carrinho).
- Console direito = ferramenta; troca **substitui** o conteúdo do painel.
- Sem teclas de função (F1…); ações por botões.
- **Não** exibir formas de pagamento (Dinheiro / PIX / …) no PDV.
- Após “Enviar ao caixa”, o vendedor acompanha status (ex.: Aguardando → Em pagamento → Pago).

Detalhamento de produtividade do vendedor: `PLANO_EXPERIENCIA_VENDEDOR.md`.

---

# 6. Conceito de Caixa

O Caixa representa o terminal financeiro.

## Responsabilidades

Permitido:

- Receber pedidos da fila.
- Confirmar pagamento.
- Operar dinheiro.
- Operar cartão.
- Operar PIX.
- Operar voucher.
- Realizar sangria (out).
- Realizar suprimento (in).
- Abrir / fechar sessão de caixa.

Não permitido:

- Criar pedido comercial (exceto fluxos excepcionais definidos por permissão).

## UI do Caixa

Layout típico:

1. **Fila de pagamento** (pedidos enviados pelos PDVs).
2. **Console contextual** (pagamento, valor recebido, troco, ou movimento de caixa).
3. **Barra inferior contextual** — somente no Caixa:
   - Dinheiro · PIX · Débito · Crédito · Voucher
   - Suprimento · Sangria

A barra **não** abre outra tela: muda o contexto do console.

Pagamento em dinheiro usa numpad sob demanda (valor recebido / troco).

## Movimentos de caixa (Suprimento / Sangria)

**Não usar modal flutuante.** O console do Caixa muda para o contexto Suprimento ou Sangria.

Campos obrigatórios:

- Valor (numpad);
- Motivo (lista rápida + detalhe opcional).

Documento relacionado (**opcional**, recomendado para auditoria):

| Tipo | Exemplo |
|------|---------|
| Sem documento | Fundo de troco interno |
| Recibo / NF | Compra mercado, material |
| Vale / adiantamento | Pagamento de vale funcionário |
| Comprovante banco | Depósito / sangria para cofre |
| Pedido / OS | Referência interna |

Se o tipo de documento for informado, a referência (número) torna-se obrigatória.

Todo movimento entra no diário financeiro do caixa e no log da sessão (para fechamento e auditoria).

---

# 7. Fluxo operacional

## Venda
  Cliente

↓

Vendedor

↓

PDV

↓

Sale Order

↓

Fila de pagamento

↓

Caixa

↓

Pagamento

↓

Documento fiscal

↓

Entrega


---

# 8. Modelo de estados do pedido


Rascunho

↓

Cotação

↓

Pedido confirmado

↓

Aguardando pagamento

↓

Pago

↓

Faturado

↓

Entregue


---

# 9. Modelo de diários contábeis

## Diário operacional do PDV

Exemplo:


Pedido Clientes POS


Configuração:


Tipo:
sale

l10n_latam_use_documents:
False


Uso:

- pedidos;
- cotações;
- reservas.

Não gera documento fiscal.

---

# Diário financeiro do Caixa

Exemplo:


Caixa Loja 01


Configuração:


Tipo:
cash

l10n_latam_use_documents:
False


Uso:

- pagamentos;
- recebimentos;
- movimentos de caixa.

---

# Diário fiscal

Exemplo:


Faturas Clientes POS


Configuração:


Tipo:
sale

l10n_latam_use_documents:
True


Uso:

- NF-e 55;
- NFC-e 65;
- NFS-e.

---

# 10. Exemplo de instalação

## Loja pequena


1 vendedor

1 caixa


Configuração:


PDV 01

CAIXA 01


---

## Loja média


10 vendedores

3 caixas


Configuração:


PDV 01
PDV 02
...
PDV 10

CAIXA 01
CAIXA 02
CAIXA 03


---

## Loja grande


100 vendedores

20 caixas


Mesma arquitetura.

---

# 11. Permissões

## Vendedor

Grupo:


POS Operator


Pode:

- criar venda;
- editar pedido;
- consultar produtos.

Não pode:

- receber pagamento;
- acessar caixa.

---

## Caixa

Grupo:


Cashier


Pode:

- receber;
- cancelar pagamento autorizado;
- fechar caixa.

---

## Supervisor

Grupo:


POS Supervisor


Pode:

- autorizar desconto;
- cancelar venda;
- liberar operações especiais.

---

# 12. Auditoria

Toda operação deve registrar:


Usuário

Terminal

Data/Hora

Operação

Pedido

Caixa responsável


Exemplo:


Pedido 000123

Criado:
João
PDV-04

Pagamento:
Maria
CAIXA-02

Documento:
NFC-e 000456


---

# 13. Benefícios

## Operacionais

- Atendimento mais rápido.
- Menor fila.
- Melhor divisão de tarefas.

## Financeiros

- Melhor controle de caixa.
- Separação de responsabilidades.
- Auditoria completa.

## Técnicos

- Arquitetura escalável.
- Menos acoplamento.
- Integração simplificada com fiscal.

---

# 14. Regras importantes

## Regra 1

PDV não movimenta dinheiro.

## Regra 2

Caixa não cria pedido comercial.

## Regra 3

Documento fiscal nasce somente após confirmação financeira.

## Regra 4

Fechamento de caixa nunca utiliza diário fiscal.

## Regra 5

Diários fiscais devem permanecer separados dos diários operacionais.

## Regra 6

Formas de pagamento e barra de recebimento existem **somente** no terminal Caixa (ou perfil híbrido explicitamente autorizado).

## Regra 7

Suprimento e sangria usam console contextual (valor + motivo + documento opcional); não usam modal genérico.

## Regra 8

O conceito de “carrinho” não é usado. A unidade comercial no PDV é o **Pedido** (Sale Order).

---

# 15. Implementação futura

Este RFC deverá orientar:

- módulo POS (PDV + Operator Console);
- módulo Caixa (fila, pagamento, suprimento/sangria);
- módulo Fiscal;
- módulo Venda;
- módulo Permissões;
- módulo Auditoria.

Referências de UX já em andamento:

- `PLANO_EXPERIENCIA_VENDEDOR.md` — Smart Panel e produtividade do vendedor;
- `pages/pos.html` + `js/pos-pdv.js` — protótipo UI PDV/Caixa.

---

# 16. Conclusão

A arquitetura proposta transforma o POS em uma plataforma de venda distribuída, separando atendimento comercial de operação financeira.

O modelo permite atender desde pequenas lojas até operações corporativas mantendo:

- controle;
- escalabilidade;
- segurança;
- conformidade fiscal.

**Changelog 1.1 (30/07/2026):** documenta Operator Console / Smart Panel no PDV; barra contextual e movimentos de caixa (suprimento/sangria + documento) no Caixa; reforça ausência de “carrinho” e de pagamento no PDV.
