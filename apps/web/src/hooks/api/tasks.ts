import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, TaskPayload, TaskListType } from "../../lib/api";

export function useWorkspaceTasks(
  workspaceId: string | null,
  discipline?: string,
  projectId?: string,
) {
  return useQuery({
    queryKey: ["workspace-tasks", workspaceId, discipline, projectId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.workspaceTasks(workspaceId, discipline, projectId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useCreateWorkspaceTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, payload }: { workspaceId: string; payload: Parameters<typeof api.createWorkspaceTask>[1] }) =>
      api.createWorkspaceTask(workspaceId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["workspace-tasks", variables.workspaceId] });
    },
  });
}

/** @deprecated Use useWorkspaceTasks */
export function useTaskLists(workspaceId: string | null) {
  return useQuery({
    queryKey: ["task-lists", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.taskLists(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useCreateTaskList() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, name, type }: { workspaceId: string; name: string; type: TaskListType }) => 
      api.createTaskList(workspaceId, name, type),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["task-lists", variables.workspaceId] });
    },
  });
}

export function useTasksInList(listId: string | null) {
  return useQuery({
    queryKey: ["tasks", listId],
    queryFn: () => {
      if (!listId) throw new Error("No list ID provided");
      return api.tasksInList(listId);
    },
    enabled: Boolean(listId),
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ listId, payload }: { listId: string; payload: TaskPayload }) =>
      api.createTask(listId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["tasks", variables.listId] });
    },
  });
}

export function useAssignableUsers(workspaceId: string | null) {
  return useQuery({
    queryKey: ["assignable-users", workspaceId],
    queryFn: () => {
      if (!workspaceId) throw new Error("No workspace ID provided");
      return api.assignableUsers(workspaceId);
    },
    enabled: Boolean(workspaceId),
  });
}

export function useMyTasks() {
  return useQuery({
    queryKey: ["tasks", "me"],
    queryFn: api.myTasks,
  });
}

export function useTaskComments(taskId: string | null) {
  return useQuery({
    queryKey: ["task-comments", taskId],
    queryFn: () => {
      if (!taskId) throw new Error("No task ID provided");
      return api.taskComments(taskId);
    },
    enabled: Boolean(taskId),
  });
}

export function useCreateTaskComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, body, clientVisible }: { taskId: string; body: string; clientVisible?: boolean }) =>
      api.createTaskComment(taskId, body, clientVisible),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["task-comments", variables.taskId] });
    },
  });
}

export function useDeleteTaskComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ commentId }: { commentId: string; taskId: string }) => api.deleteTaskComment(commentId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["task-comments", variables.taskId] });
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: Partial<TaskPayload> }) => 
      api.updateTask(taskId, payload),
    onSuccess: (data) => {
      if (data.list_id) {
        queryClient.invalidateQueries({ queryKey: ["tasks", data.list_id] });
      }
      queryClient.invalidateQueries({ queryKey: ["workspace-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["tasks", "me"] });
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId }: { taskId: string; listId?: string; workspaceId?: string }) => 
      api.deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["workspace-tasks"] });
    },
  });
}
