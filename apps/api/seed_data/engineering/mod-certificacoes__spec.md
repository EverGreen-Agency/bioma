# Spec: mod-certificacoes

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho baixa prioridade
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-certificacoes`, `mod-rh`

## 1. Objetivo

Criar trilhas, provas e certificações internas para garantir padrão EG em operação, vendas, tráfego, BI, atendimento e cultura.

## 2. Contexto

À medida que a EG crescer, precisa provar que pessoas e parceiros entendem método, tom, regras de segurança e padrões de entrega. Hoje isso não bloqueia o MVP.

## 3. Escopo

- Trilhas de aprendizado.
- Quizzes/checkpoints.
- Certificados internos por competência.
- Validade/renovação.
- Ligação com `mod-rh`.

## 4. Fora de Escopo

- Plataforma educacional pública.
- Certificação externa vendável no MVP.
- Gamificação complexa.

## 5. Requisitos Funcionais

- RF1 — RH deve criar trilha e competências.
- RF2 — Colaborador deve concluir etapas e avaliações.
- RF3 — Certificação deve ter status e validade.
- RF4 — Certificação deve impactar permissões apenas se aprovado por regra.

## 6. Requisitos Não-Funcionais

- **Simplicidade:** usar como controle interno, não LMS completo.
- **Auditabilidade:** histórico de conclusão preservado.

## 7. Critérios de Aceite

- CA1 — Colaborador conclui trilha e recebe certificação interna.
- CA2 — Certificação expirada aparece como pendência.
- CA3 — Gestor vê competências por pessoa.

## 8. Riscos e Dependências

- **Risco:** burocracia sem equipe suficiente.  
  **Mitigação:** baixa prioridade até contratação.

- **Dependência:** `mod-rh`.

