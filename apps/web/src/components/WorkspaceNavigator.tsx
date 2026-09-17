import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowRight, BookmarkPlus, BriefcaseBusiness, Building2, ChevronDown, Clock3, Pin, Search, Star, Trash2, UserRound, X } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { api, type ClientSummary, type CurrentUser, type WorkspaceSavedView, type WorkspaceSummary } from "../lib/api";
import { statusLabel } from "../lib/app-config";
import { externalClients } from "../lib/client-scope";
import { resolveAgencyWorkspace } from "../lib/workspace-context";

type StoredRecentWorkspace =
  | { workspaceId: string }
  | { kind: "agency" }
  | { kind: "client"; clientId: string };

type ClientWorkspaceEntry = {
  workspace: WorkspaceSummary;
  client: ClientSummary;
};

type RecentWorkspaceEntry =
  | { kind: "agency"; workspace: WorkspaceSummary }
  | ({ kind: "client" } & ClientWorkspaceEntry);

type WorkspaceFilter = "all" | "mine" | "favorites";

function loadRecentWorkspaces(storageKey: string): StoredRecentWorkspace[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(storageKey) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is StoredRecentWorkspace => Boolean(
      item
      && typeof item === "object"
      && (
        ("workspaceId" in item && typeof item.workspaceId === "string")
        || ("kind" in item && item.kind === "agency")
        || ("kind" in item && item.kind === "client" && "clientId" in item && typeof item.clientId === "string")
      )
    ));
  } catch {
    return [];
  }
}

function normalizeSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR")
    .trim();
}

function clientIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/clientes\/([^/]+)/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

function clientSuffixFromPath(pathname: string): string {
  const match = pathname.match(/^\/clientes\/[^/]+\/(contexto|crm|financeiro|analytics|documentos|integracoes|conteudo-ia|tarefas|acessos|projetos)/);
  if (match?.[1]) return match[1];
  if (pathname.startsWith("/operacao/crm")) return "crm";
  if (pathname.startsWith("/operacao/financeiro")) return "financeiro";
  if (pathname.startsWith("/operacao/metricas")) return "analytics";
  return "";
}

function clientDestination(clientId: string, pathname: string): string {
  const suffix = clientSuffixFromPath(pathname);
  return suffix ? `/clientes/${clientId}/${suffix}` : `/clientes/${clientId}`;
}

function agencyDestination(pathname: string): string {
  const suffix = clientSuffixFromPath(pathname);
  if (suffix === "crm") return "/operacao/crm";
  if (suffix === "financeiro") return "/operacao/financeiro";
  if (suffix === "analytics") return "/operacao/metricas";
  return "/operacao";
}

