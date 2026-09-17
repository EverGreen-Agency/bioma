-- Duas correções que vieram da revisão do Eduardo (2026-07-31).

-- 1) BUG: o seeder tinha guard de sobrescrita apenas em `eg_knowledge_docs`.
--    Ideias e stack seriam REVERTIDAS ao conteúdo do arquivo a cada boot em
--    produção — toda edição feita na tela se perderia no próximo deploy.
--    Mesma marca de proveniência das outras tabelas: enquanto `seeded` for
--    true, o seeder pode atualizar; na primeira edição pelo produto vira false
--    e o registro passa a ser intocável pelo deploy.
alter table eg_ideas add column if not exists seeded boolean not null default true;
alter table eg_stack_techs add column if not exists seeded boolean not null default true;

-- 2) Tarefas não tinham controle de visibilidade — só comentários tinham.
--    Sem isso, misturar entrega do cliente com trabalho interno no mesmo board
--    expõe o interno. `true` como padrão preserva o comportamento atual (o
--    cliente já enxerga o board); o que nasce interno marca false.
alter table eg_tasks add column if not exists client_visible boolean not null default true;

create index if not exists idx_eg_tasks_client_visible
  on eg_tasks (list_id) where client_visible = false;
