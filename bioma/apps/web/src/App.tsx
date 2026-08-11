import { FormEvent, ReactNode, Suspense, lazy, useEffect, useState } from "react";
import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { enabledModulesFor, navItems, viewModule, type ViewId } from "./lib/app-config";
import type { UserOrganization } from "./lib/api";
import { externalClients } from "./lib/client-scope";
import { SettingsView } from "./views/SettingsView";
import { CockpitView } from "./views/CockpitView";
import { LoginView } from "./views/LoginView";
import { InviteView } from "./views/InviteView";
import { ResetPasswordView } from "./views/ResetPasswordView";
import { PrivacyView } from "./views/PrivacyView";
import { PublicProposalView } from "./views/PublicProposalView";
import { ArtifactModal } from "./components/ArtifactModal";
import { CopilotPanel } from "./components/CopilotPanel";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { useUiStore } from "./store/uiStore";
import { useApiHealth, useCurrentUser, useClients, useWorkspaces, useLogin, useLogout, useUpdateArtifact, useDeleteArtifact, useSurfaceVisibility } from "./hooks/useBiomaApi";
import { normalizeArtifactPayload } from "./lib/format";
import { emptyArtifactDraft } from "./lib/app-config";
import {
  ClientAnalyticsRoute,
  ClientAiContentRoute,
  ClientCrmRoute,
  ClientFinanceRoute,
  ClientTasksRoute,
  ClientIntegrationsRoute,
  ClientFilesRoute,
  ClientProfileRoute,
  ClientVaultRoute,
  ClientProjectsRoute,
  ClientWorkspaceView,
} from "./views/ClientWorkspaceView";

const ClientsView = lazy(() => import("./views/ClientsView").then((module) => ({ default: module.ClientsView })));
const ClientHubView = lazy(() => import("./views/ClientHubView").then((module) => ({ default: module.ClientHubView })));
const WikiEgView = lazy(() => import("./views/admin/WikiEgView").then((module) => ({ default: module.WikiEgView })));
const EngineeringView = lazy(() => import("./views/EngineeringView").then((module) => ({ default: module.EngineeringView })));
const AgencyWorkspaceView = lazy(() => import("./views/AgencyWorkspaceView").then((module) => ({ default: module.AgencyWorkspaceView })));
const AgencyOverviewRoute = lazy(() => import("./views/AgencyWorkspaceView").then((module) => ({ default: module.AgencyOverviewRoute })));
const AgencyCrmRoute = lazy(() => import("./views/AgencyWorkspaceView").then((module) => ({ default: module.AgencyCrmRoute })));
const AgencyTasksRoute = lazy(() => import("./views/AgencyWorkspaceView").then((module) => ({ default: module.AgencyTasksRoute })));
const AgencyFinanceRoute = lazy(() => import("./views/AgencyWorkspaceView").then((module) => ({ default: module.AgencyFinanceRoute })));
const AgencyAnalyticsRoute = lazy(() => import("./views/AgencyWorkspaceView").then((module) => ({ default: module.AgencyAnalyticsRoute })));
const AgencyAiOperationsRoute = lazy(() => import("./views/AgencyWorkspaceView").then((module) => ({ default: module.AgencyAiOperationsRoute })));
const AgencyMarketResearchRoute = lazy(() => import("./views/AgencyWorkspaceView").then((module) => ({ default: module.AgencyMarketResearchRoute })));
const AgencyProofRoute = lazy(() => import("./views/AgencyWorkspaceView").then((module) => ({ default: module.AgencyProofRoute })));
const AgencyLocalRadarRoute = lazy(() => import("./views/AgencyWorkspaceView").then((module) => ({ default: module.AgencyLocalRadarRoute })));


