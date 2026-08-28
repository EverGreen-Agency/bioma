# Decisões abertas — Bioma

Atualizado em 2026-08-24.

**Este arquivo só tem o que ainda TRAVA.** Cada bloco tem contexto, opções,
minha recomendação e uma linha `RESPOSTA:` para você preencher. O que estiver
respondido eu implemento sem voltar a perguntar.

Se ele encolhe, é sinal bom.

## Onde está o resto

| Documento | O que tem |
|---|---|
| **este arquivo** | o que trava: sem resposta, ou respondido e ainda em disputa |
| [DECISOES-DECIDIDAS.md](DECISOES-DECIDIDAS.md) | **respondidas e ainda não construídas** — é a fila de trabalho |
| [DECISOES-FECHADAS.md](DECISOES-FECHADAS.md) | decididas E implementadas; ninguém precisa reabrir |

**Regra de manutenção.** Decisão respondida sai daqui no mesmo commit que a
responde — vai para DECIDIDAS. Quando for construída, desce para FECHADAS. Uma
decisão pronta parada aqui faz o arquivo parecer maior que o trabalho real, e
foi exatamente o que aconteceu: em 2026-08-24 este arquivo tinha 12 seções, das
quais 8 já estavam resolvidas.

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

## 6. Nome do repositório

**Contexto.** Você concordou em renomear depois da faxina, e observou que ao
renomear a pasta local seus chats e copilots perdem o contexto.

**Faxina feita em 2026-08-05** (Opensquad apagado) — só falta o nome e a ordem
**pasta local → remoto**.

`RESPOSTA (nome final):`

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

## 14. CMS — publicar e GERENCIAR blog do cliente e da EG (parcial)

> **Estado em 2026-08-24.** Publicar E gerenciar estao construidos. Falta um
> unico passo, e ele e seu: a credencial.
>
> **Gerenciar o blog de dentro do Bioma** (pedido em 2026-08-24) entrou:
> Estudio > aba **Blog do site** lista os posts vindos do CMS AO VIVO —
> inclusive os que nao nasceram no Bioma, com selo de origem. Da para publicar,
> tirar do ar, agendar e mandar para a lixeira. Nunca apaga de vez: `force` nao
> e usado, entao o cliente restaura pelo painel dele.
>
> **Bug corrigido no mesmo dia:** `create_post` era chamado sempre, entao
> republicar criava post DUPLICADO no site do cliente enquanto a tela afirmava,
> em texto, que atualizava o mesmo post. Era erro de modelo tambem — a
> publicacao era unica por (artefato, VERSAO, alvo), tratando cada versao como
> um post novo. Migracao 0095: um artigo e UM post por destino, e `version`
> passa a significar qual versao esta no ar.
>
> **Estado em 2026-08-11.** Suas tres respostas foram implementadas ate onde
> da para provar sem um WordPress real na mao.
>
> **Pronto (fluxo inteiro, menos o envio real):** score SEO/GEO
> (`content_quality.py` + painel), camada pura (`cms.py`), cliente REST
> (`integrations/wordpress.py`), migracao 0094 (`cms_targets` +
> `artifact_publications`), servico, rotas, tela de conectar site em
> Integracoes e painel de publicar no Estudio — com PREVIA obrigatoria: o botao
> nao aparece antes de a pessoa poder ver o que vai ser enviado.
>
> Duas regras que ficaram travadas por teste: `direct` nao vence falta de
> aprovacao, e a PERMISSAO E ATRELADA AO RISCO — rascunho exige `manage_work`,
> ir ao ar exige `approve`. Um operador rascunha a vontade; so quem aprova
> coloca no site do cliente.
>
> A publicacao registra a VERSAO, nao a peca: a v1 pode estar no ar enquanto a
> v3 e rascunho, e sem isso "esta peca esta publicada?" nao tem resposta
> honesta.
>
> **FALTA SO ISTO, e e do seu lado:** uma Application Password do
> `cms.evergreenmkt.com.br` cadastrada no cofre. Passo a passo:
>
> 1. WordPress > Usuarios > Perfil > **Senhas de aplicativo**;
> 2. nome: `Bioma`; copie os 24 caracteres (com espacos, tanto faz);
> 3. no Bioma: workspace da EG > **Acessos** > nova credencial, plataforma
>    `wordpress`, usuario = seu login do WP, senha = a que acabou de gerar;
> 4. Configuracoes > Integracoes > **Sites (CMS)** > Conectar, apontando
>    `https://cms.evergreenmkt.com.br` para essa credencial;
> 5. **Testar conexao** — e o botao que prova tudo de uma vez.
>
> **Nao cole a senha aqui no chat**, pelo mesmo motivo do token do Better Stack:
> o que passa pelo chat esta comprometido e precisa ser rotacionado.
>
> **Sua oferta de projetos open source de SEO continua de pe e util** — o que
> tenho hoje e checklist do proprio texto, e nao substitui dado de volume de
> busca, concorrencia de termo ou backlink, que e onde essas ferramentas
> entram.

Levantado em 2026-08-11. Necessidade real e imediata: gerenciar e publicar
artigos no blog da EG (SEO/GEO) e no de pelo menos um cliente. Hoje isso é
manual e não existe nada no Bioma.

**O encaixe é melhor do que parece**, porque três peças já existem e a
integração é o elo que falta, não uma feature do zero:

- **artefatos versionados** (0089) — o artigo nasce como artefato, com
  procedência (`thread_id`/`run_id`) e versão;
- **Estúdio** — a vista onde se revisa antes de publicar;
- **`performance_connections`** — o padrão de conexão por workspace, com
  credencial no ambiente e nunca no banco.

**WordPress não precisa de plugin.** A REST API é nativa
(`/wp-json/wp/v2/posts`) e autentica por Application Password, que se gera no
perfil do usuário. É a rota mais simples e a que menos depende do cliente.

### Desenho proposto

```
conversa com copiloto  →  artefato (kind: artigo)
                              ↓ revisão no Estúdio
                              ↓ status: approved
                       publicar  →  WordPress como RASCUNHO
                              ↓
                    guarda post_id + URL de volta no artefato
```

**Publicar sempre como rascunho, nunca direto no ar.** Erro de IA no blog do
cliente é público, indexável e fica no cache do Google — o custo de um rascunho
a mais é zero perto disso. Quem aperta "publicar" é uma pessoa, no WordPress.

Guardar `post_id` e URL de volta no artefato é o que fecha o ciclo: sem isso,
uma segunda publicação cria post duplicado em vez de atualizar, e ninguém
consegue ir do artefato ao que está no ar.

### O que eu NÃO faria junto

**Score de SEO/GEO é outra feature.** Score exige critério definido — e sem
critério vira exatamente o problema das recomendações fixas que saíram dos PDFs
e do "IA Insight": um número com aparência de análise e nenhuma análise atrás.
Se for fazer, primeiro se define o que se mede.

**Newsletter também é outra coisa.** WordPress publica; newsletter dispara. São
provedores diferentes (Mailchimp, Brevo, Resend) e o risco é oposto — post
errado se despublica, e-mail enviado não volta.

`RESPOSTA (WordPress primeiro, ou já contemplar outros CMS?):`Pode ser por enqaunto wordpress mas já deixe planejado outros conhecidos do mercado.

`RESPOSTA (publicar como rascunho sempre, ou permitir publicar direto?):`Ter como configurar as duasopções.

`RESPOSTA (score de SEO/GEO entra agora ou fica para depois?):`Gostaria que entrasse agora. E se precisar, eu achei projetos open source de SEO. Se precisar lhe trago!


---

## Quais são as 7 dimensões do Raio-X Tecnológico

**Contexto.** O Documento-Mestre §10.1 define a Escada de Oferta de Tecnologia e
promete, como entregável do Tech 1, um *"score de maturidade AI-First em 7
dimensões"*. **As sete dimensões não estão enumeradas em lugar nenhum** — nem no
Documento-Mestre, nem no Bioma, nem no repo do site. O número 7 aparece rastreado
a uma referência externa: um log de sessão de junho/2026 registra *"ai-firstify
plugin (7 dimensions, 9 principles)"* como inspiração do Guardião/Arquiteto.

Ou seja: o entregável está vendido, a régua não está escrita.

**O que eu fiz enquanto isso.** A LP `/tech` (`src/app/tech/data.ts` no repo
`EGMKT/eg`) usa sete dimensões **propostas por mim**, derivadas da lista
"Diferencial tecnológico da EG" do próprio Documento-Mestre, que por coincidência
também tem sete itens:

| # | Dimensão | A pergunta que ela abre |
|---|---|---|
| 1 | Diagnóstico | Existe leitura da operação ou só percepção de quem está dentro? |
| 2 | Execução | O que demora semanas por depender de uma pessoa específica? |
| 3 | Documentação | O que só existe na cabeça de alguém? |
| 4 | Dados | Quantas planilhas respondem à mesma pergunta de formas diferentes? |
| 5 | Automação | Qual trabalho manual se repete toda semana sem variação? |
| 6 | Qualidade | O resultado muda conforme quem faz? |
| 7 | Margem | Atender o dobro exigiria o dobro de time? |

**Isto é proposta, não recuperação.** A coincidência de ambos serem sete não
prova que sejam a mesma lista.

**Por que trava a publicação.** Hoje `/servicos` diz, com todas as letras, que
*"o diagnóstico tecnológico é mais amplo e desenhado caso a caso — preferimos
dizer isso a fingir uma régua que ainda não existe"*. Se a `/tech` for ao ar
afirmando sete dimensões, passam a existir duas afirmações contraditórias no
mesmo domínio — exatamente o problema que a auditoria da `/growth` acabou de
resolver. **Não publicar `/tech` antes de fechar isto.**

Três saídas:

1. **Confirmar estas sete.** Então `/servicos` precisa ser atualizada junto: a
   frente tech deixa de ser "aberta" e passa a ter régua, como o §10.1 já promete.
2. **Escrever outras sete.** Troca-se o array em `data.ts` e vale a mesma
   atualização de `/servicos`.
3. **Assumir que não há régua.** Aí o §10.1 é que está desatualizado, o
   entregável do Tech 1 precisa ser reescrito sem "7 dimensões", e a `/tech` troca
   a seção 02 por outra coisa.

Minha recomendação é a 1: as sete acima saem do próprio documento, são
perguntáveis numa call de diagnóstico e não exigem instrumentação nova.

`RESPOSTA (confirmar as sete, escrever outras, ou assumir que não há régua):`
