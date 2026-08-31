import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import type { SquadInfo } from "../../../types/state";
import { api, type BackofficeArchitecture } from "../../../lib/api";

// ── types ─────────────────────────────────────────────────────────────────────

// ── simple markdown renderer ──────────────────────────────────────────────────
// Handles: h1-h3, blockquote, hr, code blocks, inline code, bullet lists, bold, plain text.

function renderMarkdown(md: string): React.ReactNode[] {
  const lines = md.split("\n");
  const nodes: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      nodes.push(
        <pre key={key++} style={s.pre}>
          {lang && <span style={s.codeLang}>{lang}</span>}
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      i++;
      continue;
    }

    // HTML comments — skip
    if (line.startsWith("<!--")) {
      while (i < lines.length && !lines[i].includes("-->")) i++;
      i++;
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      nodes.push(<hr key={key++} style={s.hr} />);
      i++;
      continue;
    }

    // Headings
    const h3 = line.match(/^###\s+(.*)/);
    const h2 = line.match(/^##\s+(.*)/);
    const h1 = line.match(/^#\s+(.*)/);
    if (h1) { nodes.push(<h1 key={key++} style={s.h1}>{inlineRender(h1[1])}</h1>); i++; continue; }
    if (h2) { nodes.push(<h2 key={key++} style={s.h2}>{inlineRender(h2[1])}</h2>); i++; continue; }
    if (h3) { nodes.push(<h3 key={key++} style={s.h3}>{inlineRender(h3[1])}</h3>); i++; continue; }

    // Blockquote
    if (line.startsWith("> ")) {
      const bqLines: string[] = [];
      while (i < lines.length && lines[i].startsWith("> ")) {
        bqLines.push(lines[i].slice(2));
        i++;
      }
      nodes.push(
        <blockquote key={key++} style={s.blockquote}>
          {bqLines.map((l, j) => <p key={j} style={{ margin: 0 }}>{inlineRender(l)}</p>)}
        </blockquote>
      );
      continue;
    }

    // Bullet list
    if (/^[-*]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s/, ""));
        i++;
      }
      nodes.push(
        <ul key={key++} style={s.ul}>
          {items.map((it, j) => <li key={j} style={s.li}>{inlineRender(it)}</li>)}
        </ul>
      );
      continue;
    }

    // Empty line
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Paragraph
    nodes.push(<p key={key++} style={s.p}>{inlineRender(line)}</p>);
    i++;
  }

  return nodes;
}

function inlineRender(text: string): React.ReactNode {
  // Split on **bold**, `code`, [link](url) and plain text
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i} style={s.inlineCode}>{part.slice(1, -1)}</code>;
    }
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link) {
      return <span key={i} style={s.link}>{link[1]}</span>;
    }
    return part;
  });
}

// ── squad map (live scan) ─────────────────────────────────────────────────────

