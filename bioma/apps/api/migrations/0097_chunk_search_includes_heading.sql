-- O título do fragmento estava FORA do índice de busca — decisão 7, Fase 1.
--
-- A 0096 guardou a trilha de títulos em `heading_path` (metadado) e indexou só
-- `content`. Resultado, pego pelo smoke na primeira execução: um fragmento sob
-- o título "Prazo de resposta" NÃO era encontrado buscando "prazo resposta",
-- porque o corpo dele diz "respondida em até quatro horas" e as palavras da
-- pergunta só existiam no título.
--
-- É erro de RECUPERAÇÃO, não de exibição: a trilha de títulos é a parte mais
-- densa de informação do fragmento — é ela que diz do que aquele pedaço TRATA —
-- e era justamente a que a busca não enxergava.
--
-- **Por que uma coluna de texto em vez de derivar do array.** A primeira versão
-- desta migração usava `array_to_string(heading_path, ' ')` dentro da coluna
-- gerada e o Postgres recusou: `array_to_string` é STABLE, não IMMUTABLE, e
-- coluna gerada exige immutable. Guardar a trilha também como texto simples,
-- escrito pela aplicação junto do fragmento, resolve sem truque — e mantém
-- `heading_path` como array, que é a forma certa para a tela mostrar a trilha.
--
-- O título entra com peso 'A' e o corpo com 'B': fragmento cujo TÍTULO casa com
-- a pergunta é mais relevante que outro que menciona o termo de passagem no
-- meio do texto, e `ts_rank` usa esse peso para ordenar.
--
-- Continua em `simple`, sem stemming. O dicionário `portuguese` existe nesta
-- instalação, mas também não resolveria este caso ("respondida" e "resposta"
-- são lemas diferentes) — trocar seria mexer numa variável que não é a causa.

alter table knowledge_chunks
  add column if not exists heading_text text not null default '';

-- Preenche o que já existe antes de indexar, senão os fragmentos antigos
-- continuariam invisíveis pelo título.
update knowledge_chunks
set heading_text = array_to_string(heading_path, ' ')
where heading_text = '' and cardinality(heading_path) > 0;

alter table knowledge_chunks drop column if exists search_vector;

alter table knowledge_chunks
  add column search_vector tsvector
  generated always as (
    setweight(to_tsvector('simple', heading_text), 'A')
    || setweight(to_tsvector('simple', content), 'B')
  ) stored;

create index if not exists knowledge_chunks_search_idx
  on knowledge_chunks using gin (search_vector);
