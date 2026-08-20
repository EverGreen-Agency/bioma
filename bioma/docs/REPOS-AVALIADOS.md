# Três repos avaliados para absorção

Pedido em 2026-08-11: "verifique o que desses repos podemos absorver e tornar
nosso". Licenças conferidas **no arquivo LICENSE de cada repositório**, não no
README nem de memória — é o fato que decide tudo aqui.

| Repo | Licença (verificada) | Veredito |
|---|---|---|
| [every-app/open-seo](https://github.com/every-app/open-seo) | MIT | **Não absorver o código.** Absorver uma ideia. |
| [makeplane/plane](https://github.com/makeplane/plane) | **AGPL-3.0** | **Não tocar no código.** Só olhar. |
| [santifer/career-ops](https://github.com/santifer/career-ops) | MIT | Encaixe fino. Vale um padrão, não o projeto. |

---

## 1. open-seo — MIT, mas o valor não está no código

**O que é:** ferramenta de SEO self-hosted (pesquisa de palavra-chave, rank
tracking, backlinks, site audit, visibilidade em IA), com servidor MCP.
TypeScript, Docker/Cloudflare, Drizzle.

**O detalhe que decide:** o README diz, literalmente, *"you need a DataForSEO
API key to get SEO data"*. Não há crawler próprio — **todo dado é comprado do
DataForSEO**. A versão hospedada deles cobra 28% em cima do custo do DataForSEO.

Ou seja: o repositório é a *interface*, e a interface é a parte barata.
Absorver o código não traz dado nenhum de graça.

**E aqui está o ponto que muda a conversa: a EG já paga Ahrefs.**
`bioma_api/integrations/ahrefs.py` existe, a chave está no `config.py`, e o
`content_intelligence` já consome. Ahrefs cobre o mesmo terreno do DataForSEO —
volume de busca, backlink, rank tracking, site audit — **e ainda tem o Brand
Radar**, que mede citação em resposta de IA.

Isso importa muito para a decisão 14: meu `content_quality.py` é uma checklist
do próprio texto e **não consegue** medir se a EG está sendo citada por motor
generativo. Ahrefs consegue. A lacuna que eu documentei tem preenchimento
comprado e já pago.

**Recomendação:** não forkar. Manter um fork de um app de 12,8 mil estrelas
para usar 5% dele é custo permanente por benefício pontual. O que vale tirar
de lá:

1. **A lista de checks do site audit deles** para estender nossa checklist —
   ideia, não código.
2. **Confirmar que o caminho certo é ampliar a integração Ahrefs**, não abrir
   uma segunda fonte de dado de SEO. Duas fontes é dobrar custo e criar a
   pergunta "qual das duas está certa?".

---

## 2. plane — AGPL-3.0, e isso é impeditivo

**Licença conferida no `LICENSE.txt`:** GNU Affero General Public License,
Version 3, 19 November 2007.

**Por que isso trava:** a AGPL tem a cláusula de rede (§13). Software AGPL
oferecido a usuários **através da rede** obriga a oferecer a esses usuários o
código-fonte completo da versão modificada. Bioma é servido a clientes pela
rede. Absorver código do Plane obrigaria a EG a **abrir o código do Bioma para
todo cliente que o usar** — inclusive concorrentes.

Não é burocracia contornável: é o propósito da licença.

**E, mesmo ignorando a licença, o encaixe é fraco.** O Bioma já tem tarefas com
quadro, lista, calendário e Gantt, com vocabulário de status por disciplina —
que é justamente a parte que o Plane *não* tem. Absorver Plane seria substituir
o que existe e funciona por algo genérico.

**Recomendação:** ler para roubar decisão de produto (a modelagem de ciclos e
módulos deles é boa), nunca copiar código. E, se alguém for ler para se
inspirar, que não seja quem está escrevendo a mesma feature no Bioma na mesma
semana — a fronteira entre "me inspirei" e "reproduzi" fica fina.

---

## 3. career-ops — MIT, mas resolve outro problema

**O que é:** automação de busca de emprego para o **candidato** — avalia vagas
por rubrica (A–H, nota 1,0 a 5,0), gera CV sob medida por vaga, varre portais
(Greenhouse, Ashby, Lever) e acompanha candidaturas. Node, Playwright, Go.

**Por que o encaixe é fino:** o Radar Local da EG procura *oportunidade de
negócio local*, não vaga de emprego. E o módulo de RH do Bioma está do lado de
quem **contrata**, não de quem se candidata. São problemas espelhados, não o
mesmo problema.

**O que dá para absorver de verdade — e é um padrão, não código:**

1. **Rubrica explícita com nota por critério.** É o mesmo problema do
   `content_quality.py`: transformar julgamento em critérios verificáveis, cada
   um com peso, em vez de um número que sai de lugar nenhum. Serve direto para
   qualificação de lead no copiloto de vendas — hoje isso é texto do LLM, sem
   rubrica.
2. **Varredura de portal com Playwright.** A EG já tem `scrapers/` no worker.
   Se o Radar Local for varrer fonte nova, o padrão deles é mais maduro que
   começar do zero.

**Recomendação:** não absorver. Ler a rubrica deles antes de escrever a nossa
de qualificação de lead.

---

## O que eu não verifiquei

- **Contagem de estrelas e atividade:** os números vieram do resumo das páginas
  do GitHub e eu não os confirmei na API. Não são load-bearing para nenhuma das
  três decisões.
- **Auditoria de dependências transitivas** de open-seo e career-ops. MIT no
  projeto não garante MIT em tudo que ele puxa. Se algum dia a decisão virar
  "absorver de verdade", isso precisa ser feito antes.
- **Não li o código-fonte de nenhum dos três.** As conclusões vêm de README,
  LICENSE e da estrutura declarada. Para "ler a rubrica do career-ops" e "a
  lista de checks do open-seo", que são as duas recomendações concretas, isso
  ainda está por fazer.
