import { FormEvent, useMemo, useState } from "react";
import { Bot, DatabaseZap, Gauge, Link2, Network, Plus, RefreshCw, Route } from "lucide-react";

import {
  useAiRoutingControlPlane,
  useBootstrapAiModels,
  useBootstrapAiRoutingPolicies,
  useCollectAiQuota,
  useConnectAiProviderWebSession,
  useCreateAiProviderAccount,
  usePreviewAiRoute,
  useRecordAiQuotaBucket,
} from "../hooks/useBiomaApi";
import type { AiProviderChannel } from "../lib/api";
import { EmptyState, SectionHeader } from "./shared";

const channelOptions: Record<AiProviderChannel, {
  label: string;
  provider: "openai" | "anthropic" | "google";
  authMode: "chatgpt" | "claude_subscription" | "google_subscription" | "api_key" | "vertex_adc";
  executionMode: "local_cli" | "sdk" | "manual_handoff";
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
    executionMode: "manual_handoff",
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
};

const taskOptions = [
  ["internal_chat", "Chat interno"],
  ["content_draft", "Rascunho de conteúdo"],
  ["brand_strategy", "Estratégia / brand book"],
  ["code_agent", "Engenharia / squads"],
] as const;

function formatQuota(value: number | string | null) {
  if (value === null) return "não informado";
  return `${Number(value).toFixed(1)}% restante`;
}

export function AiControlPlanePanel() {
  const { data: controlPlane, error } = useAiRoutingControlPlane();
  const createAccount = useCreateAiProviderAccount();
  const bootstrapModels = useBootstrapAiModels();
  const bootstrapPolicies = useBootstrapAiRoutingPolicies();
  const recordQuota = useRecordAiQuotaBucket();
  const collectQuota = useCollectAiQuota();
  const previewRoute = usePreviewAiRoute();
  const connectWebSession = useConnectAiProviderWebSession();
  const [channel, setChannel] = useState<AiProviderChannel>("codex_chatgpt");
  const [displayName, setDisplayName] = useState("Codex local");
  const [quotaAccountId, setQuotaAccountId] = useState("");
  const [bucketKey, setBucketKey] = useState("weekly");
  const [remainingPercent, setRemainingPercent] = useState("100");
  const [windowMinutes, setWindowMinutes] = useState("10080");
  const [resetsAt, setResetsAt] = useState("");
  const [taskKind, setTaskKind] = useState("content_draft");
  
  // Web session modal states
  const [sessionAccountId, setSessionAccountId] = useState<string | null>(null);
  const [sessionToken, setSessionToken] = useState("");
  const [oauthToken, setOauthToken] = useState("");

  const modelCount = useMemo(
    () => controlPlane?.accounts.reduce((total, account) => total + account.models.length, 0) ?? 0,
    [controlPlane],
  );
  const selectedPreset = channelOptions[channel];

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
      capabilities: ["chat", "content", "strategy", "code"],
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

  const handleConnectWebSession = (event: FormEvent) => {
    event.preventDefault();
    if (!sessionAccountId || !sessionToken) return;
    connectWebSession.mutate(
      {
        accountId: sessionAccountId,
        payload: {
          session_token: sessionToken,
          oauth_token: oauthToken || undefined,
        },
      },
      {
        onSuccess: () => {
          setSessionAccountId(null);
          setSessionToken("");
          setOauthToken("");
        },
      }
    );
  };

  return (
    <div className="operations-layout">
      {error && <div className="notice error">{error.message}</div>}
      <div className="notice">
        <strong>Dois canais Google, duas cotas diferentes.</strong>{" "}
        Antigravity CLI usa a assinatura Google e hoje exige handoff manual; Antigravity SDK executa no worker
        com Gemini API ou Vertex. O Bioma nunca soma esses saldos como se fossem a mesma conta.
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
            {controlPlane?.policies.length === 0 && (
              <button className="secondary-button" type="button" onClick={() => bootstrapPolicies.mutate()} disabled={bootstrapPolicies.isPending}>
                Criar políticas padrão
              </button>
            )}
          </div>
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
                {account.channel === "codex_chatgpt" && (
                  <button className="secondary-button" type="button" onClick={() => collectQuota.mutate(account.id)} disabled={collectQuota.isPending}>
                    <Gauge size={14} /> Coletar cota
                  </button>
                )}
                {["codex_chatgpt", "claude_code", "antigravity_sdk"].includes(account.channel) && (
                  <button className="secondary-button" type="button" onClick={() => setSessionAccountId(account.id)}>
                    <Link2 size={14} /> Conectar
                  </button>
                )}
              </div>
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

      {sessionAccountId && (
        <div className="modal-backdrop" onClick={() => setSessionAccountId(null)}>
          <div className="modal-card wide" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "560px" }}>
            <div className="modal-header">
              <div className="modal-title-group">
                <Link2 size={18} className="modal-icon" color="var(--brand-accent)" />
                <div>
                  <h3 className="modal-title">Conectar Conta via Web</h3>
                  <p className="modal-subtitle">Insira as credenciais de sessão para autorizar esta conta.</p>
                </div>
              </div>
              <button className="modal-close" onClick={() => setSessionAccountId(null)}>×</button>
            </div>
            <div className="modal-body" style={{ padding: "20px" }}>
              <form className="form-grid" onSubmit={handleConnectWebSession}>
                <label>
                  Session Token (Requerido)
                  <textarea 
                    value={sessionToken} 
                    onChange={(e) => setSessionToken(e.target.value)} 
                    placeholder="Cole o cookie da sessão ou token equivalente..."
                    rows={4}
                  />
                </label>
                <label>
                  OAuth Token / Extra (Opcional)
                  <textarea 
                    value={oauthToken} 
                    onChange={(e) => setOauthToken(e.target.value)} 
                    placeholder="Token adicional, se exigido pelo provider..."
                    rows={2}
                  />
                </label>
                <div className="modal-actions" style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "16px" }}>
                  <button className="secondary-button" type="button" onClick={() => setSessionAccountId(null)}>
                    Cancelar
                  </button>
                  <button className="primary-button" type="submit" disabled={!sessionToken || connectWebSession.isPending}>
                    Confirmar Conexão
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
