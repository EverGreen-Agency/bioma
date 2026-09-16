export type UnivetFront = 'growth' | 'infra' | 'seo';
export type PriorityLevel = 'P0' | 'P1' | 'P2';
export type TaskStatus = 'pronto_para_iniciar' | 'em_andamento' | 'planejado';

export interface BacklogTask {
  id: string;
  front: UnivetFront;
  title: string;
  description: string;
  priority: PriorityLevel;
  timeline: string;
  acceptanceCriteria: string;
  status: TaskStatus;
  owner: string;
}

export interface FunnelSegment {
  id: string;
  name: string;
  defaultTicket: number;
  description: string;
  steps: {
    leads: number;
    contactRate: number; // 0 a 100
    qualifiedRate: number; // 0 a 100
    demoRate: number; // 0 a 100
    closeRate: number; // 0 a 100
  };
}

export interface SlideData {
  id: number;
  slug: string;
  badge: string;
  title: string;
  subtitle: string;
}

export const SLIDES: SlideData[] = [
  {
    id: 1,
    slug: 'alinhamento-estrategico',
    badge: 'Slide 01 · Eixo do Projeto',
    title: 'Da Métrica de Vaidade ao Faturamento Real de Lupas',
    subtitle: 'Por que o projeto da Univet Loupes é centrado em oportunidades qualificadas e vendas, não apenas em cliques e formulários.',
  },
  {
    id: 2,
    slug: 'metodo-evergreen',
    badge: 'Slide 02 · Método Raiz',
    title: 'O Sistema EverGreen Aplicado à Univet',
    subtitle: 'Os 3 pilares de receita (Oferta, Demanda e Conversão) sustentados por Dados, Tecnologia, Pessoas e Processo comercial.',
  },
  {
    id: 3,
    slug: 'tres-frentes-paralelas',
    badge: 'Slide 03 · Estrutura Operacional',
    title: 'As 3 Frentes Paralelas de Execução Imediata',
    subtitle: 'Como Growth, Infraestrutura e SEO trabalham simultaneamente desde a semana 01 para evitar semanas travadas em setup.',
  },
  {
    id: 4,
    slug: 'simulador-funil',
    badge: 'Slide 04 · Unit Economics',
    title: 'Simulador de Funil Comercial & Identificação de Gargalos',
    subtitle: 'Calcule o impacto financeiro de cada etapa do funil: Leads → Contato → Qualificado → Demonstração → Fechamento.',
  },
  {
    id: 5,
    slug: 'roadmap-backlog',
    badge: 'Slide 05 · Plano de Ação',
    title: 'Roadmap de 90 Dias & Sprint de Kickoff (Dias 1-7)',
    subtitle: 'Backlog transparente, prioridades cirúrgicas e o checklist dos primeiros 7 dias para início imediato da operação.',
  },
];

