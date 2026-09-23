# 02: Campo de Edição de Confiança na Interface e Feed Semântico Preciso

**What to build:**
Adicionar na interface do usuário (no card do Laya Signal) um controle visual intuitivo (input numérico e/ou slider com display percentual) para permitir ao usuário ajustar em tempo real o limiar mínimo de confiança do Laya (ex: 35%, 40%, 50%), persistindo na API, atualizando os chips de legenda dinamicamente e eliminando completamente textos estáticos contraditórios como '45% < 40%'.

**Blocked by:** 01: Limiar de Confiança Configurável no Backend e Classificação Semântica de Decisão

**Status:** completed

- [x] Adicionar controle de edição do limiar de confiança no card **Laya Signal** com input percentual (`id="inputConfidenceThreshold"`), botão de salvar/ajuste automático `onchange="updateConfidenceThreshold(this.value)"`.
- [x] Atualizar dinamicamente os chips de legenda com o percentual configurado pelo usuário (`BUY ≥ [X]% conf` e `SELL ≥ [X]% conf`).
- [x] No `addDecision(d)` do frontend:
  - Se `d.execution_status === 'executed'`: `EXECUÇÃO: BUY · 45%` (verde + seta no gráfico).
  - Se `d.execution_status === 'already_in_position'`: `MANTER LONG: BUY · 45% (Já em posição)` (azul com ícone de escudo, sem seta).
  - Se `d.execution_status === 'no_position_to_sell'`: `MANTER CASH: SELL · 45% (Sem custódia)` (azul/slate, sem seta).
  - Se `d.execution_status === 'low_confidence'`: `SINAL FRACO: <ACTION> · <CONF>% (< <THRESH>%)` (apenas quando conf for estritamente menor que o threshold).
  - Se `d.execution_status === 'insufficient_cash'`: `SEM SALDO: BUY · <CONF>% (Cash insuficiente)`.
- [x] Sincronizar o valor do campo de confiança no carregamento inicial (`bootstrap`) e em mensagens WebSocket `config` / `trading_config`.
- [x] Validação interativa no navegador Chrome com o subagente.
