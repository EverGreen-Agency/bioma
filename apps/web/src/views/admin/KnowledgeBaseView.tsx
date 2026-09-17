import { BookOpen } from "lucide-react";

import { KnowledgeBaseManager } from "../../components/KnowledgeBaseManager";
import { EmptyState, SectionHeader } from "../../components/shared";
import { useCurrentUser, useWorkspaces } from "../../hooks/useBiomaApi";
import { resolveAgencyWorkspace } from "../../lib/workspace-context";

/**
 * Base de conhecimento da EG — decisão 7, Fase 1.
 *
 * A do CLIENTE não tem tela própria aqui de propósito: a base pende do
 * workspace, então ela aparece dentro do hub de cada cliente. Duas telas para o
 * mesmo objeto criariam duas formas de fazer a mesma coisa.
 */
export function KnowledgeBaseView() {
  const { data: workspaces = [], isLoading } = useWorkspaces();
  const { data: user } = useCurrentUser();
  const resolution = resolveAgencyWorkspace(workspaces, user);

  if (isLoading) return <EmptyState text="Carregando Operação EG..." />;
  if (resolution.status !== "ready") {
    return <EmptyState text="Workspace da Operação EG não encontrado." />;
  }

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
      <SectionHeader eyebrow="Operação EG" title="Base de Conhecimento" icon={BookOpen} />
      <p style={{ fontSize: 12, color: "var(--text-faint)", margin: 0, maxWidth: 720, lineHeight: 1.55 }}>
        Processos, políticas e contratos-modelo da casa, fragmentados e buscáveis.
        Cada resultado abre no texto de origem — o que não dá para conferir de onde
        saiu não serve para decidir nada.
      </p>
      <KnowledgeBaseManager workspaceId={resolution.workspace.workspaceId} />
    </div>
  );
}
