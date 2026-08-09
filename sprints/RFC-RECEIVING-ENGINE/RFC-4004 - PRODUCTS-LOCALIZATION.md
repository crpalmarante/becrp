# RFC-4004 - Localização de Produtos

| Campo | Valor |
|--------|-------|
| RFC | 4004 |
| Nome | Localização de Produtos |
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

Esta RFC define o módulo **Localização de Produtos** do Retail ERP.

O módulo é responsável por identificar e localizar produtos recebidos através de documentos externos, relacionando os itens recebidos com os produtos existentes no cadastro interno.

Seu objetivo é garantir que uma mercadoria recebida seja corretamente associada ao produto correspondente dentro do ERP.

---

# 2. Motivação

Documentos de fornecedores normalmente utilizam informações próprias para identificar produtos.

Um mesmo produto pode possuir diferentes identificações:

- código interno do fornecedor;
- código EAN;
- GTIN;
- descrição comercial;
- referência do fabricante;
- código interno da empresa.

Exemplo:

Fornecedor:

O sistema precisa identificar que ambos representam o mesmo item.

---

# 3. Responsabilidades

O módulo Localização de Produtos é responsável por:

- localizar produtos existentes;
- sugerir correspondências;
- controlar vínculos fornecedor × produto;
- registrar histórico de identificações;
- permitir aprovação manual;
- criar pendências quando não houver correspondência;
- manter regras de localização.

---

# 4. Não é responsabilidade do módulo

O módulo não executa:

- criação física do produto;
- alteração de preço;
- movimentação de estoque;
- cálculo fiscal;
- atualização financeira.

Essas responsabilidades pertencem aos módulos especializados.

---

# 5. Fontes de Identificação

A localização pode utilizar:

## Código do fornecedor

Exemplo:

--- 
Fornecedor A
Código: ABC123

## GTIN / EAN

Exemplo:

7891234567890

---

## Referência do fabricante

Exemplo:


Modelo: XYZ-400


---

## Descrição

Utilizada como último recurso.

Exemplo:


Geladeira Duplex 400 litros inox


---

# 6. Prioridade de Localização

A ordem de busca deve seguir:


1 - Código interno já conhecido

2 - GTIN/EAN

3 - Código fornecedor x produto

4 - Referência fabricante

5 - Similaridade de descrição

6 - Análise manual


---

# 7. Fluxo Geral


Item recebido

↓

Buscar identificação conhecida

↓

Encontrou?

 Sim
  |
  v

Associar produto

 Não
  |
  v

Criar pendência

↓

Análise usuário

↓

Criar vínculo


---

# 8. Vínculo Fornecedor × Produto

O sistema deve manter relacionamento:


SupplierProductReference

supplier_id

product_id

supplier_code

supplier_description

gtin

manufacturer_reference

last_seen_date


---

# 9. Sugestão Automática

O sistema pode sugerir produtos utilizando:

- códigos conhecidos;
- GTIN;
- histórico anterior;
- similaridade textual;
- fabricante;
- categoria.

A sugestão nunca substitui uma decisão quando houver risco de associação incorreta.

---

# 10. Pendências

Quando um produto não for localizado:

Criar pendência:


ProductLocalizationPending


Informações:

- fornecedor;
- documento origem;
- descrição recebida;
- código fornecedor;
- GTIN;
- usuário responsável;
- status.

Estados:


Novo

Em análise

Associado

Ignorado


---

# 11. Integração com Cadastro de Produtos

Quando permitido:

O módulo pode solicitar criação de produto.

Fluxo:


Produto não encontrado

↓

Solicitação criação

↓

Cadastro Produto

↓

Novo produto criado

↓

Vínculo realizado


A criação pertence ao módulo Produto.

---

# 12. Auditoria

Registrar:

- usuário;
- data;
- produto localizado;
- origem da localização;
- regra utilizada;
- alterações realizadas.

Exemplo:


Produto localizado por:

GTIN

Usuário:
admin

Data:
2026-07-31


---

# 13. Eventos

O módulo publica eventos:


product.localization.started

product.localization.completed

product.localization.failed

product.localization.pending

product.reference.created


---

# 14. Integrações

## Recebimento

Fornece os itens que precisam ser localizados.

## Cadastro de Produtos

Mantém os produtos internos.

## Compras

Utiliza histórico fornecedor × produto.

## Inventário

Recebe produtos já identificados.

---

# 15. Princípios

O módulo segue:

- Simples é melhor do que complexo.
- Nunca confiar apenas em descrição.
- Toda associação deve ser rastreável.
- Sugestão automática não elimina controle humano.
- Cada módulo possui responsabilidade única.

---

# 16. Roadmap

Próximas RFCs:

RFC-4005 - Atualização de Fornecedores

RFC-4006 - Workspace de Recebimento

RFC-4007 - Pendências de Recebimento

RFC-4008 - Conferência Física

RFC-4009 - Integração com Inventário

RFC-4010 - Integração com Financeiro

RFC-4011 - Integração Fiscal

RFC-4012 - Receiving Event Model

---

# 17. Considerações Finais

O módulo Localização de Produtos é responsável por criar uma ponte entre documentos externos e o cadastro interno do ERP.

Ele evita duplicação de produtos, reduz erros operacionais e permite que diferentes fornecedores sejam integrados mantendo uma estrutura simples e confiável.

A localização correta dos produtos é uma etapa fundamental para garantir qualidade no recebimento, estoque e fiscal.
