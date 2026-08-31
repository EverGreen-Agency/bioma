import { FormEvent, useMemo, useState } from "react";
import { Building2, Plus, Trash2 } from "lucide-react";
import { EmptyState, SectionHeader } from "../components/shared";
import {
  type LeadPayload,
  type LeadStage,
  type LeadSummary,
} from "../lib/api";
import {
  useCurrentUser,
  useLeads,
  useCreateLead,
  useUpdateLead,
  useDeleteLead,
} from "../hooks/useBiomaApi";

const leadStages: Array<{ id: LeadStage; label: string }> = [
  { id: "new", label: "Novo" },
  { id: "qualifying", label: "Qualificando" },
  { id: "meeting", label: "Reunião" },
  { id: "proposal", label: "Proposta" },
  { id: "won", label: "Ganho" },
  { id: "lost", label: "Perdido" },
];

const emptyLead: LeadPayload = {
  name: "",
  company: "",
  stage: "new",
  source: "",
  expected_value: null,
  notes: "",
};

function formatMoney(value: number | null, currency = "BRL") {
  if (value === null || Number.isNaN(value)) return "sem valor";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(value);
}

function toNullableNumber(value: string) {
  const normalized = value.replace(",", ".").trim();
  return normalized ? Number(normalized) : null;
}

export function CrmView({ clientId }: { clientId: string }) {
  const { data: user } = useCurrentUser();

  const isEgAdmin = user?.organizations.some((organization: { slug: string; role: string }) => organization.slug === "eg" && organization.role === "eg_admin") ?? false;

  const { data: leadsData, error: leadsError } = useLeads(clientId);

  const createLead = useCreateLead();
  const updateLead = useUpdateLead();
  const deleteLead = useDeleteLead();

  const [leadDraft, setLeadDraft] = useState<LeadPayload>(emptyLead);

  const leads = leadsData ?? [];

  const error = leadsError ? leadsError.message : "";

  const forecast = useMemo(
    () => leads.reduce((total, lead) => total + (lead.stage !== "lost" ? lead.expected_value ?? 0 : 0), 0),
    [leads],
  );

  function handleCreateLead(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!leadDraft.name.trim()) return;
    createLead.mutate({ clientId, payload: leadDraft }, {
      onSuccess: () => setLeadDraft(emptyLead)
    });
  }

  function handleStageChange(lead: LeadSummary, stage: LeadStage) {
    updateLead.mutate({ clientId, leadId: lead.id, payload: { stage } });
  }

  function handleDeleteLead(lead: LeadSummary) {
    deleteLead.mutate({ clientId, leadId: lead.id });
  }

  return (
    <section className="operations-layout">
      {error && <div className="notice error">{error}</div>}

      <div className="bento-grid">
        <article className="bento-card col-span-2">
          <div className="bento-header">
            <h3>Pipeline de Leads Ativo</h3>
            <Building2 size={16} />
          </div>
          <div className="bento-value">
            {leads.filter((lead) => !["won", "lost"].includes(lead.stage)).length}
          </div>
          <div className="bento-footer">
            {formatMoney(forecast)} em oportunidades ativas no funil
          </div>
        </article>
      </div>

      <div className="operations-grid" style={{ gridTemplateColumns: "1fr" }}>
        <article className="surface">
          <SectionHeader eyebrow="CRM mínimo" title="Funil de Vendas" icon={Building2} />
          <div className="kanban-board">
            {leadStages.map((stage) => (
              <section className="kanban-column" key={stage.id}>
                <h3>{stage.label}</h3>
                {leads.filter((lead) => lead.stage === stage.id).map((lead) => (
                  <div className="lead-card" key={lead.id}>
                    <strong>{lead.name}</strong>
                    <small>{lead.company ?? "sem empresa"} · {formatMoney(lead.expected_value)}</small>
                    <p>{lead.notes || lead.source || "Sem observação."}</p>
                    {isEgAdmin && (
                      <div className="row-actions">
                        <select
                          className="status-select"
                          value={lead.stage}
                          onChange={(event) => handleStageChange(lead, event.target.value as LeadStage)}
                          disabled={updateLead.isPending}
                        >
                          {leadStages.map((option) => (
                            <option key={option.id} value={option.id}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        <button className="icon-button danger" type="button" onClick={() => handleDeleteLead(lead)}>
                          <Trash2 size={15} />
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </section>
            ))}
          </div>
        </article>
      </div>

      {isEgAdmin && (
        <section className="admin-dock">
          <form className="dock-panel" onSubmit={handleCreateLead}>
            <SectionHeader eyebrow="Novo lead" title="Adicionar oportunidade" icon={Plus} />
            <div className="form-grid two">
              <label>
                Nome
                <input value={leadDraft.name} onChange={(event) => setLeadDraft({ ...leadDraft, name: event.target.value })} />
              </label>
              <label>
                Empresa
                <input value={leadDraft.company ?? ""} onChange={(event) => setLeadDraft({ ...leadDraft, company: event.target.value })} />
              </label>
              <label>
                Etapa
                <select value={leadDraft.stage ?? "new"} onChange={(event) => setLeadDraft({ ...leadDraft, stage: event.target.value as LeadStage })}>
                  {leadStages.map((stage) => (
                    <option key={stage.id} value={stage.id}>
                      {stage.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Valor esperado
                <input
                  value={leadDraft.expected_value ?? ""}
                  onChange={(event) => setLeadDraft({ ...leadDraft, expected_value: toNullableNumber(event.target.value) })}
                />
              </label>
            </div>
            <label className="form-grid">
              Observação
              <textarea value={leadDraft.notes ?? ""} onChange={(event) => setLeadDraft({ ...leadDraft, notes: event.target.value })} />
            </label>
            <button className="primary-button" type="submit" disabled={createLead.isPending}>
              <Plus size={16} />
              Criar lead
            </button>
          </form>
        </section>
      )}
    </section>
  );
}
