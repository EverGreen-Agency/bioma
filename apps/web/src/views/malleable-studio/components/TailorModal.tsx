import React, { useState } from "react";
import { X, Sparkles, Globe, RefreshCw, Check } from "lucide-react";
import type { MalleableClientPreset } from "../data/malleable-mock";
import { POPPI_PRESET, UNIVET_PRESET } from "../data/malleable-mock";

interface TailorModalProps {
  currentPreset: MalleableClientPreset;
  onApplyPreset: (newPreset: MalleableClientPreset) => void;
  onClose: () => void;
}

export const TailorModal: React.FC<TailorModalProps> = ({
  currentPreset,
  onApplyPreset,
  onClose,
}) => {
  const [urlInput, setUrlInput] = useState("");
  const [isExtracting, setIsExtracting] = useState(false);
  const [selectedQuick, setSelectedQuick] = useState(currentPreset.brand.id);

  const handleApplyQuick = (presetKey: "poppi" | "univet") => {
    setSelectedQuick(presetKey);
    const preset = presetKey === "poppi" ? POPPI_PRESET : UNIVET_PRESET;
    onApplyPreset(preset);
    onClose();
  };

  const handleExtractFromUrl = (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setIsExtracting(true);

    // Simulação do Thinker extraindo DNA da URL em tempo real
    setTimeout(() => {
      setIsExtracting(false);
      const isUnivet = urlInput.toLowerCase().includes("univet");
      const targetPreset = isUnivet ? UNIVET_PRESET : POPPI_PRESET;

      // Se for uma URL customizada diferente, criamos uma derivação maleável
      const customPreset: MalleableClientPreset = {
        ...targetPreset,
        brand: {
          ...targetPreset.brand,
          id: "custom-" + Date.now(),
          name: urlInput.replace(/^https?:\/\//, "").split(".")[0].toUpperCase() + " STUDIO",
          url: urlInput,
          tagline: "Custom Brand Engine · Tailored via CRAFT",
        },
      };

      onApplyPreset(customPreset);
      onClose();
    }, 1200);
  };

  return (
    <div className="craft-modal-overlay" onClick={onClose}>
      <div
        className="craft-modal-dialog"
        style={{ maxWidth: "680px" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="craft-modal-header">
          <div>
            <span
              style={{
                fontSize: "0.72rem",
                fontFamily: "var(--craft-font-mono)",
                color: "var(--craft-orange)",
                fontWeight: 900,
              }}
            >
              STAGE 5 OF 5 · TAILOR (CRAFT FRAMEWORK)
            </span>
            <h3 style={{ margin: "4px 0 0 0", fontSize: "1.15rem", fontWeight: 900 }}>
              Rebrand Studio para Qualquer Cliente
            </h3>
          </div>
          <button className="craft-btn craft-btn-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="craft-modal-body" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <p style={{ fontSize: "0.9rem", color: "var(--craft-ink-muted)", margin: 0, lineHeight: 1.5 }}>
            <strong>Software Maleável na prática:</strong> O motor de IA (The Thinker + The Designer + The Publisher) permanece idêntico. Ao inserir a URL de um novo cliente, o sistema reestiliza a interface, puxa fontes, paleta, concorrentes e fotos, transformando esta ferramenta em um produto sob medida.
          </p>

          {/* URL Input Form */}
          <form onSubmit={handleExtractFromUrl} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <label style={{ fontSize: "0.82rem", fontWeight: 800 }}>
              LINK INICIAL DA MARCA (URL DO SITE):
            </label>
            <div style={{ display: "flex", gap: "10px" }}>
              <div style={{ position: "relative", flex: 1 }}>
                <Globe
                  size={16}
                  style={{
                    position: "absolute",
                    left: "12px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "var(--craft-ink-muted)",
                  }}
                />
                <input
                  type="text"
                  placeholder="ex: drinkpoppi.com ou univetloupes.com"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 10px 10px 38px",
                    fontFamily: "var(--craft-font-sans)",
                    fontSize: "0.9rem",
                    border: "var(--craft-border)",
                    borderRadius: "2px",
                    background: "var(--craft-paper)",
                    color: "var(--craft-ink)",
                    boxSizing: "border-box",
                  }}
                />
              </div>
              <button
                type="submit"
                className="craft-btn craft-btn-primary"
                disabled={isExtracting}
                style={{ whiteSpace: "nowrap" }}
              >
                {isExtracting ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" /> Extraindo look...
                  </>
                ) : (
                  <>
                    <Sparkles size={14} /> Rebrand em 1 Clique
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Quick Presets */}
          <div>
            <div style={{ fontSize: "0.8rem", fontWeight: 800, marginBottom: "10px" }}>
              OU ALTERNE ENTRE CLIENTES PRÉ-CONFIGURADOS:
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              {/* Poppi Card */}
              <div
                className={`craft-card ${selectedQuick === "poppi" ? "selected" : ""}`}
                onClick={() => handleApplyQuick("poppi")}
                style={{
                  cursor: "pointer",
                  borderColor: selectedQuick === "poppi" ? "var(--craft-orange)" : "var(--craft-ink)",
                  borderWidth: selectedQuick === "poppi" ? "3px" : "2px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span style={{ fontWeight: 900, fontSize: "1rem" }}>POPPI SODA</span>
                  {selectedQuick === "poppi" && <Check size={16} color="var(--craft-orange)" />}
                </div>
                <div style={{ fontSize: "0.78rem", color: "var(--craft-ink-muted)", marginBottom: "8px" }}>
                  Bebida funcional pré-biótica · Pop neon, unhinged summer e estética vibrante.
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  {["#ff2a85", "#d4ff00", "#ff6b1a"].map((c) => (
                    <span
                      key={c}
                      style={{
                        width: "16px",
                        height: "16px",
                        borderRadius: "2px",
                        background: c,
                        border: "1px solid #1c1a16",
                      }}
                    />
                  ))}
                </div>
              </div>

              {/* Univet Card */}
              <div
                className={`craft-card ${selectedQuick === "univet" ? "selected" : ""}`}
                onClick={() => handleApplyQuick("univet")}
                style={{
                  cursor: "pointer",
                  borderColor: selectedQuick === "univet" ? "var(--craft-orange)" : "var(--craft-ink)",
                  borderWidth: selectedQuick === "univet" ? "3px" : "2px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span style={{ fontWeight: 900, fontSize: "1rem" }}>UNIVET LOUPES</span>
                  {selectedQuick === "univet" && <Check size={16} color="var(--craft-orange)" />}
                </div>
                <div style={{ fontSize: "0.78rem", color: "var(--craft-ink-muted)", marginBottom: "8px" }}>
                  Óptica cirúrgica e odontológica italiana · Ergonomia, titânio e alta precisão.
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  {["#0070f3", "#00dfd8", "#0b1320"].map((c) => (
                    <span
                      key={c}
                      style={{
                        width: "16px",
                        height: "16px",
                        borderRadius: "2px",
                        background: c,
                        border: "1px solid #1c1a16",
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
