# Pesquisa Técnica: Univet Loupes Brasil — Ecossistema Integrado (CRM, ERP, IA Determinística e BI)

## Sumário Executivo
Este documento consolida a pesquisa aprofundada solicitada para a esteira da **Univet Loupes Brasil**, unindo:
1. **ERP Nomus Industrial**: Arquitetura REST API, autenticação e sincronização de pedidos de venda faturados.
2. **Kommo CRM (v4)**: Pipeline comercial, ciclo de vida e mapeamento dos 12 campos personalizados da operação da Bruna (extraídos do documento `Configuração Kommo - Univet Loupes (1).docx`).
3. **IA Determinística para CRM (Laya vs. Jev)**: Modelos de decisão não-autorregressivos de saída tipada para inferência em tempo real sem alucinações nem custos por token.
4. **Arquitetura de BI Ponta a Ponta**: Comparativo entre Looker Studio + BigQuery vs. Cockpit Nativo Bioma para a jornada completa (SEO/GEO + Mídia + CRM + ERP).

---

## 1. ERP Nomus Industrial — Arquitetura de Integração

### 1.1 Contexto e Papel na Operação
O **Nomus Industrial** é o ERP que gerencia estoque, ordens de produção, cadastros fiscais (CNPJ/Inscrição Estadual), emissão de NF-e e faturamento das lupas e sistemas de iluminação Univet.
No modelo operacional da Univet:
- A prospecção e negociação ocorrem no **Kommo CRM** (conduzidos pela Bruna e representantes regionais).
- O pedido formal e faturamento ocorrem no **Nomus**.
- A inteligência comercial precisa que quando uma venda é faturada no Nomus, o negócio correspondente no Kommo seja automaticamente dado como **"Venda Ganha" (Closed Won)** com valor real e número da NF-e, retroalimentando o ROI das fontes de tráfego (SEO/GEO, Meta Ads, Google Ads).

### 1.2 Especificações da API REST Nomus
- **Autenticação**: HTTP Basic Auth (`Authorization: Basic base64(token_ou_usuario:senha)`) ou cabeçalhos de token da instância corporativa da Univet.
- **Base URL Típica**: `https://[instancia].nomus.com.br/nomus/rest/`
- **Endpoints Chave**:
  - `GET /rest/pedidos_venda`: Consulta de pedidos de venda.
    - Filtros: `dataEmissaoInicial`, `dataEmissaoFinal`, `codigoCliente`, `statusPedido` (`FATURADO`, `LIBERADO_FATURAMENTO`, `CANCELADO`).
    - Retorno: Dados de cabeçalho (número do pedido, data, valor total, status, código e CNPJ do cliente) e itens (código do produto, quantidade, valor unitário).
  - `GET /rest/clientes`: Consulta de clientes cadastrados por CNPJ, CPF, razão social ou e-mail.
  - `POST /rest/pedidos_venda` (opcional caso a automação crie o pré-pedido a partir do Kommo).

### 1.3 Estratégia de Sincronização Nomus → Kommo
1. **Trigger Periódico (Cron a cada 15 min no n8n ou Bioma Worker)**:
   - Consulta `GET /rest/pedidos_venda` com filtro `statusPedido=FATURADO` e `dataUltimaModificacao >= now() - 30min`.
2. **Reconciliação e Match de Entidades**:
   - Chave Primária: CNPJ / CPF do cliente.
   - Chave Secundária: Telefone normalizado E.164 ou E-mail.
   - Chave Terciária: ID do Lead Kommo (caso gravado no campo de observação do pedido no Nomus).
3. **Atualização no Kommo CRM (API v4)**:
   - `PATCH /api/v4/leads/{lead_id}`:
     - `status_id`: ID da etapa "Venda Ganha" (142).
     - `price`: Valor total faturado no Nomus.
     - `custom_fields_values`: Número do pedido Nomus, Chave da NF-e, Data do faturamento.

---

## 2. Kommo CRM — Estrutura e Operação da Univet

### 2.1 Análise do Documento de Configuração (`Configuração Kommo - Univet Loupes (1).docx`)
A análise do documento oficial de implantação da Univet revela diretrizes operacionais fundamentais:
- **Operadora Principal**: Bruna (atendimento comercial, triagem e encaminhamento).
- **Diretriz de Design de Processo**: **Atrito Mínimo**. A Bruna não pode ter que preencher formulários longos e repetitivos enquanto atende 30 a 50 médicos e dentistas simultaneamente no WhatsApp.
- **Diferenciação Crítica**:
  - *Tipo de atendimento*: A natureza do contato (Venda nova, Pós-venda, Garantia, Reparo, Peças, Outro).
  - *Solicitação inicial*: O que o lead pediu explicitamente no primeiro contato (Preço, Catálogo, Dúvida técnica, Agendamento de Visita, Contato de Representante).

### 2.2 Os 12 Campos Personalizados Oficiais

