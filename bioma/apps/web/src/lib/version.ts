/** Versão do Bioma — fonte única de verdade.
 *  SemVer: MAJOR.MINOR.PATCH
 *  - MAJOR: breaking change de produto / lançamento público
 *  - MINOR: feature nova visível ao usuário
 *  - PATCH: bugfix, ajuste visual, melhoria interna
 *  Atualizada automaticamente pelo release-please a cada release em main
 *  (a anotação x-release-please-version na linha abaixo é o marcador).
 */
export const APP_VERSION = "0.6.0"; // x-release-please-version

/** Estado do build, injetado pelo Vite (ver vite.config.mjs).
 *
 *  NÃO é exibido na interface: branch e hash de commit não dizem nada para o
 *  cliente e poluem a marca. Fica exposto em `window.__BIOMA_BUILD__` para
 *  quando alguém precisar saber exatamente qual build está no ar — que é o
 *  único momento em que essa informação importa.
 */
declare const __BUILD_COMMIT__: string;
declare const __BUILD_BRANCH__: string;
declare const __BUILD_AT__: string;

export const BUILD_INFO = {
  version: APP_VERSION,
  commit: typeof __BUILD_COMMIT__ === "string" ? __BUILD_COMMIT__ : "",
  branch: typeof __BUILD_BRANCH__ === "string" ? __BUILD_BRANCH__ : "",
  builtAt: typeof __BUILD_AT__ === "string" ? __BUILD_AT__ : "",
};

if (typeof window !== "undefined") {
  (window as unknown as Record<string, unknown>).__BIOMA_BUILD__ = BUILD_INFO;
}
