import React, { useState, useEffect } from "react";
import {
  Sun,
  Moon,
  Sparkles,
  Layers,
  Globe,
  Radar,
  Calendar,
  Eye,
  SlidersHorizontal,
  ChevronRight,
  Send,
  RotateCcw,
} from "lucide-react";
import "../../styles/malleable-studio.css";

import {
  POPPI_PRESET,
  UNIVET_PRESET,
  type MalleableClientPreset,
  type PostIdea,
  type BrandDna,
  type GlobalTrend,
  type SeasonalEvent,
} from "./data/malleable-mock";

import { StudioWorkbenchView } from "./views/StudioWorkbenchView";
import { BrandDnaView } from "./views/BrandDnaView";
import { CompetitorRadarView } from "./views/CompetitorRadarView";
import { SeasonalityTrendsView } from "./views/SeasonalityTrendsView";
import { ImageCloudView } from "./views/ImageCloudView";
import { SchedulerPipelineView } from "./views/SchedulerPipelineView";
import { CarouselModal } from "./components/CarouselModal";
import { TailorModal } from "./components/TailorModal";

export type StudioTabId =
  | "workbench"
  | "brand-dna"
  | "competitors"
  | "trends"
  | "cloud"
  | "scheduler";

export const MalleableStudioView: React.FC = () => {
  // Tema Light / Dark do design system CRAFT
  const [theme, setTheme] = useState<"light" | "dark">("light");

  // Marca ativa e dados maleáveis
  const [currentPreset, setCurrentPreset] = useState<MalleableClientPreset>(POPPI_PRESET);
  const [ideas, setIdeas] = useState<PostIdea[]>(POPPI_PRESET.ideas);

  // Tab ativa (as "várias paginações" para manter a estrutura)
  const [activeTab, setActiveTab] = useState<StudioTabId>("workbench");

  // Modais
  const [previewIdea, setPreviewIdea] = useState<PostIdea | null>(null);
  const [isTailorModalOpen, setIsTailorModalOpen] = useState(false);

  // Alternar preset (Tailor)
  const handleApplyPreset = (newPreset: MalleableClientPreset) => {
    setCurrentPreset(newPreset);
    setIdeas(newPreset.ideas);
  };

  // Toggle do tema
  const toggleTheme = () => {
    setTheme((t) => (t === "light" ? "dark" : "light"));
  };

  // Ação de agendar post
  const handleSchedulePost = (idea: PostIdea) => {
    setIdeas((prev) =>
      prev.map((i) => (i.id === idea.id ? { ...i, status: "scheduled" } : i)),
    );
  };

  // Atualizar ideia
  const handleUpdateIdea = (updated: PostIdea) => {
    setIdeas((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
  };

  // Gerar nova ideia no Workbench
  const handleAddNewIdea = (promptText: string, ideasCount: number) => {
    const brand = currentPreset.brand;
    const newItems: PostIdea[] = Array.from({ length: ideasCount }).map((_, idx) => ({
      id: `generated-${Date.now()}-${idx}`,
      title: `${promptText.slice(0, 30)} · Drop #${ideas.length + idx + 1}`,
      category: "Campanha Estratégica",
      visualIdea: {
        previewImage: brand.productPhotos[idx % brand.productPhotos.length]?.url || brand.productPhotos[0].url,
        concept: `Conceito visual calibrado para ${brand.name} explorando a paleta ${brand.palette.primary} com tipografia ${brand.typography.heading}.`,
      },
      writtenIdea: `Conceito criado pelo Thinker: ${promptText}. Focado no público de ${brand.name} com gatilhos de diferenciação e autoridade.`,
      suggestedCaption: `o novo drop de ${brand.name} chegou para transformar sua rotina ✨ ${promptText}. comente EU QUERO para receber o link exclusivo via DM! #brand #viral #carrossel`,
      hashtags: ["#novidade", `#${brand.id}`, "#carrossel", "#socialmedia"],
      productPhotoIds: [brand.productPhotos[0]?.id || "p1"],
      slidesCount: 4,
      status: "draft",
      slides: [
        {
          slideNumber: 1,
          headline: `Por que ${brand.name} é a escolha definitiva`,
          body: "Arraste para o lado e descubra em 4 lâminas o que muda a partir de hoje.",
          visualPrompt: `High contrast poster design with ${brand.palette.primary} background and product front and center.`,
          assignedPhotoUrl: brand.productPhotos[0]?.url,
          backgroundColor: brand.palette.primary,
          textColor: "#ffffff",
        },
        {
          slideNumber: 2,
          headline: "O problema que você aceitava em silêncio",
          body: "A maioria das soluções no mercado entrega menos do que promete.",
          visualPrompt: "Clean comparison card with bold typography.",
          assignedPhotoUrl: brand.productPhotos[1 % brand.productPhotos.length]?.url,
          backgroundColor: brand.palette.background,
          textColor: brand.palette.text,
        },
        {
          slideNumber: 3,
          headline: "A virada de chave",
          body: `${brand.tagline} com máxima eficiência e qualidade superior.`,
          visualPrompt: "Macro detail of the product.",
          assignedPhotoUrl: brand.productPhotos[2 % brand.productPhotos.length]?.url,
          backgroundColor: brand.palette.secondary,
          textColor: brand.palette.text,
        },
        {
          slideNumber: 4,
          headline: "Garanta o seu hoje",
          body: "Clique no link da bio e faça parte da nova era.",
          visualPrompt: "Strong call to action with final packaging display.",
          assignedPhotoUrl: brand.productPhotos[0]?.url,
          backgroundColor: brand.palette.accent,
          textColor: "#ffffff",
        },
      ],
    }));

    setIdeas((prev) => [...newItems, ...prev]);
  };

  // Adaptar uma Trend para a marca
  const handleAdaptTrend = (trend: GlobalTrend) => {
    handleAddNewIdea(`Adaptação da trend viral "${trend.topic}" (${trend.platform}): ${trend.suggestedHook}`, 1);
    setActiveTab("workbench");
  };

  // Adaptar uma Sazonalidade para a marca
  const handleAdaptSeasonality = (season: SeasonalEvent) => {
    handleAddNewIdea(`Campanha sazonal para ${season.title}: ${season.recommendedAngle}`, 1);
    setActiveTab("workbench");
  };

  // Gerar post contragolpe de concorrente
  const handleGenerateCounterPost = (competitorName: string, gapTopic: string) => {
    handleAddNewIdea(`Diferenciação contra ${competitorName} atacando o gap: ${gapTopic}`, 1);
    setActiveTab("workbench");
  };

  const scheduledCount = ideas.filter(
    (i) => i.status === "scheduled" || i.status === "rendered",
  ).length;

  return (
    <div className="craft-studio-root" data-craft-theme={theme}>
      {/* CRAFT Top Header */}
      <header className="craft-header">
        <div className="craft-brand-logo">
          <span className="craft-brand-badge">CRAFT</span>
          <div>
            <h1 className="craft-brand-title">
              RENDER STUDIO
              <span className="craft-brand-subtitle">by RoboNuggets / Bioma</span>
            </h1>
          </div>

          <div
            onClick={() => setIsTailorModalOpen(true)}
            style={{
              marginLeft: "12px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "var(--craft-paper)",
              padding: "4px 10px",
              border: "var(--craft-border)",
              boxShadow: "var(--craft-shadow-sm)",
              borderRadius: "2px",
              cursor: "pointer",
              fontSize: "0.8rem",
              fontWeight: 800,
            }}
            title="Clique para customizar / rebrandar o estúdio para qualquer cliente"
          >
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: currentPreset.brand.palette.primary,
              }}
            />
            <span>CLIENTE: {currentPreset.brand.name.toUpperCase()}</span>
            <span style={{ fontSize: "0.7rem", color: "var(--craft-orange)", marginLeft: "4px" }}>
              [TAILOR ▾]
            </span>
          </div>
        </div>

        <div className="craft-header-actions">
          <button
            className="craft-btn"
            onClick={() => setActiveTab("scheduler")}
            style={{ fontSize: "0.8rem" }}
          >
            <Calendar size={14} />
            <span>View scheduled</span>
            <span
              style={{
                background: "var(--craft-orange)",
                color: "#fff",
                fontSize: "0.7rem",
                padding: "1px 5px",
                borderRadius: "2px",
                fontFamily: "var(--craft-font-mono)",
              }}
            >
              {scheduledCount}
            </span>
          </button>

          <button
            className="craft-btn craft-btn-icon"
            onClick={toggleTheme}
            title={theme === "light" ? "Mudar para modo escuro" : "Mudar para modo claro"}
          >
            {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
          </button>

          <button
            className="craft-btn craft-btn-orange"
            onClick={() => setIsTailorModalOpen(true)}
          >
            <Sparkles size={14} /> Tailor Rebrand
          </button>
        </div>
      </header>

      {/* Navigation Bar (Paginações do Sistema Maleável) */}
      <nav className="craft-nav-bar">
        <button
          className={`craft-nav-tab ${activeTab === "workbench" ? "active" : ""}`}
          onClick={() => setActiveTab("workbench")}
        >
          <Layers size={16} />
          <span>Workbench (Estúdio)</span>
          <span className="craft-nav-tab-badge">{ideas.length}</span>
        </button>

        <button
          className={`craft-nav-tab ${activeTab === "brand-dna" ? "active" : ""}`}
          onClick={() => setActiveTab("brand-dna")}
        >
          <Globe size={16} />
          <span>Brand DNA (Link Inicial)</span>
        </button>

        <button
          className={`craft-nav-tab ${activeTab === "competitors" ? "active" : ""}`}
          onClick={() => setActiveTab("competitors")}
        >
          <Radar size={16} />
          <span>Competitor Spy Radar</span>
          <span className="craft-nav-tab-badge">{currentPreset.competitors.length}</span>
        </button>

        <button
          className={`craft-nav-tab ${activeTab === "trends" ? "active" : ""}`}
          onClick={() => setActiveTab("trends")}
        >
          <Calendar size={16} />
          <span>Sazonalidade & Trends</span>
          <span className="craft-nav-tab-badge">{currentPreset.trends.length}</span>
        </button>

        <button
          className={`craft-nav-tab ${activeTab === "cloud" ? "active" : ""}`}
          onClick={() => setActiveTab("cloud")}
        >
          <Eye size={16} />
          <span>3D Image Cloud</span>
        </button>

        <button
          className={`craft-nav-tab ${activeTab === "scheduler" ? "active" : ""}`}
          onClick={() => setActiveTab("scheduler")}
        >
          <Send size={16} />
          <span>Publisher Pipeline</span>
          <span className="craft-nav-tab-badge">{scheduledCount}</span>
        </button>
      </nav>

      {/* Main View Container */}
      <main className="craft-view-container">
        {activeTab === "workbench" && (
          <StudioWorkbenchView
            brand={currentPreset.brand}
            ideas={ideas}
            onOpenCarousel={(idea) => setPreviewIdea(idea)}
            onSchedulePost={handleSchedulePost}
            onUpdateIdea={handleUpdateIdea}
            onAddNewIdea={handleAddNewIdea}
          />
        )}

        {activeTab === "brand-dna" && (
          <BrandDnaView
            brand={currentPreset.brand}
            onUpdateBrand={(brand) =>
              setCurrentPreset((prev) => ({ ...prev, brand }))
            }
          />
        )}

        {activeTab === "competitors" && (
          <CompetitorRadarView
            brand={currentPreset.brand}
            competitors={currentPreset.competitors}
            onGenerateCounterPost={handleGenerateCounterPost}
          />
        )}

        {activeTab === "trends" && (
          <SeasonalityTrendsView
            brand={currentPreset.brand}
            seasonality={currentPreset.seasonality}
            trends={currentPreset.trends}
            onAdaptTrend={handleAdaptTrend}
            onAdaptSeasonality={handleAdaptSeasonality}
          />
        )}

        {activeTab === "cloud" && (
          <ImageCloudView
            brand={currentPreset.brand}
            ideas={ideas}
          />
        )}

        {activeTab === "scheduler" && (
          <SchedulerPipelineView
            brand={currentPreset.brand}
            ideas={ideas}
            onOpenCarousel={(idea) => setPreviewIdea(idea)}
          />
        )}
      </main>

      {/* Modal de visualização expandida de lâminas do carrossel */}
      {previewIdea && (
        <CarouselModal
          idea={previewIdea}
          brand={currentPreset.brand}
          onClose={() => setPreviewIdea(null)}
          onSchedule={handleSchedulePost}
        />
      )}

      {/* Modal de Rebranding Maleável (Tailor) */}
      {isTailorModalOpen && (
        <TailorModal
          currentPreset={currentPreset}
          onApplyPreset={handleApplyPreset}
          onClose={() => setIsTailorModalOpen(false)}
        />
      )}
    </div>
  );
};
