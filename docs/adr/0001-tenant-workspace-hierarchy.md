# ADR 0001 — Hierarquia Platform → Tenant/Agência → Workspaces

- Estado: aceito para implementação incremental
- Data: 2026-07-18
- Decisores: EverGreen + engenharia Bioma
- Tarefas: `ARCH-CTX-001`, `DATA-WS-001A`

## Contexto

O Bioma começou com tenancy flat: uma organização EG e organizações de
clientes. Essa estrutura atende o MVP local, mas mistura três conceitos:

1. a EverGreen como dona da plataforma;
2. a EverGreen como agência que usa o produto;
3. cada cliente como contexto operacional e comercial.

Ela também não escala para uma agência white-label com equipe e clientes
próprios. A Operação EG precisa manter CRM, financeiro e métricas próprios sem
aparecer na carteira e sem duplicar os motores usados pelos clientes.

## Decisão

O modelo canônico do produto é:

```text
Bioma Platform
└── Tenant / Agência
    ├── Workspace agency_internal
    └── Workspaces client
```

- **Platform** é o control plane do produto.
- **Tenant** é a agência assinante/operadora e, nesta transição, é representado
  por uma organização raiz.
- **Workspace** é a identidade do contexto operacional e da fronteira de dados.
- **ClientAccount** (`clients`) é a extensão comercial de um workspace cliente;
  não é a identidade de um workspace interno.

`workspaces.id` passa a ser a identidade canônica de contexto. Durante a
transição, `workspaces.subject_organization_id` aponta para a organização que
continua escopando fisicamente os dados existentes.

## Invariantes

1. Uma organização-subject possui no máximo um workspace ativo no modelo v1.
2. Um tenant possui no máximo um workspace `agency_internal` ativo.
3. A Operação EG é `agency_internal`; nunca é retornada como ClientAccount.
4. O cliente pertence a um tenant de forma explícita; não há fallback por nome,
   posição em lista ou cliente selecionado na UI.
5. `enabled_modules` é entitlement de produto, não autorização de escrita.
6. Acesso efetivo futuro será `papel + assignment + módulo habilitado`.
7. Rotas legadas recebem `client_id` apenas por adapter. A regra de negócio não
   deve passar a depender de `EverGreen Internal` em código novo.
8. Dados de outro workspace retornam `404` depois da resolução de acesso, para
   reduzir enumeração/IDOR.

## Rotas e navegação

As URLs continuam rasas e compatíveis:

- `/operacao/...` para o workspace interno da EG;
- `/clientes/:clientId/...` enquanto os módulos ainda usam o adapter legado;
- `GET /workspaces` para descoberta autenticada e escalável de contextos.

O navegador do Topbar usa workspaces persistentes e guarda recentes por
`workspace.id`. A carteira continua sendo uma visão comercial completa, não uma
lista de navegação dentro da Sidebar.

No futuro, a URL pode receber um identificador opaco de workspace quando houver
mais de um tenant acessível à mesma pessoa, mas não deve materializar a árvore
`platform/tenant/client` inteira.

## Autorização

Estado transitório:

- `eg_admin` na organização EG continua sendo platform admin;
- `client_user` continua limitado aos workspaces cliente ativos em cuja
  organização possui membership direta com esse papel;
- `parent_organization_id` e `tenant_organization_id` não concedem acesso por si
  mesmos;
- `GET /workspaces` retorna tudo para platform admin e somente workspaces
  `client` ativos com membership direta `client_user` para os demais usuários;
- convites de cliente não podem ser emitidos nem aceitos para o workspace
  interno da agência.
- Client Hub, Files, Performance e Kommo resolvem o mesmo workspace ativo antes
  de acessar o adapter por `client_id` ou `organization_id`.

Antes do white-label serão obrigatórios:

- `platform_admin` separado de `tenant_admin`;
- papéis operacionais/viewer/aprovador;
- times e assignments de workspace;
- uma dependência central `require_workspace_access/permission`;
- matriz automatizada de tenant A × tenant B × workspace interno × cliente.

## White-label e billing

Este ADR prepara, mas não declara prontos:

- branding/domínio por tenant;
- cobrança, plano e limites de uso;
- customização de módulos;
- isolamento administrativo entre agências;
- impersonation/suporte do control plane;
- exportação e portabilidade de dados.

Billing deve pertencer ao tenant. Entitlements podem restringir módulos e
limites do plano, mas não substituem RBAC/assignments.

## Migração incremental

1. **Identidade e descoberta — entregue:** tabela `workspaces`, backfill,
   provisionamento transacional e `GET /workspaces`.
2. **Adapters — entregue:** resolver `workspace_id → organization_id/client_id`
   antes de reutilizar services/repositories atuais.
3. **Domínios organization-scoped — entregue:** CRM, financeiro, arquivos,
   artefatos e métricas manuais aceitam workspace sem duplicar lógica.
4. **Performance — entregue em transição:** identificador externo renomeado para
   `gtm_workspace_id`; UUID canônico adicionado com backfill e dual-write. As
   colunas `client_id` permanecem até a remoção segura da ponte.
5. **Papéis e assignments:** separar platform/tenant e introduzir times.
6. **Remoção da ponte:** excluir `EverGreen Internal` apenas quando não houver
   endpoint, fila ou FK dependente de seu `client_id`.

## Alternativas rejeitadas

- **Manter a EG como cliente comum:** confunde carteira e operação interna.
- **Duplicar CRM/financeiro/métricas para a EG:** aumenta drift e manutenção.
- **Fazer a migração total em uma rodada:** Performance e worker ainda possuem
  várias FKs em `client_id`; o risco de perda/regressão é desnecessário.
- **Usar apenas `parent_organization_id`:** hierarquia organizacional sozinha não
  fornece identidade de contexto, assignments ou autorização.

## Consequências

Positivas: identidade estável, navegador escalável, transição auditável e base
para white-label. Temporárias: duas identidades convivem (`workspace_id` e
`client_id`) e a Operação EG ainda precisa de `legacy_client_id` para alguns
módulos. Essa dívida é explícita e tem ordem de remoção definida acima.
