import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bot,
  BarChart3,
  LineChart,
  RefreshCw,
  Sparkles,
  Target,
  TrendingUp,
  Printer,
} from "lucide-react";
import { EmptyState, SectionHeader } from "../components/shared";
import { ExecutiveReportPdfModal } from "../components/ExecutiveReportPdfModal";
import { TrendChart, type TrendPoint } from "../components/bi/TrendChart";
import {
  Ga4Icon,
  GoogleAdsIcon,
  GtmIcon,
  KommoIcon,
  LinkedInAdsIcon,
  MetaAdsIcon,
  SearchConsoleIcon,
} from "../components/icons/BrandIcons";
import {
  api,
  type AdsCampaignSummary,
  type Ga4AcquisitionSummary,
  type GscQuerySummary,
  type GtmSnapshotSummary,
  type PerformanceOverview,
  type PerformanceProvider,
  type PerformanceSyncRunEntry,
} from "../lib/api";
import {
  useClients,
  useKommoAnalytics,
  useKommoConfig,
  useLinkedInAdsDaily,
  useMetaAdsDaily,
  usePerformanceAiSummary,
  usePerformanceConnections,
} from "../hooks/useBiomaApi";

function formatNumber(value: number) {
  return new Intl.NumberFormat("pt-BR").format(Math.round(value));
}

function formatMoneyMicros(value: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value / 1_000_000);
}

function formatMoneyCents(value: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value / 100);
}

function formatPercent(value: number) {
  return new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 2 }).format(value);
}

function providerLabel(provider: string) {
  return {
    google_ads: "Google Ads",
    ga4: "GA4",
    search_console: "Search Console",
    gtm: "GTM",
    kommo: "Kommo CRM",
    meta_ads: "Meta Ads",
    linkedin_ads: "LinkedIn Ads",
  }[provider] ?? provider;
}

type PerformanceTab = "overview" | "ai_summary" | "kommo" | "google_ads" | "meta_ads" | "linkedin_ads" | "ga4" | "search_console" | "gtm";

type PerformanceTabIcon = typeof BarChart3 | typeof GoogleAdsIcon;

const performanceTabs: Array<{ id: PerformanceTab; label: string; icon: PerformanceTabIcon }> = [
  { id: "overview", label: "Visão geral", icon: LineChart },
  { id: "ai_summary", label: "IA Insight Multicanal", icon: Bot },
  { id: "kommo", label: "Kommo CRM", icon: KommoIcon },
  { id: "google_ads", label: "Google Ads", icon: GoogleAdsIcon },
  { id: "meta_ads", label: "Meta Ads", icon: MetaAdsIcon },
  { id: "linkedin_ads", label: "LinkedIn Ads", icon: LinkedInAdsIcon },
  { id: "ga4", label: "GA4", icon: Ga4Icon },
  { id: "search_console", label: "Search Console", icon: SearchConsoleIcon },
  { id: "gtm", label: "GTM", icon: GtmIcon },
];

type FreshnessEntry = PerformanceOverview["freshness"][number];

function FreshnessBanner({ freshness }: { freshness: FreshnessEntry | null }) {
  if (!freshness || freshness.last_synced_at) return null;
  return (
    <div className="demo-banner" role="status">
      <AlertTriangle size={18} />
      <span>
        Ainda sem sincronização real desta fonte para este cliente. Os números exibidos vêm da simulação
        do Bioma até a conexão no painel de Integrações.
      </span>
    </div>
  );
}

/** Por que a tela está sem número: última sincronização, status e ERRO.
 *
 * Existia `POST /sync` para pedir e nada para ver o resultado — conexão mal
 * configurada dava silêncio total. Agora o motivo real aparece aqui. */
