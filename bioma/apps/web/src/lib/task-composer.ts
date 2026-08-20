/**
 * Qual projeto a nova tarefa recebe — e quando a tela precisa perguntar.
 *
 * Decisão 13 (2026-08-08): tarefa de CLIENTE exige projeto; na Operação EG é
 * opcional. O backend recusa com 422, e 422 na cara de quem só queria digitar
 * um título é a pior forma de ensinar uma regra.
 *
 * Esta função vive fora do componente de propósito: ela é a regra, e é a regra
 * que muda de comportamento entre workspace de cliente e da agência. Deixá-la
 * dentro do JSX foi como o `surfaceKeyForPath` acabou reescrito à mão em três
 * telas, com o mesmo erro nas três.
 *
 * O viés é NÃO PERGUNTAR: se a tela já sabe o projeto (filtro ativo, ou um
 * projeto só), ela decide sozinha. Perguntar é o último recurso.
 */

export type ComposerProject = { id: string; name: string };

export type ComposerProjectState =
  | { ready: true; projectId: string | null }
  | { ready: false; reason: "sem-projeto" | "escolha-projeto"; message: string };

export function resolveComposerProject({
  kind,
  projects,
  projectFilter,
}: {
  kind: "agency_internal" | "client";
  projects: ComposerProject[];
  projectFilter: string;
}): ComposerProjectState {
  // O filtro só vale se o projeto ainda existir: arquivar um projeto com a tela
  // aberta deixaria um id fantasma, e o backend responderia "projeto de outro
  // workspace" — verdade técnica que não explica nada para quem está usando.
  const filtrado = projects.find((project) => project.id === projectFilter);

  if (kind === "agency_internal") {
    return { ready: true, projectId: filtrado?.id ?? null };
  }

  if (filtrado) return { ready: true, projectId: filtrado.id };

  if (projects.length === 0) {
    return {
      ready: false,
      reason: "sem-projeto",
      message:
        "Tarefa de cliente precisa de um projeto. Crie o primeiro em Projetos e contratos.",
    };
  }

  if (projects.length === 1) {
    return { ready: true, projectId: projects[0].id };
  }

  return {
    ready: false,
    reason: "escolha-projeto",
    message: "Escolha um projeto no filtro acima para anotar a tarefa nele.",
  };
}
