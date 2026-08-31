import { execSync } from "node:child_process";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Estado do build, injetado em tempo de compilação e consumido por
 * `src/lib/version.ts`. Não aparece na interface — vive em
 * `window.__BIOMA_BUILD__` para quando alguém precisar saber qual build está
 * no ar.
 *
 * Sem git disponível (container de build sem .git), os campos vêm vazios.
 */
function git(command) {
  try {
    return execSync(command, { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch {
    return "";
  }
}

const API_TARGET = "http://127.0.0.1:8000";

/**
 * Prefixos da API que o dev server encaminha para o backend.
 *
 * Por que a lista é longa e explícita: antes havia só 5 prefixos aqui, e a API
 * tem 30. Toda chamada para um prefixo ausente caía no fallback SPA do Vite,
 * que devolve `index.html` — e a tela quebrava com
 * `Unexpected token '<', "<!doctype "... is not valid JSON`. Como isso só
 * acontece em desenvolvimento (em produção o front fala com a API direto),
 * passava despercebido até alguém abrir a tela.
 *
 * REGRA: ao criar um router novo na API, adicione o prefixo aqui. O teste que
 * protege isso é `apps/api/scripts/smoke_vite_proxy.py`, rodado pelo runner.
 */
const API_PREFIXES = [
  "/agent-memory",
  "/analytics",
  // Decisão 8: artefatos versionados do copiloto (a vista do Estúdio).
  "/artifacts",
  "/auth",
  "/backoffice",
  "/benchmark",
  "/clients",
  "/contracts",
  "/copilot",
  "/health",
  "/improvement-requests",
  "/integrations",
  // A tela não chama /mcp (quem chama é o ChatGPT, de servidor para servidor,
  // contra a API publicada). Fica aqui mesmo assim para manter a invariante do
  // smoke — todo prefixo da API é proxiado — e para dar pra apontar um cliente
  // MCP local na porta do Vite ao depurar.
  "/mcp",
  // Decisão 11: resolução de acesso do próprio usuário (`/me/surfaces`) e
  // administração por sujeito (`/surfaces/catalog`, `/users/{id}/surfaces`).
  "/me",
  "/organizations",
  "/platform-studies",
  "/project-phases",
  "/project-plan-items",
  "/project-planning-intakes",
  "/project-plans",
  "/projects",
  "/proposals",
  "/public",
  "/scope-items",
  "/subtasks",
  "/surfaces",
  "/task-comments",
  "/task-lists",
  "/tasks",
  "/teams",
  "/tenants",
  "/users",
  "/wins",
  "/workspaces",
  // Painel de prova (/eg/proof): disponibilidade, entregas e correções.
  "/eg",
  // Documentação do FastAPI, útil para inspecionar o contrato em dev.
  "/docs",
  "/redoc",
  "/openapi.json",
];

export default defineConfig({
  plugins: [react()],
  define: {
    __BUILD_COMMIT__: JSON.stringify(git("git rev-parse --short HEAD")),
    __BUILD_BRANCH__: JSON.stringify(git("git rev-parse --abbrev-ref HEAD")),
    __BUILD_AT__: JSON.stringify(new Date().toISOString()),
  },
  server: {
    port: 5173,
    proxy: Object.fromEntries(API_PREFIXES.map((prefix) => [prefix, API_TARGET])),
  },
});
