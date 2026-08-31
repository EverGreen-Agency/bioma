import type { ClientSummary, CurrentUser, WorkspaceSummary } from "./api";

export type AgencyWorkspaceContext = {
  kind: "agency_internal";
  workspaceId: string;
  tenantOrganizationId: string;
  organizationId: string;
  organizationName: string;
  name: string;
  accessRole: WorkspaceSummary["access_role"];
};

export type ClientWorkspaceContext = {
  kind: "client";
  workspaceId: string;
  organizationId: string;
  organizationName: string;
  clientId: string;
  name: string;
  accessRole: WorkspaceSummary["access_role"];
};

export type WorkspaceContext = AgencyWorkspaceContext | ClientWorkspaceContext;

export type AgencyWorkspaceResolution =
  | { status: "ready"; workspace: AgencyWorkspaceContext }
  | { status: "missing_organization" }
  | { status: "missing_workspace"; organizationName: string };

export function clientWorkspaceContext(client: ClientSummary, workspace: WorkspaceSummary): ClientWorkspaceContext {
  return {
    kind: "client",
    workspaceId: workspace.id,
    organizationId: client.organization_id,
    organizationName: client.organization_name,
    clientId: client.id,
    name: client.name,
    accessRole: workspace.access_role,
  };
}

/**
 * Resolve o workspace operacional interno da agência EG.
 */
export function resolveAgencyWorkspace(
  workspaces: WorkspaceSummary[],
  user: CurrentUser | null | undefined,
): AgencyWorkspaceResolution {
  const agencyOrganization = user?.organizations.find(
    (organization) => organization.slug === "eg" && organization.role === "eg_admin",
  );
  if (!agencyOrganization) return { status: "missing_organization" };

  const agencyWorkspace = workspaces.find(
    (workspace) => workspace.kind === "agency_internal" && workspace.organization_id === agencyOrganization.id,
  ) || workspaces.find((workspace) => workspace.kind === "agency_internal");

  if (!agencyWorkspace) {
    return { status: "missing_workspace", organizationName: agencyOrganization.name };
  }

  return {
    status: "ready",
    workspace: {
      kind: "agency_internal",
      workspaceId: agencyWorkspace.id,
      tenantOrganizationId: agencyWorkspace.tenant_organization_id,
      organizationId: agencyOrganization.id,
      organizationName: agencyOrganization.name,
      name: agencyWorkspace.name,
      accessRole: agencyWorkspace.access_role,
    },
  };
}

export function operationalClientId(workspace: WorkspaceContext): string {
  return workspace.workspaceId;
}
