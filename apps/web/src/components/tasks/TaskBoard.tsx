import { useState } from "react";
import { Plus, Info } from "lucide-react";
import { useUpdateTask } from "../../hooks/useBiomaApi";
import type { TaskSummary, TaskGroupStatus, Discipline, TaskListType } from "../../lib/api";
import { statusesForFrente, groupForStatus, getMacroGroupTooltip } from "../../lib/task-frentes";
import { TaskCard } from "./TaskCard";
import { TaskDrawer } from "./TaskDrawer";
import { InlineTaskComposer } from "./InlineTaskComposer";
import type { ComposerProjectState } from "../../lib/task-composer";

type TaskBoardProps = {
  /** Projeto da nova tarefa, resolvido pela decisao 13. */
  composerProject: ComposerProjectState;
  workspaceId: string;
  tasks: TaskSummary[];
  discipline?: Discipline | string;
  taskFilter?: (task: TaskSummary) => boolean;
  listId?: string;
};

const MACRO_COLUMNS: { id: string; group: TaskGroupStatus; label: string }[] = [
  { id: "NOT_STARTED", group: "NOT_STARTED", label: "A fazer" },
  { id: "ACTIVE", group: "ACTIVE", label: "Em progresso" },
  { id: "DONE", group: "DONE", label: "Concluído" },
  { id: "CLOSED", group: "CLOSED", label: "Finalizado" },
];

