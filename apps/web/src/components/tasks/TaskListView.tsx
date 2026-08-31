import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, CheckSquare, Circle } from "lucide-react";

import { useUpdateTask } from "../../hooks/useBiomaApi";
import { EmptyState } from "../shared";
import { TaskDrawer } from "./TaskDrawer";
import { InlineTaskComposer } from "./InlineTaskComposer";
import type { ComposerProjectState } from "../../lib/task-composer";
import { formatDueDate } from "../../lib/format";
import { statusesForFrente } from "../../lib/task-frentes";
import type { Discipline, TaskGroupStatus, TaskListType, TaskSummary } from "../../lib/api";

type TaskListViewProps = {
  /** Projeto da nova tarefa, resolvido pela decisao 13. */
  composerProject: ComposerProjectState;
  workspaceId: string;
  tasks: TaskSummary[];
  discipline?: Discipline | string;
  listId?: string;       // legado
  listType?: TaskListType; // legado
  taskFilter?: (task: TaskSummary) => boolean;
};

/** Colunas macro, quando não há disciplina selecionada para dar os detalhados. */
const MACRO_SECTIONS: { status: string; group: TaskGroupStatus; label: string }[] = [
  { status: "NOT_STARTED", group: "NOT_STARTED", label: "A fazer" },
  { status: "ACTIVE", group: "ACTIVE", label: "Em progresso" },
  { status: "DONE", group: "DONE", label: "Concluído" },
  { status: "CLOSED", group: "CLOSED", label: "Finalizado" },
];

