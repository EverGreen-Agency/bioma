import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type SeoGeoAuditResponse, type SeoGeoAuditSummary } from "../../lib/api";

export function usePreviewSeoGeoAudit() {
  return useMutation({
    mutationFn: (url: string) => api.previewSeoGeoAudit(url),
  });
}

export function useWorkspaceSeoGeoAudits(workspaceId: string | null) {
  return useQuery({
    queryKey: ["seo-geo-audits", workspaceId],
    queryFn: () => (workspaceId ? api.listWorkspaceSeoGeoAudits(workspaceId) : Promise.resolve([])),
    enabled: Boolean(workspaceId),
  });
}

export function useWorkspaceSeoGeoAudit(workspaceId: string | null, auditId: string | null) {
  return useQuery({
    queryKey: ["seo-geo-audit", workspaceId, auditId],
    queryFn: () =>
      workspaceId && auditId ? api.getWorkspaceSeoGeoAudit(workspaceId, auditId) : Promise.resolve(null),
    enabled: Boolean(workspaceId && auditId),
  });
}

export function useCreateWorkspaceSeoGeoAudit(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (url: string) => {
      if (!workspaceId) throw new Error("Workspace obrigatório.");
      return api.createWorkspaceSeoGeoAudit(workspaceId, url);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["seo-geo-audits", workspaceId] });
    },
  });
}

export function useDeleteWorkspaceSeoGeoAudit(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (auditId: string) => {
      if (!workspaceId) throw new Error("Workspace obrigatório.");
      return api.deleteWorkspaceSeoGeoAudit(workspaceId, auditId);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["seo-geo-audits", workspaceId] });
    },
  });
}
