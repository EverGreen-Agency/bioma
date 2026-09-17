import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Crown, Loader2, Pin, Plus, RefreshCw, Sparkles, Trash2 } from "lucide-react";

import { api, type Win, type WinCategory } from "../../lib/api";

/**
 * Mural de vitórias.
 *
 * Por que existe: o Bioma sabe de tudo que está atrasado, bloqueado e em risco —
 * e de nada que deu certo. Operação que só enxerga problema desgasta quem
 * trabalha nela.
 *
 * Duas origens, e a tela mostra a diferença: `manual` é alguém que digitou
 * ("conta aprovada na plataforma X" não está em tabela nenhuma), `automatic` é
 * um detector que viu no banco — e nesse caso a evidência fica visível, porque
 * vitória automática sem origem é indistinguível de vitória inventada.
 */

const CATEGORY_LABELS: Record<WinCategory, string> = {
  comercial: "Comercial",
  operacao: "Operação",
  produto: "Produto",
  cliente: "Cliente",
  time: "Time",
  financeiro: "Financeiro",
};

const REACTIONS = ["🎉", "🔥", "👏", "🚀"];

function relativeDay(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "hoje";
  if (days === 1) return "ontem";
  if (days < 30) return `há ${days} dias`;
  return new Date(iso).toLocaleDateString("pt-BR");
}

function WinCard({ win }: { win: Win }) {
  const queryClient = useQueryClient();
  const [showEvidence, setShowEvidence] = useState(false);
  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ["wins"] });
    await queryClient.invalidateQueries({ queryKey: ["wins-overview"] });
  };

  const react = useMutation({ mutationFn: (emoji: string) => api.reactToWin(win.id, emoji), onSuccess: invalidate });
  const update = useMutation({
    mutationFn: (payload: Parameters<typeof api.updateWin>[1]) => api.updateWin(win.id, payload),
    onSuccess: invalidate,
  });
  const remove = useMutation({ mutationFn: () => api.deleteWin(win.id), onSuccess: invalidate });

  return (
    <article className={`surface win-card ${win.pinned ? "pinned" : ""}`}>
      <div className="win-card-head">
        <div>
          <div className="win-card-tags">
            <span className="win-badge">{CATEGORY_LABELS[win.category]}</span>
            {win.is_ceo && <span className="win-badge ceo"><Crown size={10} /> CEO</span>}
            {win.source === "automatic" && <span className="win-badge auto">detectada</span>}
            {win.visibility === "client" && <span className="win-badge">visível ao cliente</span>}
          </div>
          <h3>{win.title}</h3>
          {win.description && <p>{win.description}</p>}
        </div>
        {win.metric_value && (
          <div className="win-metric">
            <strong>{Number(win.metric_value).toLocaleString("pt-BR")}</strong>
            <span>{win.metric_unit}</span>
          </div>
        )}
      </div>

      <div className="win-card-foot">
        <div className="win-reactions">
          {REACTIONS.map((emoji) => {
            const people = win.reactions[emoji] ?? [];
            return (
              <button
                key={emoji}
                type="button"
                className={people.length ? "active" : ""}
                onClick={() => react.mutate(emoji)}
              >
                {emoji}{people.length > 0 && <small>{people.length}</small>}
              </button>
            );
          })}
        </div>

        <div className="win-card-actions">
          <span>{relativeDay(win.occurred_at)}</span>
          {win.source === "automatic" && (
            <button type="button" onClick={() => setShowEvidence((value) => !value)}>
              {showEvidence ? "ocultar origem" : "de onde veio"}
            </button>
          )}
          <button
            type="button"
            title={win.pinned ? "Desafixar" : "Fixar no topo"}
            className={win.pinned ? "active" : ""}
            onClick={() => update.mutate({ pinned: !win.pinned })}
          >
            <Pin size={13} />
          </button>
          <button
            type="button"
            title={win.visibility === "client" ? "Esconder do cliente" : "Mostrar ao cliente"}
            onClick={() => update.mutate({ visibility: win.visibility === "client" ? "eg" : "client" })}
            disabled={!win.workspace_id}
          >
            {win.visibility === "client" ? "🙈" : "👁"}
          </button>
          <button type="button" title="Remover" onClick={() => remove.mutate()}>
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {showEvidence && (
        <pre className="win-evidence">{JSON.stringify(win.evidence, null, 2)}</pre>
      )}
    </article>
  );
}

