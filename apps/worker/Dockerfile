FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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

COPY --chown=bioma:bioma . .

USER bioma

CMD ["python", "-m", "bioma_worker.cli"]