function SyncDiagnostics({ clientId }: { clientId: string }) {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["performance-sync-runs", clientId],
    queryFn: () => api.performanceSyncRuns(clientId),
    enabled: Boolean(clientId),
  });

  const last = runs[0];
  const failed = runs.find((run: PerformanceSyncRunEntry) => run.status === "error");

  return (
    <div className="demo-banner" role="status" style={{ flexDirection: "column", alignItems: "flex-start", gap: 8 }}>
      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <AlertTriangle size={18} />
        <strong>Nenhuma fonte sincronizou ainda — os números abaixo são zero, não estimativa.</strong>
      </span>

      {isLoading && <span style={{ fontSize: 12.5 }}>Consultando o histórico de sincronização...</span>}

      {!isLoading && runs.length === 0 && (
        <span style={{ fontSize: 12.5 }}>
          Nenhuma execução registrada. Cadastre a conta em Configurações → Empresa → Integrações e clique em
          Sincronizar — ou espere o worker rodar (de hora em hora).
        </span>
      )}

      {failed && (
        <span style={{ fontSize: 12.5, color: "var(--danger)" }}>
          Última falha{failed.provider ? ` (${failed.provider})` : ""}:{" "}
          {failed.error_message || failed.error_code || "sem motivo registrado"}
        </span>
      )}

      {last && !failed && (
        <span style={{ fontSize: 12.5 }}>
          Última execução: {last.status} · {last.records_processed} registro(s) ·{" "}
          {new Date(last.started_at).toLocaleString("pt-BR")}
          {last.status === "queued" && " — ainda na fila, o worker roda de hora em hora."}
        </span>
      )}
    </div>
  );
}

