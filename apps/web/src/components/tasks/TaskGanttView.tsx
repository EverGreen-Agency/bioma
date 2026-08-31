import { useMemo, useState } from "react";
import { useWorkspaceProjects } from "../../hooks/useBiomaApi";
import { EmptyState } from "../shared";
import { TaskDrawer } from "./TaskDrawer";
import type { Discipline, TaskListType, TaskSummary } from "../../lib/api";

/**
 * Visão Gantt/Timeline — uma das quatro visões de qualquer frente (não é
 * exclusiva do cliente). Manual v1: "gráfico visual baseado nas Datas
 * Iniciais e Datas de Vencimento", agrupado por projeto para mostrar as
 * frentes de trabalho de cada contrato lado a lado.
 *
 * Tarefa sem data de início vira um marco (losango) no vencimento; tarefa sem
 * data nenhuma fica listada abaixo da linha do tempo — nunca some.
 */

type TaskGanttViewProps = {
  workspaceId: string;
  tasks: TaskSummary[];
  discipline?: Discipline | string;
  listId?: string;       // legado
  listType?: TaskListType; // legado
  taskFilter?: (task: TaskSummary) => boolean;
};

const DAY_MS = 24 * 60 * 60 * 1000;

function dayFloor(value: string | Date): number {
  const date = new Date(value);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

const GROUP_COLORS: Record<TaskSummary["group_status"], string> = {
  NOT_STARTED: "var(--text-faint)",
  ACTIVE: "var(--accent)",
  DONE: "var(--mint-deep)",
  CLOSED: "var(--text-faint)",
};

export function TaskGanttView({ workspaceId, tasks: allTasks, discipline, listId, listType, taskFilter }: TaskGanttViewProps) {
  const { data: projects = [] } = useWorkspaceProjects(workspaceId ?? null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const visible = useMemo(
    () => allTasks.filter((task) => (taskFilter ? taskFilter(task) : true)),
    [allTasks, taskFilter],
  );

  const dated = visible.filter((task) => task.due_date || task.start_date);
  const undated = visible.filter((task) => !task.due_date && !task.start_date);

  // Janela: das datas reais, com folga — mínimo de 4 semanas pra régua não
  // colapsar quando só existe uma tarefa.
  const { windowStart, windowEnd, months } = useMemo(() => {
    const points = dated.flatMap((task) =>
      [task.start_date, task.due_date].filter(Boolean).map((value) => dayFloor(value as string)),
    );
    const today = dayFloor(new Date());
    const min = Math.min(...(points.length ? points : [today]), today) - 3 * DAY_MS;
    let max = Math.max(...(points.length ? points : [today]), today) + 3 * DAY_MS;
    if (max - min < 28 * DAY_MS) max = min + 28 * DAY_MS;

    const monthMarks: Array<{ label: string; leftPct: number }> = [];
    const cursor = new Date(min);
    cursor.setDate(1);
    cursor.setMonth(cursor.getMonth() + 1);
    while (cursor.getTime() < max) {
      monthMarks.push({
        label: cursor.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }),
        leftPct: ((cursor.getTime() - min) / (max - min)) * 100,
      });
      cursor.setMonth(cursor.getMonth() + 1);
    }
    return { windowStart: min, windowEnd: max, months: monthMarks };
  }, [dated]);

  if (visible.length === 0) return <EmptyState text="Nenhuma tarefa para exibir na linha do tempo." />;

  const span = windowEnd - windowStart;
  const pct = (time: number) => Math.min(100, Math.max(0, ((time - windowStart) / span) * 100));
  const todayPct = pct(dayFloor(new Date()));

  const projectName = (id: string | null | undefined) =>
    id ? projects.find((project) => project.id === id)?.name ?? "Projeto" : "Sem projeto";

  // Agrupa por projeto preservando ordem estável (projetos com nome primeiro).
  const groups = new Map<string, { label: string; tasks: TaskSummary[] }>();
  for (const task of dated) {
    const key = task.project_id ?? "__none__";
    if (!groups.has(key)) groups.set(key, { label: projectName(task.project_id), tasks: [] });
    groups.get(key)!.tasks.push(task);
  }

  return (
    <>
      <div className="surface" style={{ borderRadius: 8, border: "1px solid var(--border)", padding: 16, display: "flex", flexDirection: "column", gap: 4, overflowX: "auto" }}>
        {/* Régua de meses */}
        <div style={{ display: "flex" }}>
          <div style={{ width: 220, flexShrink: 0 }} />
          <div style={{ flex: 1, position: "relative", height: 22, borderBottom: "1px solid var(--border)", minWidth: 480 }}>
            {months.map((month) => (
              <span key={month.label + month.leftPct} style={{ position: "absolute", left: `${month.leftPct}%`, fontSize: 10, color: "var(--text-faint)", borderLeft: "1px solid var(--border)", paddingLeft: 4, height: "100%" }}>
                {month.label}
              </span>
            ))}
          </div>
        </div>

        {[...groups.values()].map((group) => (
          <div key={group.label}>
            <div style={{ display: "flex", alignItems: "center" }}>
              <strong style={{ width: 220, flexShrink: 0, fontSize: 12, color: "var(--accent)", padding: "8px 0 4px" }}>
                {group.label} <span style={{ color: "var(--text-faint)", fontWeight: 400 }}>({group.tasks.length})</span>
              </strong>
              <div style={{ flex: 1, minWidth: 480 }} />
            </div>

            {group.tasks.map((task) => {
              const start = dayFloor((task.start_date ?? task.due_date) as string);
              const end = dayFloor((task.due_date ?? task.start_date) as string);
              const isMilestone = !task.start_date || start === end;
              const left = pct(start);
              const width = Math.max(isMilestone ? 0.8 : 1.5, pct(end + DAY_MS) - left);
              const done = task.group_status === "DONE" || task.group_status === "CLOSED";

              return (
                <div key={task.id} style={{ display: "flex", alignItems: "center", minHeight: 30 }}>
                  <button
                    type="button"
                    onClick={() => setSelectedTaskId(task.id)}
                    title={task.title}
                    style={{ width: 220, flexShrink: 0, background: "none", border: "none", padding: "2px 8px 2px 0", textAlign: "left", cursor: "pointer", fontSize: 12, color: done ? "var(--text-faint)" : "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", textDecoration: done ? "line-through" : "none" }}
                  >
                    {task.title}
                  </button>
                  <div style={{ flex: 1, position: "relative", height: 22, minWidth: 480, background: "linear-gradient(to right, transparent, transparent)" }}>
                    {/* linha de hoje */}
                    <span style={{ position: "absolute", left: `${todayPct}%`, top: -2, bottom: -2, width: 1, background: "var(--danger-soft)", opacity: 0.6 }} />
                    <button
                      type="button"
                      onClick={() => setSelectedTaskId(task.id)}
                      title={`${task.title} · ${task.status}${task.due_date ? ` · vence ${new Date(task.due_date).toLocaleDateString("pt-BR")}` : ""}`}
                      style={{
                        position: "absolute",
                        left: `${left}%`,
                        width: `${width}%`,
                        top: 4,
                        height: 14,
                        borderRadius: isMilestone ? 3 : 7,
                        transform: isMilestone ? "rotate(45deg) scale(0.75)" : undefined,
                        background: GROUP_COLORS[task.group_status],
                        opacity: done ? 0.45 : 0.9,
                        border: "none",
                        cursor: "pointer",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ))}

        {undated.length > 0 && (
          <div style={{ marginTop: 12, paddingTop: 10, borderTop: "1px dashed var(--border)" }}>
            <span style={{ fontSize: 11, color: "var(--text-faint)" }}>
              Sem datas (fora da linha do tempo — defina início/vencimento para aparecerem):
            </span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
              {undated.map((task) => (
                <button key={task.id} type="button" className="mini-button" onClick={() => setSelectedTaskId(task.id)}>
                  {task.title}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {selectedTaskId && (
        <TaskDrawer
          workspaceId={workspaceId}
          listId={listId}
          discipline={discipline as Discipline | undefined}
          listType={listType}
          taskId={selectedTaskId}
          onClose={() => setSelectedTaskId(null)}
        />
      )}
    </>
  );
}
