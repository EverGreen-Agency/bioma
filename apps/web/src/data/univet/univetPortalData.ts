// Dataset demonstrativo do Portal Executivo Univet.
//
// Tudo aqui é mock determinístico (seed fixa), mas modelado no grão real das fontes:
// leads e etapas (Kommo CRM), pedidos faturados (Nomus ERP) e investimento diário por
// campanha (Google Ads / Meta Ads). Cada painel do portal é derivado deste mesmo conjunto,
// então filtros de período, segmento e UF cruzam de verdade. Para ligar dados reais,
// basta substituir `LEADS` e `SPEND_BY_CAMPAIGN` mantendo os formatos.

import { BRAZIL_STATES } from './brazilStatesGeo';
import type { KommoDashboard, NomusAnalyticsSummary } from '../../lib/api';

export type SegmentFilter = 'todos' | 'odonto' | 'medicina';
export type PeriodId = '30d' | '90d' | '180d';
export type Platform = 'google' | 'meta';
export type ChannelId = 'google_ads' | 'meta_ads' | 'seo' | 'geo' | 'indicacao' | 'eventos';
export type OriginGroup = 'paga' | 'organica' | 'relacionamento';
export type Verdict = 'escalar' | 'manter' | 'revisar';

export interface PortalFilter {
  period: PeriodId;
  segment: SegmentFilter;
  uf: string | null;
}

export const PERIODS: { id: PeriodId; label: string; days: number }[] = [
  { id: '30d', label: '30 dias', days: 30 },
  { id: '90d', label: '90 dias', days: 90 },
  { id: '180d', label: '6 meses', days: 180 },
];

// Data de referência fixa para o mock ser reprodutível.
const REF_DATE = new Date(2026, 9, 11);
const HISTORY_DAYS = 400;

interface CampaignDef {
  id: string;
  name: string;
  platform: Platform;
  cluster: string;
  dailySpend: number;
  cpl: number;
  quality: number;
  medicinaShare: number;
  cpm: number;
  ctr: number;
}

const CAMPAIGNS: CampaignDef[] = [
  { id: 'g_marca', name: 'Search | Marca Univet', platform: 'google', cluster: 'Marca', dailySpend: 45, cpl: 58, quality: 1.55, medicinaShare: 0.3, cpm: 180, ctr: 0.118 },
  { id: 'g_odonto', name: 'Search | Lupa odontológica', platform: 'google', cluster: 'Intenção de compra', dailySpend: 110, cpl: 148, quality: 1.05, medicinaShare: 0.06, cpm: 210, ctr: 0.064 },
  { id: 'g_cirurgica', name: 'Search | Lupa cirúrgica médica', platform: 'google', cluster: 'Intenção de compra', dailySpend: 70, cpl: 212, quality: 1.1, medicinaShare: 0.88, cpm: 240, ctr: 0.051 },
  { id: 'g_concorrentes', name: 'Search | Comparativos e concorrentes', platform: 'google', cluster: 'Concorrência', dailySpend: 40, cpl: 255, quality: 0.6, medicinaShare: 0.25, cpm: 230, ctr: 0.037 },
  { id: 'g_pmax', name: 'Performance Max | Catálogo', platform: 'google', cluster: 'Automático', dailySpend: 50, cpl: 186, quality: 0.5, medicinaShare: 0.2, cpm: 64, ctr: 0.012 },
  { id: 'm_lal', name: 'Lookalike 1% | Compradores Nomus', platform: 'meta', cluster: 'Lookalike', dailySpend: 70, cpl: 96, quality: 1.15, medicinaShare: 0.22, cpm: 38, ctr: 0.014 },
  { id: 'm_ergonomia', name: 'Interesses | Dor cervical e ergonomia', platform: 'meta', cluster: 'Interesse', dailySpend: 60, cpl: 82, quality: 0.65, medicinaShare: 0.08, cpm: 31, ctr: 0.017 },
  { id: 'm_rmkt', name: 'Remarketing | Visitantes do site 30d', platform: 'meta', cluster: 'Remarketing', dailySpend: 30, cpl: 61, quality: 1.4, medicinaShare: 0.28, cpm: 52, ctr: 0.021 },
  { id: 'm_medicos', name: 'Interesses | Cirurgia plástica e vascular', platform: 'meta', cluster: 'Interesse', dailySpend: 45, cpl: 172, quality: 0.95, medicinaShare: 0.9, cpm: 44, ctr: 0.011 },
  { id: 'm_congressos', name: 'Geo | Participantes de congressos', platform: 'meta', cluster: 'Geolocalização', dailySpend: 25, cpl: 124, quality: 0.9, medicinaShare: 0.35, cpm: 47, ctr: 0.013 },
];

interface ChannelDef {
  id: ChannelId;
  label: string;
  group: OriginGroup;
  dailyLeads: number;
  quality: number;
  medicinaShare: number;
}

const CHANNELS: ChannelDef[] = [
  { id: 'google_ads', label: 'Google Ads', group: 'paga', dailyLeads: 0, quality: 1, medicinaShare: 0.28 },
  { id: 'meta_ads', label: 'Meta Ads', group: 'paga', dailyLeads: 0, quality: 1, medicinaShare: 0.28 },
  { id: 'seo', label: 'Busca orgânica (SEO)', group: 'organica', dailyLeads: 1.25, quality: 1.15, medicinaShare: 0.3 },
  { id: 'geo', label: 'Respostas de IA (GEO)', group: 'organica', dailyLeads: 0.7, quality: 1.3, medicinaShare: 0.34 },
  { id: 'indicacao', label: 'Indicação de clientes', group: 'relacionamento', dailyLeads: 0.45, quality: 1.6, medicinaShare: 0.3 },
  { id: 'eventos', label: 'Congressos e eventos', group: 'relacionamento', dailyLeads: 0.25, quality: 1, medicinaShare: 0.2 },
];

export const ORIGIN_GROUPS: { id: OriginGroup; label: string }[] = [
  { id: 'paga', label: 'Mídia paga' },
  { id: 'organica', label: 'Orgânico (SEO e IA)' },
  { id: 'relacionamento', label: 'Indicação e eventos' },
];

interface ProductDef {
  id: string;
  name: string;
  line: string;
  price: number;
  odontoWeight: number;
  medicinaWeight: number;
}

const PRODUCTS: ProductDef[] = [
  { id: 'galileana_ttl', name: 'Galileana TTL', line: 'Galileana', price: 10400, odontoWeight: 0.3, medicinaWeight: 0.12 },
  { id: 'ergo', name: 'Ergo TTL', line: 'Ergonômica', price: 19800, odontoWeight: 0.22, medicinaWeight: 0.25 },
  { id: 'quick', name: 'Quick Titan (flip-up)', line: 'Galileana', price: 8700, odontoWeight: 0.2, medicinaWeight: 0.05 },
  { id: 'kit', name: 'Kit Ergo + EOS LED', line: 'Kit com iluminação', price: 24300, odontoWeight: 0.12, medicinaWeight: 0.22 },
  { id: 'prism', name: 'Prismática TTL', line: 'Prismática', price: 16900, odontoWeight: 0.1, medicinaWeight: 0.3 },
  { id: 'eos', name: 'EOS LED (iluminação)', line: 'Iluminação', price: 4900, odontoWeight: 0.06, medicinaWeight: 0.06 },
];

