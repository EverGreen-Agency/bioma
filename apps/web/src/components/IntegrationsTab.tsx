import { FormEvent, useState } from "react";
import {
  Activity,
  Bot,
  Cloud,
  KeyRound,
  PenLine,
  Plus,
  RefreshCw,
  Server,
  Briefcase,
} from "lucide-react";
import { CmsTargetsManager } from "./CmsTargetsManager";
import { useUiStore } from "../store/uiStore";
import {
  useClients,
  useCreatePerformanceConnection,
  useIntegrationsStatus,
  usePerformanceConnections,
  useRequestPerformanceSync,
  useSavePerformanceProviderToken,
  useUpdatePerformanceConnection,
  useKommoConfig,
  useSetupKommoConfig,
} from "../hooks/useBiomaApi";
import { formatDateTime } from "../lib/format";
import type { PerformanceConnection, PerformanceProvider, OpportunityPlatformConfig } from "../lib/api";
import { api, apiUrl } from "../lib/api";
import { useEffect } from "react";
import { WhatsAppManager } from "./WhatsAppManager";
import { StatusPill } from "./StatusPill";
import { IntegrationGuide } from "./IntegrationGuide";
import {
  Ga4Icon,
  GoogleAdSenseIcon,
  GoogleAdsIcon,
  GoogleBusinessProfileIcon,
  GtmIcon,
  HubSpotIcon,
  InstagramIcon,
  KommoIcon,
  LinkedInAdsIcon,
  MetaAdsIcon,
  OpenAiAdsIcon,
  RdStationIcon,
  SearchConsoleIcon,
  TikTokIcon,
  YouTubeIcon,
} from "./icons/BrandIcons";

const PROVIDER_META: Record<PerformanceProvider, {
  label: string;
  icon: typeof GoogleAdsIcon;
  accountLabel: string;
  accountPlaceholder: string;
  parentLabel?: string;
  parentPlaceholder?: string;
  oauthConnect?: boolean;
  /** CRMs que autenticam por token colado (não OAuth, não account id). */
  tokenConnect?: { label: string; placeholder: string };
}> = {
  google_ads: {
    label: "Google Ads",
    icon: GoogleAdsIcon,
    accountLabel: "Customer ID",
    accountPlaceholder: "123-456-7890",
    parentLabel: "MCC (login customer id) — opcional",
    parentPlaceholder: "111-222-3333",
  },
  ga4: {
    label: "Google Analytics 4",
    icon: Ga4Icon,
    accountLabel: "Property ID",
    accountPlaceholder: "123456789",
  },
  search_console: {
    label: "Search Console",
    icon: SearchConsoleIcon,
    accountLabel: "Propriedade",
    accountPlaceholder: "sc-domain:evergreenmkt.com.br",
  },
  gtm: {
    label: "Google Tag Manager",
    icon: GtmIcon,
    accountLabel: "Container ID",
    accountPlaceholder: "GTM-XXXXXXX",
    parentLabel: "Account ID",
    parentPlaceholder: "6000000000",
  },
  meta_ads: {
    label: "Meta Ads",
    icon: MetaAdsIcon,
    accountLabel: "Ad Account ID",
    accountPlaceholder: "act_1234567890",
  },
  linkedin_ads: {
    label: "LinkedIn Ads",
    icon: LinkedInAdsIcon,
    accountLabel: "Sponsored Account ID",
    accountPlaceholder: "123456789",
  },
  openai_ads: {
    label: "ChatGPT Ads (OpenAI)",
    icon: OpenAiAdsIcon,
    accountLabel: "Account ID",
    accountPlaceholder: "act_openai_12345",
  },
  instagram_organic: {
    label: "Instagram (orgânico)",
    icon: InstagramIcon,
    accountLabel: "Instagram Business Account ID",
    accountPlaceholder: "17841400000000000",
  },
  google_business_profile: {
    label: "Google Meu Negócio",
    icon: GoogleBusinessProfileIcon,
    accountLabel: "Location ID",
    accountPlaceholder: "locations/1234567890",
  },
  google_adsense: {
    label: "Google AdSense",
    icon: GoogleAdSenseIcon,
    accountLabel: "Account ID",
    accountPlaceholder: "accounts/pub-1234567890123456",
  },
  youtube_organic: {
    label: "YouTube (orgânico)",
    icon: YouTubeIcon,
    accountLabel: "Channel ID",
    accountPlaceholder: "UCxxxxxxxxxxxxxxxxxxxxxx",
  },
  tiktok_organic: {
    label: "TikTok (orgânico)",
    icon: TikTokIcon,
    accountLabel: "Resolvido automaticamente pela autorização",
    accountPlaceholder: "",
    oauthConnect: true,
  },
  tiktok_ads: {
    label: "TikTok Ads",
    icon: TikTokIcon,
    accountLabel: "Resolvido automaticamente pela autorização",
    accountPlaceholder: "",
    oauthConnect: true,
  },
  linkedin_organic: {
    label: "LinkedIn (orgânico)",
    icon: LinkedInAdsIcon,
    accountLabel: "Resolvido automaticamente pela autorização",
    accountPlaceholder: "",
    oauthConnect: true,
  },
  rd_station_crm: {
    label: "RD Station CRM",
    icon: RdStationIcon,
    accountLabel: "Conexão por token",
    accountPlaceholder: "",
    tokenConnect: { label: "Token da instância", placeholder: "Cole o token gerado no RD Station CRM" },
  },
  hubspot: {
    label: "HubSpot",
    icon: HubSpotIcon,
    accountLabel: "Conexão por token",
    accountPlaceholder: "",
    tokenConnect: { label: "Token do app privado", placeholder: "pat-na1-..." },
  },
};

