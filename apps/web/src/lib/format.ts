import type { ArtifactPayload, ClientPayload, DeliverablePayload } from "./api";

export function normalizeClientPayload(payload: ClientPayload): ClientPayload {
  return {
    ...payload,
    name: payload.name.trim(),
    organization_name: normalizeOptional(payload.organization_name) ?? payload.name.trim(),
    responsible_name: normalizeOptional(payload.responsible_name),
  };
}

export function normalizeArtifactPayload(payload: ArtifactPayload): ArtifactPayload {
  return {
    ...payload,
    title: payload.title.trim(),
    kind: payload.kind.trim() || "briefing",
    content: normalizeOptional(payload.content),
    url: normalizeOptional(payload.url),
  };
}

export function normalizeDeliverablePayload(payload: DeliverablePayload): DeliverablePayload {
  return {
    ...payload,
    title: payload.title.trim(),
    due_at: normalizeOptional(payload.due_at),
  };
}

export function formatDueDate(value: string | null) {
  if (!value) return "Sem prazo";
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(new Date(value));
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function approvalStatusLabel(status: string) {
  const labels: Record<string, string> = {
    approved: "Aprovado",
    rejected: "Reprovado",
    cancelled: "Cancelado",
  };
  return labels[status] ?? status;
}

export function artifactKindLabel(kind: string) {
  const labels: Record<string, string> = {
    briefing: "Briefing",
    brand_book: "Brand book",
    calendar: "Calendário",
    integration_map: "Mapa de integração",
  };
  return labels[kind] ?? kind;
}

export function auditLabel(eventType: string) {
  const labels: Record<string, string> = {
    "auth.login": "Login",
    "client.created": "Cliente criado",
    "client.updated": "Cliente atualizado",
    "artifact.created": "Artefato criado",
    "artifact.updated": "Artefato atualizado",
    "artifact.deleted": "Artefato excluído",
    "deliverable.created": "Entrega criada",
    "deliverable.updated": "Entrega atualizada",
    "deliverable.deleted": "Entrega excluída",
    "approval.decided": "Aprovação decidida",
  };
  return labels[eventType] ?? eventType;
}

export function compactMetadata(metadata: Record<string, unknown>) {
  const keys = Object.keys(metadata);
  if (keys.length === 0) return "sem metadados";
  return keys
    .slice(0, 3)
    .map((key) => `${key}: ${String(metadata[key])}`)
    .join(" · ");
}

export type ContentSection = {
  title: string;
  lines: string[];
};

/**
 * Divide o conteúdo textual de um artefato (briefing, brand book) em seções
 * usando headings markdown (#, ##, ###) ou linhas inteiras em negrito como título.
 */
export function parseContentSections(content: string): ContentSection[] {
  const sections: ContentSection[] = [];
  let current: ContentSection | null = null;

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    const heading = line.match(/^#{1,4}\s+(.+?)\s*$/) ?? line.match(/^\*\*(.+?)\*\*:?\s*$/);
    if (heading) {
      current = { title: heading[1].trim(), lines: [] };
      sections.push(current);
      continue;
    }
    if (!line) continue;
    if (!current) {
      current = { title: "", lines: [] };
      sections.push(current);
    }
    current.lines.push(line);
  }

  return sections;
}

export function isSessionError(error: Error) {
  const message = error.message.toLowerCase();
  return message.includes("sessão ausente") || message.includes("sessão inválida");
}

function normalizeOptional(value: string | null | undefined) {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}