export const FRONT_DETAILS = {
  growth: {
    label: 'Growth & Mídia',
    shortTitle: 'Growth',
    tagline: 'Demanda intencional e mensuração de vendas',
    color: '#00491E',
    accentColor: '#10B981',
    kpis: ['Custo por Lead Qualificado (CPLQ)', 'Taxa de Agendamento de Demonstração', 'CAC Real por Venda', 'ROAS Comercial'],
    pillars: [
      {
        title: 'Segmentação por Especialidade',
        text: 'Campanhas hiper-focadas: Odontologia (Endo/Perio/Prótese) vs. Medicina (Plástica, Vascular, Oftalmo).',
      },
      {
        title: 'Funil Oficial de Aquisição',
        text: 'Anúncio de Dor/Ergonomia → Landing Page Técnica → Formulário/WhatsApp com UTMs → Kommo CRM.',
      },
      {
        title: 'Backlog de Criativos Contínuo',
        text: 'Vídeos de demonstração óptica, antes/depois da postura de trabalho e depoimentos de especialistas.',
      },
      {
        title: 'Rotina Semanal de Testes',
        text: 'Análise toda segunda-feira cruzando gasto de mídia com propostas abertas no CRM.',
      },
    ],
  },
  infra: {
    label: 'Infra & Implementação',
    shortTitle: 'Infraestrutura',
    tagline: 'Integrações seguras, dados limpos e resposta ágil',
    color: '#4E4B48',
    accentColor: '#3B82F6',
    kpis: ['SLA de Primeiro Contato (< 15 min)', 'Consistência de UTMs no CRM (100%)', 'Core Web Vitals Verde', 'Taxa de Erro 0%'],
    pillars: [
      {
        title: 'Validação do Site em Produção',
        text: 'Auditoria de mobile, tempos de carregamento, responsividade e fluxo de envio sem atrito.',
      },
      {
        title: 'Integração Site → Kommo CRM',
        text: 'Webhook enviando UTMs, produto de interesse, estado/cidade e especialidade diretamente na esteira do representante.',
      },
      {
        title: 'Stack Completa de Tracking',
        text: 'Google Tag Manager + GA4 + Meta Pixel/CAPI (server-side) + Google Ads + Microsoft Clarity.',
      },
      {
        title: 'Cockpit Marketing → Vendas',
        text: 'Dashboard unificado que permite enxergar em tempo real o retorno de cada anúncio até o dinheiro no caixa.',
      },
    ],
  },
  seo: {
    label: 'SEO & Conteúdo Técnico',
    shortTitle: 'SEO',
    tagline: 'Autoridade orgânica de longo prazo e menor CAC',
    color: '#1E293B',
    accentColor: '#F59E0B',
    kpis: ['Posicionamento Top 3 em Termos Transacionais', 'Tráfego Orgânico Qualificado', 'Leads Orgânicos sem Custo de Mídia', 'Páginas Indexadas'],
    pillars: [
      {
        title: 'Auditoria Técnica & Indexação',
        text: 'Correção de sitemap, canonicals, robots.txt, redirects e schema markup (MedicalDevice / Product).',
      },
      {
        title: 'Google Search Console & GA4',
        text: 'Monitoramento contínuo de impressões, CTR e termos de busca com maior conversão para lupas.',
      },
      {
        title: 'Arquitetura de Produtos e Categorias',
        text: 'Otimização de headings (H1/H2), meta tags e descrições das linhas Galileanas, Prismáticas e Ergonômicas.',
      },
      {
        title: 'Backlog Editorial de Alta Autoridade',
        text: 'Conteúdos cirúrgicos sobre prevenção de dores cervicais, guia de magnificação (2.5x vs 3.5x vs 5.0x) e normas de segurança.',
      },
    ],
  },
};

export const FUNNEL_SEGMENTS: FunnelSegment[] = [
  {
    id: 'odonto',
    name: 'Odontologia de Alta Performance',
    defaultTicket: 11500,
    description: 'Cirurgiões-dentistas (Endo, Perio, Implante, Estética). Alto volume, decisão focada em ergonomia diária e precisão de preparo.',
    steps: {
      leads: 120,
      contactRate: 75,
      qualifiedRate: 55,
      demoRate: 45,
      closeRate: 35,
    },
  },
  {
    id: 'medicina',
    name: 'Especialidades Médicas Cirúrgicas',
    defaultTicket: 18500,
    description: 'Cirurgia Plástica, Vascular, Neuro, Oftalmo. Decisão consultiva, ciclo de venda mais longo, ticket muito elevado.',
    steps: {
      leads: 60,
      contactRate: 70,
      qualifiedRate: 50,
      demoRate: 40,
      closeRate: 40,
    },
  },
];

