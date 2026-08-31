import { FormEvent, useMemo, useState } from "react";
import { Bot, CheckCircle2, Download, Play, ShieldCheck, Workflow } from "lucide-react";

import { EmptyState, SectionHeader } from "../components/shared";
import { CopilotWorkbench } from "../components/CopilotWorkbench";
import { CopilotAnalyticsPanel } from "../components/CopilotAnalyticsPanel";
import { AiControlPlanePanel } from "../components/AiControlPlanePanel";
import {
  useAiWorkflowDefinitions,
  useAiWorkflowRuns,
  useAiWorkflowTemplates,
  useApproveAiWorkflowRun,
  useCreateAiWorkflowRun,
  useInstallAiWorkflowTemplate,
} from "../hooks/useBiomaApi";

const runStatusLabel = {
  pending_approval: "Aguardando aprovação",
  ready: "Na fila do worker",
  running: "Em execução",
  completed: "Concluído",
  failed: "Falhou",
  cancelled: "Cancelado",
} as const;

export function AiOperationsView({ workspaceId }: { workspaceId: string }) {
  const { data: templates = [], error: templatesError } = useAiWorkflowTemplates();
  const { data: definitions = [], error: definitionsError } = useAiWorkflowDefinitions();
  const { data: runs = [], error: runsError } = useAiWorkflowRuns();
  const installTemplate = useInstallAiWorkflowTemplate();
  const createRun = useCreateAiWorkflowRun();
  const approveRun = useApproveAiWorkflowRun();
  const [definitionId, setDefinitionId] = useState("");
  const [context, setContext] = useState("");

  const installed = useMemo(
    () => new Set(definitions.map((definition) => `${definition.slug}:${definition.version}`)),
    [definitions],
  );
  const selectedDefinition = definitions.find((definition) => definition.id === definitionId);
  const requiredInputKey = selectedDefinition
    ? ((selectedDefinition.input_schema.required as string[] | undefined)?.[0] ?? "context")
    : "context";
  const error = templatesError ?? definitionsError ?? runsError;

  function handleCreateRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!definitionId || context.trim().length < 10) return;
    createRun.mutate(
      {
        definition_id: definitionId,
        workspace_id: workspaceId,
        idempotency_key: crypto.randomUUID(),
        input: { [requiredInputKey]: context.trim() },
      },
      { onSuccess: () => setContext("") },
    );
  }

  return (
    <div className="operations-layout fade-in">
      {error && <div className="notice error">{error.message}</div>}

      <AiControlPlanePanel />

      {/* Personalização do copiloto num lugar só: memória, habilidades, planos
          multi-etapa e a fila de melhorias. Antes eram painéis empilhados. */}
      <CopilotWorkbench
        workspaceId={null}
        title="Copiloto da EG"
        description="Identidade, procedimentos e planos que valem em qualquer cliente. Nada entra em uso sem sua aprovação."
      />

      <CopilotAnalyticsPanel />

      <div className="bento-grid">
        <article className="bento-card col-span-2">
          <div className="bento-header">
            <h3>Workflows instalados</h3>
            <Workflow size={16} color="var(--mint)" />
          </div>
          <div className="bento-value" style={{ color: "var(--mint)" }}>{definitions.length}</div>
          <div className="bento-footer">Definições versionadas; cada execução possui trilha e idempotência.</div>
        </article>
        <article className="bento-card col-span-2">
          <div className="bento-header">
            <h3>Aguardando HITL</h3>
            <ShieldCheck size={16} />
          </div>
          <div className="bento-value">{runs.filter((run) => run.status === "pending_approval").length}</div>
          <div className="bento-footer">Nenhum workflow começa sem aprovação explícita da EG.</div>
        </article>
      </div>

      <div className="operations-grid" style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)" }}>
        <article className="surface">
          <SectionHeader eyebrow="Catálogo" title="Fluxos prontos para instalar" icon={Bot} />
          <div className="hub-block-list">
            {templates.map((template) => {
              const isInstalled = installed.has(`${template.slug}:${template.version}`);
              return (
                <div className="work-row" key={`${template.slug}:${template.version}`}>
                  <Workflow size={16} />
                  <div>
                    <strong>{template.name} · v{template.version}</strong>
                    <small>{template.description}</small>
                    <small>{template.steps.length} etapas · {template.steps.filter((step) => step.interactive).length} checkpoints HITL</small>
                  </div>
                  <button
                    className={isInstalled ? "secondary-button" : "primary-button"}
                    type="button"
                    disabled={isInstalled || installTemplate.isPending}
                    onClick={() => installTemplate.mutate(template.slug)}
                  >
                    {isInstalled ? <CheckCircle2 size={15} /> : <Download size={15} />}
                    {isInstalled ? "Instalado" : "Instalar"}
                  </button>
                </div>
              );
            })}
          </div>
        </article>

        <article className="surface">
          <SectionHeader eyebrow="Nova execução" title="Solicitar workflow" icon={Play} />
          <form className="form-grid" onSubmit={handleCreateRun}>
            <label>
              Workflow
              <select value={definitionId} onChange={(event) => setDefinitionId(event.target.value)}>
                <option value="">Selecione</option>
                {definitions.filter((definition) => definition.status === "active").map((definition) => (
                  <option key={definition.id} value={definition.id}>{definition.name} · v{definition.version}</option>
                ))}
              </select>
            </label>
            <label>
              Contexto de entrada
              <textarea
                rows={7}
                value={context}
                onChange={(event) => setContext(event.target.value)}
                placeholder="Contrato, briefing, objetivo ou contexto necessário para este fluxo..."
              />
            </label>
            {selectedDefinition && (
              <small>
                Etapas: {selectedDefinition.steps.map((step) => step.name).join(" → ")}
              </small>
            )}
            <button className="primary-button" type="submit" disabled={!definitionId || context.trim().length < 10 || createRun.isPending}>
              <Play size={16} />
              Criar e enviar para aprovação
            </button>
          </form>
        </article>
      </div>

      <article className="surface">
        <SectionHeader eyebrow="Execuções" title="Trilha operacional" icon={Workflow} />
        <div className="hub-block-list">
          {runs.length === 0 && <EmptyState compact text="Nenhuma execução criada." />}
          {runs.map((run) => (
            <div className="work-row" key={run.id}>
              <Bot size={16} />
              <div>
                <strong>{run.definition_name} · v{run.definition_version}</strong>
                <small>{runStatusLabel[run.status]}{run.current_step_key ? ` · etapa atual: ${run.current_step_key}` : ""}</small>
                <small>
                  {run.steps.map((step) => `${step.name}: ${step.status}${step.model ? ` (${step.provider}/${step.model})` : ""}`).join(" · ")}
                </small>
                {run.steps.filter((step) => step.output?.text).map((step) => (
                  <details key={step.id} style={{ marginTop: 8 }}>
                    <summary>{step.name} · ver entrega</summary>
                    <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: 13 }}>
                      {String(step.output?.text)}
                    </pre>
                  </details>
                ))}
              </div>
              <div className="row-tail">
                <span className={`status-pill ${run.status}`}>{runStatusLabel[run.status]}</span>
                {run.status === "pending_approval" && (
                  <button className="primary-button" type="button" disabled={approveRun.isPending} onClick={() => approveRun.mutate(run.id)}>
                    <ShieldCheck size={15} />
                    {run.steps.some((step) => step.step_key === run.current_step_key && step.status === "waiting_approval")
                      ? "Aprovar entrega e continuar"
                      : "Aprovar início"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}
