import { useState, useMemo, useEffect } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Award,
  CheckCircle2,
  ChevronRight,
  Compass,
  DollarSign,
  Gift,
  HelpCircle,
  History,
  Layers,
  Lightbulb,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
  UserCheck,
  Zap,
} from "lucide-react";
import {
  BoardVerdict,
  OfferBonus,
  OfferEvaluatePayload,
  OfferStack,
  OfferValidationResponse,
  ProblemSolutionItem,
  RiskReversalGuarantee,
  ValueEquation,
} from "../../lib/api";
import {
  useOfferValidations,
  useCreateOfferValidation,
  useDeleteOfferValidation,
} from "../../hooks/useBiomaApi";

interface OfferLabStudioProps {
  workspaceId?: string | null;
  workspaceName?: string;
}

const DEFAULT_VALUE_EQUATION: ValueEquation = {
  dream_outcome: 8.5,
  perceived_likelihood: 8.0,
  time_delay: 2.5,
  effort_and_sacrifice: 2.5,
  notes: {},
};

const DEFAULT_STACK: OfferStack = {
  core_offer_name: "Consultoria de Aceleração Comercial",
  core_offer_description: "Estruturação completa de canais de aquisição e funil de vendas.",
  magic_name: "Sprint de Tração B2B em 30 Dias",
  bonuses: [
    {
      title: "Playbook Pronto de Fechamento de Vendas",
      description: "Scripts exatos e objeções contornadas para o time comercial fechar mais rápido.",
      perceived_value_cents: 250_000,
      delivery_cost: "low",
    },
    {
      title: "Setup de Dashboard Executivo de Métricas",
      description: "Painel em tempo real integrado às contas de anúncios sem custo de licença.",
      perceived_value_cents: 180_000,
      delivery_cost: "low",
    },
  ],
  guarantee: {
    type: "conditional",
    title: "Garantia Condicionada de Resultado",
    terms: "Se em 60 dias o número acordado de leads qualificados não for gerado e você cumpriu sua parte, trabalhamos sem custos até atingir a meta.",
    conditions: [
      "Comparecer aos alinhamentos quinzenais",
      "Validar criativos e copys em até 48 horas",
    ],
  },
  scarcity_urgency: "Turma limitada a 4 novas contas por ciclo para dedicação do time sênior.",
};

function formatMoneyCents(cents: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(cents / 100);
}

function calculateScore(ve: ValueEquation): number {
  const num = ve.dream_outcome * ve.perceived_likelihood;
  const den = Math.max(1, ve.time_delay * ve.effort_and_sacrifice);
  return Math.round((num / den) * 100) / 100;
}

