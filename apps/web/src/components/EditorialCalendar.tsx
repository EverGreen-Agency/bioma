import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { deliverableStatusLabel } from "../lib/app-config";
import type { DeliverableSummary } from "../lib/api";

const DAY_MS = 24 * 60 * 60 * 1000;
const WEEK_MS = 7 * DAY_MS;

function startOfWeek(reference: Date) {
  const date = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate());
  const weekdayFromMonday = (date.getDay() + 6) % 7;
  return new Date(date.getTime() - weekdayFromMonday * DAY_MS);
}

function dayKey(date: Date) {
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

const weekdayFormat = new Intl.DateTimeFormat("pt-BR", { weekday: "short" });
const rangeFormat = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" });

export function EditorialCalendar({ deliverables }: { deliverables: DeliverableSummary[] }) {
  const [weekOffset, setWeekOffset] = useState(0);

  const weekStart = useMemo(() => new Date(startOfWeek(new Date()).getTime() + weekOffset * WEEK_MS), [weekOffset]);
  const days = useMemo(
    () => Array.from({ length: 7 }, (_, index) => new Date(weekStart.getTime() + index * DAY_MS)),
    [weekStart],
  );

  const byDay = useMemo(() => {
    const groups = new Map<string, DeliverableSummary[]>();
    for (const deliverable of deliverables) {
      if (!deliverable.due_at) continue;
      const key = dayKey(new Date(deliverable.due_at));
      groups.set(key, [...(groups.get(key) ?? []), deliverable]);
    }
    return groups;
  }, [deliverables]);

  const weekItems = days.reduce((total, day) => total + (byDay.get(dayKey(day))?.length ?? 0), 0);
  const withoutDueDate = deliverables.filter((deliverable) => !deliverable.due_at).length;
  const todayKey = dayKey(new Date());

  return (
    <div className="editorial-calendar">
      <div className="calendar-toolbar">
        <strong className="calendar-range">
          {rangeFormat.format(weekStart)} – {rangeFormat.format(days[6])}
        </strong>
        <div className="calendar-nav">
          <button className="icon-button" type="button" onClick={() => setWeekOffset(weekOffset - 1)} aria-label="Semana anterior">
            <ChevronLeft size={16} />
          </button>
          {weekOffset !== 0 && (
            <button className="mini-button" type="button" onClick={() => setWeekOffset(0)}>
              Semana atual
            </button>
          )}
          <button className="icon-button" type="button" onClick={() => setWeekOffset(weekOffset + 1)} aria-label="Próxima semana">
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      <div className="calendar-scroll">
        <div className="calendar-grid">
          {days.map((day) => {
            const key = dayKey(day);
            const items = byDay.get(key) ?? [];
            return (
              <div className={key === todayKey ? "calendar-day today" : "calendar-day"} key={key}>
                <h5>
                  {weekdayFormat.format(day)} {day.getDate()}
                </h5>
                {items.map((deliverable) => (
                  <div className={`calendar-item ${deliverable.status}`} key={deliverable.id}>
                    <span className="item-type">{deliverableStatusLabel[deliverable.status]}</span>
                    <p>{deliverable.title}</p>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>

      {weekItems === 0 && <p className="calendar-note">Nenhuma entrega com prazo nesta semana.</p>}
      {withoutDueDate > 0 && (
        <p className="calendar-note">
          {withoutDueDate} entrega(s) sem prazo definido não aparecem no calendário.
        </p>
      )}
    </div>
  );
}
