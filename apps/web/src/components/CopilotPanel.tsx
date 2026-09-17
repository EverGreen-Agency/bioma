import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive, ChevronDown, ChevronRight, Clock, ExternalLink, FileText, Image as ImageIcon,
  Loader2, MessageSquarePlus, Mic, Paperclip, PanelRightClose, Send, Sparkles, TriangleAlert, X,
} from "lucide-react";

import {
  api,
  type CopilotAction,
  type CopilotAttachment,
  type CopilotBlock,
  type CopilotRunTrace,
  type CopilotSource,
  type CopilotSurface,
} from "../lib/api";
import { useDictation } from "../hooks/useDictation";
import { useUiStore } from "../store/uiStore";
import { SaveToStudioButton } from "./SaveToStudioButton";

/**
 * Painel fixo do copiloto — a "sala" da conversa.
 *
 * Decisão do Eduardo (DECISOES-ABERTAS #3): painel lateral colapsável + `Ctrl+K`
 * como porta de entrada. Não são alternativas — o atalho abre o painel com o
 * foco no campo, como Gemini/Docs e Cursor fazem.
 *
 * A conversa acompanha você ao trocar de tela: o fio do assunto continua e o
 * escopo (workspace/tarefa) passa a ser o da tela nova.
 */

const STORAGE_KEY = "bioma_copilot_panel_open";

function formatDuration(ms: number | null) {
  if (ms === null) return "—";
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}

function formatCost(cents: number | null) {
  // Nulo é "modelo sem preço na tabela", não "de graça". Dizer isso importa.
  if (cents === null) return "sem preço na tabela";
  return `US$ ${(cents / 100).toFixed(4)}`;
}

function formatResetIn(iso: string | null) {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "resetando agora";
  const hours = Math.round(ms / 3_600_000);
  if (hours < 24) return `reseta em ${hours}h`;
  return `reseta em ${Math.round(hours / 24)}d`;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const KIND_ICON = { image: ImageIcon, audio: Mic, document: FileText } as const;

/**
 * Markdown mínimo: negrito, itálico, código e lista.
 *
 * Uma biblioteca completa traria sanitização, tabelas e 40 KB para renderizar o
 * que o copiloto de fato devolve. Escapamos o HTML primeiro — a resposta vem de
 * um modelo, e modelo repete o que leu, inclusive `<script>` que estava num
 * anexo.
 */
function renderAnswer(text: string) {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const html = escaped
    .replace(/`([^`\n]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|\s)\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/^[-*]\s+(.+)$/gm, "<li>$1</li>")
    .replace(/(<li>[\s\S]*?<\/li>)(?!\s*<li>)/g, "<ul>$1</ul>");
  return { __html: html.replace(/\n{2,}/g, "<br/><br/>").replace(/\n/g, "<br/>") };
}

/** Escopo derivado da rota: o copiloto enxerga a tela em que você está. */
function useScopeFromRoute(): {
  surface: CopilotSurface;
  workspaceId?: string;
  projectId?: string;
  opportunityId?: string;
  proposalId?: string;
  label: string;
} {
  const location = useLocation();
  const params = useParams();
  const selectedClientId = useUiStore((state) => state.selectedClientId);
  const { data: workspaces } = useQuery({
    queryKey: ["workspaces"],
    queryFn: () => api.workspaces(),
    staleTime: 5 * 60 * 1000,
  });

  return useMemo(() => {
    const clientId = params.clientId ?? selectedClientId;
    const workspace = workspaces?.find((item) => item.kind === "client" && item.client_id === clientId);
    if (location.pathname.startsWith("/clientes") && workspace) {
      return {
        surface: "workspace" as const,
        workspaceId: workspace.id,
        projectId: params.projectId,
        opportunityId: params.oppId ?? params.opportunityId,
        proposalId: params.proposalId,
        label: workspace.name,
      };
    }
    return { surface: "workspace" as const, label: "Operação EG" };
  }, [
    location.pathname,
    params.clientId,
    params.projectId,
    params.oppId,
    params.opportunityId,
    params.proposalId,
    selectedClientId,
    workspaces,
  ]);
}

