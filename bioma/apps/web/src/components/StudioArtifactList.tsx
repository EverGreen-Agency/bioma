import { useState } from "react";
import { Check, Copy, FileText, History, MessageSquareText, Sparkles } from "lucide-react";
import {
  useStudioArtifacts,
  useStudioArtifactKinds,
  useStudioArtifact,
  useSetStudioArtifactStatus,
} from "../hooks/useBiomaApi";
import type { StudioArtifact, StudioArtifactStatus } from "../lib/api";
import { EmptyState } from "./shared";
import { ContentQualityPanel } from "./ContentQualityPanel";
import { PublishToCmsPanel } from "./PublishToCmsPanel";

const statusLabel: Record<StudioArtifactStatus, string> = {
  draft: "Rascunho",
  approved: "Aprovado",
  published: "Publicado",
  archived: "Arquivado",
};

function statusColor(status: StudioArtifactStatus): string {
  if (status === "approved") return "var(--mint)";
  if (status === "published") return "var(--accent)";
  if (status === "archived") return "var(--text-faint)";
  return "var(--amber)";
}

/** Painel de uma peça: conteúdo corrente + histórico de versões.
 *
 * O histórico é o ponto inteiro da decisão 8 — sem ele, "muda o gancho" apaga
 * o gancho anterior e não há como comparar. Cada versão mostra se saiu do
 * copiloto (tem execução) ou de uma edição à mão. */
