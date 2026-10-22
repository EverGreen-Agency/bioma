import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, OfferEvaluatePayload, OfferValidationResponse } from "../../lib/api";

export function useOfferValidations(workspaceId: string | null | undefined) {
  return useQuery({
    queryKey: ["offer-validations", workspaceId],
    queryFn: () => {
      if (!workspaceId) return [];
      return api.listOfferValidations(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useCreateOfferValidation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, payload }: { workspaceId: string; payload: OfferEvaluatePayload }) =>
      api.createOfferValidation(workspaceId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["offer-validations", variables.workspaceId] });
    },
  });
}

export function useDeleteOfferValidation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, validationId }: { workspaceId: string; validationId: string }) =>
      api.deleteOfferValidation(workspaceId, validationId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["offer-validations", variables.workspaceId] });
    },
  });
}

export function useEvaluateOfferPreview() {
  return useMutation({
    mutationFn: (payload: OfferEvaluatePayload) => api.evaluateOffer(payload),
  });
}