function SourceItems({ sources }: { sources: CopilotSource[] }) {
  return (
    <div className="copilot-sources">
      {sources.map((source, index) => {
        if (source.kind === "web") {
          let label = source.reference;
          try { label = new URL(source.reference).hostname; } catch { /* fonte inválida fica como texto */ }
          return source.reference.startsWith("http") ? (
            <a key={index} href={source.reference} target="_blank" rel="noreferrer">
              <ExternalLink size={11} /> {label}
            </a>
          ) : <span key={index}>{label}</span>;
        }
        return <span key={index}>{source.reference}</span>;
      })}
    </div>
  );
}

function CopilotBlockView({ block }: { block: CopilotBlock }) {
  if (block.kind === "markdown") {
    return <div className="copilot-answer" dangerouslySetInnerHTML={renderAnswer(String(block.data.text ?? ""))} />;
  }
  if (block.kind === "entity_summary") {
    return (
      <div className="copilot-entity-block">
        <strong>{block.title ?? "Contexto ativo"}</strong>
        <span>{String(block.data.entity_type ?? "item")} · {String(block.data.entity_id ?? "")}</span>
      </div>
    );
  }
  if (block.kind === "action_list") {
    const actions = Array.isArray(block.data.items) ? block.data.items as CopilotAction[] : [];
    return (
      <ul className="copilot-actions">
        {actions.map((action, index) => (
          <li key={index} className={action.status}>
            <strong>{action.label}</strong>
            <span>{action.detail}</span>
            {action.undo_hint && <em>Desfazer: {action.undo_hint}</em>}
          </li>
        ))}
      </ul>
    );
  }
  if (block.kind === "source_list") {
    const sources = Array.isArray(block.data.items) ? block.data.items as CopilotSource[] : [];
    return <SourceItems sources={sources} />;
  }
  return (
    <div className="copilot-entity-block">
      <strong>{block.title ?? block.kind.replace(/_/g, " ")}</strong>
      <span>Bloco disponível na visualização operacional.</span>
    </div>
  );
}

function AttachmentChip({
  attachment,
  onRemove,
}: {
  attachment: CopilotAttachment;
  onRemove?: () => void;
}) {
  const Icon = KIND_ICON[attachment.kind];
  // Anexo que o copiloto não consegue ler continua visível, com o motivo. Sumir
  // com ele faria a pessoa achar que foi lido.
  const unreadable = !attachment.has_text && attachment.kind !== "image";
  return (
    <span className={`copilot-chip ${unreadable ? "warn" : ""}`} title={attachment.extraction_error ?? undefined}>
      {unreadable ? <TriangleAlert size={12} /> : <Icon size={12} />}
      <span className="copilot-chip-name">{attachment.file_name}</span>
      <small>{formatSize(attachment.size_bytes)}</small>
      {onRemove && (
        <button type="button" onClick={onRemove} aria-label={`Remover ${attachment.file_name}`}>
          <X size={11} />
        </button>
      )}
    </span>
  );
}

