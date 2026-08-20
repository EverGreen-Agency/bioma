import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type StudioArtifactStatus } from "../../lib/api";

/** Decisão 8 — a vista do Estúdio: o que a conversa produziu, organizado. */
export function useStudioArtifacts(
  workspaceId: string | null,
  filters?: { kind?: string | null; status?: string | null },
) {
  return useQuery({
    queryKey: ["studio-artifacts", workspaceId, filters?.kind ?? null, filters?.status ?? null],
    queryFn: () => api.studioArtifacts(workspaceId as string, filters),
    enabled: Boolean(workspaceId),
  });
}

export function useStudioArtifactKinds(workspaceId: string | null) {
  return useQuery({
    queryKey: ["studio-artifact-kinds", workspaceId],
    queryFn: () => api.studioArtifactKinds(workspaceId as string),
    enabled: Boolean(workspaceId),
  });
}

/** Decisao 14 — checklist SEO/GEO do texto.
 *
 * `useQuery` e nao mutation: a rota e POST so porque o texto vai no corpo, mas
 * nao tem efeito colateral nenhum. Chaveada pelo proprio conteudo, entao trocar
 * de versao ou de peca recalcula sozinho e voltar reaproveita o cache. */
export function useContentQuality(
  workspaceId: string | null,
  input: { title?: string; content: string; keyword?: string | null },
  enabled = true,
) {
  return useQuery({
    queryKey: ["content-quality", workspaceId, input.title ?? "", input.content, input.keyword ?? null],
    queryFn: () => api.contentQuality(workspaceId as string, input),
    enabled: Boolean(workspaceId) && enabled && input.content.trim().length > 0,
    staleTime: Infinity,
  });
}

export function useStudioArtifact(artifactId: string | null) {
  return useQuery({
    queryKey: ["studio-artifact", artifactId],
    queryFn: () => api.studioArtifact(artifactId as string),
    enabled: Boolean(artifactId),
  });
}

/** Invalida a lista E o detalhe: depois de uma nova versão os dois mudam, e
 *  atualizar só um deixa a tela mostrando v2 na lista e v1 aberta ao lado. */
function useStudioMutation<TVars>(
  fn: (vars: TVars) => Promise<unknown>,
  artifactIdOf: (vars: TVars) => string | undefined,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["studio-artifacts"] });
      queryClient.invalidateQueries({ queryKey: ["studio-artifact-kinds"] });
      const id = artifactIdOf(vars);
      if (id) queryClient.invalidateQueries({ queryKey: ["studio-artifact", id] });
    },
  });
}

export function useCreateStudioArtifact() {
  return useStudioMutation(
    ({ workspaceId, ...payload }: { workspaceId: string; title: string; kind: string; content?: string | null }) =>
      api.createStudioArtifact(workspaceId, payload),
    () => undefined,
  );
}

export function useAddStudioArtifactVersion() {
  return useStudioMutation(
    ({ artifactId, ...payload }: { artifactId: string; title: string; content?: string | null; change_note?: string | null }) =>
      api.addStudioArtifactVersion(artifactId, payload),
    (vars) => vars.artifactId,
  );
}

export function useSetStudioArtifactStatus() {
  return useStudioMutation(
    ({ artifactId, status }: { artifactId: string; status: StudioArtifactStatus }) =>
      api.setStudioArtifactStatus(artifactId, status),
    (vars) => vars.artifactId,
  );
}

export function useSaveArtifactFromRun() {
  return useStudioMutation(
    ({ runId, ...payload }: { runId: string; title: string; kind?: string; content?: string | null; workspace_id?: string | null; artifact_id?: string | null; change_note?: string | null }) =>
      api.saveArtifactFromRun(runId, payload),
    (vars) => vars.artifact_id ?? undefined,
  );
}
