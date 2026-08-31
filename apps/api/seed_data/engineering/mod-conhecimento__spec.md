# Spec: mod-conhecimento

- **Cliente:** EverGreen + contexto por cliente (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-conhecimento`, `segundo-cerebro`, `vector-store`, `context-decay`, `stack-memoria-zep`, `squad-voz-cliente`, `dossie-provas`, `evidence-ledger`, `drive-rag-cliente`, `clonagem-personas`, `mod-conhecimento-video`

## 1. Objetivo

Transformar reuniões, documentos, relatórios, áudios, aprendizados e casos da EG em uma base curada de conhecimento consultável por humanos, squads e módulos do Bioma, com isolamento rígido por tenant.

## 2. Contexto

IA sem memória vira ferramenta genérica. A EG precisa de uma base viva que contenha voz do cliente, histórico de decisões, objeções, entregas, provas, sucessos, fracassos e contexto operacional. O ponto crítico é curadoria: nem tudo deve entrar, nem tudo deve ter o mesmo peso, e nem tudo pode sair para LLM externa.

## 3. Escopo

O que será construído:

- Registro de fontes de conhecimento: reunião, áudio, documento, proposta, contrato, relatório, case, playbook, curso, site e arquivo de cliente.
- Pipeline de ingestão com classificação, limpeza, chunking, embedding e revisão.
- Busca RAG filtrada por tenant, módulo, tipo de fonte, data e confiança.
- Context decay para reduzir peso de conhecimento antigo/desatualizado.
- Curadoria manual: promover, arquivar, invalidar, corrigir e marcar conhecimento sensível.
- Base de voz do cliente e dossiê de provas.
- Integração futura com drive próprio/drive do cliente.
- Registro de proveniência: de onde veio, quem autorizou, quando foi indexado e restrições de uso.
- Livro de evidências operacionais com decisões, aprovações, entregáveis, reuniões, relatórios enviados e resultados.

## 4. Fora de Escopo

- Jogar todo arquivo da EG no vetor sem triagem.
- Disponibilizar cursos/conteúdo de terceiros para clientes sem direito de uso.
- Criar clones de mentores/personas em produção sem análise jurídica.
- Usar dados de um cliente para responder outro cliente.
- Substituir storage de arquivos por banco vetorial.

## 5. Requisitos Funcionais

- RF1 — Sistema deve registrar fonte, tenant, autor/origem, data, tipo e nível de sensibilidade.
- RF2 — Pipeline deve gerar chunks e embeddings apenas para fontes aprovadas.
- RF3 — Busca RAG deve exigir `tenant_id` ou escopo interno explicitamente autorizado.
- RF4 — Resultado de busca deve retornar trechos, metadados, origem e score.
- RF5 — Curador deve poder desativar fonte ou chunk específico.
- RF6 — Sistema deve aplicar decay por idade, categoria e validade declarada.
- RF7 — Sistema deve expor endpoint interno para outros módulos consultarem contexto.
- RF8 — Sistema deve registrar qual conhecimento foi usado em resposta/relatório relevante.
- RF9 — Sistema deve distinguir conhecimento interno EG, conhecimento do cliente e conhecimento público.
- RF10 — Sistema deve permitir marcar conteúdo como proibido para LLM externa.
- RF11 — Sistema deve registrar evidências em formato append-only quando eventos relevantes ocorrerem em entregas, aprovações, relatórios e reuniões.

## 6. Requisitos Não-Funcionais

- **Segurança:** RLS e filtro de tenant também na busca vetorial.
- **Privacidade:** PII e dados sensíveis precisam de classificação antes de embedding externo.
- **Performance:** consultas comuns de RAG devem responder em até 500ms p95 para top-k moderado.
- **Qualidade:** fonte sem proveniência não pode ser usada em saída para cliente.
- **Governança:** todo pipeline automático precisa de fila de revisão para fontes sensíveis.

## 7. Critérios de Aceite

- CA1 — Query de um tenant nunca retorna chunk de outro tenant.
- CA2 — Uma fonte arquivada deixa de aparecer em buscas novas.
- CA3 — Um relatório gerado com RAG registra as fontes usadas.
- CA4 — Conteúdo marcado como "não enviar a LLM externa" é bloqueado no adapter.
- CA5 — Conhecimento antigo perde relevância conforme regra de decay.
- CA6 — O curador consegue rastrear origem de qualquer chunk retornado.

## 8. Riscos e Dependências

- **Risco:** conhecimento infinito gerar respostas ruins e caras.  
  **Mitigação:** curadoria, decay, limites por fonte e avaliação.

- **Risco:** direitos autorais/LGPD em cursos, vídeos e materiais de terceiros.  
  **Mitigação:** módulo jurídico/governança antes de qualquer uso externo.

- **Dependência:** `mod-multitenant` para isolamento.
- **Dependência:** ADR pgvector-vs-banco dedicado.
- **Dependência:** ADR memória de conversação/Zep.
- **Dependência:** `mod-lgpd-governanca-dados` para classificação e política de uso.
