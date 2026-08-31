import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  Calendar,
  Check,
  CheckCircle2,
  Copy,
  Film,
  Image as ImageIcon,
  Lightbulb,
  LoaderCircle,
  MessageSquareText,
  Plus,
  Send,
  Sparkles,
  Globe,
  WandSparkles,
  TrendingUp,
} from "lucide-react";

import {
  api,
  type AiContentPost,
  type AiContentImage,
  type AiContentVideoScript,
  type ContentScriptSummary,
} from "../lib/api";
import { StudioArtifactList } from "./StudioArtifactList";
import { CmsPostsManager } from "./CmsPostsManager";
import {
  useBrandBook,
  useSaveBrandBook,
  useCalendarItems,
  useContentHookBank,
  useContentScripts,
  useCreateCalendarItem,
  useLinkPostToScript,
  useScriptScoreboard,
  useGenerateContentScripts,
  useGenerateRetrospective,
  useInstagramPosts,
  useLatestRetrospective,
  useUpdateCalendarStage,
  useUpdateContentScript,
} from "../hooks/useBiomaApi";
import { EmptyState, SectionHeader } from "./shared";
import { StatusPill } from "./StatusPill";

type MainTab = "artifacts" | "blog" | "studio" | "brand_book" | "calendar" | "retrospective";
type ContentType = "social_posts" | "image_generation" | "video_scripts";
type ImageProvider = "dalle_3" | "flux" | "higgsfield" | "custom";

const channelOptions: Array<{ value: AiContentPost["channel"]; label: string }> = [
  { value: "instagram", label: "Instagram" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "facebook", label: "Facebook" },
  { value: "tiktok", label: "TikTok" },
  { value: "youtube", label: "YouTube" },
];

function BrandBookSection({ workspaceId }: { workspaceId: string }) {
  const { data: book, isLoading } = useBrandBook(workspaceId);
  const saveMutation = useSaveBrandBook();

  const [tom, setTom] = useState("");
  const [arquetipo, setArquetipo] = useState("");
  const [posicionamento, setPosicionamento] = useState("");
  const [proposta, setProposta] = useState("");
  const [regras, setRegras] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  function handleSave(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate(
      {
        workspaceId,
        payload: {
          tom_de_voz: tom || book?.tom_de_voz || "Profissional",
          arquetipo: arquetipo || book?.arquetipo || "O Governante",
          posicionamento: posicionamento || undefined,
          proposta_valor: proposta || undefined,
          regras_copy: regras.split("\n").map((r) => r.trim()).filter(Boolean),
        },
      },
      {
        onSuccess: (res) => setFeedback(`Brand Book v${res.version} salvo com sucesso!`),
      }
    );
  }

  if (isLoading) return <EmptyState compact text="Carregando Brand Book do workspace..." />;

  return (
    <article className="surface" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <SectionHeader
        eyebrow="Manual de Marca EG"
        title={`Brand Book Versionado (Versão Atual: v${book?.version ?? 1})`}
        icon={BookOpen}
      />

      {feedback && <div className="notice success">{feedback}</div>}

      <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "12px", marginBottom: "4px" }}>Tom de Voz da Marca</label>
            <input
              type="text"
              defaultValue={book?.tom_de_voz ?? ""}
              onChange={(e) => setTom(e.target.value)}
              placeholder="Ex: Autoridade, Direto e Humano"
              style={{ width: "100%", padding: "8px 12px", borderRadius: "4px", border: "1px solid var(--border-light)" }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "12px", marginBottom: "4px" }}>Arquétipo de Marca</label>
            <input
              type="text"
              defaultValue={book?.arquetipo ?? ""}
              onChange={(e) => setArquetipo(e.target.value)}
              placeholder="Ex: O Governante / O Especialista"
              style={{ width: "100%", padding: "8px 12px", borderRadius: "4px", border: "1px solid var(--border-light)" }}
            />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label style={{ display: "block", fontSize: "12px", marginBottom: "4px" }}>Posicionamento Estratégico</label>
            <textarea
              defaultValue={book?.posicionamento ?? ""}
              onChange={(e) => setPosicionamento(e.target.value)}
              rows={2}
              placeholder="Definição do posicionamento único da marca no mercado"
              style={{ width: "100%", padding: "8px 12px", borderRadius: "4px", border: "1px solid var(--border-light)" }}
            />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label style={{ display: "block", fontSize: "12px", marginBottom: "4px" }}>Proposta Única de Valor</label>
            <textarea
              defaultValue={book?.proposta_valor ?? ""}
              onChange={(e) => setProposta(e.target.value)}
              rows={2}
              placeholder="O que a marca promete entregar que ninguém mais entrega?"
              style={{ width: "100%", padding: "8px 12px", borderRadius: "4px", border: "1px solid var(--border-light)" }}
            />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label style={{ display: "block", fontSize: "12px", marginBottom: "4px" }}>Regras de Copywriting (1 por linha)</label>
            <textarea
              defaultValue={book?.regras_copy.join("\n") ?? ""}
              onChange={(e) => setRegras(e.target.value)}
              rows={3}
              placeholder="Sempre citar dados concretos&#10;Nunca usar jargões corporativos vazios"
              style={{ width: "100%", padding: "8px 12px", borderRadius: "4px", border: "1px solid var(--border-light)" }}
            />
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button className="primary-button" type="submit" disabled={saveMutation.isPending}>
            <Sparkles size={15} />
            {saveMutation.isPending ? "Salvando..." : "Salvar Nova Versão do Brand Book"}
          </button>
        </div>
      </form>
    </article>
  );
}

