# eg-publish (deploy de artefatos: Vercel / GitHub Pages)

**id:** `eg-publish` · **tipo:** skill (Infra) · **stage:** capture · **origin:** internal
**relação:** last-mile de `web-artifacts-builder` e `doc-generator-eg`

## Problema
Quando a EG entrega um artefato web (protótipo, landing, doc HTML) para cliente, mandar como **link de artefato do claude.ai derruba a percepção de valor**. E hospedar à mão dá trabalho. Falta uma forma de **um comando → URL profissional**.

## O que faz
Recebe uma **pasta com o artefato estático** e publica:
- **Vercel** (padrão EG): CLI (`vercel deploy --prod`) ou MCP autenticado. Domínio custom fácil (subdomínio EG). Deploy instantâneo, preview por deploy.
- **GitHub Pages**: via `gh` (cria/usa repo, habilita Pages). 100% grátis; URL menos slick sem domínio custom.
Devolve a **URL**.

## Vercel × GitHub Pages (quando usar cada)
| | GitHub Pages | Vercel |
|---|---|---|
| Custo | grátis | grátis (Hobby) |
| URL | `user.github.io/repo` | `projeto.vercel.app` + domínio custom trivial |
| Deploy | push → minutos | instantâneo |
| Serverless/SSR | não | sim |
| Percepção (cliente) | ok | **melhor** (domínio EG) |
| Melhor pra | estático simples | **entregável de cliente**, escala p/ app |

## Guardrails (inegociáveis)
- **Deploy só de pasta isolada** contendo APENAS o artefato. **Nunca a raiz do repo** — senão vaza `squads/`, `_opensquad/_memory/`, dados de cliente. (Aprendizado do deploy do protótipo Rian: o MCP `deploy_to_vercel` não recebe caminho e deployaria a raiz — por isso: isolar a pasta e usar a CLI escopada.)
- **HITL** antes de publicar artefato que referencie cliente/dado sensível (NDA). URL não indexada por padrão; genericizar quando fizer sentido.

## Aprendizado técnico (deploy Rian, 02/07)
- Vercel CLI instalada mas **precisa `vercel login`** (interativo) — o MCP é autenticado mas **sem escopo de pasta** (risco de vazar repo).
- `gh` não estava no PATH.
- Fluxo seguro: `mkdir pasta-isolada` → copiar só o artefato → `vercel deploy --prod --yes` a partir dela.

## Caminho (Trilho B)
Registrada (capture). Próximo: Arquiteto (cabe? reaproveita MCP Vercel/`gh`?) → se `build`, vira skill via Engenharia. Dor ativa (deploy do protótipo Rian) → sugestão de horizonte NOW/MEDIUM.
