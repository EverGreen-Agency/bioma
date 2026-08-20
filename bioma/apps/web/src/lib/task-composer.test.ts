import { describe, expect, it } from "vitest";

import { resolveComposerProject } from "./task-composer";

/**
 * Decisão 13: tarefa de CLIENTE exige projeto. O backend recusa com 422.
 *
 * Estes testes descrevem como a tela evita o 422 — e, principalmente, como ela
 * evita virar um formulário chato. O caso comum (um projeto só, ou filtro de
 * projeto ativo) tem que resolver sozinho, sem perguntar nada.
 */

const UM = { id: "p1", name: "Site novo" };
const OUTRO = { id: "p2", name: "Campanha de verão" };

describe("workspace da EG (projeto opcional)", () => {
  it("cria sem projeto nenhum", () => {
    const r = resolveComposerProject({ kind: "agency_internal", projects: [], projectFilter: "" });
    expect(r).toEqual({ ready: true, projectId: null });
  });

  it("respeita o filtro quando há um, mesmo sendo opcional", () => {
    const r = resolveComposerProject({ kind: "agency_internal", projects: [UM], projectFilter: "p1" });
    expect(r).toEqual({ ready: true, projectId: "p1" });
  });
});

describe("workspace de cliente (projeto obrigatório)", () => {
  it("usa o projeto do filtro ativo sem perguntar nada", () => {
    // A pessoa está olhando um projeto; a tarefa é daquele projeto. Perguntar
    // de novo seria burocracia sobre algo que a tela já sabe.
    const r = resolveComposerProject({ kind: "client", projects: [UM, OUTRO], projectFilter: "p2" });
    expect(r).toEqual({ ready: true, projectId: "p2" });
  });

  it("com um único projeto, escolhe sozinho", () => {
    const r = resolveComposerProject({ kind: "client", projects: [UM], projectFilter: "" });
    expect(r).toEqual({ ready: true, projectId: "p1" });
  });

  it("com vários projetos e sem filtro, pede para escolher", () => {
    const r = resolveComposerProject({ kind: "client", projects: [UM, OUTRO], projectFilter: "" });
    expect(r.ready).toBe(false);
    if (r.ready) return;
    expect(r.reason).toBe("escolha-projeto");
    // A mensagem tem que dizer o que fazer, não só que não deu.
    expect(r.message).toMatch(/filtro/i);
  });

  it("sem projeto nenhum, manda criar o projeto", () => {
    const r = resolveComposerProject({ kind: "client", projects: [], projectFilter: "" });
    expect(r.ready).toBe(false);
    if (r.ready) return;
    expect(r.reason).toBe("sem-projeto");
    expect(r.message).toMatch(/Projetos e contratos/);
  });

  it("filtro apontando para projeto que não existe mais não passa batido", () => {
    // Projeto arquivado enquanto a tela estava aberta. Mandar o id fantasma
    // para o backend daria 'projeto de outro workspace', que não explica nada.
    const r = resolveComposerProject({ kind: "client", projects: [UM], projectFilter: "p-sumiu" });
    expect(r).toEqual({ ready: true, projectId: "p1" });
  });
});
