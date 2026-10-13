# Plano Diretor de Execução: Univet Loupes Brasil
## BI Executivo, Agente de Pré-qualificação, Kommo CRM e ERP Nomus

---

## 1. Matriz de Responsabilidades & O que Precisa de Você

Para avançarmos de forma cirúrgica e sem bloqueios, esta é a divisão entre o que a engenharia executa em código e o que precisa ser fornecido por você:

### 1.1 Checklist de Credenciais e Acessos Necessários

| Item | Origem | O que precisa fornecer | Onde será usado |
|---|---|---|---|
| **Kommo CRM** | Painel Kommo Univet | 1. Subdomínio da conta (ex.: `univet.kommo.com`)<br>2. Long-Lived Token / Chave OAuth privada<br>3. ID do Pipeline Principal | Conexão API v4 via n8n e script de configuração |
| **Nomus ERP** | Painel Nomus Univet | 1. URL base da API REST (ex.: `https://univet.nomus.com.br/univet`)<br>2. Usuário e Senha (ou Token Base64)<br>3. Nome exato do status de faturamento (ex.: `FATURADO`) | Sincronização automática de pedidos faturados |
| **Google Cloud (BigQuery)** | Console GCP | 1. ID do Projeto GCP (ex.: `univet-bioma-analytics`)<br>2. Arquivo de Chave de Conta de Serviço (JSON) com permissão de edição no BigQuery | Armazenamento analítico e alimentação do Looker Studio |
| **Google Analytics 4 & Search Console** | Google Cloud / Search Console | Acesso ou vínculo dos relatórios GSC/GA4 para exportação ao BigQuery | Alimentação de dados de tráfego SEO e campanhas |
| **WhatsApp / Mensageria** | Provedor de Mensagens | Identificação do conector ativo no Kommo (Kommo WhatsApp Nativo, Z-API, Evolution API, Twilio) | Gatilho para o Agente de Pré-qualificação no n8n |

---

## 2. Agente de Pré-qualificação: Arquitetura & Levantamento de LLMs

### 2.1 O Papel do Agente no Início do Funil
O agente opera no primeiro ponto de contato (WhatsApp comercial da Univet), com uma missão estrita:
1. Recepcionar com empatia e tom profissional médico/odontológico.
2. Identificar a especialidade clínica, localização (UF/cidade) e necessidade principal (nova lupa, iluminação, orçamento ou assistência técnica).
3. Preencher os 12 campos no Kommo em segundo plano.
4. Fazer o transbordo imediato para a **Bruna** e para o **Representante Regional**.

### 2.2 Comparativo Técnico de Modelos de Linguagem (LLM)

| Modelo | Latência Média | Custo Estimado | Janela de Contexto | Adequação ao Caso Univet |
|---|---|---|---|---|
| **Google Gemini 2.0 Flash / 1.5 Flash** *(Recomendado)* | **~350ms** | Praticamente **$0.00** (Free Tier generoso no AI Studio; $0.075 / 1M tokens) | 1.000.000 tokens | **Ideal**: Excelente compreensão do vocabulário cirúrgico/odontológico, catálogo técnico completo cabe na memória de contexto, latência baixa. |
| **Llama 3.3 70B (via Groq)** | ~250ms | ~$0.59 / 1M tokens | 128.000 tokens | Muito rápido, porém menor flexibilidade para injetar catálogos extensos em PDF. |
| **Claude 3.5 Haiku** | ~450ms | $0.80 / 1M tokens input | 200.000 tokens | Excelente tom humano, mas custo superior para volume alto de mensagens. |

### 2.3 Arquitetura Híbrida: Diálogo (Gemini Flash) + Decisão Tipada (Laya)
- **Camada Conversacional (Gemini Flash)**: Conduz o diálogo no WhatsApp de forma natural.
- **Camada Determinística (Laya no Bioma Worker)**: Analisa o texto e extrai os campos exatos sem risco de alucinar enums:
  - `Tipo de atendimento` → `Venda nova`
  - `Solicitação inicial` → `Preço` ou `Visita presencial`
  - `Segmento` → `Odontologia Clínica` ou `Cirurgia Bucomaxilofacial`
  - `UF` → `SP`
  - `Produto de interesse` → `Lupa Prismática Ergo`

---

## 3. Telas e Dados do BI (Looker Studio)

O BI será estruturado em **3 Telas Principais**:

