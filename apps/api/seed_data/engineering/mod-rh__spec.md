# Spec: mod-rh

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-rh`, `mod-certificacoes`, `times-comerciais-ab`

## 1. Objetivo

Gerir rampagem, cultura, desempenho, responsabilidades e evolução de pessoas na EG, preparando a operação para crescer sem perder padrão.

## 2. Contexto

Hoje a EG ainda é enxuta, então RH não deve ser prioridade de código pesado. Mesmo assim, a visão do Bioma exige uma base futura para onboarding de funcionários, avaliação, certificações internas, carteira de clientes por gestor e times comerciais de teste/controle.

## 3. Escopo

O que será construído:

- Cadastro de colaboradores, papéis, alocações e permissões operacionais.
- Jornada de onboarding 15/30/60/90 dias.
- Trilhas e certificações internas.
- Avaliação de performance por entregas, carteira, cliente e cultura.
- eNPS e feedbacks internos.
- Controle de hardware comodato via `mod-logistica-kits`.
- Futuro experimento de times comerciais A/B para ICP e abordagem.

## 4. Fora de Escopo

- Folha de pagamento completa.
- Substituir contador/DP.
- Monitoramento invasivo de funcionário.
- Gamificação/jogo interno no MVP.
- Automatizar demissão ou punição por IA.

## 5. Requisitos Funcionais

- RF1 — Sistema deve cadastrar colaborador e vínculo com usuário do Bioma.
- RF2 — Sistema deve associar colaborador a papéis, squads, clientes e responsabilidades.
- RF3 — Onboarding deve gerar trilha de tarefas e checkpoints.
- RF4 — Sistema deve registrar avaliações, feedbacks e certificações.
- RF5 — Gestor deve ver carteira de clientes/projetos sob responsabilidade de cada pessoa.
- RF6 — Sistema deve integrar bônus/PLR apenas como dado para financeiro, sem cálculo definitivo no MVP.
- RF7 — eNPS deve permitir coleta anônima agregada.

## 6. Requisitos Não-Funcionais

- **Privacidade:** dados de RH altamente restritos.
- **Ética:** IA pode apoiar análise, não decidir punição/benefício sozinha.
- **Segurança:** feedbacks e eNPS com acesso segmentado.
- **Escala:** modelar simples para equipe pequena, expandir depois.

## 7. Critérios de Aceite

- CA1 — Novo colaborador recebe trilha de onboarding.
- CA2 — Gestor consegue ver clientes/projetos sob responsabilidade de um colaborador.
- CA3 — Feedback sensível não é visível para usuários sem permissão.
- CA4 — Certificação concluída fica registrada no perfil.
- CA5 — eNPS mostra resultado agregado sem expor respondente.

## 8. Riscos e Dependências

- **Risco:** módulo nascer antes de haver equipe suficiente.  
  **Mitigação:** manter spec pronta, execução posterior.

- **Risco:** cruzar performance financeira de cliente com avaliação de pessoa de forma injusta.  
  **Mitigação:** métricas como insumo, não sentença.

- **Dependência:** `mod-multitenant` para usuários/roles.
- **Dependência:** `mod-logistica-kits` para hardware.
- **Dependência:** `mod-financeiro` se houver bônus/PLR.

