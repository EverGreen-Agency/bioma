-- Reserva local e reconciliação de escritas externas no GitHub.
alter table deliverables
  add column if not exists github_issue_write_status text not null default 'idle'
    check (github_issue_write_status in ('idle', 'pending', 'completed', 'failed')),
  add column if not exists github_issue_write_error text,
  add column if not exists github_issue_write_requested_at timestamptz;
