import { useState, type FormEvent } from "react";
import { CheckCircle2, ExternalLink, MapPin, Search, Send, Sparkles, TrendingUp, Upload, XCircle } from "lucide-react";

import {
  useAuditLocalRadarProspect,
  useCreateLocalRadarScan,
  useImportLocalRadarScan,
  useDecideLocalRadarProspect,
  useLocalRadarScan,
  useLocalRadarScans,
  useSendLocalRadarProspect,
  useUpdateLocalRadarMessage,
} from "../hooks/useBiomaApi";
import type { LocalRadarImportRow, LocalRadarProspect, WhatsAppProviderType } from "../lib/api";


/**
 * Converte o texto colado de uma planilha de scrape do Google Maps (extensões
 * tipo Instant Data Scraper exportam CSV/TSV) em linhas de prospect.
 * Roda 100% no navegador: nenhuma chamada de API é gasta nesse caminho.
 *
 * Detecta o separador e casa as colunas por nome de cabeçalho, aceitando os
 * rótulos mais comuns em pt/en. Coluna que não é reconhecida é ignorada — o
 * import nunca adivinha valor de campo ausente.
 */
const HEADER_ALIASES: Record<keyof LocalRadarImportRow, string[]> = {
  name: ["name", "nome", "title", "business", "empresa", "negocio", "negócio"],
  address: ["address", "endereco", "endereço", "location", "localizacao", "localização"],
  phone: ["phone", "telefone", "tel", "celular", "whatsapp"],
  website: ["website", "site", "url", "web", "página", "pagina"],
  google_maps_url: ["google_maps_url", "maps", "link", "href", "maps_url", "google maps"],
  rating: ["rating", "nota", "avaliacao", "avaliação", "stars", "estrelas"],
  rating_count: ["rating_count", "reviews", "avaliacoes", "avaliações", "num_reviews", "qtd"],
};

function normalizeHeader(value: string) {
  return value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/^"|"$/g, "");
}