export function TaskListView({ workspaceId, tasks: allTasks, discipline, composerProject, listId, listType, taskFilter }: TaskListViewProps) {
  const tasks = taskFilter ? allTasks.filter(taskFilter) : allTasks;
  const updateTask = useUpdateTask();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const frenteType = (discipline || undefined) as TaskListType | undefined;
  const detailed = frenteType ? statusesForFrente(frenteType) : null;

  /**
   * Agrupar por status em vez de uma tabela plana ordenada por "feito".
   *
   * A lista plana obrigava a ler a coluna Status linha a linha para saber o que
   * estava parado — a informação que mais importa num gestor de tarefas era
   * justamente a que exigia mais esforço para extrair. Seção com contagem
   * responde isso de relance, e é o mesmo recorte do kanban: as duas visões
   * passam a contar a mesma história.
   */
  const sections = useMemo(() => {
    const base = detailed
      ? detailed.map((item) => ({ status: item.status, group: item.group, label: item.status }))
      : MACRO_SECTIONS;

    const used = new Set<string>();
    const built = base.map((section) => {
      const rows = tasks.filter((task) => {
        if (detailed) {
          const taskStatus = (task.status || "").trim().toLowerCase();
          if (taskStatus === section.status.toLowerCase()) return true;
          // Tarefa sem status detalhado cai na primeira seção do seu grupo,
          // senão sumiria da lista por não casar com nenhuma coluna.
          const firstOfGroup = detailed.find((item) => item.group === task.group_status);
          return !task.status && firstOfGroup?.status === section.status;
        }
        return task.group_status === section.group;
      });
      rows.forEach((row) => used.add(row.id));
      return { ...section, rows };
    });

    // Rede de segurança: status escrito à mão (ou vindo de importação) que não
    // casa com nenhuma seção continua visível, em vez de desaparecer da tela.
    const orphans = tasks.filter((task) => !used.has(task.id));
    if (orphans.length > 0) {
      built.push({ status: "__outros__", group: "ACTIVE" as TaskGroupStatus, label: "Outros status", rows: orphans });
    }
    return built;
  }, [tasks, detailed]);

  const canCreate = Boolean(workspaceId);

  return (
    <>
      <div className="task-sections">
        {sections.map((section) => {
          const isCollapsed = collapsed[section.status] ?? false;
          const isOrphanSection = section.status === "__outros__";
          return (
            <section key={section.status} className="task-section">
              <button
                type="button"
                className="task-section-header"
                onClick={() => setCollapsed((current) => ({ ...current, [section.status]: !isCollapsed }))}
                aria-expanded={!isCollapsed}
              >
                {isCollapsed ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
                <span className="task-section-label">{section.label}</span>
                <span className="task-section-count">{section.rows.length}</span>
              </button>

              {!isCollapsed && (
                <div className="task-section-body">
                  {section.rows.length > 0 && (
                    <table className="task-table">
                      <thead>
                        <tr>
                          <th style={{ width: 40 }}></th>
                          <th>Nome</th>
                          <th style={{ width: 120 }}>Prioridade</th>
                          <th style={{ width: 150 }}>Área / Missão</th>
                          <th style={{ width: 110 }}>Esforço</th>
                          <th style={{ width: 120 }}>Vencimento</th>
                        </tr>
                      </thead>
                      <tbody>
                        {section.rows.map((task) => {
                          const isDone = task.group_status === "DONE" || task.group_status === "CLOSED";
                          const area = task.custom_fields?.find((f) => f.field_name === "Área do Projeto")?.field_value
                            || task.custom_fields?.find((f) => f.field_name === "Missão")?.field_value
                            || "-";
                          const effort = task.custom_fields?.find((f) => f.field_name === "Esforço")?.field_value || "-";
                          const isLegacy = task.external_source === "clickup";

                          return (
                            <tr
                              key={task.id}
                              className={isDone ? "task-row done" : "task-row"}
                              onClick={() => setSelectedTaskId(task.id)}
                            >
                              <td onClick={(event) => event.stopPropagation()} style={{ textAlign: "center" }}>
                                <button
                                  className="icon-button"
                                  style={{ padding: 4 }}
                                  disabled={isLegacy}
                                  title={isLegacy ? "Registro legado importado; duplique como tarefa nativa para editar." : undefined}
                                  onClick={() => updateTask.mutate({
                                    taskId: task.id,
                                    payload: { group_status: isDone ? "ACTIVE" : "DONE" },
                                  })}
                                >
                                  {isDone
                                    ? <CheckSquare size={16} color="var(--mint)" />
                                    : <Circle size={16} color="var(--text-dim)" />}
                                </button>
                              </td>
                              <td className="task-cell-title">
                                {task.title}
                                {isLegacy && <small>Legado importado · somente leitura</small>}
                              </td>
                              <td>{task.priority || "-"}</td>
                              <td className="task-cell-dim">{area}</td>
                              <td className="task-cell-dim">{effort}</td>
                              <td className="task-cell-dim">
                                {task.due_date ? formatDueDate(task.due_date) : "-"}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}

                  {/* Seção de órfãos não recebe composer: não existe status real
                      para nascer nela. */}
                  {canCreate && !isOrphanSection && (
                    <InlineTaskComposer
                  project={composerProject}
                      workspaceId={workspaceId}
                      // Sem disciplina não existe status detalhado real: gravar
                      // o rótulo da seção ("A fazer") inventaria um status que
                      // nenhuma frente reconhece, e a tarefa cairia em "Outros
                      // status" ao abrir a visão por disciplina. `pending` é o
                      // mesmo default que o TaskDrawer já usa nesse caso.
                      status={detailed ? section.status : "pending"}
                      groupStatus={section.group}
                      discipline={discipline as Discipline | undefined}
                      placeholder={`Adicionar em ${section.label}…`}
                    />
                  )}
                </div>
              )}
            </section>
          );
        })}
      </div>

      {tasks.length === 0 && <EmptyState text="Nenhuma tarefa ainda. Escreva o título em uma das seções acima." />}

      {selectedTaskId && (
        <TaskDrawer
          workspaceId={workspaceId}
          listId={listId}
          discipline={discipline as Discipline | undefined}
          listType={listType}
          taskId={selectedTaskId}
          // Ordem achatada das seções, não a lista crua: navegar tem que
          // seguir o que está na tela, senão a "próxima" seria uma tarefa de
          // outra seção que nem está visível.
          siblingIds={sections.flatMap((section) => section.rows.map((row) => row.id))}
          onNavigate={setSelectedTaskId}
          onClose={() => setSelectedTaskId(null)}
        />
      )}
    </>
  );
}
