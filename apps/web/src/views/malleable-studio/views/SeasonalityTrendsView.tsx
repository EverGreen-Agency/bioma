import React, { useState } from "react";
import { Calendar, Flame, Globe2, Sparkles, TrendingUp, AlertTriangle } from "lucide-react";
import type { SeasonalEvent, GlobalTrend, BrandDna } from "../data/malleable-mock";

interface SeasonalityTrendsViewProps {
  brand: BrandDna;
  seasonality: SeasonalEvent[];
  trends: GlobalTrend[];
  onAdaptTrend: (trend: GlobalTrend) => void;
  onAdaptSeasonality: (season: SeasonalEvent) => void;
}

export const SeasonalityTrendsView: React.FC<SeasonalityTrendsViewProps> = ({
  brand,
  seasonality,
  trends,
  onAdaptTrend,
  onAdaptSeasonality,
}) => {
  const [platformFilter, setPlatformFilter] = useState("TODAS");

  const filteredTrends = platformFilter === "TODAS"
    ? trends
    : trends.filter((t) => t.platform === platformFilter);

  const platforms = ["TODAS", "TikTok", "Instagram", "X / Twitter", "Reddit", "Google Trends"];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
      {/* Top Banner */}
      <div className="craft-card">
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
          <Globe2 size={20} color="var(--craft-orange)" />
          <h2 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 900 }}>
            SAZONALIDADE & TENDÊNCIAS GLOBAIS MULTI-PLATAFORMA
          </h2>
        </div>
        <p style={{ fontSize: "0.9rem", color: "var(--craft-ink-muted)", margin: 0, lineHeight: 1.5 }}>
          O Thinker cruza o ciclo de demanda da empresa com os picos de interesse globais na internet (TikTok, Reels, Reddit, X e Google). Converta movimentações culturais em carrosséis oportunos antes que a onda passe.
        </p>
      </div>

      {/* Section 1: Seasonality Calendar */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
          <Calendar size={18} color="var(--craft-orange)" />
          <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 800 }}>
            CALENDÁRIO DE SAZONALIDADE E PICOS COMERCIAIS
          </h3>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "16px" }}>
          {seasonality.map((season) => (
            <div key={season.id} className="craft-card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span
                    style={{
                      fontSize: "0.72rem",
                      fontWeight: 900,
                      fontFamily: "var(--craft-font-mono)",
                      background: season.impact === "CRÍTICO" ? "var(--craft-orange)" : "var(--craft-ink)",
                      color: "#fff",
                      padding: "2px 6px",
                      borderRadius: "2px",
                    }}
                  >
                    IMPACTO {season.impact}
                  </span>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--craft-ink-muted)" }}>
                    {season.category}
                  </span>
                </div>

                <h4 style={{ margin: "4px 0 8px 0", fontSize: "1.1rem", fontWeight: 900 }}>
                  {season.title}
                </h4>
                <div style={{ fontSize: "0.8rem", color: "var(--craft-orange)", fontWeight: 700, marginBottom: "8px" }}>
                  Período: {season.dateRange}
                </div>
                <p style={{ fontSize: "0.85rem", color: "var(--craft-ink-muted)", lineHeight: 1.45, margin: "0 0 12px 0" }}>
                  {season.description}
                </p>

                <div
                  style={{
                    background: "var(--craft-paper)",
                    padding: "10px",
                    borderRadius: "2px",
                    border: "1px solid var(--craft-ink-faint)",
                    fontSize: "0.82rem",
                    lineHeight: 1.4,
                  }}
                >
                  <strong style={{ color: "var(--craft-ink)" }}>Ângulo Recomendado:</strong>{" "}
                  {season.recommendedAngle}
                </div>
              </div>

              <div style={{ marginTop: "16px", borderTop: "1px solid var(--craft-ink-faint)", paddingTop: "12px" }}>
                <button
                  className="craft-btn craft-btn-primary"
                  onClick={() => onAdaptSeasonality(season)}
                  style={{ width: "100%" }}
                >
                  <Sparkles size={14} /> Gerar Carrossel para Esta Data
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 2: Global Internet Trends */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Flame size={18} color="var(--craft-orange)" />
            <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 800 }}>
              TRENDS VIRALIZANDO NA INTERNET (MULTI-PLATAFORMA)
            </h3>
          </div>

          <div style={{ display: "flex", gap: "6px" }}>
            {platforms.map((p) => (
              <button
                key={p}
                onClick={() => setPlatformFilter(p)}
                className="craft-btn"
                style={{
                  padding: "4px 10px",
                  fontSize: "0.75rem",
                  background: platformFilter === p ? "var(--craft-ink)" : "var(--craft-paper-card)",
                  color: platformFilter === p ? "var(--craft-paper)" : "var(--craft-ink)",
                }}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {filteredTrends.map((trend) => (
            <div key={trend.id} className="craft-card" style={{ padding: "18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px", marginBottom: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span
                    style={{
                      background: "var(--craft-ink)",
                      color: "var(--craft-paper)",
                      fontSize: "0.75rem",
                      fontWeight: 800,
                      padding: "3px 8px",
                      borderRadius: "2px",
                      fontFamily: "var(--craft-font-mono)",
                    }}
                  >
                    {trend.platform}
                  </span>
                  <h4 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 900 }}>
                    {trend.topic}
                  </h4>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 800,
                      color: "var(--craft-orange)",
                      background: "var(--craft-orange-light)",
                      padding: "2px 8px",
                      borderRadius: "2px",
                    }}
                  >
                    {trend.momentum}
                  </span>
                  <span style={{ fontSize: "0.75rem", fontFamily: "var(--craft-font-mono)", color: "var(--craft-ink-muted)" }}>
                    Vol: {trend.volume}
                  </span>
                </div>
              </div>

              <p style={{ fontSize: "0.88rem", color: "var(--craft-ink-muted)", margin: "0 0 12px 0", lineHeight: 1.45 }}>
                {trend.insight}
              </p>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  background: "var(--craft-paper)",
                  padding: "10px 14px",
                  borderRadius: "2px",
                  border: "1px solid var(--craft-ink-faint)",
                  flexWrap: "wrap",
                  gap: "12px",
                }}
              >
                <div style={{ fontSize: "0.85rem", flex: 1 }}>
                  <strong style={{ color: "var(--craft-orange)" }}>Gancho Viral Sugerido:</strong>{" "}
                  &ldquo;{trend.suggestedHook}&rdquo;
                </div>

                <button
                  className="craft-btn craft-btn-orange"
                  onClick={() => onAdaptTrend(trend)}
                  style={{ whiteSpace: "nowrap" }}
                >
                  <Sparkles size={14} /> Adaptar para {brand.name}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
