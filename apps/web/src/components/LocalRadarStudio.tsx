import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  Flame,
  Globe,
  Instagram,
  LayoutList,
  Linkedin,
  Mail,
  MapPin,
  Phone,
  Search,
  Send,
  Sparkles,
  Table as TableIcon,
  TrendingUp,
  Upload,
  XCircle,
  Zap,
} from "lucide-react";

import {
  useAuditLocalRadarProspect,
  useCreateLocalRadarScan,
  useDecideLocalRadarProspect,
  useEnrichLocalRadarBatch,
  useEnrichLocalRadarProspect,
  useImportLocalRadarScan,
  useLocalRadarScan,
  useLocalRadarScans,
  useSendLocalRadarProspect,
  useUpdateLocalRadarMessage,
  useWorkspaces,
} from "../hooks/useBiomaApi";
import { api, type LocalRadarImportRow, type LocalRadarProspect, type WhatsAppProviderType } from "../lib/api";

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
  const cleaned = value.replace(/\./g, "").replace(",", ".").replace(/[^\d.]/g, "");
  const parsed = Number.parseFloat(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function countOf(line: string, character: string) {
  return line.split(character).length - 1;
}

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

  const candidates: Array<[string, number]> = [
    ["\t", countOf(lines[0], "\t")],
    [";", countOf(lines[0], ";")],
    [",", countOf(lines[0], ",")],
  ];
  candidates.sort((a, b) => b[1] - a[1]);
  const separator = candidates[0][1] > 0 ? candidates[0][0] : "\t";

  const rawHeaders = splitRespectingQuotes(lines[0], separator);
  const headerMap: Partial<Record<keyof LocalRadarImportRow, number>> = {};

  rawHeaders.forEach((header, index) => {
    const normalized = normalizeHeader(header);
    (Object.keys(HEADER_ALIASES) as Array<keyof LocalRadarImportRow>).forEach((field) => {
      if (headerMap[field] === undefined && HEADER_ALIASES[field].includes(normalized)) {
        headerMap[field] = index;
      }
    });
  });

  if (headerMap.name === undefined) {
    return { rows: [], ignored: lines.length - 1 };
  }

  const rows: LocalRadarImportRow[] = [];
  let ignored = 0;

  for (let i = 1; i < lines.length; i += 1) {
    const cells = splitRespectingQuotes(lines[i], separator).map((c) => c.trim().replace(/^"|"$/g, ""));
    const name = headerMap.name !== undefined ? cells[headerMap.name] : "";
    if (!name) {
      ignored += 1;
      continue;
    }
    rows.push({
      name,
      address: headerMap.address !== undefined ? cells[headerMap.address] || null : null,
      phone: headerMap.phone !== undefined ? cells[headerMap.phone] || null : null,
      website: headerMap.website !== undefined ? cells[headerMap.website] || null : null,
      google_maps_url: headerMap.google_maps_url !== undefined ? cells[headerMap.google_maps_url] || null : null,
      rating: headerMap.rating !== undefined ? parseNumber(cells[headerMap.rating]) : null,
      rating_count: headerMap.rating_count !== undefined ? parseNumber(cells[headerMap.rating_count]) : null,
    });
  }

  return { rows, ignored };
}

function scoreColor(score: number | null): string {
  if (score === null) return "var(--text-muted)";
  if (score >= 70) return "#2e9e5b";
  if (score >= 40) return "#ffab00";
  return "#ff5252";
}

const reviewLabels: Record<LocalRadarProspect["review_status"], { label: string; color: string }> = {
  new: { label: "Novo", color: "#888" },
  audited: { label: "Auditado", color: "#4f8ef7" },
  approved: { label: "Aprovado", color: "#2e9e5b" },
  rejected: { label: "Rejeitado", color: "#ff5252" },
  sent: { label: "Enviado", color: "#00c48c" },
};

type ViewMode = "table" | "cards";
type FilterKind = "all" | "with_email" | "with_social" | "no_website" | "approved";

