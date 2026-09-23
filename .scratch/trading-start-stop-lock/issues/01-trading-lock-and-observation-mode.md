# 01: Trava Estrita de Negociação Automática e Isolamento do Modo Observação

**What to build:**
Garantir que `state["trading_active"]` seja respeitado rigorosamente. Quando o botão estiver em Stop/Pausado, o Laya não deve emitir ordens de compra/venda, não deve gerar setas de execução no gráfico e o card de sinal deve exibir claramente o estado `PAUSADO` / `OBSERVAÇÃO`, impedindo qualquer impressão de que o sistema está negociando por conta própria.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] O estado `state["trading_active"]` deve iniciar estritamente como `False` e só mudar mediante ação explícita do usuário via API.
- [x] No ciclo `process_closed_candle()`, se `trading_active` for `False`, o motor não executa ordens (trade = None) e a decisão é marcada com `is_live_trading: False` e rotulada como observação.
- [x] No frontend, quando a negociação estiver pausada (`trading_active == False`), o card do Laya Signal deve exibir o badge `PAUSADO` (ou `OBSERVAÇÃO`), a barra lateral não deve plotar setas de compra/venda no gráfico como se fossem ordens reais.
- [x] Apenas quando `trading_active == True`, os sinais `BUY` e `SELL` devem ser tratados como operacionais ativos, disparando ordens e plotando markers de execução.
- [x] Testes unitários comprovando que nenhuma ordem ou execução ocorre com `trading_active == False`.
