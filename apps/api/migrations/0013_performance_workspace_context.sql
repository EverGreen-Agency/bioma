-- DATA-WS-001B: identidade canônica de workspace na camada de Performance.
--
-- `client_id` permanece durante a transição. Um trigger garante dual-write e
-- rejeita pares client/workspace inconsistentes, permitindo migrar leitores
-- sem interromper workers, seeds ou integrações existentes.

do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'gtm_audit_snapshots'
      and column_name = 'workspace_id'
      and data_type = 'text'
  ) and not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'gtm_audit_snapshots'
      and column_name = 'gtm_workspace_id'
  ) then
    alter table gtm_audit_snapshots rename column workspace_id to gtm_workspace_id;
  end if;
end $$;

do $$
declare
  table_name text;
  performance_tables text[] := array[
    'sync_runs',
    'performance_connections',
    'monthly_targets',
    'ads_campaign_daily',
    'ads_keyword_daily',
    'ads_search_term_daily',
    'ads_segment_daily',
    'ads_conversion_daily',
    'ga4_acquisition_daily',
    'ga4_landing_page_daily',
    'ga4_event_daily',
    'ga4_device_daily',
    'gsc_query_daily',
    'gsc_page_daily',
    'gtm_audit_snapshots',
    'tracking_findings',
    'performance_insights',
    'analyst_actions'
  ];
begin
  foreach table_name in array performance_tables loop
    execute format(
      'alter table %I add column if not exists workspace_id uuid references workspaces(id) on delete cascade',
      table_name
    );
    execute format(
      'update %I target set workspace_id = w.id from clients c join workspaces w on w.subject_organization_id = c.organization_id where target.client_id = c.id and target.workspace_id is null',
      table_name
    );
    execute format(
      'create index if not exists %I on %I (workspace_id)',
      table_name || '_workspace_idx',
      table_name
    );
  end loop;
end $$;

do $$
declare
  table_name text;
  has_missing boolean;
  required_tables text[] := array[
    'performance_connections',
    'monthly_targets',
    'ads_campaign_daily',
    'ads_keyword_daily',
    'ads_search_term_daily',
    'ads_segment_daily',
    'ads_conversion_daily',
    'ga4_acquisition_daily',
    'ga4_landing_page_daily',
    'ga4_event_daily',
    'ga4_device_daily',
    'gsc_query_daily',
    'gsc_page_daily',
    'gtm_audit_snapshots',
    'tracking_findings',
    'performance_insights',
    'analyst_actions'
  ];
begin
  foreach table_name in array required_tables loop
    execute format('select exists (select 1 from %I where workspace_id is null)', table_name)
      into has_missing;
    if has_missing then
      raise exception 'Backfill de workspace incompleto em %', table_name;
    end if;
    execute format('alter table %I alter column workspace_id set not null', table_name);
  end loop;
end $$;

create or replace function enforce_performance_workspace_context()
returns trigger
language plpgsql
as $$
declare
  resolved_workspace_id uuid;
begin
  if new.client_id is null then
    return new;
  end if;

  select w.id
  into resolved_workspace_id
  from clients c
  join workspaces w on w.subject_organization_id = c.organization_id
  where c.id = new.client_id;

  if resolved_workspace_id is null then
    raise exception 'Cliente % não possui workspace canônico.', new.client_id;
  end if;

  if new.workspace_id is null then
    new.workspace_id := resolved_workspace_id;
  elsif new.workspace_id <> resolved_workspace_id then
    raise exception 'Workspace % não pertence ao cliente %.', new.workspace_id, new.client_id;
  end if;

  return new;
end;
$$;

do $$
declare
  table_name text;
  performance_tables text[] := array[
    'sync_runs',
    'performance_connections',
    'monthly_targets',
    'ads_campaign_daily',
    'ads_keyword_daily',
    'ads_search_term_daily',
    'ads_segment_daily',
    'ads_conversion_daily',
    'ga4_acquisition_daily',
    'ga4_landing_page_daily',
    'ga4_event_daily',
    'ga4_device_daily',
    'gsc_query_daily',
    'gsc_page_daily',
    'gtm_audit_snapshots',
    'tracking_findings',
    'performance_insights',
    'analyst_actions'
  ];
begin
  foreach table_name in array performance_tables loop
    execute format('drop trigger if exists performance_workspace_context_trigger on %I', table_name);
    execute format(
      'create trigger performance_workspace_context_trigger before insert or update of client_id, workspace_id on %I for each row execute function enforce_performance_workspace_context()',
      table_name
    );
  end loop;
end $$;
