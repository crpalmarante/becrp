# RFC-INVENTORY-MODERN-ERP-ARCHITECTURE.md

# RFC: Arquitetura de Inventory para ERPs Modernos

## Status

Proposta

## Versão

1.0

## Data

28/07/2026

## Objetivo

Definir a arquitetura moderna do módulo de estoque (Inventory), permitindo
operações de varejo, distribuição, e-commerce, POS e logística utilizando
um modelo escalável, auditável e orientado a eventos.

---

# 1. Resumo

O módulo Inventory é responsável pelo controle físico e lógico dos produtos
dentro do ERP.

A arquitetura proposta abandona o conceito simples:
Produto = Quantidade em estoque


e adota:


Produto
+
Localização
+
Movimentações
+
Reservas
+
Custos
+
Rastreamento
+
Eventos

---

# 2. Motivação

ERPs tradicionais possuem limitações:

- Estoque global sem localização real.
- Alterações diretas de quantidade.
- Pouca rastreabilidade.
- Dificuldade em operações omnichannel.
- Mistura de estoque físico e estoque disponível.
- Falta de auditoria.

ERPs modernos precisam suportar:

- lojas físicas;
- centros de distribuição;
- marketplaces;
- e-commerce;
- POS;
- delivery;
- transferência entre unidades;
- múltiplos depósitos.

---

# 3. Princípios da arquitetura

## 3.1 Estoque baseado em movimentos

O estoque nunca deve ser alterado diretamente.

Modelo incorreto:
Produto
Quantidade = 50


Modelo correto:


Entrada +100

Venda -20

Transferência -10

Ajuste -5

Saldo = movimentos acumulados


---

# 4. Modelo conceitual

             Produto

                |

          Stock Movement

                |

    -----------------------

    |                     |

Origem Destino

    |                     |

Localização A Localização B


Toda alteração gera uma movimentação.

---

# 5. Entidades principais

## Product

Representa o item comercial.

Exemplo:


Geladeira Brastemp 400L


Informações:

- código;
- descrição;
- categoria;
- unidade;
- peso;
- volume;
- NCM;
- fornecedor;
- custo.

---

# Stock Location

Representa onde o produto está.

Exemplos:


Matriz

├── Loja Centro

├── Loja Norte

└── Depósito Principal


Tipos:

- estoque físico;
- estoque reservado;
- trânsito;
- perda;
- devolução.

---

# Stock Quant

Representa a posição atual.

Exemplo:


Produto:
Sofá 3 lugares

Local:
Depósito

Disponível:
20 unidades

Reservado:
5 unidades


---

# Stock Move

Representa uma movimentação.

Exemplo:


Venda:

Depósito

-1 Sofá

↓

Cliente


Campos:


produto

quantidade

origem

destino

usuário

data

documento origem


---

# 6. Separação de estoques

O sistema deve separar:

## Estoque físico

Produto realmente existente.

Exemplo:


Depósito:
100 unidades


---

## Estoque reservado

Produto comprometido.

Exemplo:


Venda aberta:

20 unidades reservadas


---

## Estoque disponível

Cálculo:


Físico - Reservado


Exemplo:


100 - 20 = 80 disponíveis


---

# 7. Fluxo POS

## Venda imediata


POS

↓

Pagamento

↓

Documento fiscal

↓

Stock Move

↓

Baixa estoque


---

## Pedido futuro


Venda

↓

Reserva

↓

Separação

↓

Entrega

↓

Baixa definitiva


---

# 8. Fluxo E-commerce


Pedido online

    |

Reserva estoque

    |

Separação

    |

Expedição

    |

Entrega


---

# 9. Múltiplos depósitos

O ERP deve suportar:


Empresa

├── CD Principal

├── Loja A

├── Loja B

└── Estoque Terceiros


---

# 10. Transferência interna

Exemplo:


CD

↓

Transferência

↓

Loja Centro


Processo:


Criar transferência

↓

Separação

↓

Envio

↓

Recebimento

↓

Atualização estoque


---

# 11. Reserva inteligente

A reserva deve considerar:

- estoque disponível;
- localização;
- distância;
- prazo;
- custo logístico.

Exemplo:

Cliente compra:


Produto X


Sistema decide:


CD Norte:
50 unidades

ou

Loja Centro:
10 unidades


---

# 12. Custos

O Inventory deve suportar:

## Custo médio


Valor estoque / quantidade


## FIFO

Primeiro que entra,
primeiro que sai.

## Custo padrão

Valor definido pela empresa.

---

# 13. Rastreamento

Suporte para:

## Lote

Exemplo:


Lote:
ABC2026


## Série

Exemplo:


IMEI
Número equipamento
Chassi


## Validade

Exemplo:


Medicamentos
Alimentos


---

# 14. Auditoria

Nenhum movimento deve ser apagado.

Modelo:


Stock Event

ID

Usuário

Data

