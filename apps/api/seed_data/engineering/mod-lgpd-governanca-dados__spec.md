# Spec: mod-lgpd-governanca-dados

- **Cliente:** EverGreen + clientes EG (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideia:** proposta de módulo transversal; registrar no Banco de Ideias se aprovado

## 1. Objetivo

Definir e operar governança de dados, privacidade, consentimento, retenção, classificação e uso de IA com dados de clientes, funcionários e leads.

## 2. Contexto

O Bioma lidará com credenciais, campanhas, reuniões, áudios, contratos, documentos, dados financeiros, dados pessoais e saídas de LLM. Sem uma camada clara de governança, qualquer módulo pode vazar dado, reter demais, enviar informação sensível para LLM externa ou publicar algo indevido.

## 3. Escopo

O que será construído:

- Classificação de dados: público, interno, cliente, sensível, segredo, financeiro, jurídico, PII.
- Registro de finalidade e base de uso para dados sensíveis.
- Políticas de retenção por tipo de dado.
- Consentimentos e permissões para captura/transcrição/uso de dados.
- Regras de uso de LLM externa por classe de dado.
- Exportação/remoção/anomização quando aplicável.
- Checklist de publicação pública e client-hub.

## 4. Fora de Escopo

- Substituir assessoria jurídica.
- Garantir conformidade legal completa sem revisão humana.
- Implementar DLP corporativo completo no MVP.
- Permitir uso de dados sensíveis por padrão em qualquer modelo externo.

## 5. Requisitos Funcionais

- RF1 — Sistema deve permitir classificar tipos de dado e recursos.
- RF2 — Módulos devem registrar finalidade para dados sensíveis.
- RF3 — Sistema deve bloquear envio de dados proibidos para LLM externa.
- RF4 — Consentimento deve ser registrado para captura/transcrição quando necessário.
- RF5 — Política de retenção deve sinalizar dados vencidos.
- RF6 — Export/delete/anonymize deve existir para entidades suportadas.
- RF7 — Publicação pública deve exigir checklist de privacidade.
- RF8 — Auditoria deve registrar acesso a PII/segredo.

## 6. Requisitos Não-Funcionais

- **Segurança:** classificação deve ser aplicada server-side.
- **Privacidade:** coleta mínima por finalidade.
- **Auditabilidade:** decisões de exceção precisam de justificativa.
- **Operação:** política simples o suficiente para ser usada.

## 7. Critérios de Aceite

- CA1 — Dado marcado como segredo não é enviado a LLM externa.
- CA2 — Áudio sem consentimento aplicável não entra em pipeline de transcrição/RAG.
- CA3 — Conteúdo público com dados de cliente exige aprovação de privacidade.
- CA4 — Recurso com retenção vencida aparece em fila de revisão.
- CA5 — Acesso a PII sensível gera audit log.

## 8. Riscos e Dependências

- **Risco:** governança virar documento ignorado.  
  **Mitigação:** enforcement por API/adapters, não só política escrita.

- **Risco:** excesso de bloqueio travar operação.  
  **Mitigação:** classes simples e exceções auditadas.

- **Dependência:** `mod-multitenant`.
- **Dependência:** `cofre-senhas`.
- **Dependência:** `mod-conhecimento`.
- **Dependência:** revisão jurídica.

