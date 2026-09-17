# Spec: mod-workspace

- **Cliente:** EverGreen + futuros tenants (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho baixa prioridade
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-workspace`, `drive-rag-cliente`, `cofre-senhas`

## 1. Objetivo

Avaliar e, se fizer sentido no futuro, criar uma camada própria de workspace: arquivos, drive, e-mail, calendário, docs e permissões.

## 2. Contexto

Eduardo levantou a possibilidade de absorver Titan/Google Workspace. A avaliação atual é que isso pode ser overreach. O destino correto é manter como spec futura e só avançar se o ROI justificar.

## 3. Escopo

- Avaliar build-vs-buy para drive/e-mail/calendar/docs.
- Definir integração com Drive/RAG do cliente.
- Mapear permissões e compartilhamento de documentos.
- Começar por índice/organização de arquivos, não e-mail próprio.

## 4. Fora de Escopo

- Substituir Google Workspace/Titan no curto prazo.
- Criar servidor de e-mail próprio no MVP.
- Construir editor de documentos colaborativo.

## 5. Requisitos Funcionais

- RF1 — Sistema deve catalogar arquivos por tenant e origem.
- RF2 — Arquivo deve poder ser indexado por `mod-conhecimento`.
- RF3 — Permissões de arquivo devem respeitar tenant/RBAC.
- RF4 — Integrações externas de drive passam pelo hub de integrações.

## 6. Requisitos Não-Funcionais

- **Prioridade:** baixa; não bloqueia Fase 1.
- **Segurança:** arquivo privado nunca público por padrão.
- **Reversibilidade:** manter integração externa até prova de ROI.

## 7. Critérios de Aceite

- CA1 — Decisão build-vs-buy documentada antes de qualquer código próprio.
- CA2 — Arquivo indexado mantém origem e permissão.
- CA3 — Tenant não acessa arquivo de outro tenant.

## 8. Riscos e Dependências

- **Risco:** construir Google Workspace piorado.  
  **Mitigação:** começar como integração/catalogação, não substituição.

- **Dependência:** `mod-conhecimento`.
- **Dependência:** `mod-integrations-hub`.

