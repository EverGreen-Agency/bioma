/**
 * Guias de conexão por integração — exibidos dentro do próprio card em
 * Integrações e exportáveis para PDF/impressão.
 *
 * ── COMO ADICIONAR OS PRINTS ──────────────────────────────────────────────
 * Cada passo pode declarar `screenshot: "<slug>"`. O componente procura o
 * arquivo em:
 *
 *     bioma/apps/web/public/assets/integration-guides/<provider>/<slug>.png
 *
 * Enquanto o arquivo não existir, aparece um espaço tracejado no lugar
 * mostrando exatamente o caminho esperado — é só salvar o print naquele
 * caminho e recarregar a página; nenhum código precisa mudar.
 *
 * Ex.: o passo `screenshot: "customer-id"` do provider `google_ads` espera
 *     public/assets/integration-guides/google_ads/customer-id.png
 *
 * Formato sugerido: PNG, largura ~1200px, recortado só na área relevante.
 */

export type GuideStep = {
  title: string;
  description: string;
  link?: { label: string; url: string };
  screenshot?: string;
};

export type IntegrationGuideContent = {
  /** O que essa conexão passa a alimentar no Bioma. */
  summary: string;
  /** Quem executa: a EG, o cliente, ou os dois em etapas diferentes. */
  responsible: "eg" | "client" | "both";
  prerequisites: string[];
  steps: GuideStep[];
  /** Variáveis de ambiente que a EG precisa ter no deploy (uma vez, não por cliente). */
  envVars?: string[];
  /** Fricção conhecida que vale avisar antes da pessoa começar. */
  caveat?: string;
};

const GOOGLE_SERVICE_ACCOUNT_STEP: GuideStep = {
  title: "Copie o e-mail da service account da EG",
  description:
    "No Google Cloud Console da EG, abra IAM e Admin › Contas de serviço e copie o e-mail da conta usada pelo Bioma (termina em .iam.gserviceaccount.com). É esse e-mail que o cliente vai autorizar nos próximos passos — a EG nunca pede login nem senha do cliente.",
  link: { label: "Google Cloud Console — Contas de serviço", url: "https://console.cloud.google.com/iam-admin/serviceaccounts" },
  screenshot: "service-account-email",
};

