import { useMemo, useState } from "react";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, CheckCircle2, CircleDashed, RefreshCw } from "lucide-react";
import type { KommoDashboard, KommoRankedItem } from "../lib/api";
import { useKommoDashboard, useSyncKommoDashboard } from "../hooks/api";
import { fmtBRL, fmtInt, fmtPct } from "../data/univet/univetPortalData";
import { BrazilMap, StackedColumns } from "../views/univet/UnivetCharts";
import "../views/univet/univet-portal.css";

// Painel de dados reais: tudo aqui vem da última sincronização do Kommo guardada na API.
// Nenhum número é estimado. O que ainda não tem fonte conectada aparece como ausente.

const PERIODS = [
  { id: 0, label: "Todo o histórico" },
  { id: 30, label: "30 dias" },
  { id: 90, label: "90 dias" },
  { id: 180, label: "6 meses" },
];

// Campos mostrados como ranking. UF vai para o mapa; motivo de perda tem bloco próprio.
const RANKED_DIMENSIONS = ["origem", "segmento", "produto", "solicitacao", "tipo_atendimento", "representante"];

export function formatDateTime(value: string | number | null) {
  if (value === null) return "sem registro";
  const date = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  return date.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function PeriodSegmented({ value, onChange }: { value: number; onChange: (id: number) => void }) {
  return (
    <div className="uvSegmented" role="group" aria-label="Período">
      {PERIODS.map((period) => (
        <button key={period.id} type="button" className="uvSegmentedBtn" aria-pressed={value === period.id} onClick={() => onChange(period.id)}>
          {period.label}
        </button>
      ))}
    </div>
  );
}

function Tile({ label, value, caption, delta }: { label: string; value: string; caption: string; delta?: number | null }) {
  return (
    <div className="uvTile">
      <div className="uvTileLabel">{label}</div>
      <div className="uvTileValue">{value}</div>
      <div className="uvTileFoot">
        {delta !== undefined && delta !== null && (
          <span className={`uvDelta ${delta >= 0 ? "uvDeltaGood" : "uvDeltaBad"}`}>
            {delta >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
            {fmtPct(Math.abs(delta))}
          </span>
        )}
        <span>{caption}</span>
      </div>
    </div>
  );
}

function RankedList({ items, emptyText, color }: { items: KommoRankedItem[]; emptyText: string; color?: string }) {
  if (items.length === 0) return <p className="uvEmpty">{emptyText}</p>;
  const max = items[0].count || 1;
  return (
    <ul className="uvBarList uvBarListStatic">
      {items.slice(0, 8).map((item) => (
        <li key={item.label} className="uvBarListRow">
          <span className="uvBarListName">{item.label}</span>
          <span className="uvBarListTrack">
            <span className="uvInlineBar" style={{ width: `${Math.max((item.count / max) * 100, 2)}%`, background: color ?? "var(--uv-accent)" }} />
          </span>
          <span className="uvBarListValue">
            {fmtInt(item.count)} · {fmtPct(item.share, 0)}
          </span>
        </li>
      ))}
    </ul>
  );
}

function Sources({ subdomain }: { subdomain: string | null }) {
  const sources = [
    { name: "Kommo CRM", on: true, detail: subdomain ? `${subdomain}.kommo.com` : "Conectado", feeds: "Leads, funil, origem, segmento e perdas" },
    { name: "Nomus ERP", on: false, detail: "Não conectado", feeds: "Faturamento, pedidos, ticket e produtos vendidos" },
    { name: "Google Ads e Meta Ads", on: false, detail: "Não ligados a este painel", feeds: "Investimento, CPL, CAC e ROAS" },
  ];
  return (
    <div className="uvSources" aria-label="Fontes de dados">
      {sources.map((source) => (
        <div key={source.name} className={`uvSource ${source.on ? "uvSourceOn" : ""}`}>
          <span className="uvSourceState">
            {source.on ? <CheckCircle2 size={14} /> : <CircleDashed size={14} />}
            {source.detail}
          </span>
          <strong>{source.name}</strong>
          <span>{source.feeds}</span>
        </div>
      ))}
    </div>
  );
}

export function KommoDashboardBody({ data, subdomain }: { data: KommoDashboard; subdomain: string | null }) {
  const [hoverBucket, setHoverBucket] = useState<number | null>(null);
  const { totals } = data;
  const delta = totals.leads_previous ? (totals.leads - totals.leads_previous) / totals.leads_previous : null;
  const dimension = (key: string) => data.dimensions.find((d) => d.key === key);
  const uf = dimension("uf");
  const lossField = dimension("motivo_perda");
  const mapValues = useMemo(() => new Map((uf?.items ?? []).map((item) => [item.label.toUpperCase(), item.count])), [uf]);
  // Motivo de perda nativo do Kommo quando existir; senão, o campo personalizado.
  const losses = data.loss_reasons.length > 0 ? data.loss_reasons : lossField?.items ?? [];
  const mainPipeline = data.pipelines[0];
  const stageMax = Math.max(...(mainPipeline?.stages.map((s) => s.count) ?? [0]), 1);
  const periodCaption = data.period_days === 0 ? "em todo o histórico" : `nos últimos ${data.period_days} dias`;

  return (
    <>
      <Sources subdomain={subdomain} />

      <div className="uvKpiRow">
        <Tile label="Leads criados" value={fmtInt(totals.leads)} delta={delta} caption={data.period_days === 0 ? `${fmtInt(totals.leads_all_time)} na conta` : "vs. período anterior"} />
        <Tile label="Em atendimento" value={fmtInt(totals.open)} caption={totals.open_value > 0 ? `${fmtBRL(totals.open_value)} em valor informado` : "sem valor informado nos negócios"} />
        <Tile label="Vendas ganhas" value={fmtInt(totals.won)} caption={totals.won > 0 ? fmtBRL(totals.won_value) : "nenhum negócio marcado como ganho"} />
        <Tile label="Vendas perdidas" value={fmtInt(totals.lost)} caption={totals.leads > 0 ? `${fmtPct(totals.lost / totals.leads)} dos leads do período` : "sem leads no período"} />
        <Tile label="Com visita agendada" value={fmtInt(totals.with_visit)} caption="campo de data de visita preenchido" />
      </div>

      {totals.leads === 0 ? (
        <div className="uvNotice">
          <h4>Nenhum lead criado {periodCaption}</h4>
          <p>
            O último lead da conta foi criado em {formatDateTime(totals.last_lead_at)}. Escolha "Todo o histórico" para ver a base completa.
          </p>
        </div>
      ) : (
        <>
          <div className="uvRow uvRow-7-5">
            <section className="uvCard">
              <div className="uvCardHeader">
                <div>
                  <h3 className="uvCardTitle">Leads criados no tempo</h3>
                  <p className="uvCardSubtitle">Data de criação do negócio no Kommo, {periodCaption}</p>
                </div>
              </div>
              <StackedColumns
                data={data.timeline.map((bucket) => ({ label: bucket.label, rangeLabel: bucket.range_label, values: [bucket.leads] }))}
                series={[{ label: "Leads criados", color: "var(--uv-accent)" }]}
                height={240}
                format={fmtInt}
                axisFormat={fmtInt}
                hoverIndex={hoverBucket}
                onHover={setHoverBucket}
                ariaLabel="Leads criados por intervalo"
              />
            </section>

            <section className="uvCard">
              <div className="uvCardHeader">
                <div>
                  <h3 className="uvCardTitle">{mainPipeline ? mainPipeline.name : "Funil"}</h3>
                  <p className="uvCardSubtitle">Etapa em que cada lead do período está agora</p>
                </div>
              </div>
              {mainPipeline ? (
                <ol className="uvFunnel">
                  {mainPipeline.stages.map((stage) => (
                    <li key={stage.id} className="uvFunnelRow">
                      <div className="uvFunnelLabel">
                        <strong>{stage.name}</strong>
                        <span>{stage.kind === "won" ? "ganho" : stage.kind === "lost" ? "perdido" : "em aberto"}</span>
                      </div>
                      <div className="uvFunnelBarCell">
                        <span
                          className="uvInlineBar"
                          style={{
                            width: `${stage.count > 0 ? Math.max((stage.count / stageMax) * 100, 2) : 0}%`,
                            background: stage.kind === "lost" ? "var(--uv-critical)" : "var(--uv-accent)",
                          }}
                        />
                        <span className="uvFunnelCount">{fmtInt(stage.count)}</span>
                      </div>
                      <div className="uvFunnelCost">{fmtPct(stage.count / totals.leads, 0)}</div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="uvEmpty">Nenhum funil com leads neste período.</p>
              )}
              {data.pipelines.length > 1 && (
                <p className="uvChartNote">
                  Outros funis com leads: {data.pipelines.slice(1).map((p) => `${p.name} (${fmtInt(p.leads)})`).join(", ")}.
                </p>
              )}
            </section>
          </div>

          <div className="uvRow uvRow-7-5">
            <section className="uvCard">
              <div className="uvCardHeader">
                <div>
                  <h3 className="uvCardTitle">Leads por estado</h3>
                  <p className="uvCardSubtitle">
                    Campo UF preenchido em {fmtInt(uf?.filled ?? 0)} de {fmtInt(totals.leads)} leads
                  </p>
                </div>
              </div>
              {uf && uf.filled > 0 ? (
                <BrazilMap
                  values={mapValues}
                  selected={null}
                  onSelect={() => undefined}
                  legendFormat={fmtInt}
                  ariaLabel="Mapa do Brasil por leads com UF informada"
                  renderTooltip={(code) => (
                    <>
                      <div className="uvTooltipTitle">{code}</div>
                      <div className="uvTooltipRow"><span /><span>Leads</span><strong>{fmtInt(mapValues.get(code) ?? 0)}</strong></div>
                    </>
                  )}
                />
              ) : (
                <p className="uvEmpty">Nenhum lead do período tem o campo UF preenchido no Kommo.</p>
              )}
            </section>

            <section className="uvCard">
              <div className="uvCardHeader">
                <div>
                  <h3 className="uvCardTitle">Qualidade do cadastro</h3>
                  <p className="uvCardSubtitle">Quanto de cada campo está preenchido nos leads do período</p>
                </div>
              </div>
              <div>
                {data.quality.map((field) => {
                  const rate = field.total > 0 ? field.filled / field.total : 0;
                  return (
                    <div key={field.key} className="uvQualityRow">
                      <strong>{field.label}</strong>
                      <span className="uvBarListTrack">
                        <span
                          className="uvInlineBar"
                          style={{ width: `${field.filled > 0 ? Math.max(rate * 100, 2) : 0}%`, background: rate < 0.25 ? "var(--uv-warning)" : "var(--uv-accent)" }}
                        />
                      </span>
                      <span>
                        {fmtPct(rate, 0)} · {fmtInt(field.filled)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>

          <div className="uvCreativeGrid">
            {RANKED_DIMENSIONS.map((key) => {
              const dim = dimension(key);
              if (!dim) return null;
              return (
                <section key={key} className="uvCard">
                  <div className="uvCardHeader">
                    <div>
                      <h3 className="uvCardTitle">{dim.label}</h3>
                      <p className="uvCardSubtitle">
                        Preenchido em {fmtInt(dim.filled)} de {fmtInt(dim.total)} leads
                      </p>
                    </div>
                  </div>
                  <RankedList items={dim.items} emptyText="Campo vazio em todos os leads do período." />
                </section>
              );
            })}
            <section className="uvCard">
              <div className="uvCardHeader">
                <div>
                  <h3 className="uvCardTitle">Motivos de perda</h3>
                  <p className="uvCardSubtitle">{fmtInt(totals.lost)} negócios perdidos no período</p>
                </div>
              </div>
              <RankedList items={losses} color="var(--uv-critical)" emptyText="Nenhuma perda com motivo registrado no período." />
            </section>
          </div>
        </>
      )}
    </>
  );
}

export function KommoRealDashboard({ organizationId, canSync }: { organizationId: string; canSync: boolean }) {
  const [days, setDays] = useState(0);
  const query = useKommoDashboard(organizationId, days);
  const sync = useSyncKommoDashboard();
  const response = query.data;
  const syncError = sync.error instanceof Error ? sync.error.message : null;

  const syncButton = canSync && response?.configured && (
    <button type="button" className="uvBtnPrimary" disabled={sync.isPending} onClick={() => sync.mutate({ organizationId, days })}>
      <RefreshCw size={14} className={sync.isPending ? "uvSpin" : undefined} />
      {sync.isPending ? "Lendo o Kommo..." : "Sincronizar agora"}
    </button>
  );

  return (
    <div className="uvScope">
      <div className="uvPanelHeader">
        <div>
          <h2 className="uvPanelTitle">Painel de dados reais</h2>
          <p className="uvPanelSubtitle">
            {response?.fetched_at
              ? `Lido do Kommo em ${formatDateTime(response.fetched_at)}. Sem estimativa: o que não tem fonte conectada aparece como ausente.`
              : "Números lidos diretamente do Kommo CRM, sem dados demonstrativos."}
          </p>
        </div>
        <div className="uvControlGroup">
          {response?.dashboard && <PeriodSegmented value={days} onChange={setDays} />}
          {syncButton}
        </div>
      </div>

      {syncError && (
        <div className="uvNotice uvNoticeError" role="alert">
          <h4><AlertTriangle size={15} /> Não foi possível sincronizar</h4>
          <p>{syncError}</p>
        </div>
      )}

      {query.isLoading ? (
        <>
          <div className="uvSkeleton" style={{ height: 78 }} />
          <div className="uvSkeleton" style={{ height: 110 }} />
          <div className="uvSkeleton" style={{ height: 300 }} />
        </>
      ) : query.error ? (
        <div className="uvNotice uvNoticeError" role="alert">
          <h4>Não foi possível carregar o painel</h4>
          <p>{query.error instanceof Error ? query.error.message : "Erro inesperado."}</p>
        </div>
      ) : !response?.configured ? (
        <div className="uvNotice">
          <h4>Kommo ainda não conectado</h4>
          <p>
            Para este painel funcionar, salve o subdomínio e o token de longa duração do Kommo em Configurações, aba Integrações, para este cliente.
            Depois volte aqui e sincronize.
          </p>
        </div>
      ) : !response.dashboard ? (
        <div className="uvNotice">
          <h4>Conectado, falta a primeira leitura</h4>
          <p>
            {canSync
              ? "A conta está conectada, mas os leads ainda não foram lidos. Use Sincronizar agora: a leitura não altera nada no Kommo."
              : "A conta está conectada, mas os leads ainda não foram lidos. Peça ao time da EverGreen para fazer a primeira sincronização."}
          </p>
        </div>
      ) : (
        <KommoDashboardBody data={response.dashboard} subdomain={response.subdomain} />
      )}
    </div>
  );
}
