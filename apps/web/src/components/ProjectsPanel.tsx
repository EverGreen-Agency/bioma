import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, BriefcaseBusiness, CalendarClock, CheckCircle2, CircleGauge, Plus } from "lucide-react";

import { api, type ProjectDetail, type ProjectPayload, type ProjectSummary, type WorkspaceSummary } from "../lib/api";
import { EmptyState, SectionHeader } from "./shared";
import { ProjectPlanner } from "./ProjectPlanner";
import { TechProjectTracking } from "./TechProjectTracking";

const STATUS_LABELS: Record<ProjectSummary["status"], string> = {
  planned: "Planejado", active: "Ativo", on_hold: "Pausado", completed: "Concluído",
  cancelled: "Cancelado", archived: "Arquivado",
};
const PACE_LABELS: Record<ProjectSummary["pace_status"], string> = {
  unknown: "Sem entregas", on_track: "No ritmo", at_risk: "Em risco", off_track: "Fora do ritmo",
};
const EMPTY_PROJECT: ProjectPayload = { name: "", project_type: "general", status: "planned", client_visible: true };
type AccessRole = WorkspaceSummary["access_role"];

export function ProjectsPanel({ workspaceId, accessRole }: { workspaceId: string; accessRole: AccessRole }) {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showProjectForm, setShowProjectForm] = useState(false);
  const [projectDraft, setProjectDraft] = useState<ProjectPayload>(EMPTY_PROJECT);
  const [contractTitle, setContractTitle] = useState("");
  const [scopeTitle, setScopeTitle] = useState("");
  const [deliverableTitle, setDeliverableTitle] = useState("");
  const [scopeItemId, setScopeItemId] = useState("");
  const canManage = ["platform_admin", "tenant_admin", "workspace_manager", "operator"].includes(accessRole);

  const projects = useQuery({ queryKey: ["projects", workspaceId], queryFn: () => api.projects(workspaceId) });
  const activeId = selectedId ?? projects.data?.[0]?.id ?? null;
  const detail = useQuery({ queryKey: ["project", activeId], queryFn: () => api.project(activeId!), enabled: Boolean(activeId) });
  const refresh = async (project?: ProjectDetail) => {
    await queryClient.invalidateQueries({ queryKey: ["projects", workspaceId] });
    if (project) queryClient.setQueryData(["project", project.id], project);
  };
  const createProject = useMutation({
    mutationFn: (payload: ProjectPayload) => api.createProject(workspaceId, payload),
    onSuccess: async (project) => {
      setProjectDraft(EMPTY_PROJECT); setShowProjectForm(false); setSelectedId(project.id); await refresh(project);
    },
  });
  const createContract = useMutation({
    mutationFn: () => api.createProjectContract(activeId!, { title: contractTitle.trim(), status: "draft" }),
    onSuccess: async (project) => { setContractTitle(""); await refresh(project); },
  });
  const currentContract = detail.data?.contracts[0] ?? null;
  const createScope = useMutation({
    mutationFn: () => api.createContractScopeItem(currentContract!.id, { title: scopeTitle.trim() }),
    onSuccess: async (project) => { setScopeTitle(""); await refresh(project); },
  });
  const scopeItems = detail.data?.contracts.flatMap((contract) => contract.scope_items) ?? [];
  const createDeliverable = useMutation({
    mutationFn: () => api.createProjectDeliverable(activeId!, { title: deliverableTitle.trim(), scope_item_id: scopeItemId || null }),
    onSuccess: async (project) => { setDeliverableTitle(""); setScopeItemId(""); await refresh(project); },
  });

  function submitProject(event: FormEvent) {
    event.preventDefault();
    createProject.mutate({
      ...projectDraft,
      name: projectDraft.name.trim(), code: projectDraft.code?.trim() || null,
      objective: projectDraft.objective?.trim() || null,
    });
  }

  return (
    <section className="projects-layout">
      <div className="projects-heading">
        <SectionHeader eyebrow="Operação contratada" title="Projetos e contratos" icon={BriefcaseBusiness} />
        {canManage && <button className="primary-button" type="button" onClick={() => setShowProjectForm((value) => !value)}><Plus size={15} /> Novo projeto</button>}
      </div>
      <p className="panel-footnote">O contrato define o escopo; as entregas mostram o realizado e o ritmo sem presumir aceite do cliente.</p>

      {showProjectForm && (
        <form className="surface project-create-form" onSubmit={submitProject}>
          <label>Nome<input required minLength={2} value={projectDraft.name} onChange={(event) => setProjectDraft({ ...projectDraft, name: event.target.value })} /></label>
          <label>Tipo<select value={projectDraft.project_type} onChange={(event) => setProjectDraft({ ...projectDraft, project_type: event.target.value as ProjectPayload["project_type"] })}><option value="general">Geral</option><option value="social">Social media</option><option value="growth">Growth</option><option value="tech">Tech</option></select></label>
          <label>Código<input value={projectDraft.code ?? ""} onChange={(event) => setProjectDraft({ ...projectDraft, code: event.target.value })} /></label>
          <label className="project-objective">Objetivo<textarea rows={2} value={projectDraft.objective ?? ""} onChange={(event) => setProjectDraft({ ...projectDraft, objective: event.target.value })} /></label>
          <button className="primary-button" type="submit" disabled={createProject.isPending}>Criar projeto</button>
          {createProject.error && <span className="form-error">{createProject.error.message}</span>}
        </form>
      )}

      {projects.isLoading && <EmptyState text="Carregando projetos..." />}
      {projects.error && <div className="notice error">{projects.error.message}</div>}
      {!projects.isLoading && projects.data?.length === 0 && <EmptyState text="Nenhum projeto cadastrado neste workspace." />}
      <div className="projects-split">
        <aside className="projects-list">
          {projects.data?.map((project) => (
            <button className={`surface project-card ${activeId === project.id ? "selected" : ""}`} type="button" key={project.id} onClick={() => setSelectedId(project.id)}>
              <span className="project-card-top"><strong>{project.name}</strong><small>{STATUS_LABELS[project.status]}</small></span>
              <span className="project-progress"><i style={{ width: `${project.completion_percentage}%` }} /></span>
              <span className={`project-pace ${project.pace_status}`}><CircleGauge size={13} /> {PACE_LABELS[project.pace_status]} · {project.deliverables_done}/{project.deliverables_total}</span>
            </button>
          ))}
        </aside>
        {detail.isLoading && <EmptyState text="Carregando projeto..." />}
        {detail.error && <div className="notice error">{detail.error.message}</div>}
        {detail.data && (
          <article className="surface project-detail">
            <header><div><span>{detail.data.code ?? detail.data.project_type}</span><h2>{detail.data.name}</h2></div><span className={`status-pill ${detail.data.status}`}>{STATUS_LABELS[detail.data.status]}</span></header>
            {detail.data.objective && <p>{detail.data.objective}</p>}
            <div className="project-metrics">
              <span><CheckCircle2 size={16} /><strong>{detail.data.completion_percentage}%</strong> concluído</span>
              <span><CalendarClock size={16} /><strong>{detail.data.deliverables_overdue}</strong> atrasadas</span>
              <span><AlertTriangle size={16} /><strong>{detail.data.deliverables_blocked}</strong> bloqueadas</span>
            </div>
            <section className="project-section"><h3>Contratos e escopo</h3>
              {detail.data.contracts.map((contract) => <div className="contract-block" key={contract.id}><div><strong>{contract.title}</strong><small>v{contract.version} · {contract.status}</small></div>{contract.scope_items.map((scope) => <div className="scope-row" key={scope.id}><span>{scope.title}</span><small>{scope.delivered_total}/{scope.quantity} {scope.unit} · {scope.accepted_total} aceitas</small></div>)}</div>)}
              {canManage && !currentContract && <form className="project-inline-form" onSubmit={(event) => { event.preventDefault(); createContract.mutate(); }}><input required minLength={2} value={contractTitle} onChange={(event) => setContractTitle(event.target.value)} placeholder="Título do primeiro contrato" /><button className="mini-button" type="submit">Criar contrato</button></form>}
              {canManage && currentContract && <form className="project-inline-form" onSubmit={(event) => { event.preventDefault(); createScope.mutate(); }}><input required minLength={2} value={scopeTitle} onChange={(event) => setScopeTitle(event.target.value)} placeholder="Novo item de escopo" /><button className="mini-button" type="submit">Adicionar escopo</button></form>}
            </section>
            <section className="project-section"><h3>Entregas</h3>
              {detail.data.deliverables.length === 0 && <p className="panel-footnote">Ainda não há entregas vinculadas.</p>}
              {detail.data.deliverables.map((item) => <div className="scope-row" key={item.id}><span>{item.title}</span><small>{item.status}{item.approval_status ? ` · aceite ${item.approval_status}` : ""}</small></div>)}
              {canManage && <form className="project-inline-form" onSubmit={(event) => { event.preventDefault(); createDeliverable.mutate(); }}><input required minLength={2} value={deliverableTitle} onChange={(event) => setDeliverableTitle(event.target.value)} placeholder="Nova entrega" /><select value={scopeItemId} onChange={(event) => setScopeItemId(event.target.value)}><option value="">Sem item de escopo</option>{scopeItems.map((scope) => <option key={scope.id} value={scope.id}>{scope.title}</option>)}</select><button className="mini-button" type="submit">Adicionar entrega</button></form>}
            </section>
            <ProjectPlanner project={detail.data} accessRole={accessRole} onChanged={refresh} />
            {detail.data.project_type === "tech" && <TechProjectTracking project={detail.data} accessRole={accessRole} onChanged={refresh} />}
          </article>
        )}
      </div>
    </section>
  );
}
