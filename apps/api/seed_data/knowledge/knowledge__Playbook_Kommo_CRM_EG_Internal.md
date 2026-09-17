

| ![][image1] PLAYBOOK OPERACIONAL Kommo CRM Agência: EverGreen MKTCliente: Template PadrãoVersão: 1.1 (Atualizado jun/2026)Data: junho de 2026Responsável: Equipe EverGreen EverGreen \- Documento interno \- evergreenmkt.com.br |
| ----- |

# **![][image2]**

# 

# **Histórico de versões**

| Versão | Data | O que mudou | Responsável |
| :---- | :---- | :---- | :---- |
| 1.0 | jan/2026 | Versão inicial do playbook | Equipe EverGreen |
| 1.1 | jun/2026 | Atualização plataforma Kommo jun/2026: limite de leads ativos, leads de entrada contam no limite, automações param ao atingir o limite, limites de canal/multi-WhatsApp por plano, ads integrados → Pro, Agente de IA fora do Básico, agendamentos nativos, módulo Segmentos. Add §10. | Equipe EverGreen |

# **0\. Visão geral e regras de ouro**

## **Objetivo deste playbook**

Padronizar a operação da sua empresa dentro da Kommo, reduzindo trabalho manual e garantindo que cada lead tenha dono, contexto e próximo passo. Este documento também serve como material de orientação para clientes, com mínimas alterações.

## **O que é a Kommo na operação**

Na prática, a Kommo é o seu centro de conversas e de pipeline de vendas: tudo que acontece com o lead fica registrado no cartão e no feed.

## **Regras de ouro (obrigatórias)**

**Regras**

* Todo lead deve ter um responsável definido.

* Todo movimento de etapa deve gerar uma próxima ação (normalmente uma tarefa).

* Toda conversa relevante precisa ficar registrada no cartão (feed).

* Não existe atendimento 'por fora': WhatsApp, Instagram, Telegram, e-mail, tudo precisa estar associado ao lead.

* Sem tarefa, sem follow up: lead parado é lead perdido.

## **Padrões mínimos para rodar**

**SLA sugerido (ajuste conforme operação)**

| Situação | Tempo alvo | Quem executa | Observação |
| :---- | :---- | :---- | :---- |
| Lead novo em horário comercial | Até 5 min | Atendente/SDR | Responder e qualificar |
| Proposta enviada | Até 24 h | Closer | Follow up com valor e próximos passos |
| Sem resposta do lead | D+1, D+3, D+7 | SDR | Cadência com variações |
| **Print sugerido: visão do pipeline principal com etapas** Espaço reservado para imagem (print da tela). |  |  |  |

# **1\. Setup inicial (admin) e arquitetura recomendada**

## **1.1 Usuários, grupos e permissões**

Crie usuários por função e agrupe por times. Recomendação de papéis:

**Papéis e responsabilidades**

| Papel | Foco | Pode editar pipelines? | Pode ver todos os leads? |
| :---- | :---- | :---- | :---- |
| Admin | Configuração e integrações | Sim | Sim |
| Gestor Comercial | KPIs, distribuição e qualidade | Opcional | Sim |
| SDR/BDR/Atendente | Primeiro contato e qualificação | Não | Somente leads do time |
| Closer | Negociação e fechamento | Não | Leads atribuídos |
| CS/Suporte | Pós venda e retenção | Não | Leads/clientes atribuídos |

Passo a passo (alto nível): Configurações \> Usuários \> Adicionar usuário, depois organizar por grupos e limitar acesso conforme necessidade.

| Print sugerido: tela de usuários e grupos Espaço reservado para imagem (print da tela). |
| :---- |

### 

### **1.1.1 Como ler a escala de permissões (negado, se responsável, acesso à equipe, permitido)**

A Kommo usa uma escala de 4 níveis para cada ação (ver, editar, excluir, exportar etc.). Em resumo:

| Nível | O que significa | Quando usar |
| :---- | :---- | :---- |
| Negado | Ação bloqueada. | Dados muito sensíveis ou funções que não deveriam executar a ação. |
| Se responsável | Ação liberada somente se o usuário for o responsável do lead. | Operação padrão para SDR e Closer em pipelines compartilhados. |
| Acesso à equipe | Ação liberada se o responsável do lead estiver no mesmo grupo do usuário. | Times separados por grupo (SDR, Closers, CS). |
| Permitido | Ação liberada em todos os registros. | Admin e Gestão (com cautela para excluir e exportar). |

Boa prática: exportação quase sempre deve ser restrita para reduzir risco de vazamento e erro humano.

### **1.1.2 Grupos: o que são e como usar (ex.: Seção de vendas, Usuários gratuitos)**

Grupos organizam usuários por times e afetam o que aparece quando uma permissão está configurada como 'Acesso à equipe'. Nessa regra, o usuário consegue trabalhar em registros do mesmo grupo do responsável.

Por padrão, a conta costuma ter um grupo como 'Seção de vendas' (time principal). Você pode criar grupos por departamento (SDR/BDR, Closers, CS, Financeiro) para facilitar filtros, relatórios e atribuição.

O grupo 'Usuários gratuitos' é específico para contas do tipo free user. Ao adicionar um usuário e selecionar esse grupo, ele entra no modo de usuário gratuito conforme a configuração do plano.

Usuários gratuitos têm direitos limitados e, normalmente, só enxergam registros que foram compartilhados com eles ou em que foram marcados como responsáveis, dependendo da política de acesso definida pelo admin.

Tradução operacional:

* **Não é para “operador/atendente”** (porque atendente precisa criar tarefa, mover etapa, editar campos, ver listas, etc.).

* **É bom para “stakeholder”** (ex.: dono do negócio que só precisa acompanhar e falar em alguns cards, ou alguém que só precisa visualizar algo pontual).

* Então, não é para 'sempre optar por esse grupo'. Você ganha economia, mas perde operação e visibilidade para o time.

Como criar grupos: Configurações \> Usuários \> menu de três pontos \> Configurações de grupo.

### **1.1.3 Funções (roles): modelos prontos para salvar e reaproveitar**

A tela de permissões permite ajustar o nível de acesso por entidade (Leads, Contatos, Empresas, Tarefas etc.) e por ação (Criar, Ver, Editar, Excluir, Exportar). Depois, use 'Salvar como função' para criar um template e aplicar em novos usuários.

Modelos de função que eu recomendo para agência:

* **Admin:** acesso total e configuração.

* **Gestor:** acesso total aos dados, sem excluir em massa e com exportação limitada (opcional).

* **SDR/BDR/Atendente:** cria leads, vê e edita somente se responsável ou equipe, sem exportar.

* **Closer:** semelhante ao SDR, mas com permissão de mover para etapas de proposta e fechamento.

* **CS/Suporte:** acesso aos pipelines de pós venda e tarefas relacionadas, sem exportar.

* **Financeiro:** acesso a campos financeiros e etapas de cobrança, sem acesso ao restante da negociação (quando aplicável).

### **1.1.4 Permissões especiais por etapa do funil (Pipeline stage)**

Além das permissões gerais, a Kommo permite definir permissões específicas por etapa do funil. Isso é ideal para separar responsabilidades e reduzir movimentações erradas.

Exemplos práticos (recomendados):

* **SDR/BDR** pode criar e qualificar, mas não pode mover para etapas de Proposta ou Fechamento.

* **Closer** pode ver tudo do pipeline comercial, mas só edita e move leads atribuídos a ele ou ao grupo.

* **CS/Suporte** enxerga e edita apenas o pipeline de pós venda, não o comercial (ou vê o comercial apenas leitura).

* **Financeiro** vê e edita apenas etapas de cobrança (ex.: 'Pagamento pendente'), sem acesso ao restante da negociação.

Regra operacional: cada etapa crítica deve ter critério de entrada e próxima ação obrigatória (tarefa).

### **1.1.5 Permissões por campo (Field permissions)**

Use permissões por campo para controlar acesso a dados específicos no cartão do lead, além das permissões gerais. Isso é útil para: proteger dados sensíveis, forçar preenchimento mínimo e reduzir erro operacional.

Sugestão de campos sensíveis (normalmente restritos para Gestão e Financeiro):

* Valor estimado, valor fechado, margem, comissão.

* Condições comerciais e desconto máximo permitido.

* Dados de pagamento, fatura, nota fiscal e status financeiro.

* Contrato, anexos e documentos internos.

* Campos de qualificação internos (ex.: score, classificação, observações do gestor).

Dica: campos podem ser configurados como opcionais ou obrigatórios a partir de determinadas etapas do funil, para padronizar o avanço do lead.

| 🔒 INTERNO EG — Esta seção é para uso da equipe EverGreen O checklist de implantação abaixo descreve o processo interno da agência. Não incluir na versão entregue ao cliente. |
| :---- |

### **1.1.6 Checklist de implantação (agência)**

* Crie os grupos primeiro (SDR/BDR, Closers, CS/Suporte, Financeiro, Gestão).

* Crie as funções (roles) e salve como função para reaproveitar em novos usuários.

* Aplique permissões por etapa para bloquear movimentações indevidas (ex.: só Closer move para Proposta).

* Aplique permissões por campo para proteger dados sensíveis (ex.: valor, margem, contrato).

