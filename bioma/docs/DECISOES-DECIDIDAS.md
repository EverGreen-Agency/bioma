# Decisões decididas — fila de implementação

Movido de DECISOES-ABERTAS.md em 2026-08-24.

**O que está aqui já foi respondido e não precisa voltar a ser perguntado.** O
que falta é construir. É a fila de trabalho, em ordem de decisão, não de
prioridade — a prioridade é sua.

Quando um item for implementado, ele desce para
[DECISOES-FECHADAS.md](DECISOES-FECHADAS.md) com uma linha do que ficou
valendo.

| # | Decisão | O que ficou valendo |
|---|---|---|
| 2 | Idioma e tradução | fazer só o **B** (conteúdo gerado): um artefato, idioma canônico do destinatário, traduções em cache marcadas como tradução e somente leitura. Interface (A) fica para depois. |
| 3 | Follow-up ativo | **opção A**: card de resumo diário no cockpit, sem push por evento. |
| 7 | Context Engine | **base da EG e do cliente, ambas**. Corte vertical da Fase 1, sem embeddings. |
| 9 | GitHub ↔ Tech | issue fechada **sugere** a conclusão, não conclui sozinha. Vira item em "Precisa de você". |
| 10 | Notorious / multi-tenant | a Notorious **vira workspace por enquanto**. Multi-tenant continua sendo projeto separado. |

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

`RESPOSTA (começar pela base da EG ou do cliente?):`Faça para ambos.

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

