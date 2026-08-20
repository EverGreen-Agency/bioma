import { useEffect, useRef, useState } from "react";
import { Loader2, Plus, TriangleAlert } from "lucide-react";

import { useCreateWorkspaceTask } from "../../hooks/useBiomaApi";
import type { Discipline, TaskGroupStatus } from "../../lib/api";
import type { ComposerProjectState } from "../../lib/task-composer";

/**
 * Criação de tarefa em uma linha: digita o título, Enter, pronto.
 *
 * Antes, tanto a lista quanto o kanban abriam o `TaskDrawer` inteiro (quase mil
 * linhas de formulário) só para registrar um título — e o resto dos campos
 * ficava vazio de qualquer jeito. O atrito fazia a pessoa não anotar a tarefa,
 * que é o pior resultado possível para um gestor de tarefas.
 *
 * O composer **continua aberto após salvar**, de propósito: quem está
 * despejando o que tem na cabeça anota várias seguidas, e reabrir o campo a
 * cada item recria o atrito que este componente existe para remover. Os
 * detalhes (responsável, prazo, definição de pronto) entram depois, abrindo a
 * tarefa — e aí o formulário completo faz sentido.
 *
 * `project` chega resolvido de cima (`resolveComposerProject`). Quando a regra
 * da decisão 13 não consegue decidir sozinha, o campo não aparece: no lugar dele
 * vem o que fazer. Deixar digitar para depois responder 422 ensina a regra do
 * jeito mais caro possível — o texto já digitado some e a pessoa não sabe por quê.
 */
export function InlineTaskComposer({
  workspaceId,
  status,
  groupStatus,
  discipline,
  project,
  placeholder = "Escreva o título e tecle Enter",
  autoFocus = false,
  onCancel,
}: {
  workspaceId: string;
  /** Status detalhado da coluna/seção onde a tarefa nasce. */
  status: string;
  groupStatus: TaskGroupStatus;
  discipline?: Discipline;
  /** Projeto resolvido pela regra da decisão 13, ou o motivo de não dar. */
  project: ComposerProjectState;
  placeholder?: string;
  autoFocus?: boolean;
  onCancel?: () => void;
}) {
  const createTask = useCreateWorkspaceTask();
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  function submit() {
    const clean = title.trim();
    if (!clean || createTask.isPending) return;
    setError(null);
    createTask.mutate(
      {
        workspaceId,
        payload: {
          title: clean,
          status,
          group_status: groupStatus,
          discipline: discipline ?? null,
          project_id: project.ready ? project.projectId : null,
          recurrence: "none",
          custom_fields: [],
          dependencies: [],
          subtasks: [],
        },
      },
      {
        onSuccess: () => {
          setTitle("");
          inputRef.current?.focus();
        },
        // O erro fica na própria linha, não em alert: a pessoa vê o que
        // escreveu junto do motivo e corrige sem perder o texto.
        onError: (err: Error) => setError(err.message || "Não foi possível criar a tarefa."),
      },
    );
  }

  if (!project.ready) {
    return (
      <p className="inline-task-composer-blocked">
        <TriangleAlert size={12} aria-hidden /> {project.message}
      </p>
    );
  }

  return (
    <div className="inline-task-composer">
      <div className="inline-task-composer-row">
        {createTask.isPending ? (
          <Loader2 size={14} className="spin" aria-hidden />
        ) : (
          <Plus size={14} aria-hidden />
        )}
        <input
          ref={inputRef}
          value={title}
          placeholder={placeholder}
          aria-label="Título da nova tarefa"
          onChange={(event) => setTitle(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              submit();
            }
            if (event.key === "Escape") {
              setTitle("");
              setError(null);
              onCancel?.();
            }
          }}
          // Sair do campo sem texto fecha o composer no kanban (onde ele é
          // acionado por botão); na lista ele é permanente e `onCancel` é nulo.
          onBlur={() => {
            if (!title.trim()) onCancel?.();
          }}
          disabled={createTask.isPending}
        />
        <button
          type="button"
          className="mini-button"
          onClick={submit}
          disabled={!title.trim() || createTask.isPending}
        >
          Salvar
        </button>
      </div>
      {error && (
        <p className="inline-task-composer-error">
          <TriangleAlert size={12} aria-hidden /> {error}
        </p>
      )}
    </div>
  );
}
