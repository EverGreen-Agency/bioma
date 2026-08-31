import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle, ChevronDown, ChevronRight, ExternalLink, Loader2, Plus, Search, Trash2,
} from "lucide-react";

import { api, type PlatformStudy, type PlatformVerdict } from "../../lib/api";

/**
 * Estudo de plataformas — build vs. buy vs. parar de construir.
 *
 * A tela existe para uma decisão específica do Eduardo: ele encontrou dezenas
 * de ferramentas que prometem partes do que o Bioma faz, e precisa saber de
 * cada uma se assina, integra, absorve, compra — ou se ela é sinal de que o
 * Bioma não deveria existir naquela frente.
 *
 * O que a tela NÃO promete: que um robô testou o produto. Criar conta e usar
 * uma SaaS exige cadastro e quase sempre cartão, e os termos da maioria proíbem
 * acesso automatizado autenticado. O que ela entrega é a leitura das páginas
 * públicas com fonte, e a FILA DE PRIORIDADE de quem merece uma tarde de teste
 * com as mãos.
 */

const VERDICT_LABELS: Record<PlatformVerdict, string> = {
  assinar: "Assinar",
  integrar: "Integrar via API",
  absorver: "Absorver no Bioma",
  comprar: "Buscar aquisição",
  monitorar: "Monitorar",
  descartar: "Descartar",
  repensar: "Repensar o Bioma",
};

const THREAT_LABELS: Record<string, string> = {
  critica: "faz melhor o que o Bioma faz",
  alta: "sobreposição forte",
  media: "sobreposição parcial",
  baixa: "pouca sobreposição",
  nenhuma: "sem sobreposição",
};