function StepList({ trace }: { trace: CopilotRunTrace }) {
  const statusColor: Record<string, string> = {
    ok: "#2e9e5b", skipped: "var(--text-dim)", blocked: "#ffab00", failed: "#ff5252",
  };
  return (
    <div className="copilot-trace">
      <div className="copilot-trace-meta">
        <span><Clock size={12} /> {formatDuration(trace.duration_ms)}</span>
        {trace.generation_mode === "preview" ? (
          <span title="Sem provedor configurado: resposta gerada localmente, nenhum token gasto.">
            prévia local
          </span>
        ) : trace.routed_account ? (
          <>
            <span title="Rodou na cota da assinatura, não na chave de API">
              {trace.model ?? "modelo"} via {trace.routed_account.display_name}
            </span>
            <span>
              {trace.input_tokens ?? 0}+{trace.output_tokens ?? 0} tokens
              {trace.cost_cents !== null && <> · {formatCost(trace.cost_cents)}</>}
            </span>
            {trace.routed_account.buckets.length > 0 ? (
              trace.routed_account.buckets.slice(0, 2).map((bucket) => (
                <span
                  key={bucket.bucket_key}
                  title={
                    bucket.confidence === "authoritative"
                      ? "Reportado pelo próprio provedor"
                      : "Estimativa — não confirmada pelo provedor"
                  }
                >
                  {bucket.remaining_percent !== null ? `${Math.round(bucket.remaining_percent)}% restante` : bucket.bucket_key}
                  {bucket.resets_at && ` · ${formatResetIn(bucket.resets_at)}`}
                  {bucket.confidence !== "authoritative" && " (estimado)"}
                </span>
              ))
            ) : (
              <span title="Conta cadastrada, mas a coleta de cota ainda não rodou">cota ainda não coletada</span>
            )}
          </>
        ) : (
          <>
            <span>{trace.model ?? "modelo não informado"}</span>
            <span>
              {trace.input_tokens ?? 0}+{trace.output_tokens ?? 0} tokens · {formatCost(trace.cost_cents)}
            </span>
          </>
        )}
      </div>

      <ol className="copilot-trace-steps">
        {trace.steps.map((step) => (
          <li key={step.position}>
            <span className="copilot-trace-dot" style={{ background: statusColor[step.status] }} />
            <span className="copilot-trace-label">{step.label}</span>
            <span className="copilot-trace-time">{formatDuration(step.duration_ms)}</span>
            {step.detail && <span className="copilot-trace-detail">{step.detail}</span>}
          </li>
        ))}
      </ol>

      <div className="copilot-trace-context">
        <strong>Leu:</strong>{" "}
        {Object.entries(trace.dossier_summary)
          .filter(([, value]) => typeof value === "number" && value > 0)
          .map(([key, value]) => `${key.replace(/_/g, " ")}: ${value}`)
          .join(" · ") || "nada além do escopo da tela"}
      </div>
      {trace.memories_used.length > 0 && (
        <div className="copilot-trace-context">
          <strong>Memórias:</strong> {trace.memories_used.map((row) => row.title).join(" · ")}
        </div>
      )}
      {trace.skills_used.length > 0 && (
        <div className="copilot-trace-context">
          <strong>Habilidades:</strong> {trace.skills_used.join(" · ")}
        </div>
      )}
    </div>
  );
}

