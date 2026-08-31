import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BookOpen,
  Eye,
  EyeOff,
  FileText,
  Loader2,
  Plus,
  Search,
} from "lucide-react";

import { api, type KnowledgeChunk, type SearchHit } from "../lib/api";
import { EmptyState } from "./shared";

/**
 * Base de conhecimento — decisão 7, Fase 1.
 *
 * Resposta do Eduardo: "faça para ambos" — a base pende do **workspace**, que é
 * o eixo que já separa EG de cliente no resto do sistema.
 *
 * Duas coisas nesta tela existem para a base ser CONFIÁVEL, não só funcional:
 *
 * - **Inspeção dos fragmentos.** Quando a base responde mal, a pergunta é
 *   sempre "o que ela leu?". Sem poder ver como o documento foi partido, a
 *   resposta é um encolher de ombros.
 * - **Citação que abre na origem.** O trecho vem recortado do texto original,
 *   com o que veio antes e depois. É o que separa "está em algum lugar deste
 *   documento, confie em mim" de uma citação verificável.
 *
 * A busca é lexical e a tela **diz isso**. Sem o aviso, alguém olharia um
 * resultado fraco e concluiria que a busca semântica está ruim — quando ela
 * ainda nem existe (Fase 3).
 */
export function KnowledgeBaseManager({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient();
  const [baseId, setBaseId] = useState<string>("");
  const [novaBase, setNovaBase] = useState("");
  const [termo, setTermo] = useState("");
  const [buscado, setBuscado] = useState("");
  const [documentoAberto, setDocumentoAberto] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const { data: bases = [], isLoading } = useQuery({
    queryKey: ["knowledge-bases", workspaceId],
    queryFn: () => api.knowledgeBases(workspaceId),
  });
  const base = bases.find((item) => item.id === baseId) ?? bases[0] ?? null;

  const { data: documentos = [] } = useQuery({
    queryKey: ["knowledge-documents", workspaceId, base?.id],
    queryFn: () => api.knowledgeDocuments(workspaceId, base!.id),
    enabled: Boolean(base),
  });

  const { data: resultado } = useQuery({
    queryKey: ["knowledge-search", workspaceId, base?.id, buscado],
    queryFn: () => api.knowledgeSearch(workspaceId, buscado, base?.id),
    enabled: Boolean(base && buscado),
  });

  const criarBase = useMutation({
    mutationFn: () => api.createKnowledgeBase(workspaceId, { name: novaBase.trim() }),
    onSuccess: () => {
      setNovaBase("");
      setErro(null);
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases", workspaceId] });
    },
    onError: (err: Error) => setErro(err.message),
  });

  if (isLoading) return <EmptyState text="Carregando bases..." />;

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <header style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <BookOpen size={16} aria-hidden />
        <strong style={{ fontSize: 14 }}>Base de conhecimento</strong>
        {bases.length > 1 && (
          <select value={base?.id ?? ""} onChange={(e) => setBaseId(e.target.value)} style={{ fontSize: 12 }}>
            {bases.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} ({item.documents_total})
              </option>
            ))}
          </select>
        )}
      </header>

      {bases.length === 0 && (
        <p style={{ fontSize: 12, color: "var(--text-faint)", margin: 0, lineHeight: 1.5 }}>
          Nenhuma base neste workspace ainda. Crie a primeira e envie o texto de um
          processo, política ou contrato-modelo.
        </p>
      )}

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <input
          value={novaBase}
          onChange={(e) => setNovaBase(e.target.value)}
          placeholder="Nome da nova base (ex: Processos da EG)"
          style={{ fontSize: 12, flex: 1, minWidth: 200 }}
        />
        <button
          type="button"
          className="mini-button"
          disabled={novaBase.trim().length < 2 || criarBase.isPending}
          onClick={() => criarBase.mutate()}
        >
          <Plus size={12} aria-hidden /> Criar base
        </button>
      </div>

      {erro && (
        <p style={{ fontSize: 12, color: "var(--danger-soft)", margin: 0 }}>
          <AlertTriangle size={12} aria-hidden /> {erro}
        </p>
      )}

      {base && (
        <>
          <NovoDocumento workspaceId={workspaceId} baseId={base.id} />

          <form
            onSubmit={(event) => {
              event.preventDefault();
              setBuscado(termo.trim());
            }}
            style={{ display: "flex", gap: 6 }}
          >
            <input
              value={termo}
              onChange={(e) => setTermo(e.target.value)}
              placeholder="Buscar na base..."
              style={{ fontSize: 12, flex: 1 }}
            />
            <button type="submit" className="mini-button">
              <Search size={12} aria-hidden /> Buscar
            </button>
          </form>

          {resultado && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {/* O aviso do modo NÃO é detalhe técnico: sem ele, resultado
                  fraco vira "a busca por IA está ruim" — e ela nem existe. */}
              <p style={{ fontSize: 10.5, color: "var(--text-faint)", margin: 0 }}>
                Busca por palavra ({resultado.hits.length} trecho
                {resultado.hits.length === 1 ? "" : "s"}). Busca semântica ainda não
                está disponível — entra na Fase 3.
              </p>
              {resultado.hits.length === 0 && (
                <p style={{ fontSize: 12, color: "var(--text-faint)", margin: 0 }}>
                  Nada encontrado para "{resultado.query}".
                </p>
              )}
              {resultado.hits.map((hit) => (
                <ResultadoBusca key={hit.chunk_id} workspaceId={workspaceId} hit={hit} />
              ))}
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {documentos.map((documento) => (
              <article
                key={documento.id}
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: 12,
                  background: "var(--bg-inset)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
                  <div style={{ minWidth: 0 }}>
                    <strong style={{ fontSize: 13 }}>
                      <FileText size={13} aria-hidden style={{ display: "inline", marginRight: 4 }} />
                      {documento.title}
                    </strong>
                    <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 2 }}>
                      {documento.status === "indexed"
                        ? `${documento.chunks_total} fragmentos · v${documento.current_version}`
                        : documento.status === "failed"
                          ? // Documento que falhou continua na lista COM o motivo:
                            // sumir com ele faria a pessoa reenviar sem entender.
                            `não indexado — ${documento.failure_reason}`
                          : "aguardando indexação"}
                    </div>
                  </div>
                  {documento.status === "indexed" && (
                    <button
                      type="button"
                      className="mini-button"
                      onClick={() => setDocumentoAberto(documentoAberto === documento.id ? null : documento.id)}
                    >
                      {documentoAberto === documento.id ? "Fechar" : "Ver fragmentos"}
                    </button>
                  )}
                </div>
                {documentoAberto === documento.id && (
                  <ListaFragmentos workspaceId={workspaceId} documentId={documento.id} />
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function NovoDocumento({ workspaceId, baseId }: { workspaceId: string; baseId: string }) {
  const queryClient = useQueryClient();
  const [titulo, setTitulo] = useState("");
  const [conteudo, setConteudo] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const enviar = useMutation({
    mutationFn: () => api.addKnowledgeDocument(workspaceId, baseId, { title: titulo.trim(), content: conteudo }),
    onSuccess: () => {
      setTitulo("");
      setConteudo("");
      setErro(null);
      queryClient.invalidateQueries({ queryKey: ["knowledge-documents", workspaceId, baseId] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases", workspaceId] });
    },
    onError: (err: Error) => setErro(err.message),
  });

  return (
    <div
      style={{
        border: "1px dashed var(--border-strong)",
        borderRadius: 8,
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <strong style={{ fontSize: 12.5 }}>Adicionar documento</strong>
      <input
        value={titulo}
        onChange={(e) => setTitulo(e.target.value)}
        placeholder="Título (ex: Política de atendimento)"
        style={{ fontSize: 12 }}
      />
      <textarea
        value={conteudo}
        onChange={(e) => setConteudo(e.target.value)}
        rows={6}
        placeholder={"Cole o texto. Títulos em Markdown (## Seção) viram a trilha do fragmento e pesam mais na busca."}
        style={{ fontSize: 12, fontFamily: "inherit" }}
      />
      <button
        type="button"
        className="primary-button"
        disabled={titulo.trim().length < 2 || !conteudo.trim() || enviar.isPending}
        onClick={() => enviar.mutate()}
      >
        {enviar.isPending ? <Loader2 size={13} className="spin" aria-hidden /> : null} Indexar
      </button>
      {erro && (
        <p style={{ fontSize: 11.5, color: "var(--danger-soft)", margin: 0 }}>
          <AlertTriangle size={12} aria-hidden /> {erro}
        </p>
      )}
    </div>
  );
}

function ListaFragmentos({ workspaceId, documentId }: { workspaceId: string; documentId: string }) {
  const queryClient = useQueryClient();
  const { data: fragmentos = [], isLoading } = useQuery({
    queryKey: ["knowledge-chunks", workspaceId, documentId],
    queryFn: () => api.knowledgeChunks(workspaceId, documentId),
  });

  const alternar = useMutation({
    mutationFn: ({ chunkId, ativo }: { chunkId: string; ativo: boolean }) =>
      api.setKnowledgeChunkActive(workspaceId, chunkId, ativo),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-chunks", workspaceId, documentId] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-search"] });
    },
  });

  if (isLoading) return <p style={{ fontSize: 11.5, color: "var(--text-faint)" }}>Carregando fragmentos...</p>;

  return (
    <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
      {fragmentos.map((fragmento: KnowledgeChunk) => (
        <div
          key={fragmento.id}
          style={{
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: 8,
            background: "var(--surface)",
            opacity: fragmento.is_active ? 1 : 0.55,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start" }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 10, color: "var(--text-faint)" }}>
                #{fragmento.position}
                {fragmento.heading_path.length > 0 && ` · ${fragmento.heading_path.join(" › ")}`}
                {" · "}
                caracteres {fragmento.char_start}–{fragmento.char_end}
              </div>
              <p style={{ fontSize: 11.5, color: "var(--text-muted)", margin: "4px 0 0", lineHeight: 1.45 }}>
                {fragmento.content.slice(0, 220)}
                {fragmento.content.length > 220 && "..."}
              </p>
            </div>
            {/* Desativar, não apagar: o fragmento sai da busca e continua
                inspecionável. Apagar esconderia por que a base respondeu mal. */}
            <button
              type="button"
              className="mini-button"
              disabled={alternar.isPending}
              onClick={() => alternar.mutate({ chunkId: fragmento.id, ativo: !fragmento.is_active })}
              title={fragmento.is_active ? "Tirar da busca" : "Devolver à busca"}
            >
              {fragmento.is_active ? <Eye size={12} aria-hidden /> : <EyeOff size={12} aria-hidden />}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function ResultadoBusca({ workspaceId, hit }: { workspaceId: string; hit: SearchHit }) {
  const [aberto, setAberto] = useState(false);
  const { data: origem } = useQuery({
    queryKey: ["knowledge-origin", workspaceId, hit.chunk_id],
    queryFn: () => api.knowledgeChunkOrigin(workspaceId, hit.chunk_id),
    enabled: aberto,
  });

  return (
    <article style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 10, background: "var(--bg-inset)" }}>
      <div style={{ fontSize: 10.5, color: "var(--text-faint)" }}>
        {hit.document_title}
        {hit.heading_path.length > 0 && ` › ${hit.heading_path.join(" › ")}`}
      </div>
      <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "4px 0 6px", lineHeight: 1.5 }}>{hit.content}</p>
      <button type="button" className="mini-button" onClick={() => setAberto((a) => !a)}>
        {aberto ? "Fechar origem" : "Ver na origem"}
      </button>
      {aberto && origem && (
        <div
          style={{
            marginTop: 8,
            fontSize: 11.5,
            lineHeight: 1.55,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: 10,
            maxHeight: 280,
            overflowY: "auto",
            whiteSpace: "pre-wrap",
          }}
        >
          <span style={{ color: "var(--text-faint)" }}>{origem.before}</span>
          {/* O destaque é o trecho EXATO que a busca devolveu, recortado do
              texto original pelos offsets. É isso que torna a citação
              verificável em vez de um "confie em mim". */}
          <mark style={{ background: "var(--amber)", color: "#111", padding: "0 2px" }}>{origem.content}</mark>
          <span style={{ color: "var(--text-faint)" }}>{origem.after}</span>
        </div>
      )}
    </article>
  );
}
