# Spec: client-hub

- **Cliente:** EverGreen + clientes EG (`target: internal`, com superfície de produto externa)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `client-hub`, `squad-raiox`, `health-score`, `selo-benchmark`, `aprovacao-tinder`, `marketplace-addons`, `delivery-tracker`, `gamificacao-setup`, `drive-rag-cliente`, `client-operating-agreement`, `exit-handover-mode`

## 1. Objetivo

Criar a área premium do cliente EG: um portal white-glove onde decisores acompanham métricas, score, entregáveis, aprovações, documentos, comunicações e oportunidades de expansão da parceria.

## 2. Contexto

Hoje a percepção de valor da EG fica espalhada entre WhatsApp, PDFs, ClickUp, Notion, apresentações, reuniões e arquivos enviados por Drive. O `client-hub` centraliza essa experiência e torna visível o que a EG está fazendo pelo cliente.

O módulo começa como ferramenta de uso EG-com-cliente. Depois pode evoluir para uso do cliente e, no limite, para white-label. Ele depende da fundação multitenant, de entitlements/ofertas e do motor de BI.

## 3. Escopo

O que será construído:

- Dashboard executivo por tenant com KPIs essenciais, status de parceria e próximos passos.
- Visão de Score/Raio-X por pilares: Oferta, Demanda e Conversão.
- Health Score da parceria: SLA, pendências, entregas, aprovações e risco de churn.
- Timeline de entregáveis estilo tracker: solicitado, em produção, em revisão, aprovado, publicado.
- Área de aprovações de criativos, textos, relatórios e decisões, incluindo experiência "tinder-style" quando aplicável.
- Área de módulos bloqueados/desbloqueados por oferta, plano, contrato ou entitlement.
- Acesso a dashboards do `mod-bi-dashboards` de forma nativa e sem parecer ferramenta externa.
- Biblioteca de documentos/artefatos do cliente: relatórios, contratos, brand book, links, gravações e recursos aprovados.
- Entrada para NFC/magic link dos kits, com segurança e expiração.
- Comunicação centralizada, inicialmente como espelho/resumo de WhatsApp/ClickUp/e-mail, não como substituição total.
- Marketplace de add-ons futuro: módulos, análises e serviços adicionais.
- Client Operating Agreement: ficha viva com escopo, SLAs, canais oficiais, módulos comprados, limites e regras de comunicação.
- Modo Saída/Handover: pacote organizado de exportação e transição quando o cliente encerrar contrato ou mudar de formato.

## 4. Fora de Escopo

- Substituir WhatsApp, ClickUp, Drive ou CRM no MVP.
- Permitir que o cliente rode análises sensíveis sozinho sem escopo/contrato.
- Expor dados brutos de outros clientes ou da operação interna EG.
- Criar billing completo dentro do Hub; isso pertence ao `mod-saas-billing`.
- Criar BI do zero dentro do Hub; visualizações vêm do `mod-bi-dashboards`.
- Liberar white-label/reseller antes de `mod-saas-billing`, theming e tenancy estarem maduros.

## 5. Requisitos Funcionais

- RF1 — Cliente autenticado deve acessar apenas dados do próprio tenant.
- RF2 — Usuário interno EG deve alternar tenants conforme permissões e com auditoria.
- RF3 — Hub deve exibir visão executiva com KPIs, health score, entregas e aprovações pendentes.
- RF4 — Hub deve exibir Score/Raio-X com histórico e interpretação por pilar.
- RF5 — Hub deve renderizar módulos bloqueados com motivo, valor percebido e CTA interno de upsell.
- RF6 — Hub deve consumir dashboards autorizados do `mod-bi-dashboards`.
- RF7 — Hub deve registrar aprovações/reprovações de criativos/relatórios com comentário e timestamp.
- RF8 — Hub deve aceitar acesso via magic link/NFC com token de curta duração e fallback seguro.
- RF9 — Hub deve listar documentos e links aprovados para aquele cliente.
- RF10 — Hub deve mostrar timeline de entregáveis e status operacional sem expor ruído interno.
- RF11 — Hub deve permitir que EG marque conteúdo como visível/invisível ao cliente.
- RF12 — Hub deve gerar eventos para `mod-conhecimento` quando cliente aprova, rejeita ou comenta entregáveis.
- RF13 — Hub deve exibir ou referenciar o acordo operacional vigente do cliente.
- RF14 — Hub deve suportar fluxo de handover/exportação conforme contrato e política de dados.

## 6. Requisitos Não-Funcionais

- **Segurança:** isolamento por RLS/tenant; URLs assinadas para arquivos; magic links com expiração.
- **Privacidade:** não expor anotações internas, custos, margem, prompts ou logs de squad ao cliente.
- **Performance:** visão executiva deve carregar em até 1,5s p95 com dados cacheados.
- **UX:** executivos devem entender status, valor e pendências em menos de 10 segundos.
- **Acessibilidade:** responsivo e utilizável em mobile, já que NFC provavelmente abre no celular.
- **Auditabilidade:** toda aprovação, acesso sensível e mudança de visibilidade deve gerar log.

## 7. Critérios de Aceite

- CA1 — Um cliente logado não consegue acessar dashboard, documento ou aprovação de outro tenant por URL direta.
- CA2 — Um usuário EG consegue publicar um relatório como visível ao cliente e o cliente consegue abrir pelo Hub.
- CA3 — Um magic link expirado não concede acesso e oferece fluxo seguro de reenvio.
- CA4 — Um criativo pode ser aprovado/reprovado pelo cliente e o evento fica associado ao entregável.
- CA5 — Um módulo não contratado aparece bloqueado com copy comercial, mas sem liberar a funcionalidade.
- CA6 — O Hub exibe pelo menos uma visão de BI embutida sem expor credenciais ou links internos.
- CA7 — O tracker mostra entregáveis em andamento e concluídos por cliente.

## 8. Riscos e Dependências

- **Risco:** prometer ao cliente uma plataforma completa antes de a operação estar estabilizada.  
  **Mitigação:** MVP focado em visibilidade, aprovações, BI e documentos.

- **Risco:** módulos bloqueados parecerem venda agressiva.  
  **Mitigação:** ligar upsell ao diagnóstico/score e às necessidades reais.

- **Risco:** magic link/NFC virar vetor de acesso indevido.  
  **Mitigação:** tokens curtos, device/session binding e opção de revogação.

- **Dependência:** `mod-multitenant` para auth, tenant e RBAC.
- **Dependência:** `mod-bi-dashboards` para dados e visualizações.
- **Dependência:** `cofre-senhas` e `mod-integrations-hub` para integrações seguras.
- **Dependência:** ADR de NFC/magic link.
- **Dependência:** ADR de entitlements/service catalog.
