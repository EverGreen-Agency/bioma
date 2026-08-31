-- Campos do cofre equivalentes à planilha operacional: todos os valores de acesso seguem cifrados.

alter table vault_credentials
  add column if not exists platform_url text,
  add column if not exists encrypted_email text,
  add column if not exists encrypted_other_access text;

alter table vault_credentials
  drop constraint if exists vault_has_secret_check;

alter table vault_credentials
  add constraint vault_has_secret_check check (
    encrypted_username is not null
    or encrypted_email is not null
    or encrypted_password is not null
    or encrypted_other_access is not null
    or encrypted_token is not null
    or encrypted_recovery_codes is not null
    or encrypted_notes is not null
  );
