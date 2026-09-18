import { useMemo, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { useWorkspaces } from "../../hooks/useBiomaApi";
import { useBrandBook, useCalendarItems, useCreateCalendarItem, useUpdateCalendarItem, useUpdateCalendarStage } from "../../hooks/api/ai";
import { api, type EditorialCalendarItemSummary as Item, type WorkspaceSummary } from "../../lib/api";
import "../../styles/presenca.css";

type CalendarView = "month" | "week" | "list";
type Draft = Pick<Item, "title" | "content_type" | "channel" | "scheduled_at" | "post_text" | "media_urls">;
const CHANNELS: Item["channel"][] = ["instagram", "facebook", "linkedin", "youtube", "tiktok", "blog"];
const STAGES: Record<Item["stage"], string> = {
  ideation: "Ideia", production: "Produção", review: "Revisão", approved: "Aprovado",
  scheduled: "Agendado", published: "Publicado",
};
const NEXT: Partial<Record<Item["stage"], { stage: Item["stage"]; label: string }>> = {
  ideation: { stage: "production", label: "Iniciar produção" },
  production: { stage: "review", label: "Enviar para revisão" },
  review: { stage: "approved", label: "Aprovar" },
  approved: { stage: "scheduled", label: "Confirmar agendamento" },
};

function dayKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function localInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return `${dayKey(d)}T${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function emptyDraft(): Draft {
  return { title: "", content_type: "social_post", channel: "instagram", scheduled_at: null, post_text: "", media_urls: [] };
}

export function PresenceView() {
  const { data: workspaces, isLoading, isError } = useWorkspaces();
  const [params, setParams] = useSearchParams();
  const available = (workspaces ?? []).filter((w) => w.access_role === "platform_admin" || w.enabled_modules.includes("content"));
  const requested = params.get("workspaceId");
  const workspace = available.find((w) => w.id === requested) ?? available[0];

  return (
    <div className="presence-page">
      <header className="presence-heading">
        <div><p className="presence-eyebrow">EVERGREEN · OPERAÇÃO SOCIAL</p><h1>Presença</h1>
          <p>Planeje, produza, revise e aprove conteúdo no workspace do cliente.</p></div>
        <label>Workspace
          <select value={workspace?.id ?? ""} onChange={(event) => setParams({ workspaceId: event.target.value })} disabled={!available.length}>
            {available.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
        </label>
      </header>
      {isLoading ? <p>Carregando workspaces…</p> : isError ? <p role="alert">Não foi possível carregar os workspaces.</p>
        : workspace ? <PresenceCalendar key={workspace.id} workspace={workspace} />
          : <p>Nenhum workspace com o módulo de conteúdo está disponível para sua conta.</p>}
    </div>
  );
}

export function PresenceCalendar({ workspace }: { workspace: WorkspaceSummary }) {
  const { data: brandBook, isError: brandBookError } = useBrandBook(workspace.id);
  const { data: generated = [], isError: generatedError } = useQuery({
    queryKey: ["ai-content", workspace.id],
    queryFn: () => api.aiContentRequests(workspace.id),
  });
  const { data: items = [], isLoading, error } = useCalendarItems(workspace.id);
  const create = useCreateCalendarItem();
  const update = useUpdateCalendarItem();
  const move = useUpdateCalendarStage();
  const [view, setView] = useState<CalendarView>("month");
  const [channelFilter, setChannelFilter] = useState<Item["channel"] | "all">("all");
  const [stageFilter, setStageFilter] = useState<Item["stage"] | "all">("all");
  const [anchor, setAnchor] = useState(() => new Date());
  const [selected, setSelected] = useState<Item | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [formError, setFormError] = useState("");
  const canManage = ["platform_admin", "tenant_admin", "workspace_manager", "operator"].includes(workspace.access_role);
  const canApprove = ["platform_admin", "tenant_admin", "workspace_manager", "approver", "client_user"].includes(workspace.access_role);
  const busy = create.isPending || update.isPending || move.isPending;
  const visibleItems = items.filter((item) =>
    (channelFilter === "all" || item.channel === channelFilter) &&
    (stageFilter === "all" || item.stage === stageFilter));

  const days = useMemo(() => {
    if (view === "list") return [];
    const start = new Date(anchor.getFullYear(), anchor.getMonth(), view === "month" ? 1 : anchor.getDate());
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    const count = view === "month" ? 42 : 7;
    return Array.from({ length: count }, (_, index) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + index));
  }, [anchor, view]);
  const byDay = useMemo(() => {
    const map = new Map<string, Item[]>();
    for (const item of visibleItems) {
      if (!item.scheduled_at) continue;
      const key = dayKey(new Date(item.scheduled_at));
      map.set(key, [...(map.get(key) ?? []), item]);
    }
    return map;
  }, [visibleItems]);
  const unscheduled = visibleItems.filter((item) => !item.scheduled_at);
  const label = view === "week"
    ? `Semana de ${days[0]?.toLocaleDateString("pt-BR", { day: "2-digit", month: "long" })}`
    : anchor.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });

  function open(item: Item | null, date?: Date) {
    setDrawerOpen(true);
    setSelected(item);
    setDraft(item ? {
      title: item.title, content_type: item.content_type, channel: item.channel,
      scheduled_at: item.scheduled_at, post_text: item.post_text, media_urls: item.media_urls,
    } : { ...emptyDraft(), scheduled_at: date ? new Date(date.getFullYear(), date.getMonth(), date.getDate(), 9).toISOString() : null });
    setFormError("");
  }

  function shift(direction: number) {
    setAnchor((current) => view === "month"
      ? new Date(current.getFullYear(), current.getMonth() + direction, 1)
      : new Date(current.getFullYear(), current.getMonth(), current.getDate() + direction * 7));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setFormError("");
    try {
      if (selected) await update.mutateAsync({ workspaceId: workspace.id, itemId: selected.id, payload: draft });
      else await create.mutateAsync({ workspaceId: workspace.id, payload: { ...draft, stage: "ideation" } });
      setSelected(null);
      setDrawerOpen(false);
      setDraft(emptyDraft());
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : "Não foi possível salvar a peça.");
    }
  }

  async function changeStage(item: Item, stage: Item["stage"]) {
    setFormError("");
    try {
      await move.mutateAsync({ workspaceId: workspace.id, itemId: item.id, stage });
      setSelected(null);
      setDrawerOpen(false);
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : "Não foi possível mudar a etapa.");
    }
  }

  async function importGenerated(request: (typeof generated)[number], index: number) {
    const post = request.output?.posts?.[index];
    if (!post) return;
    setFormError("");
    try {
      await create.mutateAsync({ workspaceId: workspace.id, payload: {
        title: post.title,
        content_type: "social_post",
        channel: post.channel,
        stage: "ideation",
        post_text: post.caption,
        metadata: {
          source_type: "ai_content_request",
          ai_content_request_id: request.id,
          output_index: index,
          generation_mode: request.generation_mode,
          provider: request.provider,
          model: request.model,
        },
      } });
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : "Não foi possível importar o rascunho.");
    }
  }

  function exportHandoff(item: Item) {
    const text = [
      `EverGreen Presença · pacote de publicação`,
      `Workspace: ${workspace.name}`,
      `Peça: ${item.title}`,
      `Canal: ${item.channel}`,
      `Etapa: ${STAGES[item.stage]}`,
      `Data planejada: ${item.scheduled_at ? new Date(item.scheduled_at).toLocaleString("pt-BR") : "a definir"}`,
      "", "Texto:", item.post_text ?? "", "", "Mídias:", ...(item.media_urls.length ? item.media_urls : ["Nenhuma mídia vinculada"]),
      "", "Publicação externa não confirmada pelo Bioma.",
    ].join("\n");
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `presenca-${item.id}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function card(item: Item) {
    return <button type="button" key={item.id} className="presence-item" onClick={() => open(item)}>
      <span className={`presence-stage presence-stage-${item.stage}`}>{STAGES[item.stage]}</span>
      <strong>{item.title}</strong>
      <small>{item.channel} {item.scheduled_at ? `· ${new Date(item.scheduled_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}` : ""}</small>
    </button>;
  }

  return <>
    <section className="presence-context">
      <div><strong>Contexto da marca</strong><p>{brandBook
        ? `Brand Book v${brandBook.version} · Tom: ${brandBook.tom_de_voz}${brandBook.posicionamento ? ` · ${brandBook.posicionamento}` : ""}`
        : brandBookError ? "Brand Book indisponível neste workspace." : "Carregando Brand Book…"}</p></div>
      {workspace.client_id && <Link to={`/clientes/${workspace.client_id}/conteudo-ia`}>Abrir Brand Book e geração IA ↗</Link>}
    </section>
    {generatedError && <p role="alert">Não foi possível consultar os rascunhos do Estúdio IA neste workspace.</p>}
    {generated.some((request) => request.status === "ready" && request.output?.posts?.length) && <section className="presence-generated">
      <h2>Rascunhos do Estúdio IA</h2>
      <p>Peças geradas anteriormente neste workspace. Ao importar, a origem e o modo de geração ficam registrados no calendário.</p>
      <div>{generated.filter((request) => request.status === "ready").slice(0, 5).flatMap((request) =>
        (request.output?.posts ?? []).map((post, index) => {
          const imported = items.some((item) => item.metadata.ai_content_request_id === request.id && item.metadata.output_index === index);
          return <article key={`${request.id}-${index}`}>
            <span>{request.generation_mode === "live" ? "Geração ao vivo" : "Prévia ou modo não confirmado"} · {request.provider ?? "provedor não informado"}</span>
            <strong>{post.title}</strong><small>{post.channel} · {post.format}</small>
            <button type="button" disabled={!canManage || busy || imported} onClick={() => importGenerated(request, index)}>{imported ? "Já no calendário" : "Adicionar ao calendário"}</button>
          </article>;
        }))}</div>
    </section>}
    {formError && !drawerOpen && <p role="alert" className="presence-error">{formError}</p>}
    <div className="presence-toolbar">
      <div><button type="button" onClick={() => shift(-1)} aria-label="Período anterior">‹</button>
        <button type="button" onClick={() => setAnchor(new Date())}>Hoje</button>
        <button type="button" onClick={() => shift(1)} aria-label="Próximo período">›</button>
        <strong>{label}</strong></div>
      <div><span>Horários no fuso deste dispositivo</span>
        <select aria-label="Filtrar canal" value={channelFilter} onChange={(e) => setChannelFilter(e.target.value as Item["channel"] | "all")}><option value="all">Todos os canais</option>{CHANNELS.map((channel) => <option key={channel} value={channel}>{channel}</option>)}</select>
        <select aria-label="Filtrar etapa" value={stageFilter} onChange={(e) => setStageFilter(e.target.value as Item["stage"] | "all")}><option value="all">Todas as etapas</option>{Object.entries(STAGES).map(([stage, label]) => <option key={stage} value={stage}>{label}</option>)}</select>
        {(["month", "week", "list"] as CalendarView[]).map((mode) => <button key={mode} type="button" className={view === mode ? "active" : ""} onClick={() => setView(mode)}>{mode === "month" ? "Mês" : mode === "week" ? "Semana" : "Lista"}</button>)}
        {canManage && <button type="button" className="presence-primary" onClick={() => open(null)}>Nova peça</button>}
      </div>
    </div>
    <p className="presence-truth">Dados salvos no calendário do workspace. Agendar registra uma intenção editorial; a publicação em redes sociais ainda depende de integração e confirmação externa.</p>
    {items.length === 500 && <p role="status">Exibindo os 500 itens mais recentes. A busca por períodos maiores ainda precisa de paginação.</p>}
    {error && <p role="alert">Não foi possível carregar o calendário: {error.message}</p>}
    {isLoading ? <p>Carregando calendário…</p> : view === "list"
      ? <div className="presence-list">{visibleItems.length ? [...visibleItems].sort((a, b) => (a.scheduled_at ?? "9999").localeCompare(b.scheduled_at ?? "9999")).map(card) : <p>Nenhuma peça corresponde aos filtros neste workspace.</p>}</div>
      : <div className="presence-calendar">{["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"].map((name) => <div className="presence-weekday" key={name}>{name}</div>)}
        {days.map((day) => <div key={dayKey(day)} className={`presence-day ${day.getMonth() !== anchor.getMonth() && view === "month" ? "outside" : ""}`}>
          <div className="presence-day-head"><span>{day.getDate()}</span>{canManage && <button type="button" onClick={() => open(null, day)} aria-label={`Criar peça em ${day.toLocaleDateString("pt-BR")}`}>+</button>}</div>
          {(byDay.get(dayKey(day)) ?? []).map(card)}
        </div>)}</div>}
    {unscheduled.length > 0 && view !== "list" && <section className="presence-unscheduled"><h2>Sem data definida <span>{unscheduled.length}</span></h2><div>{unscheduled.map(card)}</div></section>}
    {drawerOpen && <div className="presence-drawer-backdrop" onClick={() => { setDrawerOpen(false); setSelected(null); setDraft(emptyDraft()); }}>
      <aside className="presence-drawer" onClick={(event) => event.stopPropagation()} aria-label="Editar peça editorial">
        <div className="presence-drawer-head"><h2>{selected ? "Peça editorial" : "Nova peça"}</h2><button type="button" onClick={() => { setDrawerOpen(false); setSelected(null); setDraft(emptyDraft()); }} aria-label="Fechar">×</button></div>
        {selected && <p><span className={`presence-stage presence-stage-${selected.stage}`}>{STAGES[selected.stage]}</span></p>}
        <form onSubmit={save}>
          <label>Título<input required minLength={2} maxLength={300} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} disabled={!canManage || selected?.stage === "approved" || selected?.stage === "scheduled" || selected?.stage === "published"} /></label>
          <div className="presence-form-row"><label>Canal<select value={draft.channel} onChange={(e) => setDraft({ ...draft, channel: e.target.value as Item["channel"] })} disabled={!canManage || selected?.stage === "approved" || selected?.stage === "scheduled" || selected?.stage === "published"}>{CHANNELS.map((channel) => <option key={channel}>{channel}</option>)}</select></label>
            <label>Formato<select value={draft.content_type} onChange={(e) => setDraft({ ...draft, content_type: e.target.value as Item["content_type"] })} disabled={!canManage || selected?.stage === "approved" || selected?.stage === "scheduled" || selected?.stage === "published"}><option value="social_post">Post social</option><option value="image_ad">Imagem</option><option value="video_script">Roteiro de vídeo</option><option value="article">Artigo</option></select></label></div>
          <label>Data e hora planejadas<input type="datetime-local" value={localInput(draft.scheduled_at)} onChange={(e) => setDraft({ ...draft, scheduled_at: e.target.value ? new Date(e.target.value).toISOString() : null })} disabled={!canManage || selected?.stage === "approved" || selected?.stage === "scheduled" || selected?.stage === "published"} /></label>
          <label>Texto da peça<textarea rows={8} maxLength={5000} value={draft.post_text ?? ""} onChange={(e) => setDraft({ ...draft, post_text: e.target.value })} disabled={!canManage || selected?.stage === "approved" || selected?.stage === "scheduled" || selected?.stage === "published"} /></label>
          {canManage && (!selected || ["ideation", "production", "review"].includes(selected.stage)) && <button className="presence-primary" type="submit" disabled={busy}>Salvar peça</button>}
        </form>
        {selected && <div className="presence-actions">
          {["approved", "scheduled", "published"].includes(selected.stage) && <button type="button" onClick={() => exportHandoff(selected)}>Baixar pacote de publicação</button>}
          {NEXT[selected.stage] && (NEXT[selected.stage]?.stage === "approved" ? canApprove : canManage) && <button type="button" disabled={busy} onClick={() => changeStage(selected, NEXT[selected.stage]!.stage)}>{NEXT[selected.stage]?.label}</button>}
          {selected.stage === "review" && canManage && <button type="button" disabled={busy} onClick={() => changeStage(selected, "production")}>Devolver à produção</button>}
          {selected.stage === "approved" && canManage && <button type="button" disabled={busy} onClick={() => changeStage(selected, "review")}>Reabrir revisão</button>}
          {selected.stage === "scheduled" && canManage && <button type="button" disabled={busy} onClick={() => changeStage(selected, "approved")}>Cancelar agendamento</button>}
        </div>}
        {formError && <p role="alert" className="presence-error">{formError}</p>}
      </aside>
    </div>}
  </>;
}
