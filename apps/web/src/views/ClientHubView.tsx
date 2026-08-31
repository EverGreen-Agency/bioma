import React, { useState, useEffect } from "react";
import { useParams, useNavigate, useOutletContext } from "react-router-dom";
import { ClipboardCheck, CheckCircle2, AlertCircle, ArrowLeft, CalendarDays, Settings, Trash2, MessageSquarePlus, TrendingUp } from "lucide-react";
import { SectionHeader, EmptyState } from "../components/shared";
import { externalClients } from "../lib/client-scope";
import { AdminDock } from "../components/AdminDock";
import { EditorialCalendar } from "../components/EditorialCalendar";
import { RaioXScorePanel } from "../components/RaioXScorePanel";
import { useUiStore } from "../store/uiStore";
import {
  useClients,
  useClientPortal,
  useCommercialPortal,
  useCreateApproval,
  useCreateClientRequest,
  useDecideApproval,
  useDeleteDeliverable,
  useUpdateDeliverable,
  useCurrentUser,
  useUpdateClientRequest,
} from "../hooks/useBiomaApi";
import { deliverableStatusLabel } from "../lib/app-config";
import type { DeliverableStatus } from "../lib/api";
import type { ClientWorkspaceOutletContext } from "./ClientWorkspaceView";

export function ClientHubView() {
  const { id } = useParams<{ id: string }>();
  const { workspace } = useOutletContext<ClientWorkspaceOutletContext>();
  const contextId = workspace.workspaceId;
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [requestFormOpen, setRequestFormOpen] = useState(false);
  const [requestTitle, setRequestTitle] = useState("");
  const [requestDetail, setRequestDetail] = useState("");
  const [requestCategory, setRequestCategory] = useState<"request" | "question" | "change" | "input">("request");
  
  const { setSelectedClientId } = useUiStore();

  const { data: user, isLoading: loadingUser } = useCurrentUser();
  const isEgAdmin = !loadingUser && (user?.organizations.some((org: { role: string }) => org.role === "eg_admin") ?? false);

  const { data: clientsData } = useClients();
  const clients = externalClients(clientsData ?? []);
  const selectedClient = clients.find((c) => c.id === id) ?? null;

  const { data: portalData, isLoading: loadingPortal } = useClientPortal(contextId);
  const portal = portalData ?? null;
  const decideApproval = useDecideApproval();
  const createApproval = useCreateApproval();
  const createClientRequest = useCreateClientRequest();
  const updateClientRequest = useUpdateClientRequest();
  const updateDeliverable = useUpdateDeliverable();
  const deleteDeliverable = useDeleteDeliverable();
  const { data: commercialData, refetch: refetchCommercial } = useCommercialPortal(contextId);
  
  const isBusy =
    decideApproval.isPending ||
    createApproval.isPending ||
    updateDeliverable.isPending ||
    deleteDeliverable.isPending ||
    createClientRequest.isPending ||
    updateClientRequest.isPending;

  const submitRequest = (event: React.FormEvent) => {
    event.preventDefault();
    if (!requestTitle.trim()) return;
    createClientRequest.mutate(
      {
        clientId: contextId,
        title: requestTitle.trim(),
        detail: requestDetail.trim() || undefined,
        category: requestCategory,
      },
      {
        onSuccess: () => {
          setRequestTitle("");
          setRequestDetail("");
          setRequestCategory("request");
          setRequestFormOpen(false);
        },
      },
    );
  };

  useEffect(() => {
    if (id && useUiStore.getState().selectedClientId !== id) {
      setSelectedClientId(id);
    }
  }, [id, setSelectedClientId]);

  if (!selectedClient) {
    return (
      <section style={{ padding: '24px' }}>
        <EmptyState text="Cliente não encontrado." />
        <button className="primary-button" type="button" onClick={() => navigate('/clientes')} style={{ marginTop: '16px' }}>Voltar para a lista</button>
      </section>
    );
  }

  return (
    <section style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '24px 32px 0 32px' }}>
        <button 
          type="button"
          className="icon-button" 
          onClick={() => {
            setSelectedClientId(null);
            navigate("/");
          }}
        >
          <ArrowLeft size={18} />
        </button>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
          <SectionHeader eyebrow={selectedClient.organization_name} title="Seu workspace" icon={ClipboardCheck} />
          {isEgAdmin && (
            <button 
              className="secondary-button" 
              type="button" 
              onClick={() => setDrawerOpen(true)}
              style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Settings size={16} />
              Gerenciar Cliente
            </button>
          )}
        </div>
      </div>

      {loadingPortal && <EmptyState text="Carregando hub..." />}
      {!loadingPortal && portal && (
        <div style={{ padding: '24px 32px', flex: 1 }}>
          <div className="bento-grid">
            <article className="bento-card col-span-1">
              <div className="bento-header">
                <h3>Progresso das entregas</h3>
                <TrendingUp size={16} color="var(--brand-accent)" />
              </div>
              <div style={{ marginTop: "18px", display: "grid", gap: "10px" }}>
                <strong style={{ fontSize: "32px" }}>{portal.progress.completion_percentage}%</strong>
                <div style={{ height: "8px", borderRadius: "999px", background: "var(--surface-muted, #e8e8e8)", overflow: "hidden" }}>
                  <div style={{ width: `${portal.progress.completion_percentage}%`, height: "100%", background: "var(--brand-accent)", borderRadius: "inherit" }} />
                </div>
                <small>
                  {portal.progress.deliverables_done} concluídas · {portal.progress.deliverables_in_progress} em andamento · {portal.progress.deliverables_total} no total
                </small>
                <p>Responsável EG: <strong>{selectedClient.responsible_name ?? "a definir"}</strong></p>
              </div>
            </article>
            
            <article className="bento-card col-span-2">
              <div className="bento-header">
                <h3>O que precisa da sua atenção</h3>
                <CheckCircle2 size={16} color="var(--brand-accent)" />
              </div>
              {portal.attention.length === 0 && <EmptyState compact text="Tudo em dia. A equipe segue com o trabalho." />}
              {portal.attention.map((item) => {
                const approval = item.kind === "approval" ? portal.approvals.find((entry) => entry.id === item.entity_id) : null;
                return (
                <div className="work-row" key={`${item.kind}-${item.entity_id}`}>
                  <AlertCircle size={16} />
                  <div>
                    <strong>{item.title}</strong>
                    <small>{item.detail}</small>
                  </div>
                  {approval && (
                    <div className="row-actions">
                      <button className="mini-button approve" type="button" onClick={() => decideApproval.mutate({ clientId: contextId, approvalId: approval.id, status: "approved" })} disabled={isBusy}>Aprovar</button>
                      <button className="mini-button reject" type="button" onClick={() => decideApproval.mutate({ clientId: contextId, approvalId: approval.id, status: "rejected" })} disabled={isBusy}>Pedir ajustes</button>
                    </div>
                  )}
                </div>
              )})}
            </article>
          </div>

          <article className="surface" style={{ marginTop: "24px" }}>
            <div className="surface-header" style={{ justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <MessageSquarePlus size={18} />
                <div>
                  <h3>Solicitações à equipe</h3>
                  <small>Peça algo pelo resultado esperado. A EG faz a triagem interna.</small>
                </div>
              </div>
              <button className="primary-button" type="button" onClick={() => setRequestFormOpen((open) => !open)}>
                {requestFormOpen ? "Cancelar" : "Solicitar algo"}
              </button>
            </div>
            <div style={{ padding: "0 20px 20px" }}>
              {requestFormOpen && (
                <form onSubmit={submitRequest} style={{ display: "grid", gap: "10px", marginBottom: "18px", padding: "16px", border: "1px solid var(--border-subtle, #ddd)", borderRadius: "12px" }}>
                  <label>
                    Tipo
                    <select value={requestCategory} onChange={(event) => setRequestCategory(event.target.value as typeof requestCategory)}>
                      <option value="request">Nova solicitação</option>
                      <option value="question">Dúvida</option>
                      <option value="change">Pedido de ajuste</option>
                      <option value="input">Envio de informação</option>
                    </select>
                  </label>
                  <label>
                    O que você precisa?
                    <input value={requestTitle} onChange={(event) => setRequestTitle(event.target.value)} maxLength={300} placeholder="Ex.: atualizar os criativos da campanha de setembro" required />
                  </label>
                  <label>
                    Contexto e resultado esperado
                    <textarea value={requestDetail} onChange={(event) => setRequestDetail(event.target.value)} rows={4} maxLength={5000} placeholder="Conte o contexto, prazo desejado e como saberemos que ficou bom." />
                  </label>
                  <div><button className="primary-button" type="submit" disabled={isBusy || !requestTitle.trim()}>Enviar para triagem</button></div>
                </form>
              )}
              {portal.requests.length === 0 && <EmptyState compact text="Nenhuma solicitação enviada ainda." />}
              {portal.requests.map((request) => (
                <div className="work-row" key={request.id}>
                  <div>
                    <strong>{request.title}</strong>
                    <small>{request.detail || "Sem contexto adicional"}</small>
                    {request.resolution_summary && <small><strong>Retorno:</strong> {request.resolution_summary}</small>}
                  </div>
                  <div className="row-actions">
                    {isEgAdmin ? (
                      <select
                        value={request.status}
                        disabled={isBusy}
                        onChange={(event) => updateClientRequest.mutate({ clientId: contextId, requestId: request.id, status: event.target.value as typeof request.status })}
                      >
                        <option value="submitted">Recebida</option>
                        <option value="triaged">Em triagem</option>
                        <option value="in_progress">Em andamento</option>
                        <option value="waiting_client">Aguardando cliente</option>
                        <option value="done">Concluída</option>
                        <option value="declined">Não priorizada</option>
                      </select>
                    ) : (
                      <span className={`status-pill ${request.status}`}>{{
                        submitted: "Recebida", triaged: "Em triagem", in_progress: "Em andamento",
                        waiting_client: "Aguardando você", done: "Concluída", declined: "Não priorizada",
                      }[request.status]}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="surface" style={{ marginTop: "24px" }}>
            <div className="surface-header">
              <CalendarDays size={18} />
              <h3>Entregas da semana</h3>
            </div>
            <div style={{ padding: "0 20px 16px" }}>
              <EditorialCalendar deliverables={portal.deliverables} />
            </div>

            <div style={{ padding: "0 20px 20px" }}>
              {portal.deliverables.length === 0 && (
                <EmptyState compact text="Nenhuma entrega cadastrada para este cliente." />
              )}
              {portal.deliverables.map((deliverable) => {
                const awaitingApproval = portal.approvals.some(
                  (approval) => approval.status === "pending" && approval.deliverable_id === deliverable.id,
                );
                return (
                  <div className="work-row" key={deliverable.id}>
                    <div>
                      <strong>{deliverable.title}</strong>
                      <small>
                        {deliverableStatusLabel[deliverable.status]}
                        {deliverable.due_at
                          ? ` · vence ${new Date(deliverable.due_at).toLocaleDateString("pt-BR")}`
                          : " · sem prazo"}
                      </small>
                    </div>
                    {isEgAdmin && (
                      <div className="row-actions">
                        <select
                          value={deliverable.status}
                          disabled={isBusy}
                          onChange={(event) =>
                            updateDeliverable.mutate({
                              clientId: contextId,
                              deliverableId: deliverable.id,
                              payload: { status: event.target.value as DeliverableStatus },
                            })
                          }
                        >
                          {(Object.keys(deliverableStatusLabel) as DeliverableStatus[]).map((status) => (
                            <option key={status} value={status}>
                              {deliverableStatusLabel[status]}
                            </option>
                          ))}
                        </select>
                        {/* Uma entrega so pode ter uma aprovacao pendente por vez;
                            sem esse guard o cliente recebia pedidos duplicados. */}
                        <button
                          className="mini-button"
                          type="button"
                          disabled={isBusy || awaitingApproval}
                          title={awaitingApproval ? "Ja existe aprovacao pendente" : "Pedir aprovacao ao cliente"}
                          onClick={() =>
                            createApproval.mutate({ clientId: contextId, deliverableId: deliverable.id })
                          }
                        >
                          {awaitingApproval ? "Aguardando cliente" : "Pedir aprovação"}
                        </button>
                        <button
                          className="mini-button reject"
                          type="button"
                          disabled={isBusy}
                          onClick={() => {
                            if (!window.confirm(`Excluir a entrega "${deliverable.title}"?`)) return;
                            deleteDeliverable.mutate({ clientId: contextId, deliverableId: deliverable.id });
                          }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </article>

          <div style={{ marginTop: "24px" }}>
            <RaioXScorePanel
              workspaceId={contextId}
              data={commercialData ?? null}
              onUpdate={refetchCommercial}
              canEdit={isEgAdmin}
            />
          </div>


        </div>
      )}

      {selectedClient && (
        <AdminDock selectedClient={selectedClient} isOpen={drawerOpen} onClose={() => setDrawerOpen(false)} />
      )}
    </section>
  );
}
