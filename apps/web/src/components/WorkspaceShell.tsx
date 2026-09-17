import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { NavLink } from "react-router-dom";

export type WorkspaceShellItem = {
  id: string;
  label: string;
  to: string;
  icon: LucideIcon;
  end?: boolean;
};

// A identidade do workspace e a troca de contexto vivem no Topbar
// (WorkspaceNavigator). Esta barra mostra apenas os módulos do contexto atual,
// para não duplicar o nome do workspace nem repetir um "voltar" que o próprio
// navegador do Topbar já resolve.
export function WorkspaceShell({
  title,
  items,
  children,
}: {
  title: string;
  items: WorkspaceShellItem[];
  children: ReactNode;
}) {
  return (
    <section className="workspace-shell">
      <header className="workspace-context-bar">
        <nav className="workspace-context-nav" aria-label={`Módulos de ${title}`}>
          {items.map((item) => {
            const ItemIcon = item.icon;
            return (
              <NavLink key={item.id} to={item.to} end={item.end}>
                <ItemIcon size={15} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </header>

      <div className="workspace-shell-content">{children}</div>
    </section>
  );
}
