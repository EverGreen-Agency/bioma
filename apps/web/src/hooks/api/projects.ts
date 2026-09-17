import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";

export function useMyDeliverables() {
  return useQuery({
    queryKey: ["deliverables", "me"],
    queryFn: api.getMyDeliverables,
  });
}

export function useWorkspaceProjects(workspaceId: string | null) {
  return useQuery({
    queryKey: ["projects", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.projects(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}
