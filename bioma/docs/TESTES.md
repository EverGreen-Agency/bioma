# Estratégia de testes do Bioma

Escrito em 2026-08-11, a pedido de "implementar TDD com cobertura de 100%".
Este documento existe para responder três coisas: **o que já existe**, **por que
100% é a meta errada**, e **o que fazer em vez disso**.

## O que já existe (medido, não estimado)

| Camada | Quantidade | Cobre |
|---|---|---|
| Testes puros (pytest) | 19 arquivos, 214 testes | regras de borda, sem banco |
| Smokes | 59 scripts | integração real contra Postgres |
| Frontend | 3 arquivos, 16 testes | lógica pura de `src/lib` |

**Cobertura medida:**

- backend, só testes puros: **23%** (14.498 statements)
- backend, incluindo smokes: **não medido ainda** — ver abaixo
- frontend, camada `lib`: **9,4%**

Tamanho do que existe: **35.490 linhas** de Python e **63.103** de TypeScript.

## O número de 21% mente por omissão

`pytest --cov` não enxerga os smokes, porque eles rodam em **subprocessos** (um
por smoke, pelo runner). Cobertura de subprocesso só entra na conta com
`COVERAGE_PROCESS_START` mais o hook de startup do `coverage`.

Isso importa mais do que parece: perseguir os 21% levaria ao pior desfecho
possível — gente escrevendo teste unitário para código que **já tem smoke**, só
para levantar um número que ignorava o smoke.

`scripts/coverage_report.py --smokes` monta a medição correta. Exige Postgres.

## Por que 100% é a meta errada

Não é preguiça, e não é opinião de estilo. É o que a **própria semana desta base
de código** mostrou. Estes bugs foram reais, e nenhum seria pego por cobertura:

| Bug | Por que cobertura não pegaria |
|---|---|
| `claim_next_sync` não devolvia `workspace_id` — **nenhum sync rodava** | a linha era executada; o dicionário é que não tinha a chave |
| superfície apontando feature inexistente — **gate nunca aplicava** | a linha executava e devolvia "liberado" |
| PDF afirmando "campanhas com ROI positivo" | string constante, 100% coberta, e falsa |
| botão de sync dizendo "sucesso" e recarregando tela vazia | o código fazia exatamente o que estava escrito |
| ocultar Vitórias escondia só o botão, não o card | o card renderizava — coberto e errado |

Cobertura mede **linha executada**, não **comportamento verificado**. Dá para
chegar a 100% com testes que não afirmam nada.

E o custo não é linear: os últimos 20% são quase todos ramo de erro e cola de
integração, onde o teste custa mais para escrever e manter do que o bug que
evitaria. Numa base de 98 mil linhas com 2 pessoas, isso é o trabalho de meses
que não entrega funcionalidade nenhuma.

## E "TDD"?

TDD é escrever o teste **antes** do código — vale para código NOVO. Aplicar
retroativamente a 98 mil linhas não é TDD: é **teste de caracterização**, que é
outra coisa e tem um efeito colateral perverso — ele **congela o comportamento
atual, incluindo os bugs**. Se eu tivesse escrito teste de caracterização do
`AiSummaryTab` na semana passada, teria fixado como correto o "IA Insight" que
não tinha IA.

## O que eu faria em vez disso

**1. Medir o número verdadeiro.** `coverage_report.py --smokes`. Sem isso,
qualquer meta é chute.

**2. Piso que sobe, em vez de teto perseguido.** Regra: nenhuma mudança BAIXA a
cobertura. É verificável na CI, não exige parar tudo, e converge sozinho.

**3. TDD de verdade — para o que vier a partir de agora.** Feature nova nasce
com teste primeiro. É exatamente o que o pedido diz ("começar a construir esse
projeto por TDD"), e é a parte viável dele.

**4. Backfill dirigido por incidente.** Todo bug encontrado vira teste ANTES da
correção. Isso já vinha acontecendo informalmente — o smoke de convite ao time
fixa que convite sem papel cria membro, e não admin, porque esse foi o bug.

**5. Frontend: lógica sim, componente com parcimônia.** A maior parte dos bugs
daqui não estava em renderização; estava em regra escrita à mão em três telas.
Isso se testa sem DOM, rápido e sem fragilidade. Teste de componente entra só
onde a regra vive no JSX.

## Front e back — a resposta direta

**Os dois**, com pesos diferentes:

| Camada | Alvo | Ferramenta |
|---|---|---|
| Backend — regra de negócio, permissão, resolução | alto | pytest |
| Backend — integração real | alto | smokes (já existem) |
| Frontend — `src/lib` (lógica pura) | alto | Vitest |
| Frontend — componente | seletivo | Vitest + jsdom |
| Fluxo ponta a ponta | poucos, críticos | Playwright |

## Como rodar

```bash
# backend, testes puros
cd bioma/apps/api && ./.venv/Scripts/python.exe -m pytest -q

# backend, cobertura real (com smokes; exige Postgres)
python scripts/coverage_report.py --smokes

# frontend
cd bioma/apps/web && npm test
npm run test:cov
```

## O que a regra "TDD daqui pra frente" produziu na prática

Decidida em 2026-08-11 e aplicada no mesmo dia a três entregas. O resultado
mensurável:

| Módulo | Escrito | Cobertura |
|---|---|---|
| `bioma_api/cms.py` | teste antes | **96%** |
| `bioma_api/content_quality.py` | teste antes | **96%** |
| média do resto da base | teste depois, ou nunca | 23% |

Código escrito com o teste antes chega perto de coberto **sem ninguém
perseguir cobertura** — o número vira consequência em vez de meta. É o
argumento mais forte a favor da regra, e ele é desta base, não de artigo.

E o teste antes achou coisa que ninguém tinha visto:

- A regra da decisão 13 estava **morta**: nunca recusou uma tarefa sequer.
  Descoberta ao escrever o primeiro teste dela.
- Texto **vazio** pontuava 6 no score SEO, porque "nenhuma imagem tem alt ruim"
  passava no vácuo. Virou o conceito de check que *não se aplica*.
- As reticências do resumo eram somadas **depois** do corte, estourando o
  limite em 3 caracteres.

E uma ressalva honesta, do mesmo dia: **um dos testes que escrevi estava
errado** — reprovava um slug correto. TDD estreita muito a margem de erro, mas
não a fecha: o teste também é código, e escrito com a mesma confiança. Por isso
os testes aqui têm nome em português e asserção óbvia — a revisão humana do
teste é o que fecha essa última brecha.

## O que ainda não foi feito

- A medição com smokes **não foi executada** — o Docker caiu durante a
  configuração. O caminho está montado e não foi provado.
- Não há gate de cobertura na CI.
- Não há teste de componente nem Playwright configurado no fluxo.
