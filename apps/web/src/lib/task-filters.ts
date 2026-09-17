/**
 * Filtros rápidos por frente — o que o manual v1 chamava de "views" salvas
 * (Bug Tracker, Banco de Ideias, Aprovação) na verdade eram a mesma lista com
 * um filtro fixo. Aqui viram filtros aplicáveis a QUALQUER visão (quadro,
 * lista, calendário, gantt), em vez de telas separadas.
 */

import type { TaskListType, TaskSummary } from "./api";

export type TaskQuickFilter = {
  id: string;
  label: string;
  /** Frentes onde o filtro faz sentido; vazio = todas. */
  frentes: TaskListType[];
  predicate: (task: TaskSummary) => boolean;
};

function customField(task: TaskSummary, name: string): string {
  return (
    task.custom_fields?.find((field) => field.field_name.toLowerCase() === name.toLowerCase())
      ?.field_value ?? ""
  );
}

export const TASK_QUICK_FILTERS: TaskQuickFilter[] = [
  {
    id: "bugs",
    label: "🐛 Bug Tracker",
    frentes: ["tech"],
    // v1: "Filtro: Campo Tipo (Type) é 🐛 Bug".
    predicate: (task) => customField(task, "Tipo").toLowerCase().includes("bug"),
  },
  {
    id: "ideias",
    label: "🧠 Banco de Ideias",
    frentes: [],
    // v1 (social): status Ideação; growth/tech: Brain/Ideias.
    predicate: (task) => ["IDEAÇÃO", "BRAIN", "IDEIAS"].includes((task.status || "").toUpperCase()),
  },
  {
    id: "aprovacao",
    label: "🟣 Aprovação do Cliente",
    frentes: ["social", "growth"],
    // v1: o widget do portal mostra "Aprovação Cliente", "Em Ajuste", "Em revisão".
    predicate: (task) => ["APROVAÇÃO CLIENTE", "EM AJUSTE", "IN REVIEW", "EM REVISÃO"].includes((task.status || "").toUpperCase()),
  },
  {
    id: "atrasadas",
    label: "⏰ Atrasadas",
    frentes: [],
    predicate: (task) =>
      Boolean(task.due_date) &&
      new Date(task.due_date as string).getTime() < Date.now() &&
      task.group_status !== "DONE" &&
      task.group_status !== "CLOSED",
  },
];

export function quickFiltersForFrente(type: TaskListType | undefined): TaskQuickFilter[] {
  return TASK_QUICK_FILTERS.filter(
    (filter) => filter.frentes.length === 0 || (type ? filter.frentes.includes(type) : false),
  );
}

/** Compõe filtro rápido + filtro de projeto num único predicado para as visões. */
export function buildTaskPredicate(
  quickFilterId: string | null,
  projectId: string | null,
): ((task: TaskSummary) => boolean) | undefined {
  const quick = quickFilterId
    ? TASK_QUICK_FILTERS.find((filter) => filter.id === quickFilterId)
    : undefined;
  if (!quick && !projectId) return undefined;
  return (task) => {
    if (quick && !quick.predicate(task)) return false;
    if (projectId && task.project_id !== projectId) return false;
    return true;
  };
}
