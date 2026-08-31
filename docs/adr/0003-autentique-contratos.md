# ADR 0003 — Autentique como adapter de assinatura; Bioma como fonte de verdade do contrato

- Status: aceito
- Data: 2026-07-24

## Contexto

`_opensquad/_memory/banco_arquitetura/ferramentas-externas.md` registrava Autentique como "ABSORVER (avaliar)" — construir assinatura eletrônica própria. O Mega-Plataforma.md pergunta diretamente: "a gente vai absorver isso também para nós?".

Assinatura eletrônica com validade jurídica no Brasil (MP 2.200-2/2001, certificação e cadeia de custódia, carimbo de tempo) é uma capacidade regulada e não trivial de reconstruir com segurança jurídica equivalente à de um provedor especializado. Reconstruir isso do zero é um projeto por si só, com risco legal caso a implementação falhe em algum requisito de validade probatória.

O motor nativo de contratos (PROJECT-001, `ContractCreate`/`ContractSummary` em `schemas/projects.py`) já foi desenhado com `source_provider`, `external_id` e `signed_at` — campos que só fazem sentido se a intenção original já fosse "contrato vive no Bioma, assinatura pode vir de fora". Não há necessidade de schema novo.

## Decisão

**Autentique permanece externo, como adapter de assinatura.** O Bioma continua sendo o *system of record* do conteúdo do contrato — título, versão, vigência, valor, escopo, itens — consistente com a mesma linha da ADR 0002 (ClickUp/Kommo): serviços externos regulados ou especializados entram como adapters substituíveis, nunca como dono do dado canônico.

Fluxo:
1. Contrato é redigido e versionado no Bioma (já existe, PROJECT-001).
2. Ao enviar para assinatura, o Bioma cria o documento no Autentique via API e grava `source_provider='autentique'` + `external_id=<id do documento>`.
3. Quando o Autentique confirma a assinatura (webhook ou polling), o Bioma grava `signed_at` e muda `status` para `active`.
4. O PDF assinado e a cadeia de custódia continuam no Autentique — o Bioma referencia por `external_id`, não duplica o arquivo.

## Consequências

- Nenhuma migration nova: os campos já existem desde PROJECT-001.
- A escrita real (criar documento, receber webhook de assinatura) depende de credencial/API key do Autentique — **bloqueado por credencial**, mesmo padrão de INT-G-001..004. Fica registrado como `INT-AUT-001` na fila, com o mesmo tratamento: pronto para implementar assim que houver acesso de sandbox/produção.
- Não há plano de construir assinatura eletrônica própria. Se o volume ou custo do Autentique mudar o cálculo no futuro, reabrir esta ADR — não decidir por inércia.
- `mod-juridico` (validação de contrato × lei, mencionado no Mega-Plataforma.md) é uma capacidade separada — análise de risco jurídico do *texto* do contrato, não do processo de assinatura. Não faz parte desta ADR.
