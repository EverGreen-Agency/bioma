import type { ClientSummary } from "./api";

export function isExternalClient(client: ClientSummary): boolean {
  return client.organization_slug !== "eg";
}

export function externalClients(clients: ClientSummary[]): ClientSummary[] {
  return clients.filter(isExternalClient);
}
