import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";

export function useApiHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    retry: false,
    refetchInterval: 60000,
  });
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ["user"],
    queryFn: api.me,
    retry: false,
    initialData: () => {
      try {
        const raw = localStorage.getItem("bioma_user_cache");
        return raw ? JSON.parse(raw) : undefined;
      } catch {
        return undefined;
      }
    },
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password, remember_me }: { email: string; password: string; remember_me?: boolean }) =>
      api.login(email, password, remember_me),
    onSuccess: (data) => {
      queryClient.setQueryData(["user"], data.user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => {
      try { localStorage.removeItem("bioma_user_cache"); } catch {}
      queryClient.clear();
    },
  });
}

export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: api.sessions,
  });
}

export function useRevokeSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => api.revokeSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}

export function useRevokeOtherSessions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.revokeOtherSessions(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}

export function usePersonalAccessTokens() {
  return useQuery({
    queryKey: ["personal-access-tokens"],
    queryFn: api.personalAccessTokens,
  });
}

export function useCreatePersonalAccessToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, expiresInDays }: { name: string; expiresInDays?: number | null }) =>
      api.createPersonalAccessToken(name, expiresInDays),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["personal-access-tokens"] });
    },
  });
}

export function useRevokePersonalAccessToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tokenId: string) => api.revokePersonalAccessToken(tokenId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["personal-access-tokens"] });
    },
  });
}
