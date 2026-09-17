# Gerador de Documentos EG (PDF/DOCX branded)

**id:** `doc-generator-eg` · **tipo:** skill (Infra) · **stage:** capture · **origin:** internal
**depends_on:** skill-brand-eg, filosofia-visual-eg · **enables:** squad-relatorios, squad-hunter (eg_proposals)

## Problema
Propostas, relatórios e entregáveis da EG (e para clientes) saem **toda hora com layout, configuração e branding diferentes**. Não há um motor único que garanta consistência. A dor apareceu concreta no lead **Rian/PJe-TRF1**: o documento de especificação precisou virar **PDF único** e um **protótipo navegável**, tudo montado à mão (markdown → HTML → Chrome headless). Funciona, mas não escala nem padroniza.

## O que é (e o que NÃO é)
- **É** um **motor + biblioteca de templates** que recebe conteúdo (markdown ou dados estruturados) e produz o **arquivo entregável final** com identidade consistente.
- **NÃO é** a camada de marca (isso é `skill-brand-eg` — tokens de cor/fonte). Este motor **consome** aquela camada.
- **NÃO é** UI web (isso é `web-artifacts-builder`). Aqui o alvo é **documento/arquivo** (PDF, DOCX), não tela.

## Escopo proposto
- **Entradas:** markdown (specs, propostas, relatórios) e/ou dados estruturados (JSON) + escolha de template.
- **Saídas:** **PDF** (HTML→Chrome/Edge headless `--print-to-pdf`, ou WeasyPrint) e **DOCX** (ex.: `python-docx` ou template Word).
- **Templates:** proposta comercial, relatório de cliente, spec/anexo de contrato, one-pager, capa.
- **Branding parametrizável:** perfil **EG** por padrão (musgo/menta/baunilha, Helvetica Neue); perfil de **cliente** quando o entregável é para a marca dele (logo, cores, fonte).
- **Reuso:** puxa tokens do `skill-brand-eg` / `filosofia-visual-eg`; não redefine marca.

## Quem consome
- `squad-hunter` (eg_proposals) → renderiza a proposta em PDF/DOCX branded.
- `squad-relatorios` → renderiza o relatório de cliente.
- `eg_engenharia` → specs/anexos de contrato em PDF.

## Notas técnicas (aprendizado do run Rian)
- A máquina EG **não tem** `pandoc` nem `wkhtmltopdf`; PDF sai bem via **Chrome/Edge headless `--print-to-pdf`** a partir de HTML (markdown convertido com `python-markdown`).
- Para DOCX, avaliar `python-docx` (programático) vs. template `.docx` com placeholders.
- Fase 1 sensata: **PDF branded EG a partir de markdown** (cobre proposta/spec/relatório). DOCX e branding-de-cliente entram depois.

## Escopo ampliado (feedback Eduardo, 02/07)
Além de propostas/relatórios/specs, o motor cobre:
- **Manuais e guias how-to** para clientes e funcionários — ex.: "como adicionar a BM da EverGreen como parceira dentro da sua Business Manager para gerenciarmos os ads", passo-a-passo de onboarding, tutoriais de acesso. Reduz atrito no setup de cliente e padroniza a comunicação.
- **Kit jurídico/LGPD** — DPA (acordo de tratamento de dados), política de privacidade, termos de uso e, quando o deploy transita dados fora do Brasil (ex.: Vercel/Railway nos EUA), a **cláusula de transferência internacional** (LGPD art. 33) + base legal/consentimento. Necessidade real: todo projeto que trata dado de cliente precisa desse kit; hoje sai inconsistente. Candidato a virar um sub-conjunto de templates (ou uma ideia irmã `kit-juridico-lgpd` se ganhar corpo próprio).

## Caminho (Trilho B)
Registrada no Banco (capture). Próximos saltos, sob HITL: Arquiteto (cabe? reaproveita `skill-brand-eg`?) → se `build`, vira skill formal via Engenharia. Horizonte a redefinir (sugestão MEDIUM — dor ativa e recorrente).
