import { useState, useEffect } from "react";
import { useAdminIdeaDoc, useSaveAdminIdeaDoc } from "../../../hooks/useBiomaApi";

const DOC_FALLBACK = "Este documento ainda não foi gerado pelo Curador.\n\nA ideia possui apenas o rascunho (descrição).";

export function IdeaDocModal({ id, title, onClose }: { id: string; title: string; onClose: () => void }) {
  const { data, isLoading, isError } = useAdminIdeaDoc(id);
  const saveDoc = useSaveAdminIdeaDoc();
  
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");

  const doc = isLoading ? "Carregando documento..." : isError ? DOC_FALLBACK : (data ?? DOC_FALLBACK);

  useEffect(() => {
    if (data && !isEditing) {
      setEditContent(data);
    }
  }, [data, isEditing]);

  const handleSave = () => {
    saveDoc.mutate({ id, content: editContent }, {
      onSuccess: () => {
        setIsEditing(false);
      }
    });
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
        background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 999, padding: 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--bg-primary)",
          border: "1px solid var(--border)",
          borderRadius: 8, width: 600, maxWidth: "100%", maxHeight: "90vh",
          display: "flex", flexDirection: "column",
          boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
        }}
      >
        <div style={{ padding: "12px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontWeight: 600, fontSize: 14 }}>{title}</span>
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            {!isEditing ? (
              <button onClick={() => { setEditContent(doc); setIsEditing(true); }} style={{ background: "var(--accent, #0070f3)", color: "white", border: "none", padding: "4px 12px", borderRadius: "4px", cursor: "pointer", fontSize: 12 }}>Editar</button>
            ) : (
              <>
                <button onClick={() => setIsEditing(false)} style={{ background: "transparent", color: "var(--text-secondary)", border: "1px solid var(--border)", padding: "4px 12px", borderRadius: "4px", cursor: "pointer", fontSize: 12 }}>Cancelar</button>
                <button onClick={handleSave} disabled={saveDoc.isPending} style={{ background: "var(--mint, #10b981)", color: "white", border: "none", padding: "4px 12px", borderRadius: "4px", cursor: "pointer", fontSize: 12 }}>{saveDoc.isPending ? "Salvando..." : "Salvar"}</button>
              </>
            )}
            <button onClick={onClose} style={{ background: "transparent", border: "none", color: "var(--text-secondary)", cursor: "pointer", fontSize: 16 }}>×</button>
          </div>
        </div>
        <div style={{ padding: 24, overflowY: "auto", flex: 1 }}>
          {isEditing ? (
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              style={{ width: "100%", height: "400px", minHeight: "300px", padding: "12px", background: "var(--bg-secondary)", color: "var(--text-primary)", border: "1px solid var(--border)", borderRadius: "4px", fontFamily: "monospace", fontSize: "13px", resize: "vertical" }}
            />
          ) : (
            <MarkdownViewer text={doc} />
          )}
        </div>
      </div>
    </div>
  );
}
function MarkdownViewer({ text }: { text: string }) {
  // Parser regex simples para markdown básico (o texto vem escapado antes).
  let html = text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^### (.*$)/gim, '<h3 style="margin-top:20px;margin-bottom:8px;font-size:14px;color:var(--text-primary);">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 style="margin-top:24px;margin-bottom:12px;font-size:16px;color:var(--text-primary); border-bottom:1px solid var(--border); padding-bottom:4px;">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 style="margin-top:0px;margin-bottom:16px;font-size:20px;color:#00d4ff;">$1</h1>')
    .replace(/\*\*(.*?)\*\*/gim, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/gim, "<em>$1</em>")
    .replace(/`(.*?)`/gim, '<code style="background:var(--bg-secondary);padding:2px 4px;border-radius:4px;font-family:monospace;font-size:12px;">$1</code>')
    .replace(/^&gt; (.*$)/gim, '<blockquote style="border-left:3px solid #ffab00;margin:10px 0;padding-left:10px;color:var(--text-secondary);">$1</blockquote>')
    .replace(/\n\n/gim, '</p><p style="margin-bottom:12px;line-height:1.6;font-size:13px;color:var(--text-secondary);">')
    .replace(/\n/gim, "<br />");

  html = `<p style="margin-bottom:12px;line-height:1.6;font-size:13px;color:var(--text-secondary);">${html}</p>`;

  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
