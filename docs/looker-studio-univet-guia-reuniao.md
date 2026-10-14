# Guia Rápido: Dashboard Executivo Looker Studio (Univet Loupes)
## Modelo Pronto para Apresentação em Reunião

Este guia descreve como colocar o Dashboard Executivo da **Univet Loupes** no ar em menos de 10 minutos no **Looker Studio** para a reunião de alinhamento, utilizando os dados realistas gerados na pasta [`apps/api/seed_data/looker_mock/`](file:///c:/Users/Lenovo/Desktop/EG/bioma/apps/api/seed_data/looker_mock).

---

## 1. Passo a Passo Rápido para Montar no Looker Studio

### Passo 1: Subir os Dados para o Google Sheets ou BigQuery
1. Abra o [Google Drive](https://drive.google.com) na conta da **EG** (ou conta Google de trabalho).
2. Crie uma planilha chamada `Univet - Dados BI (Mock Seed)`.
3. Crie 3 abas na planilha e importe os 3 arquivos gerados:
   - Aba 1: `Leads Kommo` ← Importar [`univet_leads_kommo.csv`](file:///c:/Users/Lenovo/Desktop/EG/bioma/apps/api/seed_data/looker_mock/univet_leads_kommo.csv)
   - Aba 2: `Vendas Nomus` ← Importar [`univet_vendas_nomus.csv`](file:///c:/Users/Lenovo/Desktop/EG/bioma/apps/api/seed_data/looker_mock/univet_vendas_nomus.csv)
   - Aba 3: `Aquisição Canais` ← Importar [`univet_aquisicao_canais.csv`](file:///c:/Users/Lenovo/Desktop/EG/bioma/apps/api/seed_data/looker_mock/univet_aquisicao_canais.csv)
*(Como alternativa, você pode criar as 3 tabelas no BigQuery da EG com o mesmo esquema).*

### Passo 2: Criar o Relatório no Looker Studio
1. Acesse [lookerstudio.google.com](https://lookerstudio.google.com) na conta da EG.
2. Clique em **Criar → Relatório**.
3. Selecione o conector **Google Planilhas** (ou **BigQuery**) e aponte para a planilha criada acima.
4. Nomeie o relatório como: `Univet Loupes Brasil — Cockpit Executivo & Inteligência Comercial`.

---

## 2. Estrutura das 3 Telas para Apresentar na Reunião

### Tela 1: Visão Executiva & Funil de Conversão (Diretoria / Sócios)
*Objetivo: Demonstrar o ROI total, volume de negócios e o funil de vendas ponta a ponta.*

- **Scorecards no Topo**:
  1. `Faturamento Real (Nomus)`: Soma de `valor_total_faturado` da tabela de vendas (Ex.: R$ 164.500).
  2. `Total de Leads Gerados`: Contagem de `lead_id` (Ex.: 150 leads).
  3. `Taxa de Conversão Global`: (Vendas Ganhas / Total Leads) × 100 (Ex.: 11,3%).
  4. `Ticket Médio Faturado`: Média de `valor_total_faturado` (Ex.: R$ 9.676).
  5. `CAC Médio`: Média de `cac_reais` (Ex.: R$ 1.450).

- **Gráficos da Página**:
  - **Funil de Vendas Comercial (Gráfico de Barras horizontais ou Funil)**:
    - Etapas: `Novo Lead` → `Contato Inicial (Bruna)` → `Demonstração Agendada` → `Proposta Enviada` → `Venda Ganha (Nomus)`.
  - **Origem dos Leads (Gráfico de Rosca)**:
    - Dimensão: `origem` (`SEO Orgânico`, `Google AI Overview - GEO`, `Google Ads`, `Instagram`, etc.).
  - **Mix de Produtos Mais Vendidos (Gráfico de Barras)**:
    - Dimensão: `produto` da tabela de vendas Nomus.
  - **Filtros Globais**: Período de Data, Segmento Clínico e UF.

---

### Tela 2: Performance Comercial & Representantes Regionais (Gestão Comercial)
*Objetivo: Demonstrar como cada representante e região está performando e onde os leads estão sendo perdidos.*

- **Tabela Dinâmica de Representantes**:
  - Dimensão: `representante`, `uf`.
  - Métricas:
    - `Leads Recebidos` (Contagem de Leads).
    - `Visitas/Demonstrações Agendadas` (Contagem onde `data_visita` não é nulo).
    - `Vendas Fechadas` (Contagem de Vendas Ganhas).
    - `Faturamento Total` (Soma de R$ faturado).
    - `Taxa de Fechamento` (Vendas / Leads %).
- **Gráficos da Página**:
  - **Mapa Geográfico do Brasil**: Densidade de receita faturada e leads por estado (`uf`).
  - **Motivos de Perda (Gráfico de Pareto)**:
    - Dimensão: `motivo_perda` (`Preço elevado`, `Concorrência`, `Sem representante na região`, etc.).

---

### Tela 3: Aquisição, Mídia & Inteligência SEO/GEO (Marketing & Growth)
*Objetivo: Demonstrar a eficiência do investimento da Evergreen em SEO, GEO e tráfego pago.*

- **Tabela Comparativa de Canais**:
  - Colunas: `Canal`, `Visitas`, `Investimento (R$)`, `Leads Gerados`, `Vendas Ganhas`, `Receita Faturada (R$)`, `CAC (R$)`, `ROAS`.
- **Destaque Estratégico (O diferencial da EG)**:
  - Destacar a linha de **Google AI Overview (GEO)** e **Google Orgânico (SEO)** mostrando **CAC $0,00** e **ROAS Infinito**, provando que as buscas por IA e o posicionamento orgânico geram médicos qualificados com o menor custo por aquisição.

---

## 3. Discurso Executivo Sugerido para a Reunião

> *"Nossa arquitetura foi desenhada para eliminar o ponto cego entre o marketing e o caixa da empresa.*
> *Hoje, nós acompanhamos a jornada completa:*
> *1. O médico faz uma busca no Google ou pergunta para uma IA generativa (SEO/GEO).*
> *2. Ele cai no WhatsApp ou site da Univet e o Kommo registra a oportunidade com os 12 campos clínicos preenchidos automaticamente.*
> *3. A Bruna encaminha para o representante regional realizar o teste da lupa.*
> *4. Quando o pedido é emitido e faturado no Nomus ERP, o BI atualiza instantaneamente a receita faturada e o ROI de cada canal e representante.*
> *O dashboard que estamos apresentando já está preparado para receber esses dados em tempo real."*
