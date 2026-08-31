import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { AgentSkillStatus, FeatureState, ImprovementRequestStatus } from "../../lib/api";
import { api } from "../../lib/api";

export function useImprovementRequests(statusFilter?: ImprovementRequestStatus, workspaceId?: string | null) {
  return useQuery({
    queryKey: ["improvement-requests", statusFilter, workspaceId],
    queryFn: () => api.listImprovementRequests(statusFilter, workspaceId),
  });
}

export function useConvertImprovementRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ requestId, listId, reviewNote }: { requestId: string; listId: string; reviewNote?: string }) =>
      api.convertImprovementRequest(requestId, { list_id: listId, review_note: reviewNote ?? null }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["improvement-requests"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useRejectImprovementRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ requestId, reviewNote }: { requestId: string; reviewNote?: string }) =>
      api.rejectImprovementRequest(requestId, reviewNote),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["improvement-requests"] }),
  });
}

export function useFeatureFlags(organizationId: string | null) {
  return useQuery({
    queryKey: ["feature-flags", organizationId],
    queryFn: () => api.listFeatureFlags(organizationId as string),
    enabled: Boolean(organizationId),
  });
}

export function useUpsertFeatureFlag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ organizationId, featureKey, state, note }: { organizationId: string; featureKey: string; state: FeatureState; note?: string }) =>
      api.upsertFeatureFlag(organizationId, { feature_key: featureKey, state, note: note ?? null }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["feature-flags"] }),
  });
}

export function useClearFeatureFlag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ organizationId, featureKey }: { organizationId: string; featureKey: string }) =>
      api.clearFeatureFlag(organizationId, featureKey),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["feature-flags"] }),
  });
}

export function useCopilotPlans(workspaceId: string | null) {
  return useQuery({
    queryKey: ["copilot-plans", workspaceId],
    queryFn: () => api.listCopilotPlans(workspaceId),
  });
}

export function useCreateCopilotPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { goal: string; workspace_id?: string | null }) => api.createCopilotPlan(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["copilot-plans"] }),
  });
}

export function useApproveCopilotPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (planId: string) => api.approveCopilotPlan(planId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["copilot-plans"] });
      void queryClient.invalidateQueries({ queryKey: ["agent-memories"] });
      void queryClient.invalidateQueries({ queryKey: ["agent-skills"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

export function useRejectCopilotPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (planId: string) => api.rejectCopilotPlan(planId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["copilot-plans"] }),
  });
}

export function useConfirmCopilotPlanStep() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, stepId }: { planId: string; stepId: string }) =>
      api.confirmCopilotPlanStep(planId, stepId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["copilot-plans"] });
      void queryClient.invalidateQueries({ queryKey: ["agent-memories"] });
    },
  });
}

export function useAgentMemories(workspaceId: string | null, includeGlobal = true) {
  return useQuery({
    queryKey: ["agent-memories", workspaceId, includeGlobal],
    queryFn: () => api.listAgentMemories(workspaceId, includeGlobal),
  });
}

export function useCreateAgentMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof api.createAgentMemory>[0]) => api.createAgentMemory(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["agent-memories"] }),
  });
}

export function useUpdateAgentMemory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ memoryId, body, reason }: { memoryId: string; body: string; reason: string }) =>
      api.updateAgentMemory(memoryId, { body, reason }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["agent-memories"] }),
  });
}

export function useSetAgentMemoryStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ memoryId, status, reason }: { memoryId: string; status: "active" | "archived"; reason: string }) =>
      api.setAgentMemoryStatus(memoryId, { status, reason }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["agent-memories"] }),
  });
}

export function useSetAgentMemoryOwner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ memoryId, isPersonal, reason }: { memoryId: string; isPersonal: boolean; reason: string }) =>
      api.setAgentMemoryOwner(memoryId, { is_personal: isPersonal, reason }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["agent-memories"] }),
  });
}

export function useAgentMemoryRevisions(memoryId: string | null) {
  return useQuery({
    queryKey: ["agent-memory-revisions", memoryId],
    queryFn: () => api.listAgentMemoryRevisions(memoryId as string),
    enabled: Boolean(memoryId),
  });
}

export function useAgentSkills(workspaceId: string | null, includeGlobal = true, statusFilter?: AgentSkillStatus) {
  return useQuery({
    queryKey: ["agent-skills", workspaceId, includeGlobal, statusFilter],
    queryFn: () => api.listAgentSkills(workspaceId, includeGlobal, statusFilter),
  });
}

export function useReviewAgentSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ skillId, status, reviewNote }: { skillId: string; status: "approved" | "rejected"; reviewNote?: string }) =>
      api.reviewAgentSkill(skillId, { status, review_note: reviewNote ?? null }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["agent-skills"] }),
  });
}

export function useRetireAgentSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (skillId: string) => api.retireAgentSkill(skillId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["agent-skills"] }),
  });
}
