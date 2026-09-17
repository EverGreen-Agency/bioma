import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clipboard, Eye, EyeOff, KeyRound, LoaderCircle, Plus, ShieldAlert } from "lucide-react";

import {
  api,
  type VaultCredentialPayload,
  type VaultCredentialSummary,
  type VaultRevealResponse,
  type VaultSecretField,
  type VaultStatus,
  type WorkspaceSummary,
} from "../lib/api";
import { formatDateTime } from "../lib/format";
import { EmptyState, SectionHeader } from "./shared";


const SECRET_LABELS: Record<VaultSecretField, string> = {
  username: "Usuário",
  email: "E-mail",
  password: "Senha",
  other_access: "Outra forma de acesso",
  token: "Token",
  recovery_codes: "Códigos de recuperação",
  notes: "Notas seguras",
};

const STATUS_LABELS: Record<VaultStatus, string> = {
  active: "Ativo",
  expired: "Expirado",
  rotating: "Em rotação",
  compromised: "Comprometido",
  revoked: "Revogado",
};

const EMPTY_DRAFT: VaultCredentialPayload = {
  platform: "",
  label: "",
  account_hint: "",
  platform_url: "",
  visibility: "internal",
  expires_at: null,
  secrets: {},
};

type AccessRole = WorkspaceSummary["access_role"];


