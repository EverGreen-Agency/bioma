import { Suspense, lazy, useEffect, type ReactNode } from "react";
import { Building2 } from "lucide-react";
import { Navigate, Outlet, useNavigate, useOutletContext, useParams } from "react-router-dom";

import { EmptyState } from "../components/shared";
import { clientHubNavItems } from "../lib/app-config";
import type { ClientModule, ClientSummary } from "../lib/api";
import { externalClients } from "../lib/client-scope";
import { clientWorkspaceContext, type ClientWorkspaceContext } from "../lib/workspace-context";
import { useClients, useCurrentUser, useWorkspaces } from "../hooks/useBiomaApi";
import { useUiStore } from "../store/uiStore";

const AnalyticsView = lazy(() => import("./AnalyticsView").then((module) => ({ default: module.AnalyticsView })));
const CrmView = lazy(() => import("./CrmView").then((module) => ({ default: module.CrmView })));
const TasksView = lazy(() => import("./TasksView").then((module) => ({ default: module.TasksView })));
const FinanceView = lazy(() => import("./FinanceView").then((module) => ({ default: module.FinanceView })));
const FilesPanel = lazy(() => import("../components/FilesPanel").then((module) => ({ default: module.FilesPanel })));
const IntegrationsTab = lazy(() => import("../components/IntegrationsTab").then((module) => ({ default: module.IntegrationsTab })));
const AiContentStudio = lazy(() => import("../components/AiContentStudio").then((module) => ({ default: module.AiContentStudio })));
const AccessVault = lazy(() => import("../components/AccessVault").then((module) => ({ default: module.AccessVault })));
const ProjectsPanel = lazy(() => import("../components/ProjectsPanel").then((module) => ({ default: module.ProjectsPanel })));
const ClientProfilePanel = lazy(() => import("../components/ClientProfilePanel").then((module) => ({ default: module.ClientProfilePanel })));

export type ClientWorkspaceOutletContext = {
  client: ClientSummary;
  workspace: ClientWorkspaceContext;
  isEgAdmin: boolean;
};

function ModuleLoading() {
  return <EmptyState text="Carregando módulo do cliente..." />;
}

export function ClientWorkspaceView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: clientsData, isLoading: loadingClients } = useClients();
  const { data: workspacesData, isLoading: loadingWorkspaces } = useWorkspaces();
  const { data: user } = useCurrentUser();
  const setSelectedClientId = useUiStore((state) => state.setSelectedClientId);

  const clients = externalClients(clientsData ?? []);
  const client = clients.find((candidate) => candidate.id === id) ?? null;
  const persistedWorkspace = (workspacesData ?? []).find(
    (workspace) => workspace.kind === "client" && workspace.client_id === client?.id,
  ) ?? null;
  const isEgAdmin = user?.organizations.some(
    (organization: { slug: string; role: string }) => organization.slug === "eg" && organization.role === "eg_admin",
  ) ?? false;

  useEffect(() => {
    if (!client) return;
    setSelectedClientId(client.id);
    return () => {
      if (useUiStore.getState().selectedClientId === client.id) {
        setSelectedClientId(null);
      }
    };
  }, [client, setSelectedClientId]);

  if (loadingClients || loadingWorkspaces) {
    return <EmptyState text="Carregando Hub do Cliente..." />;
  }

  if (!client || !persistedWorkspace) {
    return (
      <section className="workspace-empty">
        <EmptyState text="Cliente ou workspace não encontrado para esta sessão." />
        <button className="primary-button" type="button" onClick={() => navigate("/clientes")}>
          Voltar para a Carteira
        </button>
      </section>
    );
  }

  const enabledModules = new Set(client.enabled_modules ?? ["hub"]);
  enabledModules.add("hub");
  const visibleItems = clientHubNavItems.filter(
    (item) => enabledModules.has(item.module),
  );
  const workspace = clientWorkspaceContext(client, persistedWorkspace);
  const items = visibleItems.map((item) => ({
    id: item.id,
    label: item.label,
    icon: item.icon,
    to: item.path ? `/clientes/${client.id}/${item.path}` : `/clientes/${client.id}`,
    end: !item.path,
  }));

  return (
    <section className="workspace-shell">
      <div className="workspace-shell-content">
        <Outlet context={{ client, workspace, isEgAdmin } satisfies ClientWorkspaceOutletContext} />
      </div>
    </section>
  );
}

