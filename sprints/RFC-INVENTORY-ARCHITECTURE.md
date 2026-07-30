# RFC-INVENTORY-ARCHITECTURE.md

# RFC: Inventory Architecture

**Status:** Proposta

**Versão:** 1.0

**Autor:** Equipe ERP

**Data:** 29/07/2026

---

# 1. Objetivo

Definir a arquitetura oficial do módulo **Inventory** do ERP.

O Inventory é responsável pelo controle físico e lógico dos produtos da empresa, garantindo rastreabilidade, disponibilidade, auditoria e integração com os demais módulos do sistema.

Esta RFC estabelece os limites do módulo, seus componentes internos e sua integração com Sales, Purchase, Fiscal, Finance e Logistics.

---

# 2. Princípios

O módulo Inventory deve seguir os seguintes princípios:

* Todo estoque é baseado em movimentações.
* Nenhuma quantidade deve ser alterada diretamente.
* Todo movimento deve possuir origem e destino.
* Todo movimento deve ser auditável.
* O estoque físico e o estoque disponível são conceitos diferentes.
* O Inventory não executa regras fiscais.
* O Inventory não executa regras financeiras.
* O Inventory responde apenas pela movimentação dos bens.

---

# 3. Escopo

O módulo Inventory será composto pelos seguintes componentes:

```text
Inventory

├── Warehouse
├── Stock
├── Receiving
├── Reservations
├── Transfers
├── Picking
├── Packing
├── Shipping
├── Counting
├── Cost
├── Lots
├── Serials
├── Returns
├── Quality
└── Replenishment
```

Cada componente possui responsabilidade única e bem definida.

---

# 4. Componentes

## 4.1 Warehouse

Responsável pela estrutura física do estoque.

Exemplos:

* Centros de distribuição
* Lojas
* Depósitos
* Almoxarifados

Controla:

* corredores;
* ruas;
* prateleiras;
* posições;
* zonas;
* docas.

Não controla quantidade.

---

## 4.2 Stock

Responsável pela posição atual dos produtos.

Controla:

* estoque físico;
* estoque reservado;
* estoque disponível;
* estoque em trânsito;
* estoque consignado.

Toda alteração é resultado de movimentações.

---

## 4.3 Receiving

Responsável pelo recebimento de mercadorias.

Principais funções:

* recebimento físico;
* conferência;
* divergências;
* integração com compras;
* integração com XML de fornecedores.

O parser da NF-e pertence ao módulo Fiscal/Document Platform. O Receiving utiliza as informações já interpretadas para realizar a conferência e autorizar a entrada em estoque.

---

## 4.4 Reservations

Responsável pela reserva de produtos.

Exemplos:

* pedido de venda;
* e-commerce;
* produção;
* transferência.

Reservar estoque não significa baixar estoque.

---

## 4.5 Transfers

Responsável pelas movimentações entre localizações.

Exemplos:

* loja → loja;
* CD → loja;
* depósito → produção.

Toda transferência gera duas movimentações:

* saída da origem;
* entrada no destino.

---

## 4.6 Picking

Responsável pela separação dos pedidos.

Funções:

* geração de listas de separação;
* otimização de rotas;
* agrupamento de pedidos;
* confirmação de coleta.

---

## 4.7 Packing

Responsável pela embalagem dos produtos.

Controla:

* volumes;
* caixas;
* peso;
* cubagem;
* etiquetas.

---

## 4.8 Shipping

Responsável pela expedição.

Integra-se com:

* transportadoras;
* delivery;
* romaneios;
* comprovantes de entrega.

---

## 4.9 Counting

Responsável pelos inventários.

Suporta:

* inventário geral;
* inventário rotativo;
* contagem por localização;
* contagem por categoria.

Diferenças geram movimentos de ajuste auditáveis.

---

## 4.10 Cost

Responsável pelo cálculo dos custos.

Modelos previstos:

* custo médio;
* FIFO;
* custo padrão.

O módulo não executa contabilidade, apenas calcula os valores do estoque.

---

## 4.11 Lots

Responsável pelo controle por lote.

Aplicável a:

* alimentos;
* medicamentos;
* matérias-primas;
* produtos químicos.

---

## 4.12 Serials

Responsável pelo controle de números de série.

Exemplos:

* eletrodomésticos;
* notebooks;
* celulares;
* equipamentos.

Cada unidade possui identidade própria.

---

## 4.13 Returns

Responsável pelas devoluções.

Tipos:

* devolução de cliente;
* devolução ao fornecedor;
* retorno interno;
* garantia.

O destino do item dependerá das regras da empresa:

* estoque;
* quarentena;
* assistência;
* descarte.

---

## 4.14 Quality

Responsável pela inspeção da qualidade.

Permite:

* inspeção por amostragem;
* inspeção total;
* aprovação;
* rejeição;
* quarentena.

---

## 4.15 Replenishment

Responsável pela reposição automática.

Objetivos:

* manter estoque mínimo;
* sugerir transferências;
* sugerir compras;
* abastecer lojas automaticamente.

---

# 5. Integrações

## Sales

* consulta disponibilidade;
* realiza reservas;
* solicita expedição.

---

## Purchase

* cria recebimentos;
* acompanha entregas do fornecedor.

---

## Fiscal

* interpreta XML;
* fornece dados fiscais;
* registra documentos fiscais.

O Inventory não interpreta XML nem calcula impostos.

---

## Finance

Recebe apenas informações necessárias para avaliação de estoque.

Não controla pagamentos.

---

## Logistics

Responsável pelo transporte.

O Inventory apenas entrega os volumes preparados.

---

# 6. Responsabilidades

O Inventory é responsável por:

* movimentações;
* localização;
* disponibilidade;
* reservas;
* custos;
* rastreabilidade.

Não é responsável por:

* vendas;
* compras;
* emissão fiscal;
* pagamentos;
* cobrança.

---

# 7. Diretrizes Arquiteturais

* Componentes devem ser independentes.
* Comunicação por interfaces bem definidas.
* Nenhum componente deve conhecer regras internas dos demais.
* Todas as movimentações devem ser auditáveis.
* O módulo deve suportar múltiplas empresas, múltiplas filiais e múltiplos depósitos.

---

# 8. Evoluções Futuras

Os seguintes componentes poderão ser adicionados sem alterar a arquitetura principal:

* Forecast Engine
* Slotting Engine
* Cross Dock Engine
* Wave Picking
* Barcode Engine
* RFID Engine
* Heat Map
* ABC Classification
* ATP (Available To Promise)
* Warehouse Map
* IoT Integration
* Robotic Warehouse Integration

---

# 9. RFCs Derivadas

Esta RFC serve como documento mestre para as seguintes RFCs específicas:

* RFC-WAREHOUSE.md
* RFC-STOCK.md
* RFC-RECEIVING.md
* RFC-RESERVATION.md
* RFC-TRANSFER.md
* RFC-PICKING.md
* RFC-PACKING.md
* RFC-SHIPPING.md
* RFC-COUNTING.md
* RFC-COST.md
* RFC-LOTS.md
* RFC-SERIALS.md
* RFC-RETURNS.md
* RFC-QUALITY.md
* RFC-REPLENISHMENT.md

---

# 10. Conclusão

O módulo Inventory deve ser tratado como um domínio de negócio independente, responsável exclusivamente pelo controle físico e lógico dos bens da empresa.

A separação em componentes especializados reduz o acoplamento, facilita testes, melhora a escalabilidade e permite evolução incremental do ERP sem comprometer os demais módulos.
