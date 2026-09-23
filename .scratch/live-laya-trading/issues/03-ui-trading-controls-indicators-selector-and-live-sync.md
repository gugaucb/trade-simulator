# 03: Interface com Controles Start/Stop, Seletor de Indicadores e Sincronização Online

**What to build:**
Componentes visuais e interativos na aba Live Paper Trading que permitem ao usuário ligar/desligar a negociação automática, selecionar a criptomoeda (BTC, ETH, SOL, etc.), escolher os indicadores repassados ao Laya e visualizar em tempo real o sinal Laya, o balance e o log de trades sem necessidade de recarregar a página.

**Blocked by:** 02: Execução de Ordens em 1m com Atualização Online de Saldo e Logs Auditáveis

**Status:** ready-for-agent

- [ ] Botão de controle Start / Stop no painel de Laya Signal com indicador visual do estado (Verde / Negociando Ativamente com pulso vs Vermelho / Automação Pausada).
- [ ] Painel seletor de "Indicadores do Laya" com checkboxes para ativar/desativar: RSI, MACD, EMAs (20/50), Bollinger Bands, ATR e Volume Ratio.
- [ ] Atualização em tempo real do card **Laya Signal** (Ação BUY/HOLD/SELL, % de confiança, latência de inferência e setup quality) via WebSocket.
- [ ] Atualização online e contínua do **Balance** (Equity total, Cash disponível, Posição da cripto selecionada e PnL percentual/dólar).
- [ ] Inclusão imediata das negociações executadas no card **Recent trades** com indicação de lado (BUY verde / SELL vermelho), preço, volume e timestamp.
- [ ] Validação interativa completa no navegador Chrome.
