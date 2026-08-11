import { useState } from "react";
import { useWorkspaceTasks, useCreateWorkspaceTask, useWorkspaceProjects } from "../hooks/useBiomaApi";
import { TaskBoard } from "../components/tasks/TaskBoard";
import { TaskListView } from "../components/tasks/TaskListView";
import { TaskCalendarView } from "../components/tasks/TaskCalendarView";
import { TaskGanttView } from "../components/tasks/TaskGanttView";
import { EmptyState, SectionHeader } from "../components/shared";
import { buildTaskPredicate, quickFiltersForFrente } from "../lib/task-filters";
import { LayoutDashboard, Kanban, List, Calendar, ChartGantt } from "lucide-react";

type TasksViewProps = {
  workspaceId: string;
};

// Disciplinas disponíveis (Manual v2). Social vive no Estúdio IA.
const DISCIPLINES = [
  { value: "", label: "Todas as disciplinas" },
  { value: "growth", label: "Growth & Projetos" },
  { value: "tech", label: "Tech & Software" },
] as const;

export function TasksView({ workspaceId }: TasksViewProps) {
  const [discipline, setDiscipline] = useState<string>("");
  const [projectFilter, setProjectFilter] = useState<string>("");
  const [quickFilterId, setQuickFilterId] = useState<string | null>(null);
  // Gantt e uma visao como as outras, disponivel para qualquer disciplina --
  // nao e exclusiva do roadmap do cliente.
  const [viewMode, setViewMode] = useState<"board" | "list" | "calendar" | "gantt">("board");

  const { data: tasks = [], isLoading } = useWorkspaceTasks(
    workspaceId,
    discipline || undefined,
    projectFilter || undefined,
  );
  const { data: projects = [] } = useWorkspaceProjects(workspaceId);

  if (isLoading) {
    return <EmptyState text="Carregando tarefas..." />;
  }

  return (
    <div className="operations-layout" style={{ display: "flex", flexDirection: "column", height: "100%", padding: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <SectionHeader eyebrow="Workspace" title="Projetos & Operação" icon={LayoutDashboard} />

        <div style={{ display: "flex", gap: 6, background: "var(--bg-inset)", padding: 4, borderRadius: 6 }}>
          <button
            type="button"
            className={viewMode === "board" ? "primary-button" : "icon-button"}
            onClick={() => setViewMode("board")}
            title="Visão Quadro (Kanban)"
            style={{ padding: "4px 8px" }}
          >
            <Kanban size={16} />
          </button>
          <button
            type="button"
            className={viewMode === "list" ? "primary-button" : "icon-button"}
            onClick={() => setViewMode("list")}
            title="Visão em Lista (Planejamento)"
            style={{ padding: "4px 8px" }}
          >
            <List size={16} />
          </button>
          <button
            type="button"
            className={viewMode === "calendar" ? "primary-button" : "icon-button"}
            onClick={() => setViewMode("calendar")}
            title="Visão de Calendário Editorial"
            style={{ padding: "4px 8px" }}
          >
            <Calendar size={16} />
          </button>
          <button
            type="button"
            className={viewMode === "gantt" ? "primary-button" : "icon-button"}
            onClick={() => setViewMode("gantt")}
            title="Visão Roadmap (Gantt/Timeline)"
            style={{ padding: "4px 8px" }}
          >
            <ChartGantt size={16} />
          </button>
        </div>
      </div>

      {/* Filtros: disciplina, projeto e filtros rápidos por status */}
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 12 }}>
        {/* Seletor de disciplina dinâmico: exibe apenas as frentes com projetos ou tarefas ativas no workspace */}
        <div style={{ display: "flex", gap: 4 }}>
          {(() => {
            const hasGrowth = projects.some((p) => (p as any).discipline === "growth" || (p as any).project_type === "growth") || tasks.some((t) => t.discipline === "growth");
            const hasTech = projects.some((p) => (p as any).discipline === "tech" || (p as any).project_type === "tech") || tasks.some((t) => t.discipline === "tech");
            
            const visibleDisciplines = DISCIPLINES.filter((d) => {
              if (!d.value) return true; // Todas as disciplinas
              if (!hasGrowth && !hasTech) return true; // Se ainda não há projetos cadastrados, exibe ambas
              if (d.value === "growth") return hasGrowth;
              if (d.value === "tech") return hasTech;
              return true;
            });

            return visibleDisciplines.map((d) => (
              <button
                key={d.value}
                type="button"
                className={discipline === d.value ? "primary-button" : "mini-button"}
                style={{ fontSize: 11, padding: "4px 10px" }}
                onClick={() => setDiscipline(d.value)}
              >
                {d.label}
              </button>
            ));
          })()}
        </div>

        {/* Decisão 13: a visão combinada se DECLARA como tradução.
            Growth e Tech têm vocabulários de status diferentes — `Backlog` é
            ACTIVE em Growth e NOT_STARTED em Tech. Agrupar por `group_status`
            funciona, mas coloca dois cards escritos igual em colunas
            diferentes, e sem este aviso não há como saber por quê. */}
        {!discipline && (
          <span
            style={{
              fontSize: 11.5,
              color: "var(--text-faint)",
              flexBasis: "100%",
              lineHeight: 1.45,
            }}
          >
            Visão combinada: cada disciplina tem os próprios status, então as
            colunas aqui vêm do agrupamento (a fazer / em progresso / concluído),
            não do nome do status. Para trabalhar, escolha a disciplina.
          </span>
        )}


        {projects.length > 0 && (
          <select
            className="status-select"
            style={{ fontSize: 12, maxWidth: 220 }}
            value={projectFilter}
            onChange={(event) => setProjectFilter(event.target.value)}
          >
            <option value="">Todos os projetos</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
        )}
      </div>

      <div style={{ flex: 1, minHeight: 0, marginTop: 16 }}>
        {(() => {
          const taskFilter = buildTaskPredicate(quickFilterId, projectFilter || null);
          const shared = {
            workspaceId,
            tasks,
            taskFilter,
            discipline: discipline || undefined,
          } as const;
          if (viewMode === "board") return <TaskBoard {...shared} />;
          if (viewMode === "list") return <TaskListView {...shared} />;
          if (viewMode === "calendar") return <TaskCalendarView {...shared} />;
          return <TaskGanttView {...shared} />;
        })()}
      </div>
    </div>
  );
}