export function LocalRadarStudio() {
  const [niche, setNiche] = useState("");
  const [city, setCity] = useState("");
  const [limit, setLimit] = useState(20);
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [expandedProspectId, setExpandedProspectId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [pasted, setPasted] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [filterKind, setFilterKind] = useState<FilterKind>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);

  const { data: scans = [] } = useLocalRadarScans(true);
  const createScan = useCreateLocalRadarScan();
  const importScan = useImportLocalRadarScan();
  const enrichBatch = useEnrichLocalRadarBatch();
  const enrichSingle = useEnrichLocalRadarProspect();

  const activeScanId = selectedScanId ?? (scans[0]?.id || null);
  const { data: scanDetail } = useLocalRadarScan(activeScanId);

  const parsed = pasted.trim() ? parsePastedProspects(pasted) : null;

  function handleImport() {
    if (!parsed || parsed.rows.length === 0) return;
    setFeedback(null);
    importScan.mutate(
      {
        niche: niche.trim() || "Importação",
        city: city.trim() || "Lista Externa",
        rows: parsed.rows,
      },
      {
        onSuccess: (scan) => {
          setSelectedScanId(scan.id);
          setShowImport(false);
          setPasted("");
          setFeedback(`Importados ${scan.prospect_count} negócios com sucesso.`);
        },
      },
    );
  }

  function handleCreateScan(event: FormEvent) {
    event.preventDefault();
    if (!niche.trim() || !city.trim()) return;
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

  function handleCopyEmail(email: string) {
    void navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
  }

  const allProspects = scanDetail?.prospects ?? [];

  // Filtros em memória
  const filteredProspects = allProspects.filter((p) => {
    // Filtro de texto rápido
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = p.name.toLowerCase().includes(q);
      const matchPhone = (p.phone || "").toLowerCase().includes(q);
      const matchEmail = (p.emails || []).some((e) => e.toLowerCase().includes(q));
      if (!matchName && !matchPhone && !matchEmail) return false;
    }
    // Filtro por categoria
    if (filterKind === "with_email") return (p.emails || []).length > 0;
    if (filterKind === "with_social") return Object.keys(p.social_links || {}).length > 0;
    if (filterKind === "no_website") return !p.website;
    if (filterKind === "approved") return p.review_status === "approved";
    return true;
  });

  const totalCount = allProspects.length;
  const withEmailCount = allProspects.filter((p) => (p.emails || []).length > 0).length;
  const withSocialCount = allProspects.filter((p) => Object.keys(p.social_links || {}).length > 0).length;
  const noWebsiteCount = allProspects.filter((p) => !p.website).length;
  const approvedCount = allProspects.filter((p) => p.review_status === "approved").length;

  function handleToggleSelectAll() {
    if (selectedIds.size === filteredProspects.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredProspects.map((p) => p.id)));
    }
  }

  function handleToggleProspect(id: string) {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  }

  const navigate = useNavigate();
  const { data: workspaces = [] } = useWorkspaces(true);
  const activeWorkspace = workspaces.find((w) => w.kind === "agency_internal") || workspaces[0];

  async function handleCreateProspectingList() {
    if (!activeWorkspace || selectedIds.size === 0 || !scanDetail) return;
    const selectedProspects = scanDetail.prospects.filter((p) => selectedIds.has(p.id));
    const listTitle = `${scanDetail.niche} - ${scanDetail.city} (${new Date().toLocaleDateString("pt-BR")})`;

    try {
      await api.createProspectingList(activeWorkspace.id, {
        title: listTitle,
        source: "local_radar",
        segment: scanDetail.niche,
        target_region: scanDetail.city,
        items: selectedProspects.map((p) => ({
          company_name: p.name,
          contact_name: null,
          phone: p.phone,
          email: p.emails?.[0] || null,
          website: p.website,
          instagram: p.social_links?.instagram || null,
          linkedin: p.social_links?.linkedin || null,
          address: p.address,
          rating: p.rating,
          reviews_count: p.rating_count || 0,
          presence_score: p.presence_score || 0,
          category: p.place_types?.[0] || null,
          external_place_id: p.place_id,
        })),
      });
      setFeedback(`🔥 Lista "${listTitle}" criada com ${selectedProspects.length} leads! Redirecionando para o Cockpit...`);
      setTimeout(() => {
        navigate("/operacao/prospeccao");
      }, 1200);
    } catch (err) {
      setFeedback(`Erro ao criar lista: ${err instanceof Error ? err.message : "Falha na requisição"}`);
    }
  }

  function handleEnrichSelected() {
    if (!activeScanId || selectedIds.size === 0) return;
    enrichBatch.mutate(
      { scanId: activeScanId, prospectIds: Array.from(selectedIds) },
      {
        onSuccess: (res) => {
          setFeedback(
            `Enriquecimento finalizado: ${res.enriched_count} enriquecidos com sucesso, ${res.failed_count} falhas ou sem site.`,
          );
        },
      },
    );
  }

  return (
    <section className="content-grid" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Bloco de Busca & Filtros */}
      <article className="surface large">
        <div className="surface-header">
          <MapPin size={18} />
          <h3>Radar Local — Extração e Enriquecimento de Leads</h3>
        </div>
        <div style={{ padding: "0 24px 20px" }}>
          <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 14 }}>
            Prospecção no Google Maps com <strong>crawler de e-mails corporativos e redes sociais</strong>.
            Fila de abordagem consultiva com aprovação humana obrigatória.
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
            <Upload size={13} /> {showImport ? "Fechar import" : "Importar planilha CSV/TSV (sem custo de API)"}
          </button>

          {showImport && (
            <div style={{ marginTop: 10, border: "1px dashed var(--border)", borderRadius: 8, padding: "12px 14px" }}>
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
                Cole aqui o conteúdo copiado de exportações de extensões (Instant Data Scraper). O parse acontece 100% no navegador.
              </p>
              <textarea
                value={pasted}
                onChange={(e) => setPasted(e.target.value)}
                rows={5}
                placeholder={"nome\tendereço\ttelefone\tsite\tnota\tavaliações"}
                style={{ width: "100%", fontFamily: "monospace", fontSize: 11 }}
              />
              {parsed && (
                <p style={{ fontSize: 12, marginTop: 6, color: parsed.rows.length ? "#2e9e5b" : "#ff5252" }}>
                  {parsed.rows.length} linha(s) reconhecida(s)
                  {parsed.ignored > 0 ? ` · ${parsed.ignored} ignorada(s)` : ""}
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
            </div>
          )}

          {createScan.isError && (
            <div className="notice error" style={{ marginTop: 10 }}>
              {createScan.error instanceof Error ? createScan.error.message : "Falha na busca."}
            </div>
          )}
          {feedback && <div className="notice" style={{ marginTop: 10 }}>{feedback}</div>}

          {/* Histórico de Scans */}
          {scans.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
              {scans.map((scan) => (
                <button
                  key={scan.id}
                  type="button"
                  className={activeScanId === scan.id ? "primary" : ""}
                  onClick={() => setSelectedScanId(scan.id)}
                  style={{ fontSize: 12 }}
                >
                  {scan.source === "import" ? "↑ " : ""}{scan.niche} · {scan.city} ({scan.prospect_count})
                </button>
              ))}
            </div>
          )}
        </div>
      </article>

      {/* Tabela de Resultados ou Cards */}
      {scanDetail && (
        <article className="surface large">
          <div className="surface-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Sparkles size={18} />
              <h3 style={{ margin: 0 }}>
                {scanDetail.niche} em {scanDetail.city} — {allProspects.length} negócios
              </h3>
            </div>

            {/* Alternador de Visão (Tabela vs Cards) */}
            <div style={{ display: "flex", gap: 4, background: "var(--surface-2, rgba(127,127,127,0.12))", borderRadius: 8, padding: 3 }}>
              <button
                type="button"
                className={viewMode === "table" ? "primary" : ""}
                onClick={() => setViewMode("table")}
                style={{ fontSize: 12, padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: 6 }}
              >
                <TableIcon size={13} /> Tabela de Leads
              </button>
              <button
                type="button"
                className={viewMode === "cards" ? "primary" : ""}
                onClick={() => setViewMode("cards")}
                style={{ fontSize: 12, padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: 6 }}
              >
                <LayoutList size={13} /> Fichas Detalhadas
              </button>
            </div>
          </div>

          <div style={{ padding: "0 24px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Barra de Filtros Rápidos & Ações em Lote */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                <button
                  type="button"
                  className={filterKind === "all" ? "primary" : ""}
                  onClick={() => setFilterKind("all")}
                  style={{ fontSize: 11, padding: "3px 8px" }}
                >
                  Todos ({totalCount})
                </button>
                <button
                  type="button"
                  className={filterKind === "with_email" ? "primary" : ""}
                  onClick={() => setFilterKind("with_email")}
                  style={{ fontSize: 11, padding: "3px 8px" }}
                >
                  <Mail size={11} /> Com E-mail ({withEmailCount})
                </button>
                <button
                  type="button"
                  className={filterKind === "with_social" ? "primary" : ""}
                  onClick={() => setFilterKind("with_social")}
                  style={{ fontSize: 11, padding: "3px 8px" }}
                >
                  <Instagram size={11} /> Com Social ({withSocialCount})
                </button>
                <button
                  type="button"
                  className={filterKind === "no_website" ? "primary" : ""}
                  onClick={() => setFilterKind("no_website")}
                  style={{ fontSize: 11, padding: "3px 8px" }}
                >
                  Sem Site ({noWebsiteCount})
                </button>
                <button
                  type="button"
                  className={filterKind === "approved" ? "primary" : ""}
                  onClick={() => setFilterKind("approved")}
                  style={{ fontSize: 11, padding: "3px 8px" }}
                >
                  Aprovados ({approvedCount})
                </button>
              </div>

              {/* Botão de Enriquecimento em Lote */}
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="Filtrar por nome, tel ou e-mail..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ fontSize: 12, padding: "4px 8px", width: 200 }}
                />
                <button
                  type="button"
                  className="primary"
                  disabled={selectedIds.size === 0 || enrichBatch.isPending}
                  onClick={handleEnrichSelected}
                  style={{ fontSize: 12, display: "inline-flex", alignItems: "center", gap: 6 }}
                >
                  <Zap size={13} /> {enrichBatch.isPending ? "Minerando sites..." : `⚡ Enriquecer Selecionados (${selectedIds.size})`}
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={selectedIds.size === 0}
                  onClick={handleCreateProspectingList}
                  style={{ fontSize: 12, display: "inline-flex", alignItems: "center", gap: 6, borderColor: "var(--brand-accent)", color: "var(--brand-accent)" }}
                >
                  <Flame size={13} /> 🔥 Criar Fila de Prospecção ({selectedIds.size})
                </button>
              </div>
            </div>

            {/* Visualização 1: Tabela de Leads (Scraper Kit Table) */}
            {viewMode === "table" ? (
              <div style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: 10 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, textAlign: "left" }}>
                  <thead>
                    <tr style={{ background: "var(--surface-2, rgba(127,127,127,0.08))", borderBottom: "1px solid var(--border)" }}>
                      <th style={{ padding: "10px 12px", width: 30 }}>
                        <input
                          type="checkbox"
                          checked={filteredProspects.length > 0 && selectedIds.size === filteredProspects.length}
                          onChange={handleToggleSelectAll}
                        />
                      </th>
                      <th style={{ padding: "10px 12px" }}>Negócio / Local</th>
                      <th style={{ padding: "10px 12px" }}>Avaliação</th>
                      <th style={{ padding: "10px 12px" }}>Telefone</th>
                      <th style={{ padding: "10px 12px" }}>Website</th>
                      <th style={{ padding: "10px 12px" }}>E-mails Minerados</th>
                      <th style={{ padding: "10px 12px" }}>Redes Sociais</th>
                      <th style={{ padding: "10px 12px" }}>Presença</th>
                      <th style={{ padding: "10px 12px", textAlign: "right" }}>Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredProspects.map((prospect) => {
                      const isSelected = selectedIds.has(prospect.id);
                      const emails = prospect.emails || [];
                      const socials = prospect.social_links || {};
                      const hasWebsite = Boolean(prospect.website);

                      return (
                        <tr
                          key={prospect.id}
                          style={{
                            borderBottom: "1px solid var(--border)",
                            background: isSelected ? "rgba(79, 142, 247, 0.06)" : undefined,
                          }}
                        >
                          <td style={{ padding: "10px 12px" }}>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => handleToggleProspect(prospect.id)}
                            />
                          </td>
                          <td style={{ padding: "10px 12px" }}>
                            <div style={{ fontWeight: 600 }}>{prospect.name}</div>
                            {prospect.address && (
                              <div style={{ fontSize: 11, color: "var(--text-dim)", maxWidth: 220, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                {prospect.address}
                              </div>
                            )}
                            {prospect.google_maps_url && (
                              <a href={prospect.google_maps_url} target="_blank" rel="noreferrer" style={{ fontSize: 11, display: "inline-flex", alignItems: "center", gap: 3, marginTop: 2 }}>
                                Maps <ExternalLink size={10} />
                              </a>
                            )}
                          </td>
                          <td style={{ padding: "10px 12px", whiteSpace: "nowrap" }}>
                            {prospect.rating !== null ? (
                              <span style={{ fontWeight: 600 }}>
                                ★ {prospect.rating} <span style={{ fontSize: 11, color: "var(--text-dim)" }}>({prospect.rating_count ?? 0})</span>
                              </span>
                            ) : (
                              <span style={{ color: "var(--text-dim)" }}>—</span>
                            )}
                          </td>
                          <td style={{ padding: "10px 12px", whiteSpace: "nowrap" }}>
                            {prospect.phone ? (
                              <a href={`tel:${prospect.phone}`} style={{ color: "inherit", textDecoration: "none" }}>
                                <Phone size={11} style={{ verticalAlign: "middle", marginRight: 4 }} />
                                {prospect.phone}
                              </a>
                            ) : (
                              <span style={{ color: "var(--text-dim)" }}>—</span>
                            )}
                          </td>
                          <td style={{ padding: "10px 12px", maxWidth: 160, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {hasWebsite ? (
                              <a href={prospect.website!} target="_blank" rel="noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                                <Globe size={11} /> {prospect.website!.replace(/^https?:\/\/(www\.)?/, "").split("/")[0]}
                              </a>
                            ) : (
                              <span style={{ fontSize: 11, color: "#ff5252", fontWeight: 600 }}>Sem site</span>
                            )}
                          </td>
                          <td style={{ padding: "10px 12px" }}>
                            {emails.length > 0 ? (
                              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                                {emails.slice(0, 2).map((email) => (
                                  <button
                                    key={email}
                                    type="button"
                                    onClick={() => handleCopyEmail(email)}
                                    title="Clique para copiar e-mail"
                                    style={{
                                      fontSize: 11,
                                      padding: "2px 6px",
                                      borderRadius: 4,
                                      border: "1px solid var(--border)",
                                      background: "var(--surface-2, rgba(127,127,127,0.1))",
                                      display: "inline-flex",
                                      alignItems: "center",
                                      gap: 4,
                                      cursor: "pointer",
                                    }}
                                  >
                                    <Mail size={10} color="#4f8ef7" />
                                    {email}
                                    {copiedEmail === email ? <Check size={10} color="#2e9e5b" /> : <Copy size={10} opacity={0.5} />}
                                  </button>
                                ))}
                                {emails.length > 2 && (
                                  <span style={{ fontSize: 10, color: "var(--text-dim)" }}>+{emails.length - 2} outro(s)</span>
                                )}
                              </div>
                            ) : prospect.crawler_status === "completed" ? (
                              <span style={{ fontSize: 11, color: "var(--text-dim)" }}>Nenhum achado</span>
                            ) : prospect.crawler_status === "running" ? (
                              <span style={{ fontSize: 11, color: "#ffab00" }}>Minerando...</span>
                            ) : (
                              <span style={{ fontSize: 11, color: "var(--text-dim)" }}>Não minerado</span>
                            )}
                          </td>
                          <td style={{ padding: "10px 12px", whiteSpace: "nowrap" }}>
                            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                              {socials.instagram && (
                                <a href={socials.instagram} target="_blank" rel="noreferrer" title="Instagram" style={{ color: "#e1306c" }}>
                                  <Instagram size={14} />
                                </a>
                              )}
                              {socials.facebook && (
                                <a href={socials.facebook} target="_blank" rel="noreferrer" title="Facebook" style={{ color: "#1877f2" }}>
                                  <Globe size={14} />
                                </a>
                              )}
                              {socials.linkedin && (
                                <a href={socials.linkedin} target="_blank" rel="noreferrer" title="LinkedIn" style={{ color: "#0077b5" }}>
                                  <Linkedin size={14} />
                                </a>
                              )}
                              {!socials.instagram && !socials.facebook && !socials.linkedin && (
                                <span style={{ color: "var(--text-dim)" }}>—</span>
                              )}
                            </div>
                          </td>
                          <td style={{ padding: "10px 12px", whiteSpace: "nowrap" }}>
                            <span style={{ fontWeight: 700, color: scoreColor(prospect.presence_score) }}>
                              {prospect.presence_score !== null ? `${prospect.presence_score}/100` : "—"}
                            </span>
                          </td>
                          <td style={{ padding: "10px 12px", textAlign: "right", whiteSpace: "nowrap" }}>
                            <div style={{ display: "inline-flex", gap: 6 }}>
                              {hasWebsite && (
                                <button
                                  type="button"
                                  onClick={() => enrichSingle.mutate(prospect.id)}
                                  disabled={enrichSingle.isPending}
                                  title="Minerar site agora"
                                  style={{ fontSize: 11, padding: "2px 6px" }}
                                >
                                  <Zap size={11} color="#ffab00" /> Minerar
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => {
                                  setViewMode("cards");
                                  setExpandedProspectId(prospect.id);
                                }}
                                style={{ fontSize: 11, padding: "2px 8px" }}
                              >
                                Ficha
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {filteredProspects.length === 0 && (
                  <p style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)" }}>
                    Nenhum negócio corresponde ao filtro selecionado.
                  </p>
                )}
              </div>
            ) : (
              /* Visualização 2: Fichas Detalhadas */
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {filteredProspects.map((prospect) => (
                  <ProspectCard
                    key={prospect.id}
                    prospect={prospect}
                    expanded={expandedProspectId === prospect.id}
                    onToggle={() => setExpandedProspectId(expandedProspectId === prospect.id ? null : prospect.id)}
                  />
                ))}
                {filteredProspects.length === 0 && (
                  <p style={{ color: "var(--text-muted)" }}>Nenhum negócio retornado para esta busca.</p>
                )}
              </div>
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
  const enrich = useEnrichLocalRadarProspect();

  const review = reviewLabels[prospect.review_status];
  const message = messageDraft ?? prospect.outreach_message ?? "";
  const busy = audit.isPending || decide.isPending || updateMessage.isPending || send.isPending || enrich.isPending;
  const actionError = [audit, decide, updateMessage, send, enrich].find((mutation) => mutation.isError)?.error;

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

  const emails = prospect.emails || [];
  const socials = prospect.social_links || {};

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

      {/* Badges de Enriquecimento no Card */}
      {(emails.length > 0 || Object.keys(socials).length > 0) && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8, alignItems: "center" }}>
          {emails.map((email) => (
            <span
              key={email}
              style={{
                fontSize: 11,
                padding: "2px 8px",
                borderRadius: 4,
                background: "rgba(79,142,247,0.12)",
                color: "#4f8ef7",
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              <Mail size={11} /> {email}
            </span>
          ))}
          {socials.instagram && (
            <a href={socials.instagram} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: "#e1306c", display: "inline-flex", alignItems: "center", gap: 3 }}>
              <Instagram size={12} /> Instagram
            </a>
          )}
          {socials.linkedin && (
            <a href={socials.linkedin} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: "#0077b5", display: "inline-flex", alignItems: "center", gap: 3 }}>
              <Linkedin size={12} /> LinkedIn
            </a>
          )}
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

          {/* Seção do Crawler de Website */}
          {prospect.website && (
            <div style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", background: "var(--surface-2, rgba(127,127,127,0.06))" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, fontWeight: 600 }}>Enriquecimento Web (Crawler)</span>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => enrich.mutate(prospect.id)}
                  style={{ fontSize: 11, padding: "2px 8px" }}
                >
                  <Zap size={11} color="#ffab00" /> {prospect.crawler_status === "completed" ? "Re-minerar site" : "Minerar site"}
                </button>
              </div>
              {prospect.crawler_error && (
                <p style={{ fontSize: 11, color: "#ff5252", marginTop: 4 }}>{prospect.crawler_error}</p>
              )}
            </div>
          )}

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
