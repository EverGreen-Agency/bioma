import { PenLine } from "lucide-react";
import type { ArtifactSummary } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { ArtifactSectionGrid } from "./ArtifactSections";
import { EmptyState } from "./shared";

export function BriefingPanel({
  briefing,
  onEdit,
}: {
  briefing: ArtifactSummary | null;
  onEdit: (artifact: ArtifactSummary) => void;
}) {
  return (
    <>
      <div className="panel-heading compact">
        <div>
          <p className="eyebrow">Onboarding</p>
          <h2>Briefing estratégico</h2>
        </div>
        {briefing && (
          <button className="ghost-button dark" type="button" onClick={() => onEdit(briefing)}>
            <PenLine size={14} />
            Editar briefing
          </button>
        )}
      </div>

      {briefing ? (
        <>
          <ArtifactSectionGrid
            content={briefing.content}
            emptyText="Briefing sem conteúdo textual. Edite o artefato para preencher as seções."
          />
          <p className="panel-footnote">
            {briefing.title} · criado em {formatDateTime(briefing.created_at)} ·{" "}
            {briefing.visibility === "client" ? "visível para cliente" : "uso interno EG"}
          </p>
        </>
      ) : (
        <EmptyState text="Nenhum briefing cadastrado. Crie um artefato do tipo Briefing para este cliente." />
      )}
    </>
  );
}
