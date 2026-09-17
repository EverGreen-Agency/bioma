# 💻 Manual Operacional: EverGreen Tech & Software

Loom:
* * *
Objetivo: Este documento rege a engenharia da EverGreen MKT. Ele define o ciclo de vida do desenvolvimento de software, integração de APIs, plataformas DeFi e sistemas complexos. O objetivo é garantir um código limpo (Clean Code), versionamento impecável no GitHub e zero surpresas nos deploys.
* * *
## 1\. A Regra de Ouro da Task de Tech
Na lista _Tech & Software_, não trabalhamos com "ideias abstratas". Cada Task deve ser acionável e testável. Dividimos as tasks em três naturezas principais:
1. Feature: Um novo recurso a ser desenvolvido (Ex: _Criar endpoint de login_).
2. Bug/Fix: Um erro em produção que precisa ser corrigido (Ex: _Botão de checkout não renderiza no mobile_).
3. Chore: Tarefas de infraestrutura ou refatoração que não mudam o produto final para o usuário (Ex: _Atualizar dependência do React_).
* * *
## 2\. O Fluxo de Status (SDLC EverGreen)
Nosso fluxo reflete uma esteira de desenvolvimento profissional, conectada aos eventos do GitHub.
Grupo: NOT STARTED (Fila de Espera)
*   🧠 BRAIN: Não planejado. É o nosso "segundo cérebro" para a conta do cliente. Apenas uma ideia registrada que ainda não tem escopo, prioridade ou dono. O relógio não roda aqui. Aqui é as ideais.
*   🧊 BACKLOG: Tarefas mapeadas, validada e planejada. Já possui o "Definition of Done" (Definição de Pronto), um responsável designado e uma Data de Vencimento (Due Date), mas sem prioridade na sprint atual. Ficam "congeladas" aqui.
*   📋 TO DO (SPRINT): O que a engenharia se comprometeu a entregar na semana/sprint atual.
Grupo: ACTIVE (Mão na Massa - Cronômetro Rodando)
*   👨‍💻 IN PROGRESS: O desenvolvedor puxou a tarefa, criou a branch no GitHub e está escrevendo o código.
*   🔎 CODE REVIEW: O código foi submetido (Pull Request aberto). Outro dev ou o CTO (Gustavo) precisa revisar a lógica antes de aprovar.
*   🧪 QA / TESTING: O código foi aprovado e está no ambiente de Staging (Teste). Aguardando validação de qualidade (garantir que não quebrou nada).
*   🛑 BLOCKED: O dev não pode avançar (Ex: _Falta chave de API de terceiros, falta documentação_).
Grupo: DONE (Concluído, mas exige atenção)
*   🚀 READY FOR RELEASE: Passou no teste. O código está pronto para ir para Produção (Deploy), aguardando apenas a janela de lançamento.
*   🚫 CANCELLED / WON'T FIX: _\[Status Oculto via Filtro\]_ A tarefa foi cancelada, ou é um bug que a diretoria decidiu não corrigir no momento. O cronômetro para e ela sai da visão da equipe.
Grupo: CLOSED (Finalizado)
*   ✅ DEPLOYED (CLOSED): O código está em produção, o usuário já está usando e não houve rollback. Ciclo encerrado.
* * *
## 3\. Padrões de Integração com o GitHub (OBRIGATÓRIO)
O ClickUp e o GitHub conversam nativamente na EverGreen. Para que a automação funcione e o CTO não precise perguntar "onde está o código dessa tarefa?", é obrigatório o uso do ID da Tarefa do ClickUp.
_Cada tarefa no ClickUp tem um ID único (Ex:_ _`#CU-1a2b3c`_ _ou_ _`#EG-102`_ _se a ClickApp Custom Task IDs estiver ativa)._
### A. Padrão de Nomenclatura de Branches
Ao puxar uma tarefa para `IN PROGRESS`, o dev deve criar a branch no GitHub seguindo o formato: `tipo/id-da-tarefa-descricao-curta`
*   _Certo:_ `feat/EG-102-auth-login`
*   _Certo:_ `bug/EG-105-fix-header-mobile`
*   _Errado:_ `arrumando-login`
### B. Padrão de Commits (Conventional Commits)
As mensagens de commit devem seguir o padrão global, sempre incluindo o ID da tarefa no final:
*   `feat: adiciona integracao com API do Stripe (#EG-102)`
*   `fix: corrige overflow do menu lateral (#EG-105)`
*   `refactor: melhora performance da query de usuários (#EG-110)`
### C. Regras de Pull Request (PR)
1. O título do PR deve conter o ID da tarefa do ClickUp.
2. Ao abrir o PR no GitHub, o status da tarefa no ClickUp muda automaticamente de `IN PROGRESS` para `CODE REVIEW`. _(Automação configurada na lista)_.
3. Nenhum PR é "mergeado" (unido à branch principal) sem aprovação (Approve) no GitHub.
* * *
## **4\. Campos Personalizados Obrigatórios (Custom Fields de Tech)**
Para gerar inteligência sobre a velocidade do time técnico e rastrear problemas de infraestrutura, preencha:

| Campo | O que significa | Como preencher (Tipo) |
| ---| ---| --- |
| Tipo (Type) | A natureza da tarefa | Dropdown: `⭐ Feature`, `🐛 Bug`, `⚙️ Chore`. |
| Esforço (Story Points) | Complexidade do código | Dropdown (Fibonacci): `1`, `2`, `3`, `5`, `8`. |
| Prioridade | Urgência do bug/feature | Padrão: 🔴 `Alta`, 🟡 `Média`, 🔵 `Baixa`. |
| Ambiente (Environment) | Onde o bug acontece? | Dropdown: `Produção`, `Staging`, `Local`. |
| GitHub PR | Link direto para o código | Padrão da Integração ClickUp/GitHub. |
| Módulo/Épico | Parte do sistema afetada | Dropdown: `Auth`, `Dashboard`, `Pagamento`. |

* * *
## 5\. Visualizações Padrão (Views de Tech)
Para manter o time focado e o CTO com visão clara dos gargalos, usamos estas visualizações:
1. Kanban Dev (Board View):
    *   _A tela de trabalho diária._
    *   _Agrupamento:_ `Status`.
    *   _Filtro oculto:_ `Status` _não é_ `Backlog` E _não é_ `Cancelled/Won't Fix`.
2. Planejamento de Sprint (List View):
    *   _A tela do Gestor Técnico._
    *   _Agrupamento:_ `Status`.
    *   _Uso:_ Mostra o Backlog para podermos estimar os Story Points (Esforço) e arrastar para o To Do da semana.
3. Bug Tracker (List View):
    *   _O hospital do código._
    *   _Filtro:_ Campo `Tipo (Type)` _é_ `🐛 Bug`.
    *   _Uso:_ Lista exclusiva para caçar erros críticos que precisam ser resolvidos antes das novas features.
* * *
## 6\. Compartilhamento com o Cliente (O Portal Único)
A EverGreen não envia links soltos, planilhas ou prints perdidos no WhatsApp. A regra para dar visibilidade ao cliente e elevar a percepção de valor é o uso do Client Portal (Dashboard Único).
Mesmo que o cliente tenha contratado apenas Desenvolvimento de Software, Growth, Social Media, ou todos, a experiência de onboarding é a mesma.
Como funciona o Dashboard do Cliente: O Dashboard é uma Visualização (View) fixada dentro da própria Pasta do Cliente. O link público desse dashboard é a central da verdade para o cliente.
Estrutura do Dashboard (Widgets):
*   Bloco 1: Para Aprovação (Social Media): Mostra tarefas de Social Media aguardando OK. _(Se não contratado, este bloco é excluído)._
*   Bloco 2: Status do Tráfego (Growth): Mostra campanhas ativas e funis.
*   Bloco 3: Roadmap de Desenvolvimento (Tech & Software):
    *   _Tipo de Widget:_ Gantt Chart ou Task List.
    *   _Origem:_ Lista `Tech & Software`.
    *   _Filtro:_ Status não é Backlog nem Cancelled.
    *   _O que o cliente vê:_ O progresso visual das features do software dele, sabendo exatamente o que está sendo codificado hoje e o que está em fase de testes (QA).
A Regra do Link Único: O cliente recebe apenas um link no WhatsApp. Tudo o que ele precisar acompanhar durante o tempo de contrato com a EverGreen estará atualizado em tempo real neste link, garantindo transparência técnica sem sobrecarregá-lo com jargões de código.