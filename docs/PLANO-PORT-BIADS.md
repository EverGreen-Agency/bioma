# Plano de Port: BIAds → Bioma

Decisão de 2026-07-10 (Eduardo): port **completo** do BIAds (`Desktop/EG/BIAds`, "Portal de Performance Evergreen") para dentro do Bioma, na stack do Bioma. O BIAds deixa de evoluir como produto separado; sua essência (coleta Google + BI multi-tenant) vira o módulo de Dashboards/Relatórios do Bioma. Meta Ads e LinkedIn ficam para depois.

Este documento é a spec distribuível para quem executar o port (Codex/Juiz no backend, frente de UI no frontend). Fonte de verdade do que existe hoje: repo BIAds, `Docs/especificacao-dashboard-performance-evergreen.md` e `Docs/walkthrough.md` (fases 1–7 concluídas).

## O que o BIAds tem hoje

- **Coleta (Supabase Edge Function `run-sync`, Deno + pg_cron 2x/dia):**
  - Google Ads via GAQL REST → `ads_campaign_daily`, `ads_keyword_daily`, `ads_search_term_daily`, `ads_segment_daily`, `ads_conversion_daily`.
  - GA4 via `runReport` → aquisição, landing pages, eventos, dispositivos (séries diárias).
  - Search Console → `gsc_query_daily`, `gsc_page_daily` (por país e device).
  - GTM → snapshot JSONB do container live + auditoria de tags (GA4 config ausente, tags órfãs, excesso de Custom HTML).
  - OAuth2 service-account (assertion flow RS256 implementado à mão em Deno).
  - Logs por provider em `sync_runs`, sync parcial tolerante a falhas.
- **Autorização:** Supabase Auth + RLS multi-tenant (`user_can_access_client(client_id)`).
- **Frontend:** 7 páginas (Overview, Google Ads, Analytics/GA4, SEO, Tracking/GTM, Insights = timeline de otimizações manuais, Settings = sync manual), TanStack Query, Recharts, filtros de período persistidos na URL (`useFilters`), componentes `MetricCard`/`ChartCard`/`DataTable`/`TrendIndicator`.
- **Sem testes automatizados.** Deploy GitHub Pages (não portar).

## Mapa de tradução BIAds → Bioma

| BIAds (Supabase) | Bioma (FastAPI + Postgres + Redis) |
| --- | --- |
| Supabase Auth | Sessão cookie existente do Bioma (`eg_admin`/`client_user`) |
| RLS `user_can_access_client` | Autorização app-level no service layer, mesmo padrão do `client_hub` (client_user só vê o próprio cliente) |
| Edge Function Deno `run-sync` | Worker Python (`apps/worker/`) com `google-auth`; no MVP, `sync_runs` no Postgres funciona como fila durável com `FOR UPDATE SKIP LOCKED` |
| `pg_cron` 2x/dia | Comando incremental do worker acionado por job isolada no Railway; Redis/RQ só entra se a volumetria justificar |
| Tabelas `*_daily`, snapshots GTM | Migrations novas no Postgres do Bioma, mesmos nomes/colunas (aproveitar schema validado) + FK para `clients.id` do Bioma |
| `sync_runs` do BIAds | **Unificar** com o `sync_runs` existente do Bioma (acrescentar `provider`, `date_from`, `date_to`) |
| Service account JSON por cliente | Armazenamento cifrado (tabela de credenciais ou secret por ambiente); nunca em texto puro — LGPD |
| Páginas React + TanStack Query | Novas views no `apps/web` do Bioma, tema EG (tokens de `styles.css`); adotar TanStack Query nas telas de BI; `TrendChart` (recharts, cores `--chart-1/--chart-2` validadas) já existe |
| `MetricCard`/`ChartCard`/`DataTable` | Portar para `src/components/bi/` convertendo Tailwind → tokens CSS do Bioma |
| Filtros de período na URL (`useFilters`) | Portar como está (padrão bom) |
| GitHub Pages + Actions | Não portar; deploy segue o P4 do roadmap (Vercel/Railway) |
| Motor de insights automatizados | Não portar (o próprio BIAds removeu na fase 6) |

## Fases sugeridas

1. **F1 — Schema:** migrations das tabelas `*_daily` + snapshot GTM + extensão do `sync_runs`; mapeamento `clients` Bioma ↔ contas Google (customer id, property GA4, site GSC, container GTM) numa tabela `performance_connections`.
2. **F2 — Worker Google Ads:** worker + fila + job de sync Ads (GAQL) com logs e upsert idempotente por (client, data, chave).
3. **F3 — GA4 + GSC:** mais dois providers no mesmo orquestrador.
4. **F4 — GTM:** snapshot + auditoria de tags.
5. **F5 — Frontend:** páginas Performance (Overview, Ads, GA4, SEO, Tracking) dentro do Bioma consumindo endpoints novos da API (`/clients/{id}/performance/...`); estados vazios honestos enquanto não houver sync.
6. **F6 — Agendamento + Settings:** cron 2x/dia + botão de sync manual (padrão já existente no ClickUp bridge) + visão de última sincronização.

## Estado após integração de 2026-07-10

- F1 concluída: migration `0003_biads_performance.sql`, conexões por cliente e `sync_runs` unificado.
- F2 concluída em código: worker Google Ads com GAQL, autenticação via `google-auth`, upsert e logs.
- F3 concluída em código: providers GA4 e Search Console.
- F4 concluída em código: snapshot e auditoria GTM.
- F5 parcial: `TrendChart` foi criado, mas as páginas de Performance ainda não consomem os endpoints reais.
- F6 parcial: API enfileira sync e o worker oferece `--enqueue-all --drain`; cron e segredos ainda precisam ser configurados no staging.
- Validação real pendente: executar cada provider contra contas Google controladas pela EG e comparar amostras com as interfaces oficiais.

Critério de pronto por fase: migrations aplicam do zero, smoke test do provider com credencial real de 1 cliente, `tsc`/build no front, e nenhum número renderizado sem origem em tabela real (regra de honestidade do roadmap).

## Riscos e pontos de atenção

- **Credenciais:** service account precisa de acesso às contas dos clientes (MCC no Google Ads simplifica — já era premissa na reunião HM); escopos GA4/GSC/GTM concedidos por propriedade.
- **Volumetria/rate limits:** manter janela incremental de datas como no BIAds (sync por range), não full refresh.
- **IDs de cliente:** o BIAds tem `clients` próprio; no port, a fonte é `clients` do Bioma — migrar dados históricos só se valer a pena (senão, re-sincronizar 90 dias).
- **Sem testes herdados:** escrever ao menos smoke de worker por provider (mock HTTP) no padrão dos smoke tests atuais da API.
- **Meta/LinkedIn:** fora deste port; entrarão como novos providers no mesmo orquestrador (a estrutura por provider já prevê isso).
