# Pacote para o Juiz - Bioma / Mega Plataforma EG

**Data:** 2026-07-07  
**Preparado por:** Codex  
**Uso:** cole este pacote no inicio da sessao do Juiz, junto com acesso ao repo.  
**Pedido curto ao Juiz:** houve mais uma rodada com outras IAs. Analise o que mudou, corte excesso, valide/rejeite o sequenciamento P0/P0.5/P1 e diga exatamente o que deve ir para engenharia agora.

## 1. Contexto fixo

Eduardo/EG esta criando o **Bioma**, a Mega Plataforma da EverGreen.

Premissas que o Juiz deve preservar:

- A EG e boutique premium, nao agencia 360 comum.
- A EG nao e nichada estruturalmente por mercado; solar e ICP momentaneo.
- O Bioma comeca como ferramenta interna/operacional da EG, depois EG-com-cliente, depois cliente, depois white-label/SaaS.
- `mod-multitenant` e a fundacao e ja comecou producao.
- O Bioma nasce **greenfield**. O `/dashboard` antigo nao dita stack/arquitetura, mas tambem nao deve ser largado: e legado intencional a inventariar, reaproveitar e aposentar formalmente.
- Retencao legitima = suspensao contratual de acesso, nunca backdoor nocivo.
- Nao escrever codigo nesta avaliacao. A saida esperada e decisao/corte/priorizacao.

## 2. Arquivos obrigatorios para o Juiz ler

Leia nesta ordem:

1. `_opensquad/_memory/engenharia/mega-plataforma/HANDOFF.md`
2. `_opensquad/_memory/engenharia/mega-plataforma/roadmap-p0-p1.md`
3. `_opensquad/_memory/engenharia/mega-plataforma/matriz-maturidade-modulos.md`
4. `_opensquad/_memory/engenharia/mega-plataforma/matriz-rastreabilidade-ideias.md`
5. `_opensquad/_memory/engenharia/mega-plataforma/adrs-fase-1-planejados.md`
6. `_opensquad/_memory/banco_ideias/ideas.json`
7. `_opensquad/_memory/banco_arquitetura/arquitetura.md`
8. `_opensquad/_memory/knowledge/inputs-mega-plataforma/Mega-Plataforma-parte-1.md`
9. `_opensquad/_memory/knowledge/inputs-mega-plataforma/Mega-Plataforma-parte-2.md`

Depois, ler os artefatos P0/P0.5:

- `_opensquad/_memory/engenharia/mod-multitenant/spec.md`
- `_opensquad/_memory/engenharia/mod-multitenant/adr/`
- `_opensquad/_memory/engenharia/mod-observabilidade/spec.md`
- `_opensquad/_memory/engenharia/mod-observabilidade/adr/ADR-0001-observabilidade-stack.md`
- `_opensquad/_memory/engenharia/cofre-senhas/spec.md`
- `_opensquad/_memory/engenharia/cofre-senhas/adr/ADR-0001-vault-secrets.md`
- `_opensquad/_memory/engenharia/mod-integrations-hub/spec.md`
- `_opensquad/_memory/engenharia/mod-integrations-hub/adr/ADR-0001-contrato-integracoes.md`
- `_opensquad/_memory/engenharia/mod-workflows-aprovacoes/spec.md`
- `_opensquad/_memory/engenharia/mod-workflows-aprovacoes/adr/ADR-0001-motor-aprovacoes.md`
- `_opensquad/_memory/engenharia/mod-lgpd-governanca-dados/spec.md`
- `_opensquad/_memory/engenharia/mod-lgpd-governanca-dados/adr/ADR-0001-governanca-dados.md`

Depois, ler Fase 1:

- `_opensquad/_memory/engenharia/client-hub/spec.md`
- `_opensquad/_memory/engenharia/mod-bi-dashboards/spec.md`
- `_opensquad/_memory/engenharia/mod-entrega-mkt/spec.md`

## 3. O que mudou nesta ultima rodada

### Banco de Ideias

- `ideas.json` esta valido e possui **141 ideias**.
- Foram adicionadas/mapeadas 6 features sugeridas:
  - `access-request-portal`
  - `evidence-ledger`
  - `integration-doctor`
  - `client-operating-agreement`
  - `exit-handover-mode`
  - `demo-tenant-sales-theater`
- A feature `implementation-readiness-score` **nao** foi criada, por pedido do Eduardo.
- Tres modulos transversais foram formalizados no banco:
  - `mod-integrations-hub`
  - `mod-workflows-aprovacoes`
  - `mod-lgpd-governanca-dados`

### Specs

- As specs nao-multitenant foram elevadas de briefing para **rascunho estrutural completo**.
- Cada spec agora deve ter: objetivo, contexto, escopo, fora de escopo, RF, RNF, criterios de aceite, riscos/dependencias.
- Foram criadas specs para modulos antes soltos/futuros, inclusive:
  - `cofre-senhas`
  - `mod-integrations-hub`
  - `mod-workflows-aprovacoes`
  - `mod-lgpd-governanca-dados`
  - `mod-nucleo`
  - `mod-entrega-mkt`
  - `mod-marca-artefatos`
  - `mod-radar-pesquisa`
  - `mod-juridico`
  - `mod-workspace`
  - `mod-mobile`
  - `mod-conhecimento-video`
  - `mod-certificacoes`
  - `squad-negocios`
  - `mod-policy-research`

### Sequenciamento

