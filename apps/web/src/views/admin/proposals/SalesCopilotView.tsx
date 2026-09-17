import { useEffect, useState } from "react";
import { Headphones, Sparkles } from "lucide-react";
import { api, type ProposalSummary } from "../../../lib/api";
import { SalesCopilotPanel } from "./SalesCopilotPanel";

export function SalesCopilotView() {
  const [proposals, setProposals] = useState<ProposalSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.listProposals()
      .then((data) => setProposals(data))
      .catch(() => setProposals([]))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div style={{ padding: "24px", maxWidth: "1280px", margin: "0 auto", color: "var(--text)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "10px", margin: 0 }}>
            <Headphones color="var(--brand-accent)" size={28} /> Copiloto de Vendas & Reuniões IA
          </h1>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: "0.9rem" }}>
            Assistência ao vivo para reuniões comerciais, transcrição automatizada, briefing preventivo e extração de compromissos.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "rgba(58, 201, 123, 0.1)", color: "var(--mint)", padding: "6px 14px", borderRadius: "20px", fontSize: "0.82rem", fontWeight: 600 }}>
          <Sparkles size={14} /> IA Ativa em Tempo Real
        </div>
      </div>

      {isLoading ? (
        <div className="surface" style={{ padding: "40px", textAlign: "center", color: "var(--text-dim)" }}>
          Carregando dados do Copiloto...
        </div>
      ) : (
        <SalesCopilotPanel proposals={proposals} />
      )}
    </div>
  );
}