export function WinsView() {
  const queryClient = useQueryClient();
  const [category, setCategory] = useState<string>("");
  const [ceoOnly, setCeoOnly] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState({
    title: "", description: "", category: "comercial" as WinCategory,
    metric_value: "", metric_unit: "", is_ceo: false,
  });

  const overview = useQuery({ queryKey: ["wins-overview"], queryFn: () => api.winsOverview(30) });
  const wins = useQuery({
    queryKey: ["wins", category, ceoOnly],
    queryFn: () => api.wins({ category: category || undefined, ceo_only: ceoOnly }),
  });

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ["wins"] });
    await queryClient.invalidateQueries({ queryKey: ["wins-overview"] });
  };

  const create = useMutation({
    mutationFn: () =>
      api.createWin({
        title: draft.title.trim(),
        description: draft.description.trim() || null,
        category: draft.category,
        metric_value: draft.metric_value.trim() || null,
        metric_unit: draft.metric_unit.trim() || null,
        is_ceo: draft.is_ceo,
      }),
    onSuccess: async () => {
      setDraft({ title: "", description: "", category: "comercial", metric_value: "", metric_unit: "", is_ceo: false });
      setShowForm(false);
      await invalidate();
    },
  });

  const detect = useMutation({ mutationFn: () => api.detectWins(), onSuccess: invalidate });

  return (
    <div style={{ padding: 24, maxWidth: 980, margin: "0 auto", color: "var(--text)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 18 }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, margin: 0 }}>Mural de vitórias</h1>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: "0.9rem", maxWidth: 620 }}>
            O Bioma sabe de tudo que está atrasado. Aqui fica o que deu certo — registrado à mão,
            ou detectado no banco com a evidência de onde veio.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="mini-button" type="button" disabled={detect.isPending} onClick={() => detect.mutate()}>
            {detect.isPending ? <Loader2 size={13} className="spin" /> : <RefreshCw size={13} />} Detectar
          </button>
          <button className="primary-button" type="button" onClick={() => setShowForm((value) => !value)}>
            <Plus size={15} /> Registrar
          </button>
        </div>
      </div>

      {detect.data && (
        <div className="notice" style={{ marginBottom: 14 }}>
          {detect.data.created > 0
            ? `${detect.data.created} vitória(s) nova(s) detectada(s).`
            : "Nada novo desde a última varredura."}
          {detect.data.skipped_duplicates > 0 && ` ${detect.data.skipped_duplicates} já estavam no mural.`}
          {Object.keys(detect.data.errors).length > 0 && (
            <div style={{ color: "#ff8a80", marginTop: 6, fontSize: 12 }}>
              Detector com erro: {Object.entries(detect.data.errors).map(([key, message]) => `${key} (${message})`).join("; ")}
            </div>
          )}
        </div>
      )}

      {showForm && (
        <form
          className="surface"
          style={{ padding: 14, marginBottom: 16, display: "grid", gap: 8 }}
          onSubmit={(event) => { event.preventDefault(); if (draft.title.trim().length >= 2) create.mutate(); }}
        >
          <input
            required minLength={2} value={draft.title} placeholder="O que aconteceu de bom?"
            onChange={(event) => setDraft({ ...draft, title: event.target.value })}
            style={{ padding: 9, borderRadius: 7, border: "1px solid var(--border)", background: "var(--bg-inset)", color: "var(--text)" }}
          />
          <textarea
            rows={2} value={draft.description} placeholder="Contexto (opcional)"
            onChange={(event) => setDraft({ ...draft, description: event.target.value })}
            style={{ padding: 9, borderRadius: 7, border: "1px solid var(--border)", background: "var(--bg-inset)", color: "var(--text)", fontFamily: "inherit" }}
          />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <select
              value={draft.category}
              onChange={(event) => setDraft({ ...draft, category: event.target.value as WinCategory })}
              style={{ padding: 8, borderRadius: 7, border: "1px solid var(--border)", background: "var(--bg-inset)", color: "var(--text)" }}
            >
              {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <input
              value={draft.metric_value} placeholder="Número (opcional)" inputMode="decimal"
              onChange={(event) => setDraft({ ...draft, metric_value: event.target.value })}
              style={{ width: 130, padding: 8, borderRadius: 7, border: "1px solid var(--border)", background: "var(--bg-inset)", color: "var(--text)" }}
            />
            <input
              value={draft.metric_unit} placeholder="Unidade"
              onChange={(event) => setDraft({ ...draft, metric_unit: event.target.value })}
              style={{ width: 110, padding: 8, borderRadius: 7, border: "1px solid var(--border)", background: "var(--bg-inset)", color: "var(--text)" }}
            />
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-dim)" }}>
              <input
                type="checkbox" checked={draft.is_ceo}
                onChange={(event) => setDraft({ ...draft, is_ceo: event.target.checked })}
              />
              Vitória do CEO (vai para o Fóton)
            </label>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="primary-button" type="submit" disabled={create.isPending}>
              {create.isPending ? "Salvando…" : "Registrar"}
            </button>
            <span style={{ fontSize: 11, color: "var(--text-faint)" }}>
              Número é opcional — nem toda vitória se mede, e forçar um produziria número falso.
            </span>
          </div>
          {create.error && <span style={{ color: "#ff5252", fontSize: 12 }}>{create.error.message}</span>}
        </form>
      )}

      {overview.data && (
        <div className="platform-overview" style={{ marginBottom: 16 }}>
          <div className="surface"><strong>{overview.data.total}</strong><span>nos últimos 30 dias</span></div>
          <div className="surface"><strong>{overview.data.last_7_days}</strong><span>nos últimos 7 dias</span></div>
          <div className="surface"><strong>{overview.data.automatic}</strong><span>detectadas</span></div>
          <div className="surface"><strong>{overview.data.manual}</strong><span>registradas à mão</span></div>
          <div className="surface"><strong>{overview.data.ceo}</strong><span>do CEO</span></div>
        </div>
      )}

      <div style={{ display: "flex", gap: 6, marginBottom: 14, flexWrap: "wrap" }}>
        <button className={`mini-button ${!category && !ceoOnly ? "selected" : ""}`} type="button" onClick={() => { setCategory(""); setCeoOnly(false); }}>
          Todas
        </button>
        {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
          <button key={value} className={`mini-button ${category === value ? "selected" : ""}`} type="button" onClick={() => { setCategory(value); setCeoOnly(false); }}>
            {label}
          </button>
        ))}
        <button className={`mini-button ${ceoOnly ? "selected" : ""}`} type="button" onClick={() => { setCeoOnly(true); setCategory(""); }}>
          <Crown size={12} /> Do CEO
        </button>
      </div>

      {wins.isLoading && <p style={{ color: "var(--text-dim)" }}>Carregando…</p>}
      {wins.error && <div className="notice error">{wins.error.message}</div>}

      <div style={{ display: "grid", gap: 10 }}>
        {wins.data?.map((win) => <WinCard key={win.id} win={win} />)}
        {wins.data?.length === 0 && (
          <div className="surface" style={{ padding: 32, textAlign: "center", color: "var(--text-dim)" }}>
            <Sparkles size={22} style={{ opacity: 0.5 }} />
            <p style={{ margin: "8px 0 0" }}>
              Nenhuma vitória ainda. Use <strong>Detectar</strong> para varrer o que já aconteceu,
              ou registre a primeira à mão.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default WinsView;
