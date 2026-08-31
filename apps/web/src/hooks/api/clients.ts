import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ClientPayload, ArtifactPayload, DeliverablePayload } from "../../lib/api";

export function useClients() {
  return useQuery({
    queryKey: ["clients"],
    queryFn: api.clients,
  });
}

export function useWorkspaces(enabled = true) {
  return useQuery({
    queryKey: ["workspaces"],
    queryFn: api.workspaces,
    enabled,
  });
}

export function useClientPortal(clientId: string | null) {
  return useQuery({
    queryKey: ["portal", clientId],
    queryFn: () => {
      if (!clientId) throw new Error("No client ID provided");
      return api.clientPortal(clientId);
    },
    enabled: Boolean(clientId),
  });
}

export function useCreateClient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClientPayload) => api.createClient(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useCreateClientRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, title, detail, category }: { clientId: string; title: string; detail?: string; category?: "request" | "question" | "change" | "input" }) =>
      api.createClientRequest(clientId, { title, detail, category }),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["portal", variables.clientId], data);
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useUpdateClientRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, requestId, status, resolutionSummary }: { clientId: string; requestId: string; status: "submitted" | "triaged" | "in_progress" | "waiting_client" | "done" | "declined"; resolutionSummary?: string }) =>
      api.updateClientRequest(clientId, requestId, { status, resolution_summary: resolutionSummary }),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["portal", variables.clientId], data);
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useUpdateClient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<ClientPayload> }) => api.updateClient(id, payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useArchiveClient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (clientId: string) => api.archiveClient(clientId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}

export function useCreateInvite() {
  return useMutation({
    mutationFn: ({ clientId, email }: { clientId: string; email?: string | null }) => api.createInvite(clientId, email),
  });
}

export function useCreateArtifact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, payload }: { clientId: string; payload: ArtifactPayload }) => api.createArtifact(clientId, payload),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.setQueryData(["portal", variables.clientId], data);
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useUpdateArtifact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, artifactId, payload }: { clientId: string; artifactId: string; payload: Partial<ArtifactPayload> }) =>
      api.updateArtifact(clientId, artifactId, payload),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["portal", variables.clientId], data);
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useDeleteArtifact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, artifactId }: { clientId: string; artifactId: string }) => api.deleteArtifact(clientId, artifactId),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["portal", variables.clientId], data);
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useCreateDeliverable() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, payload }: { clientId: string; payload: DeliverablePayload }) => api.createDeliverable(clientId, payload),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.setQueryData(["portal", variables.clientId], data);
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useUpdateDeliverable() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, deliverableId, payload }: { clientId: string; deliverableId: string; payload: Partial<DeliverablePayload> }) =>
      api.updateDeliverable(clientId, deliverableId, payload),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.setQueryData(["portal", variables.clientId], data);
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useDeleteDeliverable() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, deliverableId }: { clientId: string; deliverableId: string }) => api.deleteDeliverable(clientId, deliverableId),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.setQueryData(["portal", variables.clientId], data);
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useCreateApproval() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, deliverableId, comment }: { clientId: string; deliverableId: string; comment?: string }) =>
      api.createApproval(clientId, deliverableId, comment),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.setQueryData(["portal", variables.clientId], data);
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}

export function useDecideApproval() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ clientId, approvalId, status }: { clientId: string; approvalId: string; status: "approved" | "rejected" }) =>
      api.decideApproval(clientId, approvalId, status),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.setQueryData(["portal", variables.clientId], data);
      queryClient.setQueryData(["portal", data.client.id], data);
    },
  });
}
