# 03: Configurar Workflow do GitHub Actions para Build e Push da Imagem no DockerHub

**What to build:**
Criar a automação de CI/CD via GitHub Actions (`.github/workflows/docker-publish.yml`) para compilar a imagem Docker do Crypto Laya Trader (`trade-simulator`) e publicá-la automaticamente no DockerHub a cada push na branch `main` e em novas tags, com cache eficiente de camadas Docker e configuração de segredos (`DOCKERHUB_USERNAME` e `DOCKERHUB_TOKEN`).

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Verificar e refinar `Dockerfile` e criar `.dockerignore` para evitar envio de `.venv`, `__pycache__`, caches temporários e bancos SQLite locais para a imagem.
- [x] Criar o arquivo de workflow `.github/workflows/docker-publish.yml` utilizando ações oficiais do Docker (`docker/setup-buildx-action`, `docker/login-action`, `docker/build-push-action`).
- [x] Configurar tagging automática (ex: `latest` na branch `main` e tags de versão semântica `v*.*.*`).
- [x] Validar sintaxe do workflow e documentar a configuração necessária dos segredos no repositório GitHub.
