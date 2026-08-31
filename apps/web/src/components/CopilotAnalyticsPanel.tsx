import { useMemo, useState } from "react";
import { Activity, Clock, Coins, Gauge } from "lucide-react";

import { useCopilotUsage } from "../hooks/useBiomaApi";
import { TrendChart, type TrendPoint } from "./bi/TrendChart";
import { EmptyState, SectionHeader } from "./shared";

const WINDOW_OPTIONS = [7, 30, 90] as const;

function formatUsd(cents: number) {
  return `US$ ${(cents / 100).toFixed(2)}`;
}

function formatDuration(ms: number) {
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Consumo do copiloto: execuções e custo por dia, e de onde vieram (provedor,
 * modelo, cota da assinatura ou chave de API). Estilo painel de uso de
 * assistente de IDE (Claude Code / Codex) — leitura real de `copilot_runs`,
 * nunca estimativa.
 */
export function CopilotAnalyticsPanel() {
  const [days, setDays] = useState<(typeof WINDOW_OPTIONS)[number]>(30);
  const { data: usage, error } = useCopilotUsage(days);

  const runsTrend = useMemo<TrendPoint[]>(
    () => usage?.daily.map((point) => ({ label: point.day.slice(5), value: point.runs })) ?? [],
    [usage],
  );
  const costTrend = useMemo<TrendPoint[]>(
    () => usage?.daily.map((point) => ({ label: point.day.slice(5), value: point.cost_cents / 100 })) ?? [],
    [usage],
  );
  const byProvider = useMemo(
    () => [...(usage?.by_provider ?? [])].sort((a, b) => b.runs - a.runs),
    [usage],
  );

  return (
    <div className="operations-layout">
      {error && <div className="notice error">{error.message}</div>}

      <div className="panel-heading compact">
        <div>
          <p className="eyebrow">Copiloto</p>
          <h2>Consumo e custo</h2>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {WINDOW_OPTIONS.map((option) => (
            <button
              key={option}
              type="button"
              className={option === days ? "primary-button" : "secondary-button"}
              onClick={() => setDays(option)}
            >
              {option}d
            </button>
          ))}
        </div>
      </div>

      <div className="bento-grid">
        <article className="bento-card">
          <div className="bento-header"><h3>Execuções</h3><Activity size={16} /></div>
          <div className="bento-value">{usage?.runs ?? 0}</div>
          <div className="bento-footer">
            {usage?.routed_runs ?? 0} na cota da assinatura · {usage?.failed_runs ?? 0} falha(s)
          </div>
        </article>
        <article className="bento-card">
          <div className="bento-header"><h3>Custo real</h3><Coins size={16} /></div>
          <div className="bento-value" style={{ color: "var(--mint)" }}>{formatUsd(usage?.cost_cents ?? 0)}</div>
          <div className="bento-footer">
            {usage?.runs_without_cost ?? 0} execução(ões) sem preço na tabela
          </div>
        </article>
        <article className="bento-card">
          <div className="bento-header"><h3>Tempo médio</h3><Clock size={16} /></div>
          <div className="bento-value">{formatDuration(usage?.avg_duration_ms ?? 0)}</div>
          <div className="bento-footer">Por execução, nesta janela.</div>
        </article>
        <article className="bento-card">
          <div className="bento-header"><h3>Prévia local</h3><Gauge size={16} /></div>
          <div className="bento-value">{usage?.preview_runs ?? 0}</div>
          <div className="bento-footer">Sem chave configurada — zero token gasto.</div>
        </article>
      </div>

      <div className="operations-grid" style={{ gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
        <article className="surface">
          <SectionHeader eyebrow="Volume" title="Execuções por dia" icon={Activity} />
          {runsTrend.length > 0
            ? <TrendChart data={runsTrend} name="Execuções" />
            : <EmptyState compact text="Sem execução nesta janela." />}
        </article>
        <article className="surface">
          <SectionHeader eyebrow="Gasto" title="Custo por dia (US$)" icon={Coins} />
          {costTrend.length > 0
            ? <TrendChart data={costTrend} name="Custo (US$)" />
            : <EmptyState compact text="Sem custo registrado nesta janela." />}
        </article>
      </div>

      <article className="surface">
        <SectionHeader eyebrow="Origem" title="Por provedor e modelo" icon={Gauge} />
        <div className="hub-block-list">
          {byProvider.length === 0 && <EmptyState compact text="Sem execução nesta janela." />}
          {byProvider.map((item) => (
            <div className="work-row" key={`${item.provider}:${item.model}`}>
              <Activity size={16} />
              <div>
                <strong>{item.provider} · {item.model}</strong>
                <small>
                  {item.runs} execução(ões){item.routed_runs > 0 ? ` · ${item.routed_runs} na cota da assinatura` : ""}
                </small>
              </div>
              <div className="row-tail">
                <span className="status-pill">{formatUsd(item.cost_cents)}</span>
              </div>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}
