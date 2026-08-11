FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar NodeJS para suportar as CLIs de IA
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*
RUN npm install -g @openai/codex @anthropic-ai/claude-code

RUN groupadd --system bioma && useradd --system --gid bioma --create-home bioma

COPY --chown=bioma:bioma . .

USER bioma

CMD ["python", "-m", "bioma_worker.cli"]
