# Sprint 10 — Identity & Access Core

## Objetivo

Implementar a infraestrutura central de identidade, autenticação, autorização e gerenciamento de contexto da plataforma.

Esta Sprint estabelece a base para todos os módulos do sistema e deve ser concluída antes do desenvolvimento dos módulos de negócio (POS, Fiscal, Financeiro, Estoque, CRM, etc.).

---

# Escopo

## 1. Setup Inicial

Assistente executado automaticamente na primeira inicialização da plataforma.

### Funcionalidades

* Criação do Administrador Master
* Criação da primeira Empresa
* Criação da primeira Filial
* Criação do primeiro Terminal (opcional)
* Configurações básicas da plataforma
* Finalização do Setup

Após a conclusão, o Setup não poderá ser executado novamente sem intervenção administrativa.

---

## 2. Autenticação

Implementação do serviço de autenticação da plataforma.

### Funcionalidades

* Login
* Logout
* Sessão autenticada
* Expiração de sessão
* Renovação de sessão
* Alteração de senha
* Recuperação de senha
* Bloqueio após tentativas inválidas (configurável)

### Segurança

* Hash seguro de senhas (Argon2id ou bcrypt)
* Tokens de sessão
* Sessões revogáveis
* Auditoria de autenticação

---

## 3. Usuários

CRUD completo de usuários.

### Funcionalidades

* Cadastro
* Edição
* Exclusão lógica
* Ativação
* Bloqueio
* Reset de senha
* Alteração de senha obrigatória (opcional)

---

## 4. Empresas

CRUD completo.

### Informações

* Dados cadastrais
* Dados fiscais
* Status
* Configurações gerais

A plataforma é nativamente multiempresa.

---

## 5. Filiais

CRUD completo.

Cada filial pertence a uma empresa.

### Informações

* Dados cadastrais
* Endereço
* Status
* Configurações locais

---

## 6. Terminais

Cadastro dos dispositivos que acessam a plataforma.

Exemplos:

* POS
* Notebook
* Tablet
* Coletor WMS
* Terminal de montagem

### Informações

* Identificação
* Nome
* Tipo
* Empresa
* Filial
* Status
* Configurações locais

O Terminal representa o equipamento utilizado e não o usuário.

---

## 7. Perfis de Acesso

Cadastro dinâmico de perfis.

Exemplos

* Administrador
* Supervisor
* Operador de Caixa
* Fiscal
* Financeiro
* Comprador
* Estoquista
* Montador
* Motorista

Cada perfil possuirá permissões próprias.

Não existem perfis fixos na aplicação.

---

## 8. Permissões

Sistema de autorização baseado em permissões.

Cada perfil poderá possuir permissões específicas sobre:

* Módulos
* Funcionalidades
* Ações
* Operações

O sistema não dependerá exclusivamente do nome do perfil.

---

## 9. Vínculos

Relacionamentos entre usuários e a estrutura organizacional.

### Usuário × Empresa

Um usuário poderá possuir acesso a uma ou mais empresas.

---

### Usuário × Filial

Um usuário poderá possuir acesso apenas às filiais autorizadas.

---

### Usuário × Perfil

O mesmo usuário poderá possuir perfis diferentes em empresas distintas.

Exemplo

Empresa A

Administrador

Empresa B

Supervisor

Empresa C

Operador

---

## 10. Context Service

Serviço responsável por manter o contexto ativo da sessão.

O Context Service não armazena dados de negócio.

Ele apenas mantém o estado atual da plataforma.

### Contexto Global

* Usuário ativo
* Empresa ativa
* Filial ativa
* Perfil ativo
* Terminal ativo
* Idioma
* Tema

### Contexto do Módulo

* Módulo atual
* Workspace
* Sidebar ativa
* Abas abertas

### Contexto da Operação

Quando existir uma operação em andamento.

Exemplos

* Atendimento atual (POS)
* Pedido em edição
* Documento em edição

Ao finalizar a operação, esse contexto é descartado automaticamente.

---

## 11. Workspace

Primeira tela apresentada após autenticação.

### Recursos

* Workspace
* Favoritos
* Recentes
* Pesquisa Global
* Seleção de módulos

O Workspace não possui menu lateral.

---

## 12. Navegação

Após entrar em um módulo.

A navegação passa a utilizar uma Sidebar contextual.

### Recursos

* Sidebar dinâmica
* Breadcrumb
* Histórico
* Favoritos
* Pesquisa Global

A Sidebar é construída conforme:

* Permissões do usuário
* Módulos instalados
* Capacidades habilitadas
* Contexto atual

---

## 13. Segurança

Serviços centrais da plataforma.

### Recursos

* Sessões
* Auditoria
* Controle de acesso
* Revogação de sessão
* Logs de autenticação

---

# Arquitetura

Esta Sprint implementa os seguintes serviços do Core:

* Authentication Service
* Authorization Service
* Session Service
* Context Service
* User Service
* Company Service
* Branch Service
* Terminal Service
* Profile Service
* Permission Service
* Workspace Service
* Navigation Service

---

# Fora do Escopo

Não fazem parte desta Sprint:

* POS
* Comercial
* Compras
* Estoque
* Fiscal
* Financeiro
* CRM
* WMS
* Produção
* BI
* Relatórios
* Impressão
* Workflow
* Event Bus
* Capability Manager

Esses componentes serão implementados em Sprints posteriores.

---

# Resultado Esperado

Ao final desta Sprint a plataforma deverá ser capaz de:

* Executar o Setup Inicial
* Autenticar usuários
* Gerenciar empresas e filiais
* Gerenciar terminais
* Gerenciar perfis e permissões
* Manter sessões autenticadas
* Manter o contexto da sessão
* Exibir o Workspace inicial
* Navegar entre módulos de forma segura e contextual
* Fornecer a infraestrutura de identidade e acesso para todos os módulos futuros
