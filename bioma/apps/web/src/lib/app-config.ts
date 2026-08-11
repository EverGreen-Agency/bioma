import { BarChart3, BookOpen, Bot, BriefcaseBusiness, ClipboardList, FileSearch, FileText, FolderOpen, GitBranch, Headphones, KeyRound, LayoutDashboard, Link2, MapPin, MessageSquare, Package, Radar, ShieldCheck, Sparkles, Target, Trophy, UserCheck, Users, WalletCards, type LucideIcon } from "lucide-react";

import type { ArtifactPayload, ClientModule, ClientPayload, ClientStatus, CurrentUser, DeliverablePayload, DeliverableStatus } from "./api";

export type ViewId =
  | "cockpit"
  | "operacao"
  | "clientes"
  | "crm"
  | "finance"
  | "engenharia"
  | "analytics"
  | "eg-wiki"
  | "eg-ideas"
  | "eg-tech"
  | "eg-architecture"
  | "eg-rh"
  | "eg-kits"
  | "eg-propostas"
  | "eg-planning"
  | "eg-plataformas"
  | "eg-vitorias"
  | "sales_copilot";

export const navItems: Array<{ id: ViewId; label: string; icon: LucideIcon }> = [
  { id: "cockpit", label: "Cockpit", icon: LayoutDashboard },
  { id: "operacao", label: "Operação EG", icon: BriefcaseBusiness },
  { id: "clientes", label: "Carteira de Clientes", icon: Users },
  
  // Rotas internas EG. Módulos de cliente vivem na navegação do próprio Hub.
  { id: "engenharia", label: "Engenharia", icon: FileText },
  { id: "eg-wiki", label: "Wiki EG", icon: BookOpen },
  { id: "eg-ideas", label: "Banco de Ideias", icon: BookOpen },
  { id: "eg-tech", label: "Banco de Stack", icon: GitBranch },
  { id: "eg-architecture", label: "Arquitetura", icon: FileText },
  { id: "eg-rh", label: "Gestão RH", icon: UserCheck },
  { id: "eg-kits", label: "Logística Kits", icon: Package },
  { id: "eg-propostas", label: "Freelas e Propostas", icon: Target },
  { id: "eg-planning", label: "Planejamentos", icon: ClipboardList },
  { id: "eg-plataformas", label: "Estudo de Plataformas", icon: Radar },
  { id: "eg-vitorias", label: "Mural de Vitórias", icon: Trophy },
  { id: "sales_copilot", label: "Copiloto de Vendas", icon: Headphones },
];

export const clientHubNavItems: Array<{
  id: "hub" | "context" | "projects" | "ai-content" | "crm" | "finance" | "analytics" | "files" | "tasks" | "vault" | "integrations";
  label: string;
  path: string;
  module: ClientModule;
  icon: LucideIcon;
}> = [
  { id: "hub", label: "Visão geral", path: "", module: "hub", icon: LayoutDashboard },
  { id: "context", label: "Contexto do cliente", path: "contexto", module: "hub", icon: FileText },
  { id: "projects", label: "Projetos e contratos", path: "projetos", module: "hub", icon: BriefcaseBusiness },
  { id: "ai-content", label: "Estúdio IA", path: "conteudo-ia", module: "content", icon: Sparkles },
  { id: "crm", label: "CRM", path: "crm", module: "commercial", icon: Users },
  { id: "finance", label: "Financeiro", path: "financeiro", module: "finance", icon: WalletCards },
  { id: "analytics", label: "Métricas", path: "analytics", module: "analytics", icon: BarChart3 },
  { id: "files", label: "Documentos", path: "documentos", module: "files", icon: FolderOpen },
  { id: "tasks", label: "Tarefas", path: "tarefas", module: "hub", icon: LayoutDashboard },
  { id: "vault", label: "Acessos", path: "acessos", module: "hub", icon: KeyRound },
  { id: "integrations", label: "Integrações", path: "integracoes", module: "integrations", icon: Link2 },
];

export const agencyWorkspaceNavItems: Array<{
  id: string;
  label: string;
  path: string;
  module: ClientModule;
  icon: LucideIcon;
}> = [
  // "tasks" incluído: sem ele a própria EG não tinha onde gerenciar demanda
  // interna (social/tech/growth da casa, treinamento de time, hackathon) —
  // o workspace interno existe desde sempre, mas não havia aba para alcançá-lo.
  ...clientHubNavItems
    .filter((item) => ["hub", "tasks", "crm", "finance", "analytics"].includes(item.id))
    .map((item) => item.id === "analytics" ? { ...item, path: "metricas" } : item),
  {
    id: "ai-operations",
    label: "Operações IA",
    path: "ia",
    module: "hub",
    icon: Bot,
  },
  {
    id: "market-research",
    label: "Pesquisa de mercado",
    path: "pesquisa-mercado",
    module: "hub",
    icon: FileSearch,
  },
  {
    // Painel de prova: disponibilidade medida por fora, entregas e correções.
    id: "proof",
    label: "Prova",
    path: "prova",
    module: "hub",
    icon: ShieldCheck,
  },
  {
    id: "local-radar",
    label: "Radar Local",
    path: "radar-local",
    module: "hub",
    icon: MapPin,
  },
  {
    id: "whatsapp",
    label: "WhatsApp & Disparos",
    path: "whatsapp",
    module: "integrations",
    icon: MessageSquare,
  },
];