### Tela 1: Visão Executiva & Funil Unificado (Diretoria)
- **Cartões de KPI (Topo)**:
  - Faturamento Total Faturado (Nomus ERP) [R$]
  - Total de Oportunidades Criadas (Kommo CRM)
  - Taxa de Conversão Global (Leads → Faturados %)
  - CAC Global Estimado (Mídia ÷ Pedidos Faturados)
  - Ticket Médio por Venda [R$]
- **Gráficos**:
  - **Funil Comercial**: Visitantes Únicos → Leads Iniciais → Qualificados → Visitas Agendadas → Propostas → Vendas Faturadas.
  - **Faturamento x Mês (Barras e Linhas)**: Comparativo com meta mensal.
  - **Origem dos Leads (Gráfico de Pizza)**: SEO Orgânico, Buscas IA (GEO), Google Ads, Meta Ads (Instagram), Indicação, Congressos.
- **Filtros Globais**: Período, Segmento Clínico, UF/Região.

### Tela 2: Performance Comercial & Representantes Regionais
- **Tabela Detalhada por Representante**:
  - Representante | UF/Região | Leads Atribuídos | Demonstrações Realizadas | Propostas | Vendas Fechadas | Faturamento Total (R$) | Ciclo Médio (Dias).
- **Gráficos**:
  - Mapa de Calor Geográfico do Brasil por volume de faturamento e densidade de leads.
  - Ranking de Representantes (Bar chart horizontal).
  - Análise de Motivos de Perda (Pareto): Preço elevado, Comprou concorrente, Não respondeu, Sem cobertura regional.

### Tela 3: Aquisição, Mídia & Inteligência SEO/GEO
- **Indicadores de Tráfego e Mídia**:
  - ROAS por Campanha (Google Ads vs Meta Ads).
  - Top 20 Consultas no Google Search Console que geraram leads (SEO).
  - Presença em Buscas Generativas (GEO): Menções da marca Univet em IA (ChatGPT, Gemini, Perplexity).
  - Mix de Produtos: Volume e receita por linha de produto (Galileu vs Prismática vs Iluminação EOS).

---

## 4. Automações e Configurações que Faltam no Kommo CRM

Com base no documento `Configuração Kommo - Univet Loupes (1).docx`:

1. **Criação e Padronização dos 12 Campos**:
   - `Origem do lead` (Select)
   - `Origem detalhada` (Text / Select)
   - `Tipo de atendimento` (Select: Venda nova, Pós-venda, Garantia, Reparo, Peças/Acessórios, Outro)
   - `Solicitação inicial` (Select: Preço, Catálogo, Dúvida técnica, Visita presencial, Representante regional, Outro)
   - `Produto de interesse` (Multiselect)
   - `Segmento` (Select: Odontologia Clínica, Cirurgia Bucomaxilo, Implantodontia, Cirurgia Geral, Veterinária, etc.)
   - `UF` (Select com as 27 UFs)
   - `Região / Representante indicado` (Select com mapeamento por estado)
   - `Motivo de perda` (Select obrigatório na etapa Perdido)
   - `Data da visita` (Date picker obrigatório na etapa Visita Agendada)
   - `Resumo do atendimento` (Multiline text)
   - `Instagram` (Text)
2. **Regras de Validação no Pipeline**:
   - Bloquear avanço para "Perdido" sem preenchimento do *Motivo de perda*.
   - Bloquear avanço para "Demonstração/Visita" sem preenchimento da *Data da visita*.
3. **Automações de Distribuição (Salesbot / Digital Pipeline)**:
   - Quando a UF for selecionada (ex.: SP Interior), criar tarefa automática para o Representante correspondente.
4. **Webhooks Ativos para o n8n**:
   - Configurar webhook em `Configurações → Integrações → Webhooks` disparando nos eventos `lead_added` e `lead_status_changed`.

---

## 5. Cronograma de Execução e Próximos Passos

1. **Etapa 1 (Hoje - Design & Estrutura)**:
   - Validar o layout e schema visual do Looker Studio.
   - Criar o script de provisionamento dos 12 campos no Kommo via API.
2. **Etapa 2 (Amanhã - Ingestão & Automações n8n)**:
   - Ativar o webhook de classificação Laya no worker Bioma.
   - Configurar o sync de pedidos faturados do Nomus no n8n.
3. **Etapa 3 (Consolidação BI & Validação)**:
   - Configurar as tabelas analíticas no BigQuery.
   - Conectar o Looker Studio e validar com dados reais da Univet.
