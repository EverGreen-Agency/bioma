-- Garante que 'ideas_docs' está presente no check constraint de category em eg_knowledge_docs
alter table eg_knowledge_docs
  drop constraint if exists eg_knowledge_docs_category_check;

alter table eg_knowledge_docs
  add constraint eg_knowledge_docs_category_check
  check (category in ('knowledge', 'engineering', 'architecture', 'company', 'blog', 'ideas_docs'));
