import { useState } from "react";
import { CheckCircle2, ListChecks, Play, ShieldAlert, XCircle } from "lucide-react";

import {
  useApproveCopilotPlan,
  useConfirmCopilotPlanStep,
  useCopilotPlans,
  useCreateCopilotPlan,
  useRejectCopilotPlan,
} from "../hooks/useBiomaApi";
import type { CopilotPlan, CopilotPlanStepStatus } from "../lib/api";

const PLAN_STATUS_LABEL: Record<CopilotPlan["status"], string> = {
  pending_approval: "Aguardando sua aprovação",
  approved: "Aprovado (etapas pendentes)",
  running: "Executando",
  completed: "Concluído",
  failed: "Falhou",
  rejected: "Rejeitado",
  cancelled: "Cancelado",
};

const STEP_COLOR: Record<CopilotPlanStepStatus, string> = {
  pending: "var(--text-dim)",
  running: "#4f8ef7",
  executed: "#2e9e5b",
  failed: "#ff5252",
  skipped: "var(--text-faint)",
  blocked: "#ffab00",
};

const STEP_LABEL: Record<CopilotPlanStepStatus, string> = {
  pending: "pendente",
  running: "executando",
  executed: "feito",
  failed: "falhou",
  skipped: "pulada",
  blocked: "precisa de confirmação",
};

/**
 * Planos multi-etapa: você descreve o objetivo, o copiloto monta a sequência,
 * e NADA roda antes de você aprovar. Etapa visível ao cliente continua exigindo
 * confirmação própria mesmo depois do plano aprovado.
 */
export function CopilotPlansPanel({ workspaceId }: { workspaceId: string | null }) {
  const { data: plans = [], isLoading } = useCopilotPlans(workspaceId);
  const createPlan = useCreateCopilotPlan();
  const approvePlan = useApproveCopilotPlan();
  const rejectPlan = useRejectCopilotPlan();
  const confirmStep = useConfirmCopilotPlanStep();

  const [goal, setGoal] = useState("");

  function handleCreate() {
    if (goal.trim().length < 2) return;
    createPlan.mutate({ goal: goal.trim(), workspace_id: workspaceId }, { onSuccess: () => setGoal("") });
  }

  return (
    <article className="surface">
      <div className="surface-header">
        <ListChecks size={18} />
        <h3>Planos do copiloto</h3>
      </div>
      <div style={{ padding: "0 20px 20px" }}>
        <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 14 }}>
          Descreva o objetivo; o copiloto monta a sequência de etapas. <strong>Nada executa antes
          da sua aprovação</strong> — e o que é visível ao cliente pede confirmação própria.
        </p>

        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <input
            style={{ flex: 1 }}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Ex: cadastrar cliente novo e montar a estrutura inicial"
            onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
          />
          <button type="button" className="primary" disabled={createPlan.isPending || goal.trim().length < 2} onClick={handleCreate}>
            <Play size={14} /> {createPlan.isPending ? "Montando..." : "Montar plano"}
          </button>
        </div>

        {createPlan.isError && (
          <div className="notice error">
            {createPlan.error instanceof Error ? createPlan.error.message : "Falha ao montar o plano."}
          </div>
        )}

        {isLoading && <p style={{ color: "var(--text-muted)" }}>Carregando planos...</p>}
        {!isLoading && plans.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--text-dim)" }}>Nenhum plano ainda.</p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {plans.map((plan) => (
            <div key={plan.id} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "12px 14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <strong style={{ flex: 1 }}>{plan.goal}</strong>
                <span style={{ fontSize: 11, fontWeight: 600, color: plan.status === "failed" ? "#ff5252" : plan.status === "completed" ? "#2e9e5b" : "#ffab00" }}>
                  {PLAN_STATUS_LABEL[plan.status]}
                </span>
                {plan.generation_mode === "preview" && (
                  <span className="demo-badge">prévia local</span>
                )}
              </div>

              {plan.summary && <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "6px 0" }}>{plan.summary}</p>}

              {plan.requires_confirmation_count > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#ffab00", margin: "4px 0" }}>
                  <ShieldAlert size={12} />
                  {plan.requires_confirmation_count} etapa(s) visível(is) ao cliente — confirmação individual
                </div>
              )}

              <ol style={{ margin: "8px 0", paddingLeft: 20, fontSize: 13 }}>
                {plan.steps.map((step) => (
                  <li key={step.id} style={{ marginBottom: 4 }}>
                    <span>{step.label}</span>{" "}
                    <span style={{ fontSize: 10, fontWeight: 600, color: STEP_COLOR[step.status] }}>
                      {STEP_LABEL[step.status]}
                    </span>
                    {step.detail && (
                      <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{step.detail}</div>
                    )}
                    {step.undo_hint && (
                      <div style={{ fontSize: 10, color: "var(--text-faint)" }}>Desfazer: {step.undo_hint}</div>
                    )}
                    {step.status === "blocked" && (plan.status === "approved" || plan.status === "running") && (
                      <button
                        type="button"
                        className="mini-button"
                        disabled={confirmStep.isPending}
                        onClick={() => confirmStep.mutate({ planId: plan.id, stepId: step.id })}
                        style={{ marginTop: 4 }}
                      >
                        Confirmar e executar
                      </button>
                    )}
                  </li>
                ))}
              </ol>

              {plan.open_questions.length > 0 && (
                <div style={{ fontSize: 12, color: "#ffab00", marginBottom: 6 }}>
                  <strong>Perguntas em aberto:</strong>
                  <ul style={{ margin: "2px 0", paddingLeft: 18 }}>
                    {plan.open_questions.map((question, index) => <li key={index}>{question}</li>)}
                  </ul>
                </div>
              )}

              {plan.status === "pending_approval" && (
                <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                  <button type="button" className="primary" disabled={approvePlan.isPending} onClick={() => approvePlan.mutate(plan.id)}>
                    <CheckCircle2 size={13} /> Aprovar e executar
                  </button>
                  <button type="button" disabled={rejectPlan.isPending} onClick={() => rejectPlan.mutate(plan.id)}>
                    <XCircle size={13} /> Rejeitar
                  </button>
                </div>
              )}

              {plan.error_message && <div className="notice error" style={{ marginTop: 6 }}>{plan.error_message}</div>}
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}
