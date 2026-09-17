import type { TaskSummary, TaskGroupStatus } from "../../lib/api";
import { formatDueDate } from "../../lib/format";

type TaskCardProps = {
  task: TaskSummary;
  onClick: () => void;
  onStatusChange: (status: string) => void;
  columns: { id: string; label: string }[];
  onDragStart?: () => void;
  onDragEnd?: () => void;
  isDragging?: boolean;
};

export function TaskCard({ task, onClick, onStatusChange, columns, onDragStart, onDragEnd, isDragging }: TaskCardProps) {
  // Tarefa legada é somente leitura: arrastar sugeriria que dá para mudar o
  // status dela, e o backend recusaria depois do gesto já ter acontecido.
  const draggable = task.external_source !== "clickup";
  return (
    <div
      className="surface task-card"
      draggable={draggable}
      onDragStart={(event) => {
        if (!draggable) return;
        // O id vai no dataTransfer, e não só no estado do React, para o drop
        // funcionar mesmo se o componente re-renderizar durante o arrasto.
        event.dataTransfer.setData("text/plain", task.id);
        event.dataTransfer.effectAllowed = "move";
        onDragStart?.();
      }}
      onDragEnd={() => onDragEnd?.()}
      style={{
        padding: 12,
        borderRadius: 6,
        cursor: draggable ? "grab" : "pointer",
        border: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        background: "var(--surface-soft)",
        opacity: isDragging ? 0.4 : 1,
        transition: "border-color 0.2s ease, opacity 0.15s ease"
      }}
      onClick={onClick}
    >
      <div style={{ fontWeight: 500, fontSize: 14 }}>{task.title}</div>
      {task.description && (
        <div style={{ fontSize: 12, color: "var(--text-dim)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {task.description}
        </div>
      )}
      
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
        {task.external_source === "clickup" && (
          <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "var(--bg-inset)", border: "1px solid var(--border)", color: "var(--text-dim)" }}>
            Legado importado · somente leitura
          </span>
        )}
        {task.recurrence && task.recurrence !== "none" && (
          <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "rgba(0,0,0,0.05)", border: "1px solid var(--border)", color: "var(--brand-accent)" }} title={`Recorrência: ${task.recurrence}`}>
            🔄 {task.recurrence === "weekly" ? "Semanal" : "Mensal"}
          </span>
        )}
        {task.subtasks && task.subtasks.length > 0 && (
          <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "rgba(0,0,0,0.05)", border: "1px solid var(--border)", color: "var(--text)" }}>
            ☑️ {task.subtasks.filter(s => s.is_completed).length}/{task.subtasks.length}
          </span>
        )}
        {task.custom_fields?.filter(f => ["Área do Projeto", "Esforço", "Missão", "Plataforma"].includes(f.field_name) && f.field_value).map(f => (
          <span key={f.field_name} style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "rgba(0,0,0,0.05)", border: "1px solid var(--border)", color: "var(--text)" }}>
            {f.field_name === "Esforço" ? "⏱️ " : ""}{f.field_value}
          </span>
        ))}
      </div>
      
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {task.priority && (
            <span style={{ fontSize: 11, padding: "2px 6px", borderRadius: 4, background: "var(--bg-inset)", color: "var(--text-dim)" }}>
              {task.priority}
            </span>
          )}
          {task.due_date && (
            <span style={{ fontSize: 11, color: "var(--text-dim)" }}>
              {formatDueDate(task.due_date)}
            </span>
          )}
        </div>
        
        <select 
          value={task.group_status}
          disabled={task.external_source === "clickup"}
          onChange={(e) => {
            e.stopPropagation();
            onStatusChange(e.target.value as TaskGroupStatus);
          }}
          onClick={(e) => e.stopPropagation()}
          className="status-select-card"
          style={{ 
            fontSize: 11, 
            fontWeight: 500,
            padding: "3px 8px", 
            background: "var(--surface)", 
            border: "1px solid var(--border)", 
            color: "var(--text)",
            borderRadius: 6,
            cursor: task.external_source === "clickup" ? "not-allowed" : "pointer",
            outline: "none"
          }}
        >
          {columns.map(c => (
            <option 
              key={c.id} 
              value={c.id}
              style={{
                background: "var(--moss-900)",
                color: "var(--cream)",
                padding: "6px 10px"
              }}
            >
              {c.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
