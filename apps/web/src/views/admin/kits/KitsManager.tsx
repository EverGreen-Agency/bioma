import { useState, useEffect } from "react";
import { Package, Truck, Layers, Plus, Image as ImageIcon, Check, Sparkles, Box } from "lucide-react";
import {
  api,
  type KitDefinitionSummary,
  type KitPieceSummary,
  type KitShipmentSummary,
  type ClientSummary,
} from "../../../lib/api";

export function KitsManager() {
  const [activeTab, setActiveTab] = useState<"shipments" | "kits" | "pieces">("shipments");
  const [shipments, setShipments] = useState<KitShipmentSummary[]>([]);
  const [kits, setKits] = useState<KitDefinitionSummary[]>([]);
  const [pieces, setPieces] = useState<KitPieceSummary[]>([]);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Modais de Criação
  const [isCreatePieceOpen, setIsCreatePieceOpen] = useState(false);
  const [isCreateKitOpen, setIsCreateKitOpen] = useState(false);
  const [isCreateShipmentOpen, setIsCreateShipmentOpen] = useState(false);

  // Form State Peça
  const [pieceName, setPieceName] = useState("");
  const [pieceSupplier, setPieceSupplier] = useState("");
  const [pieceUnitCost, setPieceUnitCost] = useState("0");
  const [pieceStockQty, setPieceStockQty] = useState("10");
  const [pieceImageUrl, setPieceImageUrl] = useState("");

  // Form State Montagem de Kit
  const [kitName, setKitName] = useState("");
  const [kitLevel, setKitLevel] = useState("premium");
  const [kitDescription, setKitDescription] = useState("");
  const [selectedPieces, setSelectedPieces] = useState<Record<string, number>>({});

  // Form State Envio de Kit
  const [shipmentKitId, setShipmentKitId] = useState("");
  const [shipmentClientId, setShipmentClientId] = useState("");
  const [shipmentNotes, setShipmentNotes] = useState("");

  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [s, k, p, w] = await Promise.all([
        api.listKitShipments(),
        api.listKitDefinitions(),
        api.listKitPieces(),
        api.workspaces(),
      ]);
      const clientWorkspaces = w.filter((item: any) => item.kind === "client");
      setShipments(s);
      setKits(k);
      setPieces(p);
      setClients(clientWorkspaces.map((cw: any) => ({ id: cw.id, name: cw.name } as any)));

      if (k.length > 0 && !shipmentKitId) setShipmentKitId(k[0].id);
      if (clientWorkspaces.length > 0 && !shipmentClientId) setShipmentClientId(clientWorkspaces[0].id);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar logística de kits.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreatePiece(e: React.FormEvent) {
    e.preventDefault();
    if (!pieceName.trim()) return;
    setSubmitting(true);
    try {
      await api.createKitPiece({
        name: pieceName.trim(),
        supplier: pieceSupplier.trim() || undefined,
        unit_cost_cents: Math.round(parseFloat(pieceUnitCost || "0") * 100),
        stock_qty: parseInt(pieceStockQty || "0", 10),
        image_url: pieceImageUrl.trim() || undefined,
      });
      setPieceName("");
      setPieceSupplier("");
      setPieceUnitCost("0");
      setPieceStockQty("10");
      setPieceImageUrl("");
      setIsCreatePieceOpen(false);
      await loadData();
    } catch (err: any) {
      alert("Erro ao criar peça: " + (err.message || "Erro desconhecido"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreateKit(e: React.FormEvent) {
    e.preventDefault();
    if (!kitName.trim()) return;

    const piecesArray = Object.entries(selectedPieces)
      .filter(([_, qty]) => qty > 0)
      .map(([pieceId, qty]) => ({ piece_id: pieceId, quantity: qty }));

    if (piecesArray.length === 0) {
      alert("Selecione pelo menos 1 peça/item para compor o kit!");
      return;
    }

    setSubmitting(true);
    try {
      await api.createKitDefinition({
        name: kitName.trim(),
        level: kitLevel,
        description: kitDescription.trim() || undefined,
        pieces: piecesArray,
      });
      setKitName("");
      setKitDescription("");
      setSelectedPieces({});
      setIsCreateKitOpen(false);
      await loadData();
    } catch (err: any) {
      alert("Erro ao montar kit: " + (err.message || "Erro desconhecido"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreateShipment(e: React.FormEvent) {
    e.preventDefault();
    if (!shipmentKitId || !shipmentClientId) return;

    setSubmitting(true);
    try {
      await api.createKitShipment({
        kit_definition_id: shipmentKitId,
        client_id: shipmentClientId,
        notes: shipmentNotes.trim() || undefined,
      });
      setShipmentNotes("");
      setIsCreateShipmentOpen(false);
      await loadData();
    } catch (err: any) {
      alert("Erro ao registrar envio: " + (err.message || "Erro desconhecido"));
    } finally {
      setSubmitting(false);
    }
  }

  const togglePieceQuantity = (pieceId: string, delta: number) => {
    setSelectedPieces((prev) => {
      const current = prev[pieceId] || 0;
      const next = Math.max(0, current + delta);
      if (next === 0) {
        const copy = { ...prev };
        delete copy[pieceId];
        return copy;
      }
      return { ...prev, [pieceId]: next };
    });
  };

  return (
    <div style={{ padding: "24px", maxWidth: "1200px", margin: "0 auto", color: "var(--text)" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "10px", margin: 0 }}>
            <Package color="var(--brand-accent)" size={28} /> Logística & Envio de Kits
          </h1>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: "0.9rem" }}>
            Catálogo de peças com fotos, composição personalizada de kits e gestão de entregas.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          {activeTab === "pieces" && (
            <button className="primary-button" onClick={() => setIsCreatePieceOpen(true)} style={{ padding: "10px 18px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Plus size={18} /> Adicionar Nova Peça
            </button>
          )}
          {activeTab === "kits" && (
            <button className="primary-button" onClick={() => setIsCreateKitOpen(true)} style={{ padding: "10px 18px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Sparkles size={18} /> Montar Novo Kit
            </button>
          )}
          {activeTab === "shipments" && (
            <button className="primary-button" onClick={() => setIsCreateShipmentOpen(true)} style={{ padding: "10px 18px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Truck size={18} /> Registrar Novo Envio
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "12px", borderBottom: "1px solid var(--border)", marginBottom: "24px" }}>
        <button
          onClick={() => setActiveTab("shipments")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "shipments" ? "2px solid var(--brand-accent)" : "2px solid transparent",
            color: activeTab === "shipments" ? "var(--brand-accent)" : "var(--text-dim)",
            padding: "10px 16px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <Truck size={18} /> Registros de Envio ({shipments.length})
        </button>
        <button
          onClick={() => setActiveTab("kits")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "kits" ? "2px solid var(--brand-accent)" : "2px solid transparent",
            color: activeTab === "kits" ? "var(--brand-accent)" : "var(--text-dim)",
            padding: "10px 16px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <Box size={18} /> Kits Montados ({kits.length})
        </button>
        <button
          onClick={() => setActiveTab("pieces")}
          style={{
            background: "none",
            border: "none",
            borderBottom: activeTab === "pieces" ? "2px solid var(--brand-accent)" : "2px solid transparent",
            color: activeTab === "pieces" ? "var(--brand-accent)" : "var(--text-dim)",
            padding: "10px 16px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <Layers size={18} /> Estoque de Peças ({pieces.length})
        </button>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "8px", color: "#ef4444", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-dim)" }}>Carregando dados de logística...</div>
      ) : activeTab === "shipments" ? (
        /* ABA ENVIOS */
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {shipments.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", color: "var(--text-dim)" }}>
              Nenhum envio registrado até o momento. Clique em "Registrar Novo Envio" para enviar um Kit para um cliente.
            </div>
          ) : (
            shipments.map((s) => (
              <div
                key={s.id}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "12px",
                  padding: "20px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 600 }}>{s.kit_name}</h3>
                  <span style={{ fontSize: "0.85rem", color: "var(--text-dim)" }}>Cliente / Destinatário: <strong>{s.client_name}</strong></span>
                  {s.notes && <p style={{ margin: "4px 0 0", fontSize: "0.8rem", color: "var(--text-dim)" }}>Observações: {s.notes}</p>}
                </div>
                <span className={`status-pill ${s.status === "entregue" ? "approved" : "open"}`}>
                  Status: {s.status.toUpperCase()}
                </span>
              </div>
            ))
          )}
        </div>
      ) : activeTab === "kits" ? (
        /* ABA KITS CADASTRADOS (MONTADOS) */
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "20px" }}>
          {kits.length === 0 ? (
            <div style={{ gridColumn: "1 / -1", padding: "40px", textAlign: "center", background: "var(--surface)", borderRadius: "12px", color: "var(--text-dim)" }}>
              Nenhum kit montado até o momento. Clique no botão <strong>"✨ Montar Novo Kit"</strong> para combinar peças do estoque!
            </div>
          ) : (
            kits.map((k) => (
              <div key={k.id} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <span style={{ fontSize: "0.72rem", background: "var(--bg-inset)", color: "var(--brand-accent)", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}>
                      NÍVEL: {k.level.toUpperCase()}
                    </span>
                    <h3 style={{ margin: "6px 0 0", fontSize: "1.15rem", fontWeight: 600 }}>{k.name}</h3>
                  </div>
                  <span style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--brand-accent)" }}>
                    R$ {((k.total_cost_cents || 0) / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-dim)" }}>{k.description || "Sem descrição informada."}</p>

                {/* Composição das Peças com fotos miniatura */}
                <div style={{ background: "var(--bg-inset)", border: "1px solid var(--border)", borderRadius: "8px", padding: "12px" }}>
                  <strong style={{ fontSize: "0.78rem", color: "var(--text-dim)", display: "block", marginBottom: "8px" }}>
                    PEÇAS COMPONENTES DO KIT ({k.pieces.length}):
                  </strong>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {k.pieces.map((entry, idx) => {
                      const piece = pieces.find((p) => p.id === entry.piece_id);
                      return (
                        <div key={idx} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.82rem" }}>
                          {piece?.image_url ? (
                            <img src={piece.image_url} alt={piece.name} style={{ width: "24px", height: "24px", borderRadius: "4px", objectFit: "cover" }} />
                          ) : (
                            <Layers size={14} color="var(--brand-accent)" />
                          )}
                          <span style={{ flex: 1, color: "var(--text)" }}>{piece?.name || "Peça do Estoque"}</span>
                          <span style={{ fontWeight: 700, color: "var(--brand-accent)" }}>{entry.quantity}x</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        /* ABA ESTOQUE DE PEÇAS COM FOTO */
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "16px" }}>
          {pieces.map((p) => (
            <div key={p.id} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px", padding: "16px", display: "flex", gap: "14px", alignItems: "center" }}>
              {/* Foto do elemento/item */}
              <div style={{ width: "64px", height: "64px", borderRadius: "8px", background: "var(--bg-inset)", border: "1px solid var(--border)", overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                {p.image_url ? (
                  <img src={p.image_url} alt={p.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (
                  <ImageIcon size={24} color="var(--text-dim)" />
                )}
              </div>

              <div style={{ flex: 1, overflow: "hidden" }}>
                <strong style={{ fontSize: "0.95rem", display: "block", color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {p.name}
                </strong>
                <span style={{ fontSize: "0.8rem", color: "var(--text-dim)", display: "block", marginTop: "2px" }}>
                  Fornecedor: {p.supplier || "Não informado"}
                </span>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "6px" }}>
                  <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--brand-accent)" }}>
                    R$ {((p.unit_cost_cents || 0) / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                  </span>
                  <span style={{ fontSize: "0.78rem", background: "var(--bg-inset)", padding: "2px 6px", borderRadius: "4px", color: "var(--text-dim)" }}>
                    Estoque: {p.stock_qty} un
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Adicionar Nova Peça (Com Foto) */}
      {isCreatePieceOpen && (
        <div className="drawer-overlay" onClick={() => setIsCreatePieceOpen(false)}>
          <div className="drawer-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "500px", padding: "24px" }}>
            <h2 style={{ marginTop: 0, fontSize: "1.2rem", display: "flex", alignItems: "center", gap: "8px" }}>
              <Plus color="var(--brand-accent)" size={22} /> Adicionar Nova Peça / Item com Foto
            </h2>
            <form onSubmit={handleCreatePiece} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Nome do Item / Brinde *
                <input required type="text" value={pieceName} onChange={(e) => setPieceName(e.target.value)} placeholder="Ex: Caneca Térmica EG 500ml" style={{ padding: "10px", borderRadius: "6px" }} />
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                URL da Foto / Imagem (Link de Imagem pública)
                <input type="url" value={pieceImageUrl} onChange={(e) => setPieceImageUrl(e.target.value)} placeholder="Ex: https://dominio.com/foto-caneca.jpg" style={{ padding: "10px", borderRadius: "6px" }} />
              </label>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                  Custo Unitário (R$)
                  <input type="number" step="0.01" value={pieceUnitCost} onChange={(e) => setPieceUnitCost(e.target.value)} placeholder="Ex: 35.50" style={{ padding: "10px", borderRadius: "6px" }} />
                </label>

                <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                  Qtd em Estoque
                  <input type="number" value={pieceStockQty} onChange={(e) => setPieceStockQty(e.target.value)} placeholder="Ex: 50" style={{ padding: "10px", borderRadius: "6px" }} />
                </label>
              </div>

              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Fornecedor / Fabricante
                <input type="text" value={pieceSupplier} onChange={(e) => setPieceSupplier(e.target.value)} placeholder="Ex: Gráfica Express Ltda" style={{ padding: "10px", borderRadius: "6px" }} />
              </label>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button type="button" className="secondary-button" onClick={() => setIsCreatePieceOpen(false)}>Cancelar</button>
                <button type="submit" className="primary-button" disabled={submitting}>
                  {submitting ? "Salvando..." : "Salvar Peça"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Montar Kit (Composição de Peças) */}
      {isCreateKitOpen && (
        <div className="drawer-overlay" onClick={() => setIsCreateKitOpen(false)}>
          <div className="drawer-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "600px", padding: "24px" }}>
            <h2 style={{ marginTop: 0, fontSize: "1.2rem", display: "flex", alignItems: "center", gap: "8px" }}>
              <Sparkles color="var(--brand-accent)" size={22} /> Montar Novo Kit Corporativo
            </h2>
            <form onSubmit={handleCreateKit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Nome do Kit *
                <input required type="text" value={kitName} onChange={(e) => setKitName(e.target.value)} placeholder="Ex: Kit Onboarding Executive 2026" style={{ padding: "10px", borderRadius: "6px" }} />
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Nível / Categoria do Kit
                <select value={kitLevel} onChange={(e) => setKitLevel(e.target.value)} style={{ padding: "10px", borderRadius: "6px" }}>
                  <option value="starter">Starter (Básico)</option>
                  <option value="premium">Premium (Intermediário)</option>
                  <option value="executive">Executive (VIP / C-Level)</option>
                </select>
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Descrição / Objetivo do Kit
                <textarea rows={2} value={kitDescription} onChange={(e) => setKitDescription(e.target.value)} placeholder="Descreva para qual momento este kit é enviado..." style={{ padding: "10px", borderRadius: "6px", fontFamily: "inherit" }} />
              </label>

              {/* Seletor de Peças */}
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                <label style={{ fontSize: "0.85rem", color: "var(--brand-accent)", fontWeight: 600 }}>
                  Selecione as Peças que compõem este Kit:
                </label>
                <div style={{ maxHeight: "200px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px", background: "var(--bg-inset)", padding: "10px", borderRadius: "8px", border: "1px solid var(--border)" }}>
                  {pieces.map((p) => {
                    const qty = selectedPieces[p.id] || 0;
                    return (
                      <div key={p.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px", background: "var(--surface)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          {p.image_url ? (
                            <img src={p.image_url} alt={p.name} style={{ width: "32px", height: "32px", borderRadius: "4px", objectFit: "cover" }} />
                          ) : (
                            <Layers size={18} color="var(--brand-accent)" />
                          )}
                          <div>
                            <strong style={{ fontSize: "0.85rem", display: "block" }}>{p.name}</strong>
                            <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>R$ {((p.unit_cost_cents || 0) / 100).toFixed(2)}</span>
                          </div>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <button type="button" onClick={() => togglePieceQuantity(p.id, -1)} style={{ width: "26px", height: "26px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--bg-inset)", cursor: "pointer", color: "var(--text)" }}>-</button>
                          <span style={{ fontWeight: 700, minWidth: "20px", textAlign: "center" }}>{qty}</span>
                          <button type="button" onClick={() => togglePieceQuantity(p.id, 1)} style={{ width: "26px", height: "26px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--bg-inset)", cursor: "pointer", color: "var(--text)" }}>+</button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button type="button" className="secondary-button" onClick={() => setIsCreateKitOpen(false)}>Cancelar</button>
                <button type="submit" className="primary-button" disabled={submitting}>
                  {submitting ? "Montando..." : "Montar & Salvar Kit"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Registrar Novo Envio */}
      {isCreateShipmentOpen && (
        <div className="drawer-overlay" onClick={() => setIsCreateShipmentOpen(false)}>
          <div className="drawer-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "500px", padding: "24px" }}>
            <h2 style={{ marginTop: 0, fontSize: "1.2rem", display: "flex", alignItems: "center", gap: "8px" }}>
              <Truck color="var(--brand-accent)" size={22} /> Registrar Novo Envio de Kit
            </h2>
            <form onSubmit={handleCreateShipment} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Selecione o Kit *
                <select value={shipmentKitId} onChange={(e) => setShipmentKitId(e.target.value)} style={{ padding: "10px", borderRadius: "6px" }}>
                  {kits.map((k) => (
                    <option key={k.id} value={k.id}>{k.name} ({k.level.toUpperCase()})</option>
                  ))}
                </select>
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Selecione o Cliente / Destinatário *
                <select value={shipmentClientId} onChange={(e) => setShipmentClientId(e.target.value)} style={{ padding: "10px", borderRadius: "6px" }}>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.85rem" }}>
                Observações de Envio / Rastreio
                <textarea rows={3} value={shipmentNotes} onChange={(e) => setShipmentNotes(e.target.value)} placeholder="Ex: Código de rastreio Correios / endereço de entrega..." style={{ padding: "10px", borderRadius: "6px", fontFamily: "inherit" }} />
              </label>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button type="button" className="secondary-button" onClick={() => setIsCreateShipmentOpen(false)}>Cancelar</button>
                <button type="submit" className="primary-button" disabled={submitting}>
                  {submitting ? "Registrando..." : "Registrar Envio"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
