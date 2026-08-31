# Contexto de build: bioma/ (não bioma/apps/api/). Precisa alcançar
# apps/worker/bioma_worker além de apps/api — ver o comentário grande abaixo.
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY apps/api/requirements.txt ./requirements.txt
COPY apps/worker/requirements.txt ./worker-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r worker-requirements.txt

# Claude Code requer Node.js 22+. A imagem Debian ainda entrega Node 20, então
# usamos o repositório oficial do NodeSource antes de instalar as CLIs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl util-linux \
    && curl -fsSL https://deb.nodesource.com/setup_22.x -o /tmp/nodesource_setup.sh \
    && bash /tmp/nodesource_setup.sh \
    && apt-get install -y --no-install-recommends nodejs \
    && rm /tmp/nodesource_setup.sh \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @openai/codex @anthropic-ai/claude-code
RUN curl -fsSL https://antigravity.google/cli/install.sh -o /tmp/install-antigravity.sh \
    && bash /tmp/install-antigravity.sh --dir /usr/local/bin \
    && rm /tmp/install-antigravity.sh

RUN groupadd --system bioma && useradd --system --gid bioma --create-home bioma

COPY --chown=bioma:bioma apps/api/ ./

# `bioma_api/worker_bridge.py` importa `bioma_worker` em processo (copiloto,
# Radar Local, geração de conteúdo IA, pesquisa de mercado, estudo de
# plataformas) — não é uma chamada de rede para o serviço `bioma-worker` do
# Railway, que é um processo separado consumindo a fila `sync_runs` para os
# syncs de Ads.
#
# Até este Dockerfile, o contexto de build era só `apps/api/`, então
# `bioma_worker` nunca existia no container da API. Em produção,
# `_ensure_worker_in_path()` sempre retornava falso e todo recurso que depende
# do worker respondia 502 "worker não encontrado" — nunca a prévia local, que só
# existe DENTRO de `bioma_worker.copilot.plan()`, que nunca era alcançado.
#
# Copiar só o pacote `bioma_worker` (não `apps/worker/` inteiro: scripts, testes
# e o `.venv` do worker não servem para nada aqui) para `./worker/bioma_worker`
# casa com um dos candidatos que `_ensure_worker_in_path()` já procura
# (`ancestor / "worker"`), então nenhum código Python precisou mudar.
COPY --chown=bioma:bioma apps/worker/bioma_worker ./worker/bioma_worker

USER bioma

EXPOSE 8000

CMD ["python", "scripts/start.py"]
