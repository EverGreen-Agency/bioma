import { useState, useEffect } from "react";
import { Users, UserCheck, CheckCircle2, Plus, Clock } from "lucide-react";
import {
  api,
  type MilestoneTemplateSummary,
  type OnboardingPlanSummary,
} from "../../../lib/api";

export function RhManager() {
  const [activeTab, setActiveTab] = useState<"onboarding" | "templates">("onboarding");
  const [plans, setPlans] = useState<OnboardingPlanSummary[]>([]);
  const [templates, setTemplates] = useState<MilestoneTemplateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [newTitle, setNewTitle] = useState("");
  const [newDayOffset, setNewDayOffset] = useState(0);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [p, t] = await Promise.all([
        api.listRhOnboardingPlans(),
        api.listRhOnboardingTemplates(),
      ]);
      setPlans(p);
      setTemplates(t);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar dados de RH.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateTemplate(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      await api.createRhOnboardingTemplate({
        title: newTitle,
        day_offset: Number(newDayOffset),
      });
      setNewTitle("");
      setNewDayOffset(0);
      loadData();
    } catch (err: any) {
      alert("Erro ao criar marco: " + err.message);
    }
  }

  async function handleToggleMilestone(planId: string, dayOffset: number, currentStatus: "pending" | "done") {
    const nextStatus = currentStatus === "done" ? "pending" : "done";
    try {
      await api.toggleRhMilestone(planId, dayOffset, nextStatus);
      loadData();
    } catch (err: any) {
      alert("Erro ao atualizar marco: " + err.message);
    }
  }

  return (
    <div style={{ padding: "24px", maxWidth: "1200px", margin: "0 auto", color: "var(--text)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "10px", margin: 0 }}>
            <Users color="var(--brand-accent)" size={28} /> Gestão de RH & Rampagem (MOD-RH-001)
          </h1>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: "0.9rem" }}>
            Acompanhamento de onboarding, rampagem de colaboradores e métricas de satisfação.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "12px", borderBottom: "1px solid var(--border)", marginBottom: "24px" }}>
        <button
          onClick={() => setActiveTab("onboarding")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "onboarding" ? "2px solid var(--brand-accent)" : "2px solid transparent",
            color: activeTab === "onboarding" ? "var(--brand-accent)" : "var(--text-dim)",
            padding: "10px 16px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <UserCheck size={18} /> Planos de Onboarding ({plans.length})
        </button>
        <button
          onClick={() => setActiveTab("templates")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "templates" ? "2px solid var(--brand-accent)" : "2px solid transparent",
            color: activeTab === "templates" ? "var(--brand-accent)" : "var(--text-dim)",
            padding: "10px 16px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <Clock size={18} /> Marcos Padrão ({templates.length})
        </button>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "8px", color: "#ef4444", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-dim)" }}>Carregando dados de RH...</div>
      ) : activeTab === "onboarding" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {plans.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", color: "var(--text-dim)" }}>
              Nenhum plano de onboarding cadastrado no momento.
            </div>
          ) : (
            plans.map((plan) => {
              const doneCount = plan.milestones.filter((m) => m.status === "done").length;
              return (
                <div
                  key={plan.id}
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "12px",
                    padding: "20px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "16px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--glass-border)", paddingBottom: "12px" }}>
                    <div>
                      <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
                        <UserCheck size={20} color="var(--brand-accent)" /> {plan.user_name}
                      </h3>
                      <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
                        {plan.user_email} • Data de Admissão: {plan.hire_date}
                      </span>
                    </div>
                    <span style={{ fontSize: "0.8rem", background: "var(--bg-inset)", color: "var(--brand-accent)", padding: "4px 12px", borderRadius: "16px", fontWeight: 600 }}>
                      {doneCount} / {plan.milestones.length} marcos concluídos
                    </span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "12px" }}>
                    {plan.milestones.map((m) => (
                      <div
                        key={m.day_offset}
                        onClick={() => handleToggleMilestone(plan.id, m.day_offset, m.status)}
                        style={{
                          background: m.status === "done" ? "rgba(16, 185, 129, 0.08)" : "var(--bg-inset)",
                          border: m.status === "done" ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid var(--border)",
                          borderRadius: "8px",
                          padding: "12px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "12px",
                          transition: "all 0.2s ease",
                        }}
                      >
                        <CheckCircle2 size={20} color={m.status === "done" ? "#10b981" : "var(--text-faint)"} />
                        <div>
                          <strong style={{ fontSize: "0.85rem", display: "block", color: m.status === "done" ? "#10b981" : "var(--text)" }}>
                            Dia {m.day_offset}: {m.title}
                          </strong>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                            {m.status === "done" ? "Concluído" : "Pendente"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Formulário Novo Marco */}
          <form
            onSubmit={handleCreateTemplate}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "12px",
              padding: "20px",
              display: "flex",
              gap: "16px",
              alignItems: "flex-end",
            }}
          >
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>Título do Marco de Rampagem</label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="Ex: Treinamento inicial de processos EG"
                style={{ padding: "10px", borderRadius: "8px", background: "var(--bg-inset)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
            </div>
            <div style={{ width: "160px", display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>Dias após Admissão</label>
              <input
                type="number"
                value={newDayOffset}
                onChange={(e) => setNewDayOffset(Number(e.target.value))}
                style={{ padding: "10px", borderRadius: "8px", background: "var(--bg-inset)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
            </div>
            <button className="primary-button" type="submit" style={{ padding: "10px 20px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Plus size={18} /> Adicionar Marco
            </button>
          </form>

          {/* Lista de Marcos Padrão */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "12px" }}>
            {templates.map((tpl) => (
              <div
                key={tpl.id}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                }}
              >
                <Clock size={20} color="var(--brand-accent)" />
                <div>
                  <strong style={{ fontSize: "0.9rem", display: "block" }}>{tpl.title}</strong>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>Executar no Dia {tpl.day_offset}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