function AiSummaryTab({ clientId }: { clientId: string }) {
  const { data: summary, isLoading, error } = usePerformanceAiSummary(clientId);

  if (isLoading) return <EmptyState compact text="Sintetizando inteligência de mídia paga..." />;
  if (error) return <div className="notice error">{error.message}</div>;
  if (!summary) return <EmptyState compact text="Nenhuma análise gerada ainda." />;

  return (
    <div className="performance-tab-panel">
      <article className="surface" style={{ background: "linear-gradient(135deg, var(--surface) 0%, rgba(58, 201, 123, 0.08) 100%)" }}>
        <SectionHeader
          eyebrow="Visão Estratégica EG"
          title={summary.generation_mode === "live" ? "Análise Multicanal por IA" : "Resumo Multicanal"}
          icon={Bot}
        />
        {/* O rótulo tem que dizer a verdade sobre o que a pessoa está lendo.
            Antes a tela dizia "IA" sempre — inclusive quando não havia IA
            nenhuma e as recomendações eram fixas no código. */}
        {summary.generation_mode !== "live" && (
          <div
            style={{
              display: "inline-flex", alignItems: "center", gap: 6, marginTop: 8,
              fontSize: 11.5, padding: "4px 10px", borderRadius: 999,
              border: "1px solid var(--amber)", color: "var(--amber)",
            }}
          >
            {summary.generation_mode === "unavailable"
              ? "Análise indisponível agora — os números abaixo são reais"
              : "Sem síntese de IA — números reais, organizados. Cadastre a conta em Operação EG → IA"}
          </div>
        )}
        <p style={{ fontSize: "15px", lineHeight: "1.6", color: "var(--text-main)", margin: "16px 0" }}>
          {summary.summary_text}
        </p>

        <div className="metrics analytics-metrics" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
          <article className="metric-card analytics-card">
            <span>Investimento Multicanal</span>
            <strong>{formatMoneyCents(summary.total_spend_cents)}</strong>
            <small>Meta Ads + LinkedIn Ads + Google</small>
          </article>
          <article className="metric-card analytics-card">
            <span>Total de Leads</span>
            <strong>{formatNumber(summary.total_leads)}</strong>
            <small>Oportunidades geradas</small>
          </article>
          <article className="metric-card analytics-card">
            <span>CPA Geral Consolidado</span>
            <strong>{formatMoneyCents(summary.overall_cpa_cents)}</strong>
            <small>Custo por aquisição</small>
          </article>
        </div>

        <h4 style={{ marginTop: "24px", marginBottom: "12px" }}>Insights de Impacto Comercial</h4>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {summary.insights.map((insight, idx) => (
            <div
              key={idx}
              style={{
                background: "var(--surface)",
                borderLeft: `4px solid ${insight.impact_level === "high" ? "var(--brand-accent)" : "var(--accent)"}`,
                padding: "16px",
                borderRadius: "6px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <strong style={{ fontSize: "14px" }}>{insight.title}</strong>
                <span className="demo-badge">{insight.channel.replace("_", " ").toUpperCase()}</span>
              </div>
              <p style={{ margin: "4px 0", color: "var(--text-muted)", fontSize: "13px" }}>{insight.finding}</p>
              <p style={{ margin: "6px 0 0 0", color: "var(--brand-accent)", fontWeight: 500, fontSize: "13px" }}>
                💡 <strong>Ação Recomendada:</strong> {insight.action_recommendation}
              </p>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

function MetaAdsTab({ clientId }: { clientId: string }) {
  const { data: metrics, isLoading, error } = useMetaAdsDaily(clientId);

  if (isLoading) return <EmptyState compact text="Carregando métricas de Meta Ads..." />;
  if (error) return <div className="notice error">{error.message}</div>;

  return (
    <div className="performance-tab-panel">
      <article className="surface">
        <SectionHeader eyebrow="Meta Ads (Instagram / Facebook)" title="Desempenho Diário" icon={MetaAdsIcon} />
        {!metrics || metrics.length === 0 ? (
          <EmptyState compact text="Nenhum dado de Meta Ads encontrado para este workspace." />
        ) : (
          <div className="table-list">
            {metrics.map((row) => (
              <div className="table-row" key={row.id}>
                <strong>{row.campaign_name}</strong>
                <span>{row.date} · {formatNumber(row.impressions)} imp.</span>
                <span>{formatNumber(row.clicks)} cliques (CTR {row.ctr}%)</span>
                <span>{formatMoneyCents(row.spend_cents)} investidos</span>
                <span>{row.leads} leads · CPA R$ {(row.cpa_cents / 100).toFixed(2)}</span>
              </div>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

function LinkedInAdsTab({ clientId }: { clientId: string }) {
  const { data: metrics, isLoading, error } = useLinkedInAdsDaily(clientId);

  if (isLoading) return <EmptyState compact text="Carregando métricas de LinkedIn Ads..." />;
  if (error) return <div className="notice error">{error.message}</div>;

  return (
    <div className="performance-tab-panel">
      <article className="surface">
        <SectionHeader eyebrow="LinkedIn Ads (B2B Lead Gen)" title="Desempenho Diário" icon={LinkedInAdsIcon} />
        {!metrics || metrics.length === 0 ? (
          <EmptyState compact text="Nenhum dado de LinkedIn Ads encontrado para este workspace." />
        ) : (
          <div className="table-list">
            {metrics.map((row) => (
              <div className="table-row" key={row.id}>
                <strong>{row.campaign_name}</strong>
                <span>{row.date} · {formatNumber(row.impressions)} imp.</span>
                <span>{formatNumber(row.clicks)} cliques (CTR {row.ctr}%)</span>
                <span>{formatMoneyCents(row.spend_cents)} investidos</span>
                <span>{row.leads} leads qualificados · CPA R$ {(row.cpa_cents / 100).toFixed(2)}</span>
              </div>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

function GoogleAdsTab({ clientId, freshness }: { clientId: string; freshness: FreshnessEntry | null }) {
  const [campaigns, setCampaigns] = useState<AdsCampaignSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!clientId) return;
    setLoading(true);
    setError("");
    api
      .adsCampaigns(clientId)
      .then(setCampaigns)
      .catch((err: Error) => setError(err.message || "Não foi possível carregar campanhas do Google Ads."))
      .finally(() => setLoading(false));
  }, [clientId]);

  return (
    <div className="performance-tab-panel">
      <FreshnessBanner freshness={freshness} />
      {error && <div className="notice error">{error}</div>}
      <article className="surface">
        <SectionHeader eyebrow="Google Ads" title="Campanhas detalhadas" icon={GoogleAdsIcon} />
        {loading ? (
          <EmptyState compact text="Carregando campanhas..." />
        ) : campaigns.length === 0 ? (
          <EmptyState compact text="Nenhuma campanha sincronizada para este cliente." />
        ) : (
          <div className="table-list">
            {campaigns.map((campaign) => (
              <div className="table-row" key={campaign.campaign_id}>
                <strong>{campaign.campaign_name}</strong>
                <span>{campaign.channel_type} · {campaign.campaign_status}</span>
                <span>{formatNumber(campaign.impressions)} imp.</span>
                <span>{formatNumber(campaign.clicks)} cliques · CTR {formatPercent(campaign.ctr)}</span>
                <span>{formatMoneyMicros(campaign.cost_micros)} · ROAS {campaign.roas.toFixed(2)}</span>
              </div>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

function Ga4Tab({ clientId, freshness }: { clientId: string; freshness: FreshnessEntry | null }) {
  const [rows, setRows] = useState<Ga4AcquisitionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!clientId) return;
    setLoading(true);
    setError("");
    api
      .ga4Acquisition(clientId)
      .then(setRows)
      .catch((err: Error) => setError(err.message || "Não foi possível carregar aquisição do GA4."))
      .finally(() => setLoading(false));
  }, [clientId]);

  return (
    <div className="performance-tab-panel">
      <FreshnessBanner freshness={freshness} />
      {error && <div className="notice error">{error}</div>}
      <article className="surface">
        <SectionHeader eyebrow="GA4" title="Aquisição por origem/mídia" icon={Ga4Icon} />
        {loading ? (
          <EmptyState compact text="Carregando aquisição do GA4..." />
        ) : rows.length === 0 ? (
          <EmptyState compact text="Nenhum dado de aquisição sincronizado para este cliente." />
        ) : (
          <div className="table-list">
            {rows.map((row, index) => (
              <div className="table-row" key={`${row.source}-${row.medium}-${row.campaign}-${index}`}>
                <strong>{row.source} / {row.medium}</strong>
                <span>{row.campaign || "sem campanha"}</span>
                <span>{formatNumber(row.sessions)} sessões</span>
                <span>{formatNumber(row.total_users)} usuários · {formatNumber(row.new_users)} novos</span>
                <span>{formatPercent(row.engagement_rate)} engaj. · {formatNumber(row.key_events)} eventos-chave</span>
              </div>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

function GscTab({ clientId, freshness }: { clientId: string; freshness: FreshnessEntry | null }) {
  const [rows, setRows] = useState<GscQuerySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!clientId) return;
    setLoading(true);
    setError("");
    api
      .gscQueries(clientId)
      .then(setRows)
      .catch((err: Error) => setError(err.message || "Não foi possível carregar consultas do Search Console."))
      .finally(() => setLoading(false));
  }, [clientId]);

  return (
    <div className="performance-tab-panel">
      <FreshnessBanner freshness={freshness} />
      {error && <div className="notice error">{error}</div>}
      <article className="surface">
        <SectionHeader eyebrow="Search Console" title="Consultas orgânicas" icon={SearchConsoleIcon} />
        {loading ? (
          <EmptyState compact text="Carregando consultas do Search Console..." />
        ) : rows.length === 0 ? (
          <EmptyState compact text="Nenhuma consulta sincronizada para este cliente." />
        ) : (
          <div className="table-list">
            {rows.map((row, index) => (
              <div className="table-row" key={`${row.query}-${row.country}-${row.device}-${index}`}>
                <strong>{row.query}</strong>
                <span>{row.country} · {row.device}</span>
                <span>{formatNumber(row.clicks)} cliques</span>
                <span>{formatNumber(row.impressions)} imp. · CTR {formatPercent(row.ctr)}</span>
                <span>posição média {row.position.toFixed(1)}</span>
              </div>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

const severityLabel: Record<string, string> = {
  info: "Info",
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

function GtmTab({ clientId, freshness }: { clientId: string; freshness: FreshnessEntry | null }) {
  const [snapshots, setSnapshots] = useState<GtmSnapshotSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!clientId) return;
    setLoading(true);
    setError("");
    api
      .gtmSnapshots(clientId)
      .then(setSnapshots)
      .catch((err: Error) => setError(err.message || "Não foi possível carregar snapshots do GTM."))
      .finally(() => setLoading(false));
  }, [clientId]);

  return (
    <div className="performance-tab-panel">
      <FreshnessBanner freshness={freshness} />
      {error && <div className="notice error">{error}</div>}
      <article className="surface">
        <SectionHeader eyebrow="Google Tag Manager" title="Snapshots do container" icon={GtmIcon} />
        {loading ? (
          <EmptyState compact text="Carregando snapshots do GTM..." />
        ) : snapshots.length === 0 ? (
          <EmptyState compact text="Nenhum snapshot de GTM coletado para este cliente." />
        ) : (
          <div className="table-list">
            {snapshots.map((snapshot) => (
              <div className="gtm-snapshot" key={snapshot.id}>
                <div className="table-row">
                  <strong>{snapshot.account_id}/{snapshot.container_id}</strong>
                  <span>GTM workspace {snapshot.gtm_workspace_id ?? "live"}</span>
                  <span>{snapshot.tags_count} tags</span>
                  <span>{snapshot.triggers_count} triggers · {snapshot.variables_count} variáveis</span>
                  <span>{new Date(snapshot.collected_at).toLocaleString("pt-BR")}</span>
                </div>
                {snapshot.findings.length > 0 && (
                  <div className="insights-list mt-3">
                    {snapshot.findings.map((finding) => (
                      <div className="insight-item" key={finding.id}>
                        <AlertTriangle size={18} className={`insight-icon severity-${finding.severity}`} />
                        <div>
                          <strong>
                            {finding.title} <em className="demo-badge">{severityLabel[finding.severity] ?? finding.severity}</em>
                          </strong>
                          <p>{finding.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

function KommoTab({ organizationId }: { organizationId: string }) {
  const { data: analytics, isLoading, error } = useKommoAnalytics(organizationId);

  return (
    <div className="performance-tab-panel">
      {error && <div className="notice error">{error.message || "Não foi possível carregar os dados do Kommo."}</div>}
      
      <article className="surface">
        <SectionHeader eyebrow="Kommo CRM" title="Métricas de Pipeline" icon={KommoIcon} />
        
        {isLoading ? (
          <EmptyState compact text="Carregando dados do Kommo..." />
        ) : !analytics || analytics.pipelines.length === 0 ? (
          <EmptyState compact text="Nenhum dado do Kommo sincronizado para esta organização." />
        ) : (
          <div className="analytics-grid" style={{ marginTop: 24, gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
            {analytics.pipelines.map((pipeline) => (
              <article key={pipeline.pipeline_id} className="surface" style={{ padding: '20px', background: 'var(--bg-elevated)', border: '1px solid var(--border-light)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <h4 style={{ margin: 0, fontSize: 16 }}>{pipeline.pipeline_name}</h4>
                  <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                    {new Date(pipeline.snapshot_date).toLocaleDateString("pt-BR")}
                  </span>
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Total de Leads</div>
                    <div style={{ fontSize: 20, fontWeight: 600 }}>{formatNumber(pipeline.total_leads)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Valor Total</div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-main)' }}>{new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(pipeline.total_value)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Leads Ganhos</div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: 'var(--brand-accent)' }}>{formatNumber(pipeline.won_leads)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Valor Ganho</div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: 'var(--brand-accent)' }}>{new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(pipeline.won_value)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Leads Perdidos</div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: 'var(--danger-soft)' }}>{formatNumber(pipeline.lost_leads)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Leads Ativos</div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: 'var(--accent)' }}>{formatNumber(pipeline.active_leads)}</div>
                  </div>
                </div>
                
                <div style={{ 
                  height: 6, 
                  background: 'var(--bg-elevated)', 
                  borderRadius: 3, 
                  display: 'flex', 
                  overflow: 'hidden' 
                }}>
                  {pipeline.total_leads > 0 && (
                    <>
                      <div style={{ width: `${(pipeline.won_leads / pipeline.total_leads) * 100}%`, background: 'var(--brand-accent)' }} title="Ganhos" />
                      <div style={{ width: `${(pipeline.active_leads / pipeline.total_leads) * 100}%`, background: 'var(--accent)' }} title="Ativos" />
                      <div style={{ width: `${(pipeline.lost_leads / pipeline.total_leads) * 100}%`, background: 'var(--danger-soft)' }} title="Perdidos" />
                    </>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

export function AnalyticsView({ clientId, workspaceName }: { clientId: string; workspaceName?: string }) {
  const { data: clientsData } = useClients();
  const clients = clientsData ?? [];
  const selectedClient = clients.find((client) => client.id === clientId) ?? null;
  const effectiveClientId = selectedClient?.id ?? "";
  const { data: connections = [] } = usePerformanceConnections(effectiveClientId || null);
  const { data: kommoConfig } = useKommoConfig(selectedClient?.organization_id ?? null);
  const [overview, setOverview] = useState<PerformanceOverview | null>(null);
  const [campaigns, setCampaigns] = useState<AdsCampaignSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<PerformanceTab>("overview");

  const connectedProviders = useMemo(
    () => new Set(connections.map((connection) => connection.provider)),
    [connections],
  );

  const visibleTabs = useMemo(
    () =>
      performanceTabs.filter((item) => {
        if (item.id === "overview" || item.id === "ai_summary") return true;
        if (item.id === "kommo") return Boolean(kommoConfig?.configured);
        return connectedProviders.has(item.id as PerformanceProvider);
      }),
    [connectedProviders, kommoConfig],
  );

  useEffect(() => {
    setTab("overview");
  }, [effectiveClientId]);

  useEffect(() => {
    if (!visibleTabs.some((item) => item.id === tab)) {
      setTab("overview");
    }
  }, [visibleTabs, tab]);

  useEffect(() => {
    if (!effectiveClientId) {
      setOverview(null);
      setCampaigns([]);
      return;
    }

    setLoading(true);
    setError("");
    Promise.all([api.performanceOverview(effectiveClientId), api.adsCampaigns(effectiveClientId)])
      .then(([nextOverview, nextCampaigns]) => {
        setOverview(nextOverview);
        setCampaigns(nextCampaigns);
      })
      .catch((err: Error) => setError(err.message || "Não foi possível carregar Performance."))
      .finally(() => setLoading(false));
  }, [effectiveClientId]);

  const trend = useMemo<TrendPoint[]>(
    () => overview?.daily.map((point) => ({ label: point.date.slice(5), value: point.impressions })) ?? [],
    [overview],
  );
  const hasSyncedSource = overview?.freshness.some((source) => source.last_synced_at) ?? false;
  const demoMode = !hasSyncedSource;

  function freshnessOf(provider: PerformanceProvider): FreshnessEntry | null {
    return overview?.freshness.find((source) => source.provider === provider) ?? null;
  }

  if (loading) {
    return <EmptyState text="Carregando Performance..." />;
  }

  const ads = overview?.ads;

  const [isPdfModalOpen, setIsPdfModalOpen] = useState(false);
  const [syncingMedia, setSyncingMedia] = useState(false);

  const handleSyncMedia = async () => {
    if (!effectiveClientId) return;
    setSyncingMedia(true);
    try {
      // `POST /sync` responde 202: ENFILEIRA, não executa. Quem executa é o
      // worker, no cron de hora em hora.
      await api.requestPerformanceSync(effectiveClientId, "all");
      const [nextOverview, nextCampaigns] = await Promise.all([
        api.performanceOverview(effectiveClientId),
        api.adsCampaigns(effectiveClientId),
      ]);
      setOverview(nextOverview);
      setCampaigns(nextCampaigns);
      // A mensagem antiga dizia "solicitada com sucesso" e a tela recarregava
      // na hora — ainda vazia, porque o worker nem tinha rodado. Quem clicava
      // concluía, com razão, que o botão não funcionava. Dizer que ficou NA
      // FILA e quando roda é a diferença entre "quebrado" e "aguardando".
      alert(
        "Sincronização enfileirada. " +
        "Ela não roda agora: o worker processa a fila de hora em hora. " +
        "Os números aparecem depois disso — e se falhar, o motivo fica no aviso " +
        "no topo desta tela."
      );
    } catch (err: any) {
      alert("Erro ao enfileirar a sincronização: " + (err.message || "Erro de conexão."));
    } finally {
      setSyncingMedia(false);
    }
  };

  return (
    <section className="analytics-layout">
      {error && <div className="notice error">{error}</div>}

      <div className="analytics-header">
        <div>
          <h2>Performance de {workspaceName ?? selectedClient?.name ?? "cliente"}</h2>
          <p>
            {overview
              ? `${overview.period_start} até ${overview.period_end}`
              : "Sem dados de Performance para o período atual."}
          </p>
        </div>
        <div className="analytics-actions" style={{ display: "flex", gap: "10px" }}>
          <button className="secondary-button" type="button" onClick={handleSyncMedia} disabled={syncingMedia}>
            <RefreshCw size={16} className={syncingMedia ? "spin" : ""} />
            {syncingMedia ? "Enfileirando..." : "Sincronizar mídia agora"}
          </button>
          {/* Desabilitado sem dados: o modal só renderiza com `overview`, então
              antes o clique nao fazia NADA — botao habilitado que ignora o
              clique e pior que botao desabilitado, porque parece quebrado. */}
          <button
            className="primary-button"
            type="button"
            onClick={() => setIsPdfModalOpen(true)}
            disabled={!overview}
            title={overview ? undefined : "Sem dados de performance no período — nada para relatar."}
          >
            <Printer size={16} /> Exportar Relatório Executivo PDF
          </button>
        </div>
      </div>

      {isPdfModalOpen && overview && (
        <ExecutiveReportPdfModal
          data={{
            title: `Relatório Executivo de Performance`,
            subtitle: `Análise consolidada de mídia paga, tráfego orgânico e conversões`,
            clientName: workspaceName ?? selectedClient?.name ?? "Cliente EG",
            period: `${overview.period_start} a ${overview.period_end}`,
            summaryMetrics: [
              { label: "Impressões Totais", value: formatNumber(overview.daily.reduce((acc, d) => acc + d.impressions, 0)) },
              { label: "Cliques em Campanhas", value: formatNumber(overview.daily.reduce((acc, d) => acc + d.clicks, 0)) },
              { label: "Investimento em Mídia", value: formatMoneyMicros(overview.daily.reduce((acc, d) => acc + d.cost_micros, 0)) },
              { label: "Receita & Conversões", value: formatMoneyMicros(overview.daily.reduce((acc, d) => acc + (d.conversion_value || 0), 0)) },
            ],
            // Sem destaques inventados. Aqui havia três frases FIXAS no código
            // — entre elas "campanhas operando com ROI positivo" — que iam para
            // um PDF entregue ao cliente independentemente dos números reais.
            // Num relatório assinado pela EG, isso é afirmação falsa sobre
            // resultado, não texto de apoio. Quando existir destaque derivado
            // do dado, ele entra aqui calculado; até lá, não entra nada.
            highlights: undefined,
            tables: campaigns.length > 0 ? [
              {
                title: "Desempenho por Campanha",
                headers: ["Campanha", "Canal", "Impressões", "Cliques", "Investimento", "ROAS"],
                rows: campaigns.slice(0, 10).map((c) => [
                  c.campaign_name,
                  c.channel_type.toUpperCase(),
                  formatNumber(c.impressions),
                  formatNumber(c.clicks),
                  formatMoneyMicros(c.cost_micros),
                  c.roas.toFixed(2),
                ]),
              },
            ] : undefined,
            // Mesmo motivo dos destaques: "próximos passos" fixos sugerem um
            // plano que ninguém definiu para este cliente.
            nextSteps: undefined,
          }}
          onClose={() => setIsPdfModalOpen(false)}
        />
      )}

      <div className="performance-tabs" role="tablist">
        {visibleTabs.map((item) => {
          const Icon = item.icon;
          return (
            <button
              className={tab === item.id ? "performance-tab active" : "performance-tab"}
              key={item.id}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              onClick={() => setTab(item.id)}
            >
              <Icon size={15} />
              {item.label}
            </button>
          );
        })}
      </div>

      {tab === "overview" && (
        <>
          {/* Diagnóstico em vez de aviso vago. O texto antigo dizia que os
              números "podem vir do seed de demonstração" — mas quando nada
              sincronizou eles são ZERO, e a mensagem escondia a informação
              útil: nunca rodou, e por quê. */}
          {demoMode && <SyncDiagnostics clientId={effectiveClientId} />}

          <div className="metrics analytics-metrics">
            <article className="metric-card analytics-card">
              <span>
                <BarChart3 size={16} /> Impressões {demoMode && <em className="demo-badge">demo</em>}
              </span>
              <strong>{formatNumber(ads?.impressions ?? 0)}</strong>
              <small>Google Ads agregado</small>
            </article>
            <article className="metric-card analytics-card">
              <span>
                <TrendingUp size={16} /> Cliques {demoMode && <em className="demo-badge">demo</em>}
              </span>
              <strong>{formatNumber(ads?.clicks ?? 0)}</strong>
              <small>CTR {formatPercent(ads?.ctr ?? 0)}</small>
            </article>
            <article className="metric-card analytics-card">
              <span>
                <Target size={16} /> Conversões {demoMode && <em className="demo-badge">demo</em>}
              </span>
              <strong>{formatNumber(ads?.conversions ?? 0)}</strong>
              <small>ROAS {(ads?.roas ?? 0).toFixed(2)}</small>
            </article>
            <article className="metric-card analytics-card">
              <span>
                <LineChart size={16} /> Investimento {demoMode && <em className="demo-badge">demo</em>}
              </span>
              <strong>{formatMoneyMicros(ads?.cost_micros ?? 0)}</strong>
              <small>CPA {formatMoneyMicros(ads?.cpa_micros ?? 0)}</small>
            </article>
          </div>

          <div className="analytics-grid">
            <article className="surface">
              <SectionHeader eyebrow="Evolução" title="Impressões por dia" icon={LineChart} />
              {trend.length > 0 ? <TrendChart data={trend} name="Impressões" /> : <EmptyState compact text="Sem série diária." />}
              <p className="panel-footnote">Dados lidos do endpoint real de Performance do Bioma.</p>
            </article>

            <article className="surface">
              <SectionHeader eyebrow="Freshness" title="Fontes conectadas" icon={Sparkles} />
              <div className="health-list">
                {overview?.freshness.map((source) => (
                  <div className="health-row" key={source.provider}>
                    <span className={source.status === "error" ? "dot" : "dot online"} />
                    <span>{providerLabel(source.provider)}</span>
                    <strong className={source.status === "error" ? "bad" : "ok"}>
                      {source.last_synced_at ? new Date(source.last_synced_at).toLocaleDateString("pt-BR") : "sem sync"}
                    </strong>
                  </div>
                ))}
                {!overview?.freshness.length && <EmptyState compact text="Nenhuma conexão de Performance." />}
              </div>
            </article>
          </div>

          <article className="surface">
            <SectionHeader eyebrow="Google Ads" title="Campanhas" icon={GoogleAdsIcon} />
            <div className="table-list">
              {campaigns.map((campaign) => (
                <div className="table-row" key={campaign.campaign_id}>
                  <strong>{campaign.campaign_name}</strong>
                  <span>{campaign.channel_type}</span>
                  <span>{formatNumber(campaign.impressions)} imp.</span>
                  <span>{formatNumber(campaign.clicks)} cliques</span>
                  <span>{formatMoneyMicros(campaign.cost_micros)}</span>
                </div>
              ))}
              {campaigns.length === 0 && <EmptyState compact text="Nenhuma campanha retornada." />}
            </div>
          </article>
        </>
      )}

      {tab === "ai_summary" && <AiSummaryTab clientId={effectiveClientId} />}
      {tab === "google_ads" && <GoogleAdsTab clientId={effectiveClientId} freshness={freshnessOf("google_ads")} />}
      {tab === "meta_ads" && <MetaAdsTab clientId={effectiveClientId} />}
      {tab === "linkedin_ads" && <LinkedInAdsTab clientId={effectiveClientId} />}
      {tab === "ga4" && <Ga4Tab clientId={effectiveClientId} freshness={freshnessOf("ga4")} />}
      {tab === "search_console" && <GscTab clientId={effectiveClientId} freshness={freshnessOf("search_console")} />}
      {tab === "gtm" && <GtmTab clientId={effectiveClientId} freshness={freshnessOf("gtm")} />}
      {tab === "kommo" && selectedClient?.organization_id && <KommoTab organizationId={selectedClient.organization_id} />}
    </section>
  );
}
