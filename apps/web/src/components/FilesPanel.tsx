import { FormEvent, useEffect, useState } from "react";
import { Download, FileText, Trash2, Upload } from "lucide-react";
import { EmptyState, SectionHeader } from "./shared";
import { api, type ClientFileSummary, type ClientFileVisibility } from "../lib/api";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

export function FilesPanel({
  clientId,
  isEgAdmin,
}: {
  clientId: string | null;
  isEgAdmin: boolean;
}) {
  const [files, setFiles] = useState<ClientFileSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [visibility, setVisibility] = useState<ClientFileVisibility>("client");

  useEffect(() => {
    if (!clientId) {
      setFiles([]);
      return;
    }
    setLoading(true);
    setError("");
    api
      .listFiles(clientId)
      .then(setFiles)
      .catch((err: Error) => setError(err.message || "Não foi possível carregar os arquivos."))
      .finally(() => setLoading(false));
  }, [clientId]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!clientId) return;
    const form = event.currentTarget;
    const input = form.elements.namedItem("file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    setBusy("upload");
    setError("");
    try {
      setFiles(await api.uploadFile(clientId, file, visibility));
      form.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível enviar o arquivo.");
    } finally {
      setBusy("");
    }
  }

  async function handleDownload(file: ClientFileSummary) {
    if (!clientId) return;
    setBusy(`download:${file.id}`);
    setError("");
    try {
      const { url } = await api.fileDownloadUrl(clientId, file.id);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível gerar o link de download.");
    } finally {
      setBusy("");
    }
  }

  async function handleDelete(file: ClientFileSummary) {
    if (!clientId) return;
    setBusy(`delete:${file.id}`);
    setError("");
    try {
      setFiles(await api.deleteFile(clientId, file.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível excluir o arquivo.");
    } finally {
      setBusy("");
    }
  }

  if (!clientId) return null;

  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  return (
    <article className="surface section-card files-panel">
      <SectionHeader eyebrow="Documentos" title="Arquivos do cliente" icon={FileText} />

      {error && <div className="notice error mt-2">{error}</div>}

      {loading ? (
        <EmptyState text="Carregando arquivos..." />
      ) : files.length === 0 ? (
        <EmptyState text="Nenhum arquivo enviado para este cliente." />
      ) : (
        <div className="files-list mt-2">
          {files.map((file) => (
            <div className="file-row" key={file.id}>
              <div className="file-row-main">
                <FileText size={18} />
                <div>
                  <strong>{file.file_name}</strong>
                  <span>
                    {formatBytes(file.size_bytes)} · {file.visibility === "client" ? "Visível ao cliente" : "Somente EG"}
                  </span>
                </div>
              </div>
              <div className="file-row-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => handleDownload(file)}
                  disabled={busy === `download:${file.id}`}
                >
                  <Download size={15} />
                  Baixar
                </button>
                {isEgAdmin && (
                  <button
                    className="icon-button danger"
                    type="button"
                    onClick={() => handleDelete(file)}
                    disabled={busy === `delete:${file.id}`}
                    title="Excluir arquivo"
                  >
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {isEgAdmin && (
        <form className="files-upload-form mt-3" onSubmit={handleUpload}>
          <label style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
            <span style={{ fontSize: 12, color: "var(--text-dim)", fontWeight: 500 }}>Arquivo</span>
            <label 
              style={{ 
                display: "flex", 
                alignItems: "center", 
                gap: 8, 
                background: "var(--bg-inset)", 
                padding: "8px 12px", 
                borderRadius: 6, 
                border: "1px dashed var(--border)", 
                cursor: "pointer",
                height: 38
              }}
            >
              <Upload size={16} style={{ color: "var(--brand-accent)" }} />
              <span style={{ fontSize: 13, color: selectedFileName ? "var(--text)" : "var(--text-dim)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {selectedFileName || "Escolher arquivo..."}
              </span>
              <input 
                type="file" 
                name="file" 
                required 
                style={{ display: "none" }}
                onChange={(e) => setSelectedFileName(e.target.files?.[0]?.name || null)}
              />
            </label>
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, color: "var(--text-dim)", fontWeight: 500 }}>Visibilidade</span>
            <select className="text-input" style={{ height: 38 }} value={visibility} onChange={(event) => setVisibility(event.target.value as ClientFileVisibility)}>
              <option value="client">Visível ao cliente</option>
              <option value="internal">Somente EG</option>
            </select>
          </label>
          <button className="primary-button" type="submit" disabled={busy === "upload"} style={{ alignSelf: "flex-end", height: 38 }}>
            <Upload size={16} />
            Enviar arquivo
          </button>
        </form>
      )}
    </article>
  );
}
