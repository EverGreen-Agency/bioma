# Auditoria: EverGreen Presença, Univet e memória dos agentes

## Escopo e evidência

Auditoria estática do `develop` em `d31e537`, das branches já incorporadas `feat/malleable-social-studio` (`96a1dc9`) e `feat/univet-kommo-nomus` (`2c674e2`), mais testes locais sem provedores externos.

## EverGreen Presença

### Estado encontrado

- As seis visões usam apenas `malleable-mock.ts`; não há API, persistência, workspace nem permissões.
- A geração de ideias concatena texto local e imagens públicas do Unsplash. Não há Thinker, Designer, renderização nem evidência de fonte.
- “Agendar” muda somente o estado React da sessão.
- O Publisher afirmava conexão com Instagram e simulava publicação com `alert()`, sem chamar qualquer integração.
- O “Tailor” alterna dois presets fixos, Poppi e Univet. Não cria configuração reutilizável por cliente.
- O calendário é uma grade de cards marcados; faltam mês/semana, data e horário editáveis, drag and drop, timezone, canais, aprovação, conflito, fila, retry e histórico.
- A tela usa um design system próprio e uma navegação dentro da navegação do Bioma, o que explica a sensação de iframe/produto separado.

### Correção imediata aplicada

A tela agora declara que é um protótipo com dados demonstrativos e que nada é salvo ou publicado. O Publisher deixou de afirmar conexão com Instagram e perdeu o botão falso de disparo.

O nome público passou de Malleable/CRAFT/Render Studio para **EverGreen Presença**. A rota principal é `/presenca`; `/malleable-studio`, `/social-studio` e `/render-studio` permanecem como redirects de compatibilidade. A Univets ganhou um item de navegação para a apresentação em `/univet`.

### Corte operacional implementado depois da auditoria

`/presenca` agora abre uma nova interface conectada ao `workspace_editorial_calendar` existente. A equipe seleciona um workspace acessível, vê peças por mês, semana ou lista, filtra por canal/etapa, cria e edita título, canal, formato, horário e texto. O Brand Book do workspace é exibido como contexto. Rascunhos prontos do Estúdio IA podem ser adotados no calendário: a API relê a saída da execução no mesmo workspace e grava origem, modo, provedor e modelo canônicos; a migração `0110` impede importação duplicada. A mesma interface aparece na aba Calendário do Estúdio IA. O protótipo antigo não é mais renderizado pela rota do produto.

A API ganhou `PUT /workspaces/{workspace_id}/calendar/{item_id}` e valida a progressão ideação → produção → revisão → aprovado → agendado. Aprovação exige papel com capacidade `approve` e texto; agendamento exige papel com `manage_work`, texto e data futura. Edição após aprovação exige reabrir a revisão. `published` não pode ser marcado manualmente por essa API. Criação, edição e transições registram eventos no audit log do Bioma. Peças aprovadas podem ser baixadas como pacote de publicação manual com canal, texto, mídias e data, sem afirmar entrega externa.

Este corte entrega persistência e gestão editorial reais no código, mas não há prova de banco/deploy nesta rodada porque o Docker local não está disponível. Agendamento é uma intenção editorial persistida; publicação externa ainda precisa de integração e confirmação da plataforma.

### Tese de produto pesquisada

Service as Software vende um resultado executado e verificável, não apenas acesso a uma ferramenta. Para este módulo, o resultado é uma presença social contínua: pauta, produção, revisão, aprovação, entrega para publicação e aprendizado. A interface é o painel de controle dessa operação.

“Software maleável” entra como capacidade de configuração: cada workspace pode adaptar voz, etapas, campos, canais, regras e aprovações sem criar um fork do produto. Mudanças estruturais propostas por IA precisam continuar revisáveis e versionadas.

Sinais usados na decisão:

