# 02: Sincronização Universal do Estado Start/Stop e Validação no Navegador

**What to build:**
Assegurar que o estado Start/Stop (`trading_active`) seja propagado em todas as mensagens do WebSocket (`hello`, `config`, `trading_status`, `candle`, `decision`) para que qualquer recarregamento de página, comutação de criptomoeda ou reconexão mantenha o botão perfeitamente sincronizado, com proteção contra duplo-clique.

**Blocked by:** 01: Trava Estrita de Negociação Automática e Isolamento do Modo Observação

**Status:** completed

- [x] Incluir `trading_active` nas mensagens `hello`, `config`, `candle` e `decision` do WebSocket.
- [x] Atualizar o frontend para que qualquer evento `config`, `hello` ou `trading_status` atualize o botão Start/Stop para o estado correto.
- [x] Desabilitar temporariamente o botão Start/Stop durante a requisição `POST /api/trading/toggle` para evitar duplo-clique acidental.
- [x] Exibir badge visual explícito no cabeçalho do terminal indicando se a automação está `🟢 Negociação Ativa` ou `⏸️ Automação Pausada`.
- [x] Validação interativa completa no navegador Chrome confirmando que o sistema permanece inerte quando pausado e só opera quando iniciado.
