# 01: Enriquecimento Semântico do Contexto do Laya e Padronização

**What to build:**
Enriquecer a montagem do estado contextual (`state`) repassado ao Laya Engine para incluir explicitamente o preço atual da cotação no nível raiz (`current_price`), o valor monetário da posição (`position_usd`), o patrimônio total (`equity`), a lista declarativa de indicadores ativos (`active_indicators`), e padronizar as regras operacionais em `decision_policy` tanto no Live Trading quanto no Backtest.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Incluir `"current_price": ctx["close"]` no nível raiz do contexto retornado por `build_filtered_laya_state`.
- [x] Incluir `"active_indicators": list(active_indicators)` no contexto para declarar ao modelo quais variáveis estão ativas.
- [x] Enriquecer `"paper_position"` com `"position_usd"` e `"equity"`.
- [x] Refinar `"decision_policy"` para especificar que ordens SPOT só compram se houver cash livre e só vendem se houver posição custodiada para liquidação em cash.
- [x] Padronizar a montagem de estado no Backtest ([`app/main.py`](file:///c:/Users/tr300869/Documents/Pessoal/Projetos/crypto_laya_trader/app/main.py)) para utilizar `build_filtered_laya_state`.
- [x] Testes unitários comprovando que indicadores desmarcados não entram em `market_state`, que `current_price` está presente e que a estrutura é consistente.