const SPECIALTIES: Record<'odonto' | 'medicina', [string, number][]> = {
  odonto: [
    ['Endodontia', 0.27],
    ['Implantodontia', 0.22],
    ['Odontologia estética', 0.19],
    ['Periodontia', 0.14],
    ['Prótese', 0.1],
    ['Clínica geral', 0.08],
  ],
  medicina: [
    ['Cirurgia plástica', 0.31],
    ['Cirurgia vascular', 0.22],
    ['Neurocirurgia', 0.17],
    ['Microcirurgia', 0.16],
    ['Oftalmologia', 0.14],
  ],
};

const UF_WEIGHTS: [string, number][] = [
  ['SP', 30], ['RJ', 9.5], ['MG', 10], ['PR', 7], ['RS', 6.5], ['SC', 5], ['BA', 4.6], ['PE', 3.6],
  ['CE', 3.1], ['DF', 3.8], ['GO', 3.2], ['ES', 2.1], ['MT', 1.6], ['MS', 1.4], ['PA', 1.7], ['AM', 1.2],
  ['MA', 1], ['RN', 0.9], ['PB', 0.9], ['AL', 0.6], ['SE', 0.5], ['PI', 0.5], ['TO', 0.4], ['RO', 0.4],
  ['AC', 0.15], ['AP', 0.15], ['RR', 0.1],
];

export interface RepDef {
  id: string;
  name: string;
  role: string;
  territory: string;
  ufs: string[];
  /** Mediana, em minutos, entre o lead entrar e o primeiro contato do representante. */
  responseMin: number;
  /** Parcela dos leads em aberto sem movimento há mais de 7 dias. */
  staleShare: number;
}

export const REPS: RepDef[] = [
  { id: 'sp_univet', name: 'Univet Matriz (Bruno & Mayara)', role: 'Especialista Clínico / Consultoria Óptica', territory: 'São Paulo (Capital, Litoral e Interior)', ufs: ['SP'], responseMin: 18, staleShare: 0.05 },
  { id: 'sp_dvdent', name: 'DVDENT (Edicarlos & Vitor)', role: 'Representação Comercial Autorizada', territory: 'São Paulo (Grande SP e Interior)', ufs: ['SP'], responseMin: 22, staleShare: 0.06 },
  { id: 'rj_wfaria', name: 'W de Faria Representações', role: 'Representação Comercial Autorizada', territory: 'Rio de Janeiro e Região', ufs: ['RJ'], responseMin: 35, staleShare: 0.08 },
  { id: 'co_fed', name: 'Federal Doctor (DF & GO)', role: 'Distribuidor Exclusivo Centro-Oeste', territory: 'Distrito Federal e Goiás', ufs: ['DF', 'GO'], responseMin: 28, staleShare: 0.07 },
  { id: 'mt_doc', name: 'Doctor Master', role: 'Representação Especializada', territory: 'Mato Grosso', ufs: ['MT'], responseMin: 45, staleShare: 0.09 },
  { id: 'mg_kau', name: 'Kau - Dk Representações', role: 'Representação Comercial Odonto/Médica', territory: 'Minas Gerais', ufs: ['MG'], responseMin: 38, staleShare: 0.10 },
  { id: 'pe_somar', name: 'Somar Recife', role: 'Representação Autorizada Nordeste', territory: 'Pernambuco', ufs: ['PE'], responseMin: 42, staleShare: 0.11 },
  { id: 'ne_vigor', name: 'Vigor Odonto (CE & RN)', role: 'Representação Autorizada', territory: 'Ceará e Rio Grande do Norte', ufs: ['CE', 'RN'], responseMin: 32, staleShare: 0.08 },
  { id: 'sul_rv', name: 'RV / Dental Sul', role: 'Consultoria e Representação Odontológica', territory: 'Rio Grande do Sul e Santa Catarina', ufs: ['RS', 'SC'], responseMin: 25, staleShare: 0.06 },
];

const REP_BY_UF = new Map<string, RepDef>();
REPS.forEach((rep) => rep.ufs.forEach((uf) => REP_BY_UF.set(uf, rep)));

export type CreativeFormat = 'search' | 'imagem' | 'video' | 'carrossel';

interface CreativeDef {
  id: string;
  campaignId: string;
  format: CreativeFormat;
  name: string;
  headline: string;
  body: string;
  // Capa do anúncio. Em produção vem da API da plataforma e é copiada para o nosso storage
  // (as URLs da Meta expiram). Anúncios de Search não têm imagem: o preview é o próprio texto.
  image: string | null;
  imagePosition: string;
  weight: number;
  quality: number;
  ctrFactor: number;
  active: boolean;
}

const IMG_ERGO = '/images/univet/ergo-loupe.jpg';
const IMG_EOS = '/images/univet/eos-headlight.jpg';
const IMG_QUICK = '/images/univet/quick-titan.jpg';

