import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { LocalRadarImportRow, WhatsAppProviderType } from "../../lib/api";
import { api } from "../../lib/api";
import type { Idea } from "../../types/idea";
import type { Tech } from "../../types/stack";

export function useScriptScoreboard(workspaceId: string | null, periodDays = 90) {
  return useQuery({
    queryKey: ["content-script-scoreboard", workspaceId, periodDays],
    queryFn: () => api.getScriptScoreboard(workspaceId as string, periodDays),
    enabled: Boolean(workspaceId),
  });
}

export function useBuildBriefingDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, persist }: { workspaceId: string; persist: boolean }) =>
      api.buildBriefingDraft(workspaceId, persist),
    onSuccess: (data, variables) => {
      if (variables.persist && data.artifact_id) {
        void queryClient.invalidateQueries({ queryKey: ["portal", variables.workspaceId] });
      }
    },
  });
}

export function useImportLocalRadarScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { niche: string; city: string; rows: LocalRadarImportRow[] }) =>
      api.importLocalRadarScan(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["local-radar"] });
    },
  });
}

export function useLocalRadarScans(enabled: boolean) {
  return useQuery({
    queryKey: ["local-radar", "scans"],
    queryFn: () => api.getLocalRadarScans(),
    enabled,
  });
}

export function useLocalRadarScan(scanId: string | null) {
  return useQuery({
    queryKey: ["local-radar", "scan", scanId],
    queryFn: () => api.getLocalRadarScan(scanId as string),
    enabled: Boolean(scanId),
  });
}

export function useCreateLocalRadarScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { niche: string; city: string; limit?: number }) =>
      api.createLocalRadarScan(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["local-radar"] });
    },
  });
}

export function useAuditLocalRadarProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (prospectId: string) => api.auditLocalRadarProspect(prospectId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["local-radar"] });
    },
  });
}

export function useUpdateLocalRadarMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ prospectId, message }: { prospectId: string; message: string }) =>
      api.updateLocalRadarMessage(prospectId, message),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["local-radar"] });
    },
  });
}

export function useDecideLocalRadarProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ prospectId, decision }: { prospectId: string; decision: "approved" | "rejected" }) =>
      api.decideLocalRadarProspect(prospectId, decision),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["local-radar"] });
    },
  });
}

export function useSendLocalRadarProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ prospectId, providerType }: { prospectId: string; providerType: WhatsAppProviderType }) =>
      api.sendLocalRadarProspect(prospectId, providerType),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["local-radar"] });
    },
  });
}

export function useIntegrationsStatus() {
  return useQuery({
    queryKey: ["integrations", "status"],
    queryFn: api.integrationsStatus,
  });
}

export function usePerformanceConnections(clientId: string | null) {
  return useQuery({
    queryKey: ["performance-connections", clientId],
    queryFn: () => {
      if (!clientId) throw new Error("No client ID provided");
      return api.performanceConnections(clientId);
    },
    enabled: Boolean(clientId),
  });
}

export function useCreatePerformanceConnection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, payload }: { clientId: string; payload: Parameters<typeof api.createPerformanceConnection>[1] }) =>
      api.createPerformanceConnection(clientId, payload),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["performance-connections", variables.clientId], data);
    },
  });
}

export function useUpdatePerformanceConnection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      clientId,
      connectionId,
      payload,
    }: {
      clientId: string;
      connectionId: string;
      payload: Parameters<typeof api.updatePerformanceConnection>[2];
    }) => api.updatePerformanceConnection(clientId, connectionId, payload),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["performance-connections", variables.clientId], data);
    },
  });
}

export function useSavePerformanceProviderToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      workspaceId,
      provider,
      token,
    }: {
      workspaceId: string;
      provider: Parameters<typeof api.savePerformanceProviderToken>[1];
      token: string;
    }) => api.savePerformanceProviderToken(workspaceId, provider, token),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["performance-connections", variables.workspaceId], data);
    },
  });
}

export function useRequestPerformanceSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, provider }: { clientId: string; provider?: Parameters<typeof api.requestPerformanceSync>[1] }) =>
      api.requestPerformanceSync(clientId, provider),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["portal", variables.clientId] });
      queryClient.invalidateQueries({ queryKey: ["performance-connections", variables.clientId] });
    },
  });
}

export function useInstagramPosts(workspaceId: string | null, days = 90) {
  return useQuery({
    queryKey: ["content-instagram-posts", workspaceId, days],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.listInstagramPosts(workspaceId, days);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useContentHookBank(workspaceId: string | null) {
  return useQuery({
    queryKey: ["content-hook-bank", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.listContentHookBank(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useLatestRetrospective(workspaceId: string | null) {
  return useQuery({
    queryKey: ["content-retrospective", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.getLatestRetrospective(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useGenerateRetrospective() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, periodDays }: { workspaceId: string; periodDays?: number }) =>
      api.generateRetrospective(workspaceId, periodDays),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["content-retrospective", variables.workspaceId], data);
      queryClient.invalidateQueries({ queryKey: ["content-hook-bank", variables.workspaceId] });
    },
  });
}

export function useContentScripts(workspaceId: string | null, status?: import("../../lib/api").ContentScriptStatus) {
  return useQuery({
    queryKey: ["content-scripts", workspaceId, status],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.listContentScripts(workspaceId, status);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useGenerateContentScripts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, count, competitorHandles }: { workspaceId: string; count?: number; competitorHandles?: string[] }) =>
      api.generateContentScripts(workspaceId, count, competitorHandles),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["content-scripts", variables.workspaceId] });
    },
  });
}

export function useUpdateContentScript() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      workspaceId,
      scriptId,
      payload,
    }: {
      workspaceId: string;
      scriptId: string;
      payload: Parameters<typeof api.updateContentScript>[2];
    }) => api.updateContentScript(workspaceId, scriptId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["content-scripts", variables.workspaceId] });
    },
  });
}

