import { useState, type FormEvent, type KeyboardEvent } from "react";
import {
  CHANNELS,
  CHANNEL_LABELS,
  NEXT_TRANSITION,
  STAGES,
  STAGE_DESCRIPTIONS,
  localInput,
  type Assignee,
  type Draft,
} from "./types";
import { PresenceMockupPreview } from "./PresenceMockupPreview";
import type {
  EditorialCalendarItemSummary as Item,
  OrganizationPerson,
  WorkspaceAssignmentSummary,
  WorkspaceSummary,
} from "../../lib/api";

interface PresenceDetailModalProps {
  item: Item | null;
  workspace: WorkspaceSummary;
  draft: Draft;
  onDraftChange: (draft: Draft) => void;
  onSave: (event: FormEvent) => Promise<void>;
  onChangeStage: (item: Item, stage: Item["stage"]) => Promise<void>;
  onOpenHandoff: (item: Item) => void;
  onClose: () => void;
  canManage: boolean;
  canApprove: boolean;
  isBusy: boolean;
  errorMessage: string;
  assignments?: WorkspaceAssignmentSummary[];
  people?: OrganizationPerson[];
}

export function PresenceDetailModal({
  item,
  workspace,
  draft,
  onDraftChange,
  onSave,
  onChangeStage,
  onOpenHandoff,
  onClose,
  canManage,
  canApprove,
  isBusy,
  errorMessage,
  assignments = [],
  people = [],
}: PresenceDetailModalProps) {
  const [activeTab, setActiveTab] = useState<"edit" | "preview">("edit");
  const [newTagInput, setNewTagInput] = useState("");
  const [mediaUrlInput, setMediaUrlInput] = useState("");

  const isLocked = item?.stage === "approved" || item?.stage === "scheduled" || item?.stage === "published";
  const canEdit = canManage && !isLocked;

  // Build unified list of eligible assignees
  const eligibleAssignees = buildAssigneesList(assignments, people);

  const tags = draft.metadata?.campaign_tags ?? [];

  function handleAddTag() {
    const clean = newTagInput.trim().replace(/^#/, "").toLowerCase();
    if (!clean || tags.includes(clean)) {
      setNewTagInput("");
      return;
    }
    onDraftChange({
      ...draft,
      metadata: {
        ...draft.metadata,
        campaign_tags: [...tags, clean],
      },
    });
    setNewTagInput("");
  }

  function handleTagKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      handleAddTag();
    }
  }

  function handleRemoveTag(tagToRemove: string) {
    onDraftChange({
      ...draft,
      metadata: {
        ...draft.metadata,
        campaign_tags: tags.filter((t) => t !== tagToRemove),
      },
    });
  }

  function handleAddMediaUrl() {
    const clean = mediaUrlInput.trim();
    if (!clean || draft.media_urls.includes(clean)) {
      setMediaUrlInput("");
      return;
    }
    onDraftChange({
      ...draft,
      media_urls: [...draft.media_urls, clean],
    });
    setMediaUrlInput("");
  }

  function handleRemoveMediaUrl(index: number) {
    onDraftChange({
      ...draft,
      media_urls: draft.media_urls.filter((_, i) => i !== index),
    });
  }

  function handleAssigneeChange(assigneeId: string) {
    if (!assigneeId) {
      onDraftChange({
        ...draft,
        metadata: {
          ...draft.metadata,
          assigned_to: null,
        },
      });
      return;
    }

    const found = eligibleAssignees.find((a) => a.id === assigneeId);
    if (found) {
      onDraftChange({
        ...draft,
        metadata: {
          ...draft.metadata,
          assigned_to: {
            id: found.id,
            name: found.name,
            email: found.email,
            role: found.role,
          },
        },
      });
    }
  }

  const selectedAssigneeId = draft.metadata?.assigned_to?.id ?? "";

  return (
    <div className="presence-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="presence-detail-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="presence-dialog-header">
          <div className="presence-dialog-title-area">
            <span className="presence-eyebrow">ESTEIRA EDITORIAL · BIOMA</span>
            <h2>{item ? "Detalhes da Peça Editorial" : "Nova Peça Editorial"}</h2>
            {item && (
              <div className="presence-stage-status-bar">
                <span className={`presence-stage-badge presence-stage-${item.stage}`}>
                  {STAGES[item.stage]}
                </span>
                <span className="presence-stage-desc">{STAGE_DESCRIPTIONS[item.stage]}</span>
              </div>
            )}
          </div>

          <div className="presence-dialog-header-actions">
            {/* Mobile Tab Toggle */}
            <div className="presence-mobile-tab-toggle">
              <button
                type="button"
                className={`presence-tab-btn ${activeTab === "edit" ? "active" : ""}`}
                onClick={() => setActiveTab("edit")}
              >
                ✏️ Editar
              </button>
              <button
                type="button"
                className={`presence-tab-btn ${activeTab === "preview" ? "active" : ""}`}
                onClick={() => setActiveTab("preview")}
              >
                👁️ Prévia ao Vivo
              </button>
            </div>

            <button type="button" className="presence-close-btn" onClick={onClose} aria-label="Fechar modal">
              ×
            </button>
          </div>
        </div>

        {/* Body (Split View) */}
        <div className={`presence-dialog-body tab-active-${activeTab}`}>
          {/* Left Column: Form */}
          <div className="presence-dialog-col-form">
            <form id="presence-piece-form" onSubmit={onSave} className="presence-form-fields">
              <label className="presence-field">
                <span className="presence-field-label">Título da Peça *</span>
                <input
                  type="text"
                  required
                  minLength={2}
                  maxLength={300}
                  placeholder="Ex: 5 Dicas para Alavancar as Vendas"
                  value={draft.title}
                  onChange={(e) => onDraftChange({ ...draft, title: e.target.value })}
                  disabled={!canEdit}
                  className="presence-input"
                />
              </label>

              <div className="presence-form-row">
                <label className="presence-field">
                  <span className="presence-field-label">Canal de Distribuição</span>
                  <select
                    value={draft.channel}
                    onChange={(e) =>
                      onDraftChange({ ...draft, channel: e.target.value as Item["channel"] })
                    }
                    disabled={!canEdit}
                    className="presence-select"
                  >
                    {CHANNELS.map((ch) => (
                      <option key={ch} value={ch}>
                        {CHANNEL_LABELS[ch]}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="presence-field">
                  <span className="presence-field-label">Formato do Conteúdo</span>
                  <select
                    value={draft.content_type}
                    onChange={(e) =>
                      onDraftChange({ ...draft, content_type: e.target.value as Item["content_type"] })
                    }
                    disabled={!canEdit}
                    className="presence-select"
                  >
                    <option value="social_post">Post Social</option>
                    <option value="image_ad">Imagem / Anúncio</option>
                    <option value="video_script">Roteiro de Vídeo</option>
                    <option value="article">Artigo / Blog</option>
                  </select>
                </label>
              </div>

              <div className="presence-form-row">
                <label className="presence-field">
                  <span className="presence-field-label">Data e Hora Programadas</span>
                  <input
                    type="datetime-local"
                    value={localInput(draft.scheduled_at)}
                    onChange={(e) =>
                      onDraftChange({
                        ...draft,
                        scheduled_at: e.target.value ? new Date(e.target.value).toISOString() : null,
                      })
                    }
                    disabled={!canEdit}
                    className="presence-input"
                  />
                  <small className="presence-field-hint">Horário no fuso local deste dispositivo.</small>
                </label>

                <label className="presence-field">
                  <span className="presence-field-label">Responsável da Equipe</span>
                  <select
                    value={selectedAssigneeId}
                    onChange={(e) => handleAssigneeChange(e.target.value)}
                    disabled={!canEdit}
                    className="presence-select"
                  >
                    <option value="">Nenhum responsável atribuído</option>
                    {eligibleAssignees.map((assignee) => (
                      <option key={assignee.id} value={assignee.id}>
                        {assignee.name} {assignee.role ? `(${assignee.role})` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {/* Campaign Tags Input */}
              <div className="presence-field">
                <span className="presence-field-label">Tags de Campanha</span>
                <div className="presence-tags-editor">
                  <div className="presence-tags-list">
                    {tags.map((tag) => (
                      <span key={tag} className="presence-tag-chip active">
                        #{tag}
                        {canEdit && (
                          <button
                            type="button"
                            onClick={() => handleRemoveTag(tag)}
                            aria-label={`Remover tag ${tag}`}
                            className="presence-tag-remove"
                          >
                            ×
                          </button>
                        )}
                      </span>
                    ))}
                  </div>
                  {canEdit && (
                    <div className="presence-tag-input-row">
                      <input
                        type="text"
                        placeholder="Adicionar tag (ex: lancamento, reels) e Enter"
                        value={newTagInput}
                        onChange={(e) => setNewTagInput(e.target.value)}
                        onKeyDown={handleTagKeyDown}
                        className="presence-tag-input"
                      />
                      <button
                        type="button"
                        onClick={handleAddTag}
                        className="presence-btn-tag-add"
                        disabled={!newTagInput.trim()}
                      >
                        + Adicionar
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Media URLs */}
              <div className="presence-field">
                <span className="presence-field-label">Imagens e Mídias Anexadas</span>
                {draft.media_urls.length > 0 && (
                  <ul className="presence-media-url-list">
                    {draft.media_urls.map((url, index) => (
                      <li key={url} className="presence-media-url-item">
                        <span className="presence-media-url-text" title={url}>
                          {url}
                        </span>
                        {canEdit && (
                          <button
                            type="button"
                            onClick={() => handleRemoveMediaUrl(index)}
                            className="presence-btn-media-remove"
                            aria-label="Remover mídia"
                          >
                            ×
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                {canEdit && (
                  <div className="presence-media-input-row">
                    <input
                      type="url"
                      placeholder="https://exemplo.com/imagem.png"
                      value={mediaUrlInput}
                      onChange={(e) => setMediaUrlInput(e.target.value)}
                      className="presence-input"
                    />
                    <button
                      type="button"
                      onClick={handleAddMediaUrl}
                      className="presence-btn-media-add"
                      disabled={!mediaUrlInput.trim()}
                    >
                      + Anexar URL
                    </button>
                  </div>
                )}
              </div>

              {/* Copy / Text */}
              <label className="presence-field">
                <span className="presence-field-label">Texto / Legenda da Peça</span>
                <textarea
                  rows={8}
                  maxLength={5000}
                  placeholder="Escreva aqui a cópia final do post, roteiro ou conteúdo..."
                  value={draft.post_text}
                  onChange={(e) => onDraftChange({ ...draft, post_text: e.target.value })}
                  disabled={!canEdit}
                  className="presence-textarea"
                />
                <span className="presence-char-count">{draft.post_text.length}/5000 caracteres</span>
              </label>

              {errorMessage && (
                <div className="presence-error-alert" role="alert">
                  ⚠️ {errorMessage}
                </div>
              )}

              {isLocked && (
                <div className="presence-locked-banner">
                  🔒 Esta peça está <strong>{STAGES[item.stage]}</strong>. Para fazer alterações no texto ou dados,
                  retorne o item para a etapa anterior na barra de ações abaixo.
                </div>
              )}
            </form>
          </div>

          {/* Right Column: Live Mockup */}
          <div className="presence-dialog-col-preview">
            <PresenceMockupPreview draft={draft} workspace={workspace} />
          </div>
        </div>

        {/* Footer Actions / Approval Pipeline */}
        <div className="presence-dialog-footer">
          <div className="presence-pipeline-actions">
            {item && (
              <>
                {/* Handoff Export Button */}
                {["approved", "scheduled", "published"].includes(item.stage) && (
                  <button
                    type="button"
                    className="presence-btn-export-handoff"
                    onClick={() => onOpenHandoff(item)}
                    title="Exportar pacote de publicação manual"
                  >
                    📦 Gerar Pacote Handoff
                  </button>
                )}

                {/* Advance stage button */}
                {NEXT_TRANSITION[item.stage] && (
                  <button
                    type="button"
                    className="presence-btn-advance"
                    disabled={
                      isBusy ||
                      (NEXT_TRANSITION[item.stage]?.stage === "approved" ? !canApprove : !canManage)
                    }
                    onClick={() => onChangeStage(item, NEXT_TRANSITION[item.stage]!.stage)}
                    title={
                      NEXT_TRANSITION[item.stage]?.stage === "approved" && !canApprove
                        ? "Apenas aprovadores ou administradores podem aprovar esta peça"
                        : NEXT_TRANSITION[item.stage]?.label
                    }
                  >
                    {isBusy ? "Processando…" : `➔ ${NEXT_TRANSITION[item.stage]?.label}`}
                  </button>
                )}

                {/* Return transitions */}
                {item.stage === "review" && canManage && (
                  <button
                    type="button"
                    className="presence-btn-revert"
                    disabled={isBusy}
                    onClick={() => onChangeStage(item, "production")}
                  >
                    ↩ Devolver à produção
                  </button>
                )}

                {item.stage === "approved" && canManage && (
                  <button
                    type="button"
                    className="presence-btn-revert"
                    disabled={isBusy}
                    onClick={() => onChangeStage(item, "review")}
                  >
                    ↩ Reabrir revisão
                  </button>
                )}

                {item.stage === "scheduled" && canManage && (
                  <button
                    type="button"
                    className="presence-btn-revert"
                    disabled={isBusy}
                    onClick={() => onChangeStage(item, "approved")}
                  >
                    ↩ Cancelar agendamento
                  </button>
                )}
              </>
            )}
          </div>

          <div className="presence-dialog-save-buttons">
            <button type="button" className="presence-btn-cancel" onClick={onClose}>
              Cancelar
            </button>
            {canEdit && (
              <button
                type="submit"
                form="presence-piece-form"
                className="presence-btn-save-primary"
                disabled={isBusy}
              >
                {isBusy ? "Salvando…" : item ? "Salvar Alterações" : "Criar Peça"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function buildAssigneesList(
  assignments: WorkspaceAssignmentSummary[],
  people: OrganizationPerson[]
): Assignee[] {
  const map = new Map<string, Assignee>();

  // Add from assignments
  for (const a of assignments) {
    if (a.user_id) {
      map.set(a.user_id, {
        id: a.user_id,
        name: a.assignee_name || "Membro da Equipe",
        email: a.assignee_email,
        role: a.role,
      });
    }
  }

  // Add from people (tenant members)
  for (const p of people) {
    if (!map.has(p.user_id)) {
      map.set(p.user_id, {
        id: p.user_id,
        name: p.display_name || p.email,
        email: p.email,
        role: p.role,
      });
    }
  }

  return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
}