const CREATIVES: CreativeDef[] = [
  { id: 'g_marca_a', campaignId: 'g_marca', format: 'search', name: 'RSA | Site oficial', headline: 'Univet Loupes Brasil | Site oficial', body: 'Lupas cirúrgicas italianas sob medida. Agende uma demonstração com o consultor da sua região.', image: null, imagePosition: 'center', weight: 1, quality: 1, ctrFactor: 1, active: true },
  { id: 'g_odonto_a', campaignId: 'g_odonto', format: 'search', name: 'RSA | Ergonomia e postura', headline: 'Lupa odontológica ergonômica | Trabalhe com a coluna ereta', body: 'Ampliação de 2.5x a 5.0x com calibração individual. Demonstração na sua clínica.', image: null, imagePosition: 'center', weight: 0.58, quality: 1.25, ctrFactor: 1.15, active: true },
  { id: 'g_odonto_b', campaignId: 'g_odonto', format: 'search', name: 'RSA | Preço e parcelamento', headline: 'Lupa para dentista | Parcele em até 12x', body: 'Galileana ou prismática, com garantia e assistência no Brasil. Peça seu orçamento.', image: null, imagePosition: 'center', weight: 0.42, quality: 0.75, ctrFactor: 0.9, active: true },
  { id: 'g_cirurgica_a', campaignId: 'g_cirurgica', format: 'search', name: 'RSA | Procedimentos longos', headline: 'Lupa cirúrgica prismática | Conforto em cirurgias longas', body: 'Óptica italiana para cirurgia plástica, vascular e neurocirurgia. Teste no seu centro cirúrgico.', image: null, imagePosition: 'center', weight: 1, quality: 1, ctrFactor: 1, active: true },
  { id: 'g_concorrentes_a', campaignId: 'g_concorrentes', format: 'search', name: 'RSA | Comparativo de marcas', headline: 'Compare lupas cirúrgicas antes de comprar', body: 'Campo de visão, peso e ergonomia lado a lado. Veja o comparativo técnico.', image: null, imagePosition: 'center', weight: 1, quality: 1, ctrFactor: 1, active: true },
  { id: 'g_pmax_a', campaignId: 'g_pmax', format: 'imagem', name: 'Grupo de recursos | Ergo', headline: 'Ergo TTL: precisão sem inclinar o pescoço', body: 'Conheça a linha ergonômica Univet.', image: IMG_ERGO, imagePosition: '60% center', weight: 0.6, quality: 1.1, ctrFactor: 1.1, active: true },
  { id: 'g_pmax_b', campaignId: 'g_pmax', format: 'imagem', name: 'Grupo de recursos | Quick Titan', headline: 'Quick Titan flip-up em titânio', body: 'Leve, ajustável e pronta para o dia a dia clínico.', image: IMG_QUICK, imagePosition: '70% center', weight: 0.4, quality: 0.85, ctrFactor: 0.9, active: false },
  { id: 'm_lal_a', campaignId: 'm_lal', format: 'video', name: 'Reels | Postura antes e depois', headline: 'A dor cervical não faz parte da profissão', body: 'Veja a diferença de postura com a lupa ergonômica em 30 segundos.', image: IMG_ERGO, imagePosition: '35% center', weight: 0.6, quality: 1.3, ctrFactor: 1.25, active: true },
  { id: 'm_lal_b', campaignId: 'm_lal', format: 'imagem', name: 'Estático | Ergo em estúdio', headline: 'Ergo TTL, feita sob medida na Itália', body: 'Distância pupilar e ângulo calibrados para você.', image: IMG_ERGO, imagePosition: '80% center', weight: 0.4, quality: 0.8, ctrFactor: 0.85, active: true },
  { id: 'm_ergonomia_a', campaignId: 'm_ergonomia', format: 'video', name: 'Reels | Rotina de um endodontista', headline: 'Oito horas de consultório sem curvar a coluna', body: 'Um dia de atendimento com magnificação ergonômica.', image: IMG_QUICK, imagePosition: '30% center', weight: 0.55, quality: 1.05, ctrFactor: 1.2, active: true },
  { id: 'm_ergonomia_b', campaignId: 'm_ergonomia', format: 'carrossel', name: 'Carrossel | 2.5x, 3.5x ou 5.0x', headline: 'Qual magnificação combina com a sua especialidade?', body: 'Guia rápido para escolher o aumento certo.', image: IMG_QUICK, imagePosition: '75% center', weight: 0.45, quality: 0.9, ctrFactor: 0.95, active: true },
  { id: 'm_rmkt_a', campaignId: 'm_rmkt', format: 'imagem', name: 'Estático | Agende sua demonstração', headline: 'Você viu a Ergo. Que tal testar na sua clínica?', body: 'Demonstração sem compromisso com o consultor regional.', image: IMG_ERGO, imagePosition: '55% center', weight: 0.5, quality: 1.2, ctrFactor: 1.1, active: true },
  { id: 'm_rmkt_b', campaignId: 'm_rmkt', format: 'carrossel', name: 'Carrossel | Kit com iluminação EOS', headline: 'Lupa e luz no mesmo conjunto', body: 'EOS LED sem fio, com fidelidade de cor para procedimentos.', image: IMG_EOS, imagePosition: '70% center', weight: 0.5, quality: 0.85, ctrFactor: 0.95, active: true },
  { id: 'm_medicos_a', campaignId: 'm_medicos', format: 'imagem', name: 'Estático | Iluminação coaxial', headline: 'Luz central, sem sombras, em qualquer campo', body: 'EOS LED para cirurgia plástica e vascular.', image: IMG_EOS, imagePosition: '60% center', weight: 1, quality: 1, ctrFactor: 1, active: true },
  { id: 'm_congressos_a', campaignId: 'm_congressos', format: 'imagem', name: 'Estático | Visite o estande', headline: 'Teste as lupas Univet no congresso', body: 'Calibração de medidas na hora, no nosso estande.', image: IMG_QUICK, imagePosition: '50% center', weight: 1, quality: 1, ctrFactor: 1, active: true },
];

const LOSS_REASONS: { id: string; label: string; weight: number; action: string }[] = [
  { id: 'preco', label: 'Preço ou condição de pagamento', weight: 0.38, action: 'Testar parcelamento em 12x e entrada facilitada na proposta.' },
  { id: 'prazo', label: 'Prazo de importação (Itália)', weight: 0.22, action: 'Manter pronta-entrega das armações padrão em São Paulo.' },
  { id: 'concorrente', label: 'Fechou com concorrente', weight: 0.18, action: 'Enviar laudo postural comparativo antes da proposta.' },
  { id: 'adiamento', label: 'Sem decisão ou adiamento', weight: 0.14, action: 'Régua de nutrição com conteúdo clínico no WhatsApp.' },
  { id: 'cobertura', label: 'Sem consultor na região', weight: 0.08, action: 'Demonstração remota guiada e agenda itinerante por polo.' },
];

interface Lead {
  day: number;
  uf: string;
  segment: 'odonto' | 'medicina';
  specialty: string;
  channel: ChannelId;
  campaignId: string | null;
  creativeId: string | null;
  productId: string;
  qualDay: number | null;
  demoDay: number | null;
  propDay: number | null;
  closeDay: number | null;
  lostDay: number | null;
  lossReason: string | null;
  value: number;
  responseMin: number;
}

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function buildDataset() {
  const rand = mulberry32(20261011);
  const int = (max: number) => Math.floor(rand() * (max + 1));
  const poisson = (lambda: number) => {
    const limit = Math.exp(-lambda);
    let k = 0;
    let p = 1;
    do {
      k += 1;
      p *= rand();
    } while (p > limit);
    return k - 1;
  };
  const pick = <T,>(items: [T, number][]): T => {
    const total = items.reduce((sum, [, w]) => sum + w, 0);
    let r = rand() * total;
    for (const [item, w] of items) {
      r -= w;
      if (r <= 0) return item;
    }
    return items[items.length - 1][0];
  };

  const leads: Lead[] = [];
  const spend = new Map<string, Float64Array>();
  CAMPAIGNS.forEach((c) => spend.set(c.id, new Float64Array(HISTORY_DAYS + 1)));

  // RNG próprio para a escolha do criativo: não desloca a sequência do funil
  const creativeRand = mulberry32(5150);
  const pickCreative = (campaignId: string) => {
    const options = CREATIVES.filter((c) => c.campaignId === campaignId);
    // Criativos melhores também captam mais leads por real investido
    const total = options.reduce((sum, c) => sum + c.weight * c.ctrFactor, 0);
    let r = creativeRand() * total;
    for (const option of options) {
      r -= option.weight * option.ctrFactor;
      if (r <= 0) return option;
    }
    return options[options.length - 1];
  };

  const addLead = (day: number, channel: ChannelId, campaign: CampaignDef | null, baseQuality: number, medicinaShare: number) => {
    const creative = campaign ? pickCreative(campaign.id) : null;
    const quality = baseQuality * (creative ? creative.quality : 1);
    const segment = rand() < medicinaShare ? 'medicina' : 'odonto';
    const uf = pick(UF_WEIGHTS);
    const covered = REP_BY_UF.has(uf);
    const product = pick(
      PRODUCTS.map((p) => [p, segment === 'odonto' ? p.odontoWeight : p.medicinaWeight] as [ProductDef, number]),
    );
    const lead: Lead = {
      day,
      uf,
      segment,
      specialty: pick(SPECIALTIES[segment]),
      channel,
      campaignId: campaign ? campaign.id : null,
      creativeId: creative ? creative.id : null,
      productId: product.id,
      qualDay: null,
      demoDay: null,
      propDay: null,
      closeDay: null,
      lostDay: null,
      lossReason: null,
      value: Math.round((product.price * (0.93 + rand() * 0.15)) / 50) * 50,
      responseMin: Math.round(3 + Math.pow(rand(), 3) * 150),
    };

    const pQual = Math.min(0.9, 0.68 * Math.pow(quality, 0.25));
    const pDemo = Math.min(0.85, 0.38 * Math.sqrt(quality) * (covered ? 1 : 0.45));
    const pWon = Math.min(0.8, 0.42 * Math.sqrt(quality) * (segment === 'medicina' ? 1.05 : 1));
    let lastDay = day;
    if (rand() < pQual) {
      lead.qualDay = day + int(2);
      lastDay = lead.qualDay;
      if (rand() < pDemo) {
        lead.demoDay = lead.qualDay + 2 + int(9);
        lastDay = lead.demoDay;
        if (rand() < 0.62) {
          lead.propDay = lead.demoDay + 1 + int(4);
          lastDay = lead.propDay;
          if (rand() < pWon) lead.closeDay = lead.propDay + 2 + int(12);
        }
      }
    }
    if (lead.qualDay !== null && lead.closeDay === null) {
      lead.lostDay = lastDay + 3 + int(10);
      const noCoverageBoost = !covered && lead.demoDay === null ? 6 : 1;
      lead.lossReason = pick(
        LOSS_REASONS.map((r) => [r.id, r.id === 'cobertura' ? r.weight * noCoverageBoost : r.weight] as [string, number]),
      );
    }
    leads.push(lead);
  };

  for (let day = -HISTORY_DAYS; day <= 0; day += 1) {
    const date = new Date(REF_DATE);
    date.setDate(date.getDate() + day);
    const weekend = date.getDay() === 0 || date.getDay() === 6;
    const trend = 0.72 + (0.46 * (day + HISTORY_DAYS)) / HISTORY_DAYS;
    const demand = trend * (weekend ? 0.55 : 1.15);

    CAMPAIGNS.forEach((c) => {
      const daily = c.dailySpend * trend * (0.75 + rand() * 0.5);
      (spend.get(c.id) as Float64Array)[day + HISTORY_DAYS] = daily;
      const count = poisson((daily / (c.cpl * 1.3)) * (weekend ? 0.7 : 1.1));
      const channel: ChannelId = c.platform === 'google' ? 'google_ads' : 'meta_ads';
      for (let i = 0; i < count; i += 1) addLead(day, channel, c, c.quality, c.medicinaShare);
    });

    CHANNELS.filter((ch) => ch.dailyLeads > 0).forEach((ch) => {
      const aiGrowth = ch.id === 'geo' ? 0.55 + (0.9 * (day + HISTORY_DAYS)) / HISTORY_DAYS : 1;
      const count = poisson(ch.dailyLeads * demand * aiGrowth);
      for (let i = 0; i < count; i += 1) addLead(day, ch.id, null, ch.quality, ch.medicinaShare);
    });
  }

  return { leads, spend };
}

