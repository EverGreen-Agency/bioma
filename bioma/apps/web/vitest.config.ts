import { defineConfig } from "vitest/config";

/** Testes do frontend do Bioma.
 *
 * Escopo deliberado: **lógica pura primeiro, componente depois.** A maior parte
 * dos bugs desta base não estava em renderização — estava em regra escrita à
 * mão em três telas diferentes (a conversão rota→superfície), em vocabulário de
 * status que muda de significado entre disciplinas, e em filtro que escondia o
 * registro interno da EG. Nada disso precisa de DOM para ser testado, e testar
 * sem DOM é ordens de magnitude mais rápido e menos frágil.
 *
 * `environment: node` porque nenhum destes testes toca DOM. Quando entrar teste
 * de componente, ele declara `jsdom` no próprio arquivo via docblock — em vez
 * de todo mundo pagar o custo do DOM por causa de alguns. */
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    coverage: {
      provider: "v8",
      reportsDirectory: "./coverage",
      // `all: true` conta arquivo SEM teste também. Sem isso a cobertura mede
      // só o que já foi lembrado — e um módulo esquecido nunca aparece como
      // buraco, que é justamente o que se quer enxergar.
      all: true,
      include: ["src/lib/**/*.ts"],
      exclude: ["src/types/**", "src/**/*.test.ts"],
    },
  },
});
