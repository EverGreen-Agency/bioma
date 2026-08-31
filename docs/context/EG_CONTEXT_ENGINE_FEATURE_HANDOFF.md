# EG / Bioma — Handoff da feature de Banco de Conhecimento e Context Engine

**Versão do contrato:** 1.0  
**Data:** 2026-08-03  
**Origem de referência:** Fóton 0.8.15  
**Objetivo:** permitir que o backoffice da EG implemente a mesma capacidade em outra stack, sem copiar os acoplamentos de Tauri, Rust, SQLite ou da interface desktop.

## 1. Resumo executivo

Esta feature transforma documentos e conhecimento interno em bases isoladas, inspecionáveis e utilizáveis por pessoas, agentes e workflows. Ela não é somente um campo para upload de arquivos nem somente uma vector store.

O produto precisa oferecer o ciclo completo:

1. criar uma base de conhecimento;
2. adicionar fontes e registrar sua proveniência;
3. extrair, normalizar, versionar e fragmentar o conteúdo;
4. permitir inspeção, edição, ativação e desativação dos fragmentos;
5. recuperar evidências por busca lexical e, quando disponível, semântica;
6. fundir e reranquear os resultados;
7. responder com citações verificáveis;
8. restringir personas, agentes e workflows às bases autorizadas;
9. testar a recuperação com datasets de Q&A e métricas;
10. registrar runs, custos, erros, decisões e versões.

Para a EG, a recomendação é implementar a feature como um módulo de domínio do Bioma ou como um serviço interno versionado. Não se deve copiar a tela React e os comandos Tauri e pedir uma refatoração sem contrato.

## 2. Valor para o backoffice da EG

Casos de uso iniciais:

- políticas, processos, contratos-modelo e documentação operacional;
- base por empresa, cliente, departamento, projeto ou operação;
- copilotos especializados com acesso somente ao escopo autorizado;
- onboarding e consulta interna com fontes;
- análise de ferramentas, fornecedores e oportunidades;
- preparação de dossiês e decisões com rastreabilidade;
- geração e revisão de perguntas de avaliação;
- transferência controlada de contexto entre Fóton e Bioma.

O Bioma não deve receber implicitamente dados pessoais do Fóton. A integração deve ser por exportação ou API com escopo, finalidade, autorização e trilha de auditoria.

## 3. Decisão de arquitetura

### Recomendação padrão

Se a stack do Bioma é diferente da do Fóton, implementar por contrato:

```text
UI do Bioma
   |
API de Knowledge/Context
   |-- banco relacional e autorização
   |-- object storage para fontes originais
   |-- índice lexical
   |-- índice vetorial opcional
   |-- fila e workers de ingestão
   |-- adaptadores de modelos e rerankers
   `-- ledger de runs e auditoria
