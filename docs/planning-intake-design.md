# Intake de planejamento versionada

## Decisão

O planejamento não cria outro cadastro de cliente e não substitui o contrato. O
cliente continua sendo o `workspace` canônico, o perfil reúne fatos duráveis e
o contrato define o escopo comercial. A intake é uma fotografia versionada do
contexto de uma iniciativa, usada para gerar e auditar um backlog candidato.

Isso absorve a parte útil do fluxo de referência recebido em 27/07/2026 sem
copiar sua navegação, suas telas ou seus campos inconsistentes.

## Fluxo

1. A equipe abre ou cria um projeto dentro do workspace já existente. Para um
   cliente novo, usa o wizard canônico; não há modal concorrente de cliente.
2. A equipe salva uma intake em rascunho. Ler exige `view`; criar, editar e
   finalizar exigem `manage_work`. Usuário de cliente não recebe intake
   estratégica interna.
3. A API valida a variante de formulário no servidor e finaliza a intake.
4. A geração de plano recebe a intake finalizada, inclui sua fotografia no
   contexto do squad e persiste a mesma fotografia no plano gerado.
5. A IA apenas sugere candidatos. A equipe seleciona, edita, aprova e só então
   materializa fases e entregas. O cliente vê somente o plano aprovado e os
   candidatos selecionados e visíveis.

## Modelo de formulário

As variantes são definidas no servidor e possuem `schema_key` e
`schema_version`. Nunca se aceita um esquema arbitrário do navegador: isso
evita que regras, opções e texto de prompt virem dados não auditáveis.

`retail_v1` é a primeira variante e cobre os sinais observados no fluxo de
referência: categorias, canais, ticket, fidelidade, uso de CRM/ERP, maturidade
e objetivo prioritário de marketing e comercial. Os objetivos permitidos mudam
com a maturidade selecionada. A validação rejeita uma meta antiga quando a
maturidade é alterada.

O núcleo comum é título e objetivo. Variantes futuras (tech, saúde, social e
growth) entram por novo `schema_key`, sem transformar o varejo em formulário
universal. Campos duráveis descobertos na intake só passam ao perfil do cliente
mediante ação explícita de atualização; a intake nunca sobrescreve o perfil.

## Regras de produto e segurança

- Rascunhos podem ser alterados; uma intake finalizada é imutável. Para mudar o
  contexto, cria-se nova intake e novo plano/versionamento.
- A geração não depende de população de dados de demonstração nem aplica
  migrações automaticamente.
- A fotografia persistida tem respostas normalizadas e o resumo derivado de
  maturidade, junto com contrato, documentos e perfil já usados pelo planner.
- O módulo não promete decisão autônoma: saída de IA continua candidata,
  revisável e auditada.

## Próximas variantes

1. `tech_v1`: fase contratual, documento técnico, integrações, ambiente,
   critérios de aceite/teste e estratégia de issues GitHub com confirmação.
2. `growth_social_v1`: canais, cadência, funil, restrições de marca e fluxo de
   aprovação adaptável por cliente.
3. Proposta e copiloto comercial consomem a fotografia autorizada, mas não
   recebem credenciais do cofre nem fatos não confirmados.
