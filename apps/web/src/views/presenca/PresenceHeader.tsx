import type { WorkspaceSummary } from "../../lib/api";

interface PresenceHeaderProps {
  workspaces: WorkspaceSummary[];
  selectedWorkspace: WorkspaceSummary | null;
  onSelectWorkspace: (workspaceId: string) => void;
  itemsCount?: number;
  scheduledCount?: number;
}

export function PresenceHeader({
  workspaces,
  selectedWorkspace,
  onSelectWorkspace,
  itemsCount = 0,
  scheduledCount = 0,
}: PresenceHeaderProps) {
  return (
    <header className="presence-heading">
      <div className="presence-heading-left">
        <p className="presence-eyebrow">EVERGREEN · OPERAÇÃO SOCIAL</p>
        <div className="presence-title-row">
          <h1>Presença</h1>
          {selectedWorkspace && (
            <div className="presence-stat-badges">
              <span className="presence-stat-pill" title="Total de peças gerenciadas neste workspace">
                <strong>{itemsCount}</strong> peças
              </span>
              <span className="presence-stat-pill presence-stat-pill-scheduled" title="Peças com data e hora confirmadas">
                <strong>{scheduledCount}</strong> agendadas
              </span>
            </div>
          )}
        </div>
        <p className="presence-description">
          Planeje, produza, revise e aprove conteúdo com esteira assistida no workspace do cliente.
        </p>
      </div>

      <div className="presence-heading-right">
        <label className="presence-workspace-selector" htmlFor="presence-workspace-select">
          <span className="presence-label-text">Workspace Ativo</span>
          <select
            id="presence-workspace-select"
            value={selectedWorkspace?.id ?? ""}
            onChange={(event) => onSelectWorkspace(event.target.value)}
            disabled={!workspaces.length}
          >
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name} {w.client_id ? "(Cliente)" : "(Interno)"}
              </option>
            ))}
          </select>
        </label>
      </div>
    </header>
  );
}
