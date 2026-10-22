import { useState, type FormEvent } from "react";
import {
  AlertTriangle,
  Bot,
  Check,
  CheckCircle2,
  Code2,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Globe,
  History,
  LayoutGrid,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";

import {
  useCreateWorkspaceSeoGeoAudit,
  useDeleteWorkspaceSeoGeoAudit,
  usePreviewSeoGeoAudit,
  useWorkspaceSeoGeoAudits,
} from "../../hooks/api";
import type { AuditCheckItem, SeoGeoAuditResponse } from "../../lib/api";

type TabId = "checklist_seo" | "checklist_geo" | "llms_txt" | "schema_jsonld" | "history";

export function SeoGeoStudio({ workspaceId }: { workspaceId?: string | null }) {
  const [urlInput, setUrlInput] = useState("");
  const [currentAudit, setCurrentAudit] = useState<SeoGeoAuditResponse | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("checklist_seo");
  const [copiedKind, setCopiedKind] = useState<string | null>(null);

  const previewMutation = usePreviewSeoGeoAudit();
  const createMutation = useCreateWorkspaceSeoGeoAudit(workspaceId ?? null);
  const deleteMutation = useDeleteWorkspaceSeoGeoAudit(workspaceId ?? null);
  const { data: history = [], refetch: refetchHistory } = useWorkspaceSeoGeoAudits(workspaceId ?? null);

  const isBusy = previewMutation.isPending || createMutation.isPending;

  function handleAudit(e: FormEvent) {
    e.preventDefault();
    if (!urlInput.trim()) return;

    if (workspaceId) {
      createMutation.mutate(urlInput.trim(), {
        onSuccess: (data) => {
          setCurrentAudit(data);
          setActiveTab("checklist_seo");
        },
      });
    } else {
      previewMutation.mutate(urlInput.trim(), {
        onSuccess: (data) => {
          setCurrentAudit(data);
          setActiveTab("checklist_seo");
        },
      });
    }
  }

  function handleCopy(text: string, kind: string) {
    void navigator.clipboard.writeText(text);
    setCopiedKind(kind);
    setTimeout(() => setCopiedKind(null), 2000);
  }

  function handleDownload(content: string, filename: string) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function getScoreColor(score: number): string {
    if (score >= 75) return "#2e9e5b";
    if (score >= 45) return "#ffab00";
    return "#ff5252";
  }

  return (
    <section className="content-grid" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Header & Input de URL */}
      <article className="surface large">
        <div className="surface-header">
          <Globe size={18} />
          <h3>Auditor Técnico de SEO & GEO (Generative Engine Optimization)</h3>
        </div>
        <div style={{ padding: "0 24px 20px" }}>
          <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 16 }}>
            Diagnóstico profundo de indexabilidade clássica (Google) e prontidão para <strong>motores generativos de IA (Perplexity, ChatGPT, Claude e Google AI Overviews)</strong>.
            Gera o arquivo <strong>`llms.txt`</strong> e código <strong>`JSON-LD Schema.org`</strong> com 1 clique.
          </p>

          <form onSubmit={handleAudit} style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ flex: "1 1 320px", display: "flex", alignItems: "center", position: "relative" }}>
              <Globe size={16} style={{ position: "absolute", left: 12, color: "var(--text-dim)" }} />
              <input
                type="text"
                placeholder="https://exemplo.com.br"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                style={{ width: "100%", paddingLeft: 36, fontSize: 13 }}
                required
              />
            </div>
            <button type="submit" className="primary" disabled={isBusy} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              {isBusy ? <RefreshCw size={14} className="spin" /> : <Search size={14} />}
              {isBusy ? "Auditando site ao vivo..." : "Auditar URL"}
            </button>
          </form>

          {(previewMutation.isError || createMutation.isError) && (
            <div className="notice error" style={{ marginTop: 12 }}>
              {((previewMutation.error || createMutation.error) as Error)?.message || "Falha ao auditar a URL."}
            </div>
          )}
        </div>
      </article>

      {/* Hero de Scores (SEO vs GEO) */}
      {currentAudit && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
            {/* Card SEO */}
            <article className="surface" style={{ padding: "18px 22px", borderRadius: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-dim)" }}>
                    Indexação Clássica (Google)
                  </span>
                  <h4 style={{ margin: "4px 0 0", fontSize: 16 }}>Score SEO Técnico</h4>
                </div>
                <div
                  style={{
                    fontSize: 26,
                    fontWeight: 800,
                    color: getScoreColor(currentAudit.seo_score),
                    background: "var(--surface-2, rgba(127,127,127,0.08))",
                    padding: "4px 14px",
                    borderRadius: 8,
                  }}
                >
                  {currentAudit.seo_score}
                  <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text-dim)" }}>/100</span>
                </div>
              </div>
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 12 }}>
                {currentAudit.seo_score >= 75
                  ? "✓ Boa conformidade com diretrizes do Google Search Central."
                  : "⚠ Há oportunidades importantes de correção em meta tags, H1 ou alt."}
              </p>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, background: "var(--surface-2, rgba(127,127,127,0.1))" }}>
                  {currentAudit.technical_audit.checks.filter((c) => c.status === "passed").length} aprovados
                </span>
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, background: "rgba(255,171,0,0.12)", color: "#ffab00" }}>
                  {currentAudit.technical_audit.checks.filter((c) => c.status === "warning").length} alertas
                </span>
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, background: "rgba(255,82,82,0.12)", color: "#ff5252" }}>
                  {currentAudit.technical_audit.checks.filter((c) => c.status === "failed").length} falhas
                </span>
              </div>
            </article>

            {/* Card GEO */}
            <article className="surface" style={{ padding: "18px 22px", borderRadius: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "#a855f7" }}>
                    Prontidão para IA (Perplexity & ChatGPT)
                  </span>
                  <h4 style={{ margin: "4px 0 0", fontSize: 16 }}>Score GEO & IA</h4>
                </div>
                <div
                  style={{
                    fontSize: 26,
                    fontWeight: 800,
                    color: getScoreColor(currentAudit.geo_score),
                    background: "var(--surface-2, rgba(127,127,127,0.08))",
                    padding: "4px 14px",
                    borderRadius: 8,
                  }}
                >
                  {currentAudit.geo_score}
                  <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text-dim)" }}>/100</span>
                </div>
              </div>
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 12 }}>
                {currentAudit.geo_audit.ai_search_readiness === "high"
                  ? "✓ Alta citabilidade: dados estruturados e sinais semânticos robustos."
                  : currentAudit.geo_audit.ai_search_readiness === "moderate"
                    ? "⚖ Média prontidão: publique o llms.txt para acelerar citação em IA."
                    : "✕ Baixa prontidão: LLMs terão dificuldade em citar a empresa com precisão."}
              </p>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
                <span
                  style={{
                    fontSize: 11,
                    padding: "2px 8px",
                    borderRadius: 4,
                    background: currentAudit.geo_audit.llms_txt_present ? "rgba(46,158,91,0.14)" : "rgba(255,171,0,0.14)",
                    color: currentAudit.geo_audit.llms_txt_present ? "#2e9e5b" : "#ffab00",
                    fontWeight: 600,
                  }}
                >
                  llms.txt: {currentAudit.geo_audit.llms_txt_present ? "Ativo" : "Não publicado"}
                </span>
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, background: "var(--surface-2, rgba(127,127,127,0.1))" }}>
                  {currentAudit.geo_audit.schemas_detected.length} Schemas JSON-LD
                </span>
              </div>
            </article>
          </div>

          {currentAudit.waf_detected && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 16px",
                borderRadius: 8,
                background: "rgba(255, 171, 0, 0.1)",
                border: "1px solid rgba(255, 171, 0, 0.3)",
                fontSize: 12,
                color: "#ffab00",
              }}
            >
              <ShieldAlert size={16} />
              <span>
                <strong>Proteção de WAF Ativa (Cloudflare):</strong> Foram analisados os metadados públicos e cabeçalhos retornados.
                Recomendamos a publicação do arquivo <code>/llms.txt</code> na raiz para garantir leitura desimpedida pelos robôs de IA.
              </span>
            </div>
          )}

          {/* Abas de Detalhes */}
          <article className="surface large">
            <div style={{ borderBottom: "1px solid var(--border)", display: "flex", gap: 4, padding: "12px 20px 0", flexWrap: "wrap" }}>
              <button
                type="button"
                className={activeTab === "checklist_seo" ? "primary" : ""}
                onClick={() => setActiveTab("checklist_seo")}
                style={{ fontSize: 12, padding: "6px 12px", display: "inline-flex", alignItems: "center", gap: 6 }}
              >
                <LayoutGrid size={13} /> Checklist SEO Técnico ({currentAudit.technical_audit.checks.length})
              </button>
              <button
                type="button"
                className={activeTab === "checklist_geo" ? "primary" : ""}
                onClick={() => setActiveTab("checklist_geo")}
                style={{ fontSize: 12, padding: "6px 12px", display: "inline-flex", alignItems: "center", gap: 6 }}
              >
                <Bot size={13} /> Prontidão GEO & IA ({currentAudit.geo_audit.checks.length})
              </button>
              <button
                type="button"
                className={activeTab === "llms_txt" ? "primary" : ""}
                onClick={() => setActiveTab("llms_txt")}
                style={{ fontSize: 12, padding: "6px 12px", display: "inline-flex", alignItems: "center", gap: 6 }}
              >
                <FileText size={13} /> Gerador llms.txt
              </button>
              <button
                type="button"
                className={activeTab === "schema_jsonld" ? "primary" : ""}
                onClick={() => setActiveTab("schema_jsonld")}
                style={{ fontSize: 12, padding: "6px 12px", display: "inline-flex", alignItems: "center", gap: 6 }}
              >
                <Code2 size={13} /> Gerador Schema.org
              </button>
              {workspaceId && (
                <button
                  type="button"
                  className={activeTab === "history" ? "primary" : ""}
                  onClick={() => {
                    setActiveTab("history");
                    void refetchHistory();
                  }}
                  style={{ fontSize: 12, padding: "6px 12px", display: "inline-flex", alignItems: "center", gap: 6 }}
                >
                  <History size={13} /> Histórico ({history.length})
                </button>
              )}
            </div>

            <div style={{ padding: "20px 24px" }}>
              {/* Tab 1: Checklist SEO */}
              {activeTab === "checklist_seo" && (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div style={{ marginBottom: 10, fontSize: 13, color: "var(--text-muted)" }}>
                    Página auditada: <strong>{currentAudit.page_title || currentAudit.target_url}</strong>
                  </div>
                  {currentAudit.technical_audit.checks.map((item) => (
                    <CheckRow key={item.id} item={item} />
                  ))}
                </div>
              )}

              {/* Tab 2: Checklist GEO */}
              {activeTab === "checklist_geo" && (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div style={{ marginBottom: 10, fontSize: 13, color: "var(--text-muted)" }}>
                    Critérios avaliados pelos algoritmos generativos (Perplexity, ChatGPT Search, Gemini):
                  </div>
                  {currentAudit.geo_audit.checks.map((item) => (
                    <CheckRow key={item.id} item={item} />
                  ))}
                </div>
              )}

              {/* Tab 3: Gerador llms.txt */}
              {activeTab === "llms_txt" && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
                    <p style={{ margin: 0, fontSize: 13, color: "var(--text-muted)" }}>
                      Arquivo gerado no padrão da indústria <code>/llms.txt</code>. Publique na raiz do seu site (ex: <code>https://seusite.com.br/llms.txt</code>).
                    </p>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        type="button"
                        onClick={() => handleCopy(currentAudit.generated_llms_txt, "llms")}
                        style={{ fontSize: 12, display: "inline-flex", alignItems: "center", gap: 6 }}
                      >
                        {copiedKind === "llms" ? <Check size={13} color="#2e9e5b" /> : <Copy size={13} />}
                        {copiedKind === "llms" ? "Copiado!" : "Copiar llms.txt"}
                      </button>
                      <button
                        type="button"
                        className="primary"
                        onClick={() => handleDownload(currentAudit.generated_llms_txt, "llms.txt")}
                        style={{ fontSize: 12, display: "inline-flex", alignItems: "center", gap: 6 }}
                      >
                        <Download size={13} /> Baixar llms.txt
                      </button>
                    </div>
                  </div>
                  <pre
                    style={{
                      background: "var(--surface-2, rgba(127,127,127,0.06))",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      padding: "16px",
                      fontSize: 12,
                      fontFamily: "monospace",
                      overflowX: "auto",
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {currentAudit.generated_llms_txt}
                  </pre>
                </div>
              )}

              {/* Tab 4: Gerador Schema.org */}
              {activeTab === "schema_jsonld" && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
                    <p style={{ margin: 0, fontSize: 13, color: "var(--text-muted)" }}>
                      Código estruturado JSON-LD recomendado. Cole dentro da tag <code>&lt;head&gt;</code> do site para ativar rich snippets no Google e IA.
                    </p>
                    <button
                      type="button"
                      className="primary"
                      onClick={() =>
                        handleCopy(
                          `<script type="application/ld+json">\n${JSON.stringify(currentAudit.generated_schema_jsonld, null, 2)}\n</script>`,
                          "schema",
                        )
                      }
                      style={{ fontSize: 12, display: "inline-flex", alignItems: "center", gap: 6 }}
                    >
                      {copiedKind === "schema" ? <Check size={13} color="#2e9e5b" /> : <Copy size={13} />}
                      {copiedKind === "schema" ? "Copiado!" : "Copiar Tag Script"}
                    </button>
                  </div>
                  <pre
                    style={{
                      background: "var(--surface-2, rgba(127,127,127,0.06))",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      padding: "16px",
                      fontSize: 12,
                      fontFamily: "monospace",
                      overflowX: "auto",
                    }}
                  >
                    {`<script type="application/ld+json">\n${JSON.stringify(currentAudit.generated_schema_jsonld, null, 2)}\n</script>`}
                  </pre>
                </div>
              )}

              {/* Tab 5: Histórico */}
              {activeTab === "history" && workspaceId && (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {history.map((item) => (
                    <div
                      key={item.id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                        padding: "10px 14px",
                        fontSize: 13,
                        flexWrap: "wrap",
                        gap: 10,
                      }}
                    >
                      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                        <strong>{item.page_title || item.target_url}</strong>
                        <span style={{ fontSize: 11, color: "var(--text-dim)" }}>
                          {item.target_url} · {new Date(item.created_at).toLocaleDateString("pt-BR")} às{" "}
                          {new Date(item.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: getScoreColor(item.seo_score) }}>
                          SEO: {item.seo_score}
                        </span>
                        <span style={{ fontSize: 12, fontWeight: 700, color: getScoreColor(item.geo_score) }}>
                          GEO: {item.geo_score}
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            setUrlInput(item.target_url);
                            createMutation.mutate(item.target_url, {
                              onSuccess: (res) => {
                                setCurrentAudit(res);
                                setActiveTab("checklist_seo");
                              },
                            });
                          }}
                          style={{ fontSize: 11, padding: "3px 8px" }}
                        >
                          Reauditar
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteMutation.mutate(item.id)}
                          style={{ fontSize: 11, padding: "3px 8px", color: "#ff5252" }}
                          title="Excluir auditoria"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                  ))}
                  {history.length === 0 && (
                    <p style={{ color: "var(--text-muted)", fontSize: 13 }}>Nenhuma auditoria anterior salva neste workspace.</p>
                  )}
                </div>
              )}
            </div>
          </article>
        </>
      )}
    </section>
  );
}

