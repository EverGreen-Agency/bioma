import { Rocket, RotateCcw } from "lucide-react";

import { useClearFeatureFlag, useFeatureFlags, useUpsertFeatureFlag } from "../hooks/useBiomaApi";
import type { FeatureState } from "../lib/api";

const STATE_LABEL: Record<FeatureState, string> = {
  hidden: "Oculto",
  coming_soon: "Em breve",
  beta: "Beta",
  active: "Ativo",
};

const STATE_COLOR: Record<FeatureState, string> = {
  hidden: "var(--text-faint)",
  coming_soon: "#ffab00",
  beta: "#4f8ef7",
  active: "#2e9e5b",
};

/**
 * Liberação de features por cliente. Eixo diferente de `enabled_modules`:
 * módulo responde "contratou?", flag responde "já está pronto para este
 * cliente?". `Em breve` aparece na interface do cliente sem dar acesso.
 */
export function FeatureFlagsPanel({ organizationId }: { organizationId: string }) {
  const { data: flags = [], isLoading } = useFeatureFlags(organizationId);
  const upsert = useUpsertFeatureFlag();
  const clear = useClearFeatureFlag();

  return (
    <article className="surface">
      <div className="surface-header">
        <Rocket size={18} />
        <h3>Liberação de features</h3>
      </div>
      <div style={{ padding: "0 20px 20px" }}>
        <p style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 14 }}>
          Controla o que este cliente já enxerga. <strong>Em breve</strong> aparece na interface
          dele sem liberar acesso — serve de vitrine. Sem exceção definida, vale o padrão do
          catálogo.
        </p>

        {isLoading && <p style={{ color: "var(--text-muted)" }}>Carregando...</p>}

        <div className="table-list">
          {flags.map((flag) => (
            <div className="table-row" key={flag.feature_key}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <strong>{flag.label}</strong>
                <small style={{ display: "block", color: "var(--text-muted)" }}>{flag.description}</small>
                {!flag.is_override && (
                  <small style={{ color: "var(--text-faint)" }}>padrão do catálogo</small>
                )}
              </div>
              <select
                value={flag.state}
                disabled={upsert.isPending}
                onChange={(e) =>
                  upsert.mutate({ organizationId, featureKey: flag.feature_key, state: e.target.value as FeatureState })
                }
                style={{ fontSize: 12, color: STATE_COLOR[flag.state], fontWeight: 600 }}
              >
                {(Object.keys(STATE_LABEL) as FeatureState[]).map((state) => (
                  <option key={state} value={state}>{STATE_LABEL[state]}</option>
                ))}
              </select>
              {flag.is_override && (
                <button
                  type="button"
                  className="icon-button"
                  title="Voltar ao padrão do catálogo"
                  disabled={clear.isPending}
                  onClick={() => clear.mutate({ organizationId, featureKey: flag.feature_key })}
                >
                  <RotateCcw size={13} />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}
