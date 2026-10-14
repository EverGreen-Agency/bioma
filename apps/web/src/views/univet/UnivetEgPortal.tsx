import { useEffect, useRef, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  ExternalLink,
  Play,
  Radio,
  RefreshCw,
  ScanSearch,
  Square,
} from "lucide-react";
import { fmtInt, fmtPct } from "../../data/univet/univetPortalData";
import { formatDateTime } from "../../components/KommoRealDashboard";
import {
  capturePortalKey,
  portalApi,
  type EgApplyProgress,
  type EgClassificationField,
  type EgClassifyProgress,
} from "../../lib/portalApi";
import { UnivetPortalChrome } from "./UnivetRealPortal";
import "./univet-portal.css";

// Operação EG da Univet: onde o Bioma lê e ESCREVE no Kommo do cliente.
// Deduplicação e classificação rodam em lotes pequenos, um após o outro, para o
// progresso aparecer na tela e a operação poder ser interrompida a qualquer momento.

const SLUG = "univet";
const DEDUP_BATCH = 15;
const CLASSIFY_BATCH = 5;

const SOURCE_LABEL: Record<EgClassificationField["source"], string> = { modelo: "modelo", regra: "regra", ddd: "DDD" };
const STATUS_LABEL: Record<string, string> = {
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
  const [key] = useState(() => capturePortalKey());
  const status = useQuery({
    queryKey: ["eg-status", SLUG, key],
    queryFn: () => portalApi.status(SLUG, key),
    retry: false,
  });

  const [busy, setBusy] = useState<null | "connect" | "sync" | "scan" | "webhook" | "dedup" | "classify">(null);
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
  const [writeToKommo, setWriteToKommo] = useState(true);
  const [classifyProgress, setClassifyProgress] = useState<EgClassifyProgress | null>(null);
  const [liveStream, setLiveStream] = useState(true);

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
      let written = 0;
      do {
        last = await portalApi.classifyBatch(SLUG, key, CLASSIFY_BATCH, writeToKommo);
        written += last.fields_written;
        setClassifyProgress(last);
        void queryClient.invalidateQueries({ queryKey: ["eg-classification", SLUG] });
      } while (last.remaining > 0 && last.processed > 0 && !stopRef.current);
      const verb = writeToKommo ? "campos gravados no Kommo" : "campos decididos (simulação, nada gravado)";
      return `${stopRef.current ? "Interrompido" : "Concluído"}: ${fmtInt(written)} ${verb}. ${fmtInt(last.remaining)} leads na fila.`;
    });


  const kommoUrl = data?.kommo.subdomain ? `https://${data.kommo.subdomain}.kommo.com` : null;
  const classification = data?.classification;
  const leadsTotal = data?.kommo.leads_count ?? 0;
  const progress = dedup.data?.progress;
  const dedupPageCount = dedup.data ? Math.max(1, Math.ceil(dedup.data.total_clusters / dedup.data.page_size)) : 1;

  return (
    <UnivetPortalChrome subtitle="Operação EG · Kommo">
      <section className="uvHero">
        <h2 className="uvHeroHeadline">Higienização e classificação do CRM</h2>
        <p className="uvHeroSubtitle">
          Daqui o Bioma lê e altera o Kommo da Univet: unifica contatos duplicados e preenche os campos dos leads a partir da conversa.
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

          <div className="uvSources" aria-label="Estado das conexões">
            <div className={`uvSource ${data.kommo.configured ? "uvSourceOn" : ""}`}>
              <span className="uvSourceState">
                {data.kommo.configured ? <CheckCircle2 size={14} /> : <CircleDashed size={14} />}
                {data.kommo.configured ? `${data.kommo.subdomain}.kommo.com` : "Não conectado"}
              </span>
              <strong>Kommo CRM</strong>
              <span>
                {data.kommo.fetched_at
                  ? `${fmtInt(leadsTotal)} leads lidos em ${formatDateTime(data.kommo.fetched_at)}`
                  : "Leads ainda não sincronizados"}
              </span>
            </div>
            <div className={`uvSource ${data.webhook.active ? "uvSourceOn" : ""}`}>
              <span className="uvSourceState">
                {data.webhook.active ? <CheckCircle2 size={14} /> : <CircleDashed size={14} />}
                {data.webhook.active ? "Captura ativa" : "Captura desligada"}
              </span>
              <strong>Mensagens e leads novos</strong>
              <span>
                {data.webhook.active
                  ? `${fmtInt(data.webhook.events_received ?? 0)} avisos recebidos${data.webhook.last_event_at ? `, último em ${formatDateTime(data.webhook.last_event_at)}` : ""}`
                  : "Sem captura, a classificação só roda sob demanda"}
              </span>
            </div>
            <div className={`uvSource ${classification?.engine === "modelo" ? "uvSourceOn" : ""}`}>
              <span className="uvSourceState">
                {classification?.engine === "modelo" ? <CheckCircle2 size={14} /> : <CircleDashed size={14} />}
                {classification?.engine === "modelo" ? "Modelo de decisão ativo" : "Sem chave do modelo"}
              </span>
              <strong>Motor de classificação</strong>
              <span>{classification?.label}</span>
            </div>
          </div>

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
                  <div className="uvControlGroup">
                    <label className="uvCheck">
                      <input type="checkbox" checked={writeToKommo} disabled={busy !== null} onChange={(event) => setWriteToKommo(event.target.checked)} />
                      Gravar no Kommo
                    </label>
                    {busy === "classify" ? (
                      <button type="button" className="uvBtnSecondary" onClick={() => (stopRef.current = true)}>
                        <Square size={13} /> Parar
                      </button>
                    ) : (
                      <button type="button" className="uvBtnPrimary" disabled={busy !== null || !data.kommo.fetched_at} onClick={handleClassify}>
                        <Play size={13} /> {writeToKommo ? "Classificar lote (5 leads)" : "Simular lote (5 leads)"}
                      </button>
                    )}
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
                        caption={classification?.simulated ? `de ${fmtInt(leadsTotal)}, sendo ${fmtInt(classification.simulated)} só simulados` : `de ${fmtInt(leadsTotal)} leads na conta`}
                      />
                      <Tile label="Classificados" value={fmtInt(classification?.classified ?? 0)} caption="com ao menos um campo decidido" />
                      <Tile label="Campos gravados" value={fmtInt(classification?.fields_written ?? 0)} caption="preenchidos no Kommo" />
                      <Tile label="Sem conversa" value={fmtInt(classification?.without_conversation ?? 0)} caption="leads sem mensagem no Kommo" />
                    </div>
                    <Progress done={classification?.total ?? 0} total={leadsTotal} />
                    {busy === "classify" && classifyProgress && (
                      <p className="uvChartNote">Lendo conversas: {fmtInt(classifyProgress.remaining)} leads na fila. Cada lead exige de 4 a 6 consultas ao Kommo.</p>
                    )}

                    {results.data && results.data.results.length > 0 ? (
                      <div className="uvFeedList">
                        {results.data.results.map((row) => (
                          <div
                            key={row.lead_id}
                            className={`uvFeedItem ${row.status === "classificado" ? "good" : row.status === "erro" ? "error" : "warn"}`}
                          >
                            <div className="uvFeedItemHeader">
                              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                                <a
                                  className="uvLink"
                                  style={{ fontWeight: 700, fontSize: 14 }}
                                  href={`${kommoUrl}/leads/detail/${row.lead_id}`}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Lead #{row.lead_id} <ExternalLink size={11} />
                                </a>
                                <span className={`uvVerdict ${row.status === "classificado" ? "uvVerdictGood" : row.status === "erro" ? "uvVerdictWarn" : ""}`} title={row.error ?? undefined}>
                                  {STATUS_LABEL[row.status] ?? row.status}
                                </span>
                                <span className={`uvTriggerBadge ${row.trigger === "webhook" ? "webhook" : ""}`}>
                                  {row.trigger === "webhook" ? "Webhook" : row.trigger === "simulacao" ? "Simulação" : "Lote"}
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
                                {row.status === "sem_conversa" ? "Nenhuma mensagem encontrada para este lead no Kommo." : "Conversa sem termos identificáveis."}
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
                                      {field.source === "modelo" ? "Laya AI" : field.source === "ddd" ? "DDD" : "Regra"}
                                    </span>
                                    <span style={{ fontSize: 11, color: "var(--uv-text-2)", fontFamily: "monospace" }}>{fmtPct(field.confidence, 0)}</span>
                                    <span style={{ fontSize: 10, color: field.written ? "var(--uv-good)" : "var(--uv-text-3)", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600 }}>
                                      {field.written ? "Gravado" : field.already_filled ? "Mantido" : "Simulado"}
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
                    ) : (
                      <p className="uvEmpty">Nenhum lead classificado ainda. Clique em "Classificar lote (5 leads)" acima ou ative o webhook.</p>
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
