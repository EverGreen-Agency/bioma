# Spec: mod-mobile

- **Cliente:** EverGreen + clientes EG (`target: platform`, futuro)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho baixa prioridade
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-mobile`, `client-hub`

## 1. Objetivo

Definir a estratégia mobile do Bioma para clientes, equipe e possíveis usuários SaaS sem antecipar app nativo antes de validar a web.

## 2. Contexto

NFC e uso executivo tendem a abrir no celular. Ainda assim, o caminho pragmático é web responsiva/PWA primeiro, app nativo depois se houver uso recorrente que justifique.

## 3. Escopo

- Requisitos mobile-first para client-hub e aprovações.
- Avaliação PWA vs React Native/Expo.
- Push notifications futuras.
- Leitura/fluxo de NFC.

## 4. Fora de Escopo

- App nativo no MVP.
- Funcionalidades offline complexas.
- Publicação App Store/Google Play antes de validação.

## 5. Requisitos Funcionais

- RF1 — Client-hub deve funcionar bem em mobile web.
- RF2 — Magic link/NFC deve abrir fluxo seguro em navegador móvel.
- RF3 — Aprovações simples devem ser possíveis pelo celular.
- RF4 — Estratégia PWA/nativo deve ser decidida por ADR futuro.

## 6. Requisitos Não-Funcionais

- **UX:** telas essenciais em até poucos toques.
- **Segurança:** sessão móvel revogável.
- **Performance:** carregamento rápido em 4G comum.

## 7. Critérios de Aceite

- CA1 — Fluxo NFC abre no mobile e não quebra autenticação.
- CA2 — Cliente aprova/reprova item pelo celular.
- CA3 — Layout não exige desktop para tarefas básicas.

## 8. Riscos e Dependências

- **Risco:** app nativo drenar foco cedo demais.  
  **Mitigação:** PWA/web responsiva primeiro.

- **Dependência:** `client-hub`.
- **Dependência:** ADR PWA-vs-nativo.

