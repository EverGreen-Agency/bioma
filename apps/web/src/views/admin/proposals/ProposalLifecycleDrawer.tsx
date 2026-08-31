import { useEffect, useMemo, useState } from "react";
import {
  Archive,
  Check,
  Copy,
  Download,
  ExternalLink,
  FileClock,
  Globe,
  GitBranch,
  Printer,
  Save,
  Send,
  X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  api,
  type ProposalClaim,
  type ProposalDetail,
  type ProposalSummary,
  type ProposalTranslation,
} from "../../../lib/api";

// Idioma do conteúdo, não da interface do Bioma (que continua pt-BR). O
// original nasce no idioma do destinatário e é ELE que sai no link público —
// a tradução aqui é só para a equipe interna ler.
const LANGUAGE_LABELS: Record<string, string> = {
  "pt-BR": "Português",
  "en-US": "Inglês",
  "es-ES": "Espanhol",
};


const NEXT_STATUS: Partial<Record<ProposalSummary["status"], ProposalSummary["status"][]>> = {
  draft: ["approved"],
  approved: ["draft", "sent"],
  sent: ["negotiating", "won", "lost"],
  negotiating: ["won", "lost"],
  lost: ["draft"],
};

const STATUS_LABEL: Record<ProposalSummary["status"], string> = {
  draft: "Rascunho",
  approved: "Aprovada internamente",
  sent: "Enviada",
  negotiating: "Em negociação",
  won: "Ganha",
  lost: "Perdida",
};