export function useLinkPostToScript() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, postId, scriptId }: { workspaceId: string; postId: string; scriptId: string }) =>
      api.linkPostToScript(workspaceId, postId, scriptId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["content-instagram-posts", variables.workspaceId] });
      queryClient.invalidateQueries({ queryKey: ["content-scripts", variables.workspaceId] });
    },
  });
}

export function useKommoConfig(organizationId: string | null) {
  return useQuery({
    queryKey: ["kommo-config", organizationId],
    queryFn: () => {
      if (!organizationId) throw new Error("No organization ID provided");
      return api.getKommoConfig(organizationId);
    },
    enabled: Boolean(organizationId),
  });
}

export function useSetupKommoConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ organizationId, payload }: { organizationId: string; payload: Parameters<typeof api.setupKommoConfig>[1] }) =>
      api.setupKommoConfig(organizationId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["kommo-config", variables.organizationId] });
    },
  });
}

export function useKommoAnalytics(organizationId: string | null) {
  return useQuery({
    queryKey: ["kommo-analytics", organizationId],
    queryFn: () => {
      if (!organizationId) throw new Error("No organization ID provided");
      return api.getKommoAnalytics(organizationId);
    },
    enabled: Boolean(organizationId),
  });
}

export function useAdminIdeas() {
  return useQuery({
    queryKey: ["admin", "ideas"],
    queryFn: api.adminIdeas,
    select: (data) => data.ideas ?? [],
  });
}

export function useSaveAdminIdeas() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ideas: Idea[]) => api.saveAdminIdeas(ideas),
    onMutate: async (ideas) => {
      await queryClient.cancelQueries({ queryKey: ["admin", "ideas"] });
      const previous = queryClient.getQueryData<{ ideas?: Idea[] }>(["admin", "ideas"]);
      queryClient.setQueryData(["admin", "ideas"], { ...(previous ?? {}), ideas });
      return { previous };
    },
    onError: (_error, _ideas, context) => {
      if (context?.previous) queryClient.setQueryData(["admin", "ideas"], context.previous);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["admin", "ideas"] }),
  });
}

export function useSaveAdminIdeaDoc() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) => api.saveAdminIdeaDoc(id, content),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "idea-doc", variables.id] });
    },
  });
}

export function useAdminIdeaDoc(id: string | null) {
  return useQuery({
    queryKey: ["admin", "idea-doc", id],
    queryFn: () => api.adminIdeaDoc(id ?? ""),
    enabled: Boolean(id),
    retry: false,
  });
}

export function useAdminStack() {
  return useQuery({
    queryKey: ["admin", "stack"],
    queryFn: api.adminStack,
  });
}

export function useSaveAdminStack() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (techs: Tech[]) => api.saveAdminStack(techs),
    onMutate: async (techs) => {
      await queryClient.cancelQueries({ queryKey: ["admin", "stack"] });
      const previous = queryClient.getQueryData<{ techs?: Tech[] }>(["admin", "stack"]);
      queryClient.setQueryData(["admin", "stack"], { ...(previous ?? {}), techs });
      return { previous };
    },
    onError: (_error, _techs, context) => {
      if (context?.previous) queryClient.setQueryData(["admin", "stack"], context.previous);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["admin", "stack"] }),
  });
}

export function useMetaAdsDaily(workspaceId: string | null) {
  return useQuery({
    queryKey: ["meta-ads-daily", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.metaAdsDaily(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useLinkedInAdsDaily(workspaceId: string | null) {
  return useQuery({
    queryKey: ["linkedin-ads-daily", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.linkedInAdsDaily(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function usePerformanceAiSummary(workspaceId: string | null) {
  return useQuery({
    queryKey: ["performance-ai-summary", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.performanceAiSummary(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useWhatsAppProviders(workspaceId: string | null) {
  return useQuery({
    queryKey: ["whatsapp-providers", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.whatsAppProviders(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useSaveWhatsAppProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, payload }: { workspaceId: string; payload: Parameters<typeof api.saveWhatsAppProvider>[1] }) =>
      api.saveWhatsAppProvider(workspaceId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-providers", variables.workspaceId] });
    },
  });
}

export function useSendWhatsAppMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, payload }: { workspaceId: string; payload: Parameters<typeof api.sendWhatsAppMessage>[1] }) =>
      api.sendWhatsAppMessage(workspaceId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-logs", variables.workspaceId] });
    },
  });
}

export function useWhatsAppLogs(workspaceId: string | null) {
  return useQuery({
    queryKey: ["whatsapp-logs", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.whatsAppLogs(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}
