import { CheckCircle2, GraduationCap, XCircle } from "lucide-react";

import { useAgentSkills, useReviewAgentSkill, useRetireAgentSkill } from "../hooks/useBiomaApi";

/**
 * Fila de revisão de skills propostas pelo copiloto. Nenhuma skill entra em
 * uso sozinha — fica `pending_review` até um admin EG aprovar (decisão do
 * Eduardo, 2026-07-30: mesma cautela da ação visível ao cliente).
 */
export function AgentSkillReviewPanel({ workspaceId }: { workspaceId: string | null }) {
  const { data: pending = [] } = useAgentSkills(workspaceId, true, "pending_review");
  const { data: approved = [] } = useAgentSkills(workspaceId, true, "approved");
  const review = useReviewAgentSkill();
  const retire = useRetireAgentSkill();

  return (
    <article className="surface">
      <div className="surface-header">
        <GraduationCap size={18} />
        <h3>Procedimentos do copiloto (skills)</h3>
      </div>
      <div style={{ padding: "0 20px 20px" }}>
        <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 14 }}>
          Quando o copiloto resolve algo não óbvio que provavelmente vai se repetir, ele propõe um
          procedimento aqui. Só passa a valer depois de aprovado.
        </p>

        <h4 style={{ fontSize: 12, textTransform: "uppercase", color: "var(--text-dim)" }}>
          Aguardando revisão ({pending.length})
        </h4>
        {pending.length === 0 && <p style={{ fontSize: 13, color: "var(--text-dim)" }}>Nada pendente.</p>}
        {pending.map((skill) => (
          <div key={skill.id} style={{ border: "1px solid #ffab00", borderRadius: 8, padding: "10px 14px", marginBottom: 8 }}>
            <strong>{skill.name}</strong>
            <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "4px 0" }}>{skill.description}</p>
            <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, background: "var(--bg-inset)", padding: 8, borderRadius: 6, fontFamily: "inherit" }}>
              {skill.procedure}
            </pre>
            {skill.source_context && (
              <small style={{ color: "var(--text-dim)" }}>Contexto: {skill.source_context}</small>
            )}
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <button
                type="button"
                className="primary"
                disabled={review.isPending}
                onClick={() => review.mutate({ skillId: skill.id, status: "approved" })}
              >
                <CheckCircle2 size={13} /> Aprovar
              </button>
              <button
                type="button"
                disabled={review.isPending}
                onClick={() => review.mutate({ skillId: skill.id, status: "rejected" })}
              >
                <XCircle size={13} /> Rejeitar
              </button>
            </div>
          </div>
        ))}

        {approved.length > 0 && (
          <>
            <h4 style={{ fontSize: 12, textTransform: "uppercase", color: "var(--text-dim)", marginTop: 16 }}>
              Aprovadas ({approved.length})
            </h4>
            <div className="table-list">
              {approved.map((skill) => (
                <div className="table-row" key={skill.id}>
                  <strong style={{ flex: 1 }}>{skill.name}</strong>
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{skill.use_count} uso(s)</span>
                  <button type="button" className="mini-button" disabled={retire.isPending} onClick={() => retire.mutate(skill.id)}>
                    Aposentar
                  </button>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </article>
  );
}