export function TaskBoard({ workspaceId, tasks: allTasks, discipline, composerProject, taskFilter, listId }: TaskBoardProps) {
  const tasks = taskFilter ? allTasks.filter(taskFilter) : allTasks;
  const updateTask = useUpdateTask();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  // Qual coluna está com o composer aberto. Antes o "+" abria o TaskDrawer
  // inteiro para registrar um título — o mesmo atrito da lista.
  const [composerColumn, setComposerColumn] = useState<string | null>(null);
  const [draggingTaskId, setDraggingTaskId] = useState<string | null>(null);
  const [dropTargetColumn, setDropTargetColumn] = useState<string | null>(null);

  // Deriva colunas detalhadas quando há disciplina selecionada
  const frenteType = (discipline || undefined) as TaskListType | undefined;
  const detailedStatuses = frenteType ? statusesForFrente(frenteType) : null;

  const boardColumns = detailedStatuses
    ? detailedStatuses.map((s) => ({
        id: s.status,
        group: s.group,
        label: s.status,
      }))
    : MACRO_COLUMNS;

  /** Regra única de "esta tarefa pertence a esta coluna".
   *
   *  Extraída do render porque a navegação entre tarefas no drawer precisa da
   *  MESMA ordem que o board mostra. Duplicar a condição faria as setas
   *  pularem para uma tarefa que não está onde a pessoa acha que está — e as
   *  duas cópias divergiriam na primeira mudança de regra. */
  const belongsToColumn = (task: TaskSummary, col: { id: string; group: TaskGroupStatus }) => {
    if (!detailedStatuses) return task.group_status === col.group;
    const taskStatus = (task.status || "").trim().toLowerCase();
    if (taskStatus === col.id.toLowerCase()) return true;
    // Sem status detalhado, cai na primeira coluna do seu grupo — senão
    // sumiria do board por não casar com nenhuma.
    const firstOfGroup = detailedStatuses.find((item) => item.group === task.group_status);
    return !task.status && task.group_status === col.group && firstOfGroup?.status === col.id;
  };

  const handleStatusChange = (taskId: string, targetColId: string) => {
    // Se a coluna for uma das macro (NOT_STARTED, ACTIVE, etc.)
    if (MACRO_COLUMNS.some((m) => m.id === targetColId)) {
      updateTask.mutate({ taskId, payload: { group_status: targetColId as TaskGroupStatus } });
      return;
    }
    // Caso seja status detalhado de uma disciplina
    const group = groupForStatus(frenteType, targetColId) ?? "ACTIVE";
    updateTask.mutate({
      taskId,
      payload: { status: targetColId, group_status: group },
    });
  };

  return (
    <div className="task-board" style={{ display: "flex", gap: 16, overflowX: "auto", padding: "16px 0", height: "100%", alignItems: "flex-start" }}>
      {boardColumns.map((col) => {
        const colTasks = tasks.filter((task) => belongsToColumn(task, col));

        return (
          <div
            key={col.id}
            className={`task-column${dropTargetColumn === col.id ? " drop-target" : ""}`}
            // `preventDefault` no dragOver é o que autoriza o drop: sem ele o
            // navegador rejeita a soltura e o card "volta" sem explicação.
            onDragOver={(event) => {
              if (!draggingTaskId) return;
              event.preventDefault();
              event.dataTransfer.dropEffect = "move";
              if (dropTargetColumn !== col.id) setDropTargetColumn(col.id);
            }}
            onDragLeave={(event) => {
              // Só limpa quando o ponteiro sai da coluna de verdade — sair para
              // um filho dispara dragLeave e faria o realce piscar.
              if (!event.currentTarget.contains(event.relatedTarget as Node)) {
                setDropTargetColumn((current) => (current === col.id ? null : current));
              }
            }}
            onDrop={(event) => {
              event.preventDefault();
              const taskId = event.dataTransfer.getData("text/plain") || draggingTaskId;
              setDropTargetColumn(null);
              setDraggingTaskId(null);
              if (!taskId) return;
              const task = tasks.find((item) => item.id === taskId);
              // Soltar na mesma coluna não é mudança: evita uma escrita à toa
              // no banco e um repaint desnecessário.
              if (!task || belongsToColumn(task, col)) return;
              handleStatusChange(taskId, col.id);
            }}
            style={{ width: 280, flexShrink: 0, display: "flex", flexDirection: "column", gap: 12, background: "var(--surface-soft)", padding: 12, borderRadius: 8 }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: 13, margin: 0, fontWeight: 600, color: "var(--text)", display: "flex", alignItems: "center", gap: 6 }}>
                {col.label} <span style={{ color: "var(--text-faint)", fontWeight: 400 }}>{colTasks.length}</span>
                {!detailedStatuses && (
                  <span title={getMacroGroupTooltip(col.group)} style={{ display: "flex", alignItems: "center" }}>
                    <Info size={14} style={{ color: "var(--text-faint)", cursor: "help" }} />
                  </span>
                )}
              </h3>
              <button
                className="icon-button"
                type="button"
                aria-label={`Adicionar tarefa em ${col.label}`}
                onClick={() => setComposerColumn(col.id)}
              >
                <Plus size={16} />
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8, minHeight: 100 }}>
              {colTasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onClick={() => setSelectedTaskId(task.id)}
                  onStatusChange={(newStatus) => handleStatusChange(task.id, newStatus)}
                  columns={boardColumns}
                  isDragging={draggingTaskId === task.id}
                  onDragStart={() => setDraggingTaskId(task.id)}
                  onDragEnd={() => {
                    setDraggingTaskId(null);
                    setDropTargetColumn(null);
                  }}
                />
              ))}

              {composerColumn === col.id && (
                <InlineTaskComposer
                  project={composerProject}
                  workspaceId={workspaceId}
                  // Ver TaskListView: sem status detalhado, gravar o rótulo da
                  // coluna inventaria um status que nenhuma frente reconhece.
                  status={detailedStatuses ? col.id : "pending"}
                  groupStatus={col.group}
                  discipline={discipline as Discipline | undefined}
                  placeholder="Título da tarefa…"
                  autoFocus
                  onCancel={() => setComposerColumn(null)}
                />
              )}
            </div>
          </div>
        );
      })}

      {selectedTaskId && (
        <TaskDrawer
          workspaceId={workspaceId}
          discipline={discipline as Discipline | undefined}
          listId={listId}
          taskId={selectedTaskId}
          // Coluna a coluna, na ordem em que aparecem no board.
          siblingIds={boardColumns.flatMap((col) =>
            tasks.filter((task) => belongsToColumn(task, col)).map((task) => task.id),
          )}
          onNavigate={setSelectedTaskId}
          onClose={() => setSelectedTaskId(null)}
        />
      )}
    </div>
  );
}
