# 01: Liquidação Total para Cash no Stop e Dimensionamento Rígido pelo Saldo

**What to build:**
Implementar o fechamento compulsório de todas as posições compradas/abertas quando o Stop for acionado, retornando 100% dos recursos para cash (equity == cash e posições zeradas), emitindo registros de trade para auditoria, e garantindo que o Laya utilize estritamente o limite de saldo em dinheiro presente no balance ao executar novas compras.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Método `liquidate_all()` na classe `Portfolio` que percorre todas as moedas com quantidade > 0 e realiza a venda total ao `last_price` (ou preço atual de mercado), creditando no `cash` e zerando as custódias.
- [x] No endpoint `POST /api/trading/toggle`, quando `state["trading_active"]` for alterado para `False` (stop/pausa), invocar a liquidação compulsória de todas as posições para cash.
- [x] Gravar registros de liquidação de trade no banco SQLite e transmitir evento WebSocket `portfolio` e `trade` para atualização imediata dos clientes.
- [x] No ciclo de trading do Laya (`process_closed_candle()`), garantir que o dimensionamento da ordem respeite o saldo em dinheiro disponível (`cash`) sem ultrapassar o balance disponível.
- [x] Testes unitários comprovando que:
  - Ao chamar `liquidate_all()`, todas as posições tornam-se 0 e `cash == equity`.
  - Ao desativar o trading via API, as posições ativas são liquidadas para cash.
  - Tentativa de compra sem cash disponível é rejeitada sem gerar posição ou saldo negativo.