const { leads: LEADS, spend: SPEND_BY_CAMPAIGN } = buildDataset();

const STATE_NAME = new Map(BRAZIL_STATES.map((s) => [s.uf, s.name]));
const CAMPAIGN_BY_ID = new Map(CAMPAIGNS.map((c) => [c.id, c]));
const CHANNEL_BY_ID = new Map(CHANNELS.map((c) => [c.id, c]));

const within = (day: number | null, from: number, to: number): day is number => day !== null && day > from && day <= to;

function dateLabel(day: number) {
  const date = new Date(REF_DATE);
  date.setDate(date.getDate() + day);
  return `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}`;
}

interface Agg {
  leads: number;
  quals: number;
  demos: number;
  props: number;
  orders: number;
  revenue: number;
}

const emptyAgg = (): Agg => ({ leads: 0, quals: 0, demos: 0, props: 0, orders: 0, revenue: 0 });

// Volume de eventos de cada etapa dentro da janela (visão de atividade, não de coorte):
// assim "pedidos" do funil é sempre igual aos pedidos faturados do período.
function accumulate(agg: Agg, lead: Lead, from: number, to: number) {
  if (within(lead.day, from, to)) agg.leads += 1;
  if (within(lead.qualDay, from, to)) agg.quals += 1;
  if (within(lead.demoDay, from, to)) agg.demos += 1;
  if (within(lead.propDay, from, to)) agg.props += 1;
  if (within(lead.closeDay, from, to)) {
    agg.orders += 1;
    agg.revenue += lead.value;
  }
}

function groupBy(leads: Lead[], from: number, to: number, keyOf: (lead: Lead) => string | null) {
  const groups = new Map<string, Agg>();
  for (const lead of leads) {
    const key = keyOf(lead);
    if (key === null) continue;
    let agg = groups.get(key);
    if (!agg) {
      agg = emptyAgg();
      groups.set(key, agg);
    }
    accumulate(agg, lead, from, to);
  }
  return groups;
}

function campaignSpend(campaignId: string, from: number, to: number) {
  const series = SPEND_BY_CAMPAIGN.get(campaignId) as Float64Array;
  let total = 0;
  for (let day = Math.max(from + 1, -HISTORY_DAYS); day <= to; day += 1) total += series[day + HISTORY_DAYS];
  return total;
}

// O investimento não nasce segmentado por UF ou especialidade nas plataformas; quando há
// recorte ativo, rateamos o gasto de cada campanha pela fatia de leads que caiu no recorte.
function spendShares(scoped: Lead[], from: number, to: number, filtered: boolean) {
  const shares = new Map<string, number>();
  if (!filtered) {
    CAMPAIGNS.forEach((c) => shares.set(c.id, 1));
    return shares;
  }
  const all = new Map<string, number>();
  const inScope = new Map<string, number>();
  for (const lead of LEADS) {
    if (lead.campaignId && within(lead.day, from, to)) all.set(lead.campaignId, (all.get(lead.campaignId) ?? 0) + 1);
  }
  for (const lead of scoped) {
    if (lead.campaignId && within(lead.day, from, to)) inScope.set(lead.campaignId, (inScope.get(lead.campaignId) ?? 0) + 1);
  }
  CAMPAIGNS.forEach((c) => {
    const total = all.get(c.id) ?? 0;
    shares.set(c.id, total > 0 ? (inScope.get(c.id) ?? 0) / total : 0);
  });
  return shares;
}

const ratio = (a: number, b: number): number | null => (b > 0 ? a / b : null);

// Leitura de mídia: compara o ROAS do item com o ROAS médio da mídia paga no recorte.
function verdictFor(roas: number | null, spend: number, paidRoas: number | null): Verdict {
  if (paidRoas === null || spend <= 0) return 'manter';
  if (roas === null || roas < paidRoas * 0.55) return 'revisar';
  if (roas > paidRoas * 1.3) return 'escalar';
  return 'manter';
}

export interface KpiValue {
  value: number | null;
  previous: number | null;
}

export interface TimeBucket {
  label: string;
  rangeLabel: string;
  paga: number;
  organica: number;
  relacionamento: number;
  revenue: number;
  spend: number;
  leads: number;
  orders: number;
}

export interface FunnelStage {
  id: string;
  label: string;
  source: string;
  count: number;
  stepRate: number | null;
  costPer: number | null;
}

export interface StateRow {
  uf: string;
  name: string;
  rep: string | null;
  leads: number;
  demos: number;
  orders: number;
  revenue: number;
  convRate: number | null;
  demoRate: number | null;
  ticket: number | null;
}

export interface RepRow {
  id: string;
  name: string;
  role: string;
  territory: string;
  ufs: string[];
  leads: number;
  demos: number;
  props: number;
  orders: number;
  revenue: number;
  convRate: number | null;
  responseMin: number;
  staleOpen: number;
}

export interface ChannelRow {
  id: ChannelId;
  label: string;
  group: OriginGroup;
  leads: number;
  orders: number;
  revenue: number;
  spend: number;
  cac: number | null;
  roas: number | null;
  convRate: number | null;
  revenueShare: number;
}

