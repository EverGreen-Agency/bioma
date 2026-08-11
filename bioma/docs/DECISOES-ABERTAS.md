# Decisões abertas — Bioma

Atualizado em 2026-08-08.

Cada bloco tem **contexto**, **opções**, **minha recomendação** e uma linha
`RESPOSTA:` para você preencher. O que estiver respondido eu implemento sem
voltar a perguntar; o que ficar em branco continua parado.

Decisão respondida sai daqui e vira comentário no código, que é onde alguém a
encontra quando importa. O histórico fica no git. Este arquivo é só o que ainda
trava — se ele encolhe, é sinal bom.

**Regra de manutenção:** decisão IMPLEMENTADA desce para "Fechadas" com uma
linha do que ficou valendo, no mesmo commit que a implementa. Deixá-la no corpo
faz o arquivo parecer maior do que o trabalho realmente aberto — foi o que
aconteceu com as decisões 8 e 11, movidas em 2026-08-08.

---

## 1. Campos do Radar Local

**Contexto.** Hoje o prospect guarda: nome, endereço, telefone, site, URL do
Maps, nota, número de avaliações, `presence_score`, `presence_gaps`, e o diff
contra o scan anterior (`changes`).

**Minha lista de lacunas** (palpite meu, você é quem sabe):

- **segmento/subnicho** — "clínica odontológica" é o termo da busca, não o que o
  negócio é; hoje isso se perde
- **ticket estimado** — muda quem vale abordar
- **já é atendido por concorrente** — muda o argumento inteiro
- **observação da call** — campo livre, para o que você aprendeu falando com eles
- **origem do contato** — indicação vs. frio muda a taxa de resposta

`RESPOSTA (quais campos faltam de verdade):`

---

## 2. Idioma e tradução

**Contexto.** Você prospecta em plataformas gringas e pode ter cliente
estrangeiro. Hoje o Bioma é 100% pt-BR: interface, e-mails, propostas públicas e
as respostas do copiloto.

São **três problemas diferentes**, e tratá-los como um só é o erro comum:

| Camada | O que é | Custo |
|---|---|---|
| **A. Interface** | rótulos, botões, mensagens de erro | ~2.000 strings hoje espalhadas em JSX; extrair é o trabalho, traduzir é barato |
| **B. Conteúdo gerado** | proposta, briefing, resposta do copiloto | quase de graça: é um parâmetro no prompt |
| **C. Conteúdo do cliente** | nome de tarefa, comentário, entrega | ninguém deveria traduzir automaticamente — muda o que a pessoa escreveu |

**Recomendo fazer B agora e A depois**, nesta ordem, por um motivo prático: B
resolve o caso que você tem hoje (proposta para cliente gringo, mensagem de
prospecção em inglês) com um campo de idioma no workspace e uma linha no prompt.
A é semanas de trabalho mecânico que só paga quando existir um usuário
estrangeiro logado no Bioma — e hoje não existe. C não deve ser feito nunca de
forma automática; no máximo um botão "traduzir" sob demanda, que deixa claro que
o original é o original.

Para A, quando for a hora: `react-i18next` é o padrão, e a migração pode ser
incremental (arquivo por arquivo) sem parar o resto.

`RESPOSTA (fazer só B agora? incluir A? quais idiomas?):` Cara, faça o B agora, mas tem uma questão, teria como ter o conteúdo geral no idioma origianal (supondo que seja para um lead americano, logo em inglês) e em português (para nossa equipe)? Só que sem precisar gerar dois materiais? tipo, dentro da nossa plataforma, só um botão de troca de idioma ou algo similar ao google tradutor automático que tem em todos sites. E o A deixe para depois para não consumir muita cota agora.

**Resposta (2026-08-04).** Dá, e o desenho certo não é "gerar dois materiais" —
é **um artefato, um idioma canônico, traduções em cache**.

O material nasce num idioma só: o do destinatário. Inglês, se o lead é
americano. Esse é o **original**, e é ele que sai pelo link público — o cliente
nunca vê tradução.

Para a equipe, um botão "ver em português" na tela interna. Na primeira vez ele
traduz e **guarda**; da segunda em diante é leitura de banco, custo zero. Como
proposta muda pouco depois de enviada, na prática você paga uma tradução por
proposta, não uma por visualização.

