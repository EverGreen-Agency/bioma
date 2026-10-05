import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Cpu,
  DatabaseZap,
  DollarSign,
  Gauge,
  KeyRound,
  Link2,
  LogOut,
  Network,
  Plus,
  RefreshCw,
  Route,
  Save,
  ServerCog,
  ShieldAlert,
  Trash2,
  Zap,
} from "lucide-react";

import {
  useAiRoutingControlPlane,
  useBootstrapAiModels,
  useBootstrapAiRoutingPolicies,
  useCollectAiQuota,
  useAiProviderLoginSession,
  useCancelAiProviderLogin,
  useCreateAiProviderAccount,
  useDisconnectAiProvider,
  usePreviewAiRoute,
  useProbeAiProviderRuntime,
  useRecordAiQuotaBucket,
  useSendAiProviderLoginInput,
  useStartAiProviderLogin,
  useUpdateAiHarness,
  useCurrentUser,
  useFreeProviders,
  useProviderKeys,
  useCreateProviderKey,
  useDeleteProviderKey,
  useTestFreeProvider,
  useOrganizationBudget,
  useUpdateOrganizationBudget,
  useUsageAnalytics,
} from "../hooks/useBiomaApi";
import type { AiProviderChannel, AiProviderRuntimeStatus } from "../lib/api";
import { EmptyState, SectionHeader } from "./shared";

const channelOptions: Record<
  AiProviderChannel,
  {
    label: string;
    provider:
      | "openai"
      | "anthropic"
      | "google"
      | "openrouter"
      | "deepseek"
      | "groq"
      | "cerebras"
      | "sambanova"
      | "mistral"
      | "together"
      | "cohere"
      | "github_models"
      | "cloudflare"
      | "deepinfra"
      | "novita"
      | "openai_compatible";
    authMode: "chatgpt" | "claude_subscription" | "google_subscription" | "api_key" | "vertex_adc" | "service_account";
    executionMode: "local_cli" | "sdk" | "api" | "manual_handoff";
    authRef: string | null;
  }
> = {
  codex_chatgpt: {
    label: "Codex · assinatura ChatGPT",
    provider: "openai",
    authMode: "chatgpt",
    executionMode: "local_cli",
    authRef: null,
  },
  claude_code: {
    label: "Claude Code · assinatura",
    provider: "anthropic",
    authMode: "claude_subscription",
    executionMode: "local_cli",
    authRef: null,
  },
  antigravity_cli: {
    label: "Antigravity CLI · assinatura",
    provider: "google",
    authMode: "google_subscription",
    executionMode: "local_cli",
    authRef: null,
  },
  antigravity_sdk: {
    label: "Antigravity SDK · Gemini API",
    provider: "google",
    authMode: "api_key",
    executionMode: "sdk",
    authRef: "env:GEMINI_API_KEY",
  },
  gemini_api: {
    label: "Gemini API · Antigravity SDK",
    provider: "google",
    authMode: "api_key",
    executionMode: "sdk",
    authRef: "env:GEMINI_API_KEY",
  },
  vertex: {
    label: "Vertex ADC · Antigravity SDK",
    provider: "google",
    authMode: "vertex_adc",
    executionMode: "sdk",
    authRef: null,
  },
  openrouter: {
    label: "OpenRouter · API Key",
    provider: "openrouter",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:OPENROUTER_API_KEY",
  },
  deepseek: {
    label: "DeepSeek · API Key",
    provider: "deepseek",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:DEEPSEEK_API_KEY",
  },
  groq: {
    label: "Groq · LPU Ultra-Rápido (Free)",
    provider: "groq",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:GROQ_API_KEY",
  },
  cerebras: {
    label: "Cerebras · CS-3 Wafer-scale (1M/dia Free)",
    provider: "cerebras",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:CEREBRAS_API_KEY",
  },
  sambanova: {
    label: "SambaNova · SN40L Reasoning (Free)",
    provider: "sambanova",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:SAMBANOVA_API_KEY",
  },
  mistral: {
    label: "Mistral AI · API",
    provider: "mistral",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:MISTRAL_API_KEY",
  },
  together: {
    label: "Together AI · Open-source",
    provider: "together",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:TOGETHER_API_KEY",
  },
  cohere: {
    label: "Cohere · Command R",
    provider: "cohere",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:COHERE_API_KEY",
  },
  github_models: {
    label: "GitHub Models · Azure (Free)",
    provider: "github_models",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:GITHUB_TOKEN",
  },
  cloudflare: {
    label: "Cloudflare Workers AI (Free)",
    provider: "cloudflare",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:CLOUDFLARE_API_TOKEN",
  },
  deepinfra: {
    label: "DeepInfra · API",
    provider: "deepinfra",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:DEEPINFRA_API_KEY",
  },
  novita: {
    label: "Novita AI · API",
    provider: "novita",
    authMode: "api_key",
    executionMode: "api",
    authRef: "env:NOVITA_API_KEY",
  },
  openai_compatible: {
    label: "OpenAI-Compatible Custom Endpoint",
    provider: "openai_compatible",
    authMode: "api_key",
    executionMode: "api",
    authRef: null,
  },
};

