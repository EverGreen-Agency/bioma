import type { CSSProperties, DragEvent } from "react";
import type { Idea, Stage } from "../../../types/idea";
import { CAT_COLOR, CAT_DESC, CAT_LABEL, HORIZON_META, STAGES, ideaStyles as styles } from "./idea-bank-config";

interface IdeaCardProps {
  idea: Idea;
  ideas: Idea[];
  stage: Stage;
  expanded: boolean;
  dragging: boolean;
  onToggle: () => void;
  onMove: (idea: Idea, dir: 1 | -1) => void;
  onArchive: (idea: Idea) => void;
  onEdit: () => void;
  onReadDoc: () => void;
  onDragStart: () => void;
  onDragEnd: () => void;
}

export function IdeaCard({
  idea,
  ideas,
  stage,
  expanded,
  dragging,
  onToggle,
  onMove,
  onArchive,
  onEdit,
  onReadDoc,
  onDragStart,
  onDragEnd,
}: IdeaCardProps) {
  const catColor = CAT_COLOR[idea.category] ?? "#8888a0";
  const stageIdx = STAGES.indexOf(stage);
  const hasPrev = stageIdx > 0;
  const hasNext = stageIdx < STAGES.length - 1;

  const dependsOn = idea.depends_on.map((id) => ideas.find((i) => i.id === id)?.title ?? id);
  const enables = idea.enables.map((id) => ideas.find((i) => i.id === id)?.title ?? id);
  const horizon = HORIZON_META[idea.horizon];
  const parent = idea.part_of ? (ideas.find((i) => i.id === idea.part_of)?.title ?? idea.part_of) : null;
  const parentShort = parent ? (parent.length > 20 ? parent.slice(0, 18) + "…" : parent) : null;
  const childrenCount = ideas.filter((i) => i.part_of === idea.id && !i.archived).length;

  return (
    <div
      draggable
      onClick={onToggle}
      onDragStart={(e: DragEvent<HTMLDivElement>) => { e.dataTransfer.effectAllowed = "move"; onDragStart(); }}
      onDragEnd={onDragEnd}
      style={{
        ...styles.card,
        borderColor: expanded ? `${catColor}55` : "var(--border)",
        opacity: dragging ? 0.35 : (idea.archived ? 0.45 : 1),
        cursor: dragging ? "grabbing" : "grab",
        transform: dragging ? "scale(0.97)" : undefined,
        transition: "opacity 0.1s, transform 0.1s, border-color 0.12s",
      }}
    >
      {/* Linha do título */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 6, marginBottom: 5 }}>
        <span style={{ flex: 1, fontSize: 12, fontWeight: 600, lineHeight: 1.45 }}>
          {idea.title}
        </span>
        {idea.origin === "external" && (
          <span title="Origem externa" style={{ fontSize: 10, color: "var(--text-secondary)", flexShrink: 0, marginTop: 1 }}>
            ↗
          </span>
        )}
      </div>

      {/* Descrição */}
      <div
        style={{
          fontSize: 11,
          color: "var(--text-secondary)",
          lineHeight: 1.55,
          marginBottom: 8,
          ...(expanded ? {} : {
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          } as CSSProperties),
        }}
      >
        {idea.desc}
      </div>

      {/* Badges */}
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
        <span
          title={CAT_DESC[idea.category]}
          style={{ ...styles.badge, background: `${catColor}22`, color: catColor, fontWeight: 700, cursor: "help" }}
        >
          {CAT_LABEL[idea.category] ?? idea.category}
        </span>
        {horizon && (
          <span
            title="Horizonte de urgência para desenvolvimento"
            style={{
              ...styles.badge,
              background: `${horizon.color}22`,
              color: horizon.color,
              border: `1px solid ${horizon.color}44`,
              fontWeight: 700,
            }}
          >
            {horizon.label}
          </span>
        )}
        {idea.depends_on.length > 0 && (
          <span style={{ ...styles.badge, color: "var(--text-secondary)" }} title={`Depende de: ${dependsOn.join(", ")}`}>
            ← {idea.depends_on.length}
          </span>
        )}
        {idea.enables.length > 0 && (
          <span style={{ ...styles.badge, color: "var(--text-secondary)" }} title={`Habilita: ${enables.join(", ")}`}>
            → {idea.enables.length}
          </span>
        )}
        {parent && (
          <span style={{ ...styles.badge, color: "var(--text-secondary)" }} title={`Faz parte de: ${parent}`}>
            ⊂ {parentShort}
          </span>
        )}
        {childrenCount > 0 && (
          <span style={{ ...styles.badge, color: "#3ac97b", background: "#3ac97b18" }} title={`Contém ${childrenCount} módulo(s)/ideia(s)`}>
            ⊃ {childrenCount}
          </span>
        )}
      </div>

      {/* Expandido: conexões + ações */}
      {expanded && (
        <div onClick={(e) => e.stopPropagation()}>
          {dependsOn.length > 0 && (
            <div style={styles.connectionRow}>
              <span style={{ color: "var(--text-secondary)" }}>← depende de: </span>
              {dependsOn.join(", ")}
            </div>
          )}
          {enables.length > 0 && (
            <div style={styles.connectionRow}>
              <span style={{ color: "var(--text-secondary)" }}>→ habilita: </span>
              {enables.join(", ")}
            </div>
          )}
          {parent && (
            <div style={styles.connectionRow}>
              <span style={{ color: "var(--text-secondary)" }}>⊂ faz parte de: </span>
              {parent}
            </div>
          )}
          {childrenCount > 0 && (
            <div style={styles.connectionRow}>
              <span style={{ color: "#3ac97b" }}>⊃ contém: </span>
              {childrenCount} módulo(s)/ideia(s)
            </div>
          )}
          {idea.readiness && (
            <div style={styles.connectionRow}>
              <span style={{ color: "var(--text-secondary)" }}>prontidão: </span>
              {idea.readiness}
            </div>
          )}
          {idea.source && (
            <div style={{ marginTop: 4, fontSize: 10, color: "var(--text-secondary)", fontStyle: "italic" }}>
              {idea.source}
            </div>
          )}

          <div style={{ marginTop: 12, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {hasPrev && (
              <button onClick={() => onMove(idea, -1)} style={styles.actionBtn}>
                ← Recuar
              </button>
            )}
            {hasNext && (
              <button
                onClick={() => onMove(idea, 1)}
                style={{ ...styles.actionBtn, color: "#00d4ff", borderColor: "#00d4ff44" }}
              >
                Avançar →
              </button>
            )}
            <button
              onClick={onEdit}
              style={{ ...styles.actionBtn, color: "#ffab00", borderColor: "#ffab0044" }}
            >
              ✎ Editar
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onReadDoc(); }}
              style={{ ...styles.actionBtn, color: "#a855f7", borderColor: "#a855f744" }}
            >
              📄 Ler Detalhes
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onArchive(idea); }}
              title={idea.archived
                ? "Restaurar: traz a ideia de volta pro board ativo."
                : "Arquivar: cemitério de ideias rejeitadas/superadas conscientemente (com o motivo) — some do board mas fica consultável. Pra lixo real (duplicata/teste), exclua em vez de arquivar."}
              style={{ ...styles.actionBtn, marginLeft: "auto" }}
            >
              {idea.archived ? "Restaurar" : "Arquivar"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
