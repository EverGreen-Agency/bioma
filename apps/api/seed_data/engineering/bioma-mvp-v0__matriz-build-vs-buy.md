# Matriz Build vs Buy - Bioma MVP v0

- **Data:** 2026-07-09
- **Status:** rascunho aprovado para planejamento
- **Escopo:** decidir o que construir, integrar, comprar ou adiar no primeiro corte do Bioma.

## 1. Princípio

Bioma deve construir o que vira moat da EG: experiência do cliente, visibilidade operacional, governança, dados, aprovações, ponte ClickUp, artefatos de engenharia e IA aplicada ao método EG.

Bioma deve integrar ou comprar o que é commodity, exige compliance pesada, possui ecossistema maduro ou atrasaria o MVP sem aumentar o diferencial.

## 2. Critérios

Use estes critérios antes de decidir:

- **Moat:** isso diferencia a EG ou só recria ferramenta comum?
- **Controle:** precisamos controlar dado, regra, UX ou workflow?
- **Tempo:** construir atrasa o primeiro deploy?
- **Risco:** erro aqui gera vazamento, LGPD, perda financeira ou instabilidade?
- **Custo:** pagar terceiro é mais barato do que manter?
- **Lock-in:** se trocar fornecedor depois, o estrago é aceitável?
- **Cliente:** o cliente percebe valor direto ou só complexidade?

## 3. Decisões v0

| Área | Decisão v0 | Motivo |
| --- | --- | --- |
| Frontend | Construir | UX é parte central do moat. Começar limpo, inspirado no dashboard legado e mockups HM, mas com branding EG. |
| Backend/API | Construir | Regras de negócio, auditoria, ClickUp, IA, auth e dados precisam de controle próprio. |
| Auth | Construir simples com libs maduras | Login/senha inicial é suficiente. Não inventar hash, sessão ou criptografia. Clerk fica como plano B se velocidade superar lock-in. |
| Banco | Postgres direto | Fonte de verdade operacional. Evita depender de BaaS como Supabase no core do MVP. |
| RLS | Avaliar como defesa adicional | RLS é primitivo do Postgres e útil para defesa em profundidade, mas a autorização principal deve ficar no backend. |
| Supabase | Não usar como default v0 | Pode ser avaliado depois, mas o desconforto com lock-in e segurança multitenant pesa contra no core. |
| ClickUp | Integrar | ClickUp continua PM tool. Bioma vira plano de controle e hub executivo. |
| CRM | Construir mínimo + integrar | Não substituir Kommo/ClickUp agora. Criar ficha de cliente, pipeline simples e relação com entregáveis. |
| Kommo | Integrar/adicionar automações depois | Dedup e CRM completo ficam depois; não bloqueiam o MVP EG/HM-like. |
| Autentique | Integrar depois | Contrato e assinatura são commodity regulada. Melhor integrar do que reconstruir. |
| Chat/WhatsApp | Adiar | Chatwoot/WhatsApp trazem complexidade operacional e política. V0 usa links/resumos/registro. |
| Cofre | Checklist + fallback seguro | Full vault é risco alto. Primeiro substituir planilha por fluxo estruturado; segredo real exige ADR. |
| BI | Snapshot/embed/import manual | Dashboard completo com ingestão API vem depois. V0 publica relatório e indicadores curados. |
| LinkedIn/Ads APIs | Contingência/manual no v0 | Dependem de aprovações, OAuth, escopos e contas externas. Planejar, não bloquear deploy. |
| IA | Harness próprio + LLM externa | O diferencial é o workflow EG, não treinar modelo próprio. Registrar prompt, schema, custo e aprovação. |
| Workers | Introduzir por necessidade | Usar worker quando houver sync recorrente, webhook, retry, LLM demorada ou relatório. |
| OpenSquad | Usar como backoffice interno | Não transformar em runtime obrigatório do produto. Bioma deve conseguir viver sem rodar squad. |
| White-label/SaaS | Adiar | Arquitetura não deve impedir, mas não construir reseller/billing no v0. |
| Infra própria/micro AWS | Adiar | Alto custo operacional. V0 sobe em Vercel + Railway. Fly fica como alternativa posterior. |

## 4. Regras de Decisão

- Se for segurança crítica e commodity madura, preferir biblioteca/provedor com boa auditoria.
- Se for experiência premium, método EG, relação com cliente ou dado operacional, preferir construir.
- Se for integração externa com termos, OAuth ou compliance própria, preferir integrar oficialmente.
- Se for só estética ou visão futura sem ROI imediato, colocar em backlog.
- Se o módulo for usado primeiro pela EG e virar produto depois, construir pequeno e dogfooding antes de vender.

## 5. Stack Recomendada Para ADR Inicial

Recomendação pragmática para o primeiro ADR:

- `apps/web`: React + Vite + TypeScript, hospedado na Vercel.
- `apps/api`: FastAPI + Python, hospedado na Railway.
- `apps/worker`: RQ/Celery ou worker Python separado, na Railway, somente quando necessário.
- `db`: Postgres gerenciado na Railway.
- `cache/queue`: Redis apenas quando houver worker real.
- `schemas`: Pydantic/OpenAPI para gerar contratos para o front.

Racional: separa front/back, evita serverless como centro da arquitetura, favorece IA e integrações em Python, permite deploy rápido e mantém o núcleo fora de uma stack BaaS. Railway é a escolha de velocidade para o MVP; Fly continua como alternativa se a EG precisar de controle mais fino de runtime, região, rede ou topologia.

## 6. Referências

- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase self-hosting: https://supabase.com/docs/guides/self-hosting
- Clerk docs: https://clerk.com/docs
- Railway environments: https://docs.railway.com/environments
- Fly pricing: https://fly.io/docs/about/pricing/

Leitura: Supabase documenta RLS como recurso de Postgres para regras granulares e defesa em profundidade, mas isso não obriga usar Supabase como plataforma. Supabase self-hosted exige operar a própria infraestrutura com Docker. Clerk oferece auth, usuários, organizações e billing, mas isso troca velocidade por dependência externa. Railway é mais direto para o MVP v0; Fly é opção técnica forte para fases com mais controle de infraestrutura.
