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

### O risco do Ads MCP Server da Meta

Ele **escreve**. Um MCP que cria e edita campanha conectado a um modelo é,
literalmente, IA com acesso ao orçamento de mídia do cliente. Isso não é
argumento para não usar — é argumento para usar com aprovação humana explícita
por ação, que é a mesma regra que já vale para as ações do copiloto no Bioma.

Eu não ligaria isso a workspace de cliente antes de existir um registro de
quem autorizou o quê.

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

## Ordem que eu proporia

1. **Conversions API** — valor direto para cliente, e o App que ela exige é o
   mesmo que a Marketing API já usa.
2. **Ad Library API** — barata, pública, alimenta benchmark de concorrente.
3. **MCPs (Google e Meta)** — depois que o copiloto interno estiver estável.
   Ligar IA com escrita em mídia paga antes disso é ordem invertida.