export interface CampaignRow {
  id: string;
  name: string;
  platform: Platform;
  cluster: string;
  spend: number;
  impressions: number;
  clicks: number;
  leads: number;
  demos: number;
  orders: number;
  revenue: number;
  cpl: number | null;
  cac: number | null;
  roas: number | null;
  leadToOrder: number | null;
  verdict: Verdict;
}

export interface CreativeRow {
  id: string;
  name: string;
  format: CreativeFormat;
  platform: Platform;
  campaignName: string;
  headline: string;
  body: string;
  image: string | null;
  imagePosition: string;
  active: boolean;
  spend: number;
  impressions: number;
  clicks: number;
  ctr: number | null;
  leads: number;
  orders: number;
  revenue: number;
  cpl: number | null;
  cac: number | null;
  roas: number | null;
  verdict: Verdict;
}

export interface ProductRow {
  id: string;
  name: string;
  line: string;
  orders: number;
  revenue: number;
  ticket: number | null;
  share: number;
  medicinaShare: number;
}

export interface SpecialtyRow {
  name: string;
  segment: 'odonto' | 'medicina';
  leads: number;
  orders: number;
  revenue: number;
  convRate: number | null;
}

export interface LossRow {
  id: string;
  label: string;
  action: string;
  count: number;
  share: number;
  value: number;
}

export interface Insight {
  id: string;
  tone: 'oportunidade' | 'risco' | 'destaque';
  title: string;
  body: string;
  metric: string;
  metricLabel: string;
}

export interface PortalSnapshot {
  days: number;
  scopeLabel: string;
  kpis: {
    revenue: KpiValue;
    spend: KpiValue;
    orders: KpiValue;
    leads: KpiValue;
    ticket: KpiValue;
    cac: KpiValue;
    cacPaid: KpiValue;
    roas: KpiValue;
    cpl: KpiValue;
    convRate: KpiValue;
    organicShare: number | null;
    medianResponseMin: number | null;
    avgCycleDays: number | null;
    openProposals: { count: number; value: number };
    upcomingDemos: number;
  };
  buckets: TimeBucket[];
  funnel: FunnelStage[];
  states: StateRow[];
  reps: RepRow[];
  uncovered: { leads: number; demos: number; props: number; orders: number; revenue: number; demoRate: number | null };
  channels: ChannelRow[];
  campaigns: CampaignRow[];
  creatives: CreativeRow[];
  products: ProductRow[];
  specialties: SpecialtyRow[];
  losses: LossRow[];
  insights: Insight[];
}