export function WorkspaceNavigator({
  user,
  clients,
  workspaces,
  isLoading,
  errorMessage,
  onRetry,
}: {
  user: CurrentUser;
  clients: ClientSummary[];
  workspaces: WorkspaceSummary[];
  isLoading: boolean;
  errorMessage: string | null;
  onRetry: () => void;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<WorkspaceFilter>("all");
  const [savedViews, setSavedViews] = useState<WorkspaceSavedView[]>([]);
  const [viewName, setViewName] = useState("");
  const [isNamingView, setIsNamingView] = useState(false);
  const [navigationError, setNavigationError] = useState<string | null>(null);
  const [favoriteBusy, setFavoriteBusy] = useState<string | null>(null);
  const storageKey = `bioma_recent_workspaces_${user.id}`;
  const [recent, setRecent] = useState<StoredRecentWorkspace[]>(() => loadRecentWorkspaces(storageKey));

  useEffect(() => {
    setRecent(loadRecentWorkspaces(storageKey));
  }, [storageKey]);

  const accessibleClients = useMemo(() => externalClients(clients), [clients]);
  const agencyResolution = useMemo(() => resolveAgencyWorkspace(workspaces, user), [workspaces, user]);
  const agencyWorkspace = agencyResolution.status === "ready" ? agencyResolution.workspace : null;
  const persistedAgencyWorkspace = agencyWorkspace
    ? workspaces.find((workspace) => workspace.id === agencyWorkspace.workspaceId) ?? null
    : null;
  const isEgAdmin = user.organizations.some(
    (organization) => organization.slug === "eg" && organization.role === "eg_admin",
  );
  const clientEntries = useMemo<ClientWorkspaceEntry[]>(() => workspaces
    .filter((workspace) => workspace.kind === "client" && Boolean(workspace.client_id))
    .flatMap((workspace) => {
      const client = accessibleClients.find((candidate) => candidate.id === workspace.client_id);
      return client ? [{ workspace, client }] : [];
    }), [accessibleClients, workspaces]);

  const currentClientId = clientIdFromPath(location.pathname);
  const currentClientEntry = clientEntries.find((entry) => entry.client.id === currentClientId) ?? null;
  const fallbackCurrentClient = accessibleClients.find((client) => client.id === currentClientId) ?? null;
  const inAgencyWorkspace = location.pathname.startsWith("/operacao");

  // O rótulo é derivado da URL: mostra em QUAL WORKSPACE você está, e o
  // controle serve de atalho para trocar (Ctrl+K).
  //
  // Só existem dois contextos possíveis no Bioma, e o rótulo agora reflete
  // exatamente isso: ou você está no workspace de um cliente, ou está no da
  // agência. Wiki EG, Banco de Ideias, Cockpit, carteira e Configurações são
  // todos trabalho interno da EG — chamá-los de "fora de workspace" era tão
  // errado quanto o "Control plane · Bioma Cockpit" que estava aqui antes
  // (um workspace que não existe no banco). Quem está no Wiki EG está na
  // Operação EG; o que muda é a tela, não o workspace.
  const currentContext = currentClientEntry
    ? { eyebrow: "Workspace do cliente", label: currentClientEntry.workspace.name, icon: Building2 }
    : fallbackCurrentClient
      ? { eyebrow: "Workspace do cliente", label: fallbackCurrentClient.name, icon: Building2 }
      : { eyebrow: "Workspace da agência", label: persistedAgencyWorkspace?.name ?? "Operação EG", icon: BriefcaseBusiness };
  const CurrentIcon = currentContext.icon;

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === "k") {
        event.preventDefault();
        setIsOpen((value) => !value);
      }
      if (event.key === "Escape") setIsOpen(false);
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    setQuery("");
    setFilter("all");
    setNavigationError(null);
    void api.workspaceViews()
      .then(setSavedViews)
      .catch((error: Error) => setNavigationError(error.message));
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  function resolveStoredWorkspaceId(item: StoredRecentWorkspace): string | null {
    if ("workspaceId" in item) return item.workspaceId;
    if (item.kind === "agency") return persistedAgencyWorkspace?.id ?? null;
    return clientEntries.find((entry) => entry.client.id === item.clientId)?.workspace.id ?? null;
  }

  function rememberWorkspace(workspaceId: string) {
    const next: StoredRecentWorkspace[] = [
      { workspaceId },
      ...recent.filter((item) => resolveStoredWorkspaceId(item) !== workspaceId),
    ].slice(0, 5);
    setRecent(next);
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
    } catch {
      // Navegação continua funcional quando storage está indisponível.
    }
  }

  function openAgencyWorkspace() {
    if (!persistedAgencyWorkspace) return;
    rememberWorkspace(persistedAgencyWorkspace.id);
    navigate(agencyDestination(location.pathname));
  }

  function openClientWorkspace(entry: ClientWorkspaceEntry) {
    if (!entry.workspace.client_id) return;
    rememberWorkspace(entry.workspace.id);
    navigate(clientDestination(entry.workspace.client_id, location.pathname));
  }

  async function toggleFavorite(workspace: WorkspaceSummary) {
    setFavoriteBusy(workspace.id);
    setNavigationError(null);
    try {
      await api.favoriteWorkspace(workspace.id, !workspace.is_favorite);
      onRetry();
    } catch (error) {
      setNavigationError(error instanceof Error ? error.message : "Não foi possível atualizar o favorito.");
    } finally {
      setFavoriteBusy(null);
    }
  }

  function applySavedView(view: WorkspaceSavedView) {
    setQuery(view.filters.query);
    setFilter(view.filters.favorite_only ? "favorites" : view.filters.mine_only ? "mine" : "all");
  }

  async function saveCurrentView() {
    const name = viewName.trim();
    if (!name) return;
    setNavigationError(null);
    try {
      const created = await api.createWorkspaceView({
        name,
        tenant_organization_id: persistedAgencyWorkspace?.tenant_organization_id ?? clientEntries[0]?.workspace.tenant_organization_id,
        filters: {
          query,
          kinds: [],
          access_roles: [],
          statuses: [],
          favorite_only: filter === "favorites",
          mine_only: filter === "mine",
        },
      });
      setSavedViews((views) => [...views, created].sort((a, b) => a.name.localeCompare(b.name, "pt-BR")));
      setViewName("");
      setIsNamingView(false);
    } catch (error) {
      setNavigationError(error instanceof Error ? error.message : "Não foi possível salvar a visão.");
    }
  }

  async function deleteSavedView(viewId: string) {
    setNavigationError(null);
    try {
      setSavedViews(await api.deleteWorkspaceView(viewId));
    } catch (error) {
      setNavigationError(error instanceof Error ? error.message : "Não foi possível excluir a visão.");
    }
  }

  const normalizedQuery = normalizeSearch(query);
  const matchingClients = clientEntries.filter(({ workspace, client }) => {
    const matchesMode = filter === "all"
      || (filter === "favorites" && workspace.is_favorite)
      || (filter === "mine" && (workspace.is_assigned || workspace.access_role === "client_user"));
    return matchesMode && normalizeSearch([
      workspace.name,
      workspace.organization_name,
      workspace.tenant_name,
      workspace.responsible_name ?? client.responsible_name ?? "",
    ].join(" ")).includes(normalizedQuery);
  });
  const agencyMatches = isEgAdmin && normalizeSearch([
    persistedAgencyWorkspace?.name ?? "Operação EG",
    persistedAgencyWorkspace?.tenant_name ?? "EverGreen",
    "agência interno",
  ].join(" ")).includes(normalizedQuery);

  const recentEntries = recent.reduce<RecentWorkspaceEntry[]>((entries, item) => {
    const workspaceId = resolveStoredWorkspaceId(item);
    if (!workspaceId || entries.some((entry) => entry.workspace.id === workspaceId)) return entries;
    if (persistedAgencyWorkspace?.id === workspaceId) {
      entries.push({ kind: "agency", workspace: persistedAgencyWorkspace });
      return entries;
    }
    const clientEntry = clientEntries.find((entry) => entry.workspace.id === workspaceId);
    if (clientEntry) entries.push({ kind: "client", ...clientEntry });
    return entries;
  }, []);
  const recentKeys = new Set(recentEntries.map((entry) => entry.workspace.id));

  const dialog = isOpen ? createPortal(
    <div
      className="workspace-navigator-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) setIsOpen(false);
      }}
    >
      <section className="workspace-navigator" role="dialog" aria-modal="true" aria-labelledby="workspace-navigator-title">
        <header className="workspace-navigator-header">
          <div>
            <span>Contexto operacional</span>
            <h2 id="workspace-navigator-title">Navegar entre workspaces</h2>
          </div>
          <button className="icon-button" type="button" onClick={() => setIsOpen(false)} aria-label="Fechar navegador">
            <X size={18} />
          </button>
        </header>

        <label className="workspace-search">
          <Search size={18} aria-hidden="true" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar cliente, organização ou responsável..."
          />
          <kbd>Esc</kbd>
        </label>

        <div className="workspace-filterbar" aria-label="Filtros de carteira">
          {([
            ["all", "Todos"],
            ["mine", "Minha carteira"],
            ["favorites", "Favoritos"],
          ] as const).map(([value, label]) => (
            <button
              className={filter === value ? "active" : ""}
              type="button"
              onClick={() => setFilter(value)}
              key={value}
            >
              {value === "mine" && <UserRound size={13} />}
              {value === "favorites" && <Star size={13} />}
              {label}
            </button>
          ))}
          <button className="save-view-trigger" type="button" onClick={() => setIsNamingView((value) => !value)}>
            <BookmarkPlus size={13} /> Salvar visão
          </button>
        </div>

        {isNamingView && (
          <div className="workspace-save-view">
            <input
              value={viewName}
              onChange={(event) => setViewName(event.target.value)}
              placeholder="Nome da visão"
              maxLength={80}
              onKeyDown={(event) => {
                if (event.key === "Enter") void saveCurrentView();
              }}
            />
            <button type="button" disabled={!viewName.trim()} onClick={() => void saveCurrentView()}>Salvar</button>
          </div>
        )}

        {savedViews.length > 0 && (
          <div className="workspace-saved-views">
            {savedViews.map((view) => (
              <span key={view.id}>
                <button type="button" onClick={() => applySavedView(view)}>{view.name}</button>
                <button type="button" aria-label={`Excluir visão ${view.name}`} onClick={() => void deleteSavedView(view.id)}>
                  <Trash2 size={12} />
                </button>
              </span>
            ))}
          </div>
        )}

        {navigationError && <div className="workspace-navigation-error" role="alert">{navigationError}</div>}

        <div className="workspace-navigator-results">
          {/* A Operação EG fica FIXA no topo, fora de "Recentes".
              É o workspace onde a EG trabalha todo dia; deixá-lo competir por
              espaço na lista de recentes fazia a casa da agência sumir
              justamente quando se atende muitos clientes seguidos. */}
          {!isLoading && !errorMessage && isEgAdmin && agencyMatches && (
            <div className="workspace-result-section">
              <div className="workspace-result-label"><Pin size={13} /> Agência</div>
              <button
                className={`workspace-result ${inAgencyWorkspace ? "active" : ""}`}
                type="button"
                onClick={openAgencyWorkspace}
              >
                <span className="workspace-result-icon agency"><BriefcaseBusiness size={17} /></span>
                <span>
                  <strong>{persistedAgencyWorkspace?.name || "Operação EG"}</strong>
                  <small>CRM, financeiro e métricas da própria agência</small>
                </span>
                <span className="workspace-kind-pill">Interno</span>
              </button>
            </div>
          )}

          {!isLoading && !errorMessage && !normalizedQuery && recentEntries.length > 0 && (
            <div className="workspace-result-section">
              <div className="workspace-result-label"><Clock3 size={13} /> Recentes</div>
              {recentEntries.map((entry) => entry.kind === "agency" ? (
                <button className="workspace-result" type="button" key={entry.workspace.id} onClick={openAgencyWorkspace}>
                  <span className="workspace-result-icon agency"><BriefcaseBusiness size={17} /></span>
                  <span><strong>{entry.workspace.name}</strong><small>Workspace interno · {entry.workspace.tenant_name}</small></span>
                  <ArrowRight size={16} />
                </button>
              ) : (
                <WorkspaceClientResult
                  entry={entry}
                  onSelect={() => openClientWorkspace(entry)}
                  onToggleFavorite={() => void toggleFavorite(entry.workspace)}
                  favoriteBusy={favoriteBusy === entry.workspace.id}
                  key={entry.workspace.id}
                />
              ))}
            </div>
          )}

          {!isLoading && !errorMessage && matchingClients.some((entry) => normalizedQuery || !recentKeys.has(entry.workspace.id)) && (
            <div className="workspace-result-section">
              <div className="workspace-result-label">Clientes disponíveis · {matchingClients.length}</div>
              {matchingClients
                .filter((entry) => normalizedQuery || !recentKeys.has(entry.workspace.id))
                .map((entry) => (
                  <WorkspaceClientResult
                    entry={entry}
                    active={currentClientEntry?.workspace.id === entry.workspace.id}
                    onSelect={() => openClientWorkspace(entry)}
                    onToggleFavorite={() => void toggleFavorite(entry.workspace)}
                    favoriteBusy={favoriteBusy === entry.workspace.id}
                    key={entry.workspace.id}
                  />
                ))}
            </div>
          )}

          {!isLoading && !errorMessage && !agencyMatches && matchingClients.length === 0 && (
            <div className="workspace-navigator-empty">Nenhum workspace corresponde à busca.</div>
          )}
          {isLoading && <div className="workspace-navigator-empty">Carregando workspaces...</div>}
          {!isLoading && errorMessage && (
            <div className="workspace-navigator-empty workspace-navigator-error" role="alert">
              <strong>Não foi possível carregar os workspaces.</strong>
              <small>{errorMessage}</small>
              <button type="button" onClick={onRetry}>Tentar novamente</button>
            </div>
          )}
        </div>

        <footer className="workspace-navigator-footer">
          {isEgAdmin && (
            <button type="button" onClick={() => navigate("/clientes")}>
              Abrir carteira completa <ArrowRight size={14} />
            </button>
          )}
          <span>Ctrl/⌘ K para abrir de qualquer tela</span>
        </footer>
      </section>
    </div>,
    document.body,
  ) : null;

  return (
    <>
      <button
        className="workspace-navigator-trigger"
        type="button"
        onClick={() => setIsOpen(true)}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
      >
        <span className="workspace-trigger-icon"><CurrentIcon size={17} /></span>
        <span className="workspace-trigger-copy">
          <small>{currentContext.eyebrow}</small>
          <strong>{currentContext.label}</strong>
        </span>
        <ChevronDown size={16} />
      </button>
      {dialog}
    </>
  );
}

