# Univet: passo a passo para conectar tudo

Objetivo: a v2 (`/portal/univet/v2`) mostrar com dados reais o mesmo que a demo
(`/portal/univet`) mostra com dados ilustrativos. O acompanhamento ao vivo de cada item
fica na Operação EG (`/portal/univet/eg`), bloco "Conexões do painel".

Ordem sugerida: 1 → 2 → 3 destravam a operação comercial já. 4 a 7 destravam receita e mídia.

| # | Conexão | Quem age | Destrava na v2 |
|---|---|---|---|
| 1 | Campos obrigatórios no Kommo | EverGreen | mapa, rankings, qualidade do cadastro |
| 2 | Representantes e territórios | Univet → EverGreen | mapa de cobertura, tabela por representante |
| 3 | Modelo de decisão (classificador) | EverGreen | classificação lendo a conversa |
| 4 | Nomus ERP | Univet → EverGreen | faturamento, pedidos, ticket, produtos |
| 5 | Google Ads | Univet → EverGreen | investimento, CPL, CAC, ROAS |
| 6 | Meta Ads e Instagram | Univet → EverGreen | investimento, criativos, orgânico |
| 7 | GA4 e GTM do site | Univet → EverGreen | eventos do site e UTMs no lead |

---

## 1. Campos obrigatórios no Kommo

O painel reconhece os campos pelo **nome** (não pelo id), então os nomes abaixo precisam
existir exatamente assim em Kommo → Configurações → Campos → Leads:

| Nome do campo | Tipo sugerido | Observação |
|---|---|---|
| `UF` (ou `Estado`) | Lista | Aceita "SP", "São Paulo" ou "SP - Interior" |
| `Origem do lead` | Lista | Site, WhatsApp, Google Ads, Meta Ads, Indicação, Evento… |
| `Região/Representante indicado` | Lista | Uma opção **por representante** (ver item 2) |
| `Segmento` | Lista | Odonto, Medicina, Veterinária… |
| `Produto de interesse` | Lista | |
| `Solicitação inicial` | Lista | Preço, Catálogo, Dúvida técnica, Visita, Representante, Outro |
| `Tipo de atendimento` | Lista | |
| `Motivo de perda` | Lista | Ou use o motivo de perda nativo do Kommo |
| `Data da visita` | Data | Conta como "visita agendada" |
| `utm_source`, `utm_medium`, `utm_campaign` | Texto | Preenchidos pelo formulário do site |

Passos:
1. Criar ou renomear os campos acima.
2. No funil, marcar UF, Origem e Representante como obrigatórios para sair de "01 Primeiro atendimento".
3. No formulário do site e no fluxo do n8n, gravar UF, origem e as três UTMs já na criação do lead.
4. Na `/eg`, clicar em "Sincronizar leads". O bloco "Saúde da captação" mostra o preenchimento de cada campo contra a meta de 90%.

## 2. Representantes e territórios

Os nomes que estão hoje na demo são ilustrativos. O território no painel real **sai dos
próprios leads**: cada lead com representante e UF preenchidos pinta o estado com a cor
daquele representante. Não existe cadastro paralelo para manter.

Pedir à Univet:
- nome de cada representante;
- estados (e cidades-polo, se houver) que cada um atende;
- se cada um terá usuário no Kommo ou se só recebe o lead repassado.

Depois:
1. Cadastrar uma opção por representante no campo `Região/Representante indicado` (o nome da pessoa, não o nome da região).
2. Se tiverem usuário no Kommo, configurar a distribuição automática por UF para o responsável certo.
3. Na v2, o mapa em "Representantes" e a tabela por representante passam a se preencher sozinhos.

## 3. Modelo de decisão (classificador da Operação EG)

Sem a chave, o classificador usa só regras e DDD. Para ele ler a conversa:
1. Gerar a chave do modelo (Jev ou Laya).
2. No Railway, serviço da API, criar `DECISION_MODEL_API_KEY`. Opcionais: `DECISION_MODEL_NAME` (padrão `jev-latest`) e `DECISION_MODEL_URL`.
3. Reiniciar a API. Na `/eg`, o cartão "Motor de classificação" muda para "Modelo de decisão ativo".