export function ProposalLifecycleDrawer({
  proposalId,
  onClose,
  onChanged,
}: {
  proposalId: string;
  onClose: () => void;
  onChanged: () => Promise<void>;
}) {
  const [detail, setDetail] = useState<ProposalDetail | null>(null);
  const [tab, setTab] = useState<"proposal" | "form" | "history">("proposal");
  const [mode, setMode] = useState<"preview" | "markdown">("preview");
  const [markdown, setMarkdown] = useState("");
  const [claims, setClaims] = useState<ProposalClaim[]>([]);
  // Nulo = mostrando o original. A edição (aba Markdown) sempre atua sobre o
  // original — traduzir e editar ao mesmo tempo faria "onde eu edito?" virar
  // pergunta sem resposta óbvia.
  const [translation, setTranslation] = useState<ProposalTranslation | null>(null);
  const [translating, setTranslating] = useState(false);
  const [translateError, setTranslateError] = useState("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [projectType, setProjectType] = useState<"tech" | "growth" | "social" | "general">("general");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = async (id = proposalId) => {
    setError("");
    const next = await api.proposalDetail(id);
    setDetail(next);
    setMarkdown(next.proposal.content_markdown);
    setClaims(next.proposal.claims);
    // Editar invalida a tradução no servidor — uma tradução guardada no estado
    // local continuaria mostrando o texto velho como se fosse atual.
    setTranslation(null);
    setTranslateError("");
  };

  async function handleSetContentLanguage(language: string) {
    if (!detail || language === detail.proposal.content_language) return;
    setBusy("language");
    setError("");
    try {
      // `updateProposal` devolve `ProposalSummary`, não o `ProposalDetail`
      // completo — mais simples recarregar do que remontar o detail à mão.
      await api.updateProposal(detail.proposal.id, { content_language: language });
      await load(detail.proposal.id);
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível marcar o idioma.");
    } finally {
      setBusy("");
    }
  }

  async function handleSelectLanguage(language: string) {
    if (!detail) return;
    if (language === detail.proposal.content_language) {
      setTranslation(null);
      return;
    }
    setTranslating(true);
    setTranslateError("");
    try {
      setTranslation(await api.translateProposal(detail.proposal.id, language));
    } catch (err) {
      setTranslateError(err instanceof Error ? err.message : "Não foi possível traduzir agora.");
    } finally {
      setTranslating(false);
    }
  }

  useEffect(() => {
    void load().catch((err) => setError(err instanceof Error ? err.message : "Falha ao carregar proposta."));
  }, [proposalId]);

  const act = async (label: string, action: () => Promise<ProposalDetail | void>) => {
    setBusy(label);
    setError("");
    try {
      const result = await action();
      if (result) {
        setDetail(result);
        setMarkdown(result.proposal.content_markdown);
        setClaims(result.proposal.claims);
        setTranslation(null);
      }
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "A ação não pôde ser concluída.");
    } finally {
      setBusy("");
    }
  };

  const publicUrl = useMemo(
    () => detail ? `${window.location.origin}/propostas/public/${detail.proposal.public_token}` : "",
    [detail],
  );

  if (!detail) {
    return (
      <div className="drawer-overlay" onClick={onClose}>
        <div className="drawer-content" onClick={(event) => event.stopPropagation()} style={{ maxWidth: 980, padding: 24 }}>
          <p>{error || "Carregando proposta…"}</p>
        </div>
      </div>
    );
  }

  const proposal = detail.proposal;
  const allClaimsApproved = claims.every((claim) => claim.approved && Boolean(claim.evidence_ref?.trim()));

  const downloadPdf = async () => {
    const blob = await api.downloadProposalPdf(proposal.id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${(proposal.title || proposal.client_name).replace(/[^\p{L}\p{N}]+/gu, "-").toLowerCase()}-v${proposal.version}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-content" onClick={(event) => event.stopPropagation()} style={{ maxWidth: 1080, width: "94vw", padding: 0 }}>
        <header style={{ padding: 20, borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", gap: 16 }}>
          <div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <span className="status-badge">{STATUS_LABEL[proposal.status]}</span>
              <span style={{ color: "var(--text-dim)", fontSize: "0.8rem" }}>versão {proposal.version}</span>
              <span style={{ color: proposal.claims_review_status === "approved" ? "#10b981" : "#f59e0b", fontSize: "0.8rem" }}>
                Alegações: {proposal.claims_review_status === "approved" ? "revisadas" : "pendentes"}
              </span>
              <label
                style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.8rem", color: "var(--text-dim)" }}
                title="Idioma em que o conteúdo nasceu — é ele que sai no link público"
              >
                Conteúdo nasceu em
                <select
                  value={proposal.content_language}
                  onChange={(event) => void handleSetContentLanguage(event.target.value)}
                  style={{ fontSize: "0.8rem" }}
                >
                  {Object.entries(LANGUAGE_LABELS).map(([code, label]) => (
                    <option key={code} value={code}>{label}</option>
                  ))}
                </select>
              </label>
            </div>
            <h2 style={{ margin: "8px 0 3px" }}>{proposal.title || proposal.client_name}</h2>
            <span style={{ color: "var(--text-dim)" }}>{proposal.client_name} · {proposal.generation_mode === "live" ? "IA live" : proposal.generation_mode === "preview" ? "prévia assistida" : "manual"}</span>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Fechar"><X size={18} /></button>
        </header>

        <nav style={{ display: "flex", gap: 8, padding: "12px 20px", borderBottom: "1px solid var(--border)" }}>
          {([
            ["proposal", "Proposta"],
            ["form", "Dados do briefing"],
            ["history", "Versões e histórico"],
          ] as const).map(([key, label]) => (
            <button key={key} type="button" className={tab === key ? "primary-button" : "secondary-button"} onClick={() => setTab(key)}>
              {label}
            </button>
          ))}
        </nav>

        <div style={{ padding: 20, maxHeight: "65vh", overflowY: "auto" }}>
          {tab === "proposal" ? (
            <div style={{ display: "grid", gap: 16 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <button className={mode === "preview" ? "primary-button" : "secondary-button"} onClick={() => setMode("preview")}>Visualização</button>
                <button className={mode === "markdown" ? "primary-button" : "secondary-button"} onClick={() => setMode("markdown")}>Markdown</button>

                {mode === "preview" && (
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto" }}>
                    <Globe size={14} color="var(--text-dim)" />
                    <select
                      value={translation?.language ?? proposal.content_language}
                      disabled={translating}
                      onChange={(event) => void handleSelectLanguage(event.target.value)}
                      title="O link público não muda de idioma — isto é só para a equipe ler"
                    >
                      {Object.entries(LANGUAGE_LABELS).map(([code, label]) => (
                        <option key={code} value={code}>
                          {label}
                          {code === proposal.content_language ? " (original)" : ""}
                        </option>
                      ))}
                    </select>
                    {translating && <span style={{ fontSize: 12, color: "var(--text-dim)" }}>traduzindo…</span>}
                  </div>
                )}
              </div>

              {translateError && <div className="notice error">{translateError}</div>}

              {mode === "preview" ? (
                <article className="surface" style={{ padding: 28, lineHeight: 1.65 }}>
                  {translation && (
                    <div
                      style={{
                        display: "flex", justifyContent: "space-between", alignItems: "center",
                        marginBottom: 16, padding: "8px 12px", borderRadius: 8,
                        background: "var(--surface-soft)", border: "1px dashed var(--border)",
                        fontSize: 12.5, color: "var(--text-dim)",
                      }}
                    >
                      <span>
                        Tradução para {LANGUAGE_LABELS[translation.language] ?? translation.language} — o original é em{" "}
                        {LANGUAGE_LABELS[proposal.content_language] ?? proposal.content_language}, e é ele que sai no
                        link público.
                      </span>
                      <button className="secondary-button" style={{ flexShrink: 0 }} onClick={() => setTranslation(null)}>
                        Ver original
                      </button>
                    </div>
                  )}
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {translation ? translation.content_markdown : markdown}
                  </ReactMarkdown>
                </article>
              ) : (
                <textarea
                  rows={24}
                  value={markdown}
                  disabled={proposal.status !== "draft"}
                  onChange={(event) => setMarkdown(event.target.value)}
                  style={{ width: "100%", fontFamily: "ui-monospace, monospace" }}
                />
              )}

              <section className="surface" style={{ padding: 16, display: "grid", gap: 10 }}>
                <div>
                  <strong>Revisão de alegações e números</strong>
                  <p style={{ margin: "4px 0", color: "var(--text-dim)", fontSize: "0.82rem" }}>
                    Resultados, garantias e afirmações quantitativas só podem ser liberados com evidência registrada.
                  </p>
                </div>
                {claims.map((claim, index) => (
                  <div key={`${claim.text}-${index}`} style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 8 }}>
                    <input value={claim.text} disabled={proposal.status !== "draft"} onChange={(event) => setClaims((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, text: event.target.value } : item))} placeholder="Alegação" />
                    <input value={claim.evidence_ref ?? ""} disabled={proposal.status !== "draft"} onChange={(event) => setClaims((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, evidence_ref: event.target.value || null } : item))} placeholder="Link ou referência da evidência" />
                    <label style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      <input type="checkbox" checked={claim.approved} disabled={proposal.status !== "draft"} onChange={(event) => setClaims((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, approved: event.target.checked } : item))} />
                      validada
                    </label>
                  </div>
                ))}
                {proposal.status === "draft" && (
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="secondary-button" onClick={() => setClaims((current) => [...current, { text: "", evidence_ref: null, approved: false }])}>Adicionar alegação</button>
                    <button className="primary-button" disabled={Boolean(busy) || markdown.trim().length < 20} onClick={() => void act("save", () => api.saveProposalContent(proposal.id, markdown, claims))}>
                      <Save size={15} /> Salvar conteúdo
                    </button>
                    <button className="secondary-button" disabled={Boolean(busy) || !allClaimsApproved} onClick={() => void act("claims", () => api.reviewProposalClaims(proposal.id, "approved"))}>
                      <Check size={15} /> Aprovar alegações
                    </button>
                  </div>
                )}
              </section>
            </div>
          ) : tab === "form" ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
              {[
                ["Tipo", proposal.proposal_type],
                ["Modalidade", proposal.delivery_modality],
                ["Contratada", proposal.contractor_name],
                ["Orçamento", proposal.estimated_budget],
                ["Pagamento", proposal.payment_terms],
                ["Urgência", proposal.urgency],
                ["Decisor", proposal.decision_maker],
                ["Problema", proposal.problem_summary],
                ["Requisitos", proposal.special_requirements],
                ["Contexto adicional", proposal.additional_context],
              ].map(([label, value]) => (
                <div key={label} className="surface" style={{ padding: 14 }}>
                  <strong style={{ display: "block", fontSize: "0.78rem", color: "var(--brand-accent)" }}>{label}</strong>
                  <span style={{ whiteSpace: "pre-wrap" }}>{value || "Não informado"}</span>
                </div>
              ))}
              <div className="surface" style={{ padding: 14, gridColumn: "1 / -1" }}>
                <strong>Serviços incluídos</strong>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                  {proposal.selected_services.map((service) => <span key={service} className="status-badge">{service.replaceAll("_", " ")}</span>)}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, .8fr) 1.2fr", gap: 16 }}>
              <section>
                <h3><GitBranch size={16} /> Revisões</h3>
                {detail.revisions.map((revision) => (
                  <button key={revision.id} className="secondary-button" style={{ width: "100%", marginBottom: 8, justifyContent: "space-between" }} onClick={() => void load(revision.id)}>
                    <span>Versão {revision.version}</span><span>{STATUS_LABEL[revision.status]}</span>
                  </button>
                ))}
              </section>
              <section>
                <h3><FileClock size={16} /> Timeline auditável</h3>
                {[...detail.events, ...detail.deliveries.map((delivery) => ({
                  id: delivery.id,
                  event_type: `delivery.${delivery.status}`,
                  created_at: delivery.created_at,
                  payload: { channel: delivery.channel, recipient: delivery.recipient_email },
                }))].sort((a, b) => b.created_at.localeCompare(a.created_at)).map((event) => (
                  <div key={event.id} style={{ borderLeft: "2px solid var(--brand-accent)", padding: "2px 0 12px 12px" }}>
                    <strong>{event.event_type.replaceAll(".", " · ")}</strong>
                    <span style={{ display: "block", color: "var(--text-dim)", fontSize: "0.78rem" }}>{new Date(event.created_at).toLocaleString("pt-BR")}</span>
                    {Object.keys(event.payload).length > 0 && <code style={{ fontSize: "0.72rem" }}>{JSON.stringify(event.payload)}</code>}
                  </div>
                ))}
              </section>
            </div>
          )}
          {error && <p style={{ color: "#ef4444" }}>{error}</p>}
        </div>

        <footer style={{ padding: 16, borderTop: "1px solid var(--border)", display: "grid", gap: 10 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {(NEXT_STATUS[proposal.status] ?? []).map((next) => (
              <button key={next} className="secondary-button" disabled={Boolean(busy)} onClick={() => void act(`status-${next}`, () => api.transitionProposal(proposal.id, next))}>
                Mover para {STATUS_LABEL[next]}
              </button>
            ))}
            <button className="secondary-button" disabled={Boolean(busy)} onClick={() => void act("revision", () => api.createProposalRevision(proposal.id, "Nova revisão solicitada na central comercial"))}>
              <Copy size={15} /> Nova revisão
            </button>
            <button className="secondary-button" onClick={() => void navigator.clipboard.writeText(publicUrl)}><ExternalLink size={15} /> Copiar link</button>
            <button className="secondary-button" onClick={() => window.print()}><Printer size={15} /> Imprimir</button>
            <button className="secondary-button" disabled={Boolean(busy)} onClick={() => void act("pdf", async () => { await downloadPdf(); })}><Download size={15} /> Exportar PDF</button>
            <button className="secondary-button" disabled={Boolean(busy)} onClick={() => {
              if (window.confirm("Arquivar esta proposta? O histórico será preservado.")) {
                void act("archive", async () => { await api.archiveProposal(proposal.id); onClose(); });
              }
            }}><Archive size={15} /> Arquivar</button>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <input value={recipientEmail} onChange={(event) => setRecipientEmail(event.target.value)} placeholder="E-mail do destinatário" style={{ minWidth: 240 }} />
            <button className="secondary-button" disabled={Boolean(busy)} onClick={() => void act("share", () => api.createProposalDelivery(proposal.id, { channel: "share_link", recipient_email: recipientEmail || null, confirm_external_send: false }))}>
              Preparar compartilhamento
            </button>
            <button className="secondary-button" disabled={Boolean(busy) || !recipientEmail} onClick={() => {
              if (window.confirm("Confirma que o envio externo já foi realizado? O Bioma apenas registrará esse fato.")) {
                void act("send", () => api.createProposalDelivery(proposal.id, { channel: "manual_email", recipient_email: recipientEmail, confirm_external_send: true }));
              }
            }}><Send size={15} /> Registrar envio manual</button>
            {proposal.status === "won" && !detail.conversion && (
              <>
                <select value={projectType} onChange={(event) => setProjectType(event.target.value as typeof projectType)}>
                  <option value="general">Projeto geral</option>
                  <option value="tech">Tech</option>
                  <option value="growth">Growth</option>
                  <option value="social">Social media</option>
                </select>
                <button className="primary-button" disabled={Boolean(busy)} onClick={() => {
                  if (window.confirm("Criar projeto, contrato e escopo a partir desta proposta ganha?")) {
                    void act("convert", () => api.convertProposal(proposal.id, {
                      confirm: true,
                      idempotency_key: `proposal-${proposal.id}-v${proposal.version}`,
                      project_type: projectType,
                    }));
                  }
                }}>Criar projeto e contrato</button>
              </>
            )}
            {detail.conversion && <span style={{ color: "#10b981" }}>Convertida no projeto {detail.conversion.project_id}</span>}
          </div>
        </footer>
      </div>
    </div>
  );
}