// Views administrativas EG
const IdeaBankView = lazy(() => import("./views/admin/idea-bank/IdeaBank").then((module) => ({ default: module.IdeaBank })));
const TechRadarView = lazy(() => import("./views/admin/tech-radar/TechRadar").then((module) => ({ default: module.TechRadar })));
const ArchitectureView = lazy(() =>
  import("./views/admin/architecture/ArchitectureView").then((module) => ({ default: module.ArchitectureView })),
);
const RhManagerView = lazy(() =>
  import("./views/admin/rh/RhManager").then((module) => ({ default: module.RhManager })),
);
const KitsManagerView = lazy(() =>
  import("./views/admin/kits/KitsManager").then((module) => ({ default: module.KitsManager })),
);
const ProposalsManagerView = lazy(() =>
  import("./views/admin/proposals/ProposalsManager").then((module) => ({ default: module.ProposalsManager })),
);
const SalesCopilotView = lazy(() =>
  import("./views/admin/proposals/SalesCopilotView").then((module) => ({ default: module.SalesCopilotView })),
);
const WinsView = lazy(() =>
  import("./views/admin/WinsView").then((module) => ({ default: module.WinsView })),
);
const PlatformStudiesView = lazy(() =>
  import("./views/admin/PlatformStudiesView").then((module) => ({ default: module.PlatformStudiesView })),
);
const PlanningPortfolioView = lazy(() =>
  import("./views/admin/proposals/PlanningPortfolioView").then((module) => ({ default: module.PlanningPortfolioView })),
);

function ViewLoadingFallback() {
  return <div className="notice">Carregando módulo...</div>;
}