export const BACKLOG_TASKS: BacklogTask[] = [
  {
    id: 'P0-01',
    front: 'infra',
    title: 'Coleta e validação de acessos das plataformas',
    description: 'Concessão de acesso administrativo para Meta Ads, Google Ads, GTM, GA4, Kommo CRM, domínio e hospedagem.',
    priority: 'P0',
    timeline: 'Dias 1 a 3',
    acceptanceCriteria: 'Todos os acessos conferidos, autenticados em cofre seguro e validados pela equipe técnica.',
    status: 'pronto_para_iniciar',
    owner: 'EverGreen + Univet',
  },
  {
    id: 'P0-02',
    front: 'infra',
    title: 'Auditoria técnica e QA do novo site em produção',
    description: 'Varredura completa de usabilidade em mobile, carregamento, testes de formulários e acionamento do botão de WhatsApp.',
    priority: 'P0',
    timeline: 'Dias 2 a 5',
    acceptanceCriteria: 'Zero erros de envio de formulário, tempo de carregamento < 2s no mobile e formulários com validação estrita.',
    status: 'pronto_para_iniciar',
    owner: 'EverGreen Tech',
  },
  {
    id: 'P0-03',
    front: 'infra',
    title: 'Integração Site Novo → Kommo CRM com UTMs',
    description: 'Configuração de webhook para injetar automaticamente os dados de leads com parâmetros UTM, especialidade e cidade.',
    priority: 'P0',
    timeline: 'Dias 3 a 7',
    acceptanceCriteria: 'Leads teste chegam com campos personalizados preenchidos e direcionados para a esteira correta no Kommo.',
    status: 'pronto_para_iniciar',
    owner: 'EverGreen Tech',
  },
  {
    id: 'P0-04',
    front: 'infra',
    title: 'Setup da stack de tracking (GTM, GA4, Meta CAPI, Clarity)',
    description: 'Implementação de tags unificadas no GTM, Conversions API server-side para contornar bloqueadores e mapas de calor no Clarity.',
    priority: 'P0',
    timeline: 'Dias 3 a 7',
    acceptanceCriteria: 'Eventos de conversão validados no Google Tag Assistant e Meta Events Manager com nota de correspondência Excelente.',
    status: 'pronto_para_iniciar',
    owner: 'EverGreen Tech',
  },
  {
    id: 'P0-05',
    front: 'growth',
    title: 'Auditoria do histórico de mídia paga e definição de funil',
    description: 'Diagnóstico das campanhas anteriores de Google e Meta: custo por lead histórico, canais de melhor conversão e vazamentos.',
    priority: 'P0',
    timeline: 'Dias 4 a 7',
    acceptanceCriteria: 'Documento entregue com aprendizados históricos, baseline de CPL e régua oficial do funil de aquisição.',
    status: 'pronto_para_iniciar',
    owner: 'EverGreen Growth',
  },
  {
    id: 'P0-06',
    front: 'seo',
    title: 'Setup do Google Search Console & Auditoria de Indexação',
    description: 'Verificação de propriedade no GSC, envio de sitemap atualizado, auditoria de robots.txt, links canônicos e erros 404.',
    priority: 'P0',
    timeline: 'Dias 5 a 7',
    acceptanceCriteria: 'GSC configurado sem erros críticos de rastreamento e todas as páginas institucionais e de produto rastreáveis.',
    status: 'pronto_para_iniciar',
    owner: 'EverGreen SEO',
  },
  {
    id: 'P1-01',
    front: 'growth',
    title: 'Estruturação e lançamento das campanhas prioritárias',
    description: 'Subir campanhas de Google Search de altíssima intenção (termos comerciais) e Meta Ads segmentado por especialidades.',
    priority: 'P1',
    timeline: 'Dias 8 a 15',
    acceptanceCriteria: 'Campanhas ativas gerando leads qualificados para a esteira do Kommo CRM.',
    status: 'planejado',
    owner: 'EverGreen Growth',
  },
  {
    id: 'P1-02',
    front: 'growth',
    title: 'Levantamento de materiais e backlog de novos criativos',
    description: 'Mapeamento de fotos/vídeos existentes da Univet Loupes e confecção de novos ângulos de anúncio com foco em ergonomia e precisão.',
    priority: 'P1',
    timeline: 'Dias 10 a 20',
    acceptanceCriteria: 'Primeiro lote de 6 novos criativos aprovados e inseridos nos testes A/B de anúncio.',
    status: 'planejado',
    owner: 'EverGreen Growth',
  },
  {
    id: 'P1-03',
    front: 'infra',
    title: 'Alinhamento de rotina e treinamento de CRM com representantes',
    description: 'Orientação com os representantes comerciais sobre movimentação dos cards no Kommo CRM e preenchimento de motivos de perda.',
    priority: 'P1',
    timeline: 'Dias 8 a 15',
    acceptanceCriteria: '100% dos representantes ativos movimentando leads e marcando reuniões/testes no CRM.',
    status: 'planejado',
    owner: 'EverGreen + Gestão Comercial Univet',
  },
  {
    id: 'P1-04',
    front: 'seo',
    title: 'Pesquisa aprofundada de palavras-chave por especialidade',
    description: 'Mapeamento semântico de buscas: produto + especialidade médica/odonto + problemas de postura + intenção de compra.',
    priority: 'P1',
    timeline: 'Dias 10 a 25',
    acceptanceCriteria: 'Planilha estratégica com oportunidades de palavras-chave, volume, dificuldade e URL de destino recomendada.',
    status: 'planejado',
    owner: 'EverGreen SEO',
  },
  {
    id: 'P1-05',
    front: 'infra',
    title: 'Dashboard de Aquisição Integrada (Mídia → CRM → Venda)',
    description: 'Criação de painel executivo com visualização das etapas: Gasto em anúncios → CPL → Demos Agendadas → Vendas Totais (R$).',
    priority: 'P1',
    timeline: 'Dias 15 a 30',
    acceptanceCriteria: 'Dashboard operacional atualizado semanalmente para orientar decisões da diretoria.',
    status: 'planejado',
    owner: 'EverGreen Tech',
  },
  {
    id: 'P2-01',
    front: 'seo',
    title: 'Backlog editorial e publicação dos 4 primeiros conteúdos pilares',
    description: 'Produção de guias técnicos de alta relevância (ex: "Guia Completo de Lupas Cirúrgicas", "Ergonomia para Cirurgiões-Dentistas").',
    priority: 'P2',
    timeline: 'Dias 31 a 60',
    acceptanceCriteria: 'Artigos otimizados publicados, indexados e rankeando para termos de topo e meio de funil.',
    status: 'planejado',
    owner: 'EverGreen SEO',
  },
  {
    id: 'P2-02',
    front: 'growth',
    title: 'Otimização com feedback de conversões offline (CAPI)',
    description: 'Envio de eventos de fechamento do Kommo CRM de volta para o Meta Ads e Google Ads para calibrar os algoritmos de lances.',
    priority: 'P2',
    timeline: 'Dias 31 a 60',
    acceptanceCriteria: 'Algoritmos aprendendo com o perfil de compradores reais e não apenas com quem preenche formulário.',
    status: 'planejado',
    owner: 'EverGreen Tech + Growth',
  },
  {
    id: 'P2-03',
    front: 'growth',
    title: 'Estratégia de geolocalização e rotas de representantes',
    description: 'Aceleração de anúncios nas cidades e regiões onde o representante da Univet estará presente em feiras ou visitas presenciais.',
    priority: 'P2',
    timeline: 'Dias 45 a 75',
    acceptanceCriteria: 'Agendas de demonstrações lotadas antecipadamente para as viagens dos representantes.',
    status: 'planejado',
    owner: 'EverGreen Growth',
  },
  {
    id: 'P2-04',
    front: 'seo',
    title: 'Implementação de Schema Markup Médico e Otimização Core Web Vitals',
    description: 'Inserção de dados estruturados Schema.org para dispositivos médicos, autorias técnicas e pontuação verde no PageSpeed.',
    priority: 'P2',
    timeline: 'Dias 60 a 90',
    acceptanceCriteria: 'Rich snippets ativos nas buscas do Google e notas > 90 em mobile no Google Lighthouse.',
    status: 'planejado',
    owner: 'EverGreen SEO + Tech',
  },
];

