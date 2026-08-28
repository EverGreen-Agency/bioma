Documento operacional da EverGreen — frente de Tecnologia.

# **Raio-X Tecnológico**

**Auditoria de Prontidão AI-First.** É o entregável do degrau **Tech 1** da Escada de Oferta de Tecnologia (`Documento-Mestre_EG.md` §10.1) e o pré-requisito de todos os degraus seguintes, exatamente como o Raio-X Comercial é para a escada de growth.

> **Nota de origem.** O Documento-Mestre §10.1 prometia "score de maturidade AI-First em 7 dimensões" desde sempre, mas nunca enumerou quais eram — o número tinha vindo de uma referência externa (o plugin `ai-firstify`). As sete abaixo foram derivadas da lista "Diferencial tecnológico da EG" do próprio Documento-Mestre e **confirmadas pelo Eduardo em 2026-08-28**. A régua está fechada.

# **1\. O que é o Raio-X Tecnológico**

O Raio-X Comercial responde *onde a receita vaza*. O Tecnológico responde uma pergunta diferente e complementar: **onde a operação gasta gente para fazer o que não deveria exigir gente.**

Não é auditoria de stack. Inventário de ferramentas é insumo, não resultado — a empresa pode ter dez sistemas e nenhuma prontidão, ou três e muita. O que se mede é o quanto a operação consegue funcionar **sem depender de alguém lembrar**.

Isso decorre direto da Política AI First (`Documento-Mestre_EG.md`): antes de somar esforço humano a qualquer processo, a pergunta padrão é se aquilo pode ser feito, acelerado ou ampliado por IA. Uma empresa AI-First não é a que usa IA — é a que documentou, padronizou e centralizou o suficiente para que IA *possa* ser usada. As sete dimensões medem esse suficiente.

## **Por que ele existe separado do Comercial**

Porque o gargalo muda de natureza. Quando o problema é comercial, a resposta é processo, cadência e oferta. Quando o problema é operacional — pedido em planilha, dado espalhado, time refém de um arquivo — mais processo comercial não resolve nada.

Um cliente pode ter Raio-X Comercial 8,0 e Tecnológico 3,0: vende bem e sufoca na entrega. O contrário também acontece. **São réguas independentes, aplicadas ao mesmo cliente quando o caso pede.**

# **2\. Como funciona o cálculo**

Deliberadamente idêntico ao Raio-X Comercial. Mesma escala, mesma conversão, mesma regra de priorização — quem entende um entende o outro.

1. Cada dimensão tem **5 perguntas**.

2. Cada pergunta recebe nota de **1 a 5**:

   * 1 \= não existe / não acontece

   * 2 \= existe de forma muito incipiente

   * 3 \= existe, mas inconsistente

   * 4 \= existe e funciona razoavelmente

   * 5 \= existe e funciona bem, de forma consistente

3. Some as 5 notas da dimensão (resultado de 5 a 25).

4. Converta para escala 0–10: **(soma ÷ 5\) × 2**.

5. **Raio-X Tecnológico geral** \= média das sete dimensões.

6. **Gargalo prioritário** \= dimensão de menor nota. É por ela que o roadmap começa.

**Diferença relevante frente ao Comercial:** sete dimensões, não três. A média geral é menos útil aqui — o valor está na leitura dimensão a dimensão, porque as dependências entre elas são fortes (ver §5). Reportar só a média esconde o diagnóstico.

# **3\. As 35 perguntas**

## **Dimensão 1 — DIAGNÓSTICO**

*A empresa enxerga onde perde eficiência, ou só sente?*

1. Existe alguma medição de tempo gasto nas rotinas operacionais, ou o custo do trabalho manual é invisível?

2. Quando algo dá errado na operação, é possível reconstruir o que aconteceu, ou depende da memória de quem estava lá?

3. A liderança sabe apontar qual é o processo mais caro da casa, com número?

4. Existe registro de retrabalho — quantas vezes a mesma coisa foi refeita e por quê?

5. Alguém é responsável por olhar a eficiência operacional, ou isso só aparece quando vira crise?

## **Dimensão 2 — EXECUÇÃO**

*Quanto tempo separa a decisão da entrega.*