function SquadMapCard({ sq }: { sq: SquadInfo }) {
  return (
    <div style={s.squadCard}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 20 }}>{sq.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.3 }}>
            {sq.name}
          </div>
          <div style={{ fontSize: 10, color: "var(--text-secondary)", fontFamily: "monospace", marginTop: 1 }}>
            {sq.code}
          </div>
        </div>
      </div>
      {sq.description && (
        <div style={{
          fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.6,
          borderTop: "1px solid var(--border)",
          paddingTop: 6,
        }}>
          {sq.description}
        </div>
      )}
      {sq.agents.length > 0 && (
        <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 3 }}>
          {sq.agents.map((a) => (
            <span key={a} style={s.agentBadge}>{a}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function SquadMap({ squads }: { squads: SquadInfo[] }) {
  return (
    <div style={s.squadMap}>
      <h2 style={s.h2}>Mapa de Squads (ao vivo)</h2>
      <p style={{ ...s.p, color: "var(--text-secondary)", fontSize: 11 }}>
        Derivado do filesystem — clique num card para expandir a descrição.
      </p>
      <div style={s.squadGrid}>
        {squads.map((sq) => <SquadMapCard key={sq.code} sq={sq} />)}
      </div>
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export function ArchitectureView() {
  const [data, setData] = useState<BackofficeArchitecture | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"doc" | "map">("doc");

  useEffect(() => {
    api.adminArchitecture()
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Falha ao carregar o Banco de Arquitetura."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={s.centered}>Carregando Banco de Arquitetura...</div>
    );
  }
  if (error) {
    return <div style={s.centered}>Erro ao carregar arquitetura.md: {error}</div>;
  }
  if (!data) {
    return <div style={s.centered}>arquitetura.md não encontrado.</div>;
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Toolbar */}
      <div style={s.toolbar}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
          Banco de Arquitetura
        </span>
        <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
          inventário vivo da EverGreen · {data.squads.length} squads detectados
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          {(["doc", "map"] as const).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              style={{
                ...s.tabBtn,
                borderColor: view === v ? "var(--accent-cyan)" : "var(--border)",
                background: view === v ? "rgba(58,201,123,0.13)" : "transparent",
                color: view === v ? "var(--accent-cyan)" : "var(--text-secondary)",
              }}
            >
              {v === "doc" ? "📄 Documento" : "🗺 Mapa de Squads"}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={s.content}>
        {view === "doc" ? (
          <div style={s.docBody}>
            {renderMarkdown(data.md)}
          </div>
        ) : (
          <SquadMap squads={data.squads} />
        )}
      </div>
    </div>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const s: Record<string, CSSProperties> = {
  centered: {
    flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
    color: "var(--text-secondary)", fontSize: 13,
  },
  toolbar: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "10px 16px", borderBottom: "1px solid var(--border)",
    flexShrink: 0, flexWrap: "wrap", background: "var(--bg-sidebar)",
  },
  tabBtn: {
    padding: "3px 10px", borderRadius: 4, fontSize: 11,
    fontFamily: "inherit", cursor: "pointer", border: "1px solid",
    transition: "all 0.12s",
  },
  content: {
    flex: 1, overflowY: "auto", padding: "24px 32px",
  },
  docBody: {
    maxWidth: 860, margin: "0 auto",
  },
  // markdown elements
  h1: { fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 12px", letterSpacing: 0.3 },
  h2: { fontSize: 15, fontWeight: 700, color: "var(--accent-cyan)", margin: "28px 0 8px", letterSpacing: 0.3 },
  h3: { fontSize: 13, fontWeight: 600, color: "var(--text-primary)", margin: "16px 0 6px" },
  p: { fontSize: 12, lineHeight: 1.7, color: "var(--text-primary)", margin: "0 0 8px" },
  hr: { border: "none", borderTop: "1px solid var(--border)", margin: "20px 0" },
  blockquote: {
    borderLeft: "3px solid var(--accent-cyan)", margin: "0 0 12px",
    paddingLeft: 12, color: "var(--text-secondary)", fontSize: 12, lineHeight: 1.6,
  },
  ul: { margin: "0 0 10px", paddingLeft: 20 },
  li: { fontSize: 12, lineHeight: 1.7, color: "var(--text-primary)", marginBottom: 2 },
  pre: {
    background: "var(--bg-secondary)", border: "1px solid var(--border)",
    borderRadius: 6, padding: "12px 14px", overflow: "auto",
    fontSize: 11, lineHeight: 1.55, fontFamily: "monospace",
    color: "var(--text-secondary)", margin: "0 0 14px", position: "relative",
  },
  codeLang: {
    position: "absolute", top: 6, right: 10,
    fontSize: 10, color: "var(--text-secondary)", opacity: 0.6,
  },
  inlineCode: {
    background: "var(--bg-secondary)", border: "1px solid var(--border)",
    borderRadius: 3, padding: "1px 5px", fontSize: "0.9em",
    fontFamily: "monospace", color: "var(--accent-cyan)",
  },
  link: { color: "var(--accent-cyan)", textDecoration: "underline", cursor: "default" },
  // squad map
  squadMap: { maxWidth: 1100, margin: "0 auto" },
  squadGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
    gap: 12, marginTop: 12,
  },
  squadCard: {
    background: "var(--bg-secondary)", border: "1px solid var(--border)",
    borderRadius: 8, padding: "14px 16px",
  },
  agentBadge: {
    fontSize: 9, padding: "2px 6px", borderRadius: 3,
    background: "rgba(58,201,123,0.12)", color: "var(--accent-cyan)",
    border: "1px solid rgba(58,201,123,0.3)", fontFamily: "monospace",
  },
};
