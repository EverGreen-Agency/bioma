import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ArrowLeft,
  BookOpenCheck,
  Check,
  Download,
  ExternalLink,
  FileSearch,
  LoaderCircle,
  Search,
  Sparkles,
} from "lucide-react";

import {
  api,
  type MarketResearchDetail,
  type MarketResearchFocusOption,
  type MarketResearchRefinement,
  type MarketResearchSource,
  type MarketResearchSummary,
} from "../lib/api";


type ResearchStep = "sector" | "focus" | "report";

const statusLabels: Record<MarketResearchSummary["status"], string> = {
  running: "Em execução",
  completed: "Concluída",
  failed: "Falhou",
  archived: "Arquivada",
};

const priorityLabels = { high: "Alta", medium: "Média", low: "Baixa" } as const;
const funnelLabels = {
  awareness: "Descoberta",
  consideration: "Consideração",
  decision: "Decisão",
  retention: "Retenção",
} as const;

export function MarketResearchStudio({
  workspaceId,
  accessRole,
}: {
  workspaceId: string;
  accessRole: string;
}) {
  const [step, setStep] = useState<ResearchStep>("sector");
  const [sector, setSector] = useState("");
  const [geographicScope, setGeographicScope] = useState("Brasil");
  const [objective, setObjective] = useState("");
  const [refinement, setRefinement] = useState<MarketResearchRefinement | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [history, setHistory] = useState<MarketResearchSummary[]>([]);
  const [activeResearch, setActiveResearch] = useState<MarketResearchDetail | null>(null);
  const [busy, setBusy] = useState<"history" | "refine" | "generate" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canManage = ["platform_admin", "tenant_admin", "workspace_manager", "operator"].includes(accessRole);
  const selectedFocus = useMemo(
    () => refinement?.focus_options.filter((option) => selectedKeys.has(option.key)) ?? [],
    [refinement, selectedKeys],
  );

  useEffect(() => {
    let cancelled = false;
    setBusy("history");
    setError(null);
    void api.marketResearches(workspaceId)
      .then((items) => {
        if (!cancelled) setHistory(items);
      })
      .catch((caught: Error) => {
        if (!cancelled) setError(caught.message);
      })
      .finally(() => {
        if (!cancelled) setBusy((current) => current === "history" ? null : current);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  async function refineSector() {
    if (sector.trim().length < 2) return;
    setBusy("refine");
    setError(null);
    try {
      const result = await api.refineMarketResearch(workspaceId, {
        sector: sector.trim(),
        geographic_scope: geographicScope.trim() || "Brasil",
        objective: objective.trim() || null,
      });
      setRefinement(result);
      setSelectedKeys(new Set(result.focus_options.map((option) => option.key)));
      setStep("focus");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível refinar o setor.");
    } finally {
      setBusy(null);
    }
  }

  async function generateResearch() {
    if (!refinement || selectedFocus.length === 0) return;
    setBusy("generate");
    setError(null);
    try {
      const result = await api.createMarketResearch(workspaceId, {
        sector: sector.trim(),
        geographic_scope: geographicScope.trim() || "Brasil",
        objective: objective.trim() || null,
        selected_focus: selectedFocus,
      });
      setActiveResearch(result);
      setHistory((items) => [result, ...items.filter((item) => item.id !== result.id)]);
      setStep("report");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível concluir a pesquisa.");
      const items = await api.marketResearches(workspaceId).catch(() => null);
      if (items) setHistory(items);
    } finally {
      setBusy(null);
    }
  }

  async function openResearch(research: MarketResearchSummary) {
    setBusy("history");
    setError(null);
    try {
      const result = await api.marketResearch(workspaceId, research.id);
      setActiveResearch(result);
      setStep("report");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível abrir a pesquisa.");
    } finally {
      setBusy(null);
    }
  }

  function toggleFocus(option: MarketResearchFocusOption) {
    setSelectedKeys((current) => {
      const next = new Set(current);
      if (next.has(option.key)) next.delete(option.key);
      else next.add(option.key);
      return next;
    });
  }

  function startNewResearch() {
    setStep("sector");
    setRefinement(null);
    setSelectedKeys(new Set());
    setActiveResearch(null);
    setError(null);
  }

  return (
    <section className="market-research-studio">
      <header className="market-research-heading">
        <div>
          <span className="eyebrow">Inteligência de mercado</span>
          <h1>Pesquisa setorial rastreável</h1>
          <p>
            Prepare a equipe para entrar em um novo nicho de prospecção: linguagem, dores,
            argumentos comerciais, oportunidades de Growth e pautas para Social Media.
          </p>
        </div>
      </header>

      {canManage && (
        <div className="market-research-steps" aria-label="Etapas da pesquisa">
          <ResearchStepCard active={step === "sector"} done={step !== "sector"} icon={Search} number="1" title="Defina o setor" />
          <ResearchStepCard active={step === "focus"} done={step === "report"} icon={Sparkles} number="2" title="Refine o foco" />
          <ResearchStepCard active={step === "report"} done={false} icon={BookOpenCheck} number="3" title="Use o relatório" />
        </div>
      )}

      {error && <div className="notice error" role="alert">{error}</div>}

      <div className="market-research-layout">
        <main>
          {!canManage && step !== "report" && (
            <section className="market-research-form">
              <h2>Pesquisas compartilhadas com você</h2>
              <p>Selecione no histórico um relatório que a equipe publicou neste workspace.</p>
            </section>
          )}

          {canManage && step === "sector" && (
            <section className="market-research-form">
              <label>
                Setor ou nicho
                <input
                  value={sector}
                  onChange={(event) => setSector(event.target.value)}
                  placeholder="Ex.: energia solar para empresas, hotelaria, clínicas..."
                  maxLength={120}
                  autoFocus
                />
                <small>{sector.length}/120 caracteres</small>
              </label>
              <div className="market-research-form-grid">
                <label>
                  Recorte geográfico
                  <input
                    value={geographicScope}
                    onChange={(event) => setGeographicScope(event.target.value)}
                    maxLength={120}
                  />
                </label>
                <label>
                  Objetivo específico <span>(opcional)</span>
                  <input
                    value={objective}
                    onChange={(event) => setObjective(event.target.value)}
                    placeholder="Ex.: preparar cold calls para integradores B2B"
                    maxLength={2000}
                  />
                </label>
              </div>
              <button
                className="primary-button"
                type="button"
                disabled={sector.trim().length < 2 || busy === "refine"}
                onClick={() => void refineSector()}
              >
                {busy === "refine" ? <LoaderCircle className="spin" size={16} /> : <Sparkles size={16} />}
                Refinar pesquisa
              </button>
            </section>
          )}

          {canManage && step === "focus" && refinement && (
            <section className="market-research-focus">
              <div className="market-research-understood">
                <span>Entendemos</span>
                <strong>{refinement.sector_interpretation}</strong>
                {refinement.generation_mode === "preview" && (
                  <em>Prévia local — os recortes ainda não foram pesquisados na web.</em>
                )}
              </div>
              <p>Selecione os recortes que devem entrar no relatório.</p>
              <div className="market-focus-options">
                {refinement.focus_options.map((option) => {
                  const selected = selectedKeys.has(option.key);
                  return (
                    <button
                      className={selected ? "selected" : ""}
                      type="button"
                      key={option.key}
                      aria-pressed={selected}
                      onClick={() => toggleFocus(option)}
                    >
                      <span className="market-focus-check">{selected && <Check size={15} />}</span>
                      <span>
                        <strong>{option.label}</strong>
                        <small>{option.description}</small>
                      </span>
                    </button>
                  );
                })}
              </div>
              {refinement.assumptions.length > 0 && (
                <div className="market-research-assumptions">
                  <strong>Hipóteses para revisão</strong>
                  <ul>{refinement.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
              )}
              <div className="market-research-actions">
                <button className="secondary-button" type="button" onClick={() => setStep("sector")}>
                  <ArrowLeft size={15} /> Editar setor
                </button>
                <button
                  className="primary-button"
                  type="button"
                  disabled={selectedFocus.length === 0 || busy === "generate"}
                  onClick={() => void generateResearch()}
                >
                  <FileSearch size={16} /> Gerar pesquisa
                </button>
              </div>
            </section>
          )}

          {step === "report" && activeResearch && (
            <MarketResearchReportView
              research={activeResearch}
              canManage={canManage}
              onNew={startNewResearch}
            />
          )}
        </main>

        <aside className="market-research-history">
          <div>
            <strong>Pesquisas deste workspace</strong>
            <span>{history.length}</span>
          </div>
          {busy === "history" && history.length === 0 && <small>Carregando histórico...</small>}
          {history.length === 0 && busy !== "history" && (
            <small>Nenhuma pesquisa persistida. O banco não é populado automaticamente.</small>
          )}
          {history.map((item) => (
            <button
              className={activeResearch?.id === item.id ? "active" : ""}
              type="button"
              key={item.id}
              onClick={() => void openResearch(item)}
            >
              <span>
                <strong>{item.sector}</strong>
                <small>v{item.version} · {item.geographic_scope}</small>
              </span>
              <em className={item.status}>{statusLabels[item.status]}</em>
            </button>
          ))}
        </aside>
      </div>

      {busy === "generate" && (
        <div className="market-research-progress" role="status" aria-live="polite">
          <div>
            <LoaderCircle className="spin" size={28} />
            <strong>Pesquisando e confrontando fontes...</strong>
            <p>Não exibimos porcentagem fictícia. O relatório será salvo quando a busca e a validação terminarem.</p>
          </div>
        </div>
      )}
    </section>
  );
}

function ResearchStepCard({
  active,
  done,
  icon: Icon,
  number,
  title,
}: {
  active: boolean;
  done: boolean;
  icon: typeof Search;
  number: string;
  title: string;
}) {
  return (
    <div className={`${active ? "active" : ""} ${done ? "done" : ""}`}>
      <span><Icon size={18} /></span>
      <strong>{number}. {title}</strong>
    </div>
  );
}

function MarketResearchReportView({
  research,
  canManage,
  onNew,
}: {
  research: MarketResearchDetail;
  canManage: boolean;
  onNew: () => void;
}) {
  const report = research.report;
  if (!report) {
    return (
      <section className="market-research-empty-report">
        <h2>Pesquisa v{research.version} sem relatório concluído</h2>
        <p>{research.error_message ?? "A execução ainda não produziu conteúdo."}</p>
        <button className="secondary-button" type="button" onClick={onNew}>Nova pesquisa</button>
      </section>
    );
  }

  return (
    <article className="market-research-report">
      <header className="market-report-header">
        <div>
          <span className="eyebrow">Pesquisa de mercado · v{research.version}</span>
          <h2>{report.title}</h2>
          <p>
            {research.source_count} fontes · {research.generation_mode === "live" ? "Pesquisa web" : "Prévia local"} ·{" "}
            {new Date(research.created_at).toLocaleString("pt-BR")}
          </p>
        </div>
        <div className="market-report-actions">
          <button className="primary-button" type="button" onClick={() => window.print()}>
            <Download size={15} /> Exportar PDF
          </button>
          {canManage && (
            <button className="secondary-button" type="button" onClick={onNew}>Nova pesquisa</button>
          )}
        </div>
      </header>

      {research.generation_mode === "preview" && (
        <div className="notice">
          Este relatório é uma prévia estrutural sem pesquisa externa. Não use como evidência em prospecção.
        </div>
      )}

      <ReportSection title="Resumo executivo">
        <p>{report.executive_summary}</p>
      </ReportSection>

      <ReportSection title="1. Visão geral do mercado">
        <p>{report.market_overview.description}</p>
        <ReportList title="Tamanho e segmentos" items={report.market_overview.market_size_and_segments} />
        <ReportList title="Modelos de negócio" items={report.market_overview.business_models} />
        <h4>Perspectivas de crescimento</h4>
        <p>{report.market_overview.growth_outlook}</p>
        <ReportList title="Tendências" items={report.market_overview.trends} />
        <SourceLinks urls={report.market_overview.source_urls} sources={research.sources} />
      </ReportSection>

      <ReportSection title="2. Processo comercial">
        <ReportList title="Estratégias de venda" items={report.commercial_process.sales_strategies} />
        <ReportList title="Aquisição e retenção" items={report.commercial_process.acquisition_and_retention} />
        <ReportList title="Jornada de compra" items={report.commercial_process.buying_journey} />
        <ReportList title="Sinais de qualificação" items={report.commercial_process.qualification_signals} />
        <SourceLinks urls={report.commercial_process.source_urls} sources={research.sources} />
      </ReportSection>

      <ReportSection title="3. Desafios e impacto">
        <div className="market-report-cards">
          {report.challenges.map((item) => (
            <div key={`${item.challenge}-${item.business_impact}`}>
              <h4>{item.challenge}</h4>
              <p><strong>Impacto:</strong> {item.business_impact}</p>
              <p><strong>Oportunidade:</strong> {item.opportunity}</p>
              <SourceLinks urls={item.source_urls} sources={research.sources} compact />
            </div>
          ))}
        </div>
      </ReportSection>

      <ReportSection title="4. Referências de mercado">
        <div className="market-report-cards">
          {report.market_leaders.map((leader) => (
            <div key={`${leader.name}-${leader.segment}`}>
              <h4>{leader.name}</h4>
              <small>{leader.segment}</small>
              <p>{leader.success_strategy}</p>
              <SourceLinks urls={leader.source_urls} sources={research.sources} compact />
            </div>
          ))}
        </div>
      </ReportSection>

      <ReportSection title="5. Terminologia">
        <dl className="market-terminology">
          {report.terminology.map((item) => (
            <div key={item.term}>
              <dt>{item.term}</dt>
              <dd>{item.definition}</dd>
            </div>
          ))}
        </dl>
      </ReportSection>

      <ReportSection title="6. Oportunidades para Growth">
        <div className="market-report-cards">
          {report.growth_opportunities.map((item) => (
            <div key={`${item.opportunity}-${item.recommended_service}`}>
              <span className={`market-priority ${item.priority}`}>{priorityLabels[item.priority]}</span>
              <h4>{item.opportunity}</h4>
              <p><strong>Serviço:</strong> {item.recommended_service}</p>
              <p>{item.rationale}</p>
              <SourceLinks urls={item.source_urls} sources={research.sources} compact />
            </div>
          ))}
        </div>
      </ReportSection>

      <ReportSection title="7. Playbook de prospecção">
        <ReportList title="Ângulos de abertura" items={report.prospecting_playbook.opening_angles} />
        <ReportList title="Perguntas de qualificação" items={report.prospecting_playbook.qualification_questions} />
        <ReportList title="Objeções prováveis" items={report.prospecting_playbook.likely_objections} />
        <ReportList title="Cuidados de credibilidade" items={report.prospecting_playbook.credibility_cautions} />
      </ReportSection>

      <ReportSection title="8. Oportunidades editoriais">
        <div className="market-report-cards">
          {report.content_opportunities.map((item) => (
            <div key={`${item.theme}-${item.recommended_format}`}>
              <small>{funnelLabels[item.funnel_stage]} · {item.recommended_format}</small>
              <h4>{item.theme}</h4>
              <p>{item.rationale}</p>
              <SourceLinks urls={item.source_urls} sources={research.sources} compact />
            </div>
          ))}
        </div>
      </ReportSection>

      {report.caveats.length > 0 && (
        <ReportSection title="Limitações e cuidados">
          <ul>{report.caveats.map((item) => <li key={item}>{item}</li>)}</ul>
        </ReportSection>
      )}

      <ReportSection title={`Fontes consultadas (${research.sources.length})`}>
        <ol className="market-source-list">
          {research.sources.map((source) => (
            <li key={source.url}>
              <a href={source.url} target="_blank" rel="noreferrer">
                {source.title || source.publisher || source.url} <ExternalLink size={12} />
              </a>
              {source.publisher && source.title && <small>{source.publisher}</small>}
            </li>
          ))}
        </ol>
      </ReportSection>
    </article>
  );
}

function ReportSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="market-report-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function ReportList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <>
      <h4>{title}</h4>
      <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>
    </>
  );
}

function SourceLinks({
  urls,
  sources,
  compact = false,
}: {
  urls: string[];
  sources: MarketResearchSource[];
  compact?: boolean;
}) {
  if (urls.length === 0) return null;
  const sourceByUrl = new Map(sources.map((source) => [source.url, source]));
  return (
    <div className={`market-inline-sources ${compact ? "compact" : ""}`}>
      <span>Fontes:</span>
      {urls.map((url, index) => {
        const source = sourceByUrl.get(url);
        return (
          <a href={url} target="_blank" rel="noreferrer" key={url}>
            {source?.publisher || source?.title || `Fonte ${index + 1}`}
          </a>
        );
      })}
    </div>
  );
}
