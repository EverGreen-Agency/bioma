import { Suspense, lazy } from "react";
import { BarChart3, Bot, FileSearch, MapPin, MessageSquare, Users, WalletCards } from "lucide-react";
import { Link, Outlet, useOutletContext } from "react-router-dom";

import { EmptyState } from "../components/shared";
import { WorkspaceShell } from "../components/WorkspaceShell";
import { useCurrentUser, useWorkspaces, useSurfaceVisibility } from "../hooks/useBiomaApi";
import { agencyWorkspaceNavItems, surfaceKeyForPath } from "../lib/app-config";
import { resolveAgencyWorkspace, type AgencyWorkspaceContext } from "../lib/workspace-context";

const AnalyticsView = lazy(() => import("./AnalyticsView").then((module) => ({ default: module.AnalyticsView })));
const CrmView = lazy(() => import("./CrmView").then((module) => ({ default: module.CrmView })));
const FinanceView = lazy(() => import("./FinanceView").then((module) => ({ default: module.FinanceView })));
const TasksView = lazy(() => import("./TasksView").then((module) => ({ default: module.TasksView })));
const AiOperationsView = lazy(() => import("./AiOperationsView").then((module) => ({ default: module.AiOperationsView })));
const MarketResearchStudio = lazy(() => import("../components/MarketResearchStudio").then((module) => ({ default: module.MarketResearchStudio })));
const ProofView = lazy(() => import("./ProofView").then((module) => ({ default: module.ProofView })));
const LocalRadarStudio = lazy(() => import("../components/LocalRadarStudio").then((module) => ({ default: module.LocalRadarStudio })));
const WhatsAppManager = lazy(() => import("../components/WhatsAppManager").then((module) => ({ default: module.WhatsAppManager })));

type AgencyWorkspaceOutletContext = {
  workspace: AgencyWorkspaceContext;
};

function ModuleLoading() {
  return <EmptyState text="Carregando módulo da Operação EG..." />;
}

export function AgencyWorkspaceView() {
  const { data: workspacesData, isLoading, isError } = useWorkspaces();
  const { data: user } = useCurrentUser();
  const { isSurfaceVisible } = useSurfaceVisibility();
  const resolution = resolveAgencyWorkspace(workspacesData ?? [], user);

  if (isLoading) {
    return <EmptyState text="Carregando Operação EG..." />;
  }

  if (resolution.status !== "ready") {
    const description = isError
      ? "Não foi possível consultar o contexto persistente deste workspace."
      : resolution.status === "missing_workspace"
        ? "A organização EG existe, mas ainda não possui um workspace interno persistente."
        : "Sua sessão não possui uma organização administrativa válida para a Operação EG.";

    return (
      <section className="workspace-empty agency-workspace-blocked">
        <span className="context-badge agency">Workspace interno</span>
        <EmptyState text="Operação EG não provisionada" />
        <p>{description}</p>
      </section>
    );
  }

  const { workspace } = resolution;
  // Decisão 11: a chave da superfície é a rota, então a sub-navegação se filtra
  // sozinha a partir do `path`. O índice não tem chave própria — quem o
  // controla é a superfície `operacao`, que já guarda esta tela inteira.
  const items = agencyWorkspaceNavItems
    .filter((item) => !item.path || isSurfaceVisible(`operacao.${item.path}`))
    .map((item) => ({
      id: item.id,
      label: item.label,
      icon: item.icon,
      to: item.path ? `/operacao/${item.path}` : "/operacao",
      end: !item.path,
    }));

  return (
    <WorkspaceShell title={workspace.name} items={items}>
      <Outlet context={{ workspace } satisfies AgencyWorkspaceOutletContext} />
    </WorkspaceShell>
  );
}

function useAgencyWorkspace() {
  return useOutletContext<AgencyWorkspaceOutletContext>();
}

