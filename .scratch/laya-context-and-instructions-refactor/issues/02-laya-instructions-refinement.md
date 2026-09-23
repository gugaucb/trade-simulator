# 02: Refinamento das Instruções e Critérios de Decisão em _predict_sync

**What to build:**
Reformular a instrução do método `_predict_sync` em `LayaDecisionEngine` para declarar de forma imperativa e explícita a escolha exclusiva entre as três operações de mercado ('buy', 'sell' ou 'hold'), alinhando os critérios aos princípios de paper trading SPOT (compra com cash disponível, venda com liquidação integral para cash e hold em dúvida ou risco).

**Blocked by:** 01: Enriquecimento Semântico do Contexto do Laya e Padronização

**Status:** completed

- [x] Atualizar a `instructions` de `action` em `_predict_sync` de modo a enunciar expressamente as três operações ('buy', 'sell' ou 'hold').
- [x] Refinar as chaves e textos de `criteria` para `buy`, `sell` e `hold` detalhando os gatilhos quantitativos e operacionais SPOT.
- [x] Testes unitários comprovando a estrutura de questões gerada pelo método `_predict_sync` e validando o mock de inferência do Laya Decision Engine com a nova instrução.

