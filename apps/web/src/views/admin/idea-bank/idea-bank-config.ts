import type { CSSProperties } from "react";
import type { Stage } from "../../../types/idea";

export const STAGES: Stage[] = ["capture", "evaluation", "processing", "project", "company"];

// Rótulos das colunas em PT (exibidos no front); chaves são os enums em inglês do JSON.
export const STAGE_META: Record<Stage, { label: string; color: string; hint: string }> = {
  capture:    { label: "Captura",      color: "#8888a0", hint: "Ideia bruta — acabou de surgir. Falta avaliar se vale o esforço." },
  evaluation: { label: "Avaliação",    color: "#ffab00", hint: "Em análise — decidindo se vira projeto ou fica no horizonte futuro." },
  processing: { label: "Em Progresso", color: "#00d4ff", hint: "Em construção — squad ativo ou artefato sendo criado agora." },
  project:    { label: "Projeto",      color: "#00e676", hint: "Entregue e em uso — funciona em produção ou uso real." },
  company:    { label: "Empresa Nova", color: "#a855f7", hint: "Virou produto ou spin-off — transformação de negócio." },
};

export const CAT_COLOR: Record<string, string> = {
  Squad:      "#00d4ff",
  Cockpit:    "#00e676",
  Feature:    "#ffab00",
  Service:    "#a855f7",
  Infra:      "#8888a0",
  Commercial: "#ff5252",
  Platform:   "#3ac97b",
};

// Descrições das categorias — tooltip nos badges e filtros.
export const CAT_DESC: Record<string, string> = {
  Squad:      "Time de agentes com pipeline próprio (ex: eg_setup, Curador, Arquiteto).",
  Cockpit:    "Interface / painel de controle — onde o humano opera (dashboard, abas, carteira).",
  Feature:    "Funcionalidade pontual dentro de um squad ou do sistema (ex: SLA Watchdog).",
  Service:    "Oferta vendável ao cliente — um entregável comercial (ex: Auditoria AI-First).",
  Infra:      "Fundação técnica que outros usam (vector store, MCP, bancos de conhecimento).",
  Commercial: "Estratégia de posicionamento, precificação ou venda (ex: AI-CMO, Dogfooding).",
  Platform:   "Mega-plataforma EG e seus módulos — o guarda-chuva e as camadas do sistema (multitenant, client-hub, financeiro...).",
};

// Rótulos em PT exibidos no front (o valor no JSON continua em inglês — enum).
export const CAT_LABEL: Record<string, string> = {
  Squad:      "Squad",
  Cockpit:    "Cockpit",
  Feature:    "Recurso",
  Service:    "Serviço",
  Infra:      "Infra",
  Commercial: "Comercial",
  Platform:   "Plataforma",
};

export const CATEGORIES = Object.keys(CAT_COLOR);

// Ordem de urgência para desenvolvimento. Menor = mais urgente; ordena os cards na coluna.
export const HORIZON_ORDER: Record<string, number> = {
  "NOW": 0,
  "MEDIUM": 1,
  "LONG": 2,
  "NEW_COMPANY": 3,
  "": 4, // a redefinir — vai para o fim
};

// Cor do badge de horizonte por urgência. NOW se destaca. Rótulos em PT.
export const HORIZON_META: Record<string, { label: string; color: string }> = {
  "NOW":         { label: "AGORA",        color: "#ff5252" },
  "MEDIUM":      { label: "MÉDIO",        color: "#ffab00" },
  "LONG":        { label: "LONGO",        color: "#8888a0" },
  "NEW_COMPANY": { label: "EMPRESA NOVA", color: "#a855f7" },
};

export const ideaStyles: Record<string, CSSProperties> = {
  toolbar: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 16px",
    borderBottom: "1px solid var(--border)",
    flexShrink: 0,
    flexWrap: "wrap",
    background: "var(--bg-sidebar)",
  },
  searchInput: {
    background: "var(--bg-primary)",
    border: "1px solid var(--border)",
    borderRadius: 4,
    padding: "4px 10px",
    color: "var(--text-primary)",
    fontSize: 12,
    fontFamily: "inherit",
    width: 180,
    outline: "none",
  },
  filterBtn: {
    padding: "3px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontFamily: "inherit",
    cursor: "pointer",
    border: "1px solid",
    background: "transparent",
    transition: "all 0.12s",
  },
  board: {
    flex: 1,
    display: "flex",
    gap: 12,
    padding: 16,
    overflowX: "auto",
    overflowY: "hidden",
    alignItems: "flex-start",
  },
  column: {
    flex: 1,
    minWidth: 260,
    display: "flex",
    flexDirection: "column",
    maxHeight: "100%",
  },
  cardList: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    overflowY: "auto",
    flex: 1,
  },
  card: {
    background: "var(--bg-secondary)",
    border: "1px solid",
    borderRadius: 6,
    padding: "10px 12px",
    cursor: "pointer",
    transition: "border-color 0.12s",
  },
  badge: {
    fontSize: 10,
    padding: "2px 5px",
    borderRadius: 3,
  },
  connectionRow: {
    marginTop: 8,
    fontSize: 11,
    lineHeight: 1.5,
    color: "var(--text-primary)",
  },
  actionBtn: {
    padding: "3px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontFamily: "inherit",
    cursor: "pointer",
    border: "1px solid var(--border)",
    background: "transparent",
    color: "var(--text-secondary)",
  },
  editInput: {
    background: "var(--bg-primary)",
    border: "1px solid var(--border)",
    borderRadius: 4,
    padding: "5px 8px",
    color: "var(--text-primary)",
    fontSize: 12,
    fontFamily: "inherit",
    width: "100%",
    boxSizing: "border-box" as const,
    outline: "none",
  },
  editSelect: {
    background: "var(--bg-primary)",
    border: "1px solid var(--border)",
    borderRadius: 4,
    padding: "4px 6px",
    color: "var(--text-primary)",
    fontSize: 11,
    fontFamily: "inherit",
    cursor: "pointer",
  },
};