1. Uma mudança pequena e aprovada leva quanto tempo para estar no ar — horas, dias ou semanas?

2. Existe alguma tarefa crítica que só uma pessoa específica consegue executar?

3. Quando essa pessoa tira férias, a operação continua ou espera?

4. Há fila visível do que está em execução, ou o trabalho chega por mensagem avulsa?

5. O tempo de resposta a um pedido interno é previsível o suficiente para alguém se planejar em cima dele?

## **Dimensão 3 — DOCUMENTAÇÃO**

*Processo escrito é processo que a IA consegue executar. Também é processo que um funcionário novo consegue executar.*

1. Os processos centrais estão escritos em algum lugar que as pessoas de fato consultam?

2. Uma pessoa nova consegue executar uma rotina lendo a documentação, sem perguntar?

3. A documentação é atualizada quando o processo muda, ou envelhece em silêncio?

4. Existem decisões importantes registradas com o *porquê*, ou só o resultado sobreviveu?

5. O que só existe na cabeça de alguém está mapeado como risco?

## **Dimensão 4 — DADOS**

*Informação num lugar só, com um número só.*

1. Quantos lugares diferentes respondem à mesma pergunta de negócio?

2. Quando duas fontes divergem, existe uma que é a oficial?

3. Os dados operacionais são registrados no momento em que acontecem, ou reconstruídos depois?

4. É possível responder a uma pergunta nova sobre a operação sem pedir para alguém montar planilha?

5. Existe alguma planilha crítica que, se corrompesse hoje, pararia a operação?

## **Dimensão 5 — AUTOMAÇÃO**

*Rotina repetível não deveria consumir gente.*

1. Qual trabalho manual se repete toda semana, praticamente sem variação?

2. Os sistemas que a empresa usa conversam entre si, ou alguém copia dado de um para o outro?

3. Quando algo automatizado falha, alguém é avisado, ou descobre-se pelo efeito?

4. As automações existentes são documentadas e reversíveis, ou ninguém mexe com medo?

5. Existe critério para decidir o que automatizar, ou automatiza-se o que incomoda mais no momento?

## **Dimensão 6 — QUALIDADE**

*Padrão que não depende de quem executou.*

1. O resultado de uma mesma tarefa muda conforme quem faz?

2. Existe critério escrito do que é "pronto" para as entregas principais?

3. Erros recorrentes viram correção de processo, ou só correção do caso?

4. Há alguma checagem antes de o trabalho chegar ao cliente?

5. A empresa consegue dizer qual é a taxa de erro de algum processo central?

## **Dimensão 7 — MARGEM**

*Crescer sem que o custo cresça junto.*

1. Atender o dobro de clientes exigiria o dobro de time?

2. O custo de servir um cliente é conhecido, ou estimado por sensação?

3. Existe alguma parte da entrega que já escala sem esforço adicional?

4. As assinaturas de software são revisadas, ou acumulam?

5. A empresa consegue dizer quanto custa, por mês, o trabalho que hoje é manual?

# **4\. Como interpretar o resultado**

Mesma leitura do Raio-X Comercial.

| Faixa da dimensão | Leitura | O que significa na prática |
| :---- | :---- | :---- |
| 0 – 3 | Crítico | Não existe estrutura. Qualquer automação em cima disso amplifica o erro. |
| 4 – 6 | Frágil | Existe, mas inconsistente. É onde estão os ganhos rápidos. |
| 7 – 8 | Saudável | Funciona. Otimização, não reconstrução. |
| 9 – 10 | Maduro | Pronto para IA de verdade sobre essa dimensão. |

**Regra de condução: ataca-se a menor dimensão primeiro** — com uma ressalva que não existe no Comercial e é a parte mais importante deste documento.

# **5\. As dependências entre dimensões**

As sete não são independentes. Automatizar por cima de uma base fraca não é ineficiente: é ativamente destrutivo, porque congela o erro em código e o torna mais caro de corrigir.

* **Documentação destrava Automação e Qualidade.** Não se automatiza o que não está escrito, e não se padroniza o que não tem critério registrado. Documentação baixa com Automação alta é o pior cenário possível — a empresa tem fluxos automáticos que ninguém entende e ninguém ousa mexer.