function RetrospectiveSection({ workspaceId }: { workspaceId: string }) {
  const { data: posts, isLoading: loadingPosts } = useInstagramPosts(workspaceId);
  const { data: hookBank } = useContentHookBank(workspaceId);
  const { data: retrospective, isLoading: loadingRetro } = useLatestRetrospective(workspaceId);
  const { data: scripts } = useContentScripts(workspaceId);
  const generateRetrospective = useGenerateRetrospective();
  const generateScripts = useGenerateContentScripts();
  const updateScript = useUpdateContentScript();
  const createCalendarItem = useCreateCalendarItem();
  const linkPostToScript = useLinkPostToScript();
  const { data: scoreboard } = useScriptScoreboard(workspaceId);

  const [scriptCount, setScriptCount] = useState(12);
  const [competitorInput, setCompetitorInput] = useState("");
  const [sentToCalendar, setSentToCalendar] = useState<Record<string, boolean>>({});

  const hasPosts = (posts?.length ?? 0) > 0;
  const output = retrospective?.output_data;

  function handleSendToCalendar(script: ContentScriptSummary) {
    createCalendarItem.mutate(
      {
        workspaceId,
        payload: {
          title: script.title,
          content_type: "video_script",
          channel: "instagram",
          post_text: script.script_body,
          scheduled_at: script.scheduled_for,
          stage: "ideation",
        },
      },
      {
        onSuccess: () => {
          setSentToCalendar((prev) => ({ ...prev, [script.id]: true }));
          updateScript.mutate({ workspaceId, scriptId: script.id, payload: { status: "approved" } });
        },
      },
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <article className="surface">
        <SectionHeader
          eyebrow="Retrospectiva de Conteúdo"
          title="O que já funcionou (sem precisar de briefing)"
          icon={Lightbulb}
        />
        <p style={{ color: "var(--text-muted)", fontSize: 13, margin: "8px 0 16px" }}>
          Analisa os posts orgânicos já sincronizados do Instagram (legenda, transcrição e métricas reais) e
          identifica temas, formatos e ganchos que performaram — sem exigir que você sugira um tema.
        </p>
        {!hasPosts && !loadingPosts && (
          <div className="notice" style={{ marginBottom: 12 }}>
            Nenhum post orgânico sincronizado ainda. Conecte o Instagram em Integrações e rode uma sincronização
            antes de gerar a retrospectiva.
          </div>
        )}
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button
            className="primary-button"
            type="button"
            disabled={generateRetrospective.isPending || !hasPosts}
            onClick={() => generateRetrospective.mutate({ workspaceId, periodDays: 60 })}
          >
            <Lightbulb size={15} />
            {generateRetrospective.isPending ? "Analisando..." : "Gerar Retrospectiva (últimos 60 dias)"}
          </button>
          {retrospective && (
            <StatusPill variant={retrospective.generation_mode === "live" ? "connected" : "paused"}>
              {retrospective.generation_mode === "live" ? "Análise real de IA" : "Prévia local (sem OPENAI_API_KEY)"}
            </StatusPill>
          )}
        </div>

        {loadingRetro && <EmptyState compact text="Carregando retrospectiva..." />}

        {output && (
          <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 12 }}>
            <p style={{ fontSize: 13, color: "var(--text-muted)" }}>{output.sintese}</p>
            {output.themes_performantes.length > 0 && (
              <div>
                <strong style={{ fontSize: 13 }}>Temas que performaram:</strong>
                <ul style={{ margin: "4px 0", paddingLeft: 20, fontSize: 13 }}>
                  {output.themes_performantes.map((theme, i) => <li key={i}>{theme}</li>)}
                </ul>
              </div>
            )}
            {output.hooks_que_funcionam.length > 0 && (
              <div>
                <strong style={{ fontSize: 13 }}>Ganchos que funcionam:</strong>
                <div className="table-list" style={{ marginTop: 6 }}>
                  {output.hooks_que_funcionam.map((hook, i) => (
                    <div className="table-row" key={i}>
                      <strong>"{hook.hook_text}"</strong>
                      <span>{hook.padrao}</span>
                      <span>{hook.por_que_funciona}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </article>

      {hookBank && hookBank.length > 0 && (
        <article className="surface">
          <SectionHeader eyebrow="Memória de Longo Prazo" title="Banco de Ganchos" icon={BookOpen} />
          <div className="table-list" style={{ marginTop: 12 }}>
            {hookBank.map((hook) => (
              <div className="table-row" key={hook.id}>
                <strong>"{hook.hook_text}"</strong>
                <span>{hook.hook_pattern ?? "—"}</span>
                <span className="demo-badge">{hook.source === "higgsfield_virality" ? "Higgsfield" : "Transcrição + IA"}</span>
              </div>
            ))}
          </div>
        </article>
      )}

      {/* O loop de aprendizado: com a atribuição roteiro->post ligada, dá para
          responder se a IA da casa performa acima do resto da conta. Média por
          post (não soma) para não premiar o grupo com mais publicações. */}
      {scoreboard && scoreboard.ai_posts > 0 && (
        <article className="surface">
          <SectionHeader
            eyebrow="Aprendizado"
            title="Roteiros da IA x resto da conta"
            icon={TrendingUp}
          />
          <p style={{ color: "var(--text-muted)", fontSize: 13, margin: "8px 0 16px" }}>
            {scoreboard.ai_posts} post(s) vindos de roteiro da IA contra {scoreboard.other_posts} post(s) do
            restante, nos últimos 90 dias. Métricas reais sincronizadas do Instagram.
          </p>

          {scoreboard.other_posts === 0 ? (
            <div className="notice">
              Ainda não há posts fora da IA no período — sem base de comparação, o placar não afirma ganho.
            </div>
          ) : (
            <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginBottom: 12 }}>
              {[
                { label: "Alcance médio", ai: scoreboard.ai_avg_reach, base: scoreboard.other_avg_reach, lift: scoreboard.lift_reach_percent },
                { label: "Engajamento médio", ai: scoreboard.ai_avg_engagement, base: scoreboard.other_avg_engagement, lift: scoreboard.lift_engagement_percent },
                { label: "Salvamentos médios", ai: scoreboard.ai_avg_saved, base: scoreboard.other_avg_saved, lift: null },
              ].map((metric) => (
                <div key={metric.label} style={{ minWidth: 170 }}>
                  <small style={{ color: "var(--text-dim)", textTransform: "uppercase", fontSize: 10 }}>{metric.label}</small>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>
                    {metric.ai !== null ? Math.round(metric.ai) : "—"}
                    <span style={{ fontSize: 13, fontWeight: 400, color: "var(--text-muted)" }}>
                      {" "}vs {metric.base !== null ? Math.round(metric.base) : "—"}
                    </span>
                  </div>
                  {metric.lift !== null && metric.lift !== undefined && (
                    <span style={{ fontSize: 12, fontWeight: 600, color: metric.lift >= 0 ? "#2e9e5b" : "#ff5252" }}>
                      {metric.lift >= 0 ? "+" : ""}{metric.lift}%
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {scoreboard.per_script.length > 0 && (
            <div className="table-list">
              {scoreboard.per_script.map((row) => (
                <div className="table-row" key={row.script_id}>
                  <strong style={{ flex: 1 }}>{row.title}</strong>
                  <span>{row.suggested_format ?? row.theme ?? "—"}</span>
                  <span>{row.posts} post(s)</span>
                  <span>{Math.round(row.avg_reach)} alcance</span>
                  <span>{Math.round(row.avg_engagement)} engaj.</span>
                </div>
              ))}
            </div>
          )}
        </article>
      )}

      {/* Fecha o ciclo: o roteiro que a IA gerou virou qual post, e como esse
          post performou de verdade. Sem isso, `source_script_id` era gravável
          pela API e invisível na interface — não havia como medir se o roteiro
          gerado funcionou. */}
      {hasPosts && (scripts?.length ?? 0) > 0 && (
        <article className="surface">
          <SectionHeader
            eyebrow="Atribuição"
            title="Qual roteiro virou qual post (e como performou)"
            icon={Lightbulb}
          />
          <p style={{ color: "var(--text-muted)", fontSize: 13, margin: "8px 0 16px" }}>
            Vincule o post publicado ao roteiro que o originou. As métricas ao lado são as reais
            sincronizadas do Instagram — é assim que se sabe se o roteiro gerado performou.
          </p>
          <div className="table-list">
            {(posts ?? []).slice(0, 15).map((post) => {
              const linkedScript = (scripts ?? []).find((script) => script.id === post.source_script_id);
              return (
                <div className="table-row" key={post.id}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <strong style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {post.caption?.slice(0, 70) || post.media_type}
                    </strong>
                    <small style={{ color: "var(--text-muted)" }}>
                      {post.posted_at ? new Date(post.posted_at).toLocaleDateString("pt-BR") : "sem data"} ·{" "}
                      {post.reach} alcance · {post.likes} likes · {post.saved} salvos
                    </small>
                  </div>
                  <select
                    value={post.source_script_id ?? ""}
                    disabled={linkPostToScript.isPending}
                    onChange={(event) => {
                      if (!event.target.value) return;
                      linkPostToScript.mutate({ workspaceId, postId: post.id, scriptId: event.target.value });
                    }}
                    style={{ fontSize: 12, maxWidth: 240 }}
                  >
                    <option value="">Sem roteiro vinculado</option>
                    {(scripts ?? []).map((script) => (
                      <option key={script.id} value={script.id}>
                        {script.title}
                      </option>
                    ))}
                  </select>
                  {linkedScript && <span className="demo-badge">roteiro EG</span>}
                </div>
              );
            })}
          </div>
          {linkPostToScript.isError && (
            <div className="notice error" style={{ marginTop: 10 }}>
              {linkPostToScript.error instanceof Error ? linkPostToScript.error.message : "Falha ao vincular."}
            </div>
          )}
        </article>
      )}

      <article className="surface">
        <SectionHeader eyebrow="Roteirização Automática" title="Gerar Roteiros do Mês" icon={WandSparkles} />
        <p style={{ color: "var(--text-muted)", fontSize: 13, margin: "8px 0 16px" }}>
          Cruza a retrospectiva, o banco de ganchos, o calendário de datas comemorativas e (opcionalmente) o
          benchmark de concorrentes do Ahrefs para gerar um lote de roteiros prontos para gravação.
        </p>
        {!retrospective && (
          <div className="notice" style={{ marginBottom: 12 }}>
            Gere a retrospectiva acima primeiro — os roteiros são construídos em cima dela.
          </div>
        )}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 12 }}>
          <label style={{ fontSize: 12 }}>
            Quantidade de roteiros
            <input
              type="number"
              min={1}
              max={30}
              value={scriptCount}
              onChange={(e) => setScriptCount(Number(e.target.value))}
              style={{ display: "block", padding: "6px 10px", borderRadius: 4, border: "1px solid var(--border-light)", marginTop: 4 }}
            />
          </label>
          <label style={{ fontSize: 12, flex: 1, minWidth: 220 }}>
            Handles de concorrentes (opcional, separados por vírgula)
            <input
              type="text"
              placeholder="@concorrente1, @concorrente2"
              value={competitorInput}
              onChange={(e) => setCompetitorInput(e.target.value)}
              style={{ display: "block", width: "100%", padding: "6px 10px", borderRadius: 4, border: "1px solid var(--border-light)", marginTop: 4, boxSizing: "border-box" }}
            />
          </label>
          <button
            className="primary-button"
            type="button"
            disabled={generateScripts.isPending || !retrospective}
            onClick={() =>
              generateScripts.mutate({
                workspaceId,
                count: scriptCount,
                competitorHandles: competitorInput.split(",").map((h) => h.trim()).filter(Boolean),
              })
            }
          >
            <WandSparkles size={15} />
            {generateScripts.isPending ? "Gerando..." : "Gerar Roteiros"}
          </button>
        </div>

        {scripts && scripts.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {scripts.map((script) => (
              <details key={script.id} className="surface" style={{ padding: 16 }}>
                <summary style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                  <span>
                    <strong>{script.title}</strong>{" "}
                    <span style={{ color: "var(--text-muted)", fontSize: 12 }}>· {script.suggested_format}</span>
                  </span>
                  <StatusPill variant={script.status === "discarded" ? "not_configured" : script.status === "suggested" ? "paused" : "connected"}>
                    {script.status}
                  </StatusPill>
                </summary>
                <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
                  <p><strong>Gancho de abertura:</strong> {script.hook_opening}</p>
                  <p style={{ whiteSpace: "pre-wrap" }}>{script.script_body}</p>
                  <p><strong>CTA:</strong> {script.cta}</p>
                  <p style={{ color: "var(--text-muted)" }}><strong>Por quê esse tema:</strong> {script.rationale}</p>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      className="mini-button approve"
                      type="button"
                      disabled={sentToCalendar[script.id] || createCalendarItem.isPending}
                      onClick={() => handleSendToCalendar(script)}
                    >
                      <Send size={13} />
                      {sentToCalendar[script.id] ? "Enviado ao Calendário" : "Enviar ao Calendário Editorial"}
                    </button>
                  </div>
                </div>
              </details>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

function CalendarSection({ workspaceId }: { workspaceId: string }) {
  const { data: items, isLoading } = useCalendarItems(workspaceId);
  const createItem = useCreateCalendarItem();
  const updateStage = useUpdateCalendarStage();

  const [title, setTitle] = useState("");
  const [channel, setChannel] = useState<"instagram" | "linkedin" | "facebook" | "tiktok">("instagram");
  const [postText, setPostText] = useState("");

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!title) return;
    createItem.mutate(
      {
        workspaceId,
        payload: {
          title,
          channel,
          post_text: postText || undefined,
          stage: "ideation",
        },
      },
      {
        onSuccess: () => {
          setTitle("");
          setPostText("");
        },
      }
    );
  }

  const stages = [
    { id: "ideation", label: "Ideação" },
    { id: "production", label: "Em Produção" },
    { id: "review", label: "Revisão" },
    { id: "approved", label: "Aprovado" },
    { id: "scheduled", label: "Agendado" },
    { id: "published", label: "Publicado" },
  ];

  if (isLoading) return <EmptyState compact text="Carregando Calendário Editorial..." />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <article className="surface">
        <SectionHeader eyebrow="Planejamento Editorial" title="Adicionar Novo Conteúdo" icon={Calendar} />
        <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "12px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
            <input
              type="text"
              placeholder="Título da peça ou ideia de anúncio..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{ padding: "8px 12px", borderRadius: "4px", border: "1px solid var(--border-light)" }}
              required
            />
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value as any)}
              style={{ padding: "8px 12px", borderRadius: "4px", border: "1px solid var(--border-light)" }}
            >
              <option value="instagram">Instagram</option>
              <option value="linkedin">LinkedIn</option>
              <option value="facebook">Facebook</option>
              <option value="tiktok">TikTok</option>
            </select>
          </div>
          <textarea
            placeholder="Legenda, roteiro ou rascunho de texto (opcional)..."
            value={postText}
            onChange={(e) => setPostText(e.target.value)}
            rows={2}
            style={{ padding: "8px 12px", borderRadius: "4px", border: "1px solid var(--border-light)" }}
          />
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button className="secondary-button" type="submit" disabled={createItem.isPending}>
              <Plus size={15} /> Adicionar à Esteira
            </button>
          </div>
        </form>
      </article>

      <article className="surface">
        <SectionHeader eyebrow="Esteira Social Media" title="Kanban do Calendário Editorial" icon={Calendar} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", marginTop: "16px" }}>
          {stages.map((stg) => {
            const stageItems = items?.filter((i) => i.stage === stg.id) ?? [];
            return (
              <div
                key={stg.id}
                style={{
                  background: "var(--bg-elevated)",
                  padding: "12px",
                  borderRadius: "6px",
                  border: "1px solid var(--border-light)",
                  minHeight: "200px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
                  <strong style={{ fontSize: "13px" }}>{stg.label}</strong>
                  <span className="demo-badge">{stageItems.length}</span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {stageItems.map((item) => (
                    <div
                      key={item.id}
                      style={{
                        background: "var(--surface)",
                        padding: "10px",
                        borderRadius: "4px",
                        border: "1px solid var(--border-light)",
                        fontSize: "12px",
                      }}
                    >
                      <strong style={{ display: "block", marginBottom: "4px" }}>{item.title}</strong>
                      <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>{item.channel.toUpperCase()}</span>
                      
                      <div style={{ marginTop: "8px", display: "flex", gap: "4px" }}>
                        {stg.id !== "published" && (
                          <button
                            className="mini-button"
                            type="button"
                            style={{ fontSize: "10px", padding: "2px 6px" }}
                            onClick={() => {
                              const nextStage = stages[stages.findIndex((s) => s.id === stg.id) + 1]?.id;
                              if (nextStage) updateStage.mutate({ workspaceId, itemId: item.id, stage: nextStage });
                            }}
                          >
                            Avançar ➔
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </article>
    </div>
  );
}

export function AiContentStudio({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient();
  const [mainTab, setMainTab] = useState<MainTab>("artifacts");
  const [contentType, setContentType] = useState<ContentType>("social_posts");
  const [imageProvider, setImageProvider] = useState<ImageProvider>("dalle_3");
  const [brief, setBrief] = useState("");
  const [channels, setChannels] = useState<AiContentPost["channel"][]>(["instagram", "linkedin"]);
  const [quantity, setQuantity] = useState(3);
  const [tone, setTone] = useState("consultivo, humano e direto");
  const [objective, setObjective] = useState("");
  const [methodology, setMethodology] = useState("Social Media Engine");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const requests = useQuery({
    queryKey: ["ai-content", workspaceId],
    queryFn: () => api.aiContentRequests(workspaceId),
    refetchInterval: (query) => query.state.data?.some((request) => ["queued", "running"].includes(request.status)) ? 3000 : false,
  });

  const createRequest = useMutation({
    mutationFn: () => api.createAiContentRequest(workspaceId, {
      content_type: contentType,
      brief: brief.trim(),
      channels,
      quantity,
      tone: tone.trim() || null,
      objective: objective.trim() || null,
      methodology_refs: methodology.split(",").map((item) => item.trim()).filter(Boolean),
      image_provider: contentType === "image_generation" ? imageProvider : undefined,
    }),
    onSuccess: async () => {
      setBrief("");
      await queryClient.invalidateQueries({ queryKey: ["ai-content", workspaceId] });
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!brief.trim()) return;
    createRequest.mutate();
  }

  function toggleChannel(channel: AiContentPost["channel"]) {
    setChannels((prev) => prev.includes(channel) ? prev.filter((c) => c !== channel) : [...prev, channel]);
  }

  function handleCopy(key: string, text: string) {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, gridColumn: "1 / -1" }}>
      {/* Abas Principais: Estúdio, Brand Book, Calendário */}
      <div className="performance-tabs" role="tablist">
        {/* Decisão 8: a vista dos artefatos vem PRIMEIRO. O formulário continua
            ao lado enquanto o fluxo pela conversa não cobre tudo (imagem e
            calendário ainda passam por ele) — mas deixou de ser a porta de
            entrada, que era o que fazia o material morrer na conversa. */}
        <button
          className={mainTab === "artifacts" ? "performance-tab active" : "performance-tab"}
          type="button"
          onClick={() => setMainTab("artifacts")}
        >
          <Sparkles size={15} /> Estúdio
        </button>
        {/* Decisao 14: gerenciar o blog SEM abrir o CMS de cada cliente.
            Fica ao lado do Estudio porque e a outra ponta do mesmo fluxo — o
            Estudio produz, o Blog e onde o produzido vive. */}
        <button
          className={mainTab === "blog" ? "performance-tab active" : "performance-tab"}
          type="button"
          onClick={() => setMainTab("blog")}
        >
          <Globe size={15} /> Blog do site
        </button>
        <button
          className={mainTab === "studio" ? "performance-tab active" : "performance-tab"}
          type="button"
          onClick={() => setMainTab("studio")}
        >
          <WandSparkles size={15} /> Geração direta
        </button>
        <button
          className={mainTab === "brand_book" ? "performance-tab active" : "performance-tab"}
          type="button"
          onClick={() => setMainTab("brand_book")}
        >
          <BookOpen size={15} /> Brand Book da Marca
        </button>
        <button
          className={mainTab === "calendar" ? "performance-tab active" : "performance-tab"}
          type="button"
          onClick={() => setMainTab("calendar")}
        >
          <Calendar size={15} /> Esteira do Calendário Editorial
        </button>
        <button
          className={mainTab === "retrospective" ? "performance-tab active" : "performance-tab"}
          type="button"
          onClick={() => setMainTab("retrospective")}
        >
          <Lightbulb size={15} /> Retrospectiva & Roteiros
        </button>
      </div>

      {mainTab === "artifacts" && <StudioArtifactList workspaceId={workspaceId} />}
      {mainTab === "blog" && <CmsPostsManager workspaceId={workspaceId} />}
      {mainTab === "brand_book" && <BrandBookSection workspaceId={workspaceId} />}
      {mainTab === "calendar" && <CalendarSection workspaceId={workspaceId} />}
      {mainTab === "retrospective" && <RetrospectiveSection workspaceId={workspaceId} />}

      {mainTab === "studio" && (
        <>
          <article className="surface">
            <SectionHeader
              eyebrow="Estúdio IA Multi-modal"
              title="Geração Inteligente de Conteúdo (Posts, Artes e Roteiros de Vídeo)"
              icon={WandSparkles}
            />

            <form className="form-grid" onSubmit={handleSubmit} style={{ marginTop: 16 }}>
              <div style={{ display: "flex", gap: 12, gridColumn: "1 / -1", flexWrap: "wrap" }}>
                <button
                  type="button"
                  className={contentType === "social_posts" ? "primary-button" : "ghost-button"}
                  onClick={() => setContentType("social_posts")}
                >
                  <MessageSquareText size={15} /> Copywriting & Posts
                </button>
                <button
                  type="button"
                  className={contentType === "image_generation" ? "primary-button" : "ghost-button"}
                  onClick={() => setContentType("image_generation")}
                >
                  <ImageIcon size={15} /> Artes Visuais (Imagens)
                </button>
                <button
                  type="button"
                  className={contentType === "video_scripts" ? "primary-button" : "ghost-button"}
                  onClick={() => setContentType("video_scripts")}
                >
                  <Film size={15} /> Roteiros de Vídeo & Ads
                </button>
              </div>

              {contentType === "image_generation" && (
                <label style={{ gridColumn: "1 / -1" }}>
                  Provedor de Imagem
                  <select value={imageProvider} onChange={(e) => setImageProvider(e.target.value as ImageProvider)}>
                    <option value="dalle_3">OpenAI DALL-E 3 (Alta precisão)</option>
                    <option value="flux">Flux.1 Schnell (Estética fotorrealista)</option>
                    <option value="higgsfield">Higgsfield AI (Artes publicitárias)</option>
                  </select>
                </label>
              )}

              <label style={{ gridColumn: "1 / -1" }}>
                Briefing / Tópico Principal
                <textarea
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  placeholder="Ex: Estratégias para escalar receita recorrente em B2B..."
                  rows={3}
                  required
                />
              </label>

              {contentType === "social_posts" && (
                <div>
                  <label style={{ marginBottom: 6, display: "block" }}>Canais Destino</label>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {channelOptions.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        className={channels.includes(opt.value) ? "mini-button approve" : "mini-button"}
                        onClick={() => toggleChannel(opt.value)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "flex-end" }}>
                <button className="primary-button" type="submit" disabled={createRequest.isPending || !brief.trim()}>
                  {createRequest.isPending ? <LoaderCircle size={16} className="spin" /> : <Sparkles size={16} />}
                  {createRequest.isPending ? "Gerando..." : "Gerar Conteúdo"}
                </button>
              </div>
            </form>
          </article>

          {/* Resultados das Requisições */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {requests.data?.map((req) => (
              <article key={req.id} className="surface" style={{ padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div>
                    <h4 style={{ margin: 0, fontSize: 15 }}>{req.brief}</h4>
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                      {new Date(req.created_at).toLocaleString("pt-BR")}
                    </span>
                  </div>
                  <span className={`status-badge status-${req.status}`}>{req.status}</span>
                </div>

                {req.status === "ready" && req.output && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 12 }}>
                    {req.output.posts?.map((post, idx) => (
                      <div key={idx} style={{ background: "var(--bg-elevated)", padding: 12, borderRadius: 6 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                          <strong>{post.channel.toUpperCase()} — {post.title} ({post.format})</strong>
                          <button className="ghost-button" type="button" onClick={() => handleCopy(`post-${idx}`, `${post.hook}\n\n${post.caption}\n\n${post.cta}`)}>
                            {copiedKey === `post-${idx}` ? <Check size={14} /> : <Copy size={14} />} Copiar
                          </button>
                        </div>
                        <p style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "var(--text-muted)" }}>{post.hook}</p>
                        <p style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "var(--text-muted)", marginTop: 6 }}>{post.caption}</p>
                      </div>
                    ))}

                    {req.output.images?.map((img, idx) => (
                      <div key={idx} style={{ background: "var(--bg-elevated)", padding: 12, borderRadius: 6 }}>
                        <strong>{img.title} ({img.provider.toUpperCase()})</strong>
                        <p style={{ fontSize: 12, color: "var(--text-muted)" }}><strong>Prompt Visual:</strong> {img.prompt_en}</p>
                      </div>
                    ))}

                    {req.output.video_scripts?.map((script, idx) => (
                      <div key={idx} style={{ background: "var(--bg-elevated)", padding: 12, borderRadius: 6 }}>
                        <strong>🎥 {script.title} (Hook: {script.hook_0_3s})</strong>
                        <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}><strong>Locução:</strong> {script.script_body}</p>
                        <p style={{ fontSize: 12, color: "var(--brand-accent)" }}><strong>Visual/B-Roll:</strong> {script.broll_notes}</p>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
