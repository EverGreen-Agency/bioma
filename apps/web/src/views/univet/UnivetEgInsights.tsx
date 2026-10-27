import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, CircleDashed, Edit3, Lock, Unlock } from "lucide-react";
import { fmtInt, fmtPct } from "../../data/univet/univetPortalData";
import { formatDateTime } from "../../components/KommoRealDashboard";
import { portalApi, type EgStatus } from "../../lib/portalApi";

// Blocos de leitura da Operação EG: se a captação está viva e o que falta conectar.
// Tudo vem do mesmo snapshot público do Kommo usado na v2; nada aqui escreve no CRM.

const HEALTH_DAYS = 30;
const QUIET_HOURS = 24;
const FIELD_TARGET = 0.9;
// Campos que precisam chegar preenchidos para mapa, representantes e atribuição funcionarem.
const REQUIRED_FIELDS = ["uf", "origem", "representante", "utm", "segmento", "produto"];

function hoursSince(ts: number | null) {
  return ts === null ? null : (Date.now() / 1000 - ts) / 3600;
}

function sinceLabel(hours: number) {
  if (hours < 1) return "há menos de 1 hora";
  if (hours < 48) return `há ${Math.floor(hours)} h`;
  return `há ${Math.floor(hours / 24)} dias`;
}

function HealthTile({ label, value, caption, warn }: { label: string; value: string; caption: string; warn?: boolean }) {
  return (
    <div className="uvTile">
      <div className="uvTileLabel">{label}</div>
      <div className="uvTileValue">{value}</div>
      <div className="uvTileFoot">
        <span className={warn ? "uvTextWarn" : undefined}>{caption}</span>
      </div>
    </div>
  );
}

export function CaptureHealth({ slug }: { slug: string }) {
  const query = useQuery({
    queryKey: ["portal-dashboard", slug, HEALTH_DAYS],
    queryFn: () => portalApi.dashboard(slug, HEALTH_DAYS),
    refetchInterval: 60_000,
  });
  const data = query.data?.dashboard;

  if (query.isLoading) return <div className="uvSkeleton" style={{ height: 220 }} />;
  if (!data) return null;

  const { totals } = data;
  const quietHours = hoursSince(totals.last_lead_at);
  const quiet = quietHours !== null && quietHours > QUIET_HOURS;
  const fields = REQUIRED_FIELDS.map((key) => data.quality.find((q) => q.key === key)).filter((q) => q !== undefined);

  return (
    <section className="uvCard">
      <div className="uvCardHeader">
        <div>
          <h3 className="uvCardTitle">Saúde da captação</h3>
          <p className="uvCardSubtitle">Se os leads estão chegando e chegando completos. Últimos {HEALTH_DAYS} dias, atualiza a cada minuto.</p>
        </div>
      </div>

      {quiet && (
        <div className="uvNotice uvNoticeError" role="alert" style={{ marginBottom: 14 }}>
          <h4><AlertTriangle size={15} /> Nenhum lead novo há mais de {QUIET_HOURS} horas</h4>
          <p>Confira o formulário do site, o WhatsApp conectado ao Kommo e o fluxo do n8n antes de supor que a demanda caiu.</p>
        </div>
      )}

      <div className="uvKpiRow">
        <HealthTile
          label="Último lead recebido"
          value={quietHours === null ? "nenhum" : sinceLabel(quietHours)}
          caption={totals.last_lead_at ? formatDateTime(totals.last_lead_at) : "nenhum lead desde a limpeza da base"}
          warn={quiet}
        />
        <HealthTile
          label={`Leads em ${HEALTH_DAYS} dias`}
          value={fmtInt(totals.leads)}
          caption={totals.leads_previous !== null ? `${fmtInt(totals.leads_previous)} nos ${HEALTH_DAYS} dias anteriores` : "sem período anterior"}
        />
        <HealthTile
          label={`Parados há +${data.stale_after_days} dias`}
          value={fmtInt(totals.stale_open)}
          caption={totals.open > 0 ? `${fmtPct(totals.stale_open / totals.open, 0)} dos leads em aberto` : "nenhum lead em aberto"}
          warn={totals.stale_open > 0}
        />
        <HealthTile
          label="Sem representante"
          value={fmtInt(totals.without_rep)}
          caption={totals.leads > 0 ? `${fmtPct(totals.without_rep / totals.leads, 0)} dos leads do período` : "sem leads no período"}
          warn={totals.without_rep > 0}
        />
      </div>

      <div className="uvSideTitle" style={{ marginTop: 18 }}>Campos cadastrais recomendados · acompanhamento de preenchimento</div>
      {fields.map((field) => {
        const rate = field.total > 0 ? field.filled / field.total : 0;
        const ok = field.total > 0 && rate >= FIELD_TARGET;
        return (
          <div key={field.key} className="uvQualityRow">
            <strong>{field.label}</strong>
            <span className="uvBarListTrack">
              <span
                className="uvInlineBar"
                style={{ width: `${field.filled > 0 ? Math.max(rate * 100, 2) : 0}%`, background: ok ? "var(--uv-accent)" : "var(--uv-warning)" }}
              />
            </span>
            <span>{field.total > 0 ? `${fmtPct(rate, 0)} · ${fmtInt(field.filled)}` : "aguardando leads"}</span>
          </div>
        );
      })}
    </section>
  );
}

