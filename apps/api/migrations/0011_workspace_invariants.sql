-- WORKSPACE-001 hardening: aplica os invariantes revisados também em bancos
-- locais que tenham executado uma versão inicial de 0010_workspaces.sql.

do $$
begin
  if exists (
    select 1
    from organizations child
    left join organizations tenant on tenant.id = child.parent_organization_id
    where child.type = 'client'
      and (
        tenant.id is null
        or child.parent_organization_id = child.id
        or tenant.type not in ('eg', 'agency')
      )
  ) then
    raise exception 'Organização cliente sem tenant válido (EG ou agência).';
  end if;
end $$;

-- O slug do tenant é globalmente único em organizations e, portanto, não
-- colide com o slug de um cliente dentro do mesmo tenant.
update workspaces w
set slug = subject.slug,
    updated_at = now()
from organizations subject
where w.kind = 'agency_internal'
  and subject.id = w.subject_organization_id
  and w.slug <> subject.slug;

alter table workspaces drop constraint if exists workspaces_internal_subject_check;
alter table workspaces
  add constraint workspaces_internal_subject_check check (
    kind <> 'agency_internal' or tenant_organization_id = subject_organization_id
  );
