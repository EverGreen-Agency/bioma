import { useState } from "react";
import { MessageSquare, Send, Server, ShieldCheck, Zap } from "lucide-react";
import { SectionHeader } from "./shared";
import { StatusPill, type StatusPillVariant } from "./StatusPill";
import { WhatsAppBrandIcon } from "./icons/BrandIcons";
import {
  useSaveWhatsAppProvider,
  useSendWhatsAppMessage,
  useWhatsAppLogs,
  useWhatsAppProviders,
} from "../hooks/useBiomaApi";
import type { WhatsAppProviderType } from "../lib/api";

const LOG_STATUS_VARIANT: Record<string, StatusPillVariant> = {
  sent: "connected",
  delivered: "connected",
  read: "connected",
  failed: "error",
  queued: "paused",
};

const providerOptions: Array<{
  type: WhatsAppProviderType;
  name: string;
  badge: string;
  description: string;
}> = [
  {
    type: "evolution",
    name: "Evolution API (Baileys)",
    badge: "Auto-hospedado",
    description: "Instância open-source via Docker. Excelente para autonomia, controle de sessões e alta vazão.",
  },
  {
    type: "meta_cloud",
    name: "Meta Cloud API Oficial",
    badge: "Oficial Meta",
    description: "Conexão direta com a Graph API Oficial da Meta. Envio seguro por modelos (Templates) pré-aprovados.",
  },
  {
    type: "zapi",
    name: "Z-API / API Não Oficial",
    badge: "SaaS / API Rest",
    description: "Provedor em nuvem rápido para envio de mensagens, webhooks de recebimento e fotos/arquivos.",
  },
  {
    type: "custom",
    name: "Webhooks / Provider Customizado",
    badge: "Custom",
    description: "Endpoint HTTP arbitrário para integração com sistemas legados ou gateways proprietários.",
  },
];

