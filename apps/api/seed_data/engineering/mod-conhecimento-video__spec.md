# Spec: mod-conhecimento-video

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho baixa prioridade
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-conhecimento-video`, `mod-conhecimento`, `clonagem-personas`

## 1. Objetivo

Tratar vídeos, cursos, aulas, reuniões gravadas e materiais audiovisuais como fontes possíveis de conhecimento, com curadoria, direitos e classificação.

## 2. Contexto

Há interesse em usar transcrições de cursos, vídeos e referências externas para formar bases de conhecimento e personas. Isso é sensível por direitos autorais, LGPD e obsolescência.

## 3. Escopo

- Ingestão de vídeo autorizado.
- Extração de áudio/transcrição.
- OCR/frame analysis quando houver necessidade.
- Curadoria antes de enviar ao RAG.
- Registro de licença/direito de uso.

## 4. Fora de Escopo

- Baixar e redistribuir curso de terceiros sem direito.
- Publicar conteúdo protegido para clientes.
- Clonar mentor/persona sem análise jurídica.

## 5. Requisitos Funcionais

- RF1 — Vídeo deve ter origem, licença e finalidade registradas.
- RF2 — Transcrição deve ser revisável antes de indexação.
- RF3 — Conteúdo deve ser classificado por sensibilidade e validade.
- RF4 — Chunks derivados devem apontar para vídeo/fonte original.

## 6. Requisitos Não-Funcionais

- **Direitos autorais:** bloqueio por padrão sem origem/uso permitido.
- **Privacidade:** reuniões gravadas exigem consentimento aplicável.
- **Qualidade:** transcrição precisa ter confiança/erro registrado.

## 7. Critérios de Aceite

- CA1 — Vídeo sem licença/finalidade não entra no RAG.
- CA2 — Transcrição revisada pode ser indexada com origem.
- CA3 — Conteúdo antigo pode receber decay.

## 8. Riscos e Dependências

- **Risco:** uso indevido de cursos/terceiros.  
  **Mitigação:** governança e jurídico antes de produção.

- **Dependência:** `mod-conhecimento`.
- **Dependência:** `mod-lgpd-governanca-dados`.
- **Dependência:** `mod-juridico`.

