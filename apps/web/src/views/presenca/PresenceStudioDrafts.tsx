import type { AiContentPost, AiContentRequest, EditorialCalendarItemSummary } from "../../lib/api";

interface PresenceStudioDraftsProps {
  generatedRequests: AiContentRequest[];
  calendarItems: EditorialCalendarItemSummary[];
  canManage: boolean;
  isBusy: boolean;
  onImport: (request: AiContentRequest, postIndex: number) => Promise<void>;
}

export function PresenceStudioDrafts({
  generatedRequests,
  calendarItems,
  canManage,
  isBusy,
  onImport,
}: PresenceStudioDraftsProps) {
  const readyRequests = generatedRequests.filter(
    (req) => req.status === "ready" && req.output?.posts && req.output.posts.length > 0
  );

  if (readyRequests.length === 0) return null;

  return (
    <section className="presence-generated" aria-label="Rascunhos gerados pelo Estúdio IA">
      <div className="presence-generated-header">
        <div>
          <h2>Rascunhos do Estúdio IA</h2>
          <p>
            Peças geradas com inteligência artificial neste workspace. Ao importar, a origem, modelo e parâmetros de
            geração são auditados no calendário.
          </p>
        </div>
      </div>

      <div className="presence-generated-grid">
        {readyRequests.slice(0, 6).flatMap((request) =>
          (request.output?.posts ?? []).map((post: AiContentPost, index: number) => {
            const isImported = calendarItems.some(
              (item) =>
                item.metadata.ai_content_request_id === request.id &&
                item.metadata.output_index === index
            );

            const isLive = request.generation_mode === "live";

            return (
              <article key={`${request.id}-${index}`} className="presence-draft-card">
                <div className="presence-draft-meta">
                  <span className={`presence-source-tag ${isLive ? "live" : "preview"}`}>
                    {isLive ? "Geração ao vivo" : "Prévia/Simulado"} · {request.provider ?? "IA"}
                  </span>
                  <span className="presence-channel-tag">{post.channel}</span>
                </div>

                <strong className="presence-draft-title" title={post.title}>
                  {post.title}
                </strong>

                <p className="presence-draft-snippet">
                  {post.caption ? post.caption.slice(0, 110) + (post.caption.length > 110 ? "…" : "") : "Sem legenda"}
                </p>

                <div className="presence-draft-footer">
                  <small className="presence-format-label">{post.format ?? "social_post"}</small>
                  <button
                    type="button"
                    className="presence-import-button"
                    disabled={!canManage || isBusy || isImported}
                    onClick={() => onImport(request, index)}
                    title={isImported ? "Este rascunho já foi importado para o calendário" : "Adicionar à esteira editorial"}
                  >
                    {isImported ? "✓ Já no calendário" : "+ Adicionar ao calendário"}
                  </button>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
