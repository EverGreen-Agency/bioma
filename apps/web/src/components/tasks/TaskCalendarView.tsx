import { useState } from "react";
import { EmptyState } from "../shared";
import { TaskDrawer } from "./TaskDrawer";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import type { Discipline, TaskListType, TaskSummary } from "../../lib/api";

type TaskCalendarViewProps = {
  workspaceId: string;
  tasks: TaskSummary[];
  discipline?: Discipline | string;
  listId?: string;       // legado
  listType?: TaskListType; // legado
  taskFilter?: (task: TaskSummary) => boolean;
};

export function TaskCalendarView({ workspaceId, tasks: allTasks, discipline, listId, listType, taskFilter }: TaskCalendarViewProps) {
  const tasks = taskFilter ? allTasks.filter(taskFilter) : allTasks;
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const [currentDate, setCurrentDate] = useState(new Date());


  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const firstDayOfMonth = new Date(year, month, 1);
  const startingDayOfWeek = firstDayOfMonth.getDay(); // 0 = Sunday
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const monthNames = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
  ];

  const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));

  // Agrupar tarefas por dia
  const tasksByDay: Record<number, typeof tasks> = {};
  tasks?.forEach(task => {
    if (task.due_date) {
      const d = new Date(task.due_date);
      if (d.getFullYear() === year && d.getMonth() === month) {
        const day = d.getDate();
        if (!tasksByDay[day]) tasksByDay[day] = [];
        tasksByDay[day]?.push(task);
      }
    }
  });

  const calendarCells = [];
  // Celulas vazias antes do primeiro dia
  for (let i = 0; i < startingDayOfWeek; i++) {
    calendarCells.push(null);
  }
  // Dias do mês
  for (let day = 1; day <= daysInMonth; day++) {
    calendarCells.push(day);
  }

  return (
    <>
      <div className="surface" style={{ borderRadius: 8, padding: 16, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header de navegação do calendário */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>
            {monthNames[month]} {year}
          </h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="icon-button" type="button" onClick={prevMonth}><ChevronLeft size={18} /></button>
            <button className="secondary-button" type="button" onClick={() => setCurrentDate(new Date())} style={{ padding: "4px 12px", fontSize: 12 }}>Hoje</button>
            <button className="icon-button" type="button" onClick={nextMonth}><ChevronRight size={18} /></button>
            {/* Criar tarefa existia só no Kanban; obrigava a trocar de visão. */}
            <button className="mini-button" type="button" onClick={() => setIsCreating(true)}>
              <Plus size={13} /> Nova tarefa
            </button>
          </div>
        </div>

        {/* Grade de dias da semana */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 1, background: "var(--border)", borderRadius: 6, overflow: "hidden" }}>
          {["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"].map(day => (
            <div key={day} style={{ background: "var(--bg-inset)", padding: "8px", textAlign: "center", fontWeight: 600, fontSize: 12, color: "var(--text-dim)" }}>
              {day}
            </div>
          ))}

          {calendarCells.map((day, idx) => {
            if (day === null) {
              return <div key={`empty-${idx}`} style={{ background: "var(--surface)", minHeight: 100 }} />;
            }

            const dayTasks = tasksByDay[day] || [];
            const isToday = day === new Date().getDate() && month === new Date().getMonth() && year === new Date().getFullYear();

            return (
              <div 
                key={`day-${day}`}
                style={{ 
                  background: "var(--surface)", 
                  minHeight: 100, 
                  padding: 6,
                  display: "flex",
                  flexDirection: "column",
                  gap: 4
                }}
              >
                <div style={{ fontSize: 12, fontWeight: isToday ? 700 : 500, color: isToday ? "var(--primary)" : "var(--text-dim)", alignSelf: "flex-end" }}>
                  {day}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 4, overflowY: "auto", maxHeight: 80 }}>
                  {dayTasks.map(task => (
                    <div 
                      key={task.id} 
                      onClick={() => setSelectedTaskId(task.id)}
                      style={{ 
                        fontSize: 11, 
                        padding: "3px 6px", 
                        borderRadius: 4, 
                        background: task.group_status === "DONE" ? "var(--bg-inset)" : "var(--primary)", 
                        color: task.group_status === "DONE" ? "var(--text-dim)" : "white",
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis"
                      }}
                      title={task.title}
                    >
                      {task.title}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {(selectedTaskId || isCreating) && (
        <TaskDrawer
          workspaceId={workspaceId}
          listId={listId}
          discipline={discipline as Discipline | undefined}
          listType={listType}
          taskId={selectedTaskId}
          onClose={() => {
            setSelectedTaskId(null);
            setIsCreating(false);
          }}
        />
      )}
    </>
  );
}
