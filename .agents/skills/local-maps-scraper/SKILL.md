---
name: local-maps-scraper
description: "Framework e automação para prospecção B2B local no Google Maps, extração sem custo de API e enriquecimento de contatos (e-mails e redes sociais via web crawler)."
risk: low
source: google-maps-scraper-kit
date_added: "2026-10-22"
---

# Local Maps Scraper & Contact Enrichment Kit

> Prospecção ativa de PMEs locais com extração no Google Maps e garimpo automatizado de e-mails corporativos, WhatsApp e perfis sociais.

---

## 1. Pipeline de Prospecção

```
[ Busca / Scrape Maps ] ──> [ Normalização & Score ] ──> [ Crawler Web ] ──> [ Fila de Aprovação ] ──> [ CRM ]
```

---

## 2. Regras de Resiliência e Filtros Anti-Lixo

- **Filtro de Extensões:** Rejeita `.png`, `.jpg`, `.svg`, `.webp`, `.css`, `.js`.
- **Filtro de Templates:** Descarta `wixpress.com`, `sentry.io`, `example.com`, etc.
- **Redes Sociais:** Garimpa Instagram, Facebook, LinkedIn e link de WhatsApp.
- **Resiliência:** Timeout de 7s por site e tolerância a SSL de empresas locais.
