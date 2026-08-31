import { useEffect, useState } from "react";
import { Bot, CalendarClock, MessageCircle, Plus, X } from "lucide-react";
import { api, type CommercialActivity, type OpportunityDetail, type OpportunitySummary } from "../../../lib/api";

const STATUS_LABEL: Record<OpportunitySummary["status"], string> = {
  new: "Nova", qualifying: "Qualificando", qualified: "Qualificada", contacted: "Contato feito",
  meeting: "Em reunião", proposal: "Preparando proposta", proposal_generated: "Proposta gerada",
  negotiating: "Negociação", won: "Ganha", lost: "Perdida", rejected: "Rejeitada", archived: "Arquivada",
};

const ACTIVITY_LABEL: Record<CommercialActivity["activity_type"], string> = {
  captured: "Captura", status_changed: "Mudança de status", note: "Nota", follow_up_prepared: "Follow-up preparado",
  follow_up_sent: "Follow-up enviado", message_received: "Mensagem recebida", meeting_scheduled: "Reunião agendada",
  meeting_completed: "Reunião concluída", proposal_created: "Proposta criada", proposal_sent: "Proposta enviada",
  decision: "Decisão", won: "Ganha", lost: "Perdida",
};

export function OpportunityJourneyDrawer({ opportunityId, onClose, onChanged }: { opportunityId: string; onClose: () => void; onChanged: () => void }) {
  const [detail, setDetail] = useState<OpportunityDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [activityType, setActivityType] = useState<CommercialActivity["activity_type"]>("note");
  const [channel, setChannel] = useState("internal");
  const [activityTitle, setActivityTitle] = useState("");
  const [activityBody, setActivityBody] = useState("");
  const [nextActionAt, setNextActionAt] = useState("");

  const load = async () => {
    setError(null);
    try {
      const result = await api.opportunityDetail(opportunityId);
      setDetail(result);
      setNextActionAt(result.opportunity.next_action_at?.slice(0, 16) ?? "");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao carregar a oportunidade.");
    }
  };

  useEffect(() => { void load(); }, [opportunityId]);

  const update = async (payload: Parameters<typeof api.updateOpportunity>[1]) => {
    setBusy(true);
    try { setDetail(await api.updateOpportunity(opportunityId, payload)); onChanged(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Falha ao atualizar."); }
    finally { setBusy(false); }
  };

  const addActivity = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!activityTitle.trim()) return;
    setBusy(true);
    try {
      const direction = activityType === "message_received" ? "inbound" : activityType.includes("sent") ? "outbound" : "internal";
      setDetail(await api.addOpportunityActivity(opportunityId, {
        activity_type: activityType, direction, channel, title: activityTitle.trim(), body: activityBody.trim() || null,
        source_kind: "manual", metadata: {},
      }));
      setActivityTitle(""); setActivityBody(""); onChanged();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Falha ao registrar atividade."); }
    finally { setBusy(false); }
  };

  const draftFollowUp = async () => {
    if (!detail) return;
    setBusy(true); setError(null);
    try {
      const response = await api.runCopilot({
        surface: "workspace", workspace_id: detail.opportunity.workspace_id ?? undefined,
        opportunity_id: detail.opportunity.id, expert: "Propostas",
        message: "Gere uma mensagem curta de follow-up para WhatsApp com base na oportunidade e na linha do tempo. Não invente resposta do lead. Termine com uma pergunta simples que faça a conversa avançar.",
        allow_web_search: false, dry_run: true,
      });
      setActivityType("follow_up_prepared"); setChannel("whatsapp");
      setActivityTitle("Follow-up para WhatsApp"); setActivityBody(response.answer);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Não foi possível gerar o follow-up."); }
    finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ justifyContent: "flex-end" }}>
      <aside onClick={(event) => event.stopPropagation()} style={{ width: "min(720px, 94vw)", height: "100%", overflowY: "auto", background: "var(--bg)", borderLeft: "1px solid var(--border)", padding: 22 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <div><small>Continuidade comercial</small><h2 style={{ margin: "4px 0" }}>{detail?.opportunity.title ?? "Carregando..."}</h2></div>
          <button className="icon-button" onClick={onClose} type="button"><X size={18} /></button>
        </div>
        {error && <p className="error-state">{error}</p>}
        {detail && <>
          <div className="surface" style={{ padding: 14, marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <label>Status<select value={detail.opportunity.status} disabled={busy} onChange={(event) => update({ status: event.target.value as OpportunitySummary["status"] })}>{Object.entries(STATUS_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label>Próxima ação<div style={{ display: "flex", gap: 6 }}><input type="datetime-local" value={nextActionAt} onChange={(event) => setNextActionAt(event.target.value)} /><button className="mini-button" type="button" disabled={busy} onClick={() => update({ next_action_at: nextActionAt ? new Date(nextActionAt).toISOString() : null })}><CalendarClock size={14} /> Salvar</button></div></label>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 18 }}>
            <div><h3 style={{ margin: 0 }}>Linha do tempo</h3><small>Respostas, reuniões, follow-ups, propostas e decisões no mesmo contexto.</small></div>
            <button className="secondary-button" type="button" onClick={draftFollowUp} disabled={busy}><Bot size={15} /> Gerar follow-up</button>
          </div>
          <div style={{ display: "grid", gap: 8, marginTop: 10 }}>
            {detail.activities.map((activity) => <div className="work-row" key={activity.id} style={{ alignItems: "flex-start" }}><MessageCircle size={15} /><div><small>{ACTIVITY_LABEL[activity.activity_type]} · {new Date(activity.occurred_at).toLocaleString("pt-BR")}{activity.channel ? ` · ${activity.channel}` : ""}</small><strong>{activity.title}</strong>{activity.body && <p style={{ whiteSpace: "pre-wrap", margin: "4px 0 0" }}>{activity.body}</p>}</div></div>)}
          </div>

          <form onSubmit={addActivity} className="surface" style={{ display: "grid", gap: 8, marginTop: 16, padding: 14 }}>
            <h4 style={{ margin: 0 }}><Plus size={14} /> Registrar acontecimento</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <select value={activityType} onChange={(event) => setActivityType(event.target.value as CommercialActivity["activity_type"])}><option value="note">Nota interna</option><option value="message_received">Mensagem recebida</option><option value="follow_up_prepared">Follow-up preparado</option><option value="follow_up_sent">Follow-up enviado</option><option value="meeting_scheduled">Reunião agendada</option><option value="meeting_completed">Reunião concluída</option><option value="proposal_sent">Proposta enviada</option><option value="decision">Decisão</option></select>
              <select value={channel} onChange={(event) => setChannel(event.target.value)}><option value="internal">Interno</option><option value="whatsapp">WhatsApp</option><option value="email">E-mail</option><option value="meeting">Reunião</option><option value="platform">Plataforma</option></select>
            </div>
            <input value={activityTitle} onChange={(event) => setActivityTitle(event.target.value)} placeholder="Ex.: lead respondeu e pediu reunião" required />
            <textarea value={activityBody} onChange={(event) => setActivityBody(event.target.value)} rows={5} placeholder="Cole mensagens, resumo ou contexto. Revise qualquer texto gerado antes de enviar." />
            <div><button className="primary-button" type="submit" disabled={busy || !activityTitle.trim()}>Registrar na continuidade</button></div>
          </form>
        </>}
      </aside>
    </div>
  );
}
