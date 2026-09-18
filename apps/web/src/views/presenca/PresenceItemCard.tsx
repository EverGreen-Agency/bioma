import { CHANNEL_LABELS, STAGES, type Assignee } from "./types";
import type { EditorialCalendarItemSummary as Item } from "../../lib/api";

interface PresenceItemCardProps {
  item: Item;
  onSelect: (item: Item) => void;
  compact?: boolean;
}

export function PresenceItemCard({ item, onSelect, compact = false }: PresenceItemCardProps) {
  const assignee = (item.metadata?.assigned_to as Assignee | null | undefined);
  const campaignTags = Array.isArray(item.metadata?.campaign_tags)
    ? (item.metadata.campaign_tags as string[])
    : [];

  const timeLabel = item.scheduled_at
    ? new Date(item.scheduled_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    : null;

  const initials = assignee?.name
    ? assignee.name
        .split(" ")
        .slice(0, 2)
        .map((p) => p[0]?.toUpperCase() ?? "")
        .join("")
    : null;

  return (
    <button
      type="button"
      className={`presence-item-card ${compact ? "compact" : ""}`}
      onClick={() => onSelect(item)}
      aria-label={`Peça: ${item.title}. Canal: ${item.channel}. Etapa: ${STAGES[item.stage]}`}
    >
      <div className="presence-card-top">
        <span className={`presence-stage-badge presence-stage-${item.stage}`}>
          {STAGES[item.stage]}
        </span>
        <span className="presence-channel-pill" title={`Canal: ${CHANNEL_LABELS[item.channel]}`}>
          {item.channel}
        </span>
      </div>

      <strong className="presence-card-title" title={item.title}>
        {item.title}
      </strong>

      {item.post_text && !compact && (
        <p className="presence-card-excerpt">
          {item.post_text.slice(0, 75)}
          {item.post_text.length > 75 ? "…" : ""}
        </p>
      )}

      {campaignTags.length > 0 && (
        <div className="presence-card-tags">
          {campaignTags.slice(0, 2).map((tag) => (
            <span key={tag} className="presence-tag-chip">
              #{tag}
            </span>
          ))}
          {campaignTags.length > 2 && (
            <span className="presence-tag-chip more">+{campaignTags.length - 2}</span>
          )}
        </div>
      )}

      <div className="presence-card-meta">
        <span className="presence-time-tag">
          {timeLabel ? `⏰ ${timeLabel}` : "Sem horário"}
        </span>

        <div className="presence-card-indicators">
          {item.media_urls?.length > 0 && (
            <span className="presence-media-indicator" title={`${item.media_urls.length} mídia(s) anexada(s)`}>
              🖼️ {item.media_urls.length}
            </span>
          )}

          {assignee && (
            <span
              className="presence-assignee-avatar"
              title={`Responsável: ${assignee.name}${assignee.role ? ` (${assignee.role})` : ""}`}
            >
              {initials ?? "U"}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
