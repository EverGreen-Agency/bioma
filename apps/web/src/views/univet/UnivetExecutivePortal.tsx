import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowDownRight, ArrowUpRight, CheckCircle2, Download, Instagram, MapPin, Minus, Play, Sparkles, TrendingUp, X } from 'lucide-react';
import {
  computeSnapshot,
  computeSocial,
  mergeSnapshotWithRealData,
  fmtBRL,
  fmtCompactBRL,
  fmtInt,
  fmtPct,
  ORIGIN_GROUPS,
  PERIODS,
  REPS,
  type CreativeFormat,
  type CreativeRow,
  type Insight,
  type KpiValue,
  type OriginGroup,
  type PeriodId,
  type Platform,
  type SegmentFilter,
  type StateRow,
  type Verdict,
} from '../../data/univet/univetPortalData';
import { portalApi } from '../../lib/portalApi';
import { UnivetPortalChrome } from './UnivetRealPortal';
import { BrazilMap, ScatterPlot, Sparkline, StackedColumns, TERRITORY_COLORS } from './UnivetCharts';
import './univet-portal.css';

type MapMetric = 'revenue' | 'leads' | 'orders' | 'convRate' | 'coverage';
type CreativeSort = 'spend' | 'orders' | 'cpl';

const CREATIVE_SORTS: { id: CreativeSort; label: string }[] = [
  { id: 'spend', label: 'Maior investimento' },
  { id: 'orders', label: 'Mais pedidos' },
  { id: 'cpl', label: 'Menor CPL' },
];

const PLATFORM_OPTIONS: { id: 'todas' | Platform; label: string }[] = [
  { id: 'todas', label: 'Todas' },
  { id: 'google', label: 'Google Ads' },
  { id: 'meta', label: 'Meta Ads' },
];

const FORMAT_LABEL: Record<CreativeFormat, string> = {
  search: 'Anúncio de pesquisa',
  imagem: 'Imagem',
  video: 'Vídeo',
  carrossel: 'Carrossel',
};

const CREATIVES_COLLAPSED = 8;

const SEGMENTS: { id: SegmentFilter; label: string }[] = [
  { id: 'todos', label: 'Geral' },
  { id: 'odonto', label: 'Odonto' },
  { id: 'medicina', label: 'Medicina' },
];

const MAP_METRICS: { id: MapMetric; label: string; format: (v: number) => string }[] = [
  { id: 'revenue', label: 'Faturamento', format: fmtCompactBRL },
  { id: 'leads', label: 'Leads', format: fmtInt },
  { id: 'orders', label: 'Pedidos', format: fmtInt },
  { id: 'convRate', label: 'Conversão', format: (v) => fmtPct(v) },
  { id: 'coverage', label: 'Cobertura', format: fmtInt },
];

// Cobertura: cada estado com a cor do consultor responsável; sem consultor fica neutro.
const REP_COLOR = new Map(REPS.map((rep, index) => [rep.id, TERRITORY_COLORS[index % TERRITORY_COLORS.length]]));
const COVERAGE = {
  colorOf: new Map(REPS.flatMap((rep) => rep.ufs.map((code) => [code, REP_COLOR.get(rep.id) as string] as const))),
  legend: [...REPS.map((rep) => ({ label: rep.name, color: REP_COLOR.get(rep.id) as string })), { label: 'Sem consultor', color: 'var(--uv-surface-3)' }],
};

function fmtResponse(minutes: number) {
  if (minutes < 60) return `${minutes} min`;
  const hours = minutes / 60;
  return `${hours.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} h`;
}

const ORIGIN_COLOR: Record<OriginGroup, string> = {
  paga: 'var(--uv-series-1)',
  organica: 'var(--uv-series-3)',
  relacionamento: 'var(--uv-series-2)',
};

const PLATFORM: Record<Platform, { label: string; color: string }> = {
  google: { label: 'Google Ads', color: 'var(--uv-series-1)' },
  meta: { label: 'Meta Ads', color: 'var(--uv-series-2)' },
};

const VERDICT: Record<Verdict, { label: string; icon: React.ReactNode; className: string }> = {
  escalar: { label: 'Escalar', icon: <ArrowUpRight size={13} />, className: 'uvVerdictGood' },
  manter: { label: 'Manter', icon: <Minus size={13} />, className: 'uvVerdictNeutral' },
  revisar: { label: 'Revisar', icon: <AlertTriangle size={13} />, className: 'uvVerdictWarn' },
};

const INSIGHT_TONE: Record<Insight['tone'], { label: string; icon: React.ReactNode }> = {
  oportunidade: { label: 'Oportunidade', icon: <TrendingUp size={14} /> },
  risco: { label: 'Atenção', icon: <AlertTriangle size={14} /> },
  destaque: { label: 'Destaque', icon: <Sparkles size={14} /> },
};

const orDash = (value: number | null, format: (v: number) => string, empty = 'n/d') => (value === null ? empty : format(value));
const fmtRoas = (value: number) => `${value.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}x`;

function Segmented<T extends string>({ options, value, onChange, label }: { options: { id: T; label: string }[]; value: T; onChange: (id: T) => void; label: string }) {
  return (
    <div className="uvSegmented" role="group" aria-label={label}>
      {options.map((option) => (
        <button key={option.id} type="button" className="uvSegmentedBtn" aria-pressed={value === option.id} onClick={() => onChange(option.id)}>
          {option.label}
        </button>
      ))}
    </div>
  );
}

