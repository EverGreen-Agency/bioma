# Spec: mod-bi-dashboards

- **Cliente:** EverGreen + clientes EG (`target: internal`, com superfície de produto externa)
- **Autor:** Especificador EG + revisão Codex
- **Data:** 2026-07-07
- **Status:** rascunho
- **Versão:** 1.0
- **Ideias relacionadas:** `mod-bi-dashboards`, `ads-api-skills`, `squad-relatorios`, `narrative-reports`, `selo-benchmark`, `mod-data-quality` (proposto)

## 1. Objetivo

Construir o motor de dados e visualizações que alimenta a operação interna da EG e os dashboards do `client-hub`, começando por mídia paga e evoluindo para funil, vendas, SEO/GEO, social e performance operacional.

## 2. Contexto

A EG já possui referências fortes em `abstracao-bi.md`, `meta_ads_dashboard_prompt.md` e no repo BIAds. O problema não é apenas desenhar gráficos bonitos: é coletar dados confiáveis, normalizar plataformas diferentes, preservar isolamento por tenant, explicar métricas para decisores e impedir que dados quebrados virem conclusão errada.

O módulo deve distinguir quatro camadas de análise: uso interno da EG, operação EG para clientes, visão do cliente e uso futuro de assinantes SaaS/white-label.

## 3. Escopo

O que será construído:

- Modelo de dados para contas de anúncio, campanhas, conjuntos, anúncios, criativos, métricas e snapshots históricos.
- Conectores iniciais para Meta Ads, Google Ads e LinkedIn Ads quando viável.
- Gestão de OAuth/credenciais via `cofre-senhas` e `mod-integrations-hub`.
- Workers de ingestão diária e atualização sob demanda.
- Normalização de métricas entre plataformas: spend, impressions, clicks, leads, CPL, CAC, CTR, CPM, CPC, ROAS quando disponível.
- Camada de qualidade de dados: atraso, token expirado, anomalias, duplicidade e lacunas.
- Componentes de visualização nativos para o `client-hub`.
- Relatórios executivos narrados por IA em fase posterior, com rastreabilidade do modelo/prompt.
- Export/snapshot de relatórios para histórico e prova de entregável.

## 4. Fora de Escopo

- Otimizar campanhas automaticamente sem aprovação humana.
- Substituir gerenciadores oficiais de anúncios.
- Garantir atribuição perfeita all-bound quando a fonte de dados não permite.
- Construir data warehouse corporativo completo no MVP.
- Expor dados brutos de uma plataforma para cliente sem curadoria.
- Rodar scraping proibido por termos de plataforma.

## 5. Requisitos Funcionais

- RF1 — Sistema deve cadastrar uma conexão de ads por tenant e plataforma.
- RF2 — Sistema deve armazenar tokens/segredos apenas por camada segura, nunca em JSON/git.
- RF3 — Worker deve coletar métricas por período e persistir snapshots históricos.
- RF4 — Dashboard deve filtrar dados por tenant, conta, campanha, período, plataforma e objetivo.
- RF5 — Dashboard deve exibir indicadores essenciais: gasto, leads, CPL, CTR, CPC, CPM e conversões disponíveis.
- RF6 — Sistema deve marcar a confiabilidade de cada fonte: ok, atrasada, token expirado, parcial, erro.
- RF7 — Sistema deve permitir que um relatório seja publicado no `client-hub` com versão e data.
- RF8 — Sistema deve registrar logs de coleta por job, tenant, plataforma e erro.
- RF9 — Sistema deve suportar views diferentes para EG interna, cliente e futuro reseller.
- RF10 — Sistema deve gerar insumos para `selo-benchmark` e `dossie-provas` quando houver evidência validada.

## 6. Requisitos Não-Funcionais

- **Segurança:** RLS obrigatório em tabelas de métricas; tokens criptografados; sem PII em logs.
- **Confiabilidade:** ingestão idempotente; retry controlado; dead-letter para falhas recorrentes.
- **Performance:** dashboards executivos devem carregar a partir de dados agregados/cacheados.
- **Precisão:** valores monetários em centavos/decimal; timezone do tenant explícito.
- **Observabilidade:** falha de conector deve aparecer em `mod-observabilidade`.
- **Governança:** qualquer escrita em campanha/verba fica fora do MVP e sempre HITL.

## 7. Critérios de Aceite

- CA1 — Um tenant não acessa métricas de outro tenant mesmo manipulando filtros/URLs.
- CA2 — Uma conexão Meta/Google expirada aparece como alerta operacional, não como dashboard vazio.
- CA3 — Um job de ingestão repetido para o mesmo período não duplica métricas.
- CA4 — Um relatório publicado no Hub mantém snapshot versionado, mesmo que a campanha mude depois.
- CA5 — Dashboard mostra claramente quando uma métrica é parcial ou indisponível.
- CA6 — Logs de coleta permitem identificar tenant, plataforma, job, status e motivo de falha.
- CA7 — Um usuário sem permissão financeira não vê métricas sensíveis de custo/margem interna EG.

## 8. Riscos e Dependências

- **Risco:** buscar dados em tempo real e gerar lentidão/instabilidade.  
  **Mitigação:** snapshots históricos + agregações; tempo real apenas sob demanda.

- **Risco:** métricas de plataformas diferentes parecerem equivalentes quando não são.  
  **Mitigação:** dicionário de métricas e notas de qualidade por fonte.

- **Risco:** cliente interpretar dashboard como garantia de faturamento.  
  **Mitigação:** copy e relatórios focados em indicadores, hipóteses e ações, não promessa.

- **Dependência:** `mod-multitenant` para tenant/RLS.
- **Dependência:** `cofre-senhas` para credenciais.
- **Dependência:** `mod-integrations-hub` para conectores.
- **Dependência:** ADR BI build-vs-embed.
- **Dependência:** ADR estratégia de coleta/histórico.

