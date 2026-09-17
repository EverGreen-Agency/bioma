import type { ReactNode } from "react";

export type StatusPillVariant = "connected" | "not_configured" | "error" | "paused";

const VARIANT_CLASS: Record<StatusPillVariant, string> = {
  connected: "status-pill open",
  not_configured: "status-pill danger",
  error: "status-pill danger",
  paused: "status-pill paused",
};

export function StatusPill({ variant, children }: { variant: StatusPillVariant; children: ReactNode }) {
  return <span className={VARIANT_CLASS[variant]}>{children}</span>;
}
