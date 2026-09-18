import React, { useState } from "react";
import { Globe, Palette, Type, Image as ImageIcon, RefreshCw, Upload, Check, Copy } from "lucide-react";
import type { BrandDna } from "../data/malleable-mock";

interface BrandDnaViewProps {
  brand: BrandDna;
  onUpdateBrand: (updated: BrandDna) => void;
}

export const BrandDnaView: React.FC<BrandDnaViewProps> = ({ brand, onUpdateBrand }) => {
  const [copiedColor, setCopiedColor] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);

  const handleCopy = (color: string) => {
    navigator.clipboard.writeText(color);
    setCopiedColor(color);
    setTimeout(() => setCopiedColor(null), 1500);
  };

  const handleRescan = () => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
    }, 1200);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Banner: Ingested Link */}
      <div className="craft-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              background: brand.palette.primary,
              color: "#fff",
              border: "var(--craft-border)",
              boxShadow: "var(--craft-shadow-sm)",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 900,
              fontSize: "1.4rem",
            }}
          >
            {brand.name[0]}
          </div>

          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h2 style={{ margin: 0, fontSize: "1.3rem", fontWeight: 900 }}>{brand.name}</h2>
              <span
                style={{
                  fontSize: "0.75rem",
                  background: "var(--craft-orange)",
                  color: "#fff",
                  padding: "2px 8px",
                  borderRadius: "2px",
                  fontWeight: 800,
                  fontFamily: "var(--craft-font-mono)",
                }}
              >
                LIVE LINK ATIVO
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px", color: "var(--craft-ink-muted)", fontSize: "0.88rem" }}>
              <Globe size={14} />
              <a
                href={brand.url}
                target="_blank"
                rel="noreferrer"
                style={{ color: "inherit", textDecoration: "underline", fontWeight: 600 }}
              >
                {brand.url}
              </a>
              <span>·</span>
              <span>{brand.tagline}</span>
            </div>
          </div>
        </div>

        <button
          className="craft-btn"
          onClick={handleRescan}
          disabled={isScanning}
        >
          <RefreshCw size={14} className={isScanning ? "animate-spin" : ""} />
          {isScanning ? "Reescanneando DOM..." : "Reescanear Site"}
        </button>
      </div>

      {/* Grid of Attributes */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "24px" }}>
        {/* Color Palette Card */}
        <div className="craft-card">
          <div className="craft-card-header">
            <h3 className="craft-card-title">
              <Palette size={16} /> Paleta de Cores Extraída
            </h3>
            <span style={{ fontSize: "0.75rem", fontFamily: "var(--craft-font-mono)", color: "var(--craft-ink-muted)" }}>
              5 TOKENS
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {Object.entries(brand.palette).map(([role, hex]) => (
              <div
                key={role}
                onClick={() => handleCopy(hex)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 12px",
                  background: "var(--craft-paper)",
                  border: "1px solid var(--craft-ink-faint)",
                  borderRadius: "2px",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <div
                    style={{
                      width: "28px",
                      height: "28px",
                      background: hex,
                      borderRadius: "2px",
                      border: "1.5px solid var(--craft-ink)",
                    }}
                  />
                  <div>
                    <div style={{ fontSize: "0.85rem", fontWeight: 800, textTransform: "capitalize" }}>
                      {role}
                    </div>
                    <div style={{ fontSize: "0.75rem", fontFamily: "var(--craft-font-mono)", color: "var(--craft-ink-muted)" }}>
                      {hex}
                    </div>
                  </div>
                </div>

                <span style={{ fontSize: "0.75rem", color: "var(--craft-ink-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                  {copiedColor === hex ? <Check size={12} color="green" /> : <Copy size={12} />}
                  {copiedColor === hex ? "Copiado" : "Copiar"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Typography & Vibe Card */}
        <div className="craft-card">
          <div className="craft-card-header">
            <h3 className="craft-card-title">
              <Type size={16} /> Tipografia & Tom de Voz
            </h3>
            <span style={{ fontSize: "0.75rem", fontFamily: "var(--craft-font-mono)", color: "var(--craft-ink-muted)" }}>
              THE THINKER
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <div className="craft-col-tag" style={{ marginBottom: "6px" }}>FAMÍLIAS TIPOGRÁFICAS DETECTADAS</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ padding: "8px 12px", background: "var(--craft-paper)", border: "1px solid var(--craft-ink-faint)" }}>
                  <div style={{ fontSize: "0.72rem", color: "var(--craft-ink-muted)" }}>TÍTULOS / HEADINGS:</div>
                  <div style={{ fontSize: "1rem", fontWeight: 900 }}>{brand.typography.heading}</div>
                </div>
                <div style={{ padding: "8px 12px", background: "var(--craft-paper)", border: "1px solid var(--craft-ink-faint)" }}>
                  <div style={{ fontSize: "0.72rem", color: "var(--craft-ink-muted)" }}>CORPO DE TEXTO / BODY:</div>
                  <div style={{ fontSize: "0.95rem", fontWeight: 600 }}>{brand.typography.body}</div>
                </div>
              </div>
            </div>

            <div>
              <div className="craft-col-tag" style={{ marginBottom: "6px" }}>VIBE DA MARCA & ARQUÉTIPO</div>
              <div style={{ padding: "12px", background: "var(--craft-paper)", border: "1px solid var(--craft-ink-faint)", fontSize: "0.88rem", lineHeight: 1.5 }}>
                <div style={{ fontWeight: 800, color: "var(--craft-orange)", marginBottom: "4px" }}>
                  {brand.archetype}
                </div>
                <div style={{ color: "var(--craft-ink)" }}>
                  {brand.vibe}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Product Photos Assets Tray */}
      <div className="craft-card">
        <div className="craft-card-header">
          <div>
            <h3 className="craft-card-title">
              <ImageIcon size={16} /> Banco de Fotos de Produto da Marca
            </h3>
            <div style={{ fontSize: "0.8rem", color: "var(--craft-ink-muted)", marginTop: "4px" }}>
              Fotos extraídas automaticamente do site ou adicionadas pelo operador. O Designer injeta estas imagens nas lâminas de carrossel.
            </div>
          </div>

          <button className="craft-btn">
            <Upload size={14} /> Fazer Upload de Imagens
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "16px" }}>
          {brand.productPhotos.map((photo) => (
            <div
              key={photo.id}
              style={{
                border: "var(--craft-border)",
                borderRadius: "3px",
                overflow: "hidden",
                background: "var(--craft-paper)",
                boxShadow: "var(--craft-shadow-sm)",
              }}
            >
              <div style={{ width: "100%", aspectRatio: "1/1", overflow: "hidden" }}>
                <img
                  src={photo.url}
                  alt={photo.title}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              </div>
              <div style={{ padding: "10px", background: "var(--craft-paper-card)" }}>
                <div style={{ fontSize: "0.85rem", fontWeight: 800 }}>{photo.title}</div>
                <div style={{ fontSize: "0.72rem", color: "var(--craft-ink-muted)", marginTop: "2px" }}>
                  {photo.category}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
