# BusinessUI Design Rules

## Princípio Fundamental

> **COBOL é o cérebro. BusinessUI é a cara.**
>
> O Business Kernel (COBOL) é responsável por todas as regras de negócio,
> validações e persistência. A BusinessUI é 100% focada na experiência
> do usuário. Podemos redesenhar qualquer tela sem tocar no Kernel.
>
> O usuário nunca deve sentir que está "operando um ERP".
> Ele deve sentir que está usando uma ferramenta que entende seu trabalho
> e elimina tarefas repetitivas.

---

## Platform Philosophy

> **Simple is always better than complex.**
> Simples é sempre melhor do que complexo.

Design systems that are easy to understand, easy to maintain, easy to extend, and easy to use.
Avoid unnecessary abstractions. Prefer explicit behavior over hidden magic.
Every feature should solve a real business problem.
Performance and maintainability always come first.

---

## Regras Obrigatórias

### R1 — Limite de campos visíveis
Nenhuma tela pode exibir mais de **7 campos** no estado inicial.
Campos adicionais devem ser agrupados em seções expansíveis,
modais secundários ou revelados sob demanda.

*Por que:* Reduz carga cognitiva. O usuário vê apenas o essencial
e decide se quer mais detalhes.

### R2 — Estado inicial informativo
Nenhuma tela abre **vazia** quando há dados relevantes disponíveis.
- Se há registros, mostre uma lista ou resumo.
- Se não há registros, mostre uma mensagem útil + ação sugerida.
- Se o usuário já usou o sistema antes, mostre os últimos dados acessados.

*Proibido:* Telas em branco com apenas "nenhum registro encontrado".

### R3 — Confirmação em operações críticas
Toda operação que cause impacto (excluir, arquivar, aprovar, cancelar,
alterar status, desativar) exige confirmação explícita.
- Use `confirm()` ou modal de confirmação.
- A mensagem deve descrever **o que vai acontecer** em linguagem clara.

*Exemplo bom:* "Tem certeza que deseja arquivar o pedido PO-A3B2C? 
Ele ficará invisível nos relatórios padrão mas ainda poderá ser consultado."

*Exemplo ruim:* "Confirma?"

### R4 — Erro sempre com ação
Nenhuma mensagem de erro termina sem sugerir **o que o usuário pode fazer**.
- "SKU já existe" → "SKU já cadastrado para o item X. Use outro código ou edite o item existente."
- "Conexão recusada" → "Não foi possível conectar ao servidor. Verifique sua rede e tente novamente."

### R5 — Eficiência de cliques
Nenhuma operação frequente pode exigir **mais cliques que o necessário**.
- Tarefas comuns (criar, salvar, buscar) devem estar a 1 clique de distância.
- Atalhos de teclado para as 5 ações mais usadas de cada módulo.
- Não obrigar o usuário a passar por modais desnecessários.

### R6 — Atalhos de teclado consistentes
Atalhos de teclado são os **mesmos entre todos os módulos**:

| Ação | Atalho |
|------|--------|
| Novo registro | `Ctrl+N` |
| Salvar | `Ctrl+S` |
| Buscar/Pesquisar | `Ctrl+F` |
| Fechar modal | `Esc` |
| Avançar campo | `Tab` |
| Confirmar ação | `Enter` (em modais de confirmação) |
| Ajuda contextual | `F1` |

### R7 — Pesquisa universal acessível
Toda ação importante do sistema pode ser encontrada por uma
**pesquisa universal** (alcance `Ctrl+K` ou `/`).
- Busca por nome de tela, entidade, ação.
- Resultados em até 300ms.
- Atalho visível em todo canto inferior direito ou header.

### R8 — Preenchimento automático inteligente
O sistema **sempre preenche** tudo o que puder inferir:
- Números de documento gerados automaticamente (PO-20260726-0001).
- Datas padrão (hoje, fim do mês, +30 dias conforme contexto).
- Nome do usuário logado em campos "criado por", "responsável".
- Fornecedor/Cliente após digitar 3 caracteres (autocomplete).
- Endereço a partir do CEP.
- Preço sugerido a partir do último acordo/preço histórico.

*Regra de ouro:* Se o sistema consegue descobrir, o usuário não precisa digitar.

---

## Diretrizes de Implementação

### Hierarquia Visual
1. **Título da página** — o que o usuário está fazendo.
2. **Ação principal** — botão mais importante (salvar, criar, aprovar).
3. **Dados primários** — até 7 campos essenciais.
4. **Detalhes** — seções expansíveis ou abas.
5. **Ações secundárias** — editar, excluir, histórico.

### Cores e Feedback
- Ação primária: cor de destaque (primary).
- Ação destrutiva: vermelho com confirmação extra.
- Sucesso: feedback visual + mensagem auto-dismissível (3s).
- Carregando: skeleton screen (nunca spinner genérico).

### Responsividade
- Telas adaptáveis de 1024px a 1920px.
- Modais ocupam no máximo 80% da viewport.
- Tabelas com scroll horizontal em viewports estreitas.

---

## Checklist de Revisão de Tela

Antes de aprovar qualquer tela nova, verificar:

- [ ] Máximo 7 campos visíveis inicialmente?
- [ ] Estado inicial é informativo (nunca vazio)?
- [ ] Operações críticas têm confirmação clara?
- [ ] Mensagens de erro sugerem ação?
- [ ] Atalhos de teclado seguem o padrão?
- [ ] Campos obrigatórios estão marcados?
- [ ] Preenchimento automático foi aplicado onde possível?
- [ ] A tela funciona sem depender de IDs internos visíveis ao usuário?

---

*Este documento é vivo. Qualquer membro da equipe pode propor alterações via PR.*
