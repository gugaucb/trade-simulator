# 02: Execução de Ordens em 1m com Atualização Online de Saldo e Logs Auditáveis

**What to build:**
Ciclo de execução de ordens de paper trading disparado a cada candle fechado de 1 minuto pelo Laya (quando `trading_active == True`), com cálculo contínuo de PnL/balance em tempo real e emissão de eventos auditáveis de negociação.

**Blocked by:** 01: Motor de Configuração de Ativo, Indicadores Customizados e Controle Start/Stop

**Status:** completed

- [x] Avaliação do sinal Laya a cada fechamento de candle de 1m utilizando os dados públicos e gratuitos da Binance.
- [x] Execução de ordens de compra e venda simuladas com conferência de saldo disponível e tamanho de posição.
- [x] Atualização e emissão em tempo real via WebSocket do portfólio completo: `equity`, `cash`, `quantity` (com símbolo da moeda selecionada), `avg_entry`, `unrealized_pnl` e `realized_pnl`.
- [x] Persistência de cada trade na tabela `trades` do SQLite e gravação da decisão analítica na tabela `decisions`.
- [x] Emissão do evento de trade e decisão no WebSocket para inserção instantânea no feed de negociações.
- [x] Testes de integração cobrindo a execução de ordens, marcação a mercado do balance e gravação no banco.