export function App() {
  const routerNavigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [loginError, setLoginError] = useState("");
  
  const { data: healthData } = useApiHealth();
  const { data: user } = useCurrentUser();
  const login = useLogin();
  const logout = useLogout();

  const {
    selectedClientId,
    setSelectedClientId,
    selectedArtifact,
    setSelectedArtifact,
    artifactEditDraft,
    setArtifactEditDraft,
    dataError,
  } = useUiStore();

  const {
    data: clientsData,
    isLoading: loadingClients,
    isError: clientsFailed,
    error: clientsError,
    refetch: refetchClients,
  } = useClients();
  const {
    data: workspacesData,
    isLoading: loadingWorkspaces,
    isError: workspacesFailed,
    error: workspacesError,
    refetch: refetchWorkspaces,
  } = useWorkspaces(Boolean(user));
  const allClients = clientsData ?? [];
  const workspaces = workspacesData ?? [];
  const clients = externalClients(allClients);

  const updateArtifact = useUpdateArtifact();
  const deleteArtifact = useDeleteArtifact();

  const apiOnline = healthData?.status === "ok";
  // Pertencer à EG decide o que a pessoa ENXERGA. `eg_member` (0090) entra
  // aqui; quem ADMINISTRA é outra pergunta, respondida pelo backend em cada
  // escrita (`require_platform_admin`).
  //
  // Saiu daqui um `user.email.endsWith("@evergreengrowth.com.br")` que
  // concedia visão de admin por domínio de e-mail, hardcoded — e no domínio
  // ERRADO (o resto do sistema usa evergreenmkt.com.br). Não vazava dado,
  // porque o backend decide por papel, mas mostrava a interface de admin para
  // quem levaria 403 em tudo. Privilégio nunca deve vir do e-mail.
  const isEgAdmin = user
    ? user.organizations.some(
        (org: UserOrganization) =>
          org.slug === "eg" && (org.role === "eg_admin" || org.role === "eg_member"),
      )
    : false;

  useEffect(() => {
    if (
      !user &&
      location.pathname !== "/" &&
      location.pathname !== "/privacidade" &&
      !location.pathname.startsWith("/convite/") &&
      !location.pathname.startsWith("/redefinir/")
    ) {
      routerNavigate("/");
    }
  }, [user, location.pathname, routerNavigate]);

  // Erros do fluxo OAuth chegam por redirect (?oauth_error=...) porque o
  // callback é navegação de página, não fetch.
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const oauthError = params.get("oauth_error");
    if (oauthError && !user) {
      setLoginError(oauthError);
      window.history.replaceState(null, "", location.pathname);
    }
  }, [location.search, location.pathname, user]);


  useEffect(() => {
    if (!selectedArtifact) {
      setArtifactEditDraft(emptyArtifactDraft);
      return;
    }
    setArtifactEditDraft({
      title: selectedArtifact.title,
      kind: selectedArtifact.kind,
      visibility: selectedArtifact.visibility,
      content: selectedArtifact.content ?? "",
      url: selectedArtifact.url ?? "",
    });
  }, [selectedArtifact, setArtifactEditDraft]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginError("");
    login.mutate(
      { email, password, remember_me: rememberMe },
      {
        onSuccess: () => {
          setPassword("");
          routerNavigate("/");
        },
        onError: (error) => {
          setLoginError(error instanceof Error ? error.message : "Credenciais inválidas ou banco não migrado.");
        }
      }
    );
  }

  function handleLogout() {
    logout.mutate(undefined, {
      onSuccess: () => {
        setSelectedClientId(null);
        routerNavigate("/");
      }
    });
  }

  function handleUpdateArtifact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedClientId || !selectedArtifact) return;
    const payload = normalizeArtifactPayload(artifactEditDraft);
    updateArtifact.mutate({ clientId: selectedClientId, artifactId: selectedArtifact.id, payload }, {
      onSuccess: () => setSelectedArtifact(null)
    });
  }

  function handleDeleteArtifact() {
    if (!selectedClientId || !selectedArtifact) return;
    deleteArtifact.mutate({ clientId: selectedClientId, artifactId: selectedArtifact.id }, {
      onSuccess: () => setSelectedArtifact(null)
    });
  }

  const enabledModules = enabledModulesFor(user, isEgAdmin);

  // Decisão 11: a resolução dos 4 níveis (organização → equipe → usuário →
  // preferência) vem pronta do backend, com o motivo junto. A regra de fallback
  // (enquanto carrega, mostra) mora no hook, não aqui.
  const { isSurfaceVisible, isSurfaceAllowed } = useSurfaceVisibility();

  const visibleNavItems = navItems
    .filter((item) => enabledModules.has(viewModule[item.id]))
    .filter((item) => isEgAdmin || item.id === "clientes")
    .filter((item) => isSurfaceVisible(item.id))
    .map((item) => !isEgAdmin && item.id === "clientes" ? { ...item, label: "Meu Hub" } : item);
  const clientHomePath = !isEgAdmin && clients.length === 1 ? `/clientes/${clients[0].id}` : "/clientes";

  function guard(view: ViewId, element: ReactNode) {
    return enabledModules.has(viewModule[view]) ? element : <Navigate to="/" replace />;
  }

  function guardAdmin(element: ReactNode) {
    return isEgAdmin ? element : <Navigate to="/" replace />;
  }

  /** Guarda por superfície: usa `allowed`, nunca `visible`.
   *
   * A diferença é o ponto inteiro da decisão 11 — o que a pessoa escondeu do
   * menu continua acessível pela URL. Trocar por `visible` aqui transformaria
   * preferência em bloqueio e deixaria links salvos quebrados. */
  function guardSurface(surfaceKey: string, element: ReactNode) {
    if (!isEgAdmin) return <Navigate to="/" replace />;
    return isSurfaceAllowed(surfaceKey) ? element : <Navigate to="/" replace />;
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/convite/:token" element={<InviteView />} />
        <Route path="/redefinir/:token" element={<ResetPasswordView />} />
        <Route path="/privacidade" element={<PrivacyView />} />
        <Route path="/propostas/public/:token" element={<PublicProposalView />} />
        <Route
          path="*"
          element={
            <LoginView
              email={email}
              password={password}
              rememberMe={rememberMe}
              loginError={loginError}
              apiOnline={apiOnline}
              isSubmitting={login.isPending}
              onEmailChange={setEmail}
              onPasswordChange={setPassword}
              onRememberMeChange={setRememberMe}
              onSubmit={handleLogin}
            />
          }
        />
      </Routes>
    );
  }

  return (
    <main className="app-shell">
      <Sidebar
        visibleNavItems={visibleNavItems}
        user={user}
        onLogout={handleLogout}
        isLoggingOut={logout.isPending}
        clientHomePath={clientHomePath}
      />

      <section className="workspace">
        <Topbar
          user={user}
          clients={allClients}
          workspaces={workspaces}
          isLoading={loadingClients || loadingWorkspaces}
          errorMessage={clientsFailed || workspacesFailed
            ? (workspacesError ?? clientsError)?.message ?? "Não foi possível carregar os workspaces."
            : null}
          onRetry={() => {
            void refetchClients();
            void refetchWorkspaces();
          }}
        />

        {dataError && <div className="notice error">{dataError}</div>}

        <Routes>
          <Route
            path="/"
            element={
              isEgAdmin
                ? <CockpitView />
                : loadingClients
                  ? <ViewLoadingFallback />
                  : <Navigate to={clientHomePath} replace />
            }
          />
          <Route path="/configuracoes" element={<SettingsView />} />

          <Route path="/operacao" element={guardSurface("operacao",
            <Suspense fallback={<ViewLoadingFallback />}>
              <AgencyWorkspaceView />
            </Suspense>,
          )}>
            <Route index element={<AgencyOverviewRoute />} />
            <Route path="tarefas" element={guardSurface("operacao.tarefas", <AgencyTasksRoute />)} />
            <Route path="crm" element={guardSurface("operacao.crm", <AgencyCrmRoute />)} />
            <Route path="financeiro" element={guardSurface("operacao.financeiro", <AgencyFinanceRoute />)} />
            <Route path="metricas" element={guardSurface("operacao.metricas", <AgencyAnalyticsRoute />)} />
            <Route path="ia" element={guardSurface("operacao.ia", <AgencyAiOperationsRoute />)} />
            <Route path="pesquisa-mercado" element={guardSurface("operacao.pesquisa-mercado", <AgencyMarketResearchRoute />)} />
            <Route path="radar-local" element={guardSurface("operacao.radar-local", <AgencyLocalRadarRoute />)} />
            <Route path="prova" element={guardSurface("operacao.prova", <AgencyProofRoute />)} />
            {/* As integrações da EG moram em Configurações → Empresa →
                Integrações, junto das credenciais do ambiente. Esta rota fica
                como atalho para quem já tinha o link. */}
            <Route path="integracoes" element={<Navigate to="/configuracoes" replace />} />
          </Route>

          <Route path="/clientes" element={guard("clientes",
            <Suspense fallback={<ViewLoadingFallback />}>
              <ClientsView />
            </Suspense>,
          )} />
          
          <Route path="/clientes/:id" element={guard("clientes", <ClientWorkspaceView />)}>
            <Route index element={
              <Suspense fallback={<ViewLoadingFallback />}>
                <ClientHubView />
              </Suspense>
            } />
            <Route path="crm" element={<ClientCrmRoute />} />
            <Route path="tarefas" element={<ClientTasksRoute />} />
            <Route path="conteudo-ia" element={<ClientAiContentRoute />} />
            <Route path="contexto" element={<ClientProfileRoute />} />
            <Route path="financeiro" element={<ClientFinanceRoute />} />
            <Route path="analytics" element={<ClientAnalyticsRoute />} />
            <Route path="documentos" element={<ClientFilesRoute />} />
            <Route path="acessos" element={<ClientVaultRoute />} />
            <Route path="projetos" element={<ClientProjectsRoute />} />
            <Route path="integracoes" element={guardAdmin(<ClientIntegrationsRoute />)} />
          </Route>

          {/* Compatibilidade: módulos operacionais sempre resolvem um workspace explícito. */}
          <Route path="/crm" element={<Navigate to={isEgAdmin ? "/operacao/crm" : clientHomePath} replace />} />
          <Route path="/finance" element={<Navigate to={isEgAdmin ? "/operacao/financeiro" : clientHomePath} replace />} />
          <Route path="/analytics" element={<Navigate to={isEgAdmin ? "/operacao/metricas" : clientHomePath} replace />} />

          <Route path="/engenharia" element={guardSurface("engenharia",
            <Suspense fallback={<ViewLoadingFallback />}>
              <EngineeringView />
            </Suspense>,
          )} />

          {/* Rotas Administrativas EG */}
          <Route path="/eg-wiki" element={guardSurface("eg-wiki",
            <Suspense fallback={<ViewLoadingFallback />}>
              <WikiEgView />
            </Suspense>,
          )} />
          <Route path="/eg-ideas" element={guardSurface("eg-ideas",
            <Suspense fallback={<ViewLoadingFallback />}>
              <IdeaBankView />
            </Suspense>,
          )} />
          <Route path="/eg-tech" element={guardSurface("eg-tech",
            <Suspense fallback={<ViewLoadingFallback />}>
              <TechRadarView />
            </Suspense>,
          )} />
          <Route path="/eg-architecture" element={guardSurface("eg-architecture",
            <Suspense fallback={<ViewLoadingFallback />}>
              <ArchitectureView />
            </Suspense>,
          )} />
          <Route path="/eg-rh" element={guardSurface("eg-rh",
            <Suspense fallback={<ViewLoadingFallback />}>
              <RhManagerView />
            </Suspense>,
          )} />
          <Route path="/eg-kits" element={guardSurface("eg-kits",
            <Suspense fallback={<ViewLoadingFallback />}>
              <KitsManagerView />
            </Suspense>,
          )} />
          <Route path="/eg-propostas" element={guardSurface("eg-propostas",
            <Suspense fallback={<ViewLoadingFallback />}>
              <ProposalsManagerView />
            </Suspense>,
          )} />
          <Route path="/sales_copilot" element={guardSurface("sales_copilot",
            <Suspense fallback={<ViewLoadingFallback />}>
              <SalesCopilotView />
            </Suspense>,
          )} />
          <Route path="/eg-planning" element={guardSurface("eg-planning",
            <Suspense fallback={<ViewLoadingFallback />}>
              <PlanningPortfolioView />
            </Suspense>,
          )} />
          <Route path="/eg-vitorias" element={guardSurface("eg-vitorias",
            <Suspense fallback={<ViewLoadingFallback />}>
              <WinsView />
            </Suspense>,
          )} />
          <Route path="/eg-plataformas" element={guardSurface("eg-plataformas",
            <Suspense fallback={<ViewLoadingFallback />}>
              <PlatformStudiesView />
            </Suspense>,
          )} />

          <Route path="/convite/:token" element={<InviteView />} />
          <Route path="/redefinir/:token" element={<ResetPasswordView />} />
          <Route path="/privacidade" element={<PrivacyView />} />
          <Route path="/propostas/public/:token" element={<PublicProposalView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </section>

      {/* Copiloto: só EG. O painel fala com `/copilot`, que responde 403 para
          usuário de cliente — renderizar para eles seria oferecer uma porta
          fechada.

          Usa `isSurfaceVisible` (não `isSurfaceAllowed`) porque aqui não existe
          URL para acessar por fora: o painel é a única porta. Esconder é o
          mesmo que não ter, e é essa a escolha que a preferência oferece. */}
      {isEgAdmin && isSurfaceVisible("copiloto") && <CopilotPanel />}

      {selectedArtifact && (
        <ArtifactModal
          artifact={selectedArtifact}
          isEgAdmin={isEgAdmin}
          actionBusy={updateArtifact.isPending || deleteArtifact.isPending ? "artifact" : null}
          draft={artifactEditDraft}
          setDraft={setArtifactEditDraft}
          onSubmit={handleUpdateArtifact}
          onDelete={handleDeleteArtifact}
          onClose={() => setSelectedArtifact(null)}
        />
      )}
    </main>
  );
}
