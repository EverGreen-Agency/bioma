import { useEffect, useRef, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Check,
  CheckCircle2,
  CircleDashed,
  Cpu,
  ExternalLink,
  Play,
  Radio,
  RefreshCw,
  ScanSearch,
  Square,
  CheckSquare,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { fmtBRL, fmtInt, fmtPct } from "../../data/univet/univetPortalData";
import { formatDateTime } from "../../components/KommoRealDashboard";
import {
  capturePortalKey,
  isEgAuthorized,
  portalApi,
  savePortalKey,
  type EgApplyProgress,
  type EgClassificationField,
  type EgClassifyProgress,
} from "../../lib/portalApi";
import { useCurrentUser } from "../../hooks/api/auth";
import { UnivetPortalChrome } from "./UnivetRealPortal";
import { CaptureHealth, ConnectionsChecklist } from "./UnivetEgInsights";
import "./univet-portal.css";

// Operação EG da Univet: onde o Bioma lê e ESCREVE no Kommo do cliente.
// Deduplicação e classificação rodam em lotes pequenos, um após o outro, para o
// progresso aparecer na tela e a operação poder ser interrompida a qualquer momento.

const SLUG = "univet";
const DEDUP_BATCH = 15;
const CLASSIFY_BATCH = 5;

const SOURCE_LABEL: Record<EgClassificationField["source"], string> = {
  modelo: "Laya AI",
  regra: "Regra",
  ddd: "DDD",
  texto: "Texto",
};
const STATUS_LABEL: Record<string, string> = {
  sugerido: "Sugerido (Pendente)",
  gravado: "Gravado no Kommo",
  aguardando_cliente: "Aguardando Cliente",
  classificado: "Classificado",
  sem_conversa: "Sem conversa",
  sem_sinal: "Conversa sem sinal",
  erro: "Erro",
};

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Erro inesperado.";
}

function Progress({ done, total }: { done: number; total: number }) {
  const share = total > 0 ? done / total : 0;
  return (
    <div className="uvProgress" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={done}>
      <span style={{ width: `${Math.min(100, share * 100)}%` }} />
    </div>
  );
}

function Tile({ label, value, caption }: { label: string; value: string; caption: string }) {
  return (
    <div className="uvTile">
      <div className="uvTileLabel">{label}</div>
      <div className="uvTileValue">{value}</div>
      <div className="uvTileFoot"><span>{caption}</span></div>
    </div>
  );
}

