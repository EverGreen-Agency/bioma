import { describe, expect, it } from "vitest";
import { statusesForFrente } from "./task-frentes";

/** O fato que este arquivo protege, e que já foi respondido errado uma vez:
 * disciplina NÃO é filtro cosmético. Cada frente tem vocabulário próprio, e o
 * MESMO nome de status pertence a grupos diferentes conforme a frente.
 *
 * É por isso que a aba "Todas as disciplinas" é uma tradução, não a visão
 * canônica — e é isso que um refactor distraído poderia "simplificar" achando
 * que os status são iguais. */
describe("status por frente", () => {
  it("`Backlog` muda de GRUPO entre Growth e Tech", () => {
    const growth = statusesForFrente("growth").find((item) => item.status === "Backlog");
    const tech = statusesForFrente("tech").find((item) => item.status === "Backlog");

    expect(growth?.group).toBe("ACTIVE");
    expect(tech?.group).toBe("NOT_STARTED");
    // Se estes dois um dia forem iguais, a visão combinada deixa de ser
    // tradução — e o aviso na tela passa a mentir.
    expect(growth?.group).not.toBe(tech?.group);
  });

  it("Tech tem passos que Growth não conhece", () => {
    const tech = statusesForFrente("tech").map((item) => item.status);
    expect(tech).toContain("Code review");
    expect(tech).toContain("QA / testes");

    const growth = statusesForFrente("growth").map((item) => item.status);
    expect(growth).not.toContain("Code review");
  });

  it("Social tem vocabulário editorial, não de engenharia", () => {
    const social = statusesForFrente("social").map((item) => item.status);
    expect(social).toContain("Roteirização");
    expect(social).toContain("Aprovação cliente");
    expect(social).not.toContain("Backlog");
  });

  it("toda frente cobre os quatro grupos do kanban", () => {
    for (const frente of ["growth", "tech", "social"] as const) {
      const grupos = new Set(statusesForFrente(frente).map((item) => item.group));
      // Sem um status em algum grupo, aquela coluna do kanban fica órfã:
      // aparece na tela e nenhuma tarefa pode chegar nela.
      expect(grupos).toContain("NOT_STARTED");
      expect(grupos).toContain("ACTIVE");
      expect(grupos).toContain("DONE");
    }
  });
});