```

Se o Bioma já usa PostgreSQL, o caminho inicial recomendado é:

- PostgreSQL como fonte de verdade;
- busca lexical nativa ou engine já adotada pela EG;
- `pgvector` somente quando embeddings reais estiverem configurados;
- object storage compatível com S3 para arquivos originais;
- fila existente do Bioma para extração, OCR, embeddings e reindexação;
- API HTTP/JSON documentada em OpenAPI.

Não crie um microsserviço novo apenas por estética arquitetural. Se o backoffice é um monólito modular bem mantido, o domínio pode começar dentro dele, atrás de interfaces estáveis.

## 4. Modelo de domínio mínimo

Toda entidade empresarial deve carregar `organization_id` e, quando aplicável, `workspace_id`. A autorização não pode depender apenas de filtros enviados pela interface.

### `knowledge_bases`

- `id`
- `organization_id`
- `workspace_id`
- `name`
- `description`
- `chunk_strategy`
- `retrieval_policy`
- `status`: `active | archived`
- `created_by`
- `created_at`, `updated_at`

### `knowledge_documents`

- `id`
- `base_id`
- `title`
- `source_type`: `upload | note | url | connector | manual`
- `status`: `queued | extracting | ready | disabled | error`
- `current_version_id`
- `word_count`, `chunk_count`, `hit_count`
- `created_by`
- `created_at`, `updated_at`

### `document_versions`

- `id`
- `document_id`
- `version`
- `object_key` ou referência segura à origem
- `media_type`, `byte_count`, `sha256`
- `source_uri`
- `extraction_method`, `extraction_status`, `extraction_message`
- `metadata_json`
- `created_at`

### `knowledge_chunks`

- `id`
- `document_version_id`
- `position`
- `heading`
- `content`
- `char_count`, `token_count`
- `source_locator`: página, seção, timestamp ou linhas
- `sha256`
- `is_enabled`
- `created_at`, `updated_at`

### `chunk_embeddings`

- `chunk_id`
- `provider`, `model`, `dimensions`
- `vector`
- `content_checksum`
- `created_at`, `updated_at`

O embedding só é válido se seu checksum corresponder ao conteúdo atual do fragmento.

### `ingestion_runs`

- origem, hash e tamanho;
- status e etapa atual;
- extrator e versão;
- warnings e erro sanitizado;
- duração e timestamps;
- documento/versão produzidos.

### `retrieval_runs` e `retrieval_hits`

- consulta original e consulta normalizada;
- base, filtros e política;
- candidatos lexical e semântico;
- método de fusão e reranking;
- ranking, scores e fragmentos retornados;
- duração, custo e versão dos modelos;
- autor, agente ou workflow solicitante.

### `context_personas` e `persona_bases`

- identidade e instruções da persona;
- modo de grounding: `strict | balanced | interpretive`;
- bases permitidas e prioridade;
- disclosure obrigatório de simulação;
- política de modelo e ferramentas permitidas.

Uma persona “Marco Aurélio” representa uma perspectiva fundamentada nas fontes. Ela não deve alegar ser a pessoa real nem inventar conteúdo ausente.

### `qa_datasets` e `qa_items`

- dataset ligado a uma base e versão de geração;
- pergunta, resposta esperada e rationale;
- fragmento e hash de origem;
- status de revisão: `proposed | accepted | rejected`;
- métricas e resultados por versão do pipeline.

## 5. Contrato de API sugerido

Os nomes podem mudar para o padrão do Bioma; a semântica deve permanecer.

```text
POST   /v1/knowledge-bases
GET    /v1/knowledge-bases
GET    /v1/knowledge-bases/{baseId}
PATCH  /v1/knowledge-bases/{baseId}

POST   /v1/knowledge-bases/{baseId}/sources
GET    /v1/knowledge-bases/{baseId}/documents
GET    /v1/documents/{documentId}
POST   /v1/documents/{documentId}/reindex
PATCH  /v1/documents/{documentId}

GET    /v1/documents/{documentId}/chunks
PATCH  /v1/chunks/{chunkId}

POST   /v1/knowledge-bases/{baseId}/retrieve
GET    /v1/retrieval-runs/{runId}

POST   /v1/context-personas
PATCH  /v1/context-personas/{personaId}
POST   /v1/context-personas/{personaId}/query

POST   /v1/knowledge-bases/{baseId}/qa-datasets
GET    /v1/qa-datasets/{datasetId}/items
PATCH  /v1/qa-items/{itemId}

