# 🚀 Manual Operacional: EverGreen Growth

Loom:
* * *
Objetivo: Este documento rege a operação da área de Growth, Tráfego, CRM e Tecnologia da EverGreen MKT. Diferente de Social Media (que é um fluxo criativo contínuo), Growth trabalha com engenharia, dados e ciclos fechados (Projetos e Sprints). O objetivo é garantir que nenhuma campanha atrase e que o escopo de tecnologia seja entregue com precisão.
* * *
## 1\. A Regra de Ouro da Task de Growth
Na lista _Growth & Projetos_, cada Task representa um Entregável, uma Campanha ou uma Rotina.
Nós trabalhamos com 2 tipos de tarefas aqui:
1. Tarefas Finitas: Têm começo, meio e fim (Ex: _Criar Landing Page de Black Friday_, _Implementar PipeDrive_).
2. Tarefas Recorrentes: Rotinas de otimização (Ex: _Otimização Semanal de Campanhas Meta Ads_).
    *   _Regra de Recorrência:_ Não usamos status para rotinas. Usamos a função nativa de Recurring Tasks do ClickUp configurada para recriar a tarefa automaticamente (ex: toda segunda-feira) quando a anterior for concluída.
* * *
## 2\. O Fluxo de Status (Scrum Customizado EverGreen)
Nosso fluxo de trabalho em Growth e Projetos segue uma esteira ágil e enxuta. A movimentação dos cards deve refletir o exato estágio da tarefa no momento.
Grupo: NOT STARTED (Repositório / Fila de Espera)
*   🧠 BRAIN: Não planejado. É o nosso "segundo cérebro" para a conta do cliente. Apenas uma ideia registrada que ainda não tem escopo, prioridade ou dono. O relógio não roda aqui.
Grupo: ACTIVE (Mão na Massa - Cronômetro Rodando)
*   📋 BACKLOG: Tarefa validada e planejada. Já possui o "Definition of Done" (Definição de Pronto), um responsável designado e uma Data de Vencimento (Due Date). Está pronta para começar.
*   🏃 IN PROGRESS: Em andamento. O executor está ativamente com a mão na massa nesta tarefa no momento.
*   🔎 IN REVIEW: O trabalho técnico terminou, mas precisa de validação. Pode ser uma revisão interna (QA de tags, revisão de copy) ou o aguardo do "OK" formal do cliente.
*   ❌ REJECTED: O trabalho não passou na revisão. O cliente ou o Gestor do Projeto apontou erros ou pediu refações. A tarefa volta para a responsabilidade do executor com prioridade máxima para ajustes.
*   🛑 BLOCKED: Travado por dependência externa. A tarefa não pode avançar porque falta acesso, o cliente não enviou o cartão de crédito, o site caiu, etc. Requer ação imediata do Gestor da Conta para destravar.
Grupo: DONE (Concluído Parcialmente)
*   🟩 DONE: Concluído e aprovado. O esforço técnico acabou e a tarefa não está mais atrasada. Ela permanece neste status temporariamente (ao invés de ser fechada) para que possamos monitorar os primeiros dias de resultado da campanha/implementação.
Grupo: CLOSED (Finalizado)
*   ✅ CLOSED: Ciclo 100% encerrado. Projeto entregue, faturado ou campanha desativada. A tarefa é ocultada das visualizações diárias para manter nossa tela de trabalho limpa.
* * *
## 3\. Campos Personalizados (Custom Fields)
Para gerenciar tráfego e projetos tech, precisamos saber onde alocar energia e dinheiro. O preenchimento destes campos é obrigatório:

| Campo | O que significa | Como preencher (Tipo) |
| ---| ---| --- |
| Área do Projeto | O departamento responsável | Dropdown: `Tráfego`, `CRM`, `Web/Landing Page`, `Automação`. |
| Prioridade | O nível de urgência do negócio | Padrão: 🔴 `Alta`, 🟡 `Média`, 🔵 `Baixa`. |
| Esforço (Complexidade) | Quanto trabalho isso vai dar | Dropdown: `Baixo` (horas), `Médio` (dias), `Alto` (semanas). |
| Gestor da Conta | O líder estratégico do cliente | Usuário (People): Quem responde por este cliente na holding. |
| Verba (Budget) | O orçamento da campanha/projeto | Moeda (Money): Valor em R$. |
| Link do Doc | Briefing ou Arquitetura | Link (Website): URL para o Google Docs, Figma ou Miro. |
| Responsável (Assignee) | O executor técnico | Usuário: O dev ou gestor de tráfego operando a ferramenta. |
| Dono | Gestor do Projeto | Usuário |

* * *
## 4\. Visualizações Padrão (Views de Growth)
Dentro da Lista de Growth de cada cliente, utilizamos 3 visualizações principais para garantir que nada saia do controle:
1. Quadro de Execução (Board View):
    *   _Visão de Trincheira._ Mostra apenas as tarefas ativas e travadas.
    *   _Filtro oculto:_ Esconde o "Backlog" e o "Archived".
    *   _Uso:_ É aqui que a equipe técnica vive, arrastando cards de _To Do_ para _In Progress_.
2. Backlog & Planejamento (List View):
    *   _Visão do Gestor._ Mostra apenas o status "Backlog".
    *   _Uso:_ Usada semanalmente para priorizar o que vai ser feito. Analisamos a coluna de "Esforço", definimos o que cabe na semana, e arrastamos para _To Do_.
3. Roadmap do Cliente (Gantt / Timeline View):
    *   _Visão do Cliente._ Um gráfico visual baseado nas Datas Iniciais e Datas de Vencimento.
    *   _Uso:_ Tiramos print desta tela para provar ao cliente que o projeto (ex: Migração de CRM) está no prazo e mostrar as dependências visuais.
* * *
## 5\. Regras de Relacionamento (Dependencies)
Como Growth e Social Media andam de mãos dadas, mas moram em listas separadas, usamos a ferramenta "Relationships" do ClickUp.
*   Se a campanha de Tráfego (Growth) precisa dos vídeos criados pela equipe de conteúdo (Social Media), a tarefa de Tráfego deve ser marcada como "Waiting On" (Aguardando) a tarefa de Social Media.
*   Isso avisa o Gestor de Tráfego automaticamente quando o vídeo for finalizado e aprovado.
* * *
## 6\. Compartilhamento com o Cliente (O Portal Único)
A EverGreen não envia links soltos, planilhas ou prints perdidos no WhatsApp. A regra para dar visibilidade ao cliente, reduzir o atrito de aprovação e elevar a percepção de valor é o uso do Client Portal (Dashboard Único).
Mesmo que o cliente tenha contratado apenas Growth, apenas Social Media, ou ambos, a experiência de onboarding é a mesma.
Como funciona o Dashboard do Cliente: O Dashboard não fica solto no sistema. Ele é uma Visualização (View) fixada dentro da própria Pasta do Cliente.
Estrutura do Dashboard (Widgets):
*   Bloco 1: Para Aprovação (Social Media): Mostra apenas tarefas da lista _Social Media Engine_ com status `Aprovação Cliente` e `Em Ajuste`. _(Se o cliente não contratou Social, este bloco ficará vazio ou será excluído do portal dele)._
*   Bloco 2: Status do Projeto & Tráfego (Growth): Mostra o cronograma da lista _Growth & Projetos_ (Gantt ou Lista) para o cliente saber o que está `To Do` e `In Progress`.
*   Bloco 3: Links Úteis: Acesso rápido ao Drive, painel do site ou CRM.
A Regra do Link Único: Na reunião de Onboarding (Kick-off), o Gestor da Conta gera o Public Link dessa View de Dashboard e entrega ao cliente. O cliente salva esse link nos favoritos. Tudo o que ele precisar aprovar ou acompanhar durante o tempo de contrato com a EverGreen estará atualizado em tempo real neste link, sem precisar de senhas ou criar contas.