const taskOptions = [
  ["reasoning", "Planejador do copiloto"],
  ["tool_calling", "Execução de ferramentas"],
  ["quality_audit", "Auditoria de qualidade"],
  ["knowledge_curation", "Curadoria de conhecimento"],
  ["internal_chat", "Chat interno"],
  ["content_draft", "Rascunho de conteúdo"],
  ["brand_strategy", "Estratégia / brand book"],
  ["code_agent", "Engenharia / squads"],
] as const;

const harnessTools = [
  ["search_knowledge_base", "search_knowledge_base (RAG)"],
  ["update_task_status", "update_task_status (Kanban)"],
] as const;

function formatQuota(value: number | string | null) {
  if (value === null) return "não informado";
  return `${Number(value).toFixed(1)}% restante`;
}

export function AiControlPlanePanel() {
  const [activeTab, setActiveTab] = useState<"accounts" | "free_providers" | "budgets" | "harness">("accounts");

  const { data: currentUser } = useCurrentUser();
  const orgId = currentUser?.organization_id || "";

  const { data: controlPlane, error, refetch: refetchControlPlane } = useAiRoutingControlPlane();
  const createAccount = useCreateAiProviderAccount();
  const disconnectProvider = useDisconnectAiProvider();
  const bootstrapModels = useBootstrapAiModels();
  const bootstrapPolicies = useBootstrapAiRoutingPolicies();
  const recordQuota = useRecordAiQuotaBucket();
  const collectQuota = useCollectAiQuota();
  const previewRoute = usePreviewAiRoute();
  const startProviderLogin = useStartAiProviderLogin();
  const sendProviderLoginInput = useSendAiProviderLoginInput();
  const cancelProviderLogin = useCancelAiProviderLogin();
  const probeRuntime = useProbeAiProviderRuntime();
  const updateHarness = useUpdateAiHarness();

  // Hooks do pool de provedores gratuitos
  const { data: freeProviders, isLoading: loadingFreeProviders } = useFreeProviders();
  const { data: providerKeys, refetch: refetchKeys } = useProviderKeys();
  const createKey = useCreateProviderKey();
  const deleteKey = useDeleteProviderKey();
  const testProvider = useTestFreeProvider();

  // Hooks de orçamentos e FinOps
  const { data: budget } = useOrganizationBudget(orgId);
  const updateBudget = useUpdateOrganizationBudget();
  const [analyticsDays, setAnalyticsDays] = useState(30);
  const { data: analytics } = useUsageAnalytics(orgId || undefined, analyticsDays);

  // Estados locais
  const [channel, setChannel] = useState<AiProviderChannel>("codex_chatgpt");
  const [displayName, setDisplayName] = useState("Codex local");
  const [quotaAccountId, setQuotaAccountId] = useState("");
  const [bucketKey, setBucketKey] = useState("weekly");
  const [remainingPercent, setRemainingPercent] = useState("100");
  const [windowMinutes, setWindowMinutes] = useState("10080");
  const [resetsAt, setResetsAt] = useState("");
  const [taskKind, setTaskKind] = useState("content_draft");
  const [runtimeByAccount, setRuntimeByAccount] = useState<Record<string, AiProviderRuntimeStatus>>({});
  const [plannerModelId, setPlannerModelId] = useState("");
  const [toolCallerModelId, setToolCallerModelId] = useState("");
  const [auditorModelId, setAuditorModelId] = useState("");
  const [curatorModelId, setCuratorModelId] = useState("");
  const [enabledTools, setEnabledTools] = useState<string[]>(harnessTools.map(([value]) => value));

  // Estados de chaves gratuitas
  const [selectedProviderCode, setSelectedProviderCode] = useState("groq");
  const [newKeyLabel, setNewKeyLabel] = useState("Chave Principal");
  const [newKeySecret, setNewKeySecret] = useState("");
  const [testResult, setTestResult] = useState<{ provider: string; ok: boolean; message: string } | null>(null);

  // Estados de orçamento
  const [monthlyTokenCapInput, setMonthlyTokenCapInput] = useState("");
  const [monthlyCostCapInput, setMonthlyCostCapInput] = useState("");
  const [alertThresholdInput, setAlertThresholdInput] = useState(80);
  const [enforceHardStopInput, setEnforceHardStopInput] = useState(false);

  const [loginSessionId, setLoginSessionId] = useState<string | null>(null);
  const [loginInput, setLoginInput] = useState("");
  const { data: loginSession } = useAiProviderLoginSession(loginSessionId);

  useEffect(() => {
    if (budget) {
      setMonthlyTokenCapInput(budget.monthly_token_cap ? String(budget.monthly_token_cap) : "");
      setMonthlyCostCapInput(budget.monthly_cost_cap_cents ? String(budget.monthly_cost_cap_cents / 100) : "");
      setAlertThresholdInput(budget.alert_threshold_percent ?? 80);
      setEnforceHardStopInput(budget.enforce_hard_stop ?? false);
    }
  }, [budget]);

  const modelCount = useMemo(
    () => controlPlane?.accounts.reduce((total, account) => total + account.models.length, 0) ?? 0,
    [controlPlane],
  );
  const selectedPreset = channelOptions[channel];
  const modelOptions = useMemo(
    () =>
      controlPlane?.accounts.flatMap((account) =>
        account.models.map((model) => ({
          id: model.id,
          label: `${account.display_name} · ${model.display_name}`,
        })),
      ) ?? [],
    [controlPlane],
  );
  const loginUrl = useMemo(
    () => loginSession?.public_output.match(/https?:\/\/[^\s<>"']+/)?.[0] ?? null,
    [loginSession?.public_output],
  );

  useEffect(() => {
    if (loginSession?.status !== "completed") return;
    void refetchControlPlane();
    probeRuntime.mutate(loginSession.account_id, {
      onSuccess: (result) => setRuntimeByAccount((current) => ({ ...current, [loginSession.account_id]: result })),
    });
  }, [loginSession?.status, loginSession?.account_id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const config = controlPlane?.harness_config;
    if (!config) return;
    setPlannerModelId(config.planner_model_catalog_id ?? "");
    setToolCallerModelId(config.tool_caller_model_catalog_id ?? "");
    setAuditorModelId(config.auditor_model_catalog_id ?? "");
    setCuratorModelId(config.curator_model_catalog_id ?? "");
    setEnabledTools(config.enabled_tools);
  }, [controlPlane?.harness_config]);

  function handleHarness(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateHarness.mutate({
      planner_model_catalog_id: plannerModelId || null,
      tool_caller_model_catalog_id: toolCallerModelId || null,
      auditor_model_catalog_id: auditorModelId || null,
      curator_model_catalog_id: curatorModelId || null,
      enabled_tools: enabledTools,
    });
  }

  function toggleHarnessTool(tool: string) {
    setEnabledTools((current) =>
      current.includes(tool) ? current.filter((item) => item !== tool) : [...current, tool],
    );
  }

  function handleCreateAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (displayName.trim().length < 2) return;
    createAccount.mutate({
      provider: selectedPreset.provider,
      channel,
      display_name: displayName.trim(),
      auth_mode: selectedPreset.authMode,
      execution_mode: selectedPreset.executionMode,
      status: selectedPreset.executionMode === "local_cli" ? "paused" : "active",
      auth_ref: selectedPreset.authRef,
      capabilities: ["chat", "content", "strategy", "code", "reasoning", "tools", "structured_output"],
      settings: {},
    });
  }

  const handleQuota = (event: FormEvent) => {
    event.preventDefault();
    if (!quotaAccountId || !bucketKey || !remainingPercent || !windowMinutes) return;
    recordQuota.mutate({
      accountId: quotaAccountId,
      payload: {
        bucket_key: bucketKey,
        remaining_percent: parseFloat(remainingPercent),
        window_duration_minutes: parseInt(windowMinutes, 10),
        resets_at: resetsAt ? new Date(resetsAt).toISOString() : null,
        source: "manual",
        confidence: "manual",
      },
    });
  };

  const handleCreateKey = (event: FormEvent) => {
    event.preventDefault();
    if (!newKeySecret.trim()) return;
    createKey.mutate(
      {
        provider_code: selectedProviderCode,
        label: newKeyLabel.trim() || "Chave Padrão",
        api_key: newKeySecret.trim(),
      },
      {
        onSuccess: () => {
          setNewKeySecret("");
          void refetchKeys();
        },
      },
    );
  };

  const handleTestProvider = (providerCode: string) => {
    setTestResult({ provider: providerCode, ok: false, message: "Testando conexão..." });
    testProvider.mutate(providerCode, {
      onSuccess: (res) => {
        setTestResult({
          provider: providerCode,
          ok: true,
          message: `Conexão bem-sucedida com ${res.provider}! Resposta: "${res.response}" (${res.model})`,
        });
      },
      onError: (err: any) => {
        setTestResult({
          provider: providerCode,
          ok: false,
          message: `Erro no teste: ${err?.message || "Falha de conexão"}`,
        });
      },
    });
  };

  const handleSaveBudget = (event: FormEvent) => {
    event.preventDefault();
    if (!orgId) return;
    const tokenCap = monthlyTokenCapInput ? parseInt(monthlyTokenCapInput, 10) : null;
    const costCapCents = monthlyCostCapInput ? Math.round(parseFloat(monthlyCostCapInput) * 100) : null;
    updateBudget.mutate({
      organizationId: orgId,
      payload: {
        monthly_token_cap: tokenCap,
        monthly_cost_cap_cents: costCapCents,
        alert_threshold_percent: alertThresholdInput,
        enforce_hard_stop: enforceHardStopInput,
      },
    });
  };

  const handleProviderLoginInput = (event: FormEvent) => {
    event.preventDefault();
    if (!loginSessionId || !loginInput.trim()) return;
    sendProviderLoginInput.mutate(
      { sessionId: loginSessionId, value: loginInput.trim() },
      { onSuccess: () => setLoginInput("") },
    );
  };

  const closeProviderLogin = () => {
    if (loginSessionId && loginSession && ["pending", "running", "waiting_input"].includes(loginSession.status)) {
      cancelProviderLogin.mutate(loginSessionId);
    }
    setLoginSessionId(null);
    setLoginInput("");
  };

  return (
    <div className="operations-layout">
      {error && <div className="notice error">{error.message}</div>}
      {startProviderLogin.error && <div className="notice error">{startProviderLogin.error.message}</div>}
      {sendProviderLoginInput.error && <div className="notice error">{sendProviderLoginInput.error.message}</div>}
      {disconnectProvider.error && <div className="notice error">{disconnectProvider.error.message}</div>}

      {/* Navegação entre abas do Control Plane */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid var(--border-soft)", paddingBottom: "12px", marginBottom: "16px" }}>
        <button
          type="button"
          className={activeTab === "accounts" ? "primary-button" : "secondary-button"}
          onClick={() => setActiveTab("accounts")}
        >
          <Network size={16} /> Contas & Runtimes
        </button>
        <button
          type="button"
          className={activeTab === "free_providers" ? "primary-button" : "secondary-button"}
          onClick={() => setActiveTab("free_providers")}
        >
          <Zap size={16} /> Provedores Gratuitos (FreeLLMAPI)
        </button>
        <button
          type="button"
          className={activeTab === "budgets" ? "primary-button" : "secondary-button"}
          onClick={() => setActiveTab("budgets")}
        >
          <DollarSign size={16} /> FinOps & Orçamentos
        </button>
        <button
          type="button"
          className={activeTab === "harness" ? "primary-button" : "secondary-button"}
          onClick={() => setActiveTab("harness")}
        >
          <Route size={16} /> Harness & Roteamento
        </button>
      </div>

      {/* ABA 1: CONTAS & RUNTIMES */}
      {activeTab === "accounts" && (
        <>
          <div className="notice">
            <strong>Dois canais Google, duas cotas diferentes.</strong> Antigravity CLI usa a assinatura Google em modo
            headless; Antigravity SDK executa com Gemini API ou Vertex. São credenciais e cotas diferentes, e o Bioma
            não soma esses saldos.
          </div>

          <div className="bento-grid">
            <article className="bento-card col-span-2">
              <div className="bento-header">
                <h3>Contas ativas</h3>
                <Network size={16} />
              </div>
              <div className="bento-value">{controlPlane?.accounts.length ?? 0}</div>
              <div className="bento-footer">Fornecedor + canal + autenticação são identidades separadas.</div>
            </article>
            <article className="bento-card col-span-2">
              <div className="bento-header">
                <h3>Modelos roteáveis</h3>
                <Bot size={16} />
              </div>
              <div className="bento-value">{modelCount}</div>
              <div className="bento-footer">Catálogo explícito; nenhum slug é descoberto por suposição.</div>
            </article>
          </div>

          <div className="operations-grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
            <article className="surface">
              <SectionHeader eyebrow="Providers" title="Cadastrar conta" icon={Plus} />
              <form className="form-grid" onSubmit={handleCreateAccount}>
                <label>
                  Canal operacional
                  <select
                    value={channel}
                    onChange={(event) => {
                      const next = event.target.value as AiProviderChannel;
                      setChannel(next);
                      setDisplayName(channelOptions[next].label);
                    }}
                  >
                    {Object.entries(channelOptions).map(([key, option]) => (
                      <option key={key} value={key}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Nome de exibição
                  <input
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder="Ex.: Codex Pro da agência"
                  />
                </label>
                <div className="row-tail">
                  <button className="primary-button" type="submit" disabled={createAccount.isPending}>
                    <Plus size={14} /> Salvar conta
                  </button>
                </div>
              </form>
            </article>

            <article className="surface">
              <SectionHeader eyebrow="Simulação" title="Prévia de rota" icon={Route} />
              <div className="form-grid">
                <label>
                  Tipo de tarefa
                  <select value={taskKind} onChange={(event) => setTaskKind(event.target.value)}>
                    {taskOptions.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label} ({value})
                      </option>
                    ))}
                  </select>
                </label>
                <div className="row-tail">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => previewRoute.mutate(taskKind)}
                    disabled={previewRoute.isPending}
                  >
                    <Route size={14} /> Testar decisão
                  </button>
                </div>
                {previewRoute.data?.selected && (
                  <div className="notice" style={{ marginTop: "8px" }}>
                    <strong>Candidato escolhido: {previewRoute.data.selected.display_name}</strong>
                    <small>
                      Score: {previewRoute.data.selected.score} · Cota: {previewRoute.data.selected.quota_headroom ?? "N/A"}%
                    </small>
                    {previewRoute.data.selected.reasons.map((reason) => (
                      <small key={reason}>• {reason}</small>
                    ))}
                  </div>
                )}
              </div>
            </article>

            <article className="surface">
              <SectionHeader eyebrow="Reserva" title="Registrar cota manual" icon={Gauge} />
              <form className="form-grid" onSubmit={handleQuota}>
                <label>
                  Conta
                  <select value={quotaAccountId} onChange={(e) => setQuotaAccountId(e.target.value)}>
                    <option value="">Selecione uma conta</option>
                    {controlPlane?.accounts.map((acc) => (
                      <option key={acc.id} value={acc.id}>
                        {acc.display_name} ({acc.channel})
                      </option>
                    ))}
                  </select>
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  <label style={{ flex: 1 }}>
                    Chave
                    <input value={bucketKey} onChange={(e) => setBucketKey(e.target.value)} />
                  </label>
                  <label style={{ flex: 1 }}>
                    Restante %
                    <input
                      type="number"
                      value={remainingPercent}
                      onChange={(e) => setRemainingPercent(e.target.value)}
                    />
                  </label>
                </div>
                <div className="row-tail">
                  <button className="secondary-button" type="submit" disabled={recordQuota.isPending || !quotaAccountId}>
                    <Gauge size={14} /> Gravar cota
                  </button>
                </div>
              </form>
            </article>
          </div>

          <article className="surface">
            <SectionHeader eyebrow="Inventário" title="Contas, modelos e janelas" icon={Network} />
            <div className="hub-block-list">
              {controlPlane?.accounts.length === 0 && <EmptyState compact text="Cadastre a primeira conta de IA." />}
              {controlPlane?.accounts.map((account) => (
                <div className="work-row" key={account.id} style={{ alignItems: "flex-start" }}>
                  <Bot size={16} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <strong>
                      {account.display_name} · {account.channel}
                    </strong>
                    <small>
                      {account.provider} · {account.auth_mode} · {account.execution_mode} · {account.status}
                    </small>
                    <small>
                      Modelos:{" "}
                      {account.models.length
                        ? account.models.map((model) => `${model.display_name} [${model.capability_tier}]`).join(" · ")
                        : "catálogo ainda vazio"}
                    </small>
                    {account.quota_buckets.length > 0 ? (
                      <small>
                        Cotas:{" "}
                        {account.quota_buckets
                          .map(
                            (bucket) =>
                              `${bucket.bucket_key}: ${formatQuota(bucket.remaining_percent)}${
                                bucket.resets_at ? ` · reset ${new Date(bucket.resets_at).toLocaleString("pt-BR")}` : ""
                              }`,
                          )
                          .join(" | ")}
                      </small>
                    ) : (
                      <small style={{ color: "var(--warning, #d97706)" }}>
                        ⚠️ Cota: sem medição atual — router opera com reserva mínima até primeira coleta.
                      </small>
                    )}
                    {account.last_probe_at && (
                      <small style={{ opacity: 0.85 }}>
                        Último probe: {new Date(account.last_probe_at).toLocaleString("pt-BR")}
                      </small>
                    )}
                    {account.health_detail && (
                      <small style={{ color: "var(--danger, #dc2626)", display: "block", marginTop: "2px" }}>
                        Diagnóstico: {account.health_detail}
                      </small>
                    )}
                  </div>
                  <div className="row-tail">
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => bootstrapModels.mutate(account.id)}
                      disabled={bootstrapModels.isPending}
                    >
                      <RefreshCw size={14} /> Catálogo
                    </button>
                    {["codex_chatgpt", "claude_code", "antigravity_cli"].includes(account.channel) && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => collectQuota.mutate(account.id)}
                        disabled={collectQuota.isPending}
                      >
                        <Gauge size={14} /> Coletar cota
                      </button>
                    )}
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() =>
                        probeRuntime.mutate(account.id, {
                          onSuccess: (result) => setRuntimeByAccount((current) => ({ ...current, [account.id]: result })),
                        })
                      }
                      disabled={probeRuntime.isPending}
                    >
                      <ServerCog size={14} /> Verificar runtime
                    </button>
                    {["codex_chatgpt", "claude_code", "antigravity_cli"].includes(account.channel) && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() =>
                          startProviderLogin.mutate(account.id, {
                            onSuccess: (session) => setLoginSessionId(session.id),
                          })
                        }
                        disabled={startProviderLogin.isPending}
                      >
                        <Link2 size={14} /> Entrar com{" "}
                        {account.provider === "openai"
                          ? "ChatGPT"
                          : account.provider === "anthropic"
                          ? "Claude"
                          : "Google"}
                      </button>
                    )}
                    {account.credentials_configured && (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => {
                          if (
                            window.confirm(
                              `Desconectar ${account.display_name} do Bioma? A sessão será removida daqui.`,
                            )
                          )
                            disconnectProvider.mutate(account.id);
                        }}
                        disabled={disconnectProvider.isPending}
                      >
                        <LogOut size={14} /> Desconectar
                      </button>
                    )}
                  </div>
                  {runtimeByAccount[account.id] && (
                    <div
                      className={runtimeByAccount[account.id].ready ? "notice" : "notice error"}
                      style={{ width: "100%", marginTop: "8px" }}
                    >
                      <strong>
                        {runtimeByAccount[account.id].ready
                          ? "✓ Runtime pronto e autenticado"
                          : "⚠️ Runtime incompleto ou não autenticado"}
                      </strong>
                      <small>{runtimeByAccount[account.id].detail}</small>
                      {runtimeByAccount[account.id].quota_summary && (
                        <small style={{ display: "block", marginTop: "2px", fontWeight: 500 }}>
                          ℹ️ {runtimeByAccount[account.id].quota_summary}
                        </small>
                      )}
                      {runtimeByAccount[account.id].instructions.map((instruction) => (
                        <small key={instruction}>• {instruction}</small>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </article>
        </>
      )}

      {/* ABA 2: PROVEDORES GRATUITOS (FREELLMAPI NATIVO) */}
      {activeTab === "free_providers" && (
        <>
          <div className="notice" style={{ background: "rgba(16, 185, 129, 0.1)", borderColor: "var(--success, #10b981)" }}>
            <strong>Pool Nativo de Provedores Gratuitos (FreeLLMAPI Integrado)</strong>
            <p style={{ margin: "4px 0 0 0", fontSize: "13px" }}>
              O Bioma agrega mais de 10 provedores com cotas gratuitas generosas (Groq, Cerebras, SambaNova, Mistral,
              Together, Cohere, etc.). Múltiplas chaves cadastradas contam com rotação automática em caso de Rate Limit
              (HTTP 429) e fallback entre provedores com custo zero.
            </p>
          </div>

          {testResult && (
            <div className={testResult.ok ? "notice" : "notice error"} style={{ marginBottom: "16px" }}>
              <strong>{testResult.ok ? "✓ Teste de Conexão Bem-Sucedido" : "⚠️ Falha no Teste"}</strong>
              <p style={{ margin: "2px 0 0 0", fontSize: "13px" }}>{testResult.message}</p>
            </div>
          )}

          <div className="operations-grid" style={{ gridTemplateColumns: "1fr 2fr", gap: "16px" }}>
            {/* Formulário para cadastrar chave no pool */}
            <article className="surface">
              <SectionHeader eyebrow="Cofre Cifrado" title="Adicionar chave ao pool" icon={KeyRound} />
              <form className="form-grid" onSubmit={handleCreateKey}>
                <label>
                  Provedor Gratuito
                  <select
                    value={selectedProviderCode}
                    onChange={(e) => setSelectedProviderCode(e.target.value)}
                  >
                    {freeProviders?.map((p) => (
                      <option key={p.code} value={p.code}>
                        {p.name} ({p.code})
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Rótulo identificador
                  <input
                    value={newKeyLabel}
                    onChange={(e) => setNewKeyLabel(e.target.value)}
                    placeholder="Ex.: Chave 1 - Produção"
                  />
                </label>
                <label>
                  Chave de API (Secret)
                  <input
                    type="password"
                    value={newKeySecret}
                    onChange={(e) => setNewKeySecret(e.target.value)}
                    placeholder="Cole a chave (gsk_..., etc.)"
                  />
                  <small style={{ color: "var(--muted)", fontSize: "11px" }}>
                    Cifrada com SECRET_ENCRYPTION_KEY (Fernet). Nunca exposta no navegador.
                  </small>
                </label>
                <div className="row-tail">
                  <button className="primary-button" type="submit" disabled={createKey.isPending || !newKeySecret.trim()}>
                    <Plus size={14} /> Salvar no Pool
                  </button>
                </div>
              </form>
            </article>

            {/* Tabela de chaves cadastradas */}
            <article className="surface">
              <SectionHeader eyebrow="Pool Ativo" title="Chaves cadastradas e rotação" icon={Zap} />
              <div className="hub-block-list">
                {(!providerKeys || providerKeys.length === 0) && (
                  <EmptyState compact text="Nenhuma chave cadastrada no pool ainda. Adicione uma chave ao lado ou use variáveis de ambiente (.env)." />
                )}
                {providerKeys?.map((k) => (
                  <div className="work-row" key={k.id} style={{ alignItems: "center" }}>
                    <KeyRound size={16} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <strong>{k.label} · {k.provider_code.toUpperCase()}</strong>
                      <small>
                        Fingerprint: <code>{k.key_fingerprint}</code> · Chamadas: {k.call_count}
                        {k.error_count > 0 ? ` · Erros: ${k.error_count}` : ""}
                      </small>
                      {k.last_used_at && (
                        <small style={{ opacity: 0.8 }}>
                          Último uso: {new Date(k.last_used_at).toLocaleString("pt-BR")}
                        </small>
                      )}
                      {k.cooldown_until && new Date(k.cooldown_until) > new Date() && (
                        <small style={{ color: "var(--warning, #d97706)" }}>
                          ⏳ Em resfriamento até {new Date(k.cooldown_until).toLocaleTimeString("pt-BR")} (Rate Limit)
                        </small>
                      )}
                    </div>
                    <div className="row-tail">
                      <span
                        style={{
                          fontSize: "12px",
                          padding: "2px 8px",
                          borderRadius: "12px",
                          background: k.status === "active" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                          color: k.status === "active" ? "var(--success, #10b981)" : "var(--danger, #ef4444)",
                          fontWeight: 500,
                        }}
                      >
                        {k.status}
                      </span>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => {
                          if (window.confirm(`Remover esta chave do pool?`)) deleteKey.mutate(k.id);
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          </div>

          {/* Cards dos Provedores Suportados com Teste */}
          <article className="surface" style={{ marginTop: "16px" }}>
            <SectionHeader eyebrow="Catálogo de Presets" title="Provedores Gratuitos Disponíveis" icon={Bot} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "12px", marginTop: "12px" }}>
              {freeProviders?.map((p) => (
                <div
                  key={p.code}
                  style={{
                    padding: "12px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-soft)",
                    background: "var(--surface-soft, rgba(255, 255, 255, 0.03))",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <strong style={{ fontSize: "14px" }}>{p.name}</strong>
                      <span
                        style={{
                          fontSize: "11px",
                          padding: "1px 6px",
                          borderRadius: "8px",
                          background: p.active_keys_count > 0 || p.has_env_key ? "rgba(16, 185, 129, 0.2)" : "rgba(156, 163, 175, 0.2)",
                          color: p.active_keys_count > 0 || p.has_env_key ? "var(--success, #10b981)" : "var(--muted)",
                        }}
                      >
                        {p.active_keys_count > 0
                          ? `${p.active_keys_count} chave(s) no pool`
                          : p.has_env_key
                          ? `via ${p.default_env_var}`
                          : "Sem chave"}
                      </span>
                    </div>
                    <p style={{ fontSize: "12px", color: "var(--muted)", margin: "0 0 8px 0" }}>{p.description}</p>
                    <small style={{ display: "block", fontSize: "11px", opacity: 0.8 }}>
                      Modelos: {p.models.slice(0, 2).join(", ")}
                    </small>
                  </div>
                  <div style={{ marginTop: "12px", display: "flex", justifyContent: "flex-end" }}>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => handleTestProvider(p.code)}
                      disabled={testProvider.isPending}
                      style={{ fontSize: "12px", padding: "4px 10px" }}
                    >
                      <ServerCog size={12} /> Testar Conexão
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </article>
        </>
      )}

      {/* ABA 3: FINOPS & ORÇAMENTOS */}
      {activeTab === "budgets" && (
        <>
          <div className="bento-grid">
            <article className="bento-card col-span-1">
              <div className="bento-header">
                <h3>Tokens Mês Atual</h3>
                <Zap size={16} />
              </div>
              <div className="bento-value">{(analytics?.total_tokens_month ?? 0).toLocaleString("pt-BR")}</div>
              <div className="bento-footer">
                {budget?.monthly_token_cap
                  ? `Teto: ${budget.monthly_token_cap.toLocaleString("pt-BR")} tokens`
                  : "Sem teto definido"}
              </div>
            </article>

            <article className="bento-card col-span-1">
              <div className="bento-header">
                <h3>Custo Estimado (Mês)</h3>
                <DollarSign size={16} />
              </div>
              <div className="bento-value">
                US$ {((analytics?.total_cost_cents_month ?? 0) / 100).toFixed(2)}
              </div>
              <div className="bento-footer">
                {budget?.monthly_cost_cap_cents
                  ? `Teto: US$ ${(budget.monthly_cost_cap_cents / 100).toFixed(2)}`
                  : "Sem teto de valor"}
              </div>
            </article>

            <article className="bento-card col-span-2">
              <div className="bento-header">
                <h3>Total de Chamadas (Mês)</h3>
                <DatabaseZap size={16} />
              </div>
              <div className="bento-value">{(analytics?.total_calls_month ?? 0).toLocaleString("pt-BR")}</div>
              <div className="bento-footer">Execuções registradas em ai_execution_attempts</div>
            </article>
          </div>

          <div className="operations-grid" style={{ gridTemplateColumns: "1fr 2fr", gap: "16px", marginTop: "16px" }}>
            {/* Configuração de Orçamento */}
            <article className="surface">
              <SectionHeader eyebrow="Governança" title="Limites e Alertas da Organização" icon={ShieldAlert} />
              <form className="form-grid" onSubmit={handleSaveBudget}>
                <label>
                  Teto Mensal de Tokens
                  <input
                    type="number"
                    value={monthlyTokenCapInput}
                    onChange={(e) => setMonthlyTokenCapInput(e.target.value)}
                    placeholder="Ex.: 10000000 (vazio = ilimitado)"
                  />
                </label>
                <label>
                  Teto Mensal de Custo (US$)
                  <input
                    type="number"
                    step="0.01"
                    value={monthlyCostCapInput}
                    onChange={(e) => setMonthlyCostCapInput(e.target.value)}
                    placeholder="Ex.: 50.00 (vazio = ilimitado)"
                  />
                </label>
                <label>
                  Percentual para Alerta (%)
                  <input
                    type="number"
                    min="50"
                    max="99"
                    value={alertThresholdInput}
                    onChange={(e) => setAlertThresholdInput(parseInt(e.target.value, 10))}
                  />
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={enforceHardStopInput}
                    onChange={(e) => setEnforceHardStopInput(e.target.checked)}
                  />
                  <span style={{ fontSize: "13px" }}>
                    <strong>Bloqueio Rígido (Hard-Stop)</strong>: Travar execuções se atingir 100% do teto
                  </span>
                </label>
                <div className="row-tail">
                  <button className="primary-button" type="submit" disabled={updateBudget.isPending}>
                    <Save size={14} /> Salvar Orçamento
                  </button>
                </div>
              </form>
            </article>

            {/* Relatório de Uso Detalhado */}
            <article className="surface">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <SectionHeader eyebrow="Analítico" title="Histórico de Consumo Granular" icon={Gauge} />
                <select
                  value={analyticsDays}
                  onChange={(e) => setAnalyticsDays(parseInt(e.target.value, 10))}
                  style={{ width: "130px", fontSize: "12px" }}
                >
                  <option value={7}>Últimos 7 dias</option>
                  <option value={14}>Últimos 14 dias</option>
                  <option value={30}>Últimos 30 dias</option>
                </select>
              </div>

              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-soft)", textAlign: "left", opacity: 0.7 }}>
                      <th style={{ padding: "6px" }}>Data</th>
                      <th style={{ padding: "6px" }}>Provedor</th>
                      <th style={{ padding: "6px" }}>Modelo</th>
                      <th style={{ padding: "6px", textAlign: "right" }}>Chamadas</th>
                      <th style={{ padding: "6px", textAlign: "right" }}>Tokens</th>
                      <th style={{ padding: "6px", textAlign: "right" }}>Custo</th>
                      <th style={{ padding: "6px", textAlign: "right" }}>Latência</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(!analytics?.items || analytics.items.length === 0) && (
                      <tr>
                        <td colSpan={7} style={{ textAlign: "center", padding: "16px", color: "var(--muted)" }}>
                          Nenhuma execução registrada no período.
                        </td>
                      </tr>
                    )}
                    {analytics?.items.map((row, idx) => (
                      <tr key={`${row.date}-${row.model}-${idx}`} style={{ borderBottom: "1px solid var(--border-soft)" }}>
                        <td style={{ padding: "6px" }}>{row.date}</td>
                        <td style={{ padding: "6px" }}>{row.provider}</td>
                        <td style={{ padding: "6px", fontFamily: "monospace" }}>{row.model}</td>
                        <td style={{ padding: "6px", textAlign: "right" }}>{row.total_calls}</td>
                        <td style={{ padding: "6px", textAlign: "right" }}>{row.total_tokens.toLocaleString("pt-BR")}</td>
                        <td style={{ padding: "6px", textAlign: "right" }}>US$ {(row.total_cost_cents / 100).toFixed(2)}</td>
                        <td style={{ padding: "6px", textAlign: "right" }}>{row.avg_latency_ms} ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          </div>
        </>
      )}

      {/* ABA 4: HARNESS & ROTEAMENTO */}
      {activeTab === "harness" && (
        <article className="surface">
          <SectionHeader eyebrow="Orquestração" title="Harness e papéis de modelo" icon={Cpu} />
          <form className="form-grid" onSubmit={handleHarness}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "12px" }}>
              <label>
                Planejador do copiloto
                <select value={plannerModelId} onChange={(e) => setPlannerModelId(e.target.value)}>
                  <option value="">Automático pelo router</option>
                  {modelOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Execução de ferramentas
                <select value={toolCallerModelId} onChange={(e) => setToolCallerModelId(e.target.value)}>
                  <option value="">Automático pelo router</option>
                  {modelOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label>
              Ferramentas autorizadas no runtime
              <div style={{ display: "flex", gap: "16px", marginTop: "4px" }}>
                {harnessTools.map(([tool, desc]) => (
                  <label key={tool} style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={enabledTools.includes(tool)}
                      onChange={() => toggleHarnessTool(tool)}
                    />
                    <span style={{ fontSize: "13px" }}>{desc}</span>
                  </label>
                ))}
              </div>
            </label>
            <div className="row-tail">
              <button className="primary-button" type="submit" disabled={updateHarness.isPending}>
                <Save size={14} /> Salvar harness
              </button>
            </div>
          </form>
        </article>
      )}

      {/* MODAL DE LOGIN OFICIAL OAUTH */}
      {loginSessionId && (
        <div className="modal-backdrop" onClick={closeProviderLogin}>
          <div className="modal-card wide" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "560px" }}>
            <div className="modal-header">
              <div className="modal-title-group">
                <Link2 size={18} className="modal-icon" color="var(--brand-accent)" />
                <div>
                  <h3 className="modal-title">Login oficial · {loginSession?.account_name ?? "provider"}</h3>
                  <p className="modal-subtitle">O CLI roda no servidor; senhas e tokens nunca passam pelo navegador do Bioma.</p>
                </div>
              </div>
              <button className="modal-close" onClick={closeProviderLogin}>
                ×
              </button>
            </div>
            <div className="modal-body" style={{ padding: "20px" }}>
              <form className="form-grid" onSubmit={handleProviderLoginInput}>
                <div className={loginSession?.status === "failed" ? "notice error" : "notice"}>
                  <strong>Status: {loginSession?.status ?? "iniciando"}</strong>
                  <small>{loginSession?.prompt_hint ?? "Aguardando o terminal do CLI..."}</small>
                  {loginSession?.error_message && <small>{loginSession.error_message}</small>}
                </div>
                {loginUrl && (
                  <a className="primary-button" href={loginUrl} target="_blank" rel="noreferrer">
                    Abrir página oficial de login
                  </a>
                )}
                <label>
                  Saída do CLI
                  <pre
                    style={{
                      whiteSpace: "pre-wrap",
                      maxHeight: "220px",
                      overflow: "auto",
                      padding: "12px",
                      background: "var(--surface-soft)",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  >
                    {loginSession?.public_output || "Preparando sessão segura..."}
                  </pre>
                </label>
                {loginSession && ["pending", "running", "waiting_input"].includes(loginSession.status) && (
                  <label>
                    Código solicitado pelo CLI (quando houver)
                    <input
                      value={loginInput}
                      onChange={(event) => setLoginInput(event.target.value)}
                      placeholder="Cole apenas o código de uso único"
                      autoComplete="one-time-code"
                    />
                  </label>
                )}
                <div
                  className="modal-actions"
                  style={{
                    gridColumn: "1 / -1",
                    display: "flex",
                    justifyContent: "flex-end",
                    gap: "8px",
                    marginTop: "16px",
                  }}
                >
                  <button className="secondary-button" type="button" onClick={closeProviderLogin}>
                    {loginSession?.status === "completed" ? "Fechar" : "Cancelar"}
                  </button>
                  {loginSession && ["pending", "running", "waiting_input"].includes(loginSession.status) && (
                    <button
                      className="primary-button"
                      type="submit"
                      disabled={!loginInput.trim() || sendProviderLoginInput.isPending}
                    >
                      Enviar código
                    </button>
                  )}
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
