import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, UserRound } from "lucide-react";
import { api } from "../lib/api";

/** Quem é da EG.
 *
 * Substitui o bloco que mostrava só "Você" — quem convidava alguém não via a
 * pessoa em lugar nenhum, o que fazia o convite parecer não ter funcionado.
 *
 * Lê de `memberships` (o que o convite cria), não de `tenant_memberships`:
 * alguém convidado sem papel de tenant existe e precisa aparecer. */
export function OrganizationPeopleList({
  tenantOrganizationId,
  currentUserId,
}: {
  tenantOrganizationId: string | null;
  currentUserId: string;
}) {
  const { data: people = [], isLoading, isError } = useQuery({
    queryKey: ["organization-people", tenantOrganizationId],
    queryFn: () => api.organizationPeople(tenantOrganizationId as string),
    enabled: Boolean(tenantOrganizationId),
  });

  if (isLoading) return <p style={{ fontSize: 13, color: "var(--text-muted)" }}>Carregando a equipe...</p>;
  if (isError) return <p style={{ fontSize: 13, color: "var(--danger)" }}>Não foi possível carregar a equipe.</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-faint)" }}>
        Equipe · {people.length}
      </div>

      {people.map((person) => (
        <div
          key={person.user_id}
          style={{
            display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12,
            padding: "10px 12px", background: "var(--bg-elevated)", borderRadius: 8,
            border: "1px solid var(--border-light)", opacity: person.is_active ? 1 : 0.6,
          }}
        >
          <div style={{ minWidth: 0 }}>
            <strong style={{ fontSize: 13.5 }}>
              {person.display_name}
              {person.user_id === currentUserId && (
                <span style={{ fontSize: 11, color: "var(--text-faint)", fontWeight: 400 }}> · você</span>
              )}
            </strong>
            <div style={{ fontSize: 11.5, color: "var(--text-faint)", marginTop: 2 }}>
              {person.email}
              {person.teams.length > 0 && ` · ${person.teams.join(", ")}`}
              {!person.is_active && " · inativo"}
            </div>
          </div>
          <span
            style={{
              display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11,
              padding: "3px 9px", borderRadius: 999, whiteSpace: "nowrap",
              border: `1px solid ${person.role === "eg_admin" ? "var(--mint)" : "var(--border-light)"}`,
              color: person.role === "eg_admin" ? "var(--mint)" : "var(--text-muted)",
            }}
          >
            {person.role === "eg_admin" ? <ShieldCheck size={12} /> : <UserRound size={12} />}
            {person.role === "eg_admin" ? "Administrador" : person.role === "eg_member" ? "Membro" : person.role}
          </span>
        </div>
      ))}

      <p style={{ fontSize: 11.5, color: "var(--text-faint)", margin: "4px 0 0", lineHeight: 1.5 }}>
        <strong>Membro</strong> usa a plataforma; <strong>administrador</strong>{" "}
        também convida gente e mexe em acessos e integrações.
      </p>
    </div>
  );
}