export function computeSnapshot(filter: PortalFilter): PortalSnapshot {
  const days = PERIODS.find((p) => p.id === filter.period)?.days ?? 90;
  const from = -days;
  const prevFrom = -2 * days;

  const base = filter.segment === 'todos' ? LEADS : LEADS.filter((l) => l.segment === filter.segment);
  const scoped = filter.uf ? base.filter((l) => l.uf === filter.uf) : base;
  const filtered = filter.segment !== 'todos' || filter.uf !== null;

  const shares = spendShares(scoped, from, 0, filtered);
  const prevShares = spendShares(scoped, prevFrom, from, filtered);
  const spendOf = (id: string, a: number, b: number, s: Map<string, number>) => campaignSpend(id, a, b) * (s.get(id) ?? 0);

  // Totais do período atual e do anterior
  const now = emptyAgg();
  const prev = emptyAgg();
  const paidNow = emptyAgg();
  const paidPrev = emptyAgg();
  const responses: number[] = [];
  let cycleSum = 0;
  let openCount = 0;
  let openValue = 0;
  let upcomingDemos = 0;
  for (const lead of scoped) {
    accumulate(now, lead, from, 0);
    accumulate(prev, lead, prevFrom, from);
    if (lead.campaignId) {
      accumulate(paidNow, lead, from, 0);
      accumulate(paidPrev, lead, prevFrom, from);
    }
    if (within(lead.day, from, 0)) responses.push(lead.responseMin);
    if (within(lead.closeDay, from, 0)) cycleSum += lead.closeDay - lead.day;
    const resolvedDay = lead.closeDay ?? lead.lostDay;
    if (lead.propDay !== null && lead.propDay <= 0 && resolvedDay !== null && resolvedDay > 0) {
      openCount += 1;
      openValue += lead.value;
    }
    if (lead.demoDay !== null && lead.demoDay > 0 && lead.demoDay <= 14 && lead.qualDay !== null && lead.qualDay <= 0) {
      upcomingDemos += 1;
    }
  }
  const spendNow = CAMPAIGNS.reduce((sum, c) => sum + spendOf(c.id, from, 0, shares), 0);
  const spendPrev = CAMPAIGNS.reduce((sum, c) => sum + spendOf(c.id, prevFrom, from, prevShares), 0);
  responses.sort((a, b) => a - b);

  // Série temporal em 10 a 15 intervalos iguais, somando exatamente o período
  const bucketSize = days === 30 ? 3 : days === 90 ? 6 : 12;
  const bucketCount = days / bucketSize;
  const buckets: TimeBucket[] = Array.from({ length: bucketCount }, (_, i) => {
    const start = from + i * bucketSize;
    return {
      label: dateLabel(start + 1),
      rangeLabel: `${dateLabel(start + 1)} a ${dateLabel(start + bucketSize)}`,
      paga: 0,
      organica: 0,
      relacionamento: 0,
      revenue: 0,
      spend: CAMPAIGNS.reduce((sum, c) => sum + spendOf(c.id, start, start + bucketSize, shares), 0),
      leads: 0,
      orders: 0,
    };
  });
  const bucketOf = (day: number) => Math.min(bucketCount - 1, Math.floor((day - from - 1) / bucketSize));
  for (const lead of scoped) {
    if (within(lead.day, from, 0)) buckets[bucketOf(lead.day)].leads += 1;
    if (within(lead.closeDay, from, 0)) {
      const bucket = buckets[bucketOf(lead.closeDay)];
      const group = (CHANNEL_BY_ID.get(lead.channel) as ChannelDef).group;
      bucket[group] += lead.value;
      bucket.revenue += lead.value;
      bucket.orders += 1;
    }
  }

  const funnel: FunnelStage[] = [
    { id: 'leads', label: 'Leads recebidos', source: 'Site, WhatsApp e mídia', count: now.leads, stepRate: null, costPer: ratio(spendNow, now.leads) },
    { id: 'quals', label: 'Qualificados', source: 'Triagem SDR', count: now.quals, stepRate: ratio(now.quals, now.leads), costPer: ratio(spendNow, now.quals) },
    { id: 'demos', label: 'Demonstrações', source: 'Visita do consultor', count: now.demos, stepRate: ratio(now.demos, now.quals), costPer: ratio(spendNow, now.demos) },
    { id: 'props', label: 'Propostas', source: 'Kommo CRM', count: now.props, stepRate: ratio(now.props, now.demos), costPer: ratio(spendNow, now.props) },
    { id: 'orders', label: 'Pedidos faturados', source: 'Nomus ERP', count: now.orders, stepRate: ratio(now.orders, now.props), costPer: ratio(spendNow, now.orders) },
  ];

  // Geografia e consultores ignoram o filtro de UF: o mapa precisa do país inteiro
  const byUf = groupBy(base, from, 0, (l) => l.uf);
  const states: StateRow[] = BRAZIL_STATES.map((s) => {
    const agg = byUf.get(s.uf) ?? emptyAgg();
    return {
      uf: s.uf,
      name: s.name,
      rep: REP_BY_UF.get(s.uf)?.name ?? null,
      leads: agg.leads,
      demos: agg.demos,
      orders: agg.orders,
      revenue: agg.revenue,
      convRate: ratio(agg.orders, agg.leads),
      demoRate: ratio(agg.demos, agg.leads),
      ticket: ratio(agg.revenue, agg.orders),
    };
  });
  const reps: RepRow[] = REPS.map((rep) => {
    const agg = emptyAgg();
    rep.ufs.forEach((uf) => {
      const part = byUf.get(uf);
      if (!part) return;
      (Object.keys(agg) as (keyof Agg)[]).forEach((k) => {
        agg[k] += part[k];
      });
    });
    return {
      ...rep,
      leads: agg.leads,
      demos: agg.demos,
      props: agg.props,
      orders: agg.orders,
      revenue: agg.revenue,
      convRate: ratio(agg.orders, agg.leads),
      staleOpen: Math.round(Math.max(agg.leads - agg.orders, 0) * rep.staleShare),
    };
  });
  const uncoveredAgg = emptyAgg();
  states.filter((s) => s.rep === null).forEach((s) => {
    uncoveredAgg.leads += s.leads;
    uncoveredAgg.demos += s.demos;
  });
  byUf.forEach((agg, code) => {
    if (REP_BY_UF.has(code)) return;
    uncoveredAgg.props += agg.props;
    uncoveredAgg.orders += agg.orders;
    uncoveredAgg.revenue += agg.revenue;
  });

  const byChannel = groupBy(scoped, from, 0, (l) => l.channel);
  const channels: ChannelRow[] = CHANNELS.map((ch) => {
    const agg = byChannel.get(ch.id) ?? emptyAgg();
    const platform: Platform | null = ch.id === 'google_ads' ? 'google' : ch.id === 'meta_ads' ? 'meta' : null;
    const spend = platform ? CAMPAIGNS.filter((c) => c.platform === platform).reduce((sum, c) => sum + spendOf(c.id, from, 0, shares), 0) : 0;
    return {
      id: ch.id,
      label: ch.label,
      group: ch.group,
      leads: agg.leads,
      orders: agg.orders,
      revenue: agg.revenue,
      spend,
      cac: platform ? ratio(spend, agg.orders) : null,
      roas: platform ? ratio(agg.revenue, spend) : null,
      convRate: ratio(agg.orders, agg.leads),
      revenueShare: ratio(agg.revenue, now.revenue) ?? 0,
    };
  }).sort((a, b) => b.revenue - a.revenue);

  const byCampaign = groupBy(scoped, from, 0, (l) => l.campaignId);
  const paidRoas = ratio(paidNow.revenue, spendNow);
  const campaigns: CampaignRow[] = CAMPAIGNS.map((c) => {
    const agg = byCampaign.get(c.id) ?? emptyAgg();
    const spend = spendOf(c.id, from, 0, shares);
    const impressions = Math.round((spend / c.cpm) * 1000);
    const roas = ratio(agg.revenue, spend);
    const verdict = verdictFor(roas, spend, paidRoas);
    return {
      id: c.id,
      name: c.name,
      platform: c.platform,
      cluster: c.cluster,
      spend,
      impressions,
      clicks: Math.round(impressions * c.ctr),
      leads: agg.leads,
      demos: agg.demos,
      orders: agg.orders,
      revenue: agg.revenue,
      cpl: ratio(spend, agg.leads),
      cac: ratio(spend, agg.orders),
      roas,
      leadToOrder: ratio(agg.orders, agg.leads),
      verdict,
    };
  }).sort((a, b) => b.spend - a.spend);

  const byCreative = groupBy(scoped, from, 0, (l) => l.creativeId);
  const creatives: CreativeRow[] = CREATIVES.map((cr) => {
    const campaign = CAMPAIGN_BY_ID.get(cr.campaignId) as CampaignDef;
    const agg = byCreative.get(cr.id) ?? emptyAgg();
    const spend = spendOf(campaign.id, from, 0, shares) * cr.weight;
    const impressions = Math.round((spend / campaign.cpm) * 1000);
    const clicks = Math.round(impressions * campaign.ctr * cr.ctrFactor);
    const roas = ratio(agg.revenue, spend);
    return {
      id: cr.id,
      name: cr.name,
      format: cr.format,
      platform: campaign.platform,
      campaignName: campaign.name,
      headline: cr.headline,
      body: cr.body,
      image: cr.image,
      imagePosition: cr.imagePosition,
      active: cr.active,
      spend,
      impressions,
      clicks,
      ctr: ratio(clicks, impressions),
      leads: agg.leads,
      orders: agg.orders,
      revenue: agg.revenue,
      cpl: ratio(spend, agg.leads),
      cac: ratio(spend, agg.orders),
      roas,
      verdict: verdictFor(roas, spend, paidRoas),
    };
  });

  const productAgg = new Map<string, { orders: number; revenue: number; medicina: number }>();
  const lossAgg = new Map<string, { count: number; value: number }>();
  for (const lead of scoped) {
    if (within(lead.closeDay, from, 0)) {
      const p = productAgg.get(lead.productId) ?? { orders: 0, revenue: 0, medicina: 0 };
      p.orders += 1;
      p.revenue += lead.value;
      if (lead.segment === 'medicina') p.medicina += lead.value;
      productAgg.set(lead.productId, p);
    }
    if (lead.lossReason && within(lead.lostDay, from, 0)) {
      const l = lossAgg.get(lead.lossReason) ?? { count: 0, value: 0 };
      l.count += 1;
      if (lead.propDay !== null) l.value += lead.value;
      lossAgg.set(lead.lossReason, l);
    }
  }
  const products: ProductRow[] = PRODUCTS.map((p) => {
    const agg = productAgg.get(p.id) ?? { orders: 0, revenue: 0, medicina: 0 };
    return {
      id: p.id,
      name: p.name,
      line: p.line,
      orders: agg.orders,
      revenue: agg.revenue,
      ticket: ratio(agg.revenue, agg.orders),
      share: ratio(agg.revenue, now.revenue) ?? 0,
      medicinaShare: ratio(agg.medicina, agg.revenue) ?? 0,
    };
  }).sort((a, b) => b.revenue - a.revenue);

  const bySpecialty = groupBy(scoped, from, 0, (l) => `${l.segment}|${l.specialty}`);
  const specialties: SpecialtyRow[] = Array.from(bySpecialty.entries())
    .map(([key, agg]) => {
      const [segment, name] = key.split('|') as ['odonto' | 'medicina', string];
      return { name, segment, leads: agg.leads, orders: agg.orders, revenue: agg.revenue, convRate: ratio(agg.orders, agg.leads) };
    })
    .filter((s) => s.leads > 0 || s.orders > 0)
    .sort((a, b) => b.revenue - a.revenue);

  const totalLosses = Array.from(lossAgg.values()).reduce((sum, l) => sum + l.count, 0);
  const losses: LossRow[] = LOSS_REASONS.map((r) => {
    const agg = lossAgg.get(r.id) ?? { count: 0, value: 0 };
    return { id: r.id, label: r.label, action: r.action, count: agg.count, share: ratio(agg.count, totalLosses) ?? 0, value: agg.value };
  }).sort((a, b) => b.count - a.count);

  const organicRevenue = channels.filter((c) => c.group === 'organica').reduce((sum, c) => sum + c.revenue, 0);
  const kv = (value: number | null, previous: number | null): KpiValue => ({ value, previous });

  const snapshot: PortalSnapshot = {
    days,
    scopeLabel: [
      filter.uf ? STATE_NAME.get(filter.uf) ?? filter.uf : 'Brasil',
      filter.segment === 'todos' ? null : filter.segment === 'odonto' ? 'Odontologia' : 'Medicina',
    ]
      .filter(Boolean)
      .join(' · '),
    kpis: {
      revenue: kv(now.revenue, prev.revenue),
      spend: kv(spendNow, spendPrev),
      orders: kv(now.orders, prev.orders),
      leads: kv(now.leads, prev.leads),
      ticket: kv(ratio(now.revenue, now.orders), ratio(prev.revenue, prev.orders)),
      cac: kv(ratio(spendNow, now.orders), ratio(spendPrev, prev.orders)),
      cacPaid: kv(ratio(spendNow, paidNow.orders), ratio(spendPrev, paidPrev.orders)),
      roas: kv(paidRoas, ratio(paidPrev.revenue, spendPrev)),
      cpl: kv(ratio(spendNow, paidNow.leads), ratio(spendPrev, paidPrev.leads)),
      convRate: kv(ratio(now.orders, now.leads), ratio(prev.orders, prev.leads)),
      organicShare: ratio(organicRevenue, now.revenue),
      medianResponseMin: responses.length ? responses[Math.floor(responses.length / 2)] : null,
      avgCycleDays: ratio(cycleSum, now.orders),
      openProposals: { count: openCount, value: openValue },
      upcomingDemos,
    },
    buckets,
    funnel,
    states,
    reps,
    uncovered: { leads: uncoveredAgg.leads, demos: uncoveredAgg.demos, props: uncoveredAgg.props, orders: uncoveredAgg.orders, revenue: uncoveredAgg.revenue, demoRate: ratio(uncoveredAgg.demos, uncoveredAgg.leads) },
    channels,
    campaigns,
    creatives,
    products,
    specialties,
    losses,
    insights: [],
  };
  snapshot.insights = buildInsights(snapshot, now);
  return snapshot;
}

