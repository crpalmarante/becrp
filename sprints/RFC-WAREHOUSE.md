# RFC-WAREHOUSE.md

# RFC: Warehouse Management Architecture (WMS)

**Status:** Proposta

**Versão:** 1.0

**Data:** 29/07/2026

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

# 1. Objetivo

Definir a arquitetura do módulo **Warehouse**, responsável pela organização física dos armazéns, depósitos e centros de distribuição do ERP.

O Warehouse é responsável por administrar **onde** os produtos estão armazenados e **como** eles são movimentados fisicamente.

O Warehouse **não controla estoque**.

O controle das quantidades pertence ao módulo **Inventory**.

---

# 2. Motivação

Nos ERPs tradicionais é comum confundir:

* Depósito
* Estoque
* Localização

Como se fossem a mesma entidade.

Na arquitetura proposta esses conceitos são independentes.

| Domínio   | Responsabilidade    |
| --------- | ------------------- |
| Inventory | Quanto existe       |
| Warehouse | Onde está           |
| Sales     | Quem comprou        |
| Purchase  | Quem forneceu       |
| Fiscal    | Documento fiscal    |
| Finance   | Valores financeiros |

---

# 3. Escopo

O módulo Warehouse será responsável por:

* Estrutura física dos depósitos
* Endereçamento logístico
* Organização das localizações
* Recebimento físico
* Movimentações internas
* Separação
* Expedição
* Controle operacional

Não faz parte do Warehouse:

* Controle financeiro
* Controle fiscal
* Controle de preços
* Controle comercial

---

# 4. Arquitetura

```text
Warehouse

├── Warehouse Core
│
├── Location Tree
│
├── Warehouse Structure
│
├── Receiving Area
│
├── Put Away
│
├── Internal Movements
│
├── Picking
│
├── Packing
│
├── Shipping
│
├── Warehouse Tasks
│
├── Warehouse Resources
│
├── Warehouse Rules
│
└── Warehouse Analytics
```

---

# 5. Warehouse Core

O Warehouse Core é responsável por:

* cadastro de depósitos;
* identificação única;
* empresas;
* filiais;
* configurações.

Exemplo:

```text
CD Principal

Loja Centro

Loja Norte

Almoxarifado

Assistência Técnica
```

---

# 6. Árvore de Localizações

Toda localização pertence a uma árvore hierárquica.

Modelo:

```text
Empresa

└── Filial

    └── Warehouse

        ├── Zona

        │

        ├── Corredor

        │

        ├── Rack

        │

        ├── Prateleira

        │

        └── Bin
```

Essa estrutura deve permitir profundidade variável.

Nem toda empresa utilizará todos os níveis.

---

# 7. Warehouse Structure

A estrutura física poderá conter:

## Warehouse

Representa um depósito.

---

## Zone

Representa uma área lógica.

Exemplos:

* Recebimento
* Qualidade
* Armazenagem
* Expedição
* Quarentena
* Alto Valor
* Refrigerados

---

## Aisle

Corredores.

Exemplo:

```text
A01

A02

A03
```

---

## Rack

Estruturas metálicas.

---

## Shelf

Prateleiras.

---

## Bin

Menor posição física controlada.

Exemplo:

```text
A-05-02-03
```

---

# 8. Endereçamento

Todo produto deverá possuir localização completa.

Exemplo:

```text
Empresa

↓

Filial

↓

Warehouse

↓

Zona

↓

Corredor

↓

Rack

↓

Shelf

↓

Bin
```

O Inventory utilizará esse endereço para localizar fisicamente o produto.

---

# 9. Receiving Area

Área destinada ao recebimento.

Responsabilidades:

* descarga;
* conferência;
* inspeção;
* aguardando armazenagem.

Fluxo:

```text
Fornecedor

↓

Recebimento

↓

Conferência

↓

Put Away
```

---

# 10. Put Away

Após conferência o sistema define automaticamente a localização ideal.

Critérios possíveis:

* espaço disponível;
* peso;
* volume;
* categoria;
* temperatura;
* giro;
* regras de armazenagem.

---

# 11. Internal Movements

Movimentações internas.

Exemplos:

* Bin → Bin
* Zona → Zona
* Warehouse → Warehouse

Toda movimentação deverá possuir:

* origem;
* destino;
* operador;
* horário;
* motivo.

---

# 12. Picking

Separação de pedidos.

Responsabilidades:

* gerar lista de separação;
* otimizar percurso;
* confirmar coleta.

Modelos previstos:

* Picking simples
* Batch Picking
* Wave Picking
* Zone Picking

---

# 13. Packing

Empacotamento.

Controla:

* caixas;
* volumes;
* etiquetas;
* peso;
* cubagem.

---

# 14. Shipping

Expedição.

Responsabilidades:

* consolidação;
* carregamento;
* romaneios;
* integração com transportadoras;
* confirmação de saída.

---

# 15. Warehouse Tasks

Toda atividade operacional gera uma tarefa.

Exemplos:

* Receber
* Conferir
* Armazenar
* Separar
* Embalar
* Transferir
* Inventariar

Cada tarefa poderá ser atribuída a um operador ou equipe.

---

# 16. Warehouse Resources

Cadastro dos recursos utilizados.

Exemplos:

* empilhadeiras;
* paleteiras;
* leitores;
* coletores;
* impressoras;
* balanças.

---

# 17. Warehouse Rules

Permite definir regras de armazenagem.

Exemplos:

## Capacidade

* peso máximo;
* volume máximo;
* quantidade máxima.

## Compatibilidade

Produtos incompatíveis.

Exemplo:

* inflamáveis;
* alimentos;
* químicos.

## Estratégias

* FIFO
* FEFO
* LIFO (quando aplicável)

---

# 18. Warehouse Analytics

Indicadores operacionais.

Exemplos:

* ocupação;
* capacidade disponível;
* produtividade;
* tempo médio de separação;
* tempo médio de recebimento;
* pedidos em separação;
* pedidos aguardando expedição.

---

# 19. Integrações

## Inventory

Recebe:

* localizações;
* movimentações físicas.

Envia:

* saldo disponível;
* reservas.

---

## Purchase

Origina:

* recebimentos.

---

## Sales

Origina:

* separações;
* expedições.

---

## Logistics

Recebe:

* volumes;
* cargas;
* roteiros.

---

## Fiscal

Recebe confirmação de saída para emissão dos documentos fiscais quando aplicável.

---

# 20. Responsabilidades

## O Warehouse é responsável por

* organização física;
* endereçamento;
* armazenagem;
* movimentação interna;
* separação;
* expedição;
* produtividade operacional.

## O Warehouse não é responsável por

* estoque contábil;
* custos;
* impostos;
* pagamentos;
* faturamento;
* documentos fiscais.

---

# 21. Evoluções Futuras

O módulo foi projetado para suportar futuramente:

* RFID;
* Código de barras GS1;
* IoT;
* Voice Picking;
* Warehouse Robots;
* AGV (Automated Guided Vehicles);
* Drones para inventário;
* Digital Twin do armazém;
* Heat Maps;
* Warehouse Maps 2D e 3D;
* IA para otimização de armazenagem;
* IA para otimização de rotas de picking.

---

# 22. RFCs Relacionadas

* RFC-INVENTORY-ARCHITECTURE.md
* RFC-RECEIVING.md
* RFC-PICKING.md
* RFC-PACKING.md
* RFC-SHIPPING.md
* RFC-TRANSFER.md
* RFC-COUNTING.md
* RFC-REPLENISHMENT.md

---

# 23. Conclusão

O Warehouse representa o **domínio operacional da armazenagem**, sendo responsável exclusivamente pela gestão física dos armazéns e depósitos.

Sua separação do módulo Inventory reduz o acoplamento, facilita a escalabilidade do ERP e permite atender desde pequenas lojas até centros de distribuição de alta complexidade, preservando uma arquitetura modular, extensível e preparada para futuras automações.
