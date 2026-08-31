import { FormEvent } from "react";
import { Save, Trash2, X } from "lucide-react";
import type { ArtifactPayload, ArtifactSummary } from "../lib/api";
import { artifactKindLabel } from "../lib/format";

export function ArtifactModal({
  artifact,
  isEgAdmin,
  actionBusy,
  draft,
  setDraft,
  onSubmit,
  onDelete,
  onClose,
}: {
  artifact: ArtifactSummary;
  isEgAdmin: boolean;
  actionBusy: string | null;
  draft: ArtifactPayload;
  setDraft: (draft: ArtifactPayload) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="artifact-modal"
        role="dialog"
        aria-modal="true"
        aria-label={artifact.title}
        onClick={(event) => event.stopPropagation()}
      >
        <button className="modal-close" type="button" onClick={onClose} aria-label="Fechar artefato">
          <X size={18} />
        </button>
        {isEgAdmin ? (
          <form className="form-grid" onSubmit={onSubmit}>
            <p className="eyebrow">{artifactKindLabel(artifact.kind)}</p>
            <label>
              Título
              <input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} />
            </label>
            <div className="form-grid two">
              <label>
                Tipo
                <select value={draft.kind} onChange={(event) => setDraft({ ...draft, kind: event.target.value })}>
                  <option value="briefing">Briefing</option>
                  <option value="brand_book">Brand book</option>
                  <option value="calendar">Calendário</option>
                  <option value="integration_map">Mapa de integração</option>
                </select>
              </label>
              <label>
                Visibilidade
                <select
                  value={draft.visibility}
                  onChange={(event) => setDraft({ ...draft, visibility: event.target.value as ArtifactPayload["visibility"] })}
                >
                  <option value="client">Cliente</option>
                  <option value="internal">Interno EG</option>
                </select>
              </label>
            </div>
            <label>
              Conteúdo
              <textarea value={draft.content ?? ""} onChange={(event) => setDraft({ ...draft, content: event.target.value })} />
            </label>
            <div className="modal-actions">
              <button className="primary-button" type="submit" disabled={actionBusy === "artifact:update"}>
                <Save size={16} />
                Salvar
              </button>
              <button className="danger-button" type="button" onClick={onDelete} disabled={actionBusy === "artifact:delete"}>
                <Trash2 size={16} />
                Excluir
              </button>
            </div>
          </form>
        ) : (
          <>
            <p className="eyebrow">{artifactKindLabel(artifact.kind)}</p>
            <h2>{artifact.title}</h2>
            <p>{artifact.content ?? "Artefato sem conteúdo textual cadastrado."}</p>
            <small>{artifact.visibility === "client" ? "Visível para cliente" : "Uso interno EG"}</small>
          </>
        )}
      </section>
    </div>
  );
}
