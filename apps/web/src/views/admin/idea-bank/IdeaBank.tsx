import { useCallback, useState } from "react";
import type { DragEvent } from "react";
import { useAdminIdeas, useSaveAdminIdeas } from "../../../hooks/useBiomaApi";
import type { Idea, Stage } from "../../../types/idea";
import { CATEGORIES, CAT_COLOR, CAT_DESC, CAT_LABEL, HORIZON_ORDER, STAGES, STAGE_META, ideaStyles as styles } from "./idea-bank-config";
import { IdeaCard } from "./IdeaCard";
import { IdeaEditForm } from "./IdeaEditForm";
import { IdeaDocModal } from "./IdeaDocModal";

export function IdeaBank() {
  const { data: ideas = [], isLoading } = useAdminIdeas();
  const saveIdeas = useSaveAdminIdeas();

  const [search, setSearch] = useState("");
  const [selectedCat, setSelectedCat] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dragOverStage, setDragOverStage] = useState<Stage | null>(null);
  const [readingDocId, setReadingDocId] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);

  const persist = useCallback((next: Idea[]) => saveIdeas.mutate(next), [saveIdeas]);

  const moveStage = useCallback((idea: Idea, dir: 1 | -1) => {
    const idx = STAGES.indexOf(idea.stage);
    const next = STAGES[idx + dir];
    if (!next) return;
    persist(ideas.map((i) => i.id === idea.id ? { ...i, stage: next } : i));
  }, [ideas, persist]);

  const toggleArchive = useCallback((idea: Idea) => {
    persist(ideas.map((i) => i.id === idea.id ? { ...i, archived: !i.archived } : i));
  }, [ideas, persist]);

  const moveToStage = useCallback((idea: Idea, targetStage: Stage) => {
    if (idea.stage === targetStage) return;
    persist(ideas.map((i) => i.id === idea.id ? { ...i, stage: targetStage } : i));
  }, [ideas, persist]);

  const saveEdit = useCallback((updated: Idea) => {
    persist(ideas.map((i) => i.id === updated.id ? updated : i));
    setEditingId(null);
  }, [ideas, persist]);

  const handleAddIdea = useCallback((draft: Idea) => {
    const newId = `ideia-${Date.now().toString(36)}`;
    persist([...ideas, { ...draft, id: newId }]);
    setShowAddForm(false);
  }, [ideas, persist]);

  const q = search.toLowerCase();
  const filtered = ideas.filter((i) => {
    if (!showArchived && i.archived) return false;
    if (selectedCat && i.category !== selectedCat) return false;
    if (q && !i.title.toLowerCase().includes(q) && !i.desc.toLowerCase().includes(q)) return false;
    return true;
  });

  const byStage = (stage: Stage) =>
    filtered
      .filter((i) => i.stage === stage)
      .sort((a, b) => (HORIZON_ORDER[a.horizon] ?? 9) - (HORIZON_ORDER[b.horizon] ?? 9));
  const activeCount = ideas.filter((i) => !i.archived).length;

  if (isLoading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)", fontSize: 13 }}>
        Carregando banco de ideias...
      </div>
    );
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Toolbar */}
      <div style={styles.toolbar}>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar ideia..."
            style={styles.searchInput}
          />
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {CATEGORIES.map((cat) => {
            const active = selectedCat === cat;
            const color = CAT_COLOR[cat];
            return (
              <button
                key={cat}
                onClick={() => setSelectedCat(active ? null : cat)}
                title={CAT_DESC[cat]}
                style={{
                  ...styles.filterBtn,
                  borderColor: active ? color : "var(--border)",
                  background: active ? `${color}22` : "transparent",
                  color: active ? color : "var(--text-secondary)",
                }}
              >
                {CAT_LABEL[cat] ?? cat}
              </button>
            );
          })}
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={() => setShowArchived(!showArchived)}
            title="Arquivadas = ideias consideradas e descartadas/superadas de propósito (com o motivo), guardadas pra não rediscutir. Não é a lixeira: pra lixo real (duplicata, card de teste), exclua em vez de arquivar."
            style={{ ...styles.filterBtn, borderColor: "var(--border)", color: "var(--text-secondary)" }}
          >
            {showArchived ? "Ocultar arquivadas" : "Ver arquivadas"}
          </button>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            style={{
              ...styles.filterBtn,
              borderColor: showAddForm ? "var(--accent)" : "var(--border)",
              background: showAddForm ? "rgba(58,201,123,0.13)" : "transparent",
              color: showAddForm ? "var(--accent)" : "var(--text-secondary)",
            }}
          >
            {showAddForm ? "✕ Cancelar" : "+ Nova Ideia"}
          </button>
          <span style={{ fontSize: 11, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
            {activeCount} ativas
          </span>
        </div>
      </div>

      {showAddForm && (
        <div style={{ padding: "12px 16px", background: "var(--surface)", borderBottom: "1px solid var(--border)" }}>
          <IdeaEditForm
            idea={{
              id: "temp-id",
              title: "",
              desc: "",
              category: "Feature",
              stage: "capture",
              origin: "internal",
              horizon: "",
              depends_on: [],
              enables: [],
              source: "",
              archived: false,
            }}
            onSave={handleAddIdea}
            onCancel={() => setShowAddForm(false)}
          />
        </div>
      )}

      {/* Kanban */}
      <div style={styles.board}>
        {STAGES.map((stage) => {
          const cards = byStage(stage);
          const { label, color, hint } = STAGE_META[stage];
          const isDropTarget = dragOverStage === stage && draggedId !== null;
          return (
            <div key={stage} style={styles.column}>
              <div style={{ borderTop: `2px solid ${color}`, paddingTop: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 0.8, color, textTransform: "uppercase" }}>
                  {label}
                </span>
                <span style={{ marginLeft: 6, fontSize: 11, color: "var(--text-secondary)" }}>
                  {cards.length}
                </span>
              </div>
              <div style={{ fontSize: 10, color: "var(--text-secondary)", marginBottom: 10, lineHeight: 1.4 }}>
                {hint}
              </div>
              <div
                style={{
                  ...styles.cardList,
                  outline: isDropTarget ? `2px dashed ${color}66` : "2px solid transparent",
                  borderRadius: 6,
                  background: isDropTarget ? `${color}0a` : undefined,
                  transition: "outline 0.1s, background 0.1s",
                  minHeight: 48,
                }}
                onDragOver={(e: DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOverStage(stage); }}
                onDragLeave={() => setDragOverStage(null)}
                onDrop={(e: DragEvent) => {
                  e.preventDefault();
                  if (draggedId) {
                    const idea = ideas.find((i) => i.id === draggedId);
                    if (idea) moveToStage(idea, stage);
                  }
                  setDraggedId(null);
                  setDragOverStage(null);
                }}
              >
                {cards.length === 0 && !isDropTarget && (
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", fontStyle: "italic", padding: "4px 0" }}>
                    —
                  </div>
                )}
                {isDropTarget && cards.length === 0 && (
                  <div style={{ fontSize: 11, color, fontStyle: "italic", padding: "4px 0", opacity: 0.7 }}>
                    Soltar aqui
                  </div>
                )}
                {cards.map((idea) => (
                  editingId === idea.id
                    ? <IdeaEditForm key={idea.id} idea={idea} onSave={saveEdit} onCancel={() => setEditingId(null)} />
                    : <IdeaCard
                        key={idea.id}
                        idea={idea}
                        ideas={ideas}
                        stage={stage}
                        expanded={expandedId === idea.id}
                        dragging={draggedId === idea.id}
                        onToggle={() => setExpandedId(expandedId === idea.id ? null : idea.id)}
                        onMove={moveStage}
                        onArchive={toggleArchive}
                        onEdit={() => { setEditingId(idea.id); setExpandedId(null); }}
                        onReadDoc={() => setReadingDocId(idea.id)}
                        onDragStart={() => setDraggedId(idea.id)}
                        onDragEnd={() => { setDraggedId(null); setDragOverStage(null); }}
                      />
                ))}
              </div>
            </div>
          );
        })}
      </div>
      {readingDocId && (
        <IdeaDocModal
          id={readingDocId}
          title={ideas.find((i) => i.id === readingDocId)?.title ?? ""}
          onClose={() => setReadingDocId(null)}
        />
      )}
    </div>
  );
}
