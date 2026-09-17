-- Anexos do copiloto: imagem, áudio, documento.
--
-- O arquivo em si vai para o storage (S3), como todo arquivo do Bioma. O que
-- fica aqui é o ponteiro e — quando dá para extrair — o TEXTO. Guardar o texto
-- separado do binário é o que permite o anexo funcionar com qualquer provedor:
-- um PDF vira texto no prompt e roda no Codex CLI, na cota da assinatura, sem
-- precisar de modelo com visão.
--
-- `extraction_status` é explícito porque "não deu para ler" é informação, não
-- erro a esconder: um PDF escaneado sem OCR, um áudio sem transcrição
-- configurada, e um .zip são três casos diferentes, e o usuário precisa saber
-- qual aconteceu antes de perguntar "e aí, o que você achou do arquivo?".

create table if not exists copilot_attachments (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid references copilot_threads(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,

  file_name text not null,
  content_type text not null,
  size_bytes integer not null,
  storage_key text not null,
  -- image | audio | document — decide como o conteúdo chega ao modelo.
  kind text not null check (kind in ('image', 'audio', 'document')),

  extraction_status text not null default 'pending'
    check (extraction_status in ('pending', 'extracted', 'unsupported', 'failed', 'not_needed')),
  extraction_error text,
  -- Texto legível extraído (PDF, csv, md, txt) ou transcrição (áudio).
  extracted_text text,
  -- Quantos caracteres foram cortados por caber no contexto. Zero é diferente
  -- de nulo: nulo é "não extraiu", zero é "extraiu inteiro".
  truncated_chars integer,

  created_at timestamptz not null default now()
);

create index if not exists copilot_attachments_thread_idx
  on copilot_attachments (thread_id, created_at);
create index if not exists copilot_attachments_user_idx
  on copilot_attachments (user_id, created_at desc);

-- Anexos usados em cada execução. Guardado por execução, e não só por thread,
-- porque a trilha precisa responder "o que ele tinha em mãos NAQUELE turno" —
-- anexar um arquivo depois não pode reescrever a história de uma resposta que
-- já foi dada sem ele.
alter table copilot_runs
  add column if not exists attachments jsonb not null default '[]'::jsonb;