* Teste com 1 usuário de cada perfil (SDR/BDR, Closer, CS) em um lead de teste antes de liberar para o time inteiro.

Observação: grupos também ajudam em filtros, relatórios e comunicação interna por time.

## **1.2 Pipelines/Funil e estratégia de separação de leads**

Existem 3 modelos comuns. Escolha 1 e evite misturar no início.

**Modelos de arquitetura (multi WhatsApp e times)**

| Modelo | Como separar | Quando usar | Trade-off |
| :---- | :---- | :---- | :---- |
| A) 1 pipeline por número | Pipeline \= WhatsApp 01, WhatsApp 02... | Vários números com operações diferentes | Relatórios consolidados exigem visão multi pipeline |
| B) 1 pipeline por unidade/linha de negócio | Pipeline \= Unidade SP, Unidade RJ... | Times separados por local ou serviço | Precisa de regras claras de roteamento |
| C) 1 pipeline único \+ tags e responsáveis | Etapas e tags por canal/serviço | Operação pequena e centralizada | Fica frágil se o time crescer |

Recomendação para agência com clientes: Modelo B por unidade ou serviço, e dentro de cada pipeline, roteamento por responsável.

**Decisão rápida**

* Se você tem 2+ números e cada número atende um público diferente, use Modelo A.

* Se você tem 2+ times (SDR e Closer) e 1 operação principal, use Modelo C com regras rígidas.

* Se você tem filiais, produtos ou serviços distintos, use Modelo B.

| Print sugerido: lista de pipelines e etapas Espaço reservado para imagem (print da tela). |
| :---- |

### **1.2.1 Regra principal: pipeline é status, não é canal nem oferta**

Pipeline deve representar a fase do processo (o "onde está" no funil). Canal de origem (WhatsApp, cold call, e-mail, LinkedIn) e oferta (IA, Growth, recorrência, webinar) devem ser classificados preferencialmente em campos e, quando fizer sentido, tags padronizadas.

### **1.2.2 Como decidir a arquitetura em 10 minutos**

Escolha 1 modelo como padrão. Evite misturar muitos modelos no início.

* Modelo A: 1 pipeline por número ou canal principal. Use quando números atendem públicos totalmente diferentes e precisam de SLAs e regras muito distintas.

* Modelo B: 1 pipeline por unidade, linha de negócio ou produto. Use quando existem times separados por serviço ou região, com metas e processos diferentes.

* Modelo C: 1 pipeline único \+ responsável \+ campos/tags. Use quando a operação é pequena e você quer máximo de consolidação em relatórios.

Para a EG (times diferentes por frente), o desenho mais limpo costuma ser:

* Pipeline 01: EG | Inbound (leads que chegam).

* Pipeline 02: EG | Outbound (prospecção ativa).

* Pipeline 03 opcional: EG | Pós-venda / CS (implantação, renovação, suporte).

### **1.2.3 Blueprint recomendado para a agência (Inbound \+ Outbound)**

A) Pipeline EG | Inbound (processo de entrada)

1. 01 Novo lead (mensagem recebida / formulário)

2. 02 Qualificação inicial (3 perguntas \+ campos mínimos)

3. 03 Reunião agendada

4. 04 Reunião realizada (diagnóstico)

5. 05 Proposta enviada

6. 06 Negociação

7. 07 Fechado ganho

8. 08 Fechado perdido (motivo obrigatório)

9. 09 Nurturing (quando ainda não é o momento, mas vale nutrir)

B) Pipeline EG | Outbound (prospecção)

1. 01 Lista / Prospect

2. 02 Em prospecção (cadência ativa)

3. 03 Respondeu

4. 04 Qualificação

5. 05 Reunião marcada

6. 06 Reunião realizada

7. 07 Proposta enviada

8. 08 Negociação

9. 09 Nurturing (retorno futuro)

10. Venda ganha

11. Venda perdida

Observações práticas

* Use numeração (01, 02, 03...) nos nomes das etapas. Isso mantém a ordem e evita bagunça quando você duplicar para clientes.

* Tenha critério de entrada e próxima ação obrigatória por etapa. Exemplo: ao entrar em "Proposta enviada", criar tarefa automática de follow-up em 24h.

* Não crie etapa para cada canal (WhatsApp, e-mail, LinkedIn). Isso explode o funil e destrói os relatórios. Canal deve ser campo/tag.

