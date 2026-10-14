# Guia Completo: Configuração do BigQuery, Looker Studio e n8n via API & MCP

## Sumário
1. [Status Atual: n8n MCP & Workflows da Univet](#1-status-atual-n8n-mcp--workflows-da-univet)
2. [Passo a Passo: Google Cloud & BigQuery](#2-passo-a-passo-google-cloud--bigquery)
3. [Como Configurar o BigQuery MCP Server na IDE](#3-como-configurar-o-bigquery-mcp-server-na-ide)
4. [Passo a Passo: Looker Studio (Dashboards Executivos)](#4-passo-a-passo-looker-studio-dashboards-executivos)
5. [Looker MCP Server: Semântica & LookML com IA](#5-looker-mcp-server-semântica--lookml-com-ia)

---

## 1. Status Atual: n8n MCP & Workflows da Univet

### 1.1 Conexão Validada
- **URL da Instância**: `https://n8n.evergreenmkt.com.br`
- **MCP Endpoint**: `https://n8n.evergreenmkt.com.br/mcp-server/http`
- **Autenticação**: Token JWT fornecido foi validado com sucesso (HTTP 200).

### 1.2 Workflow Univet Já Criado via API
O primeiro workflow da stack da Univet já foi provisionado diretamente na sua instância n8n através da API REST com `availableInMCP: true`:
- **ID do Workflow**: `LLRwHjRDsqCAKmAo`
- **Nome**: `Univet Loupes - Stack de Automações n8n`
- **Nós Integrados**:
  1. `Webhook Ingestão (Site / WhatsApp Univet)`: Endpoint público para receber novos leads.
  2. `Pre-Check Normalizer`: Sanitização de telefone E.164 (+55) para prevenção preventiva de duplicatas.
  3. `Cron Nomus Polling (15m)`: Verificação automática de pedidos faturados no Nomus ERP.
  4. `Atualizar Lead no Kommo para Ganho`: Atualização de etapa e valor real faturado via API v4.
  5. `Notificar Bioma Cockpit (BI)`: Envio de evento para o BI.

### 1.3 MCP Global do n8n Configurado
O proxy local `n8n_proxy.js` foi registrado e está disponível nos clientes:
- Antigravity IDE (`C:\Users\Lenovo\.gemini\config\mcp_config.json`)
- Claude Code (`C:\Users\Lenovo\.claude.json`)
- Codex (`C:\Users\Lenovo\.codex\config.toml`)

---

## 2. Passo a Passo: Google Cloud & BigQuery

Para centralizar os dados da Univet no BigQuery na conta da EG e permitir consultas via código e MCP:

### Passo 1: Criar/Selecionar o Projeto no Google Cloud
1. Acesse o [Google Cloud Console](https://console.cloud.google.com).
2. No seletor de projetos no topo, clique em **Novo Projeto** (ou escolha um existente da EG).
3. Nomeie o projeto: ex.: `eg-bioma-analytics` (anote o **Project ID**, ex.: `eg-bioma-analytics-412345`).

### Passo 2: Ativar a BigQuery API
1. No menu lateral, acesse **APIs e Serviços → Biblioteca**.
2. Pesquise por **BigQuery API** e clique em **Ativar** (Enable).

### Passo 3: Criar a Conta de Serviço (Service Account)
1. Acesse **IAM e Administração → Contas de Serviço**.
2. Clique em **+ Criar conta de serviço**.
3. Nome: `bioma-bigquery-agent`.
4. Atribua os papéis (Roles):
   - **Administrador do BigQuery** (`roles/bigquery.admin`) ou
   - **Editor de dados do BigQuery** (`roles/bigquery.dataEditor`) + **Usuário de jobs do BigQuery** (`roles/bigquery.jobUser`).
5. Conclua a criação, clique na conta criada, vá na aba **Chaves (Keys) → Adicionar chave → Criar nova chave → JSON**.
6. O download do arquivo `.json` de credencial será feito. Salve-o em local seguro (ex.: `C:\Users\Lenovo\.gemini\gcp-service-account.json`).

### Passo 4: Criar o Dataset da Univet
1. No console do BigQuery ([console.cloud.google.com/bigquery](https://console.cloud.google.com/bigquery)):
2. Clique nos 3 pontinhos ao lado do ID do seu projeto e selecione **Criar conjunto de dados (Create dataset)**.
3. ID do conjunto de dados: `univet_dw`.
4. Região de dados: `southamerica-east1 (São Paulo)` ou `us-central1`.
5. Clique em **Criar conjunto de dados**.

---

## 3. Como Configurar o BigQuery MCP Server na IDE

O Google Cloud lançou o **BigQuery MCP Server** (oficial) através do **MCP Toolbox for Databases**. Ele permite que agentes de IA inspecionem schemas, listem tabelas e executem queries SQL diretamente pela IDE.

### Configuração no `mcp_config.json` (Antigravity):

Adicione o bloco abaixo em `C:\Users\Lenovo\.gemini\config\mcp_config.json`:

```json
{
  "mcpServers": {
    "bigquery": {
      "command": "npx",
      "args": ["-y", "@google-cloud/bigquery-mcp-server"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "C:\\Users\\Lenovo\\.gemini\\gcp-service-account.json",
        "BIGQUERY_PROJECT_ID": "SEU_PROJECT_ID_GCP"
      }
    }
  }
}
```

### O que os Agentes de IA conseguem fazer via BigQuery MCP:
- `list_dataset_ids`: Descobre quais bases de clientes existem.
- `list_table_ids`: Lista as tabelas `leads_kommo`, `vendas_nomus`, etc.
- `get_table_info`: Lê as colunas e tipos de dados de cada tabela.
- `execute_sql`: Cria views e executa queries analíticas para alimentar o Looker.

---

## 4. Passo a Passo: Looker Studio (Dashboards Executivos)

O **Looker Studio** ([lookerstudio.google.com](https://lookerstudio.google.com)) é a ferramenta visual de relatórios que a diretoria da Univet vai visualizar.

### Passo 1: Conectar o Looker Studio ao BigQuery
1. Acesse [lookerstudio.google.com](https://lookerstudio.google.com) logado na conta Google da EG.
2. Clique em **Criar → Fonte de Dados**.
3. Selecione o conector oficial **BigQuery**.
4. Selecione:
   - **Meus Projetos** → Escolha o projeto GCP da EG (`eg-bioma-analytics`).
   - **Conjunto de dados** → Escolha `univet_dw`.
   - **Tabela** → Escolha `leads_kommo` (ou uma view SQL consolidada).
5. Clique em **Conectar** no canto superior direito.

### Passo 2: Criar o Relatório com as 3 Telas
1. Clique em **Criar Relatório**.
2. Monte as 3 páginas estruturadas no nosso guia [`docs/looker-studio-univet-guia-reuniao.md`](file:///c:/Users/Lenovo/Desktop/EG/bioma/docs/looker-studio-univet-guia-reuniao.md):
   - **Página 1**: *Visão Executiva & Funil Unificado* (Scorecards de Faturamento, Taxa de Conversão, Ticket Médio e Funil Comercial).
   - **Página 2**: *Performance Comercial & Representantes* (Tabela por Representante, Mapa de Calor por UF, Pareto de Motivos de Perda).
   - **Página 3**: *Aquisição & ROI (SEO / GEO / Ads)* (CAC e ROAS por canal).

---

## 5. Looker MCP Server: Semântica & LookML com IA

### O Que É o Looker MCP Server Oficial do Google
Conforme anunciado no blog do Google Cloud (*Introducing Looker MCP Server*), o **Looker MCP Server** é voltado para instâncias corporativas do **Looker (Core / Enterprise)** que utilizam **LookML** (a camada semântica unificada do Google).

- **Como ele funciona**:
  - Em vez de a IA tentar adivinhar queries SQL complexas que podem errar a lógica de negócio, a IA consulta o **Looker MCP Server**.
  - O Looker traduz a pergunta em linguagem natural para dimensões e medidas governadas do LookML.
  - Garante que métricas como *CAC*, *LTV* e *Venda Faturada* sigam a mesma regra matemática formal em toda a empresa.

- **Quando Usar**:
  - **Looker Studio (Atual Univet)**: Ideal para a entrega imediata, relatórios rápidos e visuais para a reunião sem custo de licenciamento corporativo.
  - **Looker MCP Server**: Usado caso a EG ou a Univet contratem uma instância gerenciada do Google Cloud Looker Core para consultas analíticas conversacionais de ponta a ponta.
