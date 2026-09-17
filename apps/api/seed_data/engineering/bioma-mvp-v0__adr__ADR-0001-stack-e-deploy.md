# ADR-0001: Stack e Deploy do Bioma MVP v0

- **Status:** aprovado para MVP v0
- **Data:** 2026-07-09
- **Contexto:** reset enxuto do Bioma; `bioma-legacy/` preservado como referência, mas sem herdar stack/arquitetura.

## Decisão

Usar uma arquitetura com frontend e backend separados:

- `apps/web`: React + Vite + TypeScript, hospedado na Vercel.
- `apps/api`: FastAPI + Python, hospedado na Railway.
- `apps/worker`: worker Python separado na Railway apenas quando houver necessidade real.
- `packages/contracts`: contratos OpenAPI/Pydantic compartilhados com o front.
- `infra/`: Docker Compose local, scripts de ambiente e documentação.

Ambientes:

- Local: Docker para Postgres e Redis quando necessário.
- Staging: Vercel + Railway com banco e secrets separados.
- Produção: Vercel + Railway com banco, secrets, backups e healthcheck separados.

## Motivos

- Backend separado reduz acoplamento com o servidor do frontend.
- Python/FastAPI favorece integrações, IA, workers e automações.
- Vercel resolve o frontend com baixo atrito.
- Railway reduz a carga operacional no MVP para API, Postgres, Redis e worker.
- Fly fica reservado como alternativa posterior para controle fino de runtime, região, rede ou custo.

## Alternativas Consideradas

- **Next.js full-stack + Supabase:** acelerou o legado, mas não será default do reset por desconforto com serverless/BaaS como núcleo.
- **Fly primeiro:** tecnicamente forte, mas adiciona mais responsabilidade de infraestrutura no momento em que a urgência é entregar.
- **Backend dentro da Vercel:** simples no começo, fraco para jobs, webhooks, segredos, integrações demoradas e observabilidade operacional.

## Consequências

- O scaffold deve nascer em `bioma/` com `apps/web`, `apps/api`, `apps/worker`, `packages/contracts` e `infra`.
- O deploy inicial deve provar staging e produção cedo.
- Workers só entram quando ClickUp sync, webhooks, IA ou relatórios exigirem.
- `bioma-legacy/` não deve subir containers ou orientar a nova stack.