\- Nurturing não é depósito. Lead em Nurturing é lead ATIVO e conta no limite do plano (regra junho/2026). Defina um teto de permanência (ex.: 60-90 dias). Esgotado sem evolução, mova para Fechado \- Perdido com motivo e tag de reativação (ex.: mot\_sem\_timing \+ \#ReativarEm90d). Isso preserva o histórico, libera o limite e mantém o lead recuperável. Nunca acumular em Nurturing nem deletar.

### **1.2.4 Taxonomia de tags e campos (o que vai aonde)**

Regra prática: campo para classificação estável e relatório. Tag para marcação rápida e temporária.

Campos recomendados (para relatórios e roteamento)

* Origem canal (lista): WhatsApp, Instagram, LinkedIn, E-mail, Indicação, Tráfego pago, Site, Evento.

* Origem detalhada (texto): nome da campanha, anúncio, grupo, lista, evento específico.

* Tipo de entrada (lista): Inbound, Outbound.

* Oferta (lista): IA (Agentes), Growth (máquina de vendas), Execução recorrente, Consultoria, Treinamento.

* Modelo de conversão (lista): Chamada direta, Diagnóstico, Webinar, Evento presencial, Trial.

* ICP/Segmento (lista): Contabilidade, Jurídico, Saúde, E-commerce, Indústria, Outros.

* Temperatura (lista): Cold, Warm, Hot (defina regras claras).

* Próximo passo (lista curta): Reunião, Proposta, Follow-up, Nutrir, Encerrar.

Tags recomendadas (com prefixo para organizar)

* ch\_ (canal): ch\_whatsapp, ch\_linkedin, ch\_email, ch\_call.

* of\_ (oferta): of\_IA, of\_growth, of\_recor, of\_treinamento.

* mdl\_ (modelo de conversão): mdl\_webinar, mdl\_diagnostico, mdl\_evento.

* mot\_ (motivo de perda): mot\_preco, mot\_sem\_timing, mot\_sem\_fit, mot\_sem\_resposta.

Importante: mantenha poucas tags. Se passar de 25-30 tags ativas, você perde consistência.

### **1.2.5 Estratégia de separação por time (SDR/BDR, Closer, CS)**

Mesmo com 2 pipelines, a separação "quem faz o quê" deve ser garantida por responsável, grupos e permissões por etapa.

* BDR: atua até "Qualificação" e "Reunião agendada". Não move para "Proposta enviada" e não fecha.

* Closer: atua de "Reunião agendada" em diante. Pode editar valores e negociar (campos sensíveis podem ficar restritos).

* CS/Pós-venda: atua em pipeline próprio de pós-venda, ou tem acesso somente leitura ao comercial.

## **1.3 Chats, Inbox e atribuição**

Chats é a caixa de entrada unificada. A regra é atribuir conversas para evitar sobreposição e perda de contexto.

**Padrões de inbox**

* Cada conversa deve ter um responsável.

* Se o responsável mudar, registrar nota curta do motivo e criar tarefa para o novo dono.

* Mensagens devem ser respondidas dentro do SLA do canal.

| Print sugerido: Chats com conversa atribuída e botão para abrir cartão Espaço reservado para imagem (print da tela). |
| :---- |

### **1.3.1 Integração WhatsApp (coexistência) vs. WABA e a janela de 24h**

Antes de configurar qualquer automação de mensagem, é preciso entender em qual modo de integração a conta opera. Isso define o que é possível ou não no canal.

**Coexistência vs. API oficial (WABA)**. Na maioria das implantações,

o WhatsApp é integrado em modo coexistência: o número segue funcionando

no app/WhatsApp Business normal E no Kommo, simultaneamente, sem

migração nem perda de histórico. Conexão feita via Meta Business

Platform (escaneamento de QR Code), na máquina/celular de quem já usa

o número. A Meta solicita reabrir o app no celular periodicamente

(\~30 dias) para manter a sessão ativa — sem impacto se o número é

usado diariamente.

**Janela de 24h**. Toda vez que o contato envia uma mensagem, abre-se

uma janela de 24h em que é possível responder livremente (texto,

arquivos, catálogos, automações). Fora dessa janela, só é permitido

enviar mensagens via template pré-aprovado (HSM). Por isso:

\- Automações de "resposta imediata" (ex.: envio automático de catálogo)

devem disparar NO MOMENTO da entrada do lead, quando a janela está

aberta — não agendadas para depois.

\- Follow-ups fora da janela exigem template aprovado ou contato manual

iniciado pelo time.

**O que coexistência permite:**

\- Receber/responder no Kommo (omnichannel), automações dentro da

janela de 24h, ações rápidas, criação automática de lead/contato.

**O que coexistência NÃO permite:**

\- WhatsApp Commerce (catálogo/carrinho nativo do WhatsApp) — exige

API oficial (WABA), não funciona em coexistência.

\- Templates em massa e alguns recursos de automação avançada são mais

limitados; migração para WABA é avaliada caso a caso no setup.

**Modelos de integração**

| Recurso | Coexistência | WABA (Oficial) |
| :---- | :---- | :---- |
| Conexão | QR Code / Meta Platform | Migração para API Meta |
| App no celular | Sim | Não |
| Histórico prévio | Preservado | Não migra |
| Respostas livres | Dentro da janela | Sim |
| Massa / HSM | Não permitido | Sim |
| Commerce nativo | Não permitido | Sim |
| Salesbot | Sim (janela) | Sim |
| Custo variável | Isento | Cobrança por conversa |

Recomendação EverGreen: inicie via coexistência para operações de baixo volume e planeje o upgrade para WABA conforme surja a necessidade de nutrição em lote ou disparos fora da janela de 24h.

**Janela de 24h e regras da Meta**

A cada interação do contato, inicia-se um período de 24h permitindo o envio de mensagens livres (arquivos, áudio, bots). Expirado este prazo, o canal bloqueia o envio livre, exigindo templates HSM pré-aprovados e uso da API oficial. Impactos operacionais:

* **Resposta imediata:** triagem e boas-vindas devem ocorrer assim que o lead entra, aproveitando a janela aberta.

* **Follow-up padrão:** perfeitamente funcional em coexistência se realizado dentro do ciclo de 24h.

* **Leads inativos:** reativação de contatos frios não é possível via WhatsApp simples; utilize outros canais ou migre para WABA.

**Setup da conexão (Coexistência)**

1. Navegue até Configurações \> Canais de comunicação \> WhatsApp.

2. Selecione a opção de conexão via Business Platform.

3. Siga as instruções nativas da Meta.

4. Escaneie o QR Code através do menu de Aparelhos Conectados no dispositivo original.

5. Atenção: abra o aplicativo no celular mensalmente para validar a sessão.

| Print sugerido: interface de conexão WhatsApp via Business Platform Espaço reservado para imagem (print da tela). |
| :---- |

## **1.4 Campos e layout do cartão (padronização)**

Crie um conjunto mínimo de campos para todos os leads. Padronize nomes e formatos para permitir filtros e relatórios.

**Campos mínimos recomendados**

Campos base (quase sempre obrigatórios):

* Nome e telefone (ou identificador do canal).

* Origem (inbound, outbound, indicação, evento, anúncios etc.).

* Canal de entrada (WhatsApp, Instagram, ligação, e-mail, LinkedIn, site).

* Oferta (IA, Growth, consultoria, recorrência, executivo etc.).

* Modelo de conversão (Chamada direta, diagnóstico, webinar, evento presencial, trial).

* Responsável (dono do lead) e time (Inbound ou Outbound).

* Status de qualificação (Novo, Em qualificação, Qualificado, Desqualificado).

* Próximo passo (campo curto) e data do próximo contato (normalmente via tarefa).

Campos comerciais (recomendados para previsibilidade):

* Valor estimado do contrato e ticket esperado.

* Probabilidade (se você usar) e previsão de fechamento (data).

* Motivo de perda (lista fechada).

* Concorrente (opcional, lista fechada) e objeção principal (lista fechada).

**Campos obrigatórios por etapa (exemplo prático)**

A regra é: ao mover de etapa, o atendente precisa preencher o mínimo daquela etapa. Se faltar, não move. Isso é onde o CRM vira processo, não só cadastro.

* Etapa 'Qualificação': origem, oferta, canal, necessidade resumida.

* Etapa 'Reunião marcada': data e horário da reunião, link (ou local), participante decisor.

* Etapa 'Proposta enviada': valor, validade, link do documento, data de follow-up.

* Etapa 'Fechado perdido': motivo de perda e próxima ação (reativação em X dias, se fizer sentido).

**Padronização para não virar bagunça**

* Prefira listas (dropdown) em vez de texto livre para origem, oferta, motivo de perda e canal.

* Use tags só para situações temporárias ou transversais (ex.: \#Urgente, \#AguardandoResposta, \#ReativarEm30d).

| Print sugerido: layout do cartão do lead com campos destacados Espaço reservado para imagem (print da tela). |
| :---- |

## **1.5 Tarefas e calendário**

Tarefas sustentam o follow up. Defina tipos de tarefa e uma regra: toda etapa ativa precisa de uma tarefa futura.

**Tipos de tarefa recomendados**

* Follow up

* Reunião

* Ligar

* Enviar proposta

* Cobrança/Documentos

* Pós venda

**Regras de ouro de tarefas (padrão EverGreen)**

* Todo lead ativo deve ter pelo menos 1 tarefa futura. Se não tem, está abandonado.

* Cada tarefa precisa de: responsável, data/hora, descrição curta e próximo passo claro.

* Se o lead avançou de etapa, a tarefa antiga é concluída e uma nova tarefa é criada no mesmo momento.

* Evite tarefas genéricas como 'ver depois'. Use ação concreta: 'Ligar para confirmar reunião', 'Follow-up proposta', 'Enviar briefing'.

Padrão de nomenclatura (para ficar pesquisável):

* \[Canal\] Ação \+ contexto. Ex.: \[WhatsApp\] Follow-up proposta X

* \[Ligação\] Confirmar decisor e próximos passos

* \[E-mail\] Enviar contrato e solicitar assinatura

**Como usar o Calendário na rotina**

* Comece o dia pelo Calendário para ver o que vence hoje.

* Para agendar reuniões com o lead, usar o agendamento nativo da Kommo (jun/2026) em vez de ferramenta externa: link de reserva, horário de trabalho e lembrete automático ficam dentro do CRM.

* Use filtros por pipeline, responsável e tipo de tarefa.

* Gestor revisa: tarefas vencidas, leads sem tarefa e leads parados na mesma etapa.

| Print sugerido: Calendar com tarefas e tipos Espaço reservado para imagem (print da tela). |
| :---- |

**1.6 Templates de resposta e personalização**

Crie templates curtos, com variáveis, e treine o time a editar antes de enviar.

**Templates essenciais (mínimo viável)**

| Nome | Quando usar | Texto base (ajuste) | Observação |
| :---- | :---- | :---- | :---- |
| Primeiro contato | Lead novo | Oi {Nome}, vi seu contato por {Origem}. Qual é seu objetivo principal hoje? | 1 pergunta por vez |
| Agendar conversa | Após qualificação | Perfeito. Posso te ligar em 2 horários: {Op1} ou {Op2}. Qual prefere? | Sempre ofereça 2 opções |
| Follow up D+1 | Sem resposta | Passando para confirmar se ainda faz sentido falarmos sobre {Serviço}. Posso te ajudar com algo? | Sem pressão |
| **Print sugerido: tela de templates (respostas rápidas)** Espaço reservado para imagem (print da tela). |  |  |  |

# **2\. Leads, contatos e empresas: estrutura e cartão**

## **2.1 Conceitos**

Use esta regra prática:

**Definições**

* Lead: oportunidade em andamento no pipeline.

* Contato: pessoa com quem você conversa.

* Empresa: organização vinculada a um ou mais contatos e leads.

**Relacionamentos 1:1 e 1:N (para não confundir)**

Pense assim:

* Um contato pode ter vários leads (1:N). Ex.: mesma pessoa pede 'IA' hoje e 'Growth' daqui 2 meses. São oportunidades diferentes, então leads diferentes.

* Uma empresa pode ter vários contatos e vários leads (1:N). Ex.: empresa cliente tem decisor, financeiro e operação.

* Um lead pode ter mais de um contato associado (N:1). Ex.: você vende para 2 sócios que decidem juntos.

Regra prática EverGreen: 1 lead \= 1 oportunidade (uma venda ou um projeto). Se surgir um novo interesse que vira outra oportunidade, crie um novo lead e conecte ao mesmo contato/empresa.

**Quando um novo contato manda mensagem (WhatsApp, Instagram, etc.)**

* Se o recurso 'Incoming leads' estiver ativo, uma nova conversa de alguém ainda não qualificado pode cair em uma etapa de entrada (incoming) do funil. A partir daí, você aceita, atribui responsável e começa o processo.

* Dependendo do canal e da configuração, a Kommo pode criar automaticamente um contato e um lead vinculados ao primeiro evento de mensagem. O lead vira o 'cartão' de trabalho, e o contato fica como pessoa vinculada.

* Se a mesma pessoa falar por outro mensageiro, pode aparecer um novo lead na entrada. A regra é revisar, mesclar quando for a mesma pessoa e manter o histórico organizado.

Atenção (regra junho/2026): lead parado na etapa de entrada agora CONTA no limite de leads ativos do plano. Antes, leads recebidos não eram contabilizados; hoje são. Não deixe conversas acumularem na entrada sem tratamento: aceite, qualifique e mova, ou encerre como Fechado \- Perdido. Lead de entrada não processado consome limite e, no agregado, pode travar a operação (ver seção 6).

**O que automatizar vs o que preencher manualmente**

Automatize o que é objetivo e repetitivo, e deixe manual o que exige interpretação.

Boa automação (objetivo):

* Preencher origem e canal automaticamente (pela fonte do chat ou formulário).

* Aplicar tag do canal (\#WhatsApp, \#Instagram, \#Ligação) ou campo 'Canal de entrada'.

* Criar tarefa imediata 'Responder em X' ao entrar na etapa de entrada.

* Atribuir responsável por regra (rodízio, carga, grupo).

Bom preenchimento manual (interpretação):

* Necessidade e contexto (resumo de 1 a 2 linhas).

* Orçamento, urgência e decisor.

* Qualificação (quente, morno, frio) e próximos passos.

Obs.: as configurações detalhadas de automação e distribuição aparecem nas seções 5, 6 e 7\.

## **2.2 Como criar ou importar leads**

Você pode criar manualmente ou importar via planilha (CSV). Para importação avançada, use colunas Pipeline e Lead status com nomes idênticos aos da Kommo.

| Print sugerido: tela de importação de planilha Espaço reservado para imagem (print da tela). |
| :---- |

## **2.3 Anatomia do cartão de lead**

O cartão é onde mora o histórico e o próximo passo. Campos, feed, arquivos, tarefas e responsáveis devem ser visíveis.

| Print sugerido: cartão do lead aberto com feed e tarefas visíveis Espaço reservado para imagem (print da tela). |
| :---- |

## **2.4 Movendo o lead entre etapas**

**Regras para mover etapas**

* Mover etapa só quando houver evidência (resposta, reunião marcada, proposta enviada).

* Ao mover, criar tarefa correspondente.

* Ao perder, registrar motivo de perda e, se aplicável, tag do motivo.

| Print sugerido: mover lead de etapa e registrar motivo Espaço reservado para imagem (print da tela). |
| :---- |

# **3\. Atendimento (Chats) e padrões de resposta**

## **3.1 Onde o time trabalha**

Fluxo recomendado: Inbox (Chats) para responder, e cartão para registrar contexto e criar tarefa.

| Print sugerido: Chats com atalho para abrir cartão Espaço reservado para imagem (print da tela). |
| :---- |

## **3.2 Script operacional (atendente/SDR)**

**Fluxo padrão de atendimento**

| Passo | Ação | Saída esperada |
| :---- | :---- | :---- |
| 1 | Responder dentro do SLA | Lead engajado |
| 2 | Fazer 3 perguntas (dor, meta, prazo) | Qualificação mínima |
| 3 | Preencher campos essenciais | Dados padronizados |
| 4 | Criar tarefa | Follow up garantido |
| 5 | Mover etapa | Pipeline atualizado |

## **3.3 Padrões de escrita**

**Boas práticas**

* Mensagens curtas e objetivas.

* Uma pergunta por vez.

* Confirmar entendimento antes de propor solução.

* Evitar áudio longo; se usar, resumir em texto no cartão.

## **3.4 App mobile (iOS / Android)**

A Kommo tem app nativo para iOS e Android. Boa parte do time atende pelo celular, mas há diferenças importantes em relação à versão web.

**O que funciona no app**

| Funcionalidade | Disponibilidade |
| :---- | :---- |
| Chats (inbox, resposta, notas) | ✅ Completo |
| Cartão do lead (ler e editar campos) | ✅ Completo |
| Criar e concluir tarefas | ✅ Completo |
| Mover lead entre etapas do pipeline | ✅ Completo |
| Notificações push (nova mensagem, tarefa) | ✅ Completo |
| Visualizar pipeline e filtros | ✅ Completo |
| Gravar e enviar áudio pelo WhatsApp | ✅ Disponível |

**Limitações do app (só na web)**

* Bots e Salesbot não disparam quando o usuário está apenas no app — a lógica roda no servidor, mas configuração só pela web.

* Pipeline Triggers (Digital Pipeline): configurar apenas na web.

* Criação de campos personalizados, grupos, funções e permissões: apenas na web.

* Integração de canais (conectar WhatsApp, Instagram, etc.): apenas na web.

* Relatórios avançados e configuração de metas: apenas na web.

* Módulo Segmentos: apenas na web.

| Regra prática: app \= atendimento e follow-up no campo. Configuração, setup e relatórios ficam sempre na web. Oriente o time a nunca tentar mudar configurações pelo celular. |
| :---- |

**Dicas de uso no app**

* Ative notificações push para novos leads e tarefas vencidas — é a única forma de não perder o SLA quando o atendente está fora do computador.

* Use o atalho de cartão dentro do chat (ícone lateral) para preencher campos sem sair do Chats.

* Tarefas vencidas aparecem com destaque no app; revise ao abrir o dia.

* Em iOS, o app pode ser adicionado à tela inicial como atalho para acesso rápido.

# **4\. Separação e distribuição de leads (manual e automática)**

Este é o coração da previsibilidade. A meta é eliminar disputa por lead e garantir que todo lead seja atendido.

## **4.1 Separar leads: canal, número, serviço e unidade**

**Matriz de separação (modelo)**

| Critério | Como implementar | Exemplo |
| :---- | :---- | :---- |
| Número de WhatsApp | Pipeline por número ou campo Origem | WhatsApp 01, WhatsApp 02 |
| Serviço/Produto | Campo Serviço \+ regras de roteamento | Implantação, Suporte, Consultoria |
| Unidade/Região | Pipeline por unidade ou tag | SP, RJ, Sul |
| Nível do lead | Tag \+ etapa | Hot, Warm, Cold |

## **4.2 Distribuição manual (mínimo viável)**

**Quando usar manual**

* Time pequeno (1 a 3 pessoas).

* Baixo volume de leads.

* Operação em validação.

**Procedimento de distribuição manual**

| Passo | Ação |
| :---- | :---- |
| 1 | Abrir o cartão do lead |
| 2 | Alterar responsável para o atendente correto |
| 3 | Registrar nota curta do motivo |
| 4 | Criar tarefa para o novo responsável (se necessário) |
| **Print sugerido: alterar responsável do lead** Espaço reservado para imagem (print da tela). |  |

## **4.3 Distribuição automática (Round Robin)**

Para distribuir automaticamente entre atendentes, use Round Robin dentro do Salesbot. Ele permite alternar ações e responsáveis em sequência circular.

**Pré-requisitos**

* Atendentes criados como usuários.

* Regra clara: qual gatilho inicia a distribuição (lead criado, mensagem recebida, etapa específica).

* Definição do que acontece quando atendente está offline.

**Configuração recomendada (modelo)**

| Item | Configuração |
| :---- | :---- |
| Gatilho | Novo lead em 'Entrada' ou primeira mensagem recebida |
| Ação 1 | Round Robin: atribuir responsável |
| Ação 2 | Criar tarefa: responder em 15 min |
| Ação 3 | Enviar mensagem interna de notificação |

Atenção (regra junho/2026): ao atingir o limite de leads ativos do plano, a Kommo PARA de processar novos leads. O Round Robin deixa de atribuir, e os novos leads ficam sem responsável e sem SLA, sem mensagem de erro evidente. Se o time relatar "leads chegando sem dono", a primeira hipótese é limite atingido (ver seção 6 e seção 9).

| Print sugerido: Salesbot com bloco Round Robin Espaço reservado para imagem (print da tela). |
| :---- |

## **4.4 Handoff SDR \-\> Closer (repasse)**

Quando o lead estiver qualificado, o SDR repassa para o Closer. O repasse precisa ser padronizado.

**Critério mínimo de repasse (exemplo)**

| Campo | Critério |
| :---- | :---- |
| Dor/Objetivo | Claro e confirmado |
| Prazo | Definido (ex.: 30 dias) |
| Orçamento | Faixa ou sinal de capacidade |
| Autoridade | Quem decide identificado |
| Próximo passo | Reunião agendada ou proposta solicitada |

**Formato da nota de repasse (copiar e colar)**

* Resumo: {dor principal} \+ {meta} \+ {prazo}

* Contexto: {origem} \+ {canal} \+ {número} \+ {tags}

* BANT: Budget {x}, Authority {x}, Need {x}, Timeline {x}

* Acordos: {o que ficou combinado}

* Próxima ação: {tarefa} até {data/hora}

| Print sugerido: lead com nota de repasse e tarefa para closer Espaço reservado para imagem (print da tela). |
| :---- |

# **5\. Tarefas e rotinas (SLA, tipos, calendário)**

## **5.1 Regra central**

Todo lead ativo deve ter pelo menos 1 tarefa futura. Sem tarefa, o lead tende a morrer no funil.

## **5.2 Tipos de tarefa e convenções**

**Convenção de título de tarefa**

| Tipo | Formato sugerido | Exemplo |
| :---- | :---- | :---- |
| Follow up | FU \- {canal} \- {motivo} | FU \- WhatsApp \- confirmar reunião |
| Reunião | Call \- {etapa} \- {objetivo} | Call \- Diagnóstico \- entender cenário |
| Proposta | Proposta \- {valor} \- {data} | Proposta \- R$ 5k \- hoje |
| Documentos | Docs \- {tipo} \- {prazo} | Docs \- contrato \- D+2 |

## **5.3 Matriz de tarefas por etapa (exemplo)**

**Tarefas por etapa do pipeline**

| Etapa | Tarefa obrigatória | Prazo | Responsável padrão |
| :---- | :---- | :---- | :---- |
| Entrada | Responder e qualificar | 15 min | Atendente/SDR |
| Qualificado | Agendar reunião | 24 h | SDR |
| Reunião marcada | Confirmar presença | D-1 | SDR/Closer |
| Proposta | Follow up proposta | 48 h | Closer |
| Fechado \- ganho | Onboarding/Entrega | 24 h | CS/Entrega |
| **Print sugerido: calendário com tarefas e filtros por responsável** Espaço reservado para imagem (print da tela). |  |  |  |

# **6\. Automações e cadência (Pipeline Triggers e Salesbot)**

## **6.1 Pipeline Triggers (Digital Pipeline)**

Use triggers para criar tarefas ao entrar em etapas e para garantir cadência mínima.

**Automações essenciais (versão 1.0)**

| Gatilho | Ação | Resultado |
| :---- | :---- | :---- |
| Lead entra em Entrada | Criar tarefa 'Responder em 15 min' | SLA garantido |
| Lead entra em Proposta | Criar tarefa 'Follow up em 48 h' | Proposta não morre |
| Lead fica 3 dias na mesma etapa | Criar tarefa 'Revisar lead' | Evita estagnação |

IMPORTANTE (regra junho/2026): os Pipeline Triggers param de disparar para novos leads quando a conta atinge o limite de leads ativos. As tarefas de SLA ("responder em 15 min", "follow up em 48h") deixam de ser criadas automaticamente. Mantenha a conta abaixo do limite encerrando leads mortos e limpando a entrada (ver seção 6.4).

| Print sugerido: Pipeline Triggers configurado na etapa Espaço reservado para imagem (print da tela). |
| :---- |

## **6.2 Salesbot**

Salesbot é o motor de automações conversacionais. Use primeiro para triagem, distribuição e fora do horário.

Esclarecimento importante: o Salesbot é um bot de REGRAS (gatilho/condição), não o "Agente de IA" (LLM) da Kommo. Os 3 bots abaixo continuam disponíveis em todos os planos, inclusive Básico. A partir de junho/2026, o Agente de IA (resposta autônoma por LLM) saiu do plano Básico e exige Avançado ou superior. Triagem, Round Robin e atendimento fora do horário NÃO dependem do Agente de IA e seguem funcionando no Básico.

Atenção: ao atingir o limite de leads ativos, o Salesbot também para de rodar para novos leads. Triagem e distribuição quebram silenciosamente.

**Mapa de ferramentas de automação**

Antes de iniciar qualquer configuração, identifique a ferramenta ideal para cada cenário. As lógicas e restrições variam conforme o recurso escolhido.

| Ferramenta | O que faz | Plano mínimo | Coexistência |
| :---- | :---- | :---- | :---- |
| Pipeline Trigger | Gera tarefas e muda etapas por eventos | Básico | Sim |
| Salesbot (regras) | Mensagens e triagem por gatilho fixo | Básico | Janela 24h |
| AI Agent (LLM) | Respostas autônomas e linguagem natural | Avançado+ | Janela 24h |
| Segmentos | Públicos dinâmicos, transmissão, reativação (ver \#6.6) | Advanced (Ads: Pro)  | Parcial |

Regra de ouro: use Pipeline Trigger para processos internos, Salesbot para triagens fixas, AI Agent para conversas fluidas e Segmentos para nutrição em escala.

**Salesbot (bot de regras)**

Trabalha via fluxograma visual (Gatilho → Condição → Ação). Executa comandos literais sem interpretação subjetiva.

**Estrutura de um fluxo de Salesbot**

* **Gatilho:** o evento iniciador (ex.: entrada de lead, palavra-chave, horário específico).

* **Condição:** filtros de segmentação (ex.: canal, origem do anúncio, estado/região).

* **Ação:** a tarefa executada (ex.: atribuir dono, criar tarefa, preencher campos).

* **Mensagem:** conteúdo interativo com botões ou variáveis como {Nome}.

**Bots essenciais para implantar primeiro**

* **Bot 1 — Boas-vindas e triagem:** focado em coletar dados mínimos (produto, cidade) logo na entrada via WhatsApp.

* **Bot 2 — Fora de horário:** informa a indisponibilidade e garante a criação de tarefa para o início da operação.

* **Bot 3 — Confirmação de visita:** dispara detalhes de agendamento quando o lead atinge etapas de showroom ou reunião.

Cuidado: o limite de leads ativos trava a execução do Salesbot sem alertas prévios. Mantenha o pipeline limpo para evitar interrupções.

| Print sugerido: editor de fluxo do Salesbot com gatilho, condição e ação Espaço reservado para imagem (print da tela). |
| :---- |

## **6.3 AI Agent (Agente de IA com LLM)**

Diferente do Salesbot, o AI Agent utiliza processamento de linguagem natural para compreender intenções e responder autonomamente com base no contexto do lead.

**O que o AI Agent faz**

* Processa dúvidas técnicas e comerciais usando o histórico do cartão.

* Decifra intenções de compra sem depender de menus de botões.

* Alimenta campos do CRM através da extração de dados da conversa.

* Transfere para humanos em casos complexos ou solicitações diretas.

**Como configurar**

1. Acesse as configurações do AI Agent no menu do sistema.

2. Defina as instruções de persona: tom de voz, escopo e limites de atuação.

3. Carregue a base de conhecimento (FAQs, manuais, scripts).

4. Vincule aos canais desejados e estabeleça o cronograma de ativação.

5. Realize simulações em ambiente de teste antes do go-live.

**Quando ativar**

* Saturação de dúvidas repetitivas ou equipe sobrecarregada.

* Necessidade de cobertura 24/7 sem atendimento humano disponível.

**Quando NÃO ativar (ou ativar com cautela)**

* **Vendas complexas/High Ticket:** a falta de toque humano pode comprometer a confiança.

* **Serviços muito customizados:** risco de alucinação em informações com muitas variáveis.

* **Pós-venda estabelecido:** clientes antigos costumam exigir prioridade humana.

Requisito: Plano Avançado ou Pro. Recurso indisponível no plano Básico desde jun/2026.

| Print sugerido: tela de configuração do AI Agent com campo de instruções Espaço reservado para imagem (print da tela). |
| :---- |

## **6.4 Cadência de follow up (modelo 7 dias)**

**Cadência exemplo (ajuste mensagem e horários)**

| Dia | Objetivo | Mensagem base |
| :---- | :---- | :---- |
| D0 | Confirmar demanda | Oi {Nome}, vi seu contato sobre {Serviço}. Qual é o principal objetivo agora? |
| D1 | Gerar valor | Separei 2 ideias rápidas para seu caso. Quer que eu te envie? |
| D3 | Retomar | Conseguiu ver minha mensagem? Se preferir, te ligo em 10 min. |
| D5 | Alternativa | Se não for prioridade agora, posso te mandar um resumo e retomar mais para frente. |
| D7 | Encerrar com porta aberta | Vou pausar por aqui para não te incomodar. Quando fizer sentido, é só responder que retomamos. |

Onde construir a cadência em escala: o módulo Segmentos (novo, jun/2026) centraliza transmissões e nutrição em lote. Use Segmentos para campanhas de reativação e disparos para públicos salvos, em vez de criar tarefas manuais uma a uma.

## **6.5 Disparos fora da janela de 24h: como atingir leads frios**

Este ponto gera recorrentes dúvidas na operação. A viabilidade técnica depende estritamente do modelo de integração (coexistência vs. WABA).

**Diagrama de decisão**

| Cenário: Coexistência | Cenário: WABA (API Oficial) |
| :---- | :---- |
| Envio bloqueado pelo WhatsApp. Adotar canais alternativos. | Permitido via HSM (template aprovado) em Segmentos ou bots. |

**Em coexistência: alternativas para leads frios**

| Opção | Uso ideal | Execução no Kommo |
| :---- | :---- | :---- |
| Telefone | Contatos recentes e quentes | Tarefa de ligar com roteiro |
| E-mail | Possuindo o dado no cadastro | Disparo via aba e-mail no lead |
| Instagram | Leads advindos desse canal | Resposta via omnichannel |
| Aguardar | Frios e sem prioridade imediata | Uso do módulo Segmentos |
| Upgrade WABA | Necessidade de escala e reativação | Consultar fluxo de migração |

**Em WABA: HSM templates e disparos em lote**

Formatos HSM são obrigatórios para diálogos iniciados pela empresa fora da janela ativa. Exigem validação prévia pela Meta.

**Fluxo de aprovação de template HSM**

* Acessar o Gerenciador de WhatsApp no Business Manager da Meta.

* Configurar modelo: definir nome, categoria técnica e conteúdo.

* Implementar variáveis dinâmicas seguindo o padrão \`{{n}}\`.

* Aguardar auditoria (geralmente concluída em poucas horas).

* Utilizar modelos aprovados no Salesbot ou Transmissões da Kommo.

Dica de custo: categorias Utilitárias são mais acessíveis que Marketing. Priorize Utilitárias para avisos e follow-ups transacionais.

**Disparos em lote via Módulo Segmentos (jun/2026)**

O recurso permite isolar audiências específicas baseadas em campos ou tags do CRM para ações de transmissão massiva.

**Passo a passo operacional**

1. Navegar até a seção Segmentos na barra lateral.

2. Definir filtros de audiência (status, ausência de tarefas, etc.).

3. Selecionar Transmissão e vincular o HSM aprovado.

4. Monitorar métricas de entrega diretamente no cartão do lead.

Nota crítica: em modo coexistência, transmissões dependem de diálogos pré-existentes. A garantia total de entrega em base fria só ocorre via WABA.

**Quando recomendar migração para WABA**

A transição para API oficial é recomendada quando houver necessidade de:

* Reativação massiva de contatos inativos.

* Alertas automáticos sem interação prévia do lead.

* Uso de carrinhos e catálogo nativo (Commerce).

* Volume de mensagens que comporte o modelo de custos Meta.

Observação: o número é preservado, porém o histórico de chats não é portado para a nova interface.

| Print sugerido: visão do módulo Segmentos e disparos em massa Espaço reservado para imagem (print da tela). |
| :---- |

# **6.6 Segmentos: públicos dinâmicos, nutrição e reativação**

O módulo Segmentos ganhou seção própria no menu lateral a partir de 1º/jun/2026 (antes ficava escondido dentro de Transmissões). É a forma nativa da Kommo de criar públicos reutilizáveis e acioná-los em transmissão, anúncios e nutrição. 

## **O que é**

Segmento é um público dinâmico definido por condições, não uma lista estática. O lead entra e sai do segmento automaticamente conforme atende ou deixa de atender as regras. Exemplo: o segmento "Perdidos por preço nos últimos 90 dias" perde um lead automaticamente se ele for reaberto e ganho. 

**Diferença entre as quatro formas de agrupar:**

| Mecanismo | O que é | Quando usar |
| :---- | :---- | :---- |
| Campo | Dado estruturado no cartão (UF, produto) | Classificar e filtrar o lead individualmente |
| Tag | Etiqueta livre aplicada ao lead | Marcação pontual e flexível; Evitar como estrutura primária |
| Filtro | Busca temporária na lista de lead | Consulta do dia a dia, não persiste |
| Segmento | Público salvo e dinâmico por condições | Reusar o mesmo público em transmissão, anúncio e nutrição |

Regra de ouro: filtro é para olhar agora; segmento é para acionar de novo depois. Se você vai usar o mesmo recorte mais de uma vez, é segmento.

## **Regras por plano (corrigida jun/2026)**

**Atenção — houve renomeação de planos (ver \#10). A regra correta:** 

| Recurso | Plano mínimo |
| :---- | :---- |
| Criar segmento e usar em transmissão/mensagem em lote | Advanced |
| Enviar segmento como público para Meta/Google Ads | Pro |
| AI Analyst sobre segmentos (análise de performance)  | Pro |

O plano Base não cria segmentos para transmissão. Durante o trial de 14 dias a conta tem acesso completo (nível Pro), então Segmentos aparece funcionando — mas o recurso some ao migrar para Base. Nunca prometer Segmentos a cliente que vai fechar no Base.

Permissão: apenas usuários Administrador acessam, criam e editam segmentos. Operador comum (ex.: atendente) não enxerga o módulo.

## **Como funciona na prática**

* Acesse a aba Segmentos no menu esquerdo.

* Adicione condições, que podem ser cruzadas: etapa do funil \+ origem \+ valor \+ data da última conversa. Ex.: "Leads na etapa Reunião Realizada" \+ "Origem: Meta Ads" \+ "Valor \> R$ 10.000". 

* Salve. A lista passa a operar dinamicamente dentro do CRM.

* Para acionar: selecione o segmento e clique em Nova transmissão (mensagem em lote) ou Usar em anúncios (envio para Ads).

## **Quando usar**

* **Reativação comercial:** "perdidos por preço há 90 dias" para uma campanha promocional.

* **Aviso direcionado:** "leads de determinada região" sobre uma visita ou evento.

* **Remarketing qualificado:** enviar para Meta/Google Ads um público de leads em negociação para criar Lookalike de alta qualidade, sem exportar CSV.

* **Nutrição por estágio:** público salvo por etapa que recebe conteúdo recorrente. 

## **Quando NÃO usar**

* Operação sem base histórica ainda (cliente novo, trial): não há volume para segmentar; é recurso de maturidade.

* Substituir o campo estruturado: segmento não dispensa preencher origem/produto/UF; ele se apoia neles.

* Disparo frio em coexistência: em coexistência a transmissão só entrega de forma confiável para quem tem conversa aberta. Base fria de verdade só via WABA \+ HSM (ver §6.5).

## **Limitação operacional crítica (Ads)**

A Kommo não atualiza o público nas plataformas de anúncio em tempo real. Se o segmento muda muito (leads entrando/saindo), é preciso reenviar o segmento manualmente para Meta/Google para a audiência de tráfego pago ficar atual. Documentar isso no setup de qualquer cliente que use Segmentos para Ads, senão a audiência envelhece sem o cliente perceber.

## **LGPD e mensagens em massa**

Disparo em lote para base de leads é tratamento de dados pessoais e mensagem não solicitada — risco de bloqueio do número e risco legal. Regras EG ao implementar Segmentos para qualquer cliente: 

* **Base de origem legítima:** só disparar para quem teve contato prévio com a empresa (lead que entrou, não lista comprada). Lista comprada é proibida.

* **Opt-out claro:** toda transmissão de marketing oferece saída ("responda SAIR para não receber"). Registrar e respeitar a saída.

* **Finalidade e minimização:** mensagem coerente com o motivo pelo qual o lead deixou o dado; não usar dado coletado para venda para disparar conteúdo sem relação.

* **Categoria correta no HSM:** marketing é marketing — não disfarçar promoção como utilitário para burlar custo/política da Meta.

* **Frequência:** cadência que não vira spam; proteger a saúde do número (ver risco de bloqueio em \#6.5).

A responsabilidade pelo conteúdo e pela base é do cliente (controlador); a EG configura a ferramenta (operador). Deixar esse papel claro no contrato de setup.

| Print sugerido: interface de Segmentos com cruzamento de dados Espaço reservado para imagem (print da tela). |
| :---- |

# 

# **7\. Relatórios e governança**

## **7.1 KPIs mínimos**

**KPIs operacionais**

| KPI | Como medir | Meta inicial |
| :---- | :---- | :---- |
| Tempo de 1a resposta | Chats \+ tarefas | Até 15 min |
| Leads sem responsável | Filtro no pipeline | 0 |
| Leads sem tarefa futura | Filtro no pipeline | 0 |
| Taxa de conversão por etapa | Relatórios do pipeline | A definir |
| Aging por etapa | Tempo médio por etapa | Reduzir mês a mês |
| Leads ativos vs. limite do plano | Total de lead ativo \+ limite do plano | Alerta em 80% |
| Leads parados na entrada | Filtro: etapa de entrada sem tarefa | Reduzir a zero |

**7.2 Checklist semanal do gestor**

**Checklist**

* Revisar leads sem responsável.

* Revisar leads sem tarefa futura.

* Revisar gargalos por etapa (muito volume parado).

* Auditar 10 leads (qualidade do registro, tarefas, motivo de perda).

# **8\. Treinamento e biblioteca de tutoriais**

## **8.1 Onboarding do atendente em 1 dia**

**Plano de onboarding (8 blocos)**

| Bloco | Duração | O que treinar | Checklist de validação |
| :---- | :---- | :---- | :---- |
| 1 | 30 min | Abrir Chats e responder | Responde e registra nota |
| 2 | 30 min | Abrir cartão e preencher campos | Campos mínimos preenchidos |
| 3 | 30 min | Criar tarefa e agendar | Tarefa futura criada |
| 4 | 30 min | Mover etapas e registrar motivo | Pipeline atualizado |
| 5 | 30 min | Templates e variáveis | Envia template editado |
| 6 | 30 min | Handoff e nota padrão | Repasse com nota e tarefa |
| 7 | 30 min | Uso de filtros e listas | Encontra leads sem tarefa |
| 8 | 30 min | Simulação completa | Lead sai de Entrada para Proposta |

## **8.2 Como gravar tutoriais rapidamente (Scribe/Tango/Guidde)**

Recomendação: grave 8 a 12 tutoriais curtos (2 a 6 min) e cole o link aqui. Isso vira seu treinamento escalável.

**Biblioteca de tutoriais (preencher com links)**

| Tutorial | Objetivo | Link | Público |
| :---- | :---- | :---- | :---- |
| Responder no Chats e abrir cartão | Velocidade e contexto | {LINK} | Atendente |
| Distribuição Round Robin | Separar e atribuir | {LINK} | Gestor/Admin |
| Criar tarefa e SLA | Follow up | {LINK} | Atendente |
| Handoff SDR \-\> Closer | Repasse | {LINK} | SDR/Closer |
| Pipeline Triggers | Automatizar tarefas | {LINK} | Admin |
| Templates e variáveis | Padronizar resposta | {LINK} | Atendente |

# **9\. Troubleshooting e FAQ**

## **9.1 Problemas comuns**

**Problemas e soluções rápidas**

| Problema | Causa provável | Solução |
| :---- | :---- | :---- |
| Lead não apareceu no pipeline | Filtro aplicado ou lead caiu em outro pipeline | Limpar filtros e pesquisar em 'Todos os leads' |
| Lead sem responsável | Distribuição não configurada | Aplicar regra de Round Robin ou atribuir manualmente |
| Mensagem automática não enviou | Condição do bot não bateu ou canal não permite | Revisar gatilhos e logs do bot |
| Atendente não recebeu notificação | Notificações desligadas ou usuário sem permissão | Revisar configurações do usuário |
| Automações, bots e SLA pararam para todos os leads novos | Limite de leads ativos do plano atingido | Encerrar leads mortos (Fechado \- Perdido), limpar entrada, ou fazer upgrade de plano. Há 24h de carência após o aviso. |
| Time não recebe novos leads para atribuir | Limite atingido (Round Robin pausado) ou distribuição não configurada | Verificar uso do limite primeiro; depois revisar regra de Round Robin |

## **9.2 Quando acionar suporte Kommo**

**Acione suporte quando**

* Integração de canal não autentica ou desconecta.

* Mensagens entram duplicadas ou não entram em nenhum lead.

* Automação falha para todos os leads mesmo após revisão.

| 🔒 INTERNO EG — Seção interna EverGreen — material de parceiro e vendas Esta seção contém informações de estratégia comercial da EG (planos, limites, gatilhos de upgrade). Ao clonar para o cliente, remova esta seção ou mantenha apenas §10.1 e §10.2 como referência operacional. |
| :---- |

# **10\. Planos, limites e quando recomendar upgrade (jun/2026)**

Esta seção é referência de parceiro: ajuda a escolher o plano certo na implantação e a justificar upgrade ao cliente. Preço de assinatura muda com frequência; confira valores atuais antes de fechar.

ATENÇÃO — renomeação de planos (jun/2026): o plano antes chamado "Enterprise" passou a se chamar \*\*Pro\*\*. Foi criado um \*\*novo Enterprise\*\*, de nível superior, com preço personalizado e suporte dedicado. Nomenclatura atual e preços de referência (USD, por usuário/mês): \*\*Base $15 · Advanced $25 · Pro $45 · Enterprise custom\*\*. Todos com trial de 14 dias com acesso de nível Pro. Recursos de IA consomem um pool único de créditos por conta. 

## **10.1 Limites por plano**

| Limite | Básico | Avançado | Pro | Empresarial |
| :---- | :---- | :---- | :---- | :---- |
| Leads ativos | 2.500 | 5.000 | 10.000 | Personalizado |
| Números WhatsApp | 1 | 3 | Ilimitado | Ilimitado |
| Instagram | 1 | 3 | Ilimitado | Ilimitado |
| Créditos IA/mês (por usuário) | 750 | 1.250 | 2.250 | Sob medida |

Nota: Usuários extras (Básico/Avançado) adicionam \+1 canal cada. Créditos de IA operam em pool único por conta (Agente, sugestão de resposta, reescrita, resumo) e renovam mensalmente; não acumulam. Recursos core de IA (escrita assistida, resumos, sugestão de resposta/tarefa) estão em todos os planos; o AI Agent (LLM) exige Advanced+; o AI Analyst exige Pro+. 

## **10.2 Regras que mudaram em 1º de junho de 2026**

1. Leads de entrada passam a contar no limite de leads ativos. Fechado \- Ganho e Fechado \- Perdido não contam.

2. Ao atingir o limite: para novos leads, param os bots, os Pipeline Triggers, as transmissões e a criação manual. Há 24h de carência com aviso em modal; sem ação, ocorre bloqueio do processamento de novos leads.

3. Limites de canal: canais conectados antes de 1º/jun ficam protegidos (direito adquirido, não expira). Canais novos seguem a regra do plano.

4. Integrações de terceiros para canal (Twilio, Gupshup, WABA via terceiros) são consideradas obsoletas sob a nova lógica. Em contas novas, usar canais nativos.

5. Integrações de ads (Meta/Google/TikTok Ads, Meta API, Google Analytics) e envio de público de Segmentos para Ads: novas configurações só no Pro. Quem já tem ativo mantém. Transmissão/mensagem em lote (sem Ads) já entra no Advanced.

6. Agente de IA (LLM) saiu do Base → exige Advanced. Recursos avançados (agente de voz, reconhecimento de áudio, AI Analyst, multiagentes) → Pro. Quem comprou Base antes de 1º/jun mantém o AI Agent sob a regra antiga (direito adquirido).

## **10.3 Qual plano recomendar na implantação**

* **Base:** 1 número de WhatsApp, operação enxuta, sem necessidade de AI Agent, sem Segmentos/transmissão em lote, sem integração nativa de ads.

* **Advanced:** até 3 números, AI Agent, times separados, Salesbot, \*\*Segmentos e transmissão em lote\*\*, campos obrigatórios. Piso real para a maioria das integradoras solar e para a Univet no fechamento.

* **Pro:** alto volume, 4+ números, integração nativa de ads, envio de público para Meta/Google, AI Analyst, agendamento com IA, ROI por campanha.

* **Enterprise:** organizações com requisitos custom — segurança avançada, SLA, backup, suporte dedicado, multiagentes em escala.

Regra prática: precisa de Segmentos/transmissão, AI Agent ou 2-3 números → Advanced. Precisa de ads nativo, 4+ números ou AI Analyst → Pro. Precisa só de mais gente acompanhando → adicionar usuários no mesmo plano.

| 🔒 INTERNO EG — \#10.4 — Gatilhos de upgrade (coaching de vendas, não entregar ao cliente) Estes são argumentos de venda para a conversa do time EG com o cliente — não são orientações operacionais. Remover na versão cliente. |
| :---- |

## **10.4 Gatilhos de upgrade para Pro (usar na conversa com o cliente)**

* Roda tráfego pago e quer integração nativa de ads no CRM.

* Usa ou vai usar 4 ou mais números de WhatsApp.

* Receita depende de agendamento, lembrete e remarcação (agora nativo na Kommo).

* Volume de comunicação ultrapassa o trabalho manual → automação por intenção.

* Precisa de segmentação, sincronização de audiências e ROI por campanha.

## **10.5 Recursos novos a aproveitar (jun/2026)**

1. **Agendamento nativo:** substitui Calendly. Link de reserva, horário de trabalho, atribuição automática, lembrete e follow-up via Agente de IA, tudo dentro da Kommo. Usar na etapa "Reunião marcada".

2. **Módulo Segmentos:** cria públicos dinâmicos uma vez e reusa em transmissão, anúncios e nutrição (ver §6.6). Transmissão exige Advanced; envio para Ads exige Pro; só Admin acessa. Centraliza o que antes era tag espalhada.

3. **WhatsApp Commerce:** catálogo e carrinho no WhatsApp, todos os planos, apenas WABA (não funciona em coexistência). Relevante só para cliente que vende produto pelo WhatsApp.

# **Apêndice A. Templates de mensagens (copiar e colar)**

**Templates base**

| Situação | Mensagem |
| :---- | :---- |
| Primeiro contato | Oi {Nome}, aqui é {SeuNome}. Vi seu contato sobre {Serviço}. Qual é seu objetivo principal agora? |
| Qualificação (dor) | Perfeito. Hoje, qual é o maior problema que você quer resolver? |
| Qualificação (prazo) | E em quanto tempo você quer ver isso funcionando? |
| Agendar call | Consigo falar com você em {Op1} ou {Op2}. Qual horário prefere? |
| Follow up proposta | Passei para confirmar se conseguiu ver a proposta. Quer que eu esclareça algum ponto? |

# **Apêndice B. Blueprint de pipeline (exemplo pronto)**

**Pipeline de Entrada (exemplo)**

| Etapa | Critério de entrada | Critério de saída | Automação mínima |
| :---- | :---- | :---- | :---- |
| Entrada | Mensagem recebida ou lead criado | Qualificado | Criar tarefa responder em 15 min |
| Qualificação | Dor e prazo coletados | Reunião marcada | Criar tarefa agendar reunião |
| Reunião marcada | Data confirmada | Proposta | Criar tarefa confirmar presença |
| Proposta | Proposta enviada | Fechado ganho ou perdido | Criar tarefa follow up 48 h |

# **Apêndice C. Referências (documentação oficial)**

Acesso em 12/01/2026.

* [Importação avançada (pipeline e lead status)](https://www.kommo.com/support/crm/import-advanced/)

* [Como importar dados](https://www.kommo.com/support/crm/how-to-import/)

* [Chats section](https://www.kommo.com/support/crm/chat-section/)

* [Pipeline triggers](https://www.kommo.com/support/crm/pipeline-triggers/)

* [Round Robin no Salesbot](https://www.kommo.com/support/crm/introducing-round-robin-in-salesbot/)

* [Unified Inbox](https://www.kommo.com/unified-inbox/)

* [Layout do cartão do lead](https://www.kommo.com/support/crm/card-layout/)

# **Apêndice D. Glossário**

Definições dos principais termos técnicos usados neste playbook. Referência para novos membros do time.

| Termo | Definição |
| :---- | :---- |
| Agente de IA (LLM) | Recurso da Kommo que usa um modelo de linguagem (ex.: GPT) para responder leads automaticamente, interpretar intenção e acionar fluxos. Disponível a partir do plano Avançado; recursos avançados (voz, multiagentes) no Pro. |
| Coexistência | Modelo de integração WhatsApp onde o número pessoal continua funcionando normalmente e a Kommo recebe e envia mensagens via sincronização. Não é WABA; tem restrições (sem HSM, sem lote de disparos, janela de 24h diferente). |
| Funil de entrada (Pipeline) | Sequência de etapas que o lead percorre, da chegada ao fechamento. Na Kommo, cada pipeline tem etapas, campos, automações e visibilidade configurados separadamente. |
| HSM (Highly Structured Message) | Mensagem de template aprovada pelo Meta para envio via WABA fora da janela de 24h. Exige aprovação prévia e uso de variáveis definidas. Usada para reativar leads frios. |
| Incoming leads | Leads que chegam diretamente de canais conectados (WhatsApp, Instagram, formulários, ads). Desde jun/2026 contam no limite de leads ativos do plano. |
| Pipeline Triggers (Digital Pipeline) | Automações que disparam ações ao mover um lead de etapa (ex.: criar tarefa, enviar mensagem, notificar usuário). Configuradas dentro de cada pipeline na seção Digital Pipeline. |
| Round Robin | Distribuição automática de leads entre os membros de um grupo, de forma sequencial e igualitária. Configurado dentro do Salesbot. Exige que os usuários estejam no mesmo grupo. |
| Salesbot | Construtor de fluxos de automação da Kommo baseado em condições e ações (if/then). Permite enviar mensagens, criar tarefas, mover etapas, atribuir responsáveis e acionar o Agente de IA. |
| Segmentos | Módulo da Kommo (jun/2026) que cria públicos dinâmicos reutilizáveis por condições. Transmissão exige Advanced; envio para Ads exige Pro; acesso só de Admin. Ver \#6.6. |
| SLA (Service Level Agreement) | Acordo de tempo-resposta mínimo para cada tipo de ação (1ª resposta, follow-up, proposta). No playbook, define a meta operacional do time. |
| Tokens de IA | Unidade de consumo dos recursos de IA da Kommo (Agente, sugestão de resposta, reescrita). Operados em pool mensal por conta; o volume varia por plano. |
| WABA (WhatsApp Business API) | Integração oficial do WhatsApp via API, gerenciada pela Meta. Permite HSM, disparo em lote, catálogo de produtos e WhatsApp Commerce. Diferente da coexistência: o número fica exclusivo na plataforma. |
| Janela de 24h | Período após a última mensagem do contato dentro do qual a empresa pode enviar qualquer tipo de mensagem pelo WhatsApp. Fora dessa janela, só HSM (em WABA) ou alternativas de coexistência. |
| Campo obrigatório por etapa (Field permissions) | Configuração na Kommo que exige que determinados campos do cartão sejam preenchidos antes de o lead avançar para a próxima etapa. Garante dados mínimos capturados no momento certo. |
| SDR / BDR | Sales Development Representative / Business Development Representative. SDR qualifica leads inbound; BDR prospecta ativamente. Na Kommo, geralmente cada perfil tem pipeline e permissões diferentes. |
| Closer | Vendedor responsável pelo fechamento (proposta e negociação). Recebe o lead qualificado via handoff do SDR. |
| CS (Customer Success) | Profissional responsável pelo pós-venda e retenção do cliente. Pode ter pipeline separado na Kommo para acompanhar onboarding e renovações. |
| Feed do cartão | Histórico cronológico de todas as interações com o lead: mensagens, notas, mudanças de etapa, tarefas concluídas, chamadas. É o registro oficial da negociação. |

# **Apêndice E. Cartão de referência rápida — Atendente**

| *Imprima ou fixe no desktop. Esta página resume tudo que o atendente precisa no dia a dia.* |
| :---- |

**As 5 Regras de Ouro**

1. Todo lead tem dono. Se chegou sem responsável, assuma na hora.

1. Nenhum lead fica sem tarefa futura. Lead parado \= lead perdido.

1. Todo movimento de etapa gera uma próxima ação.

1. Toda conversa relevante entra no cartão (feed). Nada 'por fora'.

1. Responda dentro do SLA. Se não conseguir resolver, registre e peça ajuda.

**Fluxo de atendimento em 5 passos**

| Passo | Ação | Como fazer na Kommo | Saída esperada |
| :---- | :---- | :---- | :---- |
| 1 | Responder (SLA) | Abrir Chats → responder → registrar nota no cartão | Lead engajado em \< 5 min |
| 2 | Qualificar | 3 perguntas: Dor, Prazo, Orçamento | Campos de qualificação preenchidos |
| 3 | Criar tarefa | Botão '+' no cartão → escolher tipo → definir data/hora | Próxima ação agendada |
| 4 | Mover etapa | Arrastar cartão no pipeline ou botão 'Avançar etapa' | Pipeline atualizado |
| 5 | Handoff (se houver) | Nota de repasse padrão \+ reatribuir responsável | Closer avisado com contexto |

**Tipos de tarefa e quando usar**

| Tipo | Quando usar | Título sugerido |
| :---- | :---- | :---- |
| Ligar | Qualificar, follow up por voz | Ligar: {Nome} — {Motivo} |
| Escrever | Follow up por mensagem, envio de proposta | Escrever: {Nome} — proposta / follow D+N |
| Reunião | Demonstração, fechamento presencial | Reunião: {Nome} — {Data} {Hora} |
| Tarefa | Ações internas (verificar dados, aguardar retorno) | Verificar: {Nome} — {O que} |

**SLAs do time**

| Situação | Tempo alvo | Quem | Observação |
| :---- | :---- | :---- | :---- |
| Lead novo (horário comercial) | \< 5 min | Atendente/SDR | Responder e qualificar |
| Lead novo (fora do horário) | Até abertura | Atendente/SDR | Bot segura; humano retoma |
| Proposta enviada — follow up | Até 24h | Closer | Com valor e próximos passos |
| Sem resposta do lead | D+1, D+3, D+7 | SDR | Cadência com variações de tom |
| Handoff SDR → Closer | Mesmo dia | SDR | Nota padrão preenchida |

**Convenção de título de tarefa**

| Formato: \[Tipo\]: \[Nome do lead\] — \[Motivo ou prazo\]Exemplo: *Ligar: João Silva — follow up proposta D+3* |
| :---- |

**Atalhos e dicas de produtividade**

* Use filtros salvos no pipeline para ver apenas seus leads com tarefa vencida.

* Templates de resposta: acesse digitando '/' no campo de chat.

* Atalho de cartão dentro do chat: ícone lateral direito no Chats.

* No app mobile: push de tarefa vencida \= sinal de ação imediata.

* Dúvida técnica: consulte §9 (Troubleshooting e FAQ) antes de acionar suporte.

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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/PhUsx5j1gWLs9GaqsRjAOdBFfz7hzOnTqw2r7hq70u68M4urQCrONtxunTxqHOLRCWV3+Wi6/enFEJb/e77x7771jbzYxjCfAEmrH78Ky+sd70q5fTDxaPPbpxvJqJrdLlyvoBn5qKC1orYuLxAVcRz5WzWNRcFzoPz9cvCG1dlTrPnj3P9bJ8T4uriRwcy29V3vUJ4fZA6J0+sdv2XyyY8QqbPHRXVKEmtXvip1pgvG0+aNdT8HykiZ+6owk/jFeNhqR69OBxEoHOR61c1mS67fe8EUYnBXLwGbfWayRFN7mo6btog9CB44q8FnpmLUL9jw6lzRnz/xRHXa1No4cN3d3Ub0snZjSpF70/9JBet89+16Yvn1/301QnXMdw/vzu1fPXsVj1bmuveoPS29XoM64z73demAYuwb3iEaP+9pPBTrTFzsVpCaINOjbZue0Qedc5Xmq8jF9XLARgsxjZJcS5iLhJ5/DAX/0TlI4OCM2PRvWa0q4ffEF3w+icVC4bXqa3rqvMZ2TCx6vW+xaa4cFcmtUjHRjPb15et46brC4REdMthLhIREdmYi0RERDbmIhERkY25SEREZGMuEhER2ZiLRERENuYiERGRjblIRERkYy4SERHZmItEREQ25iIREZGNuUhERGRjLhIREdmYi0RERDbmIhERkY25SEREZGMuEhER2ZiLRERENuYiERGRjblIRERkYy4SERHZmItEREQ25iIREZGNuUhERGRjLhIREdmYi0RERDbmIhERkY25SEREZGMuEhER2ZiLRERENuYiERGRjblIRERkYy4SERHZmItEREQ25iIREZGNuUhERGRjLhIREdmYi0RERDbmIhERkY25SEREZGMuEhER2ZiLRERENuYiERGRjblIRERkYy4SERHZmItEREQ2/8rFcnF1qtSLJiKiW0K5mNpmT/57869ctATXICKiW4PZh//+/C8XiYiIfGMuEhER2ZiLRERENuYiERGRjblIRERkYy4SERHZmItEREQ25iIREZGNuUhERGRjLhIREdmYi0RERDbmIhERkY25SEREZGMuEhER2ZiLRERENuYiERGRjblIRERkYy5eQ51ZHcMe7FapVby5iIiISh4/zcXSsUEIvJrDm5iLNGknp2acnxH5eB9zkS/l0sNC77sr/OEe5iIiIrrJ+Wku1pnVIWHr6NSj2ZU7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>