function ArtifactPanel({ artifactId, workspaceId }: { artifactId: string; workspaceId: string }) {
  const { data: artifact, isLoading } = useStudioArtifact(artifactId);
  const setStatus = useSetStudioArtifactStatus();
  const [openVersion, setOpenVersion] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);

  if (isLoading || !artifact) return <EmptyState text="Carregando a peça..." />;

  const shown = openVersion
    ? artifact.versions.find((version) => version.version === openVersion)
    : artifact.versions.find((version) => version.version === artifact.current_version);

  function handleCopy() {
    navigator.clipboard.writeText(shown?.content ?? artifact?.content ?? "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div style={{ minWidth: 0 }}>
          <h3 style={{ margin: 0, fontSize: 16 }}>{artifact.title}</h3>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
            {artifact.kind} · v{artifact.current_version} de {artifact.versions_total}
            {artifact.thread_id && " · veio de uma conversa"}
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {(Object.keys(statusLabel) as StudioArtifactStatus[]).map((status) => (
            <button
              key={status}
              type="button"
              className={artifact.status === status ? "mini-button approve" : "mini-button"}
              disabled={setStatus.isPending}
              onClick={() => setStatus.mutate({ artifactId, status })}
            >
              {statusLabel[status]}
            </button>
          ))}
        </div>
      </div>

      <div style={{ background: "var(--bg-elevated)", borderRadius: 8, border: "1px solid var(--border-light)", padding: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <strong style={{ fontSize: 12.5 }}>
            {openVersion && openVersion !== artifact.current_version
              ? `Versão ${openVersion} (histórico)`
              : `Versão ${artifact.current_version} (atual)`}
          </strong>
          <button type="button" className="mini-button" onClick={handleCopy}>
            {copied ? <Check size={13} /> : <Copy size={13} />} Copiar
          </button>
        </div>
        <p style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "var(--text-muted)", margin: 0, lineHeight: 1.55 }}>
          {shown?.content ?? artifact.content ?? "Sem conteúdo."}
        </p>
      </div>

      {/* Avalia a versao EXIBIDA, nao a corrente: abrir uma versao antiga e
          querer comparar, e um score preso na atual nao compararia nada. */}
      <ContentQualityPanel
        workspaceId={workspaceId}
        title={artifact.title}
        content={shown?.content ?? artifact.content ?? ""}
      />

      {/* Publica a versao EXIBIDA. Voltar para a v2 e o caso real de
          republicar; sem isso a unica saida seria criar uma v4 copiando a v2,
          poluindo o historico com uma mudanca que nao houve. */}
      <PublishToCmsPanel
        workspaceId={workspaceId}
        artifactId={artifactId}
        version={shown?.version ?? artifact.current_version}
      />

      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-faint)", marginBottom: 8 }}>
          <History size={13} /> Histórico
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {artifact.versions.map((version) => (
            <button
              key={version.id}
              type="button"
              onClick={() => setOpenVersion(version.version)}
              style={{
                display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12,
                padding: "9px 12px", background: "var(--bg-elevated)", borderRadius: 8, textAlign: "left",
                border: `1px solid ${(openVersion ?? artifact.current_version) === version.version ? "var(--mint)" : "var(--border-light)"}`,
                color: "var(--text-main)", cursor: "pointer",
              }}
            >
              <span style={{ minWidth: 0 }}>
                <strong style={{ fontSize: 12.5 }}>v{version.version}</strong>
                {version.change_note && (
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}> — {version.change_note}</span>
                )}
                <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 2 }}>
                  {/* A diferença entre "o copiloto escreveu" e "alguém editou"
                      é o que se quer saber ao revisar. */}
                  {version.run_id ? "gerada pelo copiloto" : "editada à mão"}
                  {version.created_by_name ? ` · ${version.created_by_name}` : ""}
                  {` · ${new Date(version.created_at).toLocaleDateString("pt-BR")}`}
                </div>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/** A vista limpa dos artefatos — o Estúdio deixa de ser formulário.
 *
 * Não há botão de "gerar" aqui de propósito: quem gera é a conversa com o
 * copiloto, e esta tela é onde o resultado dela vive. Reintroduzir um formulário
 * recriaria os dois sistemas paralelos que a decisão 8 fundiu. */
export function StudioArtifactList({ workspaceId }: { workspaceId: string }) {
  const [kind, setKind] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const { data: artifacts = [], isLoading } = useStudioArtifacts(workspaceId, { kind });
  const { data: kinds = [] } = useStudioArtifactKinds(workspaceId);

  const current = selected ?? artifacts[0]?.id ?? null;

  return (
    <article className="surface" style={{ gridColumn: "1 / -1" }}>
      <div className="surface-header">
        <Sparkles size={18} />
        <h3>Estúdio — o que já foi criado</h3>
      </div>

      <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 16px", lineHeight: 1.5 }}>
        Tudo que a conversa com o copiloto produziu e você salvou, com histórico
        de versões. Para criar algo novo, converse com o copiloto e use
        <strong> Salvar no Estúdio</strong> na resposta.
      </p>

      {kinds.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 }}>
          <button type="button" className={kind === null ? "mini-button approve" : "mini-button"} onClick={() => setKind(null)}>
            Tudo
          </button>
          {kinds.map((item) => (
            <button
              key={item.kind}
              type="button"
              className={kind === item.kind ? "mini-button approve" : "mini-button"}
              onClick={() => setKind(item.kind)}
            >
              {item.kind} · {item.total}
            </button>
          ))}
        </div>
      )}

      {isLoading && <EmptyState text="Carregando artefatos..." />}

      {!isLoading && artifacts.length === 0 && (
        <div className="notice">
          Nada salvo ainda. Abra o copiloto (Ctrl+K), peça um roteiro ou um post,
          e clique em "Salvar no Estúdio" — a peça aparece aqui com a conversa
          de origem registrada.
        </div>
      )}

      {artifacts.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, 320px) 1fr", gap: 20, alignItems: "start" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {artifacts.map((artifact: StudioArtifact) => (
              <button
                key={artifact.id}
                type="button"
                onClick={() => setSelected(artifact.id)}
                style={{
                  display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 4,
                  padding: "10px 12px", borderRadius: 8, textAlign: "left", cursor: "pointer",
                  background: "var(--bg-elevated)", color: "var(--text-main)",
                  border: `1px solid ${current === artifact.id ? "var(--mint)" : "var(--border-light)"}`,
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                  <FileText size={13} /> <strong>{artifact.title}</strong>
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "var(--text-faint)" }}>
                  <span style={{ color: statusColor(artifact.status) }}>{statusLabel[artifact.status]}</span>
                  <span>v{artifact.current_version}</span>
                  {artifact.thread_id && <MessageSquareText size={11} />}
                </span>
              </button>
            ))}
          </div>

          <div>{current && <ArtifactPanel artifactId={current} workspaceId={workspaceId} />}</div>
        </div>
      )}
    </article>
  );
}
