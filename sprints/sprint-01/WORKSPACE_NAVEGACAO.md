# Sprint 01 — Workspace & Navegação da Plataforma

## Objetivo

Implementar a tela principal da plataforma (Workspace), responsável por servir como ponto de entrada para todos os módulos do sistema.

Esta Sprint define a experiência de navegação da plataforma e estabelece o padrão que será utilizado por todos os módulos.

---

# Objetivos da Interface

A tela principal deve permitir que o usuário:

* Identifique rapidamente onde está.
* Acesse seus módulos com poucos cliques.
* Visualize informações relevantes para sua função.
* Navegue de forma simples e consistente.
* Trabalhe sem menus complexos.

---

# Estrutura da Tela

A tela principal será composta por quatro áreas.

## 1. Barra Superior (Top Bar)

Sempre visível.

Contém:

* Logotipo da plataforma
* Pesquisa Global
* Empresa ativa
* Filial ativa
* Terminal ativo (quando aplicável)
* Notificações
* Perfil do usuário
* Configurações
* Logout

Esta barra nunca muda, independentemente do módulo ativo.

---

## 2. Workspace

Área principal da plataforma.

Apresenta os módulos disponíveis para o usuário.

Exemplo:

* POS
* Comercial
* Estoque
* Compras
* Financeiro
* Fiscal
* CRM
* Produção
* WMS
* BI

Os módulos são exibidos em formato de cartões (cards).

Cada cartão representa um módulo da plataforma.

---

## 3. Painel de Informações

Área destinada a informações pessoais do usuário.

Exemplos:

### Favoritos

* POS
* Clientes
* Produtos

### Recentes

* Pedido 1458
* Cliente João Silva
* Produto XPTO

### Minhas Atividades

* Aprovações pendentes
* Entregas
* Inventários
* Tarefas

---

## 4. Rodapé (Opcional)

Informações da plataforma.

* Versão
* Ambiente
* Empresa
* Data e hora
* Status da conexão

---

# Workspace

O Workspace é a página inicial da plataforma.

Não possui Sidebar.

Não possui menu lateral.

Seu objetivo é apenas permitir o acesso aos módulos.

---

# Cartões dos Módulos

Cada módulo é representado por um cartão.

Cada cartão deve conter:

* Ícone
* Nome
* Descrição curta
* Indicadores rápidos (quando disponíveis)

Exemplo

POS

* Caixa aberto
* Vendas do dia

Financeiro

* Contas vencidas
* Recebimentos hoje

Estoque

* Inventários pendentes
* Transferências

Essas informações são apenas indicativas e nunca substituem o módulo.

---

# Abertura de Módulos

Ao clicar em um cartão:

* O Workspace é ocultado.
* O módulo é carregado.
* A Sidebar específica do módulo é exibida.
* A navegação passa a ocorrer dentro do módulo.

---

# Sidebar

A Sidebar somente existe após a abertura de um módulo.

Ela é responsável pela navegação interna.

Cada módulo possui sua própria Sidebar.

Exemplo:

## POS

* Venda
* Cotações
* Pedidos
* Reservas
* Entregas
* Caixa

---

## Estoque

* Produtos
* Recebimento
* Inventário
* Transferências
* Etiquetas

---

## Financeiro

* Receber
* Pagar
* Bancos
* Conciliação

---

# Sidebar Contextual

A Sidebar é construída dinamicamente considerando:

* Permissões do usuário
* Perfil ativo
* Empresa ativa
* Filial ativa
* Capacidades habilitadas
* Módulos instalados

Nenhuma opção deve ser exibida caso o usuário não possua acesso.

---

# Pesquisa Global

Disponível permanentemente na Top Bar.

Permite localizar:

* Clientes
* Produtos
* Pedidos
* Documentos
* Empresas
* Usuários
* Relatórios
* Configurações

A Pesquisa Global deve funcionar independentemente do módulo ativo.

---

# Favoritos

Cada usuário poderá definir seus módulos e funcionalidades favoritas.

Os favoritos ficam disponíveis no Workspace.

---

# Recentes

A plataforma manterá o histórico dos últimos acessos do usuário.

Exemplos:

* Pedido
* Cliente
* Produto
* Documento Fiscal

---

# Notificações

A Top Bar deve apresentar notificações em tempo real.

Exemplos:

* Aprovação pendente
* Documento rejeitado
* Entrega atrasada
* Pagamento recebido

---

# Navegação

Fluxo da plataforma:

Login

↓

Workspace

↓

Seleção do módulo

↓

Sidebar do módulo

↓

Funcionalidade

---

# Requisitos Funcionais

* Workspace responsivo.
* Pesquisa Global disponível em todas as telas.
* Top Bar fixa.
* Cards dos módulos configuráveis.
* Sidebar dinâmica.
* Navegação consistente.
* Breadcrumb dentro dos módulos.
* Suporte para teclado e mouse.
* Preparado para telas touch.

---

# Fora do Escopo

Não fazem parte desta Sprint:

* Desenvolvimento dos módulos de negócio.
* Regras comerciais.
* POS.
* Fiscal.
* Financeiro.
* Estoque.
* CRM.
* WMS.
* Workflow.
* Event Bus.

Esta Sprint trata exclusivamente da experiência de navegação da plataforma.

---

# Critérios de Aceite

Ao final da Sprint deverá ser possível:

* Realizar login.
* Visualizar o Workspace.
* Visualizar apenas os módulos autorizados.
* Pesquisar utilizando a Pesquisa Global.
* Abrir qualquer módulo disponível.
* Exibir automaticamente a Sidebar correspondente ao módulo.
* Navegar entre as funcionalidades do módulo.
* Retornar ao Workspace a qualquer momento.
* Manter uma experiência uniforme em toda a plataforma.

---

# Princípios

* A plataforma deve se adaptar ao usuário.
* O Workspace é a porta de entrada do sistema.
* A Sidebar existe apenas dentro dos módulos.
* A navegação deve ser simples, consistente e contextual.
* O usuário deve acessar qualquer funcionalidade com o menor número possível de cliques.
