import React, { useState } from "react";
import { ChevronDown, ChevronUp, Eye, Sparkles, Calendar, Check, Copy } from "lucide-react";
import type { PostIdea, BrandDna } from "../data/malleable-mock";

interface CarouselCardProps {
  idea: PostIdea;
  index: number;
  brand: BrandDna;
  onOpenCarousel: (idea: PostIdea) => void;
  onSchedulePost: (idea: PostIdea) => void;
  onUpdateIdea: (updated: PostIdea) => void;
}

export const CarouselCard: React.FC<CarouselCardProps> = ({
  idea,
  index,
  brand,
  onOpenCarousel,
  onSchedulePost,
  onUpdateIdea,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [caption, setCaption] = useState(idea.suggestedCaption);
  const [writtenIdea, setWrittenIdea] = useState(idea.writtenIdea);
  const [slidesCount, setSlidesCount] = useState(idea.slidesCount);
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState(0);
  const [copied, setCopied] = useState(false);
  const [isRendering, setIsRendering] = useState(false);

  const handleCopyCaption = () => {
    navigator.clipboard.writeText(caption);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRenderCarousel = () => {
    setIsRendering(true);
    setTimeout(() => {
      setIsRendering(false);
      onUpdateIdea({
        ...idea,
        status: "rendered",
        slidesCount,
        suggestedCaption: caption,
        writtenIdea,
      });
      onOpenCarousel(idea);
    }, 1000);
  };

  return (
    <div className="craft-idea-card">
      {/* Top Header Strip */}
      <div className="craft-idea-header">
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="craft-btn craft-btn-icon"
            style={{ width: "30px", height: "30px" }}
            title={isExpanded ? "Recolher card" : "Expandir card"}
          >
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          <span className="craft-idea-number">{index + 1}</span>
          <span style={{ fontWeight: 800, fontSize: "1.05rem" }}>{idea.title}</span>
          <span
            style={{
              fontSize: "0.75rem",
              background: "var(--craft-paper)",
              padding: "3px 8px",
              border: "1px solid var(--craft-ink)",
              borderRadius: "2px",
              fontFamily: "var(--craft-font-mono)",
            }}
          >
            {idea.category}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {idea.status === "rendered" && (
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: 800,
                color: "var(--craft-orange)",
                background: "var(--craft-orange-light)",
                padding: "3px 10px",
                border: "1px solid var(--craft-orange)",
                borderRadius: "2px",
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <Check size={12} /> RENDERIZADO
            </span>
          )}
          {idea.status === "scheduled" && (
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: 800,
                color: "#059669",
                background: "#ecfdf5",
                padding: "3px 10px",
                border: "1px solid #059669",
                borderRadius: "2px",
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <Calendar size={12} /> AGENDADO
            </span>
          )}
        </div>
      </div>

      {/* 3 Columns Section (idêntico à ref RoboNuggets) */}
      {isExpanded && (
        <div className="craft-idea-columns">
          {/* Column 1: VISUAL IDEA */}
          <div className="craft-idea-col">
            <div className="craft-col-tag">VISUAL IDEA</div>
            <div className="craft-preview-box" onClick={() => onOpenCarousel(idea)}>
              <img
                src={idea.visualIdea.previewImage}
                alt={idea.title}
                loading="lazy"
              />
              <div
                style={{
                  position: "absolute",
                  bottom: "8px",
                  right: "8px",
                  background: "var(--craft-ink)",
                  color: "#fff",
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: "2px",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <Eye size={12} /> Ver lâminas
              </div>
            </div>
            <div style={{ fontSize: "0.82rem", color: "var(--craft-ink-muted)", lineHeight: 1.4 }}>
              {idea.visualIdea.concept}
            </div>
          </div>

          {/* Column 2: WRITTEN IDEA & SUGGESTED CAPTION */}
          <div className="craft-idea-col">
            <div>
              <div className="craft-col-tag" style={{ marginBottom: "6px" }}>WRITTEN IDEA</div>
              <textarea
                value={writtenIdea}
                onChange={(e) => setWrittenIdea(e.target.value)}
                rows={3}
                style={{
                  width: "100%",
                  fontFamily: "var(--craft-font-sans)",
                  fontSize: "0.88rem",
                  padding: "10px",
                  background: "var(--craft-paper)",
                  border: "var(--craft-border)",
                  borderRadius: "2px",
                  color: "var(--craft-ink)",
                  resize: "vertical",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "6px",
                }}
              >
                <div className="craft-col-tag">SUGGESTED CAPTION</div>
                <button
                  onClick={handleCopyCaption}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--craft-ink-muted)",
                    cursor: "pointer",
                    fontSize: "0.75rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                    fontWeight: 700,
                  }}
                >
                  {copied ? <Check size={12} color="green" /> : <Copy size={12} />}
                  {copied ? "Copiado!" : "Copiar"}
                </button>
              </div>

              <textarea
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                rows={6}
                style={{
                  width: "100%",
                  flex: 1,
                  fontFamily: "var(--craft-font-sans)",
                  fontSize: "0.85rem",
                  padding: "10px",
                  background: "var(--craft-paper)",
                  border: "var(--craft-border)",
                  borderRadius: "2px",
                  color: "var(--craft-ink)",
                  resize: "vertical",
                  lineHeight: 1.5,
                  boxSizing: "border-box",
                }}
              />
            </div>
          </div>

          {/* Column 3: PHOTOS TRAY & RENDER CAROUSEL */}
          <div className="craft-idea-col" style={{ justifyContent: "space-between" }}>
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "8px",
                }}
              >
                <div className="craft-col-tag">PHOTOS</div>
                <span
                  style={{
                    fontSize: "0.72rem",
                    fontFamily: "var(--craft-font-mono)",
                    color: "var(--craft-ink-muted)",
                  }}
                >
                  {brand.productPhotos.length} fotos da marca
                </span>
              </div>

              {/* Product Photos Grid */}
              <div className="craft-asset-tray">
                {brand.productPhotos.slice(0, 6).map((photo, pIdx) => (
                  <div
                    key={photo.id}
                    className={`craft-asset-thumb ${selectedPhotoIndex === pIdx ? "selected" : ""}`}
                    onClick={() => setSelectedPhotoIndex(pIdx)}
                    title={photo.title}
                  >
                    <img src={photo.url} alt={photo.title} />
                    <span className="craft-asset-index">{pIdx + 1}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Slide Count Slider & Actions */}
            <div style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
              <div className="craft-slider-group">
                <span style={{ fontSize: "0.8rem", fontWeight: 800 }}>SLIDES:</span>
                <input
                  type="range"
                  min={1}
                  max={7}
                  value={slidesCount}
                  onChange={(e) => setSlidesCount(Number(e.target.value))}
                  className="craft-slider-track"
                />
                <span className="craft-slider-val">{slidesCount}</span>
              </div>

              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  className="craft-btn craft-btn-primary"
                  onClick={handleRenderCarousel}
                  disabled={isRendering}
                  style={{ flex: 1, padding: "12px" }}
                >
                  <Sparkles size={16} />
                  {isRendering ? "Renderizando lâminas..." : "Render carousel"}
                </button>

                <button
                  className="craft-btn"
                  onClick={() => onSchedulePost(idea)}
                  title="Agendar post no Instagram / Blotato"
                >
                  <Calendar size={16} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
