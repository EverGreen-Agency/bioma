import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, ChevronDown, ExternalLink, GitBranch, ListTree, Pencil, Save, Sparkles } from "lucide-react";

import { api, type PlanningIntakeSchemaKey, type ProjectDetail, type ProjectPlan, type ProjectPlanItem, type ProjectPlanningIntake, type WorkspaceSummary } from "../lib/api";

type AccessRole = WorkspaceSummary["access_role"];

const PLAN_STATUS: Record<ProjectPlan["status"], string> = {
  draft: "Rascunho",
  approved: "Aprovado",
  materialized: "Aplicado ao projeto",
  superseded: "Substituído",
};

const APPROVAL_FLOW = {
  adaptive: "Adaptativo por cliente",
  idea_before_production: "Aprovar ideia antes da produção",
  after_production: "Aprovar após produção",
  final_only: "Aprovar somente versão final",
} as const;

const PRIORITY_LABEL: Record<ProjectPlanItem["priority"], string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

const MATURITY_LABEL: Record<string, string> = {
  none: "Não fazemos marketing",
  ad_hoc: "Fazemos ações pontuais",
  recurring_unmeasured: "Ações recorrentes, sem métricas",
  measured_strategy: "Estratégia definida com métricas",
  advanced_automation: "Marketing avançado com automação",
  unstructured: "Não há processo comercial estruturado",
  relationship_led: "Vendas baseadas em relacionamento pessoal",
  clear_pipeline: "Funil comercial claro",
  measured_crm: "Processo comercial com métricas e CRM",
};

const GOAL_LABEL: Record<string, string> = {
  positioning_basics: "Fundamentos de posicionamento", first_channels: "Primeiros canais", first_campaign: "Primeira campanha",
  content_consistency: "Consistência de conteúdo", campaign_calendar: "Calendário de campanhas", first_metrics: "Primeiras métricas",
  measurement_foundation: "Base de mensuração", funnel_optimization: "Otimização do funil", content_performance: "Performance de conteúdo",
  automation: "Automação", segmentation: "Segmentação", attribution: "Atribuição",
  personalization_at_scale: "Personalização em escala", implement_ai_ml: "Implementar IA/Machine Learning", predictive_marketing: "Marketing preditivo", advanced_omnichannel: "Omnichannel avançado", attribution_modeling: "Attribution modeling",
  define_sales_process: "Definir processo comercial", ideal_customer_profile: "Perfil de cliente ideal", basic_scripts: "Scripts básicos",
  pipeline_visibility: "Visibilidade do funil", sales_routine: "Rotina comercial", lead_qualification: "Qualificação de leads",
  crm_implementation: "Implementar CRM", conversion_metrics: "Métricas de conversão", sales_enablement: "Sales enablement",
  sales_automation: "Automação comercial", revenue_operations: "Revenue operations", forecasting: "Forecasting",
  sales_intelligence: "Implementar sales intelligence", predictive_personalization: "Personalização preditiva", nurturing_automation: "Automação de nurturing", advanced_revops: "Revenue operations avançado", ai_sales_coaching: "AI-powered sales coaching",
  other: "Outro",
};

type CandidateDraft = Pick<
  ProjectPlanItem,
  "phase_name" | "title" | "description" | "due_offset_days" | "client_visible" |
  "approval_required" | "priority" | "definition_of_done" | "subtasks"
>;

