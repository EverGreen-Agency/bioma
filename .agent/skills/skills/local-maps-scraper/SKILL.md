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
[ Busca / Scrape Maps ]
        │ (Nicho + Cidade)
        ▼
[ Normalização Determinística ]
        │ (Cálculo de Presence Score 0-100 & Gaps)
        ▼
[ Enriquecimento Web (Crawler Autônomo) ]
        │ (Varredura do site: e-mails corporativos, Instagram, LinkedIn, WhatsApp)
        ▼
[ Fila de Aprovação Humana no Bioma ]
        │
        ▼
[ Conversão em Lead no CRM & Disparo WhatsApp ]
```

---

## 2. Regras de Resiliência e Filtros Anti-Lixo

### E-mails Corporativos
1. **Filtro de Extensões:** Rejeita assets estáticos (`.png`, `.jpg`, `.svg`, `.webp`, `.css`, `.js`).
2. **Filtro de Templates:** Descarta domínios geradores de falso positivo (`wixpress.com`, `sentry.io`, `example.com`, `cloudflare.com`).
3. **Ordenação por Probabilidade:** Prioriza e-mails que coincidem com o domínio raiz do estabelecimento e com prefixos comerciais (`contato@`, `comercial@`, `atendimento@`).

### Redes Sociais
1. **Instagram:** Garimpa links `instagram.com/<perfil>` descartando rotas internas (`/p/`, `/reels/`, `/explore/`).
2. **LinkedIn & Facebook:** Extrai páginas de empresas e perfis comerciais válidos.
3. **WhatsApp Link:** Detecta links diretos de `wa.me/` ou `api.whatsapp.com`.

### Resiliência de Rede
- Timeout estrito de 7 segundos por site para evitar bloqueio de thread.
- Desativação de verificação SSL rígida para permitir leitura de sites de PMEs locais com certificados autoassinados ou expirados.

---

## 3. Uso no Bioma

- **Interface:** Acesse em **Operação EG $\to$ Radar Local**.
- **Visualização em Tabela (Scraper Kit Table):** Selecione os leads desejados e clique em **⚡ Enriquecer Selecionados**.
- **Abordagem Segura:** Nenhum lead recebe mensagem sem revisão humana prévia (`review_status = 'approved'`).
