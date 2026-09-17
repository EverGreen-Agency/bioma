import { useEffect, useMemo, useRef, useState } from "react";
import { BookOpen, Plus, Upload, Save, Trash2, Paperclip, Download, X, FileText, DownloadCloud, Printer } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { SectionHeader, EmptyState } from "../../components/shared";
import { api } from "../../lib/api";
import type { WikiCategory, WikiDocumentDetail, WikiDocumentSummary } from "../../lib/api";

const CATEGORIES: { id: WikiCategory; label: string }[] = [
  { id: "comercial", label: "Comercial & Vendas" },
  { id: "rh", label: "Recursos Humanos" },
  { id: "operacao", label: "Operação" },
  { id: "geral", label: "Geral" },
];

const CATEGORY_LABEL = Object.fromEntries(CATEGORIES.map((c) => [c.id, c.label])) as Record<WikiCategory, string>;

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function WikiEgView() {
  const [documents, setDocuments] = useState<WikiDocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<WikiDocumentDetail | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<{ title: string; category: WikiCategory; content: string }>({
    title: "",
    category: "geral",
    content: "",
  });
  const [busy, setBusy] = useState(false);
  const [attachmentNote, setAttachmentNote] = useState<string | null>(null);
  const [coreNote, setCoreNote] = useState<string | null>(null);
  const importInput = useRef<HTMLInputElement>(null);
  const attachInput = useRef<HTMLInputElement>(null);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      setDocuments(await api.wikiDocuments());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível carregar o Wiki.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const openDocument = async (id: string) => {
    setEditing(false);
    setAttachmentNote(null);
    try {
      const detail = await api.wikiDocument(id);
      setSelected(detail);
      setDraft({ title: detail.title, category: detail.category, content: detail.content });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível abrir o documento.");
    }
  };

  const startNew = (category: WikiCategory = "geral") => {
    setSelected(null);
    setEditing(true);
    setAttachmentNote(null);
    setDraft({ title: "", category, content: "" });
  };

  const handleDownloadMd = () => {
    if (!selected) return;
    const blob = new Blob([selected.content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selected.title.replace(/[^a-zA-Z0-9_\-]/g, "_")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadTxt = () => {
    if (!selected) return;
    const blob = new Blob([selected.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selected.title.replace(/[^a-zA-Z0-9_\-]/g, "_")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePrintPdf = () => {
    window.print();
  };

  const handleImportCore = async () => {
    setBusy(true);
    setCoreNote(null);
    try {
      const result = await api.importCoreWikiDocuments();
      if (!result.available) {
        setCoreNote("Os manuais core só estão disponíveis no ambiente de desenvolvimento EG (monorepo).");
      } else if (result.imported.length === 0) {
        setCoreNote(`Nada novo: ${result.skipped.length} manual(is) já estavam no Wiki.`);
      } else {
        setCoreNote(`Importados ${result.imported.length} manual(is): ${result.imported.join(", ")}.`);
        await loadDocuments();
      }
    } catch (err) {
      setCoreNote(err instanceof Error ? err.message : "Falha ao importar os manuais core.");
    } finally {
      setBusy(false);
    }
  };

  const handleImport = async (file: File) => {
    const text = await file.text();
    const title = file.name.replace(/\.(md|markdown|txt)$/i, "");
    setBusy(true);
    try {
      const created = await api.createWikiDocument({ category: "geral", title, content: text });
      await loadDocuments();
      setSelected(created);
      setDraft({ title: created.title, category: created.category, content: created.content });
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao importar o arquivo.");
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async () => {
    if (!draft.title.trim()) {
      setError("Dê um título ao documento.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const saved = selected
        ? await api.updateWikiDocument(selected.id, draft)
        : await api.createWikiDocument(draft);
      await loadDocuments();
      setSelected(saved);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar.");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!selected || !window.confirm(`Excluir "${selected.title}"?`)) return;
    setBusy(true);
    try {
      await api.deleteWikiDocument(selected.id);
      await loadDocuments();
      setSelected(null);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao excluir.");
    } finally {
      setBusy(false);
    }
  };

  const handleAttach = async (file: File) => {
    if (!selected) return;
    setBusy(true);
    setAttachmentNote(null);
    try {
      await api.uploadWikiAttachment(selected.id, file);
      setSelected(await api.wikiDocument(selected.id));
      await loadDocuments();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao anexar.";
      setAttachmentNote(
        message.includes("não configurado")
          ? "Anexos precisam de armazenamento S3 configurado (STORAGE_S3_*). O texto do documento já é salvo sem isso."
          : message,
      );
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async (attachmentId: string) => {
    try {
      const { url } = await api.wikiAttachmentDownloadUrl(attachmentId);
      window.open(url, "_blank", "noopener");
    } catch (err) {
      setAttachmentNote(err instanceof Error ? err.message : "Falha ao baixar.");
    }
  };

  const handleDeleteAttachment = async (attachmentId: string) => {
    if (!selected) return;
    try {
      await api.deleteWikiAttachment(attachmentId);
      setSelected(await api.wikiDocument(selected.id));
    } catch (err) {
      setAttachmentNote(err instanceof Error ? err.message : "Falha ao remover anexo.");
    }
  };

  const grouped = useMemo(() => {
    return CATEGORIES.map((category) => ({
      ...category,
      docs: documents.filter((doc) => doc.category === category.id),
    }));
  }, [documents]);

  return (
    <section className="content-layout">
      <div className="content-main">
        <article className="surface">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ background: "var(--brand-accent)", color: "#111", padding: 12, borderRadius: 12 }}>
                <BookOpen size={24} />
              </div>
              <div>
                <h1 style={{ margin: 0, fontSize: "1.5rem" }}>Wiki EG</h1>
                <p style={{ margin: 0, color: "var(--text-muted)" }}>
                  Base de conhecimento interna, manuais e playbooks da EverGreen.
                </p>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button className="ghost-button" type="button" onClick={() => importInput.current?.click()} disabled={busy}>
                <Upload size={16} /> Importar .md
              </button>
              <button className="primary-button" type="button" onClick={() => startNew()} disabled={busy}>
                <Plus size={16} /> Novo documento
              </button>
              <input
                ref={importInput}
                type="file"
                accept=".md,.markdown,.txt,text/markdown,text/plain"
                style={{ display: "none" }}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) handleImport(file);
                  event.target.value = "";
                }}
              />
            </div>
          </div>
          {error && <p style={{ color: "var(--danger, #e5484d)", marginBottom: 0 }}>{error}</p>}
          {coreNote && <p style={{ color: "var(--text-muted)", marginBottom: 0, fontSize: "0.84rem" }}>{coreNote}</p>}
        </article>

        {loading && <EmptyState text="Carregando Wiki..." />}

        {!loading && grouped.map((group) => (
          <article className="surface" key={group.id}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <SectionHeader eyebrow="Categoria" title={group.label} />
              <button className="ghost-button" type="button" onClick={() => startNew(group.id)}>
                <Plus size={14} /> Adicionar
              </button>
            </div>
            {group.docs.length === 0 ? (
              <EmptyState text="Nenhum documento nesta categoria ainda." compact />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
                {group.docs.map((doc) => (
                  <button
                    key={doc.id}
                    type="button"
                    className="surface"
                    onClick={() => openDocument(doc.id)}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "10px 14px", cursor: "pointer", textAlign: "left",
                      borderColor: selected?.id === doc.id ? "var(--brand-accent)" : "var(--glass-border)",
                    }}
                  >
                    <span style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-main)", fontWeight: 500, fontSize: "0.88rem" }}>
                      {doc.title}
                    </span>
                    {doc.attachment_count > 0 && (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.78rem", display: "flex", alignItems: "center", gap: 4 }}>
                        <Paperclip size={13} /> {doc.attachment_count}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>

      <div className="content-sidebar">
        <article className="surface">
          {!selected && !editing ? (
            <EmptyState compact text="Selecione um documento ou crie um novo." />
          ) : (
            <>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
                <SectionHeader eyebrow={editing ? "Editando" : "Documento"} title={editing ? "" : selected?.title ?? "Novo"} icon={BookOpen} />
                <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                  {!editing && selected && (
                    <>
                      <button className="ghost-button" type="button" onClick={handleDownloadMd} title="Baixar documento em formato .md">
                        <Download size={14} /> .md
                      </button>
                      <button className="ghost-button" type="button" onClick={handleDownloadTxt} title="Baixar documento em formato .txt">
                        <Download size={14} /> .txt
                      </button>
                      <button className="ghost-button" type="button" onClick={handlePrintPdf} title="Imprimir ou Salvar em PDF">
                        <Printer size={14} /> PDF
                      </button>
                      <button className="ghost-button" type="button" onClick={() => setEditing(true)}>
                        Editar
                      </button>
                    </>
                  )}
                  {selected && (
                    <button className="icon-btn" type="button" onClick={handleDelete} aria-label="Excluir" disabled={busy}>
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>

              {editing ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <label>
                    Título
                    <input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} />
                  </label>
                  <label>
                    Categoria
                    <select value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value as WikiCategory })}>
                      {CATEGORIES.map((category) => (
                        <option key={category.id} value={category.id}>{category.label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Conteúdo (markdown)
                    <textarea
                      value={draft.content}
                      onChange={(event) => setDraft({ ...draft, content: event.target.value })}
                      rows={16}
                      style={{ fontFamily: "monospace", fontSize: "0.85rem", resize: "vertical" }}
                    />
                  </label>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="primary-button" type="button" onClick={handleSave} disabled={busy}>
                      <Save size={16} /> {busy ? "Salvando..." : "Salvar"}
                    </button>
                    <button
                      className="ghost-button"
                      type="button"
                      onClick={() => { setEditing(false); if (!selected) setDraft({ title: "", category: "geral", content: "" }); }}
                    >
                      <X size={16} /> Cancelar
                    </button>
                  </div>
                </div>
              ) : selected ? (
                <>
                  <div className="wiki-print-area">
                    <span style={{ fontSize: "0.74rem", color: "var(--brand-accent)", fontWeight: 700, textTransform: "uppercase" }}>
                      {CATEGORY_LABEL[selected.category]}
                    </span>
                    <div className="wiki-markdown" style={{ marginTop: 10, lineHeight: 1.6 }}>
                      {selected.content.trim() ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{selected.content}</ReactMarkdown>
                      ) : (
                        <EmptyState compact text="Documento sem conteúdo. Clique em Editar." />
                      )}
                    </div>
                  </div>
                  <div style={{ marginTop: 20, borderTop: "1px solid var(--glass-border)", paddingTop: 14 }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                      <strong style={{ fontSize: "0.85rem", display: "flex", alignItems: "center", gap: 6 }}>
                        <Paperclip size={14} /> Anexos
                      </strong>
                      <button className="ghost-button" type="button" onClick={() => attachInput.current?.click()} disabled={busy}>
                        <Upload size={14} /> Anexar
                      </button>
                      <input
                        ref={attachInput}
                        type="file"
                        style={{ display: "none" }}
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          if (file) handleAttach(file);
                          event.target.value = "";
                        }}
                      />
                    </div>
                    {attachmentNote && <p style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>{attachmentNote}</p>}
                    {selected.attachments.length === 0 ? (
                      <EmptyState compact text="Nenhum anexo." />
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        {selected.attachments.map((attachment) => (
                          <div key={attachment.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, fontSize: "0.82rem" }}>
                            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{attachment.file_name}</span>
                            <span style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
                              <span style={{ color: "var(--text-muted)" }}>{formatSize(attachment.size_bytes)}</span>
                              <button className="icon-btn" type="button" onClick={() => handleDownload(attachment.id)} aria-label="Baixar"><Download size={15} /></button>
                              <button className="icon-btn" type="button" onClick={() => handleDeleteAttachment(attachment.id)} aria-label="Remover"><Trash2 size={15} /></button>
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              ) : null}
            </>
          )}
        </article>
      </div>
    </section>
  );
}