export function calculateFunnelResults(
  leads: number,
  contactRate: number,
  qualifiedRate: number,
  demoRate: number,
  closeRate: number,
  ticket: number,
) {
  const contacts = Math.round(leads * (contactRate / 100));
  const qualified = Math.round(contacts * (qualifiedRate / 100));
  const demos = Math.round(qualified * (demoRate / 100));
  const sales = Math.round(demos * (closeRate / 100));
  const revenue = sales * ticket;

  const overallConversion = leads > 0 ? ((sales / leads) * 100).toFixed(2) : '0';

  // Identificação do maior gargalo
  const dropLeadsToContact = leads - contacts;
  const dropContactToQual = contacts - qualified;
  const dropQualToDemo = qualified - demos;
  const dropDemoToSales = demos - sales;

  let bottleneck = 'Entrada de Leads';
  let bottleneckLoss = 0;
  let bottleneckAdvice = 'Aumentar o volume de tráfego qualificado com intenção de compra.';

  if (dropLeadsToContact >= dropContactToQual && dropLeadsToContact >= dropQualToDemo && dropLeadsToContact >= dropDemoToSales) {
    bottleneck = 'Contato Inicial (Velocidade de Resposta)';
    bottleneckLoss = dropLeadsToContact;
    bottleneckAdvice = 'Gargalo no tempo de resposta do representante ao lead novo. Reduzir SLA para menos de 15 minutos.';
  } else if (dropContactToQual >= dropQualToDemo && dropContactToQual >= dropDemoToSales) {
    bottleneck = 'Qualificação de Perfil';
    bottleneckLoss = dropContactToQual;
    bottleneckAdvice = 'Muitos leads sem poder de compra ou especialidade incompatível. Refinar segmentação demográfica na mídia.';
  } else if (dropQualToDemo >= dropDemoToSales) {
    bottleneck = 'Agendamento de Demonstração / Teste';
    bottleneckLoss = dropQualToDemo;
    bottleneckAdvice = 'Fricção para marcar teste prático presencial. Facilitar calendário do representante e envio de maletas.';
  } else {
    bottleneck = 'Fechamento da Proposta';
    bottleneckLoss = dropDemoToSales;
    bottleneckAdvice = 'Objeção de preço ou condições de parcelamento. Ajustar cadência de follow-up pós-teste óptico.';
  }

  return {
    contacts,
    qualified,
    demos,
    sales,
    revenue,
    overallConversion,
    bottleneck,
    bottleneckLoss,
    bottleneckAdvice,
  };
}
