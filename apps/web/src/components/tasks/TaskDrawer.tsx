import { useState, useEffect, useMemo } from "react";
import { X, Save, Trash2, Plus, CheckSquare, Square, Link2, Repeat, MessageSquare, Send, Eye, EyeOff, FolderKanban, GitBranch, UserRound, Sparkles, ChevronUp, ChevronDown } from "lucide-react";
import {
  useCopilotCommands,
  useCreateTask,
  useCreateWorkspaceTask,
  useCreateTaskComment,
  useRunCopilot,
  useDeleteTask,
  useDeleteTaskComment,
  useTaskComments,
  useTasksInList,
  useWorkspaceTasks,
  useUpdateTask,
  useWorkspaceProjects,
  useAssignableUsers,
} from "../../hooks/useBiomaApi";
import type {
  CopilotResponse,
  Discipline,
  TaskDependency,
  TaskGroupStatus,
  TaskListType,
  TaskPriority,
  TaskCustomField,
  TaskSubtaskInput,
} from "../../lib/api";
import { groupForStatus, statusesForFrente } from "../../lib/task-frentes";

/** Substitui o "chat da tarefa" do ClickUp: histórico preso à tarefa em vez de
 *  espalhado no WhatsApp. Comentário nasce interno; só vai ao cliente quando
 *  marcado de propósito, porque o Hub é o mesmo lugar onde ele aprova. */
