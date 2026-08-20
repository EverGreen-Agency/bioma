import { describe, expect, it } from "vitest";
import { surfaceKeyForPath } from "./app-config";

/** `surfaceKeyForPath` é o primeiro teste do frontend por um motivo concreto:
 * essa conversão foi escrita à mão em TRÊS telas (menu lateral, Visão geral da
 * Operação, Cockpit) e nas três o esquecimento produziu o mesmo bug — ocultar
 * um módulo tirava do menu e deixava o atalho vivo noutro lugar.
 *
 * Extrair para uma função só resolveu; testá-la é o que impede a regra de
 * divergir de novo quando alguém acrescentar um caminho novo. */
describe("surfaceKeyForPath", () => {
  it("converte rota de topo em chave", () => {
    expect(surfaceKeyForPath("/eg-rh")).toBe("eg-rh");
    expect(surfaceKeyForPath("/eg-vitorias")).toBe("eg-vitorias");
  });

  it("converte sub-rota usando ponto, que é a convenção do catálogo", () => {
    expect(surfaceKeyForPath("/operacao/radar-local")).toBe("operacao.radar-local");
    expect(surfaceKeyForPath("/operacao/pesquisa-mercado")).toBe("operacao.pesquisa-mercado");
  });

  it("trata a raiz como cockpit", () => {
    expect(surfaceKeyForPath("/")).toBe("cockpit");
    expect(surfaceKeyForPath("")).toBe("cockpit");
  });

  it("ignora barra sobrando, que é o erro de digitação mais comum ao montar link", () => {
    expect(surfaceKeyForPath("/operacao/crm/")).toBe("operacao.crm");
    expect(surfaceKeyForPath("//eg-ideas//")).toBe("eg-ideas");
  });

  it("descarta querystring — link com filtro é a mesma superfície", () => {
    expect(surfaceKeyForPath("/operacao/tarefas?task=abc")).toBe("operacao.tarefas");
  });
});
