Objetivo

Criar um motor de vendas corporativas para operações entre empresas, permitindo venda consultiva, negociação comercial, análise de crédito, faturamento e logística.

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

1. Motivação

O POS tradicional atende:

Empresa → Consumidor Final
(B2C)

Mas operações corporativas precisam de:

Empresa → Empresa
(B2B)

Exemplos:

indústria vendendo para varejistas;
distribuidoras;
atacado;
lojas vendendo para construtoras;
móveis corporativos;
revendedores.
2. Diferença POS x Sales Engine
POS

Foco:

Venda rápida
Pagamento imediato
NFC-e

Fluxo:

Produto
 ↓
Pagamento
 ↓
Cupom
Sales Engine

Foco:

Relacionamento comercial
Negociação
Contrato
Prazo
Crédito

Fluxo:

Cliente
 ↓
Cotação
 ↓
Pedido
 ↓
Faturamento
 ↓
Entrega
 ↓
Cobrança
3. Entidade Cliente B2B

Cliente não é apenas um contato.

Modelo:

Company

 |
 +-- CNPJ
 |
 +-- Inscrições estaduais
 |
 +-- Endereços
 |
 +-- Contatos
 |
 +-- Limite crédito
 |
 +-- Condição pagamento
 |
 +-- Tabela preço
 |
 +-- Histórico compras
4. Cotação Comercial

Primeira etapa.

Exemplo:

Cliente:

Construtora ABC Ltda
CNPJ XX.XXX.XXX/0001-XX

Solicita:

100 portas
50 armários
20 mesas

Sistema cria:

Quotation #000145

Status:

Rascunho

↓

Enviada

↓

Negociação

↓

Aprovada

↓

Convertida em Pedido
5. Motor de Preços

O Sales Engine deve suportar:

Tabela de preço

Exemplo:

Cliente varejo

Produto:
Mesa

Preço:
R$ 800
Cliente especial
Construtora ABC

Produto:
Mesa

Preço:
R$ 650
Volume
1 unidade
R$ 800


100 unidades
R$ 600
6. Motor de desconto

Desconto deve possuir regras.

Exemplo:

Vendedor:

Até 5%

Supervisor:

Até 15%

Gerente:

Acima de 15%

Fluxo:

Pedido

↓

Desconto solicitado

↓

Aprovação

↓

Liberação
7. Crédito e risco

Antes de confirmar pedido:

Consultar:

Limite crédito

Títulos vencidos

Histórico pagamento

Score cliente

Exemplo:

Cliente:

Limite:
R$ 100.000

Pedido:
R$ 120.000

Resultado:

Enviar para aprovação financeira
8. Reserva de estoque

Após aprovação:

Pedido Venda

        |

Reserva

        |

Inventory

Exemplo:

Pedido:

100 cadeiras

Estoque:

80 disponíveis

Resultado:

Pedido parcial
9. Expedição

Fluxo:

Pedido aprovado

↓

Separação

↓

Conferência

↓

Embalagem

↓

Entrega
10. Fiscal

B2B normalmente utiliza:

NF-e Modelo 55

Fluxo:

Pedido

↓

Faturamento

↓

Fiscal Engine

↓

SEFAZ

↓

NF-e
11. Financeiro

Após faturamento:

Gerar:

Conta a receber

Exemplo:

Venda:

R$ 50.000

Pagamento:

30/60/90 dias

Gera:

Parcela 1
R$ 16.666

Parcela 2
R$ 16.666

Parcela 3
R$ 16.666
12. Integração com Inventory

O Sales Engine nunca baixa estoque diretamente.

Fluxo correto:

Sales Order

      |

Stock Reservation

      |

Delivery

      |

Stock Move

      |

Inventory
13. Integração com POS

Pode existir integração:

Cliente começou no POS:

Orçamento

Depois:

Convertido em Venda B2B

Exemplo:

Loja de móveis:

Cliente compra projeto completo.

Fluxo:

POS vendedor

↓

Sales Engine

↓

Pedido corporativo

↓

Entrega futura
14. Auditoria

Registrar:

Quem criou

Quem aprovou

Quem alterou preço

Quem liberou desconto

Quem aprovou crédito

Quem faturou
15. Arquitetura de módulos
Party / Customer Core

        |

CRM

        |

Sales Engine

        |

Pricing Engine

        |

Credit Engine

        |

Inventory

        |

Fiscal Engine

        |

Finance
16. Conclusão

O Sales Engine B2B é o núcleo comercial para operações CNPJ → CNPJ.

Ele complementa:

POS → venda rápida B2C;
Sales Engine → venda consultiva B2B;
Inventory → disponibilidade;
Fiscal → documentos;
Financeiro → cobrança.

A separação permite que o ERP atenda desde uma loja pequena até uma operação de atacado/distribuição.
