# ADR-0003: Dados, Postgres e Isolamento

- **Status:** aprovado para MVP v0
- **Data:** 2026-07-09
- **Contexto:** Bioma precisa separar dados da EG e de clientes sem antecipar complexidade de SaaS público.

## Decisão

Usar Postgres direto como fonte de verdade operacional, com autorização principal no backend.

Modelo mínimo:

- `users`
- `organizations`
- `memberships`
- `clients`
- `artifacts`
- `deliverables`
- `approvals`
- `clickup_mappings`
- `sync_runs`
- `ai_runs`
- `audit_logs`

RLS pode ser avaliado como defesa adicional, mas não substitui a autorização explícita no backend.

## Motivos

- Postgres é portável, maduro e suficiente para o MVP.
- O domínio da EG fica livre de API proprietária de BaaS.
- Auditoria e isolamento precisam ser previsíveis.
- O sistema nasce pequeno, mas com caminho claro para multi-tenant real.

## Alternativas Consideradas

- **Supabase como plataforma:** não é adotado como default no reset, embora RLS continue sendo uma técnica válida.
- **SQLite local:** simples demais para staging/produção e colaboração.
- **Banco por cliente:** isolamento forte, mas operacionalmente pesado para o MVP.

## Consequências

- Toda query sensível deve passar por tenant/organization scope.
- Testes devem cobrir acesso cruzado entre Cliente A e Cliente B.
- Migrações precisam ser explícitas e versionadas.
- Backups e restore devem entrar no checklist antes de produção real.
