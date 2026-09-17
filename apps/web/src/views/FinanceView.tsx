import { FormEvent, useMemo, useState } from "react";
import { CircleDollarSign, Cpu, Gauge, Plus, Trash2, WalletCards } from "lucide-react";
import { EmptyState, SectionHeader } from "../components/shared";
import {
  type FinancialRecordKind,
  type FinancialRecordPayload,
  type FinancialRecordStatus,
  type FinancialRecordSummary,
  type AiQuotaSnapshot,
} from "../lib/api";
import {
  useCurrentUser,
  useFinance,
  useCreateFinancialRecord,
  useUpdateFinancialRecord,
  useDeleteFinancialRecord,
  useAiFinOps,
  useCreateAiSubscription,
  useRecordAiQuota,
  useUpdateAiSubscription,
} from "../hooks/useBiomaApi";

const financialStatuses: Array<{ id: FinancialRecordStatus; label: string }> = [
  { id: "draft", label: "Rascunho" },
  { id: "open", label: "Aberto" },
  { id: "paid", label: "Pago" },
  { id: "overdue", label: "Vencido" },
  { id: "cancelled", label: "Cancelado" },
];

const emptyFinancial: FinancialRecordPayload = {
  kind: "invoice",
  title: "",
  amount: null,
  currency: "BRL",
  status: "open",
  due_at: "",
  notes: "",
};

function formatMoney(value: number | null, currency = "BRL") {
  if (value === null || Number.isNaN(value)) return "sem valor";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(value);
}

function toNullableNumber(value: string) {
  const normalized = value.replace(",", ".").trim();
  return normalized ? Number(normalized) : null;
}

function formatCents(value: number, currency = "BRL") {
  return formatMoney(value / 100, currency);
}

function formatQuota(quota: AiQuotaSnapshot | null) {
  if (!quota || quota.remaining_units === null) return "Saldo não exposto pelo provedor";
  return `${new Intl.NumberFormat("pt-BR").format(Number(quota.remaining_units))} ${quota.unit} restantes`;
}

