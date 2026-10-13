import { useEffect, useState } from "react";
import { AlertTriangle, ExternalLink, ScanSearch } from "lucide-react";
import { useKommoDedupRun, useKommoDedupRuns, useRunKommoDedupSimulation } from "../hooks/api";
import { fmtInt, fmtPct } from "../data/univet/univetPortalData";
import "../views/univet/univet-portal.css";

// Higienização do Kommo com dados reais. Cada varredura lê todos os contatos da conta,
// agrupa os que compartilham telefone ou e-mail e guarda o relatório no histórico.
// É sempre simulação: esta tela não altera contato nem lead no CRM.

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatDay(timestamp: number | null) {
  return timestamp ? new Date(timestamp * 1000).toLocaleDateString("pt-BR") : "sem data";
}

export function KommoDeduplicationPanel({ organizationId }: { organizationId: string }) {
  const runs = useKommoDedupRuns(organizationId);
  const simulate = useRunKommoDedupSimulation();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [onlyWithLeads, setOnlyWithLeads] = useState(false);

  // Sem escolha explícita, mostra a varredura mais recente.
  const runId = selectedRunId ?? runs.data?.[0]?.id ?? null;
  const detail = useKommoDedupRun(organizationId, runId, page, onlyWithLeads);

  useEffect(() => {
    setPage(1);
  }, [runId, onlyWithLeads]);

  function handleSimulate() {
    simulate.mutate(organizationId, {
      onSuccess: (run) => setSelectedRunId(run.id),
    });
  }

  const run = detail.data?.run;
  const contactUrl = (id: number) => (run ? `https://${run.subdomain}.kommo.com/contacts/detail/${id}` : "#");
  const pageCount = detail.data ? Math.max(1, Math.ceil(detail.data.total_clusters / detail.data.page_size)) : 1;
  const simulateError = simulate.error instanceof Error ? simulate.error.message : null;
  const runsError = runs.error instanceof Error ? runs.error.message : null;

  return (
    <div className="uvScope">
      <div className="uvPanelHeader">
        <div>
          <h2 className="uvPanelTitle">Higienização e deduplicação</h2>
          <p className="uvPanelSubtitle">
            Varre os contatos do Kommo atrás de pessoas cadastradas mais de uma vez (mesmo telefone ou e-mail). É uma simulação: nada é alterado no CRM.
          </p>
        </div>
        <button type="button" className="uvBtnPrimary" disabled={simulate.isPending} onClick={handleSimulate}>
          <ScanSearch size={14} className={simulate.isPending ? "uvSpin" : undefined} />
          {simulate.isPending ? "Varrendo contatos..." : "Rodar nova varredura"}
        </button>
      </div>

      {simulate.isPending && (
        <div className="uvNotice">
          <h4>Lendo todos os contatos do Kommo</h4>
          <p>Em contas com milhares de contatos a leitura leva até um minuto. Pode continuar nesta tela.</p>
        </div>
      )}

      {(simulateError || runsError) && (
        <div className="uvNotice uvNoticeError" role="alert">
          <h4><AlertTriangle size={15} /> Não foi possível concluir</h4>
          <p>{simulateError ?? runsError}</p>
        </div>
      )}

      {runs.isLoading ? (
        <>
          <div className="uvSkeleton" style={{ height: 110 }} />
          <div className="uvSkeleton" style={{ height: 320 }} />
        </>
      ) : !runsError && (runs.data?.length ?? 0) === 0 && !simulate.isPending ? (
        <div className="uvNotice">
          <h4>Nenhuma varredura feita ainda</h4>
          <p>Use Rodar nova varredura para ler os contatos e ver quantos estão duplicados. O resultado fica guardado aqui no histórico.</p>
        </div>
      ) : run && detail.data ? (
        <>
          <div className="uvKpiRow">
            <div className="uvTile">
              <div className="uvTileLabel">Contatos analisados</div>
              <div className="uvTileValue">{fmtInt(run.contacts_scanned)}</div>
              <div className="uvTileFoot"><span>{run.subdomain}.kommo.com</span></div>
            </div>
            <div className="uvTile">
              <div className="uvTileLabel">Contatos duplicados</div>
              <div className="uvTileValue">{fmtInt(run.duplicates_count)}</div>
              <div className="uvTileFoot">
                <span>{run.contacts_scanned > 0 ? `${fmtPct(run.duplicates_count / run.contacts_scanned, 0)} da base` : "base vazia"}</span>
              </div>
            </div>
            <div className="uvTile">
              <div className="uvTileLabel">Grupos de duplicatas</div>
              <div className="uvTileValue">{fmtInt(run.clusters_count)}</div>
              <div className="uvTileFoot"><span>cada grupo é a mesma pessoa</span></div>
            </div>
            <div className="uvTile">
              <div className="uvTileLabel">Leads presos em duplicatas</div>
              <div className="uvTileValue">{fmtInt(run.leads_to_reassign)}</div>
              <div className="uvTileFoot"><span>precisam ir para o contato principal</span></div>
            </div>
          </div>

          <div className="uvRow uvRow-7-5">
            <section className="uvCard">
              <div className="uvCardHeader">
                <div>
                  <h3 className="uvCardTitle">Como as duplicatas foram identificadas</h3>
                  <p className="uvCardSubtitle">Critério que ligou os contatos de cada grupo</p>
                </div>
              </div>
              <ul className="uvBarList uvBarListStatic">
                {detail.data.match_breakdown.map((item) => (
                  <li key={item.label} className="uvBarListRow">
                    <span className="uvBarListName">{item.label}</span>
                    <span className="uvBarListTrack">
                      <span className="uvInlineBar" style={{ width: `${Math.max(item.share * 100, 2)}%`, background: "var(--uv-accent)" }} />
                    </span>
                    <span className="uvBarListValue">{fmtInt(item.count)} · {fmtPct(item.share, 0)}</span>
                  </li>
                ))}
              </ul>
              {detail.data.match_breakdown.length === 0 && <p className="uvEmpty">Nenhuma duplicata encontrada nesta varredura.</p>}
            </section>

            <section className="uvCard">
              <div className="uvCardHeader">
                <div>
                  <h3 className="uvCardTitle">Histórico de varreduras</h3>
                  <p className="uvCardSubtitle">Selecione uma para rever o relatório</p>
                </div>
              </div>
              <div className="uvRunList">
                {(runs.data ?? []).map((item) => (
                  <button key={item.id} type="button" className="uvRunItem" aria-pressed={item.id === runId} onClick={() => setSelectedRunId(item.id)}>
                    <strong>{formatDateTime(item.created_at)}</strong>
                    <span>{fmtInt(item.duplicates_count)} duplicados</span>
                    <span>{item.requested_by_name ?? "Usuário removido"}</span>
                    <span>{fmtInt(item.contacts_scanned)} contatos</span>
                  </button>
                ))}
              </div>
            </section>
          </div>

          <section className="uvCard">
            <div className="uvCardHeader">
              <div>
                <h3 className="uvCardTitle">Grupos de duplicatas</h3>
                <p className="uvCardSubtitle">
                  Abra os contatos no Kommo para conferir e unificar. Os grupos com lead preso aparecem primeiro.
                </p>
              </div>
              <label className="uvCheck">
                <input type="checkbox" checked={onlyWithLeads} onChange={(event) => setOnlyWithLeads(event.target.checked)} />
                Só grupos com lead a mover
              </label>
            </div>
            {detail.data.clusters.length === 0 ? (
              <p className="uvEmpty">Nenhum grupo neste filtro.</p>
            ) : (
              <div className="uvTableWrap">
                <table className="uvTable">
                  <thead>
                    <tr>
                      <th>Contato principal</th>
                      <th>Duplicata</th>
                      <th>Critério</th>
                      <th className="uvNum">Leads a mover</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.data.clusters.map((cluster) => (
                      <tr key={cluster.cluster_id}>
                        <td>
                          <a className="uvLink" href={contactUrl(cluster.master_contact_id)} target="_blank" rel="noreferrer">
                            {cluster.master_name} <ExternalLink size={12} />
                          </a>
                          <span className="uvCellSub">Contato #{cluster.master_contact_id}</span>
                        </td>
                        <td>
                          {cluster.duplicate_contacts.map((dup) => (
                            <div key={dup.id}>
                              <a className="uvLink" href={contactUrl(dup.id)} target="_blank" rel="noreferrer">
                                {dup.name ?? "Sem nome"} <ExternalLink size={12} />
                              </a>
                              <span className="uvCellSub">
                                #{dup.id} · criado em {formatDay(dup.created_at)} · {fmtInt(dup.leads_count)} {dup.leads_count === 1 ? "lead" : "leads"}
                              </span>
                            </div>
                          ))}
                        </td>
                        <td>{cluster.match_kind}</td>
                        <td className="uvNum">{fmtInt(cluster.leads_to_reassign)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="uvPager">
              <span>
                {fmtInt(detail.data.total_clusters)} grupos · página {detail.data.page} de {pageCount}
              </span>
              <div>
                <button type="button" className="uvBtnGhost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
                <button type="button" className="uvBtnGhost" disabled={page >= pageCount} onClick={() => setPage((p) => p + 1)}>Próxima</button>
              </div>
            </div>
          </section>
        </>
      ) : detail.error ? (
        <div className="uvNotice uvNoticeError" role="alert">
          <h4>Não foi possível abrir o relatório</h4>
          <p>{detail.error instanceof Error ? detail.error.message : "Erro inesperado."}</p>
        </div>
      ) : (
        <div className="uvSkeleton" style={{ height: 320 }} />
      )}
    </div>
  );
}