function PlatformRow({ study }: { study: PlatformStudy }) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [verdictNote, setVerdictNote] = useState("");

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ["platform-studies"] });
    await queryClient.invalidateQueries({ queryKey: ["platform-studies-overview"] });
  };

  const research = useMutation({
    mutationFn: () => api.researchPlatformStudy(study.id),
    onSuccess: invalidate,
  });
  const decide = useMutation({
    mutationFn: (verdict: PlatformVerdict) =>
      api.decidePlatformStudy(study.id, { verdict, verdict_note: verdictNote.trim() || null }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: () => api.deletePlatformStudy(study.id),
    onSuccess: invalidate,
  });

  const findings = study.findings ?? {};

  return (
    <div className="surface platform-row">
      {study.preview_image_url ? (
        <img src={study.preview_image_url} alt="" loading="lazy" />
      ) : (
        <div className="platform-row-placeholder" style={{ width: 46, height: 46, borderRadius: 6, background: "var(--bg-inset)" }} />
      )}

      <div style={{ minWidth: 0 }}>
        <div className="platform-row-name">
          <a href={study.url} target="_blank" rel="noreferrer">
            {study.name} <ExternalLink size={12} />
          </a>
          {study.category && <small>{study.category}</small>}
          {study.threat_level && (
            <span className={`platform-badge ${study.threat_level}`} title={THREAT_LABELS[study.threat_level]}>
              {study.threat_level === "critica" && <AlertTriangle size={10} />}
              {study.overlap_score !== null ? `${study.overlap_score}% sobreposição` : study.threat_level}
            </span>
          )}
          {study.verdict && <span className="platform-badge media">{VERDICT_LABELS[study.verdict]}</span>}
        </div>

        <p>
          {study.research_status === "pending" && "Ainda não pesquisada."}
          {study.research_status === "researching" && "Pesquisando…"}
          {study.research_status === "failed" && `Falhou: ${study.research_error}`}
          {study.research_status === "researched" && study.one_liner}
        </p>

        {study.research_status === "researched" && (
          <>
            <button
              className="copilot-trace-toggle"
              type="button"
              onClick={() => setExpanded((value) => !value)}
            >
              {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />} Análise completa
            </button>

            {expanded && (
              <div className="platform-detail">
                <div>
                  <h4>Preço</h4>
                  <span>{study.pricing_summary}</span>
                </div>
                {findings.who_its_for && (
                  <div><h4>Para quem</h4><span>{findings.who_its_for}</span></div>
                )}
                {(findings.what_it_does ?? []).length > 0 && (
                  <div>
                    <h4>O que faz</h4>
                    <ul>{findings.what_it_does!.map((item, i) => <li key={i}>{item}</li>)}</ul>
                  </div>
                )}
                {(findings.has_that_bioma_lacks ?? []).length > 0 && (
                  <div>
                    <h4>Tem e o Bioma não tem</h4>
                    <ul>{findings.has_that_bioma_lacks!.map((item, i) => <li key={i}>{item}</li>)}</ul>
                  </div>
                )}
                {(findings.bioma_has_that_it_lacks ?? []).length > 0 && (
                  <div>
                    <h4>O Bioma tem e ela não tem</h4>
                    <ul>{findings.bioma_has_that_it_lacks!.map((item, i) => <li key={i}>{item}</li>)}</ul>
                  </div>
                )}
                {findings.verdict_reason && (
                  <div>
                    <h4>Recomendação da análise: {findings.recommended_verdict && VERDICT_LABELS[findings.recommended_verdict]}</h4>
                    <span>{findings.verdict_reason}</span>
                  </div>
                )}
                {(findings.open_questions ?? []).length > 0 && (
                  <div>
                    <h4>Perguntas que só o teste responde</h4>
                    <ul>{findings.open_questions!.map((item, i) => <li key={i}>{item}</li>)}</ul>
                  </div>
                )}

                <div>
                  <h4>Páginas realmente lidas</h4>
                  <ul>
                    {study.sources.map((source) => (
                      <li key={source}>
                        <a href={source} target="_blank" rel="noreferrer" style={{ color: "inherit" }}>{source}</a>
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4>Sua decisão</h4>
                  <textarea
                    rows={2}
                    value={verdictNote}
                    placeholder="Por quê? (fica registrado com a decisão)"
                    onChange={(event) => setVerdictNote(event.target.value)}
                    style={{ width: "100%", padding: 7, borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-inset)", color: "var(--text)", fontFamily: "inherit", fontSize: 12 }}
                  />
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 6 }}>
                    {(Object.keys(VERDICT_LABELS) as PlatformVerdict[]).map((verdict) => (
                      <button
                        key={verdict}
                        className="mini-button"
                        type="button"
                        disabled={decide.isPending}
                        onClick={() => decide.mutate(verdict)}
                      >
                        {VERDICT_LABELS[verdict]}
                      </button>
                    ))}
                  </div>
                  {study.verdict_note && (
                    <p style={{ marginTop: 6 }}><strong>Registrado:</strong> {study.verdict_note}</p>
                  )}
                </div>

                <div style={{ color: "var(--text-faint)", fontSize: 11 }}>
                  {study.model} · {study.input_tokens}+{study.output_tokens} tokens ·{" "}
                  {study.cost_cents === null ? "custo sem preço na tabela" : `US$ ${(study.cost_cents / 100).toFixed(4)}`}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="platform-row-actions">
        {study.test_priority !== null && (
          <span style={{ fontSize: 11, color: "var(--text-faint)" }}>fila {study.test_priority}</span>
        )}
        <button
          className="mini-button"
          type="button"
          disabled={research.isPending}
          onClick={() => research.mutate()}
        >
          {research.isPending ? <Loader2 size={12} className="spin" /> : <Search size={12} />}
          {study.research_status === "researched" ? " Refazer" : " Pesquisar"}
        </button>
        <button
          className="mini-button"
          type="button"
          onClick={() => remove.mutate()}
          title="Remover da lista"
        >
          <Trash2 size={12} />
        </button>
        {research.error && (
          <span style={{ fontSize: 11, color: "#ff5252", maxWidth: 180, textAlign: "right" }}>
            {research.error.message}
          </span>
        )}
      </div>
    </div>
  );
}

export function PlatformStudiesView() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<string>("");
  const [newUrls, setNewUrls] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  const overview = useQuery({
    queryKey: ["platform-studies-overview"],
    queryFn: () => api.platformStudyOverview(),
  });
  const studies = useQuery({
    queryKey: ["platform-studies", filter],
    queryFn: () => api.platformStudies(filter ? { research_status: filter } : {}),
  });

  const addMany = useMutation({
    mutationFn: (urls: string[]) => api.addPlatformStudies({ urls, targets: ["bioma", "foton"] }),
    onSuccess: async () => {
      setNewUrls("");
      setShowAdd(false);
      await queryClient.invalidateQueries({ queryKey: ["platform-studies"] });
      await queryClient.invalidateQueries({ queryKey: ["platform-studies-overview"] });
    },
  });

  const data = overview.data;

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto", color: "var(--text)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 18 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, margin: 0 }}>Estudo de plataformas</h1>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: "0.9rem", maxWidth: 620 }}>
            De cada ferramenta encontrada: assinar, integrar, absorver, comprar — ou é sinal de
            que o Bioma não deveria construir aquela frente. A análise lê as páginas públicas e
            cita quais leu; o teste com as mãos continua sendo seu, e a fila diz por onde começar.
          </p>
        </div>
        <button className="primary-button" type="button" onClick={() => setShowAdd((value) => !value)}>
          <Plus size={15} /> Adicionar
        </button>
      </div>

      {showAdd && (
        <form
          className="surface"
          style={{ padding: 14, marginBottom: 16, display: "grid", gap: 8 }}
          onSubmit={(event) => {
            event.preventDefault();
            const urls = newUrls.split(/[\s,]+/).map((item) => item.trim()).filter(Boolean);
            if (urls.length) addMany.mutate(urls);
          }}
        >
          <label style={{ fontSize: 12, color: "var(--text-dim)" }}>
            Cole quantas URLs quiser — uma por linha, ou separadas por espaço.
          </label>
          <textarea
            rows={4}
            value={newUrls}
            placeholder="https://exemplo.com&#10;outra.com"
            onChange={(event) => setNewUrls(event.target.value)}
            style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-inset)", color: "var(--text)", fontFamily: "inherit" }}
          />
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="primary-button" type="submit" disabled={addMany.isPending}>
              {addMany.isPending ? "Salvando…" : "Salvar na lista"}
            </button>
            <span style={{ fontSize: 11, color: "var(--text-faint)" }}>
              Salvar é de graça; a pesquisa é disparada uma a uma, porque gasta token.
            </span>
          </div>
          {addMany.error && <span style={{ color: "#ff5252", fontSize: 12 }}>{addMany.error.message}</span>}
        </form>
      )}

      {data && (
        <div className="platform-grid" style={{ marginBottom: 16 }}>
          <div className="platform-overview">
            <div className="surface"><strong>{data.total}</strong><span>na lista</span></div>
            <div className="surface"><strong>{data.pending}</strong><span>sem pesquisa</span></div>
            <div className="surface"><strong>{data.researched}</strong><span>pesquisadas</span></div>
            <div className="surface"><strong>{data.decided}</strong><span>com decisão</span></div>
            <div className="surface"><strong>{data.high_threat}</strong><span>sobreposição alta</span></div>
            <div className="surface">
              <strong>{data.cost_cents === 0 ? "—" : `US$ ${(data.cost_cents / 100).toFixed(2)}`}</strong>
              <span>gasto em análise</span>
            </div>
          </div>

          {data.critical_overlap.length > 0 && (
            <div className="platform-alert">
              <h3><AlertTriangle size={14} /> Plataformas que pesam na decisão de continuar</h3>
              <p style={{ margin: "0 0 8px", fontSize: 12, color: "var(--text-dim)" }}>
                Fazem, no todo ou em parte, o que o Bioma se propõe a fazer. Não significa parar —
                significa comparar a sério antes de investir mais naquela frente.
              </p>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                {data.critical_overlap.map((item) => (
                  <li key={item.id} style={{ marginBottom: 3 }}>
                    <a href={item.url} target="_blank" rel="noreferrer" style={{ color: "inherit" }}>
                      <strong>{item.name}</strong>
                    </a>{" "}
                    — {item.one_liner} <span style={{ color: "var(--text-faint)" }}>({item.overlap_score}%)</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        {[
          ["", "Todas"],
          ["pending", "Sem pesquisa"],
          ["researched", "Pesquisadas"],
          ["failed", "Falharam"],
        ].map(([value, label]) => (
          <button
            key={value}
            className={`mini-button ${filter === value ? "selected" : ""}`}
            type="button"
            onClick={() => setFilter(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {studies.isLoading && <p style={{ color: "var(--text-dim)" }}>Carregando…</p>}
      {studies.error && <div className="notice error">{studies.error.message}</div>}

      <div className="platform-grid">
        {studies.data?.map((study) => <PlatformRow key={study.id} study={study} />)}
        {studies.data?.length === 0 && (
          <p style={{ color: "var(--text-dim)", padding: 28, textAlign: "center" }}>
            Nada nesta lista ainda.
          </p>
        )}
      </div>
    </div>
  );
}

export default PlatformStudiesView;
