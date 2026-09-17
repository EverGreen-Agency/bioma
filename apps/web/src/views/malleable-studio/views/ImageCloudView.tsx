import React, { useState, useEffect, useRef } from "react";
import { Play, Pause, Maximize2, RotateCcw, X, ZoomIn, ZoomOut, Sparkles } from "lucide-react";
import type { BrandDna, PostIdea } from "../data/malleable-mock";

interface ImageCloudViewProps {
  brand: BrandDna;
  ideas: PostIdea[];
}

interface CloudImageItem {
  id: string;
  src: string;
  title: string;
  phi: number; // polar angle
  theta: number; // azimuthal angle
}

export const ImageCloudView: React.FC<ImageCloudViewProps> = ({ brand, ideas }) => {
  // Coletar todas as imagens das ideias e do brand asset
  const allImages: Array<{ id: string; src: string; title: string }> = [
    ...brand.productPhotos.map((p) => ({ id: p.id, src: p.url, title: p.title })),
    ...ideas.map((i) => ({ id: i.id, src: i.visualIdea.previewImage, title: i.title })),
    ...ideas.flatMap((i) =>
      i.slides.map((s, sIdx) => ({
        id: `${i.id}-slide-${sIdx}`,
        src: s.assignedPhotoUrl || i.visualIdea.previewImage,
        title: `${i.title} - Slide ${s.slideNumber}`,
      })),
    ),
  ];

  // Configurações do Cloud
  const [isPlaying, setIsPlaying] = useState(true);
  const [rotationSpeed, setRotationSpeed] = useState(0.4);
  const [radius, setRadius] = useState(320); // Spacing
  const [depthSeparation, setDepthSeparation] = useState(1);
  const [photoSize, setPhotoSize] = useState(150);
  const [tiltCenter, setTiltCenter] = useState(true);
  const [fadeDistant, setFadeDistant] = useState(true);
  const [activePreset, setActivePreset] = useState<"editorial" | "gallery" | "orbit" | "dense">("orbit");

  // Rotação da esfera
  const [rotX, setRotX] = useState(15);
  const [rotY, setRotY] = useState(0);
  const [zoom, setZoom] = useState(1);

  // Lightbox
  const [selectedImage, setSelectedImage] = useState<{ src: string; title: string } | null>(null);

  // Física de arraste e inércia
  const isDragging = useRef(false);
  const lastMousePos = useRef({ x: 0, y: 0 });
  const velocity = useRef({ x: 0, y: 0 });
  const animFrameId = useRef<number | null>(null);

  // Distribuir as imagens na esfera usando Fibonacci Sphere algorithm
  const sphereItems: CloudImageItem[] = React.useMemo(() => {
    const total = allImages.length;
    const goldenRatio = (1 + Math.sqrt(5)) / 2;
    return allImages.map((img, i) => {
      const theta = 2 * Math.PI * i / goldenRatio;
      const phi = Math.acos(1 - 2 * (i + 0.5) / total);
      return {
        id: img.id,
        src: img.src,
        title: img.title,
        phi,
        theta,
      };
    });
  }, [allImages]);

  // Presets
  const applyPreset = (preset: "editorial" | "gallery" | "orbit" | "dense") => {
    setActivePreset(preset);
    if (preset === "editorial") {
      setRadius(380);
      setPhotoSize(180);
      setDepthSeparation(1.2);
      setTiltCenter(true);
      setFadeDistant(true);
    } else if (preset === "gallery") {
      setRadius(300);
      setPhotoSize(140);
      setDepthSeparation(0.8);
      setTiltCenter(false);
      setFadeDistant(false);
    } else if (preset === "orbit") {
      setRadius(340);
      setPhotoSize(150);
      setDepthSeparation(1);
      setTiltCenter(true);
      setFadeDistant(true);
    } else if (preset === "dense") {
      setRadius(240);
      setPhotoSize(120);
      setDepthSeparation(0.6);
      setTiltCenter(true);
      setFadeDistant(true);
    }
  };

  // Loop de animação com inércia e rotação contínua
  useEffect(() => {
    const loop = () => {
      if (!isDragging.current) {
        // Inércia
        if (Math.abs(velocity.current.x) > 0.01 || Math.abs(velocity.current.y) > 0.01) {
          setRotY((y) => y + velocity.current.x);
          setRotX((x) => Math.max(-85, Math.min(85, x - velocity.current.y)));
          velocity.current.x *= 0.94;
          velocity.current.y *= 0.94;
        } else if (isPlaying) {
          setRotY((y) => (y + rotationSpeed) % 360);
        }
      }
      animFrameId.current = requestAnimationFrame(loop);
    };

    animFrameId.current = requestAnimationFrame(loop);
    return () => {
      if (animFrameId.current) cancelAnimationFrame(animFrameId.current);
    };
  }, [isPlaying, rotationSpeed]);

  // Eventos de mouse
  const handleMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true;
    lastMousePos.current = { x: e.clientX, y: e.clientY };
    velocity.current = { x: 0, y: 0 };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current) return;
    const dx = e.clientX - lastMousePos.current.x;
    const dy = e.clientY - lastMousePos.current.y;

    velocity.current = { x: dx * 0.4, y: dy * 0.4 };
    setRotY((y) => y + dx * 0.4);
    setRotX((x) => Math.max(-85, Math.min(85, x - dy * 0.4)));

    lastMousePos.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseUp = () => {
    isDragging.current = false;
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => Math.max(0.5, Math.min(2.2, z - e.deltaY * 0.001)));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* View Header */}
      <div className="craft-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Sparkles size={18} color="var(--craft-orange)" />
            <h2 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 900 }}>
              3D IMAGE CLOUD · NAVEGAÇÃO ESPACIAL DE PEÇAS
            </h2>
          </div>
          <div style={{ fontSize: "0.85rem", color: "var(--craft-ink-muted)", marginTop: "4px" }}>
            Todas as lâminas renderizadas e fotos de produto flutuando em uma esfera 3D interativa com profundidade real e inércia.
          </div>
        </div>

        {/* Presets Selector */}
        <div style={{ display: "flex", gap: "6px" }}>
          {(["editorial", "gallery", "orbit", "dense"] as const).map((preset) => (
            <button
              key={preset}
              onClick={() => applyPreset(preset)}
              className="craft-btn"
              style={{
                fontSize: "0.78rem",
                padding: "6px 12px",
                textTransform: "capitalize",
                background: activePreset === preset ? "var(--craft-ink)" : "var(--craft-paper-card)",
                color: activePreset === preset ? "var(--craft-paper)" : "var(--craft-ink)",
              }}
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      {/* 3D Cloud Viewport */}
      <div
        className="craft-cloud-viewport"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <div
          className="craft-cloud-sphere"
          style={{
            transform: `scale(${zoom}) rotateX(${rotX}deg) rotateY(${rotY}deg)`,
            transformStyle: "preserve-3d",
          }}
        >
          {sphereItems.map((item) => {
            // Converter coordenadas esféricas para cartesianas
            const r = radius;
            const x = r * Math.sin(item.phi) * Math.cos(item.theta);
            const y = r * Math.cos(item.phi);
            const z = r * Math.sin(item.phi) * Math.sin(item.theta) * depthSeparation;

            // Calcular distância para efeito de fade e blur
            // Rotação aproximada no plano Z
            const radY = (rotY * Math.PI) / 180;
            const radX = (rotX * Math.PI) / 180;
            const rotatedZ = x * Math.sin(radY) + z * Math.cos(radY);

            // Escala e opacidade com base em Z
            const depthFactor = (rotatedZ + r) / (2 * r); // 0 (longe) a 1 (perto)
            const opacity = fadeDistant ? Math.max(0.25, Math.min(1, 0.3 + depthFactor * 0.7)) : 1;
            const blur = fadeDistant ? Math.max(0, (1 - depthFactor) * 3) : 0;

            return (
              <div
                key={item.id}
                className="craft-cloud-item"
                onClick={() => setSelectedImage({ src: item.src, title: item.title })}
                style={{
                  width: `${photoSize}px`,
                  height: `${photoSize * 1.3}px`,
                  transform: tiltCenter
                    ? `translate3d(${x}px, ${y}px, ${z}px) rotateY(${-rotY}deg) rotateX(${-rotX}deg)`
                    : `translate3d(${x}px, ${y}px, ${z}px)`,
                  opacity,
                  filter: blur > 0.5 ? `blur(${blur}px)` : "none",
                }}
              >
                <img src={item.src} alt={item.title} loading="lazy" />
              </div>
            );
          })}
        </div>

        {/* Floating Controls Bar at Bottom */}
        <div className="craft-cloud-controls">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              className="craft-btn"
              onClick={() => setIsPlaying(!isPlaying)}
              style={{ width: "38px", height: "38px", padding: 0 }}
            >
              {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            </button>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 800 }}>VELOCIDADE:</span>
              <input
                type="range"
                min={0.1}
                max={1.5}
                step={0.1}
                value={rotationSpeed}
                onChange={(e) => setRotationSpeed(Number(e.target.value))}
                style={{ width: "80px", accentColor: "var(--craft-orange)" }}
              />
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 800 }}>ESPAÇO:</span>
              <input
                type="range"
                min={200}
                max={500}
                value={radius}
                onChange={(e) => setRadius(Number(e.target.value))}
                style={{ width: "90px", accentColor: "var(--craft-orange)" }}
              />
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: 800 }}>TAMANHO:</span>
              <input
                type="range"
                min={80}
                max={220}
                value={photoSize}
                onChange={(e) => setPhotoSize(Number(e.target.value))}
                style={{ width: "90px", accentColor: "var(--craft-orange)" }}
              />
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <button
                className="craft-btn craft-btn-icon"
                onClick={() => setZoom((z) => Math.max(0.5, z - 0.2))}
                title="Zoom Out"
              >
                <ZoomOut size={15} />
              </button>
              <button
                className="craft-btn craft-btn-icon"
                onClick={() => setZoom((z) => Math.min(2.2, z + 0.2))}
                title="Zoom In"
              >
                <ZoomIn size={15} />
              </button>
              <button
                className="craft-btn craft-btn-icon"
                onClick={() => {
                  setRotX(15);
                  setRotY(0);
                  setZoom(1);
                }}
                title="Resetar Câmera"
              >
                <RotateCcw size={15} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Lightbox Modal */}
      {selectedImage && (
        <div className="craft-modal-overlay" onClick={() => setSelectedImage(null)}>
          <div
            className="craft-modal-dialog"
            style={{ maxWidth: "600px" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="craft-modal-header">
              <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 900 }}>
                {selectedImage.title}
              </h3>
              <button className="craft-btn craft-btn-icon" onClick={() => setSelectedImage(null)}>
                <X size={18} />
              </button>
            </div>
            <div style={{ padding: "20px", display: "flex", justifyContent: "center" }}>
              <img
                src={selectedImage.src}
                alt={selectedImage.title}
                style={{
                  maxWidth: "100%",
                  maxHeight: "70vh",
                  borderRadius: "4px",
                  border: "var(--craft-border)",
                  boxShadow: "var(--craft-shadow)",
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
