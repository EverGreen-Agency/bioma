import { useState, useEffect } from "react";
import {
  Target,
  Sparkles,
  Bot,
  ExternalLink,
  Plus,
  Copy,
  CheckCircle2,
  AlertCircle,
  FileText,
  DollarSign,
  Clock,
  Send,
  Zap,
  Brain,
  RefreshCw,
  UserCheck,
  Award,
  Globe,
  Trash2,
  FolderCheck,
  AlertTriangle,
  BookOpen,
  Layers,
  BarChart3,
  TrendingUp,
  PieChart,
  Trophy,
  Wallet,
  ArrowUpRight,
  Printer,
  ClipboardList,
  Search,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { ExecutiveReportPdfModal } from "../../../components/ExecutiveReportPdfModal";
import { ProposalWizard } from "./ProposalWizard";
import { PlanningPortfolioPanel } from "./PlanningPortfolioPanel";
import { ProposalLifecycleDrawer } from "./ProposalLifecycleDrawer";
import { SalesCopilotPanel } from "./SalesCopilotPanel";
import { OpportunityJourneyDrawer } from "./OpportunityJourneyDrawer";
import {
  api,
  type OpportunitySummary,
  type ProposalSummary,
  type FreelancerProfile,
  type TechSkill,
  type OpportunitySkillGap,
  type ProposalAnalytics,
  type ProposalCohortAnalytics,
} from "../../../lib/api";

export function ProposalsManager() {
  const [activeTab, setActiveTab] = useState<"radar" | "proposals" | "profile_audit" | "skills_gaps" | "bigdata">("radar");
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([]);
  const [proposals, setProposals] = useState<ProposalSummary[]>([]);
  const [profiles, setProfiles] = useState<FreelancerProfile[]>([]);
  const [skills, setSkills] = useState<TechSkill[]>([]);
  const [gaps, setGaps] = useState<OpportunitySkillGap[]>([]);
  const [analytics, setAnalytics] = useState<ProposalAnalytics | null>(null);
  const [cohorts, setCohorts] = useState<ProposalCohortAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false);
  const [isPdfModalOpen, setIsPdfModalOpen] = useState(false);
  const [isProposalWizardOpen, setIsProposalWizardOpen] = useState(false);
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);
  const [selectedOpportunityId, setSelectedOpportunityId] = useState<string | null>(null);

  // Form State para Ingestão Manual Rápida
  const [sourcePlatform, setSourcePlatform] = useState("99freelas");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [budgetText, setBudgetText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Generating proposal & Sync state
  const [generatingOppId, setGeneratingOppId] = useState<string | null>(null);
  const [copiedProposalId, setCopiedProposalId] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);

  // Profile Auto-Audit State
  const [auditProfileUrl, setAuditProfileUrl] = useState("");
  const [auditPlatform, setAuditPlatform] = useState("workana");
  const [isAuditing, setIsAuditing] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);

  // Filtros e Paginação do Radar
  const [radarSearch, setRadarSearch] = useState("");
  const [radarPlatform, setRadarPlatform] = useState("all");
  const [radarFitFilter, setRadarFitFilter] = useState("all");
  const [radarPageSize, setRadarPageSize] = useState(20);
  const [radarCurrentPage, setRadarCurrentPage] = useState(1);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [oppsRes, propsRes, profilesRes, skillsRes, gapsRes, analyticsRes, cohortRes] = await Promise.all([
        api.listOpportunities(),
        api.listProposals(),
        api.listFreelancerProfiles(),
        api.listTechSkills(),
        api.listSkillGaps(),
        api.getProposalAnalytics(),
        api.proposalCohorts(),
      ]);
      setOpportunities(oppsRes);
      setProposals(propsRes);
      setProfiles(profilesRes);
      setSkills(skillsRes);
      setGaps(gapsRes);
      setAnalytics(analyticsRes);
      setCohorts(cohortRes);
      if (profilesRes.length > 0 && !selectedProfileId) {
        setSelectedProfileId(profilesRes[0].id);
      }
    } catch (err) {
      console.error("Erro ao carregar dados de propostas e analytics:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleIngestOpportunity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setIsSubmitting(true);
    try {
      await api.ingestOpportunity({
        source_platform: sourcePlatform,
        title,
        url: url.trim() || undefined,
        description: description.trim() || undefined,
        budget_text: budgetText.trim() || undefined,
      });

      setTitle("");
      setUrl("");
      setDescription("");
      setBudgetText("");
      setIsIngestModalOpen(false);
      await loadData();
    } catch (err: any) {
      alert("Erro ao triar vaga: " + (err.message || "Erro desconhecido"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const [evaluatingOppId, setEvaluatingOppId] = useState<string | null>(null);

  const handleGenerateProposal = async (oppId: string) => {
    setGeneratingOppId(oppId);
    try {
      await api.generateProposalForOpportunity(oppId);
      await loadData();
      setActiveTab("proposals");
    } catch (err: any) {
      alert("Erro ao gerar proposta comercial: " + (err.message || "Erro desconhecido"));
    } finally {
      setGeneratingOppId(null);
    }
  };

  const handleEvaluateAi = async (oppId: string) => {
    setEvaluatingOppId(oppId);
    try {
      await api.evaluateOpportunityWithAi(oppId);
      await loadData();
    } catch (err: any) {
      alert("Erro ao avaliar vaga com IA: " + (err.message || "Erro desconhecido"));
    } finally {
      setEvaluatingOppId(null);
    }
  };

  const handleCopyPublicLink = (token: string, proposalId: string) => {
    const fullUrl = `${window.location.origin}/propostas/public/${token}`;
    navigator.clipboard.writeText(fullUrl);
    setCopiedProposalId(proposalId);
    setTimeout(() => setCopiedProposalId(null), 3000);
  };

  const handleSyncProfile = async (urlToSync?: string, platformKeyToSync?: string) => {
    const targetUrl = urlToSync || auditProfileUrl;
    if (!targetUrl.trim()) return;

    setIsAuditing(true);
    try {
      const res = await api.syncFreelancerProfile({
        profile_url: targetUrl.trim(),
        platform_key: platformKeyToSync || auditPlatform,
      });
      setAuditProfileUrl("");
      await loadData();
      setSelectedProfileId(res.id);
    } catch (err: any) {
      alert("Erro ao realizar auto-auditoria do perfil: " + (err.message || "Erro desconhecido"));
    } finally {
      setIsAuditing(false);
    }
  };

  const handleDeleteProfile = async (profileId: string) => {
    if (!confirm("Deseja realmente desconectar este perfil da auto-vigilância?")) return;
    try {
      await api.deleteFreelancerProfile(profileId);
      if (selectedProfileId === profileId) setSelectedProfileId(null);
      await loadData();
    } catch (err: any) {
      alert("Erro ao remover perfil: " + (err.message || "Erro desconhecido"));
    }
  };

  const handleResolveGap = async (gapId: string) => {
    try {
      await api.resolveSkillGap(gapId);
      await loadData();
    } catch (err: any) {
      alert("Erro ao incorporar competência: " + (err.message || "Erro desconhecido"));
    }
  };

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId) || profiles[0];

  const filteredOpportunities = opportunities.filter((opp) => {
    if (radarPlatform !== "all" && opp.source_platform.toLowerCase() !== radarPlatform.toLowerCase()) {
      return false;
    }
    // Sem avaliação não há faixa: filtrar por nota some com quem ninguém avaliou
    // ainda, que é justamente quem precisa de atenção.
    if (radarFitFilter !== "all") {
      if (opp.fit_score === null) return radarFitFilter === "unrated";
      if (radarFitFilter === "unrated") return false;
      if (radarFitFilter === "high" && opp.fit_score < 70) return false;
      if (radarFitFilter === "medium" && (opp.fit_score < 50 || opp.fit_score >= 70)) return false;
      if (radarFitFilter === "low" && opp.fit_score >= 50) return false;
    }

    if (radarSearch.trim()) {
      const q = radarSearch.toLowerCase().trim();
      const titleMatch = opp.title.toLowerCase().includes(q);
      const descMatch = (opp.description || "").toLowerCase().includes(q);
      const platformMatch = opp.source_platform.toLowerCase().includes(q);
      if (!titleMatch && !descMatch && !platformMatch) return false;
    }
    return true;
  });

  const totalPages = Math.ceil(filteredOpportunities.length / radarPageSize) || 1;
  const safeRadarPage = Math.min(radarCurrentPage, totalPages);
  const paginatedOpportunities = filteredOpportunities.slice(
    (safeRadarPage - 1) * radarPageSize,
    safeRadarPage * radarPageSize
  );

  const availablePlatforms = Array.from(
    new Set(opportunities.map((o) => o.source_platform.toLowerCase()))
  );

  return (
    <div style={{ padding: "24px", maxWidth: "1200px", margin: "0 auto", color: "var(--text)" }}>
      {/* Header Limpo */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "10px", margin: 0 }}>
            <Target color="var(--brand-accent)" size={28} /> Freelas e Propostas
          </h1>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: "0.9rem" }}>
            Monitoramento de vagas remotas, geração assistida de propostas e métricas comerciais da agência.
          </p>
        </div>
      </div>

      {syncFeedback && (
        <div style={{ padding: "12px 16px", background: "rgba(16, 185, 129, 0.12)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "8px", color: "#10b981", marginBottom: "16px", fontSize: "0.9rem" }}>
          {syncFeedback}
        </div>
      )}

      {/* Alerta de Status do Worker */}
      <div
        style={{
          background: "rgba(16, 185, 129, 0.08)",
          border: "1px solid rgba(16, 185, 129, 0.2)",
          borderRadius: "8px",
          padding: "12px 16px",
          marginBottom: "20px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          fontSize: "0.85rem",
        }}
      >
        <Zap size={20} color="#10b981" />
        <div>
          <strong style={{ color: "#10b981" }}>Fontes verificáveis:</strong> use a varredura manual para consultar os feeds RSS públicos e as URLs configuradas. Falhas são exibidas; nenhum alerta externo é simulado.
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "12px", borderBottom: "1px solid var(--border)", marginBottom: "24px" }}>
        <button
          onClick={() => setActiveTab("radar")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "radar" ? "2px solid var(--brand-accent)" : "2px solid transparent",
            color: activeTab === "radar" ? "var(--brand-accent)" : "var(--text-dim)",
            padding: "10px 16px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <Bot size={18} /> Radar de Vagas ({opportunities.length})
        </button>
        <button
          onClick={() => setActiveTab("proposals")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "proposals" ? "2px solid var(--brand-accent)" : "2px solid transparent",
            color: activeTab === "proposals" ? "var(--brand-accent)" : "var(--text-dim)",
            padding: "10px 16px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <FileText size={18} /> Central de Propostas ({proposals.length})
        </button>
        <button
          onClick={() => setActiveTab("bigdata")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "bigdata" ? "2px solid var(--brand-accent)" : "2px solid transparent",
            color: activeTab === "bigdata" ? "var(--brand-accent)" : "var(--text-dim)",
            padding: "10px 16px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <BarChart3 size={18} color="var(--brand-accent)" /> Big Data, ROI & CAC ({analytics?.overall_roi_percentage || 0}%)
        </button>
        <button
          onClick={() => setActiveTab("profile_audit")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "profile_audit" ? "2px solid var(--brand-accent)" : "2px solid transparent",
            color: activeTab === "profile_audit" ? "var(--brand-accent)" : "var(--text-dim)",
            padding: "10px 16px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <UserCheck size={18} /> Auto-Vigilância de Perfil ({profiles.length})
        </button>
        <button
          onClick={() => setActiveTab("skills_gaps")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "skills_gaps" ? "2px solid var(--brand-accent)" : "2px solid transparent",
            color: activeTab === "skills_gaps" ? "var(--brand-accent)" : "var(--text-dim)",
            padding: "10px 16px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <AlertTriangle size={18} color={gaps.length > 0 ? "#f59e0b" : "inherit"} /> Inventário de Gaps ({gaps.length})
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-dim)" }}>
          Carregando dados do sistema...
        </div>
      ) : activeTab === "radar" ? (
        /* ABA 1: RADAR DE OPORTUNIDADES */
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Toolbar de Filtros & Ações do Radar */}
          <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap", background: "var(--surface)", padding: "14px 16px", borderRadius: "10px", border: "1px solid var(--border)" }}>
            <div style={{ flex: 1, minWidth: "220px", display: "flex", alignItems: "center", gap: "8px", background: "var(--bg-inset)", padding: "8px 12px", borderRadius: "8px", border: "1px solid var(--border)" }}>
              <Search size={16} color="var(--text-dim)" />
              <input
                type="text"
                placeholder="Buscar por título, empresa ou tecnologia..."
                value={radarSearch}
                onChange={(e) => { setRadarSearch(e.target.value); setRadarCurrentPage(1); }}
                style={{ background: "transparent", border: "none", color: "var(--text)", width: "100%", outline: "none", fontSize: "0.88rem" }}
              />
            </div>

            <select
              value={radarPlatform}
              onChange={(e) => { setRadarPlatform(e.target.value); setRadarCurrentPage(1); }}
              style={{ padding: "8px 12px", background: "#182232", border: "1px solid var(--border)", borderRadius: "8px", color: "#f8fafc", fontSize: "0.85rem", cursor: "pointer" }}
            >
              <option value="all" style={{ background: "#182232", color: "#f8fafc" }}>Todas Plataformas ({opportunities.length})</option>
              {availablePlatforms.map((plat) => (
                <option key={plat} value={plat} style={{ background: "#182232", color: "#f8fafc" }}>{plat.toUpperCase()}</option>
              ))}
            </select>

            <select
              value={radarFitFilter}
              onChange={(e) => { setRadarFitFilter(e.target.value); setRadarCurrentPage(1); }}
              style={{ padding: "8px 12px", background: "#182232", border: "1px solid var(--border)", borderRadius: "8px", color: "#f8fafc", fontSize: "0.85rem", cursor: "pointer" }}
            >
              <option value="all" style={{ background: "#182232", color: "#f8fafc" }}>Qualquer Score</option>
              <option value="unrated" style={{ background: "#182232", color: "#f8fafc" }}>Não avaliadas</option>
              <option value="high" style={{ background: "#182232", color: "#f8fafc" }}>Alto Alinhamento (Fit ≥ 70%)</option>
              <option value="medium" style={{ background: "#182232", color: "#f8fafc" }}>Médio Alinhamento (50–69%)</option>
              <option value="low" style={{ background: "#182232", color: "#f8fafc" }}>Baixo Alinhamento (&lt; 50%)</option>
            </select>

            <button
              onClick={async () => {
                setIsSyncing(true);
                setSyncFeedback(null);
                try {
                  const res = await api.syncOpportunities();
                  setSyncFeedback(`Varredura concluída! ${res.scanned} projetos verificados (${res.new} novos adicionados, ${res.skipped} duplicados ignorados).`);
                  await loadData();
                } catch (err: any) {
                  alert("Erro ao realizar varredura: " + (err.message || "Erro desconhecido"));
                } finally {
                  setIsSyncing(false);
                }
              }}
              disabled={isSyncing}
              style={{
                padding: "8px 14px",
                borderRadius: "8px",
                background: "var(--bg-inset)",
                border: "1px solid var(--border)",
                color: "var(--brand-accent)",
                fontWeight: 600,
                cursor: isSyncing ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                whiteSpace: "nowrap",
                opacity: isSyncing ? 0.7 : 1,
              }}
            >
              <RefreshCw size={15} className={isSyncing ? "animate-spin" : ""} />
              {isSyncing ? "Varrendo..." : "Varredura"}
            </button>

            <button
              className="primary-button"
              onClick={() => setIsIngestModalOpen(true)}
              style={{ padding: "8px 14px", display: "flex", alignItems: "center", gap: "6px", whiteSpace: "nowrap" }}
            >
              <Plus size={16} /> Capturar Vaga
            </button>
          </div>

          {/* Quantidade Encontrada */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.84rem", color: "var(--text-dim)" }}>
            <span>Exibindo {paginatedOpportunities.length} de {filteredOpportunities.length} vagas encontradas</span>
            {totalPages > 1 && <span>Página {safeRadarPage} de {totalPages}</span>}
          </div>

          {paginatedOpportunities.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", background: "var(--surface)", borderRadius: "12px", color: "var(--text-dim)" }}>
              Nenhuma vaga encontrada com os filtros selecionados.
            </div>
          ) : (
            paginatedOpportunities.map((opp) => (
              <div
                key={opp.id}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "12px",
                  padding: "20px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <span style={{ fontSize: "0.75rem", background: "var(--bg-inset)", color: "var(--brand-accent)", padding: "2px 8px", borderRadius: "4px", fontWeight: 600 }}>
                      {opp.source_platform.toUpperCase()}
                    </span>
                    <h2 style={{ margin: "6px 0 0", fontSize: "1.15rem", fontWeight: 600 }}>
                      {opp.url ? (
                        <a href={opp.url} target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px" }}>
                          {opp.title} <ExternalLink size={14} color="var(--text-dim)" />
                        </a>
                      ) : (
                        opp.title
                      )}
                    </h2>
                  </div>

                  <div style={{ textAlign: "right" }}>
                    {opp.fit_score === null ? (
                      <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--text-dim)" }}>
                        Não avaliada
                      </div>
                    ) : (
                      <div style={{ fontSize: "1.1rem", fontWeight: 700, color: opp.fit_score >= 70 ? "#10b981" : opp.fit_score >= 50 ? "#f59e0b" : "#ef4444" }}>
                        Score de Fit: {opp.fit_score}/100
                      </div>
                    )}
                    <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>Orçamento: {opp.budget_text || "A combinar"}</span>
                  </div>
                </div>

                <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--text-dim)", lineHeight: 1.5 }}>
                  {opp.description || "Sem descrição informada."}
                </p>

                {opp.fit_analysis ? (
                  <div style={{ background: "var(--bg-inset)", padding: "8px 12px", borderRadius: "6px", fontSize: "0.8rem", color: "var(--text-dim)", border: "1px solid var(--border)" }}>
                    💡 <strong>Avaliação:</strong> {opp.fit_analysis}
                  </div>
                ) : (
                  <div style={{ background: "var(--bg-inset)", padding: "8px 12px", borderRadius: "6px", fontSize: "0.8rem", color: "var(--text-dim)", border: "1px dashed var(--border)" }}>
                    Ninguém avaliou esta vaga ainda. Use <strong>Avaliar com IA</strong> para comparar com o
                    que a EG sabe fazer (Tech Radar + inventário comercial + projetos concluídos).
                  </div>
                )}

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
                  <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                    Cadastrado em: {new Date(opp.created_at).toLocaleDateString("pt-BR")}
                  </span>

                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <button
                      className="ghost-button"
                      onClick={() => setSelectedOpportunityId(opp.id)}
                      style={{ padding: "8px 14px", border: "1px solid var(--border)" }}
                    >
                      Abrir continuidade
                    </button>
                    <button
                      className="ghost-button"
                      onClick={() => handleEvaluateAi(opp.id)}
                      disabled={evaluatingOppId === opp.id}
                      style={{ padding: "8px 14px", display: "flex", alignItems: "center", gap: "6px", fontSize: "0.82rem", color: "var(--brand-accent)", border: "1px solid var(--border)" }}
                      title="Analisar aderência com o banco de competências e contexto da Evergreen através de IA"
                    >
                      <Brain size={15} color="#a855f7" className={evaluatingOppId === opp.id ? "animate-spin" : ""} />
                      {evaluatingOppId === opp.id ? "Analisando..." : "Avaliar com IA"}
                    </button>

                    {opp.status === "proposal_generated" ? (
                      <span style={{ fontSize: "0.8rem", color: "#10b981", fontWeight: 600, display: "flex", alignItems: "center", gap: "4px" }}>
                        <CheckCircle2 size={16} /> Proposta Comercial Gerada
                      </span>
                    ) : (
                      <button
                        className="primary-button"
                        onClick={() => handleGenerateProposal(opp.id)}
                        disabled={generatingOppId === opp.id}
                        style={{ padding: "8px 16px", display: "flex", alignItems: "center", gap: "6px" }}
                      >
                        <Sparkles size={16} />
                        {generatingOppId === opp.id ? "Squad elaborando proposta..." : "Gerar rascunho assistido"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}

          {/* Paginação do Radar */}
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "12px", marginTop: "16px", flexWrap: "wrap" }}>
            <button
              className="secondary-button"
              disabled={safeRadarPage <= 1}
              onClick={() => setRadarCurrentPage((p) => Math.max(1, p - 1))}
              style={{ padding: "8px 14px", display: "flex", alignItems: "center", gap: "4px" }}
            >
              <ChevronLeft size={16} /> Anterior
            </button>

            <span style={{ fontSize: "0.88rem", fontWeight: 600, color: "var(--text-muted)" }}>
              Página {safeRadarPage} de {totalPages}
            </span>

            <button
              className="secondary-button"
              disabled={safeRadarPage >= totalPages}
              onClick={() => setRadarCurrentPage((p) => Math.min(totalPages, p + 1))}
              style={{ padding: "8px 14px", display: "flex", alignItems: "center", gap: "4px" }}
            >
              Próxima <ChevronRight size={16} />
            </button>

            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginLeft: "12px" }}>
              <span style={{ fontSize: "0.82rem", color: "var(--text-dim)", whiteSpace: "nowrap" }}>Exibir por pág:</span>
              <select
                value={radarPageSize}
                onChange={(e) => { setRadarPageSize(Number(e.target.value)); setRadarCurrentPage(1); }}
                style={{ padding: "6px 10px", background: "#182232", border: "1px solid var(--border)", borderRadius: "8px", color: "#f8fafc", fontSize: "0.85rem", cursor: "pointer" }}
              >
                <option value={10} style={{ background: "#182232", color: "#f8fafc" }}>10 por pág.</option>
                <option value={20} style={{ background: "#182232", color: "#f8fafc" }}>20 por pág.</option>
                <option value={50} style={{ background: "#182232", color: "#f8fafc" }}>50 por pág.</option>
                <option value={100} style={{ background: "#182232", color: "#f8fafc" }}>100 por pág.</option>
              </select>
            </div>
          </div>
        </div>
      ) : activeTab === "proposals" ? (
        /* ABA 2: CENTRAL DE PROPOSTAS COMERCIAIS */
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
            <div>
              <h2 style={{ margin: 0 }}>Propostas comerciais</h2>
              <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: "0.86rem" }}>
                Briefings ligados aos clientes da plataforma, com versão, escopo e contexto preservados.
              </p>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <button
                className="secondary-button"
                onClick={() => setIsPdfModalOpen(true)}
                style={{ padding: "8px 14px", display: "flex", alignItems: "center", gap: "6px" }}
              >
                <Printer size={16} /> Relatório Executivo PDF
              </button>
              <button className="primary-button" type="button" onClick={() => setIsProposalWizardOpen(true)}>
                <Plus size={16} /> Nova proposta
              </button>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 10 }}>
            {[
              ["Total", proposals.length],
              ["Rascunhos", proposals.filter((proposal) => proposal.status === "draft").length],
              ["Enviadas", proposals.filter((proposal) => proposal.status === "sent").length],
              ["Em negociação", proposals.filter((proposal) => proposal.status === "negotiating").length],
              ["Aprovadas/ganhas", proposals.filter((proposal) => proposal.status === "approved" || proposal.status === "won").length],
            ].map(([label, value]) => (
              <div key={label} style={{ padding: 14, border: "1px solid var(--border)", borderRadius: 9, background: "var(--surface)" }}>
                <span style={{ display: "block", color: "var(--text-dim)", fontSize: "0.76rem" }}>{label}</span>
                <strong style={{ fontSize: "1.35rem" }}>{value}</strong>
              </div>
            ))}
          </div>

          {proposals.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", background: "var(--surface)", borderRadius: "12px" }}>
              Nenhuma proposta comercial gerada. Crie um briefing ligado a um cliente ou gere a partir do radar.
            </div>
          ) : (
            proposals.map((prop) => (
              <div
                key={prop.id}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "12px",
                  padding: "20px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <span style={{ fontSize: "0.75rem", background: "var(--bg-inset)", color: "var(--text-dim)", padding: "2px 8px", borderRadius: "4px" }}>
                      {prop.target_niche || "Proposta Geral"}
                    </span>
                    <h2 style={{ margin: "4px 0 0", fontSize: "1.2rem", fontWeight: 600 }}>{prop.title || prop.client_name}</h2>
                    <span style={{ color: "var(--text-dim)", fontSize: "0.78rem" }}>
                      {prop.client_name} · versão {prop.version}
                      {prop.workspace_id ? " · cliente vinculado" : " · origem externa"}
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span className="status-badge">{prop.status}</span>

                    <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--brand-accent)" }}>
                      {prop.pricing_cents > 0
                        ? `R$ ${(prop.pricing_cents / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`
                        : "Preço a definir"}
                    </span>
                    <button
                      className="secondary-button"
                      onClick={() => handleCopyPublicLink(prop.public_token, prop.id)}
                      style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 12px" }}
                    >
                      <Copy size={16} />
                      {copiedProposalId === prop.id ? "Link Copiado!" : "Copiar Link Público"}
                    </button>
                    <button
                      className="primary-button"
                      onClick={() => setSelectedProposalId(prop.id)}
                      style={{ padding: "8px 12px" }}
                    >
                      Abrir proposta
                    </button>
                  </div>
                </div>

                <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--text-dim)" }}>{prop.executive_summary}</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 7, fontSize: "0.76rem" }}>
                  <span style={{ padding: "3px 7px", borderRadius: 5, background: "var(--bg-inset)" }}>
                    IA: {prop.generation_mode === "live" ? "execução live" : prop.generation_mode === "preview" ? "prévia local" : "manual"}
                  </span>
                  {prop.delivery_modality && <span style={{ padding: "3px 7px", borderRadius: 5, background: "var(--bg-inset)" }}>Modalidade: {prop.delivery_modality}</span>}
                  {prop.selected_services.length > 0 && <span style={{ padding: "3px 7px", borderRadius: 5, background: "var(--bg-inset)" }}>{prop.selected_services.length} serviço(s) no briefing</span>}
                  {prop.estimated_budget && <span style={{ padding: "3px 7px", borderRadius: 5, background: "var(--bg-inset)" }}>Orçamento: {prop.estimated_budget}</span>}
                </div>

                {/* Pilares da EG */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", marginTop: "4px" }}>
                  <div style={{ background: "var(--bg-inset)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                    <strong style={{ fontSize: "0.8rem", color: "var(--brand-accent)", display: "block", marginBottom: "4px" }}>Pilar 1: Oferta</strong>
                    <span style={{ fontSize: "0.8rem" }}>{prop.scope_offer || "Estratégia e posicionamento de valor."}</span>
                  </div>
                  <div style={{ background: "var(--bg-inset)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                    <strong style={{ fontSize: "0.8rem", color: "var(--brand-accent)", display: "block", marginBottom: "4px" }}>Pilar 2: Conversão</strong>
                    <span style={{ fontSize: "0.8rem" }}>{prop.scope_conversion || "Estrutura de vendas e tracking."}</span>
                  </div>
                  <div style={{ background: "var(--bg-inset)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                    <strong style={{ fontSize: "0.8rem", color: "var(--brand-accent)", display: "block", marginBottom: "4px" }}>Pilar 3: Demanda</strong>
                    <span style={{ fontSize: "0.8rem" }}>{prop.scope_demand || "Escala de tráfego e prospecção."}</span>
                  </div>
                </div>

                {/* Cases Injetados Automaticamente */}
                {prop.attached_cases && prop.attached_cases.length > 0 && (
                  <div style={{ background: "rgba(16, 185, 129, 0.05)", border: "1px solid rgba(16, 185, 129, 0.2)", borderRadius: "8px", padding: "12px", marginTop: "4px" }}>
                    <strong style={{ fontSize: "0.85rem", color: "#10b981", display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                      <FolderCheck size={16} /> Cases & Provas Sociais Injetados na Proposta:
                    </strong>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      {prop.attached_cases.map((c, idx) => (
                        <div key={idx} style={{ fontSize: "0.82rem", background: "var(--surface)", padding: "8px 12px", borderRadius: "6px", border: "1px solid var(--border)" }}>
                          <strong style={{ color: "var(--text)" }}>{c.case_title} ({c.skill})</strong>: {c.description} — <em style={{ color: "#10b981" }}>{c.results_highlight}</em>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      ) : activeTab === "bigdata" ? (
        /* ABA 5: BIG DATA, ROI & CAC ANALYTICS */
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div className="surface" style={{ padding: 18, overflowX: "auto" }}>
            <h3 style={{ marginTop: 0 }}>Coortes comerciais por mês de criação</h3>
            <p style={{ color: "var(--text-dim)", fontSize: "0.82rem" }}>
              Medianas: primeiro envio {cohorts?.median_days_to_first_send?.toFixed(1) ?? "—"} dias · fechamento {cohorts?.median_days_to_close?.toFixed(1) ?? "—"} dias.
            </p>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr>{["Mês", "Criadas", "Enviadas", "Ganhas", "Perdidas", "Win rate", "Dias para fechar"].map((label) => <th key={label} style={{ padding: 8, textAlign: "left" }}>{label}</th>)}</tr></thead>
              <tbody>{cohorts?.cohorts.map((cohort) => (
                <tr key={cohort.month} style={{ borderTop: "1px solid var(--border)" }}>
                  <td style={{ padding: 8 }}>{cohort.month}</td><td>{cohort.created}</td><td>{cohort.sent}</td>
                  <td>{cohort.won}</td><td>{cohort.lost}</td><td>{cohort.win_rate_percentage.toFixed(1)}%</td>
                  <td>{cohort.average_days_to_close?.toFixed(1) ?? "—"}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          {/* KPI Cards Big Data & Financeiro */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px" }}>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px" }}>
              <span style={{ fontSize: "0.82rem", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: "6px" }}>
                <Trophy size={18} color="#10b981" /> Taxa de Conversão (Win Rate)
              </span>
              <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "#10b981", marginTop: "8px" }}>
                {analytics?.win_rate_percentage || 0}%
              </div>
              <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                {analytics?.status_counts.won || 0} ganhas de {(analytics?.status_counts.won || 0) + (analytics?.status_counts.lost || 0) + (analytics?.status_counts.sent || 0)} propostas finalizadas
              </span>
            </div>

            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px" }}>
              <span style={{ fontSize: "0.82rem", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: "6px" }}>
                <ArrowUpRight size={18} color="#10b981" /> Lucro Líquido de Prospecção
              </span>
              <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "#10b981", marginTop: "8px" }}>
                R$ {((analytics?.net_growth_profit_cents || 0) / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
              </div>
              <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                Receita ganha menos assinaturas SaaS
              </span>
            </div>

            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px" }}>
              <span style={{ fontSize: "0.82rem", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: "6px" }}>
                <TrendingUp size={18} color="var(--brand-accent)" /> ROI Global do Investimento
              </span>
              <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "var(--brand-accent)", marginTop: "8px" }}>
                +{analytics?.overall_roi_percentage || 0}%
              </div>
              <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                Retorno sobre os custos de plataformas
              </span>
            </div>

            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px" }}>
              <span style={{ fontSize: "0.82rem", color: "var(--text-dim)", display: "flex", alignItems: "center", gap: "6px" }}>
                <Wallet size={18} color="#3b82f6" /> Custo Mensal das Plataformas
              </span>
              <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "#3b82f6", marginTop: "8px" }}>
                R$ {((analytics?.total_platform_investment_cents || 0) / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}/mês
              </div>
              <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                Total investido em SaaS de prospecção
              </span>
            </div>
          </div>

          {/* Tabela de ROI, CAC & Custo por Proposta por Plataforma */}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "24px" }}>
            <h3 style={{ margin: "0 0 8px", fontSize: "1.2rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
              <PieChart color="var(--brand-accent)" size={22} /> Análise Completa de ROI & CAC por Plataforma (Big Data)
            </h3>
            <p style={{ margin: "0 0 20px", color: "var(--text-dim)", fontSize: "0.88rem" }}>
              Detalhamento de investimento mensal, custo por proposta enviada (CPP), Custo de Aquisição de Cliente (CAC), receita gerada e retorno financeiro por canal.
            </p>

            {!analytics?.platform_performance || analytics.platform_performance.length === 0 ? (
              <div style={{ padding: "24px", textAlign: "center", background: "var(--bg-inset)", borderRadius: "8px", color: "var(--text-dim)" }}>
                Nenhum dado de conversão suficiente por plataforma no momento.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                      <th style={{ padding: "12px", color: "var(--text-dim)" }}>Plataforma</th>
                      <th style={{ padding: "12px", color: "var(--text-dim)" }}>Custo Mensal</th>
                      <th style={{ padding: "12px", color: "var(--text-dim)" }}>Enviadas</th>
                      <th style={{ padding: "12px", color: "var(--text-dim)" }}>Clientes Ganho</th>
                      <th style={{ padding: "12px", color: "var(--text-dim)" }}>Custo/Proposta</th>
                      <th style={{ padding: "12px", color: "var(--text-dim)" }}>CAC (Custo/Cliente)</th>
                      <th style={{ padding: "12px", color: "var(--text-dim)" }}>Receita Ganha</th>
                      <th style={{ padding: "12px", color: "var(--text-dim)" }}>Lucro Líquido</th>
                      <th style={{ padding: "12px", color: "var(--text-dim)" }}>ROI (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.platform_performance.map((p, idx) => (
                      <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "12px", fontWeight: 600, color: "var(--brand-accent)" }}>{p.platform_name}</td>
                        <td style={{ padding: "12px" }}>R$ {(p.monthly_cost_cents / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
                        <td style={{ padding: "12px" }}>{p.total_proposals}</td>
                        <td style={{ padding: "12px", color: "#10b981", fontWeight: 600 }}>{p.won_proposals}</td>
                        <td style={{ padding: "12px" }}>R$ {(p.cost_per_proposal_cents / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
                        <td style={{ padding: "12px", color: "#3b82f6", fontWeight: 600 }}>R$ {(p.cac_cents / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
                        <td style={{ padding: "12px", fontWeight: 700 }}>R$ {(p.won_revenue_cents / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
                        <td style={{ padding: "12px", color: p.net_profit_cents >= 0 ? "#10b981" : "#ef4444", fontWeight: 700 }}>
                          R$ {(p.net_profit_cents / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                        </td>
                        <td style={{ padding: "12px" }}>
                          <span style={{ background: p.roi_percentage >= 100 ? "rgba(16, 185, 129, 0.15)" : "var(--bg-inset)", color: p.roi_percentage >= 100 ? "#10b981" : "var(--text)", padding: "4px 8px", borderRadius: "6px", fontWeight: 700 }}>
                            +{p.roi_percentage}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : activeTab === "profile_audit" ? (
        /* ABA 3: AUTO-VIGILÂNCIA & AUDITORIA DE PERFIL IA VIA URL */
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Card de Adicionar Perfil por URL */}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "24px" }}>
            <h3 style={{ margin: "0 0 8px", fontSize: "1.2rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
              <Globe color="var(--brand-accent)" size={22} /> Conectar Perfil por Link/URL para Auto-Vigilância Automática
            </h3>
            <p style={{ margin: "0 0 20px", color: "var(--text-dim)", fontSize: "0.9rem" }}>
              Cole a URL pública do seu perfil no Workana, Upwork, 99freela, LinkedIn ou Toptal. Nosso Engine raspa e analisa automaticamente o seu perfil, gerando recomendações de posicionamento e copy otimizada.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSyncProfile();
              }}
              style={{ display: "flex", gap: "12px", alignItems: "flex-end" }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "6px", width: "160px" }}>
                <label style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>Plataforma</label>
                <select
                  value={auditPlatform}
                  onChange={(e) => setAuditPlatform(e.target.value)}
                  style={{ padding: "10px", borderRadius: "8px", background: "var(--bg-inset)", border: "1px solid var(--border)", color: "var(--text)" }}
                >
                  <option value="workana">Workana</option>
                  <option value="upwork">UpWork</option>
                  <option value="99freelas">99freela</option>
                  <option value="toptal">Toptal</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="contra">Contra.com</option>
                  <option value="other">Outra Plataforma</option>
                </select>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1 }}>
                <label style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>Link/URL Completa do Perfil</label>
                <input
                  required
                  type="url"
                  value={auditProfileUrl}
                  onChange={(e) => setAuditProfileUrl(e.target.value)}
                  placeholder="Ex: https://www.workana.com/freelancer/seu-perfil ou https://linkedin.com/in/seu-perfil"
                  style={{ padding: "10px 14px", borderRadius: "8px", background: "var(--bg-inset)", border: "1px solid var(--border)", color: "var(--text)", fontSize: "0.9rem" }}
                />
              </div>

              <button className="primary-button" type="submit" disabled={isAuditing} style={{ padding: "11px 24px", display: "flex", alignItems: "center", gap: "8px" }}>
                <Sparkles size={18} className={isAuditing ? "animate-spin" : ""} />
                {isAuditing ? "Raspando & Auditando..." : "Conectar & Auditar Perfil"}
              </button>
            </form>
          </div>

          {/* Perfis Conectados */}
          {profiles.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "20px" }}>
              {/* Lista Lateral de Perfis */}
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <h4 style={{ margin: "0 0 4px", fontSize: "1rem", color: "var(--text-dim)" }}>Perfis Monitorados ({profiles.length})</h4>
                {profiles.map((p) => {
                  const isSelected = p.id === (selectedProfile?.id);
                  return (
                    <div
                      key={p.id}
                      onClick={() => setSelectedProfileId(p.id)}
                      style={{
                        background: isSelected ? "var(--bg-inset)" : "var(--surface)",
                        border: isSelected ? "2px solid var(--brand-accent)" : "1px solid var(--border)",
                        borderRadius: "10px",
                        padding: "14px",
                        cursor: "pointer",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                        <span style={{ fontSize: "0.75rem", background: "var(--bg-inset)", color: "var(--brand-accent)", padding: "2px 6px", borderRadius: "4px", fontWeight: 600, alignSelf: "flex-start" }}>
                          {p.platform_key.toUpperCase()}
                        </span>
                        <strong style={{ fontSize: "0.95rem" }}>{p.profile_name || "Perfil Freelancer"}</strong>
                        <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                          Atualizado: {p.last_audited_at ? new Date(p.last_audited_at).toLocaleDateString("pt-BR") : "Recentemente"}
                        </span>
                      </div>

                      <div style={{ textAlign: "right", display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "6px" }}>
                        <span style={{ fontSize: "1.05rem", fontWeight: 700, color: p.audit_score >= 70 ? "#10b981" : "#f59e0b" }}>
                          {p.audit_score}/100
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteProfile(p.id);
                          }}
                          style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", padding: "2px" }}
                          title="Remover Perfil"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Raio-X do Perfil Selecionado */}
              {selectedProfile && (
                <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: "16px" }}>
                    <div>
                      <span style={{ fontSize: "0.75rem", background: "var(--bg-inset)", color: "var(--brand-accent)", padding: "2px 8px", borderRadius: "4px", fontWeight: 600 }}>
                        {selectedProfile.platform_key.toUpperCase()}
                      </span>
                      <h3 style={{ margin: "4px 0 0", fontSize: "1.2rem", fontWeight: 600 }}>
                        <a href={selectedProfile.profile_url} target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px" }}>
                          {selectedProfile.profile_name || "Perfil Freelancer"} <ExternalLink size={16} color="var(--text-dim)" />
                        </a>
                      </h3>
                      <span style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>{selectedProfile.headline || "Sem headline definida"}</span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <button
                        onClick={() => handleSyncProfile(selectedProfile.profile_url, selectedProfile.platform_key)}
                        disabled={isAuditing}
                        style={{ padding: "8px 14px", borderRadius: "8px", background: "var(--bg-inset)", border: "1px solid var(--border)", color: "var(--brand-accent)", fontSize: "0.85rem", fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}
                      >
                        <RefreshCw size={16} className={isAuditing ? "animate-spin" : ""} /> Re-Auditar
                      </button>
                      <div style={{ background: "var(--bg-inset)", padding: "8px 16px", borderRadius: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
                        <Award size={20} color="var(--brand-accent)" />
                        <span style={{ fontWeight: 700, fontSize: "1.1rem", color: "var(--brand-accent)" }}>Score: {selectedProfile.audit_score}/100</span>
                      </div>
                    </div>
                  </div>

                  {/* Diagnóstico em 2 colunas */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                    <div style={{ background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)", borderRadius: "8px", padding: "16px" }}>
                      <strong style={{ color: "#10b981", fontSize: "0.9rem", display: "block", marginBottom: "8px" }}>✅ Pontos Fortes Capturados</strong>
                      <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "0.85rem", color: "var(--text)" }}>
                        {(selectedProfile.audit_analysis.strengths || ["Perfil cadastrado na plataforma"]).map((s, idx) => (
                          <li key={idx} style={{ marginBottom: "4px" }}>{s}</li>
                        ))}
                      </ul>
                    </div>
                    <div style={{ background: "rgba(245, 158, 11, 0.08)", border: "1px solid rgba(245, 158, 11, 0.2)", borderRadius: "8px", padding: "16px" }}>
                      <strong style={{ color: "#f59e0b", fontSize: "0.9rem", display: "block", marginBottom: "8px" }}>⚠️ Gaps & Oportunidades de Otimização</strong>
                      <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "0.85rem", color: "var(--text)" }}>
                        {(selectedProfile.audit_analysis.gaps || ["Adicionar mais resultados de ROI"]).map((g, idx) => (
                          <li key={idx} style={{ marginBottom: "4px" }}>{g}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Copy Otimizada */}
                  <div style={{ background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
                    <strong style={{ fontSize: "0.95rem", color: "var(--brand-accent)" }}>✨ Headline Sugerida de Alto Impacto:</strong>
                    <code style={{ background: "var(--surface)", padding: "10px", borderRadius: "6px", border: "1px solid var(--border)", color: "var(--text)", fontWeight: 600 }}>
                      {selectedProfile.audit_analysis.optimized_headline || "Especialista em Growth & Performance B2B"}
                    </code>

                    <strong style={{ fontSize: "0.95rem", color: "var(--brand-accent)", marginTop: "8px" }}>📝 Bio Reformulada pela IA (Pronta para Copiar):</strong>
                    <textarea
                      readOnly
                      rows={8}
                      value={selectedProfile.audit_analysis.optimized_bio || selectedProfile.bio || ""}
                      style={{ padding: "12px", borderRadius: "6px", background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", fontSize: "0.88rem", fontFamily: "sans-serif" }}
                    />

                    <strong style={{ fontSize: "0.95rem", color: "var(--brand-accent)", marginTop: "8px" }}>💡 Recomendação para o Portfólio:</strong>
                    <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--text-dim)" }}>
                      {selectedProfile.audit_analysis.portfolio_tips || "Destaque os 3 principais cases com painéis de métricas."}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* ABA 4: INVENTÁRIO DE GAPS & COMPETÊNCIAS */
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Gaps de Tecnologia Exigidos pelas Vagas */}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "24px" }}>
            <h3 style={{ margin: "0 0 8px", fontSize: "1.2rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
              <AlertTriangle color="#f59e0b" size={22} /> Gaps Tecnológicos Identificados no Mercado
            </h3>
            <p style={{ margin: "0 0 20px", color: "var(--text-dim)", fontSize: "0.9rem" }}>
              Tecnologias e ferramentas exigidas em vagas de alto valor que a EG ainda não possui inventariadas. Incorporar essas competências aumenta o Score de Fit de novas oportunidades!
            </p>

            {gaps.length === 0 ? (
              <div style={{ padding: "24px", textAlign: "center", background: "var(--bg-inset)", borderRadius: "8px", color: "#10b981", fontSize: "0.9rem" }}>
                ✅ Nenhum gap de tecnologia pendente! Todas as ferramentas exigidas no mercado já constam no inventário da EG.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {gaps.map((gap) => (
                  <div
                    key={gap.id}
                    style={{
                      background: "rgba(245, 158, 11, 0.06)",
                      border: "1px solid rgba(245, 158, 11, 0.25)",
                      borderRadius: "10px",
                      padding: "16px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <span style={{ fontSize: "0.75rem", background: "#f59e0b", color: "#000", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}>
                        GAP: {gap.missing_skill.toUpperCase()}
                      </span>
                      <h4 style={{ margin: "6px 0 2px", fontSize: "1rem", fontWeight: 600 }}>{gap.opportunity_title}</h4>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
                        Identificado em: {new Date(gap.created_at).toLocaleDateString("pt-BR")}
                      </span>
                    </div>

                    <button
                      className="primary-button"
                      onClick={() => handleResolveGap(gap.id)}
                      style={{ padding: "8px 16px", display: "flex", alignItems: "center", gap: "6px", fontSize: "0.85rem" }}
                    >
                      <Plus size={16} /> Incorporar Skill ao Portfólio EG
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Competências & Cases Inventariados */}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "24px" }}>
            <h3 style={{ margin: "0 0 8px", fontSize: "1.2rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers color="var(--brand-accent)" size={22} /> Inventário de Competências & Ferramentas da EG ({skills.length})
            </h3>
            <p style={{ margin: "0 0 20px", color: "var(--text-dim)", fontSize: "0.9rem" }}>
              Ferramentas e frameworks disponíveis no arsenal da EverGreen para inclusão automática em propostas comerciais.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
              {skills.map((s) => (
                <div
                  key={s.id}
                  style={{
                    background: "var(--bg-inset)",
                    border: "1px solid var(--border)",
                    borderRadius: "10px",
                    padding: "16px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ fontSize: "1rem", color: "var(--brand-accent)" }}>{s.skill_name}</strong>
                    <span style={{ fontSize: "0.72rem", background: "rgba(16, 185, 129, 0.15)", color: "#10b981", padding: "2px 6px", borderRadius: "4px", fontWeight: 600 }}>
                      {s.case_count} Case(s) Validados
                    </span>
                  </div>
                  <p style={{ margin: 0, fontSize: "0.83rem", color: "var(--text-dim)" }}>
                    {s.notes || "Ferramenta integrada ao repertório estratégico da EG."}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Modal Ingestão Manual */}
      {isIngestModalOpen && (
        <div className="drawer-overlay" onClick={() => setIsIngestModalOpen(false)}>
          <div className="drawer-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "500px", padding: "24px" }}>
            <h2 style={{ marginTop: 0, fontSize: "1.2rem" }}>Capturar Vaga / Projeto Manualmente</h2>
            <form onSubmit={handleIngestOpportunity} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Plataforma
                <select value={sourcePlatform} onChange={(e) => setSourcePlatform(e.target.value)} style={{ padding: "8px", borderRadius: "6px" }}>
                  <option value="99freelas">99freelas</option>
                  <option value="workana">Workana</option>
                  <option value="upwork">UpWork</option>
                  <option value="freelancer">Freelancer.com</option>
                  <option value="toptal">Toptal</option>
                  <option value="malt">Malt</option>
                  <option value="contra">Contra</option>
                  <option value="outros">Outros / Indicação</option>
                </select>
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Título do Projeto / Vaga *
                <input required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ex: Preciso de gestor de tráfego e CRM" style={{ padding: "8px", borderRadius: "6px" }} />
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                URL da Vaga (opcional)
                <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." style={{ padding: "8px", borderRadius: "6px" }} />
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Orçamento Anunciado
                <input value={budgetText} onChange={(e) => setBudgetText(e.target.value)} placeholder="Ex: R$ 5.000 ou $1.000 USD" style={{ padding: "8px", borderRadius: "6px" }} />
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Descrição / Briefing (Cole o texto da vaga)
                <textarea rows={4} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Cole os detalhes da oportunidade para a IA triar..." style={{ padding: "8px", borderRadius: "6px", fontFamily: "inherit" }} />
              </label>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button type="button" className="secondary-button" onClick={() => setIsIngestModalOpen(false)}>Cancelar</button>
                <button type="submit" className="primary-button" disabled={isSubmitting}>
                  {isSubmitting ? "Triando..." : "Triar & Salvar Vaga"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isPdfModalOpen && (
        <ExecutiveReportPdfModal
          data={{
            title: "Relatório Executivo de Prospecção & Propostas",
            subtitle: "Visão consolidada de oportunidades triadas, taxa de conversão e vitórias",
            clientName: "Operação EverGreen Growth",
            period: new Date().toLocaleDateString("pt-BR"),
            summaryMetrics: [
              { label: "Total de Vagas no Radar", value: String(opportunities.length) },
              { label: "Propostas Ativas Geradas", value: String(proposals.length) },
              { label: "Taxa de Vitória (Win-Rate)", value: `${(analytics?.win_rate_percentage || 0).toFixed(1)}%` },
              { label: "Faturamento Ganho", value: `R$ ${((analytics?.total_won_value_cents || 0) / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}` },
            ],
            // Havia três frases fixas aqui, entre elas "conectado a 4+
            // plataformas" — afirmação factual que ninguém verifica e que sai
            // num relatório com o nome da EG. Destaque só entra se for derivado
            // do dado; até lá, o relatório vive sem ele.
            highlights: undefined,
            tables: proposals.length > 0 ? [
              {
                title: "Propostas Comerciais Recentes",
                headers: ["Cliente/Projeto", "Nicho", "Investimento (R$)", "Prazo", "Status"],
                rows: proposals.slice(0, 8).map((p) => [
                  p.client_name,
                  p.target_niche || "Geral",
                  `R$ ${(p.pricing_cents / 100).toFixed(2)}`,
                  `${p.delivery_days} dias`,
                  p.status.toUpperCase(),
                ]),
              },
            ] : undefined,
            nextSteps: [
              "Manter a varredura contínua de RSS e APIs de plataformas ligada.",
              "Avançar nas negociações de propostas enviadas que aguardam assinatura.",
              "Atualizar os cases de sucesso no banco de dados para aumentar o fit-score.",
            ],
          }}
          onClose={() => setIsPdfModalOpen(false)}
        />
      )}

      {isProposalWizardOpen && (
        <ProposalWizard
          onClose={() => setIsProposalWizardOpen(false)}
          onCreated={(proposal) => {
            setProposals((current) => [proposal, ...current.filter((item) => item.id !== proposal.id)]);
            setIsProposalWizardOpen(false);
            setActiveTab("proposals");
          }}
        />
      )}
      {selectedProposalId && (
        <ProposalLifecycleDrawer
          proposalId={selectedProposalId}
          onClose={() => setSelectedProposalId(null)}
          onChanged={loadData}
        />
      )}
      {selectedOpportunityId && (
        <OpportunityJourneyDrawer
          opportunityId={selectedOpportunityId}
          onClose={() => setSelectedOpportunityId(null)}
          onChanged={loadData}
        />
      )}
    </div>
  );
}
