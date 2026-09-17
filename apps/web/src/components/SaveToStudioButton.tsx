import { useState } from "react";
import { BookmarkPlus, Check } from "lucide-react";
import { useSaveArtifactFromRun } from "../hooks/useBiomaApi";

/** "Salvar no Estúdio" — a ponta que faz a conversa produzir algo que dura.
 *
 * Sem este botão o resto da decisão 8 existe e ninguém alcança: a API grava
 * artefato, o Estúdio mostra, e não haveria como ir de um ao outro pela tela.
 *
 * Não pergunta thread nem execução: quem sabe isso é o servidor, que deduz da
 * própria run. Aqui só se escolhe o nome e o tipo — e o tipo é texto livre
 * porque a taxonomia é aberta. */
export function SaveToStudioButton({
  runId,
  defaultTitle,
  workspaceId,
}: {
  runId: string;
  defaultTitle: string;
  workspaceId?: string | null;
}) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState("roteiro");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const save = useSaveArtifactFromRun();

  function handleOpen() {
    // Sugere as primeiras palavras da resposta como título: quase sempre serve,
    // e quando não serve é mais rápido corrigir que digitar do zero.
    setTitle(defaultTitle.replace(/\s+/g, " ").trim().slice(0, 60));
    setError("");
    setOpen(true);
  }

  function handleSave() {
    setError("");
    save.mutate(
      { runId, title: title.trim(), kind: kind.trim() || "roteiro", workspace_id: workspaceId ?? null },
      {
        onSuccess: () => {
          setSaved(true);
          setOpen(false);
          setTimeout(() => setSaved(false), 3000);
        },
        onError: (err) => setError(err instanceof Error ? err.message : "Não foi possível salvar."),
      },
    );
  }

  if (saved) {
    return (
      <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11.5, color: "var(--mint)" }}>
        <Check size={12} /> Salvo no Estúdio
      </span>
    );
  }

  if (!open) {
    return (
      <button className="copilot-trace-toggle" type="button" onClick={handleOpen}>
        <BookmarkPlus size={12} /> Salvar no Estúdio
      </button>
    );
  }

  return (
    <div
      style={{
        display: "flex", flexDirection: "column", gap: 8, marginTop: 8, padding: 10,
        background: "var(--bg-elevated)", borderRadius: 8, border: "1px solid var(--border-light)",
      }}
    >
      <input
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder="Nome da peça"
        style={{ fontSize: 12.5 }}
        autoFocus
      />
      <input
        value={kind}
        onChange={(event) => setKind(event.target.value)}
        placeholder="Tipo (roteiro, post, legenda...)"
        style={{ fontSize: 12.5 }}
        list="studio-kind-suggestions"
      />
      <datalist id="studio-kind-suggestions">
        {["roteiro", "post", "legenda", "prompt-de-arte", "planejamento", "mensagem"].map((item) => (
          <option key={item} value={item} />
        ))}
      </datalist>

      {error && <span style={{ fontSize: 11.5, color: "var(--danger)" }}>{error}</span>}

      <div style={{ display: "flex", gap: 6 }}>
        <button
          type="button"
          className="mini-button approve"
          disabled={save.isPending || title.trim().length < 2}
          onClick={handleSave}
        >
          {save.isPending ? "Salvando..." : "Salvar"}
        </button>
        <button type="button" className="mini-button" onClick={() => setOpen(false)}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