export function WhatsAppManager({ workspaceId }: { workspaceId: string }) {
  const { data: providers, isLoading: loadingProviders } = useWhatsAppProviders(workspaceId);
  const { data: logs } = useWhatsAppLogs(workspaceId);
  const saveMutation = useSaveWhatsAppProvider();
  const sendMutation = useSendWhatsAppMessage();

  const [selectedProvider, setSelectedProvider] = useState<WhatsAppProviderType>("evolution");
  const [apiUrl, setApiUrl] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [instanceName, setInstanceName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");

  const [testNumber, setTestNumber] = useState("");
  const [testMessage, setTestMessage] = useState("Olá! Esta é uma mensagem de teste do Bioma EverGreen AI.");
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const activeProviderConfig = providers?.find((p) => p.provider_type === selectedProvider);

  function handleSaveProvider(e: React.FormEvent) {
    e.preventDefault();
    setFeedback(null);
    saveMutation.mutate(
      {
        workspaceId,
        payload: {
          provider_type: selectedProvider,
          api_url: apiUrl || undefined,
          api_token: apiToken || undefined,
          instance_name: instanceName || undefined,
          phone_number: phoneNumber || undefined,
          status: "active",
        },
      },
      {
        onSuccess: () => {
          setFeedback({ type: "success", text: `Provedor ${selectedProvider.toUpperCase()} salvo com sucesso!` });
        },
        onError: (err) => {
          setFeedback({ type: "error", text: err.message || "Erro ao salvar credenciais." });
        },
      }
    );
  }

  function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!testNumber || !testMessage) return;
    setFeedback(null);
    sendMutation.mutate(
      {
        workspaceId,
        payload: {
          provider_type: selectedProvider,
          to_number: testNumber,
          message_text: testMessage,
        },
      },
      {
        onSuccess: (res) => {
          setFeedback({
            type: "success",
            text: `Mensagem disparada com sucesso via ${(res.provider_type || selectedProvider).toUpperCase()}! Log ID: ${res.id}`,
          });
        },
        onError: (err) => {
          setFeedback({ type: "error", text: err.message || "Erro ao disparar mensagem." });
        },
      }
    );
  }

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "10px 14px",
    borderRadius: "8px",
    border: "1px solid var(--border, rgba(255,255,255,0.15))",
    background: "var(--bg-inset, #0F172A)",
    color: "var(--text, #F8FAFC)",
    fontSize: "14px",
    outline: "none",
    boxSizing: "border-box",
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: "12px",
    fontWeight: 500,
    color: "var(--text-muted, #94A3B8)",
    marginBottom: "6px",
  };

  return (
    <div className="whatsapp-manager-container" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <article className="surface" style={{ padding: "24px" }}>
        <SectionHeader
          eyebrow="Multi-provedor WhatsApp"
          title="Arquitetura Pluggable (Evolution, Meta Cloud, Z-API)"
          icon={WhatsAppBrandIcon}
        />

        {feedback && (
          <div className={`notice ${feedback.type === "error" ? "error" : "success"}`} style={{ margin: "16px 0" }}>
            {feedback.text}
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
            gap: "14px",
            margin: "20px 0 24px 0",
          }}
        >
          {providerOptions.map((opt) => {
            const isSelected = selectedProvider === opt.type;
            const isConnected = providers?.some((p) => p.provider_type === opt.type);
            return (
              <button
                key={opt.type}
                type="button"
                onClick={() => {
                  setSelectedProvider(opt.type);
                  const existing = providers?.find((p) => p.provider_type === opt.type);
                  if (existing) {
                    setApiUrl(existing.api_url || "");
                    setInstanceName(existing.instance_name || "");
                    setPhoneNumber(existing.phone_number || "");
                  }
                }}
                style={{
                  textAlign: "left",
                  padding: "16px",
                  borderRadius: "10px",
                  border: isSelected ? "2px solid var(--brand-accent, #3B82F6)" : "1px solid var(--border, rgba(255,255,255,0.1))",
                  background: isSelected ? "var(--bg-inset, rgba(59, 130, 246, 0.08))" : "var(--surface, #1E293B)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px" }}>
                    <strong style={{ fontSize: "14px", color: isSelected ? "var(--brand-accent, #3B82F6)" : "var(--text, #F8FAFC)", fontWeight: 600 }}>
                      {opt.name}
                    </strong>
                    <StatusPill variant="paused">{opt.badge}</StatusPill>
                  </div>
                  <p style={{ fontSize: "12px", color: "var(--text-muted, #94A3B8)", marginTop: "8px", lineHeight: "1.4" }}>
                    {opt.description}
                  </p>
                </div>
                <div style={{ marginTop: "12px" }}>
                  <StatusPill variant={isConnected ? "connected" : "not_configured"}>
                    {isConnected ? "Conectado no Workspace" : "Não conectado"}
                  </StatusPill>
                </div>
              </button>
            );
          })}
        </div>

        <form onSubmit={handleSaveProvider} style={{ display: "flex", flexDirection: "column", gap: "18px", paddingTop: "16px", borderTop: "1px solid var(--glass-border, rgba(255,255,255,0.1))" }}>
          <h4 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text, #F8FAFC)", margin: 0 }}>
            Configurar Conexão: <span style={{ color: "var(--brand-accent, #3B82F6)" }}>{selectedProvider.toUpperCase()}</span>
          </h4>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div>
              <label style={labelStyle}>URL Base da API (Endpoint)</label>
              <input
                type="text"
                placeholder="https://api.evolution.empresa.com"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Token / Chave de API</label>
              <input
                type="password"
                placeholder="••••••••••••••••"
                value={apiToken}
                onChange={(e) => setApiToken(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Nome da Instância / Phone Number ID</label>
              <input
                type="text"
                placeholder="instance_eg_prod ou 10982736"
                value={instanceName}
                onChange={(e) => setInstanceName(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Número WhatsApp Conectado</label>
              <input
                type="text"
                placeholder="+5511999998888"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                style={inputStyle}
              />
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
            <button className="primary-button" type="submit" disabled={saveMutation.isPending}>
              <Server size={15} />
              {saveMutation.isPending ? "Salvando..." : "Salvar Configuração de Provedor"}
            </button>
          </div>
        </form>
      </article>

      <article className="surface" style={{ padding: "24px" }}>
        <SectionHeader eyebrow="Disparo Experimental" title="Testar Envio de Mensagem WhatsApp" icon={Send} />
        <form onSubmit={handleSendMessage} style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "16px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "16px" }}>
            <div>
              <label style={labelStyle}>Número Destinatário (com DDD)</label>
              <input
                type="text"
                placeholder="5511999998888"
                value={testNumber}
                onChange={(e) => setTestNumber(e.target.value)}
                style={inputStyle}
                required
              />
            </div>
            <div>
              <label style={labelStyle}>Conteúdo da Mensagem</label>
              <input
                type="text"
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                style={inputStyle}
                required
              />
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button className="secondary-button" type="submit" disabled={sendMutation.isPending}>
              <Zap size={15} />
              {sendMutation.isPending ? "Enviando..." : `Disparar via ${selectedProvider.toUpperCase()}`}
            </button>
          </div>
        </form>
      </article>

      <article className="surface" style={{ padding: "24px" }}>
        <SectionHeader eyebrow="Audit Log" title="Histórico de Mensagens WhatsApp" icon={ShieldCheck} />
        {!logs || logs.length === 0 ? (
          <p style={{ color: "var(--text-muted, #94A3B8)", fontSize: "13px", padding: "16px 0", margin: 0 }}>Nenhuma mensagem disparada no histórico deste workspace.</p>
        ) : (
          <div className="table-list" style={{ marginTop: "12px" }}>
            {logs.map((log) => (
              <div className="table-row" key={log.id}>
                <strong style={{ color: "var(--text, #F8FAFC)" }}>{log.to_number}</strong>
                <span>{log.provider_type.toUpperCase()} ({log.message_type})</span>
                <span>{new Date(log.sent_at).toLocaleString("pt-BR")}</span>
                <StatusPill variant={LOG_STATUS_VARIANT[log.status] ?? "paused"}>{log.status}</StatusPill>
              </div>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}
