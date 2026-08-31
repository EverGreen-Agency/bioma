import { useState } from "react";
import { Check, ChevronLeft, ChevronRight, Plus, Sparkles, X, LayoutDashboard, FolderOpen, Users, BarChart3, Link2, KeyRound, Rocket } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { moduleLabels, statusLabel, toggleableModules } from "../lib/app-config";
import { useCreateClient, useCreateDeliverable, useUpdateClient } from "../hooks/useBiomaApi";
import { api, type ClientModule, type ClientProfilePayload, type ClientStatus, type ProjectType } from "../lib/api";

// Módulos essenciais do núcleo (o hub é obrigatório e sempre ativo)
const BASE_MODULES: ClientModule[] = ["hub"];

// Entregas de arranque do kickoff
const ONBOARDING_TEMPLATE = [
  "Reunião de kickoff",
  "Coletar acessos e credenciais",
  "Briefing e diagnóstico inicial",
  "Definir cronograma e escopo",
];

const MODULE_DESCRIPTIONS: Record<ClientModule, string> = {
  hub: "Visão geral, projetos e acompanhamento do cliente",
  content: "Estúdio IA para geração de posts e roteiros",
  files: "Depósito de documentos e arquivos compartilhados",
  commercial: "CRM comercial de vendas",
  finance: "Painel financeiro e faturamento",
  analytics: "Métricas de mídia (Google, Meta, GA4)",
  integrations: "Conexão com ferramentas externas",
  engineering: "Documentação técnica",
};

const STEPS = ["Identidade", "Módulos", "Entregas Iniciais"] as const;
const PROJECT_TRACKS: Array<{ type: Exclude<ProjectType, "general">; label: string; description: string }> = [
  { type: "tech", label: "Tech", description: "Roadmap técnico e candidatos a issues GitHub com HITL" },
  { type: "growth", label: "Growth", description: "Campanhas, CRM, rotinas e ciclos de otimização" },
  { type: "social", label: "Social Media", description: "Planejamento editorial e aprovação adaptativa" },
];