const PROVIDERS = Object.keys(PROVIDER_META) as PerformanceProvider[];

function EnvStatusPill({ configured }: { configured: boolean }) {
  return (
    <StatusPill variant={configured ? "connected" : "not_configured"}>
      {configured ? "Configurado" : "Não configurado"}
    </StatusPill>
  );
}

/** Lista as variáveis de ambiente ausentes, pelo nome exato.
 *
 * "Não configurado" sozinho manda conferir três variáveis sem dizer qual
 * falta. Como no Railway a API e o worker têm conjuntos separados, o erro
 * frequente é a variável existir num serviço e faltar no outro — e o nome
 * exato é o que encurta a busca. Nunca mostra valor, só nome. */
function MissingVars({ names }: { names?: string[] | null }) {
  if (!names || names.length === 0) return null;
  return (
    <div style={{ fontSize: 11.5, color: "var(--danger)", marginTop: 4 }}>
      Falta neste serviço: {names.join(", ")}
    </div>
  );
}

function ConnectionStatusPill({ connection }: { connection: PerformanceConnection | null }) {
  if (!connection) return <StatusPill variant="not_configured">Sem conexão</StatusPill>;
  if (connection.status === "error") return <StatusPill variant="error">Erro</StatusPill>;
  if (connection.status === "inactive") return <StatusPill variant="paused">Inativa</StatusPill>;
  return <StatusPill variant="connected">Ativa</StatusPill>;
}

