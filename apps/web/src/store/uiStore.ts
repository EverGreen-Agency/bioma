import { create } from "zustand";
import {
  ArtifactPayload,
  ArtifactSummary,
  ClientPayload,
  DeliverablePayload,
} from "../lib/api";
import {
  emptyArtifactDraft,
  emptyClientDraft,
  emptyDeliverableDraft,
} from "../lib/app-config";

interface UiState {
  selectedClientId: string | null;
  setSelectedClientId: (id: string | null) => void;

  selectedArtifact: ArtifactSummary | null;
  setSelectedArtifact: (artifact: ArtifactSummary | null) => void;

  newClientDraft: ClientPayload;
  setNewClientDraft: (draft: ClientPayload) => void;

  clientDraft: ClientPayload;
  setClientDraft: (draft: ClientPayload) => void;

  artifactDraft: ArtifactPayload;
  setArtifactDraft: (draft: ArtifactPayload) => void;
  
  artifactEditDraft: ArtifactPayload;
  setArtifactEditDraft: (draft: ArtifactPayload) => void;

  deliverableDraft: DeliverablePayload;
  setDeliverableDraft: (draft: DeliverablePayload) => void;

  actionBusy: string | null;
  setActionBusy: (action: string | null) => void;

  dataError: string;
  setDataError: (error: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  selectedClientId: null,
  setSelectedClientId: (id) => set({ selectedClientId: id }),

  selectedArtifact: null,
  setSelectedArtifact: (artifact) => set({ selectedArtifact: artifact }),

  newClientDraft: emptyClientDraft,
  setNewClientDraft: (draft) => set({ newClientDraft: draft }),

  clientDraft: emptyClientDraft,
  setClientDraft: (draft) => set({ clientDraft: draft }),

  artifactDraft: emptyArtifactDraft,
  setArtifactDraft: (draft) => set({ artifactDraft: draft }),

  artifactEditDraft: emptyArtifactDraft,
  setArtifactEditDraft: (draft) => set({ artifactEditDraft: draft }),

  deliverableDraft: emptyDeliverableDraft,
  setDeliverableDraft: (draft) => set({ deliverableDraft: draft }),

  actionBusy: null,
  setActionBusy: (action) => set({ actionBusy: action }),

  dataError: "",
  setDataError: (error) => set({ dataError: error }),
}));
