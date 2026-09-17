import { PlanningPortfolioPanel } from "./PlanningPortfolioPanel";

export function PlanningPortfolioView() {
  return (
    <div style={{ padding: "24px", maxWidth: "1200px", margin: "0 auto", color: "var(--text)" }}>
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, margin: 0 }}>
          Portfólio de Planejamentos
        </h1>
        <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: "0.9rem" }}>
          Uma linha por projeto da EG: em que estágio está a intake de planejamento, se o plano já
          foi gerado e por qual via (IA ou prévia local). Serve para achar projeto parado sem
          precisar abrir cliente por cliente.
        </p>
      </div>

      <PlanningPortfolioPanel />
    </div>
  );
}

export default PlanningPortfolioView;
