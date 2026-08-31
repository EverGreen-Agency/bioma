import { useState } from "react";
import { Brain, GraduationCap, Lightbulb, ListChecks, Rocket } from "lucide-react";

import { AgentMemoryPanel } from "./AgentMemoryPanel";
import { AgentSkillReviewPanel } from "./AgentSkillReviewPanel";
import { CopilotPlansPanel } from "./CopilotPlansPanel";
import { FeatureFlagsPanel } from "./FeatureFlagsPanel";
import { ImprovementQueuePanel } from "./ImprovementQueuePanel";
import { useAgentSkills, useCopilotPlans, useImprovementRequests } from "../hooks/useBiomaApi";

type Tab = "memoria" | "skills" | "planos" | "melhorias" | "features";

/**
 * Personalização do copiloto num lugar só.
 *
 * Antes, memória, skills, planos e melhorias viviam como painéis empilhados em
 * duas telas diferentes — dava para usar, mas não parecia produto. Aqui vira
 * uma seção com abas, no espírito do que o Eduardo pediu (Habilidades,
 * Conectores, Preferências do Claude).
 *
 * `organizationId` só existe no escopo de cliente; sem ele, a aba de liberação
 * de features não aparece (feature flag é por organização).
 */
export function CopilotWorkbench({
  workspaceId,
  organizationId,
  title,
  description,
}: {
  workspaceId: string | null;
  organizationId?: string;
  title: string;
  description: string;
}) {
  const [tab, setTab] = useState<Tab>("memoria");

  // Contadores no rótulo: o que exige ação fica visível sem abrir a aba.
  const { data: pendingSkills = [] } = useAgentSkills(workspaceId, true, "pending_review");
  const { data: pendingImprovements = [] } = useImprovementRequests("pending", workspaceId);
  const { data: plans = [] } = useCopilotPlans(workspaceId);
  const plansAwaiting = plans.filter((plan) => plan.status === "pending_approval").length;

  const tabs: Array<{ id: Tab; label: string; icon: typeof Brain; badge?: number }> = [
    { id: "memoria", label: "Memória", icon: Brain },
    { id: "skills", label: "Habilidades", icon: GraduationCap, badge: pendingSkills.length },
    { id: "planos", label: "Planos", icon: ListChecks, badge: plansAwaiting },
    { id: "melhorias", label: "Melhorias", icon: Lightbulb, badge: pendingImprovements.length },
    ...(organizationId ? [{ id: "features" as Tab, label: "Liberação", icon: Rocket }] : []),
  ];

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <header>
        <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0, fontSize: "1.15rem" }}>
          <Brain size={20} color="var(--brand-accent)" /> {title}
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: 13, margin: "4px 0 0" }}>{description}</p>
      </header>

      <div className="performance-tabs" role="tablist">
        {tabs.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              className={tab === item.id ? "performance-tab active" : "performance-tab"}
              onClick={() => setTab(item.id)}
            >
              <Icon size={15} /> {item.label}
              {item.badge ? (
                <span
                  style={{
                    marginLeft: 6, fontSize: 10, fontWeight: 700, padding: "1px 6px",
                    borderRadius: 999, background: "#ffab00", color: "#1a1a1a",
                  }}
                >
                  {item.badge}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {tab === "memoria" && (
        <AgentMemoryPanel
          workspaceId={workspaceId}
          title={workspaceId ? "O que o copiloto sabe deste cliente" : "Memória global do copiloto"}
          description={
            workspaceId
              ? "Fatos, preferências e diretivas guardados entre conversas — visível só para o time EG."
              : "Identidade, tom e diretivas que valem em qualquer cliente."
          }
        />
      )}
      {tab === "skills" && <AgentSkillReviewPanel workspaceId={workspaceId} />}
      {tab === "planos" && <CopilotPlansPanel workspaceId={workspaceId} />}
      {tab === "melhorias" && <ImprovementQueuePanel workspaceId={workspaceId} />}
      {tab === "features" && organizationId && <FeatureFlagsPanel organizationId={organizationId} />}
    </section>
  );
}
