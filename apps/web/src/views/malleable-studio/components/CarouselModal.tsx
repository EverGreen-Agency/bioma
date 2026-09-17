import React, { useState } from "react";
import { X, ChevronLeft, ChevronRight, Calendar, Sparkles, Check, Share2 } from "lucide-react";
import type { PostIdea, BrandDna } from "../data/malleable-mock";

interface CarouselModalProps {
  idea: PostIdea;
  brand: BrandDna;
  onClose: () => void;
  onSchedule: (idea: PostIdea) => void;
}

export const CarouselModal: React.FC<CarouselModalProps> = ({
  idea,
  brand,
  onClose,
  onSchedule,
}) => {
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const slides = idea.slides.slice(0, idea.slidesCount);
  const currentSlide = slides[currentSlideIndex] || slides[0];

  const handlePrev = () => {
    setCurrentSlideIndex((prev) => (prev > 0 ? prev - 1 : slides.length - 1));
  };

  const handleNext = () => {
    setCurrentSlideIndex((prev) => (prev < slides.length - 1 ? prev + 1 : 0));
  };

  return (
    <div className="craft-modal-overlay" onClick={onClose}>
      <div
        className="craft-modal-dialog"
        style={{ maxWidth: "1000px" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Bar */}
        <div className="craft-modal-header">
          <div>
            <span
              style={{
                fontSize: "0.75rem",
                fontFamily: "var(--craft-font-mono)",
                color: "var(--craft-orange)",
                fontWeight: 800,
              }}
            >
              CAROUSEL PREVIEW · {brand.name.toUpperCase()}
            </span>
            <h3 style={{ margin: "4px 0 0 0", fontSize: "1.2rem", fontWeight: 900 }}>
              {idea.title}
            </h3>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              className="craft-btn craft-btn-primary"
              onClick={() => {
                onSchedule(idea);
                onClose();
              }}
            >
              <Calendar size={15} /> Agendar com Blotato
            </button>
            <button className="craft-btn craft-btn-icon" onClick={onClose}>
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="craft-modal-body" style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
          {/* Slide Visual Mockup (Esquerda) */}
          <div style={{ flex: "1 1 420px", display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div
              style={{
                width: "100%",
                maxWidth: "400px",
                aspectRatio: "4/5",
                backgroundColor: currentSlide?.backgroundColor || brand.palette.background,
                color: currentSlide?.textColor || brand.palette.text,
                border: "var(--craft-border)",
                boxShadow: "var(--craft-shadow)",
                borderRadius: "4px",
                padding: "28px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                position: "relative",
                overflow: "hidden",
                boxSizing: "border-box",
              }}
            >
              {/* Slide Number Tag */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontSize: "0.75rem",
                  fontWeight: 800,
                  opacity: 0.85,
                  letterSpacing: "0.05em",
                }}
              >
                <span>{brand.name}</span>
                <span>
                  {currentSlideIndex + 1} / {slides.length}
                </span>
              </div>

              {/* Photo Layer if Assigned */}
              {currentSlide?.assignedPhotoUrl && (
                <div
                  style={{
                    width: "100%",
                    height: "180px",
                    margin: "12px 0",
                    borderRadius: "3px",
                    overflow: "hidden",
                    border: "2px solid rgba(0,0,0,0.15)",
                  }}
                >
                  <img
                    src={currentSlide.assignedPhotoUrl}
                    alt="Product"
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                </div>
              )}

              {/* Slide Headline & Text */}
              <div>
                <h4
                  style={{
                    fontSize: "1.4rem",
                    fontWeight: 900,
                    lineHeight: 1.15,
                    margin: "0 0 10px 0",
                  }}
                >
                  {currentSlide?.headline}
                </h4>
                <p
                  style={{
                    fontSize: "0.92rem",
                    lineHeight: 1.45,
                    margin: 0,
                    opacity: 0.9,
                  }}
                >
                  {currentSlide?.body}
                </p>
              </div>

              {/* Bottom Brand Stripe */}
              <div
                style={{
                  fontSize: "0.7rem",
                  fontWeight: 700,
                  opacity: 0.7,
                  borderTop: "1px solid rgba(0,0,0,0.15)",
                  paddingTop: "8px",
                }}
              >
                {brand.tagline}
              </div>
            </div>

            {/* Slide Navigation Controls */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                marginTop: "16px",
              }}
            >
              <button
                className="craft-btn craft-btn-icon"
                onClick={handlePrev}
                title="Lâmina anterior"
              >
                <ChevronLeft size={18} />
              </button>

              <div style={{ display: "flex", gap: "6px" }}>
                {slides.map((_, idx) => (
                  <button
                    key={idx}
                    onClick={() => setCurrentSlideIndex(idx)}
                    style={{
                      width: "10px",
                      height: "10px",
                      borderRadius: "50%",
                      border: "1.5px solid var(--craft-ink)",
                      background:
                        currentSlideIndex === idx ? "var(--craft-orange)" : "transparent",
                      cursor: "pointer",
                      padding: 0,
                    }}
                  />
                ))}
              </div>

              <button
                className="craft-btn craft-btn-icon"
                onClick={handleNext}
                title="Próxima lâmina"
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>

          {/* Details & Copy (Direita) */}
          <div style={{ flex: "1 1 350px", display: "flex", flexDirection: "column", gap: "16px" }}>
            <div className="craft-card" style={{ padding: "16px" }}>
              <div className="craft-col-tag" style={{ marginBottom: "8px" }}>
                PROMPT DO DESIGNER (THE DESIGNER · FAL / GPT IMAGE)
              </div>
              <div
                style={{
                  fontSize: "0.85rem",
                  fontFamily: "var(--craft-font-mono)",
                  background: "var(--craft-paper)",
                  padding: "10px",
                  borderRadius: "2px",
                  border: "1px solid var(--craft-ink-faint)",
                  color: "var(--craft-ink)",
                }}
              >
                {currentSlide?.visualPrompt}
              </div>
            </div>

            <div className="craft-card" style={{ padding: "16px" }}>
              <div className="craft-col-tag" style={{ marginBottom: "8px" }}>
                LEGENDA FINAL SUGERIDA
              </div>
              <div
                style={{
                  fontSize: "0.88rem",
                  lineHeight: 1.5,
                  whiteSpace: "pre-line",
                  background: "var(--craft-paper)",
                  padding: "12px",
                  borderRadius: "2px",
                  border: "1px solid var(--craft-ink-faint)",
                  maxHeight: "180px",
                  overflowY: "auto",
                }}
              >
                {idea.suggestedCaption}
              </div>
            </div>

            <div className="craft-card" style={{ padding: "16px" }}>
              <div className="craft-col-tag" style={{ marginBottom: "8px" }}>
                METADADOS DO PUBLICADOR (THE PUBLISHER · BLOTATO)
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "0.82rem" }}>
                <div>
                  <span style={{ color: "var(--craft-ink-muted)" }}>Formato:</span>{" "}
                  <strong>Carrossel 4:5</strong>
                </div>
                <div>
                  <span style={{ color: "var(--craft-ink-muted)" }}>Lâminas:</span>{" "}
                  <strong>{slides.length} slides</strong>
                </div>
                <div>
                  <span style={{ color: "var(--craft-ink-muted)" }}>Canal:</span>{" "}
                  <strong>Instagram Feed</strong>
                </div>
                <div>
                  <span style={{ color: "var(--craft-ink-muted)" }}>Agendamento:</span>{" "}
                  <strong>Melhor horário IA</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
