import React, { useState } from "react";
import { Radar, Users, Target, ArrowUpRight, Sparkles, TrendingUp, AlertCircle } from "lucide-react";
import type { CompetitorData, BrandDna } from "../data/malleable-mock";

interface CompetitorRadarViewProps {
  brand: BrandDna;
  competitors: CompetitorData[];
  onGenerateCounterPost: (competitorName: string, gapTopic: string) => void;
}

export const CompetitorRadarView: React.FC<CompetitorRadarViewProps> = ({
  brand,
  competitors,
  onGenerateCounterPost,
}) => {
  const [selectedCompetitorId, setSelectedCompetitorId] = useState(competitors[0]?.id);
  const activeCompetitor = competitors.find((c) => c.id === selectedCompetitorId) || competitors[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Explanation Banner */}
      <div className="craft-card" style={{ background: "var(--craft-paper-card)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
          <Radar size={20} color="var(--craft-orange)" />
          <h2 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 900 }}>
            SPY RADAR DE CONCORRENTES · {brand.name.toUpperCase()}
          </h2>
        </div>
        <p style={{ fontSize: "0.9rem", color: "var(--craft-ink-muted)", margin: 0, lineHeight: 1.5 }}>
          O sistema varre continuamente contas de concorrentes diretos para identificar quais formatos estão retendo atenção, quais ganchos estão viralizando e quais lacunas de conteúdo estão desatendidas para a sua marca dominar.
        </p>
      </div>

      {/* Main Grid: Competitor Selector & Detailed Teardown */}
      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: "24px" }}>
        {/* Left Column: Competitor Cards List */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="craft-col-tag">CONCORRENTES MONITORADOS</div>

          {competitors.map((comp) => {
            const isSelected = comp.id === selectedCompetitorId;
            return (
              <div
                key={comp.id}
                className="craft-card"
                onClick={() => setSelectedCompetitorId(comp.id)}
                style={{
                  cursor: "pointer",
                  borderColor: isSelected ? "var(--craft-orange)" : "var(--craft-ink)",
                  boxShadow: isSelected ? "var(--craft-shadow)" : "var(--craft-shadow-sm)",
                  background: isSelected ? "var(--craft-paper)" : "var(--craft-paper-card)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 900 }}>{comp.name}</h3>
                    <span style={{ fontSize: "0.78rem", color: "var(--craft-ink-muted)", fontFamily: "var(--craft-font-mono)" }}>
                      {comp.handle}
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: "0.78rem",
                      fontWeight: 800,
                      background: "var(--craft-ink)",
                      color: "var(--craft-paper)",
                      padding: "2px 6px",
                      borderRadius: "2px",
                      fontFamily: "var(--craft-font-mono)",
                    }}
                  >
                    {comp.followers}
                  </span>
                </div>

                <div style={{ marginTop: "14px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "0.8rem" }}>
                  <div>
                    <div style={{ color: "var(--craft-ink-muted)", fontSize: "0.7rem" }}>ENGAGEMENT:</div>
                    <div style={{ fontWeight: 800 }}>{comp.engagementRate}</div>
                  </div>
                  <div>
                    <div style={{ color: "var(--craft-ink-muted)", fontSize: "0.7rem" }}>FREQUÊNCIA:</div>
                    <div style={{ fontWeight: 800 }}>{comp.postingFrequency}</div>
                  </div>
                </div>
              </div>
            );
          })}

          <button className="craft-btn" style={{ marginTop: "8px" }}>
            <Users size={14} /> + Adicionar Novo Concorrente
          </button>
        </div>

        {/* Right Column: In-Depth Teardown & Content Gaps */}
        {activeCompetitor && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Winning Formats & Content Gaps */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
              {/* Winning Formats */}
              <div className="craft-card">
                <div className="craft-card-header">
                  <h3 className="craft-card-title">
                    <TrendingUp size={16} /> O Que Funciona Para Ele
                  </h3>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {activeCompetitor.winningFormats.map((fmt, fIdx) => (
                    <div
                      key={fIdx}
                      style={{
                        padding: "8px 12px",
                        background: "var(--craft-paper)",
                        border: "1px solid var(--craft-ink-faint)",
                        borderRadius: "2px",
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#059669" }} />
                      {fmt}
                    </div>
                  ))}
                </div>
              </div>

              {/* Content Gaps (Nossas Oportunidades) */}
              <div className="craft-card" style={{ borderColor: "var(--craft-orange)" }}>
                <div className="craft-card-header">
                  <h3 className="craft-card-title" style={{ color: "var(--craft-orange)" }}>
                    <Target size={16} /> Lacunas de Conteúdo (Gaps)
                  </h3>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {activeCompetitor.contentGaps.map((gap, gIdx) => (
                    <div
                      key={gIdx}
                      style={{
                        padding: "8px 12px",
                        background: "var(--craft-orange-light)",
                        border: "1px solid var(--craft-orange)",
                        borderRadius: "2px",
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        color: "var(--craft-ink)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span>{gap}</span>
                      <button
                        onClick={() => onGenerateCounterPost(activeCompetitor.name, gap)}
                        className="craft-btn craft-btn-orange"
                        style={{ padding: "4px 8px", fontSize: "0.72rem" }}
                        title="Gerar post aproveitando esta brecha"
                      >
                        <Sparkles size={11} /> Explorar Gap
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Top Post Teardown */}
            <div className="craft-card">
              <div className="craft-card-header">
                <div>
                  <div className="craft-col-tag" style={{ marginBottom: "4px" }}>POST DE MAIOR DESEMPENHO DO RIVAL</div>
                  <h3 className="craft-card-title">{activeCompetitor.topPost.title}</h3>
                </div>
                <span
                  style={{
                    background: "var(--craft-ink)",
                    color: "var(--craft-paper)",
                    fontSize: "0.75rem",
                    padding: "3px 8px",
                    borderRadius: "2px",
                    fontFamily: "var(--craft-font-mono)",
                  }}
                >
                  {activeCompetitor.topPost.metric}
                </span>
              </div>

              <div
                style={{
                  background: "var(--craft-paper)",
                  padding: "16px",
                  borderRadius: "2px",
                  border: "1px solid var(--craft-ink-faint)",
                  fontSize: "0.88rem",
                  lineHeight: 1.5,
                }}
              >
                <div style={{ fontWeight: 800, marginBottom: "6px" }}>
                  Formato: {activeCompetitor.topPost.format}
                </div>
                <p style={{ margin: "0 0 12px 0", color: "var(--craft-ink-muted)" }}>
                  {activeCompetitor.topPost.summary}
                </p>

                <div
                  style={{
                    borderTop: "1px dashed var(--craft-ink-faint)",
                    paddingTop: "12px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: "0.8rem", color: "var(--craft-orange)", fontWeight: 800 }}>
                    💡 Recomendação do Thinker: Criar versão com melhor gancho visual e mais dados concretos.
                  </span>
                  <button
                    className="craft-btn craft-btn-primary"
                    onClick={() => onGenerateCounterPost(activeCompetitor.name, activeCompetitor.topPost.title)}
                  >
                    <Sparkles size={14} /> Gerar Post Superior para {brand.name}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
