import { Eye, EyeOff, Lock, ShieldAlert, LayoutGrid } from "lucide-react";
import { useMySurfaces, useSetSurfacePreference } from "../hooks/useBiomaApi";
import type { SurfaceAccessEntry, SurfaceReason } from "../lib/api";

/** Rótulo curto do motivo. O texto longo já vem pronto do backend em `detail` —
 * aqui é só a etiqueta que se lê de relance. */
const reasonLabel: Record<SurfaceReason, string> = {
  locked: "Sempre disponível",
  platform_admin: "Equipe EG",
  not_contracted: "Não contratado",
  maturity: "Ainda não liberado",
  team_denied: "Escondido pela equipe",
  team_allowed: "Liberado pela equipe",
  user_denied: "Bloqueado para você",
  user_allowed: "Liberado para você",
  preference: "Você ocultou",
  default: "Padrão",
};

function reasonColor(reason: SurfaceReason): string {
  if (reason === "not_contracted" || reason === "user_denied" || reason === "team_denied") return "var(--danger)";
  if (reason === "maturity") return "var(--amber)";
  if (reason === "preference") return "var(--text-muted)";
  return "var(--mint)";
}

function SurfaceRow({ entry }: { entry: SurfaceAccessEntry }) {
  const setPreference = useSetSurfacePreference();
  const busy = setPreference.isPending && setPreference.variables?.surfaceKey === entry.surface_key;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 16,
        padding: "12px 14px",
        background: "var(--bg-elevated)",
        borderRadius: 8,
        border: "1px solid var(--border-light)",
        opacity: entry.allowed ? 1 : 0.72,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <strong style={{ fontSize: 14 }}>{entry.label}</strong>
          <span
            style={{
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 999,
              border: `1px solid ${reasonColor(entry.reason)}`,
              color: reasonColor(entry.reason),
              whiteSpace: "nowrap",
            }}
          >
            {reasonLabel[entry.reason]}
          </span>
          {entry.locked && <Lock size={13} style={{ color: "var(--text-faint)" }} />}
        </div>

        {/* A resposta para "por que não vejo isso?". Vem do mesmo cálculo que
            decidiu — não é um texto paralelo que pode discordar da decisão. */}
        <p style={{ margin: "6px 0 0", fontSize: 12.5, color: "var(--text-muted)", lineHeight: 1.45 }}>
          {entry.detail}
        </p>

        {entry.sources.length > 0 && (
          <p style={{ margin: "4px 0 0", fontSize: 11.5, color: "var(--text-faint)" }}>
            Herança: {entry.sources.join(" → ")}
          </p>
        )}

        {!entry.allowed && (
          <p style={{ margin: "6px 0 0", fontSize: 11.5, color: "var(--text-faint)", display: "flex", alignItems: "center", gap: 6 }}>
            <ShieldAlert size={13} />
            Isto é permissão, não preferência — só um administrador reverte.
          </p>
        )}
      </div>

      <button
        type="button"
        className="mini-button"
        disabled={!entry.can_prefer || busy}
        title={
          entry.locked
            ? "Esta tela não pode ser ocultada"
            : !entry.allowed
              ? "Você não tem acesso a esta tela"
              : entry.visible
                ? "Ocultar do menu"
                : "Mostrar no menu"
        }
        onClick={() =>
          setPreference.mutate({ surfaceKey: entry.surface_key, hidden: entry.visible })
        }
        style={{ flexShrink: 0, display: "flex", alignItems: "center", gap: 6 }}
      >
        {entry.visible ? <Eye size={14} /> : <EyeOff size={14} />}
        {entry.visible ? "Visível" : "Oculto"}
      </button>
    </div>
  );
}

/** Preferência pessoal de navegação (decisão 11, nível 4).
 *
 * Esconder aqui NÃO é bloquear: a rota continua respondendo pela URL. O que
 * está bloqueado por permissão aparece com o motivo e sem botão — porque
 * oferecer um clique que não funciona é pior do que não oferecer nada. */
export function SurfacePreferencesCard() {
  const { data, isLoading, isError } = useMySurfaces();
  const setPreference = useSetSurfacePreference();

  const groups = new Map<string, SurfaceAccessEntry[]>();
  for (const entry of data ?? []) {
    const list = groups.get(entry.group) ?? [];
    list.push(entry);
    groups.set(entry.group, list);
  }

  const hiddenCount = (data ?? []).filter((entry) => entry.allowed && !entry.visible).length;

  return (
    <article className="surface profile-section" style={{ marginTop: 24 }}>
      <div className="surface-header">
        <LayoutGrid size={18} />
        <h3>Telas e módulos</h3>
      </div>

      <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 16px", lineHeight: 1.5 }}>
        O que aparece no seu menu. Ocultar organiza a sua navegação e não apaga
        nada — a tela continua acessível pela URL e religar é um clique.
        {hiddenCount > 0 && ` Você tem ${hiddenCount} tela${hiddenCount > 1 ? "s" : ""} oculta${hiddenCount > 1 ? "s" : ""}.`}
      </p>

      {isLoading && <p style={{ fontSize: 13, color: "var(--text-muted)" }}>Carregando suas telas...</p>}
      {isError && (
        <p style={{ fontSize: 13, color: "var(--danger)" }}>
          Não foi possível carregar suas preferências. O menu segue mostrando tudo que você tem acesso.
        </p>
      )}
      {setPreference.isError && (
        <p style={{ fontSize: 13, color: "var(--danger)", marginBottom: 12 }}>
          {setPreference.error instanceof Error ? setPreference.error.message : "Não foi possível salvar."}
        </p>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {[...groups.entries()].map(([group, entries]) => (
          <div key={group}>
            <div
              style={{
                fontSize: 11,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "var(--text-faint)",
                marginBottom: 8,
              }}
            >
              {group}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {entries.map((entry) => (
                <SurfaceRow key={entry.surface_key} entry={entry} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}