function parseNumber(value: string | undefined): number | null {
  if (!value) return null;
  // "4,8" (pt-BR) e "1.234 avaliações" chegam da planilha; extraímos o número.
  const cleaned = value.replace(/\./g, "").replace(",", ".").replace(/[^\d.]/g, "");
  const parsed = Number.parseFloat(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function countOf(line: string, character: string) {
  return line.split(character).length - 1;
}

/**
 * Quebra uma linha respeitando aspas.
 *
 * `line.split(separator)` parecia bastar até aparecer o caso normal do Google
 * Maps: `"Av. Rondon Pacheco, 1234, Uberlândia"` numa exportação CSV. Aquele
 * split partia o endereço em três células e empurrava todas as colunas
 * seguintes para o lado — telefone virava pedaço de endereço, nota virava
 * telefone. Silenciosamente: cada linha continuava "válida".
 *
 * Aspas duplicadas (`""`) são o escape do formato CSV para uma aspa literal.
 */
function splitRespectingQuotes(line: string, separator: string): string[] {
  const cells: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      if (inQuotes && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === separator && !inQuotes) {
      cells.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  cells.push(current);
  return cells;
}

function parsePastedProspects(raw: string): { rows: LocalRadarImportRow[]; ignored: number } {
  const lines = raw.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length < 2) return { rows: [], ignored: 0 };

  // Extensões exportam TSV (colar direto da planilha), CSV ou CSV-ponto-e-vírgula.
  const candidates: Array<[string, number]> = [
    ["\t", countOf(lines[0], "\t")],
    [";", countOf(lines[0], ";")],
    [",", countOf(lines[0], ",")],
  ];
  const separator = candidates.sort((a, b) => b[1] - a[1])[0][0];

  const headers = splitRespectingQuotes(lines[0], separator).map(normalizeHeader);
  const indexFor = (field: keyof LocalRadarImportRow) =>
    headers.findIndex((header) => HEADER_ALIASES[field].some((alias) => header === normalizeHeader(alias)));

  const columns = {
    name: indexFor("name"),
    address: indexFor("address"),
    phone: indexFor("phone"),
    website: indexFor("website"),
    google_maps_url: indexFor("google_maps_url"),
    rating: indexFor("rating"),
    rating_count: indexFor("rating_count"),
  };

  // Sem coluna de nome não há prospect: devolve tudo como ignorado em vez de
  // inventar nomes a partir de outra coluna.
  if (columns.name < 0) return { rows: [], ignored: lines.length - 1 };

  const rows: LocalRadarImportRow[] = [];
  let ignored = 0;
  for (const line of lines.slice(1)) {
    const cells = splitRespectingQuotes(line, separator).map((cell) => cell.trim());
    const name = cells[columns.name];
    if (!name) {
      ignored += 1;
      continue;
    }
    const at = (index: number) => (index >= 0 ? cells[index] || undefined : undefined);
    const rating = parseNumber(at(columns.rating));
    rows.push({
      name,
      address: at(columns.address) ?? null,
      phone: at(columns.phone) ?? null,
      website: at(columns.website) ?? null,
      google_maps_url: at(columns.google_maps_url) ?? null,
      rating: rating !== null && rating >= 0 && rating <= 5 ? rating : null,
      rating_count: parseNumber(at(columns.rating_count)),
    });
  }
  return { rows, ignored };
}

const reviewLabels: Record<LocalRadarProspect["review_status"], { label: string; color: string }> = {
  new: { label: "Novo", color: "var(--text-dim)" },
  audited: { label: "Auditado", color: "#4f8ef7" },
  approved: { label: "Aprovado", color: "#2e9e5b" },
  rejected: { label: "Rejeitado", color: "#ff5252" },
  sent: { label: "Enviado", color: "#8a6ff0" },
};

function scoreColor(score: number | null) {
  if (score === null) return "var(--text-dim)";
  if (score <= 40) return "#ff5252";
  if (score <= 70) return "#ffab00";
  return "#2e9e5b";
}

export function LocalRadarStudio() {
  const [niche, setNiche] = useState("");
  const [city, setCity] = useState("");
  const [limit, setLimit] = useState(20);
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [expandedProspectId, setExpandedProspectId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const [pasted, setPasted] = useState("");
  const [showImport, setShowImport] = useState(false);

  const { data: scans = [] } = useLocalRadarScans(true);
  const { data: scanDetail } = useLocalRadarScan(selectedScanId);
  const createScan = useCreateLocalRadarScan();
  const importScan = useImportLocalRadarScan();

  const parsed = pasted.trim() ? parsePastedProspects(pasted) : null;

  function handleImport() {
    if (!parsed || parsed.rows.length === 0) return;
    setFeedback(null);
    importScan.mutate(
      { niche: niche.trim() || "importado", city: city.trim() || "planilha", rows: parsed.rows },
      {
        onSuccess: (scan) => {
          setSelectedScanId(scan.id);
          setPasted("");
          setShowImport(false);
          setFeedback(`${scan.prospect_count} negócios importados da planilha (nenhuma chamada de API gasta).`);
        },
      },
    );
  }

  function handleCreateScan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    createScan.mutate(
      { niche: niche.trim(), city: city.trim(), limit },
      {
        onSuccess: (scan) => {
          setSelectedScanId(scan.id);
          setFeedback(`${scan.prospect_count} negócios encontrados para "${scan.query_text}".`);
        },
      },
    );
  }

  return (
    <section className="content-grid" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <article className="surface large">
        <div className="surface-header">
          <MapPin size={18} />
          <h3>Radar Local — prospecção de negócios locais</h3>
        </div>
        <div style={{ padding: "0 24px 20px" }}>
          <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 14 }}>
            Busca negócios reais no Google Maps por nicho e cidade, audita a presença digital de cada um e
            monta a fila de abordagem. <strong>Nenhuma mensagem sai sem a sua aprovação.</strong>
          </p>
          <form onSubmit={handleCreateScan} style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
              Nicho
              <input value={niche} onChange={(e) => setNiche(e.target.value)} placeholder="clínica odontológica" required minLength={2} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
              Cidade
              <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="Uberlândia MG" required minLength={2} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
              Limite
              <input type="number" min={1} max={60} value={limit} onChange={(e) => setLimit(Number(e.target.value) || 20)} style={{ width: 70 }} />
            </label>
            <button type="submit" className="primary" disabled={createScan.isPending}>
              <Search size={14} /> {createScan.isPending ? "Buscando..." : "Buscar negócios"}
            </button>
          </form>
          <button
            type="button"
            onClick={() => setShowImport(!showImport)}
            style={{ marginTop: 10, fontSize: 12 }}
          >
            <Upload size={13} /> {showImport ? "Fechar import" : "Importar planilha (sem custo de API)"}
          </button>

          {showImport && (
            <div style={{ marginTop: 10, border: "1px dashed var(--border)", borderRadius: 8, padding: "12px 14px" }}>
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
                Cole aqui o conteúdo copiado da planilha da sua extensão de scrape (Ctrl+A, Ctrl+C na aba
                da planilha, ou o CSV exportado). O parse acontece no seu navegador; nada é enviado ao
                Google. Cabeçalhos reconhecidos: nome, endereço, telefone, site, nota, avaliações.
              </p>
              <textarea
                value={pasted}
                onChange={(e) => setPasted(e.target.value)}
                rows={6}
                placeholder={"nome\tendereço\ttelefone\tsite\tnota\tavaliações"}
                style={{ width: "100%", fontFamily: "monospace", fontSize: 11 }}
              />
              {parsed && (
                <p style={{ fontSize: 12, marginTop: 6, color: parsed.rows.length ? "#2e9e5b" : "#ff5252" }}>
                  {parsed.rows.length} linha(s) reconhecida(s)
                  {parsed.ignored > 0 ? ` · ${parsed.ignored} ignorada(s) por falta de nome` : ""}
                  {parsed.rows.length === 0 ? " — confira se a primeira linha é o cabeçalho com uma coluna de nome." : ""}
                </p>
              )}
              <button
                type="button"
                className="primary"
                style={{ marginTop: 8 }}
                disabled={!parsed || parsed.rows.length === 0 || importScan.isPending}
                onClick={handleImport}
              >
                <Upload size={13} /> {importScan.isPending ? "Importando..." : `Importar ${parsed?.rows.length ?? 0} negócios`}
              </button>
              {importScan.isError && (
                <div className="notice error" style={{ marginTop: 8 }}>
                  {importScan.error instanceof Error ? importScan.error.message : "Falha no import."}
                </div>
              )}
            </div>
          )}

          {createScan.isError && (
            <div className="notice error" style={{ marginTop: 10 }}>
              {createScan.error instanceof Error ? createScan.error.message : "Falha na busca."}
            </div>
          )}
          {feedback && <div className="notice" style={{ marginTop: 10 }}>{feedback}</div>}

          {scans.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
              {scans.map((scan) => (
                <button
                  key={scan.id}
                  type="button"
                  className={selectedScanId === scan.id ? "primary" : ""}
                  onClick={() => setSelectedScanId(scan.id)}
                  style={{ fontSize: 12 }}
                >
                  {scan.source === "import" ? "\u2191 " : ""}{scan.niche} · {scan.city} ({scan.prospect_count})
                </button>
              ))}
            </div>
          )}
        </div>
      </article>

      {scanDetail && (
        <article className="surface large">
          <div className="surface-header">
            <Sparkles size={18} />
            <h3>
              {scanDetail.niche} em {scanDetail.city} — {scanDetail.prospects.length} negócios
            </h3>
          </div>
          <div style={{ padding: "0 24px 20px", display: "flex", flexDirection: "column", gap: 10 }}>
            {scanDetail.prospects.map((prospect) => (
              <ProspectCard
                key={prospect.id}
                prospect={prospect}
                expanded={expandedProspectId === prospect.id}
                onToggle={() => setExpandedProspectId(expandedProspectId === prospect.id ? null : prospect.id)}
              />
            ))}
            {scanDetail.prospects.length === 0 && (
              <p style={{ color: "var(--text-muted)" }}>Nenhum negócio retornado para esta busca.</p>
            )}
          </div>
        </article>
      )}
    </section>
  );
}

