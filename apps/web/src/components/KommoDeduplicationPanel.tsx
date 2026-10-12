import { useState } from "react";
import {
  Users,
  ShieldCheck,
  RefreshCw,
  GitMerge,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Phone,
  Mail,
  Building,
  Info,
} from "lucide-react";
import { SectionHeader } from "./shared";

interface DuplicateCluster {
  id: string;
  matchReason: string;
  similarity: number;
  status: "pending" | "merged" | "dismissed";
  canonical: {
    id: number;
    name: string;
    phone: string;
    email: string;
    specialty?: string;
    leadsCount: number;
    createdAt: string;
  };
  duplicates: Array<{
    id: number;
    name: string;
    phone: string;
    email: string;
    specialty?: string;
    leadsCount: number;
    createdAt: string;
  }>;
}

const INITIAL_CLUSTERS: DuplicateCluster[] = [
  {
    id: "cluster-01",
    matchReason: "Telefone canônico idêntico (formatação 8 vs 9 dígitos com +55)",
    similarity: 98,
    status: "pending",
    canonical: {
      id: 489201,
      name: "Dr. Roberto M. Silveira",
      phone: "+55 (11) 98765-4321",
      email: "roberto.silveira@endo-clinica.com.br",
      specialty: "Endodontia / Microscopia",
      leadsCount: 2,
      createdAt: "12/09/2026 14:20",
    },
    duplicates: [
      {
        id: 489912,
        name: "Roberto Silveira",
        phone: "(11) 8765-4321",
        email: "roberto.silveira@endo-clinica.com.br",
        specialty: "Odontologia",
        leadsCount: 1,
        createdAt: "28/09/2026 09:15",
      },
    ],
  },
  {
    id: "cluster-02",
    matchReason: "Mesmo e-mail e clínica médica com variação no nome do cirurgião",
    similarity: 92,
    status: "pending",
    canonical: {
      id: 471043,
      name: "Dra. Camila Vasconcelos Torres",
      phone: "+55 (21) 99123-8877",
      email: "camila.torres@cirurgiaplastica.med.br",
      specialty: "Cirurgia Plástica Reconstrutiva",
      leadsCount: 3,
      createdAt: "04/08/2026 11:05",
    },
    duplicates: [
      {
        id: 490104,
        name: "Camila Torres (Clínica)",
        phone: "+55 (21) 99123-8877",
        email: "camila.torres@cirurgiaplastica.med.br",
        specialty: "Médica",
        leadsCount: 1,
        createdAt: "01/10/2026 16:40",
      },
    ],
  },
  {
    id: "cluster-03",
    matchReason: "Telefone celular idêntico via canal WhatsApp Lead Ads",
    similarity: 95,
    status: "pending",
    canonical: {
      id: 462190,
      name: "Dr. Marcelo F. Guimarães",
      phone: "+55 (31) 98844-5511",
      email: "marcelo.guimaraes@cardio.med.br",
      specialty: "Cirurgia Cardiovascular",
      leadsCount: 1,
      createdAt: "15/07/2026 17:30",
    },
    duplicates: [
      {
        id: 490518,
        name: "Marcelo Guimaraes",
        phone: "31988445511",
        email: "m.guimaraes@cardio.med.br",
        specialty: "Cirurgião",
        leadsCount: 1,
        createdAt: "02/10/2026 10:12",
      },
    ],
  },
];