export const INTEGRATION_GUIDES: Record<string, IntegrationGuideContent> = {
  google_ads: {
    summary:
      "Traz campanhas, palavras-chave, termos de busca, conversões e investimento do Google Ads para a aba Métricas. Cobre também campanhas de vídeo (YouTube Ads) — YouTube Ads não é uma conexão separada, roda dentro do Google Ads.",
    responsible: "both",
    prerequisites: [
      "Acesso de administrador à conta Google Ads do cliente",
      "Developer token do Google Ads aprovado na conta MCC da EG",
    ],
    steps: [
      {
        title: "Antes de tudo: a service account existe?",
        description:
          "Se ainda não existe, é aqui que começa. No Google Cloud Console da EG: crie/escolha um projeto, ative a Google Ads API em APIs e serviços › Biblioteca, e vá em IAM e Admin › Contas de serviço › Criar. Não precisa conceder papel algum no projeto — o acesso vem do Google Ads, não do GCP. Depois abra a conta criada › aba Chaves › Adicionar chave › Criar nova › JSON. O arquivo baixado é o que vai na variável do worker.",
        link: { label: "Google Cloud Console — Contas de serviço", url: "https://console.cloud.google.com/iam-admin/serviceaccounts" },
      },
      {
        title: "Cole o JSON na variável do WORKER (não da API)",
        description:
          "Abra o .json num editor de TEXTO PURO (Bloco de Notas — não Word, não editor que reformata), copie tudo e cole em GOOGLE_SERVICE_ACCOUNT_JSON no serviço do worker na Railway. O ponto crítico: a `private_key` precisa ficar em UMA linha, com \n escapados. Se aparecer quebrada em várias linhas, o JSON fica inválido e o sync falha antes de chamar o Google — é o erro mais comum desta integração. Ponha também GOOGLE_ADS_DEVELOPER_TOKEN e, se a conta estiver sob MCC, GOOGLE_ADS_LOGIN_CUSTOMER_ID (só números).",
      },
      GOOGLE_SERVICE_ACCOUNT_STEP,
      {
        title: "Pegue o Customer ID da conta do cliente",
        description:
          "No Google Ads, o Customer ID aparece no topo direito, no formato 123-456-7890. É esse número (com ou sem traços) que vai no campo Customer ID aqui no Bioma.",
        link: { label: "Google Ads", url: "https://ads.google.com/" },
        screenshot: "customer-id",
      },
      {
        title: "Dê acesso à service account da EG",
        description:
          "Em Google Ads › Administrador › Acesso e segurança, convide o e-mail da service account com permissão de Somente leitura. O Bioma só lê dados; nunca cria nem edita campanhas.",
        link: { label: "Google Ads — Acesso e segurança", url: "https://ads.google.com/aw/settings/accountaccess" },
        screenshot: "conceder-acesso",
      },
      {
        title: "Conta já sob o MCC da EG? Pule o passo anterior",
        description:
          "Se a conta já está vinculada ao MCC (Gerente) da EverGreen — o caso das contas da própria EG e dos clientes que a gente administra —, o acesso da service account CASCATEIA pelo MCC. Não é preciso convidar o e-mail conta a conta: basta o Customer ID da conta e o Customer ID do MCC no campo de gerente. Conceder acesso individual aí não quebra nada, só é trabalho repetido.",
        link: { label: "Google Ads — Contas do gerente", url: "https://ads.google.com/aw/accountaccess/managers" },
      },
      {
        title: "Preencha aqui e sincronize",
        description:
          'Cole o Customer ID no card. Se a conta estiver sob um MCC, preencha TAMBÉM o campo "MCC (login customer id)" com o ID da conta gerente — sem ele a API do Google recusa a leitura de conta gerenciada, com erro de permissão que parece falta de acesso. Salve e clique em Sincronizar.',
      },
    ],
    caveat:
      "O worker e a API sao SERVICOS SEPARADOS na Railway: as variaveis do Google vao no WORKER, e redeployar a API nao redeploya o worker. O worker roda como cron job — so gera log quando dispara, e os logs ficam em Deployments (a execucao especifica), nao na aba Logs do servico. " +
      "Há dois caminhos e eles não são intercambiáveis: conta AVULSA (cliente que não está sob o nosso MCC) exige convidar a service account nela; conta SOB O MCC dispensa esse convite mas exige preencher o campo de gerente. Escolher o caminho errado dá o mesmo sintoma — erro de permissão na sincronização.",
    envVars: ["GOOGLE_SERVICE_ACCOUNT_JSON", "GOOGLE_ADS_DEVELOPER_TOKEN"],
  },

  ga4: {
    summary: "Traz aquisição por origem/mídia, sessões, usuários, engajamento e eventos-chave do Google Analytics 4.",
    responsible: "both",
    prerequisites: ["Acesso de administrador à propriedade GA4 do cliente"],
    steps: [
      GOOGLE_SERVICE_ACCOUNT_STEP,
      {
        title: "Pegue o Property ID (não é o 'G-')",
        description:
          "Em GA4 › Administrador › Configurações da propriedade, copie o Property ID — um número puro, tipo 123456789. Cuidado: o código que começa com G- é o Measurement ID e NÃO serve aqui.",
        link: { label: "Google Analytics", url: "https://analytics.google.com/" },
        screenshot: "property-id",
      },
      {
        title: "Adicione a service account como Leitor",
        description:
          "Em GA4 › Administrador › Gerenciamento de acesso à propriedade, clique em + e adicione o e-mail da service account com papel Leitor (Viewer).",
        screenshot: "acesso-ga4",
      },
      {
        title: "Preencha aqui e sincronize",
        description: "Cole o Property ID no card, salve e clique em Sincronizar.",
      },
    ],
    envVars: ["GOOGLE_SERVICE_ACCOUNT_JSON"],
  },

  search_console: {
    summary: "Traz consultas orgânicas, cliques, impressões, CTR e posição média do Google Search Console.",
    responsible: "both",
    prerequisites: ["Propriedade já verificada no Search Console"],
    steps: [
      GOOGLE_SERVICE_ACCOUNT_STEP,
      {
        title: "Identifique o formato da propriedade",
        description:
          "Se for propriedade de domínio, o valor é sc-domain:exemplo.com.br. Se for prefixo de URL, é a URL completa com https:// e barra final. Copie exatamente como aparece no seletor de propriedades.",
        link: { label: "Google Search Console", url: "https://search.google.com/search-console" },
        screenshot: "propriedade",
      },
      {
        title: "Adicione a service account como usuário",
        description:
          "Em Configurações › Usuários e permissões › Adicionar usuário, informe o e-mail da service account com permissão Completo ou Restrito (leitura basta).",
        screenshot: "acesso-gsc",
      },
      {
        title: "Preencha aqui e sincronize",
        description: "Cole a propriedade no card, salve e clique em Sincronizar.",
      },
    ],
    envVars: ["GOOGLE_SERVICE_ACCOUNT_JSON"],
  },

  gtm: {
    summary: "Coleta snapshots do container do Google Tag Manager e aponta problemas de rastreamento (tags, triggers e variáveis).",
    responsible: "both",
    prerequisites: ["Acesso de administrador ao container GTM"],
    steps: [
      GOOGLE_SERVICE_ACCOUNT_STEP,
      {
        title: "Pegue o Account ID e o Container ID",
        description:
          "No GTM, o Container ID é o código GTM-XXXXXXX no topo. O Account ID é o número que aparece na URL quando você abre o container (accounts/NNNNNNNN).",
        link: { label: "Google Tag Manager", url: "https://tagmanager.google.com/" },
        screenshot: "container-id",
      },
      {
        title: "Dê acesso de leitura à service account",
        description:
          "Em Administrador › Gerenciamento de usuários (nível conta), adicione o e-mail da service account com permissão de Leitura.",
        screenshot: "acesso-gtm",
      },
      {
        title: "Preencha aqui e sincronize",
        description: "Cole o Container ID e o Account ID no card, salve e clique em Sincronizar.",
      },
    ],
    envVars: ["GOOGLE_SERVICE_ACCOUNT_JSON"],
  },

  meta_ads: {
    summary: "Traz campanhas, investimento, impressões, cliques, leads e conversões do Meta Ads (Facebook e Instagram).",
    responsible: "both",
    prerequisites: [
      "Cliente com conta de anúncios dentro de um Gerenciador de Negócios",
      "App da EG no Meta for Developers com a permissão ads_read aprovada",
    ],
    steps: [
      {
        title: "Conta já dentro da BM da EG? Pule o próximo passo",
        description:
          "Se a conta de anúncios já pertence ao Gerenciador de Negócios da EverGreen — o caso das contas da própria EG —, não há acesso a solicitar: o token da BM já enxerga a conta. Vá direto para copiar o Ad Account ID.",
        link: { label: "Meta Business Suite — Contas de anúncios", url: "https://business.facebook.com/settings/ad-accounts" },
      },
      {
        title: "Conta do cliente: peça acesso à BM dele",
        description:
          "No Gerenciador de Negócios da EG, vá em Configurações do negócio › Contas › Contas de anúncios › Adicionar › Solicitar acesso a uma conta de anúncios, e informe o ID da conta do cliente. O cliente aprova pelo Gerenciador dele. Este passo NÃO se aplica a conta que já é da EG.",
        link: { label: "Meta Business Suite", url: "https://business.facebook.com/settings" },
        screenshot: "solicitar-acesso",
      },
      {
        title: "Copie o Ad Account ID",
        description:
          "O ID aparece como act_1234567890 no Gerenciador de Anúncios. Pode colar com ou sem o prefixo act_ — o Bioma normaliza.",
        link: { label: "Gerenciador de Anúncios", url: "https://adsmanager.facebook.com/" },
        screenshot: "ad-account-id",
      },
      {
        title: "Preencha aqui e sincronize",
        description: "Cole o Ad Account ID no card, salve e clique em Sincronizar.",
      },
    ],
    envVars: ["META_ADS_ACCESS_TOKEN"],
    caveat:
      "O token da Meta é de longa duração mas não é eterno. Se a sincronização começar a falhar com erro de autenticação, é sinal de que o token precisa ser renovado no ambiente da EG.",
  },

  linkedin_ads: {
    summary: "Traz campanhas, investimento e leads qualificados do LinkedIn Ads (mídia paga B2B).",
    responsible: "both",
    prerequisites: ["Acesso à conta de anúncios do cliente no Campaign Manager"],
    steps: [
      {
        title: "Copie o Sponsored Account ID",
        description:
          "No LinkedIn Campaign Manager, o ID da conta aparece na URL depois de /accounts/ — apenas os dígitos.",
        link: { label: "LinkedIn Campaign Manager", url: "https://www.linkedin.com/campaignmanager/" },
        screenshot: "account-id",
      },
      {
        title: "Garanta que o usuário do token tem acesso",
        description:
          "A pessoa cujo token está configurado no ambiente da EG precisa ter papel de Visualizador (ou superior) na conta de anúncios do cliente.",
        screenshot: "acesso-linkedin",
      },
      {
        title: "Preencha aqui e sincronize",
        description: "Cole o Sponsored Account ID no card, salve e clique em Sincronizar.",
      },
    ],
    envVars: ["LINKEDIN_ADS_ACCESS_TOKEN"],
  },

  instagram_organic: {
    summary:
      "Traz os posts e Reels publicados (legenda, alcance, curtidas, comentários, salvamentos, plays) e gera a transcrição dos vídeos — é a base da Retrospectiva de Conteúdo e do banco de ganchos.",
    responsible: "both",
    prerequisites: [
      "Perfil do cliente convertido em Conta Comercial ou de Criador",
      "Perfil vinculado a uma Página do Facebook dentro do Gerenciador de Negócios",
    ],
    steps: [
      {
        title: "Confirme que a conta é Business (não pessoal)",
        description:
          "No app do Instagram: Configurações › Tipo de conta e ferramentas. A API de insights não funciona em perfil pessoal — esse é o motivo nº 1 de falha nessa conexão.",
        screenshot: "conta-business",
      },
      {
        title: "Pegue o Instagram Business Account ID",
        description:
          "É um número longo (17 dígitos, começa com 178414...). Dá pra obter no Explorador da Graph API consultando a Página vinculada com o campo instagram_business_account.",
        link: { label: "Explorador da Graph API", url: "https://developers.facebook.com/tools/explorer/" },
        screenshot: "ig-account-id",
      },
      {
        title: "Confirme as permissões do token da EG",
        description:
          "O token precisa ter instagram_basic e instagram_manage_insights. Atenção: são permissões diferentes das usadas pelo Meta Ads — ter Meta Ads funcionando não garante que o orgânico funcione.",
        screenshot: "permissoes-ig",
      },
      {
        title: "Preencha aqui e sincronize",
        description:
          "Cole o Business Account ID no card, salve e clique em Sincronizar. A transcrição dos vídeos roda junto, se a chave de IA estiver configurada no worker.",
      },
    ],
    envVars: ["INSTAGRAM_ACCESS_TOKEN", "OPENAI_API_KEY (para transcrição)"],
  },

  google_business_profile: {
    summary:
      "Traz impressões no Maps e na Busca, cliques no site, ligações e pedidos de rota do Google Meu Negócio — a métrica que mais importa para cliente com ponto físico.",
    responsible: "both",
    prerequisites: [
      "Ficha do cliente verificada e ativa há mais de 60 dias",
      "Acesso à API aprovado pelo Google no projeto GCP da EG",
    ],
    steps: [
      {
        title: "Solicite acesso à API (uma vez, para toda a EG)",
        description:
          "Projetos novos começam com cota ZERO nessa API — ela não funciona só habilitando. É preciso preencher o formulário de acesso do Google descrevendo o uso e aguardar aprovação. Faça isso antes de prometer prazo ao cliente.",
        link: { label: "Google — pré-requisitos e formulário", url: "https://developers.google.com/my-business/content/prereqs" },
        screenshot: "solicitar-api",
      },
      GOOGLE_SERVICE_ACCOUNT_STEP,
      {
        title: "Adicione a service account como gerente da ficha",
        description:
          "No perfil do cliente, vá em Configurações da empresa › Pessoas e acesso › Adicionar, e inclua o e-mail da service account como Gerente.",
        link: { label: "Google Meu Negócio", url: "https://business.google.com/" },
        screenshot: "acesso-gbp",
      },
      {
        title: "Pegue o Location ID",
        description:
          "Aparece no formato locations/1234567890. Você encontra na URL ao abrir a ficha, ou listando as localizações pela API.",
        screenshot: "location-id",
      },
      {
        title: "Preencha aqui e sincronize",
        description: "Cole o Location ID no card, salve e clique em Sincronizar.",
      },
    ],
    envVars: ["GOOGLE_SERVICE_ACCOUNT_JSON"],
    caveat:
      "Esta é a integração de aprovação mais demorada de todas — o Google analisa manualmente. Não é limitação do Bioma.",
  },

  google_adsense: {
    summary: "Traz receita estimada, pageviews, cliques e impressões do AdSense — relevante para cliente que monetiza conteúdo.",
    responsible: "both",
    prerequisites: ["Conta AdSense ativa do cliente"],
    steps: [
      GOOGLE_SERVICE_ACCOUNT_STEP,
      {
        title: "Pegue o Account ID (pub-...)",
        description:
          "Em AdSense › Conta › Informações da conta, o ID do editor aparece como pub-1234567890123456. O valor completo aqui é accounts/pub-1234567890123456.",
        link: { label: "Google AdSense", url: "https://www.google.com/adsense/" },
        screenshot: "publisher-id",
      },
      {
        title: "Conceda acesso à service account",
        description:
          "Em AdSense › Conta › Acesso e autorização › Acesso de usuários, adicione o e-mail da service account.",
        screenshot: "acesso-adsense",
      },
      {
        title: "Preencha aqui e sincronize",
        description: "Cole o Account ID no card, salve e clique em Sincronizar.",
      },
    ],
    envVars: ["GOOGLE_SERVICE_ACCOUNT_JSON"],
  },

  youtube_organic: {
    summary: "Traz os vídeos publicados no canal com visualizações, curtidas e comentários.",
    responsible: "eg",
    prerequisites: ["Nenhum acesso do cliente é necessário — estatística de vídeo é dado público"],
    steps: [
      {
        title: "Pegue o Channel ID (não é o @handle)",
        description:
          "O Channel ID começa com UC e tem 24 caracteres. Em YouTube Studio › Configurações › Canal › Configurações avançadas ele aparece como 'ID do canal'. O @nome do canal NÃO funciona aqui.",
        link: { label: "YouTube Studio", url: "https://studio.youtube.com/" },
        screenshot: "channel-id",
      },
      {
        title: "Preencha aqui e sincronize",
        description:
          "Cole o Channel ID no card, salve e clique em Sincronizar. Esta é a integração mais simples de todas: não exige autorização do cliente.",
      },
    ],
    envVars: ["YOUTUBE_API_KEY"],
  },

  tiktok_organic: {
    summary:
      "Traz os vídeos publicados no TikTok com visualizações, curtidas, comentários e compartilhamentos — alimenta a Retrospectiva de Conteúdo junto com o Instagram.",
    responsible: "client",
    prerequisites: ["Cliente com acesso à conta TikTok que será conectada"],
    steps: [
      {
        title: "Tenha o cliente por perto (ou envie o link)",
        description:
          "Diferente do Google, aqui não existe 'dar acesso a uma conta de serviço': quem autoriza é a própria conta do cliente, logada. Ou o cliente faz o clique final, ou vocês fazem juntos.",
      },
      {
        title: "Clique em Conectar via OAuth",
        description:
          "O botão no card leva à tela de consentimento oficial do TikTok. Confira que a conta logada no navegador é a do CLIENTE, não a da EG — o TikTok conecta a conta que estiver logada.",
        screenshot: "consentimento-tiktok",
      },
      {
        title: "Autorize e volte",
        description:
          "Depois de autorizar, o TikTok redireciona de volta ao Bioma e a conexão aparece conectada sozinha. Nenhum ID precisa ser digitado.",
        screenshot: "conectado",
      },
    ],
    envVars: ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"],
    caveat:
      "É uma integração diferente do TikTok Ads: portal de desenvolvedor diferente, app diferente e token diferente. Conectar uma não conecta a outra.",
  },

  tiktok_ads: {
    summary: "Traz campanhas, investimento, impressões, cliques e conversões do TikTok Ads (mídia paga).",
    responsible: "client",
    prerequisites: ["Cliente com conta ativa no TikTok Ads Manager"],
    steps: [
      {
        title: "Entenda o que vai ser autorizado",
        description:
          "Uma única autorização pode liberar VÁRIAS contas de anúncio de uma vez — o TikTok devolve todas as contas às quais aquele login tem acesso. O Bioma cria um registro por conta e todas aparecem listadas neste mesmo card.",
      },
      {
        title: "Clique em Conectar via OAuth",
        description:
          "O botão leva ao portal do TikTok for Business. Confirme que está logado com a conta do cliente e selecione quais contas de anúncio deseja autorizar.",
        screenshot: "selecionar-contas",
      },
      {
        title: "Confira as contas conectadas",
        description:
          "Ao voltar, o card mostra todas as contas autorizadas. Se alguma não deveria estar ali, use 'Desativar esta conta' — ela para de sincronizar sem afetar as demais.",
        screenshot: "contas-conectadas",
      },
    ],
    envVars: ["TIKTOK_ADS_APP_ID", "TIKTOK_ADS_SECRET"],
    caveat:
      "O app do TikTok Ads é registrado no TikTok for Business (business-api.tiktok.com), que é um portal SEPARADO do TikTok for Developers usado pelo TikTok orgânico. São dois cadastros, dois pares de credenciais.",
  },

  linkedin_organic: {
    summary: "Traz impressões, cliques, curtidas, comentários e compartilhamentos dos posts da página da empresa no LinkedIn.",
    responsible: "client",
    prerequisites: ["Cliente com papel de Administrador na página da empresa no LinkedIn"],
    steps: [
      {
        title: "Confirme o papel de administrador",
        description:
          "A autorização só enxerga páginas onde a pessoa logada é Administrador (Super admin). Se ela for só Editor de conteúdo, a lista volta vazia — esse é o erro mais comum aqui.",
        screenshot: "admin-pagina",
      },
      {
        title: "Clique em Conectar via OAuth",
        description:
          "O botão leva à tela de consentimento do LinkedIn. Confirme que o navegador está logado com a conta que administra a página do cliente.",
        screenshot: "consentimento-linkedin",
      },
      {
        title: "Confira as páginas conectadas",
        description:
          "O Bioma conecta todas as páginas que aquele login administra. Se vierem páginas demais, desative as que não interessam individualmente no card.",
        screenshot: "paginas-conectadas",
      },
    ],
    envVars: ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"],
    caveat:
      "Estatística de post no LinkedIn tem janela móvel de 12 meses — dados mais antigos que isso não voltam pela API, independente do Bioma.",
  },

  rd_station_crm: {
    summary: "Traz funis, negociações, valores e etapas do RD Station CRM para as métricas comerciais do cliente.",
    responsible: "both",
    prerequisites: ["Conta RD Station CRM ativa", "Usuário com permissão de administrador no CRM"],
    steps: [
      {
        title: "Gere o token da instância",
        description:
          "No RD Station CRM, vá em Configurações › Integrações › API e copie o token de acesso. É um token por instância — não expira sozinho, mas pode ser revogado ali mesmo.",
        link: { label: "RD Station CRM", url: "https://crm.rdstation.com/" },
        screenshot: "token-rd",
      },
      {
        title: "Cole o token aqui",
        description:
          "Cole no campo do card e salve. O token é gravado cifrado no banco do Bioma — nunca em texto puro, nunca exibido de volta depois de salvo.",
      },
      {
        title: "Sincronize",
        description: "Clique em Sincronizar para trazer os funis e negociações.",
      },
    ],
    caveat: "Se o token for revogado no RD Station, a sincronização passa a falhar com erro de autenticação — basta gerar outro e colar novamente.",
  },

  hubspot: {
    summary: "Traz negócios (deals), pipelines, etapas e valores do HubSpot CRM.",
    responsible: "both",
    prerequisites: ["Conta HubSpot com permissão para criar apps privados (Super admin)"],
    steps: [
      {
        title: "Crie um app privado",
        description:
          "No HubSpot, vá em Configurações › Integrações › Apps privados › Criar app privado. Dê um nome (ex.: Bioma EverGreen).",
        link: { label: "HubSpot — Apps privados", url: "https://app.hubspot.com/private-apps" },
        screenshot: "criar-app-privado",
      },
      {
        title: "Marque apenas os escopos de leitura",
        description:
          "Na aba Escopos, marque crm.objects.deals.read e crm.objects.contacts.read. Não marque escopos de escrita — o Bioma só lê do HubSpot.",
        screenshot: "escopos",
      },
      {
        title: "Copie o token de acesso",
        description:
          "Ao criar, o HubSpot mostra o token uma única vez (começa com pat-). Copie antes de fechar a tela.",
        screenshot: "token-hubspot",
      },
      {
        title: "Cole o token aqui e sincronize",
        description:
          "Cole no campo do card, salve e clique em Sincronizar. O token é gravado cifrado no banco do Bioma.",
      },
    ],
  },
};

export function guideFor(provider: string): IntegrationGuideContent | null {
  return INTEGRATION_GUIDES[provider] ?? null;
}

export function screenshotPath(provider: string, slug: string): string {
  return `/assets/integration-guides/${provider}/${slug}.png`;
}
