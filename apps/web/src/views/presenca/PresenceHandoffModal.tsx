import { useState } from "react";
import { CHANNEL_LABELS, STAGES, type Assignee } from "./types";
import type { EditorialCalendarItemSummary as Item, WorkspaceSummary } from "../../lib/api";

interface PresenceHandoffModalProps {
  item: Item;
  workspace: WorkspaceSummary;
  onClose: () => void;
}

export function PresenceHandoffModal({ item, workspace, onClose }: PresenceHandoffModalProps) {
  const [copied, setCopied] = useState(false);

  const assignee = item.metadata?.assigned_to as Assignee | null | undefined;
  const campaignTags = Array.isArray(item.metadata?.campaign_tags)
    ? (item.metadata.campaign_tags as string[])
    : [];

  const scheduledDate = item.scheduled_at ? new Date(item.scheduled_at) : null;
  const formattedSchedule = scheduledDate
    ? scheduledDate.toLocaleString("pt-BR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Data/hora a definir";

  // Build ready copy with hashtags
  const hashtagsFormatted = campaignTags.map((tag) => `#${tag.replace(/^#/, "")}`).join(" ");
  const readyCopy = [
    item.post_text ?? "",
    hashtagsFormatted ? `\n\n${hashtagsFormatted}` : "",
  ]
    .join("")
    .trim();

  async function handleCopyText() {
    try {
      await navigator.clipboard.writeText(readyCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Fallback if clipboard API fails
      const textarea = document.createElement("textarea");
      textarea.value = readyCopy;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  }

  function handleDownloadText() {
    const lines = [
      `=============================================================`,
      `EVERGREEN PRESENÇA · PACOTE DE PUBLICAÇÃO MANUAL (HANDOFF)`,
      `=============================================================`,
      `Workspace: ${workspace.name} (${workspace.slug})`,
      `Peça: ${item.title}`,
      `Canal de Destino: ${CHANNEL_LABELS[item.channel]}`,
      `Formato: ${item.content_type}`,
      `Etapa Atual: ${STAGES[item.stage]}`,
      `Horário Programado: ${formattedSchedule}`,
      `Responsável: ${assignee?.name ?? "Não atribuído"}`,
      `Tags de Campanha: ${campaignTags.length ? campaignTags.join(", ") : "Nenhuma"}`,
      `-------------------------------------------------------------`,
      `TEXTO / LEGENDA FINAL:`,
      `-------------------------------------------------------------`,
      readyCopy || "(Nenhum texto informado)",
      ``,
      `-------------------------------------------------------------`,
      `ANEXOS E MÍDIAS:`,
      `-------------------------------------------------------------`,
      item.media_urls.length
        ? item.media_urls.map((url, i) => `[${i + 1}] ${url}`).join("\n")
        : "Nenhuma mídia externa vinculada.",
      ``,
      `-------------------------------------------------------------`,
      `CHECKLIST OPERACIONAL DO SOCIAL MEDIA:`,
      `[ ] Abrir plataforma nativa (${CHANNEL_LABELS[item.channel]})`,
      `[ ] Colar a legenda formatada com hashtags`,
      `[ ] Fazer upload das mídias correspondentes`,
      `[ ] Programar para o horário: ${formattedSchedule}`,
      `[ ] Confirmar na esteira do Bioma após conclusão`,
      `-------------------------------------------------------------`,
      `Arquivo gerado automaticamente pelo Bioma EverGreen em ${new Date().toLocaleString("pt-BR")}.`,
    ].join("\n");

    const blob = new Blob([lines], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `handoff-${workspace.slug || "eg"}-${item.id.slice(0, 8)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function handleDownloadJson() {
    const payload = {
      package_type: "evergreen_social_handoff",
      generated_at: new Date().toISOString(),
      workspace: {
        id: workspace.id,
        name: workspace.name,
        slug: workspace.slug,
      },
      item: {
        id: item.id,
        title: item.title,
        channel: item.channel,
        content_type: item.content_type,
        stage: item.stage,
        scheduled_at: item.scheduled_at,
        post_text: item.post_text,
        media_urls: item.media_urls,
        metadata: item.metadata,
      },
      handoff: {
        copy_ready: readyCopy,
        hashtags: campaignTags,
        assignee: assignee ?? null,
        scheduled_display: formattedSchedule,
      },
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `handoff-${workspace.slug || "eg"}-${item.id.slice(0, 8)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="presence-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="presence-handoff-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="presence-handoff-head">
          <div>
            <span className="presence-eyebrow">PACOTE DE OPERAÇÃO SOCIAL</span>
            <h2>Exportação & Handoff</h2>
            <p>Pacote estruturado para publicação manual ou agendamento assistido.</p>
          </div>
          <button type="button" className="presence-close-btn" onClick={onClose} aria-label="Fechar">
            ×
          </button>
        </div>

        <div className="presence-handoff-body">
          <div className="presence-handoff-summary-card">
            <div className="presence-handoff-row">
              <span className="presence-label-muted">Peça:</span>
              <strong>{item.title}</strong>
            </div>
            <div className="presence-handoff-row">
              <span className="presence-label-muted">Canal / Formato:</span>
              <span>
                {CHANNEL_LABELS[item.channel]} · {item.content_type}
              </span>
            </div>
            <div className="presence-handoff-row">
              <span className="presence-label-muted">Data Programada:</span>
              <strong className="presence-highlight-text">{formattedSchedule}</strong>
            </div>
            {assignee && (
              <div className="presence-handoff-row">
                <span className="presence-label-muted">Responsável:</span>
                <span>{assignee.name}</span>
              </div>
            )}
          </div>

          <div className="presence-handoff-copy-preview">
            <div className="presence-copy-header">
              <label htmlFor="presence-handoff-textarea">Texto Final Pronto para Publicação</label>
              <button
                type="button"
                className={`presence-btn-copy ${copied ? "copied" : ""}`}
                onClick={handleCopyText}
              >
                {copied ? "✓ Copiado!" : "📋 Copiar Legenda + Hashtags"}
              </button>
            </div>
            <textarea
              id="presence-handoff-textarea"
              readOnly
              rows={6}
              value={readyCopy}
              className="presence-readonly-textarea"
            />
          </div>

          <div className="presence-handoff-checklist">
            <h4>Checklist de Entrega</h4>
            <ul>
              <li className={item.post_text ? "checked" : "pending"}>
                {item.post_text ? "✓" : "○"} Texto revisado e adaptado ao canal
              </li>
              <li className={campaignTags.length ? "checked" : "pending"}>
                {campaignTags.length ? "✓" : "○"} Tags de campanha inseridas ({campaignTags.length} tags)
              </li>
              <li className={item.scheduled_at ? "checked" : "pending"}>
                {item.scheduled_at ? "✓" : "○"} Data e horário definidos no fuso local
              </li>
              <li className={item.media_urls.length ? "checked" : "pending"}>
                {item.media_urls.length ? "✓" : "○"} Mídias anexadas ({item.media_urls.length} arquivos)
              </li>
            </ul>
          </div>
        </div>

        <div className="presence-handoff-footer">
          <div className="presence-handoff-downloads">
            <button type="button" className="presence-btn-download" onClick={handleDownloadText}>
              ⬇ Baixar Pacote (.txt / .md)
            </button>
            <button type="button" className="presence-btn-subtle" onClick={handleDownloadJson}>
              ⬇ Manifesto (.json)
            </button>
          </div>
          <button type="button" className="presence-btn-secondary" onClick={onClose}>
            Concluir
          </button>
        </div>
      </div>
    </div>
  );
}
