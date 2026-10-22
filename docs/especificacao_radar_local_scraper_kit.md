# Especificação Técnica: Radar Local & Scraper Kit de Prospecção B2B

**Data:** 22 de Outubro de 2026  
**Status:** Implementado (Pronto para Produção)  
**Branch:** `feature/google-maps-scraper-local-radar`  
**Autores:** Engenharia de Software & Arquitetura Bioma  

---

## 1. Contexto e Motivação de Domínio

### 1.1 Limitações da Google Places API e o Custo de Prospecção
A prospecção outbound de pequenas e médias empresas (PMEs) no ecossistema local tradicionalmente dependia da API oficial do Google Places (New Text Search). Embora estruturada, essa API possui custos por requisição que escalam rapidamente em campanhas de alto volume e não fornece dados vitais de contato corporativo (e-mails departamentais como `contato@` e perfis de redes sociais como Instagram, Facebook e LinkedIn).

### 1.2 O Framework do Google Maps Scraper Kit
Inspirado na arquitetura do `google-maps-scraper-kit` (e no motor open-source de extração de leads locais), integramos nativamente ao Bioma um **Web Crawler Autônomo e Resiliente de Enriquecimento de Contatos**, permitindo:
1. Extração rápida via Google Places ou ingestão sem custos via extensão de scrape (Instant Data Scraper).
2. Varredura sob demanda nos websites dos estabelecimentos minerados para garimpar e-mails corporativos e redes sociais.
3. Tratamento estrito anti-lixo para eliminar falsos positivos (como imagens `@2x.png` e domínios descartáveis de provedores de templates como `wixpress.com`, `example.com`, `sentry.io`).
4. Apresentação em formato **Tabela de Leads (Scraper Kit View)** com seleção em lote, filtros rápidos e cópia ágil para o time comercial.

---

## 2. Arquitetura de Software e Fluxo de Dados

A solução respeita integralmente a **Clean Architecture** e o isolamento de domínios do Bioma:

```
[ Frontend: React 19 / Vite / TanStack Query ]
   │
   ├─► Alternador: Tabela de Leads (Scraper Kit) vs Fichas Detalhadas
   ├─► Ações em Lote: "⚡ Enriquecer Selecionados"
   └─► Filtros em Memória: Com e-mail, Com social, Sem site, Aprovados
               │
               ▼ HTTP (REST / JSON)
[ Router: FastAPI (/backoffice/local-radar) ]
   │
   ├─► POST /prospects/{id}/enrich
   └─► POST /scans/{id}/enrich-batch
               │
               ▼
[ Service: local_radar (Coordenação e Auditoria) ]
               │
               ├─► Worker Bridge: enrich_prospect_website_safe
               │       │
               │       ▼
               │   [ bioma_worker.local_radar.enrich_prospect_website ]
               │       - HTTPX assíncrono/resiliente (timeout de 7s)
               │       - Tolerância a SSL inválido de PMEs
               │       - Regex estrito de e-mails corporativos
               │       - Parser de redes sociais (Instagram, LinkedIn, WhatsApp)
               │
               ▼ SQL Parametrizado (psycopg)
[ Repository: update_prospect_enrichment ]
               │
               ▼
[ Banco de Dados: PostgreSQL (Migration 0116) ]
   - emails JSONB DEFAULT '[]'::jsonb
   - social_links JSONB DEFAULT '{}'::jsonb
   - crawler_status VARCHAR(32) DEFAULT 'pending'
   - enriched_at TIMESTAMPTZ
```

---

## 3. Resiliência e Regras de Higienização de Dados

### 3.1 Filtro de Extensões Estáticas
O regex de e-mails do crawler descarta matches terminados em extensões de mídia ou código:
`.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`, `.ico`, `.css`, `.js`, `.woff`, `.ttf`, `.pdf`.

### 3.2 Filtro de Domínios de Templates
Descarta e-mails originários de bibliotecas de terceiros ou geradores estáticos:
`wixpress.com`, `example.com`, `domain.com`, `sentry.io`, `cloudflare.com`, `wordpress.org`, etc.

### 3.3 Priorização de Relevância
Os e-mails encontrados são ordenados dando prioridade aos que contêm o domínio raiz do próprio estabelecimento e prefixos comerciais (`contato@`, `comercial@`, `atendimento@`, `vendas@`).

---

## 4. Testes e Validação de Qualidade

1. **Testes Unitários:**
   - `test_enrich_prospect_website_empty_or_none`: Garante comportamento idempotente para sites nulos ou vazios.
   - `test_enrich_prospect_website_extracts_clean_emails_and_socials`: Valida a extração de e-mails legítimos, exclusão de extensões `@2x.png` e extração de Instagram, LinkedIn e WhatsApp.
   - `test_enrich_prospect_website_timeout_handling`: Valida resiliência graciosa contra falhas de rede e timeout sem interromper a execução.
   - **Resultado:** `3 passed in 0.43s`.
2. **Tipagem e Build:**
   - Frontend: `npx tsc -b && vite build` $\to$ 0 erros.
   - Backend: `python -m compileall bioma_api` $\to$ 0 erros.
