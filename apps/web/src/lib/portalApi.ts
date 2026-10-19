// Cliente dos portais sem login (/portal/<slug>). Não usa a sessão do Bioma:
// o painel é público e a operação EG vai com a chave do portal no cabeçalho.

import type { KommoDashboardResponse } from "./api";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
const KEY_STORAGE = "bioma_portal_key";

export class PortalError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/** Lê a chave de `?k=` uma única vez, guarda na sessão do navegador e limpa a URL. */
export function capturePortalKey(): string {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = params.get("k");
  if (fromUrl) {
    sessionStorage.setItem(KEY_STORAGE, fromUrl);
    params.delete("k");
    const query = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
  }
  return sessionStorage.getItem(KEY_STORAGE) ?? "";
}

export function savePortalKey(key: string) {
  sessionStorage.setItem(KEY_STORAGE, key.trim());
}

export function clearPortalKey() {
  sessionStorage.removeItem(KEY_STORAGE);
}

async function portalRequest<T>(path: string, init: { method?: string; body?: unknown; key?: string } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  if (init.key) headers.Authorization = `Portal ${init.key}`;
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: init.method ?? "GET",
    headers,
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  if (!response.ok) {
    let detail = `Erro ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string") detail = payload.detail;
    } catch {
      // resposta sem corpo JSON: mantém a mensagem genérica
    }
    throw new PortalError(detail, response.status);
  }
  return (await response.json()) as T;
}

export type EgStatus = {
  organization: string;
  kommo: { configured: boolean; subdomain: string | null; leads_count: number | null; fetched_at: string | null };
  dedup: {
    id: string;
    contacts_scanned: number;
    clusters_count: number;
    duplicates_count: number;
    leads_to_reassign: number;
    clusters_applied: number;
    created_at: string;
  } | null;
  classification: {
    total: number;
    simulated: number;
    classified: number;
    without_conversation: number;
    errors: number;
    fields_written: number;
    last_at: string | null;
    engine: "modelo" | "regras";
    label: string;
  };
  webhook: { active: boolean; events?: string[]; events_received?: number; last_event_at?: string | null };
};

export type EgDedupCluster = {
  cluster_id: string;
  state: "pendente" | "unificado" | "erro";
  error: string | null;
  match_kind: string;
  master_contact_id: number;
  master_name: string;
  duplicate_contacts: { id: number; name: string | null; leads_count: number }[];
  leads_to_reassign: number;
};

export type EgDedupDetail = {
  run: { id: string; subdomain: string; contacts_scanned: number; duplicates_count: number; created_at: string };
  progress: { total: number; unified: number; errors: number; pending: number };
  total_clusters: number;
  page: number;
  page_size: number;
  clusters: EgDedupCluster[];
};

export type EgApplyProgress = {
  processed: number;
  leads_moved: number;
  errors: string[];
  unified: number;
  pending: number;
  total: number;
};

export type EgClassifyProgress = {
  processed: number;
  classified: number;
  fields_written: number;
  remaining: number;
  total: number;
};

export type EgClassificationField = {
  key: string;
  label: string;
  values: string[];
  confidence: number;
  source: "modelo" | "regra" | "ddd" | "texto";
  already_filled: boolean;
  written: boolean;
  status?: "sugerido" | "gravado" | "mantido";
};

export type EgClassificationResults = {
  subdomain: string | null;
  summary: EgStatus["classification"] & {
    suggested?: number;
    written_leads?: number;
    waiting_customer?: number;
  };
  page: number;
  page_size: number;
  results: {
    lead_id: number;
    status: "classificado" | "sugerido" | "gravado" | "aguardando_cliente" | "sem_conversa" | "sem_sinal" | "erro";
    engine: string;
    trigger: "historico" | "webhook" | "simulacao";
    messages_count: number;
    fields_written: number;
    error: string | null;
    classified_at: string;
    fields: EgClassificationField[];
  }[];
};

export type EgClassifyTestResult = {
  status: "classificado" | "sem_sinal";
  engine: "modelo" | "regras";
  model_name: string;
  latency_ms: number | null;
  model_error: string | null;
  text: string;
  phone: string | null;
  fields: {
    key: string;
    label: string;
    values: string[];
    confidence: number;
    source: "modelo" | "regra" | "ddd";
  }[];
  raw_answers?: Record<string, { choice: string; confidence: number }>;
};

export const portalApi = {
  dashboard: (slug: string, days: number) =>
    portalRequest<KommoDashboardResponse>(`/portal-api/${slug}/kommo/dashboard?days=${days}`),

  status: (slug: string, key: string) => portalRequest<EgStatus>(`/portal-api/${slug}/eg/status`, { key }),
  connect: (slug: string, key: string, subdomain: string, accessToken: string) =>
    portalRequest<{ status: string; account_name: string | null }>(`/portal-api/${slug}/eg/kommo/connect`, {
      method: "POST",
      key,
      body: { subdomain, access_token: accessToken },
    }),
  sync: (slug: string, key: string) =>
    portalRequest<KommoDashboardResponse>(`/portal-api/${slug}/eg/kommo/sync`, { method: "POST", key }),

  dedupSimulate: (slug: string, key: string) =>
    portalRequest<{ id: string }>(`/portal-api/${slug}/eg/dedup/runs`, { method: "POST", key }),
  dedupDetail: (slug: string, key: string, runId: string, page: number, onlyPending: boolean) =>
    portalRequest<EgDedupDetail>(
      `/portal-api/${slug}/eg/dedup/runs/${runId}?page=${page}&page_size=15&only_pending=${onlyPending}`,
      { key },
    ),
  dedupApply: (slug: string, key: string, runId: string, limit: number) =>
    portalRequest<EgApplyProgress>(`/portal-api/${slug}/eg/dedup/runs/${runId}/apply`, { method: "POST", key, body: { limit } }),

  classifyBatch: (slug: string, key: string, limit: number, write: boolean) =>
    portalRequest<EgClassifyProgress>(`/portal-api/${slug}/eg/classification/batch`, {
      method: "POST",
      key,
      body: { limit, write },
    }),
  classificationResults: (slug: string, key: string, page: number) =>
    portalRequest<EgClassificationResults>(`/portal-api/${slug}/eg/classification/results?page=${page}&page_size=15`, { key }),

  classificationReset: (slug: string, key: string) =>
    portalRequest<{ status: string; deleted: number }>(`/portal-api/${slug}/eg/classification/reset`, { method: "POST", key }),


  applyClassificationLead: (slug: string, key: string, leadId: number) =>
    portalRequest<{ status: string; lead_id: number; fields_written: number; fields: Record<string, EgClassificationField> }>(
      `/portal-api/${slug}/eg/classification/leads/${leadId}/apply`,
      { method: "POST", key },
    ),

  applyClassificationBatch: (slug: string, key: string, limit: number) =>
    portalRequest<{ processed: number; fields_written: number; remaining: number }>(
      `/portal-api/${slug}/eg/classification/apply-batch`,
      { method: "POST", key, body: { limit } },
    ),

  classifyTest: (slug: string, key: string, text: string, phone?: string) =>
    portalRequest<EgClassifyTestResult>(`/portal-api/${slug}/eg/classification/test`, {
      method: "POST",
      key,
      body: { text, phone: phone || undefined },
    }),

  enableWebhook: (slug: string, key: string) =>
    portalRequest<{ active: boolean; events: string[] }>(`/portal-api/${slug}/eg/webhook`, { method: "POST", key }),
};