function useClientWorkspace() {
  return useOutletContext<ClientWorkspaceOutletContext>();
}

function ClientModuleBoundary({ module, children }: { module: ClientModule; children: ReactNode }) {
  const { client, isEgAdmin } = useClientWorkspace();
  const enabledModules = new Set(client.enabled_modules ?? ["hub"]);
  enabledModules.add("hub");
  if (!isEgAdmin && !enabledModules.has(module)) {
    return <Navigate to={`/clientes/${client.id}`} replace />;
  }
  return children;
}

export function ClientCrmRoute() {
  const { workspace } = useClientWorkspace();
  return (
    <ClientModuleBoundary module="commercial">
      <Suspense fallback={<ModuleLoading />}><CrmView clientId={workspace.workspaceId} /></Suspense>
    </ClientModuleBoundary>
  );
}

export function ClientTasksRoute() {
  const { workspace } = useClientWorkspace();
  return (
    <ClientModuleBoundary module="hub">
      <Suspense fallback={<ModuleLoading />}><TasksView workspaceId={workspace.workspaceId} /></Suspense>
    </ClientModuleBoundary>
  );
}

export function ClientAiContentRoute() {
  const { workspace } = useClientWorkspace();
  return (
    <ClientModuleBoundary module="content">
      <Suspense fallback={<ModuleLoading />}><AiContentStudio workspaceId={workspace.workspaceId} /></Suspense>
    </ClientModuleBoundary>
  );
}

export function ClientFinanceRoute() {
  const { workspace } = useClientWorkspace();
  return (
    <ClientModuleBoundary module="commercial">
      <Suspense fallback={<ModuleLoading />}><FinanceView clientId={workspace.workspaceId} /></Suspense>
    </ClientModuleBoundary>
  );
}

export function ClientAnalyticsRoute() {
  const { workspace } = useClientWorkspace();
  return (
    <ClientModuleBoundary module="analytics">
      <Suspense fallback={<ModuleLoading />}><AnalyticsView clientId={workspace.workspaceId} /></Suspense>
    </ClientModuleBoundary>
  );
}

export function ClientFilesRoute() {
  const { workspace, isEgAdmin } = useClientWorkspace();
  return (
    <ClientModuleBoundary module="files">
      <div className="workspace-module-panel">
        <Suspense fallback={<ModuleLoading />}><FilesPanel clientId={workspace.workspaceId} isEgAdmin={isEgAdmin} /></Suspense>
      </div>
    </ClientModuleBoundary>
  );
}

export function ClientVaultRoute() {
  const { workspace } = useClientWorkspace();
  return (
    <ClientModuleBoundary module="hub">
      <div className="workspace-module-panel">
        <Suspense fallback={<ModuleLoading />}>
          <AccessVault workspaceId={workspace.workspaceId} accessRole={workspace.accessRole} />
        </Suspense>
      </div>
    </ClientModuleBoundary>
  );
}

export function ClientProjectsRoute() {
  const { workspace } = useClientWorkspace();
  return (
    <ClientModuleBoundary module="hub">
      <div className="workspace-module-panel">
        <Suspense fallback={<ModuleLoading />}>
          <ProjectsPanel workspaceId={workspace.workspaceId} accessRole={workspace.accessRole} />
        </Suspense>
      </div>
    </ClientModuleBoundary>
  );
}

export function ClientProfileRoute() {
  const { workspace } = useClientWorkspace();
  return (
    <ClientModuleBoundary module="hub">
      <div className="workspace-module-panel">
        <Suspense fallback={<ModuleLoading />}>
          <ClientProfilePanel
            workspaceId={workspace.workspaceId}
            accessRole={workspace.accessRole}
            organizationId={workspace.organizationId}
          />
        </Suspense>
      </div>
    </ClientModuleBoundary>
  );
}

export function ClientIntegrationsRoute() {
  const { client } = useClientWorkspace();
  return (
    <ClientModuleBoundary module="integrations">
      <div className="workspace-module-panel">
        <Suspense fallback={<ModuleLoading />}><IntegrationsTab clientId={client.id} scope="client" /></Suspense>
      </div>
    </ClientModuleBoundary>
  );
}
