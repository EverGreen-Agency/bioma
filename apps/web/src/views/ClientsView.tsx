import { useState } from "react";
import { Users, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { SectionHeader, EmptyState } from "../components/shared";
import { statusLabel } from "../lib/app-config";
import { externalClients } from "../lib/client-scope";
import { NewClientWizard } from "../components/NewClientWizard";
import { useClients, useCurrentUser } from "../hooks/useBiomaApi";

export function ClientsView() {
  const navigate = useNavigate();
  const [showNewClientModal, setShowNewClientModal] = useState(false);

  const { data: user, isLoading: loadingUser } = useCurrentUser();
  const isEgAdmin = !loadingUser && (user?.organizations.some((org: { role: string }) => org.role === "eg_admin") ?? false);

  const { data: clientsData, isLoading: loadingClients } = useClients();
  const clients = externalClients(clientsData ?? []);

  return (
    <section style={{ padding: '32px', width: '100%' }}>
        <div style={{ marginBottom: '28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <SectionHeader eyebrow="Client Hub" title="Carteira" icon={Users} />
          {isEgAdmin && (
            <button className="primary-button" onClick={() => setShowNewClientModal(true)}>
              <Plus size={16} /> Novo Cliente
            </button>
          )}
        </div>
        {loadingClients && <EmptyState text="Carregando clientes..." />}
        {!loadingClients && clients.length === 0 && <EmptyState text="Nenhum cliente disponível para esta sessão." />}
        <div className="bento-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))' }}>
          {clients.map((client) => (
            <button
              className="client-card"
              key={client.id}
              type="button"
              onClick={() => navigate(`/clientes/${client.id}`)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', width: '100%', marginBottom: '8px' }}>
                <strong style={{ fontSize: '1.05rem', lineHeight: 1.3 }}>{client.name}</strong>
                <span className={`status-pill ${client.status}`}>{statusLabel[client.status]}</span>
              </div>
              <small style={{ display: 'block', textAlign: 'left', marginBottom: '16px', color: 'var(--text-muted)' }}>
                Responsável: {client.responsible_name ?? "Sem responsável"}
              </small>
              <div className="client-card-meta" style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', opacity: 0.8 }}>
                <span>{client.deliverables_total} entregas</span>
                <span>{client.approvals_pending} aprovações</span>
                <span>{client.artifacts_client} artefatos</span>
              </div>
            </button>
          ))}
        </div>

        {showNewClientModal && <NewClientWizard onClose={() => setShowNewClientModal(false)} />}
    </section>
  );
}
