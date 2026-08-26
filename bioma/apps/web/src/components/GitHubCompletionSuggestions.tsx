import { useQuery } from "@tanstack/react-query";
import { CheckCheck, ExternalLink, GitPullRequestClosed } from "lucide-react";

import { api } from "../lib/api";

/**
 * Decisão 9: a issue fechou no GitHub, a entrega segue aberta no Bioma.
 *
 * **Não há botão de concluir aqui, e isso é a decisão inteira.** Concluir
 * entrega tem efeito contratual e já tem aceite separado de propósito; um botão
 * de um clique nesta lista devolveria pela porta dos fundos exatamente a
 * conclusão automática que a decisão recusou. O painel mostra a divergência e
 * leva à issue — quem conclui é uma pessoa, no lugar onde concluir tem peso.
 *
 * O backend disso existia desde 2026-08-06 e **nenhuma tela consumia**. Ficou
 * calculando sugestão que ninguém via, que é o mesmo que não existir.
 */
export function GitHubCompletionSuggestions({ projectId, enabled }: { projectId: string; enabled: boolean }) {
  const { data, isLoading } = useQuery({
    queryKey: ["github-completion-suggestions", projectId],
    queryFn: () => api.githubCompletionSuggestions(projectId),
    enabled,
    retry: false,
  });

  // Silêncio quando não há divergência: um painel dizendo "nada divergiu" a
  // cada carregamento treina a pessoa a ignorar a área inteira.
  if (!enabled || isLoading || !data || data.suggestions.length === 0) return null;

  return (
    <div
      style={{
        border: "1px solid var(--amber)",
        borderRadius: 8,
        padding: 12,
        marginTop: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <h4 style={{ margin: 0, fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
        <GitPullRequestClosed size={15} aria-hidden style={{ color: "var(--amber)" }} />
        Precisa de você — {data.suggestions.length} entrega
        {data.suggestions.length > 1 ? "s" : ""} com issue já fechada
      </h4>
      <p style={{ fontSize: 11.5, color: "var(--text-faint)", margin: 0, lineHeight: 1.5 }}>
        A issue fechou no GitHub e a entrega continua aberta aqui. O Bioma não conclui
        sozinho: concluir entrega tem efeito contratual e passa pelo aceite de sempre.
      </p>

      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
        {data.suggestions.map((item) => (
          <li key={item.deliverable_id} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
            <CheckCheck size={13} aria-hidden style={{ color: "var(--mint)", flexShrink: 0, marginTop: 2 }} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 12.5 }}>{item.deliverable_title}</div>
              <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 2 }}>
                está como <strong>{item.deliverable_status}</strong> aqui ·{" "}
                {item.issue_url ? (
                  <a href={item.issue_url} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>
                    #{item.issue_number} {item.issue_title}{" "}
                    <ExternalLink size={9} aria-hidden style={{ display: "inline" }} />
                  </a>
                ) : (
                  <>#{item.issue_number} {item.issue_title}</>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>

      {/* Sugestão é calculada na hora, não guardada. Sem a marca de tempo não
          dá para saber se o dado é de agora ou de uma aba aberta ontem. */}
      <small style={{ fontSize: 10.5, color: "var(--text-faint)" }}>
        Lido do GitHub em {new Date(data.checked_at).toLocaleString("pt-BR")} · {data.repository}
      </small>
    </div>
  );
}
