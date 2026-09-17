import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Trash2, UserPlus } from "lucide-react";
import { api, type InviteCreated, type TenantRole } from "../lib/api";

const tenantRoleLabels: Record<TenantRole, string> = {
  tenant_admin: "Administração do tenant",
  operator: "Operação",
  approver: "Aprovação",
  viewer: "Leitura",
};

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Não foi possível concluir a operação.";
}

/** Convite de pessoa para o time da EG.
 *
 * Substitui o "Funcionalidade em breve" que estava aqui — e que era honesto,
 * porque convite só existia por cliente. O link gerado é o mesmo fluxo público
 * de sempre; o que muda é que o aceite coloca a pessoa na organização da EG e
 * já na equipe escolhida.
 *
 * O link aparece UMA vez: ele é o segredo. Guardamos só o hash, então não há
 * como reexibir depois — e é por isso que a tela insiste na cópia. */
export function TeamInviteCard({ tenantOrganizationId }: { tenantOrganizationId: string | null }) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [teamId, setTeamId] = useState("");
  const [tenantRole, setTenantRole] = useState<TenantRole | "">("");
  // Default `eg_member`: administrador tem que ser escolha explicita (0090).
  const [orgRole, setOrgRole] = useState<"eg_member" | "eg_admin">("eg_member");
  const [created, setCreated] = useState<InviteCreated | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const { data: teams = [] } = useQuery({
    queryKey: ["teams", tenantOrganizationId],
    queryFn: () => api.teams(tenantOrganizationId as string),
    enabled: Boolean(tenantOrganizationId),
  });
  const { data: invites = [] } = useQuery({
    queryKey: ["team-invites", tenantOrganizationId],
    queryFn: () => api.teamInvites(tenantOrganizationId as string),
    enabled: Boolean(tenantOrganizationId),
  });

  const createInvite = useMutation({
    mutationFn: () => api.createTeamInvite(tenantOrganizationId as string, {
      email: email.trim() || null,
      role: orgRole,
      team_id: teamId || null,
      tenant_role: tenantRole || null,
    }),
    onSuccess: (invite) => {
      setCreated(invite);
      setEmail("");
      setCopied(false);
      queryClient.invalidateQueries({ queryKey: ["team-invites", tenantOrganizationId] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const revokeInvite = useMutation({
    mutationFn: (inviteId: string) => api.revokeTeamInvite(tenantOrganizationId as string, inviteId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["team-invites", tenantOrganizationId] }),
    onError: (err) => setError(errorMessage(err)),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    createInvite.mutate();
  }

  function handleCopy() {
    if (!created) return;
    navigator.clipboard.writeText(`${window.location.origin}${created.path}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  }

  const pending = invites.filter((invite) => !invite.used_at);

  if (!tenantOrganizationId) {
    return <div className="notice">Organização da agência não encontrada.</div>;
  }

  return (
    <article className="surface profile-section">
      <div className="surface-header">
        <UserPlus size={18} />
        <h3>Convidar para o time</h3>
      </div>

      <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 16px", lineHeight: 1.5 }}>
        A pessoa recebe um link, cria a própria senha e já entra na equipe
        escolhida. Diferente do convite de cliente: aqui ela entra na EverGreen.
        <br />
        <strong>Membro</strong> usa a plataforma; <strong>administrador</strong>{" "}
        também convida gente e mexe em acessos e integrações. Na dúvida, membro —
        promover depois é um clique, tirar poder já concedido é conversa.
      </p>

      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          E-mail (opcional)
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="pessoa@evergreenmkt.com.br"
          />
        </label>
        <label>
          Equipe
          <select className="status-select" value={teamId} onChange={(event) => setTeamId(event.target.value)}>
            <option value="">Sem equipe</option>
            {teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
          </select>
        </label>
        <label>
          Acesso na EverGreen
          <select
            className="status-select"
            value={orgRole}
            onChange={(event) => setOrgRole(event.target.value as "eg_member" | "eg_admin")}
          >
            <option value="eg_member">Membro — usa a plataforma</option>
            <option value="eg_admin">Administrador — convida e gerencia acessos</option>
          </select>
        </label>
        <label>
          Papel no workspace
          <select
            className="status-select"
            value={tenantRole}
            onChange={(event) => setTenantRole(event.target.value as TenantRole | "")}
          >
            <option value="">Sem papel definido</option>
            {(Object.keys(tenantRoleLabels) as TenantRole[]).map((role) => (
              <option key={role} value={role}>{tenantRoleLabels[role]}</option>
            ))}
          </select>
        </label>
        <div className="modal-actions" style={{ gridColumn: "1 / -1" }}>
          <button className="primary-button" type="submit" disabled={createInvite.isPending}>
            <UserPlus size={15} /> {createInvite.isPending ? "Gerando..." : "Gerar convite"}
          </button>
        </div>
      </form>

      {error && <p style={{ fontSize: 13, color: "var(--danger)", marginTop: 12 }}>{error}</p>}

      {created && (
        <div style={{ marginTop: 16, padding: 14, background: "var(--bg-elevated)", borderRadius: 8, border: "1px solid var(--mint)" }}>
          <strong style={{ fontSize: 13.5 }}>Link do convite</strong>
          <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "4px 0 10px" }}>
            Copie agora — ele não é exibido de novo. Guardamos só o hash, então
            não dá para recuperá-lo depois; se perder, revogue e gere outro.
          </p>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <code style={{ fontSize: 12, wordBreak: "break-all", flex: 1, minWidth: 240 }}>
              {window.location.origin}{created.path}
            </code>
            <button type="button" className="mini-button" onClick={handleCopy}>
              {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copiado" : "Copiar"}
            </button>
          </div>
        </div>
      )}

      {pending.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-faint)", marginBottom: 8 }}>
            Convites pendentes
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {pending.map((invite) => {
              const team = teams.find((candidate) => candidate.id === invite.team_id);
              return (
                <div
                  key={invite.id}
                  style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12,
                    padding: "10px 12px", background: "var(--bg-elevated)", borderRadius: 8,
                    border: "1px solid var(--border-light)",
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <strong style={{ fontSize: 13 }}>{invite.email ?? "Convite sem e-mail"}</strong>
                    <div style={{ fontSize: 11.5, color: "var(--text-faint)", marginTop: 2 }}>
                      {team ? `Equipe ${team.name}` : "Sem equipe"}
                      {invite.tenant_role ? ` · ${tenantRoleLabels[invite.tenant_role]}` : ""}
                      {` · expira ${new Date(invite.expires_at).toLocaleDateString("pt-BR")}`}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="mini-button"
                    onClick={() => revokeInvite.mutate(invite.id)}
                    disabled={revokeInvite.isPending}
                  >
                    <Trash2 size={14} /> Revogar
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </article>
  );
}
