import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CalendarDays, CheckCircle2, FileUp, Link2, ListChecks, Network, Plus } from "lucide-react";
import { api, type ProjectDocumentImport, type TaskSummary, type WorkEntityType, type WorkItem, type WorkItemKind, type WorkRelationType } from "../../lib/api";
import { EmptyState } from "../shared";

type ProjectRef = { id: string; name: string };
type EntityOption = { key: string; type: WorkEntityType; id: string; label: string };

const KIND_LABEL: Record<WorkItemKind, string> = {
  goal: "Objetivo", spec: "Spec", story: "User story", decision: "Decisão", plan: "Plano",
  milestone: "Marco", opportunity_event: "Oportunidade/evento", deliverable: "Entregável",
  test: "Teste", evidence: "Evidência", release: "Release", asset: "Asset",
};
const RELATION_LABEL: Record<WorkRelationType, string> = {
  derives_from: "deriva de", decomposes_into: "decompõe em", implements: "implementa",
  tests: "testa", evidences: "evidencia", decides: "decide", blocks: "bloqueia",
  supersedes: "substitui", reuses: "reutiliza", materializes: "materializa",
};
const BACKLOG_LABEL: Record<WorkItem["backlog_status"], string> = {
  candidate: "Candidato", backlog: "Backlog", ready: "Pronto", in_progress: "Em andamento",
  done: "Concluído", rejected: "Descartado",
};
const PRIORITY_LABEL: Record<WorkItem["priority"], string> = {
  critical: "Crítica", high: "Alta", medium: "Média", low: "Baixa",
};
const LANES: Array<{ title: string; kinds: WorkItemKind[]; help: string }> = [
  { title: "Por quê e o quê", kinds: ["goal", "spec", "decision", "plan"], help: "Intenção e decisões." },
  { title: "Construção", kinds: ["deliverable", "asset"], help: "O que será produzido ou reutilizado." },
  { title: "Confiança", kinds: ["test", "evidence", "release"], help: "Como provamos e entregamos." },
];
const cardStyle: React.CSSProperties = { border: "1px solid var(--border)", borderRadius: 10, padding: 12, background: "var(--surface)" };

