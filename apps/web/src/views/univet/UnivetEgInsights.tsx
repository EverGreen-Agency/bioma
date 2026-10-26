import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, CircleDashed } from "lucide-react";
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

      <div className="uvSideTitle" style={{ marginTop: 18 }}>Campos obrigatórios na entrada · meta de {fmtPct(FIELD_TARGET, 0)}</div>
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

export function ConnectionsChecklist({ status }: { status: EgStatus }) {
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
      on: false,
      state: "Não ligado a este painel",
      unlocks: "Investimento, CPL, CAC, ROAS e campanhas",
      next: "Univet libera acesso de leitura ao Customer ID para o MCC da EverGreen; cadastrar o ID no Bioma.",
      owner: "Univet + EverGreen",
    },
    {
      name: "Meta Ads e Instagram",
      on: false,
      state: "Não ligado a este painel",
      unlocks: "Investimento e criativos do Meta, alcance orgânico do Instagram",
      next: "Univet adiciona a EverGreen como parceira no Business Manager (conta de anúncios e Instagram).",
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
          <h3 className="uvCardTitle">Conexões do painel</h3>
          <p className="uvCardSubtitle">
            {done} de {items.length} prontas. Cada conexão destrava um bloco da apresentação na v2.
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
    </section>
  );
}
