# Especificação Técnica: Auditor de SEO Técnico e GEO (Generative Engine Optimization)

**Data:** 22 de Outubro de 2026  
**Status:** Implementado (Pronto para Produção)  
**Branch:** `feature/seo-geo-claude-integration`  
**Autores:** Engenharia de Software & Arquitetura Bioma  

---

## 1. Fundamentação Teórica e Referencial Científico

### 1.1 A Transição de SEO (Search Engine Optimization) para GEO (Generative Engine Optimization)
O paradigma clássico de SEO (PageRank, densidade de palavras-chave e SERP de 10 links azuis) está sendo rapidamente complementado e superado pela **Busca Generativa** (Google AI Overviews, Perplexity, ChatGPT Search e Claude).

De acordo com o estudo pioneiro de Princeton University e Georgia Tech (*"GEO: Generative Engine Optimization"*, 2024), os motores de resposta sintetizada não ranqueiam apenas links; eles **decidem quais marcas citar como fontes de autoridade** com base em:
1. **Densidade Factual e Estatística:** Frases com números, fontes e dados verificáveis têm 30% a 40% mais probabilidade de inclusão em respostas sintetizadas.
2. **Semântica e Dados Estruturados (Schema.org / JSON-LD):** A identificação inequívoca de entidades (`Organization`, `LocalBusiness`, `FAQPage`, `Product`) reduz a taxa de alucinação dos LLMs a quase zero.
3. **Padrão da Indústria `llms.txt`:** Especificação aberta que declara aos robôs de IA quais URLs e resumos devem ser priorizados como fonte primária da verdade da empresa.

---

## 2. Arquitetura de Software Implementada

Seguindo os padrões rígidos de Clean Architecture do Bioma:

```
[ Frontend: React 19 / TypeScript / TanStack Query ]
   │
   ├─► SeoGeoStudio: Gauges semafóricos de SEO e GEO (0-100)
   ├─► Checklist detalhada (Passed, Warning, Failed)
   ├─► Gerador llms.txt com 1 clique (Copy & Download)
   ├─► Gerador de Schema.org / JSON-LD
   └─► Linha do tempo de histórico persistido
               │
               ▼ HTTP (REST / JSON)
[ Router: FastAPI (/seo-geo/preview, /workspaces/{id}/seo-geo/audits) ]
               │
               ▼
[ Service: seo_geo (Motor de Auditoria & Heurísticas) ]
               │
               ├─► HTTPX com User-Agent Desktop (timeout de 8s)
               ├─► Tolerância a certificados SSL expirados
               ├─► Detecção de WAF / Cloudflare com bypass gracioso
               ├─► Teste de existência de /llms.txt no host
               ├─► Parser On-Page (Title, Meta, H1, Canonical, Alt, Open Graph)
               ├─► Gerador sintético de llms.txt e Schema.org
               │
               ▼ SQL Parametrizado (psycopg)
[ Repository: workspace_seo_geo_audits (PostgreSQL Migration 0117) ]
               │
               ▼
[ Banco de Dados: Tabela workspace_seo_geo_audits ]
```

---

## 3. Critérios de Pontuação e Regras de Negócio

### 3.1 Eixo 1: Score SEO Técnico (0 a 100)
- **Title Tag (25 pts):** Presença (15 pts) + Tamanho ideal entre 30 e 65 caracteres (+10 pts).
- **Meta Description (20 pts):** Presença (10 pts) + Tamanho ideal entre 110 e 165 caracteres (+10 pts).
- **Hierarquia H1 (20 pts):** Exatamente 1 tag H1 semântica na página (20 pts); múltiplos H1 (8 pts); zero H1 (0 pts).
- **Tag Canonical (15 pts):** Presença de `<link rel="canonical">` válida.
- **Open Graph (10 pts):** Presença de `og:title` e `og:image` para compartilhamento.
- **Acessibilidade de Imagens (10 pts):** Proporção de imagens com atributo `alt` preenchido.

### 3.2 Eixo 2: Score GEO & IA (0 a 100)
- **Schemas Estruturados Schema.org (35 pts):** Presença de blocos `<script type="application/ld+json">` válidos.
- **Arquivo `llms.txt` (30 pts):** Presença de arquivo ativo em `https://dominio.com/llms.txt`.
- **Sinais de Confiabilidade E-E-A-T (20 pts):** Detecção de páginas institucionais de autoridade (Sobre/Equipe, Contato, Política de Privacidade e CNPJ).
- **Perguntas Frequentes & Respostas Diretas (15 pts):** Seções estruturadas de FAQ formatadas para citações em snippets.

---

## 4. Testes e Validação de Qualidade

1. **Testes Unitários:** Implementados em `apps/api/tests/test_seo_geo.py`:
   - `test_run_live_audit_complete_site`: Valida site com alta conformidade (Score >= 90, detecção de Schema e geração de llms.txt).
   - `test_run_live_audit_detects_gaps_on_poor_site`: Valida detecção de lacunas críticas (Score < 50, imagens sem alt, ausência de H1 e Schemas).
   - **Resultado:** `2 passed in 0.67s`.
2. **Build e Tipagem:**
   - Frontend: `tsc -b && vite build` $\to$ 0 erros.
   - Backend: `python -m compileall bioma_api` $\to$ 0 erros.
