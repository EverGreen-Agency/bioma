import { useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bug, FileText, FlaskConical, Github, GitPullRequest, ListChecks, Rocket, Send } from "lucide-react";
import { GitHubCompletionSuggestions } from "./GitHubCompletionSuggestions";

import { api, type ProjectDetail, type ProjectDocument, type ProjectPhaseStatus, type WorkspaceSummary } from "../lib/api";

const PHASE_LABELS: Record<ProjectPhaseStatus, string> = {
  planned: "Planejada",
  development: "Em desenvolvimento",
  blocked: "Bloqueada",
  internal_testing: "Em testes internos",
  client_validation: "Em validação do cliente",
  released: "Publicada",
};
const DOCUMENT_LABELS: Record<ProjectDocument["kind"], string> = {
  proposal: "Proposta",
  technical_spec: "Documento técnico",
  scope: "Escopo",
  acceptance: "Aceite",
  release_notes: "Notas de release",
};
const UPDATE_ICON = { progress: ListChecks, blocker: Bug, testing: FlaskConical, release: Rocket, note: Send };
type AccessRole = WorkspaceSummary["access_role"];

export function TechProjectTracking({ project, accessRole, onChanged }: {
  project: ProjectDetail;
  accessRole: AccessRole;
  onChanged: (project: ProjectDetail) => Promise<void>;
}) {
  const canManage = ["platform_admin", "tenant_admin", "workspace_manager", "operator"].includes(accessRole);
  const [phaseName, setPhaseName] = useState("");
  const [phaseSummary, setPhaseSummary] = useState("");
  const [documentKind, setDocumentKind] = useState<ProjectDocument["kind"]>("proposal");
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentUrl, setDocumentUrl] = useState("");
  const [documentContractId, setDocumentContractId] = useState("");
  const [documentExcerpt, setDocumentExcerpt] = useState("");
  const [updateKind, setUpdateKind] = useState<"progress" | "blocker" | "testing" | "release" | "note">("progress");
  const [updateSummary, setUpdateSummary] = useState("");
  const [updatePhaseId, setUpdatePhaseId] = useState("");
  const [githubRepository, setGithubRepository] = useState("");
  const [githubBranch, setGithubBranch] = useState("main");

  const githubConnection = useQuery({
    queryKey: ["github-connection", project.id],
    queryFn: () => api.githubConnection(project.id),
    retry: false,
  });
  const githubActivity = useQuery({
    queryKey: ["github-activity", project.id],
    queryFn: () => api.githubProjectActivity(project.id),
    enabled: githubConnection.isSuccess && githubConnection.data.status === "active",
    retry: false,
  });

  const createPhase = useMutation({
    mutationFn: () => api.createProjectPhase(project.id, {
      sequence: project.phases.length + 1,
      name: phaseName.trim(),
      status: "planned",
      client_summary: phaseSummary.trim() || null,
    }),
    onSuccess: async (next) => { setPhaseName(""); setPhaseSummary(""); await onChanged(next); },
  });
  const createDocument = useMutation({
    mutationFn: () => api.createProjectDocument(project.id, {
      kind: documentKind,
      title: documentTitle.trim(),
      url: documentUrl.trim(),
      contract_id: documentContractId || null,
      planning_excerpt: documentExcerpt.trim() || null,
    }),
    onSuccess: async (next) => {
      setDocumentTitle(""); setDocumentUrl(""); setDocumentContractId(""); setDocumentExcerpt(""); await onChanged(next);
    },
  });
  const createUpdate = useMutation({
    mutationFn: () => api.createProjectUpdate(project.id, {
      phase_id: updatePhaseId || null,
      kind: updateKind,
      summary: updateSummary.trim(),
    }),
    onSuccess: async (next) => { setUpdateSummary(""); await onChanged(next); },
  });
  const configureGitHub = useMutation({
    mutationFn: () => api.configureGitHubConnection(project.id, {
      repository: githubRepository.trim(), default_branch: githubBranch.trim(), status: "active",
    }),
    onSuccess: async () => {
      setGithubRepository("");
      await githubConnection.refetch();
    },
  });
  const publishGitHubUpdate = useMutation({
    mutationFn: () => api.publishGitHubProjectUpdate(project.id, true),
    onSuccess: async () => {
      await onChanged(await api.project(project.id));
    },
  });

  function submitPhase(event: FormEvent) { event.preventDefault(); createPhase.mutate(); }
  function submitDocument(event: FormEvent) { event.preventDefault(); createDocument.mutate(); }
  function submitUpdate(event: FormEvent) { event.preventDefault(); createUpdate.mutate(); }
  function submitGitHub(event: FormEvent) { event.preventDefault(); configureGitHub.mutate(); }

  return (
    <section className="project-section tech-tracking">
      <h3>Roadmap técnico</h3>
      <p className="panel-footnote">Fases, validações e atualizações de engenharia explicam o andamento sem transformar tempo de debugging em “avanço” artificial.</p>

      <div className="tech-documents">
        <h4><Github size={15} /> GitHub do projeto</h4>
        {githubConnection.data && <p className="panel-footnote">Repositório canônico: <a href={`https://github.com/${githubConnection.data.repository}`} target="_blank" rel="noreferrer">{githubConnection.data.repository}</a> · branch {githubConnection.data.default_branch}</p>}
        {!githubConnection.data && <p className="panel-footnote">Nenhum repositório ligado. O Bioma consulta atividade em leitura e não cria issues ou PRs automaticamente.</p>}
        {canManage && <form className="project-inline-form tech-form" onSubmit={submitGitHub}>
          <input required pattern="[^/]+/[^/]+" value={githubRepository} onChange={(event) => setGithubRepository(event.target.value)} placeholder="owner/repository" />
          <input required value={githubBranch} onChange={(event) => setGithubBranch(event.target.value)} placeholder="main" />
          <button className="mini-button" type="submit" disabled={configureGitHub.isPending}>Conectar repositório</button>
        </form>}
        {configureGitHub.error && <p className="form-error">{configureGitHub.error.message}</p>}
        {githubActivity.error && githubConnection.data && <p className="panel-footnote">Conexão salva. A leitura ficará disponível quando o token GitHub for configurado no ambiente.</p>}
        {githubActivity.data && <div className="tech-phase-list">
          <article className="tech-phase development"><div><strong>{githubActivity.data.issues.length} issues</strong><span>Leitura</span></div>{githubActivity.data.issues.slice(0, 3).map((issue) => <a key={issue.number} href={issue.url} target="_blank" rel="noreferrer">#{issue.number} {issue.title}</a>)}</article>
          <article className="tech-phase internal_testing"><div><strong>{githubActivity.data.pull_requests.length} pull requests</strong><span><GitPullRequest size={13} /> Revisões</span></div>{githubActivity.data.pull_requests.slice(0, 3).map((pull) => <a key={pull.number} href={pull.url} target="_blank" rel="noreferrer">#{pull.number} {pull.title}</a>)}</article>
          <article className="tech-phase released"><div><strong>{githubActivity.data.commits.length} commits recentes</strong><span>Branch</span></div>{githubActivity.data.commits.slice(0, 3).map((commit) => <a key={commit.sha} href={commit.url} target="_blank" rel="noreferrer">{commit.sha.slice(0, 7)} {commit.message}</a>)}</article>
        </div>}
        {/* Decisao 9: issue fechada la, entrega aberta aqui. Sem botao de
            concluir — concluir entrega tem aceite separado, de proposito. */}
        <GitHubCompletionSuggestions
          projectId={project.id}
          enabled={githubConnection.isSuccess && githubConnection.data?.status === "active"}
        />
        {githubActivity.data && canManage && (
          <button
            className="mini-button"
            type="button"
            disabled={publishGitHubUpdate.isPending}
            onClick={() => publishGitHubUpdate.mutate()}
          >
            Publicar snapshot no hub do cliente
          </button>
        )}
        {publishGitHubUpdate.error && <p className="form-error">{publishGitHubUpdate.error.message}</p>}
      </div>

      <div className="tech-phase-list">
        {project.phases.map((phase) => (
          <article className={`tech-phase ${phase.status}`} key={phase.id}>
            <div><strong>Fase {phase.sequence} · {phase.name}</strong><span>{PHASE_LABELS[phase.status]}</span></div>
            {phase.client_summary && <p>{phase.client_summary}</p>}
            <small>{phase.deliverables_done}/{phase.deliverables_total} entregas concluídas</small>
          </article>
        ))}
      </div>
      {canManage && <form className="project-inline-form tech-form" onSubmit={submitPhase}>
        <input required minLength={2} value={phaseName} onChange={(event) => setPhaseName(event.target.value)} placeholder="Ex.: Evolução 2 — agenda e prontuário" />
        <input value={phaseSummary} onChange={(event) => setPhaseSummary(event.target.value)} placeholder="Resumo para o cliente" />
        <button className="mini-button" type="submit" disabled={createPhase.isPending}>Adicionar fase</button>
      </form>}

      <div className="tech-documents">
        <h4><FileText size={15} /> Documentos do projeto</h4>
        {project.documents.length === 0 && <p className="panel-footnote">Vincule proposta, escopo e documento técnico para a equipe e o cliente encontrarem a referência correta.</p>}
        {project.documents.map((document) => <div className="tech-document" key={document.id}><a href={document.url} target="_blank" rel="noreferrer"><span>{DOCUMENT_LABELS[document.kind]}</span>{document.title}</a>{document.contract_id && <small>Vinculado ao contrato</small>}{document.planning_excerpt && <small>Incluído no planejador</small>}</div>)}
        {canManage && <form className="project-inline-form tech-form" onSubmit={submitDocument}>
          <select value={documentKind} onChange={(event) => setDocumentKind(event.target.value as ProjectDocument["kind"])}>{Object.entries(DOCUMENT_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <select value={documentContractId} onChange={(event) => setDocumentContractId(event.target.value)}><option value="">Referência geral do projeto</option>{project.contracts.map((contract) => <option key={contract.id} value={contract.id}>Contrato v{contract.version}: {contract.title}</option>)}</select>
          <input required minLength={2} value={documentTitle} onChange={(event) => setDocumentTitle(event.target.value)} placeholder="Título do documento" />
          <input required type="url" value={documentUrl} onChange={(event) => setDocumentUrl(event.target.value)} placeholder="https://..." />
          <textarea rows={3} value={documentExcerpt} onChange={(event) => setDocumentExcerpt(event.target.value)} placeholder="Trecho ou resumo confirmado para o planejador (opcional; não invente conteúdo do documento)." />
          <button className="mini-button" type="submit" disabled={createDocument.isPending}>Vincular</button>
        </form>}
      </div>

      <div className="tech-updates">
        <h4>Atualizações para o cliente</h4>
        {project.updates.length === 0 && <p className="panel-footnote">Ainda não há atualizações publicadas.</p>}
        {project.updates.map((update) => {
          const Icon = UPDATE_ICON[update.kind];
          return <div className={`tech-update ${update.kind}`} key={update.id}><Icon size={15} /><div><strong>{update.summary}</strong><small>{new Date(update.created_at).toLocaleDateString("pt-BR")}</small></div></div>;
        })}
        {canManage && <form className="project-inline-form tech-form" onSubmit={submitUpdate}>
          <select value={updateKind} onChange={(event) => setUpdateKind(event.target.value as typeof updateKind)}><option value="progress">Avanço</option><option value="blocker">Bloqueio/debug</option><option value="testing">Teste</option><option value="release">Release</option><option value="note">Nota</option></select>
          <select value={updatePhaseId} onChange={(event) => setUpdatePhaseId(event.target.value)}><option value="">Projeto geral</option>{project.phases.map((phase) => <option key={phase.id} value={phase.id}>Fase {phase.sequence}: {phase.name}</option>)}</select>
          <input required minLength={3} value={updateSummary} onChange={(event) => setUpdateSummary(event.target.value)} placeholder="Ex.: corrigimos a inconsistência de sincronização; sem entrega nova hoje." />
          <button className="mini-button" type="submit" disabled={createUpdate.isPending}>Publicar atualização</button>
        </form>}
      </div>
    </section>
  );
}
