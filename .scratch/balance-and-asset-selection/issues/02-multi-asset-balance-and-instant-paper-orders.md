# 02: Carteira Multi-Ativos com Atualização Dinâmica do Balance e Ordens Rápidas de Teste

**What to build:**
Fazer com que a seção de Balance (Paper Equity, Cash, Posição e PnL) reflita imediatamente a oscilação do mercado e os saldos reais por criptomoeda, com indicador visual de sincronização online e botões rápidos de compra/venda a mercado em paper trading para permitir teste imediato da movimentação do saldo sem aguardar fechamento de candle de 1 minuto.

**Blocked by:** 01: Seletor Visual Proeminente de Criptomoeda e Troca de Ativo

**Status:** completed

- [x] Evoluir o modelo de `Portfolio` para suportar posições por ativo (`holdings` para BTC, ETH, SOL, BNB, XRP, ADA) com registro do preço médio de entrada e PnL não-realizado por moeda.
- [x] Atualizar dinamicamente o card de Balance na chegada de cada tick do WebSocket da Binance com indicação de status online / pulso visual.
- [x] Adicionar botões de ação rápida de Paper Trading no painel ("Comprar a Mercado" / "Vender a Mercado") consumindo a API `/api/portfolio/order` para testes manuais imediatos.
- [x] Endpoint `POST /api/portfolio/order` permitindo ordens simuladas de BUY e SELL com atualização imediata de saldo, posição e histórico de trades.
- [x] Testes unitários para o `Portfolio` multi-ativos e validação completa no navegador Chrome.
