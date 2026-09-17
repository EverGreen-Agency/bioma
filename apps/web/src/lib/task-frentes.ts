/**
 * Status por frente — fonte única, derivada do Manual Operacional Bioma v2.
 *
 * Antes os status viviam hardcoded no TaskDrawer, com dois problemas: as
 * sugestões misturavam Growth e Social (a pessoa numa lista de Growth recebia
 * "ROTEIRIZAÇÃO" como opção) e o conjunto de **Tech não existia** — numa lista
 * tipo `tech` não havia como sugerir CODE REVIEW ou QA.
 *
 * `group_status` é o agrupamento das colunas do Kanban; `status` é o passo
 * específico dentro do grupo. O mapa abaixo diz, para cada frente, quais
 * status existem e a que grupo cada um pertence.
 */

import type { TaskGroupStatus, TaskListType } from "./api";

export type FrenteStatus = {
  status: string;
  group: TaskGroupStatus;
};

const GROWTH: FrenteStatus[] = [
  { status: "Brain", group: "NOT_STARTED" },
  { status: "Backlog", group: "ACTIVE" },
  { status: "Em progresso", group: "ACTIVE" },
  { status: "Em revisão", group: "ACTIVE" },
  { status: "Recusado", group: "ACTIVE" },
  { status: "Bloqueado", group: "ACTIVE" },
  { status: "Concluído", group: "DONE" },
  { status: "Finalizado", group: "CLOSED" },
];

const TECH: FrenteStatus[] = [
  { status: "Brain", group: "NOT_STARTED" },
  { status: "Backlog", group: "NOT_STARTED" },
  { status: "To Do (Sprint)", group: "NOT_STARTED" },
  { status: "Em progresso", group: "ACTIVE" },
  { status: "Code review", group: "ACTIVE" },
  { status: "QA / testes", group: "ACTIVE" },
  { status: "Bloqueado", group: "ACTIVE" },
  { status: "Pronto p/ release", group: "DONE" },
  { status: "Cancelado", group: "DONE" },
  { status: "Implantado", group: "CLOSED" },
];

const SOCIAL: FrenteStatus[] = [
  { status: "Ideação", group: "NOT_STARTED" },
  { status: "Roteirização", group: "ACTIVE" },
  { status: "Em produção", group: "ACTIVE" },
  { status: "Revisão interna", group: "ACTIVE" },
  { status: "Aprovação cliente", group: "ACTIVE" },
  { status: "Em ajuste", group: "ACTIVE" },
  { status: "Agendado", group: "DONE" },
  { status: "Publicado", group: "DONE" },
  { status: "Analisar", group: "DONE" },
  { status: "Descartado", group: "DONE" },
  { status: "Finalizado", group: "CLOSED" },
];

/** `general` usa o vocabulário de Growth: é o mais neutro dos três. */
const STATUSES_BY_FRENTE: Record<TaskListType, FrenteStatus[]> = {
  growth: GROWTH,
  tech: TECH,
  social: SOCIAL,
  general: GROWTH,
};

export function statusesForFrente(type: TaskListType | undefined): FrenteStatus[] {
  return STATUSES_BY_FRENTE[type ?? "general"] ?? GROWTH;
}

/** Grupo correto para um status, para o Kanban não depender de digitação. */
export function groupForStatus(type: TaskListType | undefined, status: string): TaskGroupStatus | null {
  const norm = status.trim().toLowerCase();
  const match = statusesForFrente(type).find((item) => item.status.toLowerCase() === norm);
  if (match) return match.group;
  // Deep search across all frentes in case of cross-frente status names
  for (const list of [GROWTH, TECH, SOCIAL]) {
    const m = list.find((item) => item.status.toLowerCase() === norm);
    if (m) return m.group;
  }
  return null;
}

export const FRENTE_LABELS: Record<TaskListType, string> = {
  growth: "Growth & Projetos",
  tech: "Tech & Software",
  social: "Social Media",
  general: "Geral",
};

/** Gera o texto de tooltip (de-para) explicando quais status detalhados entram em cada macro grupo */
export function getMacroGroupTooltip(group: TaskGroupStatus): string {
  const formatList = (list: FrenteStatus[]) => list.filter(s => s.group === group).map(s => s.status).join(", ");
  return [
    `De-Para de Status (${group}):`,
    `Growth: ${formatList(GROWTH)}`,
    `Tech: ${formatList(TECH)}`
  ].join("\n");
}
