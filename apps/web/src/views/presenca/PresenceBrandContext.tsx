import { Link } from "react-router-dom";
import type { BrandBookSummary, WorkspaceSummary } from "../../lib/api";

interface PresenceBrandContextProps {
  workspace: WorkspaceSummary;
  brandBook?: BrandBookSummary | null;
  isLoading?: boolean;
  isError?: boolean;
}

export function PresenceBrandContext({
  workspace,
  brandBook,
  isLoading,
  isError,
}: PresenceBrandContextProps) {
  return (
    <section className="presence-context" aria-label="Contexto de Marca do Workspace">
      <div className="presence-context-info">
        <div className="presence-context-title">
          <span className="presence-badge-accent">Brand Book</span>
          <strong>Diretrizes Editoriais da Marca</strong>
        </div>
        <p>
          {brandBook ? (
            <>
              Versão {brandBook.version} · Tom de voz: <strong>{brandBook.tom_de_voz}</strong>
              {brandBook.posicionamento && ` · Posicionamento: ${brandBook.posicionamento}`}
            </>
          ) : isLoading ? (
            "Carregando diretrizes de marca…"
          ) : isError ? (
            "Brand Book não configurado ou indisponível neste workspace."
          ) : (
            "Nenhum Brand Book ativo encontrado."
          )}
        </p>

        {brandBook?.paleta_cores && brandBook.paleta_cores.length > 0 && (
          <div className="presence-brand-colors" title="Paleta oficial da marca">
            {brandBook.paleta_cores.map((color, idx) => (
              <span
                key={`${color}-${idx}`}
                className="presence-color-swatch"
                style={{ backgroundColor: color }}
                title={color}
              />
            ))}
          </div>
        )}
      </div>

      {workspace.client_id && (
        <Link
          to={`/clientes/${workspace.client_id}/conteudo-ia`}
          className="presence-context-link"
          title="Acessar estúdio e gerador de diretrizes"
        >
          Abrir Brand Book e geração IA ↗
        </Link>
      )}
    </section>
  );
}
