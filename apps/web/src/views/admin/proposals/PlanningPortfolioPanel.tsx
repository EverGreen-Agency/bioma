import { useEffect, useState } from "react";

import { api, type PlanningPortfolioItem } from "../../../lib/api";


export function PlanningPortfolioPanel() {
  const [items, setItems] = useState<PlanningPortfolioItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void api.planningPortfolio()
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Falha ao carregar planejamentos."));
  }, []);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div className="surface" style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr>{["Cliente", "Projeto", "Disciplina", "Intake", "Plano", "Geração", "Atualizado"].map((label) => <th key={label} style={{ padding: 12, textAlign: "left" }}>{label}</th>)}</tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.project_id} style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: 12 }}>{item.client_name}</td>
                <td style={{ padding: 12 }}><strong>{item.project_name}</strong><span style={{ display: "block", color: "var(--text-dim)", fontSize: "0.76rem" }}>{item.project_status}</span></td>
                <td style={{ padding: 12 }}>{item.project_type}</td>
                <td style={{ padding: 12 }}>{item.intake_schema_key ? `${item.intake_schema_key} · ${item.intake_status}` : "Não iniciada"}</td>
                <td style={{ padding: 12 }}>{item.plan_id ? `v${item.plan_version} · ${item.plan_status}` : "Não gerado"}</td>
                <td style={{ padding: 12 }}>{item.generation_mode ?? "—"}</td>
                <td style={{ padding: 12 }}>{new Date(item.updated_at).toLocaleDateString("pt-BR")}</td>
              </tr>
            ))}
            {!items.length && <tr><td colSpan={7} style={{ padding: 28, textAlign: "center", color: "var(--text-dim)" }}>Nenhum projeto com planejamento encontrado.</td></tr>}
          </tbody>
        </table>
      </div>
      {error && <p style={{ color: "#ef4444" }}>{error}</p>}
    </div>
  );
}
