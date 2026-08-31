import { useState } from "react";
import {
  Bot,
  Coins,
  Cpu,
  DollarSign,
  Play,
  Rocket,
  ShieldAlert,
  Sparkles,
  Target,
  TrendingUp,
  Zap,
} from "lucide-react";
import { EmptyState, SectionHeader } from "../components/shared";
import {
  useRunSquad,
  useSquadExecutions,
  useSquadFinOps,
  useSquads,
} from "../hooks/useBiomaApi";
import type { PilarType, SquadExecutionSummary } from "../lib/api";

const PILLAR_SQUAD_PRESETS: Array<{
  pilar: PilarType;
  slug: string;
  name: string;
  badge: string;
  description: string;
  icon: typeof Target;
  agents: string[];
}> = [
  {
    pilar: "oferta",
    slug: "squad_oferta_master",
    name: "Squad Especialista em Oferta Irresistível",
    badge: "Pilar Oferta",
    description: "Analisa a proposta de valor, o mecanismo único, os bônus acumulados e a garantia para criar a oferta perfeita.",
    icon: Target,
    agents: ["Oferta Copywriter", "Pricing Strategist", "Offer Auditor"],
  },
  {
    pilar: "demanda",
    slug: "squad_demanda_growth",
    name: "Squad de Mídia Paga & Distribution",
    badge: "Pilar Demanda",
    description: "Estrutura campanhas CBO no Meta Ads e Google Ads, variando ganchos de anúncio para tráfego qualificado.",
    icon: TrendingUp,
    agents: ["Paid Media Manager", "Growth Hacker", "Creative Director"],
  },
  {
    pilar: "conversao",
    slug: "squad_conversao_sales",
    name: "Squad de Sales Closer & WhatsApp Follow-up",
    badge: "Pilar Conversão",
    description: "Cria scripts de fechamento consultivo, contorna objeções de preço e programa sequências via WhatsApp.",
    icon: Zap,
    agents: ["Sales Closer", "Kommo CRM Architect", "WhatsApp Bot Scriptwriter"],
  },
];

function formatNumber(val: number) {
  return new Intl.NumberFormat("pt-BR").format(val);
}

function formatCents(cents: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(cents / 100);
}

