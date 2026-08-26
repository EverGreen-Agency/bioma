# Decisões decididas — fila de implementação

Atualizado em 2026-08-24.

**O que está aqui já foi respondido e não precisa voltar a ser perguntado.** O
que falta é construir.

Quando um item for implementado, ele desce para
[DECISOES-FECHADAS.md](DECISOES-FECHADAS.md) com uma linha do que ficou
valendo.

| # | Decisão | O que ficou valendo | Estado |
|---|---|---|---|
| 7 | Context Engine | base da EG **e** do cliente. Corte vertical da Fase 1, sem embeddings. | **não construído** — é o único item project-sized da lista |

**Correção de 2026-08-24.** Esta fila nasceu com dois erros meus, achados ao
conferir o código em vez de confiar no documento:

- a **#2 (tradução)** já estava construída — cache por proposta, invalidação ao
  editar, botão na tela e smoke próprio. Foi para FECHADAS;
- a **#10 (Notorious)** não tem trabalho de código: a decisão foi rodar como
  workspace e **não** construir multi-tenant agora. Foi para FECHADAS;
- a **#3 (resumo diário)** e a **#9 (GitHub)** foram implementadas hoje.

Era exatamente o problema que a separação em três arquivos existe para evitar —
só que na direção contrária: coisa pronta parecendo pendente.
## 7. Context Engine — por onde começar

**Contexto.** `EG_CONTEXT_ENGINE_FEATURE_HANDOFF.md` define a feature inteira em
4 fases. Não comecei porque construir metade dela é pior que não começar: uma
base de conhecimento que responde sem citar direito, ou que vaza entre
organizações, destrói a confiança em tudo que ela devolver depois.

**O que o Bioma já tem, e que encurta bastante a Fase 1:**

| Peça do contrato | O que já existe |
|---|---|
| object storage | `services/storage.py` (S3, configurado na Railway) |
| extração de texto | `attachment_text.py` — txt, md, csv, json, PDF via pypdf |
| índice lexical | Postgres full-text, nativo |
| ledger de runs | o padrão de `copilot_runs` (etapas, tokens, duração, fontes) |
| tenancy | `organization_id`/`workspace_id` em todo o esquema |
| adaptadores de modelo | plano de roteamento com cota de assinatura |

Falta, de verdade: `knowledge_bases` / `documents` / `versions` / `chunks`, o
chunking que respeita estrutura, a busca com citação que abre na origem, e a
tela de inspeção de fragmentos.

**O corte vertical que proponho** (Fase 1 do handoff, sem Fase 2-4):

1. criar base → 2. enviar Markdown/PDF → 3. extrair e fragmentar → 4. inspecionar
e desativar fragmento → 5. buscar por texto → 6. abrir a citação na origem →
7. run registrado.

Sem embeddings, sem persona, sem reranker — e a API já devolvendo
`modeActuallyUsed: "lexical"` com `capabilities.dense: "unavailable"`, para a
Fase 3 entrar sem quebrar contrato e sem ninguém achar que houve busca híbrida.

**A pergunta que trava:** a primeira base é do **cliente** (documentos da Univet,
consultáveis no hub dela) ou da **EG** (políticas, processos, contratos-modelo)?
Muda quem enxerga por padrão, e a decisão errada aqui é cara de desfazer.

`RESPOSTA (começar pela base da EG ou do cliente?):`Faça para ambos.

