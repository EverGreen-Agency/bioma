import { useState } from "react";
import { Bot, CheckCircle2, Lightbulb, User as UserIcon, XCircle } from "lucide-react";

import {
  useConvertImprovementRequest,
  useImprovementRequests,
  useRejectImprovementRequest,
  useTaskLists,
} from "../hooks/useBiomaApi";

/**
 * Fila de necessidades que o catálogo atual não atende.
 *
 * É caixa de entrada, não board: aprovar **converte em tarefa** e o item sai
 * daqui. Nunca aparece nos dois lugares ao mesmo tempo — foi assim que o
 * Eduardo evitou a sobreposição que ele mesmo apontou.
 */
export function ImprovementQueuePanel({ workspaceId }: { workspaceId: string | null }) {
  const { data: pending = [] } = useImprovementRequests("pending", workspaceId);
  const { data: converted = [] } = useImprovementRequests("converted", workspaceId);
  const { data: lists = [] } = useTaskLists(workspaceId);
  const convert = useConvertImprovementRequest();
  const reject = useRejectImprovementRequest();

  const [listByRequest, setListByRequest] = useState<Record<string, string>>({});

  return (
    <article className="surface">
      <div className="surface-header">
        <Lightbulb size={18} />
        <h3>Melhorias solicitadas ({pending.length})</h3>
      </div>
      <div style={{ padding: "0 20px 20px" }}>
        <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 14 }}>
          Necessidades que o catálogo atual não resolve. Aprovar vira <strong>tarefa</strong> com
          prazo e responsável — entrega esperada pelo cliente nasce visível no board dele;
          melhoria interna nasce escondida.
        </p>

        {pending.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--text-dim)" }}>Nada aguardando revisão.</p>
        )}

        {pending.map((item) => (
          <div
            key={item.id}
            style={{ border: "1px solid #ffab00", borderRadius: 8, padding: "12px 14px", marginBottom: 10 }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <strong style={{ flex: 1 }}>{item.title}</strong>
              <span
                title={item.proposed_by ? "Registrado por uma pessoa" : "Percebido pelo copiloto"}
                style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11, color: item.proposed_by ? "var(--text-dim)" : "var(--accent)" }}
              >
                {item.proposed_by ? <UserIcon size={12} /> : <Bot size={12} />}
                {item.proposed_by ? "humano" : "copiloto"}
              </span>
              <span
                style={{
                  fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 999,
                  background: item.client_deliverable ? "rgba(46,158,91,0.14)" : "rgba(127,127,127,0.14)",
                  color: item.client_deliverable ? "#2e9e5b" : "var(--text-dim)",
                }}
              >
                {item.client_deliverable ? "entrega do cliente" : "interna"}
              </span>
            </div>

            <p style={{ fontSize: 13, margin: "6px 0" }}>{item.need}</p>

            {item.evidence && (
              <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "4px 0", paddingLeft: 8, borderLeft: "2px solid var(--border)" }}>
                <strong>Evidência:</strong> {item.evidence}
              </p>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap", alignItems: "center" }}>
              <select
                value={listByRequest[item.id] ?? ""}
                onChange={(e) => setListByRequest((current) => ({ ...current, [item.id]: e.target.value }))}
                style={{ fontSize: 12 }}
              >
                <option value="">Escolha a frente...</option>
                {lists.map((list) => (
                  <option key={list.id} value={list.id}>{list.name}</option>
                ))}
              </select>
              <button
                type="button"
                className="primary"
                disabled={convert.isPending || !listByRequest[item.id]}
                onClick={() => convert.mutate({ requestId: item.id, listId: listByRequest[item.id] })}
              >
                <CheckCircle2 size={13} /> Virar tarefa
              </button>
              <button type="button" disabled={reject.isPending} onClick={() => reject.mutate({ requestId: item.id })}>
                <XCircle size={13} /> Rejeitar
              </button>
            </div>
          </div>
        ))}

        {converted.length > 0 && (
          <>
            <h4 style={{ fontSize: 12, textTransform: "uppercase", color: "var(--text-dim)", marginTop: 16 }}>
              Já viraram tarefa ({converted.length})
            </h4>
            <div className="table-list">
              {converted.slice(0, 8).map((item) => (
                <div className="table-row" key={item.id}>
                  <strong style={{ flex: 1 }}>{item.title}</strong>
                  <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    {item.client_deliverable ? "entrega do cliente" : "interna"}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}

        {(convert.isError || reject.isError) && (
          <div className="notice error" style={{ marginTop: 8 }}>
            {(convert.error ?? reject.error) instanceof Error
              ? (convert.error ?? reject.error)!.message
              : "Falha ao processar a requisição."}
          </div>
        )}
      </div>
    </article>
  );
}
