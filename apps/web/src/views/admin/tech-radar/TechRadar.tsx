import { useState, useCallback } from "react";
import type { CSSProperties } from "react";
import type { Ring, Quadrant, Tech } from "../../../types/stack";
import { useAdminStack, useSaveAdminStack } from "../../../hooks/useBiomaApi";

// ── config ──────────────────────────────────────────────────────────────────

const RINGS: Ring[] = ["adopt", "trial", "assess", "hold"];

const RING_META: Record<Ring, { label: string; color: string; hint: string }> = {
  adopt:  { label: "Adotar",   color: "#3ac97b", hint: "Padrão da casa — usar sem pensar duas vezes." },
  trial:  { label: "Em Teste", color: "#ffab00", hint: "Testando em projeto real agora; vale apostar." },
  assess: { label: "Avaliar",  color: "#8fb4a3", hint: "Vale investigar, sem compromisso. Ainda é experimento." },
  hold:   { label: "Evitar",   color: "#ff6b5c", hint: "Não começar nada novo com isso. Substituir quando der." },
};

const QUADRANT_LABEL: Record<Quadrant, string> = {
  "languages":      "Linguagens",
  "frameworks":     "Frameworks",
  "tools":          "Ferramentas",
  "platforms-infra": "Plataformas & Infra",
};

const QUADRANTS: Quadrant[] = ["languages", "frameworks", "tools", "platforms-infra"];

// ── helpers ──────────────────────────────────────────────────────────────────

