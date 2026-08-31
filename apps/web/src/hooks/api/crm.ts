import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, LeadPayload } from "../../lib/api";

export function useLeads(clientId: string | null) {
  return useQuery({
    queryKey: ["leads", clientId],
    queryFn: () => {
      if (!clientId) throw new Error("No client ID provided");
      return api.leads(clientId);
    },
    enabled: Boolean(clientId),
  });
}

export function useCreateLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, payload }: { clientId: string; payload: LeadPayload }) => api.createLead(clientId, payload),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["leads", variables.clientId], data);
    },
  });
}

export function useUpdateLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, leadId, payload }: { clientId: string; leadId: string; payload: Partial<LeadPayload> }) =>
      api.updateLead(clientId, leadId, payload),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["leads", variables.clientId], data);
    },
  });
}

export function useDeleteLead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, leadId }: { clientId: string; leadId: string }) => api.deleteLead(clientId, leadId),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["leads", variables.clientId], data);
    },
  });
}