export function SquadsView({ workspaceId }: { workspaceId: string }) {
  const { data: finops, isLoading: loadingFinops } = useSquadFinOps(workspaceId);
  const { data: executions } = useSquadExecutions(workspaceId);
  const runSquadMutation = useRunSquad();

  const [activeExecution, setActiveExecution] = useState<SquadExecutionSummary | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  function handleRunSquad(preset: (typeof PILLAR_SQUAD_PRESETS)[0]) {
    setFeedback(null);
    runSquadMutation.mutate(
      {
        workspaceId,
        payload: {
          pilar: preset.pilar,
          squad_slug: preset.slug,
          squad_name: preset.name,
          input_data: { context: "Disparo via Cockpit Bioma EG" },
        },
      },
      {
        onSuccess: (res) => {
          setActiveExecution(res);
          setFeedback({
            type: "success",
            text: `Squad '${res.squad_name}' executado em modo ${res.generation_mode}. Custo est.: ${formatCents(res.estimated_cost_cents)}.`,
          });
        },
        onError: (err) => {
          setFeedback({ type: "error", text: err.message || "Erro ao disparar squad." });
        },
      }
    );
  }

  return (
    <section className="analytics-layout" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div className="analytics-header">
        <div>
          <h2>Agentes Autônomos nos 3 Pilares EG</h2>
          <p>Orquestração de múltiplos agentes de IA por pilar comercial com controle de custos e tokens em tempo real.</p>
        </div>
      </div>

      {feedback && (
        <div className={`notice ${feedback.type === "error" ? "error" : "success"}`}>
          {feedback.text}
        </div>
      )}

      {/* Cards de Métricas FinOps */}
      <div className="metrics analytics-metrics" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        <article className="metric-card analytics-card">
          <span><Coins size={16} /> Total de Tokens IA</span>
          <strong>{formatNumber(finops?.total_tokens ?? 0)}</strong>
          <small>Prompt + Completion</small>
        </article>

        <article className="metric-card analytics-card">
          <span><DollarSign size={16} /> Custo Estimado (FinOps)</span>
          <strong>{formatCents(finops?.total_cost_cents ?? 0)}</strong>
          <small>Consumo consolidado</small>
        </article>

        <article className="metric-card analytics-card">
          <span><Cpu size={16} /> Total de Execuções</span>
          <strong>{formatNumber(finops?.total_executions ?? 0)}</strong>
          <small>Pipelines de agentes</small>
        </article>

        <article className="metric-card analytics-card">
          <span><Sparkles size={16} /> Tokens de Prompt</span>
          <strong>{formatNumber(finops?.prompt_tokens ?? 0)}</strong>
          <small>Contexto alimentado</small>
        </article>
      </div>

      {/* Squads por Pilar (Oferta, Demanda, Conversão) */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
        {PILLAR_SQUAD_PRESETS.map((preset) => {
          const Icon = preset.icon;
          const isRunning = runSquadMutation.isPending && runSquadMutation.variables?.payload.squad_slug === preset.slug;

          return (
            <article key={preset.slug} className="surface" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Icon size={22} color="var(--brand-accent)" />
                  <h4 style={{ margin: 0, fontSize: "16px" }}>{preset.name}</h4>
                </div>
                <span className="demo-badge">{preset.badge}</span>
              </div>

              <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: "1.5" }}>
                {preset.description}
              </p>

              <div>
                <strong style={{ fontSize: "12px", color: "var(--text-main)" }}>Agentes Integrados no Squad:</strong>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "6px" }}>
                  {preset.agents.map((ag) => (
                    <span
                      key={ag}
                      style={{
                        fontSize: "11px",
                        background: "var(--bg-elevated)",
                        border: "1px solid var(--border-light)",
                        padding: "3px 8px",
                        borderRadius: "4px",
                      }}
                    >
                      🤖 {ag}
                    </span>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: "auto", paddingTop: "12px", borderTop: "1px solid var(--border-light)", display: "flex", justifyContent: "flex-end" }}>
                <button
                  className="primary-button"
                  type="button"
                  onClick={() => handleRunSquad(preset)}
                  disabled={runSquadMutation.isPending}
                >
                  {isRunning ? <Bot size={15} className="spin" /> : <Play size={15} />}
                  {isRunning ? "Executando Squad..." : `Executar Squad de ${preset.pilar.toUpperCase()}`}
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {/* Resultado da Última Execução */}
      {activeExecution && (
        <article className="surface" style={{ background: "linear-gradient(135deg, var(--surface) 0%, rgba(58, 201, 123, 0.05) 100%)" }}>
          <SectionHeader
            eyebrow={`Execução ${activeExecution.generation_mode.toUpperCase()}: ${activeExecution.pilar.toUpperCase()}`}
            title={activeExecution.squad_name}
            icon={Rocket}
          />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "20px", marginTop: "16px" }}>
            {/* Log de Passos dos Agentes */}
            <div style={{ background: "var(--surface)", padding: "16px", borderRadius: "6px", border: "1px solid var(--border-light)" }}>
              <h5 style={{ margin: "0 0 12px 0", fontSize: "14px" }}>Logs do Orchestrator</h5>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "300px", overflowY: "auto" }}>
                {activeExecution.execution_logs.map((log, idx) => (
                  <div key={idx} style={{ fontSize: "12px" }}>
                    <span style={{ color: "var(--brand-accent)", fontWeight: 600 }}>[{log.agent}]</span>
                    <p style={{ margin: "2px 0 0 0", color: "var(--text-muted)" }}>{log.message}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Output do Deliverable */}
            <div style={{ background: "var(--surface)", padding: "16px", borderRadius: "6px", border: "1px solid var(--border-light)" }}>
              <h5 style={{ margin: "0 0 12px 0", fontSize: "14px" }}>Entregável Gerado pelo Squad</h5>
              <pre
                style={{
                  fontSize: "12px",
                  background: "var(--bg-elevated)",
                  padding: "12px",
                  borderRadius: "4px",
                  overflowX: "auto",
                  color: "var(--text-main)",
                  whiteSpace: "pre-wrap",
                }}
              >
                {JSON.stringify(activeExecution.output_data, null, 2)}
              </pre>
            </div>
          </div>
        </article>
      )}

      {/* Histórico Recente de Execuções */}
      <article className="surface">
        <SectionHeader eyebrow="Audit Trail & FinOps" title="Histórico Recente de Execuções" icon={ShieldAlert} />
        {!executions || executions.length === 0 ? (
          <EmptyState compact text="Nenhuma execução de squad registrada para este workspace." />
        ) : (
          <div className="table-list" style={{ marginTop: "12px" }}>
            {executions.map((item) => (
              <div className="table-row" key={item.id}>
                <strong>{item.squad_name}</strong>
                <span>Pilar {item.pilar.toUpperCase()}</span>
                <span>{item.token_usage.total_tokens} tokens</span>
                <span>{formatCents(item.estimated_cost_cents)}</span>
                <span>{new Date(item.started_at).toLocaleString("pt-BR")}</span>
                <span className={`status-badge status-${item.status}`}>{item.status}</span>
              </div>
            ))}
          </div>
        )}
      </article>
    </section>
  );
}
