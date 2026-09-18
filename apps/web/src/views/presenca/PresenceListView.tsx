import { useMemo, useState } from "react";
import { CHANNEL_LABELS, STAGES, type Assignee, type ListSortOption } from "./types";
import type { EditorialCalendarItemSummary as Item } from "../../lib/api";

interface PresenceListViewProps {
  items: Item[];
  onSelect: (item: Item) => void;
  onOpenHandoff: (item: Item) => void;
}

export function PresenceListView({ items, onSelect, onOpenHandoff }: PresenceListViewProps) {
  const [pageSize, setPageSize] = useState<number>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [sortOption, setSortOption] = useState<ListSortOption>("scheduled_asc");

  const sortedItems = useMemo(() => {
    const list = [...items];
    switch (sortOption) {
      case "scheduled_asc":
        return list.sort((a, b) => {
          if (!a.scheduled_at) return 1;
          if (!b.scheduled_at) return -1;
          return a.scheduled_at.localeCompare(b.scheduled_at);
        });
      case "scheduled_desc":
        return list.sort((a, b) => {
          if (!a.scheduled_at) return 1;
          if (!b.scheduled_at) return -1;
          return b.scheduled_at.localeCompare(a.scheduled_at);
        });
      case "created_desc":
        return list.sort((a, b) => b.created_at.localeCompare(a.created_at));
      case "title_asc":
        return list.sort((a, b) => a.title.localeCompare(b.title));
      default:
        return list;
    }
  }, [items, sortOption]);

  const totalPages = Math.max(1, Math.ceil(sortedItems.length / pageSize));
  const pageIndex = Math.min(currentPage, totalPages);
  const paginatedItems = useMemo(() => {
    const start = (pageIndex - 1) * pageSize;
    return sortedItems.slice(start, start + pageSize);
  }, [sortedItems, pageIndex, pageSize]);

  function handlePageChange(newPage: number) {
    setCurrentPage(Math.max(1, Math.min(newPage, totalPages)));
  }

  if (items.length === 0) {
    return (
      <div className="presence-empty-state">
        <p>Nenhuma peça corresponde aos filtros aplicados neste workspace.</p>
      </div>
    );
  }

  return (
    <div className="presence-list-container">
      <div className="presence-list-header-bar">
        <div className="presence-list-meta">
          <span>
            Mostrando <strong>{paginatedItems.length}</strong> de <strong>{items.length}</strong> peças
          </span>
        </div>

        <div className="presence-list-controls">
          <label className="presence-sort-label">
            <span>Ordenar por:</span>
            <select
              value={sortOption}
              onChange={(e) => {
                setSortOption(e.target.value as ListSortOption);
                setCurrentPage(1);
              }}
              className="presence-sort-select"
            >
              <option value="scheduled_asc">Data programada (Próximas primeiro)</option>
              <option value="scheduled_desc">Data programada (Mais distantes)</option>
              <option value="created_desc">Mais recentes (Criação)</option>
              <option value="title_asc">Título (A-Z)</option>
            </select>
          </label>

          <label className="presence-pagesize-label">
            <span>Itens por página:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="presence-pagesize-select"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </label>
        </div>
      </div>

      <div className="presence-list-items">
        {paginatedItems.map((item) => {
          const assignee = item.metadata?.assigned_to as Assignee | null | undefined;
          const campaignTags = Array.isArray(item.metadata?.campaign_tags)
            ? (item.metadata.campaign_tags as string[])
            : [];
          const scheduledDate = item.scheduled_at ? new Date(item.scheduled_at) : null;
          const isHandoffReady = ["approved", "scheduled", "published"].includes(item.stage);

          return (
            <article key={item.id} className="presence-list-row">
              <div className="presence-row-main" onClick={() => onSelect(item)}>
                <div className="presence-row-status-col">
                  <span className={`presence-stage-badge presence-stage-${item.stage}`}>
                    {STAGES[item.stage]}
                  </span>
                  <span className="presence-channel-pill">{CHANNEL_LABELS[item.channel]}</span>
                </div>

                <div className="presence-row-content">
                  <strong className="presence-row-title">{item.title}</strong>
                  {item.post_text && (
                    <p className="presence-row-snippet">
                      {item.post_text.slice(0, 120)}
                      {item.post_text.length > 120 ? "…" : ""}
                    </p>
                  )}

                  {campaignTags.length > 0 && (
                    <div className="presence-row-tags">
                      {campaignTags.map((tag) => (
                        <span key={tag} className="presence-tag-chip">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="presence-row-scheduling">
                  <span className="presence-row-date">
                    {scheduledDate
                      ? scheduledDate.toLocaleDateString("pt-BR", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        })
                      : "Sem data definida"}
                  </span>
                  {scheduledDate && (
                    <span className="presence-row-time">
                      ⏰ {scheduledDate.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  )}
                </div>

                <div className="presence-row-assignee">
                  {assignee ? (
                    <div className="presence-assignee-badge" title={assignee.email ?? assignee.name}>
                      <span className="presence-assignee-avatar">
                        {assignee.name
                          .split(" ")
                          .slice(0, 2)
                          .map((p) => p[0]?.toUpperCase() ?? "")
                          .join("")}
                      </span>
                      <span className="presence-assignee-name">{assignee.name}</span>
                    </div>
                  ) : (
                    <span className="presence-unassigned-text">Sem responsável</span>
                  )}
                </div>
              </div>

              <div className="presence-row-actions">
                {isHandoffReady && (
                  <button
                    type="button"
                    className="presence-btn-handoff"
                    onClick={() => onOpenHandoff(item)}
                    title="Exportar pacote de publicação manual"
                  >
                    📦 Handoff
                  </button>
                )}
                <button
                  type="button"
                  className="presence-btn-edit"
                  onClick={() => onSelect(item)}
                  title="Editar ou ver detalhes da peça"
                >
                  Abrir
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {totalPages > 1 && (
        <div className="presence-pagination-bar" role="navigation" aria-label="Paginação da lista">
          <button
            type="button"
            className="presence-page-btn"
            disabled={pageIndex <= 1}
            onClick={() => handlePageChange(pageIndex - 1)}
          >
            ‹ Anterior
          </button>

          <span className="presence-page-info">
            Página <strong>{pageIndex}</strong> de <strong>{totalPages}</strong>
          </span>

          <button
            type="button"
            className="presence-page-btn"
            disabled={pageIndex >= totalPages}
            onClick={() => handlePageChange(pageIndex + 1)}
          >
            Próxima ›
          </button>
        </div>
      )}
    </div>
  );
}
