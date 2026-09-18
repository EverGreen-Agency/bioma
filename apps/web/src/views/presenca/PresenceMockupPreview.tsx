import { useState } from "react";
import { CHANNEL_LABELS, type Draft } from "./types";
import type { WorkspaceSummary } from "../../lib/api";

interface PresenceMockupPreviewProps {
  draft: Draft;
  workspace: WorkspaceSummary;
}

export function PresenceMockupPreview({ draft, workspace }: PresenceMockupPreviewProps) {
  const [activeChannel, setActiveChannel] = useState<Draft["channel"]>(draft.channel);

  const channel = activeChannel || draft.channel;
  const scheduledLabel = draft.scheduled_at
    ? new Date(draft.scheduled_at).toLocaleString("pt-BR", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Data a definir";

  // Parse hashtags from text or campaign tags
  const tags = draft.metadata?.campaign_tags ?? [];
  const text = draft.post_text ?? "";

  return (
    <div className="presence-preview-container">
      <div className="presence-preview-topbar">
        <span className="presence-preview-badge">Pré-visualização da Peça</span>
        <div className="presence-channel-selector-pills">
          {(["instagram", "linkedin", "facebook", "tiktok", "youtube", "blog"] as const).map((ch) => (
            <button
              key={ch}
              type="button"
              className={`presence-channel-btn ${ch === channel ? "active" : ""}`}
              onClick={() => setActiveChannel(ch)}
            >
              {CHANNEL_LABELS[ch]}
            </button>
          ))}
        </div>
      </div>

      <div className="presence-mockup-frame">
        {channel === "instagram" && (
          <div className="presence-mockup-instagram">
            <div className="insta-header">
              <div className="insta-avatar">{workspace.name.charAt(0).toUpperCase()}</div>
              <div className="insta-user-meta">
                <strong>{workspace.slug || workspace.name.toLowerCase().replace(/\s+/g, "_")}</strong>
                <small>{scheduledLabel} · Programado</small>
              </div>
              <span className="insta-dots">•••</span>
            </div>

            <div className="insta-media-container">
              {draft.media_urls.length > 0 ? (
                <img
                  src={draft.media_urls[0]}
                  alt={draft.title}
                  className="insta-media-image"
                  onError={(e) => {
                    // Fallback to placeholder if url fails
                    (e.target as HTMLElement).style.display = "none";
                  }}
                />
              ) : (
                <div className="insta-media-placeholder">
                  <span className="insta-placeholder-icon">📸</span>
                  <strong>{draft.title || "Título da publicação"}</strong>
                  <small>Formato: {draft.content_type}</small>
                </div>
              )}
            </div>

            <div className="insta-actions-bar">
              <div className="insta-actions-left">
                <span title="Curtir">❤️</span>
                <span title="Comentar">💬</span>
                <span title="Enviar">✈️</span>
              </div>
              <div className="insta-actions-right">
                <span title="Salvar">🔖</span>
              </div>
            </div>

            <div className="insta-caption-box">
              <p>
                <strong>{workspace.slug || workspace.name.toLowerCase().replace(/\s+/g, "_")}</strong>{" "}
                {text ? (
                  <span className="insta-text-content">{text}</span>
                ) : (
                  <span className="insta-placeholder-text">Escreva o texto da legenda para visualizar aqui...</span>
                )}
              </p>

              {tags.length > 0 && (
                <div className="insta-hashtags">
                  {tags.map((tag) => (
                    <span key={tag} className="insta-tag">
                      #{tag}{" "}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {channel === "linkedin" && (
          <div className="presence-mockup-linkedin">
            <div className="li-header">
              <div className="li-avatar">{workspace.name.charAt(0).toUpperCase()}</div>
              <div className="li-user-meta">
                <strong>{workspace.name}</strong>
                <small>Operação Social · Presença EverGreen</small>
                <small className="li-time">{scheduledLabel} · 🌐</small>
              </div>
            </div>

            <div className="li-body">
              <p className="li-text">
                {text || "Digite a cópia do artigo ou publicação profissional para acompanhar o formato..."}
              </p>

              {tags.length > 0 && (
                <div className="li-hashtags">
                  {tags.map((tag) => (
                    <span key={tag} className="li-tag">
                      #{tag}{" "}
                    </span>
                  ))}
                </div>
              )}

              {draft.media_urls.length > 0 ? (
                <div className="li-media">
                  <img src={draft.media_urls[0]} alt={draft.title} className="li-image" />
                </div>
              ) : (
                <div className="li-media-placeholder">
                  <span className="li-placeholder-title">{draft.title || "Post Corporativo"}</span>
                  <small>EverGreen Service as Software</small>
                </div>
              )}
            </div>

            <div className="li-engagement-bar">
              <span>👍 💡 ❤️ 54</span>
              <span>12 comentários · 4 compartilhamentos</span>
            </div>

            <div className="li-footer-actions">
              <span>👍 Gostei</span>
              <span>💬 Comentar</span>
              <span>🔁 Compartilhar</span>
              <span>📤 Enviar</span>
            </div>
          </div>
        )}

        {channel === "facebook" && (
          <div className="presence-mockup-facebook">
            <div className="fb-header">
              <div className="fb-avatar">{workspace.name.charAt(0).toUpperCase()}</div>
              <div>
                <strong>{workspace.name}</strong>
                <small>{scheduledLabel} · 👥</small>
              </div>
            </div>
            <div className="fb-content">
              <p>{text || "Texto da postagem para o Facebook..."}</p>
              {tags.length > 0 && (
                <p className="fb-tags">
                  {tags.map((t) => `#${t}`).join(" ")}
                </p>
              )}
              {draft.media_urls.length > 0 ? (
                <img src={draft.media_urls[0]} alt={draft.title} className="fb-image" />
              ) : (
                <div className="fb-media-box">
                  <strong>{draft.title}</strong>
                </div>
              )}
            </div>
          </div>
        )}

        {(channel === "tiktok" || channel === "youtube") && (
          <div className="presence-mockup-video">
            <div className="video-card">
              <div className="video-screen">
                <span className="video-play-btn">▶</span>
                <span className="video-channel-tag">{CHANNEL_LABELS[channel]}</span>
                <div className="video-overlay-info">
                  <strong>@{workspace.slug || "evergreen"}</strong>
                  <p>{draft.title}</p>
                  <small>{tags.map((t) => `#${t}`).join(" ")}</small>
                </div>
              </div>
              <div className="video-script-box">
                <strong>Roteiro / Legenda:</strong>
                <p>{text || "Nenhum roteiro ou descrição definida ainda."}</p>
              </div>
            </div>
          </div>
        )}

        {channel === "blog" && (
          <div className="presence-mockup-blog">
            <article className="blog-article-preview">
              <span className="blog-category">Artigo do Workspace</span>
              <h2>{draft.title || "Título do Artigo"}</h2>
              <div className="blog-meta">
                <span>Por {workspace.name}</span> · <span>{scheduledLabel}</span>
              </div>
              {draft.media_urls.length > 0 && (
                <img src={draft.media_urls[0]} alt={draft.title} className="blog-hero-image" />
              )}
              <div className="blog-body">
                <p>{text || "Conteúdo formatado do artigo..."}</p>
              </div>
            </article>
          </div>
        )}
      </div>
    </div>
  );
}
