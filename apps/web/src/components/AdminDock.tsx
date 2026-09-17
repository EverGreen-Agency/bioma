import { FormEvent, useEffect, useState } from "react";
import { Archive, Save, Settings, UserPlus, X, Trash2 } from "lucide-react";
import { DockTitle } from "./shared";
import { statusLabel, moduleLabels, toggleableModules } from "../lib/app-config";
import { useUiStore } from "../store/uiStore";
import { useArchiveClient, useUpdateClient, useCreateInvite } from "../hooks/useBiomaApi";
import { api } from "../lib/api";
import type { ClientModule, ClientStatus, ClientSummary } from "../lib/api";

export function AdminDock({ selectedClient, isOpen, onClose }: { selectedClient: ClientSummary | null, isOpen: boolean, onClose: () => void }) {
  const {
    selectedClientId,
    actionBusy,
    clientDraft,
    setClientDraft,
  } = useUiStore();

  const updateClient = useUpdateClient();
  const archiveClient = useArchiveClient();
  const createInvite = useCreateInvite();

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteLink, setInviteLink] = useState("");
  const [inviteCopied, setInviteCopied] = useState(false);

  const [resetEmail, setResetEmail] = useState("");
  const [resetLink, setResetLink] = useState("");
  const [resetCopied, setResetCopied] = useState(false);
  const [resetError, setResetError] = useState("");
  const [resetBusy, setResetBusy] = useState(false);

  useEffect(() => {
    setInviteLink("");
    setInviteCopied(false);
    if (!selectedClient) return;
    setClientDraft({
      name: selectedClient.name,
      organization_name: selectedClient.organization_name,
      status: selectedClient.status,
      responsible_name: selectedClient.responsible_name ?? "",
      enabled_modules: selectedClient.enabled_modules,
    });
  }, [selectedClient, setClientDraft, isOpen]);

  const handleCreateInvite = () => {
    if (!selectedClientId) return;
    createInvite.mutate(
      { clientId: selectedClientId, email: inviteEmail.trim() || null },
      {
        onSuccess: (invite) => {
          setInviteLink(`${window.location.origin}${invite.path}`);
          setInviteCopied(false);
          setInviteEmail("");
        },
      },
    );
  };

  const handleCopyInvite = async () => {
    if (!inviteLink) return;
    await navigator.clipboard.writeText(inviteLink);
    setInviteCopied(true);
  };

  const handleCreateReset = async () => {
    if (!resetEmail.trim()) return;
    setResetError("");
    setResetBusy(true);
    try {
      const reset = await api.createPasswordReset(resetEmail.trim());
      setResetLink(`${window.location.origin}${reset.path}`);
      setResetCopied(false);
      setResetEmail("");
    } catch (err) {
      setResetError(err instanceof Error ? err.message : "Não foi possível gerar o link.");
    } finally {
      setResetBusy(false);
    }
  };

  const handleCopyReset = async () => {
    if (!resetLink) return;
    await navigator.clipboard.writeText(resetLink);
    setResetCopied(true);
  };

  const toggleModule = (module: ClientModule) => {
    const current = new Set(clientDraft.enabled_modules ?? selectedClient?.enabled_modules ?? []);
    if (current.has(module)) {
      current.delete(module);
    } else {
      current.add(module);
    }
    current.add("hub");
    setClientDraft({ ...clientDraft, enabled_modules: Array.from(current) });
  };

  const handleUpdateClient = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedClientId) return;
    updateClient.mutate({ id: selectedClientId, payload: clientDraft });
  };

  const isBusy = Boolean(actionBusy) || updateClient.isPending;

  if (!isOpen || !selectedClient) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-content" onClick={e => e.stopPropagation()}>
        <div className="drawer-header">
          <h2><Settings size={20} color="var(--brand-accent)" /> Gerenciar Cliente</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Fechar">
            <X size={20} />
          </button>
        </div>
        
        <div className="drawer-body" style={{ overflowY: 'auto', flex: 1, paddingBottom: 64 }}>
          <form onSubmit={handleUpdateClient}>
            <DockTitle icon={Save} title="Editar cliente selecionado" />
            <div className="form-grid two">
              <label>
                Nome
                <input value={clientDraft.name ?? ""} onChange={(event) => setClientDraft({ ...clientDraft, name: event.target.value })} />
              </label>
              <label>
                Status
                <select
                  value={clientDraft.status ?? "onboarding"}
                  onChange={(event) => setClientDraft({ ...clientDraft, status: event.target.value as ClientStatus })}
                >
                  {Object.entries(statusLabel).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Responsável EG
                <select
                  value={clientDraft.responsible_name ?? ""}
                  onChange={(event) => setClientDraft({ ...clientDraft, responsible_name: event.target.value })}
                >
                  <option value="Eduardo EG">Eduardo EG (eduardo@evergreengrowth.com.br)</option>
                  {clientDraft.responsible_name && clientDraft.responsible_name !== "Eduardo EG" && (
                    <option value={clientDraft.responsible_name}>{clientDraft.responsible_name}</option>
                  )}
                </select>
              </label>
            </div>

            <fieldset className="module-toggles" style={{ marginTop: '20px', padding: '16px', border: '1px solid var(--border)', borderRadius: '8px' }}>
              <legend style={{ padding: '0 8px', fontSize: '0.85rem', color: 'var(--text-dim)' }}>
                Módulos habilitados para o cliente
              </legend>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '8px' }}>
                {toggleableModules.map(mod => (
                  <label key={mod} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={clientDraft.enabled_modules?.includes(mod) ?? selectedClient?.enabled_modules?.includes(mod) ?? false}
                      onChange={() => toggleModule(mod)}
                    />
                    {moduleLabels[mod]}
                  </label>
                ))}
              </div>
            </fieldset>

            <button className="primary-button" type="submit" disabled={isBusy} style={{ marginTop: '20px', width: '100%' }}>
              <Save size={16} />
              Salvar cliente
            </button>
          </form>

          <hr style={{ border: 'none', borderTop: '1px solid var(--glass-border)', margin: '16px 0' }} />

          <div>
            <DockTitle icon={UserPlus} title="Convidar usuário do cliente" />
            <p style={{ fontSize: "0.8rem", color: "var(--text-faint)", marginTop: 0, marginBottom: "12px" }}>
              Gera um link de uso único (expira em 7 dias). Envie por WhatsApp; a pessoa define a própria senha.
            </p>
            <div className="form-grid" style={{ display: "flex", gap: "12px", flexDirection: "column" }}>
              <label>
                E-mail (opcional, restringe o convite)
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="pessoa@cliente.com.br"
                />
              </label>
              <button
                className="primary-button"
                type="button"
                onClick={handleCreateInvite}
                disabled={isBusy || createInvite.isPending}
                style={{ alignSelf: 'flex-start' }}
              >
                <UserPlus size={16} />
                Gerar link de convite
              </button>
            </div>
            {inviteLink && (
              <div style={{ marginTop: "12px", background: "var(--bg-inset)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "12px" }}>
                <input readOnly value={inviteLink} style={{ flex: 1, padding: "8px", fontSize: "0.85rem", background: "transparent", border: "none", color: "var(--text)" }} />
                <button type="button" onClick={handleCopyInvite} className="secondary-button" style={{ padding: "8px" }} title="Copiar link">
                  {inviteCopied ? "Copiado!" : "Copiar"}
                </button>
              </div>
            )}
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid var(--glass-border)', margin: '16px 0' }} />

          <div style={{ marginTop: 32, borderTop: "1px solid var(--danger, #e5484d)", paddingTop: 16 }}>
            <h3 style={{ color: "var(--danger, #e5484d)", display: "flex", alignItems: "center", gap: 8, fontSize: "0.95rem", margin: "0 0 12px 0" }}>
              <Trash2 size={16} /> Zona de Perigo
            </h3>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 0, marginBottom: "12px" }}>
              Remover este cliente ocultará o workspace da carteira ativa e interromperá serviços ativos.
            </p>
            {selectedClient?.status === "archived" ? (
              <p style={{ fontSize: "0.85rem", color: "var(--danger, #e5484d)" }}>Este cliente já foi removido.</p>
            ) : (
              <button
                className="primary-button"
                style={{ background: "var(--danger, #e5484d)", color: "#fff", width: "100%" }}
                type="button"
                disabled={isBusy || archiveClient.isPending || !selectedClient}
                onClick={() => {
                  if (!selectedClient) return;
                  if (!window.confirm(`Tem certeza que deseja remover ${selectedClient.name}? O acesso do cliente será encerrado e ele sumirá da carteira.`)) return;
                  archiveClient.mutate(selectedClient.id, { onSuccess: onClose });
                }}
              >
                {archiveClient.isPending ? "Removendo..." : "Remover Cliente"}
              </button>
            )}
            {archiveClient.isError && (
              <div className="notice error" style={{ marginTop: "10px" }}>
                {archiveClient.error instanceof Error ? archiveClient.error.message : "Falha ao remover."}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
