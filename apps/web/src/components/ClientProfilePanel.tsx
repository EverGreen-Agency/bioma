import { useEffect, useMemo, useState } from "react";
import { Building2, CheckCircle2, Save } from "lucide-react";

import { CopilotWorkbench } from "./CopilotWorkbench";
import { useCurrentUser } from "../hooks/useBiomaApi";
import { api, type ClientProfile, type ClientProfilePayload } from "../lib/api";


const MANAGE_ROLES = new Set(["platform_admin", "tenant_admin", "workspace_manager", "operator"]);

const SECTIONS: Array<{
  key: string;
  title: string;
  fields: Array<{ key: keyof ClientProfilePayload; label: string; multiline?: boolean; type?: "email" | "url" }>;
}> = [
  {
    key: "basic",
    title: "Informações básicas",
    fields: [
      { key: "sector", label: "Setor de atuação" },
      { key: "primary_offer", label: "Produto/serviço principal" },
      { key: "initial_objective", label: "Objetivo inicial", multiline: true },
    ],
  },
  {
    key: "contact",
    title: "Informações de contato",
    fields: [
      { key: "contact_email", label: "E-mail", type: "email" },
      { key: "contact_phone", label: "Telefone" },
      { key: "website", label: "Website", type: "url" },
      { key: "business_address", label: "Endereço" },
    ],
  },
  {
    key: "business",
    title: "Detalhes do negócio",
    fields: [
      { key: "business_details", label: "Negócio e contexto", multiline: true },
      { key: "target_audience", label: "Público-alvo", multiline: true },
      { key: "competitors", label: "Concorrentes", multiline: true },
    ],
  },
  {
    key: "marketing",
    title: "Marketing e objetivos",
    fields: [
      { key: "marketing_objectives", label: "Objetivos de marketing", multiline: true },
      { key: "marketing_history", label: "Histórico e estratégias", multiline: true },
      { key: "challenges_opportunities", label: "Desafios e oportunidades", multiline: true },
    ],
  },
  {
    key: "preferences",
    title: "Recursos e preferências",
    fields: [
      { key: "resources_budget", label: "Recursos e orçamento", multiline: true },
      { key: "tone_of_voice", label: "Tom de voz desejado", multiline: true },
      { key: "preferences_restrictions", label: "Preferências e restrições", multiline: true },
    ],
  },
];

function profilePayload(profile: ClientProfile): ClientProfilePayload {
  return Object.fromEntries(
    Object.keys(profile).filter((key) => !["workspace_id", "completion_percentage", "sections", "updated_at"].includes(key))
      .map((key) => [key, profile[key as keyof ClientProfile] ?? ""]),
  ) as ClientProfilePayload;
}

export function ClientProfilePanel({
  workspaceId,
  accessRole,
  organizationId,
}: {
  workspaceId: string;
  accessRole: string;
  // Feature flags são por organização, não por workspace — daí a prop extra.
  organizationId?: string;
}) {
  const [profile, setProfile] = useState<ClientProfile | null>(null);
  const [draft, setDraft] = useState<ClientProfilePayload>({});
  const [busy, setBusy] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canManage = MANAGE_ROLES.has(accessRole);
  const { data: currentUser } = useCurrentUser();
  const isEgAdmin = currentUser?.organizations.some((org: { role: string }) => org.role === "eg_admin") ?? false;

  useEffect(() => {
    let cancelled = false;
    setBusy(true);
    setError(null);
    void api.clientProfile(workspaceId)
      .then((result) => {
        if (cancelled) return;
        setProfile(result);
        setDraft(profilePayload(result));
      })
      .catch((caught: Error) => !cancelled && setError(caught.message))
      .finally(() => !cancelled && setBusy(false));
    return () => { cancelled = true; };
  }, [workspaceId]);

  const sections = useMemo(() => new Map(profile?.sections.map((item) => [item.key, item]) ?? []), [profile]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const result = await api.updateClientProfile(workspaceId, draft);
      setProfile(result);
      setDraft(profilePayload(result));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível salvar o contexto.");
    } finally {
      setSaving(false);
    }
  }

  if (busy) return <section className="surface"><p>Carregando contexto do cliente...</p></section>;
  if (!profile) return <section className="surface"><p>{error ?? "Contexto indisponível."}</p></section>;

  return (
    <section className="client-profile-panel">
      <header className="panel-heading">
        <div>
          <p className="eyebrow">Onboarding estruturado</p>
          <h2><Building2 size={18} /> Contexto do cliente</h2>
          <p>Informações que qualificam briefing, planejamento e execução. Credenciais continuam exclusivamente no cofre.</p>
        </div>
        <div className="client-profile-progress" title="Completude do contexto">
          <strong>{profile.completion_percentage}%</strong>
          <span>preenchido</span>
        </div>
      </header>

      {!canManage && <div className="notice">A equipe responsável atualiza este contexto; você pode consultar as informações compartilhadas.</div>}
      {error && <div className="notice error" role="alert">{error}</div>}

      <div className="client-profile-sections">
        {SECTIONS.map((section) => {
          const progress = sections.get(section.key);
          return (
            <section className="surface client-profile-section" key={section.key}>
              <header>
                <div>
                  <h3>{section.title}</h3>
                  <small>{progress?.filled ?? 0} de {progress?.total ?? section.fields.length} campos preenchidos</small>
                </div>
                <span>{progress?.percentage ?? 0}%</span>
              </header>
              <div className="form-grid two">
                {section.fields.map((field) => (
                  <label key={field.key} className={field.multiline ? "span-two" : ""}>
                    {field.label}
                    {field.multiline ? (
                      <textarea
                        rows={4}
                        readOnly={!canManage}
                        value={draft[field.key] ?? ""}
                        onChange={(event) => setDraft((current) => ({ ...current, [field.key]: event.target.value }))}
                      />
                    ) : (
                      <input
                        type={field.type ?? "text"}
                        readOnly={!canManage}
                        value={draft[field.key] ?? ""}
                        onChange={(event) => setDraft((current) => ({ ...current, [field.key]: event.target.value }))}
                      />
                    )}
                  </label>
                ))}
              </div>
            </section>
          );
        })}
      </div>

      {canManage && (
        <footer className="client-profile-actions">
          <button className="primary-button" type="button" disabled={saving} onClick={() => void save()}>
            {saving ? <span className="spin">◌</span> : <Save size={16} />}
            {saving ? "Salvando..." : "Salvar contexto"}
          </button>
          {profile.updated_at && <small><CheckCircle2 size={14} /> Atualizado em {new Date(profile.updated_at).toLocaleString("pt-BR")}</small>}
        </footer>
      )}

      {/* EG-only mesmo dentro do hub do cliente: o usuário do cliente nunca vê
          a memória, os planos nem a fila de melhorias sobre ele. */}
      {isEgAdmin && (
        <div style={{ marginTop: 16 }}>
          <CopilotWorkbench
            workspaceId={workspaceId}
            organizationId={organizationId}
            title="Copiloto neste cliente"
            description="O que o copiloto sabe, o que ele já aprendeu a fazer e o que está esperando sua revisão."
          />
        </div>
      )}
    </section>
  );
}
