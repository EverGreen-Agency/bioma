create table if not exists eg_tombstones (
    entity_type text not null, -- 'idea', 'doc', 'tech'
    slug text not null,
    deleted_at timestamptz not null default now(),
    primary key (entity_type, slug)
);

-- Permite category = 'ideas_docs' em eg_knowledge_docs
alter table eg_knowledge_docs drop constraint if exists eg_knowledge_docs_category_check;
alter table eg_knowledge_docs add constraint eg_knowledge_docs_category_check 
  check (category in ('knowledge', 'engineering', 'architecture', 'company', 'ideas_docs'));
