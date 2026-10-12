import { useState } from "react";
import { PresenceItemCard } from "./PresenceItemCard";
import type { EditorialCalendarItemSummary as Item } from "../../lib/api";

interface PresenceUnscheduledProps {
  items: Item[];
  onSelect: (item: Item) => void;
}

export function PresenceUnscheduled({ items, onSelect }: PresenceUnscheduledProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (items.length === 0) return null;

  return (
    <section className="presence-unscheduled" aria-label="Peças sem data programada">
      <div className="presence-unscheduled-header">
        <div className="presence-unscheduled-title">
          <h2>
            Sem data definida <span className="presence-count-pill">{items.length}</span>
          </h2>
          <p className="presence-unscheduled-desc">
            Peças na esteira que ainda precisam de agendamento de data e horário.
          </p>
        </div>

        <button
          type="button"
          className="presence-toggle-btn"
          onClick={() => setCollapsed(!collapsed)}
          aria-expanded={!collapsed}
        >
          {collapsed ? "Expandir backlog ▾" : "Recolher ▴"}
        </button>
      </div>

      {!collapsed && (
        <div className="presence-unscheduled-grid">
          {items.map((item) => (
            <PresenceItemCard key={item.id} item={item} onSelect={onSelect} />
          ))}
        </div>
      )}
    </section>
  );
}
