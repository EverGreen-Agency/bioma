import { FormEvent, Suspense, lazy, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, KeyRound, Link2, User, Building2, Unlink, Phone, Briefcase, Mail, X, Laptop, ShieldCheck, Trash2, Copy, Terminal } from "lucide-react";
import { api, apiUrl } from "../lib/api";
import {
  useCurrentUser,
  useWorkspaces,
  useSessions,
  useRevokeSession,
  useRevokeOtherSessions,
  usePersonalAccessTokens,
  useCreatePersonalAccessToken,
  useRevokePersonalAccessToken,
} from "../hooks/useBiomaApi";
import { SectionHeader, GoogleIcon } from "../components/shared";
import { SurfacePreferencesCard } from "../components/SurfacePreferencesCard";
import { SurfaceAccessManager } from "../components/SurfaceAccessManager";
import { TeamInviteCard } from "../components/TeamInviteCard";
import { OrganizationPeopleList } from "../components/OrganizationPeopleList";
import Cropper from 'react-easy-crop';
import getCroppedImg from '../lib/cropImage';

const IntegrationsTab = lazy(() =>
  import("../components/IntegrationsTab").then((module) => ({ default: module.IntegrationsTab })),
);
const TeamPortfolioManager = lazy(() =>
  import("../components/TeamPortfolioManager").then((module) => ({ default: module.TeamPortfolioManager })),
);
const AccessVault = lazy(() =>
  import("../components/AccessVault").then((module) => ({ default: module.AccessVault })),
);
const WhatsAppManager = lazy(() =>
  import("../components/WhatsAppManager").then((module) => ({ default: module.WhatsAppManager })),
);

