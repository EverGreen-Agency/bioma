---
name: claude-seo-geo
description: "Framework avançado de auditoria de SEO Técnico, GEO (Generative Engine Optimization), AEO, validação de Schema.org/JSON-LD e geração de llms.txt para motores de IA."
risk: low
source: claude-seo
date_added: "2026-10-22"
---

# Claude SEO & GEO (Generative Engine Optimization)

> Da indexação tradicional por palavras-chave à recomendação e citação direta por motores generativos de IA (Perplexity, ChatGPT, Claude e Google AI Overviews).

---

## 1. Os Dois Eixos da Otimização Moderna

### Eixo 1: SEO Técnico On-Page (Busca Clássica)
1. **Title Tag:** Deve conter a entidade ou palavra-chave principal, idealmente entre 30 e 60 caracteres.
2. **Meta Description:** Resumo claro e com call-to-action de 120 a 160 caracteres.
3. **Hierarquia Semântica:** Apenas um `<h1>` por página refletindo o tema central; `<h2>` e `<h3>` estruturando os tópicos.
4. **Canonical & Indexação:** Garantir `<link rel="canonical">` absoluto para evitar canibalização de URLs.
5. **Acessibilidade:** Todas as tags `<img>` com atributo `alt` descritivo.

---

### Eixo 2: GEO & AEO (Motores Generativos de IA)
1. **Padrão `llms.txt`:**
   - O padrão da indústria (equivalente ao `robots.txt` para IA) que declara aos robôs do ChatGPT, Perplexity e Claude o escopo da empresa, links oficiais e diretrizes de autoridade.
   - Deve residir na raiz do domínio: `https://dominio.com/llms.txt`.
2. **Dados Estruturados Schema.org / JSON-LD:**
   - Injeção obrigatória de schemas tipados: `Organization`, `LocalBusiness`, `FAQPage`, `Article`, `Service`.
   - Permite que o motor de busca extraia entidades em grafos de conhecimento sem alucinações.
3. **E-E-A-T & Fatos Declarativos:**
   - Respostas diretas nas primeiras 3 linhas de cada seção (*Answer First Pattern*).
   - Páginas de transparência verificadas: Quem Somos/Autoria, Política de Privacidade e Dados de Registro (CNPJ/Razão Social).
   - Seções de FAQ bem formatadas com perguntas comuns e respostas objetivas.

---

## 2. Como Usar no Bioma

- **Acesse o Estúdio:** Na barra lateral da **Operação EG $\to$ Auditor SEO & GEO**.
- **Insira a URL:** O sistema executa a varredura ao vivo em menos de 5 segundos.
- **Exporte os Ativos:**
  - Baixe o `llms.txt` pronto para colocar na hospedagem do cliente.
  - Copie o script `<script type="application/ld+json">` gerado para colar no cabeçalho do site.
  - Acompanhe a evolução histórica dos scores no banco do workspace.
