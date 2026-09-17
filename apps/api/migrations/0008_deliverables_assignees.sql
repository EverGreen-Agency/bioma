alter table deliverables add column if not exists assignee_emails jsonb not null default '[]'::jsonb;