// Feature-gating por organização (decisão 2026-07-14): cada view exige um
// módulo habilitado; EG admin enxerga tudo, client_user só o que a org tem.
export const viewModule: Record<ViewId, ClientModule> = {
  cockpit: "hub",
  operacao: "hub",
  clientes: "hub",
  crm: "commercial",
  finance: "finance",
  analytics: "analytics",
  engenharia: "engineering",
  // Rotas internas não devem depender de módulos de cliente,
  // mas para obedecer à tipagem sem erro, colocamos hub.
  // A proteção real se dará no App.tsx com isEgAdmin.
  "eg-wiki": "hub",
  "eg-ideas": "hub",
  "eg-tech": "hub",
  "eg-architecture": "hub",
  "eg-rh": "hub",
  "eg-kits": "hub",
  "eg-propostas": "hub",
  "eg-planning": "hub",
  "eg-plataformas": "hub",
  "eg-vitorias": "hub",
  sales_copilot: "commercial",
};

export const moduleLabels: Record<ClientModule, string> = {
  hub: "Visão geral do cliente",
  content: "Estúdio IA",
  files: "Arquivos e Documentos",
  commercial: "CRM (Vendas)",
  finance: "Financeiro",
  analytics: "Métricas e Analytics",
  integrations: "Integrações",
  engineering: "Engenharia",
};

// Módulos que o EG admin pode ligar/desligar por cliente ("hub" é o núcleo,
// sempre ativo — o backend força isso também).
export const toggleableModules: ClientModule[] = ["content", "files", "commercial", "finance", "analytics", "integrations"];

export function enabledModulesFor(user: CurrentUser | null | undefined, isEgAdmin: boolean): Set<ClientModule> {
  if (isEgAdmin) {
    return new Set<ClientModule>(["hub", "content", "files", "commercial", "analytics", "integrations", "engineering"]);
  }
  const modules = new Set<ClientModule>();
  for (const organization of user?.organizations ?? []) {
    for (const module of organization.enabled_modules ?? []) {
      modules.add(module);
    }
  }
  modules.add("hub");
  return modules;
}

export const statusLabel: Record<ClientStatus, string> = {
  onboarding: "Onboarding",
  active: "Ativo (Recorrência)",
  paused: "Pausado",
  completed: "Projeto Concluído",
  archived: "Arquivado",
};

export const deliverableStatusLabel: Record<DeliverableStatus, string> = {
  planned: "Planejado",
  in_progress: "Em execução",
  waiting_approval: "Aguardando aprovação",
  done: "Concluído",
  blocked: "Bloqueado",
};

export const integrationRows = [
  { name: "SleekFlow", status: "Descoberta", detail: "adapter omnichannel condicionado à parceria e ao contrato oficial da API" },
  { name: "Drive", status: "Backlog", detail: "centralizar links e arquivos do cliente no hub" },
  { name: "LinkedIn/Analytics", status: "MVP Demo", detail: "Demonstração visual do dashboard de performance (sem dados reais ainda)" },
  { name: "Autentique", status: "Backlog", detail: "contratos e assinaturas sem duplicar ferramenta jurídica" },
];

export const emptyClientDraft: ClientPayload = {
  name: "",
  organization_name: "",
  status: "onboarding",
  responsible_name: "",
};

export const emptyArtifactDraft: ArtifactPayload = {
  title: "",
  kind: "briefing",
  visibility: "client",
  content: "",
  url: "",
};

export const emptyDeliverableDraft: DeliverablePayload = {
  title: "",
  status: "planned",
  due_at: "",
};

/** Converte um caminho de rota na chave de superfície correspondente.
 *
 * A convenção do catálogo é "a chave é a rota": `/eg-rh` → `eg-rh`,
 * `/operacao/radar-local` → `operacao.radar-local`. Esta função existe porque
 * a mesma conversão já foi escrita à mão em três telas — e nas três o
 * esquecimento produziu o MESMO bug: ocultar um módulo tirava do menu e
 * deixava o atalho vivo noutro lugar, o que parece defeito de quem ocultou.
 *
 * Devolve `null` para caminhos que não são superfície (ex.: `/configuracoes`),
 * e quem consome trata `null` como "sempre visível". */
export function surfaceKeyForPath(path: string): string | null {
  const clean = path.split("?")[0].replace(/^\/+|\/+$/g, "");
  if (!clean) return "cockpit";
  return clean.replace(/\//g, ".");
}

export function currentViewFromHash(): ViewId {
  const id = window.location.hash.replace("#", "") as ViewId;
  return navItems.some((item) => item.id === id) ? id : "cockpit";
}