export function CopilotPanel() {
  const queryClient = useQueryClient();
  const scope = useScopeFromRoute();
  const [isOpen, setIsOpen] = useState(() => {
    // Fechado no primeiro acesso; depois lembra o último estado.
    try { return localStorage.getItem(STORAGE_KEY) === "true"; } catch { return false; }
  });
  const [threadId, setThreadId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState<CopilotAttachment[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [openTrace, setOpenTrace] = useState<string | null>(null);
  const [showThreads, setShowThreads] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Ditado pelo navegador: não consome cota de provedor nenhum. O trecho
  // reconhecido é acrescentado ao que já estava escrito, para dar para misturar
  // digitar e falar sem perder o começo.
  const dictation = useDictation((text) =>
    setMessage((current) => (current ? `${current.trimEnd()} ${text}` : text)),
  );

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, String(isOpen)); } catch { /* modo privado */ }
  }, [isOpen]);

  // `Ctrl+K` (ou `Cmd+K`) abre o painel já com o foco no campo — é a porta.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setIsOpen(true);
        window.setTimeout(() => inputRef.current?.focus(), 60);
      }
      if (event.key === "Escape" && document.activeElement === inputRef.current) {
        inputRef.current?.blur();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const threads = useQuery({
    queryKey: ["copilot-threads"],
    queryFn: () => api.copilotThreads("active"),
    enabled: isOpen,
  });

  const runs = useQuery({
    queryKey: ["copilot-thread", threadId],
    queryFn: () => api.copilotThreadRuns(threadId!),
    enabled: isOpen && Boolean(threadId),
  });

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadCopilotAttachment(file, threadId ?? undefined),
    onSuccess: (attachment) => {
      setUploadError(null);
      setPending((current) => [...current, attachment]);
    },
    onError: (error: Error) => setUploadError(error.message),
  });

  const send = useMutation({
    mutationFn: (text: string) =>
      api.runCopilot({
        message: text,
        surface: scope.surface,
        workspace_id: scope.workspaceId,
        project_id: scope.projectId,
        opportunity_id: scope.opportunityId,
        proposal_id: scope.proposalId,
        thread_id: threadId ?? undefined,
        attachment_ids: pending.map((item) => item.id),
      }),
    onSuccess: async (response) => {
      setThreadId(response.thread_id);
      setMessage("");
      setPending([]);
      await queryClient.invalidateQueries({ queryKey: ["copilot-thread", response.thread_id] });
      await queryClient.invalidateQueries({ queryKey: ["copilot-threads"] });
      if (response.actions.some((action) => action.status === "executed")) {
        // Algo mudou de verdade no Bioma: a tela por trás precisa refletir.
        await queryClient.invalidateQueries({ queryKey: ["tasks"] });
      }
    },
  });

  const archive = useMutation({
    mutationFn: (id: string) => api.archiveCopilotThread(id),
    onSuccess: async (_data, id) => {
      if (threadId === id) setThreadId(null);
      await queryClient.invalidateQueries({ queryKey: ["copilot-threads"] });
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [runs.data?.length, send.isPending]);

  function attachFiles(files: FileList | File[] | null) {
    if (!files) return;
    for (const file of Array.from(files)) upload.mutate(file);
  }

  function submit() {
    const text = message.trim();
    if (text && !send.isPending) send.mutate(text);
  }

  if (!isOpen) {
    return (
      <button
        className="copilot-launcher"
        type="button"
        onClick={() => { setIsOpen(true); window.setTimeout(() => inputRef.current?.focus(), 60); }}
        title="Abrir copiloto (Ctrl+K)"
      >
        <Sparkles size={18} />
      </button>
    );
  }

  return (
    <aside
      className={`copilot-panel ${isDragging ? "dragging" : ""}`}
      onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        attachFiles(event.dataTransfer.files);
      }}
    >
      <header className="copilot-panel-header">
        <div>
          <strong><Sparkles size={15} /> Copiloto</strong>
          <span title="Escopo que o copiloto enxerga nesta tela">{scope.label}</span>
        </div>
        <div className="copilot-panel-header-actions">
          <button type="button" onClick={() => setShowThreads((value) => !value)} title="Conversas">
            <MessageSquarePlus size={15} />
          </button>
          <button type="button" onClick={() => setIsOpen(false)} title="Fechar (Ctrl+K reabre)">
            <PanelRightClose size={15} />
          </button>
        </div>
      </header>

      {showThreads && (
        <div className="copilot-threads">
          <button
            className="copilot-thread-new"
            type="button"
            onClick={() => { setThreadId(null); setShowThreads(false); inputRef.current?.focus(); }}
          >
            + Nova conversa
          </button>
          {threads.isLoading && <p className="copilot-empty">Carregando…</p>}
          {threads.data?.length === 0 && <p className="copilot-empty">Nenhuma conversa ainda.</p>}
          {threads.data?.map((thread) => (
            <div className={`copilot-thread-row ${thread.id === threadId ? "selected" : ""}`} key={thread.id}>
              <button type="button" onClick={() => { setThreadId(thread.id); setShowThreads(false); }}>
                <span>{thread.title ?? "Sem título"}</span>
                <small>{thread.run_count} turno(s)</small>
              </button>
              <button
                className="copilot-thread-archive"
                type="button"
                title="Arquivar"
                onClick={() => archive.mutate(thread.id)}
              >
                <Archive size={13} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="copilot-panel-body">
        {!threadId && !send.isPending && (
          <div className="copilot-intro">
            <p>Converse como no ChatGPT. Ele lê o escopo desta tela, mantém a continuidade e cita a fonte de tudo.</p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "10px 0" }}>
              <button
                type="button"
                className="mini-button"
                onClick={() => { setMessage("@Propostas "); window.setTimeout(() => inputRef.current?.focus(), 20); }}
              >
                @Propostas · colar uma vaga
              </button>
              <button
                type="button"
                className="mini-button"
                onClick={() => { setMessage("Retome o contexto e me diga a próxima ação mais útil. "); window.setTimeout(() => inputRef.current?.focus(), 20); }}
              >
                Retomar este contexto
              </button>
            </div>
            <ul>
              <li>Cole uma vaga após <strong>@Propostas</strong>: ela pode virar oportunidade ligada à conversa.</li>
              <li>Volte depois para registrar resposta, reunião, WhatsApp, proposta e decisão.</li>
              <li>Em tarefas, peça resumo, subtarefas ou próxima ação com o contexto da tela.</li>
            </ul>
            <p className="copilot-intro-hint">
              Arraste um arquivo, cole uma imagem, ou use o clipe. Documento vira texto e funciona
              em qualquer provedor.
            </p>
          </div>
        )}

        {runs.data?.map((trace) => (
          <div className="copilot-turn" key={trace.id}>
            <div className="copilot-message user">
              {trace.message}
              {trace.attachments.length > 0 && (
                <div className="copilot-chips">
                  {trace.attachments.map((item) => {
                    const Icon = KIND_ICON[item.kind as keyof typeof KIND_ICON] ?? FileText;
                    return (
                      <span className="copilot-chip small" key={item.id}>
                        <Icon size={11} /> {item.file_name}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>

            {trace.status === "failed" ? (
              <div className="copilot-message error">
                Falhou: {trace.error_message ?? "motivo não registrado"}
              </div>
            ) : (
              <div className="copilot-message agent">
                {trace.generation_mode === "preview" && (
                  <div className="copilot-preview-flag">
                    Prévia local — nenhum modelo foi consultado (sem chave de IA no servidor). Configure em
                    Configurações&nbsp;→&nbsp;Empresa ou Operação&nbsp;EG&nbsp;→&nbsp;IA.
                  </div>
                )}
                {trace.response_blocks?.length > 0 ? (
                  <div className="copilot-blocks">
                    {trace.response_blocks.map((block) => <CopilotBlockView key={block.id} block={block} />)}
                  </div>
                ) : (
                  <div className="copilot-answer" dangerouslySetInnerHTML={renderAnswer(trace.answer ?? "")} />
                )}

                {(!trace.response_blocks?.length && trace.actions.length > 0) && (
                  <ul className="copilot-actions">
                    {trace.actions.map((action, index) => (
                      <li key={index} className={action.status}>
                        <strong>{action.label}</strong>
                        <span>{action.detail}</span>
                        {action.undo_hint && <em>Desfazer: {action.undo_hint}</em>}
                      </li>
                    ))}
                  </ul>
                )}

                {(!trace.response_blocks?.length && trace.sources.length > 0) && (
                  <SourceItems sources={trace.sources as CopilotSource[]} />
                )}

                <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                  <button
                    className="copilot-trace-toggle"
                    type="button"
                    onClick={() => setOpenTrace(openTrace === trace.id ? null : trace.id)}
                  >
                    {openTrace === trace.id ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    Como ele chegou nisso
                  </button>
                  {/* Decisão 8: o que a conversa produziu deixa de morrer nela.
                      Só aparece quando há resposta — não há o que salvar de uma
                      execução que falhou. */}
                  {trace.answer && (
                    <SaveToStudioButton runId={trace.id} defaultTitle={trace.answer} />
                  )}
                </div>
                {openTrace === trace.id && <StepList trace={trace} />}
              </div>
            )}
          </div>
        ))}

        {send.isPending && (
          <div className="copilot-message agent pending">
            <Loader2 size={14} className="spin" /> Lendo o escopo e pensando…
          </div>
        )}
        {send.error && (
          <div className="copilot-message error">
            {send.error.message}
            <button type="button" onClick={() => send.reset()}><X size={12} /></button>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        className="copilot-composer"
        onSubmit={(event) => { event.preventDefault(); submit(); }}
      >
        {(pending.length > 0 || upload.isPending || uploadError) && (
          <div className="copilot-chips">
            {pending.map((attachment) => (
              <AttachmentChip
                key={attachment.id}
                attachment={attachment}
                onRemove={() => {
                  setPending((current) => current.filter((item) => item.id !== attachment.id));
                  void api.deleteCopilotAttachment(attachment.id).catch(() => undefined);
                }}
              />
            ))}
            {upload.isPending && (
              <span className="copilot-chip"><Loader2 size={11} className="spin" /> enviando…</span>
            )}
            {uploadError && (
              <span className="copilot-chip warn">
                <TriangleAlert size={11} /> {uploadError}
                <button type="button" onClick={() => setUploadError(null)}><X size={11} /></button>
              </span>
            )}
          </div>
        )}

        {(dictation.isListening || dictation.error) && (
          <div className="copilot-chips">
            {dictation.isListening && (
              <span className="copilot-chip listening">
                <Mic size={11} /> ouvindo… fale e o texto aparece no campo
              </span>
            )}
            {dictation.error && (
              <span className="copilot-chip warn">
                <TriangleAlert size={11} /> {dictation.error}
                <button type="button" onClick={dictation.clearError}><X size={11} /></button>
              </span>
            )}
          </div>
        )}

        <div className="copilot-composer-row">
          <input
            ref={fileRef}
            type="file"
            multiple
            hidden
            onChange={(event) => { attachFiles(event.target.files); event.target.value = ""; }}
          />
          <button
            type="button"
            className="copilot-attach"
            onClick={() => fileRef.current?.click()}
            title="Anexar arquivo, imagem ou áudio"
          >
            <Paperclip size={15} />
          </button>
          {dictation.isSupported && (
            <button
              type="button"
              className={`copilot-attach ${dictation.isListening ? "listening" : ""}`}
              onClick={dictation.toggle}
              title={
                dictation.isListening
                  ? "Parar de ouvir"
                  : "Ditar (reconhecimento do navegador — não consome cota)"
              }
            >
              <Mic size={15} />
            </button>
          )}
          <textarea
            ref={inputRef}
            rows={2}
            value={dictation.interim ? `${message}${message ? " " : ""}${dictation.interim}` : message}
            placeholder="Pergunte, cole uma vaga ou use @Propostas…  (Ctrl+K)"
            onChange={(event) => setMessage(event.target.value)}
            onPaste={(event) => {
              // Colar print é como a maioria manda imagem — mais que arrastar.
              const files = Array.from(event.clipboardData.files);
              if (files.length) {
                event.preventDefault();
                attachFiles(files);
              }
            }}
            onKeyDown={(event) => {
              // Enter envia, Shift+Enter quebra linha — o padrão que a mão espera.
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                // Enviar com o microfone aberto deixaria o reconhecedor
                // escrevendo numa mensagem que já foi.
                if (dictation.isListening) dictation.stop();
                submit();
              }
            }}
          />
          <button type="submit" disabled={send.isPending || !message.trim()} title="Enviar">
            <Send size={15} />
          </button>
        </div>
      </form>
    </aside>
  );
}