export function AccessVault({ workspaceId, accessRole }: { workspaceId: string; accessRole: AccessRole }) {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState<VaultCredentialPayload>(EMPTY_DRAFT);
  const [revealTarget, setRevealTarget] = useState<VaultCredentialSummary | null>(null);
  const [reason, setReason] = useState("");
  const [revealed, setRevealed] = useState<VaultRevealResponse | null>(null);
  const [copiedField, setCopiedField] = useState<VaultSecretField | null>(null);

  const canManage = ["platform_admin", "tenant_admin", "workspace_manager", "operator"].includes(accessRole);
  const canReveal = ["platform_admin", "tenant_admin", "workspace_manager"].includes(accessRole);
  const isClientDeposit = accessRole === "client_user";

  const credentials = useQuery({
    queryKey: ["vault", workspaceId],
    queryFn: () => api.vaultCredentials(workspaceId),
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["vault", workspaceId] });
  const createCredential = useMutation({
    mutationFn: (payload: VaultCredentialPayload) => api.createVaultCredential(workspaceId, payload),
    onSuccess: async () => {
      setDraft(EMPTY_DRAFT);
      setShowForm(false);
      await refresh();
    },
  });
  const setStatus = useMutation({
    mutationFn: ({ credentialId, status }: { credentialId: string; status: VaultStatus }) =>
      api.setVaultCredentialStatus(workspaceId, credentialId, status),
    onSuccess: refresh,
  });
  const reveal = useMutation({
    mutationFn: ({ credentialId, revealReason }: { credentialId: string; revealReason: string }) =>
      api.revealVaultCredential(workspaceId, credentialId, revealReason),
    onSuccess: setRevealed,
  });
  const copySecret = useMutation({
    mutationFn: ({ credentialId, field }: { credentialId: string; field: VaultSecretField }) =>
      api.copyVaultSecret(workspaceId, credentialId, field, reason.trim()),
    onSuccess: async (response) => {
      await navigator.clipboard.writeText(response.value);
      setCopiedField(response.field);
      window.setTimeout(() => setCopiedField(null), 1800);
    },
  });

  useEffect(() => {
    if (!revealed) return;
    const timer = window.setTimeout(() => {
      setRevealed(null);
      setRevealTarget(null);
      setReason("");
    }, revealed.expires_in_seconds * 1000);
    return () => window.clearTimeout(timer);
  }, [revealed]);

  const visibleSecrets = useMemo(
    () => Object.entries(revealed?.secrets ?? {}).filter((entry): entry is [VaultSecretField, string] => Boolean(entry[1])),
    [revealed],
  );

  function submit(event: FormEvent) {
    event.preventDefault();
    const secrets = Object.fromEntries(
      Object.entries(draft.secrets).filter(([, value]) => value?.trim()),
    );
    if (Object.keys(secrets).length === 0) return;
    createCredential.mutate({
      ...draft,
      platform: draft.platform.trim(),
      label: draft.label.trim(),
      account_hint: draft.account_hint?.trim() || null,
      visibility: isClientDeposit ? "client" : draft.visibility,
      expires_at: draft.expires_at || null,
      secrets,
    });
  }

  function closeReveal() {
    setRevealTarget(null);
    setRevealed(null);
    setReason("");
  }

  return (
    <section className="vault-layout">
      <div className="vault-heading">
        <SectionHeader eyebrow="Segurança operacional" title="Acessos do cliente" icon={KeyRound} />
        <button className="primary-button" type="button" onClick={() => setShowForm((value) => !value)}>
          <Plus size={15} />
          {isClientDeposit ? "Entregar acesso à EG" : "Cadastrar acesso"}
        </button>
      </div>

      <div className="notice vault-notice">
        <ShieldAlert size={17} />
        <span>Senhas e tokens são cifrados antes de chegar ao banco. A listagem nunca devolve segredos.</span>
      </div>

      {showForm && (
        <form className="surface vault-form" onSubmit={submit}>
          <div className="form-grid">
            <label>Conta / plataforma<input required minLength={2} value={draft.platform} onChange={(event) => setDraft({ ...draft, platform: event.target.value })} placeholder="Meta Business, Google Ads, Kommo..." /></label>
            <label>Conta / perfil<input required minLength={2} value={draft.label} onChange={(event) => setDraft({ ...draft, label: event.target.value })} placeholder="Conta principal" /></label>
            <label>Referência não sensível<input value={draft.account_hint ?? ""} onChange={(event) => setDraft({ ...draft, account_hint: event.target.value })} placeholder="ID, final do e-mail ou apelido" /></label>
            <label>Link da plataforma<input type="url" value={draft.platform_url ?? ""} onChange={(event) => setDraft({ ...draft, platform_url: event.target.value })} placeholder="https://..." /></label>
            {!isClientDeposit && (
              <label>Visibilidade<select value={draft.visibility} onChange={(event) => setDraft({ ...draft, visibility: event.target.value as VaultCredentialPayload["visibility"] })}><option value="internal">Somente equipe</option><option value="client">Cliente vê o registro</option></select></label>
            )}
            <label>Usuário<input autoComplete="off" value={draft.secrets.username ?? ""} onChange={(event) => setDraft({ ...draft, secrets: { ...draft.secrets, username: event.target.value } })} /></label>
            <label>E-mail<input type="email" autoComplete="off" value={draft.secrets.email ?? ""} onChange={(event) => setDraft({ ...draft, secrets: { ...draft.secrets, email: event.target.value } })} /></label>
            <label>Senha<input type="password" autoComplete="new-password" value={draft.secrets.password ?? ""} onChange={(event) => setDraft({ ...draft, secrets: { ...draft.secrets, password: event.target.value } })} /></label>
            <label>Outra forma de acesso<textarea rows={3} value={draft.secrets.other_access ?? ""} onChange={(event) => setDraft({ ...draft, secrets: { ...draft.secrets, other_access: event.target.value } })} placeholder="Google, GitHub, CPF, telefone ou instruções de acesso" /></label>
            <label>Token<textarea rows={3} value={draft.secrets.token ?? ""} onChange={(event) => setDraft({ ...draft, secrets: { ...draft.secrets, token: event.target.value } })} /></label>
            <label>Códigos de recuperação<textarea rows={3} value={draft.secrets.recovery_codes ?? ""} onChange={(event) => setDraft({ ...draft, secrets: { ...draft.secrets, recovery_codes: event.target.value } })} /></label>
            <label>Notas seguras<textarea rows={3} value={draft.secrets.notes ?? ""} onChange={(event) => setDraft({ ...draft, secrets: { ...draft.secrets, notes: event.target.value } })} /></label>
          </div>
          {createCredential.error && <span className="form-error">{createCredential.error.message}</span>}
          <div className="row-actions">
            <button className="primary-button" type="submit" disabled={createCredential.isPending}>
              {createCredential.isPending && <LoaderCircle className="spin" size={15} />}
              Salvar com criptografia
            </button>
            <button className="ghost-button" type="button" onClick={() => setShowForm(false)}>Cancelar</button>
          </div>
        </form>
      )}

      {credentials.isLoading && <EmptyState text="Carregando acessos..." />}
      {credentials.error && <div className="notice error">{credentials.error.message}</div>}
      {!credentials.isLoading && !credentials.error && credentials.data?.length === 0 && (
        <EmptyState text="Nenhum acesso seguro cadastrado para este workspace." />
      )}

      <div className="vault-grid">
        {credentials.data?.map((credential) => (
          <article className="surface vault-card" key={credential.id}>
            <header>
              <div><span>{credential.platform}</span><h3>{credential.label}</h3></div>
              <span className={`status-pill ${credential.status}`}>{STATUS_LABELS[credential.status]}</span>
            </header>
            <dl>
              {credential.account_hint && <><dt>Referência</dt><dd>{credential.account_hint}</dd></>}
              {credential.platform_url && <><dt>Link</dt><dd><a href={credential.platform_url} target="_blank" rel="noreferrer">Abrir plataforma</a></dd></>}
              <dt>Visibilidade</dt><dd>{credential.visibility === "client" ? "Cliente" : "Equipe EG"}</dd>
              <dt>Versão</dt><dd>{credential.version}</dd>
              <dt>Atualizado</dt><dd>{formatDateTime(credential.updated_at)}</dd>
            </dl>
            <div className="row-actions">
              {canReveal && !["compromised", "revoked"].includes(credential.status) && (
                <button className="mini-button" type="button" onClick={() => { closeReveal(); setRevealTarget(credential); }}><Eye size={14} /> Revelar</button>
              )}
              {canManage && (
                <select aria-label={`Status de ${credential.label}`} value={credential.status} onChange={(event) => setStatus.mutate({ credentialId: credential.id, status: event.target.value as VaultStatus })}>
                  {Object.entries(STATUS_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
                </select>
              )}
            </div>
          </article>
        ))}
      </div>

      {revealTarget && (
        <div className="modal-backdrop" role="presentation" onMouseDown={closeReveal}>
          <section className="surface vault-reveal" role="dialog" aria-modal="true" aria-label={`Revelar ${revealTarget.label}`} onMouseDown={(event) => event.stopPropagation()}>
            <header><div><span>{revealTarget.platform}</span><h3>{revealTarget.label}</h3></div><button className="icon-button" type="button" onClick={closeReveal}><EyeOff size={17} /></button></header>
            {!revealed ? (
              <form onSubmit={(event) => { event.preventDefault(); reveal.mutate({ credentialId: revealTarget.id, revealReason: reason.trim() }); }}>
                <label>Motivo da consulta<textarea required minLength={3} maxLength={500} rows={3} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Ex.: configurar campanha aprovada do cliente" /></label>
                {reveal.error && <span className="form-error">{reveal.error.message}</span>}
                <button className="primary-button" type="submit" disabled={reveal.isPending || reason.trim().length < 3}>{reveal.isPending && <LoaderCircle className="spin" size={15} />} Confirmar e auditar</button>
              </form>
            ) : (
              <div className="vault-secret-list">
                <p className="panel-footnote">Os valores serão removidos desta tela em {revealed.expires_in_seconds} segundos.</p>
                {visibleSecrets.map(([field, value]) => (
                  <div key={field}><span>{SECRET_LABELS[field]}</span><code>{value}</code><button className="mini-button" type="button" onClick={() => copySecret.mutate({ credentialId: revealTarget.id, field })}><Clipboard size={13} /> {copiedField === field ? "Copiado" : "Copiar"}{copiedField === field && <Check size={12} />}</button></div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </section>
  );
}
