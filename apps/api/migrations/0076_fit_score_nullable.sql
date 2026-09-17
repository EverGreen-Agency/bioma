-- Fit score deixa de ter valor padrão: nulo = "ninguém avaliou ainda".
--
-- Antes, toda oportunidade nascia com uma nota vinda de triagem por palavra-chave
-- (base 50, +7 por termo de uma lista fixa). O número parecia avaliação e não era.
-- Zero também não serve como "não avaliado" — zero é uma nota. Nulo é a verdade.
--
-- As notas existentes vieram todas daquela triagem, então são apagadas: manter
-- número inventado no banco é pior que não ter número. Avaliações de IA de
-- verdade ficam identificadas por `fit_analysis` começando com o rótulo do modo,
-- e as que existirem hoje são preservadas.

alter table opportunity_radar alter column fit_score drop default;

update opportunity_radar
set fit_score = null,
    fit_analysis = null
where fit_analysis is null
   or fit_analysis not like '🤖%';