export function AgencyOverviewRoute() {
  const { workspace } = useAgencyWorkspace();
  const { isSurfaceVisible } = useSurfaceVisibility();
  const allModules = [
    {
      title: "Operações de IA",
      description: "Workflows versionados, aprovações e execução auditável dos squads EG.",
      to: "/operacao/ia",
      icon: Bot,
    },
    {
      title: "Pesquisa de mercado",
      description: "Pesquisa setorial com refinamento, fontes rastreáveis e aplicação em Growth, Social e prospecção.",
      to: "/operacao/pesquisa-mercado",
      icon: FileSearch,
    },
    {
      title: "Radar Local",
      description: "Prospecção de negócios locais via Google Maps, com auditoria de presença digital e aprovação humana antes do contato.",
      to: "/operacao/radar-local",
      icon: MapPin,
    },
    {
      title: "CRM da EG",
      description: "Leads, oportunidades e pipeline comercial da própria EverGreen.",
      to: "/operacao/crm",
      icon: Users,
    },
    {
      title: "Financeiro da EG",
      description: "Recebimentos, vencimentos e visão financeira da operação interna.",
      to: "/operacao/financeiro",
      icon: WalletCards,
    },
    {
      title: "Métricas da EG",
      description: "Performance das fontes conectadas à organização EverGreen.",
      to: "/operacao/metricas",
      icon: BarChart3,
    },
    {
      title: "WhatsApp & Disparos",
      description: "Configuração multi-provedor (Evolution, Meta Cloud, Z-API, Custom), disparo experimental e auditoria.",
      to: "/operacao/whatsapp",
      icon: MessageSquare,
    },
  ];

  // Esta grade é navegação, igual ao menu lateral — logo obedece à mesma
  // resolução. Sem isto, ocultar o CRM tirava o item do menu e o deixava no
  // meio da Visão geral, que é pior que não ocultar: dá a impressão de que a
  // preferência não funcionou. A chave sai da própria rota (`/operacao/crm`
  // → `operacao.crm`), que é a convenção do catálogo.
  const modules = allModules.filter((module) => {
    const key = surfaceKeyForPath(module.to);
    return !key || isSurfaceVisible(key);
  });

  return (
    <section className="agency-workspace-home">
      <header className="agency-workspace-hero">
        <div>
          <span className="context-badge agency">Operação interna</span>
          <h1>{workspace.organizationName}</h1>
          <p>O negócio da EG vive aqui. A carteira e os hubs de clientes permanecem isolados em seus próprios workspaces.</p>
        </div>
      </header>
      <div className="agency-module-grid">
        {modules.map((module) => {
          const Icon = module.icon;
          return (
            <Link className="agency-module-card" to={module.to} key={module.to}>
              <span><Icon size={19} /></span>
              <div>
                <strong>{module.title}</strong>
                <p>{module.description}</p>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

export function AgencyCrmRoute() {
  const { workspace } = useAgencyWorkspace();
  return <Suspense fallback={<ModuleLoading />}><CrmView clientId={workspace.workspaceId} /></Suspense>;
}

export function AgencyFinanceRoute() {
  const { workspace } = useAgencyWorkspace();
  return <Suspense fallback={<ModuleLoading />}><FinanceView clientId={workspace.workspaceId} /></Suspense>;
}

export function AgencyAnalyticsRoute() {
  const { workspace } = useAgencyWorkspace();
  return (
    <Suspense fallback={<ModuleLoading />}>
      <AnalyticsView clientId={workspace.workspaceId} workspaceName={workspace.name} />
    </Suspense>
  );
}

/** Demanda interna da EG: social/tech/growth da própria casa, treinamento de
 *  time, hackathon. Mesma máquina de tarefas dos clientes, apontada para o
 *  workspace interno — sem isso a EG não conseguia usar o próprio produto. */
export function AgencyTasksRoute() {
  const { workspace } = useAgencyWorkspace();
  return <Suspense fallback={<ModuleLoading />}><TasksView workspaceId={workspace.workspaceId} /></Suspense>;
}

export function AgencyAiOperationsRoute() {
  const { workspace } = useAgencyWorkspace();
  return <Suspense fallback={<ModuleLoading />}><AiOperationsView workspaceId={workspace.workspaceId} /></Suspense>;
}

export function AgencyLocalRadarRoute() {
  return (
    <Suspense fallback={<ModuleLoading />}>
      <LocalRadarStudio />
    </Suspense>
  );
}

export function AgencyMarketResearchRoute() {
  const { workspace } = useAgencyWorkspace();
  return (
    <Suspense fallback={<ModuleLoading />}>
      <MarketResearchStudio workspaceId={workspace.workspaceId} accessRole={workspace.accessRole} />
    </Suspense>
  );
}

export function AgencyWhatsAppRoute() {
  const { workspace } = useAgencyWorkspace();
  return (
    <Suspense fallback={<ModuleLoading />}>
      <WhatsAppManager workspaceId={workspace.workspaceId} />
    </Suspense>
  );
}

/** Painel de prova (decisão de 2026-08-08). Fica na Operação EG porque é
 *  registro da própria agência, não de um cliente. */
export function AgencyProofRoute() {
  return (
    <Suspense fallback={<ModuleLoading />}>
      <ProofView />
    </Suspense>
  );
}
