import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { KommoDashboardBody, PeriodSegmented, formatDateTime } from "../../components/KommoRealDashboard";
import { portalApi } from "../../lib/portalApi";
import "./univet-portal.css";

const SLUG = "univet";

const PORTALS = [
  { path: "/portal/univet", label: "Apresentação" },
  { path: "/portal/univet/v2", label: "Dados reais" },
  { path: "/portal/univet/eg", label: "Operação EG" },
];

/** Cabeçalho comum aos portais da Univet, com a navegação entre eles. */
export function UnivetPortalChrome({ subtitle, children, actions }: { subtitle: string; children: React.ReactNode; actions?: React.ReactNode }) {
  const current = window.location.pathname.replace(/\/$/, "");
  // Todos os 3 portais acessíveis na navegação superior
  const portals = PORTALS;

  // Destrava e garante scroll nativo livre da página inteira
  useEffect(() => {
    const root = document.getElementById("root");
    const previous = [document.documentElement.style.overflow, document.body.style.overflow, root?.style.overflow ?? ""];
    document.documentElement.style.overflow = "auto";
    document.body.style.overflow = "auto";
    if (root) root.style.overflow = "visible";
    return () => {
      document.documentElement.style.overflow = previous[0];
      document.body.style.overflow = previous[1];
      if (root) root.style.overflow = previous[2];
    };
  }, []);

  return (
    <div className="uvPortalWrapper">
      <header className="uvPortalHeader">
        <div className="uvBrand">
          <div className="uvMonogram" aria-hidden="true">U</div>
          <div>
            <h1 className="uvBrandTitle">Univet Loupes</h1>
            <span className="uvBrandSubtitle">{subtitle}</span>
          </div>
        </div>
        <div className="uvHeaderActions">
          <nav className="uvSegmented" aria-label="Portais da Univet">
            {portals.map((portal) => (
              <a key={portal.path} className="uvSegmentedBtn" href={portal.path} aria-current={current === portal.path ? "page" : undefined}>
                {portal.label}
              </a>
            ))}
          </nav>
          {actions}
        </div>
      </header>
      <main className="uvPortalMain">{children}</main>
      <footer className="uvPortalFooter">
        <div>
          <strong>Univet Loupes Brasil</strong> · Fonte: Kommo CRM
        </div>
        <div>EverGreen Agency 2026</div>
      </footer>
    </div>
  );
}

export function UnivetRealPortal() {
  const [days, setDays] = useState(0);
  const query = useQuery({ queryKey: ["portal-dashboard", SLUG, days], queryFn: () => portalApi.dashboard(SLUG, days) });
  const response = query.data;

  return (
    <UnivetPortalChrome
      subtitle="Painel de dados reais · Brasil"
      actions={response?.dashboard ? <PeriodSegmented value={days} onChange={setDays} /> : undefined}
    >
      <section className="uvHero">
        <h2 className="uvHeroHeadline">O que o CRM mostra hoje</h2>
        <p className="uvHeroSubtitle">
          {response?.fetched_at
            ? `Lido do Kommo em ${formatDateTime(response.fetched_at)}. Nenhum número aqui é estimado; o que ainda não tem fonte conectada aparece como ausente.`
            : "Números lidos diretamente do Kommo CRM, sem dados demonstrativos."}
        </p>
      </section>

      {query.isLoading ? (
        <>
          <div className="uvSkeleton" style={{ height: 78 }} />
          <div className="uvSkeleton" style={{ height: 110 }} />
          <div className="uvSkeleton" style={{ height: 300 }} />
        </>
      ) : query.error ? (
        <div className="uvNotice uvNoticeError" role="alert">
          <h4>Não foi possível carregar o painel</h4>
          <p>{query.error instanceof Error ? query.error.message : "Erro inesperado."}</p>
        </div>
      ) : !response?.dashboard ? (
        <div className="uvNotice">
          <h4>{response?.configured ? "Conectado, falta a primeira leitura" : "Kommo ainda não conectado"}</h4>
          <p>
            A conexão e a sincronização são feitas pela EverGreen. Assim que a primeira leitura terminar, os números aparecem aqui.
          </p>
        </div>
      ) : (
        <KommoDashboardBody data={response.dashboard} subdomain={response.subdomain} />
      )}
    </UnivetPortalChrome>
  );
}
