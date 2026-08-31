import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BriefcaseBusiness, Plus, Trash2, UserPlus, UsersRound } from "lucide-react";
import {
  api,
  type TeamRole,
  type WorkspaceAssignmentRole,
} from "../lib/api";
import { useCurrentUser } from "../hooks/useBiomaApi";

const workspaceRoleLabels: Record<WorkspaceAssignmentRole, string> = {
  workspace_manager: "Gestão do workspace",
  operator: "Operação",
  approver: "Aprovação",
  viewer: "Leitura",
};

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Não foi possível concluir a operação.";
}

export function TeamPortfolioManager() {
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const { data: workspaces = [], isLoading: loadingWorkspaces } = useQuery({
    queryKey: ["workspaces"],
    queryFn: api.workspaces,
  });
  const tenantId = workspaces.find((workspace) => workspace.kind === "agency_internal")?.tenant_organization_id
    ?? workspaces[0]?.tenant_organization_id
    ?? null;
  const clientWorkspaces = useMemo(
    () => workspaces.filter((workspace) => workspace.kind === "client" && workspace.tenant_organization_id === tenantId),
    [tenantId, workspaces],
  );

  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [newTeamName, setNewTeamName] = useState("");
  const [memberUserId, setMemberUserId] = useState("");
  const [memberRole, setMemberRole] = useState<TeamRole>("member");
  const [assignmentRole, setAssignmentRole] = useState<WorkspaceAssignmentRole>("workspace_manager");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const { data: teams = [], isLoading: loadingTeams } = useQuery({
    queryKey: ["teams", tenantId],
    queryFn: () => api.teams(tenantId!),
    enabled: Boolean(tenantId),
  });
  const { data: tenantMembers = [] } = useQuery({
    queryKey: ["tenant-members", tenantId],
    queryFn: () => api.tenantMembers(tenantId!),
    enabled: Boolean(tenantId),
  });
  const { data: teamMembers = [] } = useQuery({
    queryKey: ["team-members", selectedTeamId],
    queryFn: () => api.teamMembers(selectedTeamId),
    enabled: Boolean(selectedTeamId),
  });
  const { data: assignments = [] } = useQuery({
    queryKey: ["workspace-assignments", selectedWorkspaceId],
    queryFn: () => api.workspaceAssignments(selectedWorkspaceId),
    enabled: Boolean(selectedWorkspaceId),
  });

  useEffect(() => {
    if (!selectedTeamId || !teams.some((team) => team.id === selectedTeamId)) {
      setSelectedTeamId(teams[0]?.id ?? "");
    }
  }, [selectedTeamId, teams]);

  useEffect(() => {
    if (!selectedWorkspaceId || !clientWorkspaces.some((workspace) => workspace.id === selectedWorkspaceId)) {
      setSelectedWorkspaceId(clientWorkspaces[0]?.id ?? "");
    }
  }, [clientWorkspaces, selectedWorkspaceId]);

  const selectedTeam = teams.find((team) => team.id === selectedTeamId) ?? null;
  const selectedWorkspace = clientWorkspaces.find((workspace) => workspace.id === selectedWorkspaceId) ?? null;
  const currentUserIsTenantMember = tenantMembers.some((member) => member.user_id === user?.id);

  function startAction() {
    setError("");
    setNotice("");
  }

  const createTeam = useMutation({
    mutationFn: () => api.createTeam(tenantId!, newTeamName.trim()),
    onSuccess: async (team) => {
      setNewTeamName("");
      setSelectedTeamId(team.id);
      setNotice(`Time ${team.name} criado.`);
      await queryClient.invalidateQueries({ queryKey: ["teams", tenantId] });
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  });

  const enableCurrentUser = useMutation({
    mutationFn: () => api.upsertTenantMember(tenantId!, user!.id, "tenant_admin"),
    onSuccess: (members) => {
      queryClient.setQueryData(["tenant-members", tenantId], members);
      setNotice("Seu usuário foi habilitado como administrador da operação.");
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  });

  const addTeamMember = useMutation({
    mutationFn: () => api.upsertTeamMember(selectedTeamId, memberUserId, memberRole),
    onSuccess: async (members) => {
      queryClient.setQueryData(["team-members", selectedTeamId], members);
      setMemberUserId("");
      setNotice("Membro associado ao time.");
      await queryClient.invalidateQueries({ queryKey: ["teams", tenantId] });
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  });

  const removeTeamMember = useMutation({
    mutationFn: (userId: string) => api.deleteTeamMember(selectedTeamId, userId),
    onSuccess: async (members) => {
      queryClient.setQueryData(["team-members", selectedTeamId], members);
      setNotice("Membro removido do time.");
      await queryClient.invalidateQueries({ queryKey: ["teams", tenantId] });
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  });

  const assignTeam = useMutation({
    mutationFn: () => api.upsertWorkspaceAssignment(selectedWorkspaceId, {
      team_id: selectedTeamId,
      role: assignmentRole,
    }),
    onSuccess: async (nextAssignments) => {
      queryClient.setQueryData(["workspace-assignments", selectedWorkspaceId], nextAssignments);
      setNotice(`${selectedTeam?.name ?? "Time"} associado a ${selectedWorkspace?.name ?? "workspace"}.`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["teams", tenantId] }),
        queryClient.invalidateQueries({ queryKey: ["workspaces"] }),
      ]);
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  });

  const removeAssignment = useMutation({
    mutationFn: (assignmentId: string) => api.deleteWorkspaceAssignment(selectedWorkspaceId, assignmentId),
    onSuccess: async (nextAssignments) => {
      queryClient.setQueryData(["workspace-assignments", selectedWorkspaceId], nextAssignments);
      setNotice("Atribuição removida da carteira.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["teams", tenantId] }),
        queryClient.invalidateQueries({ queryKey: ["workspaces"] }),
      ]);
    },
    onError: (mutationError) => setError(errorMessage(mutationError)),
  });

  function handleCreateTeam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    startAction();
    if (newTeamName.trim()) createTeam.mutate();
  }

  if (loadingWorkspaces || loadingTeams) return <div className="notice">Carregando estrutura operacional...</div>;
  if (!tenantId) return <div className="notice">Nenhuma organização operadora foi encontrada para esta conta.</div>;

  return (
    <div style={{ gridColumn: "1 / -1", display: "grid", gap: 18 }}>
      <article className="surface profile-section">
        <div className="surface-header">
          <UsersRound size={18} />
          <div>
            <h3>Equipes & carteiras</h3>
            <p className="panel-footnote" style={{ margin: "4px 0 0" }}>
              Estruture a operação da agência sem misturá-la aos hubs dos clientes.
            </p>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginTop: 16 }}>
          <div className="notice"><strong>{teams.length}</strong><br />times operacionais</div>
          <div className="notice"><strong>{tenantMembers.length}</strong><br />membros habilitados</div>
          <div className="notice"><strong>{clientWorkspaces.length}</strong><br />workspaces de clientes</div>
        </div>
        {!currentUserIsTenantMember && user && (
          <div className="notice" style={{ marginTop: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <span>Habilite seu usuário para também aparecer nas opções de alocação dos times.</span>
            <button
              type="button"
              className="mini-button"
              disabled={enableCurrentUser.isPending}
              onClick={() => { startAction(); enableCurrentUser.mutate(); }}
            >
              <UserPlus size={13} /> Habilitar meu usuário
            </button>
          </div>
        )}
        {error && <div className="form-error" style={{ marginTop: 12 }}>{error}</div>}
        {notice && <div className="form-success" style={{ marginTop: 12 }}>{notice}</div>}
      </article>

      <div className="team-manager-split">
        <article className="surface profile-section">
          <div className="surface-header"><UsersRound size={18} /><h3>Times</h3></div>
          <form onSubmit={handleCreateTeam} style={{ display: "flex", gap: 8, margin: "16px 0" }}>
            <input
              value={newTeamName}
              onChange={(event) => setNewTeamName(event.target.value)}
              placeholder="Ex.: Célula Growth"
              maxLength={120}
              aria-label="Nome do novo time"
              style={{ flex: 1 }}
            />
            <button className="mini-button" type="submit" disabled={!newTeamName.trim() || createTeam.isPending}>
              <Plus size={14} /> Criar
            </button>
          </form>
          <div className="timeline-list">
            {teams.map((team) => (
              <button
                key={team.id}
                type="button"
                className="timeline-row"
                onClick={() => setSelectedTeamId(team.id)}
                style={{ width: "100%", textAlign: "left", cursor: "pointer", borderColor: team.id === selectedTeamId ? "var(--brand-accent)" : undefined }}
              >
                <span>{team.id === selectedTeamId ? "Selecionado" : "Time"}</span>
                <strong>{team.name}</strong>
                <small>{team.members_total} membros · {team.workspaces_total} workspaces</small>
              </button>
            ))}
            {!teams.length && <div className="notice">Crie o primeiro time para segmentar a carteira.</div>}
          </div>
        </article>

        <article className="surface profile-section">
          <div className="surface-header"><UserPlus size={18} /><h3>Membros de {selectedTeam?.name ?? "um time"}</h3></div>
          {selectedTeam ? (
            <>
              <div className="team-member-controls">
                <select value={memberUserId} onChange={(event) => setMemberUserId(event.target.value)} aria-label="Membro da operação">
                  <option value="">Selecione um membro</option>
                  {tenantMembers.map((member) => <option key={member.user_id} value={member.user_id}>{member.display_name}</option>)}
                </select>
                <select value={memberRole} onChange={(event) => setMemberRole(event.target.value as TeamRole)} aria-label="Papel no time">
                  <option value="member">Membro</option>
                  <option value="manager">Gestor</option>
                </select>
                <button
                  type="button"
                  className="mini-button"
                  disabled={!memberUserId || addTeamMember.isPending}
                  onClick={() => { startAction(); addTeamMember.mutate(); }}
                >Adicionar</button>
              </div>
              <div className="timeline-list">
                {teamMembers.map((member) => (
                  <div className="timeline-row" key={member.user_id}>
                    <span>{member.role === "manager" ? "Gestor" : "Membro"}</span>
                    <strong>{member.display_name}</strong>
                    <small>{member.email}</small>
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={`Remover ${member.display_name}`}
                      onClick={() => { startAction(); removeTeamMember.mutate(member.user_id); }}
                    ><Trash2 size={14} /></button>
                  </div>
                ))}
                {!teamMembers.length && <div className="notice">Este time ainda não possui membros.</div>}
              </div>
            </>
          ) : <div className="notice" style={{ marginTop: 16 }}>Selecione ou crie um time.</div>}
        </article>
      </div>

      <article className="surface profile-section">
        <div className="surface-header"><BriefcaseBusiness size={18} /><h3>Distribuição da carteira</h3></div>
        <p className="panel-footnote">
          Um cliente pode ter mais de um time ou responsável. A visão “Minha carteira” respeita estas atribuições.
        </p>
        <div className="team-assignment-controls">
          <select value={selectedWorkspaceId} onChange={(event) => setSelectedWorkspaceId(event.target.value)} aria-label="Workspace do cliente">
            <option value="">Selecione o cliente</option>
            {clientWorkspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
          </select>
          <select value={selectedTeamId} onChange={(event) => setSelectedTeamId(event.target.value)} aria-label="Time responsável">
            <option value="">Selecione o time</option>
            {teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
          </select>
          <select value={assignmentRole} onChange={(event) => setAssignmentRole(event.target.value as WorkspaceAssignmentRole)} aria-label="Responsabilidade no workspace">
            {Object.entries(workspaceRoleLabels).map(([role, label]) => <option key={role} value={role}>{label}</option>)}
          </select>
          <button
            type="button"
            className="primary-button"
            disabled={!selectedWorkspaceId || !selectedTeamId || assignTeam.isPending}
            onClick={() => { startAction(); assignTeam.mutate(); }}
          >Atribuir</button>
        </div>
        <div className="timeline-list">
          {assignments.map((assignment) => (
            <div className="timeline-row" key={assignment.id}>
              <span>{workspaceRoleLabels[assignment.role]}</span>
              <strong>{assignment.assignee_name}</strong>
              <small>{assignment.assignee_email ?? selectedWorkspace?.name}</small>
              <button
                type="button"
                className="icon-button"
                aria-label={`Remover atribuição de ${assignment.assignee_name}`}
                onClick={() => { startAction(); removeAssignment.mutate(assignment.id); }}
              ><Trash2 size={14} /></button>
            </div>
          ))}
          {selectedWorkspaceId && !assignments.length && <div className="notice">Este workspace ainda não tem responsáveis explícitos.</div>}
          {!clientWorkspaces.length && <div className="notice">Nenhum workspace de cliente disponível para distribuição.</div>}
        </div>
      </article>
    </div>
  );
}
