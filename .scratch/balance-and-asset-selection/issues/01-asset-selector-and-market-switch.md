# 01: Seletor Visual Proeminente de Criptomoeda e Troca de Ativo

**What to build:**
Permitir que o usuário identifique com clareza qual criptomoeda está selecionada para negociação pelo Laya e troque de ativo de forma imediata através de chips/cards visuais (BTC, ETH, SOL, BNB, XRP, ADA) com feedback de cotação e status, além de corrigir os eventos `onchange` nos seletores do terminal.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Painel seletor com chips visuais e destacados para cada criptomoeda suportada (BTC, ETH, SOL, BNB, XRP, ADA) exibindo ícone, nome e indicação clara de ativo ativo para o Laya.
- [x] Adicionar evento `onchange="configure()"` nos elementos `<select id="symbolSelect">` e `<select id="intervalSelect">`.
- [x] Ao alternar de criptomoeda (seja por clique no chip ou no dropdown), acionar a comutação de mercado sem recarregar a página, atualizando título, cotação, gráfico e ticker no backend e no frontend.
- [x] Testes automatizados cobrindo a troca de ativo via API e validação no navegador.
