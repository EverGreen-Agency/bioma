# Spec: mod-cockpit-interno

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-cockpit-interno`, `banco-ideias`, `banco-stack`, `banco-arquitetura`, `hub-chat-dispatcher`, `tag-ativacao`, `cross-repo-awareness`, `eng-agentes-especializados`, `escritorio-virtual`

> Esta spec corrige a interpretação sobre o `/dashboard`: ele foi o embrião histórico do cockpit, mas não dita a arquitetura nem a stack do Bioma. O Bioma nasce greenfield. O `/dashboard` vira legado intencional: inventariado, reaproveitado quando fizer sentido e aposentado formalmente quando suas funções úteis existirem no Bioma.

## 1. Objetivo

Criar a superfície operacional interna onde Eduardo, equipe e squads acompanham ideias, arquitetura, stack, engenharia, aprovações humanas, execuções de agentes e saúde do ecossistema Bioma.

## 2. Contexto

O cockpit atual em `/dashboard` é um visualizador local em Vite/React que lê bancos internos em JSON/Markdown. Ele não possui autenticação, tenancy, operação real de negócio nem contratos de segurança para uso externo. Ainda assim, ele contém aprendizados valiosos de UI e fluxo: Banco de Ideias, Tech Radar, Arquitetura, Squads, watchers e visualização de estado.

A decisão vigente do Bioma é greenfield: Next.js, Supabase Auth, Postgres/RLS, Drizzle, BullMQ e módulos de produto. O cockpit novo deve nascer dentro dessa arquitetura. O código antigo não será migrado por obrigação, mas também não será deixado sem destino.

## 3. Escopo

O que será construído:

- Interface autenticada de administração interna do Bioma.
- Área de Banco de Ideias com leitura, filtro, edição controlada e rastreabilidade.
- Área de Engenharia listando specs, ADRs, tasks e status por módulo.
- Área de Arquitetura com decisões, ferramentas externas, banco de stack e Tech Radar.
- Hub do Dispatcher para enviar demandas a squads com aprovação humana.
- Caixa de aprovações HITL para tarefas, publicações, automações e mudanças sensíveis.
- Visão de execuções de squads, logs, estados e aprendizados.
- Inventário do `/dashboard` legado: telas úteis, componentes reaproveitáveis, código descartável e plano de aposentadoria.
- Integração com `mod-observabilidade` para expor saúde do sistema e falhas operacionais.

## 4. Fora de Escopo

- Migrar o `/dashboard` Vite inteiro para o Bioma.
- Manter compatibilidade visual ou técnica obrigatória com Phaser/Vite.
- Expor o cockpit interno para clientes finais.
- Automatizar execução sem checkpoint humano em ações sensíveis.
- Transformar o escritório virtual/pixel art em prioridade de MVP.
- Substituir o Git/Markdown como memória interna antes de uma decisão formal de portabilidade dos bancos.

## 5. Requisitos Funcionais

- RF1 — O usuário interno autenticado deve ver lista de módulos de engenharia com spec, ADRs, status e pendências.
- RF2 — O cockpit deve ler o Banco de Ideias atual e permitir edição apenas para papéis autorizados.
- RF3 — O cockpit deve listar Tech Radar/Banco de Stack com filtros por anel, categoria e decisão relacionada.
- RF4 — O cockpit deve expor uma fila de aprovações HITL com contexto, risco, ação proposta e botões de decisão.
- RF5 — O cockpit deve registrar auditoria de toda edição manual em bancos internos ou ações de squad.
- RF6 — O cockpit deve acionar o Dispatcher por comando textual e mostrar a rota proposta antes da execução.
- RF7 — O cockpit deve exibir estado de squads/runs sem depender de navegação manual em pastas.
- RF8 — O cockpit deve ter uma página "Legado /dashboard" com inventário de reaproveitamento e decisão final por item.
- RF9 — O cockpit deve distinguir artefatos de run, projetos de cliente e módulos de plataforma conforme `OUTPUT-CONVENTION.md`.
- RF10 — O cockpit deve consumir sinais de observabilidade: API, workers, filas, banco, integrações e erros críticos.

## 6. Requisitos Não-Funcionais

- **Segurança:** acesso restrito a usuários internos EG; toda escrita exige RBAC e auditoria.
- **Dados:** bancos internos continuam em arquivo até ADR específico; dados operacionais de produto ficam no DB.
- **Performance:** listagens principais devem carregar em até 1s p95 em ambiente interno.
- **Confiabilidade:** ações de squad precisam ser idempotentes ou explicitamente marcadas como não reversíveis.
- **UX:** interface densa, utilitária e escaneável; evitar landing page e decoração sem função.
- **Manutenibilidade:** nenhuma tela nova deve depender diretamente de caminhos hardcoded sem adapter.

## 7. Critérios de Aceite

- CA1 — Um usuário interno consegue abrir uma aba Engenharia e localizar `client-hub`, `mod-bi-dashboards` e `mod-multitenant` com spec/ADRs.
- CA2 — Uma alteração no Banco de Ideias feita pelo cockpit gera registro de auditoria com usuário, timestamp, diff resumido e motivo.
- CA3 — Uma demanda enviada ao Dispatcher aparece como proposta antes de executar qualquer squad.
- CA4 — A fila HITL impede ações sensíveis sem aprovação explícita.
- CA5 — O inventário do `/dashboard` classifica cada item como `portar`, `descartar`, `manter temporário` ou `substituído`.
- CA6 — Quando uma tela útil do `/dashboard` for portada, o inventário registra a nova URL/área equivalente no Bioma.
- CA7 — O cockpit não exige que o `/dashboard` antigo esteja rodando para funcionar.

## 8. Riscos e Dependências

- **Risco:** tentar migrar o Vite antigo por apego histórico e atrasar o Bioma.  
  **Mitigação:** tratar `/dashboard` como inventário de produto, não como base arquitetural.

- **Risco:** permitir edição direta em JSON sem validação e quebrar bancos internos.  
  **Mitigação:** adapters com schema validation e backup/diff antes da escrita.

- **Risco:** virar uma tela bonita de status sem resolver o fluxo real de decisão.  
  **Mitigação:** priorizar Engenharia, Ideias, Aprovações e Dispatcher antes de visualizações lúdicas.

- **Dependência:** `mod-multitenant` para auth/RBAC.
- **Dependência:** `mod-observabilidade` para sinais de saúde.
- **Dependência:** `OUTPUT-CONVENTION.md` para navegação de artefatos.