| Nº | Nome do Campo | Tipo de Dado | Opções / Regra |
|---|---|---|---|
| 1 | **Origem do lead** | Select | Google Orgânico (SEO), Google AI Overview (GEO), Google Ads, Meta Ads (Instagram/FB), Indicação de Colega, Congresso/Evento, Outro |
| 2 | **Origem detalhada** | Text / Select | Palavra-chave, Nome do Congresso, Perfil do Influenciador/Parceiro |
| 3 | **Tipo de atendimento** | Select | `Venda nova`, `Pós-venda`, `Garantia`, `Reparo`, `Peças/Acessórios`, `Outro` |
| 4 | **Solicitação inicial** | Select | `Preço`, `Catálogo`, `Dúvida técnica`, `Visita presencial`, `Representante regional`, `Outro` |
| 5 | **Produto de interesse** | Multiselect | `Lupa Galileu (Quick)`, `Lupa Prismática (Ergo/High)`, `Lupa TTL Personalizada`, `Iluminação LED EOS`, `Óculos de Proteção Laser`, `Acessórios/Armações` |
| 6 | **Segmento** | Select | `Odontologia Clínica`, `Cirurgia Bucomaxilofacial`, `Implantodontia`, `Endodontia`, `Cirurgia Geral / Plástica`, `Oftalmologia`, `Veterinária`, `Estudante/Residente`, `Outro` |
| 7 | **UF** | Select | 27 UFs do Brasil (AC a TO) |
| 8 | **Região / Representante** | Select | Distribuição automática conforme UF (ex: SP Capital, SP Interior, Sul, RJ/ES, MG, Nordeste, Centro-Oeste) |
| 9 | **Motivo de perda** | Select | Obrigatório na perda: `Preço/Orçamento elevado`, `Comprou da concorrência`, `Sem interesse imediato`, `Contato inválido / Não respondeu`, `Região sem atendimento presencial` |
| 10 | **Data da visita** | Date | Data agendada para demonstração prática com o representante |
| 11 | **Resumo do atendimento** | Multiline Text | Síntese de necessidades clínicas e preferências de magnificação |
| 12 | **Instagram** | Text | Handle `@perfil` do profissional para enriquecimento social e prospecção |

---

## 3. IA Determinística para CRM: Laya vs. Jev (Modelos de Decisão com Saída Tipada)

### 3.1 O Problema dos LLMs Tradicionais no CRM
Usar LLMs convencionais (GPT-4o, Claude 3.5 Sonnet) para preencher campos de CRM apresenta gargalos severos:
1. **Alucinação de Enums**: O LLM gera variações de texto livre (ex.: "Odonto", "Dentista Geral", "Odontologia") quando o Kommo exige o ID exato da opção `Odontologia Clínica`.
2. **Latência Alta**: Decodificação autorregressiva token a token leva entre 1.500ms e 4.000ms.
3. **Custo Recorrente**: Consumo de tokens a cada mensagem recebida no WhatsApp, inviabilizando escala gratuita.
4. **Falta de Tipagem Estrita**: Modos JSON de LLMs garantem sintaxe, mas não garantem invariantes lógicos ou garantias semânticas formais.

### 3.2 O Conceito de Modelos de Decisão (System One / Non-Autoregressive)
Modelos de saída tipada (System One Decision Models) substituem a geração de texto por **classificação e pontuação direta de estruturas tipadas**:
- O modelo processa o prompt e a mensagem do usuário em uma única passada de inferência (encoder-only ou latent decision).
- A saída é diretamente mapeada para tipos primitivos formais:
  - `Choice[Enum]`: Seleciona exatamente 1 opção de um conjunto fechado de IDs.
  - `Score[float]`: Avalia probabilidade ou fit de qualificação (0.0 a 1.0).
  - `Noul` (None/Null): Quando a informação não foi expressa pelo lead, sem inventar suposições.

### 3.3 Comparativo: Laya vs. Jev

| Critério | Laya (Convai Innovations) | Jev (TypeSafe AI) |
|---|---|---|
| **Licença / Acesso** | **Open-weight (Apache 2.0)** — Código aberto | **Fechado / SaaS Gerenciado** (API proprietária) |
| **Custo por Inferência** | **$0.00** (roda localmente na CPU/GPU do host) | Cobrança por chamada API / tier mensal |
| **Latência Típica** | **~30ms – 50ms** | ~120ms – 250ms (depende de rede HTTP) |
| **Garantia de Tipagem** | Decorators em Python/TypeScript com Pydantic nativo | SDK com esquemas JSON Schema remotos |
| **Privacidade / LGPD** | 100% On-premise (os dados do lead nunca saem do servidor) | Dados transitam pela infraestrutura externa do provedor |
| **Adequação Univet** | **Altamente Recomendado**: Elimina custos fixos para a Evergreen e Univet, velocidade instantânea no n8n/FastAPI. | Alternativa caso a equipe não queira manter o runtime local. |

