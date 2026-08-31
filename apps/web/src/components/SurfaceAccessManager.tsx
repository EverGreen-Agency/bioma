import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, UsersRound, User as UserIcon } from "lucide-react";
import { api, type SurfaceGrantEffect } from "../lib/api";
import {
  useSurfaceCatalog,
  useTeamSurfaceGrants,
  useUserSurfaceGrants,
  useUpsertTeamSurfaceGrant,
  useUpsertUserSurfaceGrant,
  useClearTeamSurfaceGrant,
  useClearUserSurfaceGrant,
} from "../hooks/useBiomaApi";

type SubjectKind = "team" | "user";

/** Estado de uma superfície para o sujeito escolhido. `inherit` = sem exceção:
 * vale o nível de cima. É o default e o botão de "desfazer". */
type Choice = "inherit" | "allow" | "deny";

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Não foi possível concluir a operação.";
}

/** Acesso a telas por equipe e por pessoa (decisão 11, níveis 2 e 3).
 *
 * Aqui se concede e se nega de verdade — diferente da preferência pessoal, que
 * só organiza a própria tela. Por isso a ordem de precedência fica escrita na
 * interface: quem administra precisa saber que a pessoa vence a equipe e que
 * nenhum dos dois passa por cima do que a organização contratou. */
export function SurfaceAccessManager() {
  const [subjectKind, setSubjectKind] = useState<SubjectKind>("team");
  const [teamId, setTeamId] = useState("");
  const [userId, setUserId] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  const { data: workspaces = [] } = useQuery({ queryKey: ["workspaces"], queryFn: api.workspaces });
  const tenantId =
    workspaces.find((workspace) => workspace.kind === "agency_internal")?.tenant_organization_id ??
    workspaces[0]?.tenant_organization_id ??
    null;

  const { data: teams = [] } = useQuery({
    queryKey: ["teams", tenantId],
    queryFn: () => api.teams(tenantId as string),
    enabled: Boolean(tenantId),
  });
  const { data: tenantMembers = [] } = useQuery({
    queryKey: ["tenant-members", tenantId],
    queryFn: () => api.tenantMembers(tenantId as string),
    enabled: Boolean(tenantId),
  });

  const { data: catalog = [], isLoading: loadingCatalog } = useSurfaceCatalog();
  const { data: teamGrants = [] } = useTeamSurfaceGrants(subjectKind === "team" ? teamId || null : null);
  const { data: userGrants = [] } = useUserSurfaceGrants(subjectKind === "user" ? userId || null : null);

  const upsertTeam = useUpsertTeamSurfaceGrant();
  const upsertUser = useUpsertUserSurfaceGrant();
  const clearTeam = useClearTeamSurfaceGrant();
  const clearUser = useClearUserSurfaceGrant();

  useEffect(() => {
    if (!teamId && teams.length > 0) setTeamId(teams[0].id);
  }, [teams, teamId]);
  useEffect(() => {
    if (!userId && tenantMembers.length > 0) setUserId(tenantMembers[0].user_id);
  }, [tenantMembers, userId]);

  const grants = subjectKind === "team" ? teamGrants : userGrants;
  const currentChoice = useMemo(() => {
    const map = new Map<string, Choice>();
    for (const grant of grants) map.set(grant.surface_key, grant.effect as Choice);
    return map;
  }, [grants]);

  const subjectReady = subjectKind === "team" ? Boolean(teamId) : Boolean(userId);
  const busy = upsertTeam.isPending || upsertUser.isPending || clearTeam.isPending || clearUser.isPending;

  function apply(surfaceKey: string, choice: Choice) {
    setError("");
    const trimmed = note.trim() || null;
    const onError = (err: unknown) => setError(errorMessage(err));

    if (choice === "inherit") {
      if (subjectKind === "team") clearTeam.mutate({ teamId, surfaceKey }, { onError });
      else clearUser.mutate({ userId, surfaceKey }, { onError });
      return;
    }
    const effect = choice as SurfaceGrantEffect;
    if (subjectKind === "team") upsertTeam.mutate({ teamId, surfaceKey, effect, note: trimmed }, { onError });
    else upsertUser.mutate({ userId, surfaceKey, effect, note: trimmed }, { onError });
  }

  const groups = new Map<string, typeof catalog>();
  for (const entry of catalog) {
    const list = groups.get(entry.group) ?? [];
    list.push(entry);
    groups.set(entry.group, list);
  }

  const exceptionCount = grants.length;

  return (
    <article className="surface profile-section">
      <div className="surface-header">
        <ShieldCheck size={18} />
        <h3>Acesso a telas</h3>
      </div>

      <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 8px", lineHeight: 1.5 }}>
        Define o que uma equipe inteira ou uma pessoa enxerga, sem configurar
        um a um. Isto é permissão: quem perde o acesso vê o motivo e não
        consegue reverter sozinho.
      </p>
      <p style={{ fontSize: 12, color: "var(--text-faint)", margin: "0 0 16px", lineHeight: 1.5 }}>
        Ordem de precedência: <strong>a pessoa vence a equipe</strong>; entre
        duas equipes, a mais restritiva vence; e nenhum dos dois libera módulo
        que a organização do cliente não contratou.
      </p>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            className={subjectKind === "team" ? "primary-button" : "ghost-button"}
            onClick={() => setSubjectKind("team")}
          >
            <UsersRound size={15} /> Equipe
          </button>
          <button
            type="button"
            className={subjectKind === "user" ? "primary-button" : "ghost-button"}
            onClick={() => setSubjectKind("user")}
          >
            <UserIcon size={15} /> Pessoa
          </button>
        </div>

        {subjectKind === "team" ? (
          <label style={{ display: "grid", gap: 6, minWidth: 240 }}>
            Equipe
            <select className="status-select" value={teamId} onChange={(event) => setTeamId(event.target.value)}>
              {teams.length === 0 && <option value="">Nenhuma equipe cadastrada</option>}
              {teams.map((team) => (
                <option key={team.id} value={team.id}>{team.name}</option>
              ))}
            </select>
          </label>
        ) : (
          <label style={{ display: "grid", gap: 6, minWidth: 240 }}>
            Pessoa
            <select className="status-select" value={userId} onChange={(event) => setUserId(event.target.value)}>
              {tenantMembers.length === 0 && <option value="">Nenhum membro encontrado</option>}
              {tenantMembers.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {member.display_name} ({member.email})
                </option>
              ))}
            </select>
          </label>
        )}

        <label style={{ display: "grid", gap: 6, flex: 1, minWidth: 240 }}>
          Motivo (opcional — aparece para quem perdeu o acesso)
          <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Ex: equipe não cuida de RH" />
        </label>
      </div>

      {error && <p style={{ fontSize: 13, color: "var(--danger)", marginBottom: 12 }}>{error}</p>}
      {subjectReady && (
        <p style={{ fontSize: 12, color: "var(--text-faint)", marginBottom: 12 }}>
          {exceptionCount === 0
            ? "Sem exceções: este sujeito herda tudo do nível de cima."
            : `${exceptionCount} exceção${exceptionCount > 1 ? "ões" : ""} definida${exceptionCount > 1 ? "s" : ""}.`}
        </p>
      )}

      {loadingCatalog && <p style={{ fontSize: 13, color: "var(--text-muted)" }}>Carregando catálogo de telas...</p>}
      {!subjectReady && !loadingCatalog && (
        <div className="notice">Selecione uma equipe ou pessoa para definir o acesso.</div>
      )}

      {subjectReady && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {[...groups.entries()].map(([group, entries]) => (
            <div key={group}>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-faint)", marginBottom: 8 }}>
                {group}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {entries.map((entry) => {
                  const choice = currentChoice.get(entry.surface_key) ?? "inherit";
                  return (
                    <div
                      key={entry.surface_key}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 12,
                        padding: "10px 12px",
                        background: "var(--bg-elevated)",
                        borderRadius: 8,
                        border: "1px solid var(--border-light)",
                      }}
                    >
                      <div style={{ minWidth: 0 }}>
                        <strong style={{ fontSize: 13.5 }}>{entry.label}</strong>
                        <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 2 }}>
                          {entry.surface_key}
                          {entry.locked && " · sempre disponível"}
                          {entry.module && ` · módulo ${entry.module}`}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                        {(["inherit", "allow", "deny"] as Choice[]).map((option) => (
                          <button
                            key={option}
                            type="button"
                            className={choice === option ? "mini-button approve" : "mini-button"}
                            disabled={busy || (entry.locked && option === "deny")}
                            title={
                              entry.locked && option === "deny"
                                ? "Esta tela não pode ser bloqueada"
                                : undefined
                            }
                            onClick={() => apply(entry.surface_key, option)}
                          >
                            {option === "inherit" ? "Herda" : option === "allow" ? "Liberado" : "Escondido"}
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
