-- An AI output may be adopted once per workspace and post index.
create unique index if not exists workspace_editorial_calendar_ai_import_uidx
  on workspace_editorial_calendar (
    workspace_id,
    (metadata->>'ai_content_request_id'),
    (metadata->>'output_index')
  )
  where metadata->>'source_type' = 'ai_content_request'
    and metadata ? 'ai_content_request_id'
    and metadata ? 'output_index';