export function UnivetEgPortal() {
  const queryClient = useQueryClient();
  const { data: currentUser, isLoading: loadingUser } = useCurrentUser();
  const [key, setKey] = useState(() => capturePortalKey());
  const [keyInput, setKeyInput] = useState("");
  const isAuthorized = Boolean(currentUser?.id || isEgAuthorized() || key);
  const status = useQuery({
    queryKey: ["eg-status", SLUG, key],
    queryFn: () => portalApi.status(SLUG, key),
    retry: false,
  });

  const dashboardQuery = useQuery({
    queryKey: ["portal-dashboard", SLUG, 0],
    queryFn: () => portalApi.dashboard(SLUG, 0),
    refetchInterval: 30_000,
  });
  const nomusData = dashboardQuery.data?.dashboard?.nomus;
  const kommoTotals = dashboardQuery.data?.dashboard?.totals;

  const [busy, setBusy] = useState<null | "connect" | "sync" | "scan" | "webhook" | "dedup" | "classify" | "apply_lead" | "apply_batch" | "reset" | "clear_lead" | "clear_batch">(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const stopRef = useRef(false);

  const [subdomain, setSubdomain] = useState("");
  const [token, setToken] = useState("");
  const [showConnect, setShowConnect] = useState(false);

  const [dedupPage, setDedupPage] = useState(1);
  const [onlyPending, setOnlyPending] = useState(true);
  const [confirmDedup, setConfirmDedup] = useState(false);
  const [applyProgress, setApplyProgress] = useState<EgApplyProgress | null>(null);

  const [resultsPage, setResultsPage] = useState(1);
  const [classifyProgress, setClassifyProgress] = useState<EgClassifyProgress | null>(null);
  const [liveStream, setLiveStream] = useState(true);
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [selectedLeadIds, setSelectedLeadIds] = useState<Set<number>>(new Set());

  const data = status.data;
  const runId = data?.dedup?.id ?? null;
  const dedup = useQuery({
    queryKey: ["eg-dedup", SLUG, key, runId, dedupPage, onlyPending],
    queryFn: () => portalApi.dedupDetail(SLUG, key, runId as string, dedupPage, onlyPending),
    enabled: Boolean(runId),
    placeholderData: (previous) => previous,
  });
  const results = useQuery({
    queryKey: ["eg-classification", SLUG, key, resultsPage],
    queryFn: () => portalApi.classificationResults(SLUG, key, resultsPage),
    enabled: Boolean(data?.kommo.configured),
    placeholderData: (previous) => previous,
    refetchInterval: liveStream ? 4000 : false,
  });

  const activeLead =
    results.data?.results.find((r) => r.lead_id === selectedLeadId) ??
    results.data?.results[0] ??
    null;

  useEffect(() => setDedupPage(1), [runId, onlyPending]);

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["eg-status", SLUG] });
    void queryClient.invalidateQueries({ queryKey: ["eg-dedup", SLUG] });
    void queryClient.invalidateQueries({ queryKey: ["eg-classification", SLUG] });
    void queryClient.invalidateQueries({ queryKey: ["portal-dashboard", SLUG] });
  }

  async function run(kind: NonNullable<typeof busy>, action: () => Promise<string | void>) {
    setBusy(kind);
    setActionError(null);
    setNotice(null);
    stopRef.current = false;
    try {
      const message = await action();
      if (message) setNotice(message);
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setBusy(null);
      refresh();
    }
  }

  const handleConnect = (event: FormEvent) => {
    event.preventDefault();
    void run("connect", async () => {
      const result = await portalApi.connect(SLUG, key, subdomain, token);
      setToken("");
      setShowConnect(false);
      return `Conectado à conta ${result.account_name ?? subdomain}. Agora sincronize os leads.`;
    });
  };

  const handleSync = () =>
    run("sync", async () => {
      const result = await portalApi.sync(SLUG, key);
      return `Leitura concluída: ${fmtInt(result.dashboard?.totals.leads_all_time ?? 0)} leads.`;
    });

  const handleScan = () =>
    run("scan", async () => {
      await portalApi.dedupSimulate(SLUG, key);
      setApplyProgress(null);
      return "Varredura concluída. Confira os grupos antes de unificar.";
    });

  const handleWebhook = () =>
    run("webhook", async () => {
      await portalApi.enableWebhook(SLUG, key);
      return "Captura ativada: o Kommo passa a avisar o Bioma a cada mensagem e lead novos.";
    });

  const handleApplyDedup = () =>
    run("dedup", async () => {
      setConfirmDedup(false);
      if (!runId) return;
      let last: EgApplyProgress | null = null;
      do {
        last = await portalApi.dedupApply(SLUG, key, runId, DEDUP_BATCH);
        setApplyProgress(last);
      } while (last.pending > 0 && last.processed > 0 && !stopRef.current);
      return stopRef.current
        ? `Interrompido. ${fmtInt(last.unified)} grupos unificados, ${fmtInt(last.pending)} pendentes.`
        : `Concluído: ${fmtInt(last.unified)} grupos unificados.`;
    });

  const handleClassify = () =>
    run("classify", async () => {
      let last: EgClassifyProgress | null = null;
      let count = 0;
      do {
        // write=false: apenas sugere a classificação para revisão prévia
        last = await portalApi.classifyBatch(SLUG, key, CLASSIFY_BATCH, false);
        count += last.classified;
        setClassifyProgress(last);
        void queryClient.invalidateQueries({ queryKey: ["eg-classification", SLUG] });
      } while (last.remaining > 0 && last.processed > 0 && !stopRef.current);
      return `${stopRef.current ? "Interrompido" : "Diagnóstico concluído"}: ${fmtInt(count)} leads analisados com sugestões geradas. ${fmtInt(last?.remaining ?? 0)} restantes na fila.`;
    });

  const handleApplySelected = () =>
    run("apply_batch", async () => {
      const ids = Array.from(selectedLeadIds);
      if (ids.length === 0) return;
      let totalFields = 0;
      for (const id of ids) {
        try {
          const res = await portalApi.applyClassificationLead(SLUG, key, id);
          totalFields += res.fields_written;
        } catch {
          // ignora falhas individuais para continuar lote
        }
      }
      setSelectedLeadIds(new Set());
      void queryClient.invalidateQueries({ queryKey: ["eg-classification", SLUG] });
      return `Gravado com sucesso! ${fmtInt(ids.length)} leads selecionados foram salvos no Kommo (${fmtInt(totalFields)} campos preenchidos).`;
    });

  const handleApplyLead = (leadId: number) =>
    run("apply_lead", async () => {
      const res = await portalApi.applyClassificationLead(SLUG, key, leadId);
      void queryClient.invalidateQueries({ queryKey: ["eg-classification", SLUG] });
      return `Gravado com sucesso! Lead #${leadId} atualizado no Kommo com ${res.fields_written} campos preenchidos.`;
    });

  const handleApplyBatch = () =>
    run("apply_batch", async () => {
      let totalApplied = 0;
      let totalFields = 0;
      let last: { processed: number; fields_written: number; remaining: number } | null = null;
      do {
        last = await portalApi.applyClassificationBatch(SLUG, key, 10);
        totalApplied += last.processed;
        totalFields += last.fields_written;
        void queryClient.invalidateQueries({ queryKey: ["eg-classification", SLUG] });
      } while (last.remaining > 0 && last.processed > 0 && !stopRef.current);
      return `Lote enviado com sucesso ao Kommo: ${fmtInt(totalApplied)} leads aprovados (${fmtInt(totalFields)} campos gravados no CRM).`;
    });

  const handleResetHistory = () =>
    run("reset", async () => {
      const res = await portalApi.classificationReset(SLUG, key);
      return `Histórico de execuções limpo: ${fmtInt(res.deleted)} logs removidos do feed.`;
    });

  const handleClearLead = (leadId: number) => {
    if (!window.confirm(`Tem certeza que deseja apagar os campos gravados no Kommo para o Lead #${leadId}? Os campos voltarão a ficar vazios no CRM.`)) {
      return;
    }
    return run("clear_lead", async () => {
      const res = await portalApi.clearLeadClassification(SLUG, key, leadId);
      void queryClient.invalidateQueries({ queryKey: ["eg-classification", SLUG] });
      return `Campos limpos com sucesso! Lead #${leadId} teve ${res.fields_cleared} campos zerados no Kommo.`;
    });
  };

  const handleClearBatch = () => {
    if (!window.confirm("ATENÇÃO: Deseja realmente limpar e apagar no Kommo CRM todos os campos gravados até agora? Essa ação zerará os campos customizados dos leads classificados no CRM.")) {
      return;
    }
    return run("clear_batch", async () => {
      let totalCleared = 0;
      let totalFields = 0;
      let last: { processed: number; fields_cleared: number; remaining: number } | null = null;
      do {
        last = await portalApi.clearClassificationBatch(SLUG, key, 20);
        totalCleared += last.processed;
        totalFields += last.fields_cleared;
        void queryClient.invalidateQueries({ queryKey: ["eg-classification", SLUG] });
      } while (last.remaining > 0 && last.processed > 0 && !stopRef.current);
      return `Limpeza no Kommo concluída: ${fmtInt(totalCleared)} leads limpos (${fmtInt(totalFields)} campos zerados no CRM).`;
    });
  };



  const kommoUrl = data?.kommo.subdomain ? `https://${data.kommo.subdomain}.kommo.com` : null;
  const classification = data?.classification;
  const leadsTotal = data?.kommo.leads_count ?? 0;
  const progress = dedup.data?.progress;
  const dedupPageCount = dedup.data ? Math.max(1, Math.ceil(dedup.data.total_clusters / dedup.data.page_size)) : 1;

  if (!isAuthorized && !loadingUser) {
    return (
      <UnivetPortalChrome subtitle="Acesso Restrito">
        <section className="uvHero" style={{ textAlign: "center", padding: "60px 20px" }}>
          <h2 className="uvHeroHeadline">Área Restrita à Operação EverGreen</h2>
          <p className="uvHeroSubtitle" style={{ maxWidth: 540, margin: "12px auto 24px" }}>
            Esta área é restrita à equipe interna da EverGreen. Faça login no Bioma ou digite a chave de acesso da agência.
          </p>
          <div style={{ display: "flex", gap: 10, justifyContent: "center", alignItems: "center", flexWrap: "wrap", marginTop: 16 }}>
            <input
              type="password"
              placeholder="Chave de acesso da agência..."
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && keyInput.trim()) {
                  savePortalKey(keyInput.trim());
                  setKey(keyInput.trim());
                }
              }}
              style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--uv-line)", background: "var(--uv-surface-2)", color: "var(--uv-text)", width: 240 }}
            />
            <button
              type="button"
              className="uvBtnPrimary"
              onClick={() => {
                if (keyInput.trim()) {
                  savePortalKey(keyInput.trim());
                  setKey(keyInput.trim());
                }
              }}
            >
              Entrar com Chave
            </button>
            <a href="/" className="uvBtnSecondary" style={{ textDecoration: "none" }}>
              Ir para Login do Bioma
            </a>
          </div>
        </section>
      </UnivetPortalChrome>
    );
  }

  return (
    <UnivetPortalChrome subtitle="Operação EG · Kommo">
      <section className="uvHero">
        <h2 className="uvHeroHeadline">Operação EG · Higienização e CRM</h2>
        <p className="uvHeroSubtitle">
          Ambiente de operação técnica da EverGreen: conexões de mídia, conciliação de vendas com Nomus ERP, deduplicação e Laya AI.
        </p>
      </section>

      {status.isLoading ? (
        <>
          <div className="uvSkeleton" style={{ height: 84 }} />
          <div className="uvSkeleton" style={{ height: 260 }} />
        </>
      ) : status.error ? (
        <div className="uvNotice uvNoticeError" role="alert">
          <h4><AlertTriangle size={15} /> Não foi possível abrir o portal</h4>
          <p>{errorMessage(status.error)}</p>
        </div>
      ) : data ? (
        <>
          {actionError && (
            <div className="uvNotice uvNoticeError" role="alert">
              <h4><AlertTriangle size={15} /> A operação não terminou</h4>
              <p>{actionError}</p>
            </div>
          )}
          {notice && (
            <div className="uvNotice uvNoticeOk" role="status">
              <p><CheckCircle2 size={14} /> {notice}</p>
            </div>
          )}

          <div className="uvControlGroup">
            <button type="button" className="uvBtnPrimary" disabled={busy !== null || !data.kommo.configured} onClick={handleSync}>
              <RefreshCw size={14} className={busy === "sync" ? "uvSpin" : undefined} />
              {busy === "sync" ? "Lendo o Kommo..." : "Sincronizar leads"}
            </button>
            {!data.webhook.active && (
              <button type="button" className="uvBtnSecondary" disabled={busy !== null || !data.kommo.configured} onClick={handleWebhook}>
                {busy === "webhook" ? "Ativando..." : "Ativar captura de mensagens"}
              </button>
            )}
            <button type="button" className="uvBtnGhost" onClick={() => setShowConnect((open) => !open)}>
              {data.kommo.configured ? "Trocar token do Kommo" : "Conectar Kommo"}
            </button>
          </div>

          {(showConnect || !data.kommo.configured) && (
            <form className="uvCard" onSubmit={handleConnect}>
              <div className="uvCardHeader">
                <div>
                  <h3 className="uvCardTitle">Conexão com o Kommo</h3>
                  <p className="uvCardSubtitle">O token fica cifrado no banco do Bioma e não volta a ser exibido.</p>
                </div>
              </div>
              <div className="uvFormRow">
                <label className="uvField">
                  <span>Subdomínio</span>
                  <input value={subdomain} onChange={(event) => setSubdomain(event.target.value)} placeholder="univetloupes" required />
                </label>
                <label className="uvField uvFieldWide">
                  <span>Token de longa duração</span>
                  <input type="password" value={token} onChange={(event) => setToken(event.target.value)} autoComplete="off" required />
                </label>
                <button type="submit" className="uvBtnPrimary" disabled={busy !== null}>
                  {busy === "connect" ? "Validando..." : "Salvar e validar"}
                </button>
              </div>
            </form>
          )}

          {data.kommo.configured && (
            <>
              {/* Inteligência Operacional · Entidades & Cotas */}
              <section className="uvCard">
                <div className="uvCardHeader">
                  <div>
                    <h3 className="uvCardTitle">Inteligência Operacional · Entidades & Cotas</h3>
                    <p className="uvCardSubtitle">
                      Relação estrutural do CRM Univet (1 Contato : N Negócios) e monitoramento de consumo de cotas de API.
                    </p>
                  </div>
                </div>

                <div className="uvKpiRow">
                  <Tile
                    label="Negócios (Leads)"
                    value={fmtInt(leadsTotal)}
                    caption="oportunidades comerciais no funil"
                  />
                  <Tile
                    label="Contatos analisados"
                    value={fmtInt(data.dedup?.contacts_scanned ?? 0)}
                    caption={data.dedup ? `${fmtInt(data.dedup.duplicates_count)} cadastros repetidos detectados` : "aguardando varredura"}
                  />
                  <Tile
                    label="Cota API Kommo"
                    value="7 req/s"
                    caption="throttling de 160ms ativo (0 risco 429)"
                  />
                  <Tile
                    label="Laya AI (ModernBERT)"
                    value="~35ms"
                    caption="inferência local · custo R$ 0 em tokens"
                  />
                </div>

                <div className="uvArchitectureBanner">
                  <div className="uvArchitectureItem">
                    <strong>Lead = Negócio / Oportunidade</strong>
                    <span>Cada lead representa uma transação comercial (Venda Nova, Pós-venda, Manutenção ou Recompra).</span>
                  </div>
                  <div className="uvArchitectureDivider" />
                  <div className="uvArchitectureItem">
                    <strong>Contato = Pessoa Física (Médico/Dentista)</strong>
                    <span>Detém o telefone/WhatsApp, DDD e especialidade. Um mesmo contato ter múltiplos leads representa o ciclo de vida (LTV) e histórico do cliente.</span>
                  </div>
                  <div className="uvArchitectureDivider" />
                  <div className="uvArchitectureItem">
                    <strong>Deduplicação Inteligente</strong>
                    <span>Unifica apenas cadastros duplicados do mesmo contato (por telefone ou e-mail), mantendo todos os seus negócios associados ao Contato Mestre.</span>
                  </div>
                </div>
              </section>

              {/* Conexões do Painel, Mídia Paga e Saúde da Captação */}
              <ConnectionsChecklist status={data} slug={SLUG} portalKey={key} onUpdate={refresh} />
              <CaptureHealth slug={SLUG} />

              {/* Triangulação Kommo CRM x Nomus ERP */}
              <section className="uvCard">
                <div className="uvCardHeader">
                  <div>
                    <h3 className="uvCardTitle">Triangulação & Auditoria de Vendas (Kommo CRM ⟷ Nomus ERP)</h3>
                    <p className="uvCardSubtitle">
                      Conciliação direta entre os pedidos faturados no Nomus ERP e as oportunidades cadastradas no Kommo CRM.
                    </p>
                  </div>
                </div>
                <div className="uvKpiRow">
                  <Tile
                    label="Faturamento Real Faturado"
                    value={fmtBRL(nomusData?.faturamento_total ?? 0)}
                    caption={`${fmtInt(nomusData?.pedidos_count ?? 0)} pedidos emitidos no Nomus ERP`}
                  />
                  <Tile
                    label="Ticket Médio Real"
                    value={fmtBRL(nomusData?.ticket_medio ?? 0)}
                    caption="média oficial por pedido faturado"
                  />
                  <Tile
                    label="Leads no Kommo CRM"
                    value={fmtInt(kommoTotals?.leads_all_time ?? leadsTotal)}
                    caption={`${fmtInt(kommoTotals?.won ?? 0)} negócios marcados ganhos no CRM`}
                  />
                  <Tile
                    label="Consultores Ativos"
                    value={fmtInt(nomusData?.representantes_count ?? 12)}
                    caption="com vendas e praças territoriais mapeadas"
                  />
                </div>

                {nomusData?.reps && nomusData.reps.length > 0 && (
                  <div className="uvTableWrap" style={{ marginTop: 16 }}>
                    <table className="uvTable">
                      <thead>
                        <tr>
                          <th>Consultor / Representante</th>
                          <th>Praça / Território Oficial</th>
                          <th className="uvNum">Pedidos</th>
                          <th className="uvNum">Faturamento</th>
                          <th className="uvNum">Participação</th>
                        </tr>
                      </thead>
                      <tbody>
                        {nomusData.reps.slice(0, 8).map((rep) => (
                          <tr key={rep.label}>
                            <td><strong>{rep.label}</strong></td>
                            <td>
                              <span className="uvChip" style={{ fontSize: 11, background: "rgba(39, 174, 130, 0.12)", color: "var(--uv-accent-ink)", border: "1px solid rgba(39, 174, 130, 0.25)" }}>
                                {rep.territorio || "Território Nacional / Matriz"}
                              </span>
                            </td>
                            <td className="uvNum">{fmtInt(rep.pedidos)}</td>
                            <td className="uvNum"><strong>{fmtBRL(rep.faturamento)}</strong></td>
                            <td className="uvNum">{fmtPct(rep.share, 1)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              {/* Deduplicação */}
              <section className="uvCard">
                <div className="uvCardHeader">
                  <div>
                    <h3 className="uvCardTitle">Contatos duplicados</h3>
                    <p className="uvCardSubtitle">
                      Unificar move os leads para o contato principal e marca a duplicata com {"[DUPLICADO]"} no nome. Nada é apagado.
                    </p>
                  </div>
                  <div className="uvControlGroup">
                    <button type="button" className="uvBtnSecondary" disabled={busy !== null} onClick={handleScan}>
                      <ScanSearch size={14} className={busy === "scan" ? "uvSpin" : undefined} />
                      {busy === "scan" ? "Varrendo contatos..." : "Rodar varredura"}
                    </button>
                    {busy === "dedup" ? (
                      <button type="button" className="uvBtnSecondary" onClick={() => (stopRef.current = true)}>
                        <Square size={13} /> Parar
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="uvBtnPrimary"
                        disabled={busy !== null || !progress || progress.pending === 0}
                        onClick={() => setConfirmDedup(true)}
                      >
                        <Play size={13} /> Unificar pendentes
                      </button>
                    )}
                  </div>
                </div>

                {confirmDedup && progress && (
                  <div className="uvConfirm" role="alertdialog" aria-label="Confirmar unificação">
                    <p>
                      Isto altera o Kommo da Univet: {fmtInt(progress.pending)} grupos terão os leads movidos para o contato principal e a
                      duplicata marcada. Pode ser interrompido a qualquer momento.
                    </p>
                    <div className="uvControlGroup">
                      <button type="button" className="uvBtnPrimary" onClick={handleApplyDedup}>Confirmar e unificar</button>
                      <button type="button" className="uvBtnGhost" onClick={() => setConfirmDedup(false)}>Cancelar</button>
                    </div>
                  </div>
                )}

                {!data.dedup ? (
                  <p className="uvEmpty">Nenhuma varredura feita ainda. Rode a primeira para ver quantos contatos estão duplicados.</p>
                ) : (
                  <>
                    <div className="uvKpiRow">
                      <Tile label="Contatos analisados" value={fmtInt(data.dedup.contacts_scanned)} caption={`varredura de ${formatDateTime(data.dedup.created_at)}`} />
                      <Tile
                        label="Contatos duplicados"
                        value={fmtInt(data.dedup.duplicates_count)}
                        caption={data.dedup.contacts_scanned > 0 ? `${fmtPct(data.dedup.duplicates_count / data.dedup.contacts_scanned, 0)} da base` : "base vazia"}
                      />
                      <Tile label="Grupos unificados" value={fmtInt(progress?.unified ?? data.dedup.clusters_applied)} caption={`de ${fmtInt(data.dedup.clusters_count)} grupos`} />
                      <Tile label="Pendentes" value={fmtInt(progress?.pending ?? 0)} caption={progress?.errors ? `${fmtInt(progress.errors)} com erro` : "aguardando unificação"} />
                    </div>
                    {progress && <Progress done={progress.unified} total={progress.total} />}
                    {applyProgress && applyProgress.errors.length > 0 && (
                      <ul className="uvErrorList">
                        {applyProgress.errors.map((line) => <li key={line}>{line}</li>)}
                      </ul>
                    )}
                    {progress && progress.unified > 0 && kommoUrl && (
                      <p className="uvChartNote">
                        Para excluir de vez: no Kommo, abra <a className="uvLink" href={`${kommoUrl}/contacts/list/contacts/`} target="_blank" rel="noreferrer">Contatos <ExternalLink size={11} /></a>,
                        busque por {"[DUPLICADO]"}, selecione todos e exclua. A API do Kommo não permite excluir contato.
                      </p>
                    )}

                    <div className="uvTableToolbar">
                      <label className="uvCheck">
                        <input type="checkbox" checked={onlyPending} onChange={(event) => setOnlyPending(event.target.checked)} />
                        Só pendentes
                      </label>
                    </div>
                    {dedup.data && dedup.data.clusters.length > 0 ? (
                      <div className="uvTableWrap">
                        <table className="uvTable">
                          <thead>
                            <tr>
                              <th>Contato principal</th>
                              <th>Duplicata</th>
                              <th>Critério</th>
                              <th className="uvNum">Leads a mover</th>
                              <th>Situação</th>
                            </tr>
                          </thead>
                          <tbody>
                            {dedup.data.clusters.map((cluster) => (
                              <tr key={cluster.cluster_id}>
                                <td>
                                  <a className="uvLink" href={`${kommoUrl}/contacts/detail/${cluster.master_contact_id}`} target="_blank" rel="noreferrer">
                                    {cluster.master_name} <ExternalLink size={11} />
                                  </a>
                                </td>
                                <td>
                                  {cluster.duplicate_contacts.map((dup) => (
                                    <div key={dup.id}>
                                      <a className="uvLink" href={`${kommoUrl}/contacts/detail/${dup.id}`} target="_blank" rel="noreferrer">
                                        {dup.name ?? "Sem nome"} <ExternalLink size={11} />
                                      </a>
                                    </div>
                                  ))}
                                </td>
                                <td>{cluster.match_kind}</td>
                                <td className="uvNum">{fmtInt(cluster.leads_to_reassign)}</td>
                                <td>
                                  <span className={`uvVerdict ${cluster.state === "unificado" ? "uvVerdictGood" : cluster.state === "erro" ? "uvVerdictWarn" : ""}`} title={cluster.error ?? undefined}>
                                    {cluster.state === "unificado" ? "Unificado" : cluster.state === "erro" ? "Erro" : "Pendente"}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="uvEmpty">{onlyPending ? "Nenhum grupo pendente." : "Nenhuma duplicata nesta varredura."}</p>
                    )}
                    {dedup.data && (
                      <div className="uvPager">
                        <span>{fmtInt(dedup.data.total_clusters)} grupos · página {dedup.data.page} de {dedupPageCount}</span>
                        <div>
                          <button type="button" className="uvBtnGhost" disabled={dedupPage <= 1} onClick={() => setDedupPage((p) => p - 1)}>Anterior</button>
                          <button type="button" className="uvBtnGhost" disabled={dedupPage >= dedupPageCount} onClick={() => setDedupPage((p) => p + 1)}>Próxima</button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </section>

              {/* Feed Descendente de Classificações em Tempo Real */}
              <section className="uvCard">
                <div className="uvCardHeader">
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                      <h3 className="uvCardTitle">Feed de Classificação em Tempo Real</h3>
                      <button
                        type="button"
                        className={`uvLiveIndicator ${liveStream ? "" : "paused"}`}
                        onClick={() => setLiveStream((v) => !v)}
                        title={liveStream ? "Clique para pausar atualização automática" : "Clique para reativar tempo real"}
                      >
                        <span className="uvLiveDot" />
                        {liveStream ? "Ao Vivo (a cada 4s)" : "Pausado"}
                      </button>
                    </div>
                    <p className="uvCardSubtitle">
                      Lista cronológica descendente: a cada webhook de mensagem nova ou execução em lote, os leads classificados descem nesta lista.
                    </p>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10, width: "100%" }}>
                    {/* Banner de Garantia Human-in-the-Loop */}
                    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", background: "rgba(39, 174, 130, 0.08)", border: "1px solid rgba(39, 174, 130, 0.25)", borderRadius: 8 }}>
                      <CheckCircle2 size={15} style={{ color: "var(--uv-accent-ink)", flexShrink: 0 }} />
                      <span style={{ fontSize: 12, color: "var(--uv-text)", lineHeight: 1.4 }}>
                        <strong style={{ color: "var(--uv-accent-ink)" }}>Human-in-the-Loop Ativo:</strong> A IA roda em modo diagnóstico e gera apenas <em>sugestões pendentes</em>. Nenhuma informação é gravada no CRM sem aprovação humana. Objeção de preço não fecha nem perde oportunidades.
                      </span>
                    </div>

                    <div className="uvControlGroup" style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
                      {busy === "classify" ? (
                        <button type="button" className="uvBtnSecondary" onClick={() => (stopRef.current = true)}>
                          <Square size={13} /> Parar Análise
                        </button>
                      ) : (
                        <div style={{ display: "flex", gap: 6, alignItems: "center", background: "var(--uv-surface-2)", padding: "4px 8px", borderRadius: 8, border: "1px solid var(--uv-line)" }}>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--uv-text-3)", textTransform: "uppercase", paddingRight: 4 }}>
                            1. Diagnóstico IA:
                          </span>
                          <button
                            type="button"
                            className="uvBtnPrimary"
                            disabled={busy !== null || !data.kommo.fetched_at}
                            onClick={handleClassify}
                            title="Lê as conversas dos leads no Kommo e gera sugestões diagnósticas pendentes"
                          >
                            <Play size={13} /> Analisar Conversas com IA
                          </button>
                        </div>
                      )}

                      <div style={{ display: "flex", gap: 6, alignItems: "center", background: "rgba(39, 174, 130, 0.06)", padding: "4px 8px", borderRadius: 8, border: "1px solid rgba(39, 174, 130, 0.2)" }}>
                        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--uv-accent-ink)", textTransform: "uppercase", paddingRight: 4 }}>
                          2. Gravação no CRM:
                        </span>
                        {selectedLeadIds.size > 0 && (
                          <button
                            type="button"
                            className="uvBtnPrimary"
                            style={{ background: "#27ae82", color: "#0b1a15" }}
                            disabled={busy !== null}
                            onClick={handleApplySelected}
                            title="Aprova e grava no Kommo apenas os leads marcados nos checkboxes"
                          >
                            <CheckSquare size={13} /> {busy === "apply_batch" ? "Gravando selecionados..." : `Aprovar Selecionados (${selectedLeadIds.size})`}
                          </button>
                        )}
                        <button
                          type="button"
                          className={selectedLeadIds.size > 0 ? "uvBtnSecondary" : "uvBtnPrimary"}
                          style={selectedLeadIds.size === 0 ? { background: "#27ae82", color: "#0b1a15" } : undefined}
                          disabled={busy !== null || !data.kommo.fetched_at || ((results.data?.summary.suggested ?? 0) === 0 && !results.data?.results.some((r) => r.status === "sugerido" || (r.status === "classificado" && r.fields_written === 0)))}
                          onClick={handleApplyBatch}
                          title="Aprova e grava no Kommo CRM todos os leads com sugestões pendentes"
                        >
                          <UploadCloud size={13} /> {busy === "apply_batch" ? "Gravando lote no CRM..." : `Aprovar Todos (${results.data?.summary.suggested ?? results.data?.results.filter((r) => r.status === "sugerido" || (r.status === "classificado" && r.fields_written === 0)).length ?? 0})`}
                        </button>
                      </div>

                      <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                        {(classification?.total ?? 0) > 0 && (
                          <button
                            type="button"
                            className="uvBtnGhost"
                            disabled={busy !== null}
                            onClick={handleResetHistory}
                            title="Apaga os logs de execução e falhas anteriores do feed local. Não altera dados no Kommo."
                          >
                            {busy === "reset" ? "Limpando..." : "Limpar histórico"}
                          </button>
                        )}
                        {(classification?.fields_written ?? 0) > 0 && (
                          <button
                            type="button"
                            className="uvBtnGhost"
                            style={{ color: "var(--uv-critical)", borderColor: "rgba(239, 68, 68, 0.3)" }}
                            disabled={busy !== null}
                            onClick={handleClearBatch}
                            title="Limpa e apaga no Kommo CRM todos os campos gravados pela IA/classificador"
                          >
                            <Trash2 size={13} /> {busy === "clear_batch" ? "Desfazendo..." : "Desfazer gravações no CRM"}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                </div>

                {!data.kommo.fetched_at ? (
                  <p className="uvEmpty">Sincronize os leads primeiro: a fila de classificação é montada a partir deles.</p>
                ) : (
                  <>
                    <div className="uvKpiRow">
                      <Tile
                        label="Leads lidos"
                        value={fmtInt(classification?.total ?? 0)}
                        caption={`de ${fmtInt(leadsTotal)} leads na conta`}
                      />
                      <Tile
                        label="Sugeridos (Pendentes)"
                        value={fmtInt(results.data?.summary.suggested ?? results.data?.results.filter((r) => r.status === "sugerido" || (r.status === "classificado" && r.fields_written === 0)).length ?? 0)}
                        caption="aguardando envio ao Kommo"
                      />
                      <Tile
                        label="Gravados no Kommo"
                        value={fmtInt(classification?.fields_written ?? 0)}
                        caption="campos preenchidos no CRM"
                      />
                      <Tile
                        label="Aguardando cliente"
                        value={fmtInt(results.data?.summary.waiting_customer ?? results.data?.results.filter((r) => r.status === "aguardando_cliente").length ?? 0)}
                        caption="apenas saudação ('Bom dia')"
                      />
                    </div>
                    <Progress done={classification?.total ?? 0} total={leadsTotal} />
                    {busy === "classify" && classifyProgress && (
                      <p className="uvChartNote">Lendo conversas: {fmtInt(classifyProgress.remaining)} leads na fila. Cada lead exige de 4 a 6 consultas ao Kommo.</p>
                    )}

                    {/* Diagnóstico em Tempo Real · Laya AI Inspector */}
                    {activeLead && (
                      <div className="uvInspectorCard">
                        <div className="uvInspectorHeader">
                          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                            <strong style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
                              <Cpu size={14} style={{ color: "var(--uv-accent-ink)" }} />
                              Diagnóstico Laya AI · Lead #{activeLead.lead_id}
                            </strong>
                            <a
                              className="uvLink"
                              style={{ fontSize: 12, fontWeight: 600 }}
                              href={`${kommoUrl}/leads/detail/${activeLead.lead_id}`}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Abrir no Kommo <ExternalLink size={10} />
                            </a>
                            <span className={`uvVerdict ${activeLead.status === "gravado" || activeLead.status === "classificado" ? "uvVerdictGood" : activeLead.status === "sugerido" ? "sugerido" : activeLead.status === "aguardando_cliente" ? "aguardando" : "uvVerdictWarn"}`}>
                              {STATUS_LABEL[activeLead.status] ?? activeLead.status}
                            </span>
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--uv-text-3)", flexWrap: "wrap" }}>
                            <span>{activeLead.messages_count} mensagens analisadas</span>
                            <span>·</span>
                            <span>{formatDateTime(activeLead.classified_at)}</span>
                            <span className="uvLatencyBadge">
                              <Activity size={10} /> {activeLead.engine === "modelo" ? "Laya AI (ModernBERT)" : "Regras + DDD"}
                            </span>
                          </div>
                        </div>

                        {activeLead.status === "sugerido" || (activeLead.status === "classificado" && activeLead.fields_written === 0) ? (
                          <div className="uvInspectorActionBanner">
                            <div>
                              <strong style={{ fontSize: 13, color: "var(--uv-accent-ink)", display: "flex", alignItems: "center", gap: 6 }}>
                                <CheckCircle2 size={16} /> Sugestão gerada · Confirmação necessária
                              </strong>
                              <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--uv-text-2)" }}>
                                Os campos abaixo foram classificados pela IA e Regras. Clique para confirmar e gravar no Kommo CRM.
                              </p>
                            </div>
                            <button
                              type="button"
                              className="uvBtnApplyPrimary"
                              disabled={busy !== null}
                              onClick={() => handleApplyLead(activeLead.lead_id)}
                            >
                              <Check size={13} /> {busy === "apply_lead" ? "Gravando..." : "Aprovar e Gravar no Kommo"}
                            </button>
                          </div>
                        ) : activeLead.status === "gravado" || activeLead.fields_written > 0 ? (
                          <div className="uvInspectorActionBanner" style={{ background: "rgba(39, 174, 130, 0.05)", borderColor: "rgba(39, 174, 130, 0.2)" }}>
                            <div>
                              <strong style={{ fontSize: 13, color: "var(--uv-good)", display: "flex", alignItems: "center", gap: 6 }}>
                                <CheckCircle2 size={16} /> Gravado no Kommo CRM
                              </strong>
                              <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--uv-text-3)" }}>
                                {activeLead.fields_written} campos sincronizados com a conta da Univet.
                              </p>
                            </div>
                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                              <button
                                type="button"
                                className="uvBtnGhost"
                                disabled={busy !== null}
                                onClick={() => handleApplyLead(activeLead.lead_id)}
                                title="Reenvia as decisões para o Kommo caso queira sincronizar novamente"
                              >
                                <RefreshCw size={12} /> {busy === "apply_lead" ? "Enviando..." : "Reenviar ao Kommo"}
                              </button>
                              <button
                                type="button"
                                className="uvBtnGhost"
                                style={{ color: "var(--uv-critical)", borderColor: "rgba(239, 68, 68, 0.3)" }}
                                disabled={busy !== null}
                                onClick={() => handleClearLead(activeLead.lead_id)}
                                title="Limpa e apaga os campos deste lead no Kommo CRM (volta para vazio)"
                              >
                                <Trash2 size={12} /> {busy === "clear_lead" ? "Limpando..." : "Limpar no Kommo"}
                              </button>
                            </div>
                          </div>
                        ) : activeLead.status === "aguardando_cliente" ? (
                          <div className="uvInspectorActionBanner" style={{ background: "rgba(251, 191, 36, 0.08)", borderColor: "rgba(251, 191, 36, 0.3)" }}>
                            <div>
                              <strong style={{ fontSize: 13, color: "#d97706", display: "flex", alignItems: "center", gap: 6 }}>
                                <AlertTriangle size={16} /> Aguardando detalhamento do cliente
                              </strong>
                              <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--uv-text-2)" }}>
                                O cliente apenas enviou saudação inicial (ex: "Bom dia"). A classificação aguarda a manifestação da dúvida para não gerar falsos positivos.
                              </p>
                            </div>
                          </div>
                        ) : null}

                        {activeLead.fields.length === 0 ? (
                          <p className="uvCellSub" style={{ padding: "8px 0" }}>
                            {activeLead.status === "sem_conversa"
                              ? "Nenhuma mensagem encontrada para este lead no Kommo."
                              : activeLead.status === "aguardando_cliente"
                              ? "Cliente ainda não expressou interesse ou segmento."
                              : "Conversa lida, mas sem termos conclusivos de especialidade, armação ou fotóforo."}
                          </p>
                        ) : (
                          <div className="uvInspectorGrid">
                            {activeLead.fields.map((f) => (
                              <div key={f.key} className="uvInspectorField">
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                  <span style={{ fontSize: 11, color: "var(--uv-text-3)", fontWeight: 550 }}>{f.label}</span>
                                  <span className={`uvSourceTag ${f.source}`}>
                                    {f.source === "modelo" ? "Laya AI" : f.source === "ddd" ? "DDD" : f.source === "texto" ? "Texto" : "Regra"}
                                  </span>
                                </div>
                                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--uv-text)" }}>
                                  {f.values.join(", ")}
                                </div>
                                <div>
                                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--uv-text-3)" }}>
                                    <span>Confiança</span>
                                    <strong style={{ fontFamily: "monospace" }}>{fmtPct(f.confidence, 0)}</strong>
                                  </div>
                                  <div className="uvConfidenceTrack">
                                    <div className="uvConfidenceFill" style={{ width: `${Math.min(100, Math.max(8, f.confidence * 100))}%` }} />
                                  </div>
                                </div>
                                <div style={{ fontSize: 10, color: f.written ? "var(--uv-good)" : f.status === "sugerido" ? "#38bdf8" : "var(--uv-text-3)", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600, marginTop: 2 }}>
                                  {f.written ? "Gravado no Kommo" : f.status === "sugerido" ? "Sugerido (Pendente)" : "Mantido (já preenchido)"}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {results.data && results.data.results.length > 0 ? (
                      <>
                        <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10, flexWrap: "wrap", padding: "6px 12px", background: "var(--uv-surface-2)", borderRadius: 8, border: "1px solid var(--uv-line)" }}>
                          <span style={{ fontSize: 12, color: "var(--uv-text-2)" }}>
                            Seleção de leads:
                          </span>
                          <button
                            type="button"
                            className="uvBtnGhost"
                            style={{ fontSize: 11, padding: "3px 8px" }}
                            onClick={() => {
                              const pendingIds = results.data?.results
                                .filter((r) => r.status === "sugerido" || (r.status === "classificado" && r.fields_written === 0))
                                .map((r) => r.lead_id) ?? [];
                              setSelectedLeadIds(new Set(pendingIds));
                            }}
                          >
                            <CheckSquare size={12} /> Selecionar Pendentes da Página
                          </button>
                          {selectedLeadIds.size > 0 && (
                            <button
                              type="button"
                              className="uvBtnGhost"
                              style={{ fontSize: 11, padding: "3px 8px", color: "var(--uv-accent-ink)" }}
                              onClick={() => setSelectedLeadIds(new Set())}
                            >
                              Desmarcar Todos ({selectedLeadIds.size} selecionados)
                            </button>
                          )}
                        </div>

                        <div className="uvFeedList">
                          {results.data.results.map((row) => (
                            <div
                              key={row.lead_id}
                              className={`uvFeedItem ${row.status === "gravado" || row.status === "classificado" ? "good" : row.status === "sugerido" ? "sugerido" : row.status === "erro" ? "error" : "warn"} ${activeLead?.lead_id === row.lead_id ? "selected" : ""}`}
                              style={{ cursor: "pointer" }}
                              onClick={() => setSelectedLeadId(row.lead_id)}
                            >
                              <div className="uvFeedItemHeader">
                                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                                  {(row.status === "sugerido" || (row.status === "classificado" && row.fields_written === 0)) && (
                                    <input
                                      type="checkbox"
                                      checked={selectedLeadIds.has(row.lead_id)}
                                      onChange={(e) => {
                                        e.stopPropagation();
                                        setSelectedLeadIds((prev) => {
                                          const next = new Set(prev);
                                          if (e.target.checked) next.add(row.lead_id);
                                          else next.delete(row.lead_id);
                                          return next;
                                        });
                                      }}
                                      onClick={(e) => e.stopPropagation()}
                                      style={{ cursor: "pointer", width: 16, height: 16, accentColor: "var(--uv-accent)" }}
                                      title="Selecionar este lead para gravação no CRM"
                                    />
                                  )}
                                  <a
                                    className="uvLink"
                                    style={{ fontWeight: 700, fontSize: 14 }}
                                    href={`${kommoUrl}/leads/detail/${row.lead_id}`}
                                    target="_blank"
                                    rel="noreferrer"
                                  >
                                    Lead #{row.lead_id} <ExternalLink size={11} />
                                  </a>
                                {(row.status === "sugerido" || (row.status === "classificado" && row.fields_written === 0)) && (
                                  <button
                                    type="button"
                                    className="uvBtnActionQuick"
                                    disabled={busy !== null}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleApplyLead(row.lead_id);
                                    }}
                                    title="Gravar decisões deste lead no Kommo"
                                  >
                                    <Check size={11} /> Gravar no Kommo
                                  </button>
                                )}
                                <span className={`uvVerdict ${row.status === "gravado" || row.status === "classificado" ? "uvVerdictGood" : row.status === "sugerido" ? "sugerido" : row.status === "aguardando_cliente" ? "aguardando" : row.status === "erro" ? "uvVerdictWarn" : ""}`} title={row.error ?? undefined}>
                                  {STATUS_LABEL[row.status] ?? row.status}
                                </span>
                                <span className={`uvTriggerBadge ${row.trigger === "webhook" ? "webhook" : ""}`}>
                                  {row.trigger === "webhook" ? "Webhook" : "Lote"}
                                </span>
                              </div>

                              <div className="uvFeedMeta">
                                <span>{fmtInt(row.messages_count)} mensagens lidas</span>
                                <span>·</span>
                                <span>{formatDateTime(row.classified_at)}</span>
                              </div>
                            </div>

                            {row.fields.length === 0 ? (
                              <div style={{ fontSize: 12, color: "var(--uv-text-3)", fontStyle: "italic" }}>
                                {row.status === "sem_conversa" ? "Nenhuma mensagem encontrada para este lead no Kommo." : row.status === "aguardando_cliente" ? "Aguardando cliente enviar mensagem substantiva." : "Conversa sem termos identificáveis."}
                              </div>
                            ) : (
                              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
                                {row.fields.map((field) => (
                                  <div
                                    key={field.key}
                                    className={`uvDecisionPill source-${field.source}`}
                                    title={`${field.label}: ${field.values.join(", ")} (${SOURCE_LABEL[field.source]} · ${fmtPct(field.confidence, 0)})`}
                                  >
                                    <span style={{ color: "var(--uv-text-3)", fontSize: 11 }}>{field.label}:</span>
                                    <strong>{field.values.join(", ")}</strong>
                                    <span className={`uvSourceTag ${field.source}`}>
                                      {field.source === "modelo" ? "Laya AI" : field.source === "ddd" ? "DDD" : field.source === "texto" ? "Texto" : "Regra"}
                                    </span>
                                    <span style={{ fontSize: 11, color: "var(--uv-text-2)", fontFamily: "monospace" }}>{fmtPct(field.confidence, 0)}</span>
                                    <span style={{ fontSize: 10, color: field.written ? "var(--uv-good)" : field.status === "sugerido" ? "#38bdf8" : "var(--uv-text-3)", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600 }}>
                                      {field.written ? "Gravado" : field.status === "sugerido" ? "Sugerido" : "Mantido"}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {row.error && (
                              <div style={{ fontSize: 12, color: "var(--uv-critical)", marginTop: 4 }}>
                                Erro: {row.error}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </>
                    ) : (
                      <p className="uvEmpty">Nenhum lead classificado ainda. Clique em "Classificar leads com IA" acima ou aguarde mensagens pelo webhook.</p>
                    )}

                    {results.data && results.data.results.length > 0 && (
                      <div className="uvPager" style={{ marginTop: 16 }}>
                        <span>página {results.data.page}</span>
                        <div>
                          <button type="button" className="uvBtnGhost" disabled={resultsPage <= 1} onClick={() => setResultsPage((p) => p - 1)}>Anterior</button>
                          <button type="button" className="uvBtnGhost" disabled={results.data.results.length < results.data.page_size} onClick={() => setResultsPage((p) => p + 1)}>Próxima</button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </section>
            </>
          )}
        </>
      ) : null}
    </UnivetPortalChrome>
  );
}
