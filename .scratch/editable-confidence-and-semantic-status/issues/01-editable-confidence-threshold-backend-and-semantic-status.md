# 01: Limiar de Confiança Configurável no Backend e Classificação Semântica de Decisão

**What to build:**
Permitir que o limiar mínimo de confiança para execução de ordens seja editado e configurado dinamicamente via API (`POST /api/trading/config` com `confidence_threshold`), armazenado no estado (`state["confidence_threshold"]`, default 0.40) e transmitido nos endpoints e WebSockets. Além disso, classificar semanticamente cada decisão no backend com `execution_status` ("executed", "already_in_position", "no_position_to_sell", "low_confidence", "insufficient_cash", "hold", "paused") e `filter_reason`, eliminando mensagens confusas.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Incluir `confidence_threshold` em `state` (default `0.40`), exposto em `/api/trading/status`, `/api/bootstrap` e eventos WebSocket.
- [x] Atualizar `POST /api/trading/config` para aceitar `confidence_threshold` (número entre 0.10 e 0.95), validando e aplicando imediatamente.
- [x] No ciclo `process_closed_candle()`, utilizar `state["confidence_threshold"]` como limiar de disparo.
- [x] No registro de cada decisão, adicionar:
  - `"execution_status"`: valor semântico exato.
  - `"threshold"`: valor ativo no momento.
  - `"filter_reason"`: texto em português explicando o motivo da não-execução.
- [x] Testes unitários cobrindo configuração dinâmica de confiança, execução com novo limiar e classificação semântica de `already_in_position` e `low_confidence`.
