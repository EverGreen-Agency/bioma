import { Printer, X, CheckCircle, TrendingUp, BarChart2, ShieldCheck, Calendar, Sparkles } from "lucide-react";

export type ExecutiveReportData = {
  title: string;
  subtitle: string;
  clientName: string;
  period: string;
  summaryMetrics: Array<{ label: string; value: string; detail?: string }>;
  /** Opcional: relatorio sem destaque e melhor que relatorio com
   *  destaque inventado. */
  highlights?: string[];
  tables?: Array<{
    title: string;
    headers: string[];
    rows: string[][];
  }>;
  nextSteps?: string[];
};

export function ExecutiveReportPdfModal({
  data,
  onClose,
}: {
  data: ExecutiveReportData;
  onClose: () => void;
}) {
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ zIndex: 9999 }}>
      {/* Container Responsivo Modal / Folha de Impressão */}
      <div
        className="modal-card wide printable-report-card"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: "850px",
          width: "90vw",
          maxHeight: "90vh",
          overflowY: "auto",
          background: "#ffffff",
          color: "#0f172a",
          padding: "36px",
          borderRadius: "16px",
          fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
        }}
      >
        {/* Barra de Ações (Oculta na impressão por CSS) */}
        <div
          className="no-print"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1px solid #e2e8f0",
            paddingBottom: "16px",
            marginBottom: "24px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Sparkles size={20} color="#10b981" />
            <strong style={{ fontSize: "1.1rem", color: "#0f172a" }}>Pré-visualização do Relatório Executivo (PDF)</strong>
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={handlePrint}
              style={{
                background: "#10b981",
                color: "#ffffff",
                border: "none",
                padding: "8px 18px",
                borderRadius: "8px",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.9rem",
              }}
            >
              <Printer size={16} /> Imprimir / Salvar em PDF
            </button>
            <button
              onClick={onClose}
              style={{
                background: "#f1f5f9",
                color: "#475569",
                border: "1px solid #cbd5e1",
                padding: "8px 14px",
                borderRadius: "8px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* CABEÇALHO EXECUTIVO EVERGREEN */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            borderBottom: "2px solid #10b981",
            paddingBottom: "20px",
            marginBottom: "24px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  background: "#10b981",
                  color: "#000",
                  fontWeight: 900,
                  fontSize: "0.75rem",
                  padding: "4px 10px",
                  borderRadius: "6px",
                  letterSpacing: "1px",
                }}
              >
                EVERGREEN GROWTH
              </span>
              <span style={{ fontSize: "0.85rem", color: "#64748b", fontWeight: 500 }}>
                Relatório Operacional & BI Executivo
              </span>
            </div>
            <h1 style={{ margin: "12px 0 4px", fontSize: "1.75rem", fontWeight: 800, color: "#0f172a" }}>
              {data.title}
            </h1>
            <p style={{ margin: 0, fontSize: "0.95rem", color: "#475569" }}>{data.subtitle}</p>
          </div>

          <div style={{ textAlign: "right" }}>
            <strong style={{ fontSize: "1.05rem", color: "#0f172a", display: "block" }}>{data.clientName}</strong>
            <span style={{ fontSize: "0.85rem", color: "#64748b", display: "flex", alignItems: "center", gap: "4px", justifyContent: "flex-end", marginTop: "4px" }}>
              <Calendar size={14} /> {data.period}
            </span>
          </div>
        </div>

        {/* METRICAS CHAVE (KPIS) */}
        {data.summaryMetrics.length > 0 && (
          <div style={{ marginBottom: "28px" }}>
            <h3 style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b", marginBottom: "12px" }}>
              📊 Indicadores Chave de Desempenho (KPIs)
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: `repeat(auto-fit, minmax(180px, 1fr))`, gap: "16px" }}>
              {data.summaryMetrics.map((m, idx) => (
                <div
                  key={idx}
                  style={{
                    background: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    borderRadius: "10px",
                    padding: "16px",
                  }}
                >
                  <span style={{ fontSize: "0.78rem", color: "#64748b", fontWeight: 600, display: "block" }}>{m.label}</span>
                  <strong style={{ fontSize: "1.4rem", color: "#0f172a", display: "block", marginTop: "4px" }}>{m.value}</strong>
                  {m.detail && <span style={{ fontSize: "0.75rem", color: "#10b981", fontWeight: 600, display: "block", marginTop: "2px" }}>{m.detail}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* HIGHLIGHTS & DESTAQUES DA OPERAÇÃO */}
        {data.highlights && data.highlights.length > 0 && (
          <div style={{ marginBottom: "28px", background: "#f0fdf4", border: "1px solid #bbf7d0", padding: "20px", borderRadius: "12px" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", color: "#166534", display: "flex", alignItems: "center", gap: "8px" }}>
              <ShieldCheck size={18} color="#166534" /> Destaques & Entregas Consolidadas
            </h3>
            <ul style={{ margin: 0, paddingLeft: "20px", color: "#15803d", fontSize: "0.9rem", lineHeight: 1.6 }}>
              {data.highlights!.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* TABELAS DETALHADAS */}
        {data.tables &&
          data.tables.map((table, tIdx) => (
            <div key={tIdx} style={{ marginBottom: "28px" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a", marginBottom: "12px" }}>{table.title}</h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
                <thead>
                  <tr style={{ background: "#f1f5f9", borderBottom: "2px solid #cbd5e1" }}>
                    {table.headers.map((h, hIdx) => (
                      <th key={hIdx} style={{ padding: "10px 12px", fontWeight: 700, color: "#334155" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((row, rIdx) => (
                    <tr key={rIdx} style={{ borderBottom: "1px solid #e2e8f0" }}>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} style={{ padding: "10px 12px", color: "#334155" }}>
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}

        {/* PRÓXIMOS PASSOS E DIRETRIZES */}
        {data.nextSteps && data.nextSteps.length > 0 && (
          <div style={{ marginBottom: "28px" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a", marginBottom: "10px" }}>🎯 Próximos Passos & Recomendações Estratégicas</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {data.nextSteps.map((step, sIdx) => (
                <div key={sIdx} style={{ display: "flex", alignItems: "flex-start", gap: "10px", fontSize: "0.88rem", color: "#334155" }}>
                  <CheckCircle size={16} color="#10b981" style={{ marginTop: "3px", flexShrink: 0 }} />
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* RODAPÉ DO RELATÓRIO */}
        <div style={{ borderTop: "1px solid #e2e8f0", paddingTop: "16px", marginTop: "32px", display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#94a3b8" }}>
          <span>Gerado automaticamente por <strong>EverGreen AI Platform</strong></span>
          <span>{new Date().toLocaleDateString("pt-BR")} — Documento Oficial da Agência</span>
        </div>

        {/* CSS para Impressão limpa PDF */}
        <style>{`
          @media print {
            .no-print { display: none !important; }
            body { background: #ffffff !important; color: #000000 !important; }
            .printable-report-card {
              max-width: 100% !important;
              width: 100% !important;
              max-height: none !important;
              box-shadow: none !important;
              padding: 0 !important;
              margin: 0 !important;
              border: none !important;
            }
          }
        `}</style>
      </div>
    </div>
  );
}
