# Próximos Passos - Bioma MVP v0

## Antes de Codar

- Revisar e aprovar os ADRs `0001` a `0005`.
- Revisar o ADR `0006` antes de produção real com dados de clientes.
- Confirmar que `bioma-legacy/` fica apenas como referência.
- Parar containers Supabase do legado quando não estiverem em uso.
- Garantir que nenhuma credencial real entre no scaffold.

## Scaffold Inicial

Criar `bioma/` com:

```text
bioma/
  apps/
    web/
    api/
    worker/
  packages/
    contracts/
  infra/
```

## Ordem de Implementação

1. Scaffold monorepo local.
2. Docker Compose local com Postgres.
3. API FastAPI com healthcheck.
4. Web React/Vite com tela base EG.
5. Modelo mínimo de auth, usuário, organização e membership.
6. Seed EG admin + cliente demo HM-like.
7. Deploy staging: Vercel + Railway.
8. Cockpit interno mínimo.
9. ClickUp Bridge read-only.
10. Client Hub mínimo.

## Gate Para Produção

- Login funcionando.
- Isolamento Cliente A/B testado.
- Staging e produção separados.
- Backup configurado.
- Healthcheck da API.
- Logs sem segredo.
- Nenhuma escrita no ClickUp sem aprovação humana.
