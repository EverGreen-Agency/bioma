import { useMemo, useState } from "react";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, CheckCircle2, CircleDashed, RefreshCw } from "lucide-react";
import type { KommoDashboard, KommoRankedItem } from "../lib/api";
import { useKommoDashboard, useSyncKommoDashboard } from "../hooks/api";
import { fmtBRL, fmtInt, fmtPct } from "../data/univet/univetPortalData";
import { BRAZIL_STATES } from "../data/univet/brazilStatesGeo";
import { BrazilMap, StackedColumns, TERRITORY_COLORS, toUfCode } from "../views/univet/UnivetCharts";
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
// Representante tem tabela própria junto do mapa.
const RANKED_DIMENSIONS = ["origem", "segmento", "produto", "solicitacao", "tipo_atendimento"];

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

function Sources({ subdomain, nomusConfigured }: { subdomain: string | null; nomusConfigured?: boolean }) {
  const sources = [
    { name: "Kommo CRM", on: true, detail: subdomain ? `${subdomain}.kommo.com` : "Conectado", feeds: "Leads, funil, origem, segmento e perdas" },
    {
      name: "Nomus ERP",
      on: Boolean(nomusConfigured),
      detail: nomusConfigured ? "Conectado via REST" : "Não conectado",
      feeds: "Faturamento, pedidos, ticket e produtos vendidos",
    },
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

type GeoLayer = "leads" | "reps";

const GEO_LAYERS: { id: GeoLayer; label: string }[] = [
  { id: "leads", label: "Leads" },
  { id: "reps", label: "Representantes" },
];

function CardTitle({ title, subtitle, children }: { title: string; subtitle: string; children?: React.ReactNode }) {
  return (
    <div className="uvCardHeader">
      <div>
        <h3 className="uvCardTitle">{title}</h3>
        <p className="uvCardSubtitle">{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

/** Soma por sigla de UF, aceitando o campo do Kommo em qualquer formato ("SP", "São Paulo"...). */
function countByUf(items: { label: string; count: number }[]) {
  const result = new Map<string, number>();
  items.forEach((item) => {
    const code = toUfCode(item.label);
    if (code) result.set(code, (result.get(code) ?? 0) + item.count);
  });
  return result;
}

function GeographyCard({ data }: { data: KommoDashboard }) {
  const [layer, setLayer] = useState<GeoLayer>("leads");
  const [selected, setSelected] = useState<string | null>(null);
  const { totals } = data;
  const uf = data.dimensions.find((d) => d.key === "uf");
  const leadsByUf = useMemo(() => countByUf(uf?.items ?? []), [uf]);

  // Território de cada representante: os estados dos leads atribuídos a ele no Kommo.
  // Quando dois disputam a mesma UF, fica com quem tem mais leads lá.
  const reps = useMemo(
    () =>
      data.reps.map((rep, index) => ({
        ...rep,
        color: TERRITORY_COLORS[index % TERRITORY_COLORS.length],
        byUf: countByUf(rep.ufs),
      })),
    [data.reps],
  );
  const territories = useMemo(() => {
    const owner = new Map<string, { color: string; count: number; label: string }>();
    reps.forEach((rep) =>
      rep.byUf.forEach((count, code) => {
        const current = owner.get(code);
        if (!current || count > current.count) owner.set(code, { color: rep.color, count, label: rep.label });
      }),
    );
    return {
      owner,
      colorOf: new Map(Array.from(owner, ([code, item]) => [code, item.color])),
      legend: reps.map((rep) => ({ label: rep.label, color: rep.color })),
    };
  }, [reps]);

  const ranking = useMemo(() => Array.from(leadsByUf).sort((a, b) => b[1] - a[1]).slice(0, 8), [leadsByUf]);
  const rankingMax = ranking[0]?.[1] ?? 1;
  const stateName = (code: string) => BRAZIL_STATES.find((s) => s.uf === code)?.name ?? code;
  const repsInSelected = selected ? reps.filter((rep) => rep.byUf.has(selected)) : [];

  return (
    <section className="uvCard">
      <CardTitle
        title="Brasil por estado"
        subtitle={
          layer === "leads"
            ? `Campo UF preenchido em ${fmtInt(uf?.filled ?? 0)} de ${fmtInt(totals.leads)} leads`
            : `Campo de representante preenchido em ${fmtInt(totals.leads - totals.without_rep)} de ${fmtInt(totals.leads)} leads`
        }
      >
        <div className="uvSegmented" role="group" aria-label="Camada do mapa">
          {GEO_LAYERS.map((option) => (
            <button key={option.id} type="button" className="uvSegmentedBtn" aria-pressed={layer === option.id} onClick={() => setLayer(option.id)}>
              {option.label}
            </button>
          ))}
        </div>
      </CardTitle>

      <div className="uvGeo">
        <BrazilMap
          values={leadsByUf}
          selected={selected}
          onSelect={setSelected}
          legendFormat={fmtInt}
          territories={layer === "reps" && reps.length > 0 ? territories : undefined}
          ariaLabel={layer === "leads" ? "Mapa do Brasil por leads com UF informada" : "Mapa do Brasil por território de representante"}
          renderTooltip={(code) => {
            const owner = territories.owner.get(code);
            return (
              <>
                <div className="uvTooltipTitle">{stateName(code)}</div>
                <div className="uvTooltipRow"><span /><span>Leads</span><strong>{fmtInt(leadsByUf.get(code) ?? 0)}</strong></div>
                <div className="uvTooltipRow"><span /><span>Representante</span><strong>{owner?.label ?? "Sem representante"}</strong></div>
              </>
            );
          }}
        />

        <div className="uvGeoSide">
          {selected ? (
            <div className="uvStateDetail">
              <div className="uvStateDetailHead">
                <div>
                  <h4>{stateName(selected)}</h4>
                  <span className={repsInSelected.length ? "" : "uvTextWarn"}>
                    {repsInSelected.length ? `Representante: ${repsInSelected.map((rep) => rep.label).join(", ")}` : "Nenhum lead daqui com representante"}
                  </span>
                </div>
                <button type="button" className="uvBtnGhost" onClick={() => setSelected(null)}>Ver Brasil</button>
              </div>
              <dl className="uvStatGrid">
                <div><dt>Leads no período</dt><dd>{fmtInt(leadsByUf.get(selected) ?? 0)}</dd></div>
                <div><dt>Participação</dt><dd>{uf?.filled ? fmtPct((leadsByUf.get(selected) ?? 0) / uf.filled, 0) : "n/d"}</dd></div>
              </dl>
            </div>
          ) : layer === "leads" ? (
            ranking.length === 0 ? (
              <div className="uvGeoEmpty">
                <strong>Mapa pronto, sem lead com estado ainda</strong>
                <p>Cada estado se pinta conforme os leads chegam com o campo UF preenchido no Kommo. O formulário do site e o atendimento devem gravar a UF já na entrada.</p>
              </div>
            ) : (
              <>
                <div className="uvSideTitle">Estados com mais leads</div>
                <ul className="uvBarList">
                  {ranking.map(([code, count]) => (
                    <li key={code}>
                      <button type="button" className="uvBarListRow" onClick={() => setSelected(code)}>
                        <span className="uvBarListName">{stateName(code)}</span>
                        <span className="uvBarListTrack">
                          <span className="uvInlineBar" style={{ width: `${Math.max((count / rankingMax) * 100, 2)}%`, background: "var(--uv-accent)" }} />
                        </span>
                        <span className="uvBarListValue">{fmtInt(count)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )
          ) : reps.length === 0 ? (
            <div className="uvGeoEmpty">
              <strong>Território dos representantes ainda vazio</strong>
              <p>
                O território sai dos próprios leads: cada lead com "Região/Representante indicado" e UF preenchidos pinta o estado com a cor do
                representante. A lista oficial de representantes ainda está sendo confirmada com a Univet.
              </p>
            </div>
          ) : (
            <>
              <div className="uvSideTitle">Estados atendidos por representante</div>
              <ul className="uvRepKeys">
                {reps.map((rep) => (
                  <li key={rep.label}>
                    <i style={{ background: rep.color }} aria-hidden="true" />
                    <strong>{rep.label}</strong>
                    <span>{Array.from(rep.byUf.keys()).join(", ") || "sem UF nos leads"}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      {reps.length > 0 && (
        <div className="uvTableWrap">
          <table className="uvTable">
            <thead>
              <tr>
                <th>Representante</th>
                <th>Estados</th>
                <th className="uvNum">Leads</th>
                <th className="uvNum">Em aberto</th>
                <th className="uvNum">Parados +{data.stale_after_days}d</th>
                <th className="uvNum">Ganhos</th>
                <th className="uvNum">Valor ganho</th>
                <th className="uvNum">Perdidos</th>
              </tr>
            </thead>
            <tbody>
              {reps.map((rep) => (
                <tr key={rep.label} className={selected && rep.byUf.has(selected) ? "uvRowActive" : ""}>
                  <td><strong>{rep.label}</strong></td>
                  <td>{Array.from(rep.byUf.keys()).join(", ") || "n/d"}</td>
                  <td className="uvNum">{fmtInt(rep.leads)}</td>
                  <td className="uvNum">{fmtInt(rep.open)}</td>
                  <td className={`uvNum ${rep.stale_open > 0 ? "uvTextWarn" : ""}`}>{fmtInt(rep.stale_open)}</td>
                  <td className="uvNum">{fmtInt(rep.won)}</td>
                  <td className="uvNum"><strong>{rep.won_value > 0 ? fmtBRL(rep.won_value) : "n/d"}</strong></td>
                  <td className="uvNum">{fmtInt(rep.lost)}</td>
                </tr>
              ))}
              <tr className="uvRowMuted">
                <td><strong>Sem representante</strong></td>
                <td>Campo vazio no Kommo</td>
                <td className="uvNum">{fmtInt(totals.without_rep)}</td>
                <td className="uvNum" colSpan={5} />
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function KommoDashboardBody({ data, subdomain }: { data: KommoDashboard; subdomain: string | null }) {
  const [hoverBucket, setHoverBucket] = useState<number | null>(null);
  const { totals } = data;
  const nomus = data.nomus;
  const delta = totals.leads_previous ? (totals.leads - totals.leads_previous) / totals.leads_previous : null;
  const dimension = (key: string) => data.dimensions.find((d) => d.key === key);
  const lossField = dimension("motivo_perda");
  // Motivo de perda nativo do Kommo quando existir; senão, o campo personalizado.
  const losses = data.loss_reasons.length > 0 ? data.loss_reasons : lossField?.items ?? [];
  const mainPipeline = data.pipelines[0];
  const stageMax = Math.max(...(mainPipeline?.stages.map((s) => s.count) ?? [0]), 1);
  const periodCaption = data.period_days === 0 ? "em todo o histórico" : `nos últimos ${data.period_days} dias`;
  const noLeads = totals.leads === 0;

  return (
    <>
      <Sources subdomain={subdomain} nomusConfigured={Boolean(nomus?.configured)} />

      <div className="uvKpiRow">
        <Tile label="Leads criados" value={fmtInt(totals.leads)} delta={delta} caption={data.period_days === 0 ? `${fmtInt(totals.leads_all_time)} na conta` : "vs. período anterior"} />
        <Tile
          label="Em atendimento"
          value={fmtInt(totals.open)}
          caption={
            totals.stale_open > 0
              ? `${fmtInt(totals.stale_open)} sem movimento há mais de ${data.stale_after_days} dias`
              : totals.open_value > 0
                ? `${fmtBRL(totals.open_value)} em valor informado`
                : "nenhum parado no momento"
          }
        />
        <Tile label="Vendas ganhas (CRM)" value={fmtInt(totals.won)} caption={totals.won > 0 ? fmtBRL(totals.won_value) : "nenhum negócio marcado como ganho"} />
        <Tile label="Vendas perdidas" value={fmtInt(totals.lost)} caption={totals.leads > 0 ? `${fmtPct(totals.lost / totals.leads)} dos leads do período` : "sem leads no período"} />
        <Tile label="Com visita agendada" value={fmtInt(totals.with_visit)} caption="campo de data de visita preenchido" />
      </div>

      {nomus && nomus.configured && (
        <div className="uvKpiRow" style={{ marginTop: 12 }}>
          <Tile
            label="Faturamento Real (Nomus ERP)"
            value={fmtBRL(nomus.faturamento_total)}
            caption={`${fmtInt(nomus.pedidos_count)} pedidos faturados emitidos`}
          />
          <Tile
            label="Ticket Médio Faturado"
            value={fmtBRL(nomus.ticket_medio)}
            caption="Média real por pedido no Nomus"
          />
          <Tile
            label="Consultores Ativos (ERP)"
            value={fmtInt(nomus.representantes_count)}
            caption="Vendedores e representantes com faturamento"
          />
          <Tile
            label="Conversão Global ERP"
            value={totals.leads > 0 ? fmtPct(nomus.pedidos_count / totals.leads, 1) : "n/d"}
            caption="Pedidos Nomus / Leads Kommo"
          />
        </div>
      )}

      {noLeads && (
        <div className="uvNotice">
          {totals.leads_all_time === 0 ? (
            <>
              <h4>Pronto para receber os primeiros leads</h4>
              <p>A base do Kommo foi zerada para recomeçar com a captação nova. Funil, mapa e rankings abaixo se preenchem sozinhos conforme os leads entram.</p>
            </>
          ) : (
            <>
              <h4>Nenhum lead criado {periodCaption}</h4>
              <p>O último lead da conta entrou em {formatDateTime(totals.last_lead_at)}. Escolha "Todo o histórico" para ver a base completa.</p>
            </>
          )}
        </div>
      )}

      <div className="uvRow uvRow-7-5">
        <section className="uvCard">
          <CardTitle title="Leads criados no tempo" subtitle={`Data de criação do negócio no Kommo, ${periodCaption}`} />
          {noLeads ? (
            <p className="uvEmpty uvEmptyFill">A linha do tempo começa no primeiro lead criado.</p>
          ) : (
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
          )}
        </section>

        <section className="uvCard">
          <CardTitle title={mainPipeline ? mainPipeline.name : "Funil"} subtitle="Etapa em que cada lead do período está agora" />
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
                  <div className="uvFunnelCost">{totals.leads > 0 ? fmtPct(stage.count / totals.leads, 0) : "n/d"}</div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="uvEmpty">Nenhum funil encontrado na conta.</p>
          )}
          {data.pipelines.length > 1 && (
            <p className="uvChartNote">
              Outros funis com leads: {data.pipelines.slice(1).map((p) => `${p.name} (${fmtInt(p.leads)})`).join(", ")}.
            </p>
          )}
        </section>
      </div>

      <GeographyCard data={data} />

      {nomus && nomus.reps && nomus.reps.length > 0 && (
        <section className="uvCard" style={{ marginTop: 16 }}>
          <CardTitle
            title="Vendas por Consultor & Representante (Nomus ERP)"
            subtitle="Faturamento e pedidos oficiais emitidos na Univet"
          />
          <div className="uvTableWrap">
            <table className="uvTable">
              <thead>
                <tr>
                  <th>Consultor / Representante</th>
                  <th className="uvNum">Pedidos</th>
                  <th className="uvNum">Faturamento Faturado</th>
                  <th className="uvNum">Participação</th>
                </tr>
              </thead>
              <tbody>
                {nomus.reps.map((rep) => (
                  <tr key={rep.label}>
                    <td><strong>{rep.label}</strong></td>
                    <td className="uvNum">{fmtInt(rep.pedidos)}</td>
                    <td className="uvNum"><strong>{fmtBRL(rep.faturamento)}</strong></td>
                    <td className="uvNum">{fmtPct(rep.share, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {nomus && nomus.top_products && nomus.top_products.length > 0 && (
        <section className="uvCard" style={{ marginTop: 16 }}>
          <CardTitle
            title="Mix de Faturamento & Produtos (Nomus ERP)"
            subtitle="Itens e produtos mais faturados no sistema de gestão"
          />
          <ul className="uvBarList uvBarListStatic">
            {nomus.top_products.slice(0, 8).map((item) => {
              const maxUnits = nomus.top_products[0]?.quantidade || 1;
              return (
                <li key={item.label} className="uvBarListRow">
                  <span className="uvBarListName">{item.label}</span>
                  <span className="uvBarListTrack">
                    <span
                      className="uvInlineBar"
                      style={{
                        width: `${Math.max((item.quantidade / maxUnits) * 100, 3)}%`,
                        background: "var(--uv-series-2)",
                      }}
                    />
                  </span>
                  <span className="uvBarListValue">
                    {fmtInt(item.quantidade)} un. {item.valor_estimado > 0 ? `· ${fmtBRL(item.valor_estimado)}` : ""}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <div className="uvRow uvRow-7-5">
        <section className="uvCard">
          <CardTitle title="Qualidade do cadastro" subtitle="Quanto de cada campo está preenchido nos leads do período" />
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
                  <span>{field.total > 0 ? `${fmtPct(rate, 0)} · ${fmtInt(field.filled)}` : "n/d"}</span>
                </div>
              );
            })}
          </div>
        </section>

        <section className="uvCard">
          <CardTitle title="Motivos de perda" subtitle={`${fmtInt(totals.lost)} negócios perdidos no período`} />
          <RankedList items={losses} color="var(--uv-critical)" emptyText="Nenhuma perda com motivo registrado no período." />
        </section>
      </div>

      <div className="uvCreativeGrid">
        {RANKED_DIMENSIONS.map((key) => {
          const dim = dimension(key);
          if (!dim) return null;
          return (
            <section key={key} className="uvCard">
              <CardTitle title={dim.label} subtitle={`Preenchido em ${fmtInt(dim.filled)} de ${fmtInt(dim.total)} leads`} />
              <RankedList items={dim.items} emptyText={noLeads ? "Aparece com os primeiros leads." : "Campo vazio em todos os leads do período."} />
            </section>
          );
        })}
      </div>
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