function CheckRow({ item }: { item: AuditCheckItem }) {
  const isPassed = item.status === "passed";
  const isWarning = item.status === "warning";

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "10px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        background: isPassed
          ? "rgba(46,158,91,0.03)"
          : isWarning
            ? "rgba(255,171,0,0.03)"
            : "rgba(255,82,82,0.03)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {isPassed ? (
            <CheckCircle2 size={16} color="#2e9e5b" />
          ) : isWarning ? (
            <AlertTriangle size={16} color="#ffab00" />
          ) : (
            <XCircle size={16} color="#ff5252" />
          )}
          <strong style={{ fontSize: 13 }}>{item.label}</strong>
          <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "var(--surface-2, rgba(127,127,127,0.12))", color: "var(--text-dim)" }}>
            {item.category}
          </span>
        </div>
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            textTransform: "uppercase",
            color: isPassed ? "#2e9e5b" : isWarning ? "#ffab00" : "#ff5252",
          }}
        >
          {isPassed ? "Aprovado" : isWarning ? "Atenção" : "Falha Crítica"}
        </span>
      </div>
      <p style={{ margin: "2px 0 0 24px", fontSize: 12, color: "var(--text-main)" }}>{item.detail}</p>
      {item.recommendation && (
        <p style={{ margin: "2px 0 0 24px", fontSize: 11, color: "var(--text-muted)" }}>
          <strong>Ação recomendada:</strong> {item.recommendation}
        </p>
      )}
    </div>
  );
}
