-- Migration 0031: AI Content Multimodal (Artes, Vídeos & Roteiros)

alter table ai_content_requests
  drop constraint if exists ai_content_requests_content_type_check;

alter table ai_content_requests
  add constraint ai_content_requests_content_type_check
  check (content_type in ('social_posts', 'image_generation', 'video_scripts'));
