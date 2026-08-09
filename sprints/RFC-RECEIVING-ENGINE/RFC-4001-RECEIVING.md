# RFC-4001 - Recebimento

| Campo | Valor |
|--------|-------|
| RFC | 4001 |
| Nome | Recebimento |
| Categoria | Recebimento |
| Status | Draft |
| Versão | 1.0 |

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

Esta RFC define o módulo **Recebimento** do Retail ERP.

O Recebimento é responsável por coordenar todo processo de entrada de mercadorias na empresa.

Seu papel é identificar a origem do recebimento, validar as informações e encaminhar os dados para os módulos responsáveis.

O Recebimento não pertence ao Inventário, ao Fiscal ou ao Financeiro.

Ele é um módulo próprio.

---

# 2. Motivação

Toda entrada de mercadorias possui um fluxo semelhante.

Independentemente da origem, normalmente existe:

- um documento de origem;
- uma empresa fornecedora;
- mercadorias;
- conferência;
- atualização de cadastros;
- movimentação de estoque;
- escrituração fiscal;
- geração de contas a pagar.

Centralizar esse fluxo em um único módulo reduz duplicidade e facilita a manutenção.

---

# 3. Responsabilidades

O módulo Recebimento é responsável por:

- iniciar o processo de recebimento;
- identificar a origem;
- validar informações obrigatórias;
- controlar o andamento do processo;
- registrar eventos;
- manter auditoria;
- coordenar a comunicação entre os módulos envolvidos.

---

# 4. Não é responsabilidade do Recebimento

O módulo Recebimento não executa:

- movimentação de estoque;
- cálculo de tributos;
- emissão de documentos fiscais;
- geração de contas a pagar;
- atualização direta de produtos;
- atualização direta de fornecedores.

Essas tarefas pertencem aos respectivos módulos especializados.

---

# 5. Origens

O Recebimento deve aceitar diferentes origens.

Inicialmente:

- NF-e de fornecedor
- Pedido de Compra
- Transferência
- Produção
- Devolução
- Bonificação
- Ajuste Manual

Novas origens poderão ser adicionadas futuramente sem alterar o funcionamento do módulo.

---

# 6. Fluxo Geral

Todos os recebimentos seguem o mesmo fluxo básico.

```text
Origem

↓

Recebimento

↓

Validação

↓

Conferência

↓

Confirmação

↓

Integrações
```

---

# 7. Integrações

Após a confirmação do recebimento, os módulos especializados são acionados conforme necessário.

Exemplos:

Inventário

- entrada física das mercadorias;
- atualização de saldos;
- lotes;
- números de série.

Fiscal

- escrituração;
- validações fiscais;
- armazenamento dos documentos.

Financeiro

- contas a pagar;
- parcelas;
- vencimentos.

Cadastro de Produtos

- novos produtos;
- atualização cadastral;
- relacionamento produto × fornecedor.

Cadastro de Parceiros

- atualização do fornecedor;
- contatos;
- endereços.

---

# 8. Modos de Recebimento

O módulo suporta três formas de operação.

## Manual

O usuário conduz todo o processo.

Exemplo:

Selecionar XML

↓

Revisar

↓

Confirmar

---

## Assistido

O sistema realiza a maior parte do processamento.

O usuário revisa apenas pendências.

---

## Automático

Todo o processamento ocorre sem intervenção humana.

Pendências são encaminhadas para análise posterior.

---

# 9. Estados

Todo recebimento possui um estado.

Estados iniciais:

- Novo
- Validando
- Aguardando Conferência
- Pendente
- Confirmado
- Processando
- Concluído
- Cancelado

---

# 10. Auditoria

Todo recebimento deve registrar:

- data;
- usuário;
- origem;
- alterações realizadas;
- eventos;
- erros encontrados.

Nenhuma operação crítica pode ocorrer sem registro.

---

# 11. Princípios

O módulo Recebimento segue os princípios definidos na RFC-0001 - Princípios da Arquitetura.

Em especial:

- Simples é melhor do que complexo.
- Cada módulo possui uma única responsabilidade.
- O negócio define a arquitetura.
- O usuário não deve conhecer detalhes técnicos.

---

# 12. Roadmap

As seguintes RFCs detalham este módulo.

RFC-4002 - Importação de NF-e

RFC-4003 - Monitor de XML

RFC-4004 - Localização de Produtos

RFC-4005 - Atualização de Fornecedores

RFC-4006 - Workspace de Recebimento

RFC-4007 - Pendências de Recebimento

RFC-4008 - Conferência Física

RFC-4009 - Integração com Inventário

RFC-4010 - Integração com Financeiro

RFC-4011 - Integração Fiscal

---

# 13. Considerações Finais

O Recebimento é um módulo de coordenação.

Ele não substitui o Inventário, o Fiscal ou o Financeiro.

Seu objetivo é centralizar o fluxo de entrada de mercadorias, oferecendo um único ponto de controle para diferentes tipos de recebimento, mantendo a arquitetura simples, desacoplada e alinhada aos processos de negócio.