export function WorkGraphPanel({ workspaceId, tasks, projects }: { workspaceId: string; tasks: TaskSummary[]; projects: ProjectRef[] }) {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["work-graph", workspaceId], queryFn: () => api.workGraph(workspaceId) });
  const [showItemForm, setShowItemForm] = useState(false);
  const [showLinkForm, setShowLinkForm] = useState(false);
  const [kind, setKind] = useState<WorkItemKind>("story");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [acceptance, setAcceptance] = useState("");
  const [definitionOfDone, setDefinitionOfDone] = useState("");
  const [priority, setPriority] = useState<WorkItem["priority"]>("medium");
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [storyPoints, setStoryPoints] = useState("");
  const [projectId, setProjectId] = useState("");
  const [sourceKey, setSourceKey] = useState("");
  const [targetKey, setTargetKey] = useState("");
  const [relation, setRelation] = useState<WorkRelationType>("implements");
  const [importProjectId, setImportProjectId] = useState(projects[0]?.id ?? "");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ProjectDocumentImport | null>(null);
  const [selectedCandidates, setSelectedCandidates] = useState<Set<string>>(new Set());
  const [createTasks, setCreateTasks] = useState(false);

  const { data: imports = [] } = useQuery({
    queryKey: ["project-document-imports", importProjectId],
    queryFn: () => api.projectDocumentImports(importProjectId),
    enabled: Boolean(importProjectId),
  });
  const activeImport = preview ?? imports[0] ?? null;
  useEffect(() => {
    if (activeImport?.status === "draft") setSelectedCandidates(new Set(activeImport.candidates.map((candidate) => candidate.id)));
  }, [activeImport?.id]);

  const entities = useMemo<EntityOption[]>(() => [
    ...(data?.items ?? []).map((item) => ({ key: `work_item:${item.id}`, type: "work_item" as const, id: item.id, label: `${KIND_LABEL[item.kind]} · ${item.title}` })),
    ...projects.map((project) => ({ key: `project:${project.id}`, type: "project" as const, id: project.id, label: `Projeto · ${project.name}` })),
    ...tasks.map((task) => ({ key: `task:${task.id}`, type: "task" as const, id: task.id, label: `Tarefa · ${task.title}` })),
  ], [data?.items, projects, tasks]);
  const labelByEntity = useMemo(() => new Map(entities.map((entity) => [entity.key, entity.label])), [entities]);
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["work-graph", workspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["tasks"] });
  };

  const createItem = useMutation({
    mutationFn: () => api.createWorkItem(workspaceId, {
      project_id: projectId || null, kind, title: title.trim(), summary: summary.trim() || null,
      status: "active", backlog_status: "backlog", priority,
      acceptance_criteria: acceptance.trim() || null, definition_of_done: definitionOfDone.trim() || null,
      story_points: storyPoints ? Number(storyPoints) : null,
      planned_start_at: startAt || null, planned_end_at: endAt || null, metadata: {},
    }),
    onSuccess: () => {
      setTitle(""); setSummary(""); setAcceptance(""); setDefinitionOfDone(""); setStoryPoints("");
      setStartAt(""); setEndAt(""); setShowItemForm(false); refresh();
    },
  });
  const updateItem = useMutation({
    mutationFn: ({ itemId, patch }: { itemId: string; patch: Parameters<typeof api.updateWorkItem>[2] }) => api.updateWorkItem(workspaceId, itemId, patch),
    onSuccess: refresh,
  });
  const materializeItem = useMutation({ mutationFn: (itemId: string) => api.materializeWorkItem(workspaceId, itemId), onSuccess: refresh });
  const createLink = useMutation({
    mutationFn: () => {
      const source = entities.find((item) => item.key === sourceKey);
      const target = entities.find((item) => item.key === targetKey);
      if (!source || !target) throw new Error("Selecione origem e destino.");
      return api.createWorkLink(workspaceId, { source: { type: source.type, id: source.id }, relation, target: { type: target.type, id: target.id } });
    },
    onSuccess: () => { setShowLinkForm(false); setSourceKey(""); setTargetKey(""); refresh(); },
  });
  const uploadImport = useMutation({
    mutationFn: () => {
      if (!importProjectId || !importFile) throw new Error("Selecione projeto e HTML.");
      return api.importProjectDocument(importProjectId, importFile);
    },
    onSuccess: (result) => {
      setPreview(result); setImportFile(null); setSelectedCandidates(new Set(result.candidates.map((candidate) => candidate.id)));
      void queryClient.invalidateQueries({ queryKey: ["project-document-imports", importProjectId] });
    },
  });
  const materializeImport = useMutation({
    mutationFn: () => {
      if (!activeImport) throw new Error("Nenhuma prévia disponível.");
      return api.materializeProjectDocumentImport(activeImport.id, [...selectedCandidates], createTasks);
    },
    onSuccess: (result) => {
      setPreview(result); refresh();
      void queryClient.invalidateQueries({ queryKey: ["project-document-imports", importProjectId] });
    },
  });

  if (isLoading) return <EmptyState text="Carregando backlog e rastreabilidade..." />;
  if (error) return <EmptyState text={error instanceof Error ? error.message : "Falha ao carregar o backlog."} />;
  const backlogItems = (data?.items ?? []).filter((item) => ["story", "milestone", "opportunity_event"].includes(item.kind));
  const mutationError = createItem.error || createLink.error || updateItem.error || materializeItem.error || uploadImport.error || materializeImport.error;

  return (
    <section style={{ height: "100%", overflowY: "auto", display: "grid", gap: 16 }}>
      <div className="surface" style={{ padding: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
          <div><h3 style={{ display: "flex", alignItems: "center", gap: 8 }}><ListChecks size={18} /> Backlog de produto e projeto</h3>
            <p style={{ color: "var(--text-faint)", marginTop: 4 }}>User stories, marcos e oportunidades ficam aqui; tarefas nascem somente quando materializadas.</p></div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="secondary-button" type="button" onClick={() => setShowLinkForm((value) => !value)}><Link2 size={15} /> Relacionar</button>
            <button className="primary-button" type="button" onClick={() => setShowItemForm((value) => !value)}><Plus size={15} /> Novo item</button>
          </div>
        </div>

        {showItemForm && <form onSubmit={(event) => { event.preventDefault(); if (title.trim()) createItem.mutate(); }} style={{ display: "grid", gridTemplateColumns: "160px minmax(220px, 1fr) 180px 150px", gap: 8, marginTop: 16 }}>
          <select value={kind} onChange={(event) => setKind(event.target.value as WorkItemKind)}>{Object.entries(KIND_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Título verificável" required />
          <select value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Workspace inteiro</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select>
          <select value={priority} onChange={(event) => setPriority(event.target.value as WorkItem["priority"])}>{Object.entries(PRIORITY_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <textarea value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Contexto, problema e resultado esperado" rows={2} style={{ gridColumn: "1 / -1" }} />
          <textarea value={acceptance} onChange={(event) => setAcceptance(event.target.value)} placeholder="Critérios de aceitação verificáveis" rows={2} style={{ gridColumn: "1 / 3" }} />
          <textarea value={definitionOfDone} onChange={(event) => setDefinitionOfDone(event.target.value)} placeholder="Definition of Done técnico/operacional" rows={2} style={{ gridColumn: "3 / -1" }} />
          <label><small>Início</small><input type="date" value={startAt} onChange={(event) => setStartAt(event.target.value)} /></label>
          <label><small>Fim</small><input type="date" value={endAt} onChange={(event) => setEndAt(event.target.value)} /></label>
          <label><small>Story points</small><input type="number" min={1} max={100} value={storyPoints} onChange={(event) => setStoryPoints(event.target.value)} /></label>
          <button className="primary-button" type="submit" disabled={createItem.isPending}>Adicionar ao backlog</button>
        </form>}

        {showLinkForm && <form onSubmit={(event) => { event.preventDefault(); createLink.mutate(); }} style={{ display: "grid", gridTemplateColumns: "1fr 180px 1fr auto", gap: 8, marginTop: 16 }}>
          <select value={sourceKey} onChange={(event) => setSourceKey(event.target.value)} required><option value="">Origem</option>{entities.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select>
          <select value={relation} onChange={(event) => setRelation(event.target.value as WorkRelationType)}>{Object.entries(RELATION_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <select value={targetKey} onChange={(event) => setTargetKey(event.target.value)} required><option value="">Destino</option>{entities.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select>
          <button className="primary-button" type="submit" disabled={createLink.isPending || sourceKey === targetKey}>Ligar</button>
        </form>}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 10 }}>
        {backlogItems.length === 0 && <EmptyState text="O backlog ainda está vazio. Crie uma story ou importe um documento HTML." />}
        {backlogItems.map((item) => <article key={item.id} style={cardStyle}>
          <small>{KIND_LABEL[item.kind]} · {PRIORITY_LABEL[item.priority]}</small><strong style={{ display: "block", margin: "5px 0" }}>{item.title}</strong>
          {item.summary && <p style={{ fontSize: 12, color: "var(--text-muted)" }}>{item.summary}</p>}
          {(item.planned_start_at || item.planned_end_at) && <small style={{ display: "flex", gap: 5, alignItems: "center" }}><CalendarDays size={13} /> {item.planned_start_at ?? "sem início"} → {item.planned_end_at ?? "sem fim"}</small>}
          {item.acceptance_criteria && <details><summary>Critérios de aceitação</summary><small>{item.acceptance_criteria}</small></details>}
          <div style={{ display: "flex", gap: 7, marginTop: 10, flexWrap: "wrap" }}>
            <select value={item.backlog_status} onChange={(event) => updateItem.mutate({ itemId: item.id, patch: { backlog_status: event.target.value as WorkItem["backlog_status"] } })}>{Object.entries(BACKLOG_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
            <select value={item.priority} onChange={(event) => updateItem.mutate({ itemId: item.id, patch: { priority: event.target.value as WorkItem["priority"] } })}>{Object.entries(PRIORITY_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
            {item.materialized_task_id ? <span className="status-badge"><CheckCircle2 size={12} /> tarefa criada</span> : <button className="mini-button" type="button" onClick={() => materializeItem.mutate(item.id)}>Criar tarefa</button>}
          </div>
        </article>)}
      </div>

      <article className="surface" style={{ padding: 16 }}>
        <h3 style={{ display: "flex", gap: 8, alignItems: "center" }}><FileUp size={18} /> Importar documento de projeto</h3>
        <p style={{ color: "var(--text-faint)", margin: "4px 0 12px" }}>O HTML vira uma prévia: datas, eventos, ações e cronograma só entram no backlog após sua confirmação.</p>
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr auto", gap: 8 }}>
          <select value={importProjectId} onChange={(event) => { setImportProjectId(event.target.value); setPreview(null); }}><option value="">Selecione o projeto</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select>
          <input type="file" accept=".html,.htm,text/html" onChange={(event) => setImportFile(event.target.files?.[0] ?? null)} />
          <button className="primary-button" type="button" disabled={!importProjectId || !importFile || uploadImport.isPending} onClick={() => uploadImport.mutate()}>Ler e criar prévia</button>
        </div>
        {activeImport && <div style={{ marginTop: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}><strong>{activeImport.extracted_title || activeImport.source_name}</strong><span className="status-badge">{activeImport.status} · {activeImport.candidates.length} candidatos</span></div>
          {activeImport.warnings.map((warning) => <p key={warning} className="notice" style={{ marginTop: 8 }}>{warning}</p>)}
          <div style={{ display: "grid", gap: 7, marginTop: 10, maxHeight: 360, overflowY: "auto" }}>
            {activeImport.candidates.map((candidate) => <label key={candidate.id} style={{ ...cardStyle, display: "grid", gridTemplateColumns: "20px 1fr auto", gap: 8, alignItems: "start" }}>
              <input type="checkbox" disabled={activeImport.status !== "draft"} checked={selectedCandidates.has(candidate.id)} onChange={(event) => setSelectedCandidates((current) => { const next = new Set(current); event.target.checked ? next.add(candidate.id) : next.delete(candidate.id); return next; })} />
              <span><strong>{candidate.title}</strong><small style={{ display: "block" }}>{KIND_LABEL[candidate.kind]} · {PRIORITY_LABEL[candidate.priority]}{candidate.planned_end_at ? ` · até ${candidate.planned_end_at}` : " · sem data exata"}</small>{candidate.acceptance_criteria && <small style={{ display: "block", marginTop: 4 }}>Ação: {candidate.acceptance_criteria}</small>}</span>
              <small>{String(candidate.metadata.timing ?? "")}</small>
            </label>)}
          </div>
          {activeImport.status === "draft" && <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginTop: 12, alignItems: "center" }}>
            <label style={{ display: "flex", gap: 7, alignItems: "center" }}><input type="checkbox" checked={createTasks} onChange={(event) => setCreateTasks(event.target.checked)} /> Também criar tarefas agora</label>
            <button className="primary-button" type="button" disabled={selectedCandidates.size === 0 || materializeImport.isPending} onClick={() => materializeImport.mutate()}>Confirmar {selectedCandidates.size} item(ns)</button>
          </div>}
        </div>}
      </article>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
        {LANES.map((lane) => { const items = (data?.items ?? []).filter((item) => lane.kinds.includes(item.kind)); return <article className="surface" key={lane.title} style={{ padding: 14, alignSelf: "start" }}><h4>{lane.title}</h4><small>{lane.help}</small><div style={{ display: "grid", gap: 8, marginTop: 12 }}>{items.length === 0 && <EmptyState compact text="Nenhum item." />}{items.map((item) => <div key={item.id} className="work-row"><div><small>{KIND_LABEL[item.kind]} · {item.status}</small><strong>{item.title}</strong></div></div>)}</div></article>; })}
      </div>

      <article className="surface" style={{ padding: 14 }}><h4 style={{ display: "flex", gap: 7, alignItems: "center" }}><Network size={16} /> Relações</h4><div style={{ display: "grid", gap: 6, marginTop: 10 }}>
        {(data?.links ?? []).length === 0 && <EmptyState compact text="Crie a primeira relação para explicar como o trabalho se conecta." />}
        {(data?.links ?? []).map((link) => { const source = labelByEntity.get(`${link.source_type}:${link.source_id}`) ?? `${link.source_type} · ${link.source_id.slice(0, 8)}`; const target = labelByEntity.get(`${link.target_type}:${link.target_id}`) ?? `${link.target_type} · ${link.target_id.slice(0, 8)}`; return <div className="work-row" key={link.id}><span>{source}</span><strong style={{ display: "flex", alignItems: "center", gap: 5 }}>{RELATION_LABEL[link.relation_type]} <ArrowRight size={14} /></strong><span>{target}</span></div>; })}
      </div></article>
      {mutationError && <p className="error-state">{mutationError instanceof Error ? mutationError.message : "Não foi possível concluir a operação."}</p>}
    </section>
  );
}
