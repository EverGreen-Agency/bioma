import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { BookOpen, ExternalLink, ImageOff, X } from "lucide-react";

import { guideFor, screenshotPath, type IntegrationGuideContent } from "../lib/integration-guides";

const RESPONSIBLE_LABEL: Record<IntegrationGuideContent["responsible"], string> = {
  eg: "Só a EG executa",
  client: "O cliente precisa autorizar",
  both: "EG + cliente, em etapas",
};

function ScreenshotSlot({ provider, slug }: { provider: string; slug: string }) {
  const [failed, setFailed] = useState(false);
  const path = screenshotPath(provider, slug);

  if (failed) {
    return (
      <div className="guide-screenshot-empty">
        <ImageOff size={15} />
        <span>
          Espaço reservado para print. Salve em <code>public{path}</code> e recarregue.
        </span>
      </div>
    );
  }

  return (
    <img
      className="guide-screenshot"
      src={path}
      alt={`Print do passo: ${slug}`}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

function GuideModal({
  provider,
  label,
  guide,
  onClose,
}: {
  provider: string;
  label: string;
  guide: IntegrationGuideContent;
  onClose: () => void;
}) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  return createPortal(
    <div className="guide-modal-backdrop" onClick={onClose}>
      <div
        className="guide-modal-card"
        role="dialog"
        aria-modal="true"
        aria-label={`Como conectar ${label}`}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="guide-modal-header">
          <div>
            <span className="guide-modal-eyebrow">Guia de integração</span>
            <h2>Como conectar {label}</h2>
            <span className="guide-modal-responsible">{RESPONSIBLE_LABEL[guide.responsible]}</span>
          </div>
          <button type="button" className="guide-modal-close" onClick={onClose} aria-label="Fechar">
            <X size={18} />
          </button>
        </header>

        <div className="guide-modal-body">
          <p className="guide-summary">{guide.summary}</p>

          {guide.caveat && (
            <div className="guide-caveat">
              <strong>Atenção:</strong> {guide.caveat}
            </div>
          )}

          {guide.prerequisites.length > 0 && (
            <section className="guide-section">
              <h3>Antes de começar</h3>
              <ul className="guide-list">
                {guide.prerequisites.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </section>
          )}

          <section className="guide-section">
            <h3>Passo a passo</h3>
            <ol className="guide-steps">
              {guide.steps.map((step, index) => (
                <li key={index}>
                  <span className="guide-step-number">{index + 1}</span>
                  <div className="guide-step-content">
                    <strong>{step.title}</strong>
                    <p>{step.description}</p>
                    {step.link && (
                      <a href={step.link.url} target="_blank" rel="noreferrer" className="guide-step-link">
                        {step.link.label} <ExternalLink size={12} />
                      </a>
                    )}
                    {step.screenshot && <ScreenshotSlot provider={provider} slug={step.screenshot} />}
                  </div>
                </li>
              ))}
            </ol>
          </section>

          {guide.envVars && guide.envVars.length > 0 && (
            <section className="guide-section">
              <h3>Configuração do ambiente EG (uma vez, não por cliente)</h3>
              <div className="guide-envvars">
                {guide.envVars.map((envVar) => (
                  <code key={envVar}>{envVar}</code>
                ))}
              </div>
            </section>
          )}
        </div>

        <footer className="guide-modal-footer">
          A EverGreen nunca solicita a senha das suas contas. Todo acesso é concedido por permissão
          nomeada ou autorização oficial da própria plataforma, e pode ser revogado por você a
          qualquer momento.
        </footer>
      </div>
    </div>,
    document.body
  );
}

export function IntegrationGuide({ provider, label }: { provider: string; label: string }) {
  const [open, setOpen] = useState(false);
  const guide = guideFor(provider);

  if (!guide) return null;

  return (
    <>
      <button type="button" className="guide-trigger" onClick={() => setOpen(true)}>
        <BookOpen size={13} />
        Como conectar
        <span className="guide-trigger-badge">{RESPONSIBLE_LABEL[guide.responsible]}</span>
      </button>

      {open && (
        <GuideModal provider={provider} label={label} guide={guide} onClose={() => setOpen(false)} />
      )}
    </>
  );
}
