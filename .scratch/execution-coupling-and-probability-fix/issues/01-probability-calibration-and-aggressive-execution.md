# 01: Calibração de Probabilidade do Laya e Execução Real no Balance

**What to build:**
Corrigir a extração de confiança no `LayaDecisionEngine` para utilizar a probabilidade real da classe escolhida (`probabilities[choice]`) em vez da métrica descalibrada, adotar o limiar agressivo de $\ge 40\%$ para disparo de ordens SPOT de Buy e Sell, gravar a flag explícita `executed: bool` em cada decisão e garantir a execução da ordem e atualização do balance.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Em `app/laya_engine.py`, extrair a probabilidade de `probabilities.get(choice)` como confiança primária da decisão tipada, com fallback para `action.get('confidence')`.
- [x] Em `app/main.py`, atualizar o limiar de execução para $\ge 0.40$ (modo agressivo).
- [x] No ciclo `process_closed_candle()`, quando `action == "buy"` com confiança $\ge 0.40$, cash disponível e sem posição aberta, executar a compra, debitando cash e creditando a posição em BTC.
- [x] Incluir no registro de decisão (`record`) e no broadcast WebSocket a flag `"executed": bool(trade is not None)` e `"trade": trade`.
- [x] Testes unitários comprovando que probabilidade $\ge 40\%$ dispara a compra e atualiza cash e quantidade, enquanto probabilidade $< 40\%$ não executa e marca `executed: False`.