export function KommoDeduplicationPanel({ clientId }: { clientId: string }) {
  const [clusters, setClusters] = useState<DuplicateCluster[]>(INITIAL_CLUSTERS);
  const [isRunningScan, setIsRunningScan] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const pendingCount = clusters.filter((c) => c.status === "pending").length;
  const mergedCount = clusters.filter((c) => c.status === "merged").length;

  function handleRunDryRun() {
    setIsRunningScan(true);
    setScanMessage(null);
    setTimeout(() => {
      setIsRunningScan(false);
      setScanMessage(
        "Varredura em Modo Dry-Run concluída: 1.482 contatos analisados no Kommo. 3 clusters de duplicatas ativos identificados com segurança."
      );
    }, 900);
  }

  function handleMerge(clusterId: string) {
    setClusters((prev) =>
      prev.map((c) => (c.id === clusterId ? { ...c, status: "merged" } : c))
    );
  }

  function handleDismiss(clusterId: string) {
    setClusters((prev) =>
      prev.map((c) => (c.id === clusterId ? { ...c, status: "dismissed" } : c))
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Top Banner de Contexto Operacional */}
      <div
        style={{
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-light)",
          borderRadius: 8,
          padding: "16px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ color: "#3B82F6" }}>
              <ShieldCheck size={20} />
            </span>
            <h3 style={{ margin: 0, fontSize: 16, color: "var(--text)" }}>
              Higienização & Deduplicação de Contatos (Kommo CRM)
            </h3>
            <span className="demo-badge" style={{ background: "rgba(59, 130, 246, 0.15)", color: "#60A5FA" }}>
              Exclusivo Operação EG
            </span>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: "var(--text-muted)" }}>
            Varredura contínua de contatos criados por múltiplos pontos de entrada (Meta Ads, Site Univet e WhatsApp), unificando oportunidades no contato canônico.
          </p>
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button
            className="ghost-button"
            type="button"
            onClick={handleRunDryRun}
            disabled={isRunningScan}
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", fontSize: 13 }}
          >
            <RefreshCw size={14} className={isRunningScan ? "spin" : ""} />
            {isRunningScan ? "Analisando Kommo..." : "Executar Varredura (Dry-Run)"}
          </button>
        </div>
      </div>

      {scanMessage && (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: 6,
            fontSize: 13,
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: "rgba(59, 130, 246, 0.12)",
            color: "#60A5FA",
            border: "1px solid rgba(59, 130, 246, 0.25)",
          }}
        >
          <Info size={16} />
          {scanMessage}
        </div>
      )}

      {/* Métricas Rápidas do Motor */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14 }}>
        <div className="surface" style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>Contatos Analisados</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text)" }}>1.482</div>
          <small style={{ color: "var(--text-dim)", fontSize: 11 }}>Base Kommo Univet</small>
        </div>
        <div className="surface" style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>Clusters Suspeitos</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: pendingCount > 0 ? "#F59E0B" : "#10B981" }}>
            {pendingCount}
          </div>
          <small style={{ color: "var(--text-dim)", fontSize: 11 }}>Aguardando validação</small>
        </div>
        <div className="surface" style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>Unificações Realizadas</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#10B981" }}>{mergedCount}</div>
          <small style={{ color: "var(--text-dim)", fontSize: 11 }}>Sem perda de histórico de leads</small>
        </div>
        <div className="surface" style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>Prevenção Ativa (n8n)</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#3B82F6" }}>100%</div>
          <small style={{ color: "var(--text-dim)", fontSize: 11 }}>Gatekeeper de ingestão E.164</small>
        </div>
      </div>

      {/* Lista de Clusters de Duplicatas */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <h4 style={{ margin: 0, fontSize: 14, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Clusters Detectados ({clusters.length})
        </h4>

        {clusters.map((cluster) => {
          const isPending = cluster.status === "pending";
          const isMerged = cluster.status === "merged";
          const isDismissed = cluster.status === "dismissed";

          return (
            <article
              key={cluster.id}
              className="surface"
              style={{
                padding: 20,
                display: "flex",
                flexDirection: "column",
                gap: 16,
                borderLeft: `4px solid ${
                  isMerged ? "#10B981" : isDismissed ? "var(--border-light)" : "#F59E0B"
                }`,
                opacity: isDismissed ? 0.6 : 1,
              }}
            >
              {/* Header do Cluster */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span
                    className="demo-badge"
                    style={{
                      background: cluster.similarity >= 95 ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.15)",
                      color: cluster.similarity >= 95 ? "#10B981" : "#F59E0B",
                      fontWeight: 600,
                    }}
                  >
                    Similaridade {cluster.similarity}%
                  </span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
                    {cluster.matchReason}
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {isMerged && (
                    <span style={{ display: "flex", alignItems: "center", gap: 4, color: "#10B981", fontSize: 12, fontWeight: 600 }}>
                      <CheckCircle2 size={14} /> Unificado no Canônico
                    </span>
                  )}
                  {isDismissed && (
                    <span style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--text-dim)", fontSize: 12 }}>
                      <XCircle size={14} /> Ignorado (Falso Positivo)
                    </span>
                  )}
                  {isPending && (
                    <>
                      <button
                        className="primary-button"
                        type="button"
                        onClick={() => handleMerge(cluster.id)}
                        style={{ padding: "6px 12px", fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}
                      >
                        <GitMerge size={14} /> Unificar no Canônico
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => handleDismiss(cluster.id)}
                        style={{ padding: "6px 10px", fontSize: 12 }}
                      >
                        Ignorar
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Comparação: Canônico vs Duplicata(s) */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                  gap: 14,
                  background: "var(--bg-elevated)",
                  padding: 14,
                  borderRadius: 6,
                }}
              >
                {/* Lado A: Canônico */}
                <div style={{ borderRight: "1px solid var(--border-light)", paddingRight: 14 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                    <span className="demo-badge" style={{ background: "rgba(16, 185, 129, 0.2)", color: "#34D399" }}>
                      Canônico (Mais Antigo / Completo)
                    </span>
                    <span style={{ fontSize: 11, color: "var(--text-dim)" }}>ID #{cluster.canonical.id}</span>
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>
                    {cluster.canonical.name}
                  </div>
                  {cluster.canonical.specialty && (
                    <div style={{ fontSize: 12, color: "#38BDF8", marginBottom: 6 }}>
                      {cluster.canonical.specialty}
                    </div>
                  )}
                  <div style={{ fontSize: 12, color: "var(--text-muted)", display: "grid", gap: 4 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <Phone size={12} /> {cluster.canonical.phone}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <Mail size={12} /> {cluster.canonical.email}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 4 }}>
                      {cluster.canonical.leadsCount} lead(s) associado(s) · Criado em {cluster.canonical.createdAt}
                    </div>
                  </div>
                </div>

                {/* Lado B: Duplicatas */}
                <div>
                  {cluster.duplicates.map((dup) => (
                    <div key={dup.id}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                        <span className="demo-badge" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#F87171" }}>
                          Registro Duplicado a Mesclar
                        </span>
                        <span style={{ fontSize: 11, color: "var(--text-dim)" }}>ID #{dup.id}</span>
                      </div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>
                        {dup.name}
                      </div>
                      {dup.specialty && (
                        <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>
                          {dup.specialty}
                        </div>
                      )}
                      <div style={{ fontSize: 12, color: "var(--text-muted)", display: "grid", gap: 4 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <Phone size={12} /> {dup.phone}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <Mail size={12} /> {dup.email}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 4 }}>
                          {dup.leadsCount} lead(s) a reatribuir · Criado em {dup.createdAt}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
