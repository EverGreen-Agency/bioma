# Tecnologias em avaliação — Google Ads e Meta

Levantadas em 2026-08-11. Este arquivo é **inventário para decidir**, não
recomendação fechada.

> **Aviso de honestidade sobre o rigor desta página.** Dos links levantados, eu
> li de fato **dois**: o de service accounts do Google Ads e a visão geral do
> Ads MCP Server da Meta. O resto está classificado por título e pelo que já se
> sabia do ecossistema — o que é palpite informado, não verificação. Onde a
> distinção importa, está marcado com ⚠️. Antes de qualquer decisão de
> implementação, o link precisa ser lido.

## Google

| Recurso | O que é | Serve ao Bioma? |
|---|---|---|
| [Google Ads API](https://developers.google.com/google-ads/api) | a API que já usamos no worker | **em uso** |
| [Service accounts](https://developers.google.com/google-ads/api/docs/oauth/service-accounts) | ✅ **lido**: suportadas, sem domain-wide delegation; o e-mail é convidado em Admin › Acesso e segurança | **em uso** — é o modelo do worker |
| [google-ads-mcp](https://github.com/googleads/google-ads-mcp) | ⚠️ servidor MCP oficial do Google para Ads | **não resolve o sync** — é consulta conversacional, não alimenta as tabelas diárias. Interessante para o copiloto/ChatGPT depois |
| [google-ads-api-developer-assistant](https://github.com/googleads/google-ads-api-developer-assistant) | ⚠️ assistente oficial para desenvolver contra a API | ferramenta de desenvolvimento, não de produto. Pode encurtar a escrita de queries GAQL |
| CLIs de terceiros (`adkit`, `google-ads-open-cli`, Composio) | ⚠️ wrappers não-oficiais | **não** — já temos adapter próprio; dependência de terceiro para algo central não se paga |

## Meta

| Recurso | O que é | Serve ao Bioma? |
|---|---|---|
| [Marketing API](https://developers.facebook.com/documentation/ads-commerce/marketing-api) | ⚠️ leitura/escrita de campanhas | **em uso parcial** (leitura, via `meta_ads`) |
| [Ads MCP Server](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-overview) | ✅ **lido**: remoto em `mcp.facebook.com/ads`, **lê E ESCREVE** (cria e edita campanhas, ad sets, anúncios), 7 categorias de ferramentas | avaliar com cuidado — ver "risco" abaixo |
| [Ads CLI](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/ads-cli-overview) | ⚠️ CLI oficial da Meta (2026) | possível para operação manual assistida |
| [Conversions API](https://developers.facebook.com/documentation/ads-commerce/conversions-api) | ⚠️ envia conversão server-side | **alto valor para cliente** — melhora atribuição sem depender de pixel/cookie |
| [Ad Library API](https://www.facebook.com/ads/library/api/) | ⚠️ anúncios públicos de qualquer anunciante | **alto valor** para benchmark de concorrente, e é pública |

### Ads MCP Server da Meta — o que foi verificado (2026-08-11)

**Confirmado:**

- remoto em `mcp.facebook.com/ads`; **lê e escreve** — cria e edita campanhas,
  ad sets e anúncios, em 7 categorias de ferramentas;
- autenticação **OAuth com escopos granulares POR FERRAMENTA**, e a orientação
  da própria Meta é conceder o mínimo: "only select scopes for tools you
  actually need";
- uso governado pelos Meta Platform Terms;
- existe também um **Devtools MCP**, para gerenciar apps e webhooks.

**NÃO confirmado** (as páginas de "Get started" truncam; três tentativas):
se exige App próprio da EG, se há verificação de negócio, Tech Provider ou
allowlist.

**Leitura do que foi confirmado:** OAuth com escopo por ferramenta, num servidor
hospedado pela Meta, é o mesmo padrão de Canva e Google Drive — o usuário
conecta a PRÓPRIA conta e autoriza escopos. Isso sugere fortemente que **não é
preciso construir App para usar**, diferente da Marketing API. Sugere, não
prova: confirmar no primeiro contato.

### Correção de uma recomendação anterior

Eu havia escrito "não ligaria a workspace de cliente antes de existir registro
de quem autorizou o quê". Era cauteloso demais e o Eduardo apontou com razão:
**gerenciar ads por IA é exatamente o objetivo**, não um efeito colateral a
conter.

A posição correta: a capacidade é desejada; o que ela **exige** é aprovação
humana por ação que gasta dinheiro — que é a mesma regra que o copiloto do
Bioma já aplica ("ação visível ao cliente sempre pede confirmação"). É
requisito de implementação, não motivo para adiar.

O escopo granular por ferramenta ajuda aqui: dá para conectar só as ferramentas
de LEITURA primeiro e acrescentar as de escrita quando a aprovação estiver no
fluxo.

## App na Meta e Tech Provider — o que eu sei e o que não sei

**Precisa de App na Meta for Developers:** Marketing API e Conversions API.
É o App que carrega as permissões (`ads_read`, `ads_management`) e recebe o
token. Isso **já vale hoje** para a integração `meta_ads` que existe.

**Não verifiquei** (e não vou afirmar): se o Ads MCP Server exige App próprio
ou usa a credencial do usuário na conversa; se há exigência de **Tech Provider**
ou de verificação de negócio para qualquer um deles; e quais permissões passam
por App Review. A documentação que li não cobre — remete a uma seção "Get
started" que não foi lida.

**Isso precisa ser verificado antes de planejar**, porque App Review da Meta é
processo com prazo, e descobrir a exigência depois de prometer a data é o tipo
de erro caro.

## Ad Library como inteligência de criação

O Eduardo levantou um uso que eu não tinha considerado e que é melhor que
"benchmark de concorrente": **alimentar a criação** de roteiro, imagem e vídeo
com os anúncios que estão no ar.

Isso encaixa direto no que já existe — o Estúdio gera artefatos, e o dossiê que
alimenta a geração hoje tem marca, tom e métricas. Acrescentar "o que os
concorrentes estão veiculando agora" é contexto real, público e verificável,
diferente de benchmark inventado (que o prompt do insight multicanal proíbe
justamente por não ter fonte).

Vale para os dois ecossistemas: a Meta tem a
[Ad Library API](https://www.facebook.com/ads/library/api/) e o Google tem o
Ads Transparency Center. ⚠️ O do Google não foi verificado — não sei se tem API
pública ou só interface.

## Ordem que eu proporia

1. **Ad Library (Meta)** — pública, sem App, e alimenta criação de conteúdo.
   Maior valor pelo menor bloqueio.
2. **Ads MCP (Meta)** — conectar primeiro com escopos de LEITURA, que já
   entrega análise conversacional sem risco de orçamento. Escrita entra com
   aprovação por ação.
3. **Conversions API** — valor direto para cliente; usa o App que a Marketing
   API já exige.
4. **MCP do Google Ads** — mesmo raciocínio do da Meta, depois.