// Variação contra o período anterior. `goodWhen` define se subir é bom (receita) ou ruim (CAC);
// `neutral` serve para métricas sem juízo de valor, como investimento.
function Delta({ kpi, goodWhen }: { kpi: KpiValue; goodWhen: 'up' | 'down' | 'neutral' }) {
  if (kpi.value === null || kpi.previous === null || kpi.previous === 0) return null;
  const change = (kpi.value - kpi.previous) / kpi.previous;
  const up = change >= 0;
  const tone = goodWhen === 'neutral' ? 'uvDeltaNeutral' : up === (goodWhen === 'up') ? 'uvDeltaGood' : 'uvDeltaBad';
  return (
    <span className={`uvDelta ${tone}`}>
      {up ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
      {fmtPct(Math.abs(change))}
    </span>
  );
}

function StatTile({ label, value, kpi, goodWhen, caption }: { label: string; value: string; kpi?: KpiValue; goodWhen?: 'up' | 'down' | 'neutral'; caption: string }) {
  return (
    <div className="uvTile">
      <div className="uvTileLabel">{label}</div>
      <div className="uvTileValue">{value}</div>
      <div className="uvTileFoot">
        {kpi && goodWhen && <Delta kpi={kpi} goodWhen={goodWhen} />}
        <span>{caption}</span>
      </div>
    </div>
  );
}

function CardHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: React.ReactNode }) {
  return (
    <div className="uvCardHeader">
      <div>
        <h3 className="uvCardTitle">{title}</h3>
        {subtitle && <p className="uvCardSubtitle">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

function InlineBar({ share, color = 'var(--uv-accent)' }: { share: number; color?: string }) {
  return <span className="uvInlineBar" style={{ width: `${Math.max(share * 100, share > 0 ? 2 : 0)}%`, background: color }} />;
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="uvEmpty">{children}</p>;
}

function CreativeCard({ creative }: { creative: CreativeRow }) {
  const verdict = VERDICT[creative.verdict];
  return (
    <article className={`uvCreative ${creative.active ? '' : 'uvCreativePaused'}`}>
      <div className="uvCreativeCover">
        {creative.image ? (
          <>
            <img src={creative.image} alt="" style={{ objectPosition: creative.imagePosition }} />
            {creative.format === 'video' && (
              <span className="uvCreativePlay" aria-hidden="true">
                <Play size={18} fill="currentColor" />
              </span>
            )}
          </>
        ) : (
          // Anúncio de pesquisa não tem imagem: o preview é o próprio texto do anúncio
          <div className="uvSearchPreview">
            <span>Patrocinado</span>
            <strong>{creative.headline}</strong>
            <p>{creative.body}</p>
          </div>
        )}
      </div>
      <div className="uvCreativeBody">
        <div className="uvCreativeHead">
          <strong>{creative.name}</strong>
          <span className={`uvVerdict ${verdict.className}`}>
            {verdict.icon}
            {verdict.label}
          </span>
        </div>
        <span className="uvCellSub">
          <span className="uvSwatch uvSwatchDot" style={{ background: PLATFORM[creative.platform].color }} />
          {PLATFORM[creative.platform].label} · {FORMAT_LABEL[creative.format]}
          {!creative.active && ' · Pausado'}
        </span>
        <p className="uvCreativeCopy">{creative.image ? creative.headline : creative.campaignName}</p>
        <dl className="uvCreativeStats">
          <div><dt>Investimento</dt><dd>{fmtBRL(creative.spend)}</dd></div>
          <div><dt>CTR</dt><dd>{orDash(creative.ctr, (v) => fmtPct(v))}</dd></div>
          <div><dt>CPL</dt><dd>{orDash(creative.cpl, fmtBRL)}</dd></div>
          <div><dt>Leads</dt><dd>{fmtInt(creative.leads)}</dd></div>
          <div><dt>Pedidos</dt><dd>{fmtInt(creative.orders)}</dd></div>
          <div><dt>CAC</dt><dd>{orDash(creative.cac, fmtBRL, 'sem pedido')}</dd></div>
        </dl>
      </div>
    </article>
  );
}

function stateMetric(state: StateRow, metric: MapMetric) {
  if (metric === 'coverage') return state.leads;
  return metric === 'convRate' ? state.convRate ?? 0 : state[metric];
}

export function UnivetExecutivePortal() {
  const [segment, setSegment] = useState<SegmentFilter>('todos');
  const [period, setPeriod] = useState<PeriodId>('90d');
  const [uf, setUf] = useState<string | null>(null);
  const [mapMetric, setMapMetric] = useState<MapMetric>('revenue');
  const [platform, setPlatform] = useState<'todas' | Platform>('todas');
  const [hoverBucket, setHoverBucket] = useState<number | null>(null);
  const [creativeSort, setCreativeSort] = useState<CreativeSort>('spend');
  const [showAllCreatives, setShowAllCreatives] = useState(false);

  // Destrava e garante scroll nativo livre da página inteira
  useEffect(() => {
    const root = document.getElementById('root');
    const prevHtmlOverflow = document.documentElement.style.overflow;
    const prevBodyOverflow = document.body.style.overflow;
    const prevRootOverflow = root?.style.overflow || '';

    document.documentElement.style.overflow = 'auto';
    document.body.style.overflow = 'auto';
    if (root) root.style.overflow = 'visible';

    return () => {
      document.documentElement.style.overflow = prevHtmlOverflow;
      document.body.style.overflow = prevBodyOverflow;
      if (root) root.style.overflow = prevRootOverflow;
    };
  }, []);

  const periodDays = PERIODS.find((p) => p.id === period)?.days ?? 90;
  const { data: portalResponse } = useQuery({
    queryKey: ['portal-dashboard', 'univet', periodDays],
    queryFn: () => portalApi.dashboard('univet', periodDays),
    staleTime: 60_000,
  });

  const baseData = useMemo(() => computeSnapshot({ period, segment, uf }), [period, segment, uf]);
  const data = useMemo(
    () => mergeSnapshotWithRealData(baseData, portalResponse?.dashboard, portalResponse?.dashboard?.nomus),
    [baseData, portalResponse],
  );
  const social = useMemo(() => computeSocial(period), [period]);
  const { kpis } = data;
  const periodLabel = PERIODS.find((p) => p.id === period)?.label ?? '';
  const metric = MAP_METRICS.find((m) => m.id === mapMetric) ?? MAP_METRICS[0];

  const mapValues = useMemo(() => new Map(data.states.map((s) => [s.uf, stateMetric(s, mapMetric)])), [data.states, mapMetric]);
  const ranking = useMemo(
    () => [...data.states].filter((s) => stateMetric(s, mapMetric) > 0).sort((a, b) => stateMetric(b, mapMetric) - stateMetric(a, mapMetric)).slice(0, 8),
    [data.states, mapMetric],
  );
  const rankingMax = ranking.length ? stateMetric(ranking[0], mapMetric) : 0;
  const selectedState = uf ? data.states.find((s) => s.uf === uf) ?? null : null;
  const uncoveredTop = useMemo(
    () => data.states.filter((s) => !s.rep && s.leads > 0).sort((a, b) => b.leads - a.leads).slice(0, 3),
    [data.states],
  );

  const campaigns = platform === 'todas' ? data.campaigns : data.campaigns.filter((c) => c.platform === platform);
  const maxCampaignSpend = Math.max(...data.campaigns.map((c) => c.spend), 1);
  const scatterPoints = campaigns
    .filter((c) => c.cpl !== null && c.leads > 0)
    .map((c) => ({
      id: c.id,
      label: c.name.split(' | ')[1] ?? c.name,
      x: c.cpl as number,
      y: c.leadToOrder ?? 0,
      size: c.spend,
      color: PLATFORM[c.platform].color,
      tooltip: (
        <>
          <div className="uvTooltipTitle">{c.name}</div>
          <div className="uvTooltipRow"><span /><span>Investimento</span><strong>{fmtBRL(c.spend)}</strong></div>
          <div className="uvTooltipRow"><span /><span>Custo por lead</span><strong>{fmtBRL(c.cpl as number)}</strong></div>
          <div className="uvTooltipRow"><span /><span>Lead em pedido</span><strong>{fmtPct(c.leadToOrder ?? 0)}</strong></div>
          <div className="uvTooltipRow"><span /><span>CAC</span><strong>{orDash(c.cac, fmtBRL, 'sem pedido')}</strong></div>
        </>
      ),
    }));
  const paidLeads = campaigns.reduce((sum, c) => sum + c.leads, 0);
  const paidOrders = campaigns.reduce((sum, c) => sum + c.orders, 0);
  const paidSpend = campaigns.reduce((sum, c) => sum + c.spend, 0);

  const creatives = useMemo(() => {
    const list = platform === 'todas' ? data.creatives : data.creatives.filter((c) => c.platform === platform);
    const sorted = [...list].sort((a, b) => {
      if (creativeSort === 'cpl') return (a.cpl ?? Infinity) - (b.cpl ?? Infinity);
      if (creativeSort === 'orders') return b.orders - a.orders || b.revenue - a.revenue;
      return b.spend - a.spend;
    });
    return sorted;
  }, [data.creatives, platform, creativeSort]);
  const visibleCreatives = showAllCreatives ? creatives : creatives.slice(0, CREATIVES_COLLAPSED);

  const maxProductRevenue = Math.max(...data.products.map((p) => p.revenue), 1);
  const maxSpecialtyRevenue = Math.max(...data.specialties.map((s) => s.revenue), 1);
  const maxChannelRevenue = Math.max(...data.channels.map((c) => c.revenue), 1);
  const funnelTop = data.funnel[0].count || 1;
  const hasOrders = (kpis.orders.value ?? 0) > 0;

  const headerActions = (
    <>
      {uf && (
        <button type="button" className="uvFilterChip" onClick={() => setUf(null)} aria-label={`Remover filtro de estado ${uf}`}>
          <MapPin size={13} />
          {uf}
          <X size={13} />
        </button>
      )}
      <Segmented options={SEGMENTS} value={segment} onChange={setSegment} label="Segmento" />
      <Segmented options={PERIODS} value={period} onChange={setPeriod} label="Período" />
      <button type="button" className="uvBtnSecondary" onClick={() => window.print()} title="Exportar o painel em PDF">
        <Download size={14} />
        <span>PDF</span>
      </button>
    </>
  );

  const dashboardReal = portalResponse?.dashboard;
  const nomusReal = dashboardReal?.nomus;

  return (
    <UnivetPortalChrome subtitle="Painel executivo · Brasil" actions={headerActions}>
      {nomusReal?.configured && (nomusReal.faturamento_total ?? 0) > 0 && (
        <div
          className="uvNotice uvNoticeSuccess"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            marginBottom: 20,
            background: 'rgba(34, 197, 94, 0.08)',
            border: '1px solid rgba(34, 197, 94, 0.25)',
            padding: '12px 18px',
            borderRadius: 8,
          }}
        >
          <CheckCircle2 size={18} color="var(--uv-accent)" />
          <span style={{ fontSize: '0.88rem' }}>
            <strong>Dados Reais Conectados:</strong> Faturamento e pedidos emitidos do <strong>Nomus ERP</strong> ({fmtBRL(nomusReal.faturamento_total)} em {nomusReal.pedidos_count} pedidos faturados) cruzados em tempo real com leads do <strong>Kommo CRM</strong> ({dashboardReal?.totals?.leads ?? 0} leads).
          </span>
        </div>
      )}
        <section className="uvHero">
          <h2 className="uvHeroHeadline">Da campanha ao pedido faturado</h2>
          <p className="uvHeroSubtitle">
            {data.scopeLabel}, últimos {periodLabel}. Mídia (Google Ads e Meta Ads), oportunidades (Kommo CRM) e faturamento (Nomus ERP) no mesmo recorte.
          </p>
        </section>

        {/* Indicadores principais */}
        <section className="uvKpiBand" aria-label="Indicadores principais">
          <div className="uvHeroTile">
            <div className="uvTileLabel">Faturamento (Nomus ERP)</div>
            <div className="uvHeroValue">{fmtBRL(kpis.revenue.value ?? 0)}</div>
            <div className="uvTileFoot">
              <Delta kpi={kpis.revenue} goodWhen="up" />
              <span>vs. {periodLabel} anteriores</span>
            </div>
            <dl className="uvHeroFacts">
              <div><dt>Pedidos faturados</dt><dd>{fmtInt(kpis.orders.value ?? 0)}</dd></div>
              <div><dt>Ticket médio</dt><dd>{orDash(kpis.ticket.value, fmtBRL)}</dd></div>
              <div><dt>Receita orgânica</dt><dd>{orDash(kpis.organicShare, (v) => fmtPct(v, 0))}</dd></div>
            </dl>
            <Sparkline values={data.buckets.map((b) => b.revenue)} label="Evolução do faturamento no período" />
          </div>

          <StatTile label="Investimento em mídia" value={fmtBRL(kpis.spend.value ?? 0)} kpi={kpis.spend} goodWhen="neutral" caption="Google Ads + Meta Ads" />
          <StatTile label="CAC estimado" value={orDash(kpis.cac.value, fmtBRL)} kpi={kpis.cac} goodWhen="down" caption={`Só mídia paga: ${orDash(kpis.cacPaid.value, fmtBRL)}`} />
          <StatTile label="ROAS de mídia" value={orDash(kpis.roas.value, fmtRoas)} kpi={kpis.roas} goodWhen="up" caption="Receita atribuída por real investido" />
          <StatTile label="Leads (Kommo CRM)" value={fmtInt(kpis.leads.value ?? 0)} kpi={kpis.leads} goodWhen="up" caption={`CPL pago: ${orDash(kpis.cpl.value, fmtBRL)}`} />
          <StatTile label="Lead em pedido" value={orDash(kpis.convRate.value, (v) => fmtPct(v))} kpi={kpis.convRate} goodWhen="up" caption={`Ciclo médio: ${orDash(kpis.avgCycleDays, (v) => `${Math.round(v)} dias`)}`} />
          <StatTile label="Propostas em aberto" value={fmtCompactBRL(kpis.openProposals.value)} caption={`${kpis.openProposals.count} propostas · ${kpis.upcomingDemos} demonstrações em 14 dias`} />
        </section>

        {/* Leituras automáticas */}
        {data.insights.length > 0 && (
          <section className="uvInsights" aria-label="Leituras do período">
            <h3 className="uvInsightsTitle">Leituras do período</h3>
            <div className="uvInsightsGrid">
              {data.insights.map((insight) => (
                <article key={insight.id} className={`uvInsight uvInsight-${insight.tone}`}>
                  <span className="uvInsightTone">
                    {INSIGHT_TONE[insight.tone].icon}
                    {INSIGHT_TONE[insight.tone].label}
                  </span>
                  <h4>{insight.title}</h4>
                  <p>{insight.body}</p>
                  <div className="uvInsightMetric">
                    <strong>{insight.metric}</strong>
                    <span>{insight.metricLabel}</span>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        {/* Receita no tempo + funil */}
        <div className="uvRow uvRow-7-5">
          <section className="uvCard">
            <CardHeader title="Receita faturada por origem" subtitle="Pedidos do Nomus atribuídos ao canal de entrada do lead">
              <ul className="uvLegend">
                {ORIGIN_GROUPS.map((group) => (
                  <li key={group.id}>
                    <span className="uvSwatch" style={{ background: ORIGIN_COLOR[group.id] }} />
                    {group.label}
                  </li>
                ))}
              </ul>
            </CardHeader>
            {hasOrders ? (
              <StackedColumns
                data={data.buckets.map((b) => ({ label: b.label, rangeLabel: b.rangeLabel, values: ORIGIN_GROUPS.map((g) => b[g.id]) }))}
                series={ORIGIN_GROUPS.map((g) => ({ label: g.label, color: ORIGIN_COLOR[g.id] }))}
                height={236}
                format={fmtBRL}
                axisFormat={(v) => (v === 0 ? '0' : fmtCompactBRL(v).replace('R$ ', ''))}
                hoverIndex={hoverBucket}
                onHover={setHoverBucket}
                showXAxis={false}
                ariaLabel="Receita faturada por intervalo, empilhada por origem"
              />
            ) : (
              <Empty>Nenhum pedido faturado neste recorte.</Empty>
            )}
            <div className="uvSubChartTitle">Investimento em mídia no mesmo intervalo</div>
            <StackedColumns
              data={data.buckets.map((b) => ({ label: b.label, rangeLabel: b.rangeLabel, values: [b.spend] }))}
              series={[{ label: 'Investimento', color: 'var(--uv-series-neutral)' }]}
              height={104}
              format={fmtBRL}
              axisFormat={(v) => (v === 0 ? '0' : fmtCompactBRL(v).replace('R$ ', ''))}
              hoverIndex={hoverBucket}
              onHover={setHoverBucket}
              ariaLabel="Investimento em mídia por intervalo"
            />
          </section>

          <section className="uvCard">
            <CardHeader title="Funil comercial" subtitle="Volume de cada etapa no período e custo de mídia por etapa" />
            <ol className="uvFunnel">
              <li className="uvFunnelRow uvFunnelHead" aria-hidden="true">
                <span>Etapa</span>
                <span>Volume</span>
                <span>Custo de mídia</span>
              </li>
              {data.funnel.map((stage) => (
                <li key={stage.id} className="uvFunnelRow">
                  <div className="uvFunnelLabel">
                    <strong>{stage.label}</strong>
                    <span>{stage.stepRate === null ? stage.source : `${fmtPct(stage.stepRate, 0)} da etapa anterior`}</span>
                  </div>
                  <div className="uvFunnelBarCell">
                    <InlineBar share={stage.count / funnelTop} />
                    <span className="uvFunnelCount">{fmtInt(stage.count)}</span>
                  </div>
                  <div className="uvFunnelCost">{orDash(stage.costPer, fmtBRL)}</div>
                </li>
              ))}
            </ol>
            <dl className="uvFactRow">
              <div><dt>Primeira resposta (mediana)</dt><dd>{orDash(kpis.medianResponseMin, (v) => `${v} min`)}</dd></div>
              <div><dt>Ciclo até o pedido</dt><dd>{orDash(kpis.avgCycleDays, (v) => `${Math.round(v)} dias`)}</dd></div>
            </dl>
          </section>
        </div>

        {/* Geografia */}
        <section className="uvCard">
          <CardHeader
            title={mapMetric === 'coverage' ? 'Cobertura comercial por estado' : 'Demanda e vendas por estado'}
            subtitle={
              mapMetric === 'coverage'
                ? 'Território de cada consultor e estados atendidos à distância. Nomes ilustrativos.'
                : 'Clique em um estado para filtrar o painel inteiro'
            }
          >
            <Segmented options={MAP_METRICS} value={mapMetric} onChange={setMapMetric} label="Métrica do mapa" />
          </CardHeader>
          <div className="uvGeo">
            <BrazilMap
              values={mapValues}
              selected={uf}
              onSelect={setUf}
              legendFormat={metric.format}
              territories={mapMetric === 'coverage' ? COVERAGE : undefined}
              ariaLabel={`Mapa do Brasil por ${metric.label.toLowerCase()}`}
              renderTooltip={(code) => {
                const state = data.states.find((s) => s.uf === code);
                if (!state) return null;
                return (
                  <>
                    <div className="uvTooltipTitle">{state.name}</div>
                    <div className="uvTooltipRow"><span /><span>Faturamento</span><strong>{fmtBRL(state.revenue)}</strong></div>
                    <div className="uvTooltipRow"><span /><span>Leads</span><strong>{fmtInt(state.leads)}</strong></div>
                    <div className="uvTooltipRow"><span /><span>Pedidos</span><strong>{fmtInt(state.orders)}</strong></div>
                    <div className="uvTooltipRow"><span /><span>Consultor</span><strong>{state.rep ?? 'Sem consultor'}</strong></div>
                  </>
                );
              }}
            />

            <div className="uvGeoSide">
              {selectedState ? (
                <div className="uvStateDetail">
                  <div className="uvStateDetailHead">
                    <div>
                      <h4>{selectedState.name}</h4>
                      <span className={selectedState.rep ? '' : 'uvTextWarn'}>
                        {selectedState.rep ? `Consultor: ${selectedState.rep}` : 'Sem consultor regional, atendimento remoto'}
                      </span>
                    </div>
                    <button type="button" className="uvBtnGhost" onClick={() => setUf(null)}>Ver Brasil</button>
                  </div>
                  <dl className="uvStatGrid">
                    <div><dt>Faturamento</dt><dd>{fmtBRL(selectedState.revenue)}</dd></div>
                    <div><dt>Pedidos</dt><dd>{fmtInt(selectedState.orders)}</dd></div>
                    <div><dt>Leads</dt><dd>{fmtInt(selectedState.leads)}</dd></div>
                    <div><dt>Demonstrações</dt><dd>{fmtInt(selectedState.demos)}</dd></div>
                    <div><dt>Lead em pedido</dt><dd>{orDash(selectedState.convRate, (v) => fmtPct(v))}</dd></div>
                    <div><dt>Ticket médio</dt><dd>{orDash(selectedState.ticket, fmtBRL)}</dd></div>
                  </dl>
                </div>
              ) : mapMetric === 'coverage' ? (
                <>
                  <div className="uvSideTitle">Consultores e territórios</div>
                  <ul className="uvRepKeys">
                    {data.reps.map((rep) => (
                      <li key={rep.id}>
                        <i style={{ background: REP_COLOR.get(rep.id) }} aria-hidden="true" />
                        <strong>{rep.name}</strong>
                        <span>{rep.ufs.join(', ')} · {fmtInt(rep.leads)} leads</span>
                      </li>
                    ))}
                    <li>
                      <i style={{ background: 'var(--uv-surface-3)' }} aria-hidden="true" />
                      <strong>Sem consultor</strong>
                      <span className="uvRepGap">
                        {data.states.filter((s) => !s.rep).length} estados · {fmtInt(data.uncovered.leads)} leads
                      </span>
                    </li>
                  </ul>
                  {uncoveredTop.length > 0 && (
                    <p className="uvChartNote">
                      Maior demanda sem consultor: {uncoveredTop.map((s) => `${s.name} (${fmtInt(s.leads)} leads)`).join(', ')}.
                    </p>
                  )}
                </>
              ) : (
                <>
                  <div className="uvSideTitle">Maiores estados por {metric.label.toLowerCase()}</div>
                  {ranking.length === 0 ? (
                    <Empty>Sem dados neste recorte.</Empty>
                  ) : (
                    <ul className="uvBarList">
                      {ranking.map((state) => (
                        <li key={state.uf}>
                          <button type="button" className="uvBarListRow" onClick={() => setUf(state.uf)}>
                            <span className="uvBarListName">
                              {state.name}
                              {!state.rep && <em>sem consultor</em>}
                            </span>
                            <span className="uvBarListTrack">
                              <InlineBar share={stateMetric(state, mapMetric) / rankingMax} />
                            </span>
                            <span className="uvBarListValue">{metric.format(stateMetric(state, mapMetric))}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="uvTableWrap">
            <table className="uvTable">
              <thead>
                <tr>
                  <th>Consultor</th>
                  <th>Território</th>
                  <th className="uvNum">Leads</th>
                  <th className="uvNum">Demonstrações</th>
                  <th className="uvNum">Propostas</th>
                  <th className="uvNum">Pedidos</th>
                  <th className="uvNum">Faturamento</th>
                  <th className="uvNum">Lead em pedido</th>
                  <th className="uvNum">1ª resposta</th>
                  <th className="uvNum">Parados +7d</th>
                </tr>
              </thead>
              <tbody>
                {data.reps.map((rep) => (
                  <tr key={rep.id} className={uf && rep.ufs.includes(uf) ? 'uvRowActive' : ''}>
                    <td>
                      <strong>{rep.name}</strong>
                      <span className="uvCellSub">{rep.role}</span>
                    </td>
                    <td>
                      {rep.territory}
                      <span className="uvCellSub">{rep.ufs.join(', ')}</span>
                    </td>
                    <td className="uvNum">{fmtInt(rep.leads)}</td>
                    <td className="uvNum">{fmtInt(rep.demos)}</td>
                    <td className="uvNum">{fmtInt(rep.props)}</td>
                    <td className="uvNum">{fmtInt(rep.orders)}</td>
                    <td className="uvNum"><strong>{fmtBRL(rep.revenue)}</strong></td>
                    <td className="uvNum">{orDash(rep.convRate, (v) => fmtPct(v))}</td>
                    <td className={`uvNum ${rep.responseMin > 120 ? 'uvTextWarn' : ''}`}>{fmtResponse(rep.responseMin)}</td>
                    <td className={`uvNum ${rep.staleOpen > 0 && rep.staleOpen / Math.max(rep.leads, 1) > 0.15 ? 'uvTextWarn' : ''}`}>{fmtInt(rep.staleOpen)}</td>
                  </tr>
                ))}
                <tr className="uvRowMuted">
                  <td>
                    <strong>Sem consultor</strong>
                    <span className="uvCellSub">Atendimento remoto</span>
                  </td>
                  <td>Demais estados</td>
                  <td className="uvNum">{fmtInt(data.uncovered.leads)}</td>
                  <td className="uvNum">{fmtInt(data.uncovered.demos)}</td>
                  <td className="uvNum">{fmtInt(data.uncovered.props)}</td>
                  <td className="uvNum">{fmtInt(data.uncovered.orders)}</td>
                  <td className="uvNum"><strong>{fmtBRL(data.uncovered.revenue)}</strong></td>
                  <td className="uvNum">{data.uncovered.leads > 0 ? fmtPct(data.uncovered.orders / data.uncovered.leads) : 'n/d'}</td>
                  <td className="uvNum">n/d</td>
                  <td className="uvNum">n/d</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Aquisição */}
        <div className="uvRow uvRow-7-5">
          <section className="uvCard">
            <CardHeader title="Canais de aquisição" subtitle="Do lead ao pedido faturado, por canal de entrada" />
            <div className="uvTableWrap">
              <table className="uvTable">
                <thead>
                  <tr>
                    <th>Canal</th>
                    <th className="uvNum">Leads</th>
                    <th className="uvNum">Pedidos</th>
                    <th>Receita</th>
                    <th className="uvNum">CAC</th>
                    <th className="uvNum">ROAS</th>
                  </tr>
                </thead>
                <tbody>
                  {data.channels.map((channel) => (
                    <tr key={channel.id}>
                      <td>
                        <span className="uvSwatch" style={{ background: ORIGIN_COLOR[channel.group] }} />
                        {channel.label}
                      </td>
                      <td className="uvNum">{fmtInt(channel.leads)}</td>
                      <td className="uvNum">{fmtInt(channel.orders)}</td>
                      <td>
                        <span className="uvBarCell">
                          <span className="uvBarCellTrack"><InlineBar share={channel.revenue / maxChannelRevenue} color={ORIGIN_COLOR[channel.group]} /></span>
                          <strong>{fmtBRL(channel.revenue)}</strong>
                        </span>
                      </td>
                      <td className="uvNum">{channel.spend > 0 ? orDash(channel.cac, fmtBRL, 'sem pedido') : 'sem mídia'}</td>
                      <td className="uvNum">{channel.spend > 0 ? orDash(channel.roas, fmtRoas) : 'n/d'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="uvCard">
            <CardHeader title="Públicos e clusters de mídia" subtitle="Quanto mais alto e à esquerda, mais barato e mais comprador">
              <ul className="uvLegend">
                {(Object.keys(PLATFORM) as Platform[]).map((id) => (
                  <li key={id}>
                    <span className="uvSwatch uvSwatchDot" style={{ background: PLATFORM[id].color }} />
                    {PLATFORM[id].label}
                  </li>
                ))}
              </ul>
            </CardHeader>
            {scatterPoints.length > 0 ? (
              <ScatterPlot
                points={scatterPoints}
                height={300}
                xLabel="Custo por lead"
                yLabel="Leads que viram pedido"
                xFormat={(v) => (v === 0 ? '0' : fmtBRL(v))}
                yFormat={(v) => fmtPct(v, 0)}
                xRef={paidLeads > 0 ? paidSpend / paidLeads : null}
                yRef={paidLeads > 0 ? paidOrders / paidLeads : null}
                ariaLabel="Dispersão de campanhas por custo por lead e taxa de conversão em pedido"
              />
            ) : (
              <Empty>Sem leads de mídia paga neste recorte.</Empty>
            )}
            <p className="uvChartNote">Tamanho do círculo: investimento. Linhas tracejadas: média da mídia paga.</p>
          </section>
        </div>

        <section className="uvCard">
          <CardHeader title="Campanhas e segmentações" subtitle="Investimento das plataformas cruzado com pedidos faturados no Nomus">
            <Segmented options={PLATFORM_OPTIONS} value={platform} onChange={setPlatform} label="Plataforma" />
          </CardHeader>
          <div className="uvTableWrap">
            <table className="uvTable">
              <thead>
                <tr>
                  <th>Campanha ou público</th>
                  <th>Investimento</th>
                  <th className="uvNum">Leads</th>
                  <th className="uvNum">CPL</th>
                  <th className="uvNum">Pedidos</th>
                  <th className="uvNum">Receita</th>
                  <th className="uvNum">CAC</th>
                  <th className="uvNum">ROAS</th>
                  <th>Leitura</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <strong>{c.name}</strong>
                      <span className="uvCellSub">
                        <span className="uvSwatch uvSwatchDot" style={{ background: PLATFORM[c.platform].color }} />
                        {PLATFORM[c.platform].label} · {c.cluster}
                      </span>
                    </td>
                    <td>
                      <span className="uvBarCell">
                        <span className="uvBarCellTrack"><InlineBar share={c.spend / maxCampaignSpend} color="var(--uv-series-neutral)" /></span>
                        <strong>{fmtBRL(c.spend)}</strong>
                      </span>
                    </td>
                    <td className="uvNum">{fmtInt(c.leads)}</td>
                    <td className="uvNum">{orDash(c.cpl, fmtBRL)}</td>
                    <td className="uvNum">{fmtInt(c.orders)}</td>
                    <td className="uvNum">{fmtBRL(c.revenue)}</td>
                    <td className="uvNum">{orDash(c.cac, fmtBRL, 'sem pedido')}</td>
                    <td className="uvNum">{orDash(c.roas, fmtRoas)}</td>
                    <td>
                      <span className={`uvVerdict ${VERDICT[c.verdict].className}`}>
                        {VERDICT[c.verdict].icon}
                        {VERDICT[c.verdict].label}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="uvCard">
          <CardHeader title="Criativos em veiculação" subtitle="Cada anúncio do Google Ads e do Meta Ads com o resultado que gerou até o pedido faturado">
            <div className="uvControlGroup">
              <Segmented options={PLATFORM_OPTIONS} value={platform} onChange={setPlatform} label="Plataforma dos criativos" />
              <Segmented options={CREATIVE_SORTS} value={creativeSort} onChange={setCreativeSort} label="Ordenação dos criativos" />
            </div>
          </CardHeader>
          <div className="uvCreativeGrid">
            {visibleCreatives.map((creative) => (
              <CreativeCard key={creative.id} creative={creative} />
            ))}
          </div>
          {creatives.length > CREATIVES_COLLAPSED && (
            <button type="button" className="uvBtnGhost uvShowMore" aria-expanded={showAllCreatives} onClick={() => setShowAllCreatives((open) => !open)}>
              {showAllCreatives ? 'Mostrar menos' : `Ver todos os ${creatives.length} criativos`}
            </button>
          )}
        </section>

        {/* Produtos e especialidades */}
        <div className="uvRow uvRow-7-5">
          <section className="uvCard">
            <CardHeader title="Produtos mais vendidos" subtitle="Pedidos faturados no Nomus ERP, por receita" />
            {hasOrders ? (
              <ul className="uvProductList">
                {data.products.map((product) => (
                  <li key={product.id}>
                    <div className="uvProductHead">
                      <span>
                        <strong>{product.name}</strong>
                        <em>{product.line}</em>
                      </span>
                      <strong>{fmtBRL(product.revenue)}</strong>
                    </div>
                    <div className="uvProductBar"><InlineBar share={product.revenue / maxProductRevenue} /></div>
                    <div className="uvProductMeta">
                      <span>{fmtInt(product.orders)} pedidos</span>
                      <span>Ticket {orDash(product.ticket, fmtBRL)}</span>
                      <span>{fmtPct(product.share, 0)} da receita</span>
                      <span>{fmtPct(product.medicinaShare, 0)} medicina</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>Nenhum pedido faturado neste recorte.</Empty>
            )}
          </section>

          <section className="uvCard">
            <CardHeader title="Especialidades que compram" subtitle="Segmento informado no CRM, por receita" />
            {data.specialties.length > 0 ? (
              <ul className="uvBarList uvBarListStatic">
                {data.specialties.slice(0, 7).map((spec) => (
                  <li key={`${spec.segment}-${spec.name}`} className="uvBarListRow">
                    <span className="uvBarListName">
                      {spec.name}
                      <em>{spec.segment === 'odonto' ? 'odonto' : 'medicina'} · {fmtInt(spec.leads)} leads · {orDash(spec.convRate, (v) => fmtPct(v))}</em>
                    </span>
                    <span className="uvBarListTrack"><InlineBar share={spec.revenue / maxSpecialtyRevenue} /></span>
                    <span className="uvBarListValue">{fmtCompactBRL(spec.revenue)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>Sem leads neste recorte.</Empty>
            )}
          </section>
        </div>

        {/* Perdas e redes sociais */}
        <div className="uvRow uvRow-7-5">
          <section className="uvCard">
            <CardHeader title="Por que perdemos oportunidades" subtitle="Motivo de perda obrigatório no Kommo, com a ação recomendada" />
            <ul className="uvLossList">
              {data.losses.filter((loss) => loss.count > 0).map((loss) => (
                <li key={loss.id}>
                  <div className="uvLossHead">
                    <strong>{loss.label}</strong>
                    <span>{fmtPct(loss.share, 0)} · {fmtInt(loss.count)} perdas{loss.value > 0 ? ` · ${fmtCompactBRL(loss.value)} em propostas` : ''}</span>
                  </div>
                  <div className="uvLossBar"><InlineBar share={loss.share / (data.losses[0].share || 1)} color="var(--uv-critical)" /></div>
                  <p>{loss.action}</p>
                </li>
              ))}
            </ul>
            {data.losses.every((loss) => loss.count === 0) && <Empty>Nenhuma perda registrada neste recorte.</Empty>}
          </section>

          <section className="uvCard">
            <CardHeader title="Instagram" subtitle="Monitoramento orgânico do perfil, sem recorte de segmento ou estado">
              <span className="uvTag"><Instagram size={13} /> Somente leitura</span>
            </CardHeader>
            <dl className="uvStatGrid">
              <div><dt>Seguidores</dt><dd>{fmtInt(social.followers)}</dd><span className="uvDelta uvDeltaGood"><ArrowUpRight size={13} />{fmtInt(social.followersDelta)}</span></div>
              <div><dt>Alcance</dt><dd>{fmtInt(social.reach)}</dd></div>
              <div><dt>Engajamento</dt><dd>{fmtPct(social.engagementRate)}</dd></div>
              <div><dt>Visitas ao perfil</dt><dd>{fmtInt(social.profileVisits)}</dd></div>
              <div><dt>Cliques no link</dt><dd>{fmtInt(social.linkClicks)}</dd></div>
            </dl>
            <Sparkline values={social.reachSeries} label="Evolução do alcance no período" />
            <div className="uvSideTitle">Conteúdos de maior alcance</div>
            <ul className="uvPostList">
              {social.topPosts.map((post) => (
                <li key={post.title}>
                  <span>
                    <strong>{post.title}</strong>
                    <em>{post.format}</em>
                  </span>
                  <span className="uvPostStats">{fmtInt(post.reach)} alcance · {fmtInt(post.saves)} salvamentos</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
    </UnivetPortalChrome>
  );
}