### 3.4 Arquitetura do Classificador Determinístico Univet
```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class TipoAtendimento(str, Enum):
    VENDA_NOVA = "Venda nova"
    POS_VENDA = "Pós-venda"
    GARANTIA = "Garantia"
    REPARO = "Reparo"
    PECAS = "Peças/Acessórios"
    OUTRO = "Outro"

class SolicitacaoInicial(str, Enum):
    PRECO = "Preço"
    CATALOGO = "Catálogo"
    DUVIDA_TECNICA = "Dúvida técnica"
    VISITA = "Visita presencial"
    REPRESENTANTE = "Representante regional"
    OUTRO = "Outro"

class SegmentoClinico(str, Enum):
    ODONTOLOGIA = "Odontologia Clínica"
    BUCOMAXILO = "Cirurgia Bucomaxilofacial"
    IMPLANTODONTIA = "Implantodontia"
    CIRURGIA_GERAL = "Cirurgia Geral / Plástica"
    VETERINARIA = "Veterinária"
    OUTRO = "Outro"

class LeadTriageDecision(BaseModel):
    tipo_atendimento: TipoAtendimento
    solicitacao_inicial: SolicitacaoInicial
    segmento: Optional[SegmentoClinico] = None
    uf: Optional[str] = Field(None, pattern=r"^[A-Z]{2}$")
    confianca: float = Field(ge=0.0, le=1.0)
```
- **Fluxo Operacional**:
  1. Lead manda primeira mensagem no WhatsApp Univet (ou via formulário).
  2. n8n intercepta via Webhook e chama o endpoint de inferência tipada (`/api/v1/triage/classify`).
  3. O modelo (Laya local ou fallback Instructor Pydantic) extrai os 12 campos tipados em menos de 50ms.
  4. O n8n aplica `PATCH /api/v4/leads/{id}` no Kommo preenchendo os campos antes mesmo da Bruna abrir a conversa.
  5. A Bruna já visualiza o lead com o Segmento, UF, Tipo de Atendimento e Solicitação identificados, precisando apenas confirmar ou ajustar.

---

## 4. Arquitetura de BI Ponta a Ponta: Looker Studio + BigQuery vs. Bioma Nativo

### 4.1 Desafio de Negócio
A Univet necessita de visibilidade da jornada completa:
$$\text{SEO/GEO (Tráfego Orgânico/IA)} \longrightarrow \text{Mídia Paga (Google/Meta)} \longrightarrow \text{Leads & Pipeline (Kommo)} \longrightarrow \text{Faturamento Real (Nomus)}$$

### 4.2 Comparativo Estratégico

| Dimensão | Opção A: Looker Studio + BigQuery | Opção B: Cockpit 100% Nativo no Bioma |
|---|---|---|
| **Tempo de Implementação (Time-to-Value)** | **Imediato (3 a 5 dias)** | Longo (4 a 6 semanas de desenvolvimento UI) |
| **Conectores Nativos** | Nativos com Google Analytics 4, Search Console, BigQuery | Exige ingestão e pipelines ETL manuais em SQL |
| **Flexibilidade Visual para o Cliente** | Alta: Filtros dinâmicos, drill-down de datas, exportação PDF automática | Limitada aos componentes pré-construídos no React |
| **Custo de Infraestrutura** | Praticamente zero (BigQuery free-tier cobre até 10 GB/mês; Looker Studio é gratuito) | Custo de processamento e queries locais |
| **Experiência de Marca** | Interface padrão Google (embedável via iframe no Bioma) | 100% proprietária, sensação de software sob medida |

### 4.3 Recomendação: Modelo Híbrido em Camadas
1. **Camada de Dados (BigQuery)**:
   - Centraliza tabelas diárias: `ga4_traffic`, `gsc_keywords_geo`, `kommo_leads`, `nomus_sales`.
   - O n8n descarrega os snapshots diários do Kommo e Nomus via API no BigQuery.
2. **Camada Analítica Univet (Looker Studio)**:
   - Dashboard Executivo Univet construído em Looker Studio, cobrindo:
     - CAC Real por canal (SEO vs Ads).
     - Taxa de conversão por representante/região.
     - Tempo médio entre primeiro contato e faturamento no Nomus.
     - LTV e taxa de recompra de peças/óculos.
   - O dashboard pode ser incorporado diretamente em uma aba "Visão Executiva (BI)" dentro do Bioma através de iframe seguro com permissão por workspace.
3. **Camada Operacional (Bioma Nativo)**:
   - O Bioma mantém o que exige **ação e escrita bidirecional**:
     - Painel de Deduplicação e Higienização de Leads Kommo.
     - Gestão de credenciais Nomus e n8n.
     - Controle e monitoramento dos prompts e provedores de IA.

---

## 5. Próximos Passos Recomendados
1. Validar com a Univet e alinhar decisões no `/grill-me`.
2. Configurar o conector BigQuery no n8n para consolidação analítica.
3. Subir o serviço de classificação determinística com Laya no worker Bioma.
4. Conectar o webhook do Kommo para preenchimento em tempo real dos 12 campos da Bruna.
