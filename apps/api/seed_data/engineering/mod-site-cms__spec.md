# Spec: mod-site-cms

- **Cliente:** EverGreen, site público e EG Lab (`target: internal`, consumo público)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-site-cms`, `portfolio-sites-recursos`, `selo-benchmark`, `mod-marca-artefatos`

## 1. Objetivo

Refatorar a presença pública da EverGreen e criar uma camada de CMS ligada ao backoffice, permitindo publicar cases, POCs, EG Lab, recursos, artigos e provas de valor com governança.

## 2. Contexto

A auditoria SEO/GEO indicou desalinhamento entre o site atual e o posicionamento da EG. Além disso, cases e POCs hoje tendem a ficar desconectados da operação real. O CMS deve aproximar site, backoffice, cliente, BI e dossiê de provas sem publicar dados sensíveis por acidente.

## 3. Escopo

O que será construído:

- Modelo de conteúdo para páginas, posts, cases, POCs, recursos e EG Lab.
- Workflow editorial: rascunho, revisão, aprovado, publicado, arquivado.
- Publicação de cases a partir de dados aprovados do backoffice.
- Portfólio de sites/recursos gratuitos como vitrine técnica.
- SEO/GEO: schema, metadados, páginas indexáveis e linguagem alinhada.
- Gestão de assets e exemplos visuais.
- Integração com `mod-marca-artefatos` e `dossie-provas`.

## 4. Fora de Escopo

- Publicar automaticamente dado de cliente sem aprovação.
- Construir page builder completo no MVP.
- Substituir ferramentas externas de design.
- Prometer faturamento/resultado financeiro no site.
- Publicar cursos/conteúdos de terceiros sem direito.

## 5. Requisitos Funcionais

- RF1 — Usuário autorizado deve criar/editar conteúdo com status editorial.
- RF2 — Conteúdo público deve ter title, description, slug, canonical e schema quando aplicável.
- RF3 — Case deve poder referenciar cliente, projeto, métricas aprovadas e assets.
- RF4 — Publicação deve exigir aprovação para conteúdos com dados de cliente.
- RF5 — Site deve separar cases reais, POCs e recursos gratuitos.
- RF6 — CMS deve registrar autor, revisor, data e versão.
- RF7 — Sistema deve suportar anonimização de métricas/cases.
- RF8 — Conteúdo aprovado deve poder ser renderizado estaticamente/ISR conforme ADR.

## 6. Requisitos Não-Funcionais

- **SEO/GEO:** páginas rápidas, semânticas e com dados estruturados.
- **Governança:** nada sensível vai ao público sem aprovação.
- **Performance:** páginas públicas devem ser estáticas/cacheadas quando possível.
- **Marca:** conteúdo precisa seguir tom e posicionamento atual da EG.
- **Segurança:** painel editorial interno autenticado e auditado.

## 7. Critérios de Aceite

- CA1 — Redator cria rascunho e revisor aprova antes de publicar.
- CA2 — Um case com métrica sensível exige aprovação explícita.
- CA3 — POC e case aparecem como tipos diferentes no site.
- CA4 — Página publicada possui metadados SEO/GEO básicos.
- CA5 — Usuário sem permissão editorial não publica conteúdo.
- CA6 — Conteúdo arquivado sai da navegação pública.

## 8. Riscos e Dependências

- **Risco:** site publicar promessa desalinhada com posicionamento premium/boutique.  
  **Mitigação:** workflow editorial e guia de copy.

- **Risco:** CMS próprio virar overengineering.  
  **Mitigação:** ADR build-vs-buy CMS.

- **Dependência:** `mod-marca-artefatos` para assets e padrões.
- **Dependência:** `mod-conhecimento`/`dossie-provas` para cases.
- **Dependência:** ADR CMS próprio-vs-headless externo.