export function NewClientWizard({
  onClose,
  onCreated,
  navigateOnCreate = true,
}: {
  onClose: () => void;
  onCreated?: (clientId: string) => void;
  navigateOnCreate?: boolean;
}) {
  const navigate = useNavigate();
  const createClient = useCreateClient();
  const updateClient = useUpdateClient();
  const createDeliverable = useCreateDeliverable();

  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState("");
  const [organization, setOrganization] = useState("");
  const [responsible, setResponsible] = useState("Eduardo EG");
  const [status, setStatus] = useState<ClientStatus>("onboarding");
  const [website, setWebsite] = useState("");
  const [sector, setSector] = useState("");
  const [primaryOffer, setPrimaryOffer] = useState("");
  const [initialObjective, setInitialObjective] = useState("");
  const [useAiSetup, setUseAiSetup] = useState(true);
  
  // Por padrão ativamos os módulos recomendados para o novo cliente
  const [modules, setModules] = useState<Set<ClientModule>>(new Set(["content", "files", "commercial", "analytics"]));
  const [onboarding, setOnboarding] = useState<Set<string>>(new Set(ONBOARDING_TEMPLATE));
  const [projectTracks, setProjectTracks] = useState<Set<Exclude<ProjectType, "general">>>(new Set());

  const busy = submitting || createClient.isPending || updateClient.isPending;
  const identityValid = name.trim().length > 0 && organization.trim().length > 0;

  const toggleModule = (module: ClientModule) => {
    setModules((prev) => {
      const next = new Set(prev);
      next.has(module) ? next.delete(module) : next.add(module);
      return next;
    });
  };

  const toggleOnboarding = (title: string) => {
    setOnboarding((prev) => {
      const next = new Set(prev);
      next.has(title) ? next.delete(title) : next.add(title);
      return next;
    });
  };

  const toggleProjectTrack = (track: Exclude<ProjectType, "general">) => {
    setProjectTracks((prev) => {
      const next = new Set(prev);
      next.has(track) ? next.delete(track) : next.add(track);
      return next;
    });
  };

  const goNext = () => {
    if (step === 0 && !identityValid) return;
    setError("");
    setStep((s) => s + 1);
  };

  const goBack = () => {
    setError("");
    setStep((s) => s - 1);
  };

  const handleCreate = async () => {
    setError("");
    setSubmitting(true);
    try {
      // 1. Criar o cliente no banco
      const res = await createClient.mutateAsync({
        name: name.trim(),
        organization_name: organization.trim(),
        responsible_name: responsible || "Eduardo EG",
        status,
      });

      const clientId = res.client.id;
      const initialContext: ClientProfilePayload = {
        sector: sector.trim() || null,
        primary_offer: primaryOffer.trim() || null,
        initial_objective: initialObjective.trim() || null,
        website: website.trim() || null,
      };
      if (Object.values(initialContext).some(Boolean)) {
        await api.updateClientProfile(clientId, initialContext);
      }

      // 2. Atualizar os módulos ativos do cliente
      const allModules = Array.from(new Set<ClientModule>(["hub", ...Array.from(modules)]));
      await updateClient.mutateAsync({
        id: clientId,
        payload: { enabled_modules: allModules },
      });

      // 3. Executar o onboarding assistido e incorporar as entregas sugeridas.
      const deliverableTitles = new Set(onboarding);
      if (useAiSetup) {
        try {
          const execution = await api.runSquad(clientId, {
            pilar: "onboarding",
            squad_slug: "client-onboarding",
            squad_name: "Onboarding & Setup do Cliente",
            input_data: {
              company_name: organization.trim(),
              client_name: name.trim(),
              website: website.trim() || null,
              client_context: initialContext,
              enabled_modules: allModules,
            },
          });
          const suggested = execution.output_data.initial_deliverables;
          if (Array.isArray(suggested)) {
            suggested
              .filter((title): title is string => typeof title === "string" && title.trim().length > 1)
              .forEach((title) => deliverableTitles.add(title.trim()));
          }
        } catch (squadError) {
          const message = squadError instanceof Error ? squadError.message : "falha desconhecida";
          window.alert(`Cliente criado, mas o onboarding assistido não foi executado: ${message}`);
        }
      }

      // 4. Criar entregáveis de kickoff selecionados/sugeridos
      const deliverablePromises = Array.from(deliverableTitles).map((title) =>
        createDeliverable.mutateAsync({
          clientId,
          payload: {
            title,
            status: "planned",
          },
        })
      );
      await Promise.all(deliverablePromises);

      // 5. Criar frentes operacionais e seus planos em rascunho.
      const planningResults = await Promise.allSettled(
        Array.from(projectTracks).map(async (projectType) => {
          const label = PROJECT_TRACKS.find((track) => track.type === projectType)?.label ?? projectType;
          const project = await api.createProject(clientId, {
            name: `${organization.trim()} — ${label}`,
            project_type: projectType,
            status: "planned",
            client_visible: true,
            objective: `Estruturar e acompanhar a frente de ${label} contratada pelo cliente.`,
          });
          if (useAiSetup) {
            await api.generateProjectPlan(project.id, {
              source_kind: "onboarding",
              objective: project.objective,
              social_approval_flow: "adaptive",
            });
          }
        }),
      );
      const failedPlans = planningResults.filter((result) => result.status === "rejected").length;
      if (failedPlans) {
        window.alert(`Cliente criado. ${failedPlans} frente(s) operacional(is) não puderam ser planejadas e podem ser retomadas em Projetos.`);
      }

      onCreated?.(clientId);
      onClose();
      if (navigateOnCreate) {
        navigate(`/clientes/${clientId}`);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro ao criar cliente. Tente novamente.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card wide" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "560px" }}>
        <div className="modal-header">
          <div className="modal-title-group">
            <Sparkles size={18} className="modal-icon" color="var(--brand-accent)" />
            <h2>Novo cliente</h2>
          </div>
          <button className="icon-button" onClick={onClose} type="button" aria-label="Fechar">
            <X size={16} />
          </button>
        </div>

        {/* Stepper */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--border)", padding: "12px 20px" }}>
          {STEPS.map((label, index) => (
            <div
              key={label}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: "0.82rem",
                fontWeight: index === step ? 700 : 500,
                color: index === step ? "var(--brand-accent)" : index < step ? "#10b981" : "var(--text-dim)",
              }}
            >
              <span
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  display: "grid",
                  placeItems: "center",
                  fontSize: "0.75rem",
                  background: index < step ? "#10b981" : index === step ? "var(--brand-accent)" : "var(--bg-inset)",
                  color: index <= step ? "#000" : "var(--text-dim)",
                  fontWeight: 700,
                }}
              >
                {index < step ? <Check size={13} color="#000" /> : index + 1}
              </span>
              {label}
            </div>
          ))}
        </div>

        <div className="modal-body" style={{ padding: "20px" }}>
          {/* ETAPA 1: IDENTIDADE */}
          {step === 0 && (
            <div className="form-grid two" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.85rem" }}>
                Nome do Cliente / Empresa *
                <input value={name} autoFocus onChange={(e) => setName(e.target.value)} placeholder="Ex: HM Conexões" style={{ padding: "10px", borderRadius: "6px" }} />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.85rem" }}>
                Razão Social / Marca *
                <input value={organization} onChange={(e) => setOrganization(e.target.value)} placeholder="Ex: HM Conexões Ltda" style={{ padding: "10px", borderRadius: "6px" }} />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.85rem" }}>
                Website / URL da Empresa (opcional para Varredura IA)
                <input value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="Ex: https://hmconexoes.com.br" style={{ padding: "10px", borderRadius: "6px" }} />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.85rem" }}>
                Setor de atuação
                <input value={sector} onChange={(e) => setSector(e.target.value)} placeholder="Ex.: saúde, energia, varejo B2B" style={{ padding: "10px", borderRadius: "6px" }} />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.85rem" }}>
                Produto/serviço principal
                <input value={primaryOffer} onChange={(e) => setPrimaryOffer(e.target.value)} placeholder="Ex.: consultoria, aplicativo, clínica" style={{ padding: "10px", borderRadius: "6px" }} />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.85rem" }}>
                Objetivo inicial
                <textarea value={initialObjective} onChange={(e) => setInitialObjective(e.target.value)} placeholder="O que o cliente precisa alcançar agora?" rows={3} style={{ padding: "10px", borderRadius: "6px" }} />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.85rem" }}>
                Responsável EG
                <select value={responsible} onChange={(e) => setResponsible(e.target.value)} style={{ padding: "10px", borderRadius: "6px" }}>
                  <option value="Eduardo EG">Eduardo EG (eduardo@evergreengrowth.com.br)</option>
                </select>
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.85rem" }}>
                Status Inicial
                <select value={status} onChange={(e) => setStatus(e.target.value as ClientStatus)} style={{ padding: "10px", borderRadius: "6px" }}>
                  {(["onboarding", "active", "completed", "paused", "archived"] as ClientStatus[]).map((value) => (
                    <option key={value} value={value}>{statusLabel[value]}</option>
                  ))}
                </select>
              </label>

              {/* Toca do Squad de Onboarding Inteligente */}
              <button
                type="button"
                onClick={() => setUseAiSetup(!useAiSetup)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 14px",
                  background: useAiSetup ? "rgba(58, 201, 123, 0.12)" : "var(--bg-inset)",
                  border: `1px solid ${useAiSetup ? "var(--brand-accent)" : "var(--border)"}`,
                  borderRadius: "8px",
                  cursor: "pointer",
                  marginTop: "6px",
                  textAlign: "left",
                }}
              >
                <div>
                  <strong style={{ fontSize: "0.88rem", color: useAiSetup ? "var(--brand-accent)" : "var(--text)", display: "flex", alignItems: "center", gap: 6 }}>
                    🤖 Disparar Squad IA de Onboarding & Setup
                  </strong>
                  <span style={{ fontSize: "0.78rem", color: "var(--text-dim)", display: "block", marginTop: 2 }}>
                    Gera um diagnóstico assistido e incorpora sugestões de kickoff ao Hub. Sem chave de IA, a execução fica identificada como prévia local.
                  </span>
                </div>
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: 6,
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                    background: useAiSetup ? "var(--brand-accent)" : "transparent",
                    border: `1px solid ${useAiSetup ? "var(--brand-accent)" : "var(--border)"}`,
                    color: "#000",
                    fontWeight: 700,
                  }}
                >
                  {useAiSetup && <Check size={14} color="#000" />}
                </span>
              </button>
            </div>
          )}

          {/* ETAPA 2: MÓDULOS (UNIFORMIZADO E SEM DUPLICAÇÃO) */}
          {step === 1 && (
            <div>
              <p style={{ color: "var(--text-dim)", marginTop: 0, marginBottom: 14, fontSize: "0.86rem" }}>
                Selecione os módulos que serão exibidos no Hub do cliente:
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: "310px", overflowY: "auto", paddingRight: "4px" }}>
                {/* Módulo Base (Hub) */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 16px",
                    background: "var(--bg-inset)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                  }}
                >
                  <div>
                    <strong style={{ fontSize: "0.9rem", color: "var(--text)", display: "block" }}>
                      {moduleLabels["hub"]}
                    </strong>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                      {MODULE_DESCRIPTIONS["hub"]}
                    </span>
                  </div>
                  <span style={{ fontSize: "0.72rem", background: "rgba(16, 185, 129, 0.15)", color: "#10b981", padding: "4px 8px", borderRadius: "4px", fontWeight: 700 }}>
                    SEMPRE ATIVO
                  </span>
                </div>

                {/* Módulos Selecionáveis */}
                {toggleableModules.map((module) => {
                  const on = modules.has(module);
                  return (
                    <button
                      key={module}
                      type="button"
                      onClick={() => toggleModule(module)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "12px 16px",
                        background: on ? "var(--surface)" : "var(--bg-inset)",
                        border: `1px solid ${on ? "var(--brand-accent)" : "var(--border)"}`,
                        borderRadius: "8px",
                        cursor: "pointer",
                        textAlign: "left",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <div>
                        <strong style={{ fontSize: "0.9rem", color: "var(--text)", display: "block" }}>
                          {moduleLabels[module]}
                        </strong>
                        <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                          {MODULE_DESCRIPTIONS[module]}
                        </span>
                      </div>
                      <span
                        style={{
                          width: 22,
                          height: 22,
                          borderRadius: 6,
                          display: "grid",
                          placeItems: "center",
                          background: on ? "var(--brand-accent)" : "transparent",
                          border: `1px solid ${on ? "var(--brand-accent)" : "var(--border)"}`,
                          color: "#000",
                          fontWeight: 700,
                        }}
                      >
                        {on && <Check size={14} color="#000" />}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* ETAPA 3: ENTREGAS INICIAIS ADAPTATIVAS */}
          {step === 2 && (
            <div>
              <div style={{ background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.25)", borderRadius: "8px", padding: "12px 14px", marginBottom: "16px" }}>
                <strong style={{ fontSize: "0.88rem", color: "#10b981", display: "flex", alignItems: "center", gap: "6px" }}>
                  <Rocket size={16} /> Entregas & Marcos de Arranque ({statusLabel[status]})
                </strong>
                <p style={{ margin: "4px 0 0", color: "var(--text)", fontSize: "0.82rem", lineHeight: 1.4 }}>
                  {status === "onboarding"
                    ? "Mesmo com o cliente em onboarding, o sistema já gera estas entregas essenciais no Hub para alinhar o atendimento inicial."
                    : status === "active"
                    ? "Para clientes ativos/em recorrência, você pode selecionar quais entregas operacionais já devem iniciar criadas no Hub do cliente."
                    : status === "completed"
                    ? "Para clientes de sprints/projetos concluídos, selecione as entregas finalizadas para manter o histórico estruturado no Hub."
                    : "Entregas base selecionadas para documentar o histórico do cliente no Hub."}
                </p>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-dim)", fontWeight: 600 }}>
                  Entregas sugeridas ({onboarding.size}/{ONBOARDING_TEMPLATE.length}):
                </span>
                <button
                  type="button"
                  onClick={() => {
                    if (onboarding.size === ONBOARDING_TEMPLATE.length) {
                      setOnboarding(new Set());
                    } else {
                      setOnboarding(new Set(ONBOARDING_TEMPLATE));
                    }
                  }}
                  style={{ background: "none", border: "none", color: "var(--brand-accent)", fontSize: "0.78rem", cursor: "pointer", fontWeight: 600 }}
                >
                  {onboarding.size === ONBOARDING_TEMPLATE.length ? "Desmarcar Todas" : "Selecionar Todas"}
                </button>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 18 }}>
                {ONBOARDING_TEMPLATE.map((title) => {
                  const on = onboarding.has(title);
                  return (
                    <button
                      key={title}
                      type="button"
                      onClick={() => toggleOnboarding(title)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "12px 14px",
                        background: on ? "var(--surface)" : "var(--bg-inset)",
                        border: `1px solid ${on ? "var(--brand-accent)" : "var(--border)"}`,
                        borderRadius: "8px",
                        cursor: "pointer",
                        textAlign: "left",
                        color: "var(--text)",
                        fontSize: "0.88rem",
                      }}
                    >
                      <span
                        style={{
                          width: 20,
                          height: 20,
                          borderRadius: 6,
                          display: "grid",
                          placeItems: "center",
                          flexShrink: 0,
                          background: on ? "var(--brand-accent)" : "transparent",
                          border: `1px solid ${on ? "var(--brand-accent)" : "var(--border)"}`,
                          color: "#000",
                        }}
                      >
                        {on && <Check size={13} color="#000" />}
                      </span>
                      {title}
                    </button>
                  );
                })}
              </div>

              <div style={{ marginBottom: 18 }}>
                <strong style={{ display: "block", fontSize: "0.82rem", marginBottom: 8 }}>Frentes operacionais iniciais</strong>
                <div style={{ display: "grid", gap: 8 }}>
                  {PROJECT_TRACKS.map((track) => {
                    const on = projectTracks.has(track.type);
                    return (
                      <button
                        key={track.type}
                        type="button"
                        onClick={() => toggleProjectTrack(track.type)}
                        style={{
                          padding: "10px 12px",
                          borderRadius: 8,
                          textAlign: "left",
                          background: on ? "var(--surface)" : "var(--bg-inset)",
                          border: `1px solid ${on ? "var(--brand-accent)" : "var(--border)"}`,
                          color: "var(--text)",
                          cursor: "pointer",
                        }}
                      >
                        <strong>{on ? "✓ " : ""}{track.label}</strong>
                        <small style={{ display: "block", color: "var(--text-dim)", marginTop: 2 }}>{track.description}</small>
                      </button>
                    );
                  })}
                </div>
                <p className="panel-footnote">O wizard cria somente projetos e planos em rascunho. Fases e entregas exigem aprovação posterior.</p>
              </div>

              {/* Resumo do Cadastro */}
              <div style={{ background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", padding: "12px 14px", fontSize: "0.85rem" }}>
                <strong style={{ color: "var(--brand-accent)" }}>{name || "—"}</strong> · {organization || "—"}<br />
                <span style={{ color: "var(--text-dim)" }}>
                  Status: <strong>{statusLabel[status]}</strong> • {1 + modules.size} Módulos • {onboarding.size} Entregas • {projectTracks.size} Frentes
                </span>
              </div>
            </div>
          )}

          {error && <p style={{ color: "#ef4444", fontSize: "0.84rem", marginTop: 14 }}>{error}</p>}

          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 22 }}>
            <button className="ghost-button" type="button" onClick={step === 0 ? onClose : goBack} disabled={busy}>
              <ChevronLeft size={16} /> {step === 0 ? "Cancelar" : "Voltar"}
            </button>
            {step < STEPS.length - 1 ? (
              <button className="primary-button" type="button" onClick={goNext} disabled={step === 0 && !identityValid}>
                Avançar <ChevronRight size={16} />
              </button>
            ) : (
              <button className="primary-button" type="button" onClick={handleCreate} disabled={busy}>
                <Plus size={16} /> {busy ? "Criando Cliente..." : "Criar cliente agora"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