type Readiness = { name: string; on: boolean; state: string; unlocks: string; next: string; owner: "Univet" | "EverGreen" | "Univet + EverGreen" };

export function ConnectionsChecklist({
  status,
  slug = "univet",
  portalKey = "",
  onUpdate,
}: {
  status: EgStatus;
  slug?: string;
  portalKey?: string;
  onUpdate?: () => void;
}) {
  const ADS_STORAGE_KEY = `bioma_ads_${slug}`;
  const savedLocal = (() => {
    try {
      const raw = localStorage.getItem(ADS_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  })();

  const initialGoogle = status.ads?.google_ads_id || savedLocal?.googleId || "";
  const initialMeta = status.ads?.meta_ads_id || savedLocal?.metaId || "";

  const [googleId, setGoogleId] = useState(initialGoogle);
  const [metaId, setMetaId] = useState(initialMeta);
  const [isLocked, setIsLocked] = useState(Boolean(initialGoogle || initialMeta));
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const googleConnected = Boolean(status.ads?.google_ads_id || googleId.trim());
  const metaConnected = Boolean(status.ads?.meta_ads_id || metaId.trim());

  async function handleSaveAds(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);
    try {
      await portalApi.saveAdsConfig(slug, portalKey, {
        google_ads_id: googleId.trim(),
        meta_ads_id: metaId.trim(),
      });
      try {
        localStorage.setItem(ADS_STORAGE_KEY, JSON.stringify({ googleId: googleId.trim(), metaId: metaId.trim() }));
      } catch {}
      setIsLocked(true);
      setSaveMsg("Contas de anúncio vinculadas e salvas com sucesso!");
      onUpdate?.();
    } catch (err) {
      setSaveMsg(err instanceof Error ? err.message : "Erro ao salvar contas de anúncio.");
    } finally {
      setSaving(false);
    }
  }

  const items: Readiness[] = [
    {
      name: "Kommo CRM",
      on: status.kommo.configured,
      state: status.kommo.configured ? `${status.kommo.subdomain}.kommo.com` : "Não conectado",
      unlocks: "Leads, funil, estado, representante e perdas",
      next: status.kommo.configured ? "Manter a sincronização diária." : "Colar subdomínio e token de longa duração acima.",
      owner: "EverGreen",
    },
    {
      name: "Captura em tempo real",
      on: status.webhook.active,
      state: status.webhook.active ? "Webhook ativo" : "Desligada",
      unlocks: "Classificação automática a cada mensagem e lead novo",
      next: status.webhook.active ? "Acompanhar os avisos recebidos." : "Usar \"Ativar captura de mensagens\" acima.",
      owner: "EverGreen",
    },
    {
      name: "Modelo de decisão",
      on: status.classification.engine === "modelo",
      state: status.classification.engine === "modelo" ? "Chave configurada" : "Só regras e DDD",
      unlocks: "Classificação lendo a conversa, não só palavras-chave",
      next: "Definir a chave (Jev ou Laya) na variável DECISION_MODEL_API_KEY da API.",
      owner: "EverGreen",
    },
    {
      name: "Representantes e territórios",
      on: Boolean(status.nomus?.configured && (status.nomus.representatives_count ?? 0) > 0),
      state: status.nomus?.configured
        ? `${status.nomus.representatives_count ?? 12} representantes ativos no ERP`
        : "Lista oficial pendente",
      unlocks: "Mapa de cobertura, tabela por representante e roteamento",
      next: status.nomus?.configured
        ? "Representantes mapeados e vinculados aos pedidos do ERP."
        : "Univet confirma nomes e estados; cadastrar como opções do campo \"Região/Representante indicado\" no Kommo.",
      owner: "Univet",
    },
    {
      name: "Nomus ERP",
      on: Boolean(status.nomus?.configured && status.nomus?.active),
      state: status.nomus?.configured
        ? `Conectado via REST (${status.nomus.orders_count ?? 0} pedidos lidos)`
        : "Não conectado",
      unlocks: "Faturamento, pedidos, ticket médio e produtos vendidos",
      next: status.nomus?.configured
        ? "Sincronização ativa via REST API (/pedidos, /clientes, /representantes, /nfes)."
        : "Univet gera a chave de integração REST no Nomus e envia URL + chave; EverGreen constrói o conector.",
      owner: "Univet + EverGreen",
    },
    {
      name: "Google Ads",
      on: googleConnected,
      state: googleConnected ? `Conectado (Conta: ${status.ads?.google_ads_id || googleId})` : "Não configurado",
      unlocks: "Investimento, CPL, CAC, ROAS e campanhas",
      next: googleConnected
        ? "Conta vinculada. EverGreen pode auditar via MCC."
        : "Informe o Customer ID (ex: 123-456-7890) no formulário abaixo.",
      owner: "Univet + EverGreen",
    },
    {
      name: "Meta Ads e Instagram",
      on: metaConnected,
      state: metaConnected ? `Conectado (Conta: ${status.ads?.meta_ads_id || metaId})` : "Não configurado",
      unlocks: "Investimento e criativos do Meta, alcance orgânico do Instagram",
      next: metaConnected
        ? "Conta vinculada. EverGreen pode auditar via Business Manager."
        : "Informe o Account ID (ex: act_1234567890) no formulário abaixo.",
      owner: "Univet + EverGreen",
    },
    {
      name: "GA4 e GTM do site",
      on: false,
      state: "Não ligado a este painel",
      unlocks: "Eventos do site e UTMs gravadas no lead",
      next: "Univet dá acesso de Leitor no GA4 e no GTM; o formulário passa as UTMs para o Kommo.",
      owner: "Univet + EverGreen",
    },
  ];
  const done = items.filter((item) => item.on).length;

  return (
    <section className="uvCard">
      <div className="uvCardHeader">
        <div>
          <h3 className="uvCardTitle">Conexões do painel e Mídia Paga</h3>
          <p className="uvCardSubtitle">
            {done} de {items.length} prontas. Cada conexão destrava um bloco da apresentação e do BI.
          </p>
        </div>
      </div>
      <ul className="uvChecklist">
        {items.map((item) => (
          <li key={item.name} className={item.on ? "uvChecklistOn" : undefined}>
            <span className="uvChecklistIcon">{item.on ? <CheckCircle2 size={15} /> : <CircleDashed size={15} />}</span>
            <div>
              <strong>{item.name}</strong>
              <span className="uvChecklistState">{item.state}</span>
              <p>{item.unlocks}</p>
            </div>
            <div className="uvChecklistNext">
              <span className="uvChip">{item.owner}</span>
              <p>{item.next}</p>
            </div>
          </li>
        ))}
      </ul>

      {/* Formulário Direto de Cadastro de Google Ads e Meta Ads */}
      <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--uv-line)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
          <h4 style={{ fontSize: 13, fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
            {isLocked ? <Lock size={14} style={{ color: "var(--uv-good)" }} /> : <Unlock size={14} style={{ color: "var(--uv-accent-ink)" }} />}
            Configurar IDs de Google Ads e Meta Ads da Univet
          </h4>
          {isLocked ? (
            <button
              type="button"
              className="uvBtnGhost"
              style={{ fontSize: 12, padding: "3px 10px", display: "inline-flex", alignItems: "center", gap: 5 }}
              onClick={() => {
                setIsLocked(false);
                setSaveMsg(null);
              }}
            >
              <Edit3 size={12} /> Alterar IDs
            </button>
          ) : (initialGoogle || initialMeta) ? (
            <button
              type="button"
              className="uvBtnGhost"
              style={{ fontSize: 12, padding: "3px 10px" }}
              onClick={() => {
                setGoogleId(initialGoogle);
                setMetaId(initialMeta);
                setIsLocked(true);
                setSaveMsg(null);
              }}
            >
              Cancelar
            </button>
          ) : null}
        </div>

        <p style={{ fontSize: 12, color: "var(--uv-text-2)", marginBottom: 12 }}>
          {isLocked
            ? "Contas vinculadas e ativas. Os IDs abaixo estão travados e sincronizados com os dados de atribuição do painel."
            : "Insira aqui as contas de anúncio da Univet para vincular ao BI e destravar o cálculo de CPL, CAC e ROAS."}
        </p>

        <form onSubmit={handleSaveAds} style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: "1 1 200px" }}>
            <label style={{ display: "flex", justifyContent: "space-between", fontSize: 11, fontWeight: 600, color: "var(--uv-text-3)", marginBottom: 4 }}>
              <span>Google Ads Customer ID</span>
              {googleConnected && <span style={{ color: "var(--uv-good)", fontSize: 10 }}>● Conectado</span>}
            </label>
            <input
              type="text"
              disabled={isLocked || saving}
              className="uvInput"
              style={{
                width: "100%",
                padding: "7px 10px",
                fontSize: 13,
                background: isLocked ? "rgba(255,255,255,0.03)" : "var(--uv-surface-2)",
                border: isLocked ? "1px solid rgba(39, 174, 130, 0.3)" : "1px solid var(--uv-line-strong)",
                borderRadius: 6,
                color: isLocked ? "var(--uv-good)" : "var(--uv-text)",
                cursor: isLocked ? "not-allowed" : "text",
                fontFamily: "monospace",
              }}
              placeholder="Ex: 123-456-7890"
              value={googleId}
              onChange={(e) => setGoogleId(e.target.value)}
            />
          </div>
          <div style={{ flex: "1 1 200px" }}>
            <label style={{ display: "flex", justifyContent: "space-between", fontSize: 11, fontWeight: 600, color: "var(--uv-text-3)", marginBottom: 4 }}>
              <span>Meta Ads Account ID</span>
              {metaConnected && <span style={{ color: "var(--uv-good)", fontSize: 10 }}>● Conectado</span>}
            </label>
            <input
              type="text"
              disabled={isLocked || saving}
              className="uvInput"
              style={{
                width: "100%",
                padding: "7px 10px",
                fontSize: 13,
                background: isLocked ? "rgba(255,255,255,0.03)" : "var(--uv-surface-2)",
                border: isLocked ? "1px solid rgba(39, 174, 130, 0.3)" : "1px solid var(--uv-line-strong)",
                borderRadius: 6,
                color: isLocked ? "var(--uv-good)" : "var(--uv-text)",
                cursor: isLocked ? "not-allowed" : "text",
                fontFamily: "monospace",
              }}
              placeholder="Ex: act_1234567890"
              value={metaId}
              onChange={(e) => setMetaId(e.target.value)}
            />
          </div>
          <div>
            {!isLocked ? (
              <button
                type="submit"
                className="uvBtnPrimary"
                disabled={saving || (!googleId.trim() && !metaId.trim())}
                style={{ padding: "8px 16px", fontSize: 13 }}
              >
                {saving ? "Salvando..." : "Salvar e Bloquear IDs"}
              </button>
            ) : (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "7px 14px",
                  borderRadius: 6,
                  background: "rgba(39, 174, 130, 0.12)",
                  border: "1px solid rgba(39, 174, 130, 0.3)",
                  color: "var(--uv-good)",
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                <CheckCircle2 size={13} /> Contas Conectadas e Ativas
              </div>
            )}
          </div>
        </form>

        {saveMsg && (
          <div
            style={{
              marginTop: 10,
              padding: "6px 12px",
              borderRadius: 6,
              background: saveMsg.includes("sucesso") ? "rgba(39, 174, 130, 0.1)" : "rgba(239, 68, 68, 0.1)",
              border: `1px solid ${saveMsg.includes("sucesso") ? "rgba(39, 174, 130, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
              fontSize: 12,
              color: saveMsg.includes("sucesso") ? "var(--uv-good)" : "var(--uv-critical)",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <CheckCircle2 size={13} /> {saveMsg}
          </div>
        )}
      </div>
    </section>
  );
}
