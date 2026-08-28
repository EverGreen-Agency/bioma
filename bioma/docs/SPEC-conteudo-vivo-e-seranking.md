# Spec — conteúdo vivo e integração de SEO no Bioma

Status: **proposta, nada implementado.** Escrito em 2026-08-28.
Cobre duas frentes que compartilham a mesma tese: **o Bioma é a fonte, o site lê.**

1. Conteúdo das apresentações (`/growth`, `/tech`) e dos cases saindo do código
2. Dados de SEO (SE Ranking ou equivalente) entrando no Bioma, em dois níveis

---

## ADR 1 — O que vai para o banco e o que fica no código

**Contexto.** Hoje o conteúdo das duas LPs vive em `src/app/growth/data.ts` e
`src/app/tech/data.ts`, no repo do site. Mudar uma vírgula de copy exige editar
TypeScript, rodar build e dar deploy. O Eduardo levantou que isso devia ser vivo,
como uma página de cases.

**Decisão.** Dividir por natureza do conteúdo, não mover tudo.

| Conteúdo | Onde vive | Por quê |
|---|---|---|
| **Cases** | **Bioma** | Mudam com frequência, precisam de trilha de autorização, e são reusados em proposta, portfólio e nas duas LPs. Hoje estão duplicados em três lugares. |
| **Método, fases, escada, manifesto** | **Código** | São o Documento-Mestre transformado em tela. Devem mudar só quando o documento muda — e aí um deploy é a fricção *certa*, não um atrito a remover. |
| **Copy de UI (títulos, eyebrows, CTA)** | **Código** | Acoplada ao layout. Editar sem ver o resultado quebra mais do que resolve. |

**Consequência mais importante:** o campo `leadConsent` que hoje é um objeto
opcional num array TypeScript (`src/config/portfolio.ts`) vira **coluna com
`NOT NULL` onde precisa ser**. A pendência de autorização da Dra. Sara e da Kontes
deixa de depender de alguém lembrar e passa a ser uma trava do banco: case sem
autorização registrada não é publicável.

Isso, sozinho, já justifica a migração dos cases.

**Alternativa descartada:** mover tudo para o banco. Perde a segurança de tipo em
conteúdo que quase nunca muda, e obriga a construir um editor completo antes de
qualquer ganho.

---

## ADR 2 — Como o site consome

**Decisão.** Repetir o padrão do benchmark, que já está construído e funciona:
Bioma expõe endpoint público read-only, o site lê. Nada de o site falar com o
banco.

Precedente: `GET /public/benchmark` (`bioma/apps/api/.../routers/benchmark.py`,
migração 0012). Mesma forma:

```
GET /public/cases?deck=growth&lang=pt
GET /public/cases/{slug}
```

Sem autenticação, só conteúdo já marcado como publicável. O site busca em build
com revalidação (ISR) — assim uma edição no Bioma aparece sozinha em minutos, sem
deploy, e o site continua de pé se a API cair.

**Fallback obrigatório:** se a API não responder, a LP renderiza o último
conteúdo em cache. Uma apresentação comercial não pode ficar em branco porque a
API estava reiniciando — ela vai colada numa proposta.

---

## User stories — conteúdo vivo

**US-1 · Editar um case sem deploy**
Como Eduardo, quero corrigir um número ou uma frase de um case pela tela do
Bioma, para que a correção apareça na LP sem depender do CTO nem de build.
*Aceite:* editar → salvar → a `/growth` mostra o texto novo em até 5 minutos; o
histórico guarda quem mudou o quê.

**US-2 · Autorização como trava, não como lembrete**
Como Eduardo, quero que um case com dado de cliente nomeado só possa ser
publicado com a autorização registrada, para que não exista de novo o caso de a
`/growth` publicar funil e custo de aquisição sem trilha.
*Aceite:* case com `client_named = true` e `consent_status != 'granted'` não sai
no endpoint público; a tela mostra por que está retido.

**US-3 · Um case, três destinos**
Como Eduardo, quero escrever o case uma vez e escolher onde ele aparece (LP de
growth, LP de tech, portfólio), para parar de manter três cópias divergentes.
*Aceite:* o mesmo case aparece nos destinos marcados; editar num lugar edita em
todos.

**US-4 · Ver o deck como o prospect vê**
Como Eduardo, quero pré-visualizar a LP com o conteúdo em rascunho antes de
publicar.
*Aceite:* uma URL de preview com token mostra o rascunho; o público continua
vendo a versão publicada.

---

## Modelo de dados — esboço