Três coisas que precisam ficar explícitas na tela, e é onde o "Google Tradutor
automático" erra:

- **a tradução é marcada como tradução**, com o idioma original ao lado. Uma
  cláusula comercial lida em tradução e assumida como original é o tipo de erro
  que aparece na renegociação;
- **editar só vale no original.** Se alguém corrige um valor na versão traduzida,
  ou a correção se perde ou o original passa a mentir. Tradução é somente
  leitura, e editar o original invalida o cache;
- **o widget do Google traduz a interface junto** e mistura rótulo do sistema com
  conteúdo. Aqui é o inverso: traduz só o conteúdo, e a interface (item A) fica
  para depois, como você pediu.

Custo: usa a mesma cota da assinatura pelo plano de roteamento. Não é chamada
nova de provedor.

---

## 3. Follow-up ativo — formato do resumo diário

**Contexto.** Você aprovou o resumo diário único (sem push por evento). Falta
decidir o **canal** e o **horário**, que mudam a implementação:

| Opção | Como é | Implicação |
|---|---|---|
| **A. Dentro do Bioma** | card no cockpit ao abrir | zero infra nova; só vê quem entrar |
| B. WhatsApp | usa o provedor que já existe | precisa do seu número cadastrado e de opt-out |
| C. E-mail | resumo às 8h | precisa de provedor de e-mail transacional (não temos) |

**Recomendo A para começar** — funciona amanhã e não depende de infra nova. B é
o passo natural depois, porque o canal já existe no Bioma.

`RESPOSTA (canal e horário):` Opção A, como recomendou.

---

## 4. Custo de IA — preço vem de onde

**Contexto.** Você perguntou se não existe endpoint para puxar preço de modelo.

A resposta separada em duas partes, porque são coisas diferentes:

- **Preço por token: não existe API pública.** OpenAI, Anthropic e Google
  publicam preço em página web, não em endpoint versionado. Qualquer coisa que
  "puxe preço automaticamente" estaria raspando uma página de marketing — que
  muda de layout sem aviso e quebraria calado, gravando custo errado no banco.
  Por isso a tabela está em `bioma_api/model_pricing.py`, versionada em git: o
  histórico de preço fica auditável junto com o código, e atualizar é um commit
  de uma linha.

