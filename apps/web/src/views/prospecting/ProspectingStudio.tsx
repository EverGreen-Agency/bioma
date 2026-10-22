import { useEffect, useState, useMemo } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  Compass,
  Copy,
  ExternalLink,
  Flame,
  MessageSquare,
  Phone,
  PhoneCall,
  PhoneForwarded,
  PhoneMissed,
  Play,
  RotateCcw,
  Search,
  ShieldAlert,
  Sparkles,
  StopCircle,
  ThumbsDown,
  UserCheck,
  Zap,
} from "lucide-react";
import {
  api,
  type ProspectingCockpitContext,
  type ProspectingListItem,
  type ProspectingListSummary,
  type ProspectingSession,
  type SalesKnowledgeCard,
  type WorkspaceSummary,
} from "../../lib/api";

interface ProspectingStudioProps {
  workspaces: WorkspaceSummary[];
}

export function ProspectingStudio({ workspaces }: ProspectingStudioProps) {
  const activeWorkspace = workspaces.find((w) => w.kind === "agency_internal") || workspaces[0];
  const workspaceId = activeWorkspace?.id || "";

  const [activeTab, setActiveTab] = useState<"cockpit" | "lists" | "knowledge">("cockpit");
  const [lists, setLists] = useState<ProspectingListSummary[]>([]);
  const [cards, setCards] = useState<SalesKnowledgeCard[]>([]);
  const [activeSession, setActiveSession] = useState<ProspectingSession | null>(null);
  const [cockpit, setCockpit] = useState<ProspectingCockpitContext | null>(null);

  // Cockpit Session Form
  const [selectedListId, setSelectedListId] = useState("");
  const [sessionMotion, setSessionMotion] = useState<"growth" | "ai_automation">("growth");
  const [targetCalls, setTargetCalls] = useState(30);

  // Timer state
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Call Notes & Disposition
  const [callNotes, setCallNotes] = useState("");
  const [followUpDate, setFollowUpDate] = useState("");
  const [showFollowUpModal, setShowFollowUpModal] = useState(false);
  const [showHandoffModal, setShowHandoffModal] = useState(false);
  const [handoffProblem, setHandoffProblem] = useState("");
  const [handoffImpact, setHandoffImpact] = useState("");
  const [handoffMeetingAt, setHandoffMeetingAt] = useState("");
  const [handoffCloserNotes, setHandoffCloserNotes] = useState("");

  // Card Drawer / Search
  const [cardSearchQuery, setCardSearchQuery] = useState("");
  const [selectedCard, setSelectedCard] = useState<SalesKnowledgeCard | null>(null);
  const [cardMotionFilter, setCardMotionFilter] = useState("all");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const loadData = async () => {
    if (!workspaceId) return;
    try {
      setLoading(true);
      const [fetchedLists, fetchedCards] = await Promise.all([
        api.listProspectingLists(workspaceId),
        api.listProspectingCards(workspaceId),
      ]);
      setLists(fetchedLists);
      setCards(fetchedCards);
      if (fetchedLists.length > 0 && !selectedListId) {
        setSelectedListId(fetchedLists[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar dados de prospecção.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [workspaceId]);

  // Session Stopwatch
  useEffect(() => {
    if (!activeSession || activeSession.status !== "active") return;
    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [activeSession]);

  const formatTimer = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  const startSession = async () => {
    if (!workspaceId) return;
    try {
      setLoading(true);
      setError("");
      const session = await api.startProspectingSession(workspaceId, {
        list_id: selectedListId || null,
        motion: sessionMotion,
        target_calls: targetCalls,
      });
      setActiveSession(session);
      setElapsedSeconds(0);
      const context = await api.getProspectingCockpit(workspaceId, session.id);
      setCockpit(context);
      setCallNotes("");
      if (context.cards.length > 0) {
        setSelectedCard(context.cards[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao iniciar sessão de prospecção.");
    } finally {
      setLoading(false);
    }
  };

  const handleRecordDisposition = async (
    disposition: "unanswered" | "busy" | "wrong_number" | "not_interested" | "follow_up" | "meeting_scheduled",
    handoffData?: any,
    customFollowUpDate?: string
  ) => {
    if (!workspaceId || !activeSession || !cockpit?.current_item) return;
    try {
      setLoading(true);
      setError("");
      const effectiveFollowUp = customFollowUpDate !== undefined ? customFollowUpDate : followUpDate;
      const updatedContext = await api.recordProspectingDisposition(workspaceId, activeSession.id, {
        item_id: cockpit.current_item.id,
        disposition,
        notes: callNotes.trim() || undefined,
        scheduled_follow_up_at: disposition === "follow_up" && effectiveFollowUp ? effectiveFollowUp : undefined,
        handoff: handoffData || undefined,
      });
      setCockpit(updatedContext);
      setActiveSession(updatedContext.session);
      setCallNotes("");
      setFollowUpDate("");
      setShowFollowUpModal(false);
      setShowHandoffModal(false);

      if (disposition === "meeting_scheduled") {
        setSuccessMsg("🎉 Reunião agendada com sucesso! Briefing e oportunidade enviados ao Copiloto do Closer.");
        setTimeout(() => setSuccessMsg(""), 6000);
      } else if (disposition === "follow_up") {
        setSuccessMsg("📅 Retorno agendado com sucesso!");
        setTimeout(() => setSuccessMsg(""), 4000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao registrar disposição.");
    } finally {
      setLoading(false);
    }
  };

  const handleFinishSession = async () => {
    if (!workspaceId || !activeSession) return;
    try {
      setLoading(true);
      const finished = await api.finishProspectingSession(workspaceId, activeSession.id);
      setActiveSession(null);
      setCockpit(null);
      setSuccessMsg(`Sessão finalizada com sucesso! Total de toques: ${finished.completed_calls}. Reuniões: ${finished.meetings_booked}.`);
      setTimeout(() => setSuccessMsg(""), 6000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao encerrar sessão.");
    } finally {
      setLoading(false);
    }
  };

  const filteredCards = useMemo(() => {
    return cards.filter((card) => {
      const matchesMotion =
        cardMotionFilter === "all" || card.motion === "cross_motion" || card.motion === cardMotionFilter;
      const term = cardSearchQuery.toLowerCase().trim();
      const matchesSearch =
        !term ||
        card.title.toLowerCase().includes(term) ||
        card.code.toLowerCase().includes(term) ||
        (card.ask_first && card.ask_first.toLowerCase().includes(term)) ||
        card.aliases.some((a) => a.toLowerCase().includes(term));
      return matchesMotion && matchesSearch;
    });
  }, [cards, cardSearchQuery, cardMotionFilter]);

  const currentItem = cockpit?.current_item;

  // WhatsApp Opener builder
  const getWhatsAppOpener = (item: ProspectingListItem) => {
    const contact = item.contact_name ? item.contact_name.split(" ")[0] : "Olá";
    if (sessionMotion === "growth") {
      return `Oi, ${contact}. Dei uma olhada na operação da ${item.company_name} e fiquei com uma dúvida: hoje as novas oportunidades de clientes vêm de canais previsíveis ou ainda depende bastante de indicação e boca a boca?`;
    }
    return `Oi, ${contact}. Tenho olhado para empresas do setor de ${item.category || "serviços"} em que processos operacionais repetitivos começam a travar o crescimento da equipe. Existe alguma rotina por aí na ${item.company_name} que vocês sentem ser muito manual?`;
  };

  return (
    <div style={{ padding: "24px", maxWidth: "1500px", margin: "0 auto", color: "var(--text)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "10px" }}>
            <Flame color="var(--brand-accent)" size={28} /> Sales & Prospecting OS
          </h1>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: "0.88rem" }}>
            Cockpit de Prospecção Ativa, Fila de Ligações com Disposição Rápida e Battlecards Dinâmicos.
          </p>
        </div>

        {/* Tab Buttons */}
        <div style={{ display: "flex", background: "var(--bg-inset)", padding: "4px", borderRadius: "10px", border: "1px solid var(--border)" }}>
          <button
            onClick={() => setActiveTab("cockpit")}
            style={{
              padding: "7px 16px",
              borderRadius: "8px",
              border: "none",
              fontSize: "0.85rem",
              fontWeight: 600,
              cursor: "pointer",
              background: activeTab === "cockpit" ? "var(--brand-accent)" : "transparent",
              color: activeTab === "cockpit" ? "#000" : "var(--text)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <Compass size={15} /> Cockpit & Sessão
          </button>
          <button
            onClick={() => setActiveTab("lists")}
            style={{
              padding: "7px 16px",
              borderRadius: "8px",
              border: "none",
              fontSize: "0.85rem",
              fontWeight: 600,
              cursor: "pointer",
              background: activeTab === "lists" ? "var(--brand-accent)" : "transparent",
              color: activeTab === "lists" ? "#000" : "var(--text)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <Phone size={15} /> Listas ({lists.length})
          </button>
          <button
            onClick={() => setActiveTab("knowledge")}
            style={{
              padding: "7px 16px",
              borderRadius: "8px",
              border: "none",
              fontSize: "0.85rem",
              fontWeight: 600,
              cursor: "pointer",
              background: activeTab === "knowledge" ? "var(--brand-accent)" : "transparent",
              color: activeTab === "knowledge" ? "#000" : "var(--text)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <BookOpen size={15} /> Playbooks & Battlecards ({cards.length})
          </button>
        </div>
      </div>

      {successMsg && (
        <div className="notice" style={{ background: "rgba(58, 201, 123, 0.15)", border: "1px solid var(--mint)", color: "var(--mint)", marginBottom: 16 }}>
          {successMsg}
        </div>
      )}
      {error && (
        <div className="notice error" style={{ marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* TAB 1: COCKPIT DE SESSÃO */}
      {activeTab === "cockpit" && (
        <div>
          {!activeSession ? (
            /* Launcher de Nova Sessão */
            <div className="surface" style={{ padding: "32px", borderRadius: "14px", maxWidth: "680px", margin: "20px auto", border: "1px solid var(--border)" }}>
              <div style={{ textAlign: "center", marginBottom: "24px" }}>
                <div style={{ width: "56px", height: "56px", borderRadius: "50%", background: "rgba(58, 201, 123, 0.12)", color: "var(--brand-accent)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
                  <Zap size={28} />
                </div>
                <h2 style={{ fontSize: "1.3rem", fontWeight: 700, margin: "0 0 6px" }}>Iniciar Sessão de Prospecção (Focus Mode)</h2>
                <p style={{ color: "var(--text-dim)", fontSize: "0.88rem", margin: 0 }}>
                  Defina o bloco de foco para disparar ligações em sequência com auxílio dos Battlecards e Disposição Rápida.
                </p>
              </div>

              <div style={{ display: "grid", gap: "16px" }}>
                <div>
                  <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-dim)", display: "block", marginBottom: 6 }}>
                    Lista de Prospecção Alvo *
                  </label>
                  <select
                    value={selectedListId}
                    onChange={(e) => setSelectedListId(e.target.value)}
                    style={{ width: "100%", padding: "10px 14px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)" }}
                  >
                    <option value="">Selecione uma lista...</option>
                    {lists.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.title} ({l.total_leads} leads · {l.source})
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-dim)", display: "block", marginBottom: 6 }}>
                      Commercial Motion
                    </label>
                    <select
                      value={sessionMotion}
                      onChange={(e) => setSessionMotion(e.target.value as any)}
                      style={{ width: "100%", padding: "10px 14px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)" }}
                    >
                      <option value="growth">Motion Growth (Vendas & Aquisição)</option>
                      <option value="ai_automation">Motion AI & Automation (Processos Manuais)</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-dim)", display: "block", marginBottom: 6 }}>
                      Meta de Ligações / Tentativas
                    </label>
                    <input
                      type="number"
                      min={5}
                      max={150}
                      value={targetCalls}
                      onChange={(e) => setTargetCalls(Number(e.target.value))}
                      style={{ width: "100%", padding: "10px 14px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)" }}
                    />
                  </div>
                </div>

                <button
                  className="primary-button"
                  disabled={!selectedListId || loading}
                  onClick={() => void startSession()}
                  style={{ width: "100%", padding: "12px", justifyContent: "center", fontSize: "0.95rem", fontWeight: 700, marginTop: "8px" }}
                >
                  <Play size={18} /> Iniciar Bloco de Prospecção
                </button>
              </div>
            </div>
          ) : (
            /* Cockpit Ativo de Prospecção */
            <div style={{ display: "grid", gap: "18px" }}>
              {/* Header do Cockpit Ativo com Cronômetro e KPIs */}
              <div
                className="surface"
                style={{
                  padding: "16px 20px",
                  borderRadius: "12px",
                  border: "1px solid var(--border)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: "14px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "rgba(239, 68, 68, 0.12)", color: "#ef4444", padding: "6px 14px", borderRadius: "20px", fontSize: "0.85rem", fontWeight: 700 }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#ef4444", animation: "pulse 1.5s infinite" }} />
                    SESSÃO ATIVA
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "1.1rem", fontWeight: 700, fontFamily: "monospace" }}>
                    <Clock size={18} color="var(--brand-accent)" /> {formatTimer(elapsedSeconds)}
                  </div>
                  <span style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>
                    Motion: <strong style={{ color: "var(--text)" }}>{activeSession.motion === "growth" ? "Growth" : "AI & Automation"}</strong>
                  </span>
                </div>

                {/* KPIs da Sessão */}
                <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                  <div style={{ textAlign: "center" }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Progresso</span>
                    <strong style={{ display: "block", fontSize: "1.05rem" }}>
                      {activeSession.completed_calls} / {activeSession.target_calls}
                    </strong>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Conexões</span>
                    <strong style={{ display: "block", fontSize: "1.05rem", color: "var(--brand-accent)" }}>
                      {activeSession.connections_count}
                    </strong>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Conversas</span>
                    <strong style={{ display: "block", fontSize: "1.05rem", color: "#60a5fa" }}>
                      {activeSession.conversations_count}
                    </strong>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Reuniões ⭐</span>
                    <strong style={{ display: "block", fontSize: "1.05rem", color: "var(--mint)" }}>
                      {activeSession.meetings_booked}
                    </strong>
                  </div>

                  <button
                    className="secondary-button"
                    onClick={() => void handleFinishSession()}
                    style={{ borderColor: "rgba(239, 68, 68, 0.4)", color: "#ef4444", padding: "6px 14px", fontSize: "0.82rem" }}
                  >
                    <StopCircle size={15} /> Encerrar Sessão
                  </button>
                </div>
              </div>

              {/* Grid Principal: Cartão do Lead em Foco vs. Battlecards Overlay */}
              <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "18px", alignItems: "start" }}>
                {/* Coluna Esquerda: Lead em Foco */}
                <div className="surface" style={{ padding: "24px", borderRadius: "12px", border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: "18px" }}>
                  {!currentItem ? (
                    <div style={{ textAlign: "center", padding: "60px 20px" }}>
                      <CheckCircle2 size={48} color="var(--mint)" style={{ margin: "0 auto 12px" }} />
                      <h3 style={{ fontSize: "1.2rem", fontWeight: 700 }}>Fila da Sessão Concluída!</h3>
                      <p style={{ color: "var(--text-dim)", fontSize: "0.88rem" }}>
                        Você passou por todos os leads pendentes desta lista.
                      </p>
                      <button className="primary-button" onClick={() => void handleFinishSession()} style={{ margin: "16px auto 0" }}>
                        Ver Resumo da Sessão
                      </button>
                    </div>
                  ) : (
                    <>
                      {/* Soft Warning Banner se houver conflito de dono / histórico */}
                      {currentItem.ownership_warning && (
                        <div
                          style={{
                            background: "rgba(245, 158, 11, 0.12)",
                            border: "1px solid rgba(245, 158, 11, 0.3)",
                            borderRadius: "8px",
                            padding: "10px 14px",
                            display: "flex",
                            alignItems: "center",
                            gap: "10px",
                            color: "#fbbf24",
                            fontSize: "0.85rem",
                          }}
                        >
                          <ShieldAlert size={18} />
                          <div>
                            <strong>Alerta de Histórico / Dono:</strong> {currentItem.ownership_warning.warning_label}
                          </div>
                        </div>
                      )}

                      {/* Header do Lead */}
                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
                          <div>
                            <h2 style={{ fontSize: "1.35rem", fontWeight: 700, margin: "0 0 4px" }}>
                              {currentItem.company_name}
                            </h2>
                            <span style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>
                              {currentItem.contact_name ? `Contato: ${currentItem.contact_name} · ` : ""}
                              Setor: {currentItem.category || "Não informado"}
                            </span>
                          </div>

                          <div style={{ display: "flex", gap: "8px" }}>
                            {currentItem.rating && (
                              <span style={{ background: "rgba(234, 179, 8, 0.15)", color: "#facc15", padding: "4px 10px", borderRadius: "12px", fontSize: "0.78rem", fontWeight: 700 }}>
                                ★ {currentItem.rating} ({currentItem.reviews_count} avaliações)
                              </span>
                            )}
                            <span style={{ background: "rgba(58, 201, 123, 0.15)", color: "var(--mint)", padding: "4px 10px", borderRadius: "12px", fontSize: "0.78rem", fontWeight: 700 }}>
                              Presença {currentItem.presence_score}/100
                            </span>
                          </div>
                        </div>

                        {currentItem.address && (
                          <p style={{ fontSize: "0.82rem", color: "var(--text-dim)", margin: "8px 0 0" }}>
                            📍 {currentItem.address}
                          </p>
                        )}
                      </div>

                      {/* Botões de Ação Imediata: Tel, WhatsApp, Links */}
                      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", padding: "14px", background: "var(--bg-inset)", borderRadius: "10px", border: "1px solid var(--border)" }}>
                        {currentItem.phone ? (
                          <>
                            <a
                              href={`tel:${currentItem.phone}`}
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "6px",
                                background: "var(--brand-accent)",
                                color: "#000",
                                padding: "8px 14px",
                                borderRadius: "8px",
                                fontSize: "0.88rem",
                                fontWeight: 700,
                                textDecoration: "none",
                              }}
                            >
                              <PhoneCall size={16} /> Ligar: {currentItem.phone}
                            </a>

                            <button
                              className="secondary-button"
                              onClick={() => {
                                navigator.clipboard.writeText(currentItem.phone || "");
                                setSuccessMsg("Telefone copiado!");
                                setTimeout(() => setSuccessMsg(""), 2000);
                              }}
                              style={{ padding: "8px 10px" }}
                              title="Copiar telefone"
                            >
                              <Copy size={15} />
                            </button>

                            {(() => {
                              const digits = currentItem.phone.replace(/\D/g, "");
                              const waNumber = digits.length <= 11 && !digits.startsWith("55") ? `55${digits}` : digits;
                              return (
                                <a
                                  href={`https://wa.me/${waNumber}?text=${encodeURIComponent(getWhatsAppOpener(currentItem))}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "6px",
                                    background: "#25D366",
                                    color: "#fff",
                                    padding: "8px 14px",
                                    borderRadius: "8px",
                                    fontSize: "0.88rem",
                                    fontWeight: 700,
                                    textDecoration: "none",
                                  }}
                                >
                                  <MessageSquare size={16} /> WhatsApp Opener
                                </a>
                              );
                            })()}
                          </>
                        ) : (
                          <span style={{ color: "var(--text-dim)", fontSize: "0.85rem" }}>Telefone não localizado.</span>
                        )}

                        {currentItem.website && (
                          <a
                            href={currentItem.website.startsWith("http") ? currentItem.website : `https://${currentItem.website}`}
                            target="_blank"
                            rel="noreferrer"
                            className="secondary-button"
                            style={{ display: "inline-flex", alignItems: "center", gap: "6px", textDecoration: "none", padding: "8px 12px" }}
                          >
                            <ExternalLink size={14} /> Website
                          </a>
                        )}
                        {currentItem.instagram && (
                          <a
                            href={currentItem.instagram}
                            target="_blank"
                            rel="noreferrer"
                            className="secondary-button"
                            style={{ display: "inline-flex", alignItems: "center", gap: "6px", textDecoration: "none", padding: "8px 12px" }}
                          >
                            Instagram
                          </a>
                        )}
                      </div>

                      {/* Anotações da Chamada */}
                      <div>
                        <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-dim)", display: "block", marginBottom: 6 }}>
                          Anotações da Conversa / Dores Relatadas
                        </label>
                        <textarea
                          rows={3}
                          value={callNotes}
                          onChange={(e) => setCallNotes(e.target.value)}
                          placeholder="Ex: Falou com Dra. Marina; disse que indicação oscila muito no inverno; já tem agência só pra posts..."
                          style={{ width: "100%", padding: "10px 14px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)", fontSize: "0.88rem", resize: "vertical" }}
                        />
                      </div>

                      {/* RÉGUA DE DISPOSIÇÃO RÁPIDA */}
                      <div>
                        <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", display: "block", marginBottom: 8 }}>
                          Disposição Rápida do Toque
                        </span>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "8px" }}>
                          <button
                            disabled={loading}
                            onClick={() => void handleRecordDisposition("unanswered")}
                            style={{ padding: "10px 6px", borderRadius: "8px", border: "1px solid rgba(239, 68, 68, 0.3)", background: "rgba(239, 68, 68, 0.08)", color: "#ef4444", fontSize: "0.78rem", fontWeight: 700, cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}
                          >
                            <PhoneMissed size={16} /> Não Atendeu
                          </button>

                          <button
                            disabled={loading}
                            onClick={() => void handleRecordDisposition("busy")}
                            style={{ padding: "10px 6px", borderRadius: "8px", border: "1px solid rgba(245, 158, 11, 0.3)", background: "rgba(245, 158, 11, 0.08)", color: "#f59e0b", fontSize: "0.78rem", fontWeight: 700, cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}
                          >
                            <RotateCcw size={16} /> Ocupado
                          </button>

                          <button
                            disabled={loading}
                            onClick={() => void handleRecordDisposition("not_interested")}
                            style={{ padding: "10px 6px", borderRadius: "8px", border: "1px solid var(--border)", background: "var(--bg-inset)", color: "var(--text-dim)", fontSize: "0.78rem", fontWeight: 700, cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}
                          >
                            <ThumbsDown size={16} /> Sem Interesse
                          </button>

                          <button
                            disabled={loading}
                            onClick={() => {
                              setShowFollowUpModal(true);
                            }}
                            style={{ padding: "10px 6px", borderRadius: "8px", border: "1px solid rgba(59, 130, 246, 0.3)", background: "rgba(59, 130, 246, 0.08)", color: "#60a5fa", fontSize: "0.78rem", fontWeight: 700, cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}
                          >
                            <PhoneForwarded size={16} /> Follow-up
                          </button>

                          <button
                            disabled={loading}
                            onClick={() => {
                              setHandoffProblem(callNotes);
                              setShowHandoffModal(true);
                            }}
                            style={{ padding: "10px 6px", borderRadius: "8px", border: "none", background: "var(--brand-accent)", color: "#000", fontSize: "0.78rem", fontWeight: 800, cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}
                          >
                            <Sparkles size={16} /> Agendar Reunião
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>

                {/* Coluna Direita: Live Battlecards & Playbooks Overlay */}
                <div className="surface" style={{ padding: "20px", borderRadius: "12px", border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: "14px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h3 style={{ fontSize: "1rem", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                      <BookOpen size={18} color="var(--brand-accent)" /> Playbooks & Battlecards (<span style={{ color: "var(--brand-accent)" }}>&lt; 5s</span>)
                    </h3>
                    <span style={{ fontSize: "0.75rem", background: "var(--bg-inset)", padding: "3px 8px", borderRadius: "6px", color: "var(--text-dim)" }}>
                      Call Mode
                    </span>
                  </div>

                  {/* Campo de Busca Rápida de Objeções */}
                  <div style={{ position: "relative" }}>
                    <Search size={15} style={{ position: "absolute", left: "10px", top: "10px", color: "var(--text-dim)" }} />
                    <input
                      type="text"
                      placeholder="Buscar objeção (ex: agência, caro, ERP, IA)..."
                      value={cardSearchQuery}
                      onChange={(e) => setCardSearchQuery(e.target.value)}
                      style={{ width: "100%", padding: "8px 10px 8px 32px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)", fontSize: "0.84rem" }}
                    />
                  </div>

                  {/* Chips de Objeções Mais Comuns */}
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {cards.slice(0, 5).map((card) => (
                      <button
                        key={card.id}
                        onClick={() => setSelectedCard(card)}
                        style={{
                          padding: "4px 10px",
                          borderRadius: "14px",
                          border: selectedCard?.id === card.id ? "1px solid var(--brand-accent)" : "1px solid var(--border)",
                          background: selectedCard?.id === card.id ? "rgba(58, 201, 123, 0.15)" : "var(--bg-inset)",
                          color: selectedCard?.id === card.id ? "var(--brand-accent)" : "var(--text)",
                          fontSize: "0.76rem",
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        {card.title}
                      </button>
                    ))}
                  </div>

                  {/* Cartão Selecionado em Foco */}
                  {selectedCard ? (
                    <div style={{ background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <strong style={{ fontSize: "0.95rem", color: "var(--brand-accent)" }}>
                          [{selectedCard.code}] {selectedCard.title}
                        </strong>
                        <span style={{ fontSize: "0.72rem", background: "var(--surface)", padding: "2px 8px", borderRadius: "6px" }}>
                          {selectedCard.status}
                        </span>
                      </div>

                      {/* Pergunte Primeiro */}
                      {selectedCard.ask_first && (
                        <div style={{ background: "rgba(58, 201, 123, 0.08)", borderLeft: "3px solid var(--brand-accent)", padding: "10px 12px", borderRadius: "0 8px 8px 0" }}>
                          <span style={{ fontSize: "0.74rem", fontWeight: 700, color: "var(--mint)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                            🎯 Pergunte Primeiro (Discovery)
                          </span>
                          <p style={{ margin: 0, fontSize: "0.88rem", fontWeight: 600, color: "var(--text)" }}>
                            “{selectedCard.ask_first}”
                          </p>
                        </div>
                      )}

                      {/* Talk Track para Ligação */}
                      {selectedCard.call_talk_track && (
                        <div>
                          <span style={{ fontSize: "0.74rem", fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                            💬 Talk Track para Ligação
                          </span>
                          <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>
                            {selectedCard.call_talk_track}
                          </p>
                        </div>
                      )}

                      {/* O que Evitar */}
                      {selectedCard.avoid && selectedCard.avoid.length > 0 && (
                        <div style={{ background: "rgba(239, 68, 68, 0.08)", borderLeft: "3px solid #ef4444", padding: "8px 12px", borderRadius: "0 8px 8px 0" }}>
                          <span style={{ fontSize: "0.74rem", fontWeight: 700, color: "#ef4444", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                            🚫 O Que Evitar
                          </span>
                          <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "0.82rem", color: "var(--text-dim)" }}>
                            {selectedCard.avoid.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Branches / Caminhos de Resposta */}
                      {selectedCard.branches && selectedCard.branches.length > 0 && (
                        <div>
                          <span style={{ fontSize: "0.74rem", fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", display: "block", marginBottom: 6 }}>
                            🔀 Branches de Resposta
                          </span>
                          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                            {selectedCard.branches.map((b, idx) => (
                              <div key={idx} style={{ padding: "6px 10px", background: "var(--surface)", borderRadius: "6px", fontSize: "0.78rem" }}>
                                <strong style={{ color: "var(--brand-accent)" }}>Se {b.condition}:</strong> {b.action}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ textAlign: "center", padding: "40px 10px", color: "var(--text-dim)", fontSize: "0.85rem" }}>
                      Selecione um battlecard para ver o roteiro em tempo real.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: LISTAS DE PROSPECÇÃO */}
      {activeTab === "lists" && (
        <div className="surface" style={{ padding: "24px", borderRadius: "12px", border: "1px solid var(--border)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h2 style={{ fontSize: "1.2rem", fontWeight: 700, margin: 0 }}>Listas de Prospecção Salvas</h2>
            <span style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>
              Listas são criadas automaticamente ao exportar do <strong>Radar Local</strong> ou CRM.
            </span>
          </div>

          {lists.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--text-dim)" }}>
              Nenhuma lista de prospecção criada ainda. Vá até <strong>Radar Local</strong> e selecione leads para exportar!
            </div>
          ) : (
            <div style={{ display: "grid", gap: "12px" }}>
              {lists.map((l) => (
                <div
                  key={l.id}
                  style={{
                    padding: "16px 20px",
                    background: "var(--bg-inset)",
                    borderRadius: "10px",
                    border: "1px solid var(--border)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <h4 style={{ margin: "0 0 4px", fontSize: "1rem", fontWeight: 700 }}>{l.title}</h4>
                    <span style={{ fontSize: "0.82rem", color: "var(--text-dim)" }}>
                      Origem: <strong>{l.source}</strong> · {l.total_leads} leads no total
                      {l.pending_leads !== undefined ? ` · ${l.pending_leads} pendentes` : ""}
                    </span>
                  </div>

                  <button
                    className="primary-button"
                    onClick={() => {
                      setSelectedListId(l.id);
                      setActiveTab("cockpit");
                    }}
                    style={{ fontSize: "0.82rem", padding: "8px 16px" }}
                  >
                    Iniciar Sessão Nesta Lista <ArrowRight size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: BASE DE CONHECIMENTO & PLAYBOOKS */}
      {activeTab === "knowledge" && (
        <div className="surface" style={{ padding: "24px", borderRadius: "12px", border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
            <div>
              <h2 style={{ fontSize: "1.2rem", fontWeight: 700, margin: 0 }}>Sales Knowledge & Battlecards (PostgreSQL)</h2>
              <span style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>
                Conhecimento comercial vivo com governança editorial da metodologia EverGreen.
              </span>
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              <select
                value={cardMotionFilter}
                onChange={(e) => setCardMotionFilter(e.target.value)}
                style={{ padding: "8px 12px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)", fontSize: "0.82rem" }}
              >
                <option value="all">Todos os Motions</option>
                <option value="growth">Growth</option>
                <option value="ai_automation">AI & Automation</option>
              </select>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: "14px" }}>
            {filteredCards.map((card) => (
              <div
                key={card.id}
                style={{
                  padding: "16px",
                  background: "var(--bg-inset)",
                  borderRadius: "10px",
                  border: "1px solid var(--border)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <span style={{ fontSize: "0.72rem", color: "var(--brand-accent)", fontWeight: 700 }}>
                      [{card.code}] · {card.card_type.toUpperCase()}
                    </span>
                    <h4 style={{ margin: "2px 0 0", fontSize: "0.95rem", fontWeight: 700 }}>{card.title}</h4>
                  </div>
                  <span style={{ fontSize: "0.72rem", background: "var(--surface)", padding: "2px 8px", borderRadius: "6px" }}>
                    {card.status}
                  </span>
                </div>

                {card.ask_first && (
                  <div style={{ background: "rgba(58, 201, 123, 0.08)", padding: "8px 10px", borderRadius: "6px", fontSize: "0.82rem" }}>
                    <strong style={{ color: "var(--mint)", display: "block", fontSize: "0.72rem", textTransform: "uppercase" }}>Pergunte Primeiro:</strong>
                    “{card.ask_first}”
                  </div>
                )}

                {card.call_talk_track && (
                  <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    {card.call_talk_track}
                  </p>
                )}

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "auto", paddingTop: "8px", borderTop: "1px solid var(--border)" }}>
                  <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>Motion: {card.motion}</span>
                  <button
                    className="secondary-button"
                    onClick={async () => {
                      const nextStatus = card.status === "VALIDATED" ? "TESTING" : "VALIDATED";
                      await api.updateProspectingCardStatus(workspaceId, card.id, nextStatus as any);
                      void loadData();
                    }}
                    style={{ fontSize: "0.72rem", padding: "4px 8px" }}
                  >
                    Marcar {card.status === "VALIDATED" ? "TESTING" : "VALIDATED"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL DE HANDOFF ESTRUTURADO (SDR -> CLOSER) */}
      {showHandoffModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "20px",
          }}
        >
          <div
            className="surface"
            style={{
              width: "100%",
              maxWidth: "580px",
              padding: "28px",
              borderRadius: "14px",
              border: "1px solid var(--border)",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <Sparkles size={24} color="var(--brand-accent)" />
              <div>
                <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700 }}>Handoff Estruturado para o Closer</h3>
                <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
                  Preencha os 3 vetores canônicos para alimentar automaticamente o <strong>Copiloto de Vendas</strong>.
                </span>
              </div>
            </div>

            <div>
              <label style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>
                1. Dor / Problema Principal Identificado *
              </label>
              <textarea
                rows={2}
                value={handoffProblem}
                onChange={(e) => setHandoffProblem(e.target.value)}
                placeholder="Ex: Aquisição depende 80% do fundador; mês de julho caiu 40%..."
                style={{ width: "100%", padding: "10px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)", fontSize: "0.86rem" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>
                2. Impacto Declarado pelo Prospect *
              </label>
              <textarea
                rows={2}
                value={handoffImpact}
                onChange={(e) => setHandoffImpact(e.target.value)}
                placeholder="Ex: Não conseguem planejar contratações sem previsibilidade de faturamento..."
                style={{ width: "100%", padding: "10px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)", fontSize: "0.86rem" }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>
                  Data/Hora da Reunião *
                </label>
                <input
                  type="text"
                  value={handoffMeetingAt}
                  onChange={(e) => setHandoffMeetingAt(e.target.value)}
                  placeholder="Ex: Sexta-feira, 26/10 às 15:00"
                  style={{ width: "100%", padding: "10px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)", fontSize: "0.86rem" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>
                  Motion Provável
                </label>
                <select
                  value={sessionMotion}
                  onChange={(e) => setSessionMotion(e.target.value as any)}
                  style={{ width: "100%", padding: "10px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)", fontSize: "0.86rem" }}
                >
                  <option value="growth">Motion Growth</option>
                  <option value="ai_automation">Motion AI & Automation</option>
                </select>
              </div>
            </div>

            <div>
              <label style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>
                Notas Adicionais para o Closer
              </label>
              <input
                type="text"
                value={handoffCloserNotes}
                onChange={(e) => setHandoffCloserNotes(e.target.value)}
                placeholder="Ex: Falar direto com o sócio que também estará presente..."
                style={{ width: "100%", padding: "10px", background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", color: "var(--text)", fontSize: "0.86rem" }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
              <button className="secondary-button" onClick={() => setShowHandoffModal(false)}>
                Cancelar
              </button>
              <button
                className="primary-button"
                disabled={!handoffProblem.trim() || !handoffMeetingAt.trim() || loading}
                onClick={() =>
                  void handleRecordDisposition("meeting_scheduled", {
                    problem: handoffProblem.trim(),
                    impact: handoffImpact.trim() || "Não mensurado em números",
                    motion: sessionMotion,
                    meeting_at: handoffMeetingAt.trim(),
                    closer_notes: handoffCloserNotes.trim() || undefined,
                  })
                }
              >
                Confirmar Reunião & Gerar Briefing
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL DE FOLLOW-UP RÁPIDO */}
      {showFollowUpModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "20px",
          }}
        >
          <div
            className="surface"
            style={{
              width: "100%",
              maxWidth: "480px",
              padding: "24px",
              borderRadius: "14px",
              border: "1px solid var(--border)",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <PhoneForwarded size={22} color="#60a5fa" />
              <div>
                <h3 style={{ margin: 0, fontSize: "1.15rem", fontWeight: 700 }}>Agendar Retorno (Follow-up)</h3>
                <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
                  Defina quando o Bioma deve recolocar este prospect na fila prioritária.
                </span>
              </div>
            </div>

            {/* Presets Rápidos */}
            <div>
              <label style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-dim)", display: "block", marginBottom: 6 }}>
                Atalhos Rápidos:
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    const d = new Date();
                    d.setHours(17, 0, 0, 0);
                    setFollowUpDate(d.toISOString().slice(0, 16));
                  }}
                  style={{ fontSize: "0.8rem", padding: "8px" }}
                >
                  Hoje às 17h
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    const d = new Date();
                    d.setDate(d.getDate() + 1);
                    d.setHours(10, 0, 0, 0);
                    setFollowUpDate(d.toISOString().slice(0, 16));
                  }}
                  style={{ fontSize: "0.8rem", padding: "8px" }}
                >
                  Amanhã às 10h
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    const d = new Date();
                    d.setDate(d.getDate() + 1);
                    d.setHours(15, 0, 0, 0);
                    setFollowUpDate(d.toISOString().slice(0, 16));
                  }}
                  style={{ fontSize: "0.8rem", padding: "8px" }}
                >
                  Amanhã às 15h
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    const d = new Date();
                    d.setDate(d.getDate() + 3);
                    d.setHours(14, 0, 0, 0);
                    setFollowUpDate(d.toISOString().slice(0, 16));
                  }}
                  style={{ fontSize: "0.8rem", padding: "8px" }}
                >
                  Em 3 dias (14h)
                </button>
              </div>
            </div>

            {/* Input Manual Datetime */}
            <div>
              <label style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-dim)", display: "block", marginBottom: 6 }}>
                Ou escolha data e horário específico:
              </label>
              <input
                type="datetime-local"
                value={followUpDate}
                onChange={(e) => setFollowUpDate(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px",
                  background: "var(--bg-inset)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  color: "var(--text)",
                  fontSize: "0.88rem",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  setShowFollowUpModal(false);
                  setFollowUpDate("");
                }}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="primary-button"
                disabled={loading}
                onClick={() => {
                  const isoDate = followUpDate ? new Date(followUpDate).toISOString() : undefined;
                  void handleRecordDisposition("follow_up", undefined, isoDate);
                }}
                style={{ background: "#3b82f6", color: "#fff" }}
              >
                Confirmar Agendamento
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