* **Dados destravam Diagnóstico e Margem.** Sem fonte única, qualquer medição é discutível, e discussão sobre número mata decisão.

* **Diagnóstico destrava tudo.** É a única dimensão que, baixa, invalida a leitura das outras seis — a empresa não sabe o que não sabe.

* **Margem é sempre consequência, nunca causa.** Não se ataca Margem diretamente. Ela sobe quando Automação e Dados sobem.

**Consequência prática na priorização:** se a menor dimensão for Margem, **não é por ela que se começa.** Sobe-se a menor entre Documentação, Dados e Diagnóstico primeiro. Esta é a diferença central entre o Raio-X Tecnológico e o Comercial — lá o menor pilar é sempre o ponto de entrada; aqui há ordem de precedência.

# **6\. A régua que evolui — dois níveis**

Mesma lógica do Comercial.

* **Nível 1 — Fundacional** (as 35 perguntas deste documento): mede se a estrutura *existe*. Usado no diagnóstico e nos primeiros ciclos.

* **Nível 2 — Otimização:** com a dimensão em 4–5, as perguntas endurecem. Não mais "o processo está escrito?", e sim "a documentação é versionada, testada contra a realidade e consumível por um agente de IA sem ambiguidade?".

## **As 35 perguntas do Nível 2 — Otimização**

O Nível 1 pergunta se a estrutura **existe**. Quando uma dimensão chega a 4–5 consistente, essa pergunta para de discriminar. O Nível 2 troca *existe?* por *é versionado, medido e confiável o suficiente para uma máquina operar em cima?*.

Mesma escala, mesma conversão, mesma precedência do §5 — inclusive a regra de que Margem nunca é ponto de entrada.

**Ativa-se por dimensão, não pelo conjunto.** Uma empresa pode estar em Nível 2 em Dados e ainda em Nível 1 em Documentação, e essa assimetria é informação: significa que ela tem número bom sobre um processo que ninguém escreveu.

### **Dimensão 1 — DIAGNÓSTICO (Nível 2)**

1. O custo do trabalho manual é apurado periodicamente, ou foi medido uma vez?
2. Existe comparação da eficiência operacional entre períodos, com a mesma régua?
3. Quando um processo piora, alguém é avisado por limite definido — ou descobre-se pelo efeito?
4. As decisões de investimento em tecnologia citam o número que as motivou?
5. O retrabalho é categorizado por causa, e não só contado?

### **Dimensão 2 — EXECUÇÃO (Nível 2)**

1. O tempo entre decisão e entrega é medido, e a mediana é conhecida?
2. Existe alguma dependência de pessoa única ainda mapeada como risco aberto?
3. Mudança pequena vai ao ar sem exigir uma janela combinada?
4. Existe capacidade de reverter uma entrega em minutos?
5. A fila de execução é priorizada por critério escrito, ou por quem pediu mais alto?

### **Dimensão 3 — DOCUMENTAÇÃO (Nível 2)**

1. A documentação é versionada junto com o que ela descreve?
2. Existe checagem — mesmo manual — de que ela ainda bate com a realidade?
3. Um agente de IA conseguiria executar o processo lendo o documento, sem ambiguidade?
4. As decisões registram alternativas descartadas e o porquê, não só o resultado?
5. Documento desatualizado é detectado por alguma rotina, ou por alguém tropeçar nele?

### **Dimensão 4 — DADOS (Nível 2)**

1. Existe uma fonte declarada como oficial para cada indicador central?
2. Divergência entre fontes dispara alerta, ou é descoberta em reunião?
3. O dado histórico é preservado de forma que permita comparar períodos?
4. Uma pergunta nova é respondida por quem precisa dela, sem intermediário técnico?
5. Existe alguma planilha crítica remanescente — e ela está mapeada como risco?

### **Dimensão 5 — AUTOMAÇÃO (Nível 2)**

1. Toda automação tem dono nomeado e alerta de falha?
2. Automação é idempotente — rodar duas vezes produz o mesmo resultado?
3. Existe registro do que cada automação fez, auditável depois?
4. Automação quebrada é detectada em minutos ou em dias?
5. Existe critério escrito para decidir o que automatizar em seguida, e a fila segue ele?

### **Dimensão 6 — QUALIDADE (Nível 2)**

