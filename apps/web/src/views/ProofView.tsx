import { useQuery } from "@tanstack/react-query";
import { Activity, Bug, Rocket, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";
import { EmptyState, SectionHeader } from "../components/shared";

function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes}min`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `${hours}h` : `${Math.floor(hours / 24)}d`;
}

/** Painel de prova — o que a EG entrega e o que ela mantém no ar.
 *
 * A diferença para o painel que inspirou este: **cada número tem origem**, e o
 * que não tem origem não aparece. Disponibilidade vem de um prober EXTERNO;
 * entregas e correções vêm dos registros que já existem. Nada é estimado.
 *
 * Interno por enquanto. Se virar público, o que muda é o gate — os números já
 * nascem verificáveis, que é a parte difícil. */
export function ProofView() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["proof-panel"], queryFn: api.proofPanel });

  if (isLoading) return <EmptyState text="Carregando o painel..." />;
  if (isError || !data) return <div className="notice error">Não foi possível carregar o painel.</div>;

  const window90 = data.uptime.find((item) => item.window_days === 90 && item.kind === "monitor");
  // Quantos dias de medição existem de fato. Publicar "90 dias" com 1 dia de
  // histórico é o erro que tira a credibilidade do painel inteiro.
  const measuredDays = window90?.measured_since
    ? Math.max(1, Math.round((Date.now() - new Date(window90.measured_since).getTime()) / 86400000))
    : 0;
  const matured = measuredDays >= 90;

  return (
    <section className="profile-grid">
      <SectionHeader
        eyebrow="Prova"
        title="A gente não promete. Registra."
        icon={ShieldCheck}
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16, gridColumn: "1 / -1" }}>
        <article className="surface" style={{ padding: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-muted)" }}>
            <Activity size={16} /> Disponibilidade
          </div>
          {window90 ? (
            <>
              <div style={{ fontSize: 34, fontWeight: 700, marginTop: 8 }}>
                {window90.availability.toFixed(2)}%
              </div>
              <div style={{ fontSize: 12, color: matured ? "var(--text-muted)" : "var(--amber)", marginTop: 4 }}>
                {matured
                  ? "últimos 90 dias · medido por prober externo"
                  : `medindo há ${measuredDays} dia${measuredDays > 1 ? "s" : ""} — ainda não são 90`}
              </div>
            </>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-faint)", marginTop: 10 }}>
              Sem medição ainda. O coletor grava assim que o prober externo
              estiver configurado — não estimamos este número.
            </div>
          )}
        </article>

        <article className="surface" style={{ padding: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-muted)" }}>
            <Bug size={16} /> Correções em aberto
          </div>
          <div style={{ fontSize: 34, fontWeight: 700, marginTop: 8, color: data.open_issues === 0 ? "var(--mint)" : "var(--amber)" }}>
            {data.open_issues}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
            {data.fixes.length > 0
              ? `última resolvida em ${formatMinutes(data.fixes[0].minutes_to_resolve)}`
              : "nenhuma resolvida ainda"}
          </div>
        </article>

        <article className="surface" style={{ padding: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-muted)" }}>
            <Rocket size={16} /> Entregas concluídas
          </div>
          <div style={{ fontSize: 34, fontWeight: 700, marginTop: 8 }}>{data.deliveries.length}</div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
            registradas em `deliverables`
          </div>
        </article>
      </div>

      {data.daily_uptime.length > 0 && (
        <article className="surface" style={{ gridColumn: "1 / -1", padding: 18 }}>
          <strong style={{ fontSize: 13.5 }}>Dia a dia</strong>
          <div style={{ display: "flex", gap: 3, marginTop: 12, flexWrap: "wrap" }}>
            {data.daily_uptime.map((point) => (
              <span
                key={point.date}
                title={`${point.date} · ${point.availability.toFixed(2)}%`}
                style={{
                  width: 12, height: 26, borderRadius: 2,
                  background: point.availability >= 99.9 ? "var(--mint)" : point.availability >= 95 ? "var(--amber)" : "var(--danger)",
                }}
              />
            ))}
          </div>
          <p style={{ fontSize: 11.5, color: "var(--text-faint)", margin: "10px 0 0" }}>
            Um quadrado por dia medido. A barra cresce com o histórico — não
            preenchemos os dias anteriores à primeira medição.
          </p>
        </article>
      )}

      <article className="surface" style={{ gridColumn: "1 / -1", padding: 18 }}>
        <strong style={{ fontSize: 13.5 }}>Linha de produção</strong>
        {data.deliveries.length === 0 ? (
          <p style={{ fontSize: 12.5, color: "var(--text-faint)", marginTop: 8 }}>
            Nenhuma entrega concluída registrada. Este painel lê `deliverables`
            — concluir entregas nos projetos alimenta esta lista sozinho.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 12 }}>
            {data.deliveries.slice(0, 12).map((delivery) => (
              <div
                key={delivery.id}
                style={{
                  display: "flex", justifyContent: "space-between", gap: 12,
                  padding: "9px 12px", background: "var(--bg-elevated)", borderRadius: 8,
                  border: "1px solid var(--border-light)", fontSize: 13,
                }}
              >
                <span>
                  <strong>{delivery.title}</strong>
                  {delivery.workspace_name && (
                    <span style={{ color: "var(--text-faint)", fontSize: 11.5 }}> · {delivery.workspace_name}</span>
                  )}
                </span>
                <span style={{ color: "var(--text-faint)", fontSize: 11.5, whiteSpace: "nowrap" }}>
                  {new Date(delivery.completed_at).toLocaleDateString("pt-BR")}
                </span>
              </div>
            ))}
          </div>
        )}
      </article>
    </section>
  );
}
