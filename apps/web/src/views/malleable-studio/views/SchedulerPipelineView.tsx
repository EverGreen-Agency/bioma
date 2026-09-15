import React from "react";
import { Calendar, CheckCircle2, Clock, Instagram, Send, Sparkles } from "lucide-react";
import type { PostIdea, BrandDna } from "../data/malleable-mock";

interface SchedulerPipelineViewProps {
  brand: BrandDna;
  ideas: PostIdea[];
  onOpenCarousel: (idea: PostIdea) => void;
}

export const SchedulerPipelineView: React.FC<SchedulerPipelineViewProps> = ({
  brand,
  ideas,
  onOpenCarousel,
}) => {
  const scheduledIdeas = ideas.filter(
    (i) => i.status === "scheduled" || i.status === "rendered",
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Banner */}
      <div className="craft-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Calendar size={20} color="var(--craft-orange)" />
            <h2 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 900 }}>
              PUBLISHER PIPELINE · INTEGRAÇÃO BLOTATO / INSTAGRAM
            </h2>
          </div>
          <div style={{ fontSize: "0.85rem", color: "var(--craft-ink-muted)", marginTop: "4px" }}>
            The Publisher despacha diretamente os carrosséis aprovados para a API do Instagram sem necessidade de exportação manual.
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "var(--craft-paper)",
              padding: "6px 12px",
              border: "var(--craft-border)",
              borderRadius: "2px",
              fontFamily: "var(--craft-font-mono)",
              fontSize: "0.8rem",
            }}
          >
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#059669" }} />
            CONECTADO AO INSTAGRAM
          </div>
        </div>
      </div>

      {/* Grid of Scheduled Posts */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "20px" }}>
        {scheduledIdeas.map((idea, idx) => (
          <div key={idea.id} className="craft-card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <span
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 800,
                    color: "#059669",
                    background: "#ecfdf5",
                    padding: "2px 8px",
                    borderRadius: "2px",
                    border: "1px solid #059669",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <CheckCircle2 size={12} /> PRONTO PARA PUBLICAÇÃO
                </span>

                <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.8rem", fontFamily: "var(--craft-font-mono)" }}>
                  <Instagram size={14} color="#e1306c" />
                  <span>Feed</span>
                </div>
              </div>

              <div
                style={{
                  width: "100%",
                  aspectRatio: "16/9",
                  borderRadius: "2px",
                  overflow: "hidden",
                  border: "1px solid var(--craft-ink-faint)",
                  marginBottom: "12px",
                }}
              >
                <img
                  src={idea.visualIdea.previewImage}
                  alt={idea.title}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              </div>

              <h4 style={{ margin: "0 0 6px 0", fontSize: "1.05rem", fontWeight: 900 }}>
                {idea.title}
              </h4>
              <div style={{ fontSize: "0.8rem", color: "var(--craft-orange)", fontWeight: 700, marginBottom: "8px" }}>
                {idea.slidesCount} lâminas renderizadas
              </div>

              <p
                style={{
                  fontSize: "0.82rem",
                  color: "var(--craft-ink-muted)",
                  margin: 0,
                  display: "-webkit-box",
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: "vertical",
                  overflow: "hidden",
                  lineHeight: 1.4,
                }}
              >
                {idea.suggestedCaption}
              </p>
            </div>

            <div style={{ marginTop: "16px", borderTop: "1px solid var(--craft-ink-faint)", paddingTop: "12px", display: "flex", gap: "8px" }}>
              <button
                className="craft-btn craft-btn-primary"
                onClick={() => onOpenCarousel(idea)}
                style={{ flex: 1 }}
              >
                Inspecionar Lâminas
              </button>
              <button
                className="craft-btn craft-btn-orange"
                onClick={() => alert(`Post "${idea.title}" disparado para o Instagram via Blotato!`)}
                title="Disparar postagem imediata"
              >
                <Send size={14} /> Disparar Agora
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
