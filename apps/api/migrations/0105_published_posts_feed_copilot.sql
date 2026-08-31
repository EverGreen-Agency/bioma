-- Post publicado alimenta o copiloto. Rascunho não.
--
-- A migração 0104 deixou os posts fora de `eg_knowledge_docs` de propósito: aquela
-- tabela é a base que o copiloto consulta, e encher de rascunho de marketing
-- polui a fonte — ele passaria a citar como verdade da casa um texto que ainda
-- está sendo escrito.
--
-- O Eduardo apontou o outro lado, e ele está certo: **o post publicado é
-- conhecimento da casa.** Ele carrega a posição da EG sobre processo comercial,
-- sobre quando um CRM não vale, sobre o que nunca automatizar. Deixar isso fora
-- do copiloto é perder a parte mais destilada do que a empresa pensa.
--
-- A separação certa não é "post não entra", é "rascunho não entra".
--
-- Implementado por trigger, não em código de aplicação, por um motivo: publicar
-- pode acontecer por vários caminhos — a tela, o seeder, uma correção manual em
-- SQL. Regra em trigger não tem caminho que escape. Despublicar remove.

alter table eg_knowledge_docs
  drop constraint if exists eg_knowledge_docs_category_check;

alter table eg_knowledge_docs
  add constraint eg_knowledge_docs_category_check
  check (category in ('knowledge', 'engineering', 'architecture', 'company', 'blog'));

create or replace function eg_sync_published_post_to_knowledge()
returns trigger
language plpgsql
as $$
declare
  doc_path text := 'blog__' || new.slug || '.md';
  doc_body text;
begin
  if new.status = 'published' then
    -- O cabeçalho dá ao copiloto o que ele precisa para citar com contexto:
    -- que é post público, qual a keyword-alvo e onde está no ar.
    doc_body :=
      '> Post publicado no blog da EverGreen.' ||
      coalesce(' Keyword-alvo: ' || new.target_keyword || '.', '') ||
      coalesce(' Publicado em: ' || new.published_url || '.', '') ||
      chr(10) || chr(10) ||
      coalesce(new.excerpt || chr(10) || chr(10), '') ||
      new.content;

    insert into eg_knowledge_docs (path, category, title, content, seeded)
    values (doc_path, 'blog', new.title, doc_body, false)
    on conflict (path) do update set
      title = excluded.title,
      content = excluded.content,
      updated_at = now();

  elsif tg_op = 'UPDATE' and old.status = 'published' then
    -- Saiu do ar: sai da base. O copiloto não deve citar o que foi despublicado.
    delete from eg_knowledge_docs where path = doc_path and category = 'blog';
  end if;

  return new;
end;
$$;

drop trigger if exists eg_blog_posts_sync_knowledge on eg_blog_posts;

create trigger eg_blog_posts_sync_knowledge
  after insert or update of status, title, content, excerpt, published_url, target_keyword
  on eg_blog_posts
  for each row
  execute function eg_sync_published_post_to_knowledge();

-- Post apagado sai da base junto.
create or replace function eg_remove_post_from_knowledge()
returns trigger
language plpgsql
as $$
begin
  delete from eg_knowledge_docs
   where path = 'blog__' || old.slug || '.md' and category = 'blog';
  return old;
end;
$$;

drop trigger if exists eg_blog_posts_remove_knowledge on eg_blog_posts;

create trigger eg_blog_posts_remove_knowledge
  after delete on eg_blog_posts
  for each row
  execute function eg_remove_post_from_knowledge();