- Ink & Switch trata maleabilidade como programação e adaptação pelo usuário: https://www.inkandswitch.com/end-user-programming/
- Thoughtworks descreve Service as Software como venda de resultados e execução por agentes: https://www.thoughtworks.com/insights/blog/generative-ai/service-as-software-a-new-economic-model-for-age-of-ai-agents
- Discussões recentes no Reddit alertam que o modelo vira apenas “agência com outro nome” quando não há automação repetível, logs e economia demonstrável: https://www.reddit.com/r/gtmengineering/comments/1unvrfi/building_a_service_as_a_software_company_which/ e https://www.reddit.com/r/SaaS/comments/1t3j8fn/service_as_a_software_the_new_saas/
- No X, o tema aparece ligado à tese de elevar margens de serviços com execução por IA: https://x.com/i/trending/2039425731030388866

O nome de trabalho **EverGreen Presença** foi escolhido porque descreve o resultado comprado. “SocialOps” e “ContentOps” já são usados por múltiplos produtos e agências.

### Corte vertical recomendado

1. **Calendário real**: mês/semana/lista, fonte `editorial_calendar`, filtros de canal/etapa e drawer de edição implementados. Faltam responsável, paginação e QA visual em ambiente autenticado.
2. **Aprovação e persistência**: progressão até agendada e audit log implementados. Publicada/falhou, idempotência de publicação e confirmação externa dependem do adaptador de canal.
3. **Brand profile por workspace**: trocar presets por Brand Book, ativos do workspace e regras versionadas.
4. **Geração rastreável**: importação da saída existente do Estúdio IA com id da execução, modo, provedor e modelo implementada. Falta ligar o gerador ao novo control plane e preservar prompt/versionamento, fontes, tokens e custo no artefato.
5. **Publicação**: exportação e handoff manual implementados. Conectar Meta/Blotato somente depois de sandbox, token por workspace, dry-run e aprovação humana.
6. **Maleabilidade vendável**: templates de serviço versionados, campos configuráveis e módulos por cliente. Mudanças geradas por IA entram como proposta revisável, sem alterar código ou schema em produção de forma autônoma.

O primeiro produto plug and play recomendável é **Operação Social Assistida**: calendário, brand profile, geração, revisão e pacote de publicação. É um resultado comercial claro e usa capacidades que o Bioma já possui.

## Univet

### O que existe

- Motor Python de deduplicação do Kommo, CLI com dry-run e três testes de normalização/cluster.
- Dois JSONs de workflow n8n e documentação de implantação.
- Servidor MCP genérico para administrar n8n.
- Preset visual da Univets e apresentação comercial no frontend.

### Lacunas críticas

- Os workflows descritos não estão provados como importados ou ativos em uma instância n8n.
- A documentação aponta `POST /workspaces/{id}/integrations/sales_event`, mas esse endpoint não existe na API atual.
- Nomus, Kommo e n8n não foram consultados nesta auditoria; não há prova de credenciais, dados reais, ids de status ou execução.
- O script de deduplicação aceita aplicação e deleção em produção; qualquer uso real precisa começar em dry-run, com relatório revisado e backup/exportação do CRM.

Os seis testes locais combinados de DataForSEO e Kommo passaram. Isso valida transformação e regras locais, não as integrações externas.

## Memória entre agentes

### Implementado

- Memórias globais e por workspace no Postgres, revisão de cada mudança, arquivamento e preferências pessoais isoladas por usuário.
- Skills propostas pelo agente ficam `pending_review`; só skills aprovadas entram no dossiê do copiloto.
- O copiloto lê memórias globais mais as do workspace e registra uso de skills.

### Limite da afirmação

O compartilhamento ocorre entre execuções que usam a API e o mesmo Postgres do Bioma. A memória local do Codex, arquivos do Antigravity/Claude e worktrees Git não são sincronizados automaticamente com `agent_memories`.

O smoke de ponta a ponta já existe (`smoke_agent_memory.py`), mas não pôde ser executado nesta rodada porque o Postgres/Docker local estava indisponível. A evidência atual é estática mais o contrato OpenAPI atualizado; falta a prova com banco real.
