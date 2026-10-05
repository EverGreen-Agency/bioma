import { useMemo, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { useWorkspaces } from "../../hooks/useBiomaApi";
import {
  useBrandBook,
  useCalendarItems,
  useCreateCalendarItem,
  useUpdateCalendarItem,
  useUpdateCalendarStage,
} from "../../hooks/api/ai";
import { api, type AiContentRequest, type EditorialCalendarItemSummary as Item, type WorkspaceSummary } from "../../lib/api";
import {
  dayKey,
  emptyDraft,
  type Assignee,
  type CalendarView,
  type Draft,
} from "./types";
import { PresenceHeader } from "./PresenceHeader";
import { PresenceBrandContext } from "./PresenceBrandContext";
import { PresenceStudioDrafts } from "./PresenceStudioDrafts";
import { PresenceToolbar } from "./PresenceToolbar";
import { PresenceCalendarGrid } from "./PresenceCalendarGrid";
import { PresenceListView } from "./PresenceListView";
import { PresenceUnscheduled } from "./PresenceUnscheduled";
import { PresenceDetailModal } from "./PresenceDetailModal";
import { PresenceHandoffModal } from "./PresenceHandoffModal";
import "../../styles/presenca.css";

export function PresenceView() {
  const { data: workspaces, isLoading, isError } = useWorkspaces();
  const [params, setParams] = useSearchParams();

  const available = (workspaces ?? []).filter(
    (w) => w.access_role === "platform_admin" || w.enabled_modules.includes("content")
  );
  const requested = params.get("workspaceId");
  const workspace = available.find((w) => w.id === requested) ?? available[0];

  return (
    <div className="presence-page">
      <PresenceHeader
        workspaces={available}
        selectedWorkspace={workspace ?? null}
        onSelectWorkspace={(id) => setParams({ workspaceId: id })}
      />

      {isLoading ? (
        <div className="presence-loading-state">
          <p>Carregando workspaces com módulo de conteúdo…</p>
        </div>
      ) : isError ? (
        <div className="presence-error-state" role="alert">
          <p>Não foi possível carregar os workspaces.</p>
        </div>
      ) : workspace ? (
        <PresenceCalendar key={workspace.id} workspace={workspace} />
      ) : (
        <div className="presence-empty-state">
          <p>Nenhum workspace com o módulo de conteúdo está disponível para sua conta.</p>
        </div>
      )}
    </div>
  );
}

export function PresenceCalendar({ workspace }: { workspace: WorkspaceSummary }) {
  const { data: brandBook, isLoading: brandBookLoading, isError: brandBookError } = useBrandBook(workspace.id);

  const { data: generated = [], isError: generatedError } = useQuery({
    queryKey: ["ai-content", workspace.id],
    queryFn: () => api.aiContentRequests(workspace.id),
  });

  const { data: items = [], isLoading, error } = useCalendarItems(workspace.id);

  const { data: assignments = [] } = useQuery({
    queryKey: ["workspace-assignments", workspace.id],
    queryFn: () => api.workspaceAssignments(workspace.id),
    enabled: Boolean(workspace.id),
  });

  const { data: people = [] } = useQuery({
    queryKey: ["tenant-people", workspace.tenant_organization_id],
    queryFn: () => api.organizationPeople(workspace.tenant_organization_id),
    enabled: Boolean(workspace.tenant_organization_id),
  });

  const create = useCreateCalendarItem();
  const update = useUpdateCalendarItem();
  const move = useUpdateCalendarStage();

  const [view, setView] = useState<CalendarView>("month");
  const [channelFilter, setChannelFilter] = useState<Item["channel"] | "all">("all");
  const [stageFilter, setStageFilter] = useState<Item["stage"] | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [anchor, setAnchor] = useState(() => new Date());

  const [selected, setSelected] = useState<Item | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [handoffModalOpen, setHandoffModalOpen] = useState(false);
  const [handoffItem, setHandoffItem] = useState<Item | null>(null);

  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [formError, setFormError] = useState("");

  const canManage = ["platform_admin", "tenant_admin", "workspace_manager", "operator"].includes(
    workspace.access_role
  );
  const canApprove = ["platform_admin", "tenant_admin", "workspace_manager", "approver", "client_user"].includes(
    workspace.access_role
  );

  const isBusy = create.isPending || update.isPending || move.isPending;

  // Filter items
  const visibleItems = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return items.filter((item) => {
      if (channelFilter !== "all" && item.channel !== channelFilter) return false;
      if (stageFilter !== "all" && item.stage !== stageFilter) return false;
      if (query) {
        const titleMatch = item.title.toLowerCase().includes(query);
        const textMatch = item.post_text?.toLowerCase().includes(query) ?? false;
        const tags = Array.isArray(item.metadata?.campaign_tags)
          ? (item.metadata.campaign_tags as string[]).map((t) => t.toLowerCase())
          : [];
        const tagMatch = tags.some((t) => t.includes(query));
        const assignee = item.metadata?.assigned_to as Assignee | null | undefined;
        const assigneeMatch = assignee?.name.toLowerCase().includes(query) ?? false;
        if (!titleMatch && !textMatch && !tagMatch && !assigneeMatch) return false;
      }
      return true;
    });
  }, [items, channelFilter, stageFilter, searchQuery]);

  // Calendar dates
  const days = useMemo(() => {
    if (view === "list") return [];
    const start = new Date(
      anchor.getFullYear(),
      anchor.getMonth(),
      view === "month" ? 1 : anchor.getDate()
    );
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    const count = view === "month" ? 42 : 7;
    return Array.from(
      { length: count },
      (_, index) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + index)
    );
  }, [anchor, view]);

  // Group items by day
  const itemsByDay = useMemo(() => {
    const map = new Map<string, Item[]>();
    for (const item of visibleItems) {
      if (!item.scheduled_at) continue;
      const key = dayKey(new Date(item.scheduled_at));
      map.set(key, [...(map.get(key) ?? []), item]);
    }
    return map;
  }, [visibleItems]);

  const unscheduledItems = visibleItems.filter((item) => !item.scheduled_at);
  const scheduledCount = items.filter((item) => item.scheduled_at).length;

  const periodLabel =
    view === "week"
      ? `Semana de ${days[0]?.toLocaleDateString("pt-BR", { day: "2-digit", month: "long" })}`
      : anchor.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });

  function openDetail(item: Item | null, date?: Date) {
    setSelected(item);
    setDetailModalOpen(true);
    setFormError("");

    if (item) {
      setDraft({
        title: item.title,
        content_type: item.content_type,
        channel: item.channel,
        scheduled_at: item.scheduled_at,
        post_text: item.post_text ?? "",
        media_urls: [...item.media_urls],
        metadata: {
          assigned_to: (item.metadata?.assigned_to as Assignee | null | undefined) ?? null,
          campaign_tags: Array.isArray(item.metadata?.campaign_tags)
            ? [...(item.metadata.campaign_tags as string[])]
            : [],
          ...item.metadata,
        },
      });
    } else {
      const initialDate = date
        ? new Date(date.getFullYear(), date.getMonth(), date.getDate(), 9, 0, 0).toISOString()
        : null;
      setDraft({
        ...emptyDraft(),
        scheduled_at: initialDate,
      });
    }
  }

  function shiftPeriod(direction: number) {
    setAnchor((current) =>
      view === "month"
        ? new Date(current.getFullYear(), current.getMonth() + direction, 1)
        : new Date(current.getFullYear(), current.getMonth(), current.getDate() + direction * 7)
    );
  }

  async function saveItem(event: FormEvent) {
    event.preventDefault();
    setFormError("");
    try {
      if (selected) {
        await update.mutateAsync({
          workspaceId: workspace.id,
          itemId: selected.id,
          payload: {
            title: draft.title,
            content_type: draft.content_type,
            channel: draft.channel,
            scheduled_at: draft.scheduled_at,
            post_text: draft.post_text,
            media_urls: draft.media_urls,
            metadata: draft.metadata,
          },
        });
      } else {
        await create.mutateAsync({
          workspaceId: workspace.id,
          payload: {
            title: draft.title,
            content_type: draft.content_type,
            channel: draft.channel,
            stage: "ideation",
            scheduled_at: draft.scheduled_at,
            post_text: draft.post_text,
            media_urls: draft.media_urls,
            metadata: draft.metadata,
          },
        });
      }
      setSelected(null);
      setDetailModalOpen(false);
      setDraft(emptyDraft());
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : "Não foi possível salvar a peça editorial.");
    }
  }

  async function changeStage(item: Item, stage: Item["stage"]) {
    setFormError("");
    try {
      await move.mutateAsync({
        workspaceId: workspace.id,
        itemId: item.id,
        stage,
      });
      setSelected(null);
      setDetailModalOpen(false);
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : "Não foi possível alterar a etapa da esteira.");
    }
  }

  async function importGeneratedPost(request: AiContentRequest, index: number) {
    const post = request.output?.posts?.[index];
    if (!post) return;
    setFormError("");
    try {
      await create.mutateAsync({
        workspaceId: workspace.id,
        payload: {
          title: post.title,
          content_type: "social_post",
          channel: post.channel,
          stage: "ideation",
          post_text: post.caption,
          media_urls: [],
          metadata: {
            source_type: "ai_content_request",
            ai_content_request_id: request.id,
            output_index: index,
            generation_mode: request.generation_mode,
            provider: request.provider,
            model: request.model,
          },
        },
      });
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : "Não foi possível importar o rascunho de IA.");
    }
  }

  function openHandoff(item: Item) {
    setHandoffItem(item);
    setHandoffModalOpen(true);
  }

  return (
    <div className="presence-calendar-container">
      {/* Brand Book Context */}
      <PresenceBrandContext
        workspace={workspace}
        brandBook={brandBook}
        isLoading={brandBookLoading}
        isError={brandBookError}
      />

      {/* AI Content Drafts */}
      {generatedError && (
        <p role="alert" className="presence-error-alert">
          Não foi possível consultar os rascunhos do Estúdio IA neste workspace.
        </p>
      )}
      <PresenceStudioDrafts
        generatedRequests={generated}
        calendarItems={items}
        canManage={canManage}
        isBusy={isBusy}
        onImport={importGeneratedPost}
      />

      {formError && !detailModalOpen && (
        <div className="presence-error-alert" role="alert">
          ⚠️ {formError}
        </div>
      )}

      {/* Toolbar */}
      <PresenceToolbar
        view={view}
        onViewChange={setView}
        periodLabel={periodLabel}
        onShiftPeriod={shiftPeriod}
        onResetToday={() => setAnchor(new Date())}
        channelFilter={channelFilter}
        onChannelFilterChange={setChannelFilter}
        stageFilter={stageFilter}
        onStageFilterChange={setStageFilter}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        canManage={canManage}
        onOpenNew={() => openDetail(null)}
      />

      <p className="presence-truth">
        ℹ️ Dados salvos no calendário do workspace. Agendar registra uma intenção editorial; a publicação externa
        assistida é realizada via pacote de Handoff manual ou integração.
      </p>

      {items.length === 500 && (
        <p role="status" className="presence-status-banner">
          Exibindo os 500 itens mais recentes.
        </p>
      )}

      {error && (
        <p role="alert" className="presence-error-alert">
          Não foi possível carregar o calendário: {error.message}
        </p>
      )}

      {/* Views */}
      {isLoading ? (
        <div className="presence-loading-state">
          <p>Carregando calendário editorial…</p>
        </div>
      ) : view === "list" ? (
        <PresenceListView
          items={visibleItems}
          onSelect={(item) => openDetail(item)}
          onOpenHandoff={openHandoff}
        />
      ) : (
        <PresenceCalendarGrid
          view={view}
          anchor={anchor}
          days={days}
          itemsByDay={itemsByDay}
          canManage={canManage}
          onSelect={(item) => openDetail(item)}
          onQuickAdd={(date) => openDetail(null, date)}
        />
      )}

      {/* Unscheduled Backlog (for Month/Week views) */}
      {view !== "list" && (
        <PresenceUnscheduled
          items={unscheduledItems}
          onSelect={(item) => openDetail(item)}
        />
      )}

      {/* Detail & Live Mockup Modal */}
      {detailModalOpen && (
        <PresenceDetailModal
          item={selected}
          workspace={workspace}
          draft={draft}
          onDraftChange={setDraft}
          onSave={saveItem}
          onChangeStage={changeStage}
          onOpenHandoff={(item) => {
            setDetailModalOpen(false);
            openHandoff(item);
          }}
          onClose={() => {
            setDetailModalOpen(false);
            setSelected(null);
            setDraft(emptyDraft());
            setFormError("");
          }}
          canManage={canManage}
          canApprove={canApprove}
          isBusy={isBusy}
          errorMessage={formError}
          assignments={assignments}
          people={people}
        />
      )}

      {/* Handoff Export Modal */}
      {handoffModalOpen && handoffItem && (
        <PresenceHandoffModal
          item={handoffItem}
          workspace={workspace}
          onClose={() => {
            setHandoffModalOpen(false);
            setHandoffItem(null);
          }}
        />
      )}
    </div>
  );
}