GET    /v1/ingestion-runs/{runId}
POST   /v1/ingestion-runs/{runId}/retry
```

### Exemplo de recuperação

```json
{
  "query": "Qual é a política de aprovação de fornecedores?",
  "limit": 8,
  "filters": {
    "documentIds": [],
    "tags": [],
    "createdAfter": null
  },
  "mode": "hybrid",
  "rerank": true
}
```

Resposta mínima:

```json
{
  "runId": "run_...",
  "modeActuallyUsed": "lexical",
  "capabilities": {
    "lexical": "ready",
    "dense": "unavailable",
    "reranker": "unavailable"
  },
  "hits": [
    {
      "chunkId": "chunk_...",
      "documentId": "doc_...",
      "documentTitle": "Política de compras",
      "sourceLocator": "p. 12, Aprovação",
      "excerpt": "...",
      "rank": 1,
      "scores": {
        "lexical": 0.82,
        "dense": null,
        "fused": 0.82,
        "rerank": null
      },
      "sourceSha256": "..."
    }
  ]
}
```

O campo `modeActuallyUsed` evita afirmar que houve busca híbrida quando embeddings ou reranker não estavam disponíveis.

## 6. Pipeline de ingestão

### Formatos da primeira entrega

1. Markdown e texto simples;
2. PDF com texto selecionável;
3. PDF escaneado por OCR como fallback explícito;
4. DOCX;
5. HTML e páginas capturadas.

CSV, JSON e YAML podem ser úteis para dados estruturados, mas exigem uma política própria para não transformar linhas sem contexto em fragmentos ruins.

### Etapas

1. validar autorização, MIME real, extensão, tamanho e malware;
2. armazenar a origem imutável e calcular SHA-256;
3. extrair texto preservando página, título, seção e ordem;
4. normalizar sem apagar semântica útil;
5. separar frontmatter e metadados do corpo pesquisável;
6. fragmentar respeitando títulos, parágrafos e marcadores manuais;
7. manter pequeno overlap somente quando necessário;
8. persistir fragmentos e seus localizadores;
9. atualizar índice lexical;
10. calcular embeddings se houver provider configurado;
11. executar testes básicos e publicar o documento como `ready`;
12. registrar todo o run e warnings.

O marcador `---` pode ser aceito como uma indicação editorial de quebra, mas não deve ser a única estratégia. O pipeline deve priorizar estrutura do documento e permitir inspeção/correção humana.

## 7. Recuperação recomendada

### Versão 1

- busca lexical BM25/full-text;
- filtros por base, documento, tipo, data e metadados;
- deduplicação de resultados;
- citações com localização e hash;
- console de teste e registro de runs.

### Versão 2

- embeddings reais e versionados;
- busca vetorial;
- fusão por Reciprocal Rank Fusion (RRF);
- reranker opcional;
- expansão de consulta controlada;
- avaliação por dataset antes de promover a nova versão.

Não presuma que busca vetorial é sempre superior. Consultas com nomes, códigos e termos exatos frequentemente dependem fortemente da busca lexical.

## 8. Interface mínima

### Lista de bases

- nome, descrição, status, documentos, fragmentos e volume de uso;
- responsáveis e escopo organizacional;
- indicador real das capacidades: lexical, embeddings, reranker e OCR.

### Dentro de uma base

- `Documentos`: fontes, versões, status, erros e reindexação;
- `Fragmentos`: inspeção, edição, ativação e localização na origem;
- `Recuperação`: consulta de teste, ranking, scores e citações;
- `Personas`: instruções, bases autorizadas e disclosure;
- `Avaliações`: datasets Q&A, revisão e métricas;
- `Configurações`: chunking, retrieval, modelos, retenção e permissões.

O usuário deve conseguir abrir um resultado e chegar ao fragmento e à página original que o sustentam.

## 9. Segurança e governança obrigatórias

- autorização server-side por organização, workspace, base e ação;
- isolamento de tenant em todas as queries e jobs;
- RLS no PostgreSQL quando compatível com a arquitetura adotada;
- URLs assinadas e curtas para arquivos; bucket nunca público;
- segredos em cofre próprio, nunca em prompts ou banco em texto aberto;
- MIME sniffing, limites de tamanho, antivírus e proteção contra zip bombs;
- conteúdo recuperado tratado como dado não confiável, não como instrução do sistema;
- defesa contra prompt injection em fontes;
- logs sem conteúdo sensível por padrão;
- trilha de auditoria de upload, leitura, alteração, consulta e exportação;
- retenção, exclusão e reindexação compatíveis com LGPD;
- exportação entre Fóton e Bioma somente por escopo explicitamente autorizado.

## 10. Critérios de aceite do primeiro corte vertical

Uma entrega inicial está pronta quando:

1. um usuário autorizado cria uma base;
2. envia um PDF ou Markdown;
3. acompanha a ingestão e vê erros reais;
4. inspeciona fragmentos e sua localização na origem;
5. desativa ou corrige um fragmento;
6. pesquisa e recebe resultados relevantes com citações;
7. um usuário de outra organização não consegue enumerar nem recuperar os dados;
8. uma persona consulta somente as bases autorizadas;
9. o run registra pipeline, scores, fontes e duração;
10. golden tests e testes de isolamento passam no CI.

## 11. Plano de implementação recomendado

### Fase 0 — contrato e segurança

- confirmar stack, tenancy e autenticação do Bioma;
- produzir OpenAPI, schemas e matriz de permissões;
- criar fixtures sintéticas e golden tests;
- decidir storage, fila e worker.

### Fase 1 — corte vertical lexical

- base → upload → extração → chunks → inspeção → BM25/full-text → citações;
- Markdown e PDF com texto;
- ledger de ingestão e recuperação;
- UI administrativa mínima.

### Fase 2 — personas e avaliações

- vínculo persona/base;
- resposta grounded com disclosure;
- datasets de Q&A revisáveis;
- recall@k, MRR/nDCG e taxa de citação válida.

### Fase 3 — retrieval híbrido

- provider de embeddings;
- backfill idempotente;
- busca vetorial, RRF e reranker;
- comparação contra o baseline lexical.

### Fase 4 — conectores e automação

- Google Drive, Notion, sites e sistemas da EG conforme prioridade;
- sincronização incremental e versionamento;
- políticas por agente/workflow;
- alertas de fontes desatualizadas.

## 12. Estado da referência no Fóton 0.8.15

Já existe no Fóton:

- bases, notas/documentos e fragmentos;
- edição e ativação de chunks;
- SQLite FTS5/BM25;
- registro de retrieval runs e hits;
- estrutura para embeddings e retrieval híbrido honesto;
- proveniência e hashes de ingestão;
- personas ligadas a bases com disclosure;
- propostas de Q&A auditáveis e revisão;
- UI inicial de documentos, personas, pipeline, recuperação, Q&A e configurações.

Limitações atuais que não devem ser copiadas como requisitos do Bioma:

- arquitetura single-user/local;
- documentos nativos originalmente ligados a notas do Fóton;
- ingestão real pronta para Markdown, TXT, CSV, JSON, YAML e HTML;
- PDF, EPUB e DOCX ainda reportados como indisponíveis, sem fingir extração;
- embeddings e reranker dependem de provider real e podem estar indisponíveis;
- personas atuais produzem dossiê grounded sem se passar por uma LLM quando não há provider;
- não existe ainda tenancy empresarial completa.

Arquivos de referência no repositório:

```text
apps/foton-desktop/src-tauri/src/commands/context.rs
apps/foton-desktop/src-tauri/src/commands/context/ingestion.rs
apps/foton-desktop/src-tauri/src/commands/context/retrieval.rs
apps/foton-desktop/src-tauri/src/commands/context/persona.rs
apps/foton-desktop/src-tauri/src/commands/context/qa.rs
apps/foton-desktop/src-tauri/src/db/context_migrations.rs
apps/foton-desktop/src/components/knowledge/ContextBasesWorkspace.tsx
apps/foton-desktop/src/lib/contextRepository.ts
FOTON_CONTEXT_ENGINE_PORTABILITY.md
```

Esses arquivos devem ser tratados como implementação de referência, não como pacote copiável para produção empresarial.

## 13. Pacote que deve acompanhar este handoff

Antes da implementação, o time deve acrescentar:

```text
context-engine-contract/
  README.md
  api/openapi.yaml
  domain/*.schema.json
  migrations/reference-schema.sql
  fixtures/documents/*
  fixtures/expected-chunks.json
  fixtures/expected-retrieval.json
  evals/questions.jsonl
  evals/relevance-judgments.jsonl
  security/threat-model.md
  security/permission-matrix.md
  ui/flows.md
  decisions/ADR-*.md
```

Não inclua vault real, banco SQLite de produção, tokens, embeddings privados ou screenshots com segredos.

## 14. Prompt pronto para o time/copiloto do Bioma

```text
Implemente no backoffice da EG o Knowledge & Context Engine descrito em
EG_CONTEXT_ENGINE_FEATURE_HANDOFF.md.

Não copie mecanicamente a implementação Tauri/Rust/SQLite do Fóton. Use-a apenas
como referência de comportamento. Adapte a solução à stack e aos padrões já
existentes no Bioma.

Antes de editar código:
1. mapeie autenticação, tenancy, banco, object storage, filas, observabilidade e
   convenções de API do Bioma;
2. proponha o corte vertical mínimo e registre divergências do contrato;
3. produza OpenAPI, modelo de dados, matriz de permissões e threat model;
4. confirme como organization_id/workspace_id serão aplicados server-side.

Implemente primeiro o fluxo completo:
criar base -> enviar Markdown/PDF -> extrair -> fragmentar -> inspecionar chunks
-> pesquisar lexicalmente -> abrir citação na origem -> registrar o run.

Exija testes de autorização entre tenants, idempotência, golden tests de chunking
e retrieval, erros honestos para capabilities indisponíveis e auditoria. Não
afirme que embeddings, OCR, reranker ou busca híbrida funcionam antes de haver
provider real, testes e telemetria.

Entregue ao final:
- diff e decisões arquiteturais;
- migrations e rollback;
- OpenAPI e schemas;
- testes e resultados;
- riscos restantes;
- instruções de operação e backup.
```

## 15. Decisão de integração Fóton ↔ Bioma

Fóton e Bioma devem manter bancos e políticas separados:

- Fóton: contexto pessoal, vida, decisões e conhecimento privado;
- Bioma: contexto empresarial, operações, clientes, equipes e permissões corporativas;
- integração: capability/API com consentimento, escopo, finalidade, expiração e auditoria;
- nenhum dos dois deve montar diretamente o banco interno do outro.

O artefato transferido deve ser um dossiê ou pacote de contexto explicitamente selecionado, com fontes e hashes, e não uma cópia silenciosa de toda a memória pessoal.
