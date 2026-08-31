-- Correção de modelo: um artigo é UM post no CMS, não um post por versão.
--
-- A 0094 tornou a publicação única por `(artifact_id, version, target_id)`. Isso
-- descreve "cada versão vira um post", que não é o que acontece nem o que se
-- quer: publicar a v3 de um artigo deve ATUALIZAR o post que a v1 criou, não
-- encher o blog do cliente com três artigos quase iguais.
--
-- O bug era pior que o modelo: `create_post` sempre fazia `POST /posts`, então
-- republicar criava post duplicado no site do cliente enquanto o banco
-- sobrescrevia o `external_id` em silêncio — perdendo o rastro do primeiro. E a
-- tela afirmava, em texto, que republicar "atualiza o mesmo post".
--
-- Agora a linha é única por `(artifact_id, target_id)` e `version` passa a
-- significar **qual versão está no ar agora**, que é a pergunta que a tela faz.
-- O histórico de quem publicou o quê e quando continua na trilha de auditoria
-- (`cms.published`), que é onde ele pertence.

-- Sobra de execuções anteriores: fica a mais recente de cada par, que é a que
-- corresponde ao post realmente no ar.
delete from artifact_publications p
where exists (
  select 1 from artifact_publications outra
  where outra.artifact_id = p.artifact_id
    and outra.target_id = p.target_id
    and (outra.published_at, outra.id) > (p.published_at, p.id)
);

alter table artifact_publications
  drop constraint if exists artifact_publications_artifact_id_version_target_id_key;

alter table artifact_publications
  add constraint artifact_publications_artifact_target_key
  unique (artifact_id, target_id);
