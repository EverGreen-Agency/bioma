import type { ClientSummary, CurrentUser, WorkspaceSummary } from "../lib/api";
import { WorkspaceNavigator } from "./WorkspaceNavigator";

export function Topbar({
  user,
  clients,
  workspaces,
  isLoading,
  errorMessage,
  onRetry,
}: {
  user: CurrentUser;
  clients: ClientSummary[];
  workspaces: WorkspaceSummary[];
  isLoading: boolean;
  errorMessage: string | null;
  onRetry: () => void;
}) {
  return (
    <header className="topbar">
      <WorkspaceNavigator
        user={user}
        clients={clients}
        workspaces={workspaces}
        isLoading={isLoading}
        errorMessage={errorMessage}
        onRetry={onRetry}
      />
    </header>
  );
}