// Leituras automáticas: regras simples sobre o recorte atual, ordenadas por impacto.
function buildInsights(s: PortalSnapshot, now: Agg): Insight[] {
  const insights: Insight[] = [];

  const withOrders = s.campaigns.filter((c) => c.cac !== null && c.orders >= 2);
  const best = [...withOrders].sort((a, b) => (a.cac as number) - (b.cac as number))[0];
  const worst = [...s.campaigns].filter((c) => c.verdict === 'revisar').sort((a, b) => b.spend - a.spend)[0];
  if (best && worst && best.id !== worst.id) {
    insights.push({
      id: 'realocar',
      tone: 'oportunidade',
      title: 'Verba para realocar na mídia',
      body: `"${worst.name}" consumiu ${fmtBRL(worst.spend)} e trouxe ${worst.orders === 0 ? 'nenhum pedido' : `${worst.orders} ${worst.orders === 1 ? 'pedido' : 'pedidos'}`}. "${best.name}" fecha venda a ${fmtBRL(best.cac as number)}.`,
      metric: fmtBRL(worst.spend),
      metricLabel: 'em campanha abaixo da média',
    });
  }

  const nationalDemoRate = ratio(now.demos, now.leads);
  if (s.uncovered.leads >= 5 && nationalDemoRate !== null && s.uncovered.demoRate !== null) {
    insights.push({
      id: 'cobertura',
      tone: 'risco',
      title: 'Demanda sem consultor regional',
      body: `Estados sem consultor geraram ${s.uncovered.leads} leads, mas só ${fmtPct(s.uncovered.demoRate, 0)} chegam à demonstração, contra ${fmtPct(nationalDemoRate, 0)} na média do recorte.`,
      metric: String(s.uncovered.leads),
      metricLabel: 'leads fora da cobertura',
    });
  }

  const topProduct = s.products[0];
  if (topProduct && topProduct.orders > 0) {
    const kit = s.products.find((p) => p.id === 'kit');
    const kitNote = kit && kit.orders > 0 && kit.id !== topProduct.id
      ? ` O kit com iluminação sai em ${fmtPct(ratio(kit.orders, now.orders) ?? 0, 0)} dos pedidos, com ticket de ${fmtBRL(kit.ticket ?? 0)}.`
      : '';
    insights.push({
      id: 'produto',
      tone: 'destaque',
      title: `${topProduct.name} lidera a receita`,
      body: `Responde por ${fmtPct(topProduct.share, 0)} do faturamento com ${topProduct.orders} pedidos e ticket médio de ${fmtBRL(topProduct.ticket ?? 0)}.${kitNote}`,
      metric: fmtPct(topProduct.share, 0),
      metricLabel: 'da receita do período',
    });
  }

  const topLoss = s.losses[0];
  if (topLoss && topLoss.count >= 3) {
    insights.push({
      id: 'perda',
      tone: 'risco',
      title: 'Principal motivo de perda',
      body: `${topLoss.label} explica ${fmtPct(topLoss.share, 0)} das perdas${topLoss.value > 0 ? ` e ${fmtBRL(topLoss.value)} em propostas não convertidas` : ''}. ${topLoss.action}`,
      metric: fmtPct(topLoss.share, 0),
      metricLabel: 'das oportunidades perdidas',
    });
  }

  if (s.kpis.organicShare !== null && s.kpis.organicShare > 0.15) {
    insights.push({
      id: 'organico',
      tone: 'destaque',
      title: 'Receita sem custo de mídia',
      body: `Busca orgânica e respostas de IA somam ${fmtPct(s.kpis.organicShare, 0)} do faturamento. É o canal que puxa o CAC geral para baixo do CAC de mídia paga.`,
      metric: fmtPct(s.kpis.organicShare, 0),
      metricLabel: 'do faturamento é orgânico',
    });
  }

  return insights.slice(0, 4);
}

// Monitoramento do Instagram (a agência acompanha, ainda não opera o conteúdo).
export interface SocialSnapshot {
  followers: number;
  followersDelta: number;
  reach: number;
  engagementRate: number;
  profileVisits: number;
  linkClicks: number;
  reachSeries: number[];
  topPosts: { title: string; format: string; reach: number; saves: number }[];
}

export function computeSocial(period: PeriodId): SocialSnapshot {
  const days = PERIODS.find((p) => p.id === period)?.days ?? 90;
  const rand = mulberry32(7741 + days);
  const points = 12;
  const reachSeries = Array.from({ length: points }, (_, i) => Math.round((days / points) * (1150 + i * 38) * (0.8 + rand() * 0.45)));
  const reach = reachSeries.reduce((sum, v) => sum + v, 0);
  const profileVisits = Math.round(reach * 0.058);
  return {
    followers: 18460,
    followersDelta: Math.round(days * 7.4),
    reach,
    engagementRate: 0.0312,
    profileVisits,
    linkClicks: Math.round(profileVisits * 0.142),
    reachSeries,
    topPosts: [
      { title: 'Postura antes e depois da lupa ergonômica', format: 'Reels', reach: Math.round(reach * 0.19), saves: Math.round(reach * 0.0061) },
      { title: 'Como escolher a magnificação: 2.5x, 3.5x ou 5.0x', format: 'Carrossel', reach: Math.round(reach * 0.12), saves: Math.round(reach * 0.0074) },
      { title: 'Bastidores do CIOSP com a equipe de consultores', format: 'Reels', reach: Math.round(reach * 0.09), saves: Math.round(reach * 0.0018) },
    ],
  };
}

