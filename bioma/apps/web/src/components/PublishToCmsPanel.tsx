import { useState } from "react";
import { AlertTriangle, ExternalLink, Globe, Loader2, Send, TriangleAlert } from "lucide-react";

import { useCmsTargets, usePublishPreview, usePublishArtifact, useArtifactPublications } from "../hooks/useBiomaApi";
import { EmptyState } from "./shared";

/**
 * Publicar a peça em um CMS — decisão 14.
 *
 * O botão de publicar **não aparece antes da prévia**. O destino é o site do
 * cliente: ver o que vai antes de mandar é o que separa um erro corrigível de
 * um post publicado em nome dele. Um clique só, direto para o ar, seria mais
 * rápido e transformaria todo engano em algo que precisa ser despublicado.
 *
 * A prévia mostra o `status` REAL que vai ser aplicado — e, quando ele é menor
 * que o configurado, o motivo. Sem o motivo, quem configurou "direto" clica,
 * vê "rascunho" e conclui que a configuração está quebrada.
 */
export function PublishToCmsPanel({
  workspaceId,
  artifactId,
  version,
}: {
  workspaceId: string;
  artifactId: string;
  version: number;
}) {
  const [targetId, setTargetId] = useState<string>("");
  const [erro, setErro] = useState<string | null>(null);

  const { data: targets = [], isLoading: carregandoAlvos } = useCmsTargets(workspaceId);
  const { data: publicacoes = [] } = useArtifactPublications(workspaceId, artifactId);
  const opcoes = targetId ? { target_id: targetId, version } : null;
  const { data: previa, isLoading: carregandoPrevia, error: erroPrevia } = usePublishPreview(
    workspaceId,
    artifactId,
    opcoes,
  );
  const publicar = usePublishArtifact(workspaceId, artifactId);

  const ativos = targets.filter((target) => target.is_active);
  const jaPublicada = publicacoes.find((p) => p.version === version && p.target_id === targetId);

  if (carregandoAlvos) return <EmptyState text="Carregando destinos..." />;

  if (ativos.length === 0) {
    return (
      <p className="inline-task-composer-blocked">
        <Globe size={12} aria-hidden /> Nenhum site conectado. Cadastre o WordPress em
        Configurações › Integrações e aponte para uma credencial do cofre.
      </p>
    );
  }

  return (
    <section
      style={{
        border: "1px solid var(--border)",
        borderRadius: 8,
        background: "var(--bg-inset)",
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <header style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Globe size={14} aria-hidden />
        <strong style={{ fontSize: 13 }}>Publicar no site</strong>
        <span style={{ fontSize: 11, color: "var(--text-faint)" }}>v{version}</span>
      </header>

      <select
        value={targetId}
        onChange={(event) => {
          setTargetId(event.target.value);
          setErro(null);
        }}
        aria-label="Destino da publicação"
        style={{ fontSize: 12 }}
      >
        <option value="">Escolha o destino...</option>
        {ativos.map((target) => (
          <option key={target.id} value={target.id}>
            {target.label} — {target.publish_mode === "direct" ? "publica direto" : "rascunho"}
          </option>
        ))}
      </select>

      {carregandoPrevia && (
        <p style={{ fontSize: 12, color: "var(--text-faint)", margin: 0 }}>
          <Loader2 size={12} className="spin" aria-hidden /> Montando a prévia...
        </p>
      )}

      {erroPrevia && (
        <p style={{ fontSize: 12, color: "var(--danger-soft)", margin: 0 }}>
          <TriangleAlert size={12} aria-hidden /> {(erroPrevia as Error).message}
        </p>
      )}

      {previa && (
        <>
          {previa.downgrade_reason && (
            <p
              style={{
                fontSize: 11.5,
                color: "var(--amber)",
                margin: 0,
                display: "flex",
                gap: 6,
                alignItems: "flex-start",
                lineHeight: 1.45,
              }}
            >
              <AlertTriangle size={13} aria-hidden style={{ flexShrink: 0, marginTop: 1 }} />
              {previa.downgrade_reason}
            </p>
          )}

          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Vai como{" "}
            <strong style={{ color: previa.resulting_status === "publish" ? "var(--mint)" : "var(--amber)" }}>
              {previa.resulting_status === "publish" ? "PUBLICADO (no ar)" : "RASCUNHO"}
            </strong>
          </div>

          <details>
            <summary style={{ fontSize: 11, color: "var(--text-faint)", cursor: "pointer" }}>
              Ver exatamente o que será enviado
            </summary>
            <pre
              style={{
                fontSize: 10.5,
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: 10,
                marginTop: 8,
                overflowX: "auto",
                maxHeight: 260,
                color: "var(--text-muted)",
              }}
            >
              {JSON.stringify(previa.payload, null, 2)}
            </pre>
          </details>

          {jaPublicada && (
            <p style={{ fontSize: 11, color: "var(--text-faint)", margin: 0 }}>
              Esta versão já foi para este destino em{" "}
              {new Date(jaPublicada.published_at).toLocaleString("pt-BR")}. Publicar de novo
              atualiza o mesmo post.
            </p>
          )}

          <button
            type="button"
            className="primary-button"
            disabled={publicar.isPending}
            onClick={() => {
              setErro(null);
              publicar.mutate(
                { target_id: targetId, version },
                { onError: (err: Error) => setErro(err.message) },
              );
            }}
            style={{ display: "flex", alignItems: "center", gap: 6, justifyContent: "center" }}
          >
            {publicar.isPending ? <Loader2 size={13} className="spin" aria-hidden /> : <Send size={13} aria-hidden />}
            {previa.resulting_status === "publish" ? "Publicar no ar" : "Enviar como rascunho"}
          </button>
        </>
      )}

      {erro && (
        <p style={{ fontSize: 12, color: "var(--danger-soft)", margin: 0, lineHeight: 1.45 }}>
          <TriangleAlert size={12} aria-hidden /> {erro}
        </p>
      )}

      {publicacoes.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 10.5,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              color: "var(--text-faint)",
              marginBottom: 6,
            }}
          >
            Já publicado
          </div>
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 5 }}>
            {publicacoes.map((publicacao) => (
              <li key={publicacao.id} style={{ fontSize: 11.5, color: "var(--text-muted)" }}>
                v{publicacao.version} → {publicacao.target_label}
                {publicacao.external_status && ` (${publicacao.external_status})`}
                {publicacao.external_url && (
                  <a
                    href={publicacao.external_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ marginLeft: 6, color: "var(--accent)" }}
                  >
                    abrir <ExternalLink size={10} aria-hidden style={{ display: "inline" }} />
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
