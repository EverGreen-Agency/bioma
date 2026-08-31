import { useEffect, useMemo, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Plus, Sparkles, X } from "lucide-react";

import { NewClientWizard } from "../../../components/NewClientWizard";
import {
  api,
  type ClientSummary,
  type ProposalBriefPayload,
  type ProposalCatalog,
  type ProposalSummary,
} from "../../../lib/api";

type Props = {
  onClose: () => void;
  onCreated: (proposal: ProposalSummary) => void;
};

const emptyBrief: Omit<ProposalBriefPayload, "workspace_id"> = {
  title: "",
  proposal_type: "",
  contractor_name: "Evergreen Growth",
  team_members: [],
  delivery_modality: "",
  selected_services: [],
  special_requirements: "",
  estimated_budget: "",
  payment_terms: "",
  urgency: "",
  decision_maker: "",
  problem_summary: "",
  additional_context: "",
};

export function ProposalWizard({ onClose, onCreated }: Props) {
  const [step, setStep] = useState(0);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [catalog, setCatalog] = useState<ProposalCatalog | null>(null);
  const [workspaceId, setWorkspaceId] = useState("");
  const [search, setSearch] = useState("");
  const [brief, setBrief] = useState(emptyBrief);
  const [teamText, setTeamText] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [showClientWizard, setShowClientWizard] = useState(false);

  const loadReferenceData = async (preferredClientId?: string) => {
    setLoading(true);
    try {
      const [clientRows, catalogData] = await Promise.all([api.clients(), api.proposalCatalog()]);
      setClients(clientRows.filter((client) => client.status !== "archived"));
      setCatalog(catalogData);
      if (preferredClientId) setWorkspaceId(preferredClientId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível carregar clientes e catálogo.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadReferenceData();
  }, []);

  const selectedClient = clients.find((client) => client.id === workspaceId);
  const filteredClients = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase("pt-BR");
    if (!needle) return clients;
    return clients.filter((client) =>
      `${client.name} ${client.organization_name}`.toLocaleLowerCase("pt-BR").includes(needle)
    );
  }, [clients, search]);

  const updateBrief = <K extends keyof typeof brief>(key: K, value: (typeof brief)[K]) => {
    setBrief((current) => ({ ...current, [key]: value }));
  };

  const stepValid = [
    Boolean(workspaceId),
    Boolean(brief.title.trim() && brief.proposal_type && brief.contractor_name.trim()),
    Boolean(brief.delivery_modality && brief.selected_services.length),
    Boolean(
      brief.estimated_budget.trim() &&
      brief.payment_terms.trim() &&
      brief.urgency &&
      brief.decision_maker.trim() &&
      brief.problem_summary.trim().length >= 10
    ),
  ][step];

  const toggleService = (key: string) => {
    updateBrief(
      "selected_services",
      brief.selected_services.includes(key)
        ? brief.selected_services.filter((item) => item !== key)
        : [...brief.selected_services, key],
    );
  };

  const submit = async () => {
    if (!workspaceId || !stepValid) return;
    setSubmitting(true);
    setError("");
    try {
      const proposal = await api.createProposalFromBrief({
        ...brief,
        workspace_id: workspaceId,
        team_members: teamText
          .split(",")
          .map((member) => member.trim())
          .filter(Boolean),
        special_requirements: brief.special_requirements?.trim() || null,
        additional_context: brief.additional_context?.trim() || null,
      });
      onCreated(proposal);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível gerar a proposta.");
    } finally {
      setSubmitting(false);
    }
  };

  if (showClientWizard) {
    return (
      <NewClientWizard
        navigateOnCreate={false}
        onClose={() => setShowClientWizard(false)}
        onCreated={(clientId) => {
          setShowClientWizard(false);
          void loadReferenceData(clientId);
        }}
      />
    );
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card wide" onClick={(event) => event.stopPropagation()} style={{ maxWidth: 900 }}>
        <div className="modal-header">
          <div className="modal-title-group">
            <Sparkles size={18} color="var(--brand-accent)" />
            <div>
              <h2 style={{ margin: 0 }}>Nova proposta comercial</h2>
              <span style={{ color: "var(--text-dim)", fontSize: "0.8rem" }}>
                Briefing versionado + geração assistida com revisão humana
              </span>
            </div>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Fechar">
            <X size={16} />
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", borderBottom: "1px solid var(--border)" }}>
          {["Cliente", "Informações", "Escopo", "Contexto"].map((label, index) => (
            <div key={label} style={{ padding: 12, color: index === step ? "var(--brand-accent)" : "var(--text-dim)", fontWeight: index === step ? 700 : 500, borderBottom: index === step ? "2px solid var(--brand-accent)" : "2px solid transparent" }}>
              {index < step ? <Check size={14} style={{ verticalAlign: "middle", marginRight: 6 }} /> : `${index + 1}. `}
              {label}
            </div>
          ))}
        </div>

        <div className="modal-body" style={{ padding: 20, maxHeight: "68vh", overflowY: "auto" }}>
          {loading ? (
            <p>Carregando dados comerciais…</p>
          ) : step === 0 ? (
            <div style={{ display: "grid", gap: 12 }}>
              <div style={{ display: "flex", gap: 8 }}>
                <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar cliente ou empresa…" style={{ flex: 1, padding: 10 }} />
                <button type="button" className="secondary-button" onClick={() => setShowClientWizard(true)}>
                  <Plus size={15} /> Criar cliente
                </button>
              </div>
              <div style={{ display: "grid", gap: 8 }}>
                {filteredClients.map((client) => (
                  <button key={client.id} type="button" onClick={() => setWorkspaceId(client.id)} style={{ padding: 14, textAlign: "left", borderRadius: 8, border: `1px solid ${workspaceId === client.id ? "var(--brand-accent)" : "var(--border)"}`, background: workspaceId === client.id ? "rgba(58, 201, 123, 0.10)" : "var(--bg-inset)", color: "var(--text)", cursor: "pointer" }}>
                    <strong>{client.organization_name}</strong>
                    <span style={{ display: "block", color: "var(--text-dim)", fontSize: "0.8rem", marginTop: 3 }}>
                      {client.name} · {client.status}
                    </span>
                  </button>
                ))}
                {!filteredClients.length && <p style={{ color: "var(--text-dim)" }}>Nenhum cliente encontrado.</p>}
              </div>
            </div>
          ) : step === 1 ? (
            <div className="form-grid two">
              <label>Título da proposta *<input value={brief.title} onChange={(event) => updateBrief("title", event.target.value)} placeholder="Ex.: Fase 3 do aplicativo" /></label>
              <label>Tipo da proposta *<select value={brief.proposal_type} onChange={(event) => updateBrief("proposal_type", event.target.value)}><option value="">Selecione</option>{catalog?.proposal_types.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
              <label>Nome da contratada *<input value={brief.contractor_name} onChange={(event) => updateBrief("contractor_name", event.target.value)} /></label>
              <label>Equipe (separe por vírgulas)<input value={teamText} onChange={(event) => setTeamText(event.target.value)} placeholder="Tech Lead, Designer, Desenvolvedor" /></label>
            </div>
          ) : step === 2 ? (
            <div style={{ display: "grid", gap: 16 }}>
              <label>Modalidade de entrega *<select value={brief.delivery_modality} onChange={(event) => updateBrief("delivery_modality", event.target.value)}><option value="">Selecione</option>{catalog?.delivery_modalities.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
              {catalog?.service_groups.map((group) => (
                <section key={group.key} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 14 }}>
                  <strong>{group.label}</strong>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 8, marginTop: 10 }}>
                    {group.services.map((service) => {
                      const selected = brief.selected_services.includes(service.key);
                      return <button key={service.key} type="button" onClick={() => toggleService(service.key)} style={{ padding: 10, textAlign: "left", borderRadius: 7, border: `1px solid ${selected ? "var(--brand-accent)" : "var(--border)"}`, color: "var(--text)", background: selected ? "rgba(58, 201, 123, 0.10)" : "var(--bg-inset)", cursor: "pointer" }}>{selected ? "✓ " : ""}{service.label}</button>;
                    })}
                  </div>
                </section>
              ))}
              <label>Requisitos especiais<textarea rows={3} value={brief.special_requirements ?? ""} onChange={(event) => updateBrief("special_requirements", event.target.value)} placeholder="Integrações, compliance, ferramentas e restrições…" /></label>
            </div>
          ) : (
            <div className="form-grid two">
              <label>Orçamento estimado *<input value={brief.estimated_budget} onChange={(event) => updateBrief("estimated_budget", event.target.value)} placeholder="R$ 20.000 ou faixa a validar" /></label>
              <label>Urgência *<select value={brief.urgency} onChange={(event) => updateBrief("urgency", event.target.value)}><option value="">Selecione</option>{catalog?.urgency_levels.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
              <label style={{ gridColumn: "1 / -1" }}>Forma e prazo de pagamento *<textarea rows={2} value={brief.payment_terms} onChange={(event) => updateBrief("payment_terms", event.target.value)} /></label>
              <label>Tomador de decisão *<input value={brief.decision_maker} onChange={(event) => updateBrief("decision_maker", event.target.value)} /></label>
              <label style={{ gridColumn: "1 / -1" }}>Dor/problema que a proposta resolve *<textarea rows={4} value={brief.problem_summary} onChange={(event) => updateBrief("problem_summary", event.target.value)} /></label>
              <label style={{ gridColumn: "1 / -1" }}>Contexto adicional<textarea rows={3} value={brief.additional_context ?? ""} onChange={(event) => updateBrief("additional_context", event.target.value)} /></label>
            </div>
          )}

          {selectedClient && step > 0 && (
            <div style={{ marginTop: 16, padding: 10, borderRadius: 8, background: "var(--bg-inset)", color: "var(--text-dim)", fontSize: "0.82rem" }}>
              Cliente canônico: <strong style={{ color: "var(--text)" }}>{selectedClient.organization_name}</strong>. O perfil já cadastrado será incluído no contexto da geração.
            </div>
          )}
          {error && <p style={{ color: "#ef4444" }}>{error}</p>}
        </div>

        <div className="modal-footer" style={{ display: "flex", justifyContent: "space-between" }}>
          <button type="button" className="secondary-button" disabled={step === 0 || submitting} onClick={() => setStep((current) => current - 1)}>
            <ChevronLeft size={15} /> Voltar
          </button>
          {step < 3 ? (
            <button type="button" className="primary-button" disabled={!stepValid} onClick={() => setStep((current) => current + 1)}>
              Próximo <ChevronRight size={15} />
            </button>
          ) : (
            <button type="button" className="primary-button" disabled={!stepValid || submitting} onClick={() => void submit()}>
              <Sparkles size={15} /> {submitting ? "Gerando rascunho…" : "Gerar proposta"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
