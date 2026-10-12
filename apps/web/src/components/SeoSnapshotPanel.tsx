import React, { useCallback, useEffect, useState } from "react";
import { RefreshCw, Search } from "lucide-react";

import { api, SeoSnapshotState } from "../lib/api";


export function SeoSnapshotPanel({ workspaceId, canCollect }: { workspaceId: string; canCollect: boolean }) {
  const [state, setState] = useState<SeoSnapshotState | null>(null);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setState(await api.seoSnapshot(workspaceId));
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar SEO.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => { void load(); }, [load]);

  const collect = async () => {
    setCollecting(true);
    try {
      setState(await api.collectSeoSnapshot(workspaceId));
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao coletar SEO.");
    } finally {
      setCollecting(false);
    }
  };

  const latest = state?.latest;
  const organic = latest?.organic ?? {};
  const top10 = (organic.pos_1 ?? 0) + (organic.pos_2_3 ?? 0) + (organic.pos_4_10 ?? 0);
  const card: React.CSSProperties = { background: "rgba(255,255,255,.04)", border: "1px solid rgba(255,255,255,.09)", borderRadius: 10, padding: 16 };

  return (
    <article style={{ ...card, marginTop: 24 }}>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}><Search size={18} /><strong>SEO interno</strong></div>
          <p style={{ margin: "6px 0 0", opacity: .7, fontSize: 13 }}>Snapshot manual e imutável do DataForSEO · Brasil · português</p>
        </div>
        {canCollect && <button className="mini-button" type="button" disabled={collecting} onClick={collect}>
          <RefreshCw size={14} /> {collecting ? "Coletando…" : "Coletar agora"}
        </button>}
      </header>

      {error && <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: "rgba(245,158,11,.12)", color: "#FCD34D" }}>{error}</div>}
      {loading && <p style={{ opacity: .65 }}>Carregando snapshot…</p>}
      {!loading && !latest && !error && <div style={{ marginTop: 16, padding: 18, textAlign: "center", opacity: .72 }}>
        Ainda não há dados de SEO para este workspace. A coleta acontece somente quando um administrador solicita.
      </div>}
      {!loading && latest && !latest.has_data && <div style={{ marginTop: 16, padding: 18, textAlign: "center", opacity: .72 }}>
        O DataForSEO respondeu com sucesso, mas não encontrou métricas para <strong>{latest.target}</strong>.
      </div>}
      {!loading && latest?.has_data && <>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10, marginTop: 16 }}>
          <Metric label="Palavras ranqueadas" value={organic.count ?? 0} />
          <Metric label="Posições 1–10" value={top10} />
          <Metric label="Tráfego estimado" value={Math.round(organic.etv ?? 0)} />
          <Metric label="Valor estimado (USD)" value={(organic.estimated_paid_traffic_cost ?? 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} />
        </div>
        <p style={{ margin: "12px 0 0", opacity: .62, fontSize: 12 }}>
          {latest.target} · medido em {new Date(latest.measured_at).toLocaleString("pt-BR")} · tarefa {latest.source_task_id ?? "sem id"}
        </p>
      </>}
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div style={{ background: "rgba(9,35,27,.55)", borderRadius: 8, padding: 12 }}>
    <div style={{ opacity: .65, fontSize: 12 }}>{label}</div>
    <div style={{ fontSize: 22, fontWeight: 700, marginTop: 4 }}>{value}</div>
  </div>;
}