Origem

Destino

Documento

Antes

Depois


---

# 15. Integrações

## POS


Venda

↓

Estoque


---

## Compras


Pedido fornecedor

↓

Recebimento

↓

Entrada estoque


---

## Fiscal


NF-e entrada

↓

Produtos

↓

Custo

↓

Estoque


---

## Delivery


Pedido

↓

Reserva

↓

Separação

↓

Entrega


---

# 16. Regras de negócio

## Regra 1

Nunca alterar quantidade diretamente.

## Regra 2

Toda alteração gera movimento.

## Regra 3

Reserva não reduz estoque físico.

## Regra 4

Entrega reduz estoque disponível.

## Regra 5

Movimentos são imutáveis.

---

# 17. Arquitetura técnica

Proposta:


Inventory Core

    |

Stock Engine

    |

Reservation Engine

    |

Cost Engine

    |

Logistics Engine

    |

Integration Layer


---

# 18. Futuras evoluções

- previsão de demanda;
- inteligência de reposição;
- integração marketplace;
- roteirização;
- inventário por RFID;
- leitura por código de barras;
- aplicativo móvel de estoque.

---

# 19. Conclusão

O Inventory moderno deve ser tratado como um motor de movimentações,
não como uma simples tabela de quantidade.

A arquitetura proposta permite:

- múltiplas lojas;
- múltiplos depósitos;
- POS;
- e-commerce;
- logística;
- fiscal;
- auditoria completa.

Este RFC define a base para um ERP moderno, escalável e preparado para operações omnichannel.

20. Importação de XML de Fornecedor (NF-e Entrada)
Objetivo

Permitir a entrada de mercadorias através da importação automática de NF-e de fornecedores, garantindo:

rastreabilidade fiscal;
atualização de estoque;
atualização de custos;
vínculo com fornecedor;
auditoria completa.
20.1 Fluxo de entrada
Fornecedor envia NF-e

        |
        v

Importação XML

        |
        v

Validação Fiscal

        |
        v

Conferência de Produtos

        |
        v

Recebimento

        |
        v

Entrada Estoque

        |
        v

Atualização Custo
20.2 Etapas da importação
1. Recepção do XML

Sistema recebe:

arquivo XML;
chave NF-e;
fornecedor;
data emissão;
valor total;
produtos;
impostos.

Exemplo:

NF-e 35260712345678000190550010000012345678901234
2. Leitura do XML

Extrair:

Cabeçalho
emitente;
CNPJ;
número NF;
série;
data;
natureza da operação.
Produtos

Por item:

código fornecedor;
descrição;
NCM;
CFOP;
quantidade;
unidade;
valor unitário;
desconto;
frete;
seguro.
Impostos
ICMS;
ICMS ST;
IPI;
PIS;
COFINS;
DIFAL;
IBS/CBS futuro.
20.3 Associação de produtos

O sistema deve identificar:

Produto XML
       |
       |
Código fornecedor
       |
       |
Produto interno

Exemplo:

XML:

COD_PROD:
ABC123
Descrição:
Geladeira 400L

Sistema:

Produto:
Geladeira Brastemp 400L
ID:
4521

Caso não encontre:

Criar pendência:

Produto não identificado

Ação:
[Associar]
[Criar Produto]
[Ignorar]
20.4 Conferência antes da entrada

A entrada não deve ser automática sem validação.

Tela:

NF-e Fornecedor

Fornecedor:
ABC Distribuidora

Itens:

☑ Geladeira 400L     10 un
☑ Sofá 3 lugares      5 un
☐ Produto desconhecido

Ações:

Confirmar Recebimento

ou

Enviar para análise
20.5 Geração do movimento de estoque

Após aprovação:

Criar:

Stock Move

Exemplo:

Origem:
Fornecedor

Destino:
Depósito Principal

Produto:
Geladeira

Quantidade:
10
20.6 Atualização de custo

A entrada deve atualizar:

Custo médio

Exemplo:

Antes:

100 unidades
Custo R$ 500

Entrada:

20 unidades
Custo R$ 550

Novo custo:

(100*500 + 20*550) / 120
20.7 Integração com Purchase

O XML pode validar contra pedido de compra:

Pedido Compra

Produto:
100 unidades

NF-e Entrada

Produto:
100 unidades

Resultado:

OK

Ou:

Pedido:
100 unidades

Recebido:
120 unidades

Status:
Divergência
20.8 Auditoria

A entrada deve manter:

NF-e XML original

↓

Documento Fiscal

↓

Recebimento

↓

Stock Move

↓

Custo

↓

Contabilidade

Nada deve ser perdido.

20.9 Arquitetura dos módulos

Eu ajustaria a arquitetura assim:

Document Platform
        |
        |
Fiscal Engine
        |
        |
Purchase Receipt
        |
        |
Inventory Core
        |
        |
Stock Engine
        |
        |
Cost Engine
