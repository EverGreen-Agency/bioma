# ADR-0006: LGPD, DPA e Região de Infra

- **Status:** aprovado como guarda de risco para MVP v0
- **Data:** 2026-07-09
- **Contexto:** o MVP recomenda Railway para backend, Postgres, Redis e worker. Railway possui DPA público, mas as regiões oficiais listadas no momento não incluem Brasil.

## Decisão

Usar Railway no MVP v0 é aceitável para staging e início controlado, desde que produção com dados reais cumpra um gate jurídico/operacional:

- DPA assinado/aceito com Railway.
- Termos de uso e política de privacidade da EG alinhados.
- Mapa de dados documentando quais dados pessoais entram no Bioma.
- Registro de subprocessadores relevantes.
- Política clara de retenção, exclusão, backup e resposta a titulares.
- Avaliação de transferência internacional, se dados pessoais ficarem fora do Brasil.
- Revisão jurídica antes de dados sensíveis, credenciais reais ou volume relevante de clientes.

## Motivos

- LGPD não proíbe automaticamente usar provedor fora do Brasil, mas exige base legal, transparência, segurança e governança.
- O MVP precisa equilibrar velocidade com responsabilidade.
- Railway reduz atrito operacional, mas não elimina obrigações da EG como controladora dos dados.
- Se a exigência de residência no Brasil ficar forte, a arquitetura FastAPI/Postgres/Redis continua portável para Fly, provedor BR, RDS, Neon ou self-host.

## Risco Atual

Railway lista regiões nas Américas, Europa e Ásia-Pacífico, com opções oficiais como EUA, Amsterdam e Singapore. Brasil não aparece na lista oficial consultada em 2026-07-09.

## Consequências

- Não armazenar credenciais reais de clientes no MVP até decisão de cofre/criptografia.
- Evitar dados sensíveis em staging.
- Separar logs e mascarar PII.
- Antes de produção real: revisar DPA, política, termos, região, backups, logs e subprocessadores.
- Se residência Brasil virar requisito contratual, migrar backend e banco para provedor com região adequada.
