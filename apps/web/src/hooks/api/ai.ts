import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, CopilotSurface, AiSubscriptionPayload, AiQuotaPayload } from "../../lib/api";

export function useCopilotCommands(surface: CopilotSurface, enabled: boolean) {
  return useQuery({
    queryKey: ["copilot-commands", surface],
    queryFn: () => api.copilotCommands(surface),
    enabled,
    staleTime: 10 * 60 * 1000,
  });
}

export function useRunCopilot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof api.runCopilot>[0]) => api.runCopilot(payload),
    onSuccess: (data, variables) => {
      const changed = data.actions.some((action) => action.status === "executed");
      if (changed && variables.task_id) {
        void queryClient.invalidateQueries({ queryKey: ["tasks"] });
        void queryClient.invalidateQueries({ queryKey: ["task-comments", variables.task_id] });
      }
    },
  });
}

export function useAiFinOps(enabled = true) {
  return useQuery({
    queryKey: ["ai-finops"],
    queryFn: api.aiFinOps,
    enabled,
  });
}

export function useCreateAiSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AiSubscriptionPayload) => api.createAiSubscription(payload),
    onSuccess: (data) => queryClient.setQueryData(["ai-finops"], data),
  });
}

export function useUpdateAiSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ subscriptionId, payload }: { subscriptionId: string; payload: Partial<AiSubscriptionPayload> }) =>
      api.updateAiSubscription(subscriptionId, payload),
    onSuccess: (data) => queryClient.setQueryData(["ai-finops"], data),
  });
}

export function useRecordAiQuota() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ subscriptionId, payload }: { subscriptionId: string; payload: AiQuotaPayload }) =>
      api.recordAiQuota(subscriptionId, payload),
    onSuccess: (data) => queryClient.setQueryData(["ai-finops"], data),
  });
}

export function useAiWorkflowTemplates() {
  return useQuery({ queryKey: ["ai-workflow-templates"], queryFn: api.aiWorkflowTemplates });
}

export function useAiWorkflowDefinitions() {
  return useQuery({ queryKey: ["ai-workflow-definitions"], queryFn: api.aiWorkflowDefinitions });
}

export function useInstallAiWorkflowTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) => api.installAiWorkflowTemplate(slug),
    onSuccess: (data) => queryClient.setQueryData(["ai-workflow-definitions"], data),
  });
}

export function useAiWorkflowRuns() {
  return useQuery({ queryKey: ["ai-workflow-runs"], queryFn: api.aiWorkflowRuns, refetchInterval: 4000 });
}

export function useCreateAiWorkflowRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createAiWorkflowRun,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-workflow-runs"] }),
  });
}

export function useApproveAiWorkflowRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.approveAiWorkflowRun(runId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai-workflow-runs"] }),
  });
}

export function useAiRoutingControlPlane() {
  return useQuery({
    queryKey: ["ai-routing-control-plane"],
    queryFn: api.aiRoutingControlPlane,
    refetchInterval: 10000,
  });
}

export function useCopilotUsage(days: number, mineOnly = false) {
  return useQuery({
    queryKey: ["copilot-usage", days, mineOnly],
    queryFn: () => api.copilotUsage(days, mineOnly),
    staleTime: 60_000,
  });
}

function useControlPlaneMutation<T>(mutationFn: (payload: T) => Promise<Awaited<ReturnType<typeof api.aiRoutingControlPlane>>>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: (data) => queryClient.setQueryData(["ai-routing-control-plane"], data),
  });
}

export function useCreateAiProviderAccount() {
  return useControlPlaneMutation<Parameters<typeof api.createAiProviderAccount>[0]>(api.createAiProviderAccount);
}

export function useBootstrapAiModels() {
  return useControlPlaneMutation<string>(api.bootstrapAiModels);
}

export function useRecordAiQuotaBucket() {
  return useControlPlaneMutation<{
    accountId: string;
    payload: Parameters<typeof api.recordAiQuotaBucket>[1];
  }>(({ accountId, payload }) => api.recordAiQuotaBucket(accountId, payload));
}

export function useCollectAiQuota() {
  return useControlPlaneMutation<string>(api.collectAiQuota);
}

export function useProbeAiProviderRuntime() {
  return useMutation({ mutationFn: api.probeAiProviderRuntime });
}

export function useStartAiProviderLogin() {
  return useMutation({ mutationFn: api.startAiProviderLogin });
}

export function useDisconnectAiProvider() {
  return useControlPlaneMutation<string>(api.disconnectAiProvider);
}

export function useAiProviderLoginSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["ai-provider-login", sessionId],
    queryFn: () => api.aiProviderLoginSession(sessionId!),
    enabled: Boolean(sessionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ["completed", "failed", "canceled", "expired"].includes(status) ? false : 1000;
    },
  });
}

export function useSendAiProviderLoginInput() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, value }: { sessionId: string; value: string }) =>
      api.sendAiProviderLoginInput(sessionId, value),
    onSuccess: (data) => queryClient.setQueryData(["ai-provider-login", data.id], data),
  });
}

export function useCancelAiProviderLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.cancelAiProviderLogin,
    onSuccess: (data) => queryClient.setQueryData(["ai-provider-login", data.id], data),
  });
}

export function useBootstrapAiRoutingPolicies() {
  return useControlPlaneMutation<void>(() => api.bootstrapAiRoutingPolicies());
}

export function useUpdateAiHarness() {
  return useControlPlaneMutation<Parameters<typeof api.updateAiHarness>[0]>(api.updateAiHarness);
}

export function usePreviewAiRoute() {
  return useMutation({ mutationFn: api.previewAiRoute });
}

export function useSquads(workspaceId: string | null) {
  return useQuery({
    queryKey: ["squads", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.squads(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useRunSquad() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, payload }: { workspaceId: string; payload: Parameters<typeof api.runSquad>[1] }) =>
      api.runSquad(workspaceId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["squad-executions", variables.workspaceId] });
      queryClient.invalidateQueries({ queryKey: ["squad-finops", variables.workspaceId] });
    },
  });
}

export function useSquadExecutions(workspaceId: string | null) {
  return useQuery({
    queryKey: ["squad-executions", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.squadExecutions(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useSquadFinOps(workspaceId: string | null) {
  return useQuery({
    queryKey: ["squad-finops", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.squadFinOps(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useBrandBook(workspaceId: string | null) {
  return useQuery({
    queryKey: ["brand-book", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.brandBook(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useSaveBrandBook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, payload }: { workspaceId: string; payload: Parameters<typeof api.saveBrandBook>[1] }) =>
      api.saveBrandBook(workspaceId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["brand-book", variables.workspaceId] });
    },
  });
}

export function useCalendarItems(workspaceId: string | null, stage?: string) {
  return useQuery({
    queryKey: ["calendar-items", workspaceId, stage],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.calendarItems(workspaceId, stage);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useCreateCalendarItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, payload }: { workspaceId: string; payload: Parameters<typeof api.createCalendarItem>[1] }) =>
      api.createCalendarItem(workspaceId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["calendar-items", variables.workspaceId] });
    },
  });
}

export function useUpdateCalendarStage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, itemId, stage }: { workspaceId: string; itemId: string; stage: string }) =>
      api.updateCalendarStage(workspaceId, itemId, stage),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["calendar-items", variables.workspaceId] });
    },
  });
}