export function SettingsView() {
  const { data: user } = useCurrentUser();
  const location = useLocation();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<"user" | "company">("user");
  const [activeSubTab, setActiveSubTab] = useState<"general" | "teams" | "integrations" | "vault">("general");
  const { data: workspaces = [] } = useWorkspaces(Boolean(user));
  const [vaultWorkspaceId, setVaultWorkspaceId] = useState("");
  const clientWorkspaces = workspaces.filter((workspace) => workspace.kind === "client" && workspace.status === "active");
  const selectedVaultWorkspace = clientWorkspaces.find((workspace) => workspace.id === vaultWorkspaceId) ?? clientWorkspaces[0] ?? null;

  // Sujeito das contas de mídia da EG: o WORKSPACE da agência.
  //
  // Era o registro "EverGreen Internal" em `clients`, criado só porque
  // `performance_connections` exigia `client_id`. Com a 0087 e o resolvedor
  // por workspace, esse registro deixou de existir — a agência não é cliente
  // de si mesma, e agora o código também não finge que é.
  const agencyWorkspace = workspaces.find((workspace) => workspace.kind === "agency_internal") ?? null;
  const egSubjectId = agencyWorkspace?.id ?? null;
  const tenantOrganizationId = agencyWorkspace?.tenant_organization_id ?? workspaces[0]?.tenant_organization_id ?? null;

  // Avatar local (base64 em localStorage até endpoint de upload existir no backend)
  const avatarKey = user ? `bioma_avatar_${user.id}` : null;
  const [avatarSrc, setAvatarSrc] = useState<string | null>(() => {
    if (!avatarKey) return null;
    try { return localStorage.getItem(avatarKey); } catch { return null; }
  });

  const [cropImageSrc, setCropImageSrc] = useState<string | null>(null);
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);

  // Campos de perfil local
  const profileKey = user ? `bioma_profile_${user.id}` : null;
  const loadProfile = () => {
    if (!profileKey) return { cargo: '', telefone: '' };
    try { return JSON.parse(localStorage.getItem(profileKey) ?? '{}'); } catch { return {}; }
  };
  const [cargo, setCargo] = useState<string>(() => loadProfile().cargo ?? '');
  const [telefone, setTelefone] = useState<string>(() => loadProfile().telefone ?? '');
  const [profileSaved, setProfileSaved] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const { data: identities } = useQuery({ queryKey: ["identities"], queryFn: api.identities });
  const googleIdentity = identities?.find((identity) => identity.provider === "google") ?? null;
  const [identityError, setIdentityError] = useState("");
  const [unlinking, setUnlinking] = useState(false);

  const searchParams = new URLSearchParams(location.search);
  const linkedNow = searchParams.get("linked") === "google";
  const oauthError = searchParams.get("oauth_error");

  function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !avatarKey) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const src = ev.target?.result as string;
      setCropImageSrc(src);
    };
    reader.readAsDataURL(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const onCropComplete = (croppedArea: any, croppedAreaPixels: any) => {
    setCroppedAreaPixels(croppedAreaPixels);
  };

  const handleSaveCrop = async () => {
    if (!cropImageSrc || !croppedAreaPixels || !avatarKey) return;
    try {
      const croppedImage = await getCroppedImg(cropImageSrc, croppedAreaPixels);
      setAvatarSrc(croppedImage);
      localStorage.setItem(avatarKey, croppedImage);
      window.dispatchEvent(new Event('avatarUpdated'));
      setCropImageSrc(null);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCancelCrop = () => {
    setCropImageSrc(null);
  };

  function handleSaveProfile() {
    if (!profileKey) return;
    localStorage.setItem(profileKey, JSON.stringify({ cargo, telefone }));
    setProfileSaved(true);
    setTimeout(() => setProfileSaved(false), 2500);
  }

  async function handleUnlink() {
    if (!googleIdentity) return;
    setIdentityError("");
    setUnlinking(true);
    try {
      await api.unlinkIdentity(googleIdentity.id);
      await queryClient.invalidateQueries({ queryKey: ["identities"] });
    } catch (err) {
      setIdentityError(err instanceof Error ? err.message : "Não foi possível desvincular.");
    } finally {
      setUnlinking(false);
    }
  }

  if (!user) return null;

  const initials = user.display_name.substring(0, 2).toUpperCase();
  const isEgAdmin = user.organizations.some((org: { role: string }) => org.role === "eg_admin");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");
    if (newPassword.length < 8) {
      setError("A nova senha precisa ter pelo menos 8 caracteres.");
      return;
    }
    if (newPassword !== confirm) {
      setError("As senhas não conferem.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await api.changePassword(currentPassword, newPassword);
      setSuccess(
        result.revoked_sessions > 0
          ? `Senha alterada. ${result.revoked_sessions} outra(s) sessão(ões) foram encerradas.`
          : "Senha alterada com sucesso."
      );
      setCurrentPassword("");
      setNewPassword("");
      setConfirm("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível alterar a senha.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="profile-grid">
      <SectionHeader eyebrow="Ajustes" title="Configurações" icon={User} />

      {/* Tabs principais */}
      <div className="settings-tabs">
        {(["user", "company"] as const)
          .filter(t => t === "user" || isEgAdmin)
          .map(t => (
            <button
              key={t}
              type="button"
              className={`settings-tab-btn ${activeTab === t ? "active" : ""}`}
              onClick={() => setActiveTab(t)}
            >
              {t === "user" ? "Meu Perfil" : "Empresa"}
            </button>
          ))}
      </div>

      {/* Hero do perfil */}
      {activeTab === "user" && (
        <div className="profile-hero">
          <div className="profile-avatar-wrap">
            <div className="profile-avatar-large" style={{ backgroundImage: avatarSrc ? `url(${avatarSrc})` : undefined, backgroundSize: 'cover', backgroundPosition: 'center', color: avatarSrc ? 'transparent' : undefined }}>
              {!avatarSrc && initials}
            </div>
            <button
              type="button"
              className="avatar-upload-btn"
              title="Trocar foto"
              onClick={() => fileInputRef.current?.click()}
            >
              <Camera size={14} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={handleAvatarChange}
            />
          </div>
          <div className="profile-hero-info">
            <h2 className="profile-hero-name">{user.display_name}</h2>
            <span className="profile-hero-email">{user.email}</span>
            {cargo && <span className="profile-hero-role">{cargo}</span>}
          </div>
          <div className="profile-hero-badges">
            {isEgAdmin && (
              <span className="level-badge" style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                EG Admin
              </span>
            )}
            {!isEgAdmin && user.organizations.map((org: { id: string; role: string }) => (
              <span key={org.id} className="level-badge" style={{ fontSize: '0.7rem' }}>
                {org.role}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Cropper Modal */}
      {cropImageSrc && (
        <div className="modal-overlay" style={{ zIndex: 9999, backdropFilter: 'blur(4px)' }}>
          <div className="modal-content" style={{ 
            width: '440px', 
            maxWidth: '90vw', 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '24px',
            padding: '24px',
            borderRadius: '16px',
            background: 'var(--surface)',
            boxShadow: '0 24px 48px rgba(0,0,0,0.4)',
            border: '1px solid var(--border-light)'
          }}>
            <div className="modal-header" style={{ marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Ajustar foto de perfil</h3>
              <button type="button" className="icon-button" onClick={handleCancelCrop} aria-label="Fechar">
                <X size={18} />
              </button>
            </div>
            
            <div style={{ position: 'relative', width: '100%', height: '320px', borderRadius: '12px', overflow: 'hidden', background: '#111' }}>
              {/* @ts-expect-error type incompatibility with react-easy-crop in strict mode */}
              <Cropper
                image={cropImageSrc}
                crop={crop}
                zoom={zoom}
                aspect={1}
                cropShape="round"
                showGrid={false}
                onCropChange={setCrop}
                onZoomChange={setZoom}
                onCropComplete={onCropComplete}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '0 8px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Zoom</span>
              <input
                type="range"
                value={zoom}
                min={1}
                max={3}
                step={0.1}
                aria-label="Zoom"
                onChange={(e) => setZoom(Number(e.target.value))}
                style={{
                  flex: 1,
                  accentColor: 'var(--brand-accent)',
                  cursor: 'pointer'
                }}
              />
            </div>

            <div className="modal-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
              <button type="button" className="ghost-button" onClick={handleCancelCrop}>
                Cancelar
              </button>
              <button type="button" className="primary-button" onClick={handleSaveCrop}>
                Salvar Foto
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === "user" && (
        <div className="profile-content">

          {/* Informações pessoais */}
          <article className="surface profile-section" style={{ gridColumn: '1 / -1' }}>
            <div className="surface-header">
              <User size={18} />
              <h3>Informações pessoais</h3>
            </div>
            <p className="panel-footnote" style={{ marginTop: 0 }}>
              Dados locais por enquanto — em breve sincronizados com o backend.
            </p>
            <div className="form-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '16px' }}>
              <label>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                  <Mail size={13} /> E-mail
                </span>
                <input value={user.email} disabled style={{ opacity: 0.6 }} />
              </label>
              <label>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                  <Briefcase size={13} /> Cargo / Função
                </span>
                <input
                  value={cargo}
                  onChange={e => setCargo(e.target.value)}
                  placeholder="Ex: Growth Lead, Designer..."
                />
              </label>
              <label>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                  <Phone size={13} /> Telefone / WhatsApp
                </span>
                <input
                  value={telefone}
                  onChange={e => setTelefone(e.target.value)}
                  placeholder="+55 (11) 99999-9999"
                  type="tel"
                />
              </label>
            </div>
            <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button type="button" className="primary-button" onClick={handleSaveProfile}>
                Salvar informações
              </button>
              {profileSaved && <span className="form-success">Salvo ✓</span>}
            </div>
          </article>

          <article className="surface profile-section">
            <div className="surface-header">
              <Link2 size={18} />
              <h3>Contas conectadas</h3>
            </div>
            <p className="panel-footnote" style={{ marginTop: 0 }}>
              Vincule sua conta Google para entrar no Bioma com um clique. Sua conta continua sendo a do convite EG —
              o vínculo pode ser desfeito a qualquer momento, e a senha continua valendo.
            </p>
            {linkedNow && <span className="form-success">Conta Google vinculada com sucesso.</span>}
            {oauthError && <span className="form-error">{oauthError}</span>}
            {identityError && <span className="form-error">{identityError}</span>}
            <div className="timeline-list" style={{ marginTop: 12 }}>
              {googleIdentity ? (
                <div className="timeline-row">
                  <span>Google</span>
                  <strong>{googleIdentity.email ?? "conta vinculada"}</strong>
                  {user.has_password ? (
                    <button
                      className="mini-button"
                      type="button"
                      onClick={handleUnlink}
                      disabled={unlinking}
                    >
                      <Unlink size={13} />
                      {unlinking ? "Desvinculando..." : "Desvincular"}
                    </button>
                  ) : (
                    <button
                      className="mini-button"
                      type="button"
                      disabled
                      title="O Google é seu único método de login. Defina uma senha na seção Segurança abaixo para poder desvincular."
                    >
                      <Unlink size={13} />
                      Defina uma senha antes
                    </button>
                  )}
                </div>
              ) : (
                <div className="timeline-row">
                  <span>Google</span>
                  <strong>Nenhuma conta vinculada</strong>
                  <button
                    className="login-social-btn"
                    type="button"
                    style={{ margin: 0, width: '100%', justifyContent: 'center' }}
                    onClick={() => {
                      window.location.href = apiUrl("/auth/oauth/google/start?mode=link");
                    }}
                  >
                    <GoogleIcon />
                    <span>Conectar Google</span>
                  </button>
                </div>
              )}
            </div>
          </article>

          <article className="surface profile-section">
            <div className="surface-header">
              <KeyRound size={18} />
              <h3>Segurança</h3>
            </div>
            <form className="form-grid" onSubmit={handleSubmit}>
              <label>
                Senha atual
                <input
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  type="password"
                  required
                  autoComplete="current-password"
                />
              </label>
              <label>
                Nova senha
                <input
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  placeholder="Mínimo 8 caracteres"
                />
              </label>
              <label>
                Confirmar nova senha
                <input
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </label>
              {error && <span className="form-error">{error}</span>}
              {success && <span className="form-success">{success}</span>}
              <div className="modal-actions" style={{ marginTop: "16px" }}>
                <button className="primary-button" type="submit" disabled={submitting}>
                  Atualizar Senha
                </button>
              </div>
            </form>
          </article>

          {/* Preferência de navegação (decisão 11, nível 4): esconde do menu
              sem apagar nada, e mostra de onde vem cada bloqueio. */}
          <SurfacePreferencesCard />

          {/* Dispositivos & Sessões Ativas */}
          <SessionsManagerCard />

          {/* Tokens de Acesso Pessoal (apps externos, ex: Fóton) */}
          <PersonalAccessTokensCard />
        </div>
      )}

      {activeTab === "company" && isEgAdmin && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24, width: "100%" }}>
          <div style={{ display: "flex", gap: "16px", borderBottom: "1px solid var(--border-light)", paddingBottom: "12px" }}>
            <button
              type="button"
              onClick={() => setActiveSubTab("general")}
              style={{ background: "transparent", border: "none", cursor: "pointer", color: activeSubTab === "general" ? "var(--text-main)" : "var(--text-muted)", fontWeight: activeSubTab === "general" ? 600 : 400, padding: "8px 0", borderBottom: activeSubTab === "general" ? "2px solid var(--brand-accent)" : "2px solid transparent" }}
            >
              Geral
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab("teams")}
              style={{ background: "transparent", border: "none", cursor: "pointer", color: activeSubTab === "teams" ? "var(--text-main)" : "var(--text-muted)", fontWeight: activeSubTab === "teams" ? 600 : 400, padding: "8px 0", borderBottom: activeSubTab === "teams" ? "2px solid var(--brand-accent)" : "2px solid transparent" }}
            >
              Equipes & carteiras
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab("integrations")}
              style={{ background: "transparent", border: "none", cursor: "pointer", color: activeSubTab === "integrations" ? "var(--text-main)" : "var(--text-muted)", fontWeight: activeSubTab === "integrations" ? 600 : 400, padding: "8px 0", borderBottom: activeSubTab === "integrations" ? "2px solid var(--brand-accent)" : "2px solid transparent" }}
            >
              Integrações
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab("vault")}
              style={{ background: "transparent", border: "none", cursor: "pointer", color: activeSubTab === "vault" ? "var(--text-main)" : "var(--text-muted)", fontWeight: activeSubTab === "vault" ? 600 : 400, padding: "8px 0", borderBottom: activeSubTab === "vault" ? "2px solid var(--brand-accent)" : "2px solid transparent" }}
            >
              Acessos
            </button>
          </div>

          <div>
            {activeSubTab === "general" && (
              <article className="surface profile-section">
                <div className="surface-header">
                  <Building2 size={18} />
                  <h3>EverGreen</h3>
                </div>
                <div style={{ padding: "16px 0" }}>
                  <p style={{ color: "var(--text-muted)", marginBottom: "16px" }}>
                    Configurações da agência. Gerencie usuários internos e preferências globais.
                  </p>
                  
                  {/* Antes este bloco mostrava só o usuário logado — quem
                      convidava alguém não via a pessoa em lugar nenhum. Agora
                      lista todo mundo da organização, com papel e equipes. */}
                  <OrganizationPeopleList tenantOrganizationId={tenantOrganizationId} currentUserId={user.id} />
                </div>
              </article>
            )}

            {/* Convite ao time (0088). Substitui o "Funcionalidade em breve"
                que estava aqui: convite só existia por cliente, e colocar
                alguém no time exigia que a pessoa já tivesse conta. */}
            {activeSubTab === "general" && (
              <div style={{ marginTop: 24 }}>
                <TeamInviteCard tenantOrganizationId={tenantOrganizationId} />
              </div>
            )}

            {activeSubTab === "teams" && (
              <Suspense fallback={<div className="notice">Carregando equipes e carteiras...</div>}>
                <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
                  <TeamPortfolioManager />
                  {/* Níveis 2 e 3 da decisão 11: acesso por equipe e por
                      pessoa, no mesmo lugar onde a equipe é montada. */}
                  <SurfaceAccessManager />
                </div>
              </Suspense>
            )}

            {activeSubTab === "integrations" && (
              <Suspense fallback={<div className="notice">Carregando estado do ambiente...</div>}>
                {/* `all` (e não `environment`): além das credenciais do ambiente
                    e das plataformas de freelancer, esta aba passa a mostrar as
                    contas de mídia da própria EG — Google Ads via MCC, Meta via
                    BM, GA4, Search Console. Ficam juntas de propósito: são a
                    mesma pergunta ("o que a EG tem conectado?") e separá-las em
                    duas telas era o que obrigava a procurar em dois lugares. */}
                <IntegrationsTab scope="all" clientId={egSubjectId} subjectName="EverGreen (Operação EG)" />
              </Suspense>
            )}

            {activeSubTab === "vault" && (
              <section className="workspace-module-panel" style={{ width: "100%" }}>
                <div className="surface" style={{ padding: 16, marginBottom: 16 }}>
                  <label style={{ display: "grid", gap: 6, maxWidth: 420 }}>
                    Empresa / workspace do cliente
                    <select
                      className="status-select"
                      value={selectedVaultWorkspace?.id ?? ""}
                      onChange={(event) => setVaultWorkspaceId(event.target.value)}
                      disabled={clientWorkspaces.length === 0}
                    >
                      {clientWorkspaces.length === 0 && <option value="">Nenhum workspace de cliente disponível</option>}
                      {clientWorkspaces.map((workspace) => <option value={workspace.id} key={workspace.id}>{workspace.organization_name}</option>)}
                    </select>
                  </label>
                  <p className="panel-footnote" style={{ marginBottom: 0, marginTop: 6 }}>Gerencie os acessos por empresa sem expor segredos nas listagens.</p>
                </div>
                {selectedVaultWorkspace ? (
                  <Suspense fallback={<div className="notice">Carregando cofre...</div>}>
                    <AccessVault workspaceId={selectedVaultWorkspace.id} accessRole={selectedVaultWorkspace.access_role} />
                  </Suspense>
                ) : <div className="notice">Crie ou atribua um workspace de cliente para acessar o cofre.</div>}
              </section>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function SessionsManagerCard() {
  const { data: sessions = [], isLoading } = useSessions();
  const revokeSession = useRevokeSession();
  const revokeOther = useRevokeOtherSessions();

  return (
    <article className="surface profile-section" style={{ marginTop: "24px" }}>
      <div className="surface-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Laptop size={18} />
          <h3 style={{ margin: 0 }}>Dispositivos & Sessões Ativas</h3>
        </div>
        {sessions.filter((s) => !s.is_current).length > 0 && (
          <button
            className="ghost-button danger"
            type="button"
            style={{ fontSize: "0.8rem" }}
            onClick={() => revokeOther.mutate()}
            disabled={revokeOther.isPending}
          >
            <Trash2 size={14} /> Desconectar outros dispositivos
          </button>
        )}
      </div>

      <p style={{ fontSize: "0.85rem", color: "var(--text-dim)", margin: "0 0 16px" }}>
        Estes são os navegadores e dispositivos atualmente autorizados na sua conta.
      </p>

      {isLoading && <p style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>Carregando sessões...</p>}

      {!isLoading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {sessions.map((session) => {
            const createdDate = session.created_at ? new Date(session.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "Desconhecido";
            const expiresDate = session.expires_at ? new Date(session.expires_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : "30 dias";
            const lastSeen = session.last_seen_at
              ? new Date(session.last_seen_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
              : "sem registro";
            return (
              <div
                key={session.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  background: session.is_current ? "rgba(58, 201, 123, 0.08)" : "var(--bg-inset)",
                  border: `1px solid ${session.is_current ? "rgba(58, 201, 123, 0.3)" : "var(--border)"}`,
                  borderRadius: "8px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <Laptop size={20} color={session.is_current ? "var(--brand-accent)" : "var(--text-dim)"} />
                  <div>
                    <strong style={{ fontSize: "0.9rem", color: "var(--text)", display: "flex", alignItems: "center", gap: 8 }}>
                      {session.device_label}
                      {session.is_current && (
                        <span style={{ fontSize: "0.72rem", background: "rgba(58, 201, 123, 0.2)", color: "var(--mint)", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}>
                          ESTE DISPOSITIVO (SESSÃO ATUAL)
                        </span>
                      )}
                    </strong>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-dim)", display: "block", marginTop: 2 }}>
                      Conectado em: {createdDate} • Último uso: {lastSeen} • Válido até: {expiresDate}
                    </span>
                  </div>
                </div>

                {!session.is_current && (
                  <button
                    className="ghost-button danger"
                    type="button"
                    style={{ padding: "6px 12px", fontSize: "0.8rem" }}
                    onClick={() => revokeSession.mutate(session.id)}
                    disabled={revokeSession.isPending}
                  >
                    Encerrar
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </article>
  );
}

function PersonalAccessTokensCard() {
  const { data: tokens = [], isLoading } = usePersonalAccessTokens();
  const createToken = useCreatePersonalAccessToken();
  const revokeToken = useRevokePersonalAccessToken();

  const [name, setName] = useState("");
  const [expiresInDays, setExpiresInDays] = useState<string>("");
  const [justCreated, setJustCreated] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    createToken.mutate(
      { name: name.trim(), expiresInDays: expiresInDays ? Number(expiresInDays) : null },
      {
        onSuccess: (result) => {
          setJustCreated(result.token);
          setCopied(false);
          setName("");
          setExpiresInDays("");
        },
      },
    );
  }

  function handleCopy() {
    if (!justCreated) return;
    navigator.clipboard.writeText(justCreated);
    setCopied(true);
  }

  return (
    <article className="surface profile-section" style={{ marginTop: "24px" }}>
      <div className="surface-header" style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Terminal size={18} />
        <h3 style={{ margin: 0 }}>Tokens de Acesso Pessoal</h3>
      </div>
      <p style={{ fontSize: "0.85rem", color: "var(--text-dim)", margin: "0 0 16px" }}>
        Para apps externos (ex: Fóton) chamarem a API do Bioma como você, sem depender do cookie de sessão do
        navegador. O token herda exatamente os seus próprios direitos de acesso.
      </p>

      {justCreated && (
        <div
          style={{
            background: "rgba(58, 201, 123, 0.08)",
            border: "1px solid rgba(58, 201, 123, 0.3)",
            borderRadius: 8,
            padding: 12,
            marginBottom: 16,
          }}
        >
          <strong style={{ fontSize: "0.85rem", display: "block", marginBottom: 6 }}>
            Copie agora — ele não será mostrado de novo:
          </strong>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <code style={{ flex: 1, fontSize: "0.8rem", wordBreak: "break-all", background: "var(--bg-inset)", padding: "6px 10px", borderRadius: 6 }}>
              {justCreated}
            </code>
            <button className="mini-button" type="button" onClick={handleCopy}>
              <Copy size={13} /> {copied ? "Copiado!" : "Copiar"}
            </button>
          </div>
        </div>
      )}

      <form onSubmit={handleCreate} style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap", marginBottom: 16 }}>
        <label style={{ fontSize: "0.8rem", flex: 1, minWidth: 180 }}>
          Nome (ex: Fóton)
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Fóton"
            style={{ display: "block", width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, boxSizing: "border-box" }}
            required
          />
        </label>
        <label style={{ fontSize: "0.8rem" }}>
          Expira em (dias, opcional)
          <input
            type="number"
            min={1}
            value={expiresInDays}
            onChange={(e) => setExpiresInDays(e.target.value)}
            placeholder="Nunca expira"
            style={{ display: "block", width: 160, padding: "8px 10px", borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, boxSizing: "border-box" }}
          />
        </label>
        <button className="primary-button" type="submit" disabled={createToken.isPending}>
          {createToken.isPending ? "Gerando..." : "Gerar token"}
        </button>
      </form>

      {isLoading && <p style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>Carregando tokens...</p>}

      {!isLoading && tokens.length === 0 && (
        <p style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>Nenhum token de acesso pessoal criado ainda.</p>
      )}

      {!isLoading && tokens.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {tokens.map((token) => (
            <div
              key={token.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 16px",
                background: "var(--bg-inset)",
                border: "1px solid var(--border)",
                borderRadius: 8,
              }}
            >
              <div>
                <strong style={{ fontSize: "0.9rem", color: "var(--text)" }}>{token.name}</strong>
                <span style={{ fontSize: "0.78rem", color: "var(--text-dim)", display: "block", marginTop: 2 }}>
                  {token.token_prefix}... · criado em {new Date(token.created_at).toLocaleDateString("pt-BR")} ·{" "}
                  {token.last_used_at
                    ? `último uso em ${new Date(token.last_used_at).toLocaleDateString("pt-BR")}`
                    : "nunca usado"}{" "}
                  · {token.expires_at ? `expira em ${new Date(token.expires_at).toLocaleDateString("pt-BR")}` : "sem expiração"}
                </span>
              </div>
              <button
                className="ghost-button danger"
                type="button"
                style={{ padding: "6px 12px", fontSize: "0.8rem" }}
                onClick={() => revokeToken.mutate(token.id)}
                disabled={revokeToken.isPending}
              >
                Revogar
              </button>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
