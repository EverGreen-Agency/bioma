import type { EditorialCalendarItemSummary as Item } from "../../lib/api";

export type CalendarView = "month" | "week" | "list";

export type Assignee = {
  id: string;
  name: string;
  email?: string | null;
  role?: string | null;
};

export type Draft = {
  title: string;
  content_type: Item["content_type"];
  channel: Item["channel"];
  scheduled_at: string | null;
  post_text: string;
  media_urls: string[];
  metadata: {
    assigned_to?: Assignee | null;
    campaign_tags?: string[];
    source_type?: string;
    ai_content_request_id?: string;
    output_index?: number;
    generation_mode?: string;
    provider?: string;
    model?: string;
    [key: string]: unknown;
  };
};

export const CHANNELS: Item["channel"][] = [
  "instagram",
  "facebook",
  "linkedin",
  "youtube",
  "tiktok",
  "blog",
];

export const CHANNEL_LABELS: Record<Item["channel"], string> = {
  instagram: "Instagram",
  facebook: "Facebook",
  linkedin: "LinkedIn",
  youtube: "YouTube",
  tiktok: "TikTok",
  blog: "Blog / Artigo",
};

export const STAGES: Record<Item["stage"], string> = {
  ideation: "Ideia",
  production: "Produção",
  review: "Revisão",
  approved: "Aprovado",
  scheduled: "Agendado",
  published: "Publicado",
};

export const STAGE_DESCRIPTIONS: Record<Item["stage"], string> = {
  ideation: "Conceito inicial ou rascunho importado",
  production: "Criação de cópia, design e ativos de mídia",
  review: "Validação interna de qualidade e tom de voz",
  approved: "Aprovado pelo cliente ou gestor responsável",
  scheduled: "Programado para distribuição nos canais",
  published: "Publicado externamente",
};

export const NEXT_TRANSITION: Partial<Record<Item["stage"], { stage: Item["stage"]; label: string; action: string }>> = {
  ideation: { stage: "production", label: "Iniciar produção", action: "start_production" },
  production: { stage: "review", label: "Enviar para revisão", action: "send_review" },
  review: { stage: "approved", label: "Aprovar peça", action: "approve" },
  approved: { stage: "scheduled", label: "Confirmar agendamento", action: "schedule" },
};

export type ListSortOption = "scheduled_asc" | "scheduled_desc" | "created_desc" | "title_asc";

export function dayKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function localInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return `${dayKey(d)}T${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function emptyDraft(): Draft {
  return {
    title: "",
    content_type: "social_post",
    channel: "instagram",
    scheduled_at: null,
    post_text: "",
    media_urls: [],
    metadata: {
      assigned_to: null,
      campaign_tags: [],
    },
  };
}