function WorkspaceClientResult({
  entry,
  active = false,
  onSelect,
  onToggleFavorite,
  favoriteBusy,
}: {
  entry: ClientWorkspaceEntry;
  active?: boolean;
  onSelect: () => void;
  onToggleFavorite: () => void;
  favoriteBusy: boolean;
}) {
  const { client, workspace } = entry;
  return (
    <div className={`workspace-result-row ${active ? "active" : ""}`}>
      <button className="workspace-result" type="button" onClick={onSelect}>
        <span className="workspace-result-icon"><Building2 size={17} /></span>
        <span>
          <strong>{workspace.name}</strong>
          <small>{workspace.responsible_name ? `Responsável: ${workspace.responsible_name}` : workspace.organization_name}</small>
        </span>
        <span className="workspace-kind-pill">{statusLabel[client.status]}</span>
      </button>
      <button
        className={`workspace-favorite ${workspace.is_favorite ? "active" : ""}`}
        type="button"
        disabled={favoriteBusy}
        aria-label={workspace.is_favorite ? `Remover ${workspace.name} dos favoritos` : `Favoritar ${workspace.name}`}
        onClick={onToggleFavorite}
      >
        <Star size={15} fill={workspace.is_favorite ? "currentColor" : "none"} />
      </button>
    </div>
  );
}