- **Gasto real: existe, sim.** A OpenAI tem a Costs API
  (`GET https://api.openai.com/v1/organization/costs`), que devolve o gasto
  diário — o número da fatura, não uma conta nossa. Duas pegadinhas: exige uma
  **chave de admin da organização**, diferente da chave de projeto que o Bioma
  usa hoje; e só um **Organization Owner** consegue criar essa chave.
  ([referência da API](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs),
  [cookbook](https://developers.openai.com/cookbook/examples/completions_usage_api),
  verificado em 2026-08-02)

Isso abre uma terceira opção melhor que as duas anteriores:

| Opção | Como é |
|---|---|
| A. Manter como está | preço em código; modelo desconhecido fica sem custo |
| B. Estimar pela família | número aproximado, marcado como tal |
| **C. Reconciliar com a fatura** | mantém A **e** puxa o gasto real da Usage API, mostrando os dois lado a lado |

**Recomendo C**, mas em duas etapas: A já está no ar e funciona; C entra quando
você gerar a chave de admin. O valor de C não é o custo por execução — é
descobrir que a soma do que o Bioma achou que gastou não bate com a fatura, que
é exatamente o erro que ninguém percebe sozinho.

`RESPOSTA (fico em A por enquanto, ou já quer C?):`Podemos ir para C porém uma coisa, esqueci mas não estamos usando o cobrança por subscrição/cota das assinaturas? Então basicaemnte não seria ver nossa assintatura, quantidade usada da cota por requisição e calcular a combase no que pagamos de assinatura?

**Resposta (2026-08-04).** Você está certo, e isso derruba a premissa das três
opções acima. Elas assumiam cobrança por token, que é o modelo da chave de API.
Com assinatura, **o token não custa nada na margem** — você já pagou o mês. O
que custa é a **cota**, que é finita e não acumula.

Então a pergunta certa não é "quanto essa execução custou", é **"quanto dessa
cota essa execução consumiu, e quanto sobrou até o reset"**. São coisas
diferentes: a primeira é contabilidade, a segunda é operação. Estourar a cota na
terça-feira para pela metade da semana; um relatório de custo não avisa isso.

O modelo certo, então:

| Camada | O quê |
|---|---|
| **Custo de referência** | `preço da assinatura ÷ cota do período` = quanto vale uma unidade. Serve para comparar execuções entre si e responder "vale a pena rodar isso 200 vezes?" |
| **Cota restante** | o número que importa no dia a dia — quanto sobrou e quando reseta |
| **Chave de API** | só aí o custo é dinheiro de verdade, e a tabela de preços vale |

Duas coisas que a infraestrutura já tem e ninguém está usando:
`ai_provider_subscriptions` (com o valor pago) e `ai_quota_buckets` (com
`remaining_percent` e `resets_at`, alimentado por `quota_collectors.py`).

O que falta é ligar: registrar as unidades consumidas por execução no bucket, e
derivar o custo de referência. Com isso o painel deixa de mostrar "US$ 0,0032" —
que é ficção quando a cobrança é assinatura — e passa a mostrar "3% da cota
semanal do Claude Code, reseta quinta".

**Implementado em 2026-08-04.** `copilot_runs` liga cada execução à conta que
respondeu; a trilha lê a cota ATUAL dessa conta (`ai_quota_buckets`, que já
integra com o contrato oficial `account/rateLimits/read` do Codex — reportado
pelo próprio provedor, não estimativa). `/copilot/usage` mostra `routed_runs` e
`routed_accounts` com a cota de cada uma. Não implementei o "custo de
referência" (preço da assinatura ÷ cota do período) que eu tinha sugerido: sem
um número confiável de unidades-por-dólar publicado pelo provedor, seria outro
número inventado — melhor mostrar a cota real, que existe de verdade, do que
uma conversão para dólar que não existe. A Costs API da OpenAI (opção C)
continua valendo só para o que roda por chave de API, não por assinatura.

De quebra, achei e corrigi um bug: execução roteada por assinatura podia
ganhar um custo em dólar FALSO quando o `model_id` da conta coincidia por acaso
com um nome precificado na tabela. Corrigido — execução de assinatura nunca
aplica preço por token.

Falta só você registrar as contas (Operação EG → IA) para isso ganhar vida —
hoje `ai_provider_accounts` está vazia, então o painel não mostra nada ainda.

---

## 5. Memória e alma do agente — escopo e personalização

**Contexto.** Sua pergunta: como a memória (`memory.md`) e a identidade
(`soul.md`) do agente são gerenciadas, e como ele se comporta por
local/workspace/cliente e por usuário.

**O que já existe hoje** (tabela `agent_memories`, migração 0070):

- **Memória global** (`workspace_id = NULL`) — vale em toda a EG. É o mais
  próximo de `soul.md`: tom de voz, princípios, o que nunca fazer.
- **Memória de workspace** — vale só naquele cliente. "A Univet prefere reunião
  na sexta" não deve vazar para outro cliente, e não vaza (tem smoke provando).
- **Toda escrita gera revisão** (`agent_memory_revisions`) — dá para ver o que
  mudou e quando.
- **Habilidades** (`agent_skills`) — procedimento aprendido, com o mesmo escopo,
  e que **só entra em uso depois de aprovação humana**.

**O que NÃO existe, e é a sua pergunta de verdade: memória por usuário.** Hoje a
memória é da EG e do cliente, nunca sua. Se você e outra pessoa da EG usarem o
copiloto, os dois recebem o mesmo dossiê.

| Opção | Como é | A favor | Contra |
|---|---|---|---|
| **A. Três escopos: global + workspace + usuário** | acrescenta `user_id` na memória | ele aprende seu jeito sem impor aos outros | uma pessoa pode "ensinar errado" e ninguém vê |
| B. Manter dois escopos | como está | tudo é auditável por todos | ele nunca personaliza para você |
| C. Escopo de usuário só para preferência | fato e diretriz continuam coletivos | separa "como falar comigo" de "o que é verdade" | mais um conceito para entender |

**Recomendo C.** A distinção que importa não é quem escreveu, é **o que é
preferência e o que é fato**. "Prefiro resposta curta, sem introdução" é seu.
"O contrato da Univet vence em março" é da EG, e não pode depender de quem
perguntou. C dá personalização sem fragmentar a verdade.

Sobre `soul.md`: hoje a identidade está em código (as instruções do modelo, em
`bioma_worker/copilot.py`). Movê-la para memória global editável te deixaria
ajustar o tom sem deploy — mas também deixaria alguém quebrar o copiloto por
acidente. Recomendo **manter em código** e usar memória global para o que é
ajuste fino.

`RESPOSTA (escopo de memória, e soul.md em código ou editável?):`pode manter o soul em código por enquanto. E o escopo da memória, não entendi bem a diferença de A para C. Acho interessante saber o que cada usuário fez com o copiloto também, mas acho que independente dessas opções, é rastreável.

**Resposta (2026-08-04).** A diferença é **o que pode ser privado**, e o exemplo
deixa claro. Suponha que você diga ao copiloto: *"a Univet vence o contrato em
março, e me responda sempre sem introdução"*. São duas coisas numa frase.

**Opção A — escopo por usuário, sem distinção.** As duas viram memória sua. O
copiloto passa a responder curto **para você** (certo) e a saber do vencimento
**só quando você pergunta** (errado). Outra pessoa da EG abre a mesma tela e o
copiloto não sabe do contrato. Um fato da empresa virou segredo pessoal por
acidente — porque quem digitou foi você.

**Opção C — separa por natureza.** "Responda sem introdução" é preferência e
fica sua. "A Univet vence em março" é fato e vai para a memória do workspace,
que todo mundo enxerga. O critério não é **quem escreveu**, é **o que é**.

Concordo com sua observação de que rastreabilidade é ortogonal: a trilha já
registra quem rodou o quê, com qual memória, em `copilot_runs` — e isso vale nas
duas opções. Não é argumento para nenhuma.

Fica **C**, então, salvo objeção sua. Implicação prática: a memória ganha um
campo de escopo pessoal, e o copiloto classifica ao gravar — com você podendo
corrigir a classificação, porque ele vai errar às vezes.

**Implementado em 2026-08-04.** `agent_memories` ganhou `owner_user_id`
(banco recusa em qualquer categoria que não seja `preference` — não confia só
no código). O dossiê de cada pessoa traz fato/diretriz sempre, e preferência só
a dela; a listagem administrativa continua mostrando tudo, com selo de quem é
o dono — rastreabilidade não é a mesma coisa que vazar no dossiê de outra
pessoa. Tem botão pra corrigir a classificação quando o copiloto errar.

---

## 6. Nome do repositório

**Contexto.** Você concordou em renomear depois da faxina, e observou que ao
renomear a pasta local seus chats e copilots perdem o contexto.

**Faxina feita em 2026-08-05** (Opensquad apagado) — só falta o nome e a ordem
**pasta local → remoto**.

`RESPOSTA (nome final):`

---

## 7. Context Engine — por onde começar

**Contexto.** `EG_CONTEXT_ENGINE_FEATURE_HANDOFF.md` define a feature inteira em
4 fases. Não comecei porque construir metade dela é pior que não começar: uma
base de conhecimento que responde sem citar direito, ou que vaza entre
organizações, destrói a confiança em tudo que ela devolver depois.

**O que o Bioma já tem, e que encurta bastante a Fase 1:**

| Peça do contrato | O que já existe |
|---|---|
| object storage | `services/storage.py` (S3, configurado na Railway) |
| extração de texto | `attachment_text.py` — txt, md, csv, json, PDF via pypdf |
| índice lexical | Postgres full-text, nativo |
| ledger de runs | o padrão de `copilot_runs` (etapas, tokens, duração, fontes) |
| tenancy | `organization_id`/`workspace_id` em todo o esquema |
| adaptadores de modelo | plano de roteamento com cota de assinatura |

Falta, de verdade: `knowledge_bases` / `documents` / `versions` / `chunks`, o
chunking que respeita estrutura, a busca com citação que abre na origem, e a
tela de inspeção de fragmentos.

**O corte vertical que proponho** (Fase 1 do handoff, sem Fase 2-4):

1. criar base → 2. enviar Markdown/PDF → 3. extrair e fragmentar → 4. inspecionar
e desativar fragmento → 5. buscar por texto → 6. abrir a citação na origem →
7. run registrado.

Sem embeddings, sem persona, sem reranker — e a API já devolvendo
`modeActuallyUsed: "lexical"` com `capabilities.dense: "unavailable"`, para a
Fase 3 entrar sem quebrar contrato e sem ninguém achar que houve busca híbrida.

**A pergunta que trava:** a primeira base é do **cliente** (documentos da Univet,
consultáveis no hub dela) ou da **EG** (políticas, processos, contratos-modelo)?
Muda quem enxerga por padrão, e a decisão errada aqui é cara de desfazer.

`RESPOSTA (começar pela base da EG ou do cliente?):`

---

## 9. GitHub ↔ Tech — fechar o loop

**Contexto.** Sua pergunta em 2026-08-05: "o Tech está integrado
bidirecionalmente com o GitHub?". Está, mas as duas pontas são **manuais
(pull)**, e o ciclo não fecha:

- **Bioma → GitHub**: cria issue a partir de uma entrega, idempotente via
  marcador `[Bioma:<deliverable_id>]`. Funciona.
- **GitHub → Bioma**: lê commits/PRs/issues sob demanda e publica como
  atualização do projeto. Funciona, mas alguém tem que clicar.

**Os três gaps:**

1. **Sem webhook** — nada é tempo real.
2. **O estado da issue não volta.** Fechar a issue no GitHub **não** conclui a
   entrega no Bioma. Grava-se `github_issue_number` na criação e acabou. É o
   que mais dói: as duas pontas divergem em silêncio.
3. **PR não se liga a entrega** — só issue. PR mergeado não marca nada.

**A decisão que trava o item 2:** issue fechada deve **concluir a entrega
automaticamente**, ou apenas **sugerir** a conclusão para alguém confirmar?
Automático é o que o time espera de uma integração; sugerir respeita a regra
de que concluir entrega tem aceite separado (que hoje existe de propósito).
Minha recomendação: **sugerir** — vira item em "Precisa de você" no cockpit,
não conclusão silenciosa, porque "entrega concluída" tem efeito contratual.

`RESPOSTA (issue fechada conclui a entrega ou sugere?):` Acho melhor sugerir. Mas tem um ponto, quero saber se, na lista de tarefa, tem algum campo que já link o repositório. Ou o repo fica linkado ao projeto (que este tem campo na lista de tarefas)? E como está essa distinção para a EG? Por exemplo uma tarefa de tech na EG, como vou distinguir projeto e repo? Isso que eu perguntei anteriormente, de como que ficou definido essa distinção de projetos internos e empresas (problema de Notorius)

**Resposta (2026-08-06).** Fica **sugerir** — implemento assim.

Sobre repo × projeto × tarefa, a cadeia hoje é:

```text
tarefa --(project_id)--> projeto --(1:1)--> repositório
```

- **A tarefa NÃO tem campo de repositório.** Ela tem `project_id` (em
  `TaskBase`), e é por aí que chega ao repo.
- **O repo é ligado ao PROJETO, e é 1:1**: `project_github_connections.project_id`
  é `unique` (migração 0028). Um projeto tem no máximo um repositório.
- Só projeto `tech` aceita repositório — o serviço recusa os outros.

**Na prática, para uma tarefa de tech da EG:** crie um projeto interno (ex.:
"Bioma"), ligue o repositório a ele, e as tarefas apontam para esse projeto.
O repo vem por herança; você nunca escolhe repo na tarefa.

**A distinção EG × Notorious não é resolvida por este campo** — é a decisão nº
10. Projeto pertence a um workspace; workspace pertence a uma organização.
Enquanto a Notorious for um workspace dentro da EG, os projetos dela ficam sob
a EG e aparecem no mesmo financeiro. É exatamente o que o multi-tenant separa.
A mecânica de repo funciona igual nos dois casos — o que muda é de quem é o
projeto.

**Limite conhecido:** 1 repo por projeto. Se um projeto precisar de dois
repositórios (front e back separados, por exemplo), hoje precisa virar dois
projetos. Não mudei isso porque não sei se acontece na EG — se acontecer, me
diga que a alteração é pequena.

---

## 10. Onde mora o que não é cliente: Notorious, holdings e white label

**Contexto.** Suas perguntas em 2026-08-06: onde ficam as tarefas de uma
empresa sua que não é a EG (Notorious)? Cliente holding com várias frentes é um
workspace ou vários? Isso já é a estrutura de multi-tenant do white label?

**O que a estrutura já suporta.** `organizations` tem
`parent_organization_id` — já é hierárquica. `workspaces` é onde o trabalho
acontece; `clients` é o registro comercial. Hoje existe **um tenant só** (a
EG), e todo cliente é organização filha dela. Vários pontos do código assumem
isso (o `mcp_server.py` documenta a suposição explicitamente).

**Os três casos, e por que dois deles são o mesmo problema:**

| Caso | Resposta | Critério |
|---|---|---|
| **Notorious** (fonte de renda sua) | organização **irmã** da EG, não filha | tem P&L próprio? Se você quer faturamento/custo separados, misturar destrói o significado do cockpit e do financeiro |
| **Cliente holding** | **uma organização, vários workspaces** | onde está o contrato. Um contrato = uma organização. Contratos separados por frente = organizações sob a holding |
| **White label** | outra agência vira **tenant**, com clientes filhos | é o caso Notorious generalizado |

Notorious e white label são **o mesmo trabalho**: tornar o tenant um eixo real,
hoje fixado na EG. Resolver um resolve o outro. Spec: `mod-multitenant` (no
seed de engenharia).

**Recomendação: não forçar agora.** Rodar a Notorious como workspace dentro da
EG, sabendo que é temporário, e tratar multi-tenant como o projeto que é. O
erro caro seria construir meia estrutura de tenant e ter que desfazer.

**Consequência para a memória do agente** (não é item separado): a memória
global hoje é `workspace_id = NULL` = "vale para toda a EG". Se a Notorious
virar tenant, essa camada precisa passar a ser **por tenant** — senão o tom de
voz e as diretivas da EG vazariam para a outra empresa. As outras duas camadas
(workspace e pessoal) já estão corretas e não mudam.

`RESPOSTA (a Notorious tem P&L próprio? isso decide irmã vs. workspace):` vai virar workspace no momento.

---

## 12. Mais LLMs como motor (OpenRouter e chaves diretas)

**Contexto.** Sua pergunta em 2026-08-06: dá para implementar mais LLMs como
motor? Traz a qualidade e as features esperadas? Pensando em chave de API
direta e agregadores tipo OpenRouter.

**O que o Bioma já tem, e por que isso é mais barato do que parece.** O plano
de roteamento (migração 0064) já separa os eixos certos:

- `provider` — hoje restrito a `openai`, `anthropic`, `google` (**único ponto
  que exige migração**);
- `channel` — **texto livre**, não precisa de migração;
- `auth_mode` — já aceita `api_key`;
- `execution_mode` — já aceita `sdk` e `api`.

E o despacho em `ai_providers.execute_candidate` é um `if/elif` por canal. Ou
seja: **um provedor novo é um executor + um `elif` + uma linha de migração.**

**OpenRouter especificamente** ([docs](https://openrouter.ai/docs/faq)): API
compatível com OpenAI, 300+ modelos, uma chave só, e normaliza *tool calling* e
*structured outputs* entre provedores — que é justamente onde cada API diverge
e onde estaria o trabalho chato. Preço é repasse do provedor + margem da
plataforma.

**A parte que muda de natureza, e que importa mais que o código:** hoje o
roteamento é por **cota de assinatura** (Codex, Claude Code — você já pagou o
mês, o token não custa na margem). OpenRouter é **por token, dinheiro de
verdade**. Não dá para tratar os dois com a mesma régua:

- conta de assinatura → mostra cota restante e reset (o que já existe);
- conta OpenRouter → mostra custo em dólar (a tabela `model_pricing.py` e o
  caminho de `cost_cents` já existem, e a correção de 2026-08-04 garante que
  execução de assinatura nunca ganha preço inventado).

O valor real não é "ter mais modelos" — é ter **fallback quando a cota acaba**.
Estourar a cota do Codex na terça hoje para o copiloto pela metade da semana;
com OpenRouter cadastrado, o roteamento cai para ele e o trabalho continua, ao
custo de alguns centavos. Essa é a razão para fazer, e ela deveria guiar a
política de roteamento: **assinatura primeiro, chave paga como rede**.

**Sobre "traz a qualidade esperada":** o gargalo do copiloto hoje não é o
modelo — é que `ai_provider_accounts` está **vazia**, então nada roteia e tudo
cai em prévia local ou chave avulsa. Trocar de modelo não resolve isso.
Recomendo cadastrar as contas que você já paga antes de acrescentar provedor
novo, para medir de onde vem a insatisfação.

**Esforço estimado:** migração de uma linha, executor (~40 linhas, API
compatível com OpenAI), um `elif`, e a opção no painel de IA. Meio dia.

`RESPOSTA (cadastrar as contas atuais primeiro, ou já implementar OpenRouter junto?):` Tipo, tava pensando também, o que poderiamos tornar herness. Tipo, o curador de memória/soul (estilo hermes agent) fica em um modelo, dai tool calling fica em outro, auditar quais issus devem surgir no git e quais correspondem as tarefas é outro modelo... ou acha que isso pioraria a qualidade?
E não entendi sua pergunta. Mas prefiro implementar novos modelos pois parece que não está funcionando o sistema de uso das cotas/auth do claude e chatgpt. E todo modelo que formos implementar, tem que trazer documentação nova?

---

## 13. Tarefa ligada a projeto, e disciplina como estrutura (não filtro)

Levantado pelo Eduardo em 2026-08-08, e ele está certo em dois pontos que eu
tinha respondido errado antes. São **dois problemas distintos** que vieram
juntos na conversa; separá-los é o que torna os dois resolvíveis.

### Problema A — disciplina não é filtro, é vocabulário

Eu disse que Growth/Tech eram "só um filtro". Não são. Cada frente tem o
**próprio conjunto de status** (`lib/task-frentes.ts`), e o mesmo nome muda de
significado entre elas:

| Status | Growth | Tech |
|---|---|---|
| `Backlog` | **ACTIVE** | **NOT_STARTED** |

Growth vai de Brain a Finalizado; Tech tem `To Do (Sprint)`, `Code review`,
`QA / testes`, `Pronto p/ release`, `Implantado`; Social tem `Roteirização`,
`Aprovação cliente`, `Publicado`. São vocabulários operacionais diferentes, não
rótulos.

Consequência, que é o que o Eduardo chamou de "de-para": a aba **Todas as
disciplinas** não é a matriz nem a visão canônica. Ela agrupa por
`group_status`, então funciona — mas coloca lado a lado dois cards escritos
`Backlog` em colunas diferentes, e quem lê não tem como saber por quê. A visão
combinada é uma tradução, e hoje ela não se anuncia como tal.

### Problema B — tarefa sem projeto perde o contexto

A proposta: tarefa se liga a projeto, e as abas de disciplina só se destravam
quando existe projeto no workspace (com mensagem dizendo "crie um projeto para
vincular").

O argumento não é organização — é **contexto acumulado**. Projeto como o nó que
amarra comunicação (WhatsApp, e-mail), planejamento, documento, proposta e
artefato. Isso alimenta, nesta ordem de valor:

1. o copiloto saber o que já aconteceu naquele projeto;
2. o benchmark da EG (o que funcionou, em que tipo de projeto);
3. a identificação de gaps quando se procura projeto ou vaga;
4. a geração de conteúdo — nossa e do cliente — com contexto real.

### Onde eu concordo

- **Disciplina é estrutural.** A aba combinada precisa se declarar como
  tradução, ou some.
- **Ligar tarefa a projeto vale.** E vale AGORA: cada tarefa e artefato que
  nasce sem `project_id` é histórico órfão que fica caro de retrofitar. Os
  artefatos (0089) já carregam `thread_id`/`run_id`; dar-lhes `project_id`
  fecha metade do desenho.

### Onde eu faria diferente

**Destravar a aba ≠ tornar o vínculo obrigatório.** São coisas diferentes, e a
segunda quebra um caso real: a Operação EG tem demanda interna legítima sem
projeto — treinamento, hackathon, social da casa. Forçar projeto ali obrigaria
a inventar um projeto "diversos", que é pior que o vínculo nulo porque polui o
contexto que a mudança existe para melhorar.

O próprio Eduardo disse: *"não estou falando que tem que prender tudo e tornar
chumbado o sistema"*. Então a regra que eu proporia:

| Workspace | Vínculo com projeto |
|---|---|
| **Cliente** | obrigatório — toda tarefa pertence a um projeto contratado |
| **Operação EG** | opcional — demanda interna existe sem projeto |

Isso entrega o contexto onde ele importa (cliente, benchmark, conteúdo) sem
engessar a casa.

`RESPOSTA (vínculo obrigatório só em cliente, ou em todos os workspaces?):` Só para cliente.

`RESPOSTA (a aba combinada some, ou fica declarada como tradução?):` Fica declarada como tradução.

**Concordo.** Sumir com ela custaria a única visão de "tudo que está aberto
neste cliente", que é o que se quer no início do dia. O problema nunca foi a
existência da aba — foi ela se apresentar como matriz. Declarada, ela vira o
que sempre deveria ter sido: um panorama que avisa que os nomes de status
pertencem a vocabulários diferentes, e que a coluna vem de `group_status`, não
do nome.

---

## Fechadas — implementadas, não precisam voltar

- **8. Estúdio IA como artefatos do copiloto** — implementado em 2026-08-08
  (migração 0089). Estendeu a tabela `artifacts` que já existia em vez de criar
  outra; procedência (`thread_id`/`run_id`) deduzida no servidor; versão nunca
  sobrescreve; `/artifacts/from-run/{id}` salva a resposta do copiloto e, com
  `artifact_id`, vira a próxima versão. Proposta e briefing ficaram nas casas
  próprias. Estúdio virou a vista; o formulário virou "Geração direta".
- **11. Ocultar módulos que a EG não usa** — implementado em 2026-08-06
  (migração 0086), com os 4 níveis: organização, equipe, usuário e preferência.
  "Preferência nunca concede" virou `check (hidden)` no banco. `allowed` e
  `visible` são campos separados, e é isso que faz esconder não quebrar link
  salvo. Papel `eg_member` (0090) veio depois, para convite ao time deixar de
  criar administrador sempre.

- **S3**: já configurado na Railway. Os 2 binários (`Manual de Marca.pdf`,
  `Proposta_EverGreen_HM_Conexoes_Poderosas_v3.pdf`) foram enviados por você.
  **Faltava só anexá-los pela tela do Wiki EG** (upload direto no S3 não
  registra `storage_key` no Postgres — quem cria essa referência é a própria
  rota de anexo). `_opensquad/`, `squads/`, `skills/` e `scratch/` foram
  apagados em 2026-08-05, junto com o comando `/opensquad` (que existia
  triplicado em `.agent/`, `.agents/` e `.claude/`) e o config do Playwright
  MCP, que apontava para dentro de `_opensquad/` e foi movido para
  `infra/mcp/playwright.config.json`.
- **Painel do copiloto**: painel lateral colapsável + `Ctrl+K`, conversa
  acompanha a troca de tela, fechado no primeiro acesso e depois lembra o
  estado. Implementado.
- **Follow-up**: resumo diário único, sem push por evento. (Canal na decisão 3.)
- **Score de fit**: removido. Nulo até "Avaliar com IA".
- **Inventário de gaps**: Tech Radar + inventário comercial + projetos
  concluídos, cada item com sua evidência.
- **Ações do copiloto**: reversível executa com dica de desfazer; visível ao
  cliente sempre pede confirmação.
- **Busca na web**: permitida, sempre com fonte — inclusive quando o dado é do
  Bioma (cita tabela/tela).
- **Escopo do copiloto**: só EG.
- **Skill proposta pelo agente**: só vale depois de aprovação humana.
- **Flexibilidade**: configuração sim, composição sim, definição não.
- **Guia de integração**: virou modal; o "PDF" quebrado (que imprimia a
  aplicação inteira) foi removido.
- **Memória por natureza**: preferência é pessoal, fato/diretriz são
  compartilhados. Corrigível quando o copiloto classificar errado.
- **Custo por cota**: execução roteada por assinatura mostra a cota real da
  conta, nunca preço por token inventado. Falta cadastrar as contas para
  ganhar vida.