export function IntegrationsTab({
  clientId = null,
  scope = "all",
  subjectName = null,
}: {
  clientId?: string | null;
  scope?: "all" | "environment" | "client";
  /** Nome a exibir quando o sujeito não está na carteira (ex.: a própria EG). */
  subjectName?: string | null;
} = {}) {
  const { selectedClientId: storedClientId, setSelectedClientId } = useUiStore();
  const selectedClientId = clientId ?? storedClientId;
  const { data: clients = [] } = useClients();
  const { data: envStatus } = useIntegrationsStatus();
  const { data: connections = [], isLoading: loadingConnections } = usePerformanceConnections(selectedClientId);

  const createConnection = useCreatePerformanceConnection();
  const updateConnection = useUpdatePerformanceConnection();
  const requestSync = useRequestPerformanceSync();
  const saveProviderToken = useSavePerformanceProviderToken();

  const [oppPlatforms, setOppPlatforms] = useState<OpportunityPlatformConfig[]>([]);
  const [editingPlatformKey, setEditingPlatformKey] = useState<string | null>(null);
  const [editRssUrl, setEditRssUrl] = useState("");
  const [editStatus, setEditStatus] = useState<"active" | "paused" | "not_configured">("active");
  const [editMonthlyCost, setEditMonthlyCost] = useState(0);
  const [savingPlatform, setSavingPlatform] = useState(false);

  useEffect(() => {
    loadOppPlatforms();
  }, []);

  async function loadOppPlatforms() {
    try {
      const data = await api.listOpportunityPlatforms();
      setOppPlatforms(data);
    } catch (err) {
      console.error("Erro ao carregar plataformas de oportunidades:", err);
    }
  }

  async function handleSavePlatformConfig(e: FormEvent) {
    e.preventDefault();
    if (!editingPlatformKey) return;
    setSavingPlatform(true);
    try {
      await api.updateOpportunityPlatform(editingPlatformKey, {
        platform_name:
          oppPlatforms.find((platform) => platform.platform_key === editingPlatformKey)?.platform_name
          ?? editingPlatformKey,
        status: editStatus,
        rss_url: editRssUrl || null,
        monthly_cost_cents: Math.round(Number(editMonthlyCost) * 100),
      });
      setEditingPlatformKey(null);
      await loadOppPlatforms();
    } catch (err: any) {
      alert("Erro ao salvar configuração da plataforma: " + (err.message || "Erro desconhecido"));
    } finally {
      setSavingPlatform(false);
    }
  }

  const [editingProvider, setEditingProvider] = useState<PerformanceProvider | null>(null);
  const [providerToken, setProviderToken] = useState("");
  const [accountId, setAccountId] = useState("");
  const [parentId, setParentId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [syncFeedback, setSyncFeedback] = useState<string>("");

  // O sujeito pode NÃO estar na carteira: a Operação EG é um workspace sem
  // registro comercial (nada de "EverGreen Internal" desde a 0087), e a
  // carteira só lista clientes externos. Sem este fallback, apontar esta tela
  // para a EG mostrava "Selecione um cliente" e nenhum campo para preencher —
  // que foi exatamente o que aconteceu ao mover as integrações para cá.
  const selectedClient =
    clients.find((client) => client.id === selectedClientId) ??
    (clientId && subjectName ? { id: clientId, name: subjectName, organization_id: null } : null);
  const organizationId = selectedClient?.organization_id ?? null;

  const { data: kommoConfig, isLoading: loadingKommo } = useKommoConfig(organizationId);
  const setupKommo = useSetupKommoConfig();

  const [kommoClientId, setKommoClientId] = useState("");
  const [kommoClientSecret, setKommoClientSecret] = useState("");
  const [kommoAccessToken, setKommoAccessToken] = useState("");
  const [kommoSubdomain, setKommoSubdomain] = useState("");
  const [isEditingKommo, setIsEditingKommo] = useState(false);

  // Um único consentimento OAuth pode devolver várias contas (ex: TikTok Ads
  // com N advertisers, LinkedIn com N organizações administradas). Guardamos
  // uma conexão por conta, então o card precisa listar todas — senão as
  // demais sincronizam invisíveis.
  const connectionsFor = (provider: PerformanceProvider) =>
    connections.filter((connection) => connection.provider === provider);

  const connectionFor = (provider: PerformanceProvider) =>
    connectionsFor(provider)[0] ?? null;

  function startEdit(provider: PerformanceProvider) {
    const existing = connectionFor(provider);
    setEditingProvider(provider);
    setAccountId(existing?.external_account_id ?? "");
    setParentId(existing?.external_parent_id ?? "");
    setDisplayName(existing?.display_name ?? "");
  }

  function cancelEdit() {
    setEditingProvider(null);
    setAccountId("");
    setParentId("");
    setDisplayName("");
    setProviderToken("");
  }

  function handleSaveProviderToken(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedClientId || !editingProvider || !providerToken.trim()) return;
    saveProviderToken.mutate(
      { workspaceId: selectedClientId, provider: editingProvider, token: providerToken.trim() },
      { onSuccess: cancelEdit },
    );
  }

  function startEditKommo() {
    setIsEditingKommo(true);
    setKommoSubdomain(kommoConfig?.subdomain ?? "");
  }

  function cancelEditKommo() {
    setIsEditingKommo(false);
    setKommoClientId("");
    setKommoClientSecret("");
    setKommoAccessToken("");
    setKommoSubdomain("");
  }

  function handleSaveKommo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!organizationId) return;
    setupKommo.mutate(
      {
        organizationId,
        payload: {
          client_id: kommoClientId.trim(),
          client_secret: kommoClientSecret.trim(),
          access_token: kommoAccessToken.trim(),
          subdomain: kommoSubdomain.trim(),
        },
      },
      { onSuccess: cancelEditKommo }
    );
  }

  function handleSaveConnection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedClientId || !editingProvider || !accountId.trim()) return;
    const existing = connectionFor(editingProvider);
    const payload = {
      provider: editingProvider,
      external_account_id: accountId.trim(),
      external_parent_id: parentId.trim() || null,
      display_name: displayName.trim() || null,
    };
    const onSuccess = () => cancelEdit();
    if (existing) {
      updateConnection.mutate(
        { clientId: selectedClientId, connectionId: existing.id, payload },
        { onSuccess },
      );
    } else {
      createConnection.mutate({ clientId: selectedClientId, payload }, { onSuccess });
    }
  }

  function handleToggleStatus(connection: PerformanceConnection) {
    if (!selectedClientId) return;
    updateConnection.mutate({
      clientId: selectedClientId,
      connectionId: connection.id,
      payload: { status: connection.status === "active" ? "inactive" : "active" },
    });
  }

  function handleProviderSync(provider: PerformanceProvider) {
    if (!selectedClientId) return;
    setSyncFeedback("");
    requestSync.mutate(
      { clientId: selectedClientId, provider },
      {
        onSuccess: (run) => setSyncFeedback(
          `Sync de ${PROVIDER_META[provider].label} enfileirado (${run.status}). O worker processa fora da requisição.`,
        ),
      },
    );
  }

  const savingConnection = createConnection.isPending || updateConnection.isPending;

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "9px 12px",
    borderRadius: "8px",
    border: "1px solid var(--border, rgba(255,255,255,0.15))",
    background: "var(--bg-inset, #0F172A)",
    color: "var(--text, #F8FAFC)",
    fontSize: "13px",
    boxSizing: "border-box",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32, gridColumn: "1 / -1", width: "100%" }}>
      {/* Ambiente (flags reais, somente leitura) */}
      {scope !== "client" && (
        <section>
          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, display: "flex", alignItems: "center", gap: 8, color: "var(--text, #F8FAFC)" }}>
              <Server size={18} /> Ambiente EverGreen
            </h3>
            <p style={{ color: "var(--text-muted, #94A3B8)", fontSize: 14, margin: "4px 0 0 0" }}>
              Estado real das credenciais deste ambiente ({envStatus?.app_env ?? "..."}). Configuração é feita por
              variáveis de ambiente no deploy, nunca pela interface.
            </p>
          </div>
          <div className="health-list">
            <div className="health-row">
              <Cloud size={18} />
              <span>
                Storage de arquivos (S3) <small style={{ color: "var(--text-faint, #64748B)" }}>· STORAGE_S3_*</small>
                {/* Nomear a variável ausente: no Railway, API e worker são
                    serviços com variáveis separadas, e o caso comum é ela
                    existir num e faltar no outro. */}
                <MissingVars names={envStatus?.storage_missing_vars} />
              </span>
              {envStatus ? <EnvStatusPill configured={envStatus.storage_configured} /> : <StatusPill variant="paused">...</StatusPill>}
            </div>
            <div className="health-row">
              <KeyRound size={18} />
              <span>
                Login com Google (OAuth) <small style={{ color: "var(--text-faint, #64748B)" }}>· GOOGLE_OAUTH_*</small>
                <MissingVars names={envStatus?.google_oauth_missing_vars} />
              </span>
              {envStatus ? <EnvStatusPill configured={envStatus.google_oauth_configured} /> : <StatusPill variant="paused">...</StatusPill>}
            </div>
          </div>
        </section>
      )}

      {/* Conexões por cliente */}
      {scope !== "environment" && (
        <section>
          <div style={{ marginBottom: 16, display: "flex", alignItems: "flex-end", gap: 16, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 260 }}>
              <h3 style={{ fontSize: 18, fontWeight: 600, display: "flex", alignItems: "center", gap: 8, color: "var(--text, #F8FAFC)" }}>
                <Activity size={18} /> Contas conectadas
              </h3>
              <p style={{ color: "var(--text-muted, #94A3B8)", fontSize: 14, margin: "4px 0 0 0" }}>
                Contas de mídia e fontes de dados deste workspace — cliente ou a própria EG.
              </p>
            </div>
            {!clientId && (
              <label className="form-grid" style={{ minWidth: 220 }}>
                Cliente
                <select
                  className="status-select"
                  style={{ maxWidth: "none" }}
                  value={selectedClientId ?? ""}
                  onChange={(event) => setSelectedClientId(event.target.value || null)}
                >
                  <option value="">— selecione —</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>{client.name}</option>
                  ))}
                </select>
              </label>
            )}
          </div>

          {!selectedClient && <div className="empty-state compact">Selecione um cliente para gerenciar conexões.</div>}

          {selectedClient && (
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
                {/* Kommo CRM */}
                <article className="surface" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <KommoIcon size={20} />
                      <h4 style={{ margin: 0, fontSize: 15, color: "var(--text, #F8FAFC)" }}>Kommo CRM</h4>
                    </div>
                    <StatusPill variant={kommoConfig?.configured ? "connected" : "not_configured"}>
                      {kommoConfig?.configured ? "Configurado" : "Não configurado"}
                    </StatusPill>
                  </div>

                  {loadingKommo && <div style={{ fontSize: 12, color: "var(--text-dim)" }}>Carregando...</div>}

                  {!isEditingKommo && kommoConfig && (
                    <div style={{ fontSize: 12, color: "var(--text-muted)", display: "grid", gap: 4 }}>
                      {kommoConfig.configured ? (
                        <>
                          <div>Subdomínio: <strong>{kommoConfig.subdomain}</strong></div>
                          <div style={{ color: "var(--text-muted)", marginTop: 8 }}>
                            Credenciais salvas e seguras no banco de dados.
                          </div>
                        </>
                      ) : (
                        <div>O Kommo não está configurado para a organização deste cliente.</div>
                      )}
                    </div>
                  )}

                  {isEditingKommo && (
                    <form onSubmit={handleSaveKommo} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                      <div>
                        <label style={{ display: "block", fontSize: 12, marginBottom: 4, color: "var(--text-muted)" }}>Client ID</label>
                        <input
                          value={kommoClientId}
                          onChange={(e) => setKommoClientId(e.target.value)}
                          style={inputStyle}
                          required
                        />
                      </div>
                      <div>
                        <label style={{ display: "block", fontSize: 12, marginBottom: 4, color: "var(--text-muted)" }}>Client Secret</label>
                        <input
                          value={kommoClientSecret}
                          onChange={(e) => setKommoClientSecret(e.target.value)}
                          type="password"
                          style={inputStyle}
                          required
                        />
                      </div>
                      <div>
                        <label style={{ display: "block", fontSize: 12, marginBottom: 4, color: "var(--text-muted)" }}>Access Token</label>
                        <input
                          value={kommoAccessToken}
                          onChange={(e) => setKommoAccessToken(e.target.value)}
                          type="password"
                          style={inputStyle}
                          required
                        />
                      </div>
                      <div>
                        <label style={{ display: "block", fontSize: 12, marginBottom: 4, color: "var(--text-muted)" }}>Subdomínio Kommo</label>
                        <input
                          value={kommoSubdomain}
                          onChange={(e) => setKommoSubdomain(e.target.value)}
                          placeholder="exemplo-empresa"
                          style={inputStyle}
                          required
                        />
                      </div>
                      <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                        <button className="primary-button" type="submit" disabled={setupKommo.isPending} style={{ flex: 1, padding: 8, fontSize: 13 }}>
                          {setupKommo.isPending ? "Salvando..." : "Salvar"}
                        </button>
                        <button className="ghost-button" type="button" onClick={cancelEditKommo} style={{ padding: 8, fontSize: 13 }}>
                          Cancelar
                        </button>
                      </div>
                    </form>
                  )}

                  {!isEditingKommo && !loadingKommo && (
                    <div style={{ marginTop: "auto", display: "flex", gap: 8, paddingTop: 8 }}>
                      <button className="mini-button" type="button" onClick={startEditKommo}>
                        {kommoConfig?.configured ? <PenLine size={13} /> : <Plus size={13} />}
                        {kommoConfig?.configured ? "Editar credenciais" : "Configurar"}
                      </button>
                    </div>
                  )}
                </article>

                {/* Google providers (performance_connections reais) */}
                {PROVIDERS.map((provider) => {
                  const meta = PROVIDER_META[provider];
                  const Icon = meta.icon;
                  const providerConnections = connectionsFor(provider);
                  const connection = providerConnections[0] ?? null;
                  const hasActive = providerConnections.some((item) => item.status === "active");
                  const isEditing = editingProvider === provider;
                  return (
                    <article key={provider} className="surface" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                          <span style={{ display: "inline-flex", opacity: hasActive ? 1 : 0.5 }}>
                            <Icon size={20} />
                          </span>
                          <h4 style={{ margin: 0, fontSize: 15, color: "var(--text, #F8FAFC)" }}>{meta.label}</h4>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          {providerConnections.length > 1 && (
                            <span className="demo-badge">{providerConnections.length} contas</span>
                          )}
                          <ConnectionStatusPill connection={connection} />
                        </div>
                      </div>

                      <IntegrationGuide provider={provider} label={meta.label} />

                      {loadingConnections && <div style={{ fontSize: 12, color: "var(--text-dim)" }}>Carregando...</div>}

                      {!isEditing && providerConnections.map((item) => (
                        <div
                          key={item.id}
                          style={{
                            fontSize: 12,
                            color: "var(--text-muted)",
                            display: "grid",
                            gap: 4,
                            paddingTop: providerConnections.length > 1 ? 8 : 0,
                            borderTop: providerConnections.length > 1 ? "1px solid var(--border)" : undefined,
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                            <span>
                              {meta.tokenConnect
                                ? "Token configurado e cifrado"
                                : <>{meta.accountLabel}: <strong>{item.external_account_id}</strong></>}
                            </span>
                            {providerConnections.length > 1 && <ConnectionStatusPill connection={item} />}
                          </div>
                          {item.external_parent_id && <div>{meta.parentLabel ?? "Conta-pai"}: <strong>{item.external_parent_id}</strong></div>}
                          {item.display_name && <div>Nome: <strong>{item.display_name}</strong></div>}
                          <div>
                            Último sync:{" "}
                            <strong>{item.last_synced_at ? formatDateTime(item.last_synced_at) : "nunca"}</strong>
                          </div>
                          {item.last_error_message && (
                            <div style={{ color: "var(--danger-soft)" }}>Erro: {item.last_error_message}</div>
                          )}
                          {providerConnections.length > 1 && (
                            <button
                              className="mini-button"
                              type="button"
                              style={{ width: "fit-content", marginTop: 4 }}
                              onClick={() => handleToggleStatus(item)}
                              disabled={updateConnection.isPending}
                            >
                              {item.status === "active" ? "Desativar esta conta" : "Reativar esta conta"}
                            </button>
                          )}
                        </div>
                      ))}

                      {!isEditing && providerConnections.length === 0 && (
                        <div style={{ fontSize: 12, color: "var(--text-dim)" }}>
                          {meta.oauthConnect
                            ? `Nenhuma conta ${meta.label} conectada. A conexão exige autorização OAuth — clique em "Conectar via OAuth" abaixo.`
                            : meta.tokenConnect
                              ? `${meta.label} ainda não conectado. Siga o guia acima para gerar o token e cole-o aqui.`
                              : `Nenhuma conta ${meta.label} mapeada para ${selectedClient.name}.`}
                        </div>
                      )}

                      {isEditing && meta.tokenConnect && (
                        <form onSubmit={handleSaveProviderToken} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                          <div>
                            <label style={{ display: "block", fontSize: 12, marginBottom: 4, color: "var(--text-muted)" }}>
                              {meta.tokenConnect.label}
                            </label>
                            <input
                              type="password"
                              value={providerToken}
                              onChange={(event) => setProviderToken(event.target.value)}
                              placeholder={meta.tokenConnect.placeholder}
                              style={inputStyle}
                              required
                            />
                            <p style={{ fontSize: 11, color: "var(--text-faint)", margin: "6px 0 0" }}>
                              O token é gravado cifrado e nunca é exibido de volta. Para trocar, basta colar um novo.
                            </p>
                          </div>
                          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                            <button className="primary-button" type="submit" disabled={saveProviderToken.isPending} style={{ flex: 1, padding: 8, fontSize: 13 }}>
                              {saveProviderToken.isPending ? "Salvando..." : "Salvar token"}
                            </button>
                            <button className="ghost-button" type="button" onClick={cancelEdit} style={{ padding: 8, fontSize: 13 }}>
                              Cancelar
                            </button>
                          </div>
                          {saveProviderToken.isError && (
                            <div className="notice error" style={{ fontSize: 12 }}>
                              {(saveProviderToken.error as Error)?.message ?? "Não foi possível salvar o token."}
                            </div>
                          )}
                        </form>
                      )}

                      {isEditing && !meta.oauthConnect && !meta.tokenConnect && (
                        <form onSubmit={handleSaveConnection} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                          <div>
                            <label style={{ display: "block", fontSize: 12, marginBottom: 4, color: "var(--text-muted)" }}>{meta.accountLabel}</label>
                            <input
                              value={accountId}
                              onChange={(event) => setAccountId(event.target.value)}
                              placeholder={meta.accountPlaceholder}
                              style={inputStyle}
                              required
                            />
                          </div>
                          {meta.parentLabel && (
                            <div>
                              <label style={{ display: "block", fontSize: 12, marginBottom: 4, color: "var(--text-muted)" }}>{meta.parentLabel}</label>
                              <input
                                value={parentId}
                                onChange={(event) => setParentId(event.target.value)}
                                placeholder={meta.parentPlaceholder}
                                style={inputStyle}
                              />
                            </div>
                          )}
                          <div>
                            <label style={{ display: "block", fontSize: 12, marginBottom: 4, color: "var(--text-muted)" }}>Nome de exibição</label>
                            <input
                              value={displayName}
                              onChange={(event) => setDisplayName(event.target.value)}
                              placeholder={`${meta.label} — ${selectedClient.name}`}
                              style={inputStyle}
                            />
                          </div>
                          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                            <button className="primary-button" type="submit" disabled={savingConnection} style={{ flex: 1, padding: 8, fontSize: 13 }}>
                              {savingConnection ? "Salvando..." : "Salvar conexão"}
                            </button>
                            <button className="ghost-button" type="button" onClick={cancelEdit} style={{ padding: 8, fontSize: 13 }}>
                              Cancelar
                            </button>
                          </div>
                        </form>
                      )}

                      {!isEditing && (
                        <div style={{ marginTop: "auto", display: "flex", gap: 8, flexWrap: "wrap", paddingTop: 8 }}>
                          {meta.oauthConnect ? (
                            <a
                              className="mini-button"
                              href={apiUrl(`/workspaces/${selectedClient.id}/performance/connections/${provider}/authorize`)}
                            >
                              <PenLine size={13} />
                              {connection ? "Reconectar via OAuth" : "Conectar via OAuth"}
                            </a>
                          ) : meta.tokenConnect ? (
                            <button className="mini-button" type="button" onClick={() => { setEditingProvider(provider); setProviderToken(""); }}>
                              {connection ? <PenLine size={13} /> : <Plus size={13} />}
                              {connection ? "Trocar token" : "Conectar com token"}
                            </button>
                          ) : (
                            <button className="mini-button" type="button" onClick={() => startEdit(provider)}>
                              {connection ? <PenLine size={13} /> : <Plus size={13} />}
                              {connection ? "Editar" : "Conectar"}
                            </button>
                          )}
                          {connection && providerConnections.length === 1 && (
                            <button className="mini-button" type="button" onClick={() => handleToggleStatus(connection)} disabled={updateConnection.isPending}>
                              {connection.status === "active" ? "Desativar" : "Reativar"}
                            </button>
                          )}
                          {hasActive && (
                            <button
                              className="mini-button approve"
                              type="button"
                              onClick={() => handleProviderSync(provider)}
                              disabled={requestSync.isPending}
                            >
                              <RefreshCw size={13} />
                              {providerConnections.length > 1 ? "Sincronizar todas" : "Sincronizar"}
                            </button>
                          )}
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            </div>
          )}

          {syncFeedback && <div className="form-success" style={{ marginTop: 12 }}>{syncFeedback}</div>}
        </section>
      )}

      {/* --- Plataformas de Oportunidades & Freelancers (Radar B2B) - Apenas gestão interna EG --- */}
      {scope !== "client" && (
        <section className="section-card" style={{ marginTop: 24 }}>
          <header className="section-header">
            <Briefcase size={20} color="var(--brand-accent)" />
            <div>
              <h3>Plataformas de Oportunidades & Freelancers (Radar B2B)</h3>
            <p className="section-desc">
              Status das integrações, RSS customizados e lançamento automático de gastos (assinaturas SaaS) no Financeiro.
            </p>
          </div>
        </header>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16, marginTop: 16 }}>
          {oppPlatforms.map((item) => {
            const isEditingThis = editingPlatformKey === item.platform_key;
            const costFormatted = item.monthly_cost_cents > 0
              ? (item.monthly_cost_cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) + "/mês"
              : "Gratuito";

            const statusVariant = item.status === "active" ? "connected" : item.status === "paused" ? "paused" : "not_configured";
            const statusLabelText = item.status === "active" ? "Varredura Ativa" : item.status === "paused" ? "Requer Assinatura / Token" : "Não Configurado";

            return (
              <article
                key={item.platform_key}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  padding: 16,
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h4 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 600 }}>{item.platform_name}</h4>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>{item.notes || "Plataforma B2B"}</span>
                  </div>
                  <StatusPill variant={statusVariant}>{statusLabelText}</StatusPill>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.8rem", color: "var(--text-dim)" }}>
                  <span style={{ background: "var(--bg-inset)", padding: "2px 8px", borderRadius: 4, color: "var(--brand-accent)", fontWeight: 600 }}>
                    Custo: {costFormatted}
                  </span>
                  {item.rss_url && <span style={{ color: "#10b981" }}>✓ RSS Customizado Salvo</span>}
                </div>

                {isEditingThis ? (
                  <form onSubmit={handleSavePlatformConfig} style={{ display: "flex", flexDirection: "column", gap: 10, background: "var(--bg-inset)", padding: 12, borderRadius: 8, border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <label style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>Status da Varredura</label>
                      <select
                        value={editStatus}
                        onChange={(e) => setEditStatus(e.target.value as any)}
                        style={{ padding: 6, borderRadius: 6, background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }}
                      >
                        <option value="active">Ativo (Varredura Ligada)</option>
                        <option value="paused">Pausado (Requer Assinatura / Token)</option>
                        <option value="not_configured">Não Configurado</option>
                      </select>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <label style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>URL do Feed RSS Customizado / Busca</label>
                      <input
                        type="text"
                        value={editRssUrl}
                        onChange={(e) => setEditRssUrl(e.target.value)}
                        placeholder="https://plataforma.com/rss.xml ou busca salva"
                        style={{ padding: 6, borderRadius: 6, background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", fontSize: "0.8rem" }}
                      />
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <label style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>Custo mensal observado (em R$)</label>
                      <input
                        type="number"
                        step="0.01"
                        value={editMonthlyCost}
                        onChange={(e) => setEditMonthlyCost(Number(e.target.value))}
                        placeholder="Ex: 59.90 para R$ 59,90/mês"
                        style={{ padding: 6, borderRadius: 6, background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", fontSize: "0.8rem" }}
                      />
                    </div>

                    <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                      <button className="primary-button" type="submit" disabled={savingPlatform} style={{ flex: 1, padding: 6, fontSize: 12 }}>
                        {savingPlatform ? "Salvando..." : "Salvar configuração"}
                      </button>
                      <button className="ghost-button" type="button" onClick={() => setEditingPlatformKey(null)} style={{ padding: 6, fontSize: 12 }}>
                        Cancelar
                      </button>
                    </div>
                  </form>
                ) : (
                  <button
                    className="mini-button"
                    type="button"
                    onClick={() => {
                      setEditingPlatformKey(item.platform_key);
                      setEditRssUrl(item.rss_url || "");
                      setEditStatus(item.status);
                      setEditMonthlyCost(item.monthly_cost_cents / 100);
                    }}
                    style={{ marginTop: "auto" }}
                  >
                    <PenLine size={13} /> Configurar RSS e custo
                  </button>
                )}
              </article>
            );
          })}
        </div>
      </section>
      )}

      {/* Decisao 14: onde as pecas do Estudio podem ser publicadas. O id
          aqui ja e o do workspace — a rota de conexoes usa o mesmo. */}
      {selectedClientId && <CmsTargetsManager workspaceId={selectedClientId} />}
    </div>
  );
}