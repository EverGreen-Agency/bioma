import React, { useState } from "react";
import {
  api,
  CommercialPilar,
  CommercialPortalResponse,
  CommercialPlanStatus,
  DiagnosticAnswerSummary,
} from "../lib/api";

interface RaioXScorePanelProps {
  workspaceId: string;
  data: CommercialPortalResponse | null;
  onUpdate: () => void;
  canEdit?: boolean;
}

const MATURITY_LABELS: Record<string, { label: string; icon: string; desc: string; color: string }> = {
  semente: { label: "Semente", icon: "🌱", desc: "Fase inicial — diagnóstico e primeiros fundamentos em construção", color: "var(--amber, #F59E0B)" },
  muda: { label: "Muda", icon: "🌿", desc: "Estrutura comercial em consolidação com primeiras vitórias", color: "var(--mint, #3AC97B)" },
  arvore: { label: "Árvore", icon: "🌳", desc: "Operação estruturada com previsibilidade e cadência constante", color: "var(--mint-deep, #10B981)" },
  floresta: { label: "Floresta", icon: "🌲", desc: "Parceria madura em alta escala, composição contínua e expansão", color: "var(--mint, #34D399)" },
};

const PILAR_QUESTIONS: Record<CommercialPilar, Record<number, Array<{ key: string; label: string; desc: string }>>> = {
  oferta: {
    1: [
      { key: "proposta_padronizada", label: "Proposta Padronizada", desc: "A proposta comercial tem modelo único, claro e sem improvisos?" },
      { key: "icp_definido", label: "Definição de ICP", desc: "O Perfil de Cliente Ideal está claramente documentado?" },
      { key: "precificacao_margem", label: "Precificação & Margem", desc: "O preço e as margens de lucro estão validados?" },
    ],
    2: [
      { key: "oferta_high_ticket", label: "Oferta High-Ticket / Recorrência", desc: "Existe esteira de produtos com produtos de maior valor ou SaaS?" },
      { key: "teste_ab_proposta", label: "Testes A/B de Copy & Proposta", desc: "A proposta é testada e otimizada continuamente com base em conversão?" },
    ],
  },
  demanda: {
    1: [
      { key: "canais_medidos", label: "Canais de Aquisição Medidos", desc: "Origem dos leads e canais de tráfego possuem rastreamento?" },
      { key: "volume_minimo_leads", label: "Volume Mínimo de Oportunidades", desc: "A empresa gera fluxo constante de novas oportunidades por mês?" },
    ],
    2: [
      { key: "atribuicao_multitoque", label: "Atribuição & BI Integrado", desc: "O custo por aquisição (CAC/CPL) é medido em tempo real via dashboard?" },
      { key: "origem_diversificada", label: "Aquisição Multicanal (Inbound/Outbound)", desc: "A demanda vem de mais de um canal independente (ex: Google, Meta, LinkedIn)?" },
    ],
  },
  conversao: {
    1: [
      { key: "crm_cadencia", label: "CRM & Cadência de Follow-up", desc: "Todos os leads passam por etapas claras de pipeline com follow-up?" },
      { key: "scripts_vendas", label: "Scripts & Treinamento Comercial", desc: "O time de vendas segue scripts e roteiros padronizados?" },
    ],
    2: [
      { key: "automacao_followup", label: "Automação Preditiva no CRM", desc: "Existem automações de e-mail/WhatsApp para resgatar leads estagnados?" },
      { key: "sla_atendimento", label: "SLA Comercial & Tempo de Resposta", desc: "Leads novos são atendidos em tempo recorde (< 15 minutos)?" },
    ],
  },
};