1. A taxa de erro dos processos centrais é medida e acompanhada ao longo do tempo?
2. Existe checagem automatizada em algum ponto do fluxo, não só revisão humana?
3. Erro recorrente vira mudança de processo dentro de um prazo definido?
4. O critério de "pronto" é verificável por alguém que não executou?
5. A variação de resultado entre executores é conhecida em número?

### **Dimensão 7 — MARGEM (Nível 2)**

1. O custo de servir é apurado por cliente, e não só na média?
2. A parcela da entrega que escala sem esforço adicional é conhecida em percentual?
3. As assinaturas de software são revisadas em ciclo definido, com corte efetivo?
4. Existe projeção de qual seria o custo de dobrar o volume?
5. O ganho de eficiência das automações entregues foi medido depois, e não só estimado antes?

### **Sobre a queda de nota**

Uma dimensão que estava em 9 no Nível 1 costuma cair para 4 ou 5 quando a régua sobe. **Diga isso antes de aplicar**, não depois.

A nota não piorou: a pergunta ficou mais dura. Sem esse enquadramento, a mudança de régua parece manobra para justificar mais trabalho — e essa leitura destrói a confiança construída até ali.

A formulação que funciona: *"você venceu o Nível 1 nessa dimensão. A partir de agora medimos outra coisa, e a nota recomeça."*

## **A corrente completa, do lado tecnológico**

O equivalente ao capítulo 3.4 do Playbook. Cinco elos: **dimensão → causa → métrica → ponto de atuação → entregável.**

| Dimensão-gargalo | Métrica que prova | Ponto de atuação | Entregável |
| :---- | :---- | :---- | :---- |
| **Diagnóstico** | ausência de qualquer medição de tempo operacional | instrumentar as três rotinas mais caras | Tech 1 |
| **Execução** | mediana entre decisão e entrega; nº de dependências de pessoa única | remover o gargalo de aprovação; documentar a tarefa crítica | Tech 2 |
| **Documentação** | % dos processos centrais escritos e consultados | escrever os cinco processos mais repetidos | Tech 2 |
| **Dados** | nº de fontes que respondem à mesma pergunta | declarar fonte oficial; integrar o resto a ela | Tech 2 |
| **Automação** | nº de rotinas semanais idênticas ainda manuais | automatizar as já escritas — só as já escritas | Tech 2 · Tech 3 |
| **Qualidade** | variação de resultado entre executores | critério de pronto escrito + checagem antes da entrega | Tech 3 |
| **Margem** | custo de servir por cliente | *nenhum — Margem não se ataca direto* | — |

A última linha é a parte que mais se erra. **Margem é sempre consequência.** Quando ela é a menor nota, o ponto de atuação está em Dados ou Automação, e a Margem sobe atrás.

E vale a mesma regra do lado comercial: **a métrica é escolhida antes da intervenção, nunca depois.** Registre o valor dela no dia do diagnóstico — é o que transforma o Raio-X seguinte em comparação em vez de nova opinião.

**Frequência de re-score:** completo a cada trimestre, junto da revisão estratégica do Tech 3. Pulso mensal apenas nas 5 perguntas da dimensão-gargalo.

# **7\. Como é entregue**

* **No Tech 1 (diagnóstico):** é o entregável central — as sete notas, o geral, a dimensão-gargalo respeitando a precedência do §5, o inventário da stack e o roadmap de implementação.

* **No Tech 2 (Sprint):** o roadmap vira escopo fechado de 6 a 8 semanas, entregue em corte vertical.

* **No Tech 3 (Retainer):** revisado a cada ciclo. É a prova visual de que a estruturação funcionou.

**Garantia** (§10.1): se o cliente não sair com clareza prática sobre gargalos tecnológicos e prioridades, a EG revisa o diagnóstico sem custo até ficar cristalino.

# **8\. Nota de naming**

"Raio-X Tecnológico" é deliberado: reaproveita o reconhecimento do Raio-X Comercial em vez de criar categoria nova. O cliente que já passou por um entende o outro sem explicação.

Pelas fases do Sistema Raiz, o Raio-X Tecnológico é **Raiz** — diagnosticar. Vale para as duas frentes; a árvore é a mesma.
