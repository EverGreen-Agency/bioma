-- PROJECT-GH-002: escrita GitHub idempotente — rastreia a issue criada a
-- partir de uma entrega, para nunca criar uma segunda ao reprocessar.

alter table deliverables add column if not exists github_issue_number integer;
alter table deliverables add column if not exists github_issue_url text;