function ProspectCard({
  prospect,
  expanded,
  onToggle,
}: {
  prospect: LocalRadarProspect;
  expanded: boolean;
  onToggle: () => void;
}) {
  const [messageDraft, setMessageDraft] = useState<string | null>(null);
  const [providerType, setProviderType] = useState<WhatsAppProviderType>("evolution");
  const [sendFeedback, setSendFeedback] = useState<string | null>(null);

  const audit = useAuditLocalRadarProspect();
  const decide = useDecideLocalRadarProspect();
  const updateMessage = useUpdateLocalRadarMessage();
  const send = useSendLocalRadarProspect();

  const review = reviewLabels[prospect.review_status];
  const message = messageDraft ?? prospect.outreach_message ?? "";
  const busy = audit.isPending || decide.isPending || updateMessage.isPending || send.isPending;
  const actionError = [audit, decide, updateMessage, send].find((mutation) => mutation.isError)?.error;

  function handleSend() {
    setSendFeedback(null);
    send.mutate(
      { prospectId: prospect.id, providerType },
      {
        onSuccess: (result) => {
          if (result.send_status === "sent") setSendFeedback("Mensagem enviada.");
          else setSendFeedback(result.detail ?? "A mensagem não foi enviada.");
        },
      },
    );
  }

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 10, padding: "12px 16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer", flexWrap: "wrap" }} onClick={onToggle}>
        <strong style={{ flex: "1 1 200px" }}>{prospect.name}</strong>
        <span style={{ fontWeight: 700, color: scoreColor(prospect.presence_score) }}>
          {prospect.presence_score !== null ? `${prospect.presence_score}/100` : "—"}
        </span>
        <span style={{ fontSize: 12, color: "var(--text-dim)" }}>
          {prospect.rating !== null ? `★ ${prospect.rating} (${prospect.rating_count ?? 0})` : "sem avaliações"}
        </span>
        <span style={{ fontSize: 12, fontWeight: 600, color: review.color }}>{review.label}</span>
      </div>

      {prospect.changes.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
          {prospect.changes.map((change) => (
            <span
              key={change}
              style={{
                fontSize: 11,
                padding: "2px 8px",
                borderRadius: 999,
                background: "rgba(79,142,247,0.14)",
                color: "#4f8ef7",
                fontWeight: 600,
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              <TrendingUp size={11} /> {change}
            </span>
          ))}
        </div>
      )}

      {prospect.presence_gaps.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
          {prospect.presence_gaps.map((gap) => (
            <span key={gap} style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, background: "var(--surface-2, rgba(127,127,127,0.12))" }}>
              {gap}
            </span>
          ))}
        </div>
      )}

      {expanded && (
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", color: "var(--text-muted)" }}>
            {prospect.address && <span>{prospect.address}</span>}
            {prospect.phone && <span>{prospect.phone}</span>}
            {prospect.website && (
              <a href={prospect.website} target="_blank" rel="noreferrer">site <ExternalLink size={11} /></a>
            )}
            {prospect.google_maps_url && (
              <a href={prospect.google_maps_url} target="_blank" rel="noreferrer">Google Maps <ExternalLink size={11} /></a>
            )}
          </div>

          {prospect.audit ? (
            <div style={{ background: "var(--surface-2, rgba(127,127,127,0.08))", borderRadius: 8, padding: "10px 14px" }}>
              {prospect.audit_mode === "preview" && (
                <p style={{ fontSize: 11, color: "#ffab00", fontWeight: 600, marginBottom: 6 }}>
                  Prévia determinística — sem análise de IA (OPENAI_API_KEY não configurada).
                </p>
              )}
              {prospect.audit.research_used && (
                <p style={{ fontSize: 11, color: "#2e9e5b", fontWeight: 600, marginBottom: 6 }}>
                  Abordagem calibrada pela pesquisa de mercado de "{prospect.audit.research_used.sector}".
                </p>
              )}
              <p>{prospect.audit.diagnosis}</p>
              {(prospect.audit.opportunities ?? []).map((opportunity, index) => (
                <p key={index} style={{ marginTop: 6, color: "var(--text-muted)" }}>
                  <strong>{opportunity.issue}</strong> → {opportunity.recommended_service}. {opportunity.rationale}
                </p>
              ))}
              {(prospect.audit.cautions ?? []).length > 0 && (
                <p style={{ marginTop: 6, fontSize: 12, color: "#ffab00" }}>
                  Conferir antes de enviar: {(prospect.audit.cautions ?? []).join(" · ")}
                </p>
              )}
            </div>
          ) : (
            <p style={{ color: "var(--text-muted)" }}>Ainda sem auditoria — rode a auditoria para gerar o diagnóstico e a mensagem.</p>
          )}

          {prospect.review_status !== "sent" && (
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
              Mensagem de abordagem (edite antes de aprovar)
              <textarea
                value={message}
                onChange={(e) => setMessageDraft(e.target.value)}
                rows={3}
                onBlur={() => {
                  if (messageDraft !== null && messageDraft !== prospect.outreach_message && messageDraft.trim()) {
                    updateMessage.mutate({ prospectId: prospect.id, message: messageDraft });
                  }
                }}
              />
            </label>
          )}

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            {["new", "audited", "rejected"].includes(prospect.review_status) && (
              <button type="button" disabled={busy} onClick={() => audit.mutate(prospect.id)}>
                <Sparkles size={13} /> {prospect.audit ? "Reauditar" : "Auditar"}
              </button>
            )}
            {prospect.review_status === "audited" && (
              <>
                <button type="button" className="primary" disabled={busy} onClick={() => decide.mutate({ prospectId: prospect.id, decision: "approved" })}>
                  <CheckCircle2 size={13} /> Aprovar (cria lead na EG)
                </button>
                <button type="button" disabled={busy} onClick={() => decide.mutate({ prospectId: prospect.id, decision: "rejected" })}>
                  <XCircle size={13} /> Rejeitar
                </button>
              </>
            )}
            {prospect.review_status === "approved" && (
              <>
                <select value={providerType} onChange={(e) => setProviderType(e.target.value as WhatsAppProviderType)} style={{ fontSize: 12 }}>
                  <option value="evolution">Evolution API</option>
                  <option value="meta_cloud">Meta Cloud (oficial)</option>
                  <option value="zapi">Z-API</option>
                  <option value="custom">Custom</option>
                </select>
                <button type="button" className="primary" disabled={busy || !prospect.phone} onClick={handleSend}>
                  <Send size={13} /> Enviar WhatsApp
                </button>
                {!prospect.phone && <span style={{ fontSize: 12, color: "var(--text-dim)" }}>sem telefone no Google</span>}
              </>
            )}
            {prospect.lead_id && <span style={{ fontSize: 12, color: "#2e9e5b" }}>Lead criado no CRM da EG</span>}
          </div>

          {actionError instanceof Error && <div className="notice error">{actionError.message}</div>}
          {sendFeedback && <div className="notice">{sendFeedback}</div>}
        </div>
      )}
    </div>
  );
}
