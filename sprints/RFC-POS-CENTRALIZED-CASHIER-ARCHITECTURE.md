# RFC-POS-CENTRALIZED-CASHIER-ARCHITECTURE.md

# RFC: Arquitetura POS com PDVs Distribuídos e Caixas Centralizados

## Status

Proposta

## Versão

1.0

## Data

28/07/2026

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
- Alterar movimentação financeira.

---

# 6. Conceito de Caixa

O Caixa representa o terminal financeiro.

## Responsabilidades

Permitido:

- Receber pedidos.
- Confirmar pagamento.
- Operar dinheiro.
- Operar cartão.
- Operar PIX.
- Realizar sangria.
- Realizar suprimento.
- Fechar sessão.

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

---

# 15. Implementação futura

Este RFC deverá orientar:

- módulo POS;
- módulo Caixa;
- módulo Fiscal;
- módulo Venda;
- módulo Permissões;
- módulo Auditoria.

---

# 16. Conclusão

A arquitetura proposta transforma o POS em uma plataforma de venda distribuída, separando atendimento comercial de operação financeira.

O modelo permite atender desde pequenas lojas até operações corporativas mantendo:

- controle;
- escalabilidade;
- segurança;
- conformidade fiscal.
