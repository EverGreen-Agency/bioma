import {
  Flag,
  Hash,
  Heart,
  LockKeyhole,
  Megaphone,
  MessageCircle,
  NotebookPen,
  Star,
  Target,
  Users,
  type LucideIcon,
} from "lucide-react";
import { parseContentSections } from "../lib/format";
import { EmptyState } from "./shared";

const sectionIcons: Array<{ pattern: RegExp; icon: LucideIcon }> = [
  { pattern: /objetivo/i, icon: Target },
  { pattern: /posicionamento/i, icon: Flag },
  { pattern: /prop[óo]sito|ess[êe]ncia/i, icon: Heart },
  { pattern: /tom de voz|voz/i, icon: MessageCircle },
  { pattern: /p[úu]blico|audi[êe]ncia|icp/i, icon: Users },
  { pattern: /tema|pilar/i, icon: Hash },
  { pattern: /mensagem|mensagens/i, icon: Megaphone },
  { pattern: /restri[çc]|diretriz|compliance|lgpd/i, icon: LockKeyhole },
  { pattern: /diferencia|prova/i, icon: Star },
];

function sectionIcon(title: string): LucideIcon {
  return sectionIcons.find(({ pattern }) => pattern.test(title))?.icon ?? NotebookPen;
}

function isBulletLine(line: string) {
  return /^([-*•]|\d+[.)])\s+/.test(line);
}

function stripBullet(line: string) {
  return line.replace(/^([-*•]|\d+[.)])\s+/, "").replace(/\*\*/g, "");
}

function renderLines(lines: string[]) {
  const blocks: Array<{ type: "list"; items: string[] } | { type: "paragraph"; text: string }> = [];
  for (const line of lines) {
    if (isBulletLine(line)) {
      const last = blocks[blocks.length - 1];
      if (last?.type === "list") {
        last.items.push(stripBullet(line));
      } else {
        blocks.push({ type: "list", items: [stripBullet(line)] });
      }
    } else {
      blocks.push({ type: "paragraph", text: line.replace(/\*\*/g, "") });
    }
  }

  return blocks.map((block, index) =>
    block.type === "list" ? (
      <ul key={index}>
        {block.items.map((item, itemIndex) => (
          <li key={itemIndex}>{item}</li>
        ))}
      </ul>
    ) : (
      <p key={index}>{block.text}</p>
    ),
  );
}

/**
 * Renderiza o conteúdo textual de um artefato como grid de cards por seção.
 * Sem headings no conteúdo, cai para um card único com o texto corrido.
 */
export function ArtifactSectionGrid({ content, emptyText }: { content: string | null; emptyText: string }) {
  if (!content?.trim()) {
    return <EmptyState text={emptyText} />;
  }

  const sections = parseContentSections(content);

  return (
    <div className="doc-grid">
      {sections.map((section, index) => {
        const Icon = sectionIcon(section.title);
        return (
          <div className="doc-section" key={`${section.title}-${index}`}>
            {section.title && (
              <h4>
                <Icon size={14} /> {section.title}
              </h4>
            )}
            {renderLines(section.lines)}
          </div>
        );
      })}
    </div>
  );
}
