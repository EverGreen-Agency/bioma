import { CHANNELS, CHANNEL_LABELS, STAGES, type CalendarView } from "./types";
import type { EditorialCalendarItemSummary as Item } from "../../lib/api";

interface PresenceToolbarProps {
  view: CalendarView;
  onViewChange: (view: CalendarView) => void;
  periodLabel: string;
  onShiftPeriod: (direction: number) => void;
  onResetToday: () => void;
  channelFilter: Item["channel"] | "all";
  onChannelFilterChange: (channel: Item["channel"] | "all") => void;
  stageFilter: Item["stage"] | "all";
  onStageFilterChange: (stage: Item["stage"] | "all") => void;
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  canManage: boolean;
  onOpenNew: () => void;
}

export function PresenceToolbar({
  view,
  onViewChange,
  periodLabel,
  onShiftPeriod,
  onResetToday,
  channelFilter,
  onChannelFilterChange,
  stageFilter,
  onStageFilterChange,
  searchQuery,
  onSearchQueryChange,
  canManage,
  onOpenNew,
}: PresenceToolbarProps) {
  return (
    <div className="presence-toolbar" role="toolbar" aria-label="Controles do calendário editorial">
      <div className="presence-toolbar-nav">
        <div className="presence-nav-buttons">
          <button
            type="button"
            className="presence-btn-icon"
            onClick={() => onShiftPeriod(-1)}
            aria-label="Período anterior"
            title="Período anterior"
          >
            ‹
          </button>
          <button
            type="button"
            className="presence-btn-subtle"
            onClick={onResetToday}
            title="Voltar para a data atual"
          >
            Hoje
          </button>
          <button
            type="button"
            className="presence-btn-icon"
            onClick={() => onShiftPeriod(1)}
            aria-label="Próximo período"
            title="Próximo período"
          >
            ›
          </button>
        </div>
        <strong className="presence-period-label">{periodLabel}</strong>
      </div>

      <div className="presence-toolbar-controls">
        <div className="presence-search-box">
          <input
            type="search"
            placeholder="Buscar peças, tags..."
            value={searchQuery}
            onChange={(e) => onSearchQueryChange(e.target.value)}
            aria-label="Buscar peças editoriais por título ou tag"
            className="presence-search-input"
          />
        </div>

        <div className="presence-filter-group">
          <select
            aria-label="Filtrar por canal"
            value={channelFilter}
            onChange={(e) => onChannelFilterChange(e.target.value as Item["channel"] | "all")}
            className="presence-select-filter"
          >
            <option value="all">Todos os canais</option>
            {CHANNELS.map((channel) => (
              <option key={channel} value={channel}>
                {CHANNEL_LABELS[channel]}
              </option>
            ))}
          </select>

          <select
            aria-label="Filtrar por etapa"
            value={stageFilter}
            onChange={(e) => onStageFilterChange(e.target.value as Item["stage"] | "all")}
            className="presence-select-filter"
          >
            <option value="all">Todas as etapas</option>
            {Object.entries(STAGES).map(([stage, label]) => (
              <option key={stage} value={stage}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div className="presence-view-tabs" role="radiogroup" aria-label="Modo de visualização">
          {(["month", "week", "list"] as CalendarView[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={`presence-view-tab ${view === mode ? "active" : ""}`}
              onClick={() => onViewChange(mode)}
              role="radio"
              aria-checked={view === mode}
            >
              {mode === "month" ? "Mês" : mode === "week" ? "Semana" : "Lista"}
            </button>
          ))}
        </div>

        {canManage && (
          <button
            type="button"
            className="presence-primary-button"
            onClick={onOpenNew}
            title="Criar nova peça no calendário"
          >
            + Nova peça
          </button>
        )}
      </div>
    </div>
  );
}
