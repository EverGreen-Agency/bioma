-- Acervo de cases da EG — fonte única para as LPs, o portfólio e as propostas.
--
-- Hoje o mesmo case existe em três lugares que divergem entre si: o array
-- `casesPt/casesEn` de `src/app/growth/data.ts`, o de `src/app/tech/data.ts` e
-- o `portfolioItems` de `src/config/portfolio.ts` — todos no repo do site. Editar
-- um número exige deploy, e nada garante que os três concordem.
--
-- **O motivo real de virem para o banco não é conveniência de edição.** É a
-- autorização. Hoje `leadConsent` é um campo OPCIONAL num array TypeScript: quem
-- esquece de preencher publica assim mesmo. A auditoria de 2026-08-27 encontrou a
-- /growth no ar publicando funil, custo por tratamento e faixa de ticket de
-- cliente nomeado, indexável, sem nenhuma trilha de autorização.
--
-- Aqui isso vira trava: `status` só pode ser 'published' quando o caso não expõe
-- terceiro OU tem autorização registrada. É `check` de banco, não disciplina.
--
-- O site mantém os arrays TypeScript como fallback — uma apresentação comercial
-- não pode ficar em branco porque a API estava reiniciando.

create table if not exists eg_cases (
  id uuid primary key default gen_random_uuid(),

  deck text not null check (deck in ('growth', 'tech', 'ambos')),
  slug text not null,
  display_order int not null default 0,

  -- exposição de terceiro
  client_named   boolean not null default false,
  consent_status text not null default 'none'
    check (consent_status in ('none', 'requested', 'granted', 'waived', 'not_applicable')),
  consent_note   text,
  consent_at     timestamptz,
  consent_by     uuid references users(id) on delete set null,

  status text not null default 'draft'
    check (status in ('draft', 'retained', 'published', 'archived')),

  -- a trava: nada com cliente nomeado e sem autorização sai como publicado
  constraint eg_cases_consent_gate check (
    status <> 'published'
    or client_named = false
    or consent_status in ('granted', 'waived', 'not_applicable')
  ),

  seeded     boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  updated_by uuid references users(id) on delete set null,

  unique (deck, slug)
);

-- Conteúdo por idioma. PT e EN são linhas irmãs, não colunas — foi a estrutura de
-- colunas paralelas que deixou o deck em inglês com metade do conteúdo por semanas
-- sem ninguém notar.
create table if not exists eg_case_translations (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references eg_cases(id) on delete cascade,
  lang text not null check (lang in ('pt', 'en')),

  name       text not null,
  category   text not null,
  headline   text not null,
  metric     text not null,
  evidence   text not null,
  highlights jsonb not null default '[]'::jsonb,

  -- mesmo formato de CaseContentSection no site: label, title e blocks[]
  sections jsonb not null default '[]'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  unique (case_id, lang)
);

create index if not exists eg_cases_deck_status_idx on eg_cases (deck, status, display_order);
create index if not exists eg_case_translations_case_idx on eg_case_translations (case_id, lang);

comment on constraint eg_cases_consent_gate on eg_cases is
  'Case com cliente nomeado só publica com autorização registrada. Ver auditoria de 2026-08-27.';
