import { useState } from "react";
import {
  CalendarClock,
  CheckCircle2,
  ExternalLink,
  FileText,
  Loader2,
  Search,
  Sparkles,
  Trash2,
  TriangleAlert,
} from "lucide-react";

import { useCmsPosts, useCmsTargets, useUpdateCmsPost, useTrashCmsPost } from "../hooks/useBiomaApi";
import type { CmsPost } from "../lib/api";
import { EmptyState } from "./shared";

/**
 * Gerenciar o blog de dentro do Bioma — decisão 14.
 *
 * A lista vem do **CMS ao vivo**, não do banco do Bioma. É a única fonte que
 * não mente sobre o que está no ar agora: alguém pode ter publicado, editado ou
 * despublicado pelo painel do WordPress, e um espelho local diria o contrário
 * com toda a confiança.
 *
 * Por isso aparecem também os posts que **não nasceram aqui**. Mostrar só o que
 * o Bioma publicou faria "gerenciar o blog" significar "gerenciar a metade que
 * passou por aqui" — e o selo de origem é o que deixa a mistura visível.
 */
export function CmsPostsManager({ workspaceId }: { workspaceId: string }) {
  const { data: targets = [], isLoading: carregandoAlvos } = useCmsTargets(workspaceId);
  const ativos = targets.filter((target) => target.is_active);
  const [targetId, setTargetId] = useState<string>("");
  const alvo = ativos.find((target) => target.id === targetId) ?? ativos[0] ?? null;

  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [pagina, setPagina] = useState(1);
  const [erro, setErro] = useState<string | null>(null);

  const { data, isLoading, error } = useCmsPosts(workspaceId, alvo?.id ?? null, {
    page: pagina,
    search: buscaAplicada || undefined,
  });
  const atualizar = useUpdateCmsPost(workspaceId, alvo?.id ?? "");
  const paraLixeira = useTrashCmsPost(workspaceId, alvo?.id ?? "");

  if (carregandoAlvos) return <EmptyState text="Carregando..." />;

  if (ativos.length === 0) {
    return (
      <p className="inline-task-composer-blocked">
        <FileText size={12} aria-hidden /> Nenhum site conectado neste workspace. Conecte o
        WordPress em Configurações › Integrações › Sites (CMS).
      </p>
    );
  }

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        {ativos.length > 1 && (
          <select
            value={alvo?.id ?? ""}
            onChange={(event) => {
              setTargetId(event.target.value);
              setPagina(1);
            }}
            aria-label="Site"
            style={{ fontSize: 12 }}
          >
            {ativos.map((target) => (
              <option key={target.id} value={target.id}>
                {target.label}
              </option>
            ))}
          </select>
        )}
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setBuscaAplicada(busca.trim());
            setPagina(1);
          }}
          style={{ display: "flex", gap: 6, flex: 1, minWidth: 200 }}
        >
          <input
            value={busca}
            onChange={(event) => setBusca(event.target.value)}
            placeholder="Buscar no blog..."
            style={{ fontSize: 12, flex: 1 }}
          />
          <button type="submit" className="mini-button">
            <Search size={12} aria-hidden /> Buscar
          </button>
        </form>
      </div>

      {isLoading && <EmptyState text="Lendo o blog..." />}

      {error && (
        <p style={{ fontSize: 12, color: "var(--danger-soft)", margin: 0, lineHeight: 1.45 }}>
          <TriangleAlert size={12} aria-hidden /> {(error as Error).message}
        </p>
      )}

      {erro && (
        <p style={{ fontSize: 12, color: "var(--danger-soft)", margin: 0, lineHeight: 1.45 }}>
          <TriangleAlert size={12} aria-hidden /> {erro}
        </p>
      )}

      {data && data.items.length === 0 && (
        <p style={{ fontSize: 12, color: "var(--text-faint)" }}>
          Nenhum post encontrado {buscaAplicada && `para "${buscaAplicada}"`}.
        </p>
      )}

      {data?.items.map((post) => (
        <PostRow
          key={post.id}
          post={post}
          ocupado={atualizar.isPending || paraLixeira.isPending}
          onStatus={(status, date) => {
            setErro(null);
            atualizar.mutate(
              { postId: String(post.id), payload: date ? { status, date } : { status } },
              { onError: (err: Error) => setErro(err.message) },
            );
          }}
          onLixeira={() => {
            setErro(null);
            paraLixeira.mutate(String(post.id), { onError: (err: Error) => setErro(err.message) });
          }}
        />
      ))}

      {data && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 11.5, color: "var(--text-faint)" }}>
          <button
            type="button"
            className="mini-button"
            disabled={pagina <= 1}
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
          >
            Anterior
          </button>
          <span>
            Página {data.page}
            {/* `total` nulo = o site não devolveu o cabeçalho. Dizer "de ?" é
                honesto; inventar um total faria a paginação mentir. */}
            {data.total_pages ? ` de ${data.total_pages}` : ""}
            {data.total !== null && ` · ${data.total} posts`}
          </span>
          <button
            type="button"
            className="mini-button"
            disabled={data.total_pages ? pagina >= data.total_pages : data.items.length === 0}
            onClick={() => setPagina((p) => p + 1)}
          >
            Próxima
          </button>
        </div>
      )}
    </section>
  );
}

