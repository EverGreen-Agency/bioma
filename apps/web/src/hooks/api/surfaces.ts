import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type SurfaceAccessEntry, type SurfaceGrantEffect } from "../../lib/api";

/** Decisão 11 — o que esta pessoa enxerga, e por quê.
 *
 * `enabled` sai de "existe usuário": antes do login a rota responde 401 e a
 * tentativa só polui o console. */
export function useMySurfaces(enabled = true) {
  return useQuery({
    queryKey: ["my-surfaces"],
    queryFn: api.mySurfaces,
    enabled,
    // A resolução muda quando um admin mexe em grant — raro, mas quando muda
    // uma tela some ou aparece. Revalidar ao focar a janela é o meio-termo
    // entre menu velho e requisição a cada clique.
    refetchOnWindowFocus: true,
    staleTime: 60_000,
  });
}

export function useSetSurfacePreference() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ surfaceKey, hidden }: { surfaceKey: string; hidden: boolean }) =>
      api.setSurfacePreference(surfaceKey, hidden),
    onSuccess: (entries: SurfaceAccessEntry[]) => {
      // A rota já devolve a resolução inteira: escrever no cache evita um
      // segundo round-trip e o piscar do menu entre esconder e recarregar.
      queryClient.setQueryData(["my-surfaces"], entries);
    },
  });
}

/** Consulta de visibilidade para telas que só querem saber "mostro ou não".
 *
 * A regra de fallback mora aqui e só aqui: enquanto a resolução não chegou —
 * ou se a chamada falhou — vale o que valia antes (mostrar). Repetir esse
 * `?? true` em cada componente é como um deles acaba com `?? false` e um
 * soluço de rede vira "sumiu o menu".
 *
 * Segurança não depende disto: quem barra cliente é o backend. */
export function useSurfaceVisibility() {
  const { data, isLoading, isError } = useMySurfaces();
  const byKey = new Map((data ?? []).map((entry) => [entry.surface_key, entry]));
  const ready = Boolean(data);
  return {
    ready,
    isLoading,
    isError,
    entry: (key: string) => byKey.get(key) ?? null,
    isSurfaceVisible: (key: string) => !ready || (byKey.get(key)?.visible ?? true),
    isSurfaceAllowed: (key: string) => !ready || (byKey.get(key)?.allowed ?? true),
  };
}

export function useSurfaceCatalog(enabled = true) {
  return useQuery({ queryKey: ["surface-catalog"], queryFn: api.surfaceCatalog, enabled, staleTime: 300_000 });
}

export function useTeamSurfaceGrants(teamId: string | null) {
  return useQuery({
    queryKey: ["team-surface-grants", teamId],
    queryFn: () => api.teamSurfaceGrants(teamId as string),
    enabled: Boolean(teamId),
  });
}

export function useUpsertTeamSurfaceGrant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ teamId, surfaceKey, effect, note }: { teamId: string; surfaceKey: string; effect: SurfaceGrantEffect; note?: string | null }) =>
      api.upsertTeamSurfaceGrant(teamId, { surface_key: surfaceKey, effect, note }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["team-surface-grants", variables.teamId] });
      // Mexer em equipe pode mudar o próprio menu de quem mexeu.
      queryClient.invalidateQueries({ queryKey: ["my-surfaces"] });
    },
  });
}

export function useClearTeamSurfaceGrant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ teamId, surfaceKey }: { teamId: string; surfaceKey: string }) =>
      api.clearTeamSurfaceGrant(teamId, surfaceKey),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["team-surface-grants", variables.teamId] });
      queryClient.invalidateQueries({ queryKey: ["my-surfaces"] });
    },
  });
}

export function useUserSurfaceGrants(userId: string | null) {
  return useQuery({
    queryKey: ["user-surface-grants", userId],
    queryFn: () => api.userSurfaceGrants(userId as string),
    enabled: Boolean(userId),
  });
}

export function useUpsertUserSurfaceGrant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, surfaceKey, effect, note }: { userId: string; surfaceKey: string; effect: SurfaceGrantEffect; note?: string | null }) =>
      api.upsertUserSurfaceGrant(userId, { surface_key: surfaceKey, effect, note }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["user-surface-grants", variables.userId] });
      queryClient.invalidateQueries({ queryKey: ["my-surfaces"] });
    },
  });
}

export function useClearUserSurfaceGrant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, surfaceKey }: { userId: string; surfaceKey: string }) =>
      api.clearUserSurfaceGrant(userId, surfaceKey),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["user-surface-grants", variables.userId] });
      queryClient.invalidateQueries({ queryKey: ["my-surfaces"] });
    },
  });
}