export function OfferLabStudio({ workspaceId, workspaceName }: OfferLabStudioProps) {
  const { data: savedValidations = [], isLoading: loadingList, refetch } = useOfferValidations(workspaceId);
  const createMutation = useCreateOfferValidation();
  const deleteMutation = useDeleteOfferValidation();

  // Estados locais da oferta em análise
  const [title, setTitle] = useState("Nova Arquitetura de Oferta");
  const [productOrService, setProductOrService] = useState("Consultoria de Performance e Tráfego");
  const [targetAudience, setTargetAudience] = useState("Empresas B2B e Varejistas High-Ticket");
  const [currentPriceCents, setCurrentPriceCents] = useState(500_000); // R$ 5.000,00
  const [valueEquation, setValueEquation] = useState<ValueEquation>(DEFAULT_VALUE_EQUATION);
  const [problems, setProblems] = useState<ProblemSolutionItem[]>([
    {
      obstacle: "Falta de tempo e conhecimento interno para gerenciar mídia",
      timing: "before_buying",
      solution: "Operação 100% Done-For-You com gestores dedicados",
      delivery_vehicle: "done_for_you",
      cost_to_deliver: "low",
      perceived_value: "high",
    },
    {
      obstacle: "Medo de investir dinheiro e não obter leads reais",
      timing: "during_delivery",
      solution: "Garantia contratual de leads mínimos qualificados",
      delivery_vehicle: "checklist",
      cost_to_deliver: "low",
      perceived_value: "extreme",
    },
  ]);
  const [stack, setStack] = useState<OfferStack>(DEFAULT_STACK);
  const [activeTab, setActiveTab] = useState<"equation" | "problems" | "stack" | "board">("equation");
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // Novo item de obstáculo
  const [newObstacle, setNewObstacle] = useState("");
  const [newSolution, setNewSolution] = useState("");
  const [newVehicle, setNewVehicle] = useState<ProblemSolutionItem["delivery_vehicle"]>("done_for_you");

  // Novo bônus
  const [newBonusTitle, setNewBonusTitle] = useState("");
  const [newBonusDesc, setNewBonusDesc] = useState("");
  const [newBonusValue, setNewBonusValue] = useState(150_000);

  const score = useMemo(() => calculateScore(valueEquation), [valueEquation]);

  const scoreBadge = useMemo(() => {
    if (score >= 12.0) {
      return {
        label: "Grand Slam Offer ($100M)",
        color: "var(--accent-mint, #3AC97B)",
        bg: "rgba(58, 201, 123, 0.15)",
        desc: "Oferta de alto valor percebido e atrito quase nulo. Alta propensão de compra imediata.",
      };
    }
    if (score >= 5.0) {
      return {
        label: "Oferta Viável / Razoável",
        color: "#FFB800",
        bg: "rgba(255, 184, 0, 0.15)",
        desc: "A oferta é boa, mas o comprador ainda sente esforço ou incerteza. Adicione garantias e encurte o tempo até a 1ª vitória.",
      };
    }
    return {
      label: "Oferta Frágil / Alta Resistência",
      color: "#FF5C5C",
      bg: "rgba(255, 92, 92, 0.15)",
      desc: "Demora excessiva ou esforço muito alto exigido do cliente. Perigo de rejeição comercial.",
    };
  }, [score]);

  const handleAddProblem = () => {
    if (!newObstacle || !newSolution) return;
    setProblems((prev) => [
      ...prev,
      {
        obstacle: newObstacle,
        timing: "before_buying",
        solution: newSolution,
        delivery_vehicle: newVehicle,
        cost_to_deliver: "low",
        perceived_value: "high",
      },
    ]);
    setNewObstacle("");
    setNewSolution("");
  };

  const handleAddBonus = () => {
    if (!newBonusTitle) return;
    setStack((prev) => ({
      ...prev,
      bonuses: [
        ...prev.bonuses,
        {
          title: newBonusTitle,
          description: newBonusDesc,
          perceived_value_cents: newBonusValue,
          delivery_cost: "low",
        },
      ],
    }));
    setNewBonusTitle("");
    setNewBonusDesc("");
  };

  const handleSaveValidation = () => {
    if (!workspaceId) return;
    setSaveSuccessMsg(null);
    const payload: OfferEvaluatePayload = {
      title,
      product_or_service: productOrService,
      target_audience: targetAudience,
      current_price_cents: currentPriceCents,
      value_equation: valueEquation,
      problems_and_solutions: problems,
      offer_stack: stack,
    };

    createMutation.mutate(
      { workspaceId, payload },
      {
        onSuccess: () => {
          setSaveSuccessMsg("Oferta avaliada e salva com sucesso!");
          setTimeout(() => setSaveSuccessMsg(null), 4000);
          void refetch();
        },
      }
    );
  };

  const handleLoadValidation = (item: OfferValidationResponse) => {
    setTitle(item.title);
    setProductOrService(item.product_or_service);
    setTargetAudience(item.target_audience);
    setCurrentPriceCents(item.current_price_cents);
    setValueEquation(item.value_equation);
    setProblems(item.problems_and_solutions);
    setStack(item.offer_stack);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, padding: "8px 0" }}>
      {/* Header com indicador de metodologia */}
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        padding: "16px 20px",
        background: "var(--card-bg, #09231b15)",
        border: "1px solid var(--border-color, #ffffff15)",
        borderRadius: 12,
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Award size={22} color="var(--accent-mint, #3AC97B)" />
            <h3 style={{ margin: 0, fontSize: "1.15rem", fontWeight: 600 }}>
              Laboratório de Ofertas & Validação (Metodologia Founder)
            </h3>
          </div>
          <p style={{ margin: "4px 0 0 0", fontSize: "0.85rem", color: "var(--text-muted, #a0aec0)" }}>
            Framework de Alex Hormozi ($100M Offers), Peter Thiel e Steve Jobs para arquitetar ofertas irrecusáveis.
          </p>
        </div>

        {workspaceId && (
          <button
            type="button"
            className="primary-button"
            onClick={handleSaveValidation}
            disabled={createMutation.isPending}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            {createMutation.isPending ? <RefreshCw className="animate-spin" size={15} /> : <Save size={15} />}
            Salvar Oferta
          </button>
        )}
      </div>

      {saveSuccessMsg && (
        <div style={{
          padding: "10px 16px",
          background: "rgba(58, 201, 123, 0.15)",
          border: "1px solid #3AC97B",
          borderRadius: 8,
          color: "#3AC97B",
          fontSize: "0.88rem",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}>
          <CheckCircle2 size={16} />
          {saveSuccessMsg}
        </div>
      )}

      {/* Tabs de Navegação */}
      <div style={{ display: "flex", gap: 8, borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: 8 }}>
        <button
          type="button"
          onClick={() => setActiveTab("equation")}
          style={{
            padding: "8px 16px",
            background: activeTab === "equation" ? "rgba(58, 201, 123, 0.15)" : "transparent",
            color: activeTab === "equation" ? "var(--accent-mint, #3AC97B)" : "inherit",
            border: "none",
            borderRadius: 6,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <Zap size={16} /> 1. Equação de Valor Hormozi
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("problems")}
          style={{
            padding: "8px 16px",
            background: activeTab === "problems" ? "rgba(58, 201, 123, 0.15)" : "transparent",
            color: activeTab === "problems" ? "var(--accent-mint, #3AC97B)" : "inherit",
            border: "none",
            borderRadius: 6,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <Layers size={16} /> 2. Mapeador de Objeções & Soluções
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("stack")}
          style={{
            padding: "8px 16px",
            background: activeTab === "stack" ? "rgba(58, 201, 123, 0.15)" : "transparent",
            color: activeTab === "stack" ? "var(--accent-mint, #3AC97B)" : "inherit",
            border: "none",
            borderRadius: 6,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <Gift size={16} /> 3. Grand Slam Offer Stack
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("board")}
          style={{
            padding: "8px 16px",
            background: activeTab === "board" ? "rgba(58, 201, 123, 0.15)" : "transparent",
            color: activeTab === "board" ? "var(--accent-mint, #3AC97B)" : "inherit",
            border: "none",
            borderRadius: 6,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <UserCheck size={16} /> 4. Parecer do Conselho (Board)
        </button>
      </div>

      {/* Conteúdo da Tab 1: Equação de Valor */}
      {activeTab === "equation" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* Parâmetros e Sliders */}
          <div style={{
            background: "var(--card-bg, rgba(9, 35, 27, 0.3))",
            padding: 20,
            borderRadius: 12,
            border: "1px solid var(--border-color, rgba(255,255,255,0.08))",
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}>
            <h4 style={{ margin: "0 0 4px 0", fontSize: "1rem", fontWeight: 600 }}>Parâmetros da Oferta</h4>

            <div>
              <label style={{ fontSize: "0.82rem", color: "var(--text-muted, #a0aec0)" }}>Nome da Solução</label>
              <input
                type="text"
                value={productOrService}
                onChange={(e) => setProductOrService(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", borderRadius: 6, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "inherit" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "0.82rem", color: "var(--text-muted, #a0aec0)" }}>Público-Alvo / Avatar</label>
              <input
                type="text"
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", borderRadius: 6, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "inherit" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "0.82rem", color: "var(--text-muted, #a0aec0)" }}>Preço Desejado de Venda</label>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input
                  type="range"
                  min={100_00}
                  max={50_000_00}
                  step={100_00}
                  value={currentPriceCents}
                  onChange={(e) => setCurrentPriceCents(Number(e.target.value))}
                  style={{ flex: 1, accentColor: "var(--accent-mint, #3AC97B)" }}
                />
                <strong>{formatMoneyCents(currentPriceCents)}</strong>
              </div>
            </div>

            <div style={{ borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: 14, display: "flex", flexDirection: "column", gap: 14 }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--accent-mint, #3AC97B)" }}>
                Os 4 Pilares da Equação de Valor
              </span>

              {/* Dream Outcome */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", marginBottom: 4 }}>
                  <span>1. Resultado dos Sonhos (Dream Outcome):</span>
                  <strong>{valueEquation.dream_outcome} / 10</strong>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  step={0.5}
                  value={valueEquation.dream_outcome}
                  onChange={(e) => setValueEquation((v) => ({ ...v, dream_outcome: Number(e.target.value) }))}
                  style={{ width: "100%", accentColor: "var(--accent-mint, #3AC97B)" }}
                />
              </div>

              {/* Perceived Likelihood */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", marginBottom: 4 }}>
                  <span>2. Certeza Percebida de Atingimento:</span>
                  <strong>{valueEquation.perceived_likelihood} / 10</strong>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  step={0.5}
                  value={valueEquation.perceived_likelihood}
                  onChange={(e) => setValueEquation((v) => ({ ...v, perceived_likelihood: Number(e.target.value) }))}
                  style={{ width: "100%", accentColor: "var(--accent-mint, #3AC97B)" }}
                />
              </div>

              {/* Time Delay (Invertido) */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", marginBottom: 4 }}>
                  <span>3. Tempo até o 1º Resultado (Demora):</span>
                  <strong>{valueEquation.time_delay} / 10 (Menor é melhor)</strong>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  step={0.5}
                  value={valueEquation.time_delay}
                  onChange={(e) => setValueEquation((v) => ({ ...v, time_delay: Number(e.target.value) }))}
                  style={{ width: "100%", accentColor: "#FFB800" }}
                />
              </div>

              {/* Effort & Sacrifice (Invertido) */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", marginBottom: 4 }}>
                  <span>4. Esforço e Sacrifício Exigidos:</span>
                  <strong>{valueEquation.effort_and_sacrifice} / 10 (Menor é melhor)</strong>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  step={0.5}
                  value={valueEquation.effort_and_sacrifice}
                  onChange={(e) => setValueEquation((v) => ({ ...v, effort_and_sacrifice: Number(e.target.value) }))}
                  style={{ width: "100%", accentColor: "#FF5C5C" }}
                />
              </div>
            </div>
          </div>

          {/* Painel de Diagnóstico do Score */}
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{
              background: "linear-gradient(135deg, rgba(9, 35, 27, 0.8) 0%, rgba(20, 60, 48, 0.5) 100%)",
              border: `1px solid ${scoreBadge.color}`,
              borderRadius: 12,
              padding: 24,
            }}>
              <span style={{ fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--accent-mint, #3AC97B)", fontWeight: 600 }}>
                Score da Equação de Valor
              </span>
              <div style={{ fontSize: "3rem", fontWeight: 700, margin: "6px 0", color: scoreBadge.color }}>
                {score.toFixed(1)}
                <span style={{ fontSize: "1rem", color: "var(--text-muted, #a0aec0)", marginLeft: 8 }}>/ 100</span>
              </div>
              <div style={{
                display: "inline-block",
                padding: "4px 12px",
                borderRadius: 20,
                background: scoreBadge.bg,
                color: scoreBadge.color,
                fontWeight: 600,
                fontSize: "0.82rem",
                marginBottom: 12,
              }}>
                {scoreBadge.label}
              </div>
              <p style={{ margin: 0, fontSize: "0.88rem", color: "#FFF4C7", lineHeight: 1.5 }}>
                {scoreBadge.desc}
              </p>
            </div>

            <div style={{
              background: "var(--card-bg, rgba(9, 35, 27, 0.25))",
              padding: 20,
              borderRadius: 12,
              border: "1px solid rgba(255,255,255,0.08)",
              fontSize: "0.85rem",
              lineHeight: 1.6,
            }}>
              <h5 style={{ margin: "0 0 10px 0", fontSize: "0.95rem", fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                <Lightbulb size={18} color="var(--accent-mint, #3AC97B)" />
                Como Transformar em uma $100M Offer:
              </h5>
              <ul style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 8 }}>
                <li><strong>Aumente a certeza percebida:</strong> Inclua garantias onde o cliente só paga se houver resultado ou onde ele recebe suporte estendido sem custo.</li>
                <li><strong>Reduza o delay do primeiro valor:</strong> Entregue uma auditoria, setup ou vitória rápida nas primeiras 48 horas de contrato.</li>
                <li><strong>Elimine esforço:</strong> Troque treinamentos longos por entregáveis "Feitos Para Você" (Done-For-You) ou automações prontas.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Conteúdo da Tab 2: Objeções & Soluções */}
      {activeTab === "problems" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{
            background: "var(--card-bg, rgba(9, 35, 27, 0.3))",
            padding: 20,
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.08)",
          }}>
            <h4 style={{ margin: "0 0 8px 0", fontSize: "1rem", fontWeight: 600 }}>
              Lista de Atritos e Objeções (Problemas → Soluções)
            </h4>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted, #a0aec0)", margin: "0 0 16px 0" }}>
              Mapeie cada dúvida ou dificuldade do cliente antes, durante e após a compra, e transforme em uma entrega de valor.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 20 }}>
              {problems.map((p, idx) => (
                <div
                  key={idx}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr auto",
                    gap: 12,
                    padding: "12px 16px",
                    background: "rgba(0,0,0,0.2)",
                    borderRadius: 8,
                    alignItems: "center",
                  }}
                >
                  <div>
                    <span style={{ fontSize: "0.72rem", color: "#FF5C5C", textTransform: "uppercase", fontWeight: 600 }}>Objeção / Atrito</span>
                    <div style={{ fontSize: "0.85rem", fontWeight: 500 }}>{p.obstacle}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.72rem", color: "var(--accent-mint, #3AC97B)", textTransform: "uppercase", fontWeight: 600 }}>Solução / Bônus</span>
                    <div style={{ fontSize: "0.85rem" }}>{p.solution}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setProblems((prev) => prev.filter((_, i) => i !== idx))}
                    style={{ background: "transparent", border: "none", color: "#FF5C5C", cursor: "pointer", padding: 6 }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>

            {/* Adicionar novo obstáculo */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr auto auto",
              gap: 12,
              padding: 16,
              background: "rgba(255,255,255,0.03)",
              borderRadius: 8,
              alignItems: "flex-end",
            }}>
              <div>
                <label style={{ fontSize: "0.8rem", color: "var(--text-muted, #a0aec0)" }}>Qual obstáculo o cliente enfrenta?</label>
                <input
                  type="text"
                  placeholder="Ex: Não tenho ninguém para produzir os vídeos"
                  value={newObstacle}
                  onChange={(e) => setNewObstacle(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", borderRadius: 6, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "inherit", fontSize: "0.82rem" }}
                />
              </div>
              <div>
                <label style={{ fontSize: "0.8rem", color: "var(--text-muted, #a0aec0)" }}>Como nossa oferta resolve isso?</label>
                <input
                  type="text"
                  placeholder="Ex: Fornecemos roteiros validados e edição completa inclusa"
                  value={newSolution}
                  onChange={(e) => setNewSolution(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", borderRadius: 6, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "inherit", fontSize: "0.82rem" }}
                />
              </div>
              <div>
                <label style={{ fontSize: "0.8rem", color: "var(--text-muted, #a0aec0)" }}>Veículo de Entrega</label>
                <select
                  value={newVehicle}
                  onChange={(e) => setNewVehicle(e.target.value as any)}
                  style={{ width: "100%", padding: "7px 10px", borderRadius: 6, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "inherit", fontSize: "0.82rem" }}
                >
                  <option value="done_for_you">Done-For-You (Nós fazemos)</option>
                  <option value="software">Software / Ferramenta</option>
                  <option value="checklist">Checklist / Template</option>
                  <option value="1_on_1">Mentoria 1-on-1</option>
                </select>
              </div>
              <button
                type="button"
                className="secondary-button"
                onClick={handleAddProblem}
                style={{ padding: "7px 16px", display: "flex", alignItems: "center", gap: 6 }}
              >
                <Plus size={16} /> Adicionar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Conteúdo da Tab 3: Grand Slam Offer Stack */}
      {activeTab === "stack" && (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            {/* Naming MAGIC */}
            <div style={{ background: "var(--card-bg, rgba(9, 35, 27, 0.3))", padding: 18, borderRadius: 10, border: "1px solid rgba(255,255,255,0.08)" }}>
              <label style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--accent-mint, #3AC97B)" }}>
                Nome Magnético da Oferta (Fórmula M.A.G.I.C)
              </label>
              <span style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted, #a0aec0)", marginBottom: 8 }}>
                Magnet + Avatar + Goal + Interval + Container (ex: "Sprint de Tração B2B em 30 Dias")
              </span>
              <input
                type="text"
                value={stack.magic_name}
                onChange={(e) => setStack((s) => ({ ...s, magic_name: e.target.value }))}
                style={{ width: "100%", padding: "8px 12px", borderRadius: 6, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "inherit", fontWeight: 600 }}
              />
            </div>

            {/* Bônus Estratégicos */}
            <div style={{ background: "var(--card-bg, rgba(9, 35, 27, 0.3))", padding: 18, borderRadius: 10, border: "1px solid rgba(255,255,255,0.08)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h5 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600 }}>Bônus Estratégicos de Alto Valor</h5>
                <span style={{ fontSize: "0.78rem", color: "var(--text-muted, #a0aec0)" }}>Custo de entrega baixo para você, valor percebido alto para o cliente</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 14 }}>
                {stack.bonuses.map((b, idx) => (
                  <div key={idx} style={{ padding: 12, background: "rgba(0,0,0,0.25)", borderRadius: 6, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <strong style={{ fontSize: "0.88rem", display: "block" }}>{b.title}</strong>
                      <span style={{ fontSize: "0.78rem", color: "var(--text-muted, #a0aec0)" }}>{b.description}</span>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span style={{ color: "var(--accent-mint, #3AC97B)", fontWeight: 600 }}>{formatMoneyCents(b.perceived_value_cents)}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Inserir Bônus */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 10 }}>
                <input
                  type="text"
                  placeholder="Título do bônus..."
                  value={newBonusTitle}
                  onChange={(e) => setNewBonusTitle(e.target.value)}
                  style={{ padding: "6px 10px", borderRadius: 6, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "inherit", fontSize: "0.82rem" }}
                />
                <input
                  type="text"
                  placeholder="Descrição da transformação..."
                  value={newBonusDesc}
                  onChange={(e) => setNewBonusDesc(e.target.value)}
                  style={{ padding: "6px 10px", borderRadius: 6, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "inherit", fontSize: "0.82rem" }}
                />
                <button type="button" className="secondary-button" onClick={handleAddBonus} style={{ padding: "6px 14px" }}>
                  Adicionar
                </button>
              </div>
            </div>

            {/* Garantia de Reversão de Risco */}
            <div style={{ background: "var(--card-bg, rgba(9, 35, 27, 0.3))", padding: 18, borderRadius: 10, border: "1px solid rgba(255,255,255,0.08)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <h5 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                  <ShieldCheck size={18} color="var(--accent-mint, #3AC97B)" />
                  Garantia de Reversão de Risco (Risk Reversal)
                </h5>
                <select
                  value={stack.guarantee.type}
                  onChange={(e) => setStack((s) => ({ ...s, guarantee: { ...s.guarantee, type: e.target.value as any } }))}
                  style={{ padding: "4px 8px", borderRadius: 6, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "inherit", fontSize: "0.8rem" }}
                >
                  <option value="conditional">Garantia Condicional (Mais Segura)</option>
                  <option value="unconditional">Garantia Incondicional (100% Risco Nosso)</option>
                  <option value="performance_based">Baseada em Performance</option>
                </select>
              </div>

              <textarea
                rows={3}
                value={stack.guarantee.terms}
                onChange={(e) => setStack((s) => ({ ...s, guarantee: { ...s.guarantee, terms: e.target.value } }))}
                style={{ width: "100%", padding: "8px 12px", borderRadius: 6, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "inherit", fontSize: "0.85rem", lineHeight: 1.4 }}
              />
            </div>
          </div>

          {/* Card Resumo do Stack */}
          <div style={{
            background: "linear-gradient(135deg, rgba(9, 35, 27, 0.8) 0%, rgba(20, 60, 48, 0.5) 100%)",
            border: "1px solid var(--accent-mint, #3AC97B)",
            borderRadius: 12,
            padding: 24,
            display: "flex",
            flexDirection: "column",
            gap: 16,
            height: "fit-content",
          }}>
            <span style={{ fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--accent-mint, #3AC97B)", fontWeight: 600 }}>
              Visualização da Oferta Irrecusável
            </span>
            <h3 style={{ margin: 0, fontSize: "1.3rem", color: "#FFF4C7" }}>
              {stack.magic_name || productOrService}
            </h3>

            <div style={{ borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: 12 }}>
              <div style={{ fontSize: "0.82rem", color: "var(--text-muted, #a0aec0)" }}>Investimento Base</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{formatMoneyCents(currentPriceCents)}</div>
            </div>

            {stack.bonuses.length > 0 && (
              <div>
                <span style={{ fontSize: "0.8rem", color: "var(--accent-mint, #3AC97B)", fontWeight: 600 }}>
                  Bônus Inclusos Sem Custo Adicional:
                </span>
                <ul style={{ margin: "6px 0 0 0", paddingLeft: 18, fontSize: "0.82rem" }}>
                  {stack.bonuses.map((b, i) => (
                    <li key={i} style={{ marginBottom: 4 }}>
                      {b.title} (Avaliado em {formatMoneyCents(b.perceived_value_cents)})
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div style={{ padding: 12, background: "rgba(0,0,0,0.3)", borderRadius: 8, fontSize: "0.82rem" }}>
              <span style={{ color: "var(--accent-mint, #3AC97B)", fontWeight: 600, display: "block", marginBottom: 2 }}>
                {stack.guarantee.title}:
              </span>
              <p style={{ margin: 0, color: "#FFF4C7" }}>{stack.guarantee.terms}</p>
            </div>
          </div>
        </div>
      )}

      {/* Conteúdo da Tab 4: Parecer do Conselho (Board) */}
      {activeTab === "board" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
          {/* Card Hormozi */}
          <div style={{ background: "rgba(9, 35, 27, 0.4)", border: "1px solid var(--accent-mint, #3AC97B)", padding: 20, borderRadius: 12, display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong style={{ color: "var(--accent-mint, #3AC97B)" }}>Alex Hormozi</strong>
              <span style={{ fontSize: "0.75rem", background: "rgba(58, 201, 123, 0.2)", padding: "2px 8px", borderRadius: 10 }}>$100M Offers</span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "#FFF4C7", lineHeight: 1.5, margin: 0 }}>
              "Se você precisa ser um gênio em vendas para fechar, sua oferta é ruim. Faça uma oferta tão boa que as pessoas se sintam burras em dizer não."
            </p>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted, #a0aec0)" }}>
              {valueEquation.effort_and_sacrifice > 5
                ? "Atenção: O esforço percebido está muito alto. Entregue mais 'Done-For-You'."
                : "Excelente redução de esforço do cliente."}
            </div>
          </div>

          {/* Card Peter Thiel */}
          <div style={{ background: "rgba(9, 35, 27, 0.4)", border: "1px solid #4285F4", padding: 20, borderRadius: 12, display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong style={{ color: "#4285F4" }}>Peter Thiel</strong>
              <span style={{ fontSize: "0.75rem", background: "rgba(66, 133, 244, 0.2)", padding: "2px 8px", borderRadius: 10 }}>Zero to One</span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "#FFF4C7", lineHeight: 1.5, margin: 0 }}>
              "A competição é para perdedores. Se você quer criar e capturar valor duradouro, você precisa construir um monopólio no seu nicho."
            </p>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted, #a0aec0)" }}>
              Busque um segredo específico do mercado para que ninguém consiga comparar seu preço com agências tradicionais.
            </div>
          </div>

          {/* Card Steve Jobs */}
          <div style={{ background: "rgba(9, 35, 27, 0.4)", border: "1px solid #FFF4C7", padding: 20, borderRadius: 12, display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong style={{ color: "#FFF4C7" }}>Steve Jobs</strong>
              <span style={{ fontSize: "0.75rem", background: "rgba(255, 244, 199, 0.2)", padding: "2px 8px", borderRadius: 10 }}>Foco & Simplicidade</span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "#FFF4C7", lineHeight: 1.5, margin: 0 }}>
              "Foco não é dizer sim para o que você quer fazer, é dizer não para centenas de outras boas ideias para manter o produto simples e perfeito."
            </p>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted, #a0aec0)" }}>
              {valueEquation.time_delay > 4
                ? "Time-to-Value lento. Entregue um primeiro resultado visível nas primeiras 48h."
                : "Bom tempo de ativação inicial."}
            </div>
          </div>
        </div>
      )}

      {/* Histórico de Validações Salvas no Workspace */}
      {workspaceId && savedValidations.length > 0 && (
        <div style={{
          background: "var(--card-bg, rgba(9, 35, 27, 0.2))",
          padding: 20,
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <History size={18} color="var(--accent-mint, #3AC97B)" />
            <h5 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 600 }}>Ofertas Validadas Anteriores</h5>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12 }}>
            {savedValidations.map((item) => (
              <div
                key={item.id}
                style={{
                  padding: 14,
                  background: "rgba(0,0,0,0.25)",
                  borderRadius: 8,
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                  border: "1px solid rgba(255,255,255,0.05)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <strong style={{ fontSize: "0.9rem" }}>{item.title}</strong>
                  <span style={{ fontSize: "0.78rem", color: "var(--accent-mint, #3AC97B)", fontWeight: 600 }}>
                    Score: {item.value_score}
                  </span>
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted, #a0aec0)" }}>
                  {item.product_or_service} ({formatMoneyCents(item.current_price_cents)})
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
                  <button
                    type="button"
                    onClick={() => handleLoadValidation(item)}
                    style={{ background: "transparent", border: "none", color: "var(--accent-mint, #3AC97B)", fontSize: "0.8rem", cursor: "pointer", padding: 0, fontWeight: 500 }}
                  >
                    Carregar no Estúdio →
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate({ workspaceId, validationId: item.id })}
                    style={{ background: "transparent", border: "none", color: "#FF5C5C", cursor: "pointer", padding: 4 }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
