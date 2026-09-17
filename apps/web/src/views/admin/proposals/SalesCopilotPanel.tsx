import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Bot,
  Brain,
  CheckCircle2,
  Clock,
  FileAudio,
  GitBranch,
  Headphones,
  KeyRound,
  Loader2,
  Mic,
  Play,
  Plus,
  Radio,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Square,
  UserPlus,
  Users,
  Video,
} from "lucide-react";

import {
  api,
  type ClientSummary,
  type FathomMeeting,
  type OpportunitySummary,
  type ProposalSummary,
  type SalesCopilotMetrics,
  type SalesCopilotRealtimeStatus,
  type SalesCopilotSession,
} from "../../../lib/api";

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 14px",
  background: "var(--bg-inset)",
  border: "1px solid var(--border)",
  borderRadius: "8px",
  color: "var(--text)",
  fontSize: "0.88rem",
  outline: "none",
  boxSizing: "border-box",
  transition: "border-color 0.2s, box-shadow 0.2s",
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  cursor: "pointer",
};

export function SalesCopilotPanel({ proposals }: { proposals: ProposalSummary[] }) {
  const [sessions, setSessions] = useState<SalesCopilotSession[]>([]);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([]);
  const [metrics, setMetrics] = useState<SalesCopilotMetrics | null>(null);
  const [adapter, setAdapter] = useState<SalesCopilotRealtimeStatus | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [title, setTitle] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");
  const [opportunityId, setOpportunityId] = useState("");
  const [proposalId, setProposalId] = useState("");
  const [objective, setObjective] = useState("");
  const [transcriptChunk, setTranscriptChunk] = useState("");
  const [speakerId, setSpeakerId] = useState("");
  const [meetingProvider, setMeetingProvider] = useState<"manual" | "google_meet" | "microsoft_teams">("manual");
  const [meetingUrl, setMeetingUrl] = useState("");
  const [consentGranted, setConsentGranted] = useState(false);
  const [fathomMeetings, setFathomMeetings] = useState<FathomMeeting[] | null>(null);
  const [fathomFeedback, setFathomFeedback] = useState("");
  const [participantName, setParticipantName] = useState("");
  const [participantTitle, setParticipantTitle] = useState("");
  const [participantGroup, setParticipantGroup] = useState<"eg_team" | "client" | "partner" | "unknown">("client");
  const [actionTitle, setActionTitle] = useState("");
  const [adapterCredential, setAdapterCredential] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const replaceSession = (session: SalesCopilotSession) => {
    setSessions((current) => [session, ...current.filter((item) => item.id !== session.id)]);
    setSelectedId(session.id);
  };

  const load = async () => {
    const [sessionRows, clientRows, opportunityRows, metricData, adapterData] = await Promise.all([
      api.salesCopilotSessions(),
      api.clients(),
      api.listOpportunities(),
      api.salesCopilotMetrics(),
      api.salesCopilotRealtimeStatus(),
    ]);
    setSessions(sessionRows);
    setClients(clientRows.filter((client) => client.status !== "archived"));
    setOpportunities(opportunityRows.filter((item) => !["archived", "rejected", "lost"].includes(item.status)));
    setMetrics(metricData);
    setAdapter(adapterData);
    setSelectedId((current) => current || sessionRows[0]?.id || "");
  };

  useEffect(() => {
    void load().catch((err) => setError(err instanceof Error ? err.message : "Falha ao carregar o Copiloto."));
  }, []);

  useEffect(() => {
    const selected = sessions.find((session) => session.id === selectedId);
    if (!selected || selected.status !== "active") return;
    const timer = window.setInterval(() => {
      void api.salesCopilotSession(selected.id).then(replaceSession).catch(() => undefined);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [selectedId, sessions]);

  const selected = sessions.find((session) => session.id === selectedId);

  const run = async (label: string, action: () => Promise<SalesCopilotSession>) => {
    setBusy(label);
    setError("");
    try {
      replaceSession(await action());
      const metricData = await api.salesCopilotMetrics();
      setMetrics(metricData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível concluir a ação.");
    } finally {
      setBusy("");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <span style={{ background: "rgba(58, 201, 123, 0.2)", color: "var(--mint)", padding: "3px 10px", borderRadius: "12px", fontSize: "0.75rem", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: "4px" }}><Radio size={12} className="animate-pulse" /> Em Andamento</span>;
      case "completed":
        return <span style={{ background: "rgba(59, 130, 246, 0.2)", color: "#60a5fa", padding: "3px 10px", borderRadius: "12px", fontSize: "0.75rem", fontWeight: 700 }}>Concluída</span>;
      default:
        return <span style={{ background: "rgba(245, 158, 11, 0.2)", color: "#fbbf24", padding: "3px 10px", borderRadius: "12px", fontSize: "0.75rem", fontWeight: 700 }}>Rascunho</span>;
    }
  };

  return (
    <div style={{ display: "grid", gap: 20 }}>
      {/* Banner Adaptador Real-Time */}
      <div
        style={{
          background: adapter?.available ? "rgba(58, 201, 123, 0.08)" : "rgba(255, 255, 255, 0.03)",
          border: `1px solid ${adapter?.available ? "rgba(58, 201, 123, 0.25)" : "var(--border)"}`,
          borderRadius: "10px",
          padding: "14px 18px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Headphones size={22} color={adapter?.available ? "var(--mint)" : "var(--text-dim)"} />
          <div>
            <strong style={{ fontSize: "0.92rem", display: "block" }}>Adaptador de Transcrição Automática</strong>
            <span style={{ fontSize: "0.82rem", color: "var(--text-dim)" }}>
              {adapter?.message ?? "Verificando estado dos conectores Google Meet e Microsoft Teams..."}
            </span>
          </div>
        </div>
        <span style={{ fontSize: "0.78rem", background: "var(--surface)", border: "1px solid var(--border)", padding: "4px 10px", borderRadius: "6px", color: "var(--text-muted)" }}>
          {adapter?.transport ? `Transporte: ${adapter.transport}` : "Ingestão Manual / API"}
        </span>
      </div>

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
        {[
          { label: "Total de Reuniões", value: metrics?.total_sessions ?? 0, icon: <Video size={18} color="var(--brand-accent)" /> },
          { label: "Tempo Total Analisado", value: `${Math.round((metrics?.total_duration_seconds ?? 0) / 60)} min`, icon: <Clock size={18} color="var(--mint)" /> },
          { label: "Análises Concluídas", value: metrics?.analyses_completed ?? 0, icon: <Brain size={18} color="#a855f7" /> },
        ].map((item) => (
          <div key={item.label} className="surface" style={{ padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", borderRadius: "10px" }}>
            <div>
              <span style={{ color: "var(--text-dim)", fontSize: "0.82rem", fontWeight: 500 }}>{item.label}</span>
              <strong style={{ display: "block", fontSize: "1.6rem", marginTop: 4, fontWeight: 700 }}>{item.value}</strong>
            </div>
            <div style={{ padding: 10, background: "var(--bg-inset)", borderRadius: "8px" }}>
              {item.icon}
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid: Create/List vs Active Session Workspace */}
      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 18 }}>
        {/* Left Column: Form & Sessions List */}
        <section className="surface" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16, borderRadius: "12px" }}>
          <div>
            <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
              <Play size={18} color="var(--brand-accent)" /> Nova Reunião
            </h3>
            <p style={{ margin: "4px 0 0", fontSize: "0.8rem", color: "var(--text-dim)" }}>Inicie ou agende um acompanhamento comercial.</p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div>
              <label style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>Título da Reunião *</label>
              <input
                style={inputStyle}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Ex.: Discovery com Cliente X"
              />
            </div>

            <div>
              <label style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>Cliente Vinculado</label>
              <select
                style={selectStyle}
                value={workspaceId}
                onChange={(event) => {
                  setWorkspaceId(event.target.value);
                  setOpportunityId("");
                  setProposalId("");
                }}
              >
                <option value="">Sem cliente vinculado</option>
                {clients.map((client) => (
                  <option key={client.id} value={client.id}>{client.organization_name}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>Oportunidade</label>
              <select style={selectStyle} value={opportunityId} onChange={(event) => setOpportunityId(event.target.value)}>
                <option value="">Sem oportunidade vinculada</option>
                {opportunities
                  .filter((item) => !workspaceId || item.workspace_id === workspaceId)
                  .map((item) => (
                    <option key={item.id} value={item.id}>{item.title} · {item.status}</option>
                  ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>Proposta Comercial</label>
              <select style={selectStyle} value={proposalId} onChange={(event) => setProposalId(event.target.value)}>
                <option value="">Sem proposta vinculada</option>
                {proposals.filter((p) => !workspaceId || p.workspace_id === workspaceId).map((proposal) => (
                  <option key={proposal.id} value={proposal.id}>{proposal.title || proposal.client_name} · v{proposal.version}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>Objetivo e Contexto</label>
              <textarea
                style={{ ...inputStyle, resize: "vertical" }}
                rows={3}
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
                placeholder="Ex.: Entender dores técnicas e apresentar escopo de migração..."
              />
            </div>

            <button
              className="primary-button"
              disabled={!title.trim() || Boolean(busy)}
              onClick={() => void run("create", () => api.createSalesCopilotSession({
                title: title.trim(),
                workspace_id: workspaceId || null,
                opportunity_id: opportunityId || null,
                proposal_id: proposalId || null,
                session_type: proposalId ? "proposal_review" : "discovery",
                objective: objective.trim() || null,
              }))}
              style={{ width: "100%", justifyContent: "center", padding: "10px", marginTop: 4 }}
            >
              {busy === "create" ? <Loader2 size={16} className="animate-spin" /> : <Bot size={16} />}
              Criar Sessão
            </button>
          </div>

          <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "4px 0" }} />

          <div>
            <h4 style={{ margin: "0 0 10px", fontSize: "0.9rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Reuniões Recentes ({sessions.length})
            </h4>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: "360px", overflowY: "auto" }}>
              {sessions.length === 0 && (
                <span style={{ fontSize: "0.82rem", color: "var(--text-dim)" }}>Nenhuma reunião registrada ainda.</span>
              )}
              {sessions.map((session) => {
                const isSelected = session.id === selectedId;
                return (
                  <div
                    key={session.id}
                    onClick={() => setSelectedId(session.id)}
                    style={{
                      padding: "10px 12px",
                      borderRadius: "8px",
                      background: isSelected ? "rgba(58, 201, 123, 0.08)" : "var(--bg-inset)",
                      border: `1px solid ${isSelected ? "rgba(58, 201, 123, 0.3)" : "var(--border)"}`,
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: 4,
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ fontSize: "0.85rem", color: isSelected ? "var(--brand-accent)" : "var(--text)" }}>
                        {session.title}
                      </strong>
                      {getStatusBadge(session.status)}
                    </div>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                      {session.meeting_provider} · {session.participants.length} participante(s)
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Right Column: Selected Session Active Cockpit */}
        <section className="surface" style={{ padding: 22, borderRadius: "12px" }}>
          {!selected ? (
            <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-dim)" }}>
              <FileAudio size={40} style={{ opacity: 0.4, marginBottom: 12 }} />
              <p style={{ margin: 0, fontSize: "0.95rem" }}>Selecione uma sessão à esquerda ou crie uma nova para iniciar o copiloto.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              {/* Header da Sessão Selecionada */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid var(--border)", paddingBottom: 14 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <h2 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 600 }}>{selected.title}</h2>
                    {getStatusBadge(selected.status)}
                  </div>
                  <span style={{ fontSize: "0.82rem", color: "var(--text-dim)", display: "block", marginTop: 4 }}>
                    Idioma: {selected.language.toUpperCase()} · Provedor: {selected.meeting_provider} · Consentimento: <strong>{selected.consent_status}</strong>
                  </span>
                </div>
                {selected.status === "draft" && (
                  <button
                    className="primary-button"
                    disabled={Boolean(busy)}
                    onClick={() => void run("prepare", () => api.prepareSalesCopilotSession(selected.id))}
                    style={{ padding: "8px 16px" }}
                  >
                    {busy === "prepare" ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                    Preparar Briefing Contextual
                  </button>
                )}
              </div>

              {/* Configuração da Reunião e Consentimento (para sessões ativas/draft) */}
              {selected.status !== "completed" && (
                <div style={{ background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "10px", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
                  <strong style={{ fontSize: "0.88rem", display: "flex", alignItems: "center", gap: 8 }}>
                    <Video size={16} color="var(--brand-accent)" /> Conexão da Reunião & Consentimento
                  </strong>
                  
                  <div style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: 10 }}>
                    <select style={selectStyle} value={meetingProvider} onChange={(event) => setMeetingProvider(event.target.value as typeof meetingProvider)}>
                      <option value="manual">Manual / Upload</option>
                      <option value="google_meet">Google Meet</option>
                      <option value="microsoft_teams">Microsoft Teams</option>
                    </select>
                    <input
                      style={inputStyle}
                      value={meetingUrl}
                      onChange={(event) => setMeetingUrl(event.target.value)}
                      placeholder="Link da Reunião (ex.: https://meet.google.com/xyz-abc)"
                    />
                  </div>

                  <label style={{ display: "flex", gap: 8, alignItems: "center", fontSize: "0.84rem", color: "var(--text-muted)", cursor: "pointer" }}>
                    <input type="checkbox" checked={consentGranted} onChange={(event) => setConsentGranted(event.target.checked)} style={{ accentColor: "var(--brand-accent)" }} />
                    Participantes informados e consentimento de gravação/transcrição registrado
                  </label>

                  <div style={{ display: "flex", gap: 10 }}>
                    <button
                      className="secondary-button"
                      disabled={Boolean(busy) || (meetingProvider !== "manual" && !meetingUrl.trim())}
                      onClick={() => void run("meeting", () => api.configureSalesCopilotMeeting(selected.id, {
                        meeting_provider: meetingProvider,
                        meeting_url: meetingUrl.trim() || null,
                        consent_granted: consentGranted,
                        retention_days: 90,
                      }))}
                    >
                      <ShieldCheck size={15} /> Salvar Configurações
                    </button>

                    {selected.meeting_provider !== "manual" && selected.consent_status === "granted" && (
                      <button
                        className="secondary-button"
                        disabled={Boolean(busy)}
                        onClick={() => {
                          setBusy("credential");
                          setError("");
                          void api.issueSalesCopilotIngestionCredential(selected.id)
                            .then((credential) => {
                              setAdapterCredential(`${credential.endpoint_path}\n${credential.ingest_token}`);
                              window.setTimeout(() => setAdapterCredential(""), 60_000);
                            })
                            .catch((err) => setError(err instanceof Error ? err.message : "Falha ao emitir credencial."))
                            .finally(() => setBusy(""));
                        }}
                      >
                        <KeyRound size={15} /> Emitir Credencial do Adaptador
                      </button>
                    )}
                  </div>

                  {/* Fathom e o gravador que a EG usa de verdade. Import por PULL:
                      o Bioma busca a transcricao, sem expor endpoint publico nem
                      administrar token por sessao. Mesma exigencia de
                      consentimento das outras fontes automaticas. */}
                  {selected.consent_status === "granted" && (
                    <div style={{ marginTop: 10, borderTop: "1px dashed var(--border)", paddingTop: 10 }}>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                        <button
                          className="secondary-button"
                          disabled={Boolean(busy)}
                          onClick={() => {
                            setBusy("fathom");
                            setError("");
                            setFathomFeedback("");
                            void api.fathomMeetings(15)
                              .then((meetings) => {
                                setFathomMeetings(meetings);
                                if (meetings.length === 0) setFathomFeedback("Nenhuma reuniao encontrada no Fathom.");
                              })
                              .catch((err) => setError(err instanceof Error ? err.message : "Falha ao consultar o Fathom."))
                              .finally(() => setBusy(""));
                          }}
                        >
                          <Video size={15} /> Buscar reunioes no Fathom
                        </button>
                        {fathomFeedback && <small style={{ color: "var(--text-muted)" }}>{fathomFeedback}</small>}
                      </div>

                      {fathomMeetings && fathomMeetings.length > 0 && (
                        <div className="table-list" style={{ marginTop: 8 }}>
                          {fathomMeetings.map((meeting) => (
                            <div className="table-row" key={meeting.recording_id}>
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <strong>{meeting.title}</strong>
                                <small style={{ display: "block", color: "var(--text-muted)" }}>
                                  {meeting.started_at ? new Date(meeting.started_at).toLocaleString("pt-BR") : "sem data"}
                                  {meeting.external_invitees.length > 0
                                    ? ` · ${meeting.external_invitees.map((guest) => guest.domain ?? guest.email).filter(Boolean).join(", ")}`
                                    : ""}
                                </small>
                              </div>
                              <button
                                className="mini-button"
                                disabled={Boolean(busy)}
                                onClick={() => {
                                  setBusy(`fathom-${meeting.recording_id}`);
                                  setError("");
                                  setFathomFeedback("");
                                  void api.importFathomMeeting(selected.id, meeting.recording_id)
                                    .then((result) => {
                                      setFathomFeedback(
                                        `${result.imported_segments} segmento(s) importado(s)` +
                                          (result.skipped_segments > 0 ? `, ${result.skipped_segments} ja existia(m)` : "") +
                                          (result.analyzed ? " · analise executada" : ""),
                                      );
                                      void load();
                                    })
                                    .catch((err) => setError(err instanceof Error ? err.message : "Falha ao importar."))
                                    .finally(() => setBusy(""));
                                }}
                              >
                                Importar transcricao
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {adapterCredential && (
                    <div className="notice" style={{ marginTop: 6 }}>
                      <strong>Credencial Segura (Exibida por 60s)</strong>
                      <pre style={{ whiteSpace: "pre-wrap", background: "var(--surface)", padding: 10, borderRadius: 6, margin: "8px 0" }}>{adapterCredential}</pre>
                      <small>Guarde no secret store do seu conector automatizado.</small>
                    </div>
                  )}
                </div>
              )}

              {/* Participantes */}
              <div style={{ background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "10px", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
                <strong style={{ fontSize: "0.88rem", display: "flex", alignItems: "center", gap: 8 }}>
                  <Users size={16} color="var(--brand-accent)" /> Participantes Conectados ({selected.participants.length})
                </strong>
                
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {selected.participants.length === 0 && <span style={{ fontSize: "0.82rem", color: "var(--text-dim)" }}>Nenhum participante adicionado.</span>}
                  {selected.participants.map((participant) => (
                    <span key={participant.id} className="status-badge" style={{ background: "var(--surface)", border: "1px solid var(--border)", padding: "4px 10px", borderRadius: "6px" }}>
                      {participant.display_name} · <em>{participant.job_title || participant.decision_role}</em> ({participant.participant_group})
                    </span>
                  ))}
                </div>

                {selected.status !== "completed" && (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 140px 140px", gap: 8, marginTop: 4 }}>
                    <input style={inputStyle} value={participantName} onChange={(event) => setParticipantName(event.target.value)} placeholder="Nome completo" />
                    <input style={inputStyle} value={participantTitle} onChange={(event) => setParticipantTitle(event.target.value)} placeholder="Cargo (ex: CEO, CFO)" />
                    <select style={selectStyle} value={participantGroup} onChange={(event) => setParticipantGroup(event.target.value as typeof participantGroup)}>
                      <option value="client">Cliente</option>
                      <option value="eg_team">Equipe EG</option>
                      <option value="partner">Parceiro</option>
                      <option value="unknown">Outro</option>
                    </select>
                    <button
                      className="secondary-button"
                      disabled={!participantName.trim() || Boolean(busy)}
                      onClick={() => void run("participant", async () => {
                        const session = await api.addSalesCopilotParticipant(selected.id, {
                          display_name: participantName.trim(),
                          participant_group: participantGroup,
                          job_title: participantTitle.trim() || null,
                          seniority: /ceo|cfo|cto|chief|sóci|propriet/i.test(participantTitle) ? "c_level" : /diretor/i.test(participantTitle) ? "director" : "unknown",
                          decision_role: /ceo|cfo|diretor|sóci|propriet/i.test(participantTitle) ? "decision_maker" : "unknown",
                        });
                        setParticipantName("");
                        setParticipantTitle("");
                        return session;
                      })}
                    >
                      <UserPlus size={14} /> Adicionar
                    </button>
                  </div>
                )}
              </div>

              {/* Briefing de Preparação */}
              {Object.keys(selected.preparation_brief).length > 0 && (
                <div className="notice" style={{ background: "rgba(168, 85, 247, 0.08)", border: "1px solid rgba(168, 85, 247, 0.2)" }}>
                  <strong style={{ color: "#c084fc", display: "flex", alignItems: "center", gap: 6 }}><Sparkles size={16} /> Briefing de Preparação IA</strong>
                  <pre style={{ whiteSpace: "pre-wrap", margin: "8px 0 0", fontSize: "0.82rem" }}>{JSON.stringify(selected.preparation_brief, null, 2)}</pre>
                </div>
              )}

              {/* Ingestão de Transcrição ao Vivo */}
              {selected.status !== "completed" && (
                <div style={{ background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "10px", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
                  <strong style={{ fontSize: "0.88rem", display: "flex", alignItems: "center", gap: 8 }}>
                    <Mic size={16} color="var(--brand-accent)" /> Transcrição Diarizada & Análise ao Vivo
                  </strong>

                  <select style={selectStyle} value={speakerId} onChange={(event) => setSpeakerId(event.target.value)}>
                    <option value="">Falante não identificado / Geral</option>
                    {selected.participants.map((participant) => (
                      <option key={participant.id} value={participant.id}>{participant.display_name}</option>
                    ))}
                  </select>

                  <textarea
                    style={{ ...inputStyle, resize: "vertical" }}
                    rows={4}
                    value={transcriptChunk}
                    onChange={(event) => setTranscriptChunk(event.target.value)}
                    placeholder="Digite ou cole aqui o trecho falado na reunião..."
                  />

                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <button
                      className="secondary-button"
                      disabled={!transcriptChunk.trim() || Boolean(busy)}
                      onClick={() => void run("chunk", async () => {
                        const participant = selected.participants.find((item) => item.id === speakerId);
                        const session = await api.ingestSalesCopilotSegments(selected.id, {
                          segments: [{
                            idempotency_key: crypto.randomUUID(),
                            participant_id: speakerId || null,
                            speaker_label: participant?.display_name || null,
                            source: "manual",
                            content: transcriptChunk.trim(),
                            is_final: true,
                          }],
                        });
                        setTranscriptChunk("");
                        return session;
                      })}
                    >
                      <Plus size={15} /> Adicionar Trecho
                    </button>

                    <button
                      className="secondary-button"
                      disabled={selected.segments.length === 0 || Boolean(busy)}
                      onClick={() => void run("analyze", () => api.analyzeSalesCopilotLive(selected.id))}
                    >
                      <Brain size={15} color="#a855f7" /> Sugerir Intervenção IA
                    </button>

                    <button
                      className="primary-button"
                      disabled={!selected.transcript.trim() || Boolean(busy)}
                      onClick={() => void run("complete", () => api.completeSalesCopilotSession(selected.id, 0))}
                    >
                      <Square size={14} /> Concluir e Gerar Resumo
                    </button>
                  </div>
                </div>
              )}

              {/* Sugestões ao Vivo */}
              {selected.suggestions.length > 0 && (
                <div className="notice" style={{ background: "rgba(58, 201, 123, 0.08)", border: "1px solid rgba(58, 201, 123, 0.2)" }}>
                  <strong style={{ color: "var(--mint)", display: "flex", alignItems: "center", gap: 6 }}><Brain size={16} /> Assistência IA ao Vivo</strong>
                  {selected.suggestions.slice(0, 5).map((suggestion) => (
                    <div key={suggestion.id} style={{ marginTop: 10, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
                      <span className="status-badge" style={{ background: "var(--surface)", fontSize: "0.72rem" }}>{suggestion.suggestion_type}</span>
                      <p style={{ margin: "6px 0", fontSize: "0.88rem", fontWeight: 500 }}>{suggestion.content}</p>
                      {suggestion.rationale && <small style={{ color: "var(--text-dim)" }}>{suggestion.rationale}</small>}
                    </div>
                  ))}
                </div>
              )}

              {/* Histórico da Conversa */}
              {selected.segments.length > 0 && (
                <div style={{ background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "10px", padding: 16 }}>
                  <strong style={{ fontSize: "0.88rem", display: "block", marginBottom: 10 }}>Transcrição da Reunião ({selected.segments.length} trechos)</strong>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: "240px", overflowY: "auto" }}>
                    {selected.segments.slice(-20).map((segment) => (
                      <div key={segment.id} style={{ padding: "8px 12px", background: "var(--surface)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                        <strong style={{ color: "var(--brand-accent)", fontSize: "0.82rem" }}>{segment.speaker_label || "Falante"}:</strong>
                        <p style={{ margin: "4px 0 0", fontSize: "0.85rem", whiteSpace: "pre-wrap" }}>{segment.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Resumo Final */}
              {selected.summary && (
                <div className="notice">
                  <strong>Resumo da Reunião</strong>
                  <p style={{ margin: "6px 0 0", fontSize: "0.88rem" }}>{selected.summary}</p>
                </div>
              )}

              {selected.status === "completed" && !selected.journey_snapshot && (
                <div className="notice" style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
                  <span>Esta reunião é anterior ao registro de jornada. Gere a projeção usando os vínculos e evidências já salvos.</span>
                  <button className="secondary-button" disabled={Boolean(busy)} onClick={() => void run("journey", () => api.rebuildSalesCopilotJourney(selected.id))}>
                    <GitBranch size={14} /> Gerar jornada
                  </button>
                </div>
              )}

              {/* Funil, jornada e raio-X derivados da reunião. Nenhuma nota é
                  inventada: scores ficam nulos até haver Raio-X comercial. */}
              {selected.journey_snapshot && (
                <div style={{ background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "10px", padding: 16, display: "grid", gap: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
                    <strong style={{ display: "flex", alignItems: "center", gap: 8 }}><GitBranch size={17} color="var(--brand-accent)" /> Jornada e funil registrados</strong>
                    <button className="secondary-button" disabled={Boolean(busy)} onClick={() => void run("journey", () => api.rebuildSalesCopilotJourney(selected.id))}>
                      <RefreshCw size={14} /> Recalcular com evidências atuais
                    </button>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 8 }}>
                    {selected.journey_snapshot.funnel_map.map((stage) => (
                      <div key={stage.key} style={{ padding: 10, borderRadius: 8, border: `1px solid ${stage.state === "current" ? "var(--brand-accent)" : "var(--border)"}`, background: stage.state === "completed" ? "rgba(58, 201, 123, 0.08)" : "var(--surface)" }}>
                        <small>{stage.state === "completed" ? "concluído" : stage.state === "current" ? "etapa atual" : "a seguir"}</small>
                        <strong style={{ display: "block", marginTop: 3 }}>{stage.label}</strong>
                      </div>
                    ))}
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1.25fr .75fr", gap: 12 }}>
                    <div>
                      <small style={{ textTransform: "uppercase", letterSpacing: ".08em" }}>Jornada 5 A's</small>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 7, marginTop: 7 }}>
                        {selected.journey_snapshot.journey_stages.map((stage) => (
                          <div key={stage.key} style={{ padding: 9, borderRadius: 8, border: `1px solid ${stage.state === "current" ? "#f59e0b" : "var(--border)"}`, background: "var(--surface)" }}>
                            <strong style={{ fontSize: ".82rem" }}>{stage.label}</strong>
                            <small style={{ display: "block", marginTop: 3 }}>{stage.score === null ? stage.state : stage.score}</small>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="notice" style={{ margin: 0 }}>
                      <strong style={{ display: "flex", gap: 6, alignItems: "center" }}><AlertTriangle size={15} /> Gargalo atual</strong>
                      {selected.journey_snapshot.bottlenecks.map((item) => <p key={`${item.stage}-${item.title}`} style={{ margin: "6px 0 0", fontSize: ".82rem" }}>{item.title}</p>)}
                    </div>
                  </div>

                  <div><small style={{ textTransform: "uppercase", letterSpacing: ".08em" }}>Próximas ações</small>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginTop: 7 }}>{selected.journey_snapshot.recommended_actions.map((item, index) => <span className="status-badge" key={`${item.title}-${index}`}>{item.title}</span>)}</div>
                  </div>
                  <small style={{ color: "var(--text-dim)" }}>Modo: {selected.journey_snapshot.generation_mode} · {selected.journey_snapshot.evidence_refs.length} referência(s) de evidência.</small>
                </div>
              )}

              {/* Compromissos Pós-Reunião */}
              <div style={{ background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "10px", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
                <strong style={{ fontSize: "0.88rem", display: "flex", alignItems: "center", gap: 8 }}>
                  <CheckCircle2 size={16} color="var(--mint)" /> Compromissos e Ações Acordadas
                </strong>
                
                {selected.actions.length === 0 && <span style={{ fontSize: "0.82rem", color: "var(--text-dim)" }}>Nenhum compromisso extraído ainda.</span>}
                {selected.actions.map((action) => (
                  <div key={action.id} style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", padding: "8px 12px", background: "var(--surface)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                    <span style={{ fontSize: "0.85rem" }}>{action.title} · <em style={{ color: "var(--text-dim)" }}>{action.action_type}</em></span>
                    {action.status === "proposed" && (
                      <button className="secondary-button" disabled={Boolean(busy)} onClick={() => void run("materialize", () => api.materializeSalesCopilotAction(action.id, `copilot-${action.id}`))}>
                        {action.action_type === "opportunity_registration" ? "Confirmar e registrar oportunidade" : "Confirmar e materializar"}
                      </button>
                    )}
                  </div>
                ))}

                <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
                  <input
                    style={inputStyle}
                    value={actionTitle}
                    onChange={(event) => setActionTitle(event.target.value)}
                    placeholder="Adicionar novo follow-up ou entregável..."
                  />
                  <button
                    className="secondary-button"
                    disabled={!actionTitle.trim() || Boolean(busy)}
                    onClick={() => void run("action", async () => {
                      const session = await api.addSalesCopilotAction(selected.id, {
                        action_type: "follow_up_task",
                        title: actionTitle.trim(),
                        idempotency_key: crypto.randomUUID(),
                      });
                      setActionTitle("");
                      return session;
                    })}
                    style={{ whiteSpace: "nowrap" }}
                  >
                    <Plus size={15} /> Adicionar Ação
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>

      {error && <p style={{ color: "#ef4444", margin: 0, fontWeight: 500 }}>{error}</p>}
    </div>
  );
}
