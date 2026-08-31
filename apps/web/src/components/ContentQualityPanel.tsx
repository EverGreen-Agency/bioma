import { useState } from "react";
import { Check, ChevronDown, ChevronRight, CircleDashed, Search, Sparkles, X } from "lucide-react";

import { useContentQuality } from "../hooks/useBiomaApi";
import type { ContentQualityCheck } from "../lib/api";
import { EmptyState } from "./shared";

/**
 * Prontidão SEO/GEO de uma peça — decisão 14.
 *
 * O painel abre com o que FALTA, não com o que passou. Um checklist que começa
 * por dez linhas verdes obriga a caçar o problema no meio do elogio; o que
 * reprovou é a única parte acionável, então é a que fica visível.
 *
 * O aviso de que isto não estima posição no Google fica no painel, permanente,
 * e não em tooltip. "Score 82" é lido como promessa de resultado por padrão —
 * a ressalva precisa estar onde o número está, sempre.
 */
export function ContentQualityPanel({
  workspaceId,
  title,
  content,
  keyword,
}: {
  workspaceId: string;
  title?: string;
  content: string;
  keyword?: string | null;
}) {
  const [showPassed, setShowPassed] = useState(false);
  const { data: report, isLoading, error } = useContentQuality(workspaceId, { title, content, keyword });

  if (!content.trim()) return null;
  if (isLoading) return <EmptyState text="Avaliando o texto..." />;
  if (error) {
    return (
      <p style={{ fontSize: 12, color: "var(--danger-soft)", margin: 0 }}>
        Não foi possível avaliar o texto: {(error as Error).message}
      </p>
    );
  }
  if (!report) return null;

  const failed = report.checks.filter((check) => check.applicable && !check.passed);
  const passed = report.checks.filter((check) => check.applicable && check.passed);
  const skipped = report.checks.filter((check) => !check.applicable);

  return (
    <section
      style={{
        border: "1px solid var(--border)",
        borderRadius: 8,
        background: "var(--bg-inset)",
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <header style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <strong style={{ fontSize: 13 }}>Prontidão para publicar</strong>
        <span style={{ fontSize: 11, color: "var(--text-faint)" }}>{report.words} palavras</span>
      </header>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <ScoreChip icon={Search} label="SEO" hint="Buscador clássico" value={report.seo_score} />
        <ScoreChip icon={Sparkles} label="GEO" hint="Citação por IA" value={report.geo_score} />
      </div>

      <p style={{ fontSize: 11, color: "var(--text-faint)", margin: 0, lineHeight: 1.5 }}>
        Checklist do próprio texto. <strong>Não estima posição no Google</strong> — autoridade
        do domínio, backlinks e concorrência do termo não entram nesta conta.
      </p>

      {failed.length === 0 ? (
        <p style={{ fontSize: 12, color: "var(--mint)", margin: 0, display: "flex", gap: 6, alignItems: "center" }}>
          <Check size={13} aria-hidden /> Todos os critérios aplicáveis foram atendidos.
        </p>
      ) : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 10 }}>
          {failed.map((check) => (
            <CheckRow key={check.id} check={check} showHint />
          ))}
        </ul>
      )}

      {(passed.length > 0 || skipped.length > 0) && (
        <div>
          <button
            type="button"
            className="mini-button"
            onClick={() => setShowPassed((open) => !open)}
            style={{ display: "flex", alignItems: "center", gap: 4 }}
          >
            {showPassed ? <ChevronDown size={12} aria-hidden /> : <ChevronRight size={12} aria-hidden />}
            {passed.length} atendidos
            {skipped.length > 0 && `, ${skipped.length} não se aplicam`}
          </button>
          {showPassed && (
            <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 6 }}>
              {passed.map((check) => (
                <CheckRow key={check.id} check={check} />
              ))}
              {skipped.map((check) => (
                <CheckRow key={check.id} check={check} />
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function ScoreChip({
  icon: Icon,
  label,
  hint,
  value,
}: {
  icon: typeof Search;
  label: string;
  hint: string;
  value: number;
}) {
  // Faixas largas de propósito: a checklist distingue "falta bastante" de "está
  // perto", não pretende ter resolução de um ponto.
  const color = value >= 80 ? "var(--mint)" : value >= 50 ? "var(--amber)" : "var(--danger-soft)";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        border: "1px solid var(--border)",
        borderRadius: 6,
        padding: "6px 10px",
        background: "var(--surface)",
      }}
    >
      <Icon size={14} aria-hidden style={{ color }} />
      <div>
        <div style={{ fontSize: 15, fontWeight: 600, color, lineHeight: 1.1 }}>{value}</div>
        <div style={{ fontSize: 10, color: "var(--text-faint)" }}>
          {label} · {hint}
        </div>
      </div>
    </div>
  );
}

function CheckRow({ check, showHint = false }: { check: ContentQualityCheck; showHint?: boolean }) {
  const icon = !check.applicable ? (
    <CircleDashed size={13} aria-hidden style={{ color: "var(--text-faint)", flexShrink: 0, marginTop: 2 }} />
  ) : check.passed ? (
    <Check size={13} aria-hidden style={{ color: "var(--mint)", flexShrink: 0, marginTop: 2 }} />
  ) : (
    <X size={13} aria-hidden style={{ color: "var(--danger-soft)", flexShrink: 0, marginTop: 2 }} />
  );

  return (
    <li style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
      {icon}
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 12, color: check.applicable ? "var(--text-muted)" : "var(--text-faint)" }}>
          {check.label}
          <span style={{ fontSize: 10, color: "var(--text-faint)", marginLeft: 6 }}>
            {check.family.toUpperCase()}
            {!check.applicable && " · não se aplica"}
          </span>
        </div>
        {showHint && <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 3, lineHeight: 1.45 }}>{check.hint}</div>}
      </div>
    </li>
  );
}
