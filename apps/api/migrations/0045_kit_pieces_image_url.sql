-- 0045_kit_pieces_image_url.sql: Adiciona campo de foto/imagem em kit_pieces

alter table kit_pieces add column if not exists image_url text;
