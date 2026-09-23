# 01: Gerar Nova Chave SSH Exclusiva para o GitHub e Configurar Cliente SSH

**What to build:**
Gerar um par de chaves SSH novo e dedicado (ed25519) sem interferir nas chaves SSH já existentes utilizadas em outros projetos, configurar a conexão no arquivo de configuração SSH do usuário (`~/.ssh/config`) mapeando para o host do GitHub, exibir a chave pública formatada na tela para o usuário adicionar em sua conta no GitHub e validar a conectividade.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Verificar chaves SSH existentes em `~/.ssh` para garantir preservação de chaves existentes.
- [x] Gerar novo par de chaves ed25519 dedicado (ex: `~/.ssh/id_ed25519_trade_simulator`) com comentário identificando a conta `gugaucb`.
- [x] Configurar entrada no arquivo `~/.ssh/config` ou `core.sshCommand` no repositório para usar essa identidade para `github.com`.
- [x] Exibir para o usuário a chave pública completa para cadastro no GitHub (`https://github.com/settings/ssh/new`).
- [x] Testar autenticação SSH com `ssh -T git@github.com`.
