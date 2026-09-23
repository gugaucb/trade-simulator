# 02: Desacoplamento Visual: Execução Real vs. Sinal Filtrado por Ruído

**What to build:**
Assegurar que o frontend reflita estritamente a verdade das execuções financeiras, reservando o rótulo "EXECUÇÃO: BUY/SELL" e as setas no gráfico de candles exclusivamente para ordens efetivamente executadas (`d.executed == true`), enquanto sinais com confiança abaixo do limiar agressivo (< 40%) são rotulados como filtrados/ruído sem setas de execução.

**Blocked by:** 01: Calibração de Probabilidade do Laya e Execução Real no Balance

**Status:** completed

- [x] Em `app/templates/index.html`, na função `addDecision(d)`:
  - Se `d.executed == true`: aplicar `EXECUÇÃO: BUY` ou `EXECUÇÃO: SELL` com ícone de atividade, cor viva e chamar `applyMarker(d)`.
  - Se `!d.executed`:
    - Se `d.is_live_trading` e `d.action` for `buy` ou `sell`: rotular como `SINAL FILTRADO: <ACTION> (< 40%)` em cor neutra/âmbar com ícone de filtro, **sem chamar `applyMarker`**.
    - Se `d.action` for `hold`: rotular como `DECISÃO: HOLD` em cinza neutro.
- [x] No card **Laya Signal**, atualizar os chips de legenda para `BUY ≥ 40% conf`, `HOLD neutro / ruído`, `SELL ≥ 40% conf`.
- [x] No card **Laya Signal**, exibir `HOLD (Ruído)` se a ação for `buy`/`sell` mas com confiança insuficiente para execução.
- [x] Garantir que quando `d.trade` vier na mensagem WebSocket `decision`, a função `setPortfolio` e `addTrade` sejam chamadas de imediato, atualizando os cartões de Cash, Posição e Equity sem delay.
- [x] Validação interativa no navegador Chrome com o subagente.

