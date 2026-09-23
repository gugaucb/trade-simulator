# 01: Motor de Configuração de Ativo, Indicadores Customizados e Controle Start/Stop

**What to build:**
Mecanismo de controle no backend que permite definir o criptoativo em negociação no timeframe de 1m, selecionar dinamicamente quais indicadores quantitativos serão alimentados ao modelo Laya, e controlar o estado de ativação da negociação automática (Start/Stop).

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Suporte a estado configurável em memória e persistido: `trading_active` (booleano), `symbol` (ex: BTCUSDT, ETHUSDT) e `active_indicators` (conjunto de chaves permitidas: rsi, macd, ema, bb, atr, volume).
- [x] Função de enriquecimento dinâmico do `laya_state` que filtra o contexto de mercado apenas para os indicadores habilitados pelo usuário.
- [x] Endpoints REST `POST /api/trading/toggle` (para alternar start/stop) e `POST /api/trading/config` (para atualizar criptoativo e indicadores ativos).
- [x] Endpoint `GET /api/trading/status` retornando o estado atual da automação e indicadores selecionados.
- [x] Notificação de alteração de configuração via WebSocket para todos os clientes conectados.
- [x] Testes unitários para montagem dinâmica de estado do Laya e validação dos endpoints.
