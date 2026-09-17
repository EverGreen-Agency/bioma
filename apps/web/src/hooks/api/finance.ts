import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, FinancialRecordPayload } from "../../lib/api";

export function useFinance(clientId: string | null) {
  return useQuery({
    queryKey: ["finance", clientId],
    queryFn: () => {
      if (!clientId) throw new Error("No client ID provided");
      return api.finance(clientId);
    },
    enabled: Boolean(clientId),
  });
}

export function useCreateFinancialRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, payload }: { clientId: string; payload: FinancialRecordPayload }) =>
      api.createFinancialRecord(clientId, payload),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["finance", variables.clientId], data);
    },
  });
}

export function useUpdateFinancialRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      clientId,
      recordId,
      payload,
    }: {
      clientId: string;
      recordId: string;
      payload: Partial<FinancialRecordPayload>;
    }) => api.updateFinancialRecord(clientId, recordId, payload),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["finance", variables.clientId], data);
    },
  });
}

export function useDeleteFinancialRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, recordId }: { clientId: string; recordId: string }) => api.deleteFinancialRecord(clientId, recordId),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["finance", variables.clientId], data);
    },
  });
}

export function usePortfolioPerformance(enabled: boolean, days = 30) {
  return useQuery({
    queryKey: ["portfolio-performance", days],
    queryFn: () => api.getPortfolioPerformance(days),
    enabled,
  });
}

export function useCockpitSummary(enabled: boolean) {
  return useQuery({
    queryKey: ["cockpit-summary"],
    queryFn: api.getCockpitSummary,
    enabled,
  });
}

export function useSetMonthlyTarget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, targetLeads, budgetCents }: { clientId: string; targetLeads: number | null; budgetCents: number | null }) =>
      api.setMonthlyTarget(clientId, { target_leads: targetLeads, budget_cents: budgetCents }),
    onSuccess: (rows) => {
      queryClient.setQueryData(["portfolio-performance", 30], rows);
    },
  });
}

export function useCommercialPortal(workspaceId: string | null) {
  return useQuery({
    queryKey: ["commercial-portal", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.commercialPortal(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}
