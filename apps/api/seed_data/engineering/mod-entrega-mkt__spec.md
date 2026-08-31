# Spec: mod-entrega-mkt

- **Cliente:** EverGreen + clientes EG (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-entrega-mkt`, `squad-criativos`, `squad-trafego`, `squad-relatorios`, `squad-seo-geo`, `ads-api-skills`

## 1. Objetivo

Organizar a produção, revisão, aprovação, publicação e medição das entregas de marketing/growth da EG em torno de campanhas, criativos, SEO/GEO, relatórios e ações de tráfego.

## 2. Contexto

Hoje parte das entregas existe em squads e ferramentas externas. O módulo não deve substituir especialistas, mas criar rastreabilidade e conexão entre briefing, produção, aprovação, publicação, métrica e aprendizado.

## 3. Escopo

O que será construído:

- Registro de entregáveis de marketing por cliente, campanha, pilar e canal.
- Briefing, status, responsável, prazo, revisão e aprovação.
- Integração com squads de criativos, tráfego, relatórios e SEO/GEO.
- Aprovação cliente/interna via `mod-workflows-aprovacoes`.
- Checklist QA antes de publicar: links, UTMs, política, gramática e marca.
- Envio de evidências para `mod-bi-dashboards`, `mod-conhecimento` e `client-hub`.

## 4. Fora de Escopo

- Publicar automaticamente campanha com verba sem HITL.
- Substituir Meta/Google Ads Manager.
- Criar ferramenta de design completa.
- Automatizar toda estratégia de marketing sem julgamento humano.

## 5. Requisitos Funcionais

- RF1 — Sistema deve cadastrar entregável com cliente, canal, objetivo, prazo e owner.
- RF2 — Entregável deve passar por estados: briefing, produção, revisão, aprovação, publicado, medido.
- RF3 — Aprovação sensível deve usar `mod-workflows-aprovacoes`.
- RF4 — Criativos devem poder ser enviados para aprovação no `client-hub`.
- RF5 — Publicação deve registrar link, UTM, campanha e evidência.
- RF6 — Métricas pós-publicação devem se conectar ao BI quando disponíveis.
- RF7 — Aprendizados devem alimentar `mod-conhecimento`.

## 6. Requisitos Não-Funcionais

- **Segurança:** escrita em plataformas externas sempre HITL.
- **Rastreabilidade:** todo entregável deve ter histórico.
- **Qualidade:** QA obrigatório para links/UTMs/copy.
- **UX:** status claro para operação e cliente.

## 7. Critérios de Aceite

- CA1 — Um criativo passa de briefing até aprovado com histórico.
- CA2 — Entregável publicado registra URL/UTM e campanha.
- CA3 — Ação de tráfego com impacto em verba exige aprovação.
- CA4 — Cliente aprova/reprova material no Hub.
- CA5 — Métrica do entregável aparece ligada ao BI quando coletada.

## 8. Riscos e Dependências

- **Risco:** duplicar ClickUp sem ganho.  
  **Mitigação:** começar com rastreabilidade crítica e integração, não gestão genérica.

- **Dependência:** `client-hub`.
- **Dependência:** `mod-bi-dashboards`.
- **Dependência:** `mod-workflows-aprovacoes`.
- **Dependência:** `mod-integrations-hub`.

