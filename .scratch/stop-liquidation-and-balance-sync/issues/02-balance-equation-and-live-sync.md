# 02: Equação do Balance em Tempo Real, Exibição da Posição do Ativo Selecionado e Sincronização UI

**What to build:**
Assegurar que a interface do usuário reflita explicitamente a equação fundamental da custódia: `Paper Equity (Total) = Cash disponível + Posição em ($)`, contextualizada para o ativo selecionado (BTC, ETH, SOL, etc.), e garantir que a posição, o cash e o paper equity sejam atualizados em tempo real conforme as negociações do Laya são executadas e os preços oscilam.

**Blocked by:** 01: Liquidação Total para Cash no Stop e Dimensionamento Rígido pelo Saldo

**Status:** completed

- [x] Incluir no snapshot da carteira (`Portfolio.snapshot()`) a métrica `position_usd` (valor de mercado em dólares da posição do ativo selecionado).
- [x] Atualizar o card de **Carteira Paper** no frontend:
  - Exibir no bloco de Posição a quantidade e o valor correspondente em dólares: `0.05000 BTC (~$3,450.00)`.
  - Exibir a soma visual direta: `Cash + Posição ($) = Paper Equity (Total)`.
  - Atualizar o nome da moeda e valores imediatamente ao alternar o ativo selecionado (`selectCrypto`).
- [x] Conectar os eventos WebSocket (`decision`, `candle`, `trade`, `portfolio`, `trading_status`) para re-renderizar imediatamente o card de Balance sempre que o Laya executar uma ordem ou o stop liquidar posições.
- [x] Validação interativa no navegador Chrome com o subagente comprovando a liquidação para cash no Stop, a atualização ao vivo das negociações e a sincronia matemática `Equity = Cash + Posição ($)`.