```
cases
  id, slug, deck (growth|tech|ambos), order
  name, category, headline, metric, evidence, highlights[]
  client_named          bool     -- dispara a trava de autorização
  consent_status        enum     -- none | requested | granted | waived
  consent_note, consent_at, consent_by
  status                enum     -- draft | published | retired
  created_at, updated_at, updated_by

case_sections
  id, case_id, lang (pt|en), order, label, title
  blocks  jsonb   -- mesmo formato de CaseContentBlock hoje

  UNIQUE (case_id, lang, order)
```

`blocks` fica em `jsonb` de propósito: o formato já existe e está estável no
código (`lead | paragraph | quote | points | metrics | flow | group`), e
normalizar bloco a bloco em tabela não paga o custo.

**Paridade de idioma vira validação:** publicar exige que exista o mesmo conjunto
de seções em `pt` e `en`. Foi exatamente essa a falha que deixou o deck em inglês
com metade do conteúdo por semanas sem ninguém notar.

---

## ADR 3 — SEO no Bioma, dois níveis

**Contexto.** O Eduardo conectou um MCP de SE Ranking. Na sessão de Claude Code
ele não apareceu (só Semrush e Ahrefs, e o Ahrefs devolve `Insufficient plan`).
Independente da ferramenta, o dado de SEO deve entrar no Bioma pelos mesmos dois
níveis que o resto da plataforma já tem.

**Decisão.** Um só ingestor, dois consumidores.

| Nível | Quem vê | Para quê |
|---|---|---|
| **Cliente** | o cliente, no hub dele | posição, tráfego e saúde técnica do site dele — vira entregável do Retainer, não relatório manual |
| **EG / interno** | só a EG | o próprio `evergreenmkt.com.br`, e a visão comparada da carteira: quem está subindo, quem está caindo, onde o retainer está em risco |

**Por que interessa mais no nível EG do que parece.** O Raio-X Comercial pontua
Oferta, Demanda e Conversão. Posição orgânica e saúde técnica são evidência
direta do pilar **Demanda** — hoje esse pilar é preenchido a olho. Ligar o SEO ao
`raio_x_scores` transforma uma nota subjetiva em número auditável.

**Fornecedor é detalhe de implementação.** A tabela guarda o dado normalizado, com
`provider` como coluna. Trocar SE Ranking por Semrush não deve exigir migração.

```
seo_projects
  id, organization_id (null = a própria EG), domain, provider, external_id
  active, created_at

seo_snapshots
  id, seo_project_id, captured_at
  visibility, organic_keywords, organic_traffic
  health_score, errors, warnings, notices
  UNIQUE (seo_project_id, captured_at)

seo_keywords
  id, seo_project_id, captured_at, keyword, position, volume, url, intent
```

Coleta pelo worker, cadência diária ou semanal. Snapshot é imutável — histórico
é o produto, não efeito colateral.

---

## User stories — SEO

**US-5 · O pilar Demanda deixa de ser palpite**
Como consultor da EG, quero que o Raio-X puxe posição e saúde técnica reais do
site do cliente, para que a nota de Demanda tenha origem auditável.
*Aceite:* ao gerar um Raio-X, o pilar Demanda mostra os números e a data da
coleta; sem coleta, mostra "sem dado" em vez de um número inventado.

**US-6 · A carteira num lugar só**
Como Eduardo, quero ver todos os clientes com SEO monitorado numa tabela, com a
variação desde a última coleta, para saber onde entrar antes do cliente reclamar.
*Aceite:* ordena por queda de visibilidade; clicar abre o histórico do cliente.

**US-7 · A EG se mede pela própria régua**
Como Eduardo, quero o `evergreenmkt.com.br` monitorado como qualquer cliente,
para que a agência não venda o que não pratica.
*Aceite:* aparece na mesma tela, marcado como interno.

**US-8 · Erro técnico vira tarefa**
Como consultor, quero que um erro crítico da auditoria vire item na fila do
cliente, para não depender de alguém abrir o relatório.
*Aceite:* erro novo de severidade alta cria pendência ligada ao cliente.

---

## Ordem sugerida

1. **Cases no Bioma** (US-1, US-2, US-3) — resolve a pendência de autorização, que
   é risco aberto hoje, e mata a triplicação de conteúdo.
2. **Endpoint público + consumo no site** (ADR 2) — o padrão já existe no
   benchmark; é replicar.
3. **Ingestão de SEO nível EG** (US-7) — um domínio só, valida o modelo barato.
4. **Nível cliente e o laço com o Raio-X** (US-5, US-6) — só depois que o pilar
   Demanda estiver decidido.
5. **US-4 e US-8** — conveniência, depois do resto.

## O que trava

- **Qual ferramenta.** SE Ranking não está acessível nesta sessão; Ahrefs está sem
  plano de API; Semrush responde. Decidir antes de escrever o ingestor.
- **O pilar Demanda.** Ligar SEO ao `raio_x_scores` muda como a nota é composta —
  é decisão de método, não de código.