function TaskCommentsSection({ taskId, workspaceId }: { taskId: string; workspaceId?: string }) {
  const { data: comments = [], isLoading } = useTaskComments(taskId);
  const createComment = useCreateTaskComment();
  const deleteComment = useDeleteTaskComment();
  const [body, setBody] = useState("");
  const [clientVisible, setClientVisible] = useState(false);

  // Copiloto na própria caixa de comentário: "/" abre o menu de comandos, o
  // resto do texto vira a mensagem. Sem tela nova — a conversa da tarefa já é
  // o lugar onde a decisão acontece.
  const isCommand = body.trimStart().startsWith("/");
  const { data: commands = [] } = useCopilotCommands("task", isCommand);
  const runCopilot = useRunCopilot();
  const [copilotResult, setCopilotResult] = useState<CopilotResponse | null>(null);

  const commandFilter = isCommand ? body.trimStart().slice(1).split(" ")[0].toLowerCase() : "";
  const visibleCommands = commands.filter(
    (command) =>
      !commandFilter ||
      command.name.includes(commandFilter) ||
      command.label.toLowerCase().includes(commandFilter),
  );

  function askCopilot() {
    const message = body.trim();
    if (!message) return;
    setCopilotResult(null);
    runCopilot.mutate(
      { message, surface: "task", task_id: taskId, workspace_id: workspaceId },
      {
        onSuccess: (result) => {
          setCopilotResult(result);
          setBody("");
        },
      },
    );
  }

  function submit() {
    if (!body.trim()) return;
    createComment.mutate(
      { taskId, body: body.trim(), clientVisible },
      { onSuccess: () => { setBody(""); setClientVisible(false); } },
    );
  }

  return (
    <div style={{ background: "var(--bg-inset)", padding: 12, borderRadius: 6, display: "flex", flexDirection: "column", gap: 10 }}>
      <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
        <MessageSquare size={14} /> Conversa ({comments.length})
      </h3>

      {isLoading && <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Carregando...</span>}

      {!isLoading && comments.length === 0 && (
        <span style={{ fontSize: 12, color: "var(--text-dim)" }}>
          Nenhum comentário. O histórico desta tarefa fica aqui, não no WhatsApp.
        </span>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {comments.map((comment) => (
          <div
            key={comment.id}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 4,
              padding: "8px 10px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <strong style={{ fontSize: 12 }}>{comment.author_name ?? "Usuário removido"}</strong>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 10, color: "var(--text-faint)" }}>
                  {new Date(comment.created_at).toLocaleString("pt-BR")}
                </span>
                {comment.client_visible ? (
                  <span title="Visível para o cliente" style={{ display: "inline-flex", color: "var(--accent)" }}>
                    <Eye size={12} />
                  </span>
                ) : (
                  <span title="Interno da EG" style={{ display: "inline-flex", color: "var(--text-faint)" }}>
                    <EyeOff size={12} />
                  </span>
                )}
                <button
                  className="icon-button danger"
                  type="button"
                  style={{ padding: 2 }}
                  title="Excluir comentário"
                  onClick={() => deleteComment.mutate({ commentId: comment.id, taskId })}
                  disabled={deleteComment.isPending}
                >
                  <X size={12} />
                </button>
              </div>
            </div>
            <p style={{ margin: 0, fontSize: 13, whiteSpace: "pre-wrap" }}>{comment.body}</p>
          </div>
        ))}
      </div>

      {copilotResult && (
        <div style={{ border: "1px solid var(--accent)", borderRadius: 6, padding: "10px 12px", fontSize: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <Sparkles size={13} color="var(--accent)" />
            <strong>Copiloto</strong>
            <span style={{ color: "var(--text-faint)", fontSize: 10 }}>
              confiança {copilotResult.confidence}
              {copilotResult.generation_mode === "preview" ? " · prévia local (sem OPENAI_API_KEY)" : ""}
            </span>
            <button
              className="icon-button"
              type="button"
              style={{ marginLeft: "auto", padding: 2 }}
              onClick={() => setCopilotResult(null)}
              title="Fechar"
            >
              <X size={12} />
            </button>
          </div>

          <p style={{ margin: "0 0 6px", whiteSpace: "pre-wrap" }}>{copilotResult.answer}</p>

          {copilotResult.actions.map((action, index) => (
            <div key={`${action.name}-${index}`} style={{ marginTop: 4, paddingLeft: 8, borderLeft: "2px solid var(--border)" }}>
              <strong style={{ fontSize: 11 }}>{action.label}</strong>{" "}
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  color:
                    action.status === "executed"
                      ? "#2e9e5b"
                      : action.status === "failed"
                        ? "#ff5252"
                        : "#ffab00",
                }}
              >
                {action.status === "executed"
                  ? "feito"
                  : action.status === "pending_confirmation"
                    ? "precisa da sua confirmação"
                    : action.status === "proposed"
                      ? "proposto"
                      : "falhou"}
              </span>
              {action.detail && <div style={{ color: "var(--text-dim)" }}>{action.detail}</div>}
              {action.undo_hint && (
                <div style={{ color: "var(--text-faint)", fontSize: 10 }}>Desfazer: {action.undo_hint}</div>
              )}
            </div>
          ))}

          {/* Toda resposta cita fonte — inclusive quando o dado vem do Bioma. */}
          {copilotResult.sources.length > 0 && (
            <div style={{ marginTop: 8, fontSize: 10, color: "var(--text-faint)" }}>
              Fontes:{" "}
              {copilotResult.sources.map((source, index) => (
                <span key={`${source.reference}-${index}`}>
                  {index > 0 ? " · " : ""}
                  {source.kind === "web" ? (
                    <a href={source.reference} target="_blank" rel="noreferrer">
                      {source.reference}
                    </a>
                  ) : (
                    source.reference
                  )}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {isCommand && visibleCommands.length > 0 && (
        <div style={{ border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" }}>
          {visibleCommands.map((command) => (
            <button
              key={command.name}
              type="button"
              onClick={() => setBody(`/${command.name} `)}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "6px 10px",
                background: "none",
                border: "none",
                borderBottom: "1px solid var(--border)",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              <strong>/{command.name}</strong>{" "}
              <span style={{ color: "var(--text-dim)" }}>{command.description}</span>
              {command.requires_confirmation && (
                <span style={{ color: "#ffab00", fontSize: 10 }}> · pede confirmação</span>
              )}
            </button>
          ))}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <textarea
          className="text-input"
          style={{ minHeight: 60, resize: "vertical", fontSize: 13 }}
          placeholder="Escreva um comentário... ou digite / para chamar o copiloto"
          value={body}
          onChange={(event) => setBody(event.target.value)}
        />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-dim)", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={clientVisible}
              onChange={(event) => setClientVisible(event.target.checked)}
            />
            Visível para o cliente
          </label>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              className="secondary-button"
              type="button"
              onClick={askCopilot}
              disabled={runCopilot.isPending || !body.trim()}
              style={{ padding: "4px 12px", fontSize: 12 }}
              title="Pedir ao copiloto (ações reversíveis são aplicadas na hora)"
            >
              <Sparkles size={13} /> {runCopilot.isPending ? "Pensando..." : "Copiloto"}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={submit}
              disabled={createComment.isPending || !body.trim()}
              style={{ padding: "4px 12px", fontSize: 12 }}
            >
              <Send size={13} /> {createComment.isPending ? "Enviando..." : "Comentar"}
            </button>
          </div>
        </div>
      </div>
      {runCopilot.isError && (
        <div className="notice error" style={{ fontSize: 12 }}>
          {runCopilot.error instanceof Error ? runCopilot.error.message : "O copiloto falhou."}
        </div>
      )}
    </div>
  );
}

type TaskDrawerProps = {
  workspaceId: string;
  /** listId: opcional. Preenchido apenas para tarefas legadas vinculadas a uma lista. */
  listId?: string;
  /** discipline: substitui o tipo de lista no fluxo de criação. */
  discipline?: Discipline;
  listType?: TaskListType; // legado, derivado do discipline quando ausente
  taskId: string | null;
  initialStatus?: TaskGroupStatus;
  initialDetailedStatus?: string;
  /** Preenchido ao criar uma SUBTAREFA a partir de outra tarefa. */
  parentTaskId?: string | null;
  /** Ids das tarefas irmãs, NA ORDEM EM QUE APARECEM na tela que abriu o
   *  drawer. Permite andar de tarefa em tarefa sem fechar e reabrir — ler dez
   *  tarefas exigia dez idas e voltas à lista. A ordem vem de quem chama
   *  justamente para respeitar filtro e agrupamento em vigor. */
  siblingIds?: string[];
  onNavigate?: (taskId: string) => void;
  onClose: () => void;
};


export function TaskDrawer({
  workspaceId,
  listId,
  discipline,
  listType,
  taskId,
  initialStatus,
  initialDetailedStatus,
  parentTaskId,
  siblingIds,
  onNavigate,
  onClose,
}: TaskDrawerProps) {
  /** Vizinhas na ordem da tela. Nulo ao criar tarefa (não há de onde navegar)
   *  ou quando quem abriu não passou a lista — o drawer segue funcionando
   *  igual, só sem as setas. */
  const navigation = useMemo(() => {
    if (!taskId || !siblingIds || !onNavigate) return null;
    const index = siblingIds.indexOf(taskId);
    if (index === -1 || siblingIds.length < 2) return null;
    return {
      position: index + 1,
      total: siblingIds.length,
      previousId: index > 0 ? siblingIds[index - 1] : null,
      nextId: index < siblingIds.length - 1 ? siblingIds[index + 1] : null,
    };
  }, [taskId, siblingIds, onNavigate]);
  // Para editar uma tarefa existente, precisamos encontrá-la:
  // tarefas novas: busca por workspace; tarefas legadas: busca por lista.
  const { data: workspaceTasks } = useWorkspaceTasks(listId ? null : workspaceId);
  const { data: legacyListTasks } = useTasksInList(listId ?? null);
  const tasks = listId ? legacyListTasks : workspaceTasks;

  // Projetos alimentam o seletor de Projeto; sem workspaceId não há como
  // saber quais projetos são elegíveis (o backend recusa projeto de outro).
  const { data: projects = [] } = useWorkspaceProjects(workspaceId ?? null);
  const { data: assignableUsers = [] } = useAssignableUsers(workspaceId ?? null);
  const existingTask = taskId ? tasks?.find(t => t.id === taskId) : null;
  const readOnlyProjection = existingTask?.external_source === "clickup";
  
  const createTask = useCreateTask();
  const createWorkspaceTask = useCreateWorkspaceTask();
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();

  // Tipo efetivo da lista: usa discipline se não há listType explícito
  const effectiveListType: TaskListType = (listType ?? discipline ?? "growth") as TaskListType;

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [acceptanceCriteria, setAcceptanceCriteria] = useState("");
  const [definitionOfDone, setDefinitionOfDone] = useState("");
  const [groupStatus, setGroupStatus] = useState<TaskGroupStatus>("NOT_STARTED");
  const [specificStatus, setSpecificStatus] = useState("");
  const [priority, setPriority] = useState<TaskPriority | "">("");
  const [startDate, setStartDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [recurrence, setRecurrence] = useState<"none" | "weekly" | "monthly">("none");
  const [customFields, setCustomFields] = useState<Record<string, string>>({});
  const [subtasks, setSubtasks] = useState<TaskSubtaskInput[]>([]);
  const [newSubtaskTitle, setNewSubtaskTitle] = useState("");
  const [waitingOnTaskId, setWaitingOnTaskId] = useState<string>("");
  const [projectId, setProjectId] = useState<string>("");
  const [assigneeId, setAssigneeId] = useState<string>("");
  const [ownerId, setOwnerId] = useState<string>("");
  const [creatingSubtaskFor, setCreatingSubtaskFor] = useState<string | null>(null);
  // Entrega do cliente vive no board dele; trabalho interno de plataforma some
  // da visão dele. O filtro real acontece no backend — isto é só o controle.
  const [clientVisible, setClientVisible] = useState(true);

  // Filhas vivem na mesma lista/workspace, entao saem do fetch que ja temos.
  const childTasks = taskId ? (tasks ?? []).filter((t) => t.parent_task_id === taskId) : [];

  useEffect(() => {
    if (existingTask) {
      setTitle(existingTask.title);
      setDescription(existingTask.description || "");
      setAcceptanceCriteria(existingTask.acceptance_criteria || "");
      setDefinitionOfDone(existingTask.definition_of_done || "");
      setClientVisible(existingTask.client_visible ?? true);
      setGroupStatus(existingTask.group_status);
      setSpecificStatus(existingTask.status);
      setPriority(existingTask.priority || "");
      setStartDate(existingTask.start_date ? existingTask.start_date.split("T")[0] : "");
      setDueDate(existingTask.due_date ? existingTask.due_date.split("T")[0] : "");
      setRecurrence(existingTask.recurrence || "none");
      
      const fields: Record<string, string> = {};
      existingTask.custom_fields?.forEach(f => {
        fields[f.field_name] = f.field_value;
      });
      setCustomFields(fields);

      setSubtasks(existingTask.subtasks || []);
      setWaitingOnTaskId(existingTask.dependencies?.[0]?.depends_on_task_id || "");
      setProjectId(existingTask.project_id || "");
      setAssigneeId(existingTask.assignee_id || "");
      setOwnerId(existingTask.owner_id || "");
    } else {
      setTitle("");
      setDescription("");
      setAcceptanceCriteria("");
      setDefinitionOfDone("");
      setGroupStatus(initialStatus || "NOT_STARTED");
      setSpecificStatus(initialDetailedStatus || statusesForFrente(effectiveListType)[0]?.status || "");
      setPriority("");
      setStartDate("");
      setDueDate("");
      setRecurrence("none");
      setCustomFields({});
      setSubtasks([]);
      setWaitingOnTaskId("");
      setProjectId("");
      setAssigneeId("");
      setOwnerId("");
    }
  }, [existingTask, initialStatus, initialDetailedStatus, effectiveListType]);

  const handleAddSubtask = () => {
    if (!newSubtaskTitle.trim()) return;
    setSubtasks(prev => [...prev, { title: newSubtaskTitle.trim(), is_completed: false }]);
    setNewSubtaskTitle("");
  };

  const handleToggleSubtask = (index: number) => {
    setSubtasks(prev => prev.map((st, i) => i === index ? { ...st, is_completed: !st.is_completed } : st));
  };

  const handleRemoveSubtask = (index: number) => {
    setSubtasks(prev => prev.filter((_, i) => i !== index));
  };

  const handleSave = () => {
    if (!title) return;
    
    const formattedFields: TaskCustomField[] = Object.entries(customFields).map(([k, v]) => ({
      field_name: k,
      field_value: v
    }));

    const dependencies: TaskDependency[] = waitingOnTaskId
      ? [{ depends_on_task_id: waitingOnTaskId, type: "waiting_on" }]
      : [];
    
    if (taskId) {
      updateTask.mutate({
        taskId,
        payload: {
          title,
          description,
          acceptance_criteria: acceptanceCriteria || null,
          definition_of_done: definitionOfDone || null,
          group_status: groupStatus,
          status: specificStatus || "pending",
          priority: priority || null,
          start_date: startDate ? new Date(startDate).toISOString() : null,
          due_date: dueDate ? new Date(dueDate).toISOString() : null,
          recurrence,
          client_visible: clientVisible,
          project_id: projectId || null,
          assignee_id: assigneeId || null,
          owner_id: ownerId || null,
          custom_fields: formattedFields,
          dependencies,
          subtasks,
        }
      }, {
        onSuccess: onClose
      });
    } else if (listId) {
      // Criação legada: via lista
      createTask.mutate({
        listId,
        payload: {
          title,
          description,
          acceptance_criteria: acceptanceCriteria || null,
          definition_of_done: definitionOfDone || null,
          status: specificStatus || "pending",
          group_status: groupStatus,
          priority: priority || null,
          start_date: startDate ? new Date(startDate).toISOString() : null,
          due_date: dueDate ? new Date(dueDate).toISOString() : null,
          recurrence,
          client_visible: clientVisible,
          project_id: projectId || null,
          parent_task_id: parentTaskId || null,
          assignee_id: assigneeId || null,
          owner_id: ownerId || null,
          custom_fields: formattedFields,
          dependencies,
          subtasks,
        }
      }, {
        onSuccess: onClose
      });
    } else {
      // Criação nova: direto no workspace, sem lista
      createWorkspaceTask.mutate({
        workspaceId,
        payload: {
          title,
          description,
          acceptance_criteria: acceptanceCriteria || null,
          definition_of_done: definitionOfDone || null,
          status: specificStatus || "pending",
          group_status: groupStatus,
          priority: priority || null,
          start_date: startDate ? new Date(startDate).toISOString() : null,
          due_date: dueDate ? new Date(dueDate).toISOString() : null,
          recurrence,
          client_visible: clientVisible,
          project_id: projectId || null,
          parent_task_id: parentTaskId || null,
          assignee_id: assigneeId || null,
          owner_id: ownerId || null,
          discipline: discipline ?? null,
          custom_fields: formattedFields,
          dependencies,
          subtasks,
        }
      }, {
        onSuccess: onClose
      });
    }
  };

  const handleDelete = () => {
    if (taskId && confirm("Tem certeza que deseja excluir esta tarefa?")) {
      deleteTask.mutate({ taskId, listId }, {
        onSuccess: onClose
      });
    }
  };

  const isBusy = createTask.isPending || createWorkspaceTask.isPending || updateTask.isPending || deleteTask.isPending;
  // effectiveListType serve só para renderizar os status disponíveis.
  // Para tarefas novas sem listId, usa o discipline como proxy.
  const updateField = (name: string, value: string) => {
    setCustomFields(prev => ({ ...prev, [name]: value }));
  };

  return (
    <>
      <div 
        className="task-drawer-overlay" 
        style={{ 
          position: "fixed", inset: 0, 
          background: "rgba(4, 15, 11, 0.75)", 
          backdropFilter: "blur(6px)", 
          WebkitBackdropFilter: "blur(6px)", 
          zIndex: 10000 
        }} 
        onClick={onClose}
      />
      <div 
        className="task-drawer-panel" 
        style={{ 
          position: "fixed", top: 0, right: 0, bottom: 0, width: "100%", maxWidth: 540,
          background: "#09231b",
          borderLeft: "1px solid var(--border-strong)",
          zIndex: 10001, padding: 24, display: "flex", flexDirection: "column",
          boxShadow: "-4px 0 24px rgba(0,0,0,0.5)",
          overflowY: "auto"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>{taskId ? "Editar Tarefa" : "Nova Tarefa"}</h2>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {navigation && (
              <>
                <button
                  className="icon-button"
                  type="button"
                  aria-label="Tarefa anterior"
                  title="Tarefa anterior"
                  disabled={navigation.previousId === null}
                  onClick={() => navigation.previousId && onNavigate?.(navigation.previousId)}
                >
                  <ChevronUp size={18} />
                </button>
                <button
                  className="icon-button"
                  type="button"
                  aria-label="Próxima tarefa"
                  title="Próxima tarefa"
                  disabled={navigation.nextId === null}
                  onClick={() => navigation.nextId && onNavigate?.(navigation.nextId)}
                >
                  <ChevronDown size={18} />
                </button>
                <span style={{ marginRight: 4, color: "var(--text-dim)", fontSize: 12 }}>
                  {navigation.position} de {navigation.total}
                </span>
              </>
            )}
            <button className="icon-button" type="button" onClick={onClose}><X size={20} /></button>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16, flex: 1 }}>
          {readOnlyProjection && (
            <div className="empty-state compact">
              Registro legado importado em modo somente leitura. Duplique-o como tarefa nativa para continuar o trabalho no Bioma.
            </div>
          )}
          {existingTask?.semantic_review_required && (
            <div
              role="status"
              style={{
                padding: "10px 12px",
                border: "1px solid #ffab00",
                borderRadius: 6,
                background: "rgba(255,171,0,0.08)",
                fontSize: 12,
              }}
            >
              Esta tarefa veio do modelo antigo. O texto anterior foi preservado em
              Definição de Pronto; revise a separação entre contexto, aceite e DoD ao salvar.
            </div>
          )}

          <label style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Título</span>
            <input 
              className="text-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex: Definir personas da campanha"
              disabled={isBusy}
            />
          </label>
          
          <div style={{ display: "flex", gap: 16 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>Status da Tarefa</span>
              <select 
                className="text-input" 
                value={specificStatus || (statusesForFrente(effectiveListType)[0]?.status ?? "")}
                onChange={(e) => {
                  const nextStatus = e.target.value;
                  setSpecificStatus(nextStatus);
                  const group = groupForStatus(effectiveListType, nextStatus);
                  if (group) setGroupStatus(group);
                }}
                disabled={isBusy}
              >
                {statusesForFrente(effectiveListType).map((item) => (
                  <option key={item.status} value={item.status}>
                    {item.status}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>Grupo Kanban</span>
              <select 
                className="text-input" 
                value={groupStatus}
                onChange={(e) => setGroupStatus(e.target.value as TaskGroupStatus)}
                disabled={isBusy}
              >
                <option value="NOT_STARTED">A fazer</option>
                <option value="ACTIVE">Em progresso</option>
                <option value="DONE">Concluído</option>
                <option value="CLOSED">Finalizado</option>
              </select>
            </label>
          </div>

          <div style={{ display: "flex", gap: 16 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>Prioridade</span>
              <select 
                className="text-input" 
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority | "")}
                disabled={isBusy}
              >
                <option value="">Nenhuma</option>
                <option value="Baixa">Baixa</option>
                <option value="Média">Média</option>
                <option value="Alta">Alta</option>
              </select>
            </label>

            <label style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>Data de Início</span>
              <input
                type="date"
                className="text-input"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                disabled={isBusy}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>Data de Vencimento</span>
              <input
                type="date"
                className="text-input"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                disabled={isBusy}
              />
            </label>
          </div>

          {/* Entrega contratada mora no board do cliente; trabalho interno de
              plataforma fica escondido dele. O filtro é aplicado no backend. */}
          <label
            style={{
              display: "flex", alignItems: "center", gap: 8, fontSize: 13,
              padding: "10px 12px", borderRadius: 6,
              background: clientVisible ? "transparent" : "rgba(255,171,0,0.08)",
              border: `1px solid ${clientVisible ? "var(--border)" : "#ffab00"}`,
            }}
          >
            <input
              type="checkbox"
              checked={clientVisible}
              onChange={(event) => setClientVisible(event.target.checked)}
              disabled={isBusy}
            />
            {clientVisible ? <Eye size={14} /> : <EyeOff size={14} color="#ffab00" />}
            <span style={{ flex: 1 }}>
              <strong>{clientVisible ? "Visível para o cliente" : "Interna da EG"}</strong>
              <span style={{ display: "block", fontSize: 11, color: "var(--text-dim)" }}>
                {clientVisible
                  ? "Aparece no board do cliente — use para entregas que ele espera."
                  : "Some do board do cliente — use para trabalho interno de plataforma."}
              </span>
            </span>
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 6 }}>
              <Repeat size={14} /> Recorrência Automática (Growth)
            </span>
            <select 
              className="text-input"
              value={recurrence}
              onChange={(e) => setRecurrence(e.target.value as "none" | "weekly" | "monthly")}
              disabled={isBusy}
            >
              <option value="none">Não recorrente (Única)</option>
              <option value="weekly">Semanal (Recria a cada 7 dias)</option>
              <option value="monthly">Mensal (Recria a cada 30 dias)</option>
            </select>
          </label>

          {/* Responsável e Dono: os manuais v1 já pediam os dois, mas não
              existia seletor nenhum na tela — sem isso "Minhas tarefas" do
              Cockpit nunca populava, porque nada ficava atribuído. */}
          {assignableUsers.length > 0 && (
            <div style={{ display: "flex", gap: 16 }}>
              <label style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
                <span style={{ fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 6 }}>
                  <UserRound size={14} /> Responsável
                </span>
                <select
                  className="text-input"
                  value={assigneeId}
                  onChange={(e) => setAssigneeId(e.target.value)}
                  disabled={isBusy}
                >
                  <option value="">Ninguém</option>
                  {assignableUsers.map((person) => (
                    <option key={person.id} value={person.id}>{person.display_name}</option>
                  ))}
                </select>
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
                <span style={{ fontSize: 13, fontWeight: 500 }}>Dono (gestor)</span>
                <select
                  className="text-input"
                  value={ownerId}
                  onChange={(e) => setOwnerId(e.target.value)}
                  disabled={isBusy}
                >
                  <option value="">Ninguém</option>
                  {assignableUsers.map((person) => (
                    <option key={person.id} value={person.id}>{person.display_name}</option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {/* Projeto: a frente define os status, o projeto define escopo e
              contrato (Manual v2). Só aparece se o workspace tiver projetos. */}
          {projects.length > 0 && (
            <label style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 6 }}>
                <FolderKanban size={14} /> Projeto
              </span>
              <select
                className="text-input"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                disabled={isBusy}
              >
                <option value="">Sem projeto</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {/* Subtarefas reais: tarefas com pai. Diferente do checklist abaixo,
              cada uma tem responsável, prazo e status próprios — é o caso de
              quando o trabalho passa para outra área/equipe. */}
          {taskId && (
            <div style={{ background: "var(--bg-inset)", padding: 12, borderRadius: 6, display: "flex", flexDirection: "column", gap: 10 }}>
              <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                <GitBranch size={14} /> Subtarefas ({childTasks.length})
              </h3>
              <span style={{ fontSize: 11, color: "var(--text-dim)", marginTop: -6 }}>
                Use quando o trabalho troca de responsável ou de prazo. Cada uma
                aparece no quadro com o prazo dela.
              </span>

              {childTasks.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {childTasks.map((child) => (
                    <div
                      key={child.id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: 8,
                        background: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: 4,
                        padding: "6px 10px",
                        fontSize: 12,
                      }}
                    >
                      <span>{child.title}</span>
                      <span style={{ color: "var(--text-dim)", fontSize: 11 }}>
                        {child.status}
                        {child.due_date ? ` · ${new Date(child.due_date).toLocaleDateString("pt-BR")}` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <button
                className="mini-button"
                type="button"
                onClick={() => setCreatingSubtaskFor(taskId)}
                style={{ width: "fit-content" }}
                disabled={readOnlyProjection}
              >
                <Plus size={13} /> Nova subtarefa
              </button>
            </div>
          )}

          {/* Subtarefas / Checklists */}
          <div style={{ background: "var(--bg-inset)", padding: 12, borderRadius: 6, display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Manual v2: isto é CHECKLIST — etapas da mesma tarefa, mesmo
                responsável e mesmo prazo. Quando o trabalho troca de mão ou de
                prazo, o certo é criar uma subtarefa (tarefa com pai), que
                aparece no Kanban da equipe que assumiu. */}
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Checklist</h3>
            <span style={{ fontSize: 11, color: "var(--text-dim)", marginTop: -6 }}>
              Etapas desta mesma tarefa. Se mudar o responsável ou o prazo, crie
              uma subtarefa em vez de um item aqui.
            </span>
            
            <div style={{ display: "flex", gap: 8 }}>
              <input 
                className="text-input" 
                placeholder="Adicionar item ao checklist..."
                value={newSubtaskTitle}
                onChange={(e) => setNewSubtaskTitle(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleAddSubtask(); } }}
                style={{ flex: 1, fontSize: 12 }}
              />
              <button className="secondary-button" type="button" onClick={handleAddSubtask} style={{ padding: "4px 10px" }}>
                <Plus size={14} />
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
              {subtasks.map((st, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--surface)", padding: "6px 10px", borderRadius: 4, border: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }} onClick={() => handleToggleSubtask(i)}>
                    {st.is_completed ? <CheckSquare size={16} color="var(--primary)" /> : <Square size={16} color="var(--text-dim)" />}
                    <span style={{ fontSize: 13, textDecoration: st.is_completed ? "line-through" : "none", color: st.is_completed ? "var(--text-dim)" : "var(--text)" }}>
                      {st.title}
                    </span>
                  </div>
                  <button className="icon-button danger" type="button" onClick={() => handleRemoveSubtask(i)} style={{ padding: 2 }}>
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Relacionamento / Waiting On */}
          <label style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 6 }}>
              <Link2 size={14} /> Dependência (Aguardando Tarefa)
            </span>
            <select 
              className="text-input" 
              value={waitingOnTaskId}
              onChange={(e) => setWaitingOnTaskId(e.target.value)}
              disabled={isBusy}
            >
              <option value="">Nenhuma dependência (Livre)</option>
              {tasks?.filter(t => t.id !== taskId).map(t => (
                <option key={t.id} value={t.id}>
                  {t.title} ({t.status || t.group_status})
                </option>
              ))}
            </select>
          </label>
          
          <div style={{ background: "var(--bg-inset)", padding: 12, borderRadius: 6, display: "flex", flexDirection: "column", gap: 12 }}>
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>Campos Personalizados (Custom Fields)</h3>
            
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Esforço</span>
              <select className="text-input" value={customFields["Esforço"] || ""} onChange={e => updateField("Esforço", e.target.value)}>
                <option value="">-</option>
                <option value="Baixo">Baixo (horas)</option>
                <option value="Médio">Médio (dias)</option>
                <option value="Alto">Alto (semanas)</option>
              </select>
            </label>
            
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Área do Projeto</span>
              <select className="text-input" value={customFields["Área do Projeto"] || ""} onChange={e => updateField("Área do Projeto", e.target.value)}>
                <option value="">-</option>
                <option value="Tráfego">Tráfego</option>
                <option value="CRM">CRM</option>
                <option value="Web/Landing Page">Web/Landing Page</option>
                <option value="Automação">Automação</option>
              </select>
            </label>
            
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Missão (Social)</span>
              <select className="text-input" value={customFields["Missão"] || ""} onChange={e => updateField("Missão", e.target.value)}>
                <option value="">-</option>
                <option value="Atrair">Atrair</option>
                <option value="Nutrir">Nutrir</option>
                <option value="Posicionar">Posicionar</option>
                <option value="Converter">Converter</option>
              </select>
            </label>
            
            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Verba / Budget</span>
              <input type="text" className="text-input" placeholder="R$ 0,00" value={customFields["Verba"] || ""} onChange={e => updateField("Verba", e.target.value)} />
            </label>

            <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Link do Doc</span>
              <input type="url" className="text-input" placeholder="https://" value={customFields["Link do Doc"] || ""} onChange={e => updateField("Link do Doc", e.target.value)} />
            </label>
          </div>

          <label style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Contexto e resultado esperado</span>
            <span style={{ fontSize: 11, color: "var(--text-dim)", marginTop: -4 }}>
              Por que existe, qual problema resolve e qual resultado se espera.
            </span>
            <textarea
              className="text-input"
              style={{ minHeight: 90, resize: "vertical" }}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ex: o cliente precisa acompanhar o avanço sem pedir atualização no WhatsApp."
              disabled={isBusy}
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Critérios de aceite</span>
            <span style={{ fontSize: 11, color: "var(--text-dim)", marginTop: -4 }}>
              Comportamentos específicos que uma pessoa consegue verificar.
            </span>
            <textarea
              className="text-input"
              style={{ minHeight: 90, resize: "vertical" }}
              value={acceptanceCriteria}
              onChange={(e) => setAcceptanceCriteria(e.target.value)}
              placeholder="Ex: dado o workspace do cliente, ao abrir a Home, ele vê a próxima decisão pendente."
              disabled={isBusy}
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>Definição de Pronto</span>
            <span style={{ fontSize: 11, color: "var(--text-dim)", marginTop: -4 }}>
              Gates técnicos e operacionais para esta tarefa poder ser fechada.
            </span>
            <textarea
              className="text-input"
              style={{ minHeight: 100, resize: "vertical" }}
              value={definitionOfDone}
              onChange={(e) => setDefinitionOfDone(e.target.value)}
              placeholder="Ex: testes passam, PR aprovado e deploy em staging validado."
              disabled={isBusy}
            />
          </label>

          {taskId && <TaskCommentsSection taskId={taskId} workspaceId={workspaceId} />}
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
          {taskId ? (
            <button className="danger-button" type="button" onClick={handleDelete} disabled={isBusy || readOnlyProjection}>
              <Trash2 size={16} /> Excluir
            </button>
          ) : <div></div>}
          
          <div style={{ display: "flex", gap: 12 }}>
            <button className="secondary-button" type="button" onClick={onClose} disabled={isBusy}>
              Cancelar
            </button>
            <button className="primary-button" type="button" onClick={handleSave} disabled={isBusy || !title || readOnlyProjection}>
              <Save size={16} /> Salvar
            </button>
          </div>
        </div>
      </div>

      {/* Drawer aninhado para criar a subtarefa, já com o pai preenchido. */}
      {creatingSubtaskFor && (
        <TaskDrawer
          workspaceId={workspaceId}
          listId={listId}
          discipline={discipline}
          listType={listType}
          taskId={null}
          parentTaskId={creatingSubtaskFor}
          onClose={() => setCreatingSubtaskFor(null)}
        />
      )}
    </>
  );
}
