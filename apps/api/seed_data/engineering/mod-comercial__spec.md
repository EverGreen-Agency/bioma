# Spec: mod-comercial

- **Cliente:** EverGreen, uso interno (`target: internal`, plataforma)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-comercial`, `carteira-clientes`, `squad-prospector`, `squad-hunter`, `squad-reunioes`, `squad-onboarding`, `matriz-risco-comercial`, `copilot-vendas`, `kommo-squad-dedup`, `centralizacao-comunicacoes`, `integ-google-meu-negocio`, `demo-tenant-sales-theater`

## 1. Objetivo

Unificar captação, qualificação, proposta, fechamento e onboarding comercial da EverGreen em uma superfície própria, sem perder integrações úteis com Kommo, ClickUp, Google, Meta e squads existentes.

## 2. Contexto

Hoje a jornada comercial da EG vive em squads, conversas, CRMs externos, planilhas, ClickUp e memória do time. O objetivo não é criar um CRM genérico no dia 1, e sim uma camada comercial premium da EG que use dados, risco, histórico e IA para vender melhor, reduzir retrabalho e preparar o cliente para entrar no Bioma.

## 3. Escopo

O que será construído:

- Carteira de leads, oportunidades e clientes.
- Pipeline de negócios high-ticket com estágios customizados.
- Matriz de risco comercial antes de proposta/fechamento.
- Integração com squads de prospecção, propostas, reuniões e onboarding.
- Registro de reuniões, transcrições, objeções, próximos passos e SPICED/SPIN.
- Copilot de vendas como feature futura, com modo privado/vendedor e modo apresentação/cliente.
- Motor de onboarding comercial: contrato, tenant, acessos, ClickUp, Drive, Hub, kit.
- Deduplicação/normalização de dados vindos de Kommo quando necessário.
- Integração com Google Meu Negócio e ativos de marketing do cliente quando fizer sentido.
- Demo Tenant / Sales Theater para pitch, treinamento comercial e demonstração sem dados reais de clientes.

## 4. Fora de Escopo

- Substituir Kommo/Apollo imediatamente sem ADR.
- Fazer disparo frio em massa sem conformidade e aprovação.
- Automatizar fechamento sem humano.
- Criar call center, discador ou operação SDR completa no MVP.
- Prometer previsibilidade de receita ao cliente; o sistema apoia decisão, não garante faturamento.

## 5. Requisitos Funcionais

- RF1 — Usuário EG deve cadastrar lead, empresa, contatos, origem e estágio.
- RF2 — Oportunidade deve ter score/riscos mínimos antes de avançar para proposta.
- RF3 — Sistema deve anexar transcrições e resumos de reunião ao deal.
- RF4 — Sistema deve gerar ou acionar rascunho de proposta via squad apropriado.
- RF5 — Ao marcar `Closed Won`, sistema deve disparar checklist de onboarding.
- RF6 — Onboarding deve criar/solicitar tenant, contrato, acessos, pasta/drive, ClickUp e Hub conforme etapa.
- RF7 — Sistema deve registrar objeções e aprendizados para `mod-conhecimento`.
- RF8 — Sistema deve detectar possíveis duplicidades de leads/contatos importados de Kommo.
- RF9 — Sistema deve registrar comunicação principal por deal, mesmo que a conversa continue em WhatsApp/ClickUp.
- RF10 — Sistema deve distinguir lead, cliente ativo, cliente legado, parceiro e reseller.
- RF11 — Sistema deve permitir acesso a um tenant demo com dados fictícios para apresentação comercial e treinamento.

## 6. Requisitos Não-Funcionais

- **Segurança:** dados comerciais e gravações restritos por papel; auditoria em mudanças de estágio crítico.
- **Integrações:** toda integração externa deve passar por `mod-integrations-hub` e segredos por `cofre-senhas`.
- **Operação:** pipeline deve funcionar mesmo com integrações externas indisponíveis, com fallback manual.
- **UX:** foco em deal high-ticket; evitar CRM massivo inchado.
- **Dados:** deduplicação precisa preservar histórico, não apagar conversas sem revisão.

## 7. Critérios de Aceite

- CA1 — Um lead pode ser convertido em oportunidade, proposta e cliente ativo com histórico preservado.
- CA2 — Deal sem campos mínimos de risco não avança para proposta sem override auditado.
- CA3 — Um `Closed Won` cria checklist de onboarding com responsáveis e dependências.
- CA4 — Uma transcrição de reunião fica associada ao deal e pode alimentar RAG com tenant correto.
- CA5 — Duplicidades vindas de Kommo são sugeridas para revisão antes de merge.
- CA6 — O sistema registra quem alterou estágio, valor, escopo e status contratual.

## 8. Riscos e Dependências

- **Risco:** tentar competir com CRMs maduros antes de validar o fluxo EG.  
  **Mitigação:** construir camada de deal/onboarding primeiro; contato massivo pode continuar externo.

- **Risco:** automações criarem dados errados em tenant/ClickUp/Drive.  
  **Mitigação:** checklist com aprovação e logs por etapa.

- **Dependência:** `mod-multitenant` para usuários/tenant/RBAC.
- **Dependência:** `mod-contratos` para contrato.
- **Dependência:** `cofre-senhas` para acessos de cliente.
- **Dependência:** ADR build-vs-Kommo/Apollo.