## 4. Nomus ERP

O conector ainda **não existe** no Bioma. A EverGreen constrói depois de receber o acesso.

Pedir à Univet (quem administra o Nomus):
1. Gerar a chave de acesso REST em **Configuração Geral → Chave de acesso para integração com o ERP via REST**.
2. Enviar a **URL base** do Nomus (formato `https://{servidor}/{contexto}`) e a **chave**, por canal seguro (nunca por e-mail aberto ou grupo).
3. Confirmar que os módulos de **clientes**, **pedidos de venda** e **notas fiscais** estão liberados para a chave.
4. Confirmar que o cadastro de cliente no Nomus guarda **telefone e CPF/CNPJ**. É por eles que o pedido é ligado ao lead do Kommo.

Atenção: o pedido no Nomus não carrega o id do lead. A ligação será por telefone, CPF/CNPJ,
nome e janela de datas, ou seja, provável e não exata. O painel vai mostrar isso como "atribuição provável".

## 5. Google Ads

O Bioma lê o Google Ads pelo worker, com as variáveis `GOOGLE_SERVICE_ACCOUNT_JSON`,
`GOOGLE_ADS_DEVELOPER_TOKEN` e, se houver, `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (a MCC da EverGreen).
Se outro cliente já sincroniza Google Ads no Bioma, a parte da EverGreen está pronta.

Pedir à Univet:
1. O **Customer ID** da conta (formato `123-456-7890`, aparece no topo do Google Ads).
2. Aceitar a solicitação de vínculo da MCC da EverGreen em Google Ads → Administrador → Acesso e segurança → Gerentes.

Parte da EverGreen:
1. Pela MCC, enviar a solicitação de vínculo para o Customer ID da Univet.
2. Garantir que a conta de serviço do `GOOGLE_SERVICE_ACCOUNT_JSON` tem acesso à MCC.
3. No Bioma, Configurações → Integrações → cliente Univet → Google Ads: salvar o Customer ID (e a MCC no campo opcional).

## 6. Meta Ads e Instagram

O worker usa `META_ADS_ACCESS_TOKEN` e `INSTAGRAM_ACCESS_TOKEN` (token de usuário do sistema do
Business Manager da EverGreen).

Pedir à Univet, em business.facebook.com → Configurações do negócio:
1. **Parceiros → Adicionar**: informar o ID do Business Manager da EverGreen.
2. Compartilhar a **conta de anúncios** (permissão de ver desempenho) e a **conta do Instagram**.
3. Enviar o **ID da conta de anúncios** (`act_…`).

Parte da EverGreen:
1. Atribuir os ativos recebidos ao usuário do sistema que gera os tokens.
2. Pegar o **Instagram Business Account ID** (Configurações do negócio → Contas do Instagram).
3. No Bioma, Integrações → cliente Univet: salvar o `act_…` em Meta Ads e o ID em Instagram (orgânico).

## 7. GA4 e GTM do site

Pedir à Univet (ou a quem cuida do site):
1. GA4 → Administrador → Gerenciamento de acesso à propriedade: adicionar o **e-mail da conta de serviço** da EverGreen como **Leitor**.
2. Enviar o **Property ID** (Administrador → Detalhes da propriedade).
3. GTM: acesso de leitura ao contêiner e o **Container ID** (`GTM-XXXXXXX`).

Parte da EverGreen:
1. Salvar Property ID e Container ID no Bioma, em Integrações → cliente Univet.
2. Garantir que o formulário do site manda `utm_source`, `utm_medium` e `utm_campaign` para o lead no Kommo (item 1).

---

## O que ainda é desenvolvimento nosso

Conectar os itens 5 a 7 faz os dados entrarem no Bioma (módulo de performance do cliente).
Para eles aparecerem na v2 falta ligar o cliente Univet do Bioma ao portal. O conector do Nomus
(item 4) também precisa ser construído. Cada um vira uma entrega quando o acesso chegar.