function newId(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

// ── empty tech form ───────────────────────────────────────────────────────────

const EMPTY_TECH: Omit<Tech, "id"> = {
  name: "", quadrant: "tools", ring: "assess", note: "", adr: "", source: "",
};

// ── component ─────────────────────────────────────────────────────────────────

export function TechRadar() {
  const { data: radar, isLoading } = useAdminStack();
  const saveStack = useSaveAdminStack();
  const [quadFilter, setQuadFilter] = useState<Quadrant | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);

  const techs = radar?.techs ?? [];
  const save = useCallback((next: Tech[]) => saveStack.mutate(next), [saveStack]);

  const moveRing = useCallback((tech: Tech, dir: 1 | -1) => {
    const idx = RINGS.indexOf(tech.ring);
    const next = RINGS[idx + dir];
    if (!next) return;
    save(techs.map((t) => t.id === tech.id ? { ...t, ring: next } : t));
  }, [techs, save]);

  const deleteTech = useCallback((id: string) => {
    save(techs.filter((t) => t.id !== id));
  }, [techs, save]);

  const addTech = useCallback((draft: Omit<Tech, "id">) => {
    const id = newId(draft.name) || `tech-${Date.now()}`;
    save([...techs, { ...draft, id }]);
    setShowAddForm(false);
  }, [techs, save]);

  const updateTech = useCallback((updated: Tech) => {
    save(techs.map((t) => t.id === updated.id ? updated : t));
  }, [techs, save]);

  if (isLoading) return <Centered>Carregando Tech Radar...</Centered>;
  if (!radar?.schema_version && techs.length === 0) return <Centered>stack.json não encontrado.</Centered>;

  const visible = quadFilter ? techs.filter((t) => t.quadrant === quadFilter) : techs;
  const byRing = (ring: Ring) => visible.filter((t) => t.ring === ring);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Toolbar */}
      <div style={s.toolbar}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>Tech Radar</span>
        <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
          {techs.length} tecnologias no radar
        </span>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {QUADRANTS.map((q) => {
            const active = quadFilter === q;
            return (
              <button
                key={q}
                type="button"
                onClick={() => setQuadFilter(active ? null : q)}
                style={{
                  ...s.filterBtn,
                  borderColor: active ? "var(--accent-cyan)" : "var(--border)",
                  background: active ? "rgba(58,201,123,0.13)" : "transparent",
                  color: active ? "var(--accent-cyan)" : "var(--text-secondary)",
                }}
              >
                {QUADRANT_LABEL[q]}
              </button>
            );
          })}
        </div>
        <div style={{ marginLeft: "auto" }}>
          <button
            type="button"
            onClick={() => setShowAddForm(!showAddForm)}
            style={{
              ...s.filterBtn,
              borderColor: showAddForm ? "var(--accent-cyan)" : "var(--border)",
              background: showAddForm ? "rgba(58,201,123,0.13)" : "transparent",
              color: showAddForm ? "var(--accent-cyan)" : "var(--text-secondary)",
            }}
          >
            {showAddForm ? "✕ Cancelar" : "+ Nova Tech"}
          </button>
        </div>
      </div>

      {/* Add form */}
      {showAddForm && (
        <AddTechForm onAdd={addTech} onCancel={() => setShowAddForm(false)} />
      )}

      {/* Rings board */}
      <div style={s.board}>
        {RINGS.map((ring) => {
          const cards = byRing(ring);
          const meta = RING_META[ring];
          return (
            <div key={ring} style={s.column}>
              <div style={{ borderTop: `2px solid ${meta.color}`, paddingTop: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: 0.6, color: meta.color, textTransform: "uppercase" }}>
                  {meta.label}
                </span>
                <span style={{ marginLeft: 6, fontSize: 11, color: "var(--text-secondary)" }}>
                  {cards.length}
                </span>
              </div>
              <div style={{ fontSize: 10, color: "var(--text-secondary)", marginBottom: 10, lineHeight: 1.4 }}>
                {meta.hint}
              </div>
              <div style={s.cardList}>
                {cards.length === 0 && (
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", fontStyle: "italic" }}>—</div>
                )}
                {cards.map((tech) => (
                  <TechCard
                    key={tech.id}
                    tech={tech}
                    ringColor={meta.color}
                    ringIdx={RINGS.indexOf(ring)}
                    totalRings={RINGS.length}
                    onMove={moveRing}
                    onDelete={deleteTech}
                    onUpdate={updateTech}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── tech card ─────────────────────────────────────────────────────────────────

interface TechCardProps {
  tech: Tech;
  ringColor: string;
  ringIdx: number;
  totalRings: number;
  onMove: (tech: Tech, dir: 1 | -1) => void;
  onDelete: (id: string) => void;
  onUpdate: (tech: Tech) => void;
}

function TechCard({ tech, ringColor, ringIdx, totalRings, onMove, onDelete, onUpdate }: TechCardProps) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Tech>(tech);

  const hasPrev = ringIdx > 0;
  const hasNext = ringIdx < totalRings - 1;

  function handleSave() {
    onUpdate(draft);
    setEditing(false);
    setOpen(false);
  }

  if (editing) {
    return (
      <div style={{ ...s.card, borderColor: `${ringColor}55` }} onClick={(e) => e.stopPropagation()}>
        <input
          value={draft.name}
          onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
          style={s.editInput}
          placeholder="Nome"
          autoFocus
        />
        <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
          <select
            value={draft.quadrant}
            onChange={(e) => setDraft((d) => ({ ...d, quadrant: e.target.value as Quadrant }))}
            style={s.editSelect}
          >
            {QUADRANTS.map((q) => <option key={q} value={q}>{QUADRANT_LABEL[q]}</option>)}
          </select>
          <select
            value={draft.ring}
            onChange={(e) => setDraft((d) => ({ ...d, ring: e.target.value as Ring }))}
            style={s.editSelect}
          >
            {RINGS.map((r) => <option key={r} value={r}>{RING_META[r].label}</option>)}
          </select>
        </div>
        <textarea
          value={draft.note}
          onChange={(e) => setDraft((d) => ({ ...d, note: e.target.value }))}
          rows={3}
          style={{ ...s.editInput, resize: "vertical", marginTop: 6 }}
          placeholder="Nota / contexto"
        />
        <input
          value={draft.source}
          onChange={(e) => setDraft((d) => ({ ...d, source: e.target.value }))}
          style={{ ...s.editInput, marginTop: 6 }}
          placeholder="Fonte"
        />
        <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
          <button type="button" onClick={handleSave} style={{ ...s.actionBtn, color: "#3ac97b", borderColor: "#3ac97b55", flex: 1 }}>
            Salvar
          </button>
          <button type="button" onClick={() => { setEditing(false); setDraft(tech); }} style={{ ...s.actionBtn, flex: 1 }}>
            Cancelar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={() => setOpen(!open)}
      style={{ ...s.card, borderColor: open ? `${ringColor}55` : "var(--border)" }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ flex: 1, fontSize: 12, fontWeight: 600 }}>{tech.name}</span>
        <span style={{ ...s.badge, color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
          {QUADRANT_LABEL[tech.quadrant]}
        </span>
      </div>
      {open && (
        <div onClick={(e) => e.stopPropagation()}>
          {tech.note && (
            <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5, marginTop: 6 }}>
              {tech.note}
            </div>
          )}
          {(tech.adr || tech.source) && (
            <div style={{ fontSize: 10, color: "var(--text-secondary)", fontStyle: "italic", marginTop: 4 }}>
              {tech.adr ? `ADR: ${tech.adr} · ` : ""}{tech.source}
            </div>
          )}
          <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {hasPrev && (
              <button type="button" onClick={() => onMove(tech, -1)} style={s.actionBtn} title={`Mover para ${RING_META[RINGS[ringIdx - 1]].label}`}>
                ← {RING_META[RINGS[ringIdx - 1]].label}
              </button>
            )}
            {hasNext && (
              <button type="button" onClick={() => onMove(tech, 1)} style={{ ...s.actionBtn, color: ringColor, borderColor: `${ringColor}44` }} title={`Mover para ${RING_META[RINGS[ringIdx + 1]].label}`}>
                {RING_META[RINGS[ringIdx + 1]].label} →
              </button>
            )}
            <button type="button" onClick={() => setEditing(true)} style={{ ...s.actionBtn, color: "#ffab00", borderColor: "#ffab0044" }}>
              ✎ Editar
            </button>
            <button
              type="button"
              onClick={() => { if (confirm(`Remover "${tech.name}" do radar?`)) onDelete(tech.id); }}
              style={{ ...s.actionBtn, marginLeft: "auto", color: "#ff6b5c", borderColor: "#ff6b5c44" }}
            >
              🗑
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── add tech form ─────────────────────────────────────────────────────────────

function AddTechForm({ onAdd, onCancel }: { onAdd: (t: Omit<Tech, "id">) => void; onCancel: () => void }) {
  const [draft, setDraft] = useState<Omit<Tech, "id">>({ ...EMPTY_TECH });

  return (
    <div style={s.addForm}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <input
          value={draft.name}
          onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
          placeholder="Nome da tech (ex: Bun, Drizzle ORM...)"
          style={{ ...s.editInput, flex: 2, minWidth: 160 }}
          autoFocus
        />
        <select
          value={draft.quadrant}
          onChange={(e) => setDraft((d) => ({ ...d, quadrant: e.target.value as Quadrant }))}
          style={s.editSelect}
        >
          {QUADRANTS.map((q) => <option key={q} value={q}>{QUADRANT_LABEL[q]}</option>)}
        </select>
        <select
          value={draft.ring}
          onChange={(e) => setDraft((d) => ({ ...d, ring: e.target.value as Ring }))}
          style={s.editSelect}
        >
          {RINGS.map((r) => <option key={r} value={r}>{RING_META[r].label}</option>)}
        </select>
        <input
          value={draft.note}
          onChange={(e) => setDraft((d) => ({ ...d, note: e.target.value }))}
          placeholder="Nota / por que está aqui"
          style={{ ...s.editInput, flex: 3, minWidth: 200 }}
        />
        <input
          value={draft.source}
          onChange={(e) => setDraft((d) => ({ ...d, source: e.target.value }))}
          placeholder="Fonte"
          style={{ ...s.editInput, flex: 1, minWidth: 100 }}
        />
        <button
          type="button"
          onClick={() => draft.name.trim() && onAdd(draft)}
          style={{ ...s.actionBtn, color: "#3ac97b", borderColor: "#3ac97b55", whiteSpace: "nowrap" }}
        >
          + Adicionar
        </button>
        <button type="button" onClick={onCancel} style={s.actionBtn}>✕</button>
      </div>
    </div>
  );
}

// ── helpers ───────────────────────────────────────────────────────────────────

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)", fontSize: 13 }}>
      {children}
    </div>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const s: Record<string, CSSProperties> = {
  toolbar: {
    display: "flex", alignItems: "center", gap: 12, padding: "10px 16px",
    borderBottom: "1px solid var(--border)", flexShrink: 0, flexWrap: "wrap",
    background: "var(--bg-sidebar)",
  },
  filterBtn: {
    padding: "3px 8px", borderRadius: 4, fontSize: 11, fontFamily: "inherit",
    cursor: "pointer", border: "1px solid", transition: "all 0.12s",
  },
  addForm: {
    padding: "10px 16px", borderBottom: "1px solid var(--border)",
    background: "var(--bg-secondary)", flexShrink: 0,
  },
  board: {
    flex: 1, display: "flex", gap: 12, padding: 16,
    overflowX: "auto", overflowY: "hidden", alignItems: "flex-start",
  },
  column: {
    width: 256, minWidth: 256, display: "flex", flexDirection: "column", maxHeight: "100%",
  },
  cardList: {
    display: "flex", flexDirection: "column", gap: 8, overflowY: "auto", flex: 1,
  },
  card: {
    background: "var(--bg-secondary)", border: "1px solid", borderRadius: 6,
    padding: "8px 12px", cursor: "pointer", transition: "border-color 0.12s",
  },
  badge: { fontSize: 10, padding: "2px 5px", borderRadius: 3 },
  actionBtn: {
    padding: "3px 8px", borderRadius: 4, fontSize: 11, fontFamily: "inherit",
    cursor: "pointer", border: "1px solid var(--border)", background: "transparent",
    color: "var(--text-secondary)",
  },
  editInput: {
    background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 4,
    padding: "5px 8px", color: "var(--text-primary)", fontSize: 12, fontFamily: "inherit",
    width: "100%", boxSizing: "border-box" as const, outline: "none",
  },
  editSelect: {
    background: "var(--bg-primary)", border: "1px solid var(--border)", borderRadius: 4,
    padding: "4px 6px", color: "var(--text-primary)", fontSize: 11, fontFamily: "inherit",
    cursor: "pointer",
  },
};
