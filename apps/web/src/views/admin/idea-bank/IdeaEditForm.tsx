import { useEffect, useRef, useState } from "react";
import type { Category, Horizon, Idea } from "../../../types/idea";
import { CAT_LABEL, ideaStyles as styles } from "./idea-bank-config";

export function IdeaEditForm({ idea, onSave, onCancel }: { idea: Idea; onSave: (i: Idea) => void; onCancel: () => void }) {
  const [draft, setDraft] = useState<Idea>({ ...idea });
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => { titleRef.current?.focus(); }, []);

  const field = (key: keyof Idea, value: string | boolean) =>
    setDraft((d) => ({ ...d, [key]: value }));

  return (
    <div
      onClick={(e) => e.stopPropagation()}
      style={{ ...styles.card, borderColor: "#ffab0055", display: "flex", flexDirection: "column", gap: 8 }}
    >
      <input
        ref={titleRef}
        value={draft.title}
        onChange={(e) => field("title", e.target.value)}
        placeholder="Título"
        style={{ ...styles.editInput, fontWeight: 600 }}
      />
      <textarea
        value={draft.desc}
        onChange={(e) => field("desc", e.target.value)}
        placeholder="Descrição"
        rows={4}
        style={{ ...styles.editInput, resize: "vertical", lineHeight: 1.5 }}
      />
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <select
          value={draft.category}
          onChange={(e) => field("category", e.target.value as Category)}
          style={styles.editSelect}
        >
          {(["Squad", "Cockpit", "Feature", "Service", "Infra", "Commercial", "Platform"] as Category[]).map((c) => (
            <option key={c} value={c}>{CAT_LABEL[c] ?? c}</option>
          ))}
        </select>
        <select
          value={draft.horizon}
          onChange={(e) => field("horizon", e.target.value as Horizon)}
          style={styles.editSelect}
        >
          <option value="">— sem horizonte —</option>
          <option value="NOW">Agora</option>
          <option value="MEDIUM">Médio Prazo</option>
          <option value="LONG">Longo Prazo</option>
          <option value="NEW_COMPANY">Empresa Nova</option>
        </select>
      </div>
      <input
        value={draft.source}
        onChange={(e) => field("source", e.target.value)}
        placeholder="Fonte / referência"
        style={styles.editInput}
      />
      <div style={{ display: "flex", gap: 6 }}>
        <input
          value={draft.depends_on.join(", ")}
          onChange={(e) => setDraft((d) => ({ ...d, depends_on: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) }))}
          placeholder="Depende de (IDs separados por vírgula)"
          style={{ ...styles.editInput, fontSize: 10 }}
          title="IDs das ideias das quais esta depende"
        />
        <input
          value={draft.enables.join(", ")}
          onChange={(e) => setDraft((d) => ({ ...d, enables: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) }))}
          placeholder="Habilita (IDs separados por vírgula)"
          style={{ ...styles.editInput, fontSize: 10 }}
          title="IDs das ideias que esta ideia desbloqueia"
        />
      </div>
      <input
        value={draft.part_of ?? ""}
        onChange={(e) => setDraft((d) => ({ ...d, part_of: e.target.value.trim() || undefined }))}
        placeholder="Faz parte de (ID do módulo/umbrella — part_of)"
        style={{ ...styles.editInput, fontSize: 10 }}
        title="ID da ideia guarda-chuva/módulo que esta compõe (part_of)"
      />
      <textarea
        value={draft.readiness ?? ""}
        onChange={(e) => setDraft((d) => ({ ...d, readiness: e.target.value || undefined }))}
        placeholder="Prontidão / portões externos p/ começar (mercado, equipe, dinheiro)"
        rows={2}
        style={{ ...styles.editInput, resize: "vertical", fontSize: 10 }}
      />
      <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
        <button
          type="button"
          onClick={() => onSave(draft)}
          style={{ ...styles.actionBtn, color: "#3ac97b", borderColor: "#3ac97b55", flex: 1 }}
        >
          Salvar
        </button>
        <button type="button" onClick={onCancel} style={{ ...styles.actionBtn, flex: 1 }}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