export function ProjectPlanner({
  project,
  accessRole,
  onChanged,
}: {
  project: ProjectDetail;
  accessRole: AccessRole;
  onChanged: (project: ProjectDetail) => Promise<void>;
}) {
  const canManage = ["platform_admin", "tenant_admin", "workspace_manager", "operator"].includes(accessRole);
  const canApprove = ["platform_admin", "tenant_admin", "workspace_manager", "approver"].includes(accessRole);
  const intakeSchemaKey: PlanningIntakeSchemaKey = project.project_type === "tech"
    ? "tech_v1"
    : project.project_type === "growth" || project.project_type === "social"
      ? "growth_social_v1"
      : "retail_v1";
  const [briefing, setBriefing] = useState("");
  const [technicalContext, setTechnicalContext] = useState("");
  const [contractId, setContractId] = useState("");
  const [approvalFlow, setApprovalFlow] = useState<keyof typeof APPROVAL_FLOW>("adaptive");
  const [intakeId, setIntakeId] = useState<string | null>(null);
  const [intakeTitle, setIntakeTitle] = useState(project.name);
  const [intakeObjective, setIntakeObjective] = useState(project.objective ?? "");
  const [intakeAnswers, setIntakeAnswers] = useState<Record<string, unknown>>(() =>
    intakeSchemaKey === "retail_v1"
      ? {
          product_categories: [], upsell_cross_sell: "", operating_channels: [],
          has_loyalty_program: false, campaign_types: "", has_customer_system: false,
          marketing_maturity: "none", marketing_goal: "positioning_basics",
          commercial_maturity: "unstructured", commercial_goal: "define_sales_process",
        }
      : {},
  );
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [candidateDraft, setCandidateDraft] = useState<CandidateDraft | null>(null);
  const clientProfile = useQuery({
    queryKey: ["client-profile", project.workspace_id],
    queryFn: () => api.clientProfile(project.workspace_id),
  });
  const intakeSchema = useQuery({
    queryKey: ["project-planning-intake-schema", project.id, intakeSchemaKey],
    queryFn: () => api.projectPlanningIntakeSchema(project.id, intakeSchemaKey),
    enabled: canManage,
  });
  const intakes = useQuery({
    queryKey: ["project-planning-intakes", project.id],
    queryFn: () => api.projectPlanningIntakes(project.id),
    enabled: canManage,
  });

  useEffect(() => {
    const draft = intakes.data?.find((item) => item.status === "draft" && item.schema_key === intakeSchemaKey);
    if (!draft) return;
    setIntakeId(draft.id);
    setIntakeTitle(draft.title);
    setIntakeObjective(draft.objective);
    setIntakeAnswers(draft.answers);
  }, [intakeSchemaKey, intakes.data]);

  const refresh = async () => onChanged(await api.project(project.id));
  const generate = useMutation({
    mutationFn: () => {
      const contract = project.contracts.find((item) => item.id === contractId) ?? project.contracts[0];
      return api.generateProjectPlan(project.id, {
        contract_id: contract?.id ?? null,
        source_kind: contract ? "contract" : briefing.trim() ? "briefing" : "onboarding",
        briefing: briefing.trim() || null,
        technical_context: technicalContext.trim() || null,
        objective: project.objective,
        planning_intake_id: intakeId,
        social_approval_flow: approvalFlow,
      });
    },
    onSuccess: refresh,
  });
  const approve = useMutation({
    mutationFn: (planId: string) => api.approveProjectPlan(planId),
    onSuccess: refresh,
  });
  const materialize = useMutation({
    mutationFn: (planId: string) => api.materializeProjectPlan(planId),
    onSuccess: onChanged,
  });
  const updateCandidate = useMutation({
    mutationFn: ({ itemId, payload }: { itemId: string; payload: Partial<CandidateDraft> & { selected?: boolean } }) =>
      api.updateProjectPlanItem(itemId, payload),
    onSuccess: async () => {
      setEditingItemId(null);
      setCandidateDraft(null);
      await refresh();
    },
  });
  const bulkSelection = useMutation({
    mutationFn: ({ plan, selected }: { plan: ProjectPlan; selected: boolean }) =>
      Promise.all(
        plan.items
          .filter((item) => item.selected !== selected)
          .map((item) => api.updateProjectPlanItem(item.id, { selected })),
      ),
    onSuccess: refresh,
  });
  const createIssue = useMutation({
    mutationFn: ({ deliverableId, body }: { deliverableId: string; body: string }) =>
      api.createGitHubIssue(deliverableId, body),
    onSuccess: refresh,
  });
  const saveIntake = useMutation({
    mutationFn: () => {
      const payload = { schema_key: intakeSchemaKey, title: intakeTitle.trim(), objective: intakeObjective.trim(), answers: intakeAnswers };
      return intakeId
        ? api.updateProjectPlanningIntake(intakeId, payload)
        : api.createProjectPlanningIntake(project.id, payload);
    },
    onSuccess: async (saved) => {
      setIntakeId(saved.id);
      await intakes.refetch();
    },
  });
  const finalizeIntake = useMutation({
    mutationFn: async () => {
      const saved = intakeId
        ? await api.updateProjectPlanningIntake(intakeId, { title: intakeTitle.trim(), objective: intakeObjective.trim(), answers: intakeAnswers })
        : await api.createProjectPlanningIntake(project.id, { schema_key: intakeSchemaKey, title: intakeTitle.trim(), objective: intakeObjective.trim(), answers: intakeAnswers });
      setIntakeId(saved.id);
      return api.finalizeProjectPlanningIntake(saved.id);
    },
    onSuccess: async (saved) => {
      setIntakeId(saved.id);
      await intakes.refetch();
    },
  });

  const error = generate.error ?? approve.error ?? materialize.error ?? updateCandidate.error
    ?? bulkSelection.error ?? createIssue.error ?? saveIntake.error ?? finalizeIntake.error;

  const beginEdit = (item: ProjectPlanItem) => {
    setEditingItemId(item.id);
    setCandidateDraft({
      phase_name: item.phase_name,
      title: item.title,
      description: item.description,
      due_offset_days: item.due_offset_days,
      client_visible: item.client_visible,
      approval_required: item.approval_required,
      priority: item.priority,
      definition_of_done: item.definition_of_done,
      subtasks: item.subtasks,
    });
  };

  return (
    <section className="project-section project-planner">
      <h3><ListTree size={16} /> Planejador do projeto</h3>
      <p className="panel-footnote">
        Converte contrato ou briefing em um plano versionado. O plano precisa de aprovação antes de criar fases e entregas no Hub.
        {project.project_type === "tech"
          ? " Itens técnicos podem virar issues, sempre com confirmação individual."
          : " Este fluxo permanece dentro do Bioma e não cria issues no GitHub."}
      </p>
      <div className="notice">
        <strong>Contexto do cliente: {clientProfile.isLoading ? "carregando..." : `${clientProfile.data?.completion_percentage ?? 0}% completo`}</strong>
        <span style={{ display: "block", marginTop: 4 }}>
          Contrato, escopo, documentos e contexto cadastrado qualificam o backlog. Campos ausentes viram premissas, nunca fatos inventados.
        </span>
      </div>

      {canManage && (
        <div className="surface" style={{ padding: 14, display: "grid", gap: 10 }}>
          <details>
            <summary><strong>Intake estratégica versionada</strong> · rascunho antes da IA</summary>
            <div style={{ display: "grid", gap: 10, paddingTop: 12 }}>
              <p className="panel-footnote" style={{ margin: 0 }}>O contexto é salvo no projeto e congelado ao finalizar. Ele não altera o perfil permanente do cliente.</p>
              <input value={intakeTitle} onChange={(event) => setIntakeTitle(event.target.value)} placeholder="Título do planejamento" />
              <textarea rows={3} value={intakeObjective} onChange={(event) => setIntakeObjective(event.target.value)} placeholder="Objetivo principal" />
              <span className="status-badge">{intakeSchema.data?.label ?? intakeSchemaKey}</span>
              {intakeSchemaKey === "retail_v1" ? (
                <>
              <label>Produtos ou categorias (separados por vírgula)
                <input value={(intakeAnswers.product_categories as string[] ?? []).join(", ")} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, product_categories: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} />
              </label>
              <label>Canais de operação (separados por vírgula)
                <input value={(intakeAnswers.operating_channels as string[] ?? []).join(", ")} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, operating_channels: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} />
              </label>
              <label>Upsell/cross-sell
                <select value={String(intakeAnswers.upsell_cross_sell ?? "")} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, upsell_cross_sell: event.target.value })}>
                  <option value="">Selecione</option><option value="never">Não ou raramente</option><option value="informal">Sim, de modo informal</option><option value="defined">Sim, com estratégia ou sistema</option><option value="other">Outro</option>
                </select>
              </label>
              <label>Ticket médio (centavos)
                <input type="number" min={0} value={String(intakeAnswers.average_ticket_cents ?? "")} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, average_ticket_cents: event.target.value === "" ? undefined : Number(event.target.value) })} />
              </label>
              <label>Campanhas mais usadas
                <input value={String(intakeAnswers.campaign_types ?? "")} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, campaign_types: event.target.value })} />
              </label>
              <label><input type="checkbox" checked={Boolean(intakeAnswers.has_loyalty_program)} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, has_loyalty_program: event.target.checked })} /> Programa de fidelidade</label>
              <label><input type="checkbox" checked={Boolean(intakeAnswers.has_customer_system)} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, has_customer_system: event.target.checked })} /> CRM, ERP ou analytics de clientes</label>
              <label>Maturidade de marketing
                <select value={String(intakeAnswers.marketing_maturity)} onChange={(event) => {
                  const maturity = event.target.value; const goals = intakeSchema.data?.marketing_goals_by_maturity[maturity] ?? [];
                  setIntakeAnswers({ ...intakeAnswers, marketing_maturity: maturity, marketing_goal: goals[0] ?? "" });
                }}>
                  {(intakeSchema.data?.marketing_maturities ?? []).map((value) => <option key={value} value={value}>{MATURITY_LABEL[value] ?? value}</option>)}
                </select>
              </label>
              <label>Meta prioritária de marketing
                <select value={String(intakeAnswers.marketing_goal)} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, marketing_goal: event.target.value })}>
                  {(intakeSchema.data?.marketing_goals_by_maturity[String(intakeAnswers.marketing_maturity)] ?? []).map((value) => <option key={value} value={value}>{GOAL_LABEL[value] ?? value}</option>)}
                </select>
              </label>
              <label>Maturidade comercial
                <select value={String(intakeAnswers.commercial_maturity)} onChange={(event) => {
                  const maturity = event.target.value; const goals = intakeSchema.data?.commercial_goals_by_maturity[maturity] ?? [];
                  setIntakeAnswers({ ...intakeAnswers, commercial_maturity: maturity, commercial_goal: goals[0] ?? "" });
                }}>
                  {(intakeSchema.data?.commercial_maturities ?? []).map((value) => <option key={value} value={value}>{MATURITY_LABEL[value] ?? value}</option>)}
                </select>
              </label>
              <label>Meta prioritária comercial
                <select value={String(intakeAnswers.commercial_goal)} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, commercial_goal: event.target.value })}>
                  {(intakeSchema.data?.commercial_goals_by_maturity[String(intakeAnswers.commercial_maturity)] ?? []).map((value) => <option key={value} value={value}>{GOAL_LABEL[value] ?? value}</option>)}
                </select>
              </label>
                </>
              ) : (
                <>
                  {(intakeSchema.data?.fields ?? []).map((field) => (
                    <label key={field.key}>{field.label}
                      {field.type === "select" ? (
                        <select value={String(intakeAnswers[field.key] ?? "")} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, [field.key]: event.target.value })}>
                          <option value="">Selecione</option>
                          {(field.options ?? []).map((option) => <option key={option} value={option}>{option.replaceAll("_", " ")}</option>)}
                        </select>
                      ) : field.type === "textarea" ? (
                        <textarea rows={3} value={String(intakeAnswers[field.key] ?? "")} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, [field.key]: event.target.value })} />
                      ) : field.type === "multi_text" ? (
                        <input value={((intakeAnswers[field.key] as string[] | undefined) ?? []).join(", ")} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, [field.key]: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} placeholder="Separe por vírgulas" />
                      ) : (
                        <input value={String(intakeAnswers[field.key] ?? "")} onChange={(event) => setIntakeAnswers({ ...intakeAnswers, [field.key]: event.target.value })} />
                      )}
                    </label>
                  ))}
                </>
              )}
              <div style={{ display: "flex", gap: 8 }}>
                <button className="mini-button" type="button" disabled={saveIntake.isPending || finalizeIntake.isPending} onClick={() => saveIntake.mutate()}><Save size={14} /> Salvar rascunho</button>
                <button className="mini-button" type="button" disabled={finalizeIntake.isPending || intakeSchema.isLoading} onClick={() => finalizeIntake.mutate()}><CheckCircle2 size={14} /> Finalizar intake</button>
              </div>
              {intakes.data?.filter((item) => item.status === "finalized").length ? <small className="panel-footnote">Uma intake finalizada fica congelada e pode ser usada na próxima versão do plano.</small> : null}
            </div>
          </details>
          {!project.contracts.length && (
            <textarea
              rows={3}
              value={briefing}
              onChange={(event) => setBriefing(event.target.value)}
              placeholder="Briefing opcional. Sem contrato ou briefing, o plano parte do objetivo e do onboarding."
            />
          )}
          {project.contracts.length > 1 && (
            <label style={{ display: "grid", gap: 4 }}>
              <span className="panel-footnote">Contrato de referência</span>
              <select value={contractId} onChange={(event) => setContractId(event.target.value)}>
                <option value="">Versão mais recente</option>
                {project.contracts.map((contract) => <option value={contract.id} key={contract.id}>v{contract.version} · {contract.title}</option>)}
              </select>
            </label>
          )}
          {project.project_type === "tech" && (
            <textarea
              rows={4}
              value={technicalContext}
              onChange={(event) => setTechnicalContext(event.target.value)}
              placeholder="Contexto técnico complementar: requisitos, integrações, restrições, critérios de teste ou trecho confirmado da especificação."
            />
          )}
          {project.project_type === "social" && (
            <label style={{ display: "grid", gap: 4 }}>
              <span className="panel-footnote">Momento de aprovação do cliente</span>
              <select value={approvalFlow} onChange={(event) => setApprovalFlow(event.target.value as keyof typeof APPROVAL_FLOW)}>
                {Object.entries(APPROVAL_FLOW).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
              </select>
            </label>
          )}
          <button className="mini-button" type="button" disabled={generate.isPending} onClick={() => generate.mutate()}>
            <Sparkles size={14} /> {generate.isPending ? "Planejando..." : "Gerar nova versão do plano"}
          </button>
        </div>
      )}

      {error && <p className="form-error">{error.message}</p>}
      {project.plans.length === 0 && <p className="panel-footnote">Nenhum plano gerado para este projeto.</p>}

      {project.plans.map((plan) => (
        <article className="surface" key={plan.id} style={{ padding: 14, marginTop: 10 }}>
          <header style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
            <div>
              <strong>{plan.title}</strong>
              <small style={{ display: "block" }}>
                v{plan.version} · {PLAN_STATUS[plan.status]} · {plan.generation_mode}
              </small>
            </div>
            <span className={`status-pill ${plan.status}`}>{plan.discipline}</span>
          </header>
          {plan.objective && <p>{plan.objective}</p>}
          {plan.assumptions.length > 0 && (
            <ul className="panel-footnote">
              {plan.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}
            </ul>
          )}

          {plan.status === "draft" && (
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", marginBottom: 8 }}>
              <small>{plan.items.filter((item) => item.selected).length} de {plan.items.length} candidatos selecionados</small>
              {canManage && (
                <span style={{ display: "flex", gap: 6 }}>
                  <button className="mini-button" type="button" disabled={bulkSelection.isPending} onClick={() => bulkSelection.mutate({ plan, selected: true })}>
                    Selecionar todos
                  </button>
                  <button className="mini-button" type="button" disabled={bulkSelection.isPending} onClick={() => bulkSelection.mutate({ plan, selected: false })}>
                    Limpar seleção
                  </button>
                </span>
              )}
            </div>
          )}

          <div style={{ display: "grid", gap: 7 }}>
            {(plan.status === "draft" ? plan.items : plan.items.filter((item) => item.selected)).map((item) => (
              <details className="scope-row" key={item.id} style={{ display: "block" }}>
                <summary style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                  {plan.status === "draft" && canManage && (
                    <input
                      type="checkbox"
                      checked={item.selected}
                      disabled={updateCandidate.isPending}
                      aria-label={`Selecionar ${item.title}`}
                      onClick={(event) => event.stopPropagation()}
                      onChange={(event) => updateCandidate.mutate({ itemId: item.id, payload: { selected: event.target.checked } })}
                    />
                  )}
                  <ChevronDown size={13} />
                  <span style={{ flex: 1 }}>
                    <strong>{item.phase_name}</strong> · {item.title}
                    {item.approval_required && <small> · exige aceite</small>}
                  </span>
                  <small>{PRIORITY_LABEL[item.priority]} · {item.materialized_deliverable_id ? "Entrega criada" : `D+${item.due_offset_days ?? "—"}`}</small>
                </summary>

                <div style={{ display: "grid", gap: 8, padding: "10px 4px 2px 28px" }}>
                  {item.description && <p style={{ margin: 0 }}>{item.description}</p>}
                  {item.definition_of_done && (
                    <div><strong>Definição de pronto</strong><p style={{ margin: "4px 0 0" }}>{item.definition_of_done}</p></div>
                  )}
                  {item.subtasks.length > 0 && (
                    <div><strong>Subtarefas</strong><ul>{item.subtasks.map((subtask) => <li key={subtask}>{subtask}</li>)}</ul></div>
                  )}
                  <small>
                    {item.client_visible ? "Visível ao cliente" : "Somente equipe"}
                    {item.github_issue_url && (
                      <> · <a href={item.github_issue_url} target="_blank" rel="noreferrer">issue #{item.github_issue_number} <ExternalLink size={11} /></a></>
                    )}
                  </small>

                  {plan.status === "draft" && canManage && editingItemId !== item.id && (
                    <button className="mini-button" type="button" onClick={() => beginEdit(item)}>
                      <Pencil size={13} /> Editar candidato
                    </button>
                  )}
                  {plan.status === "draft" && canManage && editingItemId === item.id && candidateDraft && (
                    <div className="surface" style={{ display: "grid", gap: 8, padding: 10 }}>
                      <input value={candidateDraft.phase_name} onChange={(event) => setCandidateDraft({ ...candidateDraft, phase_name: event.target.value })} placeholder="Fase" />
                      <input value={candidateDraft.title} onChange={(event) => setCandidateDraft({ ...candidateDraft, title: event.target.value })} placeholder="Título" />
                      <textarea rows={3} value={candidateDraft.description ?? ""} onChange={(event) => setCandidateDraft({ ...candidateDraft, description: event.target.value || null })} placeholder="Descrição" />
                      <textarea rows={3} value={candidateDraft.definition_of_done ?? ""} onChange={(event) => setCandidateDraft({ ...candidateDraft, definition_of_done: event.target.value || null })} placeholder="Definição de pronto" />
                      <textarea
                        rows={4}
                        value={candidateDraft.subtasks.join("\n")}
                        onChange={(event) => setCandidateDraft({
                          ...candidateDraft,
                          subtasks: event.target.value.split("\n").map((value) => value.trim()).filter(Boolean),
                        })}
                        placeholder="Uma subtarefa por linha"
                      />
                      <label>
                        Prioridade
                        <select value={candidateDraft.priority} onChange={(event) => setCandidateDraft({ ...candidateDraft, priority: event.target.value as ProjectPlanItem["priority"] })}>
                          {Object.entries(PRIORITY_LABEL).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
                        </select>
                      </label>
                      <label>
                        Prazo relativo (dias)
                        <input
                          type="number"
                          min={0}
                          max={730}
                          value={candidateDraft.due_offset_days ?? ""}
                          onChange={(event) => setCandidateDraft({ ...candidateDraft, due_offset_days: event.target.value === "" ? null : Number(event.target.value) })}
                        />
                      </label>
                      <label><input type="checkbox" checked={candidateDraft.client_visible} onChange={(event) => setCandidateDraft({ ...candidateDraft, client_visible: event.target.checked })} /> Visível ao cliente</label>
                      <label><input type="checkbox" checked={candidateDraft.approval_required} onChange={(event) => setCandidateDraft({ ...candidateDraft, approval_required: event.target.checked })} /> Exige aceite</label>
                      <span style={{ display: "flex", gap: 6 }}>
                        <button className="mini-button" type="button" disabled={updateCandidate.isPending} onClick={() => updateCandidate.mutate({ itemId: item.id, payload: candidateDraft })}>
                          <Save size={13} /> Salvar
                        </button>
                        <button className="mini-button" type="button" onClick={() => { setEditingItemId(null); setCandidateDraft(null); }}>Cancelar</button>
                      </span>
                    </div>
                  )}

                  {project.project_type === "tech"
                    && item.github_eligible
                    && item.materialized_deliverable_id
                    && !item.github_issue_url
                    && canManage && (
                      <button
                        className="mini-button"
                        type="button"
                        disabled={createIssue.isPending}
                        onClick={() => {
                          if (!window.confirm(`Criar uma issue real no GitHub para "${item.title}"?`)) return;
                          createIssue.mutate({
                            deliverableId: item.materialized_deliverable_id!,
                            body: [
                              item.description || "Entrega originada do plano aprovado no Bioma.",
                              item.definition_of_done ? `Definição de pronto:\n${item.definition_of_done}` : "",
                              item.subtasks.length ? `Subtarefas:\n${item.subtasks.map((value) => `- ${value}`).join("\n")}` : "",
                              `Plano: ${plan.title} v${plan.version}`,
                              item.approval_required ? "Critério: exige validação/aceite antes de concluir." : "",
                            ].filter(Boolean).join("\n\n"),
                          });
                        }}
                      >
                        <GitBranch size={13} /> Criar issue
                      </button>
                    )}
                </div>
              </details>
            ))}
          </div>

          <footer style={{ display: "flex", gap: 8, marginTop: 12 }}>
            {plan.status === "draft" && canApprove && (
              <button
                className="mini-button"
                type="button"
                disabled={approve.isPending || plan.items.every((item) => !item.selected)}
                onClick={() => {
                  if (window.confirm(`Aprovar o plano v${plan.version}? Ele ficará pronto para aplicação.`)) {
                    approve.mutate(plan.id);
                  }
                }}
              >
                <CheckCircle2 size={13} /> Aprovar {plan.items.filter((item) => item.selected).length} itens
              </button>
            )}
            {plan.status === "approved" && canManage && (
              <button
                className="mini-button"
                type="button"
                disabled={materialize.isPending}
                onClick={() => {
                  if (window.confirm("Criar as fases e entregas deste plano no Hub? A operação é idempotente.")) {
                    materialize.mutate(plan.id);
                  }
                }}
              >
                <ListTree size={13} /> Aplicar ao projeto
              </button>
            )}
          </footer>
        </article>
      ))}
    </section>
  );
}
