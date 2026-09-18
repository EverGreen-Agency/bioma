import { dayKey, type CalendarView } from "./types";
import { PresenceItemCard } from "./PresenceItemCard";
import type { EditorialCalendarItemSummary as Item } from "../../lib/api";

interface PresenceCalendarGridProps {
  view: CalendarView;
  anchor: Date;
  days: Date[];
  itemsByDay: Map<string, Item[]>;
  canManage: boolean;
  onSelect: (item: Item) => void;
  onQuickAdd: (date: Date) => void;
}

const WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

export function PresenceCalendarGrid({
  view,
  anchor,
  days,
  itemsByDay,
  canManage,
  onSelect,
  onQuickAdd,
}: PresenceCalendarGridProps) {
  const todayKey = dayKey(new Date());

  return (
    <div className={`presence-calendar-wrapper view-${view}`}>
      <div className="presence-calendar-grid">
        {WEEKDAYS.map((name) => (
          <div className="presence-weekday-header" key={name}>
            {name}
          </div>
        ))}

        {days.map((day) => {
          const key = dayKey(day);
          const isToday = key === todayKey;
          const isOutside = view === "month" && day.getMonth() !== anchor.getMonth();
          const dayItems = itemsByDay.get(key) ?? [];

          return (
            <div
              key={key}
              className={`presence-day-cell ${isOutside ? "outside-month" : ""} ${isToday ? "today" : ""}`}
            >
              <div className="presence-day-header">
                <span className={`presence-day-number ${isToday ? "today-badge" : ""}`}>
                  {day.getDate()}
                </span>

                {canManage && (
                  <button
                    type="button"
                    className="presence-quick-add-btn"
                    onClick={() => onQuickAdd(day)}
                    aria-label={`Criar nova peça em ${day.toLocaleDateString("pt-BR")}`}
                    title="Adicionar peça neste dia"
                  >
                    +
                  </button>
                )}
              </div>

              <div className="presence-day-items">
                {dayItems.map((item) => (
                  <PresenceItemCard
                    key={item.id}
                    item={item}
                    onSelect={onSelect}
                    compact={view === "month"}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
