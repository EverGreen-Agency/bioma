import { useQuery } from "@tanstack/react-query";
import { AlertOctagon, ArrowRight, CheckCircle2, Info, TriangleAlert } from "lucide-react";

import { api, type DailyBriefItem } from "../lib/api";

/**
 * Resumo diário do cockpit — decisão 3, opção A.
 *
 * **Card ao abrir, sem push por evento.** Notificação por evento vira ruído, e
 * ruído vira gente que ignora o canal inteiro — foi por isso que a opção A
 * ganhou das outras duas.
 *
 * Quando não há nada pendente, ele diz isso em uma linha e para. Um resumo que
 * fala todo dia, mesmo vazio, treina a pessoa a fechar sem ler; aí ele deixa de
 * funcionar justamente no dia em que tem algo.
 *
 * A ordem das linhas vem do servidor e é por **custo de não agir**, não por
 * quantidade: 1 entrega atrasada vem antes de 40 conexões velhas.
 */
export function DailyBriefCard({ onNavigate }: { onNavigate?: (href: string) => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["daily-brief"],
    queryFn: () => api.dailyBrief(),
    // Uma leitura por sessão basta: é um resumo do dia, não um monitor.
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (isLoading || !data) return null;

  if (data.clear) {
    return (
      <p
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 12.5,
          color: "var(--mint)",
          background: "var(--bg-inset)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: "10px 12px",
          margin: "0 0 16px",
        }}
      >
        <CheckCircle2 size={14} aria-hidden /> Nada esperando por você hoje.
      </p>
    );
  }

  return (
    <section
      style={{
        border: "1px solid var(--border)",
        borderRadius: 8,
        background: "var(--bg-inset)",
        padding: 14,
        marginBottom: 16,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <header style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
        <strong style={{ fontSize: 13 }}>Precisa de você hoje</strong>
        <span style={{ fontSize: 10.5, color: "var(--text-faint)" }}>
          {new Date(data.generated_at).toLocaleString("pt-BR")}
        </span>
      </header>

      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
        {data.items.map((item) => (
          <BriefRow key={item.kind} item={item} onNavigate={onNavigate} />
        ))}
      </ul>
    </section>
  );
}

function BriefRow({ item, onNavigate }: { item: DailyBriefItem; onNavigate?: (href: string) => void }) {
  const Icone = item.severity === "critical" ? AlertOctagon : item.severity === "warning" ? TriangleAlert : Info;
  const cor =
    item.severity === "critical"
      ? "var(--danger-soft)"
      : item.severity === "warning"
        ? "var(--amber)"
        : "var(--text-faint)";

  return (
    <li style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
      <Icone size={14} aria-hidden style={{ color: cor, flexShrink: 0, marginTop: 2 }} />
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ fontSize: 12.5 }}>
          {item.title}
          <span style={{ color: "var(--text-faint)", fontWeight: 400 }}> — {item.detail}</span>
        </div>
        {item.examples.length > 0 && (
          <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 2 }}>
            {item.examples.join(" · ")}
            {/* Diz que há mais em vez de listar: o card é um resumo. */}
            {item.count > item.examples.length && ` · e mais ${item.count - item.examples.length}`}
          </div>
        )}
      </div>
      <button
        type="button"
        className="mini-button"
        onClick={() => (onNavigate ? onNavigate(item.href) : (window.location.href = item.href))}
        style={{ flexShrink: 0 }}
      >
        Ver <ArrowRight size={11} aria-hidden />
      </button>
    </li>
  );
}
