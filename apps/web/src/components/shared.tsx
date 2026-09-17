import type { ComponentType, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

type IconLike = LucideIcon | ComponentType<{ size?: number; className?: string }>;

export function ProofItem({ icon: Icon, title, detail }: { icon: LucideIcon; title: string; detail: string }) {
  return (
    <div>
      <Icon size={20} />
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

export function SectionHeader({ eyebrow, title, icon: Icon }: { eyebrow: string; title: string; icon?: IconLike }) {
  return (
    <div className="panel-heading compact">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {Icon && <Icon size={22} />}
    </div>
  );
}

export function DockTitle({ icon: Icon, title }: { icon: LucideIcon; title: string }) {
  return (
    <div className="dock-title">
      <Icon size={16} />
      <strong>{title}</strong>
    </div>
  );
}

export function HubBlock({ title, icon: Icon, children }: { title: string; icon: LucideIcon; children: ReactNode }) {
  return (
    <section className="hub-block">
      <div className="hub-block-title">
        <Icon size={18} />
        <h3>{title}</h3>
      </div>
      <div className="hub-block-list">{children}</div>
    </section>
  );
}

export function HealthRow({ icon: Icon, label, ok, value }: { icon: LucideIcon; label: string; ok: boolean; value: string }) {
  return (
    <div className="health-row">
      <Icon size={18} />
      <span>{label}</span>
      <strong className={ok ? "ok" : "bad"}>{value}</strong>
    </div>
  );
}

export function EmptyState({ text, compact = false }: { text: string; compact?: boolean }) {
  return <div className={compact ? "empty-state compact" : "empty-state"}>{text}</div>;
}

export function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"/>
      <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"/>
      <path fill="#FBBC05" d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332Z"/>
      <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58Z"/>
    </svg>
  );
}
