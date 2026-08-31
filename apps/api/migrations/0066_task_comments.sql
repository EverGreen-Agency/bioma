-- Migration 0066: comentários em tarefa.
--
-- Substitui o "chat da tarefa" do ClickUp: histórico de conversa da equipe
-- sobre aquela tarefa específica, preso a ela em vez de espalhado no WhatsApp.
--
-- Escopo desta primeira versão: comentário em texto, autor e data. Anexos,
-- áudio, clipe de vídeo e menção a IA ficam de fora de propósito — o ClickUp
-- tinha, mas nenhum é necessário para o histórico deixar de se perder, e cada
-- um é um subsistema próprio (upload, storage, transcrição).
--
-- `client_visible` existe porque o Hub do Cliente é o mesmo lugar onde ele
-- aprova entregas: sem a coluna, todo comentário interno da EG apareceria
-- para o cliente. Padrão é FALSE (interno).

create table if not exists eg_task_comments (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references eg_tasks(id) on delete cascade,
  author_id uuid references users(id) on delete set null,
  body text not null,
  client_visible boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists eg_task_comments_task_idx
  on eg_task_comments (task_id, created_at);

comment on column eg_task_comments.client_visible is
  'Falso = conversa interna da EG. Verdadeiro = visivel para o cliente no Hub.';