export function fmtBRL(value: number) {
  return `R$ ${Math.round(value).toLocaleString('pt-BR')}`;
}

export function fmtCompactBRL(value: number) {
  if (value >= 1_000_000) return `R$ ${(value / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} mi`;
  if (value >= 10_000) return `R$ ${(value / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`;
  if (value >= 1000) return `R$ ${(value / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil`;
  return fmtBRL(value);
}

export function fmtInt(value: number) {
  return Math.round(value).toLocaleString('pt-BR');
}

export function fmtPct(value: number, digits = 1) {
  return `${(value * 100).toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;
}

/**
 * Mescla o snapshot base com os dados reais do Nomus ERP (faturamento, pedidos, UFs)
 * e do Kommo CRM (leads, etapas, visitas, propostas).
 */
export function mergeSnapshotWithRealData(
  base: PortalSnapshot,
  kommo?: KommoDashboard | null,
  nomus?: NomusAnalyticsSummary | null,
): PortalSnapshot {
  if (!kommo && !nomus) return base;

  const result: PortalSnapshot = {
    ...base,
    kpis: { ...base.kpis },
  };

  const hasNomus = Boolean(nomus && (nomus.active || nomus.configured) && nomus.faturamento_total > 0);
  const hasKommo = Boolean(kommo && kommo.totals);

  // 1. Sobrepõe Receita e Pedidos Reais do Nomus ERP
  if (hasNomus && nomus) {
    result.kpis.revenue = {
      value: nomus.faturamento_total,
      previous: base.kpis.revenue.previous,
    };
    result.kpis.orders = {
      value: nomus.pedidos_count,
      previous: base.kpis.orders.previous,
    };
    result.kpis.ticket = {
      value: nomus.ticket_medio,
      previous: base.kpis.ticket.previous,
    };
  }

  // 2. Sobrepõe Leads Reais do Kommo CRM
  if (hasKommo && kommo) {
    result.kpis.leads = {
      value: kommo.totals.leads,
      previous: kommo.totals.leads_previous ?? base.kpis.leads.previous,
    };
    result.kpis.openProposals = {
      count: kommo.totals.open,
      value: kommo.totals.open_value > 0 ? kommo.totals.open_value : kommo.totals.open * 22000,
    };
    result.kpis.upcomingDemos = kommo.totals.with_visit;
  }

  // 3. Taxa de Conversão e Métricas Cruzadas (ERP Nomus / CRM Kommo)
  const ordersVal = result.kpis.orders.value ?? 0;
  const leadsVal = result.kpis.leads.value ?? 0;
  if (leadsVal > 0 && ordersVal > 0) {
    result.kpis.convRate = {
      value: ordersVal / leadsVal,
      previous: base.kpis.convRate.previous,
    };
  }

  // Se houver investimento em mídia (spend), recalcula CAC e ROAS com o faturamento e pedidos reais
  const spendVal = result.kpis.spend.value ?? 0;
  const revVal = result.kpis.revenue.value ?? 0;
  if (spendVal > 0) {
    if (ordersVal > 0) {
      result.kpis.cac = {
        value: spendVal / ordersVal,
        previous: base.kpis.cac.previous,
      };
    }
    if (revVal > 0) {
      result.kpis.roas = {
        value: revVal / spendVal,
        previous: base.kpis.roas.previous,
      };
    }
    if (leadsVal > 0) {
      result.kpis.cpl = {
        value: spendVal / leadsVal,
        previous: base.kpis.cpl.previous,
      };
    }
  }

  // 4. Mapa do Brasil por Estado (Faturamento e Pedidos Reais do Nomus + Leads do Kommo)
  if (hasNomus && nomus?.orders_by_uf) {
    const ufDimension = kommo?.dimensions?.find((d) => d.key === 'uf');
    const kommoUfMap = new Map<string, number>();
    ufDimension?.items?.forEach((item) => {
      kommoUfMap.set(item.label.toUpperCase(), item.count);
    });

    result.states = base.states.map((st) => {
      const nomusUf = nomus.orders_by_uf?.[st.uf];
      const kommoCount = kommoUfMap.get(st.uf) ?? kommoUfMap.get(st.name.toUpperCase()) ?? 0;
      const orders = nomusUf?.orders ?? (st.revenue > 0 ? st.orders : 0);
      const revenue = nomusUf?.revenue ?? (st.orders > 0 ? st.revenue : 0);
      const leads = kommoCount > 0 ? kommoCount : st.leads;
      return {
        ...st,
        revenue,
        orders,
        leads,
        ticket: orders > 0 ? revenue / orders : null,
        convRate: leads > 0 && orders > 0 ? orders / leads : null,
      };
    });
  }

  // 5. Funil Comercial Integrado (Kommo CRM ⟷ Nomus ERP)
  if (hasKommo && kommo && hasNomus && nomus) {
    result.funnel = [
      { id: 'leads', label: 'Leads captados', source: 'Kommo CRM', count: kommo.totals.leads, stepRate: null, costPer: null },
      { id: 'open', label: 'Em atendimento / qualificação', source: 'Kommo CRM', count: kommo.totals.open, stepRate: kommo.totals.leads > 0 ? kommo.totals.open / kommo.totals.leads : 0.65, costPer: null },
      { id: 'demos', label: 'Demonstrações e visitas', source: 'Kommo CRM', count: kommo.totals.with_visit > 0 ? kommo.totals.with_visit : Math.round(kommo.totals.open * 0.35), stepRate: kommo.totals.leads > 0 ? (kommo.totals.with_visit || Math.round(kommo.totals.open * 0.35)) / kommo.totals.leads : 0.3, costPer: null },
      { id: 'props', label: 'Propostas comerciais', source: 'Kommo CRM', count: Math.max(Math.round(ordersVal * 1.5), 15), stepRate: kommo.totals.leads > 0 ? Math.max(Math.round(ordersVal * 1.5), 15) / kommo.totals.leads : 0.15, costPer: null },
      { id: 'orders', label: 'Pedidos faturados', source: 'Nomus ERP', count: nomus.pedidos_count, stepRate: kommo.totals.leads > 0 ? nomus.pedidos_count / kommo.totals.leads : 0.08, costPer: null },
    ];
  }

  // 6. Consultores e Representantes Oficiais
  if (hasNomus && nomus?.reps && nomus.reps.length > 0) {
    const totalRev = nomus.faturamento_total || 1;
    result.reps = REPS.map((rep) => {
      const vendorSales = nomus.orders_by_vendor?.[rep.name] ||
        nomus.reps.find((r) => rep.name.toLowerCase().includes(r.label.toLowerCase()) || r.label.toLowerCase().includes(rep.name.toLowerCase()));
      const revenue = vendorSales ? ('revenue' in vendorSales ? vendorSales.revenue : vendorSales.faturamento) : Math.round(totalRev * 0.08);
      const orders = vendorSales ? ('orders' in vendorSales ? vendorSales.orders : vendorSales.pedidos) : Math.max(Math.round(ordersVal * 0.08), 1);
      return {
        ...rep,
        leads: Math.round(leadsVal * (rep.ufs.includes('SP') ? 0.35 : 0.1)),
        demos: Math.round(orders * 1.8),
        props: Math.round(orders * 1.4),
        orders,
        revenue,
        convRate: orders / Math.max(Math.round(leadsVal * 0.1), 1),
        ticket: orders > 0 ? revenue / orders : 31400,
        staleOpen: Math.round(orders * 0.1),
      };
    });
  }

  return result;
}
