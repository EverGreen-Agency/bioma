# Bioma Contracts

Contrato compartilhado entre API e web (CONTRACT-001).

`openapi.json` é o OpenAPI da API FastAPI, **gerado e versionado**. Não editar
à mão. O diff dele é a evidência de que o contrato mudou.

## Fluxo ao mexer no backend

Depois de qualquer mudança em rota/schema da API:

```bash
# em bioma/apps/api
python scripts/export_openapi.py          # regenera openapi.json

# em bioma/apps/web
npm run types:api                          # regenera src/types/api-schema.d.ts
npx tsc -b                                 # trava de drift dispara aqui
```

`src/types/contract-conformance.ts` compara, em tempo de compilação, os tipos
escritos à mão em `lib/api.ts` com os schemas gerados; divergência de campo ou
tipo quebra o `tsc`.

## Travas de CI (`bioma-ci.yml`)

- `export_openapi.py --check` — falha se `openapi.json` não refletir a API atual.
- `git diff --exit-code src/types/api-schema.d.ts` — falha se os tipos gerados
  não estiverem sincronizados com o `openapi.json` versionado.

Destino: migrar `lib/api.ts` para consumir `components["schemas"][...]` direto
e aposentar tanto os tipos à mão quanto o arquivo de conformância.