function PostRow({
  post,
  ocupado,
  onStatus,
  onLixeira,
}: {
  post: CmsPost;
  ocupado: boolean;
  onStatus: (status: "publish" | "draft" | "future", date?: string) => void;
  onLixeira: () => void;
}) {
  const [agendando, setAgendando] = useState(false);
  const [quando, setQuando] = useState("");

  return (
    <article
      style={{
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 12,
        background: "var(--bg-inset)",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div style={{ minWidth: 0 }}>
          <strong style={{ fontSize: 13 }}>{post.title || "(sem título)"}</strong>
          <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 2 }}>
            <StatusSelo status={post.status} />
            {post.modified && ` · alterado em ${new Date(post.modified).toLocaleDateString("pt-BR")}`}
            {/* De onde o post veio. Escrito direto no WordPress é caso normal,
                e ver a mistura é metade do valor de gerenciar por aqui. */}
            {post.artifact_id ? (
              <span style={{ marginLeft: 6, color: "var(--mint)" }}>
                <Sparkles size={10} aria-hidden style={{ display: "inline" }} /> do Estúdio
                {post.artifact_version ? ` (v${post.artifact_version})` : ""}
              </span>
            ) : (
              <span style={{ marginLeft: 6 }}>escrito no WordPress</span>
            )}
          </div>
        </div>
        {post.link && (
          <a href={post.link} target="_blank" rel="noreferrer" style={{ fontSize: 11.5, color: "var(--accent)" }}>
            abrir <ExternalLink size={10} aria-hidden style={{ display: "inline" }} />
          </a>
        )}
      </div>

      {post.excerpt && (
        <p style={{ fontSize: 11.5, color: "var(--text-muted)", margin: 0, lineHeight: 1.45 }}>
          {post.excerpt.slice(0, 180)}
          {post.excerpt.length > 180 && "..."}
        </p>
      )}

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {post.status !== "publish" && (
          <button type="button" className="mini-button" disabled={ocupado} onClick={() => onStatus("publish")}>
            {ocupado ? <Loader2 size={12} className="spin" aria-hidden /> : <CheckCircle2 size={12} aria-hidden />}
            Publicar agora
          </button>
        )}
        {post.status !== "draft" && (
          <button type="button" className="mini-button" disabled={ocupado} onClick={() => onStatus("draft")}>
            Tirar do ar (rascunho)
          </button>
        )}
        <button type="button" className="mini-button" disabled={ocupado} onClick={() => setAgendando((a) => !a)}>
          <CalendarClock size={12} aria-hidden /> Agendar
        </button>
        <button
          type="button"
          className="mini-button"
          disabled={ocupado}
          onClick={() => {
            // Lixeira do WordPress, não exclusão definitiva — dá para
            // restaurar pelo painel do site. Mesmo assim confirma, porque
            // mexe no site do cliente.
            if (confirm(`Mover "${post.title}" para a lixeira do WordPress?`)) onLixeira();
          }}
        >
          <Trash2 size={12} aria-hidden /> Lixeira
        </button>
      </div>

      {agendando && (
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <input
            type="datetime-local"
            value={quando}
            onChange={(event) => setQuando(event.target.value)}
            style={{ fontSize: 12 }}
          />
          <button
            type="button"
            className="primary-button"
            disabled={!quando || ocupado}
            onClick={() => {
              onStatus("future", new Date(quando).toISOString());
              setAgendando(false);
            }}
          >
            Agendar publicação
          </button>
          <span style={{ fontSize: 10.5, color: "var(--text-faint)" }}>
            Agendar é publicar — só que depois, e sem ninguém revisando na hora.
          </span>
        </div>
      )}
    </article>
  );
}

function StatusSelo({ status }: { status: string }) {
  const rotulos: Record<string, { texto: string; cor: string }> = {
    publish: { texto: "no ar", cor: "var(--mint)" },
    future: { texto: "agendado", cor: "var(--accent)" },
    draft: { texto: "rascunho", cor: "var(--amber)" },
    pending: { texto: "aguardando revisão", cor: "var(--amber)" },
    private: { texto: "privado", cor: "var(--text-faint)" },
    trash: { texto: "na lixeira", cor: "var(--danger-soft)" },
  };
  const item = rotulos[status] ?? { texto: status, cor: "var(--text-faint)" };
  return <span style={{ color: item.cor, fontWeight: 600 }}>{item.texto}</span>;
}
