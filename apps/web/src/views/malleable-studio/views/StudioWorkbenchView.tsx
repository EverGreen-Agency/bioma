import React, { useState } from "react";
import { Sparkles, Plus, Sliders, Filter } from "lucide-react";
import type { PostIdea, BrandDna } from "../data/malleable-mock";
import { CarouselCard } from "../components/CarouselCard";

interface StudioWorkbenchViewProps {
  brand: BrandDna;
  ideas: PostIdea[];
  onOpenCarousel: (idea: PostIdea) => void;
  onSchedulePost: (idea: PostIdea) => void;
  onUpdateIdea: (updated: PostIdea) => void;
  onAddNewIdea: (promptText: string, ideasCount: number) => void;
}

export const StudioWorkbenchView: React.FC<StudioWorkbenchViewProps> = ({
  brand,
  ideas,
  onOpenCarousel,
  onSchedulePost,
  onUpdateIdea,
  onAddNewIdea,
}) => {
  const [promptInput, setPromptInput] = useState("");
  const [ideasCountSelect, setIdeasCountSelect] = useState(3);
  const [isGenerating, setIsGenerating] = useState(false);
  const [filterCategory, setFilterCategory] = useState("TODOS");

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptInput.trim() && ideas.length > 0) return;

    setIsGenerating(true);
    setTimeout(() => {
      onAddNewIdea(promptInput || "Lançamento de produto sazonal focado em benefícios", ideasCountSelect);
      setPromptInput("");
      setIsGenerating(false);
    }, 1200);
  };

  const filteredIdeas = filterCategory === "TODOS"
    ? ideas
    : ideas.filter((item) => item.category === filterCategory);

  const categories = ["TODOS", ...Array.from(new Set(ideas.map((i) => i.category)))];

  return (
    <div className="craft-workbench-grid">
      {/* Top Prompt Generation Bar */}
      <form onSubmit={handleGenerate} className="craft-prompt-bar">
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              fontFamily: "var(--craft-font-mono)",
              fontWeight: 900,
              fontSize: "0.8rem",
              background: "var(--craft-orange)",
              color: "#fff",
              padding: "4px 8px",
              borderRadius: "2px",
            }}
          >
            THE THINKER
          </span>
        </div>

        <input
          type="text"
          placeholder={`Sobre o que devem ser os posts para ${brand.name}? (ex: lançamento de verão, comparativo com refrigerante tradicional, quiz de personalidade)...`}
          value={promptInput}
          onChange={(e) => setPromptInput(e.target.value)}
          className="craft-prompt-input"
        />

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <select
            value={ideasCountSelect}
            onChange={(e) => setIdeasCountSelect(Number(e.target.value))}
            style={{
              fontFamily: "var(--craft-font-mono)",
              fontSize: "0.85rem",
              padding: "10px 12px",
              background: "var(--craft-paper)",
              border: "var(--craft-border)",
              borderRadius: "2px",
              color: "var(--craft-ink)",
              cursor: "pointer",
            }}
          >
            <option value={1}>1 Ideia</option>
            <option value={3}>3 Ideias</option>
            <option value={5}>5 Ideias</option>
          </select>

          <button
            type="submit"
            className="craft-btn craft-btn-primary"
            disabled={isGenerating}
            style={{ padding: "10px 20px" }}
          >
            <Sparkles size={16} />
            {isGenerating ? "Pensando ângulos..." : "Gerar Ideias de Carrossel"}
          </button>
        </div>
      </form>

      {/* Filter and Metrics Row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Filter size={15} color="var(--craft-ink-muted)" />
          <span style={{ fontSize: "0.8rem", fontWeight: 800, color: "var(--craft-ink-muted)" }}>CATEGORIAS:</span>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className="craft-btn"
              style={{
                padding: "4px 10px",
                fontSize: "0.78rem",
                background: filterCategory === cat ? "var(--craft-ink)" : "var(--craft-paper-card)",
                color: filterCategory === cat ? "var(--craft-paper)" : "var(--craft-ink)",
              }}
            >
              {cat}
            </button>
          ))}
        </div>

        <div style={{ fontSize: "0.85rem", fontFamily: "var(--craft-font-mono)", color: "var(--craft-ink-muted)" }}>
          {filteredIdeas.length} IDEIAS PRONTAS PARA RENDERIZAÇÃO
        </div>
      </div>

      {/* Ideas Cards Stack */}
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {filteredIdeas.map((idea, index) => (
          <CarouselCard
            key={idea.id}
            idea={idea}
            index={index}
            brand={brand}
            onOpenCarousel={onOpenCarousel}
            onSchedulePost={onSchedulePost}
            onUpdateIdea={onUpdateIdea}
          />
        ))}
      </div>
    </div>
  );
};