export function FinanceView({ clientId }: { clientId: string }) {
  const { data: user } = useCurrentUser();

  const isEgAdmin = user?.organizations.some((organization: { slug: string; role: string }) => organization.slug === "eg" && organization.role === "eg_admin") ?? false;

  const { data: financeData, error: financeError } = useFinance(clientId);

  const createFinance = useCreateFinancialRecord();
  const updateFinance = useUpdateFinancialRecord();
  const deleteFinance = useDeleteFinancialRecord();
  const { data: aiFinOps, error: aiFinOpsError } = useAiFinOps(isEgAdmin);
  const createSubscription = useCreateAiSubscription();
  const updateSubscription = useUpdateAiSubscription();
  const recordQuota = useRecordAiQuota();

  const [financialDraft, setFinancialDraft] = useState<FinancialRecordPayload>(emptyFinancial);
  const [subscriptionDraft, setSubscriptionDraft] = useState({
    provider: "",
    product_name: "",
    amount: "",
    currency: "BRL",
    billing_cycle: "monthly" as "monthly" | "annual" | "custom",
    seats: "1",
  });
  const [quotaDraft, setQuotaDraft] = useState({
    subscriptionId: "",
    total: "",
    used: "",
    unit: "requisições",
    source: "configured" as AiQuotaSnapshot["source"],
  });

  const finance = financeData ?? [];

  const error = financeError?.message ?? aiFinOpsError?.message ?? "";

  const openAmount = useMemo(
    () => finance.reduce((total, record) => total + (record.status !== "paid" ? record.amount ?? 0 : 0), 0),
    [finance],
  );

  function handleCreateFinancial(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!financialDraft.title.trim()) return;
    createFinance.mutate({ clientId, payload: financialDraft }, {
      onSuccess: () => setFinancialDraft(emptyFinancial)
    });
  }

  function handleFinancialStatus(record: FinancialRecordSummary, status: FinancialRecordStatus) {
    updateFinance.mutate({ clientId, recordId: record.id, payload: { status } });
  }

  function handleDeleteFinancial(record: FinancialRecordSummary) {
    deleteFinance.mutate({ clientId, recordId: record.id });
  }

  function handleCreateSubscription(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amount = toNullableNumber(subscriptionDraft.amount);
    if (!subscriptionDraft.provider.trim() || !subscriptionDraft.product_name.trim() || amount === null) return;
    createSubscription.mutate(
      {
        provider: subscriptionDraft.provider.trim(),
        product_name: subscriptionDraft.product_name.trim(),
        amount_cents: Math.round(amount * 100),
        currency: subscriptionDraft.currency.toUpperCase(),
        billing_cycle: subscriptionDraft.billing_cycle,
        billing_cycle_months: subscriptionDraft.billing_cycle === "annual" ? 12 : 1,
        seats: Number(subscriptionDraft.seats) || 1,
      },
      {
        onSuccess: () => setSubscriptionDraft({
          provider: "",
          product_name: "",
          amount: "",
          currency: "BRL",
          billing_cycle: "monthly",
          seats: "1",
        }),
      },
    );
  }

  function handleRecordQuota(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!quotaDraft.subscriptionId || !quotaDraft.unit.trim()) return;
    recordQuota.mutate(
      {
        subscriptionId: quotaDraft.subscriptionId,
        payload: {
          total_units: quotaDraft.total.trim() || null,
          used_units: quotaDraft.used.trim() || null,
          unit: quotaDraft.unit.trim(),
          source: quotaDraft.source,
        },
      },
      {
        onSuccess: () => setQuotaDraft((current) => ({ ...current, total: "", used: "" })),
      },
    );
  }

  return (
    <div className="operations-layout fade-in">
      {error && <div className="notice error">{error}</div>}

      <div className="bento-grid">
        <article className="bento-card col-span-2">
          <div className="bento-header">
            <h3>Financeiro em Aberto</h3>
            <CircleDollarSign size={16} color="var(--mint)" />
          </div>
          <div className="bento-value" style={{ color: "var(--mint)" }}>
            {formatMoney(openAmount)}
          </div>
          <div className="bento-footer">
            {finance.filter((record) => record.status !== "paid").length} faturas aguardando pagamento
          </div>
        </article>
        {isEgAdmin && (aiFinOps?.totals_by_currency ?? []).map((total) => (
          <article className="bento-card col-span-2" key={total.currency}>
            <div className="bento-header">
              <h3>IA comprometida / mês · {total.currency}</h3>
              <Cpu size={16} />
            </div>
            <div className="bento-value">{formatCents(total.committed_monthly_cents, total.currency)}</div>
            <div className="bento-footer">
              Consumo medido no mês: {formatCents(total.measured_usage_cents, total.currency)}
            </div>
          </article>
        ))}
      </div>

      {isEgAdmin && (
        <div className="operations-grid" style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)" }}>
          <article className="surface">
            <SectionHeader eyebrow="FinOps IA" title="Assinaturas e cotas" icon={Gauge} />
            <div className="hub-block-list">
              {(aiFinOps?.subscriptions ?? []).length === 0 && (
                <EmptyState compact text="Nenhuma assinatura cadastrada. O sistema não inventa cotas a partir da autenticação." />
              )}
              {(aiFinOps?.subscriptions ?? []).map((subscription) => (
                <div className="work-row" key={subscription.id}>
                  <Cpu size={16} />
                  <div>
                    <strong>{subscription.provider} · {subscription.product_name}</strong>
                    <small>
                      {formatCents(subscription.monthly_equivalent_cents, subscription.currency)}/mês equivalente · {subscription.seats} assento(s)
                    </small>
                    <small>
                      {formatQuota(subscription.latest_quota)}
                      {subscription.latest_quota ? ` · fonte: ${subscription.latest_quota.source}` : ""}
                    </small>
                  </div>
                  <div className="row-tail">
                    <span className={`status-pill ${subscription.status}`}>{subscription.status}</span>
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={updateSubscription.isPending}
                      onClick={() => updateSubscription.mutate({
                        subscriptionId: subscription.id,
                        payload: { status: subscription.status === "active" ? "paused" : "active" },
                      })}
                    >
                      {subscription.status === "active" ? "Pausar" : "Ativar"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="surface">
            <SectionHeader eyebrow="Consumo observado" title="Uso de IA no mês" icon={Cpu} />
            <div className="hub-block-list">
              {(aiFinOps?.usage_current_month ?? []).length === 0 && (
                <EmptyState compact text="Nenhum consumo registrado neste mês." />
              )}
              {(aiFinOps?.usage_current_month ?? []).map((usage) => (
                <div className="work-row" key={`${usage.provider}:${usage.model}:${usage.source}:${usage.currency}`}>
                  <Gauge size={16} />
                  <div>
                    <strong>{usage.provider}{usage.model ? ` · ${usage.model}` : ""}</strong>
                    <small>{usage.events} execução(ões) · {usage.input_units + usage.output_units} {usage.source === "ai_content" ? "tokens" : "unidades"}</small>
                    <small>
                      Custo conhecido: {formatCents(usage.known_cost_cents, usage.currency)}
                      {usage.unknown_cost_events ? ` · ${usage.unknown_cost_events} sem preço configurado` : ""}
                    </small>
                  </div>
                </div>
              ))}
            </div>
          </article>
        </div>
      )}

      <div className="operations-grid" style={{ gridTemplateColumns: "1fr" }}>
        <article className="surface">
          <SectionHeader eyebrow="Financeiro" title="Contratos e faturas" icon={CircleDollarSign} />
          <div className="hub-block-list">
            {finance.length === 0 && <EmptyState compact text="Nenhum registro financeiro." />}
            {finance.map((record) => (
              <div className="work-row" key={record.id}>
                <WalletCards size={16} />
                <div>
                  <strong>{record.title}</strong>
                  <small>{record.kind === "contract" ? "Contrato" : "Fatura"} · {formatMoney(record.amount, record.currency)}</small>
                </div>
                <div className="row-tail">
                  {isEgAdmin ? (
                    <select
                      className="status-select"
                      value={record.status}
                      onChange={(event) => handleFinancialStatus(record, event.target.value as FinancialRecordStatus)}
                      disabled={updateFinance.isPending}
                    >
                      {financialStatuses.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span className={`status-pill ${record.status}`}>{record.status}</span>
                  )}
                  {isEgAdmin && (
                    <button className="icon-button danger" type="button" onClick={() => handleDeleteFinancial(record)}>
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </article>
      </div>

      {isEgAdmin && (
        <section className="admin-dock">
          <form className="dock-panel" onSubmit={handleCreateSubscription}>
            <SectionHeader eyebrow="FinOps IA" title="Cadastrar assinatura/API" icon={Cpu} />
            <div className="form-grid two">
              <label>
                Provedor
                <input
                  placeholder="Codex, Claude, AntiGravity..."
                  value={subscriptionDraft.provider}
                  onChange={(event) => setSubscriptionDraft({ ...subscriptionDraft, provider: event.target.value })}
                />
              </label>
              <label>
                Plano/produto
                <input
                  placeholder="Pro, Team, créditos API..."
                  value={subscriptionDraft.product_name}
                  onChange={(event) => setSubscriptionDraft({ ...subscriptionDraft, product_name: event.target.value })}
                />
              </label>
              <label>
                Valor do ciclo
                <input
                  inputMode="decimal"
                  placeholder="0,00"
                  value={subscriptionDraft.amount}
                  onChange={(event) => setSubscriptionDraft({ ...subscriptionDraft, amount: event.target.value })}
                />
              </label>
              <label>
                Moeda
                <input
                  maxLength={3}
                  value={subscriptionDraft.currency}
                  onChange={(event) => setSubscriptionDraft({ ...subscriptionDraft, currency: event.target.value })}
                />
              </label>
              <label>
                Ciclo
                <select
                  value={subscriptionDraft.billing_cycle}
                  onChange={(event) => setSubscriptionDraft({
                    ...subscriptionDraft,
                    billing_cycle: event.target.value as typeof subscriptionDraft.billing_cycle,
                  })}
                >
                  <option value="monthly">Mensal</option>
                  <option value="annual">Anual</option>
                  <option value="custom">Personalizado</option>
                </select>
              </label>
              <label>
                Assentos
                <input
                  inputMode="numeric"
                  value={subscriptionDraft.seats}
                  onChange={(event) => setSubscriptionDraft({ ...subscriptionDraft, seats: event.target.value })}
                />
              </label>
            </div>
            <button className="primary-button" type="submit" disabled={createSubscription.isPending}>
              <Plus size={16} />
              Cadastrar custo
            </button>
          </form>

          <form className="dock-panel" onSubmit={handleRecordQuota}>
            <SectionHeader eyebrow="Cota observada" title="Registrar saldo sem presumir API" icon={Gauge} />
            <div className="form-grid two">
              <label>
                Assinatura
                <select
                  value={quotaDraft.subscriptionId}
                  onChange={(event) => setQuotaDraft({ ...quotaDraft, subscriptionId: event.target.value })}
                >
                  <option value="">Selecione</option>
                  {(aiFinOps?.subscriptions ?? []).map((subscription) => (
                    <option key={subscription.id} value={subscription.id}>
                      {subscription.provider} · {subscription.product_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Fonte
                <select
                  value={quotaDraft.source}
                  onChange={(event) => setQuotaDraft({ ...quotaDraft, source: event.target.value as AiQuotaSnapshot["source"] })}
                >
                  <option value="api">API oficial</option>
                  <option value="configured">Limite configurado</option>
                  <option value="manual">Leitura manual</option>
                  <option value="unavailable">Indisponível</option>
                </select>
              </label>
              <label>
                Cota total
                <input value={quotaDraft.total} onChange={(event) => setQuotaDraft({ ...quotaDraft, total: event.target.value })} />
              </label>
              <label>
                Cota usada
                <input value={quotaDraft.used} onChange={(event) => setQuotaDraft({ ...quotaDraft, used: event.target.value })} />
              </label>
              <label>
                Unidade
                <input value={quotaDraft.unit} onChange={(event) => setQuotaDraft({ ...quotaDraft, unit: event.target.value })} />
              </label>
            </div>
            <button className="primary-button" type="submit" disabled={recordQuota.isPending || !quotaDraft.subscriptionId}>
              <Plus size={16} />
              Registrar medição
            </button>
          </form>

          <form className="dock-panel" onSubmit={handleCreateFinancial}>
            <SectionHeader eyebrow="Novo financeiro" title="Registrar contrato/fatura" icon={Plus} />
            <div className="form-grid two">
              <label>
                Tipo
                <select
                  value={financialDraft.kind}
                  onChange={(event) => setFinancialDraft({ ...financialDraft, kind: event.target.value as FinancialRecordKind })}
                >
                  <option value="contract">Contrato</option>
                  <option value="invoice">Fatura</option>
                </select>
              </label>
              <label>
                Status
                <select
                  value={financialDraft.status}
                  onChange={(event) => setFinancialDraft({ ...financialDraft, status: event.target.value as FinancialRecordStatus })}
                >
                  {financialStatuses.map((status) => (
                    <option key={status.id} value={status.id}>
                      {status.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Título
                <input value={financialDraft.title} onChange={(event) => setFinancialDraft({ ...financialDraft, title: event.target.value })} />
              </label>
              <label>
                Valor
                <input
                  value={financialDraft.amount ?? ""}
                  onChange={(event) => setFinancialDraft({ ...financialDraft, amount: toNullableNumber(event.target.value) })}
                />
              </label>
            </div>
            <label className="form-grid">
              Observação
              <textarea
                value={financialDraft.notes ?? ""}
                onChange={(event) => setFinancialDraft({ ...financialDraft, notes: event.target.value })}
              />
            </label>
            <button className="primary-button" type="submit" disabled={createFinance.isPending}>
              <Plus size={16} />
              Criar registro
            </button>
          </form>
        </section>
      )}
    </div>
  );
}
