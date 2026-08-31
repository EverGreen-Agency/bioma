import { FormEvent, useEffect, useMemo, useState } from "react";
import { Bot, Cpu, DatabaseZap, Gauge, Link2, LogOut, Network, Plus, RefreshCw, Route, Save, ServerCog } from "lucide-react";

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
} from "../hooks/useBiomaApi";
import type { AiProviderChannel, AiProviderRuntimeStatus } from "../lib/api";
import { EmptyState, SectionHeader } from "./shared";

const channelOptions: Record<AiProviderChannel, {
  label: string;
  provider: "openai" | "anthropic" | "google" | "openrouter" | "deepseek" | "groq";
  authMode: "chatgpt" | "claude_subscription" | "google_subscription" | "api_key" | "vertex_adc";
  executionMode: "local_cli" | "sdk" | "api" | "manual_handoff";
  authRef: string | null;
}> = {
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
  
  const [loginSessionId, setLoginSessionId] = useState<string | null>(null);
  const [loginInput, setLoginInput] = useState("");
  const { data: loginSession } = useAiProviderLoginSession(loginSessionId);

  const modelCount = useMemo(
    () => controlPlane?.accounts.reduce((total, account) => total + account.models.length, 0) ?? 0,
    [controlPlane],
  );
  const selectedPreset = channelOptions[channel];
  const modelOptions = useMemo(
    () => controlPlane?.accounts.flatMap((account) => account.models.map((model) => ({
      id: model.id,
      label: `${account.display_name} · ${model.display_name}`,
    }))) ?? [],
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
    setEnabledTools((current) => current.includes(tool)
      ? current.filter((item) => item !== tool)
      : [...current, tool]);
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
      <div className="notice">
        <strong>Dois canais Google, duas cotas diferentes.</strong>{" "}
        Antigravity CLI usa a assinatura Google em modo headless; Antigravity SDK executa com Gemini API ou
        Vertex. São credenciais e cotas diferentes, e o Bioma não soma esses saldos.
      </div>

      <div className="bento-grid">
        <article className="bento-card col-span-2">
          <div className="bento-header"><h3>Contas ativas</h3><Network size={16} /></div>
          <div className="bento-value">{controlPlane?.accounts.length ?? 0}</div>
          <div className="bento-footer">Fornecedor + canal + autenticação são identidades separadas.</div>
        </article>
        <article className="bento-card col-span-2">
          <div className="bento-header"><h3>Modelos roteáveis</h3><Bot size={16} /></div>
          <div className="bento-value">{modelCount}</div>
          <div className="bento-footer">Catálogo explícito; nenhum slug é descoberto por suposição.</div>
        </article>
      </div>

      <div className="operations-grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
        <article className="surface">
          <SectionHeader eyebrow="Providers" title="Cadastrar conta" icon={Plus} />
          <form className="form-grid" onSubmit={handleCreateAccount}>
            <label>
              Canal
              <select value={channel} onChange={(event) => {
                const next = event.target.value as AiProviderChannel;
                setChannel(next);
                setDisplayName(channelOptions[next].label);
              }}>
                {Object.entries(channelOptions).map(([value, option]) => (
                  <option key={value} value={value}>{option.label}</option>
                ))}
              </select>
            </label>
            <label>
              Nome deste runner/conta
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
            </label>
            <small>
              Auth: {selectedPreset.authMode} · execução: {selectedPreset.executionMode}
              {selectedPreset.authRef ? ` · ${selectedPreset.authRef}` : " · keyring/ADC local"}
            </small>
            <button className="primary-button" type="submit" disabled={createAccount.isPending}>
              <Plus size={15} /> Cadastrar
            </button>
          </form>
        </article>

        <article className="surface">
          <SectionHeader eyebrow="Cotas" title="Registrar janela" icon={Gauge} />
          <form className="form-grid" onSubmit={handleQuota}>
            <label>
              Conta
              <select value={quotaAccountId} onChange={(event) => setQuotaAccountId(event.target.value)}>
                <option value="">Selecione</option>
                {controlPlane?.accounts.map((account) => (
                  <option key={account.id} value={account.id}>{account.display_name}</option>
                ))}
              </select>
            </label>
            <label>Janela <input value={bucketKey} onChange={(event) => setBucketKey(event.target.value)} /></label>
            <label>Restante (%) <input type="number" min="0" max="100" value={remainingPercent} onChange={(event) => setRemainingPercent(event.target.value)} /></label>
            <label>Duração (min) <input type="number" min="1" value={windowMinutes} onChange={(event) => setWindowMinutes(event.target.value)} /></label>
            <label>Reset <input type="datetime-local" value={resetsAt} onChange={(event) => setResetsAt(event.target.value)} /></label>
            <button className="secondary-button" type="submit" disabled={!quotaAccountId || recordQuota.isPending}>
              <DatabaseZap size={15} /> Salvar snapshot
            </button>
          </form>
        </article>

        <article className="surface">
          <SectionHeader eyebrow="Router" title="Simular escolha" icon={Route} />
          <div className="form-grid">
            <label>
              Tipo de tarefa
              <select value={taskKind} onChange={(event) => setTaskKind(event.target.value)}>
                {taskOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <button className="primary-button" type="button" onClick={() => previewRoute.mutate(taskKind)} disabled={previewRoute.isPending}>
              <Route size={15} /> Calcular rota
            </button>
            {previewRoute.data?.selected ? (
              <div className="notice">
                <strong>{previewRoute.data.selected.channel} · {previewRoute.data.selected.display_name}</strong>
                <small>score {previewRoute.data.selected.score} · {previewRoute.data.selected.reasons.join(" · ")}</small>
              </div>
            ) : previewRoute.data ? <EmptyState compact text="Nenhum candidato elegível." /> : null}
            <button className="secondary-button" type="button" onClick={() => bootstrapPolicies.mutate()} disabled={bootstrapPolicies.isPending}>
              Sincronizar políticas padrão
            </button>
          </div>
        </article>
      </div>

      <article className="surface">
        <SectionHeader eyebrow="Harness & Tools" title="Configuração de Etapa & Tool Calling" icon={Cpu} />
        <form className="form-grid" onSubmit={handleHarness} style={{ gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "16px" }}>
          <label>
            Planejador
            <select value={plannerModelId} onChange={(event) => setPlannerModelId(event.target.value)}>
              <option value="">Router escolhe por política e cota</option>
              {modelOptions.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}
            </select>
            <small>Preferência real do task kind reasoning; os elegíveis continuam como fallback.</small>
          </label>
          <label>
            Tool caller
            <select value={toolCallerModelId} onChange={(event) => setToolCallerModelId(event.target.value)}>
              <option value="">Router escolhe por política e cota</option>
              {modelOptions.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}
            </select>
            <small>Preferência do task kind tool_calling.</small>
          </label>
          <label>
            Auditor
            <select value={auditorModelId} onChange={(event) => setAuditorModelId(event.target.value)}>
              <option value="">Router escolhe por política e cota</option>
              {modelOptions.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}
            </select>
            <small>Preferência do task kind quality_audit.</small>
          </label>
          <label>
            Curador
            <select value={curatorModelId} onChange={(event) => setCuratorModelId(event.target.value)}>
              <option value="">Router escolhe por política e cota</option>
              {modelOptions.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}
            </select>
            <small>Preferência do task kind knowledge_curation.</small>
          </label>
          <div>
            <strong style={{ fontSize: "13px" }}>Ferramentas habilitadas</strong>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "6px", fontSize: "13px" }}>
              {harnessTools.map(([value, label]) => (
                <label key={value} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <input type="checkbox" checked={enabledTools.includes(value)} onChange={() => toggleHarnessTool(value)} /> {label}
                </label>
              ))}
            </div>
          </div>
          <div style={{ alignSelf: "end" }}>
            <button className="primary-button" type="submit" disabled={updateHarness.isPending}>
              <Save size={15} /> Salvar Harness
            </button>
          </div>
        </form>
      </article>

      <article className="surface">
        <SectionHeader eyebrow="Inventário" title="Contas, modelos e janelas" icon={Network} />
        <div className="hub-block-list">
          {controlPlane?.accounts.length === 0 && <EmptyState compact text="Cadastre a primeira conta de IA." />}
          {controlPlane?.accounts.map((account) => (
            <div className="work-row" key={account.id} style={{ alignItems: "flex-start" }}>
              <Bot size={16} />
              <div style={{ minWidth: 0, flex: 1 }}>
                <strong>{account.display_name} · {account.channel}</strong>
                <small>
                  {account.provider} · {account.auth_mode} · {account.execution_mode} · {account.status}
                </small>
                <small>
                  Modelos: {account.models.length
                    ? account.models.map((model) => `${model.display_name} [${model.capability_tier}]`).join(" · ")
                    : "catálogo ainda vazio"}
                </small>
                <small>
                  Cotas: {account.quota_buckets.length
                    ? account.quota_buckets.map((bucket) => `${bucket.bucket_key}: ${formatQuota(bucket.remaining_percent)}${bucket.resets_at ? ` · reset ${new Date(bucket.resets_at).toLocaleString("pt-BR")}` : ""}`).join(" | ")
                    : "sem medição atual — o router sinaliza incerteza"}
                </small>
                {account.health_detail && <small style={{ color: "var(--danger)" }}>{account.health_detail}</small>}
              </div>
              <div className="row-tail">
                <button className="secondary-button" type="button" onClick={() => bootstrapModels.mutate(account.id)} disabled={bootstrapModels.isPending}>
                  <RefreshCw size={14} /> Catálogo
                </button>
                {["codex_chatgpt", "claude_code", "antigravity_cli"].includes(account.channel) && (
                  <button className="secondary-button" type="button" onClick={() => collectQuota.mutate(account.id)} disabled={collectQuota.isPending}>
                    <Gauge size={14} /> Coletar cota
                  </button>
                )}
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => probeRuntime.mutate(account.id, {
                    onSuccess: (result) => setRuntimeByAccount((current) => ({ ...current, [account.id]: result })),
                  })}
                  disabled={probeRuntime.isPending}
                >
                  <ServerCog size={14} /> Verificar runtime
                </button>
                {["codex_chatgpt", "claude_code", "antigravity_cli"].includes(account.channel) && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => startProviderLogin.mutate(account.id, {
                      onSuccess: (session) => setLoginSessionId(session.id),
                    })}
                    disabled={startProviderLogin.isPending}
                  >
                    <Link2 size={14} /> Entrar com {account.provider === "openai" ? "ChatGPT" : account.provider === "anthropic" ? "Claude" : "Google"}
                  </button>
                )}
                {account.credentials_configured && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => {
                      if (window.confirm(
                        `Desconectar ${account.display_name} do Bioma? A sessão será removida daqui, mas a revogação no provedor continua sendo feita na conta do provedor.`,
                      )) disconnectProvider.mutate(account.id);
                    }}
                    disabled={disconnectProvider.isPending}
                  >
                    <LogOut size={14} /> Desconectar
                  </button>
                )}
              </div>
              {runtimeByAccount[account.id] && (
                <div className={runtimeByAccount[account.id].ready ? "notice" : "notice error"} style={{ width: "100%" }}>
                  <strong>{runtimeByAccount[account.id].ready ? "Runtime pronto" : "Runtime incompleto"}</strong>
                  <small>{runtimeByAccount[account.id].detail}</small>
                  {runtimeByAccount[account.id].instructions.map((instruction) => <small key={instruction}>• {instruction}</small>)}
                </div>
              )}
            </div>
          ))}
        </div>
      </article>

      {(controlPlane?.quota_collection_jobs.length ?? 0) > 0 && (
        <article className="surface">
          <SectionHeader eyebrow="Coletores" title="Últimas leituras de cota" icon={DatabaseZap} />
          <div className="hub-block-list">
            {controlPlane?.quota_collection_jobs.slice(0, 8).map((job) => (
              <div className="work-row" key={job.id}>
                <Gauge size={15} />
                <div>
                  <strong>{job.collector} · {job.status}</strong>
                  <small>{new Date(job.created_at).toLocaleString("pt-BR")} · tentativa {job.attempts}</small>
                  {job.error_message && <small style={{ color: "var(--danger)" }}>{job.error_message}</small>}
                </div>
              </div>
            ))}
          </div>
        </article>
      )}

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
              <button className="modal-close" onClick={closeProviderLogin}>×</button>
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
                  <pre style={{ whiteSpace: "pre-wrap", maxHeight: "220px", overflow: "auto", padding: "12px", background: "var(--surface-soft)", borderRadius: "8px", fontSize: "12px" }}>
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
                <div className="modal-actions" style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "16px" }}>
                  <button className="secondary-button" type="button" onClick={closeProviderLogin}>
                    {loginSession?.status === "completed" ? "Fechar" : "Cancelar"}
                  </button>
                  {loginSession && ["pending", "running", "waiting_input"].includes(loginSession.status) && (
                    <button className="primary-button" type="submit" disabled={!loginInput.trim() || sendProviderLoginInput.isPending}>
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