- Foi criada a matriz de maturidade: `matriz-maturidade-modulos.md`.
- Foi criado o recorte P0/P0.5/P1: `roadmap-p0-p1.md`.
- Proposta atual:
  - **P0:** `mod-multitenant`
  - **P0.5:** `mod-observabilidade`, `cofre-senhas`, `mod-integrations-hub`, `mod-workflows-aprovacoes`, `mod-lgpd-governanca-dados`
  - **P1:** `client-hub`, `mod-bi-dashboards`, `mod-entrega-mkt`

### ADRs

- Foram adicionados ADRs **propostos**, nao aceitos, para P0.5:
  - observabilidade/logs/status
  - vault/secrets
  - contrato central de integracoes
  - motor HITL/aprovacoes
  - governanca de dados/LGPD/uso de IA
- Foi criado backlog de ADRs da Fase 1: `adrs-fase-1-planejados.md`.

### Codigo ja iniciado

Existe um diretorio untracked `bioma/` com scaffold/producao inicial:

- Next.js + React + TypeScript.
- Supabase config/migration/seed.
- Drizzle/Postgres.
- BullMQ/Redis nas dependencias.
- Testes de RLS em `bioma/tests/rls/isolation.test.ts`.
- Testes unitarios de crypto em `bioma/tests/unit/crypto.test.ts`.
- `src/app/page.tsx` ainda parece tela default de create-next-app.

O Juiz deve tratar `bioma/` como **producao iniciada**, mas precisa verificar se o codigo esta alinhado com specs/ADRs antes de qualquer expansao.

## 4. Perguntas objetivas para o Juiz

Responda diretamente:

1. **O recorte P0/P0.5/P1 esta correto?**  
   Se nao, corte ou reordene.

2. **P0.5 deve existir antes de `client-hub`/BI?**  
   Avalie se `observabilidade`, `cofre`, `integrations hub`, `aprovações`, `LGPD` sao realmente guardrails ou se algum deve descer de prioridade.

3. **Quais ADRs P0.5 podem ser aceitos como estao, quais precisam revisao e quais devem ser descartados?**

4. **Quais specs ainda estao perigosas para engenharia?**  
   Procure escopo inchado, dependencia circular, falta de critério de aceite, ou promessa de produto cedo demais.

5. **O que deve ir para engenharia agora, exatamente?**  
   Maximo recomendado: 1 a 3 itens.

6. **O que deve ser congelado?**  
   Identifique modulos/features que devem ficar apenas no banco de ideias por enquanto.

7. **O codigo em `bioma/` parece alinhado ao plano?**  
   Se nao conseguir avaliar codigo, diga explicitamente o que precisa ser revisado pelo Engenheiro.

8. **Ha conflito entre documentos?**  
   Especialmente entre `HANDOFF.md`, `PLANO-MESTRE.md`, specs, ADRs e `ideas.json`.

## 5. Formato de saida esperado do Juiz

Use este formato:

```md
# Veredito do Juiz - Bioma

## 1. Decisoes
- ACEITAR:
- REVISAR:
- DESCARTAR:
- CONGELAR:

## 2. Sequenciamento aprovado
P0:
P0.5:
P1:
Depois:

## 3. ADRs
Aceitos:
Revisar antes de aceitar:
Novos ADRs obrigatorios:

## 4. Specs
Prontas para tasks/scaffold:
Precisam revisao:
Futuras/congeladas:

## 5. Engenharia
Proximo trabalho de engenharia permitido:
Nao codar ainda:

## 6. Riscos criticos
- Risco:
  - Evidencia:
  - Correcao:

## 7. Conflitos ou inconsistencias
- Arquivo/trecho:
  - Problema:
  - Decisao recomendada:
```

## 6. Rubrica de avaliacao

Pontue de 1 a 5:

- Aderencia a estrategia EG/boutique premium.
- Pragmatismo financeiro e operacional.
- Sequenciamento realista.
- Risco tecnico.
- Risco juridico/LGPD.
- Clareza de fronteira interno -> cliente -> white-label.
- Capacidade de evitar overengineering.
- Capacidade de preservar moat sem virar agencia 360.

## 7. Regras para o Juiz

- Nao criar novas features salvo se forem bloqueadores criticos.
- Nao escrever codigo.
- Nao tratar "spec rascunho completa" como aprovada.
- Nao aceitar ADR com afirmacao de preco/regiao/provedor atual sem fonte oficial.
- Distinguir claramente: decisao aceita, proposta, backlog e congelado.
- Priorizar corte e ordem, nao volume de documento.

## 8. Minha sugestao ao Juiz

O risco principal agora nao e faltar modulo. E excesso de superficie.  
Minha recomendacao inicial para o Juiz validar ou derrubar:

1. Manter `mod-multitenant` como unica frente de codigo principal.
2. Aprovar P0.5 como guardrail, mas talvez executar em fatias minimas:
   - observabilidade basica,
   - cofre minimo,
   - contrato de integracoes,
   - approval request simples,
   - classificacao de dados minima.
3. Nao abrir codigo de `client-hub`/BI antes de pelo menos cofre + integracoes + observabilidade terem contrato aprovado.
4. Congelar workspace, mobile, certificacoes, conhecimento-video, juridico completo, RH amplo e jogo/office virtual.
5. Usar `demo-tenant-sales-theater` como acelerador comercial, mas so depois do Hub ter primeira tela real.

