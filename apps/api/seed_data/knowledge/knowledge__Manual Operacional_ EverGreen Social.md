# 📗 Manual Operacional: EverGreen Social Media

Loom:
* * *
Objetivo: Este documento define a arquitetura, as regras e os fluxos de trabalho da operação de Social Media da EverGreen MKT. O objetivo é garantir escalabilidade, padronização de qualidade e zero atrito na entrega para nossos clientes.
* * *
## 1\. A Nossa Hierarquia (O Mapa da Empresa)
Nossa operação é dividida para separar a gestão da entrega, garantindo foco e segurança dos dados. E também por um limitação que a plataforma tinha de que um lista mantém seu status independente da view, o que não permitiu nós segmentarmos status diferentes para essas duas demandas (Growth e Social Media), mas fica melhor pois por padrão, até a data de hoje, não vendemos social media, é uma entrega a parte
*   🏢 Workspace: `Quark Holding` (Visão global do negócio)
    *   🪐 Space: `EverGreen | Gestão` (Backoffice: Financeiro, RH, Comercial)
    *   🪐 Space: `EverGreen | Operação` (Frontoffice: O motor de entrega)
Como organizamos os clientes:
Dentro do Space `Operação`, cada cliente é uma Pasta (Folder).
Dentro da pasta do cliente, temos sempre duas Listas separadas para não misturar os fluxos de trabalho:
1. 📄 Social Media Engine: Para a esteira de produção de conteúdo.
2. 📄 Growth & Projetos: Para tráfego, CRM, sites e demandas pontuais (Scrum).
* * *
## 2\. A Regra de Ouro da Task
Na lista _Social Media Engine_, trabalhamos com a seguinte regra:
👉 1 Task = 1 Conteúdo/Post.
A Task deve sempre conter:
*   Título claro: `[Data] Tema Principal do Post` (Ex: _\[15/03\] 3 Erros de Gestão_).
*   Descrição: O Roteiro (baseado no método 7x7), contendo Gancho (3s), Desenvolvimento e CTA (Chamada para Ação).
*   Subtasks: Usadas apenas para checklists de etapas (Ex: _Fazer capa, Inserir legendas_), e não para criar novas tarefas soltas.
* * *
## 3\. O Fluxo de Status (A Esteira de Produção)
Nossos status refletem exatamente em qual etapa o conteúdo está. É proibido pular etapas sem o devido preenchimento dos campos.
Grupo: NOT STARTED (Fila de Espera)
*   ⚪ IDEAÇÃO: Repositório de ideias, referências e insights. Ninguém está trabalhando nisso ainda.
Grupo: ACTIVE (Em Execução - Relógio rodando)
*   🟡 ROTEIRIZAÇÃO: O Copywriter está criando o texto, o gancho e o roteiro.
*   🟠 EM PRODUÇÃO: O Designer ou Editor de Vídeo está com a mão na massa.
*   🔵 REVISÃO INTERNA: O conteúdo está pronto e passando pelo controle de qualidade da EverGreen.
*   🟣 APROVAÇÃO CLIENTE: O conteúdo foi enviado ao cliente e estamos aguardando o "OK".
*   🔴 EM AJUSTE: O cliente pediu alterações. Prioridade máxima para correção.
Grupo: DONE (Concluído, mas ainda em monitoramento)
*   🥬 AGENDADO: Aprovado e já programado na ferramenta de publicação (Ex: Meta Business).
*   🌲 PUBLICADO: O post está no ar.
*   🗽 ANALISAR (Double Down): 7 dias após a publicação. Momento de olhar as métricas para replicar o que deu certo e descartar o que deu errado.
*   🚫 DESCARTADO (Cor: Vermelho escuro ou Cinza escuro): O cliente vetou a ideia / O post perdeu o timing.
Grupo: CLOSED (Finalizado)
*   ✅ FINALIZADO: Ciclo encerrado. Arquivos salvos e tarefa arquivada.
**Ps.: Nunca delete uma tarefa. Dados são ativos. Um post que o cliente odiou hoje pode ter um** **_gancho_** **(hook) excelente que você pode reciclar para outro cliente amanhã.**
* * *
## 4\. Campos Personalizados Obrigatórios (Custom Fields)
Toda Task de conteúdo precisa ter estes campos preenchidos para gerar inteligência de dados para a EverGreen:

| Campo | O que significa | Como preencher |
| ---| ---| --- |
| Missão | Etapa do funil do conteúdo | 🧲 Atrair, 🌱 Nutrir, 💎 Posicionar, ou 🎯 Converter |
| Plataforma | Onde será postado | Instagram, TikTok, LinkedIn, YouTube Shorts, etc. |
| Formato | O tipo de mídia | Reel, Carrossel, Imagem Estática, Story, Texto |
| Data Publicação | O dia exato de ir ao ar | Selecionar a data no calendário |
| KPI Primário | A métrica de sucesso | Alcance, Engajamento, Leads, ou Cliques |
| Link da Pasta | Arquivos brutos | Link do Google Drive com as mídias originais |
| Arquivo Final | O criativo aprovado | Upload direto do vídeo/imagem na Task |
| Legenda/Copy | O texto do post | Texto pronto para copiar e colar no agendamento |

* * *
## 5\. Visualizações Padrão (Views)
Dentro da Lista de cada cliente, utilizamos 4 visualizações principais:
1. Kanban de Produção (Board): Visão do dia a dia. Agrupado por Status para a equipe arrastar os cards pela esteira.
2. Calendário Editorial (Calendar): Visão estratégica. Mostra apenas tarefas que já passaram da fase de "Ideação".
3. Banco de Ideias (List): Visão criativa. Filtra apenas tarefas com o status "Ideação".
4. Aprovação (List Pública): Visão do cliente. Filtra apenas o status "Aprovação Cliente". É o link que enviamos para o cliente aprovar sem precisar logar no sistema.

* * *
## 6\. Compartilhamento com o Cliente (O Portal Único)
A EverGreen não envia links soltos, planilhas ou prints perdidos no WhatsApp. A regra para dar visibilidade ao cliente, reduzir o atrito de aprovação e elevar a percepção de valor é o uso do Client Portal (Dashboard Único).
Mesmo que o cliente tenha contratado apenas Growth, apenas Social Media, ou ambos, a experiência de onboarding é a mesma.
Como funciona o Dashboard do Cliente: O Dashboard não fica solto no sistema. Ele é uma Visualização (View) fixada dentro da própria Pasta do Cliente.
Estrutura do Dashboard (Widgets):
*   Bloco 1: Para Aprovação (Social Media): Mostra apenas tarefas da lista _Social Media Engine_ com status `Aprovação Cliente` e `Em Ajuste`. _(Se o cliente não contratou Social, este bloco ficará vazio ou será excluído do portal dele)._
*   Bloco 2: Status do Projeto & Tráfego (Growth): Mostra o cronograma da lista _Growth & Projetos_ (Gantt ou Lista) para o cliente saber o que está `To Do` e `In Progress`.
*   Bloco 3: Links Úteis: Acesso rápido ao Drive, painel do site ou CRM.
*   A Regra do Link Único: Na reunião de Onboarding (Kick-off), o Gestor da Conta gera o Public Link dessa View de Dashboard e entrega ao cliente. O cliente salva esse link nos favoritos. Tudo o que ele precisar aprovar ou acompanhar durante o tempo de contrato com a EverGreen estará atualizado em tempo real neste link, sem precisar de senhas ou criar contas.