export const RaioXScorePanel: React.FC<RaioXScorePanelProps> = ({
  workspaceId,
  data,
  onUpdate,
  canEdit = true,
}) => {
  const [activeModalPilar, setActiveModalPilar] = useState<CommercialPilar | null>(null);
  const [showSprintModal, setShowSprintModal] = useState(false);
  const [sprintTitle, setSprintTitle] = useState("");
  const [sprintGoals, setSprintGoals] = useState("");
  const [saving, setSaving] = useState(false);

  if (!data) {
    return <div style={{ padding: "1rem", opacity: 0.7 }}>Carregando Raio-X Comercial...</div>;
  }

  const { scores, answers, action_plans } = data;
  const maturity = MATURITY_LABELS[scores.maturity_level] || MATURITY_LABELS.semente;

  const getAnswerValue = (pilar: CommercialPilar, reguaLevel: number, questionKey: string): number => {
    const found = answers.find(
      (a: DiagnosticAnswerSummary) => a.pilar === pilar && a.regua_level === reguaLevel && a.question_key === questionKey
    );
    return found ? found.score_value : 0;
  };

  const handleSaveQuestion = async (pilar: CommercialPilar, reguaLevel: 1 | 2, questionKey: string, val: number) => {
    setSaving(true);
    try {
      await api.answerDiagnosticQuestion(workspaceId, {
        pilar,
        regua_level: reguaLevel,
        question_key: questionKey,
        score_value: val,
      });
      onUpdate();
    } catch (err) {
      alert("Erro ao salvar nota do diagnóstico: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setSaving(false);
    }
  };

  const handleCreateSprint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sprintTitle.trim() || !sprintGoals.trim()) return;
    setSaving(true);
    try {
      await api.createActionPlan(workspaceId, {
        pilar_gargalo: scores.gargalo_prioritario,
        sprint_title: sprintTitle,
        sprint_goals: sprintGoals,
      });
      setSprintTitle("");
      setSprintGoals("");
      setShowSprintModal(false);
      onUpdate();
    } catch (err) {
      alert("Erro ao criar sprint: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setSaving(false);
    }
  };

  const handleToggleSprintStatus = async (planId: string, currentStatus: CommercialPlanStatus) => {
    const nextStatus: CommercialPlanStatus =
      currentStatus === "em_andamento" ? "concluido" : currentStatus === "concluido" ? "pausado" : "em_andamento";
    try {
      await api.updateActionPlanStatus(workspaceId, planId, nextStatus);
      onUpdate();
    } catch (err) {
      alert("Erro ao atualizar status: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const pilaresConfig: Array<{ key: CommercialPilar; title: string; score: number; level: number }> = [
    { key: "oferta", title: "Oferta", score: scores.oferta_score, level: scores.oferta_level },
    { key: "demanda", title: "Demanda", score: scores.demanda_score, level: scores.demanda_level },
    { key: "conversao", title: "Conversão", score: scores.conversao_score, level: scores.conversao_level },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header de Maturidade e Sistema Raiz */}
      <div
        style={{
          background: "var(--surface, rgba(9, 35, 27, 0.6))",
          border: "1px solid var(--border, rgba(255, 255, 255, 0.1))",
          borderRadius: "12px",
          padding: "1.25rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <div style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "1px", opacity: 0.7, marginBottom: "0.25rem" }}>
            Raio-X Comercial — Sistema Raiz EG
          </div>
          <h3 style={{ margin: 0, fontSize: "1.35rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span>{maturity.icon}</span> Nível de Maturidade: <span style={{ color: maturity.color }}>{maturity.label}</span>
          </h3>
          <p style={{ margin: "0.35rem 0 0 0", fontSize: "0.88rem", opacity: 0.85 }}>{maturity.desc}</p>
        </div>
        <div
          style={{
            background: "rgba(245, 158, 11, 0.15)",
            border: "1px solid rgba(245, 158, 11, 0.4)",
            borderRadius: "8px",
            padding: "0.6rem 1rem",
            textAlign: "right",
          }}
        >
          <div style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "var(--amber, #FBBF24)", fontWeight: 600 }}>
            ⚡ Gargalo Prioritário (Plano 90 Dias)
          </div>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, textTransform: "capitalize", color: "#FFF" }}>
            Pilar: {scores.gargalo_prioritario}
          </div>
        </div>
      </div>

      {/* Grid dos 3 Pilares (Oferta, Demanda, Conversao) */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem" }}>
        {pilaresConfig.map((p) => {
          const isGargalo = scores.gargalo_prioritario === p.key;
          const percentage = Math.min(100, Math.max(0, (p.score / 10) * 100));

          return (
            <div
              key={p.key}
              style={{
                background: isGargalo
                  ? "linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(9, 35, 27, 0.8) 100%)"
                  : "var(--surface, rgba(9, 35, 27, 0.5))",
                border: isGargalo
                  ? "1px solid rgba(245, 158, 11, 0.5)"
                  : "1px solid var(--border, rgba(255, 255, 255, 0.08))",
                borderRadius: "12px",
                padding: "1.25rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.85rem",
                position: "relative",
              }}
            >
              {isGargalo && (
                <span
                  style={{
                    position: "absolute",
                    top: "-10px",
                    right: "12px",
                    background: "var(--amber, #F59E0B)",
                    color: "#000",
                    fontSize: "0.7rem",
                    fontWeight: 800,
                    padding: "2px 8px",
                    borderRadius: "4px",
                    textTransform: "uppercase",
                  }}
                >
                  Gargalo
                </span>
              )}

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 style={{ margin: 0, fontSize: "1.15rem", fontWeight: 700 }}>{p.title}</h4>
                <span style={{ fontSize: "0.75rem", background: "rgba(255,255,255,0.08)", padding: "2px 8px", borderRadius: "4px" }}>
                  Régua Nível {p.level}
                </span>
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.35rem", fontSize: "0.9rem" }}>
                  <span style={{ opacity: 0.8 }}>Nota Atual</span>
                  <span style={{ fontWeight: 700, color: p.score >= 5 ? "var(--mint, #3AC97B)" : "var(--amber, #FBBF24)" }}>
                    {p.score.toFixed(1)} / 10
                  </span>
                </div>
                <div style={{ background: "rgba(255,255,255,0.1)", borderRadius: "6px", height: "8px", overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${percentage}%`,
                      height: "100%",
                      background: p.score >= 5 ? "var(--mint, #3AC97B)" : "var(--amber, #F59E0B)",
                      transition: "width 0.3s ease",
                    }}
                  />
                </div>
              </div>

              {canEdit && (
                <button
                  type="button"
                  onClick={() => setActiveModalPilar(p.key)}
                  style={{
                    marginTop: "auto",
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: "6px",
                    color: "#FFF",
                    padding: "0.5rem",
                    cursor: "pointer",
                    fontSize: "0.85rem",
                    fontWeight: 600,
                  }}
                >
                  📝 Avaliar Pilar {p.title}
                </button>
              )}
            </div>
          );
        })}
      </div>



      {/* Modal para Avaliação do Pilar */}
      {activeModalPilar && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem",
          }}
        >
          <div
            style={{
              background: "#0E2F24",
              border: "1px solid var(--border, rgba(255, 255, 255, 0.2))",
              borderRadius: "12px",
              padding: "1.5rem",
              maxWidth: "600px",
              width: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ margin: 0, textTransform: "capitalize" }}>Diagnóstico — Pilar {activeModalPilar}</h3>
              <button
                type="button"
                onClick={() => setActiveModalPilar(null)}
                style={{ background: "none", border: "none", color: "#FFF", fontSize: "1.2rem", cursor: "pointer" }}
              >
                ✕
              </button>
            </div>

            {[1, 2].map((level) => {
              const questions = PILAR_QUESTIONS[activeModalPilar]?.[level] || [];
              if (questions.length === 0) return null;

              return (
                <div key={level} style={{ marginBottom: "1.25rem" }}>
                  <h5 style={{ margin: "0 0 0.5rem 0", color: "var(--mint, #3AC97B)", fontSize: "0.95rem" }}>
                    Régua Nível {level} {level === 1 ? "(Fundação)" : "(Escala & Automação)"}
                  </h5>

                  <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    {questions.map((q) => {
                      const val = getAnswerValue(activeModalPilar, level, q.key);

                      return (
                        <div
                          key={q.key}
                          style={{
                            background: "rgba(255,255,255,0.03)",
                            border: "1px solid rgba(255,255,255,0.08)",
                            borderRadius: "6px",
                            padding: "0.75rem",
                          }}
                        >
                          <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{q.label}</div>
                          <div style={{ fontSize: "0.8rem", opacity: 0.7, marginBottom: "0.5rem" }}>{q.desc}</div>

                          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                            <input
                              type="range"
                              min="0"
                              max="10"
                              step="0.5"
                              value={val}
                              disabled={saving}
                              onChange={(e) =>
                                handleSaveQuestion(activeModalPilar, level as 1 | 2, q.key, parseFloat(e.target.value))
                              }
                              style={{ flex: 1, accentColor: "var(--mint, #3AC97B)" }}
                            />
                            <span style={{ fontWeight: 700, width: "45px", textAlign: "right" }}>{val.toFixed(1)}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}

            <button
              type="button"
              onClick={() => setActiveModalPilar(null)}
              style={{
                width: "100%",
                background: "rgba(255,255,255,0.1)",
                color: "#FFF",
                border: "none",
                borderRadius: "6px",
                padding: "0.6rem",
                marginTop: "1rem",
                cursor: "pointer",
              }}
            >
              Concluir Avaliação
            </button>
          </div>
        </div>
      )}

      {/* Modal para Criar Novo Sprint */}
      {showSprintModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem",
          }}
        >
          <form
            onSubmit={handleCreateSprint}
            style={{
              background: "#0E2F24",
              border: "1px solid var(--border, rgba(255, 255, 255, 0.2))",
              borderRadius: "12px",
              padding: "1.5rem",
              maxWidth: "500px",
              width: "100%",
            }}
          >
            <h3 style={{ margin: "0 0 1rem 0" }}>Adicionar Sprint (Plano de 90 Dias)</h3>

            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.35rem" }}>
                Título do Sprint (Pilar Gargalo: {scores.gargalo_prioritario})
              </label>
              <input
                type="text"
                required
                value={sprintTitle}
                onChange={(e) => setSprintTitle(e.target.value)}
                placeholder="Ex: Sprint 1 — Estruturação de Proposta e Tabela de Preços"
                style={{
                  width: "100%",
                  padding: "0.5rem",
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "6px",
                  color: "#FFF",
                }}
              />
            </div>

            <div style={{ marginBottom: "1.25rem" }}>
              <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.35rem" }}>Metas & KPIs do Sprint</label>
              <textarea
                required
                rows={3}
                value={sprintGoals}
                onChange={(e) => setSprintGoals(e.target.value)}
                placeholder="Descreva as metas claras e entregáveis de transformação..."
                style={{
                  width: "100%",
                  padding: "0.5rem",
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "6px",
                  color: "#FFF",
                }}
              />
            </div>

            <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
              <button
                type="button"
                onClick={() => setShowSprintModal(false)}
                style={{ background: "none", border: "1px solid rgba(255,255,255,0.2)", color: "#FFF", borderRadius: "6px", padding: "0.5rem 1rem" }}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                style={{ background: "var(--mint, #3AC97B)", border: "none", color: "#09231B", fontWeight: 700, borderRadius: "6px", padding: "0.5rem 1rem" }}
              >
                {saving ? "Salvando..." : "Criar Sprint"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
