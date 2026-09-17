import { FormEvent, useEffect, useState } from "react";
import { CheckCircle2, FileSignature } from "lucide-react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { api, type PublicProposalLifecycleRecord } from "../lib/api";


export function PublicProposalView() {
  const { token = "" } = useParams();
  const [proposal, setProposal] = useState<PublicProposalLifecycleRecord | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void api.getPublicProposalDetail(token)
      .then(setProposal)
      .catch((err) => setError(err instanceof Error ? err.message : "Proposta indisponível."));
  }, [token]);

  const accept = async (event: FormEvent) => {
    event.preventDefault();
    if (!confirmed) return;
    setSubmitting(true);
    setError("");
    try {
      setProposal(await api.acceptPublicProposal(token, name.trim(), email.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível registrar o aceite.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!proposal) {
    return <main style={{ maxWidth: 900, margin: "60px auto", padding: 24 }}><p>{error || "Carregando proposta…"}</p></main>;
  }

  const canAccept = ["sent", "negotiating"].includes(proposal.status)
    && proposal.claims_review_status === "approved"
    && proposal.acceptance_status !== "accepted";

  return (
    <main style={{ maxWidth: 920, margin: "32px auto", padding: 20 }}>
      <header className="surface" style={{ padding: 22, marginBottom: 18 }}>
        <span className="status-badge">Proposta · versão {proposal.version}</span>
        <h1>{proposal.title || proposal.client_name}</h1>
        <p style={{ color: "var(--text-dim)" }}>Preparada para {proposal.client_name} por {proposal.contractor_name || "Evergreen Growth"}.</p>
      </header>
      <article className="surface" style={{ padding: 32, lineHeight: 1.65 }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{proposal.content_markdown}</ReactMarkdown>
      </article>

      {proposal.acceptance_status === "accepted" ? (
        <div className="notice" style={{ marginTop: 18 }}>
          <CheckCircle2 size={20} /> <strong>Aceite registrado em {proposal.accepted_at ? new Date(proposal.accepted_at).toLocaleString("pt-BR") : "data registrada"}.</strong>
          <span style={{ display: "block" }}>Signatário: {proposal.accepted_by_name}.</span>
        </div>
      ) : canAccept ? (
        <form className="surface" onSubmit={accept} style={{ padding: 22, marginTop: 18, display: "grid", gap: 12 }}>
          <h2 style={{ margin: 0 }}><FileSignature size={20} /> Aceite da proposta</h2>
          <p style={{ color: "var(--text-dim)", margin: 0 }}>O aceite registra identidade, data e versão. Contrato e assinatura eletrônica formal permanecem fluxos separados quando exigidos.</p>
          <input required minLength={2} value={name} onChange={(event) => setName(event.target.value)} placeholder="Nome completo" />
          <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="E-mail" />
          <label style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
            <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
            Confirmo que li e aceito os termos desta versão da proposta.
          </label>
          <button className="primary-button" type="submit" disabled={!confirmed || submitting}>{submitting ? "Registrando…" : "Aceitar proposta"}</button>
        </form>
      ) : (
        <div className="notice" style={{ marginTop: 18 }}>Esta versão está disponível para consulta, mas ainda não foi liberada para aceite.</div>
      )}
      {error && <p style={{ color: "#ef4444" }}>{error}</p>}
    </main>
  );